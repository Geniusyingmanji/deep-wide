#!/usr/bin/env python3
"""Post-freeze paired quality gate for the V2.54.88 IANA-detail intervention.

The twenty shared-parent forwards and both prediction arms were frozen,
audited, committed, and pushed before this evaluator was introduced.  This
module fixes the clue-to-ccTLD vector, obtains exactly one redirect-disabled,
no-retry official IANA Root Zone Database snapshot, and evaluates all forty
frozen predictions once.  Missing truth, malformed truth, or an invalid
prediction scores zero on the fixed denominator.  No prediction retry,
repair, replacement, selection, or revaluation is permitted.  Entropy or
information gain assigns no signed credit.
"""

from __future__ import annotations

import argparse
import ast
import copy
import gzip
import hashlib
import json
import os
import re
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import native_search  # noqa: E402
from deepwide_agent import v24257_score_first_runtime as table_runtime  # noqa: E402
from deepwide_agent import v25488_iana_detail_external_contract as contract  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base_audit  # noqa: E402
from scripts import control_v25488_iana_detail_external as forward_control  # noqa: E402
from scripts import run_v25488_iana_detail_external as forward_runner  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260814"
PROTOCOL_ID = "v25489_v25488_iana_detail_shared_parent_quality_v1"
SOURCE = Path("scripts/evaluate_v25489_iana_detail_quality.py")
TEST = Path("tests/test_evaluate_v25489_iana_detail_quality.py")
BUILD_AUDIT = Path(f"results/v25489_iana_detail_quality_build_audit_v1_{DATE}.json")
PROTOCOL = contract.POSTFREEZE_QUALITY_PROTOCOL
RAW_TRUTH = contract.OUTPUT_ROOT / "postfreeze_iana_root_v25489.html.gz"
TRUTH = contract.OUTPUT_ROOT / "postfreeze_iana_truth_v25489.json"
RESULT = contract.QUALITY_RESULT
AUDIT = contract.QUALITY_AUDIT

URL = "https://www.iana.org/domains/root/db"
USER_AGENT = "DeepWideResearch/1.0 (+postfreeze IANA quality evaluator)"
CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 60.0
MAXIMUM_RESPONSE_BYTES = 3_000_000
PARSER_ID = "iana_root_table_exact_three_cell_v1"
EXPECTED_TESTS = 8
METRICS = (
    "entity_coverage",
    "row_exact",
    "cell_accuracy",
    "column_accuracy",
    "quality_composite",
)
BASE_ARM = contract.runtime.BASE_ARM
CANDIDATE_ARM = contract.runtime.CANDIDATE_ARM
ARMS = (BASE_ARM, CANDIDATE_ARM)

# Evaluator-only mapping fixed after prediction freeze and pushed forward audit.
# Order is exactly the public V2.54.86 clue order; no forward dependency imports
# this module or receives this vector.
TLD_VECTOR = (
    ".gm",
    ".ge",
    ".de",
    ".gh",
    ".gr",
    ".gd",
    ".gt",
    ".gn",
    ".gw",
    ".gy",
    ".ht",
    ".hn",
    ".hu",
    ".id",
    ".ie",
    ".il",
    ".ci",
    ".ls",
    ".lr",
    ".ly",
)

FORWARD_AUDIT_SHA256 = (
    "a416ab2e384eb8d07463bd290737d23a5a2fb703210317bde9acb9296d02d84b"
)
FORWARD_RESULT_SHA256 = (
    "acc18c14b95ee0b81670677fa5670d6d28445ffb0bba2437dbe21233967c0943"
)
TASK_ROWS_SHA256 = (
    "1ae31a719259c05140966f92f465d3b8c1475bfdaae9143c6c5fd5628c64aad0"
)
PREDICTION_FREEZE_SHA256 = (
    "0932e0b53d58306e389d944d26465f6a33f57080a1b71d36b37f50c78a3d5373"
)
FORWARD_RUNNER_SHA256 = (
    "f59bf32e74e2ce754cf5c3a21a8801166b234321295dd1d8b457dba81438c402"
)
FORWARD_CONTRACT_SHA256 = (
    "6441ad33f3db60044037d810ac90f40d03bd5a2bf99c2b8ce40d980383d8d8b5"
)


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
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


