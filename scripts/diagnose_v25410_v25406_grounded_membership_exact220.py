#!/usr/bin/env python3
"""Aggregate-only diagnosis of frozen V2.54.06 exact-220 artifacts.

This offline diagnostic runs only after prediction freeze, pushed forward
audit, exactly-once evaluation, and pushed post-result audit.  It validates
the sealed V2.54.06/V2.53.79 task rows, then publishes population aggregates
only.  Visible question text is used solely to recompute label-blind schema and
explicit-membership coverage; no question, task identifier, prediction, page,
query, URL, gold value, benchmark label, per-task score, or correctness value
is emitted.

The diagnosis never feeds an outcome into a forward route.  In particular,
the proposed successor boundary is expressible only from strict membership in
the visible question: membership-absent tasks preserve V2.53.75, while a new
fresh/disjoint gate must validate any membership-present branch.  No model,
search, fetch, evaluator, network, credential, or signed-credit action occurs.
"""

from __future__ import annotations

import argparse
import collections
import copy
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25375_schema_total_changed_safe_runtime as schema  # noqa: E402
from deepwide_agent import v25376_changed_safe_exact220_contract as old_contract  # noqa: E402
from deepwide_agent import v25395_visible_membership_synthesis_runtime as membership  # noqa: E402
from deepwide_agent import v25406_grounded_membership_exact220_contract as contract  # noqa: E402
from scripts import run_v25376_changed_safe_exact220 as old_runner  # noqa: E402
from scripts import run_v25406_grounded_membership_exact220 as runner  # noqa: E402


DATE = "20260813"
OUTPUT = Path(
    f"results/v25410_v25406_grounded_membership_exact220_diagnosis_v1_{DATE}.json"
)
SOURCE = Path(
    "scripts/diagnose_v25410_v25406_grounded_membership_exact220.py"
)
ROLE = "v25410_v25406_grounded_membership_exact220_content_free_diagnosis"

