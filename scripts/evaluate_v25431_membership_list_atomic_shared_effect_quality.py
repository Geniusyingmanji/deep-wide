#!/usr/bin/env python3
"""Post-freeze quality gate for the V2.54.30 combined intervention.

The forward is already frozen and pushed before this module may open truth.
One redirect-disabled, no-retry GET obtains one RFC Editor index snapshot for
all three frozen prediction arms.  The primary comparison is the deterministic
``membership_list_atomic_candidate`` versus ``shared_base_table`` from the
same parent forward.  ``membership_changed_safe_candidate`` is diagnostic
only and cannot enter the GO decision.  Missing or malformed truth and invalid
predictions score zero on the fixed twenty-task denominator.  No retry,
refetch, prediction repair, replacement, or selective revaluation is
permitted.
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
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25430_membership_list_atomic_shared_effect_external_contract as contract  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base_audit  # noqa: E402
from scripts import control_v25430_membership_list_atomic_shared_effect_external as forward_control  # noqa: E402
from scripts import evaluate_v25416_paired_rfc_route_quality as frozen_scorer  # noqa: E402
from scripts import run_v25430_membership_list_atomic_shared_effect_external as forward_runner  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260813"
PROTOCOL_ID = "v25431_v25430_membership_list_atomic_shared_effect_quality_v1"
SOURCE = Path("scripts/evaluate_v25431_membership_list_atomic_shared_effect_quality.py")
TEST = Path("tests/test_evaluate_v25431_membership_list_atomic_shared_effect_quality.py")
BUILD_AUDIT = Path(
    f"results/v25431_membership_list_atomic_shared_effect_quality_build_audit_v1_{DATE}.json"
)
PROTOCOL = contract.POSTFREEZE_QUALITY_PROTOCOL
RAW_TRUTH = contract.OUTPUT_ROOT / "postfreeze_rfc_index_v25431.xml.gz"
TRUTH = contract.OUTPUT_ROOT / "postfreeze_rfc_truth_v25431.json"
RESULT = contract.QUALITY_RESULT
AUDIT = contract.QUALITY_AUDIT

URL = "https://www.rfc-editor.org/rfc-index.xml"
USER_AGENT = "DeepWideResearch/1.0 (+postfreeze RFC quality evaluator)"
CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 60.0
MAXIMUM_RESPONSE_BYTES = 20_000_000
RFC_INDEX_NAMESPACE = "https://www.rfc-editor.org/rfc-index"
PARSER_ID = "namespace_qualified_rfc_and_not_issued_v2"
UNKNOWN = "Unknown"
EXPECTED_TESTS = 8
METRICS = (
    "entity_coverage",
    "row_exact",
    "cell_accuracy",
    "column_accuracy",
    "quality_composite",
)
BASE_ARM = contract.runtime.BASE_ARM
RAW_ARM = contract.runtime.RAW_ARM
GUARDED_ARM = contract.runtime.GUARDED_ARM
ARMS = (BASE_ARM, RAW_ARM, GUARDED_ARM)

FORWARD_AUDIT_SHA256 = (
    "e60ef2261350872c550518cfcf2a9e07dcf143ca90fe0c3729e290dfda7d91ba"
)
FORWARD_RESULT_SHA256 = (
    "8d1fb0def68c5936f6d2e683ebeaa002d61ff2a25a51ee2668aa2a777144b75b"
)
TASK_ROWS_SHA256 = (
    "bbf4bfac4f04e79defa56778cfd79d55e05d6c74a739a853028f4966df869ed8"
)
PREDICTION_FREEZE_SHA256 = (
    "cedcaa4f6c61086bd83d65ea3dff0cd74c4f57b1d5447668e9694eca2e51f2ff"
)
FORWARD_RUNNER_SHA256 = (
    "389083a120e92a0f3d47f00f807f92173a9cfd2c04543b6c929a2d4fec4ba5ec"
)
FORWARD_CONTRACT_SHA256 = (
    "9bea1e50632f6a869b784b3831ee5b18449722b13af7ca8b3bd775be3e3dcd47"
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
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.54.31 expected a JSON object")
    return value


def _read_rows(*, tracked: bool = True) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, contract.TASK_ROWS, tracked=tracked)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.54.31 expected JSONL objects")
    return rows


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.54.31 requires a clean pushed HEAD")
    return head, target


def _future_pristine(paths: Sequence[Path]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _qualified(local: str) -> str:
    return f"{{{RFC_INDEX_NAMESPACE}}}{local}"


def _child_text(entry: ET.Element, local: str) -> str:
    child = entry.find(_qualified(local))
    return (
        frozen_scorer._text("".join(child.itertext())) if child is not None else ""
    )


def parse_rfc_index(
    raw: bytes, expected_numbers: Sequence[int]
) -> tuple[dict[str, dict[str, str]], tuple[str, ...]]:
    """Parse regular and structurally unambiguous not-issued RFC identities."""

    if not raw or len(raw) > MAXIMUM_RESPONSE_BYTES:
        raise ValueError("V2.54.31 RFC index bytes are invalid")
    root = ET.fromstring(raw)
    if root.tag != _qualified("rfc-index"):
        raise ValueError("V2.54.31 RFC index namespace or root drifted")
    numbers = tuple(int(value) for value in expected_numbers)
    if len(numbers) != len(set(numbers)):
        raise ValueError("V2.54.31 expected RFC vector is duplicated")
    wanted = set(numbers)
    records: dict[str, dict[str, str]] = {}
    not_issued: list[str] = []

    def identity_for(entry: ET.Element) -> str | None:
        match = re.fullmatch(r"(?i)RFC0*([0-9]{1,4})", _child_text(entry, "doc-id"))
        if match is None or int(match.group(1)) not in wanted:
            return None
        return f"RFC {int(match.group(1)):04d}"

    for entry in root.findall(f".//{_qualified('rfc-entry')}"):
        identity = identity_for(entry)
        if identity is None:
            continue
        authors = [
            _child_text(author, "name")
            for author in entry.findall(_qualified("author"))
            if _child_text(author, "name")
        ]
        date = entry.find(_qualified("date"))
        month = _child_text(date, "month") if date is not None else ""
        year = _child_text(date, "year") if date is not None else ""
        status = _child_text(entry, "current-status") or _child_text(
            entry, "publication-status"
        )
        record = {
            "RFC": identity,
            "Title": _child_text(entry, "title"),
            "Authors": "; ".join(authors),
            "Status": status,
            "Stream": _child_text(entry, "stream"),
            "Published": frozen_scorer._text(f"{month} {year}"),
        }
        if identity in records or any(
            not record[column] for column in contract.COLUMNS
        ):
            raise ValueError("V2.54.31 RFC record is duplicate or incomplete")
        records[identity] = record

    for entry in root.findall(f".//{_qualified('rfc-not-issued-entry')}"):
        identity = identity_for(entry)
        if identity is None:
            continue
        if identity in records or [child.tag for child in list(entry)] != [
            _qualified("doc-id")
        ]:
            raise ValueError("V2.54.31 not-issued RFC node is ambiguous")
        records[identity] = {
            "RFC": identity,
            **{column: UNKNOWN for column in contract.COLUMNS[1:]},
        }
        not_issued.append(identity)

    expected = {f"RFC {number:04d}" for number in numbers}
    if set(records) != expected:
        raise ValueError("V2.54.31 RFC snapshot lacks a fixed identity")
    return records, tuple(not_issued)


def _groups() -> dict[int, tuple[str, ...]]:
    identities = contract.population.identity_vector()
    width = contract.population.ROWS_PER_TASK
    return {
        index: tuple(identities[index * width : (index + 1) * width])
        for index in range(contract.TASK_COUNT)
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
    by_task: Mapping[int, Mapping[str, Mapping[str, Any]]],
    left_arm: str,
    right_arm: str,
    metric: str,
) -> dict[str, int]:
    output = {"right_win": 0, "tie": 0, "right_loss": 0}
    for index in range(contract.TASK_COUNT):
        left = float(by_task[index][left_arm][metric])
        right = float(by_task[index][right_arm][metric])
        delta = right - left
        key = "right_win" if delta > 1e-12 else "right_loss" if delta < -1e-12 else "tie"
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
        or [row["task_index"] for row in checked]
        != list(range(contract.TASK_COUNT))
    ):
        raise ValueError("V2.54.31 frozen task denominator drifted")
    groups = _groups()
    values: dict[str, list[dict[str, Any]]] = {arm: [] for arm in ARMS}
    by_task: dict[int, dict[str, dict[str, Any]]] = {}
    for row in checked:
        index = int(row["task_index"])
        by_task[index] = {}
        for arm in ARMS:
            metric = frozen_scorer.evaluate_prediction(
                row["predictions"][arm], groups[index], truth
            )
            values[arm].append(metric)
            by_task[index][arm] = metric

    aggregate: dict[str, Any] = {}
    for arm in ARMS:
        metrics = values[arm]
        if len(metrics) != contract.TASK_COUNT:
            raise ValueError("V2.54.31 arm denominator drifted")
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
        "arms": aggregate,
        "guarded_minus_base": _delta(aggregate[GUARDED_ARM], aggregate[BASE_ARM]),
        "raw_minus_base_diagnostic": _delta(aggregate[RAW_ARM], aggregate[BASE_ARM]),
        "guarded_minus_raw_diagnostic": _delta(
            aggregate[GUARDED_ARM], aggregate[RAW_ARM]
        ),
        "guarded_vs_base_exact_disposition": _disposition(
            by_task, BASE_ARM, GUARDED_ARM, "exact_table_success"
        ),
        "guarded_vs_base_composite_disposition": _disposition(
            by_task, BASE_ARM, GUARDED_ARM, "quality_composite"
        ),
        "guarded_vs_raw_composite_diagnostic": _disposition(
            by_task, RAW_ARM, GUARDED_ARM, "quality_composite"
        ),
        "raw_candidate_is_diagnostic_only": True,
    }


def quality_decision(metrics: Mapping[str, Any]) -> dict[str, Any]:
    arms = metrics.get("arms")
    delta = metrics.get("guarded_minus_base")
    if not isinstance(arms, Mapping) or not isinstance(delta, Mapping):
        raise ValueError("V2.54.31 quality metric surface drifted")
    if any(not isinstance(arms.get(arm), Mapping) for arm in ARMS):
        raise ValueError("V2.54.31 quality arm metric is absent")
    checks = {
        "fixed_task_and_prediction_denominator": metrics.get("evaluation_count")
        == contract.TASK_COUNT * len(ARMS)
        and all(arms[arm].get("tasks") == contract.TASK_COUNT for arm in ARMS),
        "truth_valid_for_all_fixed_predictions": all(
            arms[arm].get("invalid_tasks") == 0 for arm in ARMS
        ),
        "guarded_whole_table_exact_strict_gain": delta.get(
            "exact_table_successes", 0
        )
        > 0,
        "guarded_entity_coverage_nonregression": delta.get(
            "entity_coverage", -1
        )
        >= -1e-12,
        "guarded_row_exact_nonregression": delta.get("row_exact", -1) >= -1e-12,
        "guarded_cell_accuracy_nonregression": delta.get("cell_accuracy", -1)
        >= -1e-12,
        "guarded_column_accuracy_nonregression": delta.get(
            "column_accuracy", -1
        )
        >= -1e-12,
        "guarded_quality_composite_nonregression": delta.get(
            "quality_composite", -1
        )
        >= -1e-12,
        "guarded_fallback_nonincrease": delta.get("fallback_tasks", 1) <= 0,
        "guarded_invalid_nonincrease": delta.get("invalid_tasks", 1) <= 0,
        "raw_candidate_excluded_from_go": metrics.get(
            "raw_candidate_is_diagnostic_only"
        )
        is True,
        "shared_parent_sampling_causal_boundary": True,
        "positive_signed_credit_zero": True,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {"checks": checks, "failed_checks": failed, "quality_gate_passed": not failed}


def parser_contract() -> dict[str, Any]:
    return {
        "parser_id": PARSER_ID,
        "required_root_tag": _qualified("rfc-index"),
        "required_namespace": RFC_INDEX_NAMESPACE,
        "accepted_fixed_identity_node_types": [
            "rfc-entry",
            "rfc-not-issued-entry",
        ],
        "not_issued_structural_contract": "exactly_one_doc_id_child",
        "not_issued_non_key_field_value": UNKNOWN,
        "all_eighty_fixed_identities_required": True,
        "not_issued_count_not_opened_before_protocol": True,
    }


def scoring_contract() -> dict[str, Any]:
    return {
        "arms": list(ARMS),
        "primary_comparison": "membership_list_atomic_candidate_minus_shared_base_table",
        "raw_candidate_role": "diagnostic_only",
        "columns": list(contract.COLUMNS),
        "rows_per_task": contract.population.ROWS_PER_TASK,
        "exact": "exact RFC order and all twenty non-key cells correct",
        "entity_coverage": "expected RFC identities present divided by four",
        "row_exact": "rows with all five non-key fields correct divided by four",
        "cell_accuracy": "correct non-key cells divided by twenty",
        "column_accuracy": "macro mean of ordered key and five field accuracies",
        "quality_composite": "mean(entity,row,cell,column)",
        "invalid_prediction_or_missing_truth": "all metrics zero",
        "all_three_predictions_evaluated_once": True,
        "fixed_task_denominator": contract.TASK_COUNT,
        "positive_signed_credit_count": 0,
    }


def truth_fetch_contract() -> dict[str, Any]:
    return {
        "maximum_attempts": 1,
        "redirects": False,
        "retries": 0,
        "connect_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
        "read_timeout_seconds": READ_TIMEOUT_SECONDS,
        "maximum_response_bytes": MAXIMUM_RESPONSE_BYTES,
        "shared_one_snapshot_for_all_three_arms": True,
        "failure_is_fixed_denominator_zero_without_refetch": True,
    }


def _source_network_contract(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    request_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id in {
                "requests",
                "httpx",
                "urllib",
            }:
                request_calls.append(f"{node.func.value.id}.{node.func.attr}")
    network_imports = imports & {"requests", "httpx", "urllib", "socket", "aiohttp"}
    return network_imports == {"requests"} and request_calls == ["requests.get"]


def _forward_barrier() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    audit = _read(contract.FORWARD_AUDIT)
    forward = forward_runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    freeze = _read(contract.PREDICTION_FREEZE)
    rows = [forward_runner.validate_task_row(row) for row in _read_rows()]
    hashes = {
        contract.FORWARD_AUDIT: FORWARD_AUDIT_SHA256,
        contract.FORWARD_RESULT: FORWARD_RESULT_SHA256,
        contract.TASK_ROWS: TASK_ROWS_SHA256,
        contract.PREDICTION_FREEZE: PREDICTION_FREEZE_SHA256,
        contract.RUNNER: FORWARD_RUNNER_SHA256,
        contract.CONTRACT: FORWARD_CONTRACT_SHA256,
    }
    if (
        any(contract.sha256(ROOT / path) != expected for path, expected in hashes.items())
        or audit.get("role") != "v25430_membership_list_atomic_shared_effect_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is not True
        or audit.get("authorization", {}).get("deepwidebench_successor_build")
        is not False
        or not contract.sealed(audit, "audit_payload_sha256")
        or forward["mechanism_decision"]["mechanism_gate_passed"] is not True
        or freeze.get("role") != forward_runner.FREEZE_ROLE
        or freeze.get("task_count") != contract.TASK_COUNT
        or freeze.get("all_three_prediction_texts_persisted") is not True
        or freeze.get(
            "all_predictions_terminal_before_truth_evaluator_or_quality_decision"
        )
        is not True
        or not contract.sealed(freeze, "freeze_payload_sha256")
        or len(rows) != contract.TASK_COUNT
        or [row["opaque_id"] for row in rows]
        != [task["opaque_id"] for task in contract.task_vector()]
    ):
        raise RuntimeError("V2.54.31 pushed forward barrier drifted")
    return audit, rows


def build_audit(
    *, now: int | None = None, require_clean: bool = True
) -> dict[str, Any]:
    head, target = _clean_pushed() if require_clean else ("build-only", "build-only")
    forward_audit, _rows = _forward_barrier()
    tests = forward_control._test(TEST.name, EXPECTED_TESTS)
    source = ROOT / SOURCE
    test = ROOT / TEST
    checks = {
        "pushed_forward_audit_exact_and_quality_authorized": bool(forward_audit),
        "quality_tests_exact8": tests["passed"],
        "source_and_test_tracked": not require_clean
        or (base_audit._tracked(SOURCE) and base_audit._tracked(TEST)),
        "source_and_test_credential_literal_zero": not contract.SECRET.search(
            source.read_text(encoding="utf-8") + test.read_text(encoding="utf-8")
        ),
        "single_get_network_surface_exact": _source_network_contract(source),
        "future_quality_surfaces_pristine": _future_pristine(
            (BUILD_AUDIT, PROTOCOL, RAW_TRUTH, TRUTH, RESULT, AUDIT)
        ),
        "fixed_twenty_tasks_eighty_identities_three_arms": (
            contract.TASK_COUNT == 20
            and len(contract.population.identity_vector()) == 80
            and ARMS == forward_runner.ARMS
        ),
        "namespace_and_not_issued_parser_fixed_before_truth": (
            RFC_INDEX_NAMESPACE == "https://www.rfc-editor.org/rfc-index"
            and PARSER_ID == "namespace_qualified_rfc_and_not_issued_v2"
        ),
        "shared_parent_primary_comparison_and_raw_diagnostic": (
            scoring_contract()["primary_comparison"]
            == "membership_list_atomic_candidate_minus_shared_base_table"
            and scoring_contract()["raw_candidate_role"] == "diagnostic_only"
        ),
        "quality_gate_exact_and_signed_credit_zero": (
            contract.quality_gate()["positive_signed_credit_count"] == 0
            and scoring_contract()["positive_signed_credit_count"] == 0
        ),
        "protected_watchers_exact": False,
        "shared_api_lease_inactive": forward_control._lease_inactive(),
        "conflicting_forward_or_evaluator_processes_absent": not forward_control._active_conflicts(),
        "git_clean_head_equals_target_main": not require_clean or head == target,
        "network_truth_or_evaluator_not_called_by_build_audit": True,
    }
    # The forward audit stores the watcher check as a boolean; the protocol is
    # the exact watcher-vector authority.
    protocol = _read(contract.PROTOCOL)
    checks["protected_watchers_exact"] = (
        contract.watcher_snapshot() == protocol["protected_watchers"]
        and forward_audit["checks"]["protected_watchers_unchanged"] is True
    )
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25431_membership_list_atomic_shared_effect_quality_build_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "source_sha256": contract.sha256(source),
        "test_sha256": contract.sha256(test),
        "forward_artifact_sha256": {
            "forward_audit": FORWARD_AUDIT_SHA256,
            "forward_result": FORWARD_RESULT_SHA256,
            "task_rows": TASK_ROWS_SHA256,
            "prediction_freeze": PREDICTION_FREEZE_SHA256,
        },
        "tests": tests,
        "parser_contract": parser_contract(),
        "scoring_contract": scoring_contract(),
        "truth_fetch_contract": truth_fetch_contract(),
        "quality_gate": contract.quality_gate(),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "network_truth_or_evaluator_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "postfreeze_quality_protocol_generation": not findings,
            "truth_fetch_or_evaluation": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
            "retry_refetch_revaluation_or_selective_replacement": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_build_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role")
        != "v25431_membership_list_atomic_shared_effect_quality_build_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("source_sha256") != contract.sha256(ROOT / SOURCE)
        or copied.get("test_sha256") != contract.sha256(ROOT / TEST)
        or copied.get("parser_contract") != parser_contract()
        or copied.get("scoring_contract") != scoring_contract()
        or copied.get("truth_fetch_contract") != truth_fetch_contract()
        or copied.get("quality_gate") != contract.quality_gate()
        or copied.get("network_truth_or_evaluator_called") is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("authorization")
        != {
            "postfreeze_quality_protocol_generation": True,
            "truth_fetch_or_evaluation": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
            "retry_refetch_revaluation_or_selective_replacement": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.54.31 quality build audit drifted")
    return copied


def preregister(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    build = validate_build_audit(_read(BUILD_AUDIT))
    forward_audit, rows = _forward_barrier()
    if not _future_pristine((PROTOCOL, RAW_TRUTH, TRUTH, RESULT, AUDIT)):
        raise RuntimeError("V2.54.31 quality protocol surface is not pristine")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25431_membership_list_atomic_shared_effect_quality_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "target_main": target,
        "quality_build_audit_sha256": contract.sha256(ROOT / BUILD_AUDIT),
        "evaluator_source_sha256": build["source_sha256"],
        "evaluator_test_sha256": build["test_sha256"],
        "forward_audit_sha256": FORWARD_AUDIT_SHA256,
        "forward_result_sha256": FORWARD_RESULT_SHA256,
        "task_rows_sha256": TASK_ROWS_SHA256,
        "prediction_freeze_sha256": PREDICTION_FREEZE_SHA256,
        "frozen_task_count": len(rows),
        "fixed_prediction_count": len(rows) * len(ARMS),
        "fixed_truth_identity_count": len(contract.population.identity_vector()),
        "fixed_truth_identity_vector_sha256": contract.payload_sha256(
            contract.population.identity_vector()
        ),
        "official_truth_url": URL,
        "truth_fetch": truth_fetch_contract(),
        "parser": parser_contract(),
        "scoring": scoring_contract(),
        "quality_gate": contract.quality_gate(),
        "prediction_freeze_and_pushed_forward_audit_precede_truth_open": True,
        "base_raw_and_guarded_share_one_parent_forward": True,
        "raw_candidate_quality_is_diagnostic_only": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_truth_fetch_and_fixed_evaluation": True,
            "retry_refetch_revaluation_or_selective_replacement": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
        },
    }
    if forward_audit["authorization"]["postfreeze_quality_protocol"] is not True:
        raise RuntimeError("V2.54.31 forward audit does not authorize quality")
    return contract.seal(value, "protocol_payload_sha256")


def validate_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role")
        != "v25431_membership_list_atomic_shared_effect_quality_preregistration"
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
        or copied.get("fixed_truth_identity_count") != 80
        or copied.get("fixed_truth_identity_vector_sha256")
        != contract.payload_sha256(contract.population.identity_vector())
        or copied.get("official_truth_url") != URL
        or copied.get("truth_fetch") != truth_fetch_contract()
        or copied.get("parser") != parser_contract()
        or copied.get("scoring") != scoring_contract()
        or copied.get("quality_gate") != contract.quality_gate()
        or copied.get(
            "prediction_freeze_and_pushed_forward_audit_precede_truth_open"
        )
        is not True
        or copied.get("base_raw_and_guarded_share_one_parent_forward") is not True
        or copied.get("raw_candidate_quality_is_diagnostic_only") is not True
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("authorization")
        != {
            "one_truth_fetch_and_fixed_evaluation": True,
            "retry_refetch_revaluation_or_selective_replacement": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "protocol_payload_sha256")
    ):
        raise ValueError("V2.54.31 quality protocol drifted")
    return copied


def _fetch_once() -> tuple[bytes, int, str | None]:
    try:
        response = requests.get(
            URL,
            headers={"User-Agent": USER_AGENT},
            timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
            allow_redirects=False,
        )
        raw = bytes(response.content)
        status = int(response.status_code)
        if status != 200 or not raw or len(raw) > MAXIMUM_RESPONSE_BYTES:
            return raw[:MAXIMUM_RESPONSE_BYTES], status, "InvalidResponse"
        return raw, status, None
    except requests.RequestException as exc:
        return b"", 0, type(exc).__name__[:128] or "RequestException"


def _truth_artifact(
    raw: bytes,
    status: int,
    failure: str | None,
    records: Mapping[str, Mapping[str, str]],
    not_issued: Sequence[str],
    *,
    now: int,
) -> tuple[bytes, dict[str, Any]]:
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25431_postfreeze_official_rfc_truth",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "official_truth_url": URL,
        "attempt_count": 1,
        "http_status": int(status),
        "fetch_or_parse_failure_type": failure,
        "raw_response_bytes": len(raw),
        "raw_response_sha256": hashlib.sha256(raw).hexdigest(),
        "compressed_snapshot_sha256": hashlib.sha256(compressed).hexdigest(),
        "parser_id": PARSER_ID,
        "required_namespace": RFC_INDEX_NAMESPACE,
        "expected_identity_count": 80,
        "valid_record_count": len(records),
        "regular_record_count": len(records) - len(not_issued),
        "not_issued_count": len(not_issued),
        "not_issued_identities": list(not_issued),
        "not_issued_non_key_field_value": UNKNOWN,
        "records": dict(records),
        "one_attempt_no_redirect_retry_refetch_or_replacement": True,
        "same_snapshot_used_for_all_three_prediction_arms": True,
        "prediction_freeze_and_forward_audit_preexisted": True,
    }
    return compressed, contract.seal(value, "truth_payload_sha256")


def validate_truth(value: Mapping[str, Any], compressed: bytes) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    try:
        raw = gzip.decompress(compressed)
    except (OSError, EOFError) as exc:
        raise ValueError("V2.54.31 compressed truth snapshot drifted") from exc
    records = copied.get("records")
    failure = copied.get("fetch_or_parse_failure_type")
    if (
        copied.get("role") != "v25431_postfreeze_official_rfc_truth"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("official_truth_url") != URL
        or copied.get("attempt_count") != 1
        or copied.get("raw_response_bytes") != len(raw)
        or copied.get("raw_response_sha256") != hashlib.sha256(raw).hexdigest()
        or copied.get("compressed_snapshot_sha256")
        != hashlib.sha256(compressed).hexdigest()
        or copied.get("parser_id") != PARSER_ID
        or copied.get("required_namespace") != RFC_INDEX_NAMESPACE
        or copied.get("expected_identity_count") != 80
        or not isinstance(records, Mapping)
        or copied.get("valid_record_count") != len(records)
        or copied.get("regular_record_count")
        != len(records) - copied.get("not_issued_count", -1)
        or copied.get("not_issued_non_key_field_value") != UNKNOWN
        or copied.get("one_attempt_no_redirect_retry_refetch_or_replacement")
        is not True
        or copied.get("same_snapshot_used_for_all_three_prediction_arms") is not True
        or copied.get("prediction_freeze_and_forward_audit_preexisted") is not True
        or not contract.sealed(copied, "truth_payload_sha256")
    ):
        raise ValueError("V2.54.31 truth artifact drifted")
    if failure is None:
        expected, not_issued = parse_rfc_index(raw, contract.population.RFC_NUMBERS)
        if (
            copied.get("http_status") != 200
            or dict(records) != expected
            or copied.get("valid_record_count") != 80
            or copied.get("not_issued_identities") != list(not_issued)
            or copied.get("not_issued_count") != len(not_issued)
        ):
            raise ValueError("V2.54.31 successful truth extraction drifted")
    elif (
        records
        or copied.get("valid_record_count") != 0
        or copied.get("regular_record_count") != 0
        or copied.get("not_issued_count") != 0
        or copied.get("not_issued_identities") != []
    ):
        raise ValueError("V2.54.31 failed truth artifact retained records")
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
        "role": "v25431_membership_list_atomic_shared_effect_quality_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "status": "membership_list_atomic_shared_effect_quality_go"
        if passed
        else "membership_list_atomic_shared_effect_quality_no_go",
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
        "all_sixty_predictions_evaluated_once": True,
        "fixed_denominator_failure_as_zero": True,
        "quality_evaluation_executed_once_after_prediction_freeze_and_pushed_forward_audit": True,
        "prediction_retry_repair_selection_or_mutation": False,
        "base_raw_and_guarded_share_one_parent_forward": True,
        "raw_candidate_quality_is_diagnostic_only": True,
        "guarded_minus_base_is_shared_parent_treatment_effect": True,
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
        copied.get("role") != "v25431_membership_list_atomic_shared_effect_quality_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status")
        != (
            "membership_list_atomic_shared_effect_quality_go"
            if passed
            else "membership_list_atomic_shared_effect_quality_no_go"
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
        or copied.get("all_sixty_predictions_evaluated_once") is not True
        or copied.get("fixed_denominator_failure_as_zero") is not True
        or copied.get(
            "quality_evaluation_executed_once_after_prediction_freeze_and_pushed_forward_audit"
        )
        is not True
        or copied.get("prediction_retry_repair_selection_or_mutation") is not False
        or copied.get("base_raw_and_guarded_share_one_parent_forward") is not True
        or copied.get("raw_candidate_quality_is_diagnostic_only") is not True
        or copied.get("guarded_minus_base_is_shared_parent_treatment_effect")
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
        raise ValueError("V2.54.31 quality result drifted")
    if truth is not None and rows is not None:
        records = truth.get("records")
        if (
            not isinstance(records, Mapping)
            or copied.get("truth_payload_sha256")
            != truth.get("truth_payload_sha256")
            or copied.get("raw_truth_response_sha256")
            != truth.get("raw_response_sha256")
            or copied.get("metrics") != evaluate_rows(rows, records)
        ):
            raise ValueError("V2.54.31 quality result replay drifted")
    return copied


def evaluate(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    _forward_audit, rows = _forward_barrier()
    if not _future_pristine((RAW_TRUTH, TRUTH, RESULT, AUDIT)):
        raise RuntimeError("V2.54.31 evaluation surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.54.31 protected watcher identity drifted")
    if not forward_control._lease_inactive() or forward_control._active_conflicts():
        raise RuntimeError("V2.54.31 shared evaluation runtime is not ready")
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25431_membership_list_atomic_shared_effect_quality_v1",
        purpose="single_postfreeze_rfc_truth_and_fixed_three_arm_evaluation",
        path=ROOT / contract.LEASE_PATH,
    ):
        raw, status, fetch_failure = _fetch_once()
    records: dict[str, dict[str, str]] = {}
    not_issued: tuple[str, ...] = ()
    failure = fetch_failure
    if failure is None:
        try:
            records, not_issued = parse_rfc_index(
                raw, contract.population.RFC_NUMBERS
            )
        except (ET.ParseError, ValueError) as exc:
            failure = type(exc).__name__[:128]
            records = {}
            not_issued = ()
    timestamp = int(time.time()) if now is None else int(now)
    compressed, truth = _truth_artifact(
        raw, status, failure, records, not_issued, now=timestamp
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
        "all_sixty_frozen_predictions_recomputed_once": result[
            "all_sixty_predictions_evaluated_once"
        ]
        is True
        and recomputed_metrics["evaluation_count"] == 60,
        "metrics_and_quality_decision_recompute_exactly": (
            result["metrics"] == recomputed_metrics
            and result["quality_decision"] == recomputed_decision
        ),
        "raw_candidate_remains_diagnostic_only": (
            result["raw_candidate_quality_is_diagnostic_only"] is True
            and recomputed_metrics["raw_candidate_is_diagnostic_only"] is True
        ),
        "shared_parent_guarded_comparison_preserved": result[
            "guarded_minus_base_is_shared_parent_treatment_effect"
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
        "role": "v25431_membership_list_atomic_shared_effect_quality_audit",
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
    parser.add_argument("command", choices=("build-audit", "protocol", "evaluate", "audit"))
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