def _publish_bytes(path: Path, value: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    value = json.loads(
        contract.ordinary(ROOT, relative, tracked=tracked).read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.54.89 expected a JSON object")
    return value


def _read_rows(*, tracked: bool = True) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, contract.TASK_ROWS, tracked=tracked)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.54.89 expected JSONL objects")
    return rows


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.54.89 requires a clean pushed HEAD")
    return head, target


def _future_pristine(paths: Sequence[Path]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _mapping() -> tuple[str, ...]:
    if (
        len(TLD_VECTOR) != contract.TASK_COUNT
        or len(set(TLD_VECTOR)) != contract.TASK_COUNT
        or any(re.fullmatch(r"\.[a-z]{2}", value) is None for value in TLD_VECTOR)
    ):
        raise RuntimeError("V2.54.89 evaluator mapping drifted")
    return TLD_VECTOR


def _canonical(value: object) -> str:
    return " ".join(str(value or "").split()).casefold()


def parse_iana_page(raw_html: str) -> dict[str, dict[str, str]]:
    if not isinstance(raw_html, str) or not raw_html:
        raise ValueError("V2.54.89 IANA HTML is empty")
    _title, text = native_search.html_to_text(raw_html)
    output: dict[str, dict[str, str]] = {}
    wanted = set(_mapping())
    for line in text.splitlines():
        cells = [" ".join(value.split()) for value in line.split(" | ")]
        if len(cells) != len(contract.COLUMNS):
            continue
        domain, kind, manager = cells
        folded = domain.casefold()
        if folded not in wanted or not kind or not manager:
            continue
        row = {"Domain": domain, "Type": kind, "TLD Manager": manager}
        if folded in output and output[folded] != row:
            raise ValueError("V2.54.89 IANA row conflict")
        output[folded] = row
    if set(output) != wanted:
        raise ValueError("V2.54.89 IANA truth cohort is incomplete")
    return {identity: output[identity] for identity in _mapping()}


def _matrix(prediction: str) -> tuple[list[str], list[list[str]], bool]:
    canonical, _errors = table_runtime.extract_valid_markdown_table(
        prediction, contract.COLUMNS
    )
    if canonical is None:
        return [], [], False
    lines = [
        line.strip()
        for line in canonical.splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    cells = [
        [cell.strip() for cell in line.strip("|").split("|")] for line in lines
    ]
    if len(cells) != 3 or cells[0] != list(contract.COLUMNS):
        return [], [], False
    rows = [row for row in cells[2:] if len(row) == len(contract.COLUMNS)]
    valid = len(rows) == 1 and re.fullmatch(r"\.[A-Za-z]{2}", rows[0][0]) is not None
    return cells[0], rows, valid


def evaluate_prediction(
    prediction: str,
    expected_identity: str,
    truth: Mapping[str, Mapping[str, str]],
) -> dict[str, float | int | bool]:
    expected = str(expected_identity).casefold()
    record = truth.get(expected)
    truth_complete = (
        isinstance(record, Mapping)
        and set(record) == set(contract.COLUMNS)
        and _canonical(record["Domain"]) == expected
        and all(_canonical(record[column]) for column in contract.COLUMNS[1:])
    )
    _columns, rows, structural_valid = _matrix(prediction)
    if not truth_complete or not structural_valid:
        return {
            "valid": False,
            "exact_table_success": 0,
            "entity_coverage": 0.0,
            "row_exact": 0.0,
            "cell_accuracy": 0.0,
            "column_accuracy": 0.0,
            "quality_composite": 0.0,
        }
    row = rows[0]
    entity = int(_canonical(row[0]) == expected)
    field_hits = [
        int(entity == 1 and _canonical(row[index]) == _canonical(record[column]))
        for index, column in enumerate(contract.COLUMNS[1:], 1)
    ]
    cell_accuracy = sum(field_hits) / 2
    row_exact = float(entity == 1 and all(field_hits))
    column_accuracy = (entity + sum(field_hits)) / 3
    composite = (float(entity) + row_exact + cell_accuracy + column_accuracy) / 4
    exact = int(row_exact == 1.0)
    return {
        "valid": True,
        "exact_table_success": exact,
        "entity_coverage": float(entity),
        "row_exact": row_exact,
        "cell_accuracy": cell_accuracy,
        "column_accuracy": column_accuracy,
        "quality_composite": composite,
    }


def _delta(candidate: Mapping[str, Any], base: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "exact_table_successes": candidate["exact_table_successes"]
        - base["exact_table_successes"],
        "valid_tasks": candidate["valid_tasks"] - base["valid_tasks"],
        "invalid_tasks": candidate["invalid_tasks"] - base["invalid_tasks"],
        "fallback_tasks": candidate["fallback_tasks"] - base["fallback_tasks"],
        **{name: candidate[name] - base[name] for name in METRICS},
    }


def _disposition(
    by_task: Mapping[int, Mapping[str, Mapping[str, Any]]], metric: str
) -> dict[str, int]:
    output = {"candidate_win": 0, "tie": 0, "candidate_loss": 0}
    for index in range(contract.TASK_COUNT):
        left = float(by_task[index][BASE_ARM][metric])
        right = float(by_task[index][CANDIDATE_ARM][metric])
        delta = right - left
        key = (
            "candidate_win"
            if delta > 1e-12
            else "candidate_loss"
            if delta < -1e-12
            else "tie"
        )
        output[key] += 1
    return output


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]], truth: Mapping[str, Mapping[str, str]]
) -> dict[str, Any]:
    checked = [forward_runner.validate_task_row(row) for row in rows]
    tasks = contract.task_vector()
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked]
        != [task["opaque_id"] for task in tasks]
        or [row["task_index"] for row in checked] != list(range(contract.TASK_COUNT))
    ):
        raise ValueError("V2.54.89 frozen task denominator drifted")
    mapping = _mapping()
    values: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    by_task: dict[int, dict[str, dict[str, Any]]] = {}
    for row in checked:
        index = int(row["task_index"])
        by_task[index] = {}
        for arm in ARMS:
            metric = evaluate_prediction(row["predictions"][arm], mapping[index], truth)
            values[arm].append(metric)
            by_task[index][arm] = metric
    aggregate: dict[str, Any] = {}
    for arm in ARMS:
        metrics = values[arm]
        if len(metrics) != contract.TASK_COUNT:
            raise ValueError("V2.54.89 arm denominator drifted")
        aggregate[arm] = {
            "tasks": contract.TASK_COUNT,
            "valid_tasks": sum(metric["valid"] is True for metric in metrics),
            "invalid_tasks": sum(metric["valid"] is False for metric in metrics),
            "fallback_tasks": sum(
                row["prediction_kind"] == "fallback" for row in checked
            ),
            "exact_table_successes": sum(
                int(metric["exact_table_success"]) for metric in metrics
            ),
            **{
                name: sum(float(metric[name]) for metric in metrics)
                / contract.TASK_COUNT
                for name in METRICS
            },
        }
    return {
        "evaluation_count": contract.TASK_COUNT * len(ARMS),
        "truth_record_count": len(truth),
        "truth_complete_tasks": sum(identity in truth for identity in mapping),
        "arms": aggregate,
        "candidate_minus_base": _delta(
            aggregate[CANDIDATE_ARM], aggregate[BASE_ARM]
        ),
        "candidate_vs_base_exact_disposition": _disposition(
            by_task, "exact_table_success"
        ),
        "candidate_vs_base_composite_disposition": _disposition(
            by_task, "quality_composite"
        ),
        "shared_parent_treatment_comparison": True,
    }


