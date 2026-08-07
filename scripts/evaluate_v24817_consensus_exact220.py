#!/usr/bin/env python3
"""Post-freeze fixed-partition official evaluator for V2.48.17."""

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

from deepwide_agent import v24817_consensus_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24287_exact220 as evaluator  # noqa: E402
from scripts.finalize_fullset_rollout import (  # noqa: E402
    _live_answer_corpus_manifest_sha256,
    _live_evaluator_source_manifest_sha256,
    prepare_rollout,
    read_jsonl,
    summarize_rollout,
)


EVALUATOR_PROTOCOL = Path(f"results/v24817_consensus_exact220_evaluator_preregistration_v1_{contract.DATE}.json")
FINAL_RESULT = Path(f"results/v24817_consensus_exact220_result_v1_{contract.DATE}.json")
POSTAUDIT = Path(f"results/v24817_consensus_exact220_postresult_audit_v1_{contract.DATE}.json")
EVALUATOR_ROOT = contract.OUTPUT_ROOT / "evaluator"
EVALUATOR_WORKERS = 32
MAPPING_PATH = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
SOURCE_MANIFEST = Path("outputs/runtime_manifest_v1_repro/manifest.jsonl")
QUERY_PATH = Path("external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch/data/overall_20250916.jsonl")
ANSWER_ROOT = Path("external/Marco-Search-Agent/Marco-DeepResearch-Family/DeepWideSearch/data/overall_20250916_tables")
PARENT_EVALUATOR_PROTOCOL = Path(f"results/v24810_exact220_evaluator_preregistration_v1_{contract.DATE}.json")
PREPARE_ATTESTATION = EVALUATOR_ROOT / "prepare_attestation.json"
JOINED_OUTCOMES = EVALUATOR_ROOT / "terminal_outcomes_evaluator_joined.jsonl"
OFFICIAL_PREDICTIONS = EVALUATOR_ROOT / "official_predictions.jsonl"
EVALUATOR_RUNS = EVALUATOR_ROOT / "official_eval_workers"
EVALUATOR_LOGS = EVALUATOR_ROOT / "logs"
MERGED_RESULTS = EVALUATOR_ROOT / "official_eval_results.jsonl"
MERGE_ATTESTATION = EVALUATOR_ROOT / "merge_attestation.json"
SUMMARY = EVALUATOR_ROOT / "conservative_summary.json"
EVALUATOR_OWNER = "v24817_consensus_exact220_evaluator_v1"
EVALUATOR_PURPOSE = "postfreeze_fixed_partition_consensus_exact220_official_evaluator"
RESULT_CLAIMS = {
    "public_exact220_posthoc_three_rollout_ensemble": True,
    "cold_execution": False,
    "unseen_or_held_out": False,
    "source_rollouts_previously_evaluated": True,
    "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
    "avg_at_4": False,
    "leaderboard_submitted": False,
    "sota": False,
}
RESULT_AUTHORIZATION = {
    "additional_rollout_or_revaluation": False,
    "leaderboard_submission": False,
    "sota_claim": False,
}


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"V2.48.17 evaluator expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise RuntimeError("V2.48.17 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value); seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20, check=True).stdout.strip()


def _publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def _lease_inactive() -> bool:
    try:
        with (ROOT / contract.LEASE_PATH).open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB); fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError): return False


def _barrier() -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT, _read(ROOT / contract.PROTOCOL)); audit = _read(ROOT / contract.FORWARD_AUDIT); forward = _read(ROOT / contract.FORWARD_RESULT); freeze = _read(ROOT / contract.PREDICTION_FREEZE); summary = _read(ROOT / contract.RUN_SUMMARY); rows = [json.loads(line) for line in (ROOT / contract.RUNTIME_PREDICTIONS).read_text(encoding="utf-8").splitlines() if line.strip()]; tasks = contract.task_vector(ROOT)
    if (audit.get("audit_valid") is not True or audit.get("findings") != [] or audit.get("authorization", {}).get("postfreeze_exact220_evaluator_protocol") is not True or not _sealed(audit, "audit_payload_sha256") or forward.get("terminal_predictions") != 220 or not _sealed(forward, "result_payload_sha256") or freeze.get("terminal") != 220 or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False or not _sealed(freeze, "freeze_payload_sha256") or summary.get("completed") != 220 or summary.get("failed") != 0 or not _sealed(summary, "summary_payload_sha256") or len(rows) != 220 or [row.get("opaque_id") for row in rows] != [task["opaque_id"] for task in tasks]): raise RuntimeError("V2.48.17 forward barrier drifted")
    return {"protocol": protocol, "forward": forward, "freeze": freeze, "summary": summary, "runtime_rows": rows, "tasks": tasks}


