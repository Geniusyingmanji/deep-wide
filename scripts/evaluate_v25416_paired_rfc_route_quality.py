#!/usr/bin/env python3
"""Post-freeze RFC quality evaluation for the V2.54.15 paired route gate.

This component is deliberately absent from the forward dependency closure.
It may run only after all forty predictions and the V2.54.15 forward audit are
committed and pushed.  One fixed, redirect-disabled, no-retry GET obtains the
official RFC Editor index.  Both route branches share that one truth snapshot.

The evaluator never reruns, repairs, or selects predictions.  Missing truth,
an invalid table, a duplicate RFC key, or any schema failure is failure-as-zero
for the fixed task denominator.  The paired tasks have independent provider
effects, so their quality delta is decision evidence rather than a shared-
sampling causal estimate.  Entropy/information gain receives no signed credit.
"""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24257_score_first_runtime as table_runtime  # noqa: E402
from deepwide_agent import v25411_visible_membership_route_runtime as route  # noqa: E402
from deepwide_agent import v25415_paired_rfc_route_external_contract as contract  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base_audit  # noqa: E402
from scripts import control_v25415_paired_rfc_route_external as forward_control  # noqa: E402
from scripts import run_v25415_paired_rfc_route_external as forward_runner  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260813"
SOURCE = Path("scripts/evaluate_v25416_paired_rfc_route_quality.py")
TEST = Path("tests/test_evaluate_v25416_paired_rfc_route_quality.py")
BUILD_AUDIT = Path(
    f"results/v25416_paired_rfc_route_quality_build_audit_v1_{DATE}.json"
)
RAW_TRUTH = contract.OUTPUT_ROOT / "postfreeze_rfc_index.xml.gz"
TRUTH = contract.OUTPUT_ROOT / "postfreeze_rfc_truth.json"
URL = "https://www.rfc-editor.org/rfc-index.xml"
USER_AGENT = "DeepWideResearch/1.0 (+postfreeze RFC quality evaluator)"
CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 60.0
MAXIMUM_RESPONSE_BYTES = 20_000_000
EXPECTED_TESTS = 8
METRICS = (
    "entity_coverage",
    "row_exact",
    "cell_accuracy",
    "column_accuracy",
    "quality_composite",
)
MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
STREAM_ALIASES = {
    "ietf": "ietf",
    "internetengineeringtaskforce": "ietf",
    "internetengineeringtaskforceietf": "ietf",
    "iab": "iab",
    "internetarchitectureboardiab": "iab",
    "irtf": "irtf",
    "internetresearchtaskforce": "irtf",
    "internetresearchtaskforceirtf": "irtf",
    "independent": "independent",
    "independentsubmission": "independent",
    "independentstream": "independent",
    "legacy": "legacy",
}


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
        raise RuntimeError("V2.54.16 expected JSON object")
    return value


def _read_rows(relative: Path, *, tracked: bool = True) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    values = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError("V2.54.16 expected JSONL objects")
    return values


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.54.16 requires clean pushed HEAD")
    return head, target


def _text(value: object) -> str:
    return " ".join(
        unicodedata.normalize("NFKC", str(value or "")).replace("\u00a0", " ").split()
    )