OLD_RESULT = old_contract.RESULT
OLD_POSTAUDIT = old_contract.POSTAUDIT
PEAK_RESULT = contract.PEAK_RESULT


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(
        contract.ordinary(ROOT, relative, tracked=True).read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.54.10 expected one JSON object")
    return value


def _read_rows(
    relative: Path,
    validator: Any,
) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    rows = [
        validator(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.54.10 task denominator drifted")
    return rows


def _artifact_barrier() -> dict[str, Any]:
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    old_forward = old_runner.validate_forward_result(
        _read(old_contract.FORWARD_RESULT)
    )
    forward_audit = _read(contract.FORWARD_AUDIT)
    result = _read(contract.RESULT)
    post = _read(contract.POSTAUDIT)
    old_result = _read(OLD_RESULT)
    old_post = _read(OLD_POSTAUDIT)
    peak = _read(PEAK_RESULT)
    if (
        forward.get("terminal_predictions") != contract.TASK_COUNT
        or forward_audit.get("audit_valid") is not True
        or forward_audit.get("findings") != []
        or forward_audit.get("forward_result_sha256")
        != contract.sha256(ROOT / contract.FORWARD_RESULT)
        or result.get("status") != "exact220_single_rollout_complete"
        or result.get("selected") != contract.TASK_COUNT
        or result.get("claims", {}).get("sota") is not False
        or post.get("audit_valid") is not True
        or post.get("findings") != []
        or post.get("checks", {}).get("joined_official_merged_rows_exact220")
        is not True
        or post.get("checks", {}).get("no_selective_retry_or_revaluation")
        is not True
        or old_forward.get("terminal_predictions") != contract.TASK_COUNT
        or old_result.get("status") != "exact220_single_rollout_complete"
        or old_post.get("audit_valid") is not True
        or old_post.get("findings") != []
        or peak.get("status") != "exact220_single_rollout_complete"
    ):
        raise RuntimeError("V2.54.10 frozen artifact barrier drifted")
    return {
        "forward": forward,
        "result": result,
        "old_forward": old_forward,
        "old_result": old_result,
        "peak_result": peak,
    }


def _chain(value: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    current = dict(value)
    first = dict(current["private_parent_result"])
    second = dict(first["private_parent_result"])
    third = dict(second["private_parent_result"])
    return current, first, second, third


def _sum(values: list[Mapping[str, Any]], name: str) -> int:
    return sum(int(value[name]) for value in values)


def _count(values: list[Mapping[str, Any]], name: str) -> int:
    return sum(bool(value[name]) for value in values)


def _published(metrics: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "selected": int(metrics["selected"]),
        "whole_table_successes": int(metrics["whole_table_successes"]),
        "score": float(metrics["score"]),
        "entity_acc": float(metrics["entity_acc"]),
        "f1_by_row": float(metrics["f1_by_row"]),
        "f1_by_item": float(metrics["f1_by_item"]),
        "column_f1": float(metrics["column_f1"]),
        "quality_composite": float(metrics["quality_composite"]),
        "evaluator_valid": int(metrics["evaluator_valid"]),
        "evaluator_invalid_or_not_run": int(
            metrics["evaluator_invalid_or_not_run"]
        ),
    }


def _funnel(
    tasks: list[dict[str, str]],
    rows: list[dict[str, Any]],
    old_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    if (
        [row["opaque_id"] for row in rows]
        != [row["opaque_id"] for row in old_rows]
        or [row["opaque_id"] for row in rows]
        != [task["opaque_id"] for task in tasks]
    ):
        raise RuntimeError("V2.54.10 cross-run task order drifted")

    limits = schema.score.ScoreFirstLimits(**contract.LIMITS)
    visible_schema_sources: collections.Counter[str] = collections.Counter()
    visible_membership_sources: collections.Counter[str] = collections.Counter()
    visible_member_total = 0
    for task in tasks:
        _plan, _observation, source = schema.projected_plan(
            {}, task["question"], limits
        )
        visible_schema_sources[source] += 1
        members, membership_source = membership.visible_membership(
            task["question"]
        )
        visible_membership_sources[membership_source] += 1
        visible_member_total += len(members)

    completed_rows = [row for row in rows if row["runtime_completed"]]
    completed = [row["runtime_result"] for row in completed_rows]
    chains = [_chain(value) for value in completed]
    record_receipts = [value[0]["grounded_record_membership_receipt"] for value in chains]
    membership_receipts = [value[1]["visible_membership_synthesis_receipt"] for value in chains]
    hybrid_receipts = [value[2]["hybrid_record_fallback_receipt"] for value in chains]
    base_receipts = [value[3]["content_free_receipt"] for value in chains]
    edit_receipts = [value["changed_safe_edit_receipt"] for value in base_receipts]

    outer = [row for row in rows if not row["runtime_completed"]]
    completed_fallbacks = [
        row for row in completed_rows if row["prediction_kind"] == "fallback"
    ]
    matched_old = [
        old
        for current, old in zip(rows, old_rows, strict=True)
        if not current["runtime_completed"]
    ]
    outer_health = sum(
        sum(int(value) for value in row["effect_health"].values())
        for row in outer
    )
    outer_provider_success = sum(
        row["actual_effect_snapshot"]["model_provider_successes"] == 3
        for row in outer
    )
    outer_exact_effect = sum(
        row["actual_effect_snapshot"]["logical_queries"] == 4
        and row["actual_effect_snapshot"]["fetch_requests"] == 10
        and row["actual_effect_snapshot"]["model_logical_requests"] == 3
        for row in outer
    )
    outer_stage_receipts = sum(
        row["content_free_stage_receipt"] is not None for row in outer
    )
    outer_types = collections.Counter(
        str(row["outer_failure_type"] or "none") for row in outer
    )

    record_applied_with_raw = sum(
        receipt["grounded_record_membership_constraint_applied"]
        and receipt["grounded_raw_record_count"] > 0
        for receipt in record_receipts
    )
    record_unapplied_raw = sum(
        int(receipt["grounded_raw_record_count"])
        for receipt in record_receipts
        if not receipt["grounded_record_membership_constraint_applied"]
    )
    changed_applied = sum(
        chain[0]["prediction_changed"]
        and chain[0]["grounded_record_membership_receipt"][
            "grounded_record_membership_constraint_applied"
        ]
        for chain in chains
    )
    changed_unapplied = sum(
        chain[0]["prediction_changed"]
        and not chain[0]["grounded_record_membership_receipt"][
            "grounded_record_membership_constraint_applied"
        ]
        for chain in chains
    )

    counts = {
        "task_count": len(rows),
        "runtime_completed_tasks": len(completed_rows),
        "outer_failure_as_zero_tasks": len(outer),
        "completed_fallback_tasks": len(completed_fallbacks),
        "model_generated_tasks": sum(
            row["prediction_kind"] == "model_generated" for row in rows
        ),
        "visible_membership_task_count": len(rows)
        - visible_membership_sources.get("none", 0),
        "visible_member_total": visible_member_total,
        "completed_membership_constraint_applied_tasks": _count(
            membership_receipts, "membership_constraint_applied"
        ),
        "completed_visible_membership_exact_tasks": _count(
            membership_receipts, "base_visible_membership_exact"
        ),
        "completed_grounded_record_constraint_applied_tasks": _count(
            record_receipts, "grounded_record_membership_constraint_applied"
        ),
        "grounded_record_constraint_applied_with_raw_record_tasks": record_applied_with_raw,
        "grounded_raw_record_tasks": sum(
            value["grounded_raw_record_count"] > 0 for value in record_receipts
        ),
        "grounded_raw_record_count": _sum(
            record_receipts, "grounded_raw_record_count"
        ),
        "grounded_raw_membership_match_count": _sum(
            record_receipts, "grounded_raw_membership_match_count"
        ),
        "grounded_raw_membership_mismatch_count": _sum(
            record_receipts, "grounded_raw_membership_mismatch_count"
        ),
        "grounded_raw_membership_unclassified_count": _sum(
            record_receipts, "grounded_raw_membership_unclassified_count"
        ),
        "raw_records_outside_membership_constraint": record_unapplied_raw,
        "joint_raw_record_tasks": sum(
            value["joint_raw_record_count"] > 0 for value in hybrid_receipts
        ),
        "joint_raw_record_count": _sum(hybrid_receipts, "joint_raw_record_count"),
        "selected_raw_record_tasks": sum(
            value["selected_raw_record_count"] > 0 for value in hybrid_receipts
        ),
        "selected_raw_record_count": _sum(
            hybrid_receipts, "selected_raw_record_count"
        ),
        "parsed_record_count": _sum(edit_receipts, "parsed_record_count"),
        "parsed_field_count": _sum(edit_receipts, "parsed_field_count"),
        "verified_record_tasks": sum(
            value["verified_record_count"] > 0 for value in edit_receipts
        ),
        "verified_record_count": _sum(edit_receipts, "verified_record_count"),
        "verified_field_count": _sum(edit_receipts, "verified_field_count"),
        "missing_row_rejected_field_count": _sum(
            edit_receipts, "missing_row_rejected_field_count"
        ),
        "unchanged_verified_coordinate_count": _sum(
            edit_receipts, "unchanged_verified_coordinate_count"
        ),
        "changed_safe_tasks": sum(
            value["changed_safe_coordinate_count"] > 0 for value in edit_receipts
        ),
        "changed_safe_coordinate_count": _sum(
            edit_receipts, "changed_safe_coordinate_count"
        ),
        "prediction_changed_tasks": sum(value[0]["prediction_changed"] for value in chains),
        "attributable_prediction_changed_tasks": sum(
            value[0]["attributable_prediction_change"] for value in chains
        ),
        "prediction_changed_with_membership_constraint_tasks": changed_applied,
        "prediction_changed_without_membership_constraint_tasks": changed_unapplied,
        "positive_signed_credit_count": _sum(
            base_receipts, "positive_signed_credit_count"
        ),
        "outer_value_error_tasks": outer_types.get("ValueError", 0),
        "outer_stage_receipt_tasks": outer_stage_receipts,
        "outer_exact_4_query_10_fetch_3_model_effect_tasks": outer_exact_effect,
        "outer_three_provider_success_tasks": outer_provider_success,
        "outer_effect_health_event_count": outer_health,
        "matched_v25379_runtime_completed_tasks": sum(
            row["runtime_completed"] for row in matched_old
        ),
        "matched_v25379_model_generated_tasks": sum(
            row["prediction_kind"] == "model_generated" for row in matched_old
        ),
        "matched_v25379_exact_4_query_10_fetch_3_model_effect_tasks": sum(
            row["actual_effect_snapshot"]["logical_queries"] == 4
            and row["actual_effect_snapshot"]["fetch_requests"] == 10
            and row["actual_effect_snapshot"]["model_logical_requests"] == 3
            for row in matched_old
        ),
    }
    return {
        "counts": counts,
        "visible_schema_source_counts": dict(sorted(visible_schema_sources.items())),
        "visible_membership_source_counts": dict(
            sorted(visible_membership_sources.items())
        ),
        "outer_failure_type_counts": dict(sorted(outer_types.items())),
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    barrier = _artifact_barrier()
    rows = _read_rows(contract.TASK_ROWS, runner.validate_task_row)
    old_rows = _read_rows(old_contract.TASK_ROWS, old_runner.validate_task_row)
    tasks = contract.task_vector(ROOT)
    funnel = _funnel(tasks, rows, old_rows)
    counts = funnel["counts"]
    current = _published(barrier["result"]["metrics"]["all_220"])
    old = _published(barrier["old_result"]["metrics"]["all_220"])
    peak = _published(barrier["peak_result"]["metrics"]["all_220"])
    deltas = {
        "whole_table_success_delta": current["whole_table_successes"]
        - old["whole_table_successes"],
        "score_delta": current["score"] - old["score"],
        "entity_acc_delta": current["entity_acc"] - old["entity_acc"],
        "f1_by_row_delta": current["f1_by_row"] - old["f1_by_row"],
        "f1_by_item_delta": current["f1_by_item"] - old["f1_by_item"],
        "column_f1_delta": current["column_f1"] - old["column_f1"],
        "quality_composite_delta": current["quality_composite"]
        - old["quality_composite"],
    }
    peak_deltas = {
        "whole_table_success_delta": current["whole_table_successes"]
        - peak["whole_table_successes"],
        "quality_composite_delta": current["quality_composite"]
        - peak["quality_composite"],
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "source_bindings": {
            "v25406_task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "v25406_forward_result_sha256": contract.sha256(
                ROOT / contract.FORWARD_RESULT
            ),
            "v25406_forward_audit_sha256": contract.sha256(
                ROOT / contract.FORWARD_AUDIT
            ),
            "v25406_result_sha256": contract.sha256(ROOT / contract.RESULT),
            "v25406_postresult_audit_sha256": contract.sha256(
                ROOT / contract.POSTAUDIT
            ),
            "v25379_task_rows_sha256": contract.sha256(ROOT / old_contract.TASK_ROWS),
            "v25379_forward_result_sha256": contract.sha256(
                ROOT / old_contract.FORWARD_RESULT
            ),
            "v25379_result_sha256": contract.sha256(ROOT / OLD_RESULT),
            "v25379_postresult_audit_sha256": contract.sha256(
                ROOT / OLD_POSTAUDIT
            ),
            "v24857_peak_result_sha256": contract.sha256(ROOT / PEAK_RESULT),
        },
        "funnel": funnel,
        "published_all220_metrics": {
            "v25406": current,
            "v25379": old,
            "v24857_single_rollout_peak": peak,
            "v25406_minus_v25379": deltas,
            "v25406_minus_v24857_peak": peak_deltas,
        },
        "diagnosis": {
            "v25406_exact_up_but_all_soft_metrics_and_composite_down_vs_v25379": (
                deltas["whole_table_success_delta"] == 2
                and deltas["quality_composite_delta"] < 0
                and all(
                    deltas[name] < 0
                    for name in (
                        "entity_acc_delta",
                        "f1_by_row_delta",
                        "f1_by_item_delta",
                        "column_f1_delta",
                    )
                )
            ),
            "visible_membership_coverage_is_eleven_of_220": (
                counts["visible_membership_task_count"] == 11
            ),
            "successful_membership_constrained_grounded_record_reach_is_zero": (
                counts["completed_grounded_record_constraint_applied_tasks"] == 9
                and counts[
                    "grounded_record_constraint_applied_with_raw_record_tasks"
                ]
                == 0
            ),
            "all_grounded_raw_records_arose_without_membership_constraint": (
                counts["grounded_raw_record_count"] == 14
                and counts["raw_records_outside_membership_constraint"] == 14
            ),
            "sole_attributable_changed_safe_edit_arose_without_membership_constraint": (
                counts["attributable_prediction_changed_tasks"] == 1
                and counts[
                    "prediction_changed_with_membership_constraint_tasks"
                ]
                == 0
                and counts[
                    "prediction_changed_without_membership_constraint_tasks"
                ]
                == 1
            ),
            "membership_outer_utility_not_identified_by_independent_cold_rollouts": True,
            "eleven_new_outer_value_errors_followed_healthy_complete_provider_effects": (
                counts["outer_value_error_tasks"] == 11
                and counts["outer_exact_4_query_10_fetch_3_model_effect_tasks"] == 11
                and counts["outer_three_provider_success_tasks"] == 11
                and counts["outer_effect_health_event_count"] == 0
                and counts["outer_stage_receipt_tasks"] == 0
            ),
            "same_eleven_tasks_completed_model_generated_in_v25379": (
                counts["matched_v25379_runtime_completed_tasks"] == 11
                and counts["matched_v25379_model_generated_tasks"] == 11
            ),
            "exact_postprovider_exception_source_not_identifiable_from_content_free_artifacts": True,
            "entropy_information_gain_signed_credit_evidence_absent": (
                counts["positive_signed_credit_count"] == 0
            ),
        },
        "decision": {
            "v25406_quality": "no_go",
            "repeat_retry_resume_backfill_or_selective_rerun_v25406": False,
            "public_exact220_successor_authorized": False,
            "next_build_priority": "visible_membership_route_gate_parent_preservation_and_postprovider_totality",
            "membership_absent_branch": "byte_exact_v25375_parent_path",
            "membership_present_branch": "v25401_only_after_fresh_disjoint_branch_gate",
            "next_gate_requires_fresh_external_shared_prefix_population": True,
            "runtime_route_may_use_visible_membership_but_not_historical_outcome": True,
            "historical_score_correctness_or_evaluator_feedback_runtime_routing": False,
            "entropy_or_information_gain_signed_credit_authorized": False,
        },
        "content_free_aggregate_only": True,
        "visible_question_used_only_for_offline_label_blind_aggregate_features": True,
        "contains_question_opaque_id_query_url_page_quote_record_value_prediction_gold_label_per_task_score_or_per_task_correctness": False,
        "model_search_fetch_evaluator_network_or_external_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "next_build_only": True,
            "new_external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    counts = copied.get("funnel", {}).get("counts", {})
    diagnosis = copied.get("diagnosis") or {}
    decision = copied.get("decision") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or counts.get("task_count") != 220
        or counts.get("runtime_completed_tasks") != 209
        or counts.get("outer_failure_as_zero_tasks") != 11
        or counts.get("completed_fallback_tasks") != 5
        or counts.get("model_generated_tasks") != 204
        or counts.get("visible_membership_task_count") != 11
        or counts.get("completed_membership_constraint_applied_tasks") != 9
        or counts.get("completed_grounded_record_constraint_applied_tasks") != 9
        or counts.get("grounded_record_constraint_applied_with_raw_record_tasks") != 0
        or counts.get("grounded_raw_record_count") != 14
        or counts.get("raw_records_outside_membership_constraint") != 14
        or counts.get("selected_raw_record_count") != 18
        or counts.get("verified_record_count") != 3
        or counts.get("verified_field_count") != 3
        or counts.get("missing_row_rejected_field_count") != 2
        or counts.get("changed_safe_tasks") != 1
        or counts.get("attributable_prediction_changed_tasks") != 1
        or counts.get("prediction_changed_with_membership_constraint_tasks") != 0
        or counts.get("outer_value_error_tasks") != 11
        or counts.get("outer_stage_receipt_tasks") != 0
        or counts.get("outer_three_provider_success_tasks") != 11
        or counts.get("outer_effect_health_event_count") != 0
        or counts.get("matched_v25379_runtime_completed_tasks") != 11
        or counts.get("matched_v25379_model_generated_tasks") != 11
        or counts.get("positive_signed_credit_count") != 0
        or not diagnosis
        or not all(diagnosis.values())
        or decision
        != {
            "v25406_quality": "no_go",
            "repeat_retry_resume_backfill_or_selective_rerun_v25406": False,
            "public_exact220_successor_authorized": False,
            "next_build_priority": "visible_membership_route_gate_parent_preservation_and_postprovider_totality",
            "membership_absent_branch": "byte_exact_v25375_parent_path",
            "membership_present_branch": "v25401_only_after_fresh_disjoint_branch_gate",
            "next_gate_requires_fresh_external_shared_prefix_population": True,
            "runtime_route_may_use_visible_membership_but_not_historical_outcome": True,
            "historical_score_correctness_or_evaluator_feedback_runtime_routing": False,
            "entropy_or_information_gain_signed_credit_authorized": False,
        }
        or copied.get("content_free_aggregate_only") is not True
        or copied.get(
            "visible_question_used_only_for_offline_label_blind_aggregate_features"
        )
        is not True
        or copied.get("contains_question_opaque_id_query_url_page_quote_record_value_prediction_gold_label_per_task_score_or_per_task_correctness")
        is not False
        or copied.get("model_search_fetch_evaluator_network_or_external_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or authorization
        != {
            "next_build_only": True,
            "new_external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.10 diagnosis drifted")
    return copied


def _publish(value: Mapping[str, Any]) -> None:
    path = ROOT / OUTPUT
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    value = build_diagnosis()
    if not args.validate_only:
        _publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "diagnosis": value["diagnosis"],
                "decision": value["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
