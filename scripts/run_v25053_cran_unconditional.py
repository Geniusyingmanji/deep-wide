#!/usr/bin/env python3
"""Unconditional fixed-denominator CRAN bridge forward for V2.50.53."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
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

from deepwide_agent import v25053_cran_unconditional_denominator_contract as contract  # noqa: E402
from scripts import run_v25052_cran_fixed_denominator as parent  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


# Reuse the audited V2.50.52 task-local mechanics under the successor's frozen
# constants.  Hard-coded artifact roles are translated and resealed below.
parent.contract = contract

normalize_prediction = parent.normalize_prediction
_publish = parent._publish
_publish_jsonl = parent._publish_jsonl
_clean_pushed = parent._clean_pushed
_lease_inactive = parent._lease_inactive
_fetch_exact = parent._fetch_exact
_validate_prepared = parent._validate_prepared
_zero_usage = parent._zero_usage
_synthesize = parent._synthesize


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.53 expected JSON object")
    return value


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
        "one_unconditional_fixed_denominator_forward": True,
        "evaluator": False,
        "deepwidebench_dev64_exact220_or_sota": False,
        "retry_resume_population_replacement_or_selective_revaluation": False,
    }
    if (
        set(value) != expected_keys
        or value.get("artifact_version") != 1
        or value.get("role") != "v25053_cran_unconditional_execution_start"
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
        raise RuntimeError("V2.50.53 execution start drifted")
    return value


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
        "ready_count_does_not_control_activation": True,
        "no_model_call_before_all_preparations_terminal": True,
        "output_root_absent_before_readiness": not (ROOT / contract.OUTPUT_ROOT).exists(),
    }
    passed = all(checks.values())
    value = {
        "artifact_version": 1,
        "role": "v25053_cran_unconditional_readiness",
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
            "unconditional_fixed_denominator_forward": passed,
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
        "all_preparations_terminal", "ready_count_does_not_control_activation",
        "no_model_call_before_all_preparations_terminal",
        "output_root_absent_before_readiness",
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
    evidence = copied.get("shared_ready_evidence_characters_per_arm", -1)
    expected_checks = {
        "all_preparations_terminal": copied.get("terminal_preparations")
        == contract.TASK_COUNT,
        "ready_count_does_not_control_activation": True,
        "no_model_call_before_all_preparations_terminal": True,
        "output_root_absent_before_readiness": True,
    }
    counts_coherent = bool(
        counters_valid
        and copied.get("task_count") == contract.TASK_COUNT
        and 0 <= ready <= contract.TASK_COUNT
        and failures == contract.TASK_COUNT - ready
        and 0 <= copied.get("fetch_successes", -1)
        <= copied.get("fetch_attempts", -1)
        <= contract.TASK_COUNT
        and 0 <= evidence <= ready * contract.EVIDENCE_CHAR_CAP
        and (ready == 0) is (evidence == 0)
    )
    passed = counts_coherent and all(expected_checks.values())
    expected_authorization = {
        "unconditional_fixed_denominator_forward": passed,
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
        or copied.get("role") != "v25053_cran_unconditional_readiness"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not counts_coherent
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
        or copied.get("findings") != []
        or copied.get("contains_project_question_field_value_endpoint_page_prediction_hash_or_credential") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_read") is not False
        or copied.get("model_search_or_evaluator_called_before_receipt") is not False
        or copied.get("authorization") != expected_authorization
        or not contract.sealed(copied, "readiness_payload_sha256")
    ):
        raise RuntimeError("V2.50.53 readiness drifted")
    return copied


def _row_from_prepared(item: Mapping[str, Any]) -> dict[str, Any]:
    parent._synthesize = _synthesize
    parent_row = parent._row_from_prepared(item)
    parent_row = copy.deepcopy(parent_row)
    parent_row["role"] = "v25053_cran_unconditional_task_result"
    return contract.seal(parent_row, "result_payload_sha256")


def _parent_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied["role"] = "v25052_cran_fixed_denominator_task_result"
    return contract.seal(copied, "result_payload_sha256")


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25053_cran_unconditional_task_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.50.53 task result drifted")
    parent.validate_task_row(_parent_task_row(copied))
    return copied


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    return parent.aggregate([_parent_task_row(row) for row in checked])


def mechanism_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    return parent.mechanism_decision(value)


def validate_snapshot_rows(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    parent.ROOT = ROOT
    return parent.validate_snapshot_rows(values)


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
        raise RuntimeError("V2.50.53 effect surface is not pristine")
    if not _lease_inactive():
        raise RuntimeError("V2.50.53 shared lease is active")
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25053_cran_unconditional_forward_v1",
        purpose="unconditional_fixed_denominator_paired_failure_as_zero",
        path=ROOT / contract.LEASE_PATH,
    ):
        if contract.watcher_snapshot() != protocol["protected_watchers"]:
            raise RuntimeError("V2.50.53 protected watcher drifted before effect")
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
            "role": "v25053_cran_unconditional_prediction_freeze",
            "protocol_id": contract.PROTOCOL_ID,
            "task_count": contract.TASK_COUNT,
            "terminal_arm_predictions": contract.TASK_COUNT * len(contract.ARMS),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_hash_vector_sha256": contract.payload_sha256(
                [[row["prediction_sha256"][arm] for arm in contract.ARMS] for row in checked]
            ),
            "readiness_sha256": contract.sha256(ROOT / contract.PARSER_READINESS),
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
            "role": "v25053_cran_unconditional_forward_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "task_count": contract.TASK_COUNT,
            "wall_seconds": round(wall, 6),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_freeze_sha256": freeze_sha256,
            "public_snapshot_sha256": contract.sha256(ROOT / contract.PUBLIC_SNAPSHOT),
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "execution_start_payload_sha256": start["execution_start_payload_sha256"],
            "readiness_sha256": contract.sha256(ROOT / contract.PARSER_READINESS),
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
    expected_keys = {
        "artifact_version", "role", "protocol_id", "created_at_unix",
        "task_count", "wall_seconds", "task_rows_sha256",
        "prediction_freeze_sha256", "public_snapshot_sha256",
        "execution_start_sha256", "execution_start_payload_sha256",
        "readiness_sha256", "aggregate", "mechanism_decision",
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
        set(copied) != expected_keys
        or copied.get("artifact_version") != 1
        or copied.get("role") != "v25053_cran_unconditional_forward_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("task_count") != contract.TASK_COUNT
        or isinstance(copied.get("wall_seconds"), bool)
        or not isinstance(copied.get("wall_seconds"), (int, float))
        or copied["wall_seconds"] < 0
        or copied.get("task_rows_sha256") != contract.sha256(ROOT / contract.TASK_ROWS)
        or copied.get("prediction_freeze_sha256") != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or copied.get("public_snapshot_sha256") != contract.sha256(ROOT / contract.PUBLIC_SNAPSHOT)
        or copied.get("execution_start_sha256") != contract.sha256(ROOT / contract.EXECUTION_START)
        or copied.get("readiness_sha256") != contract.sha256(ROOT / contract.PARSER_READINESS)
        or copied.get("mechanism_decision") != mechanism_decision(copied.get("aggregate") or {})
        or copied.get("all_predictions_terminal_before_public_snapshot_evaluator_or_quality_decision") is not True
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_read") is not False
        or copied.get("authorization") != expected_authorization
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.50.53 forward result drifted")
    return copied


def main() -> None:
    value = run_forward()
    path = (
        contract.PARSER_READINESS
        if value.get("role") == "v25053_cran_unconditional_readiness"
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