def _parent_evaluator_contract() -> dict[str, Any]:
    parent = _read(ROOT / PARENT_EVALUATOR_PROTOCOL); value = json.loads(json.dumps(parent["evaluator_contract"])); value.pop("opened_only_after_v24800_exact220_prediction_freeze", None); value["opened_only_after_v24817_consensus_prediction_freeze"] = True; return value


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    barrier = _barrier()
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"): raise RuntimeError("V2.48.17 evaluator protocol requires clean pushed HEAD")
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (EVALUATOR_PROTOCOL, FINAL_RESULT, POSTAUDIT, EVALUATOR_ROOT)): raise RuntimeError("V2.48.17 evaluator future surface not pristine")
    value = {"artifact_version": 1, "role": "v24817_consensus_exact220_evaluator_preregistration", "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now), "selected": 220, "evaluator_workers": 32, "forward_barrier": {"forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT), "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT), "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE), "runtime_predictions_sha256": contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS), "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY), "terminal_predictions": 220, "mapping_or_evaluator_opened_during_consensus": False, "source_evaluator_result_or_score_opened_or_hashed_during_consensus": False}, "evaluator_contract": _parent_evaluator_contract(), "evaluation_contract": {"all_220_predictions_frozen_before_mapping_query_answer_or_evaluator_open": True, "fixed_contiguous_32_way_partition_in_prediction_order": True, "official_evaluator_on_every_frozen_prediction_exactly_once": True, "worker_error_rows_are_terminal_failure_as_zero": True, "selective_retry_revaluation_or_prediction_selection": False, "conservative_denominators": {"test_156": 156, "all_220": 220}}, "outputs": {"evaluator_root": str(EVALUATOR_ROOT), "final_result": str(FINAL_RESULT), "postresult_audit": str(POSTAUDIT)}, "lease": {"path": str(contract.LEASE_PATH), "owner": EVALUATOR_OWNER, "purpose": EVALUATOR_PURPOSE, "nonblocking_single_owner": True}, "source_policy": {"mapping_opened_only_after_consensus_exact220_prediction_freeze_and_pushed_audit": True, "same_evaluation_feedback_used_for_consensus_or_prediction_selection": False, "posthoc_public_task_ensemble_not_unseen_or_heldout": True, "source_rollouts_previously_evaluated": True, "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True}, "authorization": {"postfreeze_exact220_evaluation": True, "selective_retry_or_revaluation": False, "additional_rollout_avg4_leaderboard_or_sota": False}}
    value["protocol_payload_sha256"] = contract.payload_sha256(value); return value


def validate_protocol(value: dict[str, Any]) -> dict[str, Any]:
    parent = _parent_evaluator_contract(); unsigned = dict(value); seal = unsigned.pop("protocol_payload_sha256", None)
    if (value.get("role") != "v24817_consensus_exact220_evaluator_preregistration" or value.get("protocol_id") != contract.PROTOCOL_ID or value.get("selected") != 220 or value.get("evaluator_workers") != 32 or value.get("forward_barrier", {}).get("forward_audit_sha256") != contract.sha256(ROOT / contract.FORWARD_AUDIT) or value.get("evaluator_contract") != parent or value.get("authorization") != {"postfreeze_exact220_evaluation": True, "selective_retry_or_revaluation": False, "additional_rollout_avg4_leaderboard_or_sota": False} or seal != contract.payload_sha256(unsigned)): raise RuntimeError("V2.48.17 evaluator protocol drifted")
    live = evaluator.validate_live_evaluator_identity(ROOT, value)
    if live["query_data_sha256"] != parent["query_data"]["sha256"]: raise RuntimeError("V2.48.17 live evaluator drifted")
    _barrier(); return value


def fixed_partitions() -> list[tuple[int, int]]:
    base, remainder = divmod(220, 32); output = []; start = 0
    for index in range(32):
        size = base + (1 if index < remainder else 0); output.append((start, start + size)); start += size
    if start != 220: raise RuntimeError("V2.48.17 partition drifted")
    return output


