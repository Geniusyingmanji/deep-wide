#!/usr/bin/env python3
"""Counts-only post-freeze diagnosis of V2.50.45 weak treatment exposure."""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25045_evidence_constrained_external_contract as contract  # noqa: E402
from scripts import run_v25045_evidence_constrained_external as runner  # noqa: E402


OUTPUT = Path("results/v25046_v25045_weak_abstention_diagnosis_v1_20260811.json")
UNKNOWN = frozenset({"unknown", "未知", "不详", "n/a", "na", "none", "null", "-", "—", "?", ""})


def _read(path: Path) -> dict[str, Any]:
    absolute = ROOT / path
    if path.is_absolute() or ".." in path.parts or absolute.is_symlink() or not absolute.is_file():
        raise RuntimeError(f"V2.50.46 expected ordinary object: {path}")
    value = json.loads(absolute.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.46 expected JSON object")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    absolute = ROOT / path
    if path.is_absolute() or ".." in path.parts or absolute.is_symlink() or not absolute.is_file():
        raise RuntimeError(f"V2.50.46 expected ordinary JSONL: {path}")
    values = [
        json.loads(line)
        for line in absolute.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError("V2.50.46 expected JSONL objects")
    return values


def _matrix(text: str) -> list[list[str]]:
    lines = [
        line.strip()
        for line in str(text).replace("\r\n", "\n").splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    cells = [
        [cell.strip() for cell in line[1:-1].split("|")]
        for line in lines
    ]
    if len(cells) < 3:
        raise RuntimeError("V2.50.46 expected one canonical table")
    return cells


def _shape_delta(control: str, candidate: str) -> dict[str, Any]:
    before = _matrix(control)
    after = _matrix(candidate)
    before_rows = before[2:]
    after_rows = after[2:]
    overlapping = min(len(before_rows), len(after_rows))
    changed = replacements = to_unknown = from_unknown = 0
    for row_index in range(overlapping):
        width = min(len(before_rows[row_index]), len(after_rows[row_index]))
        for column_index in range(width):
            old = before_rows[row_index][column_index]
            new = after_rows[row_index][column_index]
            if old == new:
                continue
            changed += 1
            old_unknown = old.strip().casefold() in UNKNOWN
            new_unknown = new.strip().casefold() in UNKNOWN
            to_unknown += int(not old_unknown and new_unknown)
            from_unknown += int(old_unknown and not new_unknown)
            replacements += int(not old_unknown and not new_unknown)
    return {
        "row_delta": len(after_rows) - len(before_rows),
        "column_delta": len(after[0]) - len(before[0]),
        "changed_overlapping_cells": changed,
        "nonunknown_to_unknown_cells": to_unknown,
        "unknown_to_nonunknown_cells": from_unknown,
        "nonunknown_to_different_nonunknown_cells": replacements,
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    audit = _read(contract.FORWARD_AUDIT)
    rows = [runner.validate_task_row(value) for value in _jsonl(contract.TASK_ROWS)]
    if (
        audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or not contract.sealed(audit, "audit_payload_sha256")
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_implementation_and_protocol"
        )
        is not False
        or len(rows) != contract.TASK_COUNT
    ):
        raise RuntimeError("V2.50.46 frozen parent barrier drifted")

    changed = [row for row in rows if row["prediction_changed"]]
    deltas = [
        _shape_delta(
            row["predictions"][contract.CONTROL_ARM],
            row["predictions"][contract.CANDIDATE_ARM],
        )
        for row in changed
    ]
    row_hist = Counter(str(delta["row_delta"]) for delta in deltas)
    column_hist = Counter(str(delta["column_delta"]) for delta in deltas)
    changed_hist = Counter(str(delta["changed_overlapping_cells"]) for delta in deltas)
    totals = {
        name: sum(int(delta[name]) for delta in deltas)
        for name in (
            "changed_overlapping_cells",
            "nonunknown_to_unknown_cells",
            "unknown_to_nonunknown_cells",
            "nonunknown_to_different_nonunknown_cells",
        )
    }
    aggregate = forward["aggregate"]
    checks = {
        "forward_and_postforward_audit_valid": True,
        "fixed_denominator_exact20": len(rows) == contract.TASK_COUNT,
        "prediction_change_count_recomputes": len(changed)
        == aggregate["prediction_changed_task_count"],
        "mechanism_gate_is_no_go": forward["mechanism_decision"]["mechanism_gate_passed"]
        is False,
        "evaluator_and_gold_remain_unauthorized_and_absent": not any(
            (ROOT / path).exists() or (ROOT / path).is_symlink()
            for path in (
                contract.EVALUATOR,
                contract.EVALUATOR_TEST,
                contract.EVALUATOR_PROTOCOL,
                contract.RESULT,
                contract.POSTAUDIT,
                contract.GOLD_SNAPSHOT,
            )
        ),
        "no_task_identity_question_prediction_value_or_per_task_delta_emitted": True,
        "postfreeze_only_zero_network_model_search_fetch_or_evaluator_effect": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25046_v25045_counts_only_weak_abstention_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "prompt_only_binding_treatment_weak_abstention_no_go",
        "parents": {
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        },
        "aggregate": {
            "tasks": len(rows),
            "completed_tasks": aggregate["completed_task_count"],
            "failure_as_zero_tasks": aggregate["failure_as_zero_task_count"],
            "prediction_changed_tasks": len(changed),
            "row_delta_histogram": dict(sorted(row_hist.items())),
            "column_delta_histogram": dict(sorted(column_hist.items())),
            "changed_overlapping_cell_histogram": dict(sorted(changed_hist.items())),
            **totals,
            "control_model_total_tokens": aggregate[
                f"{contract.CONTROL_ARM}_total_tokens"
            ],
            "candidate_model_total_tokens": aggregate[
                f"{contract.CANDIDATE_ARM}_total_tokens"
            ],
            "candidate_over_control_model_total_token_ratio": round(
                aggregate[f"{contract.CANDIDATE_ARM}_total_tokens"]
                / aggregate[f"{contract.CONTROL_ARM}_total_tokens"],
                12,
            ),
        },
        "diagnosis": {
            "prompt_only_treatment_natural_exposure_below_preregistered_gate": True,
            "all_observed_changes_are_single_cell_abstentions": (
                len(changed) > 0
                and totals["changed_overlapping_cells"] == len(changed)
                and totals["nonunknown_to_unknown_cells"] == len(changed)
                and totals["unknown_to_nonunknown_cells"] == 0
                and totals["nonunknown_to_different_nonunknown_cells"] == 0
                and row_hist == {"0": len(changed)}
                and column_hist == {"0": len(changed)}
            ),
            "fact_correction_or_quality_gain_established": False,
            "same_population_evaluator_retry_or_threshold_relaxation_allowed": False,
            "next_candidate_should_change_evidence_representation_not_prompt_strength": True,
            "next_candidate_must_use_identity_bound_compact_records_from_same_fetched_bytes": True,
            "query_fetch_model_output_token_context_and_wall_caps_must_not_increase": True,
            "entropy_or_information_gain_credit_validated": False,
        },
        "source_policy": {
            "postfreeze_only": True,
            "opaque_ids_used_only_for_in_memory_iteration_and_not_emitted": True,
            "question_prediction_cell_value_gold_evaluator_or_per_task_delta_emitted": False,
            "benchmark_category_question_type_split_mapping_score_or_reward_used": False,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "authorization": {
            "fresh_identity_bound_representation_gate_design": not findings,
            "same_population_evaluator_or_rerun": False,
            "new_deepwidebench_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = json.loads(json.dumps(dict(value), ensure_ascii=False))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role") != "v25046_v25045_counts_only_weak_abstention_diagnosis"
        or copied.get("status") != "prompt_only_binding_treatment_weak_abstention_no_go"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("diagnosis", {}).get(
            "all_observed_changes_are_single_cell_abstentions"
        )
        is not True
        or copied.get("diagnosis", {}).get("fact_correction_or_quality_gain_established")
        is not False
        or copied.get("diagnosis", {}).get("entropy_or_information_gain_credit_validated")
        is not False
        or copied.get("authorization")
        != {
            "fresh_identity_bound_representation_gate_design": True,
            "same_population_evaluator_or_rerun": False,
            "new_deepwidebench_exact220": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.46 diagnosis drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    diagnosis = build_diagnosis()
    publish_new(ROOT / OUTPUT, diagnosis)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "status": diagnosis["status"],
                "diagnosis_valid": diagnosis["diagnosis_valid"],
                "authorization": diagnosis["authorization"],
            },
            sort_keys=True,
        )
    )
