"""Provider-wide paced successor for the frozen Tavily URL-lead transport.

V2.48.51 showed that a provider-wide 429 was treated as if it were a
credential-local failure: each failed logical query immediately rotated across
all twelve keys, yielding exactly twelve 429 responses per failed query.  This
append-only successor keeps the validated header-only URL-lead projection and
deterministic page fetch, but adds a cross-process provider gate:

* request starts are globally paced across all task processes;
* a 429 opens a shared cooldown, honoring a bounded numeric Retry-After;
* a logical query receives at most two non-key-local provider attempts;
* 401/403/432 remain credential-local and disable only that key.

The gate stores only counters and monotonic timing state.  It has no benchmark,
question, query, URL, page, prediction, evaluator, score, or credential field.
"""

from __future__ import annotations

import fcntl
import json
import math
import os
import stat
import threading
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Callable

import requests

from . import v24796_deadline_tavily_search as parent
from .clients import SearchRequestError, canonicalize_url
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v24852_provider_paced_rate_aware_tavily_url_leads_v1"
POOL_ID = "v24852_global_tavily_provider_rate_gate_v1"
ROLE = "v24852_rate_aware_tavily_search_receipt"
GATE_ROLE = "v24852_tavily_provider_rate_gate"
GATE_BASENAME = "provider_rate_gate.lock"
DEFAULT_MINIMUM_START_INTERVAL_SECONDS = 0.75
DEFAULT_PROVIDER_COOLDOWN_SECONDS = 30.0
DEFAULT_MAXIMUM_COOLDOWN_SECONDS = 60.0
DEFAULT_PROVIDER_ATTEMPT_CAP = 2
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "pool_id",
        "provider_non_key_local_attempt_cap_per_logical_query",
        "minimum_start_interval_seconds",
        "default_provider_cooldown_seconds",
        "maximum_provider_cooldown_seconds",
        "provider_start_reservations",
        "provider_gate_timeouts",
        "provider_pacing_wait_events",
        "provider_cooldown_wait_events",
        "provider_cooldown_activations",
        "retry_after_values_honored",
        "total_provider_gate_wait_seconds",
        "max_provider_gate_wait_seconds",
        "provider_429_responses",
        "provider_non429_retryable_responses",
        "provider_transport_retry_events",
        "provider_wide_429_rotates_all_keys_immediately",
        "credential_local_statuses_remain_key_local",
        "provider_answer_snippet_raw_content_or_score_forwarded",
        "deterministic_public_page_fetch_is_only_active_evidence",
        "credential_value_persisted_hashed_emitted_or_in_error",
        "question_query_url_page_prediction_answer_or_opaque_id_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
)
_PROCESS_PROVIDER_GATE_LOCK = threading.Lock()


def _ordinary_directory(path: Path, output_root: Path) -> Path:
    root = output_root.resolve()
    target = path.resolve(strict=False)
    if (
        output_root.is_symlink()
        or not output_root.is_dir()
        or path.is_symlink()
        or not path.is_dir()
        or not target.is_relative_to(root)
    ):
        raise ValueError("V2.48.52 provider gate directory escaped output root")
    return target


def _gate_path(directory: Path) -> Path:
    return directory / GATE_BASENAME


def _initial_gate() -> dict[str, Any]:
    return {
        "artifact_version": 1,
        "role": GATE_ROLE,
        "generation": 0,
        "next_start_monotonic": 0.0,
        "cooldown_until_monotonic": 0.0,
        "last_status": 0,
    }


def prepare_rate_aware_key_slots(path: Path, key_count: int) -> None:
    """Create the inherited key slots plus one content-free provider gate."""

    parent.prepare_key_slots(path, key_count)
    gate = _gate_path(path)
    descriptor = os.open(
        gate,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | os.O_CLOEXEC,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(_initial_gate(), handle, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _read_gate(handle: Any) -> dict[str, Any]:
    handle.seek(0)
    try:
        value = json.load(handle)
    except (json.JSONDecodeError, OSError):
        raise RuntimeError("V2.48.52 provider gate state is invalid") from None
    expected = {
        "artifact_version",
        "role",
        "generation",
        "next_start_monotonic",
        "cooldown_until_monotonic",
        "last_status",
    }
    if (
        not isinstance(value, dict)
        or set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != GATE_ROLE
        or isinstance(value.get("generation"), bool)
        or not isinstance(value.get("generation"), int)
        or value["generation"] < 0
        or isinstance(value.get("last_status"), bool)
        or not isinstance(value.get("last_status"), int)
        or value["last_status"] < 0
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in (
                "next_start_monotonic",
                "cooldown_until_monotonic",
            )
        )
    ):
        raise RuntimeError("V2.48.52 provider gate identity drifted")
    return value


def _write_gate(handle: Any, value: Mapping[str, Any]) -> None:
    checked = dict(value)
    handle.seek(0)
    handle.truncate()
    json.dump(checked, handle, sort_keys=True)
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())


