#!/usr/bin/env python3
"""Read-only post-result audit for the frozen V2.46.30 exact-220 run."""

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

from deepwide_agent.v24630_exact220_contract import (  # noqa: E402
    ACTIVATION,
    CHILD_MARKER,
    EXECUTION_START,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    PREAUDIT,
    PROTOCOL_ID,
    RUNNER_MARKER,
    SELECTED_COUNT,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    sha256,
    validate_forward_contract,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.finalize_v24630_exact220 import (  # noqa: E402
    EVALUATOR_RUNS,
    EVALUATOR_LOGS,
    JOINED_OUTCOMES,
    MERGED_RESULTS,
    MERGE_ATTESTATION,
    OFFICIAL_PREDICTIONS,
    PREPARE_ATTESTATION,
    SUMMARY,
    _configure_base,
    fixed_partitions,
    validate_final_result,
    validate_forward_barrier,
)
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    _matching,
)
from scripts.preregister_v24630_exact220 import publish_new  # noqa: E402
from scripts.preregister_v24630_exact220_evaluator import (  # noqa: E402
    EVALUATOR_WORKERS,
    FINAL_RESULT,
    POSTAUDIT,
    PROTOCOL,
    validate_protocol,
)
from scripts.run_v24630_exact220 import (  # noqa: E402
    validate_activation,
    validate_execution_start,
    validate_preaudit,
)


FINALIZER_MARKER = "scripts/finalize_v24630_exact220.py"
EVALUATOR_MARKER = "scripts/run_official_eval_local.py"
QUALITY_METRICS = (
    "score",
    "entity_acc",
    "precision_by_row",
    "recall_by_row",
    "f1_by_row",
    "precision_by_item",
    "recall_by_item",
    "f1_by_item",
    "column_precision",
    "column_recall",
    "column_f1",
)


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.46.30 expected ordinary JSONL: {path}")
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError(f"V2.46.30 expected JSON objects: {path}")
    return rows