def quality_decision(metrics: Mapping[str, Any]) -> dict[str, Any]:
    arms = metrics.get("arms") or {}
    base = arms.get(BASE_ARM) or {}
    candidate = arms.get(CANDIDATE_ARM) or {}
    delta = metrics.get("candidate_minus_base") or {}
    checks = {
        "fixed_prediction_denominator": metrics.get("evaluation_count")
        == contract.TASK_COUNT * len(ARMS)
        and base.get("tasks") == contract.TASK_COUNT
        and candidate.get("tasks") == contract.TASK_COUNT,
        "truth_valid_for_all_fixed_tasks": metrics.get("truth_complete_tasks")
        == contract.TASK_COUNT
        and metrics.get("truth_record_count") == contract.TASK_COUNT,
        "strict_whole_table_exact_gain": delta.get("exact_table_successes", 0) > 0,
        "entity_coverage_nonregression": delta.get("entity_coverage", -1) >= 0,
        "row_exact_nonregression": delta.get("row_exact", -1) >= 0,
        "cell_accuracy_nonregression": delta.get("cell_accuracy", -1) >= 0,
        "column_accuracy_nonregression": delta.get("column_accuracy", -1) >= 0,
        "quality_composite_nonregression": delta.get("quality_composite", -1) >= 0,
        "valid_task_nonregression": delta.get("valid_tasks", -1) >= 0,
        "invalid_task_nonincrease": delta.get("invalid_tasks", 1) <= 0,
        "fallback_nonincrease": delta.get("fallback_tasks", 1) <= 0,
        "shared_parent_treatment_comparison": metrics.get(
            "shared_parent_treatment_comparison"
        )
        is True,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "failed_checks": failed,
        "quality_gate_passed": not failed,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
    }


def parser_contract() -> dict[str, Any]:
    return {
        "parser_id": PARSER_ID,
        "official_table_rows_exactly_three_cells": True,
        "exact_frozen_tld_vector_only": True,
        "duplicate_conflict_or_missing_identity_fails_closed": True,
        "no_country_tld_inference_from_predictions": True,
    }


def scoring_contract() -> dict[str, Any]:
    return {
        "fixed_task_denominator": contract.TASK_COUNT,
        "fixed_prediction_count": contract.TASK_COUNT * len(ARMS),
        "columns": list(contract.COLUMNS),
        "exactly_one_prediction_row_required": True,
        "missing_truth_malformed_truth_or_invalid_prediction_scores_zero": True,
        "metrics": list(METRICS),
        "candidate_whole_table_exact_strictly_greater_than_base": True,
        "all_soft_metrics_nonregression": True,
        "candidate_invalid_and_fallback_nonincrease": True,
        "same_truth_snapshot_and_scorer_for_both_arms": True,
    }


def truth_fetch_contract() -> dict[str, Any]:
    return {
        "url": URL,
        "method": "GET",
        "attempt_count": 1,
        "allow_redirects": False,
        "connect_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
        "read_timeout_seconds": READ_TIMEOUT_SECONDS,
        "maximum_response_bytes": MAXIMUM_RESPONSE_BYTES,
        "retry_refetch_or_replacement": False,
    }


