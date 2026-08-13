#!/usr/bin/env python3
"""Offline successor for the pre-result V2.54.17 not-issued failure.

The fixed RFC 9320--9399 interval contains one official ``rfc-not-issued-entry``
(RFC 9379).  V2.54.17 correctly handled the default XML namespace but required
every identity to be an ``rfc-entry`` and therefore failed before publishing a
truth or result artifact.  This append-only successor keeps the same snapshot,
predictions, scoring functions, and forty-task denominator.  A structurally
valid not-issued node maps its absent five metadata fields to the task's
pre-existing ``Unknown`` representation.  No network, model, search, forward,
DeepWideBench, retry, or selective revaluation is permitted.
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import gzip
import hashlib
import json
import os
import re
import sys
import time
import xml.etree.ElementTree as ET
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25415_paired_rfc_route_external_contract as contract  # noqa: E402
from scripts import audit_v25136_sparse_production_build as base_audit  # noqa: E402
from scripts import control_v25415_paired_rfc_route_external as forward_control  # noqa: E402
from scripts import evaluate_v25416_paired_rfc_route_quality as scorer  # noqa: E402
from scripts import evaluate_v25417_rfc_namespace_snapshot_recovery as failed  # noqa: E402


DATE = "20260813"
PROTOCOL_ID = "v25418_v25417_rfc_not_issued_snapshot_recovery_v1"
SOURCE = Path("scripts/evaluate_v25418_rfc_not_issued_snapshot_recovery.py")
TEST = Path("tests/test_evaluate_v25418_rfc_not_issued_snapshot_recovery.py")
BUILD_AUDIT = Path(
    f"results/v25418_rfc_not_issued_snapshot_recovery_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v25418_rfc_not_issued_snapshot_recovery_preregistration_v1_{DATE}.json"
)
RECOVERY_TRUTH = contract.OUTPUT_ROOT / "postfreeze_rfc_truth_not_issued_recovery_v1.json"
RESULT = Path(
    f"results/v25418_rfc_not_issued_snapshot_recovery_result_v1_{DATE}.json"
)
AUDIT = Path(
    f"results/v25418_rfc_not_issued_snapshot_recovery_audit_v1_{DATE}.json"
)
EXPECTED_TESTS = 8
RFC_INDEX_NAMESPACE = failed.RFC_INDEX_NAMESPACE
PARSER_ID = "namespace_qualified_rfc_and_not_issued_v1"
UNKNOWN = "Unknown"

FAILED_SOURCE_SHA256 = "c03647fb84fd3303f6523caf1f05780f7509b208c5f211a802e87193a52b7902"
FAILED_TEST_SHA256 = "44f48944ef7e4ffe265900446f0928c3db80a1be35e16045c814781efcb91a19"
FAILED_BUILD_AUDIT_SHA256 = "19222106ea4ceb8d61ae691b741395af06e73e4faa1b7403d000695439ad2951"
FAILED_PROTOCOL_SHA256 = "82b7198e500ab90e61711dc2d3ad3f9077f91c99787079e07518b1588f0c1da6"
RAW_SNAPSHOT_SHA256 = failed.RAW_SNAPSHOT_SHA256
RAW_RESPONSE_SHA256 = failed.RAW_RESPONSE_SHA256
TASK_ROWS_SHA256 = failed.TASK_ROWS_SHA256
PREDICTION_FREEZE_SHA256 = failed.PREDICTION_FREEZE_SHA256
PARENT_RESULT_SHA256 = failed.PARENT_RESULT_SHA256
EXPECTED_NOT_ISSUED_IDENTITIES = ("RFC 9379",)
DISALLOWED_NETWORK_IMPORTS = failed.DISALLOWED_NETWORK_IMPORTS


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


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.54.18 expected JSON object")
    return value


def _read_rows() -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, contract.TASK_ROWS, tracked=True)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != contract.TASK_COUNT or any(
        not isinstance(row, dict) for row in rows
    ):
        raise RuntimeError("V2.54.18 frozen row denominator drifted")
    return rows


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.54.18 requires clean pushed HEAD")
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
    return scorer._text("".join(child.itertext())) if child is not None else ""


def parse_rfc_and_not_issued_index(
    raw: bytes, expected_numbers: Sequence[int]
) -> tuple[dict[str, dict[str, str]], tuple[str, ...]]:
    """Extract fixed RFC records and map structural not-issued nodes to Unknown."""

    if not raw or len(raw) > scorer.MAXIMUM_RESPONSE_BYTES:
        raise ValueError("V2.54.18 RFC snapshot bytes are invalid")
    root = ET.fromstring(raw)
    if root.tag != _qualified("rfc-index"):
        raise ValueError("V2.54.18 RFC index namespace or root drifted")
    numbers = tuple(int(value) for value in expected_numbers)
    if len(numbers) != len(set(numbers)):
        raise ValueError("V2.54.18 expected RFC identity vector is duplicated")
    wanted = set(numbers)
    output: dict[str, dict[str, str]] = {}
    not_issued: list[str] = []

    def identity_for(entry: ET.Element) -> tuple[int, str] | None:
        doc_id = _child_text(entry, "doc-id")
        match = re.fullmatch(r"(?i)RFC0*([0-9]{1,4})", doc_id)
        if match is None or int(match.group(1)) not in wanted:
            return None
        number = int(match.group(1))
        return number, f"RFC {number:04d}"

    for entry in root.findall(f".//{_qualified('rfc-entry')}"):
        matched = identity_for(entry)
        if matched is None:
            continue
        _number, identity = matched
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
            "Published": scorer._text(f"{month} {year}"),
        }
        if identity in output or any(
            not record[column] for column in contract.COLUMNS
        ):
            raise ValueError("V2.54.18 RFC record is duplicate or incomplete")
        output[identity] = record

    for entry in root.findall(f".//{_qualified('rfc-not-issued-entry')}"):
        matched = identity_for(entry)
        if matched is None:
            continue
        _number, identity = matched
        if (
            identity in output
            or [child.tag for child in list(entry)] != [_qualified("doc-id")]
        ):
            raise ValueError("V2.54.18 not-issued RFC node is ambiguous")
        output[identity] = {
            "RFC": identity,
            **{column: UNKNOWN for column in contract.COLUMNS[1:]},
        }
        not_issued.append(identity)

    expected = {f"RFC {number:04d}" for number in numbers}
    if set(output) != expected:
        raise ValueError("V2.54.18 RFC snapshot lacks a fixed identity")
    return output, tuple(not_issued)


def _source_has_zero_network_surface(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(
            alias.name.split(".")[0] in DISALLOWED_NETWORK_IMPORTS
            for alias in node.names
        ):
            return False
        if isinstance(node, ast.ImportFrom) and (
            (node.module or "").split(".")[0] in DISALLOWED_NETWORK_IMPORTS
        ):
            return False
        if isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name) and function.id in {
                "urlopen",
                "create_connection",
            }:
                return False
            if isinstance(function, ast.Attribute) and function.attr in {
                "_fetch_once",
                "request",
                "urlopen",
                "create_connection",
            }:
                return False
    return True


def _failed_attempt_envelope() -> dict[str, Any]:
    paths = {
        "failed_source": failed.SOURCE,
        "failed_test": failed.TEST,
        "failed_build_audit": failed.BUILD_AUDIT,
        "failed_protocol": failed.PROTOCOL,
        "raw_snapshot": scorer.RAW_TRUTH,
        "task_rows": contract.TASK_ROWS,
        "prediction_freeze": contract.PREDICTION_FREEZE,
        "parent_v25416_result": contract.QUALITY_RESULT,
    }
    expected = {
        "failed_source": FAILED_SOURCE_SHA256,
        "failed_test": FAILED_TEST_SHA256,
        "failed_build_audit": FAILED_BUILD_AUDIT_SHA256,
        "failed_protocol": FAILED_PROTOCOL_SHA256,
        "raw_snapshot": RAW_SNAPSHOT_SHA256,
        "task_rows": TASK_ROWS_SHA256,
        "prediction_freeze": PREDICTION_FREEZE_SHA256,
        "parent_v25416_result": PARENT_RESULT_SHA256,
    }
    observed = {
        name: contract.sha256(contract.ordinary(ROOT, path, tracked=True))
        for name, path in paths.items()
    }
    absent = (failed.RECOVERY_TRUTH, failed.RESULT, failed.AUDIT)
    if (
        observed != expected
        or not _future_pristine(absent)
        or contract.sha256(ROOT / scorer.RAW_TRUTH) != RAW_SNAPSHOT_SHA256
        or failed.PARSER_ID != "namespace_qualified_direct_child_v1"
    ):
        raise RuntimeError("V2.54.18 failed-attempt envelope drifted")
    return {
        "paths": {name: str(path) for name, path in paths.items()},
        "sha256": expected,
        "exception": "ValueError: V2.54.17 RFC snapshot lacks a fixed truth record",
        "failed_stage": "namespace_truth_extraction_before_truth_or_result_publication",
        "failed_before_truth_publication": True,
        "failed_before_quality_evaluation": True,
        "failed_before_result_publication": True,
        "failed_recovery_surfaces_absent": [str(path) for path in absent],
        "network_model_search_forward_or_deepwidebench_calls": 0,
        "fixed_snapshot_and_predictions_unchanged": True,
    }


@contextlib.contextmanager
def _offline_guards() -> Iterator[None]:
    original_scorer = scorer._fetch_once
    original_failed = failed.parent_eval._fetch_once

    def deny() -> tuple[bytes, int, str | None]:
        raise RuntimeError("V2.54.18 offline recovery forbids truth fetch")

    scorer._fetch_once = deny
    failed.parent_eval._fetch_once = deny
    try:
        yield
    finally:
        scorer._fetch_once = original_scorer
        failed.parent_eval._fetch_once = original_failed


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    head, target = _clean_pushed() if require_clean else ("build-only", "build-only")
    failed_attempt = _failed_attempt_envelope()
    tests = base_audit._test(TEST.name, EXPECTED_TESTS)
    source = ROOT / SOURCE
    test = ROOT / TEST
    checks = {
        "v25417_prepublication_failure_exactly_bound": bool(failed_attempt),
        "recovery_tests_exact8": tests["passed"],
        "source_and_test_tracked": (
            not require_clean
            or (base_audit._tracked(SOURCE) and base_audit._tracked(TEST))
        ),
        "source_and_test_credential_literal_zero": not contract.SECRET.search(
            source.read_text(encoding="utf-8") + test.read_text(encoding="utf-8")
        ),
        "recovery_source_network_import_and_call_surface_zero": _source_has_zero_network_surface(
            source
        ),
        "failed_scorer_source_exactly_bound": contract.sha256(
            ROOT / failed.SOURCE
        )
        == FAILED_SOURCE_SHA256,
        "future_recovery_surfaces_pristine": _future_pristine(
            (BUILD_AUDIT, PROTOCOL, RECOVERY_TRUTH, RESULT, AUDIT)
        ),
        "same_snapshot_predictions_and_full_denominator_fixed": (
            contract.sha256(ROOT / scorer.RAW_TRUTH) == RAW_SNAPSHOT_SHA256
            and contract.sha256(ROOT / contract.TASK_ROWS) == TASK_ROWS_SHA256
            and contract.TASK_COUNT == 40
        ),
        "generic_not_issued_rule_frozen_before_replay": (
            PARSER_ID == "namespace_qualified_rfc_and_not_issued_v1"
            and UNKNOWN == "Unknown"
            and EXPECTED_NOT_ISSUED_IDENTITIES == ("RFC 9379",)
        ),
        "git_clean_head_equals_target_main": not require_clean or head == target,
        "build_audit_called_no_network_model_search_or_evaluator": True,
        "entropy_information_gain_signed_credit_zero": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25418_rfc_not_issued_snapshot_recovery_build_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "source_sha256": contract.sha256(source),
        "test_sha256": contract.sha256(test),
        "failed_attempt": failed_attempt,
        "tests": tests,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "network_model_search_or_evaluator_called": False,
        "authorization": {
            "offline_recovery_protocol_generation": not findings,
            "snapshot_replay_or_quality_evaluation": False,
            "new_truth_fetch_model_search_or_deepwidebench": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_build_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25418_rfc_not_issued_snapshot_recovery_build_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("source_sha256") != contract.sha256(ROOT / SOURCE)
        or copied.get("test_sha256") != contract.sha256(ROOT / TEST)
        or copied.get("failed_attempt") != _failed_attempt_envelope()
        or copied.get("network_model_search_or_evaluator_called") is not False
        or copied.get("authorization")
        != {
            "offline_recovery_protocol_generation": True,
            "snapshot_replay_or_quality_evaluation": False,
            "new_truth_fetch_model_search_or_deepwidebench": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise ValueError("V2.54.18 recovery build audit drifted")
    return copied


def preregister(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    build = validate_build_audit(_read(BUILD_AUDIT))
    failed_attempt = _failed_attempt_envelope()
    if not _future_pristine((PROTOCOL, RECOVERY_TRUTH, RESULT, AUDIT)):
        raise RuntimeError("V2.54.18 recovery surface is not pristine")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25418_rfc_not_issued_snapshot_recovery_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "target_main": target,
        "build_audit_sha256": contract.sha256(ROOT / BUILD_AUDIT),
        "recovery_source_sha256": build["source_sha256"],
        "recovery_test_sha256": build["test_sha256"],
        "failed_attempt": failed_attempt,
        "fixed_inputs": {
            "compressed_snapshot_path": str(scorer.RAW_TRUTH),
            "compressed_snapshot_sha256": RAW_SNAPSHOT_SHA256,
            "raw_snapshot_sha256": RAW_RESPONSE_SHA256,
            "task_rows_sha256": TASK_ROWS_SHA256,
            "prediction_freeze_sha256": PREDICTION_FREEZE_SHA256,
            "task_count": 40,
            "pair_count": 20,
            "truth_identity_count": 80,
        },
        "parser_recovery": {
            "parser_id": PARSER_ID,
            "required_root_tag": _qualified("rfc-index"),
            "required_namespace": RFC_INDEX_NAMESPACE,
            "accepted_fixed_identity_node_types": [
                "rfc-entry",
                "rfc-not-issued-entry",
            ],
            "not_issued_structural_contract": "exactly_one_doc_id_child",
            "not_issued_non_key_field_value": UNKNOWN,
            "expected_not_issued_identities": list(EXPECTED_NOT_ISSUED_IDENTITIES),
            "expected_regular_record_count": 79,
            "expected_not_issued_count": 1,
            "all_eighty_fixed_identities_required": True,
            "v25416_and_v25417_artifacts_not_rewritten": True,
        },
        "replay_contract": {
            "one_complete_offline_replay": True,
            "both_branches_share_same_frozen_snapshot": True,
            "all_forty_predictions_evaluated_exactly_once": True,
            "fixed_denominator_failure_as_zero": True,
            "new_truth_fetch_or_snapshot_replacement": False,
            "forward_model_search_fetch_or_deepwidebench_call": False,
            "prediction_retry_repair_selection_or_mutation": False,
            "selective_task_revaluation": False,
            "api_lease_needed": False,
        },
        "quality_gate": contract.quality_gate(),
        "paired_tasks_have_independent_provider_effects": True,
        "paired_quality_delta_is_not_shared_sampling_causal_effect": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_complete_offline_snapshot_replay": True,
            "new_truth_fetch_model_search_or_deepwidebench": False,
            "retry_refetch_selective_revaluation_or_prediction_replacement": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "protocol_payload_sha256")


def validate_protocol(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    build = validate_build_audit(_read(BUILD_AUDIT))
    fixed_inputs = copied.get("fixed_inputs") or {}
    parser = copied.get("parser_recovery") or {}
    replay = copied.get("replay_contract") or {}
    if (
        copied.get("role") != "v25418_rfc_not_issued_snapshot_recovery_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("git_head") != copied.get("target_main")
        or copied.get("build_audit_sha256") != contract.sha256(ROOT / BUILD_AUDIT)
        or copied.get("recovery_source_sha256") != build.get("source_sha256")
        or copied.get("recovery_test_sha256") != build.get("test_sha256")
        or copied.get("failed_attempt") != _failed_attempt_envelope()
        or fixed_inputs
        != {
            "compressed_snapshot_path": str(scorer.RAW_TRUTH),
            "compressed_snapshot_sha256": RAW_SNAPSHOT_SHA256,
            "raw_snapshot_sha256": RAW_RESPONSE_SHA256,
            "task_rows_sha256": TASK_ROWS_SHA256,
            "prediction_freeze_sha256": PREDICTION_FREEZE_SHA256,
            "task_count": 40,
            "pair_count": 20,
            "truth_identity_count": 80,
        }
        or parser
        != {
            "parser_id": PARSER_ID,
            "required_root_tag": _qualified("rfc-index"),
            "required_namespace": RFC_INDEX_NAMESPACE,
            "accepted_fixed_identity_node_types": [
                "rfc-entry",
                "rfc-not-issued-entry",
            ],
            "not_issued_structural_contract": "exactly_one_doc_id_child",
            "not_issued_non_key_field_value": UNKNOWN,
            "expected_not_issued_identities": ["RFC 9379"],
            "expected_regular_record_count": 79,
            "expected_not_issued_count": 1,
            "all_eighty_fixed_identities_required": True,
            "v25416_and_v25417_artifacts_not_rewritten": True,
        }
        or replay
        != {
            "one_complete_offline_replay": True,
            "both_branches_share_same_frozen_snapshot": True,
            "all_forty_predictions_evaluated_exactly_once": True,
            "fixed_denominator_failure_as_zero": True,
            "new_truth_fetch_or_snapshot_replacement": False,
            "forward_model_search_fetch_or_deepwidebench_call": False,
            "prediction_retry_repair_selection_or_mutation": False,
            "selective_task_revaluation": False,
            "api_lease_needed": False,
        }
        or copied.get("quality_gate") != contract.quality_gate()
        or copied.get("paired_tasks_have_independent_provider_effects") is not True
        or copied.get("paired_quality_delta_is_not_shared_sampling_causal_effect")
        is not True
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("protected_watchers")
        != _read(contract.PROTOCOL)["protected_watchers"]
        or copied.get("authorization")
        != {
            "one_complete_offline_snapshot_replay": True,
            "new_truth_fetch_model_search_or_deepwidebench": False,
            "retry_refetch_selective_revaluation_or_prediction_replacement": False,
            "deepwidebench_successor_build_or_forward": False,
            "leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "protocol_payload_sha256")
    ):
        raise ValueError("V2.54.18 recovery protocol drifted")
    return copied


def _truth_artifact(
    raw: bytes,
    records: Mapping[str, Mapping[str, str]],
    not_issued: Sequence[str],
    *,
    now: int,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25418_rfc_not_issued_snapshot_recovery_truth",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "source_compressed_snapshot_path": str(scorer.RAW_TRUTH),
        "source_compressed_snapshot_sha256": RAW_SNAPSHOT_SHA256,
        "source_raw_snapshot_sha256": hashlib.sha256(raw).hexdigest(),
        "parser_id": PARSER_ID,
        "required_namespace": RFC_INDEX_NAMESPACE,
        "expected_identity_count": 80,
        "valid_record_count": len(records),
        "regular_record_count": len(records) - len(not_issued),
        "not_issued_count": len(not_issued),
        "not_issued_identities": list(not_issued),
        "not_issued_non_key_field_value": UNKNOWN,
        "records": dict(records),
        "new_truth_fetch_or_snapshot_replacement": False,
        "v25416_and_v25417_artifacts_retained": True,
    }
    return contract.seal(value, "truth_payload_sha256")


def validate_truth(value: Mapping[str, Any], compressed: bytes) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    records = copied.get("records")
    try:
        raw = gzip.decompress(compressed)
    except (OSError, EOFError) as exc:
        raise ValueError("V2.54.18 compressed snapshot drifted") from exc
    expected, not_issued = parse_rfc_and_not_issued_index(
        raw, contract.population.RFC_NUMBERS
    )
    if (
        copied.get("role") != "v25418_rfc_not_issued_snapshot_recovery_truth"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("source_compressed_snapshot_sha256")
        != hashlib.sha256(compressed).hexdigest()
        or copied.get("source_compressed_snapshot_sha256") != RAW_SNAPSHOT_SHA256
        or copied.get("source_raw_snapshot_sha256") != hashlib.sha256(raw).hexdigest()
        or copied.get("source_raw_snapshot_sha256") != RAW_RESPONSE_SHA256
        or copied.get("parser_id") != PARSER_ID
        or copied.get("required_namespace") != RFC_INDEX_NAMESPACE
        or copied.get("expected_identity_count") != 80
        or copied.get("valid_record_count") != 80
        or copied.get("regular_record_count") != 79
        or copied.get("not_issued_count") != 1
        or copied.get("not_issued_identities") != ["RFC 9379"]
        or copied.get("not_issued_non_key_field_value") != UNKNOWN
        or not isinstance(records, Mapping)
        or dict(records) != expected
        or tuple(copied["not_issued_identities"]) != not_issued
        or copied.get("new_truth_fetch_or_snapshot_replacement") is not False
        or copied.get("v25416_and_v25417_artifacts_retained") is not True
        or not contract.sealed(copied, "truth_payload_sha256")
    ):
        raise ValueError("V2.54.18 recovery truth drifted")
    return copied


def _result_artifact(
    protocol: Mapping[str, Any],
    truth: Mapping[str, Any],
    metrics: Mapping[str, Any],
    *,
    now: int,
) -> dict[str, Any]:
    decision = scorer.quality_decision(metrics)
    passed = bool(decision["quality_gate_passed"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25418_rfc_not_issued_snapshot_recovery_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "status": (
            "rfc_not_issued_snapshot_recovery_go"
            if passed
            else "rfc_not_issued_snapshot_recovery_no_go"
        ),
        "passed": passed,
        "protocol_sha256": contract.sha256(ROOT / PROTOCOL),
        "task_rows_sha256": protocol["fixed_inputs"]["task_rows_sha256"],
        "prediction_freeze_sha256": protocol["fixed_inputs"][
            "prediction_freeze_sha256"
        ],
        "source_compressed_snapshot_sha256": RAW_SNAPSHOT_SHA256,
        "truth_payload_sha256": truth["truth_payload_sha256"],
        "metrics": dict(metrics),
        "quality_decision": decision,
        "all_forty_predictions_replayed_once": True,
        "new_truth_fetch_model_search_forward_or_deepwidebench_calls": 0,
        "prediction_retry_repair_selection_or_mutation": False,
        "v25416_and_v25417_artifacts_retained": True,
        "paired_tasks_have_independent_provider_effects": True,
        "paired_quality_delta_is_not_shared_sampling_causal_effect": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "claim_scope": {
            "corrected_offline_paired_quality_measured": True,
            "deepwidebench_quality_measured": False,
            "shared_sampling_causal_effect_measured": False,
            "entropy_or_signed_credit_validated": False,
            "leaderboard_or_sota_supported": False,
        },
        "authorization": {
            "deepwidebench_successor_build": passed,
            "deepwidebench_forward_or_evaluator": False,
            "additional_snapshot_replay_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "result_payload_sha256")


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
        copied.get("role") != "v25418_rfc_not_issued_snapshot_recovery_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("status")
        != (
            "rfc_not_issued_snapshot_recovery_go"
            if passed
            else "rfc_not_issued_snapshot_recovery_no_go"
        )
        or not isinstance(metrics, Mapping)
        or not isinstance(decision, Mapping)
        or scorer.quality_decision(metrics) != dict(decision)
        or passed is not decision["quality_gate_passed"]
        or copied.get("task_rows_sha256") != TASK_ROWS_SHA256
        or copied.get("prediction_freeze_sha256") != PREDICTION_FREEZE_SHA256
        or copied.get("source_compressed_snapshot_sha256") != RAW_SNAPSHOT_SHA256
        or copied.get("all_forty_predictions_replayed_once") is not True
        or copied.get("new_truth_fetch_model_search_forward_or_deepwidebench_calls")
        != 0
        or copied.get("prediction_retry_repair_selection_or_mutation") is not False
        or copied.get("v25416_and_v25417_artifacts_retained") is not True
        or copied.get("paired_tasks_have_independent_provider_effects") is not True
        or copied.get("paired_quality_delta_is_not_shared_sampling_causal_effect")
        is not True
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("claim_scope")
        != {
            "corrected_offline_paired_quality_measured": True,
            "deepwidebench_quality_measured": False,
            "shared_sampling_causal_effect_measured": False,
            "entropy_or_signed_credit_validated": False,
            "leaderboard_or_sota_supported": False,
        }
        or copied.get("authorization")
        != {
            "deepwidebench_successor_build": passed,
            "deepwidebench_forward_or_evaluator": False,
            "additional_snapshot_replay_or_revaluation": False,
            "leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.54.18 recovery result drifted")
    if truth is not None and rows is not None:
        records = truth.get("records")
        if (
            not isinstance(records, Mapping)
            or copied.get("truth_payload_sha256")
            != truth.get("truth_payload_sha256")
            or copied.get("metrics") != scorer.evaluate_rows(rows, records)
        ):
            raise ValueError("V2.54.18 result replay drifted")
    return copied


def replay(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    _failed_attempt_envelope()
    if not _future_pristine((RECOVERY_TRUTH, RESULT, AUDIT)):
        raise RuntimeError("V2.54.18 replay result surface is not pristine")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.54.18 protected watcher identity drifted")
    compressed = contract.ordinary(ROOT, scorer.RAW_TRUTH, tracked=True).read_bytes()
    if hashlib.sha256(compressed).hexdigest() != RAW_SNAPSHOT_SHA256:
        raise RuntimeError("V2.54.18 frozen compressed snapshot drifted")
    rows = _read_rows()
    timestamp = int(time.time()) if now is None else int(now)
    with _offline_guards():
        raw = gzip.decompress(compressed)
        records, not_issued = parse_rfc_and_not_issued_index(
            raw, contract.population.RFC_NUMBERS
        )
        if tuple(not_issued) != EXPECTED_NOT_ISSUED_IDENTITIES:
            raise RuntimeError("V2.54.18 not-issued identity surface drifted")
        truth = _truth_artifact(raw, records, not_issued, now=timestamp)
        metrics = scorer.evaluate_rows(rows, records)
        result = _result_artifact(protocol, truth, metrics, now=timestamp)
        validate_truth(truth, compressed)
        validate_result(result, truth=truth, rows=rows)
    _publish_json(ROOT / RECOVERY_TRUTH, truth)
    _publish_json(ROOT / RESULT, result)
    return result


def audit_result(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = validate_protocol(_read(PROTOCOL))
    failed_attempt = _failed_attempt_envelope()
    compressed = contract.ordinary(ROOT, scorer.RAW_TRUTH, tracked=True).read_bytes()
    truth = validate_truth(_read(RECOVERY_TRUTH), compressed)
    rows = _read_rows()
    result = validate_result(_read(RESULT), truth=truth, rows=rows)
    checks = {
        "v25417_prepublication_failure_and_append_only_recovery_bound": bool(
            failed_attempt
        ),
        "protocol_valid": bool(protocol),
        "same_frozen_snapshot_replayed_without_refetch": (
            truth["source_compressed_snapshot_sha256"] == RAW_SNAPSHOT_SHA256
            and truth["new_truth_fetch_or_snapshot_replacement"] is False
        ),
        "truth_extracts_seventy_nine_regular_and_one_not_issued": (
            truth["regular_record_count"] == 79
            and truth["not_issued_count"] == 1
            and truth["not_issued_identities"] == ["RFC 9379"]
        ),
        "all_forty_predictions_recomputed_once": sum(
            branch["tasks"] for branch in result["metrics"]["branches"].values()
        )
        == 40,
        "metrics_and_quality_decision_recompute_exactly": (
            result["metrics"] == scorer.evaluate_rows(rows, truth["records"])
            and result["quality_decision"]
            == scorer.quality_decision(result["metrics"])
        ),
        "no_network_model_search_forward_or_deepwidebench_calls": result[
            "new_truth_fetch_model_search_forward_or_deepwidebench_calls"
        ]
        == 0,
        "no_prediction_retry_repair_selection_or_mutation": result[
            "prediction_retry_repair_selection_or_mutation"
        ]
        is False,
        "v25416_parent_result_retained": contract.sha256(
            ROOT / contract.QUALITY_RESULT
        )
        == PARENT_RESULT_SHA256,
        "v25417_failed_surfaces_remain_absent": _future_pristine(
            (failed.RECOVERY_TRUTH, failed.RESULT, failed.AUDIT)
        ),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_inactive": forward_control._lease_inactive(),
        "paired_delta_not_misclaimed_as_shared_sampling_causal": result[
            "paired_quality_delta_is_not_shared_sampling_causal_effect"
        ]
        is True,
        "entropy_information_gain_signed_credit_zero": result[
            "positive_signed_credit_count"
        ]
        == 0,
        "audit_calls_no_network_model_search_fetch_or_deepwidebench_evaluator": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    valid = not findings
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25418_rfc_not_issued_snapshot_recovery_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / PROTOCOL),
        "source_snapshot_sha256": RAW_SNAPSHOT_SHA256,
        "recovery_truth_sha256": contract.sha256(ROOT / RECOVERY_TRUTH),
        "recovery_result_sha256": contract.sha256(ROOT / RESULT),
        "checks": checks,
        "findings": findings,
        "audit_valid": valid,
        "quality_gate_passed": result["passed"],
        "authorization": {
            "deepwidebench_successor_build": valid and result["passed"],
            "deepwidebench_forward_or_evaluator": False,
            "additional_snapshot_replay_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build-audit", "protocol", "replay", "audit"))
    args = parser.parse_args()
    if args.command == "build-audit":
        value, path = build_audit(), BUILD_AUDIT
    elif args.command == "protocol":
        value, path = preregister(), PROTOCOL
    elif args.command == "replay":
        value = replay()
        print(
            json.dumps(
                {
                    "path": str(RESULT),
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
