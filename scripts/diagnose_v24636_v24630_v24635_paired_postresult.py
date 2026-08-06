#!/usr/bin/env python3
"""Aggregate-only paired diagnosis of two frozen exact-220 results.

This script runs after both V2.46.30 and V2.46.35 completed their one-shot
forward and failure-as-zero evaluator.  It joins rows only to compute aggregate
transition counts.  It emits no task identifier, question, prediction, answer,
mapping, category, URL, page, credential, or per-task metric, and it cannot
authorize another public-benchmark run.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24635_exact220_contract import (  # noqa: E402
    payload_sha256,
    read_object,
    sha256,
)


OUTPUT = Path(
    "results/v24636_v24630_v24635_paired_postresult_diagnosis_v1_20260806.json"
)
OLD_RESULT = Path("results/v24630_exact220_result_v1_20260806.json")
NEW_RESULT = Path("results/v24635_exact220_result_v1_20260806.json")
OLD_POSTAUDIT = Path("results/v24630_exact220_postresult_audit_v1_20260806.json")
NEW_POSTAUDIT = Path("results/v24635_exact220_postresult_audit_v1_20260806.json")
OLD_FORWARD_AUDIT = Path("results/v24630_exact220_forward_audit_v1_20260806.json")
NEW_FORWARD_AUDIT = Path("results/v24635_exact220_forward_audit_v1_20260806.json")
OLD_RUNTIME = Path("outputs/v24630_exact220_v1_20260806/runtime_predictions.jsonl")
NEW_RUNTIME = Path("outputs/v24635_exact220_v1_20260806/runtime_predictions.jsonl")
OLD_EVAL_SUMMARY = Path(
    "outputs/v24630_exact220_v1_20260806/evaluator/conservative_summary.json"
)
NEW_EVAL_SUMMARY = Path(
    "outputs/v24635_exact220_v1_20260806/evaluator/conservative_summary.json"
)
SELECTED = 220
MODEL_GENERATED = frozenset(
    {"primary", "normalized_primary", "repaired", "normalized_repaired"}
)
METRICS = ("score", "entity_acc", "f1_by_row", "f1_by_item", "column_f1")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.46.36 expected ordinary repository file: {relative}")
    return path


def _jsonl_projection(root: Path, relative: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for line in _ordinary(root, relative).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        opaque_id = value.get("opaque_id")
        completion = value.get("completion_kind")
        if (
            not isinstance(value, dict)
            or not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or not isinstance(completion, str)
            or not completion
            or value.get("status") != "completed"
            or value.get("label_blind") is not True
            or value.get(
                "mapping_gold_category_question_type_split_evaluator_score_read"
            )
            is not False
            or opaque_id in output
        ):
            raise RuntimeError("V2.46.36 runtime projection drifted")
        output[opaque_id] = completion
    if len(output) != SELECTED:
        raise RuntimeError("V2.46.36 runtime denominator drifted")
    return output


def _metric_projection(root: Path, relative: Path) -> dict[str, dict[str, Any]]:
    summary = read_object(_ordinary(root, relative))
    rows = summary.get("per_task")
    if not isinstance(rows, list) or len(rows) != SELECTED:
        raise RuntimeError("V2.46.36 evaluator summary denominator drifted")
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        opaque_id = row.get("opaque_id")
        metrics = row.get("metrics")
        if (
            not isinstance(row, dict)
            or not isinstance(opaque_id, str)
            or OPAQUE.fullmatch(opaque_id) is None
            or opaque_id in output
            or not isinstance(metrics, dict)
            or any(
                not isinstance(metrics.get(name), (int, float))
                or not math.isfinite(float(metrics[name]))
                for name in METRICS
            )
            or not isinstance(row.get("evaluator_valid"), bool)
        ):
            raise RuntimeError("V2.46.36 evaluator metric projection drifted")
        output[opaque_id] = {
            "evaluator_valid": row["evaluator_valid"],
            "metrics": {name: float(metrics[name]) for name in METRICS},
        }
    return output


def _aggregate(
    ids: Iterable[str], values: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    selected = list(ids)
    if not selected:
        return {
            "n": 0,
            "evaluator_valid": 0,
            "whole_table_successes": 0,
            **{name: None for name in (*METRICS, "quality_composite")},
        }
    result: dict[str, Any] = {
        "n": len(selected),
        "evaluator_valid": sum(
            values[item]["evaluator_valid"] is True for item in selected
        ),
        "whole_table_successes": sum(
            float(values[item]["metrics"]["score"]) > 0 for item in selected
        ),
    }
    for name in METRICS:
        result[name] = sum(
            float(values[item]["metrics"][name]) for item in selected
        ) / len(selected)
    result["quality_composite"] = sum(
        float(result[name])
        for name in ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
    ) / 4
    return result


def _validate_parents(root: Path) -> dict[str, dict[str, Any]]:
    old_result = read_object(_ordinary(root, OLD_RESULT))
    new_result = read_object(_ordinary(root, NEW_RESULT))
    old_post = read_object(_ordinary(root, OLD_POSTAUDIT))
    new_post = read_object(_ordinary(root, NEW_POSTAUDIT))
    old_forward = read_object(_ordinary(root, OLD_FORWARD_AUDIT))
    new_forward = read_object(_ordinary(root, NEW_FORWARD_AUDIT))
    if (
        old_result.get("role") != "v24630_exact220_result"
        or new_result.get("role") != "v24635_exact220_result"
        or old_result.get("selected") != SELECTED
        or new_result.get("selected") != SELECTED
        or old_result.get("failure_as_zero") is not True
        or new_result.get("failure_as_zero") is not True
        or not _sealed(old_result, "result_payload_sha256")
        or not _sealed(new_result, "result_payload_sha256")
        or old_post.get("audit_valid") is not True
        or new_post.get("audit_valid") is not True
        or old_post.get("findings") != []
        or new_post.get("findings") != []
        or not _sealed(old_post, "audit_payload_sha256")
        or not _sealed(new_post, "audit_payload_sha256")
        or old_forward.get("audit_valid") is not True
        or new_forward.get("audit_valid") is not True
        or old_forward.get("findings") != []
        or new_forward.get("findings") != []
        or not _sealed(old_forward, "audit_payload_sha256")
        or not _sealed(new_forward, "audit_payload_sha256")
        or old_forward.get("runtime_predictions_sha256") != sha256(root / OLD_RUNTIME)
        or new_forward.get("runtime_predictions_sha256") != sha256(root / NEW_RUNTIME)
        or old_post.get("provenance", {}).get("conservative_summary_sha256")
        != sha256(root / OLD_EVAL_SUMMARY)
        or new_post.get("provenance", {}).get("conservative_summary_sha256")
        != sha256(root / NEW_EVAL_SUMMARY)
    ):
        raise RuntimeError("V2.46.36 frozen parent chain drifted")
    return {
        "old_result": old_result,
        "new_result": new_result,
        "old_post": old_post,
        "new_post": new_post,
    }


def _delta(old: Mapping[str, Any], new: Mapping[str, Any]) -> dict[str, Any]:
    if old["n"] != new["n"]:
        raise RuntimeError("V2.46.36 paired group denominator drifted")
    return {
        "n": old["n"],
        "evaluator_valid_delta": new["evaluator_valid"] - old["evaluator_valid"],
        "whole_table_success_delta": new["whole_table_successes"]
        - old["whole_table_successes"],
        **{
            f"{name}_delta": None
            if old[name] is None or new[name] is None
            else float(new[name]) - float(old[name])
            for name in (*METRICS, "quality_composite")
        },
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    parents = _validate_parents(root)
    old_runtime = _jsonl_projection(root, OLD_RUNTIME)
    new_runtime = _jsonl_projection(root, NEW_RUNTIME)
    old_metrics = _metric_projection(root, OLD_EVAL_SUMMARY)
    new_metrics = _metric_projection(root, NEW_EVAL_SUMMARY)
    ids = set(old_runtime)
    if ids != set(new_runtime) or ids != set(old_metrics) or ids != set(new_metrics):
        raise RuntimeError("V2.46.36 frozen paired ID sets drifted")

    old_fallback = {item for item in ids if old_runtime[item] not in MODEL_GENERATED}
    new_fallback = {item for item in ids if new_runtime[item] not in MODEL_GENERATED}
    groups = {
        "old_fallback_to_new_model": old_fallback - new_fallback,
        "old_model_to_new_fallback": new_fallback - old_fallback,
        "model_to_model": ids - old_fallback - new_fallback,
        "fallback_to_fallback": old_fallback & new_fallback,
    }
    if set().union(*groups.values()) != ids or sum(map(len, groups.values())) != SELECTED:
        raise RuntimeError("V2.46.36 transition partition drifted")

    paired_groups: dict[str, Any] = {}
    weighted_composite_delta = 0.0
    weighted_score_delta = 0.0
    whole_success_delta = 0
    for name, members in groups.items():
        old = _aggregate(sorted(members), old_metrics)
        new = _aggregate(sorted(members), new_metrics)
        delta = _delta(old, new)
        paired_groups[name] = {"old": old, "new": new, "delta": delta}
        if members:
            weighted_composite_delta += (
                len(members) / SELECTED * float(delta["quality_composite_delta"])
            )
            weighted_score_delta += len(members) / SELECTED * float(delta["score_delta"])
        whole_success_delta += int(delta["whole_table_success_delta"])

    old_all = _aggregate(sorted(ids), old_metrics)
    new_all = _aggregate(sorted(ids), new_metrics)
    all_delta = _delta(old_all, new_all)
    if (
        not math.isclose(
            weighted_composite_delta,
            float(all_delta["quality_composite_delta"]),
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        or not math.isclose(
            weighted_score_delta,
            float(all_delta["score_delta"]),
            rel_tol=0.0,
            abs_tol=1e-12,
        )
        or whole_success_delta != all_delta["whole_table_success_delta"]
    ):
        raise RuntimeError("V2.46.36 paired delta decomposition drifted")

    direction_counts = {}
    for metric in METRICS:
        direction_counts[metric] = {
            "improved": sum(
                new_metrics[item]["metrics"][metric]
                > old_metrics[item]["metrics"][metric]
                for item in ids
            ),
            "tied": sum(
                new_metrics[item]["metrics"][metric]
                == old_metrics[item]["metrics"][metric]
                for item in ids
            ),
            "worsened": sum(
                new_metrics[item]["metrics"][metric]
                < old_metrics[item]["metrics"][metric]
                for item in ids
            ),
        }
    evaluator_transitions = {
        f"old_{old_state}_new_{new_state}": sum(
            bool(old_metrics[item]["evaluator_valid"]) is (old_state == "valid")
            and bool(new_metrics[item]["evaluator_valid"]) is (new_state == "valid")
            for item in ids
        )
        for old_state in ("valid", "invalid")
        for new_state in ("valid", "invalid")
    }

    old_result = parents["old_result"]
    new_result = parents["new_result"]
    value = {
        "artifact_version": 1,
        "role": "v24636_v24630_v24635_aggregate_only_paired_postresult_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "v24630_result_sha256": sha256(root / OLD_RESULT),
            "v24630_postresult_audit_sha256": sha256(root / OLD_POSTAUDIT),
            "v24630_forward_audit_sha256": sha256(root / OLD_FORWARD_AUDIT),
            "v24630_runtime_predictions_sha256": sha256(root / OLD_RUNTIME),
            "v24630_conservative_summary_sha256": sha256(root / OLD_EVAL_SUMMARY),
            "v24635_result_sha256": sha256(root / NEW_RESULT),
            "v24635_postresult_audit_sha256": sha256(root / NEW_POSTAUDIT),
            "v24635_forward_audit_sha256": sha256(root / NEW_FORWARD_AUDIT),
            "v24635_runtime_predictions_sha256": sha256(root / NEW_RUNTIME),
            "v24635_conservative_summary_sha256": sha256(root / NEW_EVAL_SUMMARY),
        },
        "boundary": {
            "both_forwards_and_evaluators_complete_before_diagnosis": True,
            "offline_join_uses_opaque_id_only_for_alignment": True,
            "runtime_prediction_rows_opened_for_completion_kind_projection": True,
            "prediction_field_used": False,
            "evaluator_per_task_rows_opened_for_aggregate_metric_projection": True,
            "mapping_answer_category_question_type_or_split_resource_opened": False,
            "task_identifier_question_prediction_answer_query_url_page_or_credential_emitted": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "same_run_forward_feedback_or_prediction_selection": False,
            "same_run_retry_resume_skip_or_selective_revaluation": False,
        },
        "overall": {
            "old": old_all,
            "new": new_all,
            "delta": all_delta,
            "old_forward_wall_seconds": old_result["efficiency"]["forward_wall_seconds"],
            "new_forward_wall_seconds": new_result["efficiency"]["forward_wall_seconds"],
            "forward_wall_seconds_delta": new_result["efficiency"]["forward_wall_seconds"]
            - old_result["efficiency"]["forward_wall_seconds"],
            "old_model_generated_tables": old_result["metrics"]["all_220"]["model_generated_tables"],
            "new_model_generated_tables": new_result["metrics"]["all_220"]["model_generated_tables"],
            "old_fallback_tables": old_result["metrics"]["all_220"]["fallback_tables"],
            "new_fallback_tables": new_result["metrics"]["all_220"]["fallback_tables"],
        },
        "completion_transition_groups": paired_groups,
        "delta_reconciliation": {
            "weighted_quality_composite_delta": weighted_composite_delta,
            "weighted_score_delta": weighted_score_delta,
            "whole_table_success_delta": whole_success_delta,
            "matches_overall": True,
        },
        "paired_metric_direction_counts": direction_counts,
        "evaluator_validity_transitions": evaluator_transitions,
        "conclusions": {
            "capacity_reliability_improved_in_observed_run": len(old_fallback) == 34
            and len(new_fallback) == 1,
            "all_old_fallbacks_became_model_generated": len(
                groups["old_fallback_to_new_model"]
            )
            == 34,
            "rescued_old_fallback_group_gained_partial_quality": paired_groups[
                "old_fallback_to_new_model"
            ]["delta"]["quality_composite_delta"]
            > 0,
            "rescued_old_fallback_group_gained_whole_table_success": paired_groups[
                "old_fallback_to_new_model"
            ]["delta"]["whole_table_success_delta"]
            > 0,
            "strict_whole_table_primary_metric_improved": all_delta[
                "whole_table_success_delta"
            ]
            > 0,
            "quality_composite_improved": all_delta["quality_composite_delta"] > 0,
            "project_best_whole_table_score_reached": False,
            "sota_reached": False,
            "randomized_causal_effect_of_schedule_established": False,
            "same_public_task_reexecution_limits_causal_and_generalization_claims": True,
            "fallback_reduction_is_not_sufficient_for_exact_table_success": True,
        },
        "next_work": {
            "freeze_20_active_8_slots_240_seconds_as_reliability_baseline": True,
            "primary_optimization_target": "exact_table_objective_alignment_under_fixed_reliability_schedule",
            "first_allowed_experiment": "benchmark_external_table_completion_and_verification_mechanism_gate",
            "required_external_controls": [
                "same_model_search_fetch_token_and_wall_budget",
                "same_20_active_8_slots_240_second_schedule",
                "fixed_table_schema_and_exact_table_success_evaluator",
                "simple_no_entropy_baseline",
                "failure_as_zero",
            ],
            "candidate_mechanisms": [
                "schema_conditioned_coverage_ledger",
                "missing_cell_targeted_retrieval_without_more_total_work",
                "row_and_cell_consistency_verification",
                "deterministic_table_normalization_and_completion_checks",
            ],
            "public_exact220_allowed_from_this_diagnosis": False,
            "per_task_public_benchmark_error_pattern_tuning_allowed": False,
            "new_public_exact220_requires_predeclared_external_gate_and_single_candidate": True,
        },
        "authorization": {
            "benchmark_external_mechanism_design": True,
            "benchmark_external_fresh_evaluation_after_preregistration": True,
            "new_dev64": False,
            "new_exact220": False,
            "same_run_retry_resume_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if OPAQUE.search(encoded) or SECRET.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.46.36 diagnosis emitted prohibited content")
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_report(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    expected = build_report(root, now=int(value.get("created_at_unix", -1)))
    if dict(value) != expected or not _sealed(value, "diagnosis_payload_sha256"):
        raise RuntimeError("V2.46.36 diagnosis drifted")
    return dict(value)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    report = build_report()
    validate_report(ROOT, report)
    publish(ROOT / OUTPUT, report)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "old_fallback": report["overall"]["old_fallback_tables"],
                "new_fallback": report["overall"]["new_fallback_tables"],
                "whole_table_success_delta": report["overall"]["delta"][
                    "whole_table_success_delta"
                ],
                "quality_composite_delta": report["overall"]["delta"][
                    "quality_composite_delta"
                ],
            },
            sort_keys=True,
        )
    )
