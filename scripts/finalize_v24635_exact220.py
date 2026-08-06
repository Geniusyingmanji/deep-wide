#!/usr/bin/env python3
"""Evaluate all 220 frozen V2.46.35 predictions and publish conservative metrics."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24635_exact220_contract import (  # noqa: E402
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    LEASE_PATH,
    OUTPUT_ROOT,
    PREDICTION_FREEZE,
    PROTOCOL_ID,
    RUNTIME_PREDICTIONS,
    RUN_SUMMARY,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    payload_sha256,
    read_object,
    selected_ids,
    sha256,
    validate_forward_contract,
)
from scripts import finalize_v24287_exact220 as base  # noqa: E402
from scripts.finalize_fullset_rollout import summarize_rollout  # noqa: E402
from scripts.preregister_v24635_exact220 import publish_new  # noqa: E402
from scripts.preregister_v24635_exact220_evaluator import (  # noqa: E402
    EVALUATOR_ROOT,
    EVALUATOR_WORKERS,
    FINAL_RESULT,
    FORWARD_AUDIT,
    MAPPING_PATH,
    PROTOCOL,
    validate_protocol,
)


PREPARE_ATTESTATION = EVALUATOR_ROOT / "prepare_attestation.json"
JOINED_OUTCOMES = EVALUATOR_ROOT / "terminal_outcomes_evaluator_joined.jsonl"
OFFICIAL_PREDICTIONS = EVALUATOR_ROOT / "official_predictions.jsonl"
EVALUATOR_RUNS = EVALUATOR_ROOT / "official_eval_workers"
EVALUATOR_LOGS = EVALUATOR_ROOT / "logs"
MERGED_RESULTS = EVALUATOR_ROOT / "official_eval_results.jsonl"
MERGE_ATTESTATION = EVALUATOR_ROOT / "merge_attestation.json"
SUMMARY = EVALUATOR_ROOT / "conservative_summary.json"
EVALUATOR_OWNER = "v24635_exact220_evaluator_v1"
EVALUATOR_PURPOSE = "postfreeze_fixed_partition_parallel_exact220_official_evaluator"
V24267_RESULT = Path("results/v24267_exact220_result_v1_20260802.json")
V24287_RESULT = Path("results/v24287_exact220_result_v1_20260803.json")
V24630_RESULT = Path("results/v24630_exact220_result_v1_20260806.json")


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def validate_forward_barrier(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    forward = read_object(root / FORWARD_RESULT)
    freeze = read_object(root / PREDICTION_FREEZE)
    audit = read_object(root / FORWARD_AUDIT)
    rows = [
        json.loads(line)
        for line in (root / RUNTIME_PREDICTIONS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if (
        forward.get("terminal_predictions") != SELECTED_COUNT
        or forward.get("official_evaluator_called") is not False
        or freeze.get("terminal") != SELECTED_COUNT
        or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        or freeze.get("runtime_predictions_sha256") != sha256(root / RUNTIME_PREDICTIONS)
        or freeze.get("run_summary_sha256") != sha256(root / RUN_SUMMARY)
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("postfreeze_exact220_evaluator") is not True
        or audit.get("forward_result_sha256") != sha256(root / FORWARD_RESULT)
        or len(rows) != SELECTED_COUNT
        or [row.get("opaque_id") for row in rows] != selected_ids(contract)
        or any(row.get("status") != "completed" or not str(row.get("prediction", "")).strip() for row in rows)
        or not _sealed(forward, "result_payload_sha256")
        or not _sealed(freeze, "freeze_payload_sha256")
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.35 evaluator forward barrier drifted")
    return {"forward": forward, "freeze": freeze, "audit": audit, "runtime_rows": rows}


def fixed_partitions(
    selected: int = SELECTED_COUNT, workers: int = EVALUATOR_WORKERS
) -> list[tuple[int, int]]:
    if selected != SELECTED_COUNT or workers != EVALUATOR_WORKERS:
        raise ValueError("V2.46.35 evaluator partition identity drifted")
    base_size, remainder = divmod(selected, workers)
    output: list[tuple[int, int]] = []
    start = 0
    for index in range(workers):
        size = base_size + (1 if index < remainder else 0)
        output.append((start, start + size))
        start += size
    if start != SELECTED_COUNT or any(end <= start for start, end in output):
        raise RuntimeError("V2.46.35 evaluator partitions are incomplete")
    return output


def _configure_base() -> None:
    assignments = {
        "PROTOCOL": PROTOCOL,
        "FINAL_RESULT": FINAL_RESULT,
        "EVALUATOR_ROOT": EVALUATOR_ROOT,
        "EVALUATOR_WORKERS": EVALUATOR_WORKERS,
        "MAPPING_PATH": MAPPING_PATH,
        "PREPARE_ATTESTATION": PREPARE_ATTESTATION,
        "JOINED_OUTCOMES": JOINED_OUTCOMES,
        "OFFICIAL_PREDICTIONS": OFFICIAL_PREDICTIONS,
        "EVALUATOR_RUNS": EVALUATOR_RUNS,
        "EVALUATOR_LOGS": EVALUATOR_LOGS,
        "MERGED_RESULTS": MERGED_RESULTS,
        "MERGE_ATTESTATION": MERGE_ATTESTATION,
        "SUMMARY": SUMMARY,
        "EVALUATOR_OWNER": EVALUATOR_OWNER,
        "EVALUATOR_PURPOSE": EVALUATOR_PURPOSE,
        "FORWARD_CONTRACT": FORWARD_CONTRACT,
        "FORWARD_RESULT": FORWARD_RESULT,
        "OUTPUT_ROOT": OUTPUT_ROOT,
        "PREDICTION_FREEZE": PREDICTION_FREEZE,
        "RUNTIME_PREDICTIONS": RUNTIME_PREDICTIONS,
        "RUN_SUMMARY": RUN_SUMMARY,
        "SOURCE_MANIFEST": SOURCE_MANIFEST,
        "SELECTED_COUNT": SELECTED_COUNT,
        "PROTOCOL_ID": PROTOCOL_ID,
        "LEASE_PATH": LEASE_PATH,
    }
    for name, value in assignments.items():
        setattr(base, name, value)
    base.validate_protocol = validate_protocol
    base.validate_forward_contract = validate_forward_contract
    base.validate_forward_barrier = validate_forward_barrier
    base.selected_ids = selected_ids
    base.fixed_partitions = fixed_partitions


def _group_metrics(summary: dict[str, Any], name: str) -> dict[str, Any]:
    group = summary["groups"][name]
    conservative = group["conservative_all_selected"]
    selected_rows = (
        [row for row in summary["per_task"] if row["split"] == "test"]
        if name == "test_156"
        else list(summary["per_task"])
    )
    return {
        "selected": group["selected"],
        "evaluator_valid": group["evaluator_valid"],
        "evaluator_invalid_or_not_run": group["evaluator_invalid_or_not_run"],
        "whole_table_successes": sum(
            row["evaluator_valid"] and row["metrics"]["score"] > 0
            for row in selected_rows
        ),
        "entity_acc": float(conservative["entity_acc"]),
        "f1_by_row": float(conservative["f1_by_row"]),
        "f1_by_item": float(conservative["f1_by_item"]),
        "column_f1": float(conservative["column_f1"]),
        "quality_composite": sum(
            float(conservative[key])
            for key in ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
        )
        / 4,
        "score": float(conservative["score"]),
    }


def _comparison(current: dict[str, Any], path: Path, label: str) -> dict[str, Any]:
    parent = read_object(path)
    metrics = parent["metrics"].get("all_220", parent["metrics"])
    return {
        "reference": label,
        "reference_result_sha256": sha256(path),
        "whole_table_success_delta": current["whole_table_successes"] - metrics["whole_table_successes"],
        "score_delta": current["score"] - metrics["score"],
        "quality_composite_delta": current["quality_composite"] - metrics["quality_composite"],
        "entity_acc_delta": current["entity_acc"] - metrics["entity_acc"],
        "f1_by_row_delta": current["f1_by_row"] - metrics["f1_by_row"],
        "f1_by_item_delta": current["f1_by_item"] - metrics["f1_by_item"],
        "column_f1_delta": current["column_f1"] - metrics["column_f1"],
    }


def validate_final_result(root: Path, protocol: dict[str, Any], value: dict[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    contract = validate_forward_contract(root)
    barrier = validate_forward_barrier(root, contract)
    summary = read_object(root / SUMMARY)
    merge = read_object(root / MERGE_ATTESTATION)
    expected_all = _group_metrics(summary, "all_220")
    expected_all.update(
        {
            "model_generated_tables": barrier["forward"]["model_generated_tables"],
            "fallback_tables": barrier["forward"]["fallback_tables"],
            "system_total_tokens": barrier["forward"]["system_total_tokens"],
        }
    )
    expected_metrics = {
        "test_156": _group_metrics(summary, "test_156"),
        "all_220": expected_all,
    }
    expected_comparisons = {
        "vs_v24267_best_exact220": _comparison(expected_all, root / V24267_RESULT, "V2.42.67"),
        "vs_v24287_low_cost_exact220": _comparison(expected_all, root / V24287_RESULT, "V2.42.87"),
        "vs_v24630_capacity_parent_exact220": _comparison(expected_all, root / V24630_RESULT, "V2.46.30"),
    }
    expected_partitions = [
        {"worker": index + 1, "start": start, "end": end}
        for index, (start, end) in enumerate(fixed_partitions())
    ]
    live = base.validate_live_evaluator_identity(root, protocol)
    provenance = value.get("provenance") or {}
    mechanism = value.get("mechanism") or {}
    if (
        value.get("role") != "v24635_exact220_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("status") != "exact220_single_rollout_complete"
        or value.get("selected") != SELECTED_COUNT
        or value.get("failure_as_zero") is not True
        or value.get("metrics") != expected_metrics
        or value.get("comparisons") != expected_comparisons
        or merge.get("workers") != EVALUATOR_WORKERS
        or merge.get("fixed_contiguous_partitions") != expected_partitions
        or merge.get("all_frozen_predictions_evaluated_exactly_once") is not True
        or merge.get("selective_retry_or_revaluation") is not False
        or len(merge.get("worker_reports") or []) != EVALUATOR_WORKERS
        or any(report.get("returncode") != 0 for report in merge["worker_reports"])
        or mechanism.get("surviving_backfilled_union_lead_count") != 0
        or mechanism.get("downstream_candidate_set_changed_by_backfill") is not False
        or value.get("claims", {}).get("sota") is not False
        or value.get("claims", {}).get("avg_at_4") is not False
        or value.get("claims", {}).get("new_or_disjoint_task_population") is not False
        or value.get("claims", {}).get(
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation"
        )
        is not True
        or value.get("authorization", {}).get("additional_rollout_or_avg4") is not False
        or provenance.get("protocol_sha256") != sha256(root / PROTOCOL)
        or provenance.get("forward_result_sha256") != sha256(root / FORWARD_RESULT)
        or provenance.get("forward_audit_sha256") != sha256(root / FORWARD_AUDIT)
        or provenance.get("prediction_freeze_sha256") != sha256(root / PREDICTION_FREEZE)
        or provenance.get("mapping_sha256") != sha256(root / MAPPING_PATH)
        or provenance.get("query_data_sha256") != live["query_data_sha256"]
        or provenance.get("answer_corpus_manifest_sha256") != live["answer_corpus_manifest_sha256"]
        or provenance.get("evaluator_source_manifest_sha256") != live["evaluator_source_manifest_sha256"]
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.46.35 final result drifted")


def finalize(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    _configure_base()
    protocol = validate_protocol(root, PROTOCOL)
    contract = validate_forward_contract(root)
    barrier = validate_forward_barrier(root, contract)
    if (root / FINAL_RESULT).exists() or (root / FINAL_RESULT).is_symlink():
        raise FileExistsError(root / FINAL_RESULT)
    live = base.validate_live_evaluator_identity(root, protocol)
    prepared = base.prepare_evaluator_inputs(root, protocol, barrier)
    with base.acquire_deepwide_api_lease(
        root, owner=EVALUATOR_OWNER, purpose=EVALUATOR_PURPOSE, path=root / LEASE_PATH
    ):
        eval_rows, parallel = base.run_parallel_evaluator(
            root, protocol, prepared["official"]
        )
    summary = summarize_rollout(prepared["joined"], eval_rows, rollout_id=1)
    base._new_json(root / SUMMARY, summary)
    metrics = {
        "test_156": _group_metrics(summary, "test_156"),
        "all_220": _group_metrics(summary, "all_220"),
    }
    metrics["all_220"].update(
        {
            "model_generated_tables": barrier["forward"]["model_generated_tables"],
            "fallback_tables": barrier["forward"]["fallback_tables"],
            "system_total_tokens": barrier["forward"]["system_total_tokens"],
        }
    )
    backfill = read_object(root / RUN_SUMMARY)["backfill_totals"]
    result = {
        "artifact_version": 1,
        "role": "v24635_exact220_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "exact220_single_rollout_complete",
        "selected": SELECTED_COUNT,
        "failure_as_zero": True,
        "exact220_prediction_freeze_before_evaluator": True,
        "metrics": metrics,
        "efficiency": {
            "forward_wall_seconds": barrier["forward"]["forward_wall_seconds"],
            "evaluator_parallel_wall_seconds": parallel["attestation"]["parallel_wall_seconds"],
            "evaluator_workers": EVALUATOR_WORKERS,
        },
        "mechanism": {
            "backfilled_action_source_count": backfill["backfilled_action_source_count"],
            "backfilled_unique_url_count": backfill["backfilled_unique_url_count"],
            "query_local_shadowed_backfilled_url_count": backfill["query_local_shadowed_backfilled_url_count"],
            "earlier_action_shadowed_backfilled_url_count": backfill["earlier_action_shadowed_backfilled_url_count"],
            "surviving_backfilled_union_lead_count": backfill["surviving_backfilled_union_lead_count"],
            "downstream_candidate_set_changed_by_backfill": backfill["surviving_backfilled_union_lead_count"] > 0,
        },
        "comparisons": {
            "vs_v24267_best_exact220": _comparison(metrics["all_220"], root / V24267_RESULT, "V2.42.67"),
            "vs_v24287_low_cost_exact220": _comparison(metrics["all_220"], root / V24287_RESULT, "V2.42.87"),
            "vs_v24630_capacity_parent_exact220": _comparison(metrics["all_220"], root / V24630_RESULT, "V2.46.30"),
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "forward_audit_sha256": sha256(root / FORWARD_AUDIT),
            "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
            "mapping_sha256": sha256(root / MAPPING_PATH),
            "query_data_sha256": live["query_data_sha256"],
            "answer_corpus_manifest_sha256": live["answer_corpus_manifest_sha256"],
            "evaluator_source_manifest_sha256": live["evaluator_source_manifest_sha256"],
            "judge": live["judge"],
            "recovery_policy": live["recovery_policy"],
            "merged_official_eval_results_sha256": sha256(root / MERGED_RESULTS),
            "parallel_merge_attestation_sha256": sha256(root / MERGE_ATTESTATION),
            "conservative_summary_sha256": sha256(root / SUMMARY),
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "mapping_opened_only_after_exact220_prediction_freeze": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "fixed_public_exact220_task_set_reexecuted": True,
            "new_or_disjoint_task_population_claimed": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        },
        "authorization": {
            "additional_rollout_or_avg4": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "claims": {
            "public_exact220_single_rollout": True,
            "cold_execution": True,
            "unseen_or_held_out": False,
            "new_or_disjoint_task_population": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
            "avg_at_4": False,
            "leaderboard_submitted": False,
            "sota": False,
        },
    }
    result["result_payload_sha256"] = payload_sha256(result)
    validate_final_result(root, protocol, result)
    publish_new(root / FINAL_RESULT, result)
    return result


if __name__ == "__main__":
    value = finalize()
    print(json.dumps({"result": str(FINAL_RESULT), "status": value["status"], "metrics": value["metrics"]["all_220"]}, sort_keys=True))
