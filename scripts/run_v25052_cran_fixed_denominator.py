#!/usr/bin/env python3
"""Fixed-denominator paired failure-as-zero CRAN bridge forward."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25049_page_self_identified_record as representation  # noqa: E402
from deepwide_agent import v25052_cran_fixed_denominator_contract as contract  # noqa: E402
from deepwide_agent.native_search import decode_web_text, html_to_document  # noqa: E402
from scripts import run_v25050_cran_html_representation as model_parent  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


ModelAttemptError = model_parent.ModelAttemptError
normalize_prediction = model_parent.normalize_prediction


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.52 expected JSON object")
    return value


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.50.52 forward requires clean pushed HEAD")


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _validate_start(protocol: Mapping[str, Any]) -> dict[str, Any]:
    value = _read(contract.EXECUTION_START)
    expected_keys = {
        "artifact_version", "role", "protocol_id", "created_at_unix",
        "git_head", "protocol_sha256", "preactivation_audit_sha256",
        "task_vector_sha256", "endpoint_vector_sha256",
        "arm_order_vector_sha256", "protected_watchers", "authorization",
        "execution_start_payload_sha256",
    }
    expected_authorization = {
        "one_fixed_denominator_external_forward": True,
        "evaluator": False,
        "deepwidebench_dev64_exact220_or_sota": False,
        "retry_resume_population_replacement_or_selective_revaluation": False,
    }
    if (
        set(value) != expected_keys
        or value.get("artifact_version") != 1
        or value.get("role") != "v25052_cran_fixed_denominator_execution_start"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or value.get("preactivation_audit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or value.get("task_vector_sha256") != protocol["population"]["task_vector_sha256"]
        or value.get("endpoint_vector_sha256") != protocol["population"]["endpoint_vector_sha256"]
        or value.get("arm_order_vector_sha256") != protocol["population"]["arm_order_vector_sha256"]
        or value.get("protected_watchers") != contract.watcher_snapshot()
        or value.get("authorization") != expected_authorization
        or not contract.sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.50.52 execution start drifted")
    return value


def _fetch_exact(index: int) -> dict[str, Any]:
    visible = contract.task_vector()[index]
    endpoint = contract.endpoint_vector()[index]
    attempts = successes = status = 0
    started = time.monotonic()
    try:
        attempts = 1
        with requests.get(
            endpoint,
            headers={"User-Agent": "DeepWideResearch/1.0 (+v25052-cran-fixed-denominator)"},
            timeout=contract.FETCH_TIMEOUT,
            allow_redirects=False,
            stream=True,
        ) as response:
            status = int(response.status_code)
            if status != 200 or str(response.url) != endpoint:
                raise ValueError("V2.50.52 exact endpoint identity drifted")
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if content_type not in {"text/html", "application/xhtml+xml", ""}:
                raise ValueError("V2.50.52 CRAN content type drifted")
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=1 << 20):
                if not chunk:
                    continue
                size += len(chunk)
                if size > contract.MAX_RESPONSE_BYTES:
                    raise ValueError("V2.50.52 response exceeds byte cap")
                chunks.append(bytes(chunk))
            raw_bytes = b"".join(chunks)
            encoding = response.encoding
        decoded = decode_web_text(raw_bytes, encoding)
        title, text, _links = html_to_document(decoded, endpoint)
        page = {"title": title, "url": endpoint, "text": text}
        rendered = representation.build_representation(
            visible["question"], page, page_character_cap=contract.EVIDENCE_CHAR_CAP
        )
        receipt = representation.validate_receipt(rendered["page_self_record_receipt"])
        record = representation.extract_record(visible["question"], page)
        if tuple(record) != contract.COLUMNS:
            raise ValueError("V2.50.52 bound record schema drifted")
        control_chars = len(rendered["control_evidence"])
        candidate_chars = len(rendered["candidate_evidence"])
        paired_length_valid = bool(
            0 < control_chars == candidate_chars <= contract.EVIDENCE_CHAR_CAP
        )
        successes = 1
        return {
            "index": index,
            "opaque_id": visible["opaque_id"],
            "question": visible["question"],
            "project": contract.PROJECTS[index],
            "endpoint": endpoint,
            "raw_response_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            "raw_response_bytes": len(raw_bytes),
            "decoded_page_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "decoded_page_characters": len(text),
            "control_evidence": rendered["control_evidence"],
            "candidate_evidence": rendered["candidate_evidence"],
            "receipt": receipt,
            "record": record,
            "fetch_attempts": attempts,
            "fetch_successes": successes,
            "http_status": status,
            "elapsed_seconds": round(max(0.0, time.monotonic() - started), 6),
            "paired_evidence_chars": control_chars if paired_length_valid else 0,
            "preparation_terminal": True,
            "ready": bool(
                receipt["mechanism_engaged"]
                and receipt["jointly_bound_identity_count"] == 1
                and receipt["retained_record_count"] == 1
                and receipt["retained_bound_observation_count"]
                == len(contract.COLUMNS) - 1
                and paired_length_valid
            ),
        }
    except Exception:
        return {
            "index": index,
            "opaque_id": visible["opaque_id"],
            "fetch_attempts": attempts,
            "fetch_successes": successes,
            "http_status": status,
            "elapsed_seconds": round(max(0.0, time.monotonic() - started), 6),
            "paired_evidence_chars": 0,
            "preparation_terminal": True,
            "ready": False,
        }


def _validate_prepared(prepared: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    expected_ids = [row["opaque_id"] for row in contract.task_vector()]
    if (
        len(prepared) != contract.TASK_COUNT
        or [row.get("index") for row in prepared] != list(range(contract.TASK_COUNT))
        or [row.get("opaque_id") for row in prepared] != expected_ids
    ):
        raise RuntimeError("V2.50.52 preparation denominator drifted")
    output = []
    for index, raw in enumerate(prepared):
        row = copy.deepcopy(dict(raw))
        for name in (
            "fetch_attempts", "fetch_successes", "http_status",
            "paired_evidence_chars",
        ):
            if isinstance(row.get(name), bool) or not isinstance(row.get(name), int):
                raise RuntimeError("V2.50.52 preparation counter drifted")
        if (
            row.get("preparation_terminal") is not True
            or (row.get("ready") is not True and row.get("ready") is not False)
            or not 0 <= row["fetch_successes"] <= row["fetch_attempts"] <= 1
            or row["http_status"] < 0
            or not 0 <= row["paired_evidence_chars"] <= contract.EVIDENCE_CHAR_CAP
        ):
            raise RuntimeError("V2.50.52 preparation row drifted")
        if row["ready"] is True:
            receipt = representation.validate_receipt(row.get("receipt") or {})
            record = row.get("record") or {}
            control_chars = len(str(row.get("control_evidence") or ""))
            candidate_chars = len(str(row.get("candidate_evidence") or ""))
            if (
                row.get("project") != contract.PROJECTS[index]
                or row.get("question") != contract.task_vector()[index]["question"]
                or row.get("endpoint") != contract.endpoint_vector()[index]
                or row["fetch_attempts"] != 1
                or row["fetch_successes"] != 1
                or row["http_status"] != 200
                or receipt["retained_record_count"] != 1
                or receipt["retained_bound_observation_count"]
                != len(contract.COLUMNS) - 1
                or not 0 < control_chars == candidate_chars <= contract.EVIDENCE_CHAR_CAP
                or row["paired_evidence_chars"] != control_chars
                or tuple(record) != contract.COLUMNS
            ):
                raise RuntimeError("V2.50.52 ready representation drifted")
        else:
            expected_failure_keys = {
                "index", "opaque_id", "fetch_attempts", "fetch_successes",
                "http_status", "elapsed_seconds", "paired_evidence_chars",
                "preparation_terminal", "ready",
            }
            if set(row) != expected_failure_keys or row["paired_evidence_chars"] != 0:
                raise RuntimeError("V2.50.52 failure preparation leaked content")
        output.append(row)
    return output


def build_readiness(
    prepared: Sequence[Mapping[str, Any]], *, now: int | None = None
) -> dict[str, Any]:
    checked = _validate_prepared(prepared)
    terminal = sum(row["preparation_terminal"] is True for row in checked)
    ready = sum(row["ready"] is True for row in checked)
    failures = contract.TASK_COUNT - ready
    attempts = sum(int(row["fetch_attempts"]) for row in checked)
    successes = sum(int(row["fetch_successes"]) for row in checked)
    status_counts = Counter(str(int(row["http_status"])) for row in checked)
    evidence_total = sum(int(row["paired_evidence_chars"]) for row in checked)
    checks = {
        "all_preparations_terminal": terminal == contract.TASK_COUNT,
        "minimum_ready_tasks_met": ready >= contract.MINIMUM_READY_TASKS,
        "preparation_failures_within_cap": failures
        <= contract.TASK_COUNT - contract.MINIMUM_READY_TASKS,
        "ready_tasks_have_positive_bounded_evidence": 0 < evidence_total
        <= ready * contract.EVIDENCE_CHAR_CAP,
        "no_model_call_before_readiness": True,
        "output_root_absent_before_readiness": not (ROOT / contract.OUTPUT_ROOT).exists(),
    }
    passed = all(checks.values())
    value = {
        "artifact_version": 1,
        "role": "v25052_cran_fixed_denominator_readiness",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "task_count": contract.TASK_COUNT,
        "terminal_preparations": terminal,
        "ready_tasks": ready,
        "preparation_failure_tasks": failures,
        "shared_ready_evidence_characters_per_arm": evidence_total,
        "fetch_attempts": attempts,
        "fetch_successes": successes,
        "http_status_counts": dict(sorted(status_counts.items())),
        "checks": checks,
        "findings": sorted(name for name, ok in checks.items() if not ok),
        "passed": passed,
        "contains_project_question_field_value_endpoint_page_prediction_hash_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "model_search_or_evaluator_called_before_receipt": False,
        "authorization": {
            "fixed_denominator_paired_forward": passed,
            "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement": False,
        },
    }
    return contract.seal(value, "readiness_payload_sha256")


def validate_readiness(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    checks = copied.get("checks") or {}
    expected_check_keys = {
        "all_preparations_terminal", "minimum_ready_tasks_met",
        "preparation_failures_within_cap",
        "ready_tasks_have_positive_bounded_evidence",
        "no_model_call_before_readiness", "output_root_absent_before_readiness",
    }
    counters = (
        "task_count", "terminal_preparations", "ready_tasks",
        "preparation_failure_tasks", "shared_ready_evidence_characters_per_arm",
        "fetch_attempts", "fetch_successes",
    )
    counters_valid = all(
        not isinstance(copied.get(name), bool)
        and isinstance(copied.get(name), int)
        and copied[name] >= 0
        for name in counters
    )
    ready = copied.get("ready_tasks", -1)
    failures = copied.get("preparation_failure_tasks", -1)
    expected_checks = {
        "all_preparations_terminal": copied.get("terminal_preparations")
        == contract.TASK_COUNT,
        "minimum_ready_tasks_met": counters_valid
        and ready >= contract.MINIMUM_READY_TASKS,
        "preparation_failures_within_cap": counters_valid
        and failures == contract.TASK_COUNT - ready
        and failures <= contract.TASK_COUNT - contract.MINIMUM_READY_TASKS,
        "ready_tasks_have_positive_bounded_evidence": counters_valid
        and 0 < copied.get("shared_ready_evidence_characters_per_arm", 0)
        <= ready * contract.EVIDENCE_CHAR_CAP,
        "no_model_call_before_readiness": True,
        "output_root_absent_before_readiness": True,
    }
    passed = counters_valid and all(expected_checks.values())
    expected_authorization = {
        "fixed_denominator_paired_forward": passed,
        "evaluator": False,
        "deepwidebench_dev64_exact220_or_sota": False,
        "retry_resume_population_replacement": False,
    }
    expected_keys = {
        "artifact_version", "role", "protocol_id", "created_at_unix",
        "task_count", "terminal_preparations", "ready_tasks",
        "preparation_failure_tasks", "shared_ready_evidence_characters_per_arm",
        "fetch_attempts", "fetch_successes", "http_status_counts", "checks",
        "findings", "passed",
        "contains_project_question_field_value_endpoint_page_prediction_hash_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "model_search_or_evaluator_called_before_receipt", "authorization",
        "readiness_payload_sha256",
    }
    if (
        set(copied) != expected_keys
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25052_cran_fixed_denominator_readiness"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("task_count") != contract.TASK_COUNT
        or not counters_valid
        or set(checks) != expected_check_keys
        or checks != expected_checks
        or not isinstance(copied.get("http_status_counts"), Mapping)
        or any(
            not isinstance(key, str)
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for key, count in (copied.get("http_status_counts") or {}).items()
        )
        or sum((copied.get("http_status_counts") or {}).values()) != contract.TASK_COUNT
        or copied.get("passed") is not passed
        or copied.get("findings")
        != ([] if passed else sorted(name for name, ok in checks.items() if ok is not True))
        or copied.get("contains_project_question_field_value_endpoint_page_prediction_hash_or_credential") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_read") is not False
        or copied.get("model_search_or_evaluator_called_before_receipt") is not False
        or copied.get("authorization") != expected_authorization
        or not contract.sealed(copied, "readiness_payload_sha256")
    ):
        raise RuntimeError("V2.50.52 readiness drifted")
    return copied


def _zero_usage() -> dict[str, int]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "elapsed_milliseconds": 0,
        "provider_attempts": 0,
    }


def _synthesize(question: str, evidence: str, *, deadline: float) -> tuple[str, dict[str, int]]:
    return model_parent._synthesize(question, evidence, deadline=deadline)


def _row_from_prepared(item: Mapping[str, Any]) -> dict[str, Any]:
    index = int(item["index"])
    started = time.monotonic()
    preparation_ready = item["ready"] is True
    if preparation_ready:
        evidence = {
            contract.CONTROL_ARM: str(item["control_evidence"]),
            contract.CANDIDATE_ARM: str(item["candidate_evidence"]),
        }
        deadline = started + contract.TASK_DEADLINE_SECONDS
        predictions: dict[str, str] = {}
        usage: dict[str, dict[str, int]] = {}
        success = {arm: False for arm in contract.ARMS}
        for arm in contract.arm_order_vector()[index]:
            try:
                predictions[arm], usage[arm] = _synthesize(
                    str(item["question"]), evidence[arm], deadline=deadline
                )
                success[arm] = True
            except ModelAttemptError as exc:
                usage[arm] = {**_zero_usage(), "provider_attempts": exc.provider_attempts}
            except Exception:
                usage[arm] = _zero_usage()
        completed = all(success.values())
        if not completed:
            predictions = {arm: contract.FALLBACK_TABLE for arm in contract.ARMS}
        receipt: Mapping[str, Any] | None = representation.validate_receipt(item["receipt"])
    else:
        evidence = {arm: "" for arm in contract.ARMS}
        predictions = {arm: contract.FALLBACK_TABLE for arm in contract.ARMS}
        usage = {arm: _zero_usage() for arm in contract.ARMS}
        success = {arm: False for arm in contract.ARMS}
        completed = False
        receipt = None
    row = {
        "artifact_version": 1,
        "role": "v25052_cran_fixed_denominator_task_result",
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": item["opaque_id"],
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_cran_html_bytes"],
        "terminal": True,
        "preparation_ready": preparation_ready,
        "preparation_failure_as_zero": not preparation_ready,
        "completed": completed,
        "failure_as_zero": not completed,
        "fetch_attempts": int(item["fetch_attempts"]),
        "fetch_successes": int(item["fetch_successes"]),
        "http_status": int(item["http_status"]),
        "representation_receipt": receipt,
        "evidence_chars": {arm: len(evidence[arm]) for arm in contract.ARMS},
        "model_success": success,
        "model_attempts": {
            arm: int((usage.get(arm) or {}).get("provider_attempts", 0))
            for arm in contract.ARMS
        },
        "model_usage": usage,
        "predictions": predictions,
        "prediction_sha256": {
            arm: contract.payload_sha256(predictions[arm]) for arm in contract.ARMS
        },
        "prediction_changed": predictions[contract.CONTROL_ARM]
        != predictions[contract.CANDIDATE_ARM],
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "unready_task_has_zero_model_calls_and_paired_fallback": not preparation_ready,
        "ready_task_uses_same_exact_response_and_decoded_page_for_both_arms": preparation_ready,
        "ready_task_evidence_lengths_positive_equal_and_at_most_cap": preparation_ready,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "retry_resume_population_replacement_or_selective_rerun": False,
        "contains_project_question_field_value_endpoint_page_answer_raw_response_or_credential": False,
    }
    return contract.seal(row, "result_payload_sha256")


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    predictions = copied.get("predictions") or {}
    hashes = copied.get("prediction_sha256") or {}
    evidence = copied.get("evidence_chars") or {}
    success = copied.get("model_success") or {}
    attempts = copied.get("model_attempts") or {}
    usage = copied.get("model_usage") or {}
    ready = copied.get("preparation_ready") is True
    completed = copied.get("completed") is True
    expected = {
        "artifact_version", "role", "protocol_id", "opaque_id",
        "runtime_input_keys", "terminal", "preparation_ready",
        "preparation_failure_as_zero", "completed", "failure_as_zero",
        "fetch_attempts", "fetch_successes", "http_status",
        "representation_receipt", "evidence_chars", "model_success",
        "model_attempts", "model_usage", "predictions", "prediction_sha256",
        "prediction_changed", "wall_seconds",
        "unready_task_has_zero_model_calls_and_paired_fallback",
        "ready_task_uses_same_exact_response_and_decoded_page_for_both_arms",
        "ready_task_evidence_lengths_positive_equal_and_at_most_cap",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "entropy_or_information_gain_assigns_credit_or_routes",
        "retry_resume_population_replacement_or_selective_rerun",
        "contains_project_question_field_value_endpoint_page_answer_raw_response_or_credential",
        "result_payload_sha256",
    }
    usage_valid = bool(
        set(usage) == set(contract.ARMS)
        and all(
            isinstance(usage[arm], Mapping)
            and set(usage[arm])
            == {
                "input_tokens", "output_tokens", "total_tokens",
                "elapsed_milliseconds", "provider_attempts",
            }
            and all(
                not isinstance(usage[arm].get(name), bool)
                and isinstance(usage[arm].get(name), int)
                and usage[arm][name] >= 0
                for name in usage[arm]
            )
            for arm in contract.ARMS
        )
    )
    ready_evidence = bool(
        set(evidence) == set(contract.ARMS)
        and all(
            not isinstance(evidence[arm], bool)
            and isinstance(evidence[arm], int)
            for arm in contract.ARMS
        )
        and 0 < evidence[contract.CONTROL_ARM]
        == evidence[contract.CANDIDATE_ARM]
        <= contract.EVIDENCE_CHAR_CAP
    )
    unready_exact = bool(
        not ready
        and copied.get("preparation_failure_as_zero") is True
        and copied.get("representation_receipt") is None
        and evidence == {arm: 0 for arm in contract.ARMS}
        and success == {arm: False for arm in contract.ARMS}
        and attempts == {arm: 0 for arm in contract.ARMS}
        and usage == {arm: _zero_usage() for arm in contract.ARMS}
        and predictions == {arm: contract.FALLBACK_TABLE for arm in contract.ARMS}
        and completed is False
        and copied.get("failure_as_zero") is True
        and copied.get("prediction_changed") is False
    )
    ready_receipt = copied.get("representation_receipt")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25052_cran_fixed_denominator_task_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("opaque_id") not in {row["opaque_id"] for row in contract.task_vector()}
        or copied.get("runtime_input_keys")
        != ["opaque_id", "question", "same_forward_public_cran_html_bytes"]
        or copied.get("terminal") is not True
        or not isinstance(copied.get("preparation_ready"), bool)
        or copied.get("preparation_failure_as_zero") is ready
        or copied.get("failure_as_zero") is completed
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            for name in ("fetch_attempts", "fetch_successes", "http_status")
        )
        or not 0 <= copied["fetch_successes"] <= copied["fetch_attempts"] <= 1
        or copied["http_status"] < 0
        or (
            ready
            and (
                copied["fetch_attempts"] != 1
                or copied["fetch_successes"] != 1
                or copied["http_status"] != 200
            )
        )
        or set(predictions) != set(contract.ARMS)
        or any(
            not isinstance(predictions[arm], str)
            or not predictions[arm]
            or normalize_prediction(predictions[arm]) != predictions[arm]
            for arm in contract.ARMS
        )
        or set(hashes) != set(contract.ARMS)
        or any(hashes[arm] != contract.payload_sha256(predictions[arm]) for arm in contract.ARMS)
        or copied.get("prediction_changed") is not (
            predictions[contract.CONTROL_ARM] != predictions[contract.CANDIDATE_ARM]
        )
        or set(success) != set(contract.ARMS)
        or any(success[arm] is not True and success[arm] is not False for arm in contract.ARMS)
        or set(attempts) != set(contract.ARMS)
        or any(
            isinstance(attempts[arm], bool)
            or not isinstance(attempts[arm], int)
            or attempts[arm] not in {0, 1}
            for arm in contract.ARMS
        )
        or not usage_valid
        or any(usage[arm]["provider_attempts"] != attempts[arm] for arm in contract.ARMS)
        or any(success[arm] is True and attempts[arm] != 1 for arm in contract.ARMS)
        or completed is not all(success.values())
        or (completed and any(predictions[arm] == contract.FALLBACK_TABLE for arm in contract.ARMS))
        or (
            not completed
            and predictions != {arm: contract.FALLBACK_TABLE for arm in contract.ARMS}
        )
        or isinstance(copied.get("wall_seconds"), bool)
        or not isinstance(copied.get("wall_seconds"), (int, float))
        or copied["wall_seconds"] < 0
        or (
            ready
            and (
                not ready_evidence
                or not isinstance(ready_receipt, Mapping)
                or representation.validate_receipt(ready_receipt) != ready_receipt
                or ready_receipt["retained_record_count"] != 1
                or ready_receipt["retained_bound_observation_count"]
                != len(contract.COLUMNS) - 1
                or copied.get("unready_task_has_zero_model_calls_and_paired_fallback") is not False
                or copied.get("ready_task_uses_same_exact_response_and_decoded_page_for_both_arms") is not True
                or copied.get("ready_task_evidence_lengths_positive_equal_and_at_most_cap") is not True
            )
        )
        or (not ready and not unready_exact)
        or (
            not ready
            and (
                copied.get("unready_task_has_zero_model_calls_and_paired_fallback") is not True
                or copied.get("ready_task_uses_same_exact_response_and_decoded_page_for_both_arms") is not False
                or copied.get("ready_task_evidence_lengths_positive_equal_and_at_most_cap") is not False
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_read",
                "entropy_or_information_gain_assigns_credit_or_routes",
                "retry_resume_population_replacement_or_selective_rerun",
                "contains_project_question_field_value_endpoint_page_answer_raw_response_or_credential",
            )
        )
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.50.52 task result drifted")
    return copied


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    if len(checked) != contract.TASK_COUNT or len({row["opaque_id"] for row in checked}) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.52 aggregate denominator drifted")
    counters: Counter[str] = Counter()
    evidence_chars = {arm: 0 for arm in contract.ARMS}
    model_tokens = {arm: 0 for arm in contract.ARMS}
    for row in checked:
        counters["terminal_tasks"] += int(row["terminal"])
        counters["ready_tasks"] += int(row["preparation_ready"])
        counters["preparation_failure_tasks"] += int(row["preparation_failure_as_zero"])
        counters["completed_tasks"] += int(row["completed"])
        counters["fallback_tasks"] += int(row["failure_as_zero"])
        counters["identity_bound_records"] += int(
            (row["representation_receipt"] or {}).get("retained_record_count", 0)
        )
        counters["bound_target_fields"] += int(
            (row["representation_receipt"] or {}).get("retained_bound_observation_count", 0)
        )
        counters["prediction_changed_tasks"] += int(row["prediction_changed"])
        for arm in contract.ARMS:
            counters[f"{arm}_model_successes"] += int(row["model_success"][arm])
            counters[f"{arm}_model_attempts"] += int(row["model_attempts"][arm])
            evidence_chars[arm] += int(row["evidence_chars"][arm])
            model_tokens[arm] += int(row["model_usage"][arm]["total_tokens"])
    return {
        **dict(counters),
        "terminal_arm_predictions": len(checked) * len(contract.ARMS),
        "evidence_chars": evidence_chars,
        "model_tokens": model_tokens,
        "contains_project_question_field_value_endpoint_page_answer_raw_response_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }


def mechanism_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = contract.gates()["mechanism"]
    ready = value.get("ready_tasks", -1)
    preparation_failures = value.get("preparation_failure_tasks", -1)
    evidence = value.get("evidence_chars") or {}
    evidence_matched = bool(
        set(evidence) == set(contract.ARMS)
        and evidence[contract.CONTROL_ARM] == evidence[contract.CANDIDATE_ARM]
        and 0 < evidence[contract.CONTROL_ARM]
        <= ready * contract.EVIDENCE_CHAR_CAP
    )
    checks = {
        "terminal_fixed_denominator": value.get("terminal_tasks") == contract.TASK_COUNT
        and value.get("terminal_arm_predictions") == contract.TASK_COUNT * len(contract.ARMS),
        "minimum_ready_tasks": ready >= contract.MINIMUM_READY_TASKS,
        "preparation_failures_within_cap": preparation_failures
        == contract.TASK_COUNT - ready
        and preparation_failures
        <= expected["maximum_preparation_failure_tasks"],
        "paired_preparation_failures_are_only_fallbacks": value.get("fallback_tasks")
        == preparation_failures,
        "all_ready_tasks_completed": value.get("completed_tasks") == ready,
        "all_ready_records_and_fields_bound": value.get("identity_bound_records") == ready
        and value.get("bound_target_fields") == ready * (len(contract.COLUMNS) - 1),
        "model_successes_and_attempts_equal_ready_tasks": all(
            value.get(f"{arm}_model_successes") == ready
            and value.get(f"{arm}_model_attempts") == ready
            for arm in contract.ARMS
        ),
        "shared_ready_evidence_total_matched_and_bounded": evidence_matched,
        "minimum_prediction_change": value.get("prediction_changed_tasks", 0)
        >= expected["minimum_prediction_changed_tasks"],
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "mechanism_gate_passed": passed,
        "postfreeze_external_evaluator_protocol": passed,
        "deepwidebench_dev64_exact220_or_sota": False,
    }


def validate_snapshot_rows(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if len(values) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.52 snapshot denominator drifted")
    expected_keys = {
        "index", "opaque_id", "project", "preparation_ready",
        "endpoint_sha256", "raw_response_sha256", "raw_response_bytes",
        "decoded_page_sha256", "decoded_page_characters", "http_status",
        "record", "prediction_freeze_sha256", "published_after_prediction_freeze",
    }
    output = []
    freeze_sha256 = contract.sha256(ROOT / contract.PREDICTION_FREEZE)
    for index, raw in enumerate(values):
        row = copy.deepcopy(dict(raw))
        ready = row.get("preparation_ready") is True
        record = row.get("record")
        ready_surface = bool(
            ready
            and isinstance(row.get("raw_response_sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", row["raw_response_sha256"])
            and isinstance(row.get("raw_response_bytes"), int)
            and not isinstance(row.get("raw_response_bytes"), bool)
            and row["raw_response_bytes"] > 0
            and isinstance(row.get("decoded_page_sha256"), str)
            and re.fullmatch(r"[0-9a-f]{64}", row["decoded_page_sha256"])
            and isinstance(row.get("decoded_page_characters"), int)
            and not isinstance(row.get("decoded_page_characters"), bool)
            and row["decoded_page_characters"] > 0
            and row.get("http_status") == 200
            and isinstance(record, Mapping)
            and tuple(record) == contract.COLUMNS
            and all(
                isinstance(record[column], str)
                and record[column]
                and not any(character in record[column] for character in "|\r\n\x00")
                for column in contract.COLUMNS
            )
            and representation._identity_key(record["Package"])
            == representation._identity_key(contract.PROJECTS[index])
            and re.fullmatch(r"\d{4}-\d{2}-\d{2}", record["Published"])
        )
        failure_surface = bool(
            not ready
            and row.get("raw_response_sha256") is None
            and row.get("raw_response_bytes") is None
            and row.get("decoded_page_sha256") is None
            and row.get("decoded_page_characters") is None
            and isinstance(row.get("http_status"), int)
            and not isinstance(row.get("http_status"), bool)
            and row["http_status"] >= 0
            and record is None
        )
        if (
            set(row) != expected_keys
            or row.get("index") != index
            or row.get("opaque_id") != contract.task_vector()[index]["opaque_id"]
            or row.get("project") != contract.PROJECTS[index]
            or not isinstance(row.get("preparation_ready"), bool)
            or row.get("endpoint_sha256")
            != hashlib.sha256(contract.endpoint_vector()[index].encode()).hexdigest()
            or not (ready_surface or failure_surface)
            or row.get("prediction_freeze_sha256") != freeze_sha256
            or row.get("published_after_prediction_freeze") is not True
        ):
            raise RuntimeError("V2.50.52 snapshot row drifted")
        output.append(row)
    return output


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _validate_start(protocol)
    future = (
        contract.PARSER_READINESS, contract.OUTPUT_ROOT, contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT, contract.EVALUATOR, contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.52 effect surface is not pristine")
    if not _lease_inactive():
        raise RuntimeError("V2.50.52 shared lease is active")
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25052_cran_fixed_denominator_forward_v1",
        purpose="fixed_denominator_paired_preparation_failure_as_zero",
        path=ROOT / contract.LEASE_PATH,
    ):
        if contract.watcher_snapshot() != protocol["protected_watchers"]:
            raise RuntimeError("V2.50.52 protected watcher drifted before effect")
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            prepared = list(pool.map(_fetch_exact, range(contract.TASK_COUNT)))
        prepared.sort(key=lambda row: int(row["index"]))
        prepared = _validate_prepared(prepared)
        readiness = validate_readiness(build_readiness(prepared))
        _publish(ROOT / contract.PARSER_READINESS, readiness)
        if not readiness["passed"]:
            return readiness
        (ROOT / contract.OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            rows = list(pool.map(_row_from_prepared, prepared))
        wall = max(0.0, time.monotonic() - started)
    checked = [validate_task_row(row) for row in rows]
    _publish_jsonl(ROOT / contract.TASK_ROWS, checked)
    totals = aggregate(checked)
    mechanism = mechanism_decision(totals)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25052_cran_fixed_denominator_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "task_count": contract.TASK_COUNT,
            "terminal_arm_predictions": contract.TASK_COUNT * len(contract.ARMS),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_hash_vector_sha256": contract.payload_sha256(
                [[row["prediction_sha256"][arm] for arm in contract.ARMS] for row in checked]
            ),
            "parser_readiness_sha256": contract.sha256(ROOT / contract.PARSER_READINESS),
            "public_snapshot_present_before_prediction_freeze": False,
            "all_predictions_terminal_before_evaluator_or_quality_decision": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "freeze_payload_sha256",
    )
    _publish(ROOT / contract.PREDICTION_FREEZE, freeze)
    freeze_sha256 = contract.sha256(ROOT / contract.PREDICTION_FREEZE)
    snapshot = validate_snapshot_rows(
        [
            {
                "index": int(item["index"]),
                "opaque_id": item["opaque_id"],
                "project": contract.PROJECTS[int(item["index"])],
                "preparation_ready": item["ready"],
                "endpoint_sha256": hashlib.sha256(
                    contract.endpoint_vector()[int(item["index"])].encode()
                ).hexdigest(),
                "raw_response_sha256": item.get("raw_response_sha256"),
                "raw_response_bytes": item.get("raw_response_bytes"),
                "decoded_page_sha256": item.get("decoded_page_sha256"),
                "decoded_page_characters": item.get("decoded_page_characters"),
                "http_status": int(item["http_status"]),
                "record": dict(item["record"]) if item["ready"] else None,
                "prediction_freeze_sha256": freeze_sha256,
                "published_after_prediction_freeze": True,
            }
            for item in prepared
        ]
    )
    _publish_jsonl(ROOT / contract.PUBLIC_SNAPSHOT, snapshot)
    result = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25052_cran_fixed_denominator_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "wall_seconds": round(wall, 6),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_freeze_sha256": freeze_sha256,
            "public_snapshot_sha256": contract.sha256(ROOT / contract.PUBLIC_SNAPSHOT),
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "execution_start_payload_sha256": start["execution_start_payload_sha256"],
            "parser_readiness_sha256": contract.sha256(ROOT / contract.PARSER_READINESS),
            "aggregate": totals,
            "mechanism_decision": mechanism,
            "all_predictions_terminal_before_public_snapshot_evaluator_or_quality_decision": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "authorization": {
                "postfreeze_external_evaluator_protocol": False,
                "deepwidebench_dev64_exact220_or_sota": False,
                "retry_resume_population_replacement_or_selective_revaluation": False,
            },
        },
        "result_payload_sha256",
    )
    _publish(ROOT / contract.FORWARD_RESULT, result)
    return result


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version", "role", "protocol_id", "created_at_unix",
        "task_count", "wall_seconds", "task_rows_sha256",
        "prediction_freeze_sha256", "public_snapshot_sha256",
        "execution_start_sha256", "execution_start_payload_sha256",
        "parser_readiness_sha256", "aggregate", "mechanism_decision",
        "all_predictions_terminal_before_public_snapshot_evaluator_or_quality_decision",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "authorization", "result_payload_sha256",
    }
    expected_authorization = {
        "postfreeze_external_evaluator_protocol": False,
        "deepwidebench_dev64_exact220_or_sota": False,
        "retry_resume_population_replacement_or_selective_revaluation": False,
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25052_cran_fixed_denominator_forward_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("task_count") != contract.TASK_COUNT
        or isinstance(copied.get("wall_seconds"), bool)
        or not isinstance(copied.get("wall_seconds"), (int, float))
        or copied["wall_seconds"] < 0
        or copied.get("task_rows_sha256") != contract.sha256(ROOT / contract.TASK_ROWS)
        or copied.get("prediction_freeze_sha256") != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or copied.get("public_snapshot_sha256") != contract.sha256(ROOT / contract.PUBLIC_SNAPSHOT)
        or copied.get("execution_start_sha256") != contract.sha256(ROOT / contract.EXECUTION_START)
        or copied.get("parser_readiness_sha256") != contract.sha256(ROOT / contract.PARSER_READINESS)
        or copied.get("mechanism_decision") != mechanism_decision(copied.get("aggregate") or {})
        or copied.get("all_predictions_terminal_before_public_snapshot_evaluator_or_quality_decision") is not True
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_read") is not False
        or copied.get("authorization") != expected_authorization
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.50.52 forward result drifted")
    return copied


def main() -> None:
    value = run_forward()
    path = (
        contract.PARSER_READINESS
        if value.get("role") == "v25052_cran_fixed_denominator_readiness"
        else contract.FORWARD_RESULT
    )
    print(
        json.dumps(
            {
                "role": value["role"], "path": str(path),
                "passed": value.get("passed"),
                "ready_tasks": value.get("ready_tasks"),
                "aggregate": value.get("aggregate"),
                "mechanism_decision": value.get("mechanism_decision"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