def _compact(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", _text(value).casefold())


def _identity(value: object) -> str | None:
    match = re.fullmatch(r"(?i)\s*RFC\s*0*([0-9]{1,4})\s*", _text(value))
    if match is None:
        return None
    return f"RFC {int(match.group(1)):04d}"


def _author_surname(value: object) -> str:
    text = re.sub(r"(?i)\b(?:ed|editor)\.?\b", " ", _text(value))
    tokens = re.findall(r"[A-Za-z0-9]+", text.casefold())
    suffixes = {"jr", "sr", "ii", "iii", "iv"}
    while tokens and tokens[-1] in suffixes:
        tokens.pop()
    return tokens[-1] if tokens else ""


def _authors(value: object) -> tuple[str, ...]:
    parts = [
        part
        for part in re.split(
            r"\s*(?:;|,|\band\b|&)\s*", _text(value), flags=re.I
        )
        if part
    ]
    return tuple(filter(None, (_author_surname(part) for part in parts)))


def _status(value: object) -> str:
    return _compact(value).replace("std", "standard")


def _stream(value: object) -> str:
    compact = _compact(value)
    return STREAM_ALIASES.get(compact, compact)


def _published(value: object) -> str:
    text = _text(value).casefold()
    year_match = re.search(r"\b(19|20)[0-9]{2}\b", text)
    if year_match is None:
        return _compact(text)
    year = int(year_match.group(0))
    month: int | None = None
    for name, number in MONTHS.items():
        if re.search(rf"\b{name}\b", text):
            month = number
            break
    if month is None:
        numeric = re.search(rf"\b{year}[-/]([01]?[0-9])\b", text)
        if numeric is not None and 1 <= int(numeric.group(1)) <= 12:
            month = int(numeric.group(1))
    return f"{year:04d}-{month:02d}" if month is not None else f"{year:04d}"


def _field_equal(field: str, left: object, right: object) -> bool:
    if field == "Authors":
        return bool(_authors(right)) and _authors(left) == _authors(right)
    if field == "Status":
        return bool(_status(right)) and _status(left) == _status(right)
    if field == "Stream":
        return bool(_stream(right)) and _stream(left) == _stream(right)
    if field == "Published":
        return bool(_published(right)) and _published(left) == _published(right)
    return bool(_compact(right)) and _compact(left) == _compact(right)


def _child_text(entry: ET.Element, name: str) -> str:
    child = entry.find(name)
    return _text("".join(child.itertext())) if child is not None else ""


def parse_rfc_index(
    raw: bytes, expected_numbers: Sequence[int]
) -> dict[str, dict[str, str]]:
    if not raw or len(raw) > MAXIMUM_RESPONSE_BYTES:
        raise ValueError("V2.54.16 RFC index bytes are invalid")
    root = ET.fromstring(raw)
    wanted = {int(value) for value in expected_numbers}
    output: dict[str, dict[str, str]] = {}
    for entry in root.findall(".//rfc-entry"):
        doc_id = _child_text(entry, "doc-id")
        match = re.fullmatch(r"(?i)RFC0*([0-9]{1,4})", doc_id)
        if match is None or int(match.group(1)) not in wanted:
            continue
        number = int(match.group(1))
        identity = f"RFC {number:04d}"
        authors = [
            _child_text(author, "name")
            for author in entry.findall("./author")
            if _child_text(author, "name")
        ]
        date = entry.find("date")
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
            "Published": _text(f"{month} {year}"),
        }
        if identity in output or any(not record[column] for column in contract.COLUMNS):
            raise ValueError("V2.54.16 RFC record is duplicate or incomplete")
        output[identity] = record
    return output


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
    if len(cells) < 3 or cells[0] != list(contract.COLUMNS):
        return [], [], False
    rows = [row for row in cells[2:] if len(row) == len(contract.COLUMNS)]
    identities = [_identity(row[0]) for row in rows]
    valid = all(identity is not None for identity in identities) and len(
        set(identities)
    ) == len(identities)
    return cells[0], rows, valid