def _source_network_contract(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "requests"
        and node.func.attr == "get"
    ]
    return len(calls) == 1 and "allow_redirects=False" in path.read_text(
        encoding="utf-8"
    )


def _forward_barrier() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    audit = _read(contract.FORWARD_AUDIT)
    forward = forward_runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    rows = [forward_runner.validate_task_row(row) for row in _read_rows()]
    freeze = _read(contract.PREDICTION_FREEZE)
    if (
        contract.sha256(ROOT / contract.FORWARD_AUDIT) != FORWARD_AUDIT_SHA256
        or contract.sha256(ROOT / contract.FORWARD_RESULT) != FORWARD_RESULT_SHA256
        or contract.sha256(ROOT / contract.TASK_ROWS) != TASK_ROWS_SHA256
        or contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        != PREDICTION_FREEZE_SHA256
        or contract.sha256(ROOT / contract.RUNNER) != FORWARD_RUNNER_SHA256
        or contract.sha256(ROOT / contract.CONTRACT) != FORWARD_CONTRACT_SHA256
        or audit.get("role") != "v25488_iana_detail_external_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("mechanism_decision", {}).get("mechanism_gate_passed")
        is not True
        or audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is not True
        or audit.get("authorization", {}).get("deepwidebench_forward_or_evaluator")
        is not False
        or audit.get("forward_result_sha256") != FORWARD_RESULT_SHA256
        or audit.get("task_rows_sha256") != TASK_ROWS_SHA256
        or audit.get("prediction_freeze_sha256") != PREDICTION_FREEZE_SHA256
        or not contract.sealed(audit, "audit_payload_sha256")
        or forward.get("task_rows_sha256") != TASK_ROWS_SHA256
        or forward.get("prediction_freeze_sha256") != PREDICTION_FREEZE_SHA256
        or len(rows) != contract.TASK_COUNT
        or [row["opaque_id"] for row in rows]
        != [task["opaque_id"] for task in contract.task_vector()]
        or freeze.get("task_count") != contract.TASK_COUNT
        or freeze.get("all_predictions_terminal_before_truth_evaluator_or_quality_decision")
        is not True
        or not contract.sealed(freeze, "freeze_payload_sha256")
    ):
        raise RuntimeError("V2.54.89 forward barrier drifted")
    return audit, rows


def _test() -> dict[str, Any]:
    return base_audit._test("test_evaluate_v25489_iana_detail_quality.py", EXPECTED_TESTS)


def build_audit(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    head, target = _clean_pushed() if require_clean else ("build-only", "build-only")
    forward_audit, rows = _forward_barrier()
    test = _test()
    tracked = all(
        not require_clean
        or contract.git(ROOT, "ls-files", "--error-unmatch", str(path))
        for path in (SOURCE, TEST)
    )
    closure = {str(path) for path in contract.forward_dependency_closure(ROOT)}
    source = contract.ordinary(ROOT, SOURCE, tracked=require_clean)
    test_path = contract.ordinary(ROOT, TEST, tracked=require_clean)
    checks = {
        "git_clean_head_equals_target_main": head == target,
        "source_and_test_tracked": tracked,
        "pushed_forward_audit_authorizes_quality": bool(forward_audit),
        "fixed_forward_hashes_exact": (
            contract.sha256(ROOT / contract.FORWARD_AUDIT) == FORWARD_AUDIT_SHA256
            and contract.sha256(ROOT / contract.FORWARD_RESULT)
            == FORWARD_RESULT_SHA256
            and contract.sha256(ROOT / contract.TASK_ROWS) == TASK_ROWS_SHA256
            and contract.sha256(ROOT / contract.PREDICTION_FREEZE)
            == PREDICTION_FREEZE_SHA256
        ),
        "all_frozen_rows_validate_before_truth": len(rows) == contract.TASK_COUNT,
        "focused_quality_tests_exact8": test["passed"],
        "evaluator_source_absent_from_forward_closure": str(SOURCE) not in closure,
        "truth_mapping_and_network_capability_absent_from_forward_closure": all(
            "evaluate_v25489" not in path for path in closure
        ),
        "single_no_redirect_requests_get_contract": _source_network_contract(source),
        "mapping_exact_unique_twenty": len(_mapping()) == contract.TASK_COUNT,
        "future_quality_surfaces_pristine": _future_pristine(
            (BUILD_AUDIT, PROTOCOL, RAW_TRUTH, TRUTH, RESULT, AUDIT)
        ),
        "credential_literal_zero": not base_audit.SECRET.search(
            source.read_text(encoding="utf-8")
        )
        and not base_audit.SECRET.search(test_path.read_text(encoding="utf-8")),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == forward_audit["protected_watchers"]
        if "protected_watchers" in forward_audit
        else contract.watcher_snapshot()
        == _read(contract.PROTOCOL)["protected_watchers"],
        "shared_api_lease_inactive": forward_control._lease_inactive(),
        "conflicting_forward_or_evaluator_processes_absent": not forward_control._active_conflicts(),
        "no_network_model_search_fetch_or_evaluation_performed_by_build_audit": True,
        "entropy_information_gain_signed_credit_zero": forward_audit["aggregate"][
            "positive_signed_credit_count"
        ]
        == 0,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25489_iana_detail_quality_build_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "evaluator_source_sha256": contract.sha256(source),
        "evaluator_test_sha256": contract.sha256(test_path),
        "forward_audit_sha256": FORWARD_AUDIT_SHA256,
        "forward_result_sha256": FORWARD_RESULT_SHA256,
        "task_rows_sha256": TASK_ROWS_SHA256,
        "prediction_freeze_sha256": PREDICTION_FREEZE_SHA256,
        "mapping_vector_sha256": contract.payload_sha256(_mapping()),
        "test": test,
        "parser": parser_contract(),
        "scoring": scoring_contract(),
        "truth_fetch": truth_fetch_contract(),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "network_model_search_fetch_or_evaluation_performed": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "postfreeze_quality_protocol_generation": not findings,
            "one_truth_fetch_or_quality_evaluation": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
            "retry_refetch_revaluation_or_selective_replacement": False,
        },
    }
    return validate_build_audit(contract.seal(value, "audit_payload_sha256"))


