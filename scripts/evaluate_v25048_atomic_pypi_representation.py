#!/usr/bin/env python3
"""Offline post-freeze quality evaluation for V2.50.48."""

from __future__ import annotations

import argparse
import ast
import copy
import fcntl
import json
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25047_pypi_current_record_representation as representation  # noqa: E402
from deepwide_agent import v25048_atomic_pypi_representation_contract as contract  # noqa: E402
from scripts import audit_v25048_persisted_snapshot as persisted  # noqa: E402


METRICS = ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")
TASK_ROW_KEYS = {
    "artifact_version", "role", "protocol_id", "opaque_id",
    "runtime_input_keys", "terminal", "completed", "failure_as_zero",
    "fetch_attempts", "fetch_successes", "http_status",
    "representation_receipt", "evidence_chars", "model_success",
    "model_attempts", "model_usage", "predictions", "prediction_sha256",
    "prediction_changed", "wall_seconds",
    "same_exact_public_response_bytes_for_both_arms",
    "control_is_fixed_raw_json_prefix",
    "candidate_is_identity_bound_current_record_then_same_raw_prefix",
    "same_evidence_chars_prompt_model_output_cap_attempt_count_and_deadline",
    "mapping_gold_category_question_type_split_evaluator_score_reward_read",
    "entropy_or_information_gain_assigns_credit_or_routes",
    "retry_resume_population_replacement_or_selective_rerun",
    "contains_project_question_field_value_endpoint_page_answer_raw_response_or_credential",
    "result_payload_sha256",
}


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.50.48 evaluator requires clean pushed HEAD")


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.48 evaluator expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = True) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not all(isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.50.48 evaluator expected JSONL objects")
    return rows


def _publish(relative: Path, value: Mapping[str, Any]) -> None:
    path = ROOT / relative
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


def _offline_source_safe() -> bool:
    source = contract.ordinary(ROOT, contract.EVALUATOR, tracked=True)
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    forbidden = {"requests", "httpx", "aiohttp", "urllib", "http", "socket"}
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(item.name.split(".", 1)[0] for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".", 1)[0])
    return not imports.intersection(forbidden)