def evaluate_prediction(
    prediction: str,
    expected_identities: Sequence[str],
    truth: Mapping[str, Mapping[str, str]],
) -> dict[str, float | int | bool]:
    expected = tuple(expected_identities)
    if len(expected) != contract.population.ROWS_PER_PAIR or len(set(expected)) != len(
        expected
    ):
        raise ValueError("V2.54.16 expected identity group drifted")
    truth_complete = all(
        identity in truth
        and isinstance(truth[identity], Mapping)
        and set(truth[identity]) == set(contract.COLUMNS)
        for identity in expected
    )
    _columns, rows, valid = _matrix(prediction)
    predicted: dict[str, list[str]] = {}
    order: list[str] = []
    if valid:
        for row in rows:
            identity = _identity(row[0])
            if identity is None or identity in predicted:
                valid = False
                break
            order.append(identity)
            predicted[identity] = row
    structural_valid = bool(valid and len(rows) == len(expected))
    invalid = not truth_complete or not structural_valid
    if invalid:
        return {
            "valid": False,
            "exact_table_success": 0,
            "entity_coverage": 0.0,
            "row_exact": 0.0,
            "cell_accuracy": 0.0,
            "column_accuracy": 0.0,
            "quality_composite": 0.0,
        }
    entity_hits = sum(identity in predicted for identity in expected)
    row_hits = 0
    cell_hits = 0
    per_field_hits = {column: 0 for column in contract.COLUMNS[1:]}
    for identity in expected:
        row = predicted.get(identity)
        if row is None:
            continue
        flags = []
        for index, column in enumerate(contract.COLUMNS[1:], 1):
            matched = _field_equal(column, row[index], truth[identity][column])
            flags.append(matched)
            cell_hits += int(matched)
            per_field_hits[column] += int(matched)
        row_hits += int(all(flags))
    key_column_accuracy = sum(
        index < len(order) and order[index] == identity
        for index, identity in enumerate(expected)
    ) / len(expected)
    column_accuracy = (
        key_column_accuracy
        + sum(per_field_hits[column] / len(expected) for column in contract.COLUMNS[1:])
    ) / len(contract.COLUMNS)
    entity_coverage = entity_hits / len(expected)
    row_exact = row_hits / len(expected)
    cell_accuracy = cell_hits / (len(expected) * (len(contract.COLUMNS) - 1))
    composite = (entity_coverage + row_exact + cell_accuracy + column_accuracy) / 4
    exact = int(
        order == list(expected)
        and entity_hits == len(expected)
        and cell_hits == len(expected) * (len(contract.COLUMNS) - 1)
    )
    return {
        "valid": True,
        "exact_table_success": exact,
        "entity_coverage": entity_coverage,
        "row_exact": row_exact,
        "cell_accuracy": cell_accuracy,
        "column_accuracy": column_accuracy,
        "quality_composite": composite,
    }


def _groups() -> dict[int, tuple[str, ...]]:
    identities = contract.population.identity_vector()
    return {
        index: tuple(
            identities[
                index * contract.population.ROWS_PER_PAIR : (index + 1)
                * contract.population.ROWS_PER_PAIR
            ]
        )
        for index in range(contract.PAIR_COUNT)
    }


def evaluate_rows(
    rows: Sequence[Mapping[str, Any]], truth: Mapping[str, Mapping[str, str]]
) -> dict[str, Any]:
    checked = [forward_runner.validate_task_row(row) for row in rows]
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked]
        != [task["opaque_id"] for task in contract.task_vector()]
    ):
        raise ValueError("V2.54.16 frozen row denominator drifted")
    groups = _groups()
    values: dict[str, list[dict[str, float | int | bool]]] = {
        branch: [] for branch in contract.BRANCHES
    }
    by_pair: dict[int, dict[str, dict[str, float | int | bool]]] = {
        index: {} for index in range(contract.PAIR_COUNT)
    }
    for row in checked:
        pair = int(row["pair_index"])
        branch = str(row["route_branch"])
        metric = evaluate_prediction(row["prediction"], groups[pair], truth)
        values[branch].append(metric)
        by_pair[pair][branch] = metric
    aggregate: dict[str, Any] = {}
    for branch in contract.BRANCHES:
        metrics = values[branch]
        if len(metrics) != contract.PAIR_COUNT:
            raise ValueError("V2.54.16 branch denominator drifted")
        aggregate[branch] = {
            "tasks": contract.PAIR_COUNT,
            "valid_tasks": sum(metric["valid"] is True for metric in metrics),
            "invalid_tasks": sum(metric["valid"] is False for metric in metrics),
            "fallback_tasks": sum(
                row["prediction_kind"] == "fallback"
                and row["route_branch"] == branch
                for row in checked
            ),
            "exact_table_successes": sum(
                int(metric["exact_table_success"]) for metric in metrics
            ),
            **{
                name: sum(float(metric[name]) for metric in metrics)
                / contract.PAIR_COUNT
                for name in METRICS
            },
        }
    stable = aggregate[route.STABLE_BRANCH]
    present = aggregate[route.MEMBERSHIP_BRANCH]
    delta = {
        "exact_table_successes": present["exact_table_successes"]
        - stable["exact_table_successes"],
        "valid_tasks": present["valid_tasks"] - stable["valid_tasks"],
        "invalid_tasks": present["invalid_tasks"] - stable["invalid_tasks"],
        "fallback_tasks": present["fallback_tasks"] - stable["fallback_tasks"],
        **{name: present[name] - stable[name] for name in METRICS},
    }
    pair_exact = {"present_win": 0, "tie": 0, "present_loss": 0}
    pair_composite = {"present_win": 0, "tie": 0, "present_loss": 0}
    for pair in range(contract.PAIR_COUNT):
        if set(by_pair[pair]) != set(contract.BRANCHES):
            raise ValueError("V2.54.16 pair branch surface drifted")
        left = by_pair[pair][route.STABLE_BRANCH]
        right = by_pair[pair][route.MEMBERSHIP_BRANCH]
        exact_delta = int(right["exact_table_success"]) - int(
            left["exact_table_success"]
        )
        exact_key = (
            "present_win" if exact_delta > 0 else "present_loss" if exact_delta < 0 else "tie"
        )
        pair_exact[exact_key] += 1
        composite_delta = float(right["quality_composite"]) - float(
            left["quality_composite"]
        )
        composite_key = (
            "present_win"
            if composite_delta > 1e-12
            else "present_loss"
            if composite_delta < -1e-12
            else "tie"
        )
        pair_composite[composite_key] += 1
    return {
        "branches": aggregate,
        "membership_present_minus_absent": delta,
        "paired_exact_disposition": pair_exact,
        "paired_composite_disposition": pair_composite,
    }