def _prepare(protocol: dict[str, Any], barrier: dict[str, Any]) -> dict[str, Any]:
    mapping_rows = read_jsonl(ROOT / MAPPING_PATH); manifest_rows = read_jsonl(ROOT / SOURCE_MANIFEST); task_ids = [task["opaque_id"] for task in barrier["tasks"]]
    joined, official, base = prepare_rollout(manifest_rows=manifest_rows, mapping_rows=mapping_rows, shards=[("all220", task_ids, barrier["runtime_rows"], barrier["summary"])], rollout_id=1)
    if len(joined) != 220 or len(official) != 220: raise RuntimeError("V2.48.17 prepare not exact220")
    (ROOT / EVALUATOR_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False); evaluator._write_jsonl_new(ROOT / JOINED_OUTCOMES, joined); evaluator._write_jsonl_new(ROOT / OFFICIAL_PREDICTIONS, official)
    attestation = {**base, "phase": "post_consensus_exact220_prediction_freeze_evaluator_prepare", "mapping_sha256": contract.sha256(ROOT / MAPPING_PATH), "manifest_sha256": contract.sha256(ROOT / SOURCE_MANIFEST), "runtime_predictions_sha256": contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS), "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE), "terminal_outcomes_sha256": contract.sha256(ROOT / JOINED_OUTCOMES), "official_predictions_sha256": contract.sha256(ROOT / OFFICIAL_PREDICTIONS), "both_consensus_forward_and_freeze_exact220_before_mapping_open": True}
    attestation["prepare_payload_sha256"] = contract.payload_sha256(attestation); evaluator._new_json(ROOT / PREPARE_ATTESTATION, attestation); return {"joined": joined, "official": official}


def _configure(protocol: dict[str, Any]) -> None:
    assignments = {"PROTOCOL": EVALUATOR_PROTOCOL, "FINAL_RESULT": FINAL_RESULT, "EVALUATOR_ROOT": EVALUATOR_ROOT, "EVALUATOR_WORKERS": 32, "MAPPING_PATH": MAPPING_PATH, "PREPARE_ATTESTATION": PREPARE_ATTESTATION, "JOINED_OUTCOMES": JOINED_OUTCOMES, "OFFICIAL_PREDICTIONS": OFFICIAL_PREDICTIONS, "EVALUATOR_RUNS": EVALUATOR_RUNS, "EVALUATOR_LOGS": EVALUATOR_LOGS, "MERGED_RESULTS": MERGED_RESULTS, "MERGE_ATTESTATION": MERGE_ATTESTATION, "SUMMARY": SUMMARY, "EVALUATOR_OWNER": EVALUATOR_OWNER, "EVALUATOR_PURPOSE": EVALUATOR_PURPOSE, "FORWARD_RESULT": contract.FORWARD_RESULT, "OUTPUT_ROOT": contract.OUTPUT_ROOT, "PREDICTION_FREEZE": contract.PREDICTION_FREEZE, "RUNTIME_PREDICTIONS": contract.RUNTIME_PREDICTIONS, "RUN_SUMMARY": contract.RUN_SUMMARY, "SOURCE_MANIFEST": SOURCE_MANIFEST, "SELECTED_COUNT": 220, "PROTOCOL_ID": contract.PROTOCOL_ID, "LEASE_PATH": contract.LEASE_PATH}
    for name, val in assignments.items(): setattr(evaluator, name, val)
    evaluator.fixed_partitions = lambda selected=220, workers=32: fixed_partitions()
    evaluator.validate_protocol = lambda _root, _path=EVALUATOR_PROTOCOL: protocol


