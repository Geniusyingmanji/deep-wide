#!/usr/bin/env python3
"""Official exact-220 evaluation of the frozen V2.48.96 collector recovery."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24895_control_binding_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24791_exact220 as base  # noqa: E402
from scripts import finalize_v24287_exact220 as evaluator  # noqa: E402
from scripts.finalize_fullset_rollout import (  # noqa: E402
    _live_answer_corpus_manifest_sha256,
    _live_evaluator_source_manifest_sha256,
    summarize_rollout,
)
from scripts import recover_v24896_collector_exact220 as recovery  # noqa: E402


DATE = "20260808"
EVALUATOR_PROTOCOL = Path(f"results/v24896_collector_recovery_exact220_evaluator_preregistration_v1_{DATE}.json")
FINAL_RESULT = Path(f"results/v24896_collector_recovery_exact220_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24896_collector_recovery_exact220_postresult_audit_v1_{DATE}.json")
EVALUATOR_ROOT = recovery.OUTPUT_ROOT / "evaluator"
PREPARE_ATTESTATION = EVALUATOR_ROOT / "prepare_attestation.json"
JOINED_OUTCOMES = EVALUATOR_ROOT / "terminal_outcomes_evaluator_joined.jsonl"
OFFICIAL_PREDICTIONS = EVALUATOR_ROOT / "official_predictions.jsonl"
EVALUATOR_RUNS = EVALUATOR_ROOT / "official_eval_workers"
EVALUATOR_LOGS = EVALUATOR_ROOT / "logs"
MERGED_RESULTS = EVALUATOR_ROOT / "official_eval_results.jsonl"
MERGE_ATTESTATION = EVALUATOR_ROOT / "merge_attestation.json"
SUMMARY = EVALUATOR_ROOT / "conservative_summary.json"
MAPPING_PATH = base.MAPPING_PATH
QUERY_PATH = base.QUERY_PATH
ANSWER_ROOT = base.ANSWER_ROOT
SOURCE_MANIFEST = base.SOURCE_MANIFEST
EVALUATOR_WORKERS = 32
OWNER = "v24896_collector_recovery_exact220_evaluator_v1"
PURPOSE = "posthoc_infrastructure_correction_exact220_official_evaluator"
ROLE = "v24896_collector_recovery_exact220"
CONTROLS = (
    "scripts/finalize_v24896_collector_recovery_exact220.py",
    "scripts/recover_v24896_collector_exact220.py",
    "scripts/finalize_v24791_exact220.py",
    "scripts/finalize_v24287_exact220.py",
    "scripts/run_official_eval_local.py",
    "scripts/finalize_fullset_rollout.py",
    "scripts/deepwide_api_lease.py",
    "tests/test_recover_v24896_collector_exact220.py",
)


def _read(path: Path) -> dict[str, Any]:
    return recovery._read(ROOT / path if not path.is_absolute() else path)


def _rows(path: Path) -> list[dict[str, Any]]:
    return recovery._rows(ROOT / path if not path.is_absolute() else path)


def _sealed(value: dict[str, Any], field: str) -> bool:
    return recovery._sealed(value, field)


def _git(*args: str) -> str:
    return recovery._git(*args)


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _barrier() -> dict[str, Any]:
    protocol = recovery.validate_protocol(_read(recovery.PROTOCOL))
    preaudit = _read(recovery.AUDIT)
    forward = _read(recovery.FORWARD_RESULT)
    audit = _read(recovery.FORWARD_AUDIT)
    summary = _read(recovery.RUN_SUMMARY)
    freeze = _read(recovery.PREDICTION_FREEZE)
    rows = _rows(recovery.RUNTIME_PREDICTIONS)
    tasks = contract.task_vector(ROOT)
    if (
        preaudit.get("audit_valid") is not True
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or forward.get("terminal_predictions") != 220
        or forward.get("model_generated_tables") != 163
        or forward.get("fallback_tables") != 57
        or not _sealed(forward, "result_payload_sha256")
        or not _sealed(summary, "summary_payload_sha256")
        or not _sealed(freeze, "freeze_payload_sha256")
        or len(rows) != 220
        or [row.get("opaque_id") for row in rows] != [task["opaque_id"] for task in tasks]
        or freeze.get("runtime_predictions_sha256") != contract.sha256(ROOT / recovery.RUNTIME_PREDICTIONS)
        or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
    ):
        raise RuntimeError("V2.48.96 recovered barrier drifted")
    return {"protocol": protocol, "forward": forward, "audit": audit, "summary": summary, "freeze": freeze, "runtime_rows": rows}


def _parent_evaluator_contract() -> dict[str, Any]:
    value = json.loads(
        (ROOT / "results/v24895_control_binding_exact220_evaluator_preregistration_v1_20260808.json").read_text(encoding="utf-8")
    )["evaluator_contract"]
    return json.loads(json.dumps(value))


def build_protocol() -> dict[str, Any]:
    barrier = _barrier()
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.48.96 evaluator protocol requires clean pushed HEAD")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (EVALUATOR_PROTOCOL, FINAL_RESULT, POSTAUDIT, EVALUATOR_ROOT)):
        raise FileExistsError("V2.48.96 evaluator future surface exists")
    controls = {path: contract.sha256(ROOT / path) for path in CONTROLS}
    evaluator_contract = _parent_evaluator_contract()
    evaluator_contract["mapping"] = {"path": str(MAPPING_PATH), "sha256": contract.sha256(ROOT / MAPPING_PATH)}
    evaluator_contract["query_data"] = {"path": str(QUERY_PATH), "sha256": contract.sha256(ROOT / QUERY_PATH)}
    evaluator_contract["answer_corpus"] = {"root": str(ANSWER_ROOT), "manifest_sha256": _live_answer_corpus_manifest_sha256(ROOT / ANSWER_ROOT)}
    evaluator_contract["evaluator_source"] = {"manifest_sha256": _live_evaluator_source_manifest_sha256()}
    evaluator_contract["opened_only_after_v24896_collector_recovery_prediction_freeze"] = True
    value = {
        "artifact_version": 1,
        "role": f"{ROLE}_evaluator_preregistration",
        "created_at_unix": int(time.time()),
        "selected": 220,
        "evaluator_workers": 32,
        "forward_barrier": {
            "source_v24895_forward_result_sha256": contract.sha256(ROOT / recovery.SOURCE_FORWARD),
            "recovered_forward_result_sha256": contract.sha256(ROOT / recovery.FORWARD_RESULT),
            "recovered_forward_audit_sha256": contract.sha256(ROOT / recovery.FORWARD_AUDIT),
            "prediction_freeze_sha256": contract.sha256(ROOT / recovery.PREDICTION_FREEZE),
            "runtime_predictions_sha256": contract.sha256(ROOT / recovery.RUNTIME_PREDICTIONS),
            "terminal_predictions": 220,
            "mapping_or_evaluator_opened_during_original_forward": False,
            "collector_rule_created_after_first_evaluation": True,
            "collector_used_correctness_score_or_evaluator_rows": False,
        },
        "evaluator_contract": evaluator_contract,
        "evaluation_contract": {
            "fixed_contiguous_32_way_partition_in_prediction_order": True,
            "official_evaluator_on_every_recovered_prediction_exactly_once": True,
            "worker_error_rows_are_terminal_failure_as_zero": True,
            "selective_retry_revaluation_or_prediction_selection": False,
            "conservative_denominators": {"test_156": 156, "all_220": 220},
        },
        "outputs": {"evaluator_root": str(EVALUATOR_ROOT), "final_result": str(FINAL_RESULT), "postresult_audit": str(POSTAUDIT)},
        "lease": {"path": str(contract.LEASE_PATH), "owner": OWNER, "purpose": PURPOSE},
        "control_manifest": controls,
        "control_manifest_sha256": contract.payload_sha256(controls),
        "source_policy": {
            "posthoc_infrastructure_correction": True,
            "cold_execution_claimed": False,
            "sota_leaderboard_or_avg4_claimed": False,
            "collector_read_mapping_gold_score_correctness_or_evaluator_rows": False,
            "same_fixed_rule_applied_to_all_220_positions": True,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        },
        "authorization": {"postfreeze_exact220_evaluation": True, "selective_retry_or_revaluation": False, "additional_rollout_avg4_leaderboard_or_sota": False},
    }
    value["protocol_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_protocol(value: dict[str, Any]) -> dict[str, Any]:
    controls = value.get("control_manifest") or {}
    if (
        value.get("role") != f"{ROLE}_evaluator_preregistration"
        or value.get("selected") != 220
        or value.get("evaluator_workers") != 32
        or value.get("forward_barrier", {}).get("recovered_forward_result_sha256") != contract.sha256(ROOT / recovery.FORWARD_RESULT)
        or value.get("forward_barrier", {}).get("collector_used_correctness_score_or_evaluator_rows") is not False
        or value.get("evaluator_contract", {}).get("mapping", {}).get("sha256") != contract.sha256(ROOT / MAPPING_PATH)
        or value.get("control_manifest_sha256") != contract.payload_sha256(controls)
        or any(contract.sha256(ROOT / path) != digest for path, digest in controls.items())
        or value.get("authorization") != {"postfreeze_exact220_evaluation": True, "selective_retry_or_revaluation": False, "additional_rollout_avg4_leaderboard_or_sota": False}
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.48.96 evaluator protocol drifted")
    _barrier()
    return value


def fixed_partitions() -> list[tuple[int, int]]:
    base_size, remainder = divmod(220, 32)
    output = []
    start = 0
    for index in range(32):
        size = base_size + int(index < remainder)
        output.append((start, start + size)); start += size
    return output


def selected_ids(_value: dict[str, Any]) -> list[str]:
    return [task["opaque_id"] for task in contract.task_vector(ROOT)]


def _algorithm_contract() -> dict[str, Any]:
    return {"task_contract": {"manifest_sha256": contract.sha256(ROOT / SOURCE_MANIFEST)}}


def configure_evaluator() -> None:
    assignments = {
        "PROTOCOL": EVALUATOR_PROTOCOL, "FINAL_RESULT": FINAL_RESULT,
        "EVALUATOR_ROOT": EVALUATOR_ROOT, "EVALUATOR_WORKERS": 32,
        "MAPPING_PATH": MAPPING_PATH, "PREPARE_ATTESTATION": PREPARE_ATTESTATION,
        "JOINED_OUTCOMES": JOINED_OUTCOMES, "OFFICIAL_PREDICTIONS": OFFICIAL_PREDICTIONS,
        "EVALUATOR_RUNS": EVALUATOR_RUNS, "EVALUATOR_LOGS": EVALUATOR_LOGS,
        "MERGED_RESULTS": MERGED_RESULTS, "MERGE_ATTESTATION": MERGE_ATTESTATION,
        "SUMMARY": SUMMARY, "EVALUATOR_OWNER": OWNER, "EVALUATOR_PURPOSE": PURPOSE,
        "FORWARD_CONTRACT": recovery.PROTOCOL, "FORWARD_RESULT": recovery.FORWARD_RESULT,
        "OUTPUT_ROOT": recovery.OUTPUT_ROOT, "PREDICTION_FREEZE": recovery.PREDICTION_FREEZE,
        "RUNTIME_PREDICTIONS": recovery.RUNTIME_PREDICTIONS, "RUN_SUMMARY": recovery.RUN_SUMMARY,
        "SOURCE_MANIFEST": SOURCE_MANIFEST, "SELECTED_COUNT": 220,
        "PROTOCOL_ID": contract.PROTOCOL_ID, "LEASE_PATH": contract.LEASE_PATH,
    }
    for name, value in assignments.items():
        setattr(evaluator, name, value)
    evaluator.validate_protocol = lambda _root, _path=EVALUATOR_PROTOCOL: validate_protocol(_read(_path))
    evaluator.validate_forward_contract = lambda _root: _algorithm_contract()
    evaluator.validate_forward_barrier = lambda _root, _contract: _barrier()
    evaluator.selected_ids = selected_ids
    evaluator.fixed_partitions = fixed_partitions


def _group(summary: dict[str, Any], name: str) -> dict[str, Any]:
    rows = summary["per_task"] if name == "all_220" else [row for row in summary["per_task"] if row["split"] == "test"]
    group = summary["groups"][name]
    metrics = group["conservative_all_selected"]
    return {
        "selected": group["selected"],
        "evaluator_valid": group["evaluator_valid"],
        "evaluator_invalid_or_not_run": group["evaluator_invalid_or_not_run"],
        "whole_table_successes": sum(row["evaluator_valid"] and row["metrics"]["score"] > 0 for row in rows),
        "entity_acc": float(metrics["entity_acc"]),
        "f1_by_row": float(metrics["f1_by_row"]),
        "f1_by_item": float(metrics["f1_by_item"]),
        "column_f1": float(metrics["column_f1"]),
        "quality_composite": sum(float(metrics[key]) for key in ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")) / 4,
        "score": float(metrics["score"]),
    }


def evaluate() -> dict[str, Any]:
    protocol = validate_protocol(_read(EVALUATOR_PROTOCOL))
    barrier = _barrier()
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (FINAL_RESULT, EVALUATOR_ROOT)):
        raise FileExistsError("V2.48.96 evaluator surface exists")
    configure_evaluator()
    live = evaluator.validate_live_evaluator_identity(ROOT, protocol)
    prepared = evaluator.prepare_evaluator_inputs(ROOT, protocol, barrier)
    with evaluator.acquire_deepwide_api_lease(ROOT, owner=OWNER, purpose=PURPOSE, path=ROOT / contract.LEASE_PATH):
        eval_rows, parallel = evaluator.run_parallel_evaluator(ROOT, protocol, prepared["official"])
    summary = summarize_rollout(prepared["joined"], eval_rows, rollout_id=1)
    evaluator._new_json(ROOT / SUMMARY, summary)
    metrics = {"test_156": _group(summary, "test_156"), "all_220": _group(summary, "all_220")}
    metrics["all_220"].update({
        "model_generated_tables": barrier["forward"]["model_generated_tables"],
        "fallback_tables": barrier["forward"]["fallback_tables"],
        "system_total_tokens": barrier["forward"]["system_total_tokens"],
    })
    result = {
        "artifact_version": 1,
        "role": f"{ROLE}_result",
        "created_at_unix": int(time.time()),
        "status": "exact220_posthoc_infrastructure_correction_complete",
        "selected": 220,
        "failure_as_zero": True,
        "metrics": metrics,
        "efficiency": {
            "original_forward_wall_seconds": barrier["forward"]["source_forward_wall_seconds"],
            "collector_wall_effect_seconds": 0.0,
            "evaluator_parallel_wall_seconds": parallel["attestation"]["parallel_wall_seconds"],
            "evaluator_workers": 32,
        },
        "provenance": {
            "evaluator_protocol_sha256": contract.sha256(ROOT / EVALUATOR_PROTOCOL),
            "source_v24895_forward_result_sha256": contract.sha256(ROOT / recovery.SOURCE_FORWARD),
            "recovered_forward_result_sha256": contract.sha256(ROOT / recovery.FORWARD_RESULT),
            "prediction_freeze_sha256": contract.sha256(ROOT / recovery.PREDICTION_FREEZE),
            "mapping_sha256": contract.sha256(ROOT / MAPPING_PATH),
            "query_data_sha256": live["query_data_sha256"],
            "answer_corpus_manifest_sha256": live["answer_corpus_manifest_sha256"],
            "evaluator_source_manifest_sha256": live["evaluator_source_manifest_sha256"],
            "judge": live["judge"],
            "recovery_policy": live["recovery_policy"],
            "merged_official_eval_results_sha256": contract.sha256(ROOT / MERGED_RESULTS),
            "parallel_merge_attestation_sha256": contract.sha256(ROOT / MERGE_ATTESTATION),
            "conservative_summary_sha256": contract.sha256(ROOT / SUMMARY),
        },
        "claims": {
            "public_exact220_single_original_rollout": True,
            "posthoc_infrastructure_correction": True,
            "cold_execution": False,
            "unseen_or_held_out": False,
            "avg_at_4": False,
            "leaderboard_submitted": False,
            "sota": False,
        },
        "authorization": {"additional_rollout_or_avg4": False, "selective_retry_or_revaluation": False, "leaderboard_submission": False, "sota_claim": False},
    }
    result["result_payload_sha256"] = contract.payload_sha256(result)
    recovery._write_json(ROOT / FINAL_RESULT, result)
    return result


def build_postaudit() -> dict[str, Any]:
    protocol = validate_protocol(_read(EVALUATOR_PROTOCOL))
    result = _read(FINAL_RESULT)
    summary = _read(SUMMARY)
    merged = _rows(MERGED_RESULTS)
    checks = {
        "protocol_sealed": _sealed(protocol, "protocol_payload_sha256"),
        "result_sealed": _sealed(result, "result_payload_sha256"),
        "exact220_merged_rows": len(merged) == 220,
        "exact220_summary_rows": len(summary.get("per_task") or []) == 220,
        "conservative_denominator_220": summary["groups"]["all_220"]["conservative_all_selected"]["denominator"] == 220,
        "posthoc_correction_disclosed": result["claims"]["posthoc_infrastructure_correction"] is True,
        "cold_sota_leaderboard_forbidden": result["claims"]["cold_execution"] is False and result["claims"]["sota"] is False and result["claims"]["leaderboard_submitted"] is False,
        "no_selective_retry_or_revaluation": result["authorization"]["selective_retry_or_revaluation"] is False,
        "lease_released": _lease_inactive(),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot() == contract.validate_protocol(ROOT, _read(contract.PROTOCOL))["execution"]["protected_watchers"],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": f"{ROLE}_postresult_audit",
        "created_at_unix": int(time.time()),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "result_sha256": contract.sha256(ROOT / FINAL_RESULT),
        "metrics": result["metrics"],
        "claims": result["claims"],
        "authorization": result["authorization"],
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "evaluate", "postaudit"))
    command = parser.parse_args().command
    if command == "protocol":
        value = build_protocol(); validate_protocol(value); recovery._write_json(ROOT / EVALUATOR_PROTOCOL, value)
        output = {"path": str(EVALUATOR_PROTOCOL), "authorization": value["authorization"]}
    elif command == "evaluate":
        value = evaluate(); output = {"path": str(FINAL_RESULT), "status": value["status"], "metrics": value["metrics"]["all_220"]}
    else:
        value = build_postaudit(); recovery._write_json(ROOT / POSTAUDIT, value)
        output = {"path": str(POSTAUDIT), "audit_valid": value["audit_valid"], "findings": value["findings"]}
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__":
    main()