def quality_decision(metrics: Mapping[str, Any]) -> dict[str, Any]:
    delta = metrics.get("membership_present_minus_absent")
    branches = metrics.get("branches")
    if not isinstance(delta, Mapping) or not isinstance(branches, Mapping):
        raise ValueError("V2.54.16 quality metrics surface drifted")
    stable = branches.get(route.STABLE_BRANCH)
    present = branches.get(route.MEMBERSHIP_BRANCH)
    if not isinstance(stable, Mapping) or not isinstance(present, Mapping):
        raise ValueError("V2.54.16 branch metrics are absent")
    checks = {
        "fixed_pair_and_task_denominator": stable.get("tasks")
        == contract.PAIR_COUNT
        and present.get("tasks") == contract.PAIR_COUNT,
        "truth_valid_for_all_fixed_tasks": stable.get("invalid_tasks") == 0
        and present.get("invalid_tasks") == 0,
        "strict_whole_table_exact_gain": delta.get("exact_table_successes", 0) > 0,
        "entity_coverage_nonregression": delta.get("entity_coverage", -1) >= 0,
        "row_exact_nonregression": delta.get("row_exact", -1) >= 0,
        "cell_accuracy_nonregression": delta.get("cell_accuracy", -1) >= 0,
        "column_accuracy_nonregression": delta.get("column_accuracy", -1) >= 0,
        "quality_composite_nonregression": delta.get("quality_composite", -1) >= 0,
        "fallback_nonincrease": delta.get("fallback_tasks", 1) <= 0,
        "invalid_nonincrease": delta.get("invalid_tasks", 1) <= 0,
        "positive_signed_credit_zero": True,
        "paired_task_delta_not_claimed_as_shared_sampling_causal": True,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {"checks": checks, "failed_checks": failed, "quality_gate_passed": not failed}


def _forward_barrier() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    audit = forward_control._read(contract.FORWARD_AUDIT)
    rows = _read_rows(contract.TASK_ROWS)
    if (
        audit.get("role") != "v25415_paired_rfc_route_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is not True
        or audit.get("authorization", {}).get("deepwidebench_successor_build")
        is not False
        or not contract.sealed(audit, "audit_payload_sha256")
        or contract.sha256(ROOT / contract.FORWARD_AUDIT)
        != "01d668bb7dab8011f92488c9c86a0c812ebed27ca9b3dbc6e4f67ea7af205779"
        or contract.sha256(ROOT / contract.TASK_ROWS)
        != "ef88b552419b7ca96d07dc2e65fc2f1a034dd3e8c11f40c119978db3b6e39246"
        or contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        != "3247ff280e177d20c137e65881f2e88352c6db016dc28d6322f5d00392d7d3e7"
        or len(rows) != contract.TASK_COUNT
    ):
        raise RuntimeError("V2.54.16 pushed forward barrier drifted")
    return audit, rows


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    head, target = _clean_pushed() if require_clean else ("build-only", "build-only")
    audit, _rows = _forward_barrier()
    tests = base_audit._test(TEST.name, EXPECTED_TESTS)
    future = (
        BUILD_AUDIT,
        contract.POSTFREEZE_QUALITY_PROTOCOL,
        contract.QUALITY_RESULT,
        contract.QUALITY_AUDIT,
        RAW_TRUTH,
        TRUTH,
    )
    source = ROOT / SOURCE
    test = ROOT / TEST
    checks = {
        "pushed_forward_audit_exact_and_quality_authorized": bool(audit),
        "quality_tests_exact8": tests["passed"],
        "source_and_test_tracked": (
            not require_clean
            or (base_audit._tracked(SOURCE) and base_audit._tracked(TEST))
        ),
        "source_and_test_credential_literal_zero": not contract.SECRET.search(
            source.read_text(encoding="utf-8") + test.read_text(encoding="utf-8")
        ),
        "future_quality_truth_result_and_audit_surfaces_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in future
        ),
        "fixed_official_index_single_get_no_retry_contract": (
            URL == "https://www.rfc-editor.org/rfc-index.xml"
            and MAXIMUM_RESPONSE_BYTES == 20_000_000
        ),
        "fixed_eighty_identity_truth_vector": len(
            contract.population.identity_vector()
        )
        == 80,
        "fixed_failure_as_zero_metrics_and_quality_gate": bool(
            contract.quality_gate()
        ),
        "git_clean_head_equals_target_main": (
            (not require_clean) or head == target
        ),
        "network_truth_or_evaluator_not_called_by_build_audit": True,
        "entropy_information_gain_signed_credit_zero": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25416_paired_rfc_route_quality_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "source_sha256": contract.sha256(source),
        "test_sha256": contract.sha256(test),
        "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(
            ROOT / contract.PREDICTION_FREEZE
        ),
        "tests": tests,
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
        copied.get("role") != "v25416_paired_rfc_route_quality_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
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
        raise ValueError("V2.54.16 quality build audit drifted")
    return copied


