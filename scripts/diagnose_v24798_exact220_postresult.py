#!/usr/bin/env python3
"""Aggregate-only post-result diagnosis of the frozen V2.47.98 exact-220.

This program runs only after the prediction freeze, official evaluation, and
post-result audit.  It aligns already released per-task rows in memory, emits
only fixed-denominator aggregates, performs no network/model/search/fetch or
evaluator effect, and grants no benchmark launch authority.
"""

from __future__ import annotations

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

from deepwide_agent import v24798_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24796_deadline_tavily_search import (  # noqa: E402
    validate_receipt as validate_direct_receipt,
)
from scripts import finalize_v24798_exact220 as finalizer  # noqa: E402


OUTPUT = Path(
    f"results/v24798_exact220_postresult_diagnosis_v1_{contract.DATE}.json"
)
BASELINE_RESULT = Path("results/v24635_exact220_result_v1_20260806.json")
BASELINE_SUMMARY = Path(
    "outputs/v24635_exact220_v1_20260806/evaluator/conservative_summary.json"
)
CURRENT_SUMMARY = finalizer.SUMMARY
METRICS = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1", "score")


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.98 diagnosis expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.98 diagnosis expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _metric_projection(row: Mapping[str, Any]) -> dict[str, float]:
    metrics = row.get("metrics") or {}
    return {name: float(metrics[name]) for name in METRICS}


def _mean(rows: list[dict[str, Any]], field: str) -> float:
    return round(sum(float(row[field]) for row in rows) / len(rows), 12)


