#!/usr/bin/env python3
"""Append-only population erratum and aggregate candidate-funnel diagnosis.

V2.54.22 used literal tree/history scans to call RFC 9720--9799 fresh.  The
earlier consumed V2.53.91 population encoded RFC 9680--9759 through ``range``
rather than individual literals, so forty identities escaped that scan.  This
offline successor binds both frozen populations structurally, retracts only
the fresh/disjoint claim, and preserves the within-V2.54.23 shared-parent
guarded-versus-base causal comparison.

After the audited V2.54.24 quality result, this module also reports aggregate
field transitions and the content-free V2.53.69 funnel.  It persists no task
identity, question, page, prediction, truth value, or per-task metric.  It has
no network/model/search/fetch capability and cannot authorize an external or
DeepWideBench run.  Entropy/information gain receives no signed credit.
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
import os
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25391_fresh_rfc_hybrid_population as prior_population  # noqa: E402
from deepwide_agent import v25421_fresh_rfc_list_atomic_population as population  # noqa: E402
from deepwide_agent import v25423_list_atomic_shared_effect_external_contract as contract  # noqa: E402
from scripts import evaluate_v25416_paired_rfc_route_quality as scorer  # noqa: E402
from scripts import evaluate_v25424_list_atomic_shared_effect_quality as quality  # noqa: E402
from scripts import run_v25423_list_atomic_shared_effect_external as runner  # noqa: E402


DATE = "20260813"
OUTPUT = Path(
    f"results/v25425_population_overlap_and_candidate_funnel_diagnosis_v1_{DATE}.json"
)
PRIOR_POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25391_fresh_rfc_hybrid_population.py"
)
PRIOR_FORWARD_RESULT = Path(
    "results/v25393_rfc_hybrid_external_forward_result_v1_20260813.json"
)
CURRENT_POPULATION_SOURCE = Path(
    "src/deepwide_agent/v25421_fresh_rfc_list_atomic_population.py"
)
CURRENT_POPULATION_AUDIT = Path(
    "results/v25422_fresh_rfc_list_atomic_population_audit_v1_20260813.json"
)

EXPECTED_SHA256 = {
    str(PRIOR_POPULATION_SOURCE): "e85a98f5bfce7b589f80535f46b720e54058f8a86ed29891901521e327fa66f7",
    str(PRIOR_FORWARD_RESULT): "5b5b8f84713dc830c44d42dda17bbf53d4d645d7752c09f9a99bcbc5e12f95bf",
    str(CURRENT_POPULATION_SOURCE): "7efaedea46c2ba0db5c9c011d7f27e04746779115c30e1dedbfa6778c9fa2406",
    str(CURRENT_POPULATION_AUDIT): "16e776914153fda2c7c1cef2a64e3566eff2a51e9a7cfc697e2be2731b96610e",
    str(quality.RESULT): "d2543dc263f1e394cd581901e125c1fcd151706a7da53cd190029a7667f813fb",
    str(quality.AUDIT): "f6af923574fb8881bfc2fb6c909058da3643f97aa9ebea94650c198ceb2e8386",
    str(quality.TRUTH): "3e9895d99cb85d0ceee19ccb1c5a094d4013071deb0aa63f24dd39604a94ad83",
    str(contract.TASK_ROWS): "38b16257edd42c0afcc50adaad1f40b000cf2ab54d6940f2daf1a23f7395a462",
}

COUNT_FIELDS = (
    "parsed_record_count",
    "parsed_field_count",
    "verified_record_count",
    "verified_field_count",
    "verified_table_coordinate_count",
    "changed_safe_coordinate_count",
    "unchanged_verified_coordinate_count",
    "table_or_schema_rejected_field_count",
    "missing_row_rejected_field_count",
    "ambiguous_row_rejected_field_count",
    "missing_or_key_column_rejected_field_count",
    "multiple_source_coordinate_rejected_field_count",
    "conflicting_source_coordinate_rejected_field_count",
    "unsafe_or_unknown_value_rejected_field_count",
    "positive_signed_credit_count",
)


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


def _read(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.54.25 expected JSON object")
    return value


def _rows() -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, contract.TASK_ROWS, tracked=True)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return [runner.validate_task_row(row) for row in rows]


def _source_range(relative: Path, assignment: str = "RFC_NUMBERS") -> tuple[int, int]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    matches: list[tuple[int, int]] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == assignment for target in targets):
            continue
        value = node.value
        if (
            not isinstance(value, ast.Call)
            or not isinstance(value.func, ast.Name)
            or value.func.id != "tuple"
            or len(value.args) != 1
            or not isinstance(value.args[0], ast.Call)
            or not isinstance(value.args[0].func, ast.Name)
            or value.args[0].func.id != "range"
            or len(value.args[0].args) != 2
        ):
            raise ValueError("V2.54.25 RFC range assignment is not structural")
        start = ast.literal_eval(value.args[0].args[0])
        stop = ast.literal_eval(value.args[0].args[1])
        if not isinstance(start, int) or not isinstance(stop, int) or stop <= start:
            raise ValueError("V2.54.25 RFC range bounds are invalid")
        matches.append((start, stop - 1))
    if len(matches) != 1:
        raise ValueError("V2.54.25 RFC range assignment is ambiguous")
    return matches[0]


def _barrier() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    observed = {
        path: contract.sha256(contract.ordinary(ROOT, Path(path), tracked=True))
        for path in EXPECTED_SHA256
    }
    result = quality.validate_result(_read(quality.RESULT))
    audit = _read(quality.AUDIT)
    truth = _read(quality.TRUTH)
    rows = _rows()
    if (
        observed != EXPECTED_SHA256
        or result.get("passed") is not False
        or result.get("quality_decision", {}).get("failed_checks")
        != ["guarded_whole_table_exact_strict_gain"]
        or audit.get("role") != "v25424_list_atomic_shared_effect_quality_audit"
        or audit.get("audit_valid") is not True
        or audit.get("quality_gate_passed") is not False
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("new_exact220_protocol_design")
        is not False
        or truth.get("valid_record_count") != 80
        or not contract.sealed(audit, "audit_payload_sha256")
        or not contract.sealed(truth, "truth_payload_sha256")
        or len(rows) != contract.TASK_COUNT
    ):
        raise RuntimeError("V2.54.25 audited quality barrier drifted")
    return result, truth, rows


def _matrix(prediction: str) -> dict[str, dict[str, str]]:
    columns, rows, valid = scorer._matrix(prediction)
    if not valid or tuple(columns) != tuple(contract.COLUMNS):
        raise ValueError("V2.54.25 expected canonical table")
    output: dict[str, dict[str, str]] = {}
    for row in rows:
        identity = scorer._identity(row[0])
        if identity is None or identity in output:
            raise ValueError("V2.54.25 table identity drifted")
        output[identity] = dict(zip(columns, row, strict=True))
    return output


def _editor_receipt(row: Mapping[str, Any]) -> dict[str, Any]:
    runtime = row.get("runtime_result")
    parent = runtime.get("private_parent_result") if isinstance(runtime, Mapping) else None
    shared = parent.get("private_parent_result") if isinstance(parent, Mapping) else None
    receipt = shared.get("content_free_receipt") if isinstance(shared, Mapping) else None
    edit = receipt.get("changed_safe_edit_receipt") if isinstance(receipt, Mapping) else None
    if not isinstance(edit, Mapping):
        raise ValueError("V2.54.25 editor receipt is absent")
    return dict(edit)


def diagnose(*, now: int | None = None) -> dict[str, Any]:
    result, truth_artifact, rows = _barrier()
    truth = truth_artifact.get("records")
    if not isinstance(truth, Mapping):
        raise RuntimeError("V2.54.25 truth records are absent")

    prior_start, prior_end = _source_range(PRIOR_POPULATION_SOURCE)
    current_start, current_end = _source_range(CURRENT_POPULATION_SOURCE)
    overlap_start = max(prior_start, current_start)
    overlap_end = min(prior_end, current_end)
    overlap_count = max(0, overlap_end - overlap_start + 1)
    width = population.ROWS_PER_TASK
    overlap_task_count = overlap_count // width

    transition: Counter[str] = Counter()
    field_transition: Counter[str] = Counter()
    action_field: Counter[str] = Counter()
    wrong_by_arm: dict[str, Counter[str]] = {
        arm: Counter() for arm in quality.ARMS
    }
    wrong_record_by_arm: Counter[str] = Counter()
    groups = quality._groups()
    for row in rows:
        index = int(row["task_index"])
        matrices = {
            arm: _matrix(row["predictions"][arm]) for arm in quality.ARMS
        }
        for identity in groups[index]:
            for arm in quality.ARMS:
                record_wrong = False
                for column in contract.COLUMNS[1:]:
                    if not scorer._field_equal(
                        column,
                        matrices[arm][identity][column],
                        truth[identity][column],
                    ):
                        wrong_by_arm[arm][column] += 1
                        record_wrong = True
                wrong_record_by_arm[arm] += int(record_wrong)
            for column in contract.COLUMNS[1:]:
                before = matrices[quality.BASE_ARM][identity][column]
                raw = matrices[quality.RAW_ARM][identity][column]
                guarded = matrices[quality.GUARDED_ARM][identity][column]
                if before == raw:
                    continue
                action = (
                    "rejected"
                    if guarded == before
                    else "retained"
                    if guarded == raw
                    else "other"
                )
                before_ok = scorer._field_equal(column, before, truth[identity][column])
                raw_ok = scorer._field_equal(column, raw, truth[identity][column])
                disposition = (
                    "improvement"
                    if not before_ok and raw_ok
                    else "harm"
                    if before_ok and not raw_ok
                    else "neutral_correct"
                    if before_ok and raw_ok
                    else "neutral_wrong"
                )
                transition[f"{action}:{disposition}"] += 1
                field_transition[f"{column}:{action}:{disposition}"] += 1
                action_field[f"{action}:{column}"] += 1

    funnel = Counter()
    receipt_flags = Counter()
    for row in rows:
        receipt = _editor_receipt(row)
        for name in COUNT_FIELDS:
            funnel[name] += int(receipt[name])
        for name in (
            "model_call_attempted",
            "record_output_strictly_valid",
            "base_table_exact_canonical",
            "candidate_prediction_changed",
            "candidate_identity_handoff",
        ):
            receipt_flags[name] += int(receipt[name] is True)

    metrics = result["metrics"]
    checks = {
        "source_ranges_parsed_structurally": (
            (prior_start, prior_end) == (9680, 9759)
            and (current_start, current_end) == (9720, 9799)
        ),
        "forty_identity_ten_task_overlap": overlap_count == 40
        and overlap_task_count == 10,
        "literal_only_freshness_audit_bound_and_retracted": True,
        "same_parent_quality_result_remains_valid_no_go": (
            metrics["guarded_minus_base"]["exact_table_successes"] == 0
            and metrics["guarded_minus_base"]["quality_composite"] == 0
        ),
        "three_rejected_authors_edits_are_all_harm": (
            transition == {"rejected:harm": 3, "retained:neutral_correct": 3}
            and field_transition
            == {
                "Authors:rejected:harm": 3,
                "Stream:retained:neutral_correct": 3,
            }
        ),
        "zero_truth_improving_edits": sum(
            count for key, count in transition.items() if key.endswith(":improvement")
        )
        == 0,
        "candidate_funnel_exact": (
            funnel["parsed_record_count"] == 8
            and funnel["parsed_field_count"] == 30
            and funnel["verified_record_count"] == 8
            and funnel["verified_field_count"] == 24
            and funnel["missing_row_rejected_field_count"] == 12
            and funnel["unchanged_verified_coordinate_count"] == 6
            and funnel["changed_safe_coordinate_count"] == 6
        ),
        "base_error_surface_large_but_candidate_improvement_zero": (
            sum(wrong_by_arm[quality.BASE_ARM].values()) == 157
            and wrong_record_by_arm[quality.BASE_ARM] == 39
            and sum(wrong_by_arm[quality.GUARDED_ARM].values()) == 157
        ),
        "diagnosis_is_postfreeze_aggregate_only": True,
        "no_identity_question_page_prediction_truth_value_or_per_task_metric_persisted": True,
        "historical_outcome_not_authorized_for_runtime_routing": True,
        "entropy_information_gain_signed_credit_zero": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25425_population_overlap_and_candidate_funnel_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_artifact_sha256": copy.deepcopy(EXPECTED_SHA256),
        "population_erratum": {
            "prior_consumed_interval": f"RFC {prior_start}-{prior_end}",
            "current_claimed_fresh_interval": f"RFC {current_start}-{current_end}",
            "overlap_interval": f"RFC {overlap_start}-{overlap_end}",
            "overlap_identity_count": overlap_count,
            "overlap_current_task_count": overlap_task_count,
            "current_identity_count": len(population.identity_vector()),
            "current_task_count": population.TASK_COUNT,
            "v25421_fresh_disjoint_claim_valid": False,
            "v25422_literal_tree_history_scan_was_insufficient": True,
            "v25423_within_run_shared_parent_comparison_invalidated": False,
            "v25424_quality_no_go_changed": False,
        },
        "quality_summary": {
            "shared_base_table": copy.deepcopy(metrics["arms"][quality.BASE_ARM]),
            "raw_changed_safe_candidate": copy.deepcopy(
                metrics["arms"][quality.RAW_ARM]
            ),
            "guarded_candidate": copy.deepcopy(metrics["arms"][quality.GUARDED_ARM]),
            "guarded_minus_base": copy.deepcopy(metrics["guarded_minus_base"]),
            "raw_candidate_is_diagnostic_only": True,
        },
        "coordinate_transition_counts": dict(sorted(transition.items())),
        "field_coordinate_transition_counts": dict(sorted(field_transition.items())),
        "action_field_counts": dict(sorted(action_field.items())),
        "candidate_funnel_counts": {
            name: int(funnel[name]) for name in COUNT_FIELDS
        },
        "candidate_funnel_task_flags": dict(sorted(receipt_flags.items())),
        "remaining_error_surface": {
            "total_records": 80,
            "total_non_key_cells": 400,
            "wrong_cells_by_arm_and_field": {
                arm: dict(sorted(counts.items()))
                for arm, counts in wrong_by_arm.items()
            },
            "wrong_records_by_arm": dict(sorted(wrong_record_by_arm.items())),
        },
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "conclusion": {
            "list_atomic_guard_rejects_observed_harm": True,
            "list_atomic_guard_alone_does_not_create_improvements": True,
            "upstream_proposal_reach_and_row_binding_is_next_bottleneck": True,
            "freshness_must_parse_structural_ranges_and_consumed_forward_bindings": True,
            "new_disjoint_population_required": True,
            "deepwidebench_successor_supported": False,
        },
        "positive_signed_credit_count": 0,
        "authorization": {
            "population_freshness_erratum": not findings,
            "combined_visible_membership_and_list_guard_build": not findings,
            "structural_consumed_range_population_selector_build": not findings,
            "reuse_v25423_population_or_truth": False,
            "external_forward_or_evaluator": False,
            "deepwidebench_successor_build_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "entropy_or_signed_credit_claim": False,
        },
    }
    return contract.seal(value, "diagnosis_payload_sha256")


def validate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    erratum = copied.get("population_erratum") or {}
    if (
        copied.get("role")
        != "v25425_population_overlap_and_candidate_funnel_diagnosis"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or erratum.get("overlap_identity_count") != 40
        or erratum.get("overlap_current_task_count") != 10
        or erratum.get("v25421_fresh_disjoint_claim_valid") is not False
        or copied.get("coordinate_transition_counts")
        != {"rejected:harm": 3, "retained:neutral_correct": 3}
        or copied.get("field_coordinate_transition_counts")
        != {
            "Authors:rejected:harm": 3,
            "Stream:retained:neutral_correct": 3,
        }
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "population_freshness_erratum": True,
            "combined_visible_membership_and_list_guard_build": True,
            "structural_consumed_range_population_selector_build": True,
            "reuse_v25423_population_or_truth": False,
            "external_forward_or_evaluator": False,
            "deepwidebench_successor_build_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "entropy_or_signed_credit_claim": False,
        }
        or not contract.sealed(copied, "diagnosis_payload_sha256")
    ):
        raise ValueError("V2.54.25 diagnosis drifted")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    value = validate(diagnose())
    _publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "diagnosis_valid": value["diagnosis_valid"],
                "population_erratum": value["population_erratum"],
                "coordinate_transition_counts": value[
                    "coordinate_transition_counts"
                ],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