def preregister(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    build = validate_build_audit(_read(BUILD_AUDIT))
    audit, rows = _forward_barrier()
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (
            contract.POSTFREEZE_QUALITY_PROTOCOL,
            contract.QUALITY_RESULT,
            contract.QUALITY_AUDIT,
            RAW_TRUTH,
            TRUTH,
        )
    ):
        raise RuntimeError("V2.54.16 quality protocol surface is not pristine")
    scoring = {
        "columns": list(contract.COLUMNS),
        "rows_per_task": contract.population.ROWS_PER_PAIR,
        "exact": "exact expected RFC order and all twenty non-key cells correct",
        "entity_coverage": "expected RFC identities present divided by four",
        "row_exact": "expected rows with all five non-key fields correct divided by four",
        "cell_accuracy": "correct non-key cells divided by twenty",
        "column_accuracy": "macro mean of ordered RFC-key accuracy and five field accuracies",
        "quality_composite": "mean(entity_coverage,row_exact,cell_accuracy,column_accuracy)",
        "invalid_prediction_or_missing_truth": "all metrics zero",
        "text_normalization": "NFKC whitespace case and punctuation normalization with ordered author surnames, stream aliases, and month-year equivalence",
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25416_paired_rfc_route_quality_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "target_main": target,
        "quality_build_audit_sha256": contract.sha256(ROOT / BUILD_AUDIT),
        "evaluator_source_sha256": build["source_sha256"],
        "evaluator_test_sha256": build["test_sha256"],
        "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(
            ROOT / contract.PREDICTION_FREEZE
        ),
        "frozen_task_count": len(rows),
        "fixed_pair_count": contract.PAIR_COUNT,
        "fixed_truth_identity_count": len(contract.population.identity_vector()),
        "fixed_truth_identity_vector_sha256": contract.payload_sha256(
            contract.population.identity_vector()
        ),
        "official_truth_url": URL,
        "truth_fetch": {
            "maximum_attempts": 1,
            "redirects": False,
            "retries": 0,
            "connect_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
            "read_timeout_seconds": READ_TIMEOUT_SECONDS,
            "maximum_response_bytes": MAXIMUM_RESPONSE_BYTES,
            "shared_one_snapshot_for_both_branches": True,
        },
        "scoring": scoring,
        "quality_gate": contract.quality_gate(),
        "prediction_freeze_and_pushed_forward_audit_precede_truth_open": True,
        "paired_tasks_have_independent_provider_effects": True,
        "paired_quality_delta_is_not_shared_sampling_causal_effect": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "one_truth_fetch_and_fixed_evaluation": True,
            "retry_refetch_revaluation_or_selective_replacement": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "protocol_payload_sha256")