def _fixed_partition_checks(root: Path, merge: dict[str, Any]) -> dict[str, Any]:
    joined = _read_jsonl(root / JOINED_OUTCOMES)
    official = _read_jsonl(root / OFFICIAL_PREDICTIONS)
    merged = _read_jsonl(root / MERGED_RESULTS)
    expected_partitions = [
        {"worker": index + 1, "start": start, "end": end}
        for index, (start, end) in enumerate(fixed_partitions())
    ]
    reports = merge.get("worker_reports") or []
    joined_ids = [str(row.get("instance_id")) for row in joined]
    official_ids = [str(row.get("instance_id")) for row in official]
    merged_ids = [str(row.get("instance_id")) for row in merged]
    worker_row_count = 0
    worker_ids: list[str] = []
    worker_summaries = 0
    worker_summaries_terminal = 0
    worker_summary_errors = 0
    worker_report_artifact_hashes_bound = True
    for partition in expected_partitions:
        worker = partition["worker"]
        start = partition["start"]
        end = partition["end"]
        shard_path = root / EVALUATOR_RUNS / f"worker_{worker:02d}_predictions.jsonl"
        run_root = root / EVALUATOR_RUNS / f"worker_{worker:02d}"
        result_path = run_root / "official_eval_results.jsonl"
        config_path = run_root / "run_config.json"
        log_path = root / EVALUATOR_LOGS / f"worker_{worker:02d}.log"
        shard = _read_jsonl(shard_path)
        results = _read_jsonl(result_path)
        shard_ids = [str(row.get("instance_id")) for row in shard]
        result_ids = [str(row.get("instance_id")) for row in results]
        if shard_ids != official_ids[start:end] or result_ids != shard_ids:
            raise RuntimeError(f"V2.46.30 evaluator worker {worker} partition drifted")
        summary = read_object(run_root / "summary.json")
        if (
            summary.get("n") != len(shard_ids)
            or summary.get("valid_n", 0) + summary.get("errors", 0) != len(shard_ids)
        ):
            raise RuntimeError(f"V2.46.30 evaluator worker {worker} summary drifted")
        worker_row_count += len(results)
        worker_ids.extend(result_ids)
        worker_summaries += 1
        worker_summaries_terminal += (
            summary.get("complete") is True
            or int(summary.get("errors", 0)) > 0
        )
        worker_summary_errors += int(summary["errors"])
        report = reports[worker - 1] if len(reports) >= worker else {}
        worker_report_artifact_hashes_bound = worker_report_artifact_hashes_bound and (
            report.get("worker") == worker
            and report.get("start") == start
            and report.get("end") == end
            and report.get("selected") == len(shard)
            and report.get("prediction_shard_sha256") == sha256(shard_path)
            and report.get("results_sha256") == sha256(result_path)
            and report.get("run_config_sha256") == sha256(config_path)
            and report.get("log_sha256") == sha256(log_path)
        )
    return {
        "workers": len(expected_partitions),
        "worker_reports": len(reports),
        "worker_summaries": worker_summaries,
        "worker_summaries_terminal": worker_summaries_terminal,
        "worker_rows": worker_row_count,
        "worker_summary_errors": worker_summary_errors,
        "official_rows": len(official),
        "merged_rows": len(merged),
        "unique_official_instance_ids": len(set(official_ids)),
        "unique_merged_instance_ids": len(set(merged_ids)),
        "fixed_partitions_exact": merge.get("fixed_contiguous_partitions")
        == expected_partitions,
        "worker_returncodes_zero": len(reports) == EVALUATOR_WORKERS
        and all(report.get("returncode") == 0 for report in reports),
        "worker_report_artifact_hashes_bound": worker_report_artifact_hashes_bound,
        "joined_official_shards_merge_in_frozen_order": joined_ids
        == official_ids
        == worker_ids
        == merged_ids,
    }


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    _configure_base()
    contract = validate_forward_contract(root)
    preaudit = validate_preaudit(root, contract)
    validate_activation(root, contract)
    execution = validate_execution_start(root, contract)
    protocol = validate_protocol(root, PROTOCOL)
    barrier = validate_forward_barrier(root, contract)
    result = read_object(root / FINAL_RESULT)
    validate_final_result(root, protocol, result)

    prepare = read_object(root / PREPARE_ATTESTATION)
    merge = read_object(root / MERGE_ATTESTATION)
    summary = read_object(root / SUMMARY)
    joined = _read_jsonl(root / JOINED_OUTCOMES)
    partition = _fixed_partition_checks(root, merge)
    per_task = summary.get("per_task") or []
    invalid = [row for row in per_task if row.get("evaluator_valid") is not True]
    error_rows_are_zero = all(
        all(float((row.get("metrics") or {}).get(metric, 1.0)) == 0.0 for metric in QUALITY_METRICS)
        for row in invalid
    )
    all_group = (summary.get("groups") or {}).get("all_220") or {}
    test_group = (summary.get("groups") or {}).get("test_156") or {}
    all_conservative = all_group.get("conservative_all_selected") or {}
    test_conservative = test_group.get("conservative_all_selected") or {}

    processes = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    runner_pids = _matching(processes, RUNNER_MARKER)
    child_pids = _matching(processes, CHILD_MARKER)
    finalizer_pids = _matching(processes, FINALIZER_MARKER)
    evaluator_pids = _matching(processes, EVALUATOR_MARKER)
    watcher_snapshot = protected_watcher_snapshot()

    checks = {
        "preactivation_audit_valid": preaudit.get("audit_valid") is True
        and preaudit.get("findings") == [],
        "execution_was_fresh_and_authorized": execution.get("resume_retry_skip_or_rerun")
        is False,
        "forward_barrier_exact220": barrier["forward"].get("terminal_predictions")
        == SELECTED_COUNT,
        "forward_mapping_and_evaluator_closed": barrier["freeze"].get(
            "mapping_gold_or_evaluator_opened_or_hashed"
        )
        is False,
        "prepare_attestation_sealed": _sealed(prepare, "prepare_payload_sha256"),
        "prepare_artifact_hashes_bound": prepare.get("terminal_outcomes_sha256")
        == sha256(root / JOINED_OUTCOMES)
        and prepare.get("official_predictions_sha256")
        == sha256(root / OFFICIAL_PREDICTIONS)
        and prepare.get("both_forward_and_freeze_exact220_before_mapping_open")
        is True,
        "merge_attestation_sealed": _sealed(merge, "merge_payload_sha256"),
        "merge_artifact_hash_bound": merge.get("merged_results_sha256")
        == sha256(root / MERGED_RESULTS),
        "joined_rows_exact220": len(joined) == SELECTED_COUNT,
        "official_rows_exact220": partition["official_rows"] == SELECTED_COUNT,
        "merged_rows_exact220": partition["merged_rows"] == SELECTED_COUNT,
        "unique_instance_ids_exact220": partition["unique_official_instance_ids"]
        == SELECTED_COUNT
        and partition["unique_merged_instance_ids"] == SELECTED_COUNT,
        "fixed_contiguous_partitions_exact": partition["fixed_partitions_exact"],
        "all_shards_merged_in_frozen_order": partition[
            "joined_official_shards_merge_in_frozen_order"
        ],
        "worker_reports_and_summaries_exact32": partition["worker_reports"]
        == EVALUATOR_WORKERS
        and partition["worker_summaries"] == EVALUATOR_WORKERS
        and partition["worker_summaries_terminal"] == EVALUATOR_WORKERS,
        "all_worker_returncodes_zero": partition["worker_returncodes_zero"],
        "worker_report_artifact_hashes_bound": partition[
            "worker_report_artifact_hashes_bound"
        ],
        "all_frozen_predictions_evaluated_exactly_once": merge.get(
            "all_frozen_predictions_evaluated_exactly_once"
        )
        is True,
        "no_selective_retry_or_revaluation": merge.get(
            "selective_retry_or_revaluation"
        )
        is False
        and result.get("authorization", {}).get("selective_retry_or_revaluation")
        is False,
        "all220_conservative_denominator": all_group.get("selected")
        == SELECTED_COUNT
        and all_conservative.get("denominator") == SELECTED_COUNT,
        "test156_conservative_denominator": test_group.get("selected") == 156
        and test_conservative.get("denominator") == 156,
        "evaluator_error_count_consistent": len(invalid)
        == all_group.get("evaluator_invalid_or_not_run")
        == partition["worker_summary_errors"],
        "evaluator_errors_are_terminal_zero": error_rows_are_zero,
        "final_result_sealed": _sealed(result, "result_payload_sha256"),
        "result_forbids_sota_avg4_or_leaderboard_claim": result.get("claims", {}).get(
            "sota"
        )
        is False
        and result.get("claims", {}).get("avg_at_4") is False
        and result.get("claims", {}).get("leaderboard_submitted") is False,
        "forward_runner_absent_after_result": not runner_pids,
        "forward_child_absent_after_result": not child_pids,
        "evaluator_finalizer_absent_after_result": not finalizer_pids,
        "evaluator_workers_absent_after_result": not evaluator_pids,
        "shared_api_lease_released": lease.get("active") is False,
        "protected_watchers_unchanged": watcher_snapshot
        == contract["execution"]["protected_watchers"],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    metrics = result["metrics"]["all_220"]
    value = {
        "artifact_version": 1,
        "role": "v24630_exact220_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "provenance": {
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "evaluator_protocol_sha256": sha256(root / PROTOCOL),
            "prepare_attestation_sha256": sha256(root / PREPARE_ATTESTATION),
            "merge_attestation_sha256": sha256(root / MERGE_ATTESTATION),
            "merged_results_sha256": sha256(root / MERGED_RESULTS),
            "conservative_summary_sha256": sha256(root / SUMMARY),
            "final_result_sha256": sha256(root / FINAL_RESULT),
        },
        "checks": checks,
        "forward": {
            "selected": barrier["forward"]["selected"],
            "terminal_predictions": barrier["forward"]["terminal_predictions"],
            "model_generated_tables": barrier["forward"]["model_generated_tables"],
            "fallback_tables": barrier["forward"]["fallback_tables"],
            "system_total_tokens": barrier["forward"]["system_total_tokens"],
            "forward_wall_seconds": barrier["forward"]["forward_wall_seconds"],
        },
        "evaluation": {
            **partition,
            "evaluator_valid": all_group["evaluator_valid"],
            "evaluator_errors_terminal_zero": len(invalid),
            "parallel_wall_seconds": merge["parallel_wall_seconds"],
            "conservative_denominator": all_conservative["denominator"],
        },
        "result": {
            "whole_table_successes": metrics["whole_table_successes"],
            "score": metrics["score"],
            "entity_acc": metrics["entity_acc"],
            "f1_by_row": metrics["f1_by_row"],
            "f1_by_item": metrics["f1_by_item"],
            "column_f1": metrics["column_f1"],
            "quality_composite": metrics["quality_composite"],
            "comparisons": result["comparisons"],
            "claims": result["claims"],
        },
        "execution_closure": {
            "forward_runner_pids": runner_pids,
            "forward_child_pids": child_pids,
            "evaluator_finalizer_pids": finalizer_pids,
            "evaluator_worker_pids": evaluator_pids,
            "shared_api_lease_active": lease.get("active") is True,
            "protected_watchers": watcher_snapshot,
            "protected_watchers_signaled_restarted_or_stopped": False,
            "active_run_killed_or_quarantined": False,
            "invalid_result_path": None,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "mapping_opened_only_after_exact220_prediction_freeze": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "audit_is_read_only_except_new_postresult_artifact": True,
            "credential_value_output_persisted_or_hashed_by_audit": False,
        },
        "authorization": {
            "additional_rollout_or_avg4": False,
            "selective_retry_or_revaluation": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "findings": findings,
        "audit_valid": not findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    report = build_report()
    dry_run = "--dry-run" in sys.argv
    if not dry_run:
        publish_new(ROOT / POSTAUDIT, report)
    print(
        json.dumps(
            {
                "path": None if dry_run else str(POSTAUDIT),
                "audit_valid": report["audit_valid"],
                "findings": report["findings"],
            },
            sort_keys=True,
        )
    )
