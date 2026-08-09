#!/usr/bin/env python3
"""Post-freeze audit and one-shot evaluator for V2.49.79."""

from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import json
import os
import re
import sys
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

from deepwide_agent import v24978_pypi_release_file_compactor as compact  # noqa: E402
from deepwide_agent import v24979_atomic_pypi_quality_contract as contract  # noqa: E402
from scripts import run_v24979_atomic_pypi_quality as runner  # noqa: E402


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(ROOT, "rev-parse", "HEAD") != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.49.79 finalizer requires clean pushed HEAD")


def _read(relative: Path, *, tracked: bool = False) -> dict[str, Any]:
    path = ROOT / relative
    if relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"V2.49.79 expected ordinary object: {relative}")
    if tracked:
        contract.ordinary_tracked(ROOT, relative)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.79 expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = False) -> list[dict[str, Any]]:
    path = ROOT / relative
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.49.79 expected ordinary JSONL")
    if tracked:
        contract.ordinary_tracked(ROOT, relative)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not all(isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.49.79 JSONL schema drifted")
    return rows


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    rows = _read_jsonl(contract.TASK_ROWS)
    if (
        copied.get("role") != "v24973_identity_bound_field_forward_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("task_count") != contract.TASK_COUNT
        or copied.get("task_rows_sha256") != contract.sha256(ROOT / contract.TASK_ROWS)
        or copied.get("prediction_freeze_sha256") != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or copied.get("aggregate") != runner.aggregate(rows)
        or copied.get("mechanism_decision") != runner.mechanism_decision(copied.get("aggregate") or {})
        or copied.get("authorization", {}).get("postfreeze_external_evaluator_protocol") is not False
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.49.79 forward result drifted")
    return copied


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    forward = validate_forward_result(_read(contract.FORWARD_RESULT))
    rows = [runner.validate_task_row(row) for row in _read_jsonl(contract.TASK_ROWS)]
    aggregate = runner.aggregate(rows)
    decision = runner.mechanism_decision(aggregate)
    freeze = _read(contract.PREDICTION_FREEZE)
    readiness = _read(contract.PARSER_READINESS)
    forbidden = {"question", "query", "url", "page", "title", "gold", "category", "question_type", "score", "reward", "credential", "answer"}
    row_keys = {key for row in rows for key in row}
    checks = {
        "protocol_valid": True,
        "forward_result_valid": True,
        "parser_readiness_passed_and_sealed": readiness.get("passed") is True and contract.sealed(readiness, "readiness_payload_sha256"),
        "parser_readiness_hash_bound": forward.get("parser_readiness_sha256") == contract.sha256(ROOT / contract.PARSER_READINESS),
        "exact_task_denominator": len(rows) == contract.TASK_COUNT and len({row["opaque_id"] for row in rows}) == contract.TASK_COUNT,
        "aggregate_recomputes_exactly": aggregate == forward["aggregate"],
        "mechanism_decision_recomputes_exactly": decision == forward["mechanism_decision"],
        "task_rows_contain_no_forbidden_content_keys": not row_keys.intersection(forbidden),
        "prediction_freeze_sealed": contract.sealed(freeze, "freeze_payload_sha256"),
        "prediction_freeze_binds_task_rows": freeze.get("task_rows_sha256") == contract.sha256(ROOT / contract.TASK_ROWS),
        "gold_surface_absent": not (ROOT / contract.GOLD_SNAPSHOT).exists(),
        "protected_watchers_unchanged": contract.watcher_snapshot() == protocol["protected_watchers"],
        "shared_api_lease_released": _lease_inactive(),
        "no_public_exact220_authority": forward["authorization"]["public_exact220_or_sota"] is False,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    audit_valid = not findings
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24979_atomic_pypi_quality_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "parser_readiness_sha256": contract.sha256(ROOT / contract.PARSER_READINESS),
        "checks": checks,
        "mechanism_decision": decision,
        "findings": findings,
        "audit_valid": audit_valid,
        "source_policy": contract.source_policy(),
        "authorization": {
            "postfreeze_external_evaluator_protocol": audit_valid and decision["mechanism_gate_passed"],
            "public_exact220_or_sota": False,
            "retry_resume_selective_rerun_or_revaluation": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_forward_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    authority = copied.get("audit_valid") is True and copied.get("mechanism_decision", {}).get("mechanism_gate_passed") is True
    if (
        copied.get("role") != "v24979_atomic_pypi_quality_forward_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization", {}).get("postfreeze_external_evaluator_protocol") is not authority
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.79 forward audit drifted")
    return copied


def build_evaluator_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    forward = validate_forward_result(_read(contract.FORWARD_RESULT, tracked=True))
    audit = validate_forward_audit(_read(contract.FORWARD_AUDIT, tracked=True))
    if not audit["authorization"]["postfreeze_external_evaluator_protocol"]:
        raise RuntimeError("V2.49.79 mechanism gate withheld evaluator authority")
    if any((ROOT / path).exists() for path in (contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT, contract.GOLD_SNAPSHOT)):
        raise RuntimeError("V2.49.79 evaluator surface is not pristine")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24979_atomic_pypi_quality_evaluator_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
        "prediction_freeze_sha256": forward["prediction_freeze_sha256"],
        "task_rows_sha256": forward["task_rows_sha256"],
        "gold_endpoint_vector_sha256": protocol["population"]["postfreeze_gold_endpoint_vector_sha256"],
        "gold_rule": {
            "same_exact_pypi_extractor_as_candidate": True,
            "one_postfreeze_http_attempt_per_task": True,
            "fixed_denominator_failure_as_zero": True,
        },
        "quality_rule": contract.gates()["quality"],
        "authorization": {"one_postfreeze_external_evaluation": True, "public_exact220_or_sota": False, "retry_or_selective_revaluation": False},
    }
    return contract.seal(value, "protocol_payload_sha256")


def validate_evaluator_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v24979_atomic_pypi_quality_evaluator_preregistration"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("gold_endpoint_vector_sha256") != contract.payload_sha256(contract.gold_endpoint_vector())
        or copied.get("quality_rule") != contract.gates()["quality"]
        or copied.get("authorization", {}).get("one_postfreeze_external_evaluation") is not True
        or not contract.sealed(copied, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.49.79 evaluator protocol drifted")
    return copied


def _normalize_project(value: object) -> str:
    return re.sub(r"[-_.]+", "-", " ".join(str(value).split()).casefold())


def _normalize(value: object) -> str:
    return " ".join(str(value).split()).casefold()


def _normalize_python(value: object) -> str:
    return re.sub(r"\s+", "", str(value)).casefold()


def _matrix(text: str) -> tuple[list[str], list[list[str]]]:
    lines = [line.strip() for line in str(text).splitlines() if line.strip().startswith("|") and line.strip().endswith("|")]
    if len(lines) < 2:
        return [], []
    cells = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines]
    return cells[0], [row for row in cells[2:] if len(row) == len(cells[0])]


def evaluate_prediction(prediction: str, gold: Mapping[str, Any]) -> dict[str, float | int]:
    columns, rows = _matrix(prediction)
    exact_columns = columns == list(contract.COLUMNS)
    if not exact_columns:
        rows = []
    expected = _normalize_project(gold["package"])
    predicted = {_normalize_project(row[0]): row for row in rows if len(row) == len(contract.COLUMNS) and _normalize_project(row[0])}
    entity = int(expected in predicted)
    precision = entity / len(predicted) if predicted else 0.0
    recall = float(entity)
    row_f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    correct = 0
    if expected in predicted:
        row = predicted[expected]
        correct += int(_normalize(row[1]) == _normalize(gold["latest_version"]))
        correct += int(_normalize_python(row[2]) == _normalize_python(gold["requires_python"]))
        correct += int(_normalize(row[3]) == _normalize(gold["release_file_count"]))
        correct += int(_normalize(row[4]) == _normalize(gold["first_upload_date"]))
        correct += int(_normalize(row[5]) == _normalize(gold["largest_file_size_bytes"]))
    predicted_items = len(predicted) * 5
    item_precision = correct / predicted_items if predicted_items else 0.0
    item_recall = correct / 5
    item_f1 = 2 * item_precision * item_recall / (item_precision + item_recall) if item_precision + item_recall else 0.0
    exact = int(exact_columns and len(rows) == 1 and list(predicted) == [expected] and correct == 5)
    column_f1 = 1.0 if exact_columns else 0.0
    return {"exact_table_success": exact, "entity_recall": recall, "row_f1": row_f1, "item_f1": item_f1, "column_f1": column_f1, "composite": (recall + row_f1 + item_f1 + column_f1) / 4}


def _fetch_gold(index: int) -> dict[str, Any]:
    project = contract.PROJECTS[index]
    url = contract.gold_endpoint_vector()[index][0]
    output: dict[str, Any] = {"opaque_id": contract.task_vector()[index]["opaque_id"], "package": project, **{field: "Unknown" for field in compact.FIELD_ORDER}, "response_sha256": "", "http_status": 0, "attempts": 0, "valid": False}
    try:
        output["attempts"] = 1
        response = requests.get(url, headers={"User-Agent": "deepwide-v24979-evaluator/1.0"}, timeout=(5, 60))
        raw = bytes(response.content)
        output["http_status"] = int(response.status_code)
        response.raise_for_status()
        record = compact.extract_record({"url": url, "text": raw.decode(response.encoding or "utf-8", errors="replace")}, project=project)
        output.update(record)
        output["response_sha256"] = hashlib.sha256(raw).hexdigest()
        output["valid"] = True
    except (requests.RequestException, ValueError, TypeError, json.JSONDecodeError):
        pass
    return output


def evaluate_rows(rows: Sequence[Mapping[str, Any]], gold_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    gold = {str(row["opaque_id"]): dict(row) for row in gold_rows}
    if len(gold) != contract.TASK_COUNT:
        raise RuntimeError("V2.49.79 gold denominator drifted")
    metrics = {arm: [] for arm in contract.ARMS}
    zero = {"exact_table_success": 0, "entity_recall": 0.0, "row_f1": 0.0, "item_f1": 0.0, "column_f1": 0.0, "composite": 0.0}
    invalid = 0
    seen: set[str] = set()
    for raw in rows:
        row = runner.validate_task_row(raw)
        opaque = str(row["opaque_id"])
        if opaque in seen or opaque not in gold:
            raise RuntimeError("V2.49.79 prediction/gold identity drifted")
        seen.add(opaque)
        if not gold[opaque]["valid"]:
            invalid += 1
            for arm in contract.ARMS:
                metrics[arm].append(dict(zero))
        else:
            for arm in contract.ARMS:
                metrics[arm].append(evaluate_prediction(str(row["predictions"][arm]), gold[opaque]))
    if len(seen) != contract.TASK_COUNT:
        raise RuntimeError("V2.49.79 evaluation denominator drifted")
    arms: dict[str, Any] = {}
    for arm in contract.ARMS:
        arms[arm] = {
            "tasks": contract.TASK_COUNT,
            "evaluator_valid": contract.TASK_COUNT - invalid,
            "evaluator_invalid_or_not_run": invalid,
            "fallback_tasks": sum(bool(row["failure_as_zero"]) for row in rows),
            "exact_table_successes": sum(int(item["exact_table_success"]) for item in metrics[arm]),
            **{key: sum(float(item[key]) for item in metrics[arm]) / contract.TASK_COUNT for key in ("entity_recall", "row_f1", "item_f1", "column_f1", "composite")},
        }
    delta = {key: arms[contract.CANDIDATE_ARM][key] - arms[contract.CONTROL_ARM][key] for key in ("exact_table_successes", "entity_recall", "row_f1", "item_f1", "column_f1", "composite", "evaluator_invalid_or_not_run", "fallback_tasks")}
    return {"arms": arms, f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}": delta}


def quality_decision(metrics: Mapping[str, Any], mechanism: Mapping[str, Any]) -> dict[str, Any]:
    arms = metrics.get("arms") or {}
    delta = metrics.get(f"{contract.CANDIDATE_ARM}_minus_{contract.CONTROL_ARM}") or {}
    checks = {
        "mechanism_gate_passed": mechanism.get("mechanism_gate_passed") is True,
        "all_gold_tasks_valid": all((arms.get(arm) or {}).get("evaluator_valid") == contract.TASK_COUNT for arm in contract.ARMS),
        "candidate_exact_strictly_greater": float(delta.get("exact_table_successes", -1)) > 0,
        "entity_nonregression": float(delta.get("entity_recall", -1)) >= 0,
        "row_nonregression": float(delta.get("row_f1", -1)) >= 0,
        "item_nonregression": float(delta.get("item_f1", -1)) >= 0,
        "column_nonregression": float(delta.get("column_f1", -1)) >= 0,
        "composite_nonregression": float(delta.get("composite", -1)) >= 0,
        "evaluator_invalid_nonincrease": float(delta.get("evaluator_invalid_or_not_run", 1)) <= 0,
        "fallback_nonincrease": float(delta.get("fallback_tasks", 1)) <= 0,
    }
    passed = all(checks.values())
    return {"checks": checks, "failed_checks": sorted(name for name, ok in checks.items() if not ok), "pypi_release_file_quality_gate_go": passed, "public_exact220_candidate_design_authorized": passed, "public_exact220_launch_authorized": False}


def run_evaluation() -> dict[str, Any]:
    _clean_pushed()
    evaluator = validate_evaluator_protocol(_read(contract.EVALUATOR_PROTOCOL, tracked=True))
    forward = validate_forward_result(_read(contract.FORWARD_RESULT, tracked=True))
    audit = validate_forward_audit(_read(contract.FORWARD_AUDIT, tracked=True))
    if any((ROOT / path).exists() for path in (contract.RESULT, contract.POSTAUDIT, contract.GOLD_SNAPSHOT)):
        raise RuntimeError("V2.49.79 result surface is not pristine")
    rows = _read_jsonl(contract.TASK_ROWS, tracked=True)
    with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
        gold_rows = list(pool.map(_fetch_gold, range(contract.TASK_COUNT)))
    gold_rows.sort(key=lambda row: str(row["opaque_id"]))
    snapshot: dict[str, Any] = {
        "artifact_version": 1, "role": "v24979_postfreeze_pypi_gold_snapshot",
        "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()),
        "prediction_freeze_sha256": forward["prediction_freeze_sha256"],
        "endpoint_vector_sha256": evaluator["gold_endpoint_vector_sha256"],
        "rows": gold_rows, "valid_rows": sum(bool(row["valid"]) for row in gold_rows),
        "attempts": sum(int(row["attempts"]) for row in gold_rows),
        "created_only_after_prediction_freeze_and_pushed_forward_audit": True,
        "retry_or_selective_refetch": False,
    }
    contract.seal(snapshot, "snapshot_payload_sha256")
    _publish(ROOT / contract.GOLD_SNAPSHOT, snapshot)
    metrics = evaluate_rows(rows, gold_rows)
    decision = quality_decision(metrics, audit["mechanism_decision"])
    value: dict[str, Any] = {
        "artifact_version": 1, "role": "v24979_atomic_pypi_quality_result",
        "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()),
        "status": "pypi_release_file_quality_gate_go" if decision["pypi_release_file_quality_gate_go"] else "pypi_release_file_quality_gate_no_go",
        "passed": decision["pypi_release_file_quality_gate_go"],
        "evaluator_protocol_sha256": contract.sha256(ROOT / contract.EVALUATOR_PROTOCOL),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
        "prediction_freeze_sha256": forward["prediction_freeze_sha256"],
        "gold_snapshot_sha256": contract.sha256(ROOT / contract.GOLD_SNAPSHOT),
        "metrics": metrics, "mechanism": audit["mechanism_decision"], "decision": decision,
        "fixed_denominator_failure_as_zero": True,
        "claim_scope": {"benchmark_external_quality_measured": True, "deepwidebench_quality_measured": False, "entropy_or_signed_credit_validated": False, "leaderboard_or_sota_supported": False},
        "authorization": {"public_exact220_candidate_design": decision["public_exact220_candidate_design_authorized"], "public_exact220_launch": False, "retry_or_selective_revaluation": False, "leaderboard_or_sota": False},
    }
    contract.seal(value, "result_payload_sha256")
    _publish(ROOT / contract.RESULT, value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    decision = quality_decision(copied.get("metrics") or {}, copied.get("mechanism") or {})
    if copied.get("role") != "v24979_atomic_pypi_quality_result" or copied.get("protocol_id") != contract.PROTOCOL_ID or copied.get("decision") != decision or copied.get("passed") is not decision["pypi_release_file_quality_gate_go"] or not contract.sealed(copied, "result_payload_sha256"):
        raise RuntimeError("V2.49.79 result drifted")
    return copied


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    result = validate_result(_read(contract.RESULT))
    snapshot = _read(contract.GOLD_SNAPSHOT)
    checks = {
        "result_valid": True,
        "gold_snapshot_sealed": contract.sealed(snapshot, "snapshot_payload_sha256"),
        "gold_snapshot_bound_to_prediction_freeze": snapshot.get("prediction_freeze_sha256") == result["prediction_freeze_sha256"],
        "gold_exactly_one_attempt_per_task": snapshot.get("attempts") == contract.TASK_COUNT,
        "decision_recomputes_exactly": result["decision"] == quality_decision(result["metrics"], result["mechanism"]),
        "fixed_denominator_failure_as_zero": result["fixed_denominator_failure_as_zero"] is True,
        "protected_watchers_unchanged": bool(contract.watcher_snapshot()),
        "shared_api_lease_inactive": _lease_inactive(),
        "no_retry_or_selective_revaluation": result["authorization"]["retry_or_selective_revaluation"] is False,
        "no_public_launch_or_sota_authority": result["authorization"]["public_exact220_launch"] is False and result["authorization"]["leaderboard_or_sota"] is False,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    passed = not findings and result["passed"] is True
    value: dict[str, Any] = {
        "artifact_version": 1, "role": "v24979_atomic_pypi_quality_postresult_audit",
        "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now),
        "result_sha256": contract.sha256(ROOT / contract.RESULT),
        "gold_snapshot_sha256": contract.sha256(ROOT / contract.GOLD_SNAPSHOT),
        "checks": checks, "findings": findings, "audit_valid": not findings,
        "pypi_release_file_quality_gate_go": passed, "source_policy": contract.source_policy(),
        "authorization": {"public_exact220_candidate_design": passed, "public_exact220_launch": False, "retry_or_selective_revaluation": False, "leaderboard_or_sota": False},
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("forward-audit", "evaluator-protocol", "evaluate", "postaudit"))
    args = parser.parse_args()
    if args.command == "forward-audit":
        value = validate_forward_audit(build_forward_audit()); path = contract.FORWARD_AUDIT; _publish(ROOT / path, value)
    elif args.command == "evaluator-protocol":
        value = validate_evaluator_protocol(build_evaluator_protocol()); path = contract.EVALUATOR_PROTOCOL; _publish(ROOT / path, value)
    elif args.command == "evaluate":
        value = run_evaluation(); path = contract.RESULT
    else:
        value = build_postaudit(); path = contract.POSTAUDIT; _publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"], "status": value.get("status"), "passed": value.get("passed")}, sort_keys=True))


if __name__ == "__main__":
    main()
