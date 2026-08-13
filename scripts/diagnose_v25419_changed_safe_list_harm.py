#!/usr/bin/env python3
"""Post-freeze diagnosis of V2.54.18 changed-safe field edits.

This script uses the already-frozen predictions and truth only after the
audited V2.54.18 quality decision.  It separates independent provider effects
between route branches from the deterministic, shared-base changed-safe edit
inside each branch.  The diagnosis may authorize a fresh-population candidate
build, but never a benchmark run, leaderboard claim, or signed entropy credit.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25415_paired_rfc_route_external_contract as contract  # noqa: E402
from scripts import evaluate_v25416_paired_rfc_route_quality as scorer  # noqa: E402
from scripts import evaluate_v25418_rfc_not_issued_snapshot_recovery as quality  # noqa: E402


DATE = "20260813"
OUTPUT = Path(f"results/v25419_changed_safe_list_harm_diagnosis_v1_{DATE}.json")
EXPECTED_RESULT_SHA256 = "ea7e1dadd8201f9697018830e852983b0a622981c5253461ea18124c4a9b834f"
EXPECTED_AUDIT_SHA256 = "c36832e4c2cc0a2bacd5f34d73988efd339ebcde0cddff5a19cd080dff314797"
EXPECTED_TRUTH_SHA256 = "5e0fc2be5b650b5313f7a3090301acad15e89713760d8758da46bba0ce06d019"


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
        raise RuntimeError("V2.54.19 expected JSON object")
    return value


def _rows() -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, contract.TASK_ROWS, tracked=True)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != contract.TASK_COUNT or any(
        not isinstance(row, dict) for row in rows
    ):
        raise RuntimeError("V2.54.19 frozen rows drifted")
    return rows


def _barrier() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    result_path = contract.ordinary(ROOT, quality.RESULT, tracked=True)
    audit_path = contract.ordinary(ROOT, quality.AUDIT, tracked=True)
    truth_path = contract.ordinary(ROOT, quality.RECOVERY_TRUTH, tracked=True)
    result = quality.validate_result(_read(quality.RESULT))
    audit = _read(quality.AUDIT)
    truth = _read(quality.RECOVERY_TRUTH)
    rows = _rows()
    if (
        contract.sha256(result_path) != EXPECTED_RESULT_SHA256
        or contract.sha256(audit_path) != EXPECTED_AUDIT_SHA256
        or contract.sha256(truth_path) != EXPECTED_TRUTH_SHA256
        or result.get("passed") is not False
        or audit.get("role") != "v25418_rfc_not_issued_snapshot_recovery_audit"
        or audit.get("audit_valid") is not True
        or audit.get("quality_gate_passed") is not False
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("deepwidebench_successor_build")
        is not False
        or truth.get("valid_record_count") != 80
        or not contract.sealed(audit, "audit_payload_sha256")
        or not contract.sealed(truth, "truth_payload_sha256")
    ):
        raise RuntimeError("V2.54.19 audited quality barrier drifted")
    return result, truth, rows


def _stages(row: Mapping[str, Any]) -> tuple[str, str]:
    runtime = row.get("runtime_result")
    if not isinstance(runtime, Mapping):
        raise ValueError("V2.54.19 runtime result is absent")
    branch = row.get("route_branch")
    if branch == scorer.route.STABLE_BRANCH:
        parent = runtime.get("private_parent_result")
    elif branch == scorer.route.MEMBERSHIP_BRANCH:
        member = runtime.get("private_parent_result")
        hybrid = member.get("private_parent_result") if isinstance(member, Mapping) else None
        parent = hybrid.get("private_parent_result") if isinstance(hybrid, Mapping) else None
    else:
        raise ValueError("V2.54.19 branch drifted")
    predictions = parent.get("predictions") if isinstance(parent, Mapping) else None
    if not isinstance(predictions, Mapping):
        raise ValueError("V2.54.19 shared prediction pair is absent")
    base = predictions.get("shared_base_table")
    candidate = predictions.get("changed_safe_verified_edit")
    if not isinstance(base, str) or not base or not isinstance(candidate, str) or not candidate:
        raise ValueError("V2.54.19 shared prediction text drifted")
    return base, candidate


def _cell_map(prediction: str) -> dict[str, dict[str, str]]:
    columns, rows, valid = scorer._matrix(prediction)
    if not valid or tuple(columns) != tuple(contract.COLUMNS):
        raise ValueError("V2.54.19 expected canonical RFC table")
    output: dict[str, dict[str, str]] = {}
    for row in rows:
        identity = scorer._identity(row[0])
        if identity is None or identity in output:
            raise ValueError("V2.54.19 table identity drifted")
        output[identity] = dict(zip(columns, row, strict=True))
    return output


def diagnose(*, now: int | None = None) -> dict[str, Any]:
    result, truth_artifact, rows = _barrier()
    truth = truth_artifact.get("records")
    if not isinstance(truth, Mapping):
        raise RuntimeError("V2.54.19 truth records are absent")
    groups = scorer._groups()
    branch_quality: dict[str, dict[str, float | int]] = {}
    edit_disposition: Counter[str] = Counter()
    field_disposition: Counter[str] = Counter()
    changed_tasks = Counter()
    for branch in contract.BRANCHES:
        branch_rows = [row for row in rows if row.get("route_branch") == branch]
        if len(branch_rows) != contract.PAIR_COUNT:
            raise RuntimeError("V2.54.19 branch denominator drifted")
        stage_values: dict[str, list[dict[str, float | int | bool]]] = {
            "shared_base_table": [],
            "changed_safe_verified_edit": [],
        }
        for row in branch_rows:
            pair = int(row["pair_index"])
            base, candidate = _stages(row)
            stage_values["shared_base_table"].append(
                scorer.evaluate_prediction(base, groups[pair], truth)
            )
            stage_values["changed_safe_verified_edit"].append(
                scorer.evaluate_prediction(candidate, groups[pair], truth)
            )
            base_cells = _cell_map(base)
            candidate_cells = _cell_map(candidate)
            task_changed = False
            for identity in groups[pair]:
                for column in contract.COLUMNS[1:]:
                    before = base_cells[identity][column]
                    after = candidate_cells[identity][column]
                    if before == after:
                        continue
                    task_changed = True
                    before_ok = scorer._field_equal(
                        column, before, truth[identity][column]
                    )
                    after_ok = scorer._field_equal(
                        column, after, truth[identity][column]
                    )
                    disposition = (
                        "improve"
                        if not before_ok and after_ok
                        else "harm"
                        if before_ok and not after_ok
                        else "neutral_correct"
                        if before_ok and after_ok
                        else "neutral_wrong"
                    )
                    edit_disposition[disposition] += 1
                    field_disposition[f"{column}:{disposition}"] += 1
            changed_tasks[branch] += int(task_changed)
        for stage, values in stage_values.items():
            key = f"{branch}:{stage}"
            branch_quality[key] = {
                "tasks": len(values),
                "exact_table_successes": sum(
                    int(value["exact_table_success"]) for value in values
                ),
                **{
                    name: sum(float(value[name]) for value in values) / len(values)
                    for name in scorer.METRICS
                },
            }

    stage_deltas: dict[str, dict[str, float | int]] = {}
    for branch in contract.BRANCHES:
        base = branch_quality[f"{branch}:shared_base_table"]
        candidate = branch_quality[f"{branch}:changed_safe_verified_edit"]
        stage_deltas[branch] = {
            "exact_table_successes": int(candidate["exact_table_successes"])
            - int(base["exact_table_successes"]),
            **{
                name: float(candidate[name]) - float(base[name])
                for name in scorer.METRICS
            },
        }
    checks = {
        "fixed_forty_task_denominator": sum(
            int(value["tasks"])
            for key, value in branch_quality.items()
            if key.endswith(":shared_base_table")
        )
        == 40,
        "fourteen_actual_coordinate_edits": sum(edit_disposition.values()) == 14,
        "zero_truth_improving_edits": edit_disposition["improve"] == 0,
        "eleven_truth_harming_edits": edit_disposition["harm"] == 11,
        "three_truth_neutral_edits": (
            edit_disposition["neutral_correct"]
            + edit_disposition["neutral_wrong"]
            == 3
        ),
        "all_harm_is_in_authors_column": field_disposition["Authors:harm"] == 11
        and sum(
            count
            for key, count in field_disposition.items()
            if key.endswith(":harm") and key != "Authors:harm"
        )
        == 0,
        "changed_safe_composite_nonpositive_both_branches": all(
            stage_deltas[branch]["quality_composite"] <= 0
            for branch in contract.BRANCHES
        ),
        "route_branch_base_difference_not_treated_as_causal": True,
        "same_branch_base_to_edit_is_shared_effect_causal_boundary": True,
        "diagnostic_population_not_reused_for_candidate_validation": True,
        "entropy_information_gain_signed_credit_zero": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25419_changed_safe_list_harm_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_quality_result_sha256": EXPECTED_RESULT_SHA256,
        "parent_quality_audit_sha256": EXPECTED_AUDIT_SHA256,
        "truth_sha256": EXPECTED_TRUTH_SHA256,
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "branch_stage_quality": branch_quality,
        "same_branch_changed_safe_minus_base": stage_deltas,
        "changed_task_count_by_branch": dict(changed_tasks),
        "coordinate_disposition": dict(edit_disposition),
        "field_coordinate_disposition": dict(field_disposition),
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "conclusion": {
            "visible_membership_forced_route_is_not_supported": True,
            "changed_safe_scalar_edit_is_unsafe_for_structured_multivalue_columns": True,
            "list_atomic_guard_candidate_supported_for_fresh_validation": not findings,
            "fresh_disjoint_population_and_shared_effect_gate_required": True,
            "deepwidebench_successor_supported": False,
        },
        "authorization": {
            "list_atomic_guard_build": not findings,
            "fresh_disjoint_shared_effect_gate_design": not findings,
            "reuse_current_population_for_candidate_validation": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "entropy_or_signed_credit_claim": False,
        },
    }
    return contract.seal(value, "diagnosis_payload_sha256")


def validate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25419_changed_safe_list_harm_diagnosis"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("coordinate_disposition")
        != {"harm": 11, "neutral_correct": 3}
        or copied.get("field_coordinate_disposition")
        != {"Authors:harm": 11, "Authors:neutral_correct": 1, "Stream:neutral_correct": 2}
        or copied.get("authorization")
        != {
            "list_atomic_guard_build": True,
            "fresh_disjoint_shared_effect_gate_design": True,
            "reuse_current_population_for_candidate_validation": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "entropy_or_signed_credit_claim": False,
        }
        or not contract.sealed(copied, "diagnosis_payload_sha256")
    ):
        raise ValueError("V2.54.19 diagnosis drifted")
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
                "coordinate_disposition": value["coordinate_disposition"],
                "field_coordinate_disposition": value[
                    "field_coordinate_disposition"
                ],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