def validate_quality_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25416_paired_rfc_route_quality_preregistration"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("git_head") != copied.get("target_main")
        or copied.get("frozen_task_count") != contract.TASK_COUNT
        or copied.get("fixed_pair_count") != contract.PAIR_COUNT
        or copied.get("fixed_truth_identity_count") != 80
        or copied.get("fixed_truth_identity_vector_sha256")
        != contract.payload_sha256(contract.population.identity_vector())
        or copied.get("official_truth_url") != URL
        or copied.get("truth_fetch")
        != {
            "maximum_attempts": 1,
            "redirects": False,
            "retries": 0,
            "connect_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
            "read_timeout_seconds": READ_TIMEOUT_SECONDS,
            "maximum_response_bytes": MAXIMUM_RESPONSE_BYTES,
            "shared_one_snapshot_for_both_branches": True,
        }
        or copied.get("quality_gate") != contract.quality_gate()
        or copied.get("prediction_freeze_and_pushed_forward_audit_precede_truth_open")
        is not True
        or copied.get("paired_tasks_have_independent_provider_effects") is not True
        or copied.get("paired_quality_delta_is_not_shared_sampling_causal_effect")
        is not True
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
        raise ValueError("V2.54.16 quality protocol drifted")
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


def evaluate(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_quality_protocol(_read(contract.POSTFREEZE_QUALITY_PROTOCOL))
    _audit, rows = _forward_barrier()
    for path in (RAW_TRUTH, TRUTH, contract.QUALITY_RESULT, contract.QUALITY_AUDIT):
        if (ROOT / path).exists() or (ROOT / path).is_symlink():
            raise FileExistsError(ROOT / path)
    with acquire_deepwide_api_lease(
        ROOT,
        owner="v25416_paired_rfc_route_quality_v1",
        purpose="single_postfreeze_official_rfc_index_truth_and_fixed_evaluation",
        path=ROOT / contract.LEASE_PATH,
    ):
        raw, status, failure = _fetch_once()
    records: dict[str, dict[str, str]] = {}
    parse_failure = failure
    if failure is None:
        try:
            records = parse_rfc_index(raw, contract.population.RFC_NUMBERS)
        except (ET.ParseError, ValueError) as exc:
            parse_failure = type(exc).__name__[:128]
            records = {}
    compressed = gzip.compress(raw, compresslevel=9, mtime=0)
    raw_sha = hashlib.sha256(raw).hexdigest()
    truth_artifact = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25416_postfreeze_official_rfc_truth",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "official_truth_url": URL,
            "attempt_count": 1,
            "http_status": status,
            "fetch_or_parse_failure_type": parse_failure,
            "raw_response_bytes": len(raw),
            "raw_response_sha256": raw_sha,
            "compressed_snapshot_sha256": hashlib.sha256(compressed).hexdigest(),
            "expected_identity_count": 80,
            "valid_record_count": len(records),
            "records": records,
            "one_attempt_no_redirect_retry_refetch_or_replacement": True,
            "same_snapshot_used_for_both_route_branches": True,
            "prediction_freeze_preexisted": True,
        },
        "truth_payload_sha256",
    )
    metrics = evaluate_rows(rows, records)
    decision = quality_decision(metrics)
    passed = bool(decision["quality_gate_passed"])
    result = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25416_paired_rfc_route_quality_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "status": "paired_rfc_route_quality_go"
            if passed
            else "paired_rfc_route_quality_no_go",
            "passed": passed,
            "quality_protocol_sha256": contract.sha256(
                ROOT / contract.POSTFREEZE_QUALITY_PROTOCOL
            ),
            "forward_audit_sha256": protocol["forward_audit_sha256"],
            "task_rows_sha256": protocol["task_rows_sha256"],
            "prediction_freeze_sha256": protocol["prediction_freeze_sha256"],
            "raw_truth_response_sha256": raw_sha,
            "truth_payload_sha256": truth_artifact["truth_payload_sha256"],
            "metrics": metrics,
            "quality_decision": decision,
            "fixed_denominator_failure_as_zero": True,
            "quality_evaluation_executed_once_after_prediction_freeze_and_pushed_forward_audit": True,
            "paired_tasks_have_independent_provider_effects": True,
            "paired_quality_delta_is_not_shared_sampling_causal_effect": True,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "positive_signed_credit_count": 0,
            "claim_scope": {
                "fresh_external_paired_quality_measured": True,
                "deepwidebench_quality_measured": False,
                "entropy_or_signed_credit_validated": False,
                "leaderboard_or_sota_supported": False,
            },
            "authorization": {
                "deepwidebench_successor_build": passed,
                "deepwidebench_forward_or_evaluator": False,
                "leaderboard_or_sota": False,
                "retry_refetch_revaluation_or_selective_replacement": False,
            },
        },
        "result_payload_sha256",
    )
    validate_truth(truth_artifact, compressed)
    validate_result(result, truth=truth_artifact, rows=rows)
    _publish_bytes(ROOT / RAW_TRUTH, compressed)
    _publish_json(ROOT / TRUTH, truth_artifact)
    _publish_json(ROOT / contract.QUALITY_RESULT, result)
    return result