def _numeric_retry_after(response: Any) -> float | None:
    headers = getattr(response, "headers", None)
    raw = headers.get("Retry-After") if isinstance(headers, Mapping) else None
    if raw is None:
        return None
    try:
        value = float(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    return value


class RateAwareDeadlineTavilyThinCompatibilityClient(
    parent.DeadlineTavilyThinCompatibilityClient
):
    """The frozen URL-lead client with a provider-wide rate circuit."""

    def __init__(
        self,
        *args: Any,
        provider_attempt_cap: int = DEFAULT_PROVIDER_ATTEMPT_CAP,
        minimum_start_interval_seconds: float = (
            DEFAULT_MINIMUM_START_INTERVAL_SECONDS
        ),
        default_provider_cooldown_seconds: float = (
            DEFAULT_PROVIDER_COOLDOWN_SECONDS
        ),
        maximum_provider_cooldown_seconds: float = (
            DEFAULT_MAXIMUM_COOLDOWN_SECONDS
        ),
        provider_gate_monotonic: Callable[[], float] = time.monotonic,
        provider_gate_sleeper: Callable[[float], None] = time.sleep,
        provider_gate_poll_seconds: float = 0.025,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        numerics = (
            minimum_start_interval_seconds,
            default_provider_cooldown_seconds,
            maximum_provider_cooldown_seconds,
            provider_gate_poll_seconds,
        )
        if (
            isinstance(provider_attempt_cap, bool)
            or not isinstance(provider_attempt_cap, int)
            or not 1 <= provider_attempt_cap <= 4
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) <= 0
                for value in numerics
            )
            or float(minimum_start_interval_seconds) > 10
            or float(default_provider_cooldown_seconds) > 300
            or float(maximum_provider_cooldown_seconds) > 600
            or float(default_provider_cooldown_seconds)
            > float(maximum_provider_cooldown_seconds)
            or float(provider_gate_poll_seconds) > 1
        ):
            raise ValueError("V2.48.52 provider gate configuration is invalid")
        self.provider_attempt_cap = provider_attempt_cap
        self.minimum_start_interval_seconds = float(
            minimum_start_interval_seconds
        )
        self.default_provider_cooldown_seconds = float(
            default_provider_cooldown_seconds
        )
        self.maximum_provider_cooldown_seconds = float(
            maximum_provider_cooldown_seconds
        )
        self.provider_gate_monotonic = provider_gate_monotonic
        self.provider_gate_sleeper = provider_gate_sleeper
        self.provider_gate_poll_seconds = float(provider_gate_poll_seconds)
        self._provider_gate_path = _gate_path(self.key_slot_directory)
        if (
            self._provider_gate_path.is_symlink()
            or not self._provider_gate_path.is_file()
        ):
            raise ValueError("V2.48.52 provider rate gate is absent")
        self._rate_lock = threading.Lock()
        self._rate_stats: dict[str, int | float] = {
            "provider_start_reservations": 0,
            "provider_gate_timeouts": 0,
            "provider_pacing_wait_events": 0,
            "provider_cooldown_wait_events": 0,
            "provider_cooldown_activations": 0,
            "retry_after_values_honored": 0,
            "total_provider_gate_wait_seconds": 0.0,
            "max_provider_gate_wait_seconds": 0.0,
            "provider_429_responses": 0,
            "provider_non429_retryable_responses": 0,
            "provider_transport_retry_events": 0,
        }

    def _rate_stat(self, name: str, amount: int | float = 1) -> None:
        with self._rate_lock:
            self._rate_stats[name] += amount

    def _open_gate(self) -> Any:
        descriptor = os.open(
            self._provider_gate_path,
            os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
        )
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            os.close(descriptor)
            raise RuntimeError("V2.48.52 provider rate gate is not regular")
        return os.fdopen(descriptor, "r+", encoding="utf-8")

    def _provider_timeout(self, waited: float) -> SearchRequestError:
        with self._rate_lock:
            self._rate_stats["provider_gate_timeouts"] += 1
            self._rate_stats["total_provider_gate_wait_seconds"] += waited
            self._rate_stats["max_provider_gate_wait_seconds"] = max(
                float(self._rate_stats["max_provider_gate_wait_seconds"]),
                waited,
            )
        return SearchRequestError(
            "V2.48.52 provider rate gate exhausted the task deadline"
        )

    def _reserve_provider_start(self) -> None:
        started = float(self.provider_gate_monotonic())
        pacing_counted = False
        cooldown_counted = False
        while True:
            reserved = False
            waited = 0.0
            wait_kind: str | None = None
            with _PROCESS_PROVIDER_GATE_LOCK:
                handle = self._open_gate()
                locked = False
                try:
                    try:
                        fcntl.flock(
                            handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                        )
                    except BlockingIOError:
                        wait_kind = "lock"
                    else:
                        locked = True
                        state = _read_gate(handle)
                        now = float(self.provider_gate_monotonic())
                        ready = max(
                            float(state["next_start_monotonic"]),
                            float(state["cooldown_until_monotonic"]),
                        )
                        if now >= ready:
                            state["generation"] = int(state["generation"]) + 1
                            state["next_start_monotonic"] = (
                                now + self.minimum_start_interval_seconds
                            )
                            if now >= float(
                                state["cooldown_until_monotonic"]
                            ):
                                state["cooldown_until_monotonic"] = 0.0
                            _write_gate(handle, state)
                            waited = max(0.0, now - started)
                            reserved = True
                        elif ready == float(
                            state["cooldown_until_monotonic"]
                        ):
                            wait_kind = "cooldown"
                        else:
                            wait_kind = "pacing"
                finally:
                    if locked:
                        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    handle.close()
            if reserved:
                with self._rate_lock:
                    self._rate_stats["provider_start_reservations"] += 1
                    self._rate_stats[
                        "total_provider_gate_wait_seconds"
                    ] += waited
                    self._rate_stats["max_provider_gate_wait_seconds"] = max(
                        float(
                            self._rate_stats["max_provider_gate_wait_seconds"]
                        ),
                        waited,
                    )
                return
            if wait_kind == "cooldown" and not cooldown_counted:
                self._rate_stat("provider_cooldown_wait_events")
                cooldown_counted = True
            elif wait_kind == "pacing" and not pacing_counted:
                self._rate_stat("provider_pacing_wait_events")
                pacing_counted = True
            now = float(self.provider_gate_monotonic())
            remaining = self.remaining_effect_seconds()
            waited = max(0.0, now - started)
            if remaining < self.minimum_attempt_seconds:
                raise self._provider_timeout(waited)
            self.provider_gate_sleeper(
                min(self.provider_gate_poll_seconds, remaining)
            )

    def _schedule_provider_cooldown(
        self, response: Any, *, status: int
    ) -> None:
        supplied = _numeric_retry_after(response)
        requested = max(
            self.default_provider_cooldown_seconds,
            supplied if supplied is not None else 0.0,
        )
        delay = min(requested, self.maximum_provider_cooldown_seconds)
        with _PROCESS_PROVIDER_GATE_LOCK:
            handle = self._open_gate()
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                state = _read_gate(handle)
                now = float(self.provider_gate_monotonic())
                until = now + delay
                previous = float(state["cooldown_until_monotonic"])
                state["generation"] = int(state["generation"]) + 1
                state["cooldown_until_monotonic"] = max(previous, until)
                state["next_start_monotonic"] = max(
                    float(state["next_start_monotonic"]),
                    state["cooldown_until_monotonic"],
                )
                state["last_status"] = int(status)
                _write_gate(handle, state)
                if until > previous:
                    self._rate_stat("provider_cooldown_activations")
                if supplied is not None:
                    self._rate_stat("retry_after_values_honored")
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()

    def _direct_search(
        self, query: str, *, max_results: int, search_depth: str
    ) -> dict[str, Any]:
        normalized = " ".join(str(query).split()).strip()
        if (
            not normalized
            or len(normalized) > 32_768
            or isinstance(max_results, bool)
            or not isinstance(max_results, int)
            or not 1 <= max_results <= 20
            or search_depth not in {"basic", "advanced", "fast", "ultra-fast"}
            or any(key in normalized for key in self._credentials)
        ):
            raise ValueError("V2.48.52 direct query shape is invalid")
        body = json.dumps(
            {
                "query": normalized,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_answer": False,
                "include_raw_content": False,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        non_key_local_attempts = 0
        while non_key_local_attempts < self.provider_attempt_cap:
            try:
                handle, index, key = self._acquire_key_slot()
            except SearchRequestError:
                break
            retry = False
            try:
                try:
                    self._reserve_provider_start()
                except SearchRequestError:
                    break
                remaining = self.remaining_effect_seconds()
                if remaining < self.minimum_attempt_seconds:
                    raise self._provider_timeout(0.0)
                self._increment("hosted_search_attempts")
                self._stat("provider_attempts")
                try:
                    response = self._post()(
                        parent.ENDPOINT,
                        headers={
                            "Authorization": "Bearer " + key,
                            "Content-Type": "application/json",
                        },
                        data=body,
                        timeout=min(self.direct_timeout_seconds, remaining),
                        allow_redirects=False,
                        verify=True,
                    )
                    self._increment("calls")
                    status = int(response.status_code)
                    self._stat(parent._status_bucket(status))
                    if status in parent.KEY_LOCAL_STATUSES:
                        parent._write_disabled(handle, index=index, status=status)
                        self._stat("key_local_disables")
                        retry = True
                        continue
                    non_key_local_attempts += 1
                    if status == 429:
                        self._stat("retryable_responses")
                        self._rate_stat("provider_429_responses")
                        self._schedule_provider_cooldown(response, status=status)
                        retry = True
                        continue
                    if status in {408, 409} or status >= 500:
                        self._stat("retryable_responses")
                        self._rate_stat(
                            "provider_non429_retryable_responses"
                        )
                        retry = True
                        continue
                    if 300 <= status < 400 or status >= 400:
                        break
                    payload = response.json()
                except (
                    requests.ConnectionError,
                    requests.Timeout,
                    json.JSONDecodeError,
                ):
                    non_key_local_attempts += 1
                    self._increment("transport_failures")
                    self._stat("transport_failures")
                    self._rate_stat("provider_transport_retry_events")
                    retry = True
                    continue
                if not isinstance(payload, Mapping):
                    self._stat("invalid_payloads")
                    retry = True
                    continue
                serialized = json.dumps(payload, ensure_ascii=False)
                if any(secret in serialized for secret in self._credentials):
                    self._stat("credential_echo_rejections")
                    break
                leads: list[dict[str, Any]] = []
                seen: set[str] = set()
                raw_results = payload.get("results") or []
                if not isinstance(raw_results, list):
                    self._stat("invalid_payloads")
                    retry = True
                    continue
                invalid = 0
                for raw in raw_results:
                    if not isinstance(raw, Mapping):
                        invalid += 1
                        continue
                    supplied_url = str(raw.get("url", "")).strip()
                    canonical = canonicalize_url(supplied_url)
                    if not canonical or canonical in seen:
                        invalid += 1
                        continue
                    seen.add(canonical)
                    leads.append(
                        {
                            "title": " ".join(
                                str(raw.get("title", "")).split()
                            )[:500],
                            "url": canonical,
                            "fetch_url": supplied_url,
                            "content": "",
                            "raw_content": "",
                            "score": None,
                            "source_type": "tavily_untrusted_url_lead",
                        }
                    )
                    if len(leads) >= max_results:
                        break
                invalid += max(0, len(raw_results) - len(leads) - invalid)
                self._stat("projected_url_leads", len(leads))
                self._stat("invalid_or_duplicate_results", invalid)
                if leads:
                    self._stat("successful_queries")
                    return {
                        "query": normalized,
                        "answer": "",
                        "results": leads,
                        "error": None,
                        "provider": "v24852-rate-aware-tavily-url-leads",
                    }
                retry = True
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()
            if not retry:
                break
        self._increment("failures")
        self._stat("failed_queries")
        return {
            "query": normalized,
            "answer": "",
            "results": [],
            "error": "rate-aware direct search request failed",
            "provider": "v24852-rate-aware-tavily-url-leads",
        }

    def rate_aware_search_receipt(self) -> dict[str, Any]:
        with self._rate_lock:
            stats = dict(self._rate_stats)
        value = {
            "artifact_version": 1,
            "role": ROLE,
            "policy_id": POLICY_ID,
            "pool_id": POOL_ID,
            "provider_non_key_local_attempt_cap_per_logical_query": (
                self.provider_attempt_cap
            ),
            "minimum_start_interval_seconds": self.minimum_start_interval_seconds,
            "default_provider_cooldown_seconds": self.default_provider_cooldown_seconds,
            "maximum_provider_cooldown_seconds": self.maximum_provider_cooldown_seconds,
            **{
                name: int(stats[name])
                for name in (
                    "provider_start_reservations",
                    "provider_gate_timeouts",
                    "provider_pacing_wait_events",
                    "provider_cooldown_wait_events",
                    "provider_cooldown_activations",
                    "retry_after_values_honored",
                    "provider_429_responses",
                    "provider_non429_retryable_responses",
                    "provider_transport_retry_events",
                )
            },
            "total_provider_gate_wait_seconds": round(
                float(stats["total_provider_gate_wait_seconds"]), 6
            ),
            "max_provider_gate_wait_seconds": round(
                float(stats["max_provider_gate_wait_seconds"]), 6
            ),
            "provider_wide_429_rotates_all_keys_immediately": False,
            "credential_local_statuses_remain_key_local": True,
            "provider_answer_snippet_raw_content_or_score_forwarded": False,
            "deterministic_public_page_fetch_is_only_active_evidence": True,
            "credential_value_persisted_hashed_emitted_or_in_error": False,
            "question_query_url_page_prediction_answer_or_opaque_id_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    integer_fields = {
        "artifact_version",
        "provider_non_key_local_attempt_cap_per_logical_query",
        "provider_start_reservations",
        "provider_gate_timeouts",
        "provider_pacing_wait_events",
        "provider_cooldown_wait_events",
        "provider_cooldown_activations",
        "retry_after_values_honored",
        "provider_429_responses",
        "provider_non429_retryable_responses",
        "provider_transport_retry_events",
    }
    numeric_fields = {
        "minimum_start_interval_seconds",
        "default_provider_cooldown_seconds",
        "maximum_provider_cooldown_seconds",
        "total_provider_gate_wait_seconds",
        "max_provider_gate_wait_seconds",
    }
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("pool_id") != POOL_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), (int, float))
            or not math.isfinite(float(copied[name]))
            or float(copied[name]) < 0
            for name in numeric_fields
        )
        or not 1
        <= copied.get(
            "provider_non_key_local_attempt_cap_per_logical_query", 0
        )
        <= 4
        or copied.get("default_provider_cooldown_seconds", 0)
        > copied.get("maximum_provider_cooldown_seconds", -1)
        or copied.get("retry_after_values_honored", 0)
        > copied.get("provider_429_responses", 0)
        or copied.get("provider_cooldown_activations", 0)
        > copied.get("provider_429_responses", 0)
        or copied.get("provider_wide_429_rotates_all_keys_immediately") is not False
        or copied.get("credential_local_statuses_remain_key_local") is not True
        or copied.get("provider_answer_snippet_raw_content_or_score_forwarded")
        is not False
        or copied.get("deterministic_public_page_fetch_is_only_active_evidence")
        is not True
        or copied.get("credential_value_persisted_hashed_emitted_or_in_error")
        is not False
        or copied.get(
            "question_query_url_page_prediction_answer_or_opaque_id_persisted"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.52 rate-aware search receipt drifted")
    return copied


def validate_search_class() -> None:
    cls = RateAwareDeadlineTavilyThinCompatibilityClient
    search_owner = next(base for base in cls.__mro__ if "_direct_search" in base.__dict__)
    if (
        search_owner is not cls
        or not issubclass(cls, parent.DeadlineTavilyThinCompatibilityClient)
    ):
        raise RuntimeError("V2.48.52 rate-aware search MRO drifted")


__all__ = [
    "DEFAULT_MAXIMUM_COOLDOWN_SECONDS",
    "DEFAULT_MINIMUM_START_INTERVAL_SECONDS",
    "DEFAULT_PROVIDER_ATTEMPT_CAP",
    "DEFAULT_PROVIDER_COOLDOWN_SECONDS",
    "POLICY_ID",
    "POOL_ID",
    "ROLE",
    "RateAwareDeadlineTavilyThinCompatibilityClient",
    "prepare_rate_aware_key_slots",
    "validate_receipt",
    "validate_search_class",
]