def validate_forward_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected_erratum = {
        "json_object_key_order_is_not_schema_order": True,
        "persisted_snapshot_validated_by_exact_key_sets": True,
        "prediction_snapshot_or_forward_artifact_modified": False,
        "network_model_fetch_or_evaluator_called": False,
        "failed_standard_audit_output_created": False,
    }
    if (
        copied.get("role") != "v25048_atomic_pypi_representation_forward_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("mechanism_decision", {}).get("mechanism_gate_passed") is not True
        or copied.get("persistence_order_erratum") != expected_erratum
        or copied.get("authorization", {}).get(
            "postfreeze_external_evaluator_implementation_and_protocol"
        ) is not True
        or copied.get("authorization", {}).get(
            "deepwidebench_dev64_exact220_or_sota"
        ) is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.48 forward audit drifted")
    return copied


def validate_prediction_rows(values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if len(values) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.48 evaluator prediction denominator drifted")
    output = []
    for index, raw in enumerate(values):
        row = copy.deepcopy(dict(raw))
        predictions = row.get("predictions") or {}
        hashes = row.get("prediction_sha256") or {}
        completed = row.get("completed") is True
        if (
            set(row) != TASK_ROW_KEYS
            or row.get("artifact_version") != 1
            or row.get("role") != "v25048_atomic_pypi_task_result"
            or row.get("protocol_id") != contract.PROTOCOL_ID
            or row.get("opaque_id") != contract.task_vector()[index]["opaque_id"]
            or row.get("runtime_input_keys")
            != ["opaque_id", "question", "same_forward_public_pypi_bytes"]
            or row.get("terminal") is not True
            or row.get("failure_as_zero") is completed
            or set(predictions) != set(contract.ARMS)
            or set(hashes) != set(contract.ARMS)
            or any(
                not isinstance(predictions[arm], str)
                or not predictions[arm]
                or hashes[arm] != contract.payload_sha256(predictions[arm])
                for arm in contract.ARMS
            )
            or row.get("prediction_changed") is not (
                predictions[contract.CONTROL_ARM] != predictions[contract.CANDIDATE_ARM]
            )
            or any(
                row.get(name) is not False
                for name in (
                    "mapping_gold_category_question_type_split_evaluator_score_reward_read",
                    "entropy_or_information_gain_assigns_credit_or_routes",
                    "retry_resume_population_replacement_or_selective_rerun",
                    "contains_project_question_field_value_endpoint_page_answer_raw_response_or_credential",
                )
            )
            or not contract.sealed(row, "result_payload_sha256")
        ):
            raise RuntimeError("V2.50.48 evaluator prediction row drifted")
        output.append(row)
    return output


def build_evaluator_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    audit = validate_forward_audit(_read(contract.FORWARD_AUDIT, tracked=True))
    forward = _read(contract.FORWARD_RESULT, tracked=True)
    rows = validate_prediction_rows(_read_jsonl(contract.TASK_ROWS, tracked=True))
    snapshots = persisted.validate_rows(
        _read_jsonl(contract.PUBLIC_SNAPSHOT, tracked=True)
    )
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT)
    ):
        raise RuntimeError("V2.50.48 evaluator effect surface is not pristine")
    if (
        len(rows) != contract.TASK_COUNT
        or len(snapshots) != contract.TASK_COUNT
        or not _offline_source_safe()
        or audit["forward_result_sha256"] != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or forward.get("task_rows_sha256") != contract.sha256(ROOT / contract.TASK_ROWS)
        or forward.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or forward.get("public_snapshot_sha256")
        != contract.sha256(ROOT / contract.PUBLIC_SNAPSHOT)
    ):
        raise RuntimeError("V2.50.48 evaluator prerequisites drifted")
    value = {
        "artifact_version": 1,
        "role": "v25048_atomic_pypi_evaluator_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "public_snapshot_sha256": contract.sha256(ROOT / contract.PUBLIC_SNAPSHOT),
        "evaluator_source_sha256": contract.sha256(ROOT / contract.EVALUATOR),
        "evaluator_test_sha256": contract.sha256(ROOT / contract.EVALUATOR_TEST),
        "gold_rule": {
            "frozen_postprediction_public_snapshot_only": True,
            "no_network_refetch_model_or_search": True,
            "exact_identity_version_date_requires_python_record": True,
            "fixed_denominator_failure_as_zero": True,
        },
        "quality_rule": contract.gates()["quality"],
        "source_policy": {
            "prediction_freeze_and_forward_audit_precede_evaluator": True,
            "public_snapshot_bound_to_prediction_freeze": True,
            "mapping_benchmark_label_score_or_reward_read": False,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "authorization": {
            "one_offline_postfreeze_evaluation": True,
            "network_refetch_model_search_or_api": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "protocol_payload_sha256")


def validate_evaluator_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected_authorization = {
        "one_offline_postfreeze_evaluation": True,
        "network_refetch_model_search_or_api": False,
        "deepwidebench_dev64_exact220_or_sota": False,
        "retry_or_selective_revaluation": False,
    }
    if (
        copied.get("role") != "v25048_atomic_pypi_evaluator_preregistration"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("parent_protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or copied.get("forward_result_sha256")
        != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or copied.get("forward_audit_sha256")
        != contract.sha256(ROOT / contract.FORWARD_AUDIT)
        or copied.get("task_rows_sha256") != contract.sha256(ROOT / contract.TASK_ROWS)
        or copied.get("prediction_freeze_sha256")
        != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or copied.get("public_snapshot_sha256")
        != contract.sha256(ROOT / contract.PUBLIC_SNAPSHOT)
        or copied.get("evaluator_source_sha256") != contract.sha256(ROOT / contract.EVALUATOR)
        or copied.get("evaluator_test_sha256")
        != contract.sha256(ROOT / contract.EVALUATOR_TEST)
        or copied.get("quality_rule") != contract.gates()["quality"]
        or copied.get("authorization") != expected_authorization
        or not contract.sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.50.48 evaluator protocol drifted")
    return copied


def _normalize(value: object) -> str:
    return " ".join(str(value).split()).casefold()


def _normalize_python(value: object) -> str:
    return re.sub(r"\s+", "", str(value)).casefold()


def _matrix(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [
        line.strip()
        for line in str(text).replace("\r\n", "\n").splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if len(lines) < 3:
        return [], []
    cells = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
    header = cells[0]
    separator = cells[1]
    if len(separator) != len(header) or any(
        re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) is None
        for cell in separator
    ):
        return [], []
    return header, [row for row in cells[2:] if len(row) == len(header)]


def evaluate_prediction(prediction: str, gold: Mapping[str, str]) -> dict[str, float | int]:
    columns, rows = _matrix(prediction)
    exact_columns = columns == list(contract.COLUMNS)
    if not exact_columns:
        rows = []
    expected = representation.normalize_project(gold["Package"])
    matching = [
        row for row in rows
        if representation.normalize_project(row[0]) == expected
    ]
    entity_recall = float(bool(matching))
    row_precision = (1.0 / len(rows)) if matching and rows else 0.0
    row_f1 = (
        2 * row_precision * entity_recall / (row_precision + entity_recall)
        if row_precision + entity_recall
        else 0.0
    )
    correct = 0
    if len(matching) == 1:
        row = matching[0]
        correct += int(_normalize(row[1]) == _normalize(gold[contract.COLUMNS[1]]))
        correct += int(_normalize(row[2]) == _normalize(gold[contract.COLUMNS[2]]))
        correct += int(
            _normalize_python(row[3]) == _normalize_python(gold[contract.COLUMNS[3]])
        )
    predicted_items = len(rows) * 3
    item_precision = correct / predicted_items if predicted_items else 0.0
    item_recall = correct / 3
    item_f1 = (
        2 * item_precision * item_recall / (item_precision + item_recall)
        if item_precision + item_recall
        else 0.0
    )
    column_f1 = 1.0 if exact_columns else 0.0
    exact = int(exact_columns and len(rows) == 1 and len(matching) == 1 and correct == 3)
    composite = (entity_recall + row_f1 + item_f1 + column_f1) / 4
    return {
        "exact_table_success": exact,
        "entity_recall": entity_recall,
        "row_f1": row_f1,
        "item_f1": item_f1,
        "column_f1": column_f1,
        "composite": composite,
    }


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]],
    snapshots: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    checked_rows = validate_prediction_rows(rows)
    checked_snapshots = persisted.validate_rows(list(snapshots))
    gold = {str(row["opaque_id"]): dict(row["record"]) for row in checked_snapshots}
    if len(gold) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.48 evaluator gold identity drifted")
    per_arm = {arm: [] for arm in contract.ARMS}
    seen: set[str] = set()
    for row in checked_rows:
        opaque_id = str(row["opaque_id"])
        if opaque_id in seen or opaque_id not in gold:
            raise RuntimeError("V2.50.48 evaluator prediction identity drifted")
        seen.add(opaque_id)
        for arm in contract.ARMS:
            per_arm[arm].append(
                evaluate_prediction(str(row["predictions"][arm]), gold[opaque_id])
            )
    if len(seen) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.48 evaluator denominator drifted")
    arms: dict[str, Any] = {}
    for arm in contract.ARMS:
        arms[arm] = {
            "tasks": contract.TASK_COUNT,
            "evaluator_valid": contract.TASK_COUNT,
            "evaluator_invalid_or_not_run": 0,
            "fallback_tasks": sum(bool(row["failure_as_zero"]) for row in checked_rows),
            "exact_table_successes": sum(
                int(item["exact_table_success"]) for item in per_arm[arm]
            ),
            **{
                metric: sum(float(item[metric]) for item in per_arm[arm])
                / contract.TASK_COUNT
                for metric in METRICS
            },
        }
    delta_keys = (
        "exact_table_successes", *METRICS,
        "evaluator_invalid_or_not_run", "fallback_tasks",
    )
    delta = {
        key: arms[contract.CANDIDATE_ARM][key] - arms[contract.CONTROL_ARM][key]
        for key in delta_keys
    }
    return {
        "arms": arms,
        f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}": delta,
    }


def quality_decision(metrics: Mapping[str, Any], mechanism: Mapping[str, Any]) -> dict[str, Any]:
    arms = metrics.get("arms") or {}
    delta = metrics.get(
        f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}"
    ) or {}
    checks = {
        "mechanism_gate_passed": mechanism.get("mechanism_gate_passed") is True,
        "fixed_denominator_all_valid": all(
            (arms.get(arm) or {}).get("tasks") == contract.TASK_COUNT
            and (arms.get(arm) or {}).get("evaluator_valid") == contract.TASK_COUNT
            for arm in contract.ARMS
        ),
        "candidate_exact_strictly_greater": float(
            delta.get("exact_table_successes", -1)
        ) > 0,
        "entity_nonregression": float(delta.get("entity_recall", -1)) >= 0,
        "row_nonregression": float(delta.get("row_f1", -1)) >= 0,
        "item_nonregression": float(delta.get("item_f1", -1)) >= 0,
        "column_nonregression": float(delta.get("column_f1", -1)) >= 0,
        "composite_nonregression": float(delta.get("composite", -1)) >= 0,
        "evaluator_invalid_nonincrease": float(
            delta.get("evaluator_invalid_or_not_run", 1)
        ) <= 0,
        "fallback_nonincrease": float(delta.get("fallback_tasks", 1)) <= 0,
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "failed_checks": sorted(name for name, ok in checks.items() if not ok),
        "pypi_current_record_representation_quality_gate_go": passed,
        "production_candidate_design_authorized": passed,
        "deepwidebench_exact220_launch_authorized": False,
    }


def run_evaluation() -> dict[str, Any]:
    _clean_pushed()
    evaluator = validate_evaluator_protocol(
        _read(contract.EVALUATOR_PROTOCOL, tracked=True)
    )
    audit = validate_forward_audit(_read(contract.FORWARD_AUDIT, tracked=True))
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (contract.RESULT, contract.POSTAUDIT)
    ):
        raise RuntimeError("V2.50.48 result surface is not pristine")
    rows = _read_jsonl(contract.TASK_ROWS, tracked=True)
    snapshots = _read_jsonl(contract.PUBLIC_SNAPSHOT, tracked=True)
    metrics = evaluate_rows(rows, snapshots)
    decision = quality_decision(metrics, audit["mechanism_decision"])
    value = {
        "artifact_version": 1,
        "role": "v25048_atomic_pypi_representation_quality_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": (
            "pypi_current_record_representation_quality_gate_go"
            if decision["pypi_current_record_representation_quality_gate_go"]
            else "pypi_current_record_representation_quality_gate_no_go"
        ),
        "passed": decision["pypi_current_record_representation_quality_gate_go"],
        "evaluator_protocol_sha256": contract.sha256(ROOT / contract.EVALUATOR_PROTOCOL),
        "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
        "task_rows_sha256": evaluator["task_rows_sha256"],
        "prediction_freeze_sha256": evaluator["prediction_freeze_sha256"],
        "public_snapshot_sha256": evaluator["public_snapshot_sha256"],
        "metrics": metrics,
        "mechanism": audit["mechanism_decision"],
        "decision": decision,
        "fixed_denominator_failure_as_zero": True,
        "network_refetch_model_search_or_api_called": False,
        "claim_scope": {
            "benchmark_external_matched_quality_measured": True,
            "deepwidebench_quality_measured": False,
            "entropy_or_signed_credit_validated": False,
            "leaderboard_or_sota_supported": False,
        },
        "authorization": {
            "production_candidate_design": decision[
                "production_candidate_design_authorized"
            ],
            "deepwidebench_exact220_launch": False,
            "retry_or_selective_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    value = contract.seal(value, "result_payload_sha256")
    _publish(contract.RESULT, value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    decision = quality_decision(
        copied.get("metrics") or {}, copied.get("mechanism") or {}
    )
    if (
        copied.get("role") != "v25048_atomic_pypi_representation_quality_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("decision") != decision
        or copied.get("passed") is not decision[
            "pypi_current_record_representation_quality_gate_go"
        ]
        or copied.get("network_refetch_model_search_or_api_called") is not False
        or copied.get("claim_scope", {}).get("deepwidebench_quality_measured") is not False
        or copied.get("authorization", {}).get("deepwidebench_exact220_launch") is not False
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.50.48 quality result drifted")
    return copied


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    evaluator = validate_evaluator_protocol(
        _read(contract.EVALUATOR_PROTOCOL, tracked=True)
    )
    result = validate_result(_read(contract.RESULT, tracked=True))
    audit = validate_forward_audit(_read(contract.FORWARD_AUDIT, tracked=True))
    rows = _read_jsonl(contract.TASK_ROWS, tracked=True)
    snapshots = _read_jsonl(contract.PUBLIC_SNAPSHOT, tracked=True)
    metrics = evaluate_rows(rows, snapshots)
    decision = quality_decision(metrics, audit["mechanism_decision"])
    checks = {
        "evaluator_protocol_valid": True,
        "result_valid": True,
        "frozen_metrics_recompute_exactly": metrics == result["metrics"],
        "decision_recomputes_exactly": decision == result["decision"],
        "prediction_and_public_snapshot_hashes_bound": result[
            "prediction_freeze_sha256"
        ] == evaluator["prediction_freeze_sha256"]
        and result["public_snapshot_sha256"] == evaluator["public_snapshot_sha256"],
        "fixed_denominator_failure_as_zero": result[
            "fixed_denominator_failure_as_zero"
        ] is True,
        "offline_evaluation_no_network_model_search_or_api": result[
            "network_refetch_model_search_or_api_called"
        ] is False,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == _read(contract.PROTOCOL, tracked=True)["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "no_retry_or_selective_revaluation": result["authorization"][
            "retry_or_selective_revaluation"
        ] is False,
        "no_deepwidebench_launch_leaderboard_or_sota_authority": result[
            "authorization"
        ]["deepwidebench_exact220_launch"] is False
        and result["authorization"]["leaderboard_or_sota"] is False,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    quality_go = not findings and result["passed"] is True
    value = {
        "artifact_version": 1,
        "role": "v25048_atomic_pypi_representation_postresult_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "evaluator_protocol_sha256": contract.sha256(ROOT / contract.EVALUATOR_PROTOCOL),
        "result_sha256": contract.sha256(ROOT / contract.RESULT),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "pypi_current_record_representation_quality_gate_go": quality_go,
        "source_policy": contract.source_policy(),
        "authorization": {
            "production_candidate_design": quality_go,
            "deepwidebench_exact220_launch": False,
            "retry_or_selective_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "evaluate", "postaudit"))
    args = parser.parse_args()
    if args.command == "protocol":
        value = validate_evaluator_protocol(build_evaluator_protocol())
        path = contract.EVALUATOR_PROTOCOL
        _publish(path, value)
    elif args.command == "evaluate":
        value = run_evaluation()
        path = contract.RESULT
    else:
        value = build_postaudit()
        if value["findings"]:
            raise RuntimeError(value["findings"])
        path = contract.POSTAUDIT
        _publish(path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value["role"],
                "status": value.get("status"),
                "passed": value.get("passed"),
                "audit_valid": value.get("audit_valid"),
                "findings": value.get("findings"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