def validate_build_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    valid = copied.get("audit_valid") is True
    checks = copied.get("checks") or {}
    if (
        copied.get("role") != "v25489_iana_detail_quality_build_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("findings")
        != sorted(name for name, passed in checks.items() if not passed)
        or valid is not (copied.get("findings") == [])
        or copied.get("test", {}).get("expected") != EXPECTED_TESTS
        or copied.get("test", {}).get("observed") != EXPECTED_TESTS
        or copied.get("test", {}).get("passed") is not True
        or copied.get("mapping_vector_sha256")
        != contract.payload_sha256(_mapping())
        or copied.get("parser") != parser_contract()
        or copied.get("scoring") != scoring_contract()
        or copied.get("truth_fetch") != truth_fetch_contract()
        or copied.get("network_model_search_fetch_or_evaluation_performed")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "postfreeze_quality_protocol_generation": valid,
            "one_truth_fetch_or_quality_evaluation": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
            "retry_refetch_revaluation_or_selective_replacement": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.54.89 quality build audit drifted")
    return copied


def preregister(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    build = validate_build_audit(_read(BUILD_AUDIT))
    forward_audit, _rows = _forward_barrier()
    if not _future_pristine((PROTOCOL, RAW_TRUTH, TRUTH, RESULT, AUDIT)):
        raise RuntimeError("V2.54.89 protocol surface is not pristine")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25489_iana_detail_quality_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "target_main": target,
        "quality_build_audit_sha256": contract.sha256(ROOT / BUILD_AUDIT),
        "evaluator_source_sha256": build["evaluator_source_sha256"],
        "evaluator_test_sha256": build["evaluator_test_sha256"],
        "forward_audit_sha256": FORWARD_AUDIT_SHA256,
        "forward_result_sha256": FORWARD_RESULT_SHA256,
        "task_rows_sha256": TASK_ROWS_SHA256,
        "prediction_freeze_sha256": PREDICTION_FREEZE_SHA256,
        "frozen_task_count": contract.TASK_COUNT,
        "fixed_prediction_count": contract.TASK_COUNT * len(ARMS),
        "fixed_truth_identity_count": contract.TASK_COUNT,
        "mapping_vector_sha256": contract.payload_sha256(_mapping()),
        "public_clue_vector_sha256": contract.population.EXPECTED_CLUE_VECTOR_SHA256,
        "official_truth_url": URL,
        "truth_fetch": truth_fetch_contract(),
        "parser": parser_contract(),
        "scoring": scoring_contract(),
        "quality_gate": contract.quality_gate(),
        "prediction_freeze_and_pushed_forward_audit_precede_truth_open": True,
        "base_and_candidate_share_one_v25472_parent_forward": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_truth_fetch_and_fixed_evaluation": True,
            "retry_refetch_revaluation_or_selective_replacement": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
        },
    }
    if forward_audit["authorization"]["postfreeze_quality_protocol"] is not True:
        raise RuntimeError("V2.54.89 forward audit does not authorize quality")
    return validate_protocol(contract.seal(value, "protocol_payload_sha256"))


