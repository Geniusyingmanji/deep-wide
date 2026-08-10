#!/usr/bin/env python3
"""Run the V2.50.35 shared-output single-column external forward."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24257_score_first_runtime as score  # noqa: E402
from deepwide_agent import v24259_deterministic_table_normalizer as control_normalizer  # noqa: E402
from deepwide_agent import v25032_single_column_table_normalizer as candidate_normalizer  # noqa: E402
from deepwide_agent import v25035_single_column_external_contract as contract  # noqa: E402
from deepwide_agent.clients import canonicalize_url, extract_response_text  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


_MODEL_SEMAPHORE = threading.BoundedSemaphore(contract.MODEL_CONCURRENCY)


class ModelAttemptError(RuntimeError):
    def __init__(self, message: str, *, provider_attempts: int) -> None:
        super().__init__(message)
        self.provider_attempts = provider_attempts


def _read(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.35 expected JSON object")
    return value


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
            )
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.50.35 forward requires clean pushed HEAD")


def _validate_start(protocol: Mapping[str, Any]) -> dict[str, Any]:
    value = _read(contract.EXECUTION_START)
    expected = {
        "one_fresh_external_forward": True,
        "postfreeze_evaluator": False,
        "retry_resume_skip_or_population_replacement": False,
        "new_deepwidebench_exact220": False,
        "leaderboard_or_sota": False,
    }
    if (
        value.get("role") != "v25035_single_column_external_execution_start"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or value.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or value.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or value.get("endpoint_vector_sha256")
        != protocol["population"]["endpoint_vector_sha256"]
        or value.get("protected_watchers") != contract.watcher_snapshot()
        or value.get("authorization") != expected
        or not contract.sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.50.35 execution start drifted")
    return value


def _canonical_project(value: object) -> str:
    return re.sub(r"[-_.]+", "-", str(value or "").strip()).casefold()


def _fetch_exact(index: int) -> dict[str, Any]:
    task = contract.task_vector()[index]
    project = contract.PROJECTS[index]
    url = contract.endpoint_vector()[index]
    started = time.monotonic()
    attempts = 0
    try:
        attempts = 1
        with requests.get(
            url,
            headers={
                "User-Agent": "DeepWideResearch/1.0 (+single-column-external-gate)"
            },
            timeout=(
                contract.FETCH_CONNECT_TIMEOUT_SECONDS,
                contract.FETCH_READ_TIMEOUT_SECONDS,
            ),
            allow_redirects=False,
            stream=True,
        ) as response:
            status = int(response.status_code)
            response.raise_for_status()
            if canonicalize_url(str(response.url)) != canonicalize_url(url):
                raise ValueError("V2.50.35 exact PyPI endpoint drifted")
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                size += len(chunk)
                if size > contract.MAX_RESPONSE_BYTES:
                    raise ValueError("V2.50.35 PyPI response exceeds hard cap")
                chunks.append(bytes(chunk))
            raw = b"".join(chunks)
        value = json.loads(raw.decode("utf-8"))
        info = value.get("info") if isinstance(value, Mapping) else None
        if not isinstance(info, Mapping):
            raise ValueError("V2.50.35 PyPI info object is absent")
        name = str(info.get("name") or "").strip()
        version = str(info.get("version") or "").strip()
        if (
            _canonical_project(name) != _canonical_project(project)
            or not version
            or len(version) > 200
            or any(character in version for character in "\r\n\x00|")
        ):
            raise ValueError("V2.50.35 PyPI identity/version binding failed")
        evidence = json.dumps(
            {"info": {"name": name, "version": version}},
            ensure_ascii=False,
            sort_keys=True,
        )
        return {
            "index": index,
            "opaque_id": task["opaque_id"],
            "question": task["question"],
            "column": contract.column_for_index(index),
            "unknown_marker": contract.marker_for_index(index),
            "evidence": evidence,
            "fetch_attempts": attempts,
            "fetch_successes": 1,
            "fetch_status": status,
            "response_bytes": len(raw),
            "elapsed_milliseconds": int((time.monotonic() - started) * 1000),
            "ready": True,
        }
    except Exception:
        return {
            "index": index,
            "opaque_id": task["opaque_id"],
            "fetch_attempts": attempts,
            "fetch_successes": 0,
            "fetch_status": 0,
            "response_bytes": 0,
            "elapsed_milliseconds": int((time.monotonic() - started) * 1000),
            "ready": False,
        }


def build_readiness(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ready = sum(row.get("ready") is True for row in rows)
    attempts = sum(int(row.get("fetch_attempts", 0)) for row in rows)
    successes = sum(int(row.get("fetch_successes", 0)) for row in rows)
    response_bytes = sum(int(row.get("response_bytes", 0)) for row in rows)
    checks = {
        "fixed_denominator": len(rows) == contract.TASK_COUNT,
        "unique_opaque_ids": len({row.get("opaque_id") for row in rows})
        == contract.TASK_COUNT,
        "all_pages_identity_version_ready": ready == contract.TASK_COUNT,
        "one_fetch_attempt_per_task": attempts == contract.TASK_COUNT,
        "all_fetches_successful": successes == contract.TASK_COUNT,
        "response_byte_cap_held": all(
            int(row.get("response_bytes", 0)) <= contract.MAX_RESPONSE_BYTES
            for row in rows
        ),
        "no_model_call_before_readiness": True,
    }
    passed = all(checks.values())
    value = {
        "artifact_version": 1,
        "role": "v25035_single_column_external_readiness",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "task_count": len(rows),
        "ready_tasks": ready,
        "fetch_attempts": attempts,
        "fetch_successes": successes,
        "response_bytes": response_bytes,
        "model_calls_before_readiness": 0,
        "checks": checks,
        "findings": sorted(name for name, ok in checks.items() if not ok),
        "passed": passed,
        "contains_identity_question_version_url_page_prediction_raw_model_output_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "authorization": {
            "shared_model_forward": passed,
            "postfreeze_evaluator": False,
            "new_deepwidebench_exact220": False,
            "retry_resume_or_population_replacement": False,
        },
    }
    return contract.seal(value, "readiness_payload_sha256")


def validate_readiness(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25035_single_column_external_readiness"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not contract.sealed(copied, "readiness_payload_sha256")
        or copied.get("contains_identity_question_version_url_page_prediction_raw_model_output_or_credential")
        is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_read")
        is not False
        or copied.get("model_calls_before_readiness") != 0
        or copied.get("passed") is not all((copied.get("checks") or {}).values())
    ):
        raise ValueError("V2.50.35 readiness drifted")
    return copied


def _model_output(item: Mapping[str, Any]) -> tuple[str, dict[str, int]]:
    deadline = time.monotonic() + contract.TASK_DEADLINE_SECONDS
    remaining = deadline - time.monotonic() - 5.0
    if remaining <= 0 or not _MODEL_SEMAPHORE.acquire(timeout=remaining):
        raise ModelAttemptError(
            "V2.50.35 model slot deadline exhausted", provider_attempts=0
        )
    started = time.monotonic()
    try:
        remaining = deadline - time.monotonic() - 5.0
        if remaining <= 0:
            raise ModelAttemptError(
                "V2.50.35 model request deadline exhausted", provider_attempts=0
            )
        user = score.SYNTHESIS_USER.format(
            question=str(item["question"]),
            columns=json.dumps([str(item["column"])], ensure_ascii=False),
            evidence=str(item["evidence"]),
        )
        try:
            response = requests.post(
                contract.ENDPOINT,
                headers={"Content-Type": "application/json"},
                json={
                    "model": contract.MODEL,
                    "input": [
                        {"role": "system", "content": score.SYNTHESIS_SYSTEM},
                        {"role": "user", "content": user},
                    ],
                    "reasoning": {"effort": contract.REASONING_EFFORT},
                    "service_tier": contract.SERVICE_TIER,
                    "max_output_tokens": contract.MODEL_OUTPUT_TOKENS,
                    "store": False,
                },
                timeout=(
                    min(5.0, remaining),
                    min(contract.MODEL_TIMEOUT_SECONDS, remaining),
                ),
            )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, Mapping):
                raise ValueError("V2.50.35 model response schema drifted")
            text = extract_response_text(payload)
            if not text.strip():
                raise ValueError("V2.50.35 model output is empty")
            usage = payload.get("usage")
            usage = usage if isinstance(usage, Mapping) else {}
            return text, {
                "input_tokens": int(usage.get("input_tokens", 0) or 0),
                "output_tokens": int(usage.get("output_tokens", 0) or 0),
                "total_tokens": int(usage.get("total_tokens", 0) or 0),
                "elapsed_milliseconds": int(
                    (time.monotonic() - started) * 1000
                ),
                "provider_attempts": 1,
            }
        except (
            requests.RequestException,
            ValueError,
            TypeError,
            json.JSONDecodeError,
        ) as exc:
            raise ModelAttemptError(
                "V2.50.35 model provider attempt failed", provider_attempts=1
            ) from exc
    finally:
        _MODEL_SEMAPHORE.release()


def _fallback(column: str, marker: str) -> str:
    return (
        "```markdown\n"
        f"| {column} |\n"
        "| --- |\n"
        f"| {marker} |\n"
        "```"
    )


def _normalize_arm(
    text: str,
    *,
    column: str,
    marker: str,
    arm: str,
) -> tuple[str, str, str, dict[str, Any]]:
    exact, _errors = score.extract_valid_markdown_table(text, [column])
    if exact is not None:
        return exact, "exact", "exact_table", {
            "nonempty_factual_cell_rewrite_count": 0,
            "additional_model_search_or_fetch_call_count": 0,
            "single_column_candidate_table_count": 0,
        }
    if arm == contract.CONTROL_ARM:
        normalized, diagnostics = control_normalizer.normalize_candidate_table(
            text, [column], unknown_marker=marker
        )
    elif arm == contract.CANDIDATE_ARM:
        normalized, diagnostics = candidate_normalizer.normalize_candidate_table(
            text, [column], unknown_marker=marker
        )
    else:
        raise ValueError("V2.50.35 arm drifted")
    status = "normalized" if normalized is not None else "fallback"
    mode = str(diagnostics.get("mode") or "unrecoverable")
    audit = {
        "nonempty_factual_cell_rewrite_count": int(
            diagnostics.get("nonempty_factual_cell_rewrite_count", 0)
        ),
        "additional_model_search_or_fetch_call_count": int(
            diagnostics.get("additional_model_search_or_fetch_call_count", 0)
        ),
        "single_column_candidate_table_count": int(
            diagnostics.get("single_column_candidate_table_count", 0)
        ),
    }
    return normalized or _fallback(column, marker), status, mode, audit


def _data_row_count(prediction: str) -> int:
    lines = [
        line.strip()
        for line in str(prediction).replace("\r\n", "\n").splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    return max(0, len(lines) - 2)


def _task_row(item: Mapping[str, Any]) -> dict[str, Any]:
    index = int(item["index"])
    started = time.monotonic()
    raw = ""
    usage = {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "elapsed_milliseconds": 0,
        "provider_attempts": 0,
    }
    model_success = False
    try:
        raw, usage = _model_output(item)
        model_success = True
    except ModelAttemptError as exc:
        usage["provider_attempts"] = exc.provider_attempts
    predictions: dict[str, str] = {}
    statuses: dict[str, str] = {}
    modes: dict[str, str] = {}
    audits: dict[str, dict[str, int]] = {}
    if model_success:
        for arm in contract.ARMS:
            prediction, status, mode, audit = _normalize_arm(
                raw,
                column=str(item["column"]),
                marker=str(item["unknown_marker"]),
                arm=arm,
            )
            predictions[arm] = prediction
            statuses[arm] = status
            modes[arm] = mode
            audits[arm] = audit
    else:
        for arm in contract.ARMS:
            predictions[arm] = _fallback(
                str(item["column"]), str(item["unknown_marker"])
            )
            statuses[arm] = "fallback"
            modes[arm] = "model_failure"
            audits[arm] = {
                "nonempty_factual_cell_rewrite_count": 0,
                "additional_model_search_or_fetch_call_count": 0,
                "single_column_candidate_table_count": 0,
            }
    natural_recovery = (
        model_success
        and statuses[contract.CONTROL_ARM] == "fallback"
        and statuses[contract.CANDIDATE_ARM] == "normalized"
    )
    value = {
        "artifact_version": 1,
        "role": "v25035_single_column_external_task_result",
        "protocol_id": contract.PROTOCOL_ID,
        "index": index,
        "opaque_id": str(item["opaque_id"]),
        "runtime_input_keys": [
            "opaque_id",
            "question",
            "same_forward_public_pypi_json",
        ],
        "terminal": True,
        "fetch_attempts": int(item["fetch_attempts"]),
        "fetch_successes": int(item["fetch_successes"]),
        "fetch_status": int(item["fetch_status"]),
        "response_bytes": int(item["response_bytes"]),
        "model_success": model_success,
        "model_usage": usage,
        "raw_model_output": raw,
        "raw_model_output_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode("utf-8")).hexdigest()
            for arm in contract.ARMS
        },
        "normalizer_status": statuses,
        "normalizer_mode": modes,
        "normalizer_audit": audits,
        "candidate_natural_recovery": natural_recovery,
        "candidate_prediction_changed": predictions[contract.CANDIDATE_ARM]
        != predictions[contract.CONTROL_ARM],
        "candidate_data_row_count": _data_row_count(
            predictions[contract.CANDIDATE_ARM]
        ),
        "wall_seconds": round(time.monotonic() - started, 6),
        "same_raw_model_output_for_both_arms": True,
        "one_model_call_shared_by_both_arms": True,
        "additional_model_search_or_fetch_calls_from_candidate": 0,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_or_population_replacement": False,
    }
    return contract.seal(value, "result_payload_sha256")


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    index = copied.get("index")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < contract.TASK_COUNT:
        raise ValueError("V2.50.35 task index drifted")
    task = contract.task_vector()[index]
    raw = copied.get("raw_model_output")
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    statuses = copied.get("normalizer_status")
    modes = copied.get("normalizer_mode")
    audits = copied.get("normalizer_audit")
    usage = copied.get("model_usage")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25035_single_column_external_task_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("opaque_id") != task["opaque_id"]
        or copied.get("runtime_input_keys")
        != ["opaque_id", "question", "same_forward_public_pypi_json"]
        or copied.get("terminal") is not True
        or copied.get("fetch_attempts") != 1
        or copied.get("fetch_successes") != 1
        or not isinstance(raw, str)
        or copied.get("raw_model_output_sha256")
        != hashlib.sha256(raw.encode("utf-8")).hexdigest()
        or not isinstance(predictions, Mapping)
        or set(predictions) != set(contract.ARMS)
        or not isinstance(hashes, Mapping)
        or set(hashes) != set(contract.ARMS)
        or not isinstance(statuses, Mapping)
        or set(statuses) != set(contract.ARMS)
        or not isinstance(modes, Mapping)
        or set(modes) != set(contract.ARMS)
        or not isinstance(audits, Mapping)
        or set(audits) != set(contract.ARMS)
        or not isinstance(usage, Mapping)
        or copied.get("same_raw_model_output_for_both_arms") is not True
        or copied.get("one_model_call_shared_by_both_arms") is not True
        or copied.get("additional_model_search_or_fetch_calls_from_candidate") != 0
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_read")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("retry_resume_skip_or_population_replacement") is not False
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.50.35 task row drifted")
    model_success = copied.get("model_success")
    if not isinstance(model_success, bool):
        raise ValueError("V2.50.35 model status drifted")
    for name in (
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "elapsed_milliseconds",
        "provider_attempts",
    ):
        item = usage.get(name)
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise ValueError("V2.50.35 model usage drifted")
    if (
        usage["provider_attempts"] not in {0, 1}
        or (model_success and usage["provider_attempts"] != 1)
        or model_success is not bool(raw)
    ):
        raise ValueError("V2.50.35 single model attempt drifted")
    expected_predictions: dict[str, str] = {}
    expected_statuses: dict[str, str] = {}
    expected_modes: dict[str, str] = {}
    expected_audits: dict[str, dict[str, int]] = {}
    for arm in contract.ARMS:
        if model_success:
            prediction, status, mode, audit = _normalize_arm(
                raw,
                column=contract.column_for_index(index),
                marker=contract.marker_for_index(index),
                arm=arm,
            )
        else:
            prediction = _fallback(
                contract.column_for_index(index), contract.marker_for_index(index)
            )
            status, mode = "fallback", "model_failure"
            audit = {
                "nonempty_factual_cell_rewrite_count": 0,
                "additional_model_search_or_fetch_call_count": 0,
                "single_column_candidate_table_count": 0,
            }
        expected_predictions[arm] = prediction
        expected_statuses[arm] = status
        expected_modes[arm] = mode
        expected_audits[arm] = audit
        if hashes[arm] != hashlib.sha256(str(predictions[arm]).encode("utf-8")).hexdigest():
            raise ValueError("V2.50.35 prediction hash drifted")
    natural = (
        model_success
        and expected_statuses[contract.CONTROL_ARM] == "fallback"
        and expected_statuses[contract.CANDIDATE_ARM] == "normalized"
    )
    if (
        dict(predictions) != expected_predictions
        or dict(statuses) != expected_statuses
        or dict(modes) != expected_modes
        or dict(audits) != expected_audits
        or copied.get("candidate_natural_recovery") is not natural
        or copied.get("candidate_prediction_changed")
        is not (
            expected_predictions[contract.CANDIDATE_ARM]
            != expected_predictions[contract.CONTROL_ARM]
        )
        or copied.get("candidate_data_row_count")
        != _data_row_count(expected_predictions[contract.CANDIDATE_ARM])
    ):
        raise ValueError("V2.50.35 normalization projection drifted")
    return copied


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if (
        len(checked) != contract.TASK_COUNT
        or {row["index"] for row in checked} != set(range(contract.TASK_COUNT))
        or len({row["opaque_id"] for row in checked}) != contract.TASK_COUNT
    ):
        raise ValueError("V2.50.35 aggregate denominator drifted")
    totals: dict[str, Any] = {
        "terminal_tasks": len(checked),
        "fetch_attempts": sum(row["fetch_attempts"] for row in checked),
        "fetch_successes": sum(row["fetch_successes"] for row in checked),
        "model_successes": sum(row["model_success"] for row in checked),
        "model_provider_attempts": sum(
            row["model_usage"]["provider_attempts"] for row in checked
        ),
        "system_total_tokens": sum(
            row["model_usage"]["total_tokens"] for row in checked
        ),
        "candidate_natural_recoveries": sum(
            row["candidate_natural_recovery"] for row in checked
        ),
        "candidate_prediction_changed_tasks": sum(
            row["candidate_prediction_changed"] for row in checked
        ),
        "candidate_extra_row_admission_tasks": sum(
            row["normalizer_status"][contract.CANDIDATE_ARM] != "fallback"
            and row["candidate_data_row_count"] != 1
            for row in checked
        ),
        "nonempty_factual_cell_rewrite_count": sum(
            row["normalizer_audit"][contract.CANDIDATE_ARM][
                "nonempty_factual_cell_rewrite_count"
            ]
            for row in checked
        ),
        "additional_model_search_or_fetch_calls": sum(
            row["additional_model_search_or_fetch_calls_from_candidate"]
            for row in checked
        ),
        "language_groups": {
            "english": {
                "tasks": contract.ENGLISH_TASK_COUNT,
                "candidate_natural_recoveries": sum(
                    row["candidate_natural_recovery"]
                    for row in checked[: contract.ENGLISH_TASK_COUNT]
                ),
            },
            "chinese": {
                "tasks": contract.CHINESE_TASK_COUNT,
                "candidate_natural_recoveries": sum(
                    row["candidate_natural_recovery"]
                    for row in checked[contract.ENGLISH_TASK_COUNT :]
                ),
            },
        },
    }
    for arm in contract.ARMS:
        totals[f"{arm}_exact_tables"] = sum(
            row["normalizer_status"][arm] == "exact" for row in checked
        )
        totals[f"{arm}_normalized_tables"] = sum(
            row["normalizer_status"][arm] == "normalized" for row in checked
        )
        totals[f"{arm}_fallback_tables"] = sum(
            row["normalizer_status"][arm] == "fallback" for row in checked
        )
    return totals


def mechanism_decision(totals: Mapping[str, Any]) -> dict[str, Any]:
    checks = {
        "fixed_denominator": totals.get("terminal_tasks") == contract.TASK_COUNT,
        "all_fetches_successful": totals.get("fetch_attempts")
        == totals.get("fetch_successes")
        == contract.TASK_COUNT,
        "all_single_model_calls_successful": totals.get("model_successes")
        == totals.get("model_provider_attempts")
        == contract.TASK_COUNT,
        "minimum_natural_recovery": totals.get("candidate_natural_recoveries", 0)
        >= contract.MINIMUM_NATURAL_RECOVERIES,
        "candidate_fallback_strictly_less": totals.get(
            f"{contract.CANDIDATE_ARM}_fallback_tables"
        )
        < totals.get(f"{contract.CONTROL_ARM}_fallback_tables"),
        "zero_extra_row_admission": totals.get(
            "candidate_extra_row_admission_tasks"
        )
        == 0,
        "zero_nonempty_factual_cell_rewrite": totals.get(
            "nonempty_factual_cell_rewrite_count"
        )
        == 0,
        "zero_additional_effect": totals.get(
            "additional_model_search_or_fetch_calls"
        )
        == 0,
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "mechanism_gate_passed": passed,
        "postfreeze_external_evaluator_protocol": passed,
        "new_deepwidebench_exact220": False,
        "leaderboard_or_sota": False,
    }


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(
        ROOT, _read(contract.PROTOCOL), tracked=True
    )
    start = _validate_start(protocol)
    future = (
        contract.READINESS,
        contract.OUTPUT_ROOT,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.35 effect surface is not pristine")
    with acquire_deepwide_api_lease(
        ROOT,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        if contract.watcher_snapshot() != protocol["protected_watchers"]:
            raise RuntimeError("V2.50.35 protected watcher drifted")
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            prepared = list(pool.map(_fetch_exact, range(contract.TASK_COUNT)))
        prepared.sort(key=lambda row: int(row["index"]))
        readiness = validate_readiness(build_readiness(prepared))
        _publish(ROOT / contract.READINESS, readiness)
        if not readiness["passed"]:
            return readiness
        (ROOT / contract.OUTPUT_ROOT).mkdir(
            mode=0o700, parents=True, exist_ok=False
        )
        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            rows = list(pool.map(_task_row, prepared))
        wall = time.monotonic() - started
    checked = sorted(
        (validate_task_row(row) for row in rows), key=lambda row: row["index"]
    )
    _publish_jsonl(ROOT / contract.TASK_ROWS, checked)
    totals = aggregate(checked)
    mechanism = mechanism_decision(totals)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25035_single_column_external_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "terminal_arm_predictions": contract.TASK_COUNT * len(contract.ARMS),
            "shared_raw_model_outputs": contract.TASK_COUNT,
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_hash_vector_sha256": contract.payload_sha256(
                [
                    [row["prediction_sha256"][arm] for arm in contract.ARMS]
                    for row in checked
                ]
            ),
            "raw_model_output_hash_vector_sha256": contract.payload_sha256(
                [row["raw_model_output_sha256"] for row in checked]
            ),
            "readiness_sha256": contract.sha256(ROOT / contract.READINESS),
            "all_predictions_terminal_before_evaluator_or_gold_refetch": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "freeze_payload_sha256",
    )
    _publish(ROOT / contract.PREDICTION_FREEZE, freeze)
    result = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25035_single_column_external_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "wall_seconds": round(wall, 6),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            "readiness_sha256": contract.sha256(ROOT / contract.READINESS),
            "execution_start_sha256": contract.sha256(
                ROOT / contract.EXECUTION_START
            ),
            "execution_start_payload_sha256": start[
                "execution_start_payload_sha256"
            ],
            "aggregate": totals,
            "mechanism_decision": mechanism,
            "all_predictions_terminal_before_evaluator_or_gold_refetch": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "authorization": {
                "postfreeze_external_evaluator_protocol": False,
                "retry_resume_or_selective_rerun": False,
                "new_deepwidebench_exact220": False,
                "leaderboard_or_sota": False,
            },
        },
        "result_payload_sha256",
    )
    _publish(ROOT / contract.FORWARD_RESULT, result)
    return result


def main() -> None:
    value = run_forward()
    print(
        json.dumps(
            {
                "role": value["role"],
                "path": str(
                    contract.FORWARD_RESULT
                    if value.get("role")
                    == "v25035_single_column_external_forward_result"
                    else contract.READINESS
                ),
                "passed": value.get("passed"),
                "aggregate": value.get("aggregate"),
                "mechanism_decision": value.get("mechanism_decision"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