def _group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise RuntimeError("V2.47.98 diagnosis cannot summarize an empty group")
    return {
        "tasks": len(rows),
        "evaluator_valid": sum(row["evaluator_valid"] for row in rows),
        "whole_table_successes": sum(row["metrics"]["score"] > 0 for row in rows),
        "metrics": {
            name: round(
                sum(row["metrics"][name] for row in rows) / len(rows), 12
            )
            for name in METRICS
        },
        "paired_delta_from_v24635": {
            name: round(
                sum(row["metrics"][name] - row["old_metrics"][name] for row in rows)
                / len(rows),
                12,
            )
            for name in METRICS
        },
        "retrieval_means": {
            name: _mean(rows, name)
            for name in (
                "queries_executed",
                "fetches_attempted",
                "usable_pages",
                "unique_hosts",
                "content_chars",
                "synthesized_rows",
                "unknown_cell_ratio",
                "risk_before",
                "risk_after",
            )
        },
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    protocol = finalizer.validate_evaluator_protocol(
        _read(ROOT / finalizer.EVALUATOR_PROTOCOL)
    )
    final = _read(ROOT / finalizer.FINAL_RESULT)
    post = _read(ROOT / finalizer.POSTAUDIT)
    finalizer.validate_final_result(final, protocol)
    finalizer.validate_postresult_audit(post)
    barrier = finalizer._forward_barrier()
    baseline_result = _read(ROOT / BASELINE_RESULT)
    current_summary = _read(ROOT / CURRENT_SUMMARY)
    baseline_summary = _read(ROOT / BASELINE_SUMMARY)
    current_rows = current_summary.get("per_task") or []
    baseline_rows = baseline_summary.get("per_task") or []
    if (
        len(current_rows) != contract.SELECTED_COUNT
        or len(baseline_rows) != contract.SELECTED_COUNT
        or final.get("metrics", {}).get("all_220", {}).get("selected")
        != contract.SELECTED_COUNT
        or post.get("audit_valid") is not True
        or not _sealed(post, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.98 diagnosis parent barrier drifted")
    current = {str(row["opaque_id"]): row for row in current_rows}
    baseline = {str(row["opaque_id"]): row for row in baseline_rows}
    if set(current) != set(baseline) or len(current) != contract.SELECTED_COUNT:
        raise RuntimeError("V2.47.98 diagnosis paired population drifted")

    projected: list[dict[str, Any]] = []
    decisions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    reasons: Counter[str] = Counter()
    row_recall_bands: dict[str, list[dict[str, Any]]] = defaultdict(list)
    explicit_targets: Counter[int] = Counter()
    evaluator_errors: Counter[str] = Counter()
    for position in range(1, contract.SELECTED_COUNT + 1):
        envelope = _read(
            ROOT / contract.TASK_ROOT / f"task_{position:04d}" / "result.json"
        )
        result = envelope.get("result") or {}
        opaque_id = str(result.get("opaque_id", ""))
        if opaque_id not in current:
            raise RuntimeError("V2.47.98 diagnosis task alignment drifted")
        retrieval = result.get("two_wave_retrieval") or {}
        receipt = retrieval.get("receipt") or {}
        controller = receipt.get("controller") or {}
        total = receipt.get("total") or {}
        table = (result.get("telemetry") or {}).get("table") or {}
        direct = validate_direct_receipt(
            _read(
                ROOT
                / contract.TASK_ROOT
                / f"task_{position:04d}"
                / contract.DIRECT_RECEIPT_NAME
            )
        )
        new_row = current[opaque_id]
        old_row = baseline[opaque_id]
        metric = _metric_projection(new_row)
        old_metric = _metric_projection(old_row)
        before = controller.get("four_layer_risk_before") or {}
        after = controller.get("four_layer_expected_risk_after") or {}
        row = {
            "evaluator_valid": new_row.get("evaluator_valid") is True,
            "metrics": metric,
            "old_metrics": old_metric,
            "queries_executed": int(total["queries_executed"]),
            "fetches_attempted": int(total["fetches_attempted"]),
            "usable_pages": int(total["usable_pages"]),
            "unique_hosts": int(total["unique_hosts"]),
            "content_chars": int(total["content_chars"]),
            "synthesized_rows": int(table["row_count"]),
            "unknown_cell_ratio": float(table["unknown_cell_ratio"]),
            "risk_before": sum(float(value) for value in before.values()),
            "risk_after": sum(float(value) for value in after.values()),
            "direct_successful_queries": int(direct["successful_queries"]),
            "direct_failed_queries": int(direct["failed_queries"]),
        }
        decision = str(controller.get("decision"))
        reason = str(controller.get("reason"))
        target = int(controller.get("first_wave", {}).get("explicit_row_target", -1))
        if decision not in {"expand", "stop"} or target < 0:
            raise RuntimeError("V2.47.98 diagnosis controller projection drifted")
        decisions[decision].append(row)
        reasons[reason] += 1
        explicit_targets[target] += 1
        recall = metric["f1_by_row"]
        band = "low_lt_0_2" if recall < 0.2 else "high_ge_0_5" if recall >= 0.5 else "middle"
        row_recall_bands[band].append(row)
        if new_row.get("evaluator_valid") is not True:
            message = str(new_row.get("evaluator_error") or "")
            kind = "out_of_range_metric" if "out-of-range" in message else "internal_error"
            evaluator_errors[kind] += 1
        projected.append(row)

    direct_totals = barrier["summary"].get("direct_search_totals") or {}
    all_metrics = final["metrics"]["all_220"]
    old_metrics = baseline_result["metrics"]["all_220"]
    overall_delta = {
        "whole_table_successes": int(all_metrics["whole_table_successes"])
        - int(old_metrics["whole_table_successes"]),
        **{
            name: round(float(all_metrics[name]) - float(old_metrics[name]), 12)
            for name in (*METRICS[:-1], "quality_composite", "score")
        },
    }
    checks = {
        "exact220_prediction_and_evaluator_barrier": len(projected) == 220,
        "all_model_generated_no_fallback": barrier["summary"].get(
            "model_generated_tables"
        )
        == 220
        and barrier["summary"].get("fallback_tables") == 0,
        "direct_provider_all_2xx": direct_totals.get("provider_attempts")
        == direct_totals.get("status_2xx"),
        "direct_transport_failures_zero": direct_totals.get("transport_failures")
        == 0,
        "direct_slot_timeouts_zero": direct_totals.get("slot_timeouts") == 0,
        "all_explicit_row_targets_zero": explicit_targets == Counter({0: 220}),
        "controller_decisions_cover_exact220": sum(map(len, decisions.values())) == 220,
        "evaluator_error_taxonomy_covers_invalid": sum(evaluator_errors.values())
        == int(all_metrics["evaluator_invalid_or_not_run"]),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v24798_exact220_aggregate_only_postresult_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "transport_recovered_row_coverage_controller_unresolved",
        "parents": {
            "result_sha256": contract.sha256(ROOT / finalizer.FINAL_RESULT),
            "postresult_audit_sha256": contract.sha256(ROOT / finalizer.POSTAUDIT),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "current_conservative_summary_sha256": contract.sha256(ROOT / CURRENT_SUMMARY),
            "v24635_result_sha256": contract.sha256(ROOT / BASELINE_RESULT),
            "v24635_conservative_summary_sha256": contract.sha256(
                ROOT / BASELINE_SUMMARY
            ),
        },
        "overall": {
            "current": {
                "whole_table_successes": all_metrics["whole_table_successes"],
                **{name: all_metrics[name] for name in (*METRICS[:-1], "quality_composite", "score")},
            },
            "paired_delta_from_v24635": overall_delta,
            "forward_wall_seconds": barrier["forward"]["forward_wall_seconds"],
            "model_generated_tables": barrier["forward"]["model_generated_tables"],
            "fallback_tables": barrier["forward"]["fallback_tables"],
        },
        "transport": {
            "provider_attempts": direct_totals["provider_attempts"],
            "status_2xx": direct_totals["status_2xx"],
            "successful_queries": direct_totals["successful_queries"],
            "failed_queries": direct_totals["failed_queries"],
            "projected_url_leads": direct_totals["projected_url_leads"],
            "transport_failures": direct_totals["transport_failures"],
            "slot_timeouts": direct_totals["slot_timeouts"],
            "key_local_disables": direct_totals["key_local_disables"],
        },
        "controller": {
            "decision_groups": {
                name: _group(rows) for name, rows in sorted(decisions.items())
            },
            "reason_counts": dict(sorted(reasons.items())),
            "explicit_row_target_histogram": {
                str(key): explicit_targets[key] for key in sorted(explicit_targets)
            },
            "row_recall_bands": {
                name: _group(rows) for name, rows in sorted(row_recall_bands.items())
            },
        },
        "evaluator": {
            "valid": all_metrics["evaluator_valid"],
            "invalid_failure_as_zero": all_metrics["evaluator_invalid_or_not_run"],
            "error_taxonomy": dict(sorted(evaluator_errors.items())),
            "selective_retry_or_revaluation": False,
        },
        "diagnosis": {
            "azure_hosted_search_transport_was_primary_v24791_regression": True,
            "tavily_url_only_transport_recovered_reliable_retrieval": True,
            "current_dominant_quality_failure_is_proven_causal": False,
            "row_coverage_or_row_eligibility_is_next_testable_bottleneck": True,
            "page_count_host_count_and_character_sufficiency_proves_open_set_coverage": False,
            "current_controller_received_any_explicit_row_target": False,
            "controller_decision_group_comparison_is_randomized_or_causal": False,
            "full_budget_no_entropy_comparator_is_required_before_claiming_entropy_value": True,
        },
        "next_gate": {
            "candidate": "fixed_full_4_query_10_fetch_no_entropy_control",
            "same_visible_task_model_prompt_renderer_and_hard_caps": True,
            "only_second_wave_admission_policy_changes": True,
            "synthetic_content_free_mechanism_gate_required_first": True,
            "fresh_exact220_required_for_quality_claim": True,
            "same_run_retry_resume_skip_or_selective_rerun": False,
        },
        "source_policy": {
            "all_predictions_and_official_evaluation_terminal_before_diagnosis": True,
            "offline_per_task_join_used_only_for_aggregate_projection": True,
            "question_prediction_query_url_page_answer_or_credential_emitted": False,
            "benchmark_category_question_type_or_gold_used": False,
            "same_run_forward_feedback_or_prediction_selection": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        },
        "checks": checks,
        "findings": findings,
        "diagnosis_valid": not findings,
        "authorization": {
            "synthetic_full_budget_control_design": not findings,
            "new_exact220_launch": False,
            "evaluator": False,
            "retry_resume_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    if (
        copied.get("role")
        != "v24798_exact220_aggregate_only_postresult_diagnosis"
        or copied.get("status")
        != "transport_recovered_row_coverage_controller_unresolved"
        or copied.get("diagnosis_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("diagnosis", {}).get(
            "current_dominant_quality_failure_is_proven_causal"
        )
        is not False
        or copied.get("diagnosis", {}).get(
            "full_budget_no_entropy_comparator_is_required_before_claiming_entropy_value"
        )
        is not True
        or copied.get("authorization")
        != {
            "synthetic_full_budget_control_design": True,
            "new_exact220_launch": False,
            "evaluator": False,
            "retry_resume_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.98 postresult diagnosis drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
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