def validate_truth(value: Mapping[str, Any], compressed: bytes) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    records = copied.get("records")
    try:
        raw = gzip.decompress(compressed)
    except (OSError, EOFError) as exc:
        raise ValueError("V2.54.16 compressed truth snapshot drifted") from exc
    if (
        copied.get("role") != "v25416_postfreeze_official_rfc_truth"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("official_truth_url") != URL
        or copied.get("attempt_count") != 1
        or copied.get("raw_response_bytes") != len(raw)
        or copied.get("raw_response_sha256") != hashlib.sha256(raw).hexdigest()
        or copied.get("compressed_snapshot_sha256")
        != hashlib.sha256(compressed).hexdigest()
        or copied.get("expected_identity_count") != 80
        or not isinstance(records, Mapping)
        or copied.get("valid_record_count") != len(records)
        or copied.get("one_attempt_no_redirect_retry_refetch_or_replacement")
        is not True
        or copied.get("same_snapshot_used_for_both_route_branches") is not True
        or copied.get("prediction_freeze_preexisted") is not True
        or not contract.sealed(copied, "truth_payload_sha256")
    ):
        raise ValueError("V2.54.16 truth artifact drifted")
    if copied.get("fetch_or_parse_failure_type") is None:
        if parse_rfc_index(raw, contract.population.RFC_NUMBERS) != dict(records):
            raise ValueError("V2.54.16 truth extraction replay drifted")
    elif records:
        raise ValueError("V2.54.16 failed truth artifact has records")
    return copied