def validate_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25489_iana_detail_quality_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("git_head") != copied.get("target_main")
        or copied.get("quality_build_audit_sha256")
        != contract.sha256(ROOT / BUILD_AUDIT)
        or copied.get("evaluator_source_sha256") != contract.sha256(ROOT / SOURCE)
        or copied.get("evaluator_test_sha256") != contract.sha256(ROOT / TEST)
        or copied.get("forward_audit_sha256") != FORWARD_AUDIT_SHA256
        or copied.get("forward_result_sha256") != FORWARD_RESULT_SHA256
        or copied.get("task_rows_sha256") != TASK_ROWS_SHA256
        or copied.get("prediction_freeze_sha256") != PREDICTION_FREEZE_SHA256
        or copied.get("frozen_task_count") != contract.TASK_COUNT
        or copied.get("fixed_prediction_count") != contract.TASK_COUNT * len(ARMS)
        or copied.get("fixed_truth_identity_count") != contract.TASK_COUNT
        or copied.get("mapping_vector_sha256")
        != contract.payload_sha256(_mapping())
        or copied.get("public_clue_vector_sha256")
        != contract.population.EXPECTED_CLUE_VECTOR_SHA256
        or copied.get("official_truth_url") != URL
        or copied.get("truth_fetch") != truth_fetch_contract()
        or copied.get("parser") != parser_contract()
        or copied.get("scoring") != scoring_contract()
        or copied.get("quality_gate") != contract.quality_gate()
        or copied.get("prediction_freeze_and_pushed_forward_audit_precede_truth_open")
        is not True
        or copied.get("base_and_candidate_share_one_v25472_parent_forward")
        is not True
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "one_truth_fetch_and_fixed_evaluation": True,
            "retry_refetch_revaluation_or_selective_replacement": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "protocol_payload_sha256")
    ):
        raise ValueError("V2.54.89 quality protocol drifted")
    return copied


def _fetch_once() -> tuple[bytes, int, str | None, str]:
    try:
        response = requests.get(
            URL,
            headers={"User-Agent": USER_AGENT},
            timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
            allow_redirects=False,
        )
        raw = bytes(response.content)
        status = int(response.status_code)
        encoding = str(response.encoding or "utf-8")
        if status != 200 or not raw or len(raw) > MAXIMUM_RESPONSE_BYTES:
            return raw[:MAXIMUM_RESPONSE_BYTES], status, "InvalidResponse", encoding
        return raw, status, None, encoding
    except requests.RequestException as exc:
        return b"", 0, type(exc).__name__[:128] or "RequestException", "utf-8"


def _truth_artifact(
    raw: bytes,
    status: int,
    failure: str | None,
    encoding: str,
    records: Mapping[str, Mapping[str, str]],
    *,
    now: int,
) -> tuple[bytes, dict[str, Any]]:
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25489_postfreeze_official_iana_truth",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "official_truth_url": URL,
        "attempt_count": 1,
        "http_status": int(status),
        "response_encoding": str(encoding),
        "fetch_or_parse_failure_type": failure,
        "raw_response_bytes": len(raw),
        "raw_response_sha256": hashlib.sha256(raw).hexdigest(),
        "compressed_snapshot_sha256": hashlib.sha256(compressed).hexdigest(),
        "parser_id": PARSER_ID,
        "mapping_vector_sha256": contract.payload_sha256(_mapping()),
        "expected_identity_count": contract.TASK_COUNT,
        "valid_record_count": len(records),
        "records": dict(records),
        "one_attempt_no_redirect_retry_refetch_or_replacement": True,
        "same_snapshot_used_for_both_prediction_arms": True,
        "prediction_freeze_and_forward_audit_preexisted": True,
    }
    return compressed, contract.seal(value, "truth_payload_sha256")


def validate_truth(value: Mapping[str, Any], compressed: bytes) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    try:
        raw = gzip.decompress(compressed)
    except (OSError, EOFError) as exc:
        raise ValueError("V2.54.89 compressed truth snapshot drifted") from exc
    records = copied.get("records")
    failure = copied.get("fetch_or_parse_failure_type")
    if (
        copied.get("role") != "v25489_postfreeze_official_iana_truth"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("official_truth_url") != URL
        or copied.get("attempt_count") != 1
        or copied.get("raw_response_bytes") != len(raw)
        or copied.get("raw_response_sha256") != hashlib.sha256(raw).hexdigest()
        or copied.get("compressed_snapshot_sha256")
        != hashlib.sha256(compressed).hexdigest()
        or copied.get("parser_id") != PARSER_ID
        or copied.get("mapping_vector_sha256")
        != contract.payload_sha256(_mapping())
        or copied.get("expected_identity_count") != contract.TASK_COUNT
        or not isinstance(records, Mapping)
        or copied.get("valid_record_count") != len(records)
        or copied.get("one_attempt_no_redirect_retry_refetch_or_replacement")
        is not True
        or copied.get("same_snapshot_used_for_both_prediction_arms") is not True
        or copied.get("prediction_freeze_and_forward_audit_preexisted") is not True
        or not contract.sealed(copied, "truth_payload_sha256")
    ):
        raise ValueError("V2.54.89 truth artifact drifted")
    if failure is None:
        decoded = raw.decode(copied.get("response_encoding") or "utf-8", errors="replace")
        expected = parse_iana_page(decoded)
        if (
            copied.get("http_status") != 200
            or dict(records) != expected
            or copied.get("valid_record_count") != contract.TASK_COUNT
        ):
            raise ValueError("V2.54.89 successful truth extraction drifted")
    elif records or copied.get("valid_record_count") != 0:
        raise ValueError("V2.54.89 failed truth artifact retained records")
    return copied


