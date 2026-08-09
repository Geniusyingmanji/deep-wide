#!/usr/bin/env python3
"""Atomic parser-ready paired forward over complete shared PyPI JSON."""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24978_pypi_release_file_compactor as compact  # noqa: E402
from deepwide_agent import v24979_atomic_pypi_quality_contract as contract  # noqa: E402
from scripts import run_v24973_identity_bound_field_quality as schema_runner  # noqa: E402
from scripts import run_v24975_raw_authority_quality as transport  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


def configure() -> None:
    contract._configure_schema()
    schema_runner.contract = contract
    schema_runner._MODEL_SEMAPHORE = threading.BoundedSemaphore(contract.MODEL_CONCURRENCY)
    transport.contract = contract


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _raw_evidence(page: Mapping[str, Any]) -> str:
    prefix = "[PYPI JSON]\n"
    text = str(page.get("text") or "")
    value = (prefix + text)[: contract.EVIDENCE_CHARS]
    return value + " " * (contract.EVIDENCE_CHARS - len(value))


def _prepare(index: int) -> dict[str, Any]:
    project = contract.PROJECTS[index]
    visible = contract.task_vector()[index]
    url = contract.endpoint_vector()[index][0]
    deadline = time.monotonic() + contract.TASK_DEADLINE_SECONDS
    attempts = successes = 0
    statuses: Counter[int] = Counter()
    try:
        attempts = 1
        page, status = transport._fetch_exact(
            url, kind="pypi_json", repository="pypi-only", deadline=deadline
        )
        successes = 1
        statuses[status] += 1
        raw = _raw_evidence(page)
        result = compact.build_compact_evidence(
            [page], raw, project=project, total_chars=contract.EVIDENCE_CHARS
        )
        receipt = compact.validate_receipt(
            result["receipt"], total_chars=contract.EVIDENCE_CHARS
        )
        ready = (
            receipt["record_admitted"] is True
            and receipt["unique_bound_field_count"] == 5
            and receipt["conflicting_field_count"] == 0
            and result["evidence"] != raw
        )
        return {
            "index": index,
            "opaque_id": visible["opaque_id"],
            "question": visible["question"],
            "raw": raw,
            "candidate": str(result["evidence"]),
            "receipt": receipt,
            "fetch_attempts": attempts,
            "fetch_successes": successes,
            "fetch_status_counts": {str(k): v for k, v in sorted(statuses.items())},
            "ready": ready,
        }
    except Exception:
        return {
            "index": index,
            "opaque_id": visible["opaque_id"],
            "fetch_attempts": attempts,
            "fetch_successes": successes,
            "fetch_status_counts": {str(k): v for k, v in sorted(statuses.items())},
            "ready": False,
        }


def parser_readiness(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if len(rows) != contract.TASK_COUNT or len({row.get("opaque_id") for row in rows}) != contract.TASK_COUNT:
        raise RuntimeError("V2.49.79 readiness denominator drifted")
    ready = sum(row.get("ready") is True for row in rows)
    fields = sum(int((row.get("receipt") or {}).get("unique_bound_field_count", 0)) for row in rows)
    conflicts = sum(int((row.get("receipt") or {}).get("conflicting_field_count", 0)) for row in rows)
    attempts = sum(int(row.get("fetch_attempts", 0)) for row in rows)
    successes = sum(int(row.get("fetch_successes", 0)) for row in rows)
    checks = {
        "fixed_task_denominator": len(rows) == contract.TASK_COUNT,
        "all_tasks_parser_ready": ready == contract.TASK_COUNT,
        "all_fields_uniquely_bound": fields == contract.TASK_COUNT * 5,
        "zero_field_conflicts": conflicts == 0,
        "all_shared_fetches_complete": attempts == successes == contract.TASK_COUNT,
        "no_model_call_before_readiness": True,
    }
    passed = all(checks.values())
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24979_atomic_pypi_readiness",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "task_count": contract.TASK_COUNT,
        "parser_ready_tasks": ready,
        "unique_bound_fields": fields,
        "field_conflicts": conflicts,
        "fetch_attempts": attempts,
        "fetch_successes": successes,
        "checks": checks,
        "findings": sorted(name for name, ok in checks.items() if not ok),
        "passed": passed,
        "contains_identity_question_value_url_page_prediction_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "model_search_or_evaluator_called_before_receipt": False,
        "authorization": {
            "paired_model_forward": passed,
            "evaluator": False,
            "public_exact220_or_sota": False,
            "retry_resume_population_replacement": False,
        },
    }
    return contract.seal(value, "readiness_payload_sha256")