def _group_metrics(summary: dict[str, Any], name: str) -> dict[str, Any]:
    rows = [row for row in summary["per_task"] if row["split"] == "test"] if name == "test_156" else list(summary["per_task"]); group = summary["groups"][name]; conservative = group["conservative_all_selected"]
    return {"selected": group["selected"], "evaluator_valid": group["evaluator_valid"], "evaluator_invalid_or_not_run": group["evaluator_invalid_or_not_run"], "whole_table_successes": sum(row["evaluator_valid"] and row["metrics"]["score"] > 0 for row in rows), "entity_acc": float(conservative["entity_acc"]), "f1_by_row": float(conservative["f1_by_row"]), "f1_by_item": float(conservative["f1_by_item"]), "column_f1": float(conservative["column_f1"]), "quality_composite": sum(float(conservative[key]) for key in ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")) / 4, "score": float(conservative["score"])}


def evaluate() -> dict[str, Any]:
    protocol = validate_protocol(_read(ROOT / EVALUATOR_PROTOCOL)); barrier = _barrier()
    if (ROOT / EVALUATOR_ROOT).exists() or (ROOT / FINAL_RESULT).exists(): raise RuntimeError("V2.48.17 evaluator surface exists")
    _configure(protocol); live = evaluator.validate_live_evaluator_identity(ROOT, protocol); prepared = _prepare(protocol, barrier)
    with evaluator.acquire_deepwide_api_lease(ROOT, owner=EVALUATOR_OWNER, purpose=EVALUATOR_PURPOSE, path=ROOT / contract.LEASE_PATH): eval_rows, parallel = evaluator.run_parallel_evaluator(ROOT, protocol, prepared["official"])
    summary = summarize_rollout(prepared["joined"], eval_rows, rollout_id=1); evaluator._new_json(ROOT / SUMMARY, summary); metrics = {"test_156": _group_metrics(summary, "test_156"), "all_220": _group_metrics(summary, "all_220")}; metrics["all_220"].update({"source_rollouts": 3, "source_predictions": 660, "incremental_model_search_or_fetch_effects": 0})
    result = {"artifact_version": 1, "role": "v24817_consensus_exact220_result", "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()), "status": "posthoc_consensus_exact220_complete", "selected": 220, "failure_as_zero": True, "exact220_prediction_freeze_before_evaluator": True, "metrics": metrics, "efficiency": {"consensus_postprocess_wall_seconds": barrier["forward"]["postprocess_wall_seconds"], "evaluator_parallel_wall_seconds": parallel["attestation"]["parallel_wall_seconds"], "evaluator_workers": 32}, "provenance": {"evaluator_protocol_sha256": contract.sha256(ROOT / EVALUATOR_PROTOCOL), "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT), "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT), "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE), "mapping_sha256": contract.sha256(ROOT / MAPPING_PATH), "query_data_sha256": live["query_data_sha256"], "answer_corpus_manifest_sha256": live["answer_corpus_manifest_sha256"], "evaluator_source_manifest_sha256": live["evaluator_source_manifest_sha256"], "judge": live["judge"], "recovery_policy": live["recovery_policy"], "merged_official_eval_results_sha256": contract.sha256(ROOT / MERGED_RESULTS), "parallel_merge_attestation_sha256": contract.sha256(ROOT / MERGE_ATTESTATION), "conservative_summary_sha256": contract.sha256(ROOT / SUMMARY)}, "source_policy": {"runtime_boundary": ["opaque_id", "question", "three_frozen_predictions"], "mapping_opened_only_after_exact220_prediction_freeze_and_pushed_audit": True, "same_evaluation_feedback_used_for_consensus_or_prediction_selection": False, "source_rollouts_previously_evaluated": True, "posthoc_public_task_ensemble_not_unseen_or_heldout": True, "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True}, "authorization": dict(RESULT_AUTHORIZATION), "claims": dict(RESULT_CLAIMS)}
    result["result_payload_sha256"] = contract.payload_sha256(result); _publish(ROOT / FINAL_RESULT, result); return result


def postaudit(*, now: int | None = None) -> dict[str, Any]:
    result = _read(ROOT / FINAL_RESULT); unsigned = dict(result); seal = unsigned.pop("result_payload_sha256", None); summary = _read(ROOT / SUMMARY); merged = read_jsonl(ROOT / MERGED_RESULTS); checks = {"result_sealed": seal == contract.payload_sha256(unsigned), "exact220_metrics": result.get("selected") == 220 and result.get("metrics", {}).get("all_220", {}).get("selected") == 220, "evaluator_rows_exact220": len(merged) == 220 and len(summary.get("per_task") or []) == 220, "failure_as_zero": result.get("failure_as_zero") is True, "claims_are_posthoc_not_sota": result.get("claims") == RESULT_CLAIMS, "no_selective_revaluation": result.get("authorization") == RESULT_AUTHORIZATION, "shared_lease_released": _lease_inactive(), "protected_watchers_stable": contract.protected_watcher_snapshot() == _barrier()["protocol"]["protected_watchers"]}
    value = {"artifact_version": 1, "role": "v24817_consensus_exact220_postresult_audit", "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now), "result_sha256": contract.sha256(ROOT / FINAL_RESULT), "evaluator_protocol_sha256": contract.sha256(ROOT / EVALUATOR_PROTOCOL), "merged_results_sha256": contract.sha256(ROOT / MERGED_RESULTS), "summary_sha256": contract.sha256(ROOT / SUMMARY), "checks": checks, "findings": sorted(name for name, okay in checks.items() if not okay), "audit_valid": all(checks.values()), "authorization": dict(RESULT_AUTHORIZATION)}; value["audit_payload_sha256"] = contract.payload_sha256(value)
    if value["findings"]: raise RuntimeError(f"V2.48.17 postaudit failed: {value['findings']}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("protocol", "evaluate", "postaudit")); args = parser.parse_args()
    if args.command in {"protocol", "postaudit"} and (_git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")): raise RuntimeError("V2.48.17 evaluator control requires clean pushed HEAD")
    if args.command == "protocol": value = build_protocol(); _publish(ROOT / EVALUATOR_PROTOCOL, value); output = {"path": str(EVALUATOR_PROTOCOL), "authorization": value["authorization"]}
    elif args.command == "evaluate": value = evaluate(); output = {"path": str(FINAL_RESULT), "status": value["status"], "metrics": value["metrics"]["all_220"]}
    else: value = postaudit(); _publish(ROOT / POSTAUDIT, value); output = {"path": str(POSTAUDIT), "audit_valid": value["audit_valid"]}
    print(json.dumps(output, sort_keys=True))


if __name__ == "__main__": main()
