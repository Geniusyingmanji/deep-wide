#!/usr/bin/env python3
"""Counts-only post-freeze output-shape diagnosis for V2.50.30 vs V2.48.57.

This script runs only after both exact-220 prediction vectors and evaluator
summaries are frozen.  Opaque identifiers are used for in-memory alignment
and are never emitted.  Questions, predictions, table cells, instance names,
gold, categories, and per-task metrics are likewise never emitted.

The diagnosis asks a deliberately narrow question: is the observed quality
gap associated with final table shape (row count, width, or explicit Unknown
cells), or does the evidence rule out treating simple completion pressure as
the next intervention?  Associations remain descriptive and cannot route a
future benchmark forward pass.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import statistics
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25029_evidence_conditioned_runtime as runtime  # noqa: E402
from deepwide_agent import v25030_evidence_conditioned_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import _split_table_row  # noqa: E402
from scripts import diagnose_v25031_v25030_exact220 as parent  # noqa: E402


OUTPUT = Path("results/v25043_v25030_v24857_output_shape_diagnosis_v1_20260811.json")
OLD_PREDICTIONS = Path(
    "outputs/v24857_pacing_aware_exact220_v1_20260808/runtime_predictions.jsonl"
)
OLD_SUMMARY = Path(
    "outputs/v24857_pacing_aware_exact220_v1_20260808/evaluator/conservative_summary.json"
)
OLD_POSTAUDIT = Path(
    "results/v24857_pacing_aware_exact220_postresult_audit_v1_20260808.json"
)
CURRENT_SUMMARY = contract.OUTPUT_ROOT / "evaluator/conservative_summary.json"
UNKNOWN = frozenset(
    {"", "-", "—", "?", "n/a", "na", "none", "null", "unknown", "未知", "不详"}
)
COMPOSITE = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")


def _read(path: Path) -> dict[str, Any]:
    absolute = ROOT / path
    if (
        path.is_absolute()
        or ".." in path.parts
        or absolute.is_symlink()
        or not absolute.is_file()
        or not absolute.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.50.43 expected ordinary repository object: {path}")
    value = json.loads(absolute.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.43 expected JSON object")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    absolute = ROOT / path
    if (
        path.is_absolute()
        or ".." in path.parts
        or absolute.is_symlink()
        or not absolute.is_file()
        or not absolute.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.50.43 expected ordinary repository JSONL: {path}")
    rows = [
        json.loads(line)
        for line in absolute.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.50.43 expected JSONL objects")
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _shape(prediction: str) -> dict[str, Any]:
    """Return only structural counts from the first canonical table group."""

    groups: list[list[str]] = []
    current: list[str] = []
    for line in str(prediction or "").replace("\r\n", "\n").splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            current.append(stripped)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    candidates: list[dict[str, Any]] = []
    for group in groups:
        if len(group) < 3:
            continue
        header = _split_table_row(group[0])
        separator = _split_table_row(group[1])
        if (
            not header
            or len(separator) != len(header)
            or any(
                re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) is None
                for cell in separator
            )
        ):
            continue
        rows = [
            row
            for row in (_split_table_row(line) for line in group[2:])
            if len(row) == len(header) and all(row)
        ]
        if not rows:
            continue
        value_cells = [cell for row in rows for cell in row[1:]]
        unknown = sum(cell.strip().casefold() in UNKNOWN for cell in value_cells)
        candidates.append(
            {
                "width": len(header),
                "rows": len(rows),
                "value_cells": len(value_cells),
                "unknown_value_cells": unknown,
            }
        )
    if len(candidates) != 1:
        raise RuntimeError("V2.50.43 expected one canonical prediction table")
    return candidates[0]


def _metric(row: Mapping[str, Any], name: str) -> float:
    if row.get("evaluator_valid") is not True:
        return 0.0
    value = (row.get("metrics") or {}).get(name)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise RuntimeError("V2.50.43 evaluator metric drifted")
    return float(value)


def _composite(row: Mapping[str, Any]) -> float:
    return sum(_metric(row, name) for name in COMPOSITE) / len(COMPOSITE)


def _band_rows(value: int) -> str:
    if value == 1:
        return "1"
    if value <= 3:
        return "2_3"
    if value <= 7:
        return "4_7"
    if value <= 15:
        return "8_15"
    return "16_plus"


def _run_shape(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    widths = Counter(str(row["shape"]["width"]) for row in rows)
    row_bands = Counter(_band_rows(int(row["shape"]["rows"])) for row in rows)
    row_counts = [int(row["shape"]["rows"]) for row in rows]
    value_cells = sum(int(row["shape"]["value_cells"]) for row in rows)
    unknown = sum(int(row["shape"]["unknown_value_cells"]) for row in rows)
    return {
        "tasks": len(rows),
        "canonical_table_tasks": len(rows),
        "total_rows": sum(row_counts),
        "mean_rows": round(statistics.fmean(row_counts), 12),
        "median_rows": float(statistics.median(row_counts)),
        "maximum_rows": max(row_counts),
        "total_value_cells": value_cells,
        "unknown_value_cells": unknown,
        "unknown_value_cell_rate": round(unknown / value_cells, 12) if value_cells else 0.0,
        "tasks_with_unknown_value_cell": sum(
            int(row["shape"]["unknown_value_cells"]) > 0 for row in rows
        ),
        "width_histogram": dict(sorted(widths.items(), key=lambda item: int(item[0]))),
        "row_count_band_histogram": dict(sorted(row_bands.items())),
    }


def _quality_group(
    ids: Sequence[str],
    current: Mapping[str, Mapping[str, Any]],
    old: Mapping[str, Mapping[str, Any]],
    shapes: Mapping[str, Mapping[str, Mapping[str, int]]],
) -> dict[str, Any]:
    if not ids:
        return {
            "tasks": 0,
            "current_composite": None,
            "old_composite": None,
            "composite_delta": None,
            "current_exact": 0,
            "old_exact": 0,
            "exact_delta": 0,
            "mean_row_delta": None,
            "mean_unknown_value_cell_delta": None,
        }
    current_composite = statistics.fmean(_composite(current[key]) for key in ids)
    old_composite = statistics.fmean(_composite(old[key]) for key in ids)
    current_exact = sum(_metric(current[key], "score") > 0 for key in ids)
    old_exact = sum(_metric(old[key], "score") > 0 for key in ids)
    return {
        "tasks": len(ids),
        "current_composite": round(current_composite, 12),
        "old_composite": round(old_composite, 12),
        "composite_delta": round(current_composite - old_composite, 12),
        "current_exact": current_exact,
        "old_exact": old_exact,
        "exact_delta": current_exact - old_exact,
        "mean_row_delta": round(
            statistics.fmean(
                shapes["v25030"][key]["rows"] - shapes["v24857"][key]["rows"]
                for key in ids
            ),
            12,
        ),
        "mean_unknown_value_cell_delta": round(
            statistics.fmean(
                shapes["v25030"][key]["unknown_value_cells"]
                - shapes["v24857"][key]["unknown_value_cells"]
                for key in ids
            ),
            12,
        ),
    }


def _sign(value: int, *, positive: str, zero: str, negative: str) -> str:
    return positive if value > 0 else negative if value < 0 else zero


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    frozen_parent = parent.validate_diagnosis(_read(parent.OUTPUT))
    current_post = _read(contract.POSTAUDIT)
    old_post = _read(OLD_POSTAUDIT)
    if (
        frozen_parent.get("diagnosis_valid") is not True
        or current_post.get("audit_valid") is not True
        or old_post.get("audit_valid") is not True
        or not _sealed(current_post, "audit_payload_sha256")
        or not _sealed(old_post, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.43 frozen parent audit barrier drifted")

    current_results = [runtime.validate_result(row) for row in _jsonl(contract.RUNTIME_RESULTS)]
    old_predictions = _jsonl(OLD_PREDICTIONS)
    current_quality_rows = _read(CURRENT_SUMMARY).get("per_task") or []
    old_quality_rows = _read(OLD_SUMMARY).get("per_task") or []
    if any(not isinstance(row, Mapping) for row in (*current_quality_rows, *old_quality_rows)):
        raise RuntimeError("V2.50.43 quality row drifted")

    current_by_id = {str(row["opaque_id"]): row for row in current_results}
    old_by_id: dict[str, dict[str, Any]] = {}
    for row in old_predictions:
        opaque_id = str(row.get("opaque_id") or "")
        prediction = str(row.get("prediction") or "")
        if (
            not opaque_id
            or row.get("status") not in {"terminal", "completed"}
            or row.get("prediction_sha256") != hashlib.sha256(prediction.encode()).hexdigest()
        ):
            raise RuntimeError("V2.50.43 old prediction barrier drifted")
        old_by_id[opaque_id] = row
    current_quality = {str(row["opaque_id"]): row for row in current_quality_rows}
    old_quality = {str(row["opaque_id"]): row for row in old_quality_rows}
    ids = set(current_by_id)
    if (
        len(ids) != 220
        or len(current_results) != 220
        or len(old_predictions) != 220
        or len(old_by_id) != 220
        or set(old_by_id) != ids
        or set(current_quality) != ids
        or set(old_quality) != ids
    ):
        raise RuntimeError("V2.50.43 exact220 alignment drifted")

    shapes: dict[str, dict[str, dict[str, int]]] = {"v25030": {}, "v24857": {}}
    paired_rows: dict[str, list[dict[str, Any]]] = {"v25030": [], "v24857": []}
    groups: dict[str, dict[str, list[str]]] = {
        "row_count_delta": defaultdict(list),
        "unknown_value_cell_delta": defaultdict(list),
        "taskwise_composite_delta": defaultdict(list),
        "whole_table_transition": defaultdict(list),
    }
    width_changed = 0
    prediction_changed = 0
    for opaque_id in sorted(ids):
        current_prediction = str(current_by_id[opaque_id]["prediction"])
        old_prediction = str(old_by_id[opaque_id]["prediction"])
        current_shape = _shape(current_prediction)
        old_shape = _shape(old_prediction)
        shapes["v25030"][opaque_id] = current_shape
        shapes["v24857"][opaque_id] = old_shape
        paired_rows["v25030"].append({"shape": current_shape})
        paired_rows["v24857"].append({"shape": old_shape})
        width_changed += current_shape["width"] != old_shape["width"]
        prediction_changed += current_prediction != old_prediction

        row_delta = current_shape["rows"] - old_shape["rows"]
        unknown_delta = (
            current_shape["unknown_value_cells"] - old_shape["unknown_value_cells"]
        )
        composite_delta = _composite(current_quality[opaque_id]) - _composite(
            old_quality[opaque_id]
        )
        current_exact = _metric(current_quality[opaque_id], "score") > 0
        old_exact = _metric(old_quality[opaque_id], "score") > 0
        groups["row_count_delta"][
            _sign(row_delta, positive="more_rows", zero="same_rows", negative="fewer_rows")
        ].append(opaque_id)
        groups["unknown_value_cell_delta"][
            _sign(
                unknown_delta,
                positive="more_unknown_cells",
                zero="same_unknown_cells",
                negative="fewer_unknown_cells",
            )
        ].append(opaque_id)
        groups["taskwise_composite_delta"][
            "gain"
            if composite_delta > 1e-12
            else "loss"
            if composite_delta < -1e-12
            else "tie"
        ].append(opaque_id)
        groups["whole_table_transition"][
            "gain"
            if current_exact and not old_exact
            else "loss"
            if old_exact and not current_exact
            else "both_exact"
            if current_exact and old_exact
            else "neither_exact"
        ].append(opaque_id)

    grouped = {
        dimension: {
            name: _quality_group(keys, current_quality, old_quality, shapes)
            for name, keys in sorted(values.items())
        }
        for dimension, values in groups.items()
    }
    current_shape = _run_shape(paired_rows["v25030"])
    old_shape = _run_shape(paired_rows["v24857"])
    checks = {
        "frozen_v25031_parent_valid": frozen_parent["diagnosis_valid"] is True,
        "both_postresult_audits_valid_and_sealed": True,
        "both_prediction_vectors_exact220_and_hash_valid": len(ids) == 220,
        "both_quality_vectors_exact220": len(current_quality) == len(old_quality) == 220,
        "all_predictions_have_one_canonical_table": all(
            summary["canonical_table_tasks"] == 220
            for summary in (current_shape, old_shape)
        ),
        "no_question_prediction_cell_instance_id_gold_or_per_task_metric_emitted": True,
        "postfreeze_only_no_network_model_search_fetch_or_evaluator_effect": True,
        "entropy_signed_credit_remains_disabled": all(
            row["content_free_receipt"][
                "entropy_or_information_gain_assigns_signed_credit"
            ]
            is False
            for row in current_results
        ),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    exact_transitions = grouped["whole_table_transition"]
    value = {
        "artifact_version": 1,
        "role": "v25043_v25030_v24857_counts_only_output_shape_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "postfreeze_output_shape_bottleneck_audited",
        "parents": {
            "v25031_diagnosis_sha256": _sha256(parent.OUTPUT),
            "v25030_runtime_results_sha256": _sha256(contract.RUNTIME_RESULTS),
            "v25030_conservative_summary_sha256": _sha256(CURRENT_SUMMARY),
            "v25030_postresult_audit_sha256": _sha256(contract.POSTAUDIT),
            "v24857_runtime_predictions_sha256": _sha256(OLD_PREDICTIONS),
            "v24857_conservative_summary_sha256": _sha256(OLD_SUMMARY),
            "v24857_postresult_audit_sha256": _sha256(OLD_POSTAUDIT),
        },
        "output_shape": {"v25030": current_shape, "v24857": old_shape},
        "paired": {
            "tasks": 220,
            "prediction_changed_tasks": prediction_changed,
            "table_width_changed_tasks": width_changed,
            "total_row_delta": current_shape["total_rows"] - old_shape["total_rows"],
            "total_unknown_value_cell_delta": (
                current_shape["unknown_value_cells"] - old_shape["unknown_value_cells"]
            ),
            "grouped_quality": grouped,
        },
        "diagnosis": {
            "shape_associations_are_descriptive_not_randomized_or_causal": True,
            "simple_unknown_reduction_is_not_a_safe_task_utility_proxy": True,
            "forced_coverage_ledger_reuse_is_not_authorized": True,
            "benchmark_output_shape_must_not_route_future_runtime": True,
            "whole_table_losses_exceed_gains": (
                exact_transitions.get("loss", {}).get("tasks", 0)
                > exact_transitions.get("gain", {}).get("tasks", 0)
            ),
            "next_candidate_must_be_evidence_constrained_and_visible_only": True,
            "next_candidate_may_change_only_synthesis_or_evidence_representation": True,
            "next_candidate_must_not_increase_query_fetch_model_token_or_wall_caps": True,
            "fresh_external_matched_gate_required_before_exact220": True,
            "entropy_or_information_gain_credit_validated": False,
        },
        "source_policy": {
            "postfreeze_evaluator_only_analysis": True,
            "opaque_ids_used_only_for_in_memory_alignment_and_not_emitted": True,
            "question_prediction_table_cell_instance_id_gold_answer_or_per_task_metric_emitted": False,
            "benchmark_category_question_type_split_family_used": False,
            "analysis_feedback_used_in_same_forward_pass": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        },
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "authorization": {
            "fresh_label_blind_external_matched_gate_design": not findings,
            "new_exact220_launch": False,
            "evaluator_or_selective_revaluation": False,
            "retry_resume_or_selective_rerun": False,
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
        copied.get("role")
        != "v25043_v25030_v24857_counts_only_output_shape_diagnosis"
        or copied.get("status") != "postfreeze_output_shape_bottleneck_audited"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("diagnosis", {}).get(
            "shape_associations_are_descriptive_not_randomized_or_causal"
        )
        is not True
        or copied.get("diagnosis", {}).get(
            "simple_unknown_reduction_is_not_a_safe_task_utility_proxy"
        )
        is not True
        or copied.get("diagnosis", {}).get(
            "entropy_or_information_gain_credit_validated"
        )
        is not False
        or copied.get("authorization")
        != {
            "fresh_label_blind_external_matched_gate_design": True,
            "new_exact220_launch": False,
            "evaluator_or_selective_revaluation": False,
            "retry_resume_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.43 diagnosis drifted")
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