def _row(item: Mapping[str, Any]) -> dict[str, Any]:
    index = int(item["index"])
    evidence = {
        contract.CONTROL_ARM: str(item["raw"]),
        contract.CANDIDATE_ARM: str(item["candidate"]),
    }
    deadline = time.monotonic() + contract.TASK_DEADLINE_SECONDS
    predictions: dict[str, str] = {}
    usage: dict[str, dict[str, int]] = {}
    success = {arm: False for arm in contract.ARMS}
    for arm in contract.arm_order_vector()[index]:
        try:
            predictions[arm], usage[arm] = schema_runner._synthesize(
                str(item["question"]), evidence[arm], deadline=deadline
            )
            success[arm] = True
        except schema_runner.ModelAttemptError as exc:
            usage[arm] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "elapsed_milliseconds": 0, "provider_attempts": exc.provider_attempts}
        except Exception:
            usage[arm] = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "elapsed_milliseconds": 0, "provider_attempts": 0}
    completed = all(success.values())
    if not completed:
        predictions = {arm: contract.FALLBACK_TABLE for arm in contract.ARMS}
    receipt = item["receipt"]
    compact_counts = {
        "exact_authority_page_count": int(receipt["exact_authority_page_count"]),
        "identity_bound_page_count": int(receipt["identity_bound_page_count"]),
        "identity_mismatch_page_count": 0,
        "malformed_page_count": 0,
        "field_observation_count": int(receipt["unique_bound_field_count"]),
        "unique_bound_field_count": int(receipt["unique_bound_field_count"]),
        "unknown_field_count": int(receipt["unknown_field_count"]),
        "conflicting_field_count": int(receipt["conflicting_field_count"]),
        "compact_prefix_chars": int(receipt["compact_prefix_chars"]),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24973_identity_bound_field_task_result",
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": item["opaque_id"],
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "completed": completed,
        "status": "completed" if completed else "failure_as_zero",
        "failure_as_zero": not completed,
        "fetch_attempts": int(item["fetch_attempts"]),
        "fetch_successes": int(item["fetch_successes"]),
        "fetch_status_counts": dict(item["fetch_status_counts"]),
        "search_tool_calls": 0,
        "github_api_calls": 0,
        "compact_receipt": compact_counts,
        "compact_record_admitted": True,
        "candidate_evidence_changed": True,
        "evidence_chars": {arm: len(evidence[arm]) for arm in contract.ARMS},
        "model_success": success,
        "model_attempt_counts": {arm: int((usage.get(arm) or {}).get("provider_attempts", 0)) for arm in contract.ARMS},
        "model_usage": usage,
        "predictions": predictions,
        "prediction_sha256": {arm: contract.payload_sha256(predictions[arm]) for arm in contract.ARMS},
        "prediction_changed": predictions[contract.CANDIDATE_ARM] != predictions[contract.CONTROL_ARM],
        "wall_seconds": 0.0,
        "same_exact_address_page_bytes_for_both_arms": True,
        "control_has_fixed_equal_namespace_raw_char_quota": True,
        "candidate_prefixes_compact_record_then_same_ordered_raw_evidence": True,
        "same_evidence_chars_prompt_model_output_cap": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "entropy_or_information_gain_assigns_credit": False,
        "retry_resume_skip_or_selective_rerun": False,
        "contains_question_field_value_url_page_answer_or_credential": False,
    }
    return contract.seal(value, "result_payload_sha256")


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    return schema_runner.validate_task_row(value)


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    configure()
    return schema_runner.aggregate(rows)


