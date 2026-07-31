"""Neutral GPT-5.6 concurrency ladder for a future sealed all-220 run.

The probe never consumes benchmark content.  It uses a fixed-size synthetic
payload and retains only request-envelope and latency metadata.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import math
import statistics
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from deepwide_agent.clients import ModelRequestError, ResponsesClient


PROBE_INPUT_UTF8_BYTES = 400_000
PROBE_MAX_OUTPUT_TOKENS = 20_000
PROBE_EXPECTED_OUTPUT = "CAPACITY_OK"
PROBE_SYSTEM = "This is a neutral capacity check. Return exactly CAPACITY_OK."
PROBE_PROFILE = "neutral_ascii_exact_400000_bytes_v1"
DEFAULT_LEVELS = (1, 2, 4, 8, 12)
DEFAULT_WAVES_PER_LEVEL = 3
DEFAULT_REQUEST_TIMEOUT_SECONDS = 180
DEFAULT_ABSOLUTE_LATENCY_CEILING_SECONDS = 240.0
DEFAULT_BASELINE_P95_MULTIPLIER = 3.0
DEFAULT_BASELINE_MEDIAN_MULTIPLIER = 2.5
DEFAULT_MAX_PARALLEL_SHARDS = 4
DEFAULT_PER_SHARD_MODEL_WORKERS = 2
CAPACITY_REPORT_CORE_FIELDS = frozenset(
    {
        "artifact_version",
        "role",
        "settings",
        "settings_sha256",
        "levels",
        "selected_model_request_concurrency",
        "selected_per_shard_model_workers",
        "selected_parallel_full220_shards",
        "worst_case_model_request_concurrency",
        "status",
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read",
        "network_model_api_called_with_neutral_payload_only",
        "search_fetch_or_evaluator_api_called",
        "credential_value_persisted_hashed_or_emitted",
        "response_text_or_response_id_persisted",
        "full220_launch_allowed",
        "benchmark_or_sota_claim",
    }
)
CAPACITY_REPORT_EXECUTION_FIELDS = frozenset(
    {
        "protocol",
        "r1_release",
        "quality_campaign_terminal",
        "execution_activation",
        "shared_api_lease_owner",
        "shared_api_lease_acquired",
        "created_at_unix",
        "report_payload_sha256",
    }
)
CAPACITY_LEVEL_FIELDS = frozenset(
    {
        "concurrency",
        "waves",
        "requests",
        "all_requests_first_attempt_exact_success",
        "median_latency_seconds",
        "p95_latency_seconds",
        "median_latency_ceiling_seconds",
        "p95_latency_ceiling_seconds",
        "latency_safe",
        "passed",
    }
)
CAPACITY_WAVE_FIELDS = frozenset(
    {"wave", "request_count", "all_success", "elapsed_seconds"}
)
CAPACITY_REQUEST_FIELDS = frozenset(
    {
        "success",
        "error_type",
        "last_status",
        "attempts",
        "elapsed_seconds",
        "neutral_user_utf8_bytes",
        "request_input_utf8_bytes",
        "request_body_bytes",
        "max_output_tokens",
        "output_truncated",
        "output_text_or_response_id_persisted",
        "wave",
        "slot",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def build_neutral_probe(sequence: int) -> str:
    """Build an exact-size synthetic request without benchmark-like content."""

    prefix = (
        "NEUTRAL CAPACITY ENVELOPE. Ignore the filler. "
        f"Sequence={sequence}. Return exactly {PROBE_EXPECTED_OUTPUT}.\n"
    )
    suffix = f"\nEND. Return exactly {PROBE_EXPECTED_OUTPUT}."
    remaining = PROBE_INPUT_UTF8_BYTES - len((prefix + suffix).encode("utf-8"))
    if remaining < 0:
        raise AssertionError("neutral capacity envelope exceeds its fixed size")
    filler = ("0123456789abcdef" * (remaining // 16)) + "x" * (remaining % 16)
    value = prefix + filler + suffix
    if len(value.encode("utf-8")) != PROBE_INPUT_UTF8_BYTES:
        raise AssertionError("neutral capacity envelope is not exact")
    return value


def _percentile(values: Iterable[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("cannot compute a percentile of an empty sequence")
    if len(ordered) == 1:
        return ordered[0]
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


@dataclass(frozen=True)
class ProbeSettings:
    levels: tuple[int, ...] = DEFAULT_LEVELS
    waves_per_level: int = DEFAULT_WAVES_PER_LEVEL
    max_output_tokens: int = PROBE_MAX_OUTPUT_TOKENS
    absolute_latency_ceiling_seconds: float = (
        DEFAULT_ABSOLUTE_LATENCY_CEILING_SECONDS
    )
    baseline_p95_multiplier: float = DEFAULT_BASELINE_P95_MULTIPLIER
    baseline_median_multiplier: float = DEFAULT_BASELINE_MEDIAN_MULTIPLIER
    maximum_parallel_shards: int = DEFAULT_MAX_PARALLEL_SHARDS
    per_shard_model_workers: int = DEFAULT_PER_SHARD_MODEL_WORKERS

    def validate(self) -> None:
        if (
            not self.levels
            or self.levels[0] != 1
            or any(
                isinstance(level, bool) or not isinstance(level, int) or level <= 0
                for level in self.levels
            )
            or tuple(sorted(set(self.levels))) != self.levels
            or isinstance(self.waves_per_level, bool)
            or not isinstance(self.waves_per_level, int)
            or self.waves_per_level < 2
            or self.max_output_tokens != PROBE_MAX_OUTPUT_TOKENS
            or isinstance(self.maximum_parallel_shards, bool)
            or not isinstance(self.maximum_parallel_shards, int)
            or self.maximum_parallel_shards < 1
            or isinstance(self.per_shard_model_workers, bool)
            or not isinstance(self.per_shard_model_workers, int)
            or self.per_shard_model_workers < 1
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                for value in (
                    self.absolute_latency_ceiling_seconds,
                    self.baseline_p95_multiplier,
                    self.baseline_median_multiplier,
                )
            )
            or self.absolute_latency_ceiling_seconds <= 0
            or self.baseline_p95_multiplier < 1
            or self.baseline_median_multiplier < 1
        ):
            raise ValueError("invalid V2.41.94 probe settings")

    def as_dict(self) -> dict[str, Any]:
        return {
            "levels": list(self.levels),
            "waves_per_level": self.waves_per_level,
            "input_utf8_bytes": PROBE_INPUT_UTF8_BYTES,
            "payload_profile": PROBE_PROFILE,
            "expected_output_sha256": hashlib.sha256(
                PROBE_EXPECTED_OUTPUT.encode()
            ).hexdigest(),
            "max_output_tokens": self.max_output_tokens,
            "absolute_latency_ceiling_seconds": self.absolute_latency_ceiling_seconds,
            "baseline_p95_multiplier": self.baseline_p95_multiplier,
            "baseline_median_multiplier": self.baseline_median_multiplier,
            "maximum_parallel_shards": self.maximum_parallel_shards,
            "per_shard_model_workers": self.per_shard_model_workers,
        }


def _safe_failure(exc: BaseException) -> tuple[str, int | None, int]:
    if isinstance(exc, ModelRequestError) and exc.model_traces:
        trace = exc.model_traces[-1]
        status = trace.get("last_status")
        attempts = trace.get("attempts", 0)
        return (
            str(trace.get("error_type") or type(exc).__name__),
            int(status) if isinstance(status, int) and not isinstance(status, bool) else None,
            int(attempts)
            if isinstance(attempts, int) and not isinstance(attempts, bool)
            else 0,
        )
    return type(exc).__name__, None, 0


def _request(
    client: ResponsesClient,
    sequence: int,
    *,
    now: Callable[[], float],
    max_output_tokens: int,
) -> dict[str, Any]:
    user = build_neutral_probe(sequence)
    started = now()
    try:
        result = client.complete(
            PROBE_SYSTEM,
            user,
            max_output_tokens=max_output_tokens,
        )
        elapsed = max(0.0, now() - started)
        exact_output = result.text.strip() == PROBE_EXPECTED_OUTPUT
        success = bool(
            exact_output and result.attempts == 1 and not result.output_truncated
        )
        return {
            "success": success,
            "error_type": None if success else (
                "unexpected_output"
                if not exact_output
                else "retry_or_truncation_observed"
            ),
            "last_status": 200,
            "attempts": int(result.attempts),
            "elapsed_seconds": round(elapsed, 6),
            "neutral_user_utf8_bytes": PROBE_INPUT_UTF8_BYTES,
            "request_input_utf8_bytes": int(result.input_utf8_bytes),
            "request_body_bytes": int(result.request_body_bytes),
            "max_output_tokens": int(result.max_output_tokens),
            "output_truncated": bool(result.output_truncated),
            "output_text_or_response_id_persisted": False,
        }
    except Exception as exc:
        elapsed = max(0.0, now() - started)
        error_type, last_status, attempts = _safe_failure(exc)
        return {
            "success": False,
            "error_type": error_type,
            "last_status": last_status,
            "attempts": attempts,
            "elapsed_seconds": round(elapsed, 6),
            "neutral_user_utf8_bytes": PROBE_INPUT_UTF8_BYTES,
            "request_input_utf8_bytes": 0,
            "request_body_bytes": 0,
            "max_output_tokens": max_output_tokens,
            "output_truncated": False,
            "output_text_or_response_id_persisted": False,
        }


def run_capacity_ladder(
    client: ResponsesClient,
    *,
    settings: ProbeSettings = ProbeSettings(),
    now: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    """Run levels in order and stop at the first unsafe concurrency."""

    settings.validate()
    levels: list[dict[str, Any]] = []
    baseline_latencies: list[float] | None = None
    selected = 0
    sequence = 0
    for concurrency in settings.levels:
        requests: list[dict[str, Any]] = []
        waves: list[dict[str, Any]] = []
        for wave in range(1, settings.waves_per_level + 1):
            wave_started = now()
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=concurrency,
                thread_name_prefix=f"v24194-capacity-{concurrency}",
            ) as executor:
                futures: dict[concurrent.futures.Future[dict[str, Any]], int] = {}
                for slot in range(1, concurrency + 1):
                    sequence += 1
                    future = executor.submit(
                        _request,
                        client,
                        sequence,
                        now=now,
                        max_output_tokens=settings.max_output_tokens,
                    )
                    futures[future] = slot
                wave_rows: list[dict[str, Any]] = []
                for future in concurrent.futures.as_completed(futures):
                    row = future.result()
                    row.update({"wave": wave, "slot": futures[future]})
                    wave_rows.append(row)
            wave_rows.sort(key=lambda row: int(row["slot"]))
            requests.extend(wave_rows)
            waves.append(
                {
                    "wave": wave,
                    "request_count": concurrency,
                    "all_success": all(bool(row["success"]) for row in wave_rows),
                    "elapsed_seconds": round(max(0.0, now() - wave_started), 6),
                }
            )

        latencies = [float(row["elapsed_seconds"]) for row in requests]
        median_latency = statistics.median(latencies)
        p95_latency = _percentile(latencies, 0.95)
        if baseline_latencies is None:
            baseline_latencies = list(latencies)
        baseline_median = statistics.median(baseline_latencies)
        baseline_p95 = _percentile(baseline_latencies, 0.95)
        median_ceiling = max(
            1.0, baseline_median * settings.baseline_median_multiplier
        )
        p95_ceiling = min(
            settings.absolute_latency_ceiling_seconds,
            max(1.0, baseline_p95 * settings.baseline_p95_multiplier),
        )
        all_success = all(bool(row["success"]) for row in requests)
        latency_safe = bool(
            median_latency <= median_ceiling and p95_latency <= p95_ceiling
        )
        passed = bool(all_success and latency_safe)
        levels.append(
            {
                "concurrency": concurrency,
                "waves": waves,
                "requests": requests,
                "all_requests_first_attempt_exact_success": all_success,
                "median_latency_seconds": round(median_latency, 6),
                "p95_latency_seconds": round(p95_latency, 6),
                "median_latency_ceiling_seconds": round(median_ceiling, 6),
                "p95_latency_ceiling_seconds": round(p95_ceiling, 6),
                "latency_safe": latency_safe,
                "passed": passed,
            }
        )
        if not passed:
            break
        selected = concurrency

    selected_per_shard_workers = (
        min(settings.per_shard_model_workers, selected) if selected > 0 else 0
    )
    max_parallel_shards = (
        min(
            settings.maximum_parallel_shards,
            selected // selected_per_shard_workers,
        )
        if selected > 0
        else 0
    )
    if selected > 0:
        max_parallel_shards = max(1, max_parallel_shards)
    return {
        "artifact_version": 1,
        "role": "v24194_neutral_gpt56_capacity_ladder_measurement",
        "settings": settings.as_dict(),
        "settings_sha256": payload_sha256(settings.as_dict()),
        "levels": levels,
        "selected_model_request_concurrency": selected,
        "selected_per_shard_model_workers": selected_per_shard_workers,
        "selected_parallel_full220_shards": max_parallel_shards,
        "worst_case_model_request_concurrency": (
            max_parallel_shards * selected_per_shard_workers
        ),
        "status": (
            "capacity_recommendation_available"
            if selected > 0
            else "capacity_no_go_serial_probe_failed"
        ),
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
        "network_model_api_called_with_neutral_payload_only": True,
        "search_fetch_or_evaluator_api_called": False,
        "credential_value_persisted_hashed_or_emitted": False,
        "response_text_or_response_id_persisted": False,
        "full220_launch_allowed": False,
        "benchmark_or_sota_claim": False,
    }


def settings_from_dict(value: dict[str, Any]) -> ProbeSettings:
    expected_hash = hashlib.sha256(PROBE_EXPECTED_OUTPUT.encode()).hexdigest()
    levels = value.get("levels")
    integer_fields = (
        "waves_per_level",
        "max_output_tokens",
        "maximum_parallel_shards",
        "per_shard_model_workers",
    )
    numeric_fields = (
        "absolute_latency_ceiling_seconds",
        "baseline_p95_multiplier",
        "baseline_median_multiplier",
    )
    if (
        value.get("input_utf8_bytes") != PROBE_INPUT_UTF8_BYTES
        or value.get("payload_profile") != PROBE_PROFILE
        or value.get("expected_output_sha256") != expected_hash
        or not isinstance(levels, list)
        or not levels
        or any(isinstance(item, bool) or not isinstance(item, int) for item in levels)
        or any(
            isinstance(value.get(field), bool)
            or not isinstance(value.get(field), int)
            for field in integer_fields
        )
        or any(
            isinstance(value.get(field), bool)
            or not isinstance(value.get(field), (int, float))
            or not math.isfinite(float(value[field]))
            for field in numeric_fields
        )
    ):
        raise RuntimeError("V2.41.94 probe identity drifted")
    try:
        settings = ProbeSettings(
            levels=tuple(levels),
            waves_per_level=value["waves_per_level"],
            max_output_tokens=value["max_output_tokens"],
            absolute_latency_ceiling_seconds=float(
                value["absolute_latency_ceiling_seconds"]
            ),
            baseline_p95_multiplier=float(value["baseline_p95_multiplier"]),
            baseline_median_multiplier=float(
                value["baseline_median_multiplier"]
            ),
            maximum_parallel_shards=value["maximum_parallel_shards"],
            per_shard_model_workers=value["per_shard_model_workers"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("V2.41.94 probe settings are malformed") from exc
    settings.validate()
    if settings.as_dict() != value:
        raise RuntimeError("V2.41.94 probe settings are noncanonical")
    return settings


def _finite_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _same_number(left: object, right: float) -> bool:
    number = _finite_number(left)
    return bool(
        number is not None
        and math.isfinite(right)
        and abs(number - round(right, 6)) <= 1e-6
    )


def validate_capacity_report(
    report: dict[str, Any],
    *,
    expected_settings: ProbeSettings | None = None,
) -> dict[str, int]:
    """Recompute the recommendation from request-level safe metadata."""

    if (
        report.get("artifact_version") != 1
        or report.get("role")
        != "v24194_neutral_gpt56_capacity_ladder_measurement"
        or not CAPACITY_REPORT_CORE_FIELDS.issubset(report)
        or not set(report).issubset(
            CAPACITY_REPORT_CORE_FIELDS | CAPACITY_REPORT_EXECUTION_FIELDS
        )
    ):
        raise RuntimeError("V2.41.94 report identity is invalid")
    raw_settings = report.get("settings")
    if not isinstance(raw_settings, dict):
        raise RuntimeError("V2.41.94 report lacks settings")
    settings = settings_from_dict(raw_settings)
    if expected_settings is not None and settings != expected_settings:
        raise RuntimeError("V2.41.94 report settings differ from protocol")
    if report.get("settings_sha256") != payload_sha256(raw_settings):
        raise RuntimeError("V2.41.94 settings seal is invalid")
    levels = report.get("levels")
    if not isinstance(levels, list) or not 1 <= len(levels) <= len(settings.levels):
        raise RuntimeError("V2.41.94 report level count is invalid")
    selected = 0
    baseline_latencies: list[float] | None = None
    failed = False
    for index, level in enumerate(levels):
        concurrency = settings.levels[index]
        if (
            not isinstance(level, dict)
            or set(level) != CAPACITY_LEVEL_FIELDS
            or level.get("concurrency") != concurrency
        ):
            raise RuntimeError("V2.41.94 report level order drifted")
        waves = level.get("waves")
        requests = level.get("requests")
        if (
            not isinstance(waves, list)
            or len(waves) != settings.waves_per_level
            or not isinstance(requests, list)
            or len(requests) != concurrency * settings.waves_per_level
        ):
            raise RuntimeError("V2.41.94 report wave/request count is invalid")
        observed_pairs: set[tuple[int, int]] = set()
        for row in requests:
            if not isinstance(row, dict) or set(row) != CAPACITY_REQUEST_FIELDS:
                raise RuntimeError("V2.41.94 request row is invalid")
            wave = row.get("wave")
            slot = row.get("slot")
            pair = (wave, slot)
            elapsed = _finite_number(row.get("elapsed_seconds"))
            attempts = row.get("attempts")
            last_status = row.get("last_status")
            request_input = row.get("request_input_utf8_bytes")
            request_body = row.get("request_body_bytes")
            expected_request_input = PROBE_INPUT_UTF8_BYTES + len(
                PROBE_SYSTEM.encode("utf-8")
            )
            if (
                isinstance(wave, bool)
                or not isinstance(wave, int)
                or not 1 <= wave <= settings.waves_per_level
                or isinstance(slot, bool)
                or not isinstance(slot, int)
                or not 1 <= slot <= concurrency
                or pair in observed_pairs
                or row.get("neutral_user_utf8_bytes") != PROBE_INPUT_UTF8_BYTES
                or row.get("max_output_tokens") != settings.max_output_tokens
                or row.get("output_text_or_response_id_persisted") is not False
                or not isinstance(row.get("output_truncated"), bool)
                or not isinstance(attempts, int)
                or isinstance(attempts, bool)
                or attempts < 0
                or elapsed is None
                or elapsed < 0
                or isinstance(request_input, bool)
                or not isinstance(request_input, int)
                or request_input < 0
                or isinstance(request_body, bool)
                or not isinstance(request_body, int)
                or request_body < 0
                or (
                    last_status is not None
                    and (
                        isinstance(last_status, bool)
                        or not isinstance(last_status, int)
                        or not 100 <= last_status <= 599
                    )
                )
                or request_input not in {0, expected_request_input}
                or (request_input == 0 and request_body != 0)
                or (request_input == expected_request_input and request_body < request_input)
            ):
                raise RuntimeError("V2.41.94 request metadata is invalid")
            observed_pairs.add(pair)
            error_type = row.get("error_type")
            exact_success = bool(
                error_type is None
                and row.get("last_status") == 200
                and row.get("attempts") == 1
                and row.get("output_truncated") is False
                and request_input == expected_request_input
                and request_body >= request_input
            )
            if (
                row.get("success") is not exact_success
                or (exact_success and error_type is not None)
                or (
                    not exact_success
                    and (
                        not isinstance(error_type, str)
                        or not error_type
                        or len(error_type) > 80
                        or not error_type.isascii()
                        or not error_type.replace("_", "").isalnum()
                    )
                )
            ):
                raise RuntimeError("V2.41.94 request success bit is not reproducible")
        for wave_number, wave in enumerate(waves, start=1):
            subset = [row for row in requests if row["wave"] == wave_number]
            wave_elapsed = (
                _finite_number(wave.get("elapsed_seconds"))
                if isinstance(wave, dict)
                else None
            )
            if (
                not isinstance(wave, dict)
                or set(wave) != CAPACITY_WAVE_FIELDS
                or wave.get("wave") != wave_number
                or wave.get("request_count") != concurrency
                or wave.get("all_success")
                is not all(bool(row["success"]) for row in subset)
                or wave_elapsed is None
                or wave_elapsed < 0
                or wave_elapsed + 1e-6
                < max(float(row["elapsed_seconds"]) for row in subset)
            ):
                raise RuntimeError("V2.41.94 wave summary is invalid")
        latencies = [float(row["elapsed_seconds"]) for row in requests]
        if baseline_latencies is None:
            baseline_latencies = list(latencies)
        median_latency = statistics.median(latencies)
        p95_latency = _percentile(latencies, 0.95)
        baseline_median = statistics.median(baseline_latencies)
        baseline_p95 = _percentile(baseline_latencies, 0.95)
        median_ceiling = max(
            1.0, baseline_median * settings.baseline_median_multiplier
        )
        p95_ceiling = min(
            settings.absolute_latency_ceiling_seconds,
            max(1.0, baseline_p95 * settings.baseline_p95_multiplier),
        )
        all_success = all(bool(row["success"]) for row in requests)
        latency_safe = bool(
            median_latency <= median_ceiling and p95_latency <= p95_ceiling
        )
        passed = bool(all_success and latency_safe)
        if (
            failed
            or level.get("all_requests_first_attempt_exact_success")
            is not all_success
            or not _same_number(
                level.get("median_latency_seconds"), median_latency
            )
            or not _same_number(level.get("p95_latency_seconds"), p95_latency)
            or not _same_number(
                level.get("median_latency_ceiling_seconds"), median_ceiling
            )
            or not _same_number(
                level.get("p95_latency_ceiling_seconds"), p95_ceiling
            )
            or level.get("latency_safe") is not latency_safe
            or level.get("passed") is not passed
        ):
            raise RuntimeError("V2.41.94 level decision is not reproducible")
        if passed:
            selected = concurrency
        else:
            failed = True
            if index != len(levels) - 1:
                raise RuntimeError("V2.41.94 ladder continued after an unsafe level")
    if not failed and len(levels) != len(settings.levels):
        raise RuntimeError("V2.41.94 ladder stopped before an unsafe level")
    workers = min(settings.per_shard_model_workers, selected) if selected else 0
    shards = (
        max(1, min(settings.maximum_parallel_shards, selected // workers))
        if selected
        else 0
    )
    status = (
        "capacity_recommendation_available"
        if selected > 0
        else "capacity_no_go_serial_probe_failed"
    )
    if (
        report.get("selected_model_request_concurrency") != selected
        or report.get("selected_per_shard_model_workers") != workers
        or report.get("selected_parallel_full220_shards") != shards
        or report.get("worst_case_model_request_concurrency") != shards * workers
        or report.get("status") != status
        or report.get(
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read"
        )
        is not False
        or report.get("network_model_api_called_with_neutral_payload_only") is not True
        or report.get("search_fetch_or_evaluator_api_called") is not False
        or report.get("credential_value_persisted_hashed_or_emitted") is not False
        or report.get("response_text_or_response_id_persisted") is not False
        or report.get("full220_launch_allowed") is not False
        or report.get("benchmark_or_sota_claim") is not False
    ):
        raise RuntimeError("V2.41.94 recommendation summary is not reproducible")
    return {"selected": selected, "workers": workers, "shards": shards}


def build_capacity_freeze(
    report: dict[str, Any],
    *,
    report_path: str,
    report_sha256: str,
    protocol_path: str,
    protocol_sha256: str,
) -> dict[str, Any]:
    if report.get("role") != "v24194_neutral_gpt56_capacity_ladder_measurement":
        raise RuntimeError("V2.41.94 report cannot produce a scheduling freeze")
    derived = validate_capacity_report(report)
    selected = derived["selected"]
    workers = derived["workers"]
    shards = derived["shards"]
    return {
        "artifact_version": 1,
        "role": "v24194_next_fresh_all220_capacity_freeze",
        "source_report": {"path": report_path, "sha256": report_sha256},
        "protocol": {"path": protocol_path, "sha256": protocol_sha256},
        "endpoint": "http://127.0.0.1:9878/responses",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
        "service_tier": "priority",
        "model_request_concurrency_cap": selected,
        "parallel_shard_cap": shards,
        "per_shard_candidate_model_workers_cap": workers,
        "per_shard_row_model_workers_cap": workers,
        "worst_case_model_request_concurrency": shards * workers,
        "same_all220_opaque_partition_required": True,
        "new_output_roots_required": True,
        "resume_or_selective_rerun_allowed": False,
        "forward_failure_scored_as_zero": True,
        "fixed_concurrency_for_entire_all220": True,
        "dev64_is_gate_not_primary_result": True,
        "all220_is_primary_result": True,
        "search_capacity_requires_separate_frozen_preflight": True,
        "candidate_forward_code_prompt_search_budget_or_threshold_frozen": False,
        "full220_launch_allowed": False,
        "separate_candidate_freeze_and_go_decision_required": True,
        "leaderboard_submission_or_sota_claim": False,
    }