def _result_artifact(
    protocol: Mapping[str, Any],
    truth: Mapping[str, Any],
    metrics: Mapping[str, Any],
    *,
    now: int,
    protocol_sha256: str,
) -> dict[str, Any]:
    decision = quality_decision(metrics)
    passed = bool(decision["quality_gate_passed"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25489_iana_detail_shared_parent_quality_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "status": "iana_detail_shared_parent_quality_go"
        if passed
        else "iana_detail_shared_parent_quality_no_go",
        "passed": passed,
        "quality_protocol_sha256": protocol_sha256,
        "forward_audit_sha256": protocol["forward_audit_sha256"],
        "forward_result_sha256": protocol["forward_result_sha256"],
        "task_rows_sha256": protocol["task_rows_sha256"],
        "prediction_freeze_sha256": protocol["prediction_freeze_sha256"],
        "raw_truth_response_sha256": truth["raw_response_sha256"],
        "compressed_truth_snapshot_sha256": truth["compressed_snapshot_sha256"],
        "truth_payload_sha256": truth["truth_payload_sha256"],
        "metrics": dict(metrics),
        "quality_decision": decision,
        "all_forty_predictions_evaluated_once": True,
        "fixed_denominator_failure_as_zero": True,
        "quality_evaluation_executed_once_after_prediction_freeze_and_pushed_forward_audit": True,
        "prediction_retry_repair_selection_or_mutation": False,
        "base_and_candidate_share_one_v25472_parent_forward": True,
        "candidate_minus_base_is_shared_parent_treatment_effect": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "claim_scope": {
            "fresh_external_shared_parent_quality_measured": True,
            "deepwidebench_quality_measured": False,
            "entropy_or_signed_credit_validated": False,
            "leaderboard_or_sota_supported": False,
        },
        "authorization": {
            "quality_audit_generation": True,
            "deepwidebench_successor_build": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_refetch_revaluation_or_selective_replacement": False,
        },
    }
    return contract.seal(value, "result_payload_sha256")


def validate_result(
    value: Mapping[str, Any],
    *,
    truth: Mapping[str, Any] | None = None,
    rows: Sequence[Mapping[str, Any]] | None = None,
    expected_protocol_sha256: str | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    metrics = copied.get("metrics")
    decision = copied.get("quality_decision")
    passed = copied.get("passed") is True
    expected_protocol = (
        contract.sha256(ROOT / PROTOCOL)
        if expected_protocol_sha256 is None
        else expected_protocol_sha256
    )
    if (
        copied.get("role") != "v25489_iana_detail_shared_parent_quality_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status")
        != (
            "iana_detail_shared_parent_quality_go"
            if passed
            else "iana_detail_shared_parent_quality_no_go"
        )
        or copied.get("quality_protocol_sha256") != expected_protocol
        or copied.get("forward_audit_sha256") != FORWARD_AUDIT_SHA256
        or copied.get("forward_result_sha256") != FORWARD_RESULT_SHA256
        or copied.get("task_rows_sha256") != TASK_ROWS_SHA256
        or copied.get("prediction_freeze_sha256") != PREDICTION_FREEZE_SHA256
        or not isinstance(metrics, Mapping)
        or not isinstance(decision, Mapping)
        or quality_decision(metrics) != dict(decision)
        or passed is not decision["quality_gate_passed"]
        or copied.get("all_forty_predictions_evaluated_once") is not True
        or copied.get("fixed_denominator_failure_as_zero") is not True
        or copied.get(
            "quality_evaluation_executed_once_after_prediction_freeze_and_pushed_forward_audit"
        )
        is not True
        or copied.get("prediction_retry_repair_selection_or_mutation") is not False
        or copied.get("base_and_candidate_share_one_v25472_parent_forward") is not True
        or copied.get("candidate_minus_base_is_shared_parent_treatment_effect")
        is not True
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("claim_scope")
        != {
            "fresh_external_shared_parent_quality_measured": True,
            "deepwidebench_quality_measured": False,
            "entropy_or_signed_credit_validated": False,
            "leaderboard_or_sota_supported": False,
        }
        or copied.get("authorization")
        != {
            "quality_audit_generation": True,
            "deepwidebench_successor_build": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_refetch_revaluation_or_selective_replacement": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.54.89 quality result drifted")
    if truth is not None and rows is not None:
        records = truth.get("records")
        if (
            not isinstance(records, Mapping)
            or copied.get("truth_payload_sha256") != truth.get("truth_payload_sha256")
            or copied.get("raw_truth_response_sha256")
            != truth.get("raw_response_sha256")
            or copied.get("metrics") != evaluate_rows(rows, records)
        ):
            raise ValueError("V2.54.89 quality result replay drifted")
    return copied


def evaluate(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    _forward_audit, rows = _forward_barrier()
    if not _future_pristine((RAW_TRUTH, TRUTH, RESULT, AUDIT)):
        raise RuntimeError("V2.54.89 evaluation surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.54.89 protected watcher identity drifted")
    if not forward_control._lease_inactive() or forward_control._active_conflicts():
        raise RuntimeError("V2.54.89 shared evaluation runtime is not ready")
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25489_iana_detail_shared_parent_quality_v1",
        purpose="single_postfreeze_iana_truth_and_fixed_two_arm_evaluation",
        path=ROOT / contract.LEASE_PATH,
    ):
        raw, status, fetch_failure, encoding = _fetch_once()
    records: dict[str, dict[str, str]] = {}
    failure = fetch_failure
    if failure is None:
        try:
            records = parse_iana_page(raw.decode(encoding, errors="replace"))
        except ValueError as exc:
            failure = type(exc).__name__[:128]
            records = {}
    timestamp = int(time.time()) if now is None else int(now)
    compressed, truth = _truth_artifact(
        raw, status, failure, encoding, records, now=timestamp
    )
    metrics = evaluate_rows(rows, records)
    result = _result_artifact(
        protocol,
        truth,
        metrics,
        now=timestamp,
        protocol_sha256=contract.sha256(ROOT / PROTOCOL),
    )
    validate_truth(truth, compressed)
    validate_result(result, truth=truth, rows=rows)
    _publish_bytes(ROOT / RAW_TRUTH, compressed)
    _publish_json(ROOT / TRUTH, truth)
    _publish_json(ROOT / RESULT, result)
    return result


def audit_result(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    _forward_audit, rows = _forward_barrier()
    compressed = contract.ordinary(ROOT, RAW_TRUTH, tracked=True).read_bytes()
    truth = validate_truth(_read(TRUTH), compressed)
    result = validate_result(_read(RESULT), truth=truth, rows=rows)
    recomputed_metrics = evaluate_rows(rows, truth["records"])
    recomputed_decision = quality_decision(recomputed_metrics)
    checks = {
        "protocol_and_forward_barrier_valid": bool(protocol),
        "one_truth_attempt_snapshot_hash_and_parser_replay_valid": bool(truth),
        "all_forty_frozen_predictions_recomputed_once": result[
            "all_forty_predictions_evaluated_once"
        ]
        is True
        and recomputed_metrics["evaluation_count"] == 40,
        "metrics_and_quality_decision_recompute_exactly": (
            result["metrics"] == recomputed_metrics
            and result["quality_decision"] == recomputed_decision
        ),
        "shared_parent_candidate_comparison_preserved": result[
            "candidate_minus_base_is_shared_parent_treatment_effect"
        ]
        is True,
        "no_prediction_retry_repair_selection_or_mutation": result[
            "prediction_retry_repair_selection_or_mutation"
        ]
        is False,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_released": forward_control._lease_inactive(),
        "conflicting_forward_or_evaluator_processes_absent": not forward_control._active_conflicts(),
        "entropy_information_gain_signed_credit_zero": result[
            "positive_signed_credit_count"
        ]
        == 0,
        "audit_calls_no_network_model_search_fetch_or_deepwidebench_evaluator": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    valid = not findings
    passed = result["passed"] is True
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25489_iana_detail_shared_parent_quality_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / PROTOCOL),
        "raw_truth_snapshot_sha256": contract.sha256(ROOT / RAW_TRUTH),
        "truth_sha256": contract.sha256(ROOT / TRUTH),
        "quality_result_sha256": contract.sha256(ROOT / RESULT),
        "checks": checks,
        "findings": findings,
        "audit_valid": valid,
        "quality_gate_passed": passed,
        "positive_signed_credit_count": 0,
        "authorization": {
            "deepwidebench_successor_build": valid and passed,
            "new_exact220_protocol_design": valid and passed,
            "deepwidebench_forward_or_evaluator": False,
            "additional_truth_fetch_replay_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("build-audit", "protocol", "evaluate", "audit")
    )
    args = parser.parse_args()
    if args.command == "build-audit":
        value, path = build_audit(), BUILD_AUDIT
    elif args.command == "protocol":
        value, path = preregister(), PROTOCOL
    elif args.command == "evaluate":
        value = evaluate()
        print(
            json.dumps(
                {
                    "path": str(RESULT),
                    "status": value["status"],
                    "passed": value["passed"],
                    "metrics": value["metrics"],
                    "quality_decision": value["quality_decision"],
                    "authorization": value["authorization"],
                },
                sort_keys=True,
            )
        )
        return
    else:
        value, path = audit_result(), AUDIT
    if value.get("findings"):
        raise RuntimeError(value["findings"])
    _publish_json(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value.get("role"),
                "audit_valid": value.get("audit_valid"),
                "quality_gate_passed": value.get("quality_gate_passed"),
                "findings": value.get("findings"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