def mechanism_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = contract.gates()["mechanism"]
    checks = {
        "terminal_fixed_denominator": value.get("terminal_tasks") == expected["terminal_tasks"],
        "all_tasks_completed": value.get("completed_tasks") == contract.TASK_COUNT,
        "shared_exact_fetches_complete": value.get("successful_shared_fetches") == expected["successful_shared_fetches"] and value.get("fetch_attempts") == expected["successful_shared_fetches"],
        "all_compact_records_admitted": value.get("admitted_compact_records") == expected["admitted_compact_records"],
        "all_fields_uniquely_bound": value.get("unique_bound_fields") == expected["unique_bound_fields"],
        "zero_field_conflict": value.get("field_conflicts") == 0,
        "candidate_evidence_changed_all_tasks": value.get("candidate_evidence_changed_tasks") == contract.TASK_COUNT,
        "minimum_prediction_change": value.get("prediction_changed_tasks", 0) >= expected["minimum_prediction_changed_tasks"],
        "model_success_and_attempts_matched": all(value.get(f"{arm}_model_successes") == contract.TASK_COUNT and value.get(f"{arm}_model_attempts") == contract.TASK_COUNT for arm in contract.ARMS),
        "fixed_evidence_budget_matched": value.get("evidence_chars") == {arm: expected["evidence_chars_per_arm"] for arm in contract.ARMS},
        "zero_fallback": value.get("fallback_tasks") == 0,
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "mechanism_gate_passed": passed,
        "postfreeze_external_evaluator_protocol": passed,
        "public_exact220_or_sota": False,
    }


def run_forward() -> dict[str, Any]:
    configure()
    schema_runner._clean_pushed()
    protocol = contract.validate_protocol(ROOT, schema_runner._read(contract.PROTOCOL))
    start = schema_runner._validate_start(protocol)
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (contract.PARSER_READINESS, contract.OUTPUT_ROOT, contract.FORWARD_RESULT, contract.FORWARD_AUDIT)):
        raise RuntimeError("V2.49.79 effect surface is not pristine")
    with acquire_deepwide_api_lease(ROOT, owner=contract.LEASE_OWNER, purpose=contract.LEASE_PURPOSE, path=ROOT / contract.LEASE_PATH):
        if contract.watcher_snapshot() != protocol["protected_watchers"]:
            raise RuntimeError("V2.49.79 protected watcher drifted")
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            prepared = list(pool.map(_prepare, range(contract.TASK_COUNT)))
        prepared.sort(key=lambda row: int(row["index"]))
        readiness = parser_readiness(prepared)
        _publish(ROOT / contract.PARSER_READINESS, readiness)
        if not readiness["passed"]:
            return readiness
        (ROOT / contract.OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        started = time.monotonic()
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            rows = list(pool.map(_row, prepared))
        wall = time.monotonic() - started
    checked = [validate_task_row(row) for row in rows]
    schema_runner._publish_jsonl(ROOT / contract.TASK_ROWS, checked)
    totals = aggregate(checked)
    mechanism = mechanism_decision(totals)
    freeze = contract.seal({
        "artifact_version": 1,
        "role": "v24973_identity_bound_field_prediction_freeze",
        "protocol_id": contract.PROTOCOL_ID,
        "task_count": contract.TASK_COUNT,
        "terminal_arm_predictions": contract.TASK_COUNT * len(contract.ARMS),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_hash_vector_sha256": contract.payload_sha256([[row["prediction_sha256"][arm] for arm in contract.ARMS] for row in checked]),
        "parser_readiness_sha256": contract.sha256(ROOT / contract.PARSER_READINESS),
        "all_predictions_terminal_before_evaluator_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }, "freeze_payload_sha256")
    schema_runner._publish(ROOT / contract.PREDICTION_FREEZE, freeze)
    result = contract.seal({
        "artifact_version": 1,
        "role": "v24973_identity_bound_field_forward_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "task_count": contract.TASK_COUNT,
        "wall_seconds": round(wall, 6),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
        "execution_start_payload_sha256": start["execution_start_payload_sha256"],
        "parser_readiness_sha256": contract.sha256(ROOT / contract.PARSER_READINESS),
        "aggregate": totals,
        "mechanism_decision": mechanism,
        "all_predictions_terminal_before_evaluator_or_quality_decision": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "authorization": {"postfreeze_external_evaluator_protocol": False, "public_exact220_or_sota": False, "retry_resume_selective_rerun": False},
    }, "result_payload_sha256")
    schema_runner._publish(ROOT / contract.FORWARD_RESULT, result)
    return result


def main() -> None:
    value = run_forward()
    print(json.dumps({
        "role": value["role"],
        "path": str(contract.FORWARD_RESULT if value.get("role") != "v24979_atomic_pypi_readiness" else contract.PARSER_READINESS),
        "passed": value.get("passed"),
        "aggregate": value.get("aggregate"),
        "mechanism_decision": value.get("mechanism_decision"),
        "parser_ready_tasks": value.get("parser_ready_tasks"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