def validate_result(
    value: Mapping[str, Any],
    *,
    truth: Mapping[str, Any] | None = None,
    rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    metrics = copied.get("metrics")
    decision = copied.get("quality_decision")
    passed = copied.get("passed") is True
    if (
        copied.get("role") != "v25416_paired_rfc_route_quality_result"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("status")
        != ("paired_rfc_route_quality_go" if passed else "paired_rfc_route_quality_no_go")
        or not isinstance(metrics, Mapping)
        or not isinstance(decision, Mapping)
        or quality_decision(metrics) != dict(decision)
        or passed is not decision["quality_gate_passed"]
        or copied.get("fixed_denominator_failure_as_zero") is not True
        or copied.get(
            "quality_evaluation_executed_once_after_prediction_freeze_and_pushed_forward_audit"
        )
        is not True
        or copied.get("paired_tasks_have_independent_provider_effects") is not True
        or copied.get("paired_quality_delta_is_not_shared_sampling_causal_effect")
        is not True
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("claim_scope")
        != {
            "fresh_external_paired_quality_measured": True,
            "deepwidebench_quality_measured": False,
            "entropy_or_signed_credit_validated": False,
            "leaderboard_or_sota_supported": False,
        }
        or copied.get("authorization")
        != {
            "deepwidebench_successor_build": passed,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_refetch_revaluation_or_selective_replacement": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.54.16 quality result drifted")
    if truth is not None and rows is not None:
        records = truth.get("records")
        if (
            not isinstance(records, Mapping)
            or copied["truth_payload_sha256"] != truth.get("truth_payload_sha256")
            or copied["metrics"] != evaluate_rows(rows, records)
        ):
            raise ValueError("V2.54.16 result/truth replay drifted")
    return copied


def audit_result(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_quality_protocol(_read(contract.POSTFREEZE_QUALITY_PROTOCOL))
    rows = _read_rows(contract.TASK_ROWS)
    compressed = (ROOT / RAW_TRUTH).read_bytes()
    truth = validate_truth(_read(TRUTH), compressed)
    result = validate_result(_read(contract.QUALITY_RESULT), truth=truth, rows=rows)
    checks = {
        "quality_protocol_valid": bool(protocol),
        "raw_snapshot_truth_and_result_hash_bound": (
            result["raw_truth_response_sha256"] == truth["raw_response_sha256"]
            and result["truth_payload_sha256"] == truth["truth_payload_sha256"]
        ),
        "truth_extraction_replays_exactly": True,
        "fixed_forty_predictions_evaluated_once": sum(
            branch["tasks"] for branch in result["metrics"]["branches"].values()
        )
        == contract.TASK_COUNT,
        "quality_metrics_and_decision_recompute_exactly": result["metrics"]
        == evaluate_rows(rows, truth["records"])
        and result["quality_decision"] == quality_decision(result["metrics"]),
        "failure_as_zero_and_no_selective_retry": result[
            "fixed_denominator_failure_as_zero"
        ]
        is True
        and truth["one_attempt_no_redirect_retry_refetch_or_replacement"] is True,
        "paired_delta_not_misclaimed_as_causal": result[
            "paired_quality_delta_is_not_shared_sampling_causal_effect"
        ]
        is True,
        "entropy_information_gain_signed_credit_zero": result[
            "positive_signed_credit_count"
        ]
        == 0,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == _read(contract.PROTOCOL)["protected_watchers"],
        "shared_api_lease_released": forward_control._lease_inactive(),
        "audit_calls_no_network_model_search_fetch_or_deepwidebench_evaluator": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    valid = not findings
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25416_paired_rfc_route_quality_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "quality_protocol_sha256": contract.sha256(
            ROOT / contract.POSTFREEZE_QUALITY_PROTOCOL
        ),
        "raw_truth_snapshot_sha256": contract.sha256(ROOT / RAW_TRUTH),
        "truth_sha256": contract.sha256(ROOT / TRUTH),
        "quality_result_sha256": contract.sha256(ROOT / contract.QUALITY_RESULT),
        "checks": checks,
        "findings": findings,
        "audit_valid": valid,
        "quality_gate_passed": result["passed"],
        "authorization": {
            "deepwidebench_successor_build": valid and result["passed"],
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_refetch_revaluation_or_selective_replacement": False,
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
        value, path = preregister(), contract.POSTFREEZE_QUALITY_PROTOCOL
    elif args.command == "evaluate":
        value = evaluate()
        print(
            json.dumps(
                {
                    "path": str(contract.QUALITY_RESULT),
                    "status": value["status"],
                    "passed": value["passed"],
                    "metrics": value["metrics"],
                    "authorization": value["authorization"],
                },
                sort_keys=True,
            )
        )
        return
    else:
        value, path = audit_result(), contract.QUALITY_AUDIT
    if value.get("findings"):
        raise RuntimeError(value["findings"])
    _publish_json(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value.get("role"),
                "audit_valid": value.get("audit_valid"),
                "findings": value.get("findings"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
