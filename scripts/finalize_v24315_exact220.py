#!/usr/bin/env python3
"""Post-freeze parallel official evaluation and conservative V2.43.15 result."""

from __future__ import annotations

import concurrent.futures
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24315_forward_contract import (  # noqa: E402
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
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.finalize_fullset_rollout import (  # noqa: E402
    _live_answer_corpus_manifest_sha256,
    _live_evaluator_source_manifest_sha256,
    prepare_rollout,
    read_jsonl,
    summarize_rollout,
    validate_evaluator_contract,
)
from scripts.preregister_v24315_exact220 import (  # noqa: E402
    EVALUATOR_ROOT,
    EVALUATOR_WORKERS,
    FINAL_RESULT,
    PROTOCOL,
    validate_protocol,
)
from scripts.run_official_eval_local import validate_committed_eval_rows  # noqa: E402
from scripts.run_v24315_exact220 import (  # noqa: E402
    validate_forward_result,
    validate_prediction_freeze,
)


MAPPING_PATH = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
PREPARE_ATTESTATION = EVALUATOR_ROOT / "prepare_attestation.json"
JOINED_OUTCOMES = EVALUATOR_ROOT / "terminal_outcomes_evaluator_joined.jsonl"
OFFICIAL_PREDICTIONS = EVALUATOR_ROOT / "official_predictions.jsonl"
EVALUATOR_RUNS = EVALUATOR_ROOT / "official_eval_workers"
EVALUATOR_LOGS = EVALUATOR_ROOT / "logs"
MERGED_RESULTS = EVALUATOR_ROOT / "official_eval_results.jsonl"
MERGE_ATTESTATION = EVALUATOR_ROOT / "merge_attestation.json"
SUMMARY = EVALUATOR_ROOT / "conservative_summary.json"
EVALUATOR_OWNER = "v24315_exact220_evaluator_v1"
EVALUATOR_PURPOSE = "post_freeze_fixed_partition_parallel_exact220_official_evaluator"


def _new_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_jsonl_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def validate_forward_barrier(root: Path, contract: dict[str, Any]) -> dict[str, Any]:
    forward = read_object(root / FORWARD_RESULT)
    validate_forward_result(root, contract, forward)
    freeze = read_object(root / PREDICTION_FREEZE)
    rows = validate_prediction_freeze(root, contract, freeze)
    return {"forward": forward, "freeze": freeze, "runtime_rows": rows}


def validate_live_evaluator_identity(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    evaluator = protocol["evaluator_contract"]
    query = evaluator["query_data"]
    answers = evaluator["answer_corpus"]
    source = evaluator["evaluator_source"]
    query_path = root / query["path"]
    answer_root = root / answers["root"]
    if (
        query_path.is_symlink()
        or not query_path.is_file()
        or sha256(query_path) != query["sha256"]
        or answer_root.is_symlink()
        or not answer_root.is_dir()
        or _live_answer_corpus_manifest_sha256(answer_root) != answers["manifest_sha256"]
        or _live_evaluator_source_manifest_sha256() != source["manifest_sha256"]
    ):
        raise RuntimeError("V2.43.15 live evaluator identity drifted")
    return {
        "query_data_sha256": query["sha256"],
        "answer_corpus_manifest_sha256": answers["manifest_sha256"],
        "evaluator_source_manifest_sha256": source["manifest_sha256"],
        "judge": dict(evaluator["judge"]),
        "recovery_policy": dict(evaluator["recovery_policy"]),
    }


def prepare_evaluator_inputs(
    root: Path, protocol: dict[str, Any], barrier: dict[str, Any]
) -> dict[str, Any]:
    mapping = root / MAPPING_PATH
    manifest = root / SOURCE_MANIFEST
    evaluator = protocol["evaluator_contract"]
    if (
        mapping.is_symlink()
        or not mapping.is_file()
        or sha256(mapping) != evaluator["mapping"]["sha256"]
        or manifest.is_symlink()
        or not manifest.is_file()
        or sha256(manifest) != validate_forward_contract(root)["task_contract"]["manifest_sha256"]
    ):
        raise RuntimeError("V2.43.15 post-freeze evaluator join identity drifted")
    contract = validate_forward_contract(root)
    joined, official, base = prepare_rollout(
        manifest_rows=read_jsonl(manifest),
        mapping_rows=read_jsonl(mapping),
        shards=[("all220", selected_ids(contract), barrier["runtime_rows"], read_object(root / RUN_SUMMARY))],
        rollout_id=1,
    )
    if len(joined) != SELECTED_COUNT or len(official) != SELECTED_COUNT:
        raise RuntimeError("V2.43.15 evaluator prepare is not exact-220")
    (root / EVALUATOR_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
    _write_jsonl_new(root / JOINED_OUTCOMES, joined)
    _write_jsonl_new(root / OFFICIAL_PREDICTIONS, official)
    attestation = {
        **base,
        "phase": "post_exact220_prediction_freeze_evaluator_prepare",
        "mapping_sha256": sha256(mapping),
        "manifest_sha256": sha256(manifest),
        "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS),
        "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "terminal_outcomes_sha256": sha256(root / JOINED_OUTCOMES),
        "official_predictions_sha256": sha256(root / OFFICIAL_PREDICTIONS),
        "both_forward_and_freeze_exact220_before_mapping_open": True,
    }
    attestation["prepare_payload_sha256"] = payload_sha256(attestation)
    _new_json(root / PREPARE_ATTESTATION, attestation)
    return {"joined": joined, "official": official, "attestation": attestation}


def fixed_partitions(selected: int = SELECTED_COUNT, workers: int = EVALUATOR_WORKERS) -> list[tuple[int, int]]:
    if selected != 220 or workers != 8:
        raise ValueError("V2.43.15 evaluator partition identity drifted")
    base, remainder = divmod(selected, workers)
    output: list[tuple[int, int]] = []
    start = 0
    for index in range(workers):
        size = base + (1 if index < remainder else 0)
        output.append((start, start + size))
        start += size
    if start != selected:
        raise AssertionError("V2.43.15 evaluator partition does not cover 220")
    return output


def evaluator_command(
    root: Path,
    protocol: dict[str, Any],
    *,
    worker: int,
    prediction_path: Path,
) -> list[str]:
    evaluator = protocol["evaluator_contract"]
    judge = evaluator["judge"]
    command = [
        str(root / ".venv-eval/bin/python"), "-I", "-B",
        str(root / "scripts/run_official_eval_local.py"),
        "--predictions", str(prediction_path),
        "--out-dir", str(root / EVALUATOR_RUNS / f"worker_{worker:02d}"),
        "--query-path", str(root / evaluator["query_data"]["path"]),
        "--answer-root", str(root / evaluator["answer_corpus"]["root"]),
        "--proxy-url", judge["proxy_url"],
        "--model", judge["model"],
        "--reasoning-effort", judge["reasoning_effort"],
        "--judge-max-output-tokens", str(judge["max_output_tokens"]),
        "--judge-timeout", str(judge["timeout_seconds"]),
        "--judge-max-retries", str(judge["max_retries"]),
    ]
    return command


def _run_worker(
    worker: int,
    command: list[str],
    root: Path,
    runner: Callable[..., subprocess.CompletedProcess[Any]],
) -> dict[str, Any]:
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"})
    log = root / EVALUATOR_LOGS / f"worker_{worker:02d}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log.open("xb") as handle:
        completed = runner(command, cwd=root, env=environment, stdout=handle, stderr=subprocess.STDOUT, check=False)
        handle.flush()
        os.fsync(handle.fileno())
    return {"worker": worker, "returncode": completed.returncode, "wall_seconds": round(max(0.0, time.monotonic() - started), 6), "log_sha256": sha256(log)}


def run_parallel_evaluator(
    root: Path,
    protocol: dict[str, Any],
    official: list[dict[str, Any]],
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    partitions = fixed_partitions()
    (root / EVALUATOR_RUNS).mkdir(mode=0o700, parents=True, exist_ok=False)
    commands: list[tuple[int, list[str], list[str], Path]] = []
    for worker, (start, end) in enumerate(partitions, start=1):
        ids = [str(row["instance_id"]) for row in official[start:end]]
        shard_path = root / EVALUATOR_RUNS / f"worker_{worker:02d}_predictions.jsonl"
        _write_jsonl_new(shard_path, official[start:end])
        commands.append(
            (
                worker,
                evaluator_command(root, protocol, worker=worker, prediction_path=shard_path),
                ids,
                shard_path,
            )
        )
    started = time.monotonic()
    reports: dict[int, dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=EVALUATOR_WORKERS, thread_name_prefix="v24315-eval") as executor:
        futures = {executor.submit(_run_worker, worker, command, root, command_runner): worker for worker, command, _, _ in commands}
        for future in concurrent.futures.as_completed(futures):
            report = future.result()
            reports[int(report["worker"])] = report
    wall = max(0.0, time.monotonic() - started)
    merged: list[dict[str, Any]] = []
    worker_rows: list[dict[str, Any]] = []
    run_contracts: list[dict[str, Any]] = []
    for worker, _, ids, shard_path in commands:
        report = reports[worker]
        if report["returncode"] != 0:
            raise RuntimeError(f"V2.43.15 evaluator worker {worker} failed")
        run_root = root / EVALUATOR_RUNS / f"worker_{worker:02d}"
        rows = read_jsonl(run_root / "official_eval_results.jsonl")
        validate_committed_eval_rows(rows, ids)
        if len(rows) != len(ids):
            raise RuntimeError(f"V2.43.15 evaluator worker {worker} is incomplete")
        run_contracts.append(
            validate_evaluator_contract(
                run_root / "run_config.json",
                expected_predictions_path=shard_path,
                expected_predictions_sha256=sha256(shard_path),
                expected_selected_count=len(ids),
            )
        )
        merged.extend(rows)
        worker_rows.append({**report, "start": partitions[worker - 1][0], "end": partitions[worker - 1][1], "selected": len(ids), "prediction_shard_sha256": sha256(shard_path), "results_sha256": sha256(run_root / "official_eval_results.jsonl"), "run_config_sha256": sha256(run_root / "run_config.json")})
    expected_ids = [str(row["instance_id"]) for row in official]
    validate_committed_eval_rows(merged, expected_ids)
    if len(merged) != SELECTED_COUNT:
        raise RuntimeError("V2.43.15 merged evaluator is not exact-220")
    evaluator = protocol["evaluator_contract"]
    for item in run_contracts:
        if (
            item.get("query_data_sha256") != evaluator["query_data"]["sha256"]
            or item.get("answer_corpus_manifest_sha256") != evaluator["answer_corpus"]["manifest_sha256"]
            or item.get("evaluator_source_manifest_sha256") != evaluator["evaluator_source"]["manifest_sha256"]
            or item.get("judge") != evaluator["judge"]
            or item.get("recovery_policy") != evaluator["recovery_policy"]
        ):
            raise RuntimeError("V2.43.15 evaluator worker provenance drifted")
    _write_jsonl_new(root / MERGED_RESULTS, merged)
    attestation = {
        "artifact_version": 1,
        "role": "v24315_parallel_evaluator_merge_attestation",
        "selected": SELECTED_COUNT,
        "workers": EVALUATOR_WORKERS,
        "fixed_contiguous_partitions": [{"worker": index + 1, "start": start, "end": end} for index, (start, end) in enumerate(partitions)],
        "worker_reports": worker_rows,
        "parallel_wall_seconds": round(wall, 6),
        "merged_results_sha256": sha256(root / MERGED_RESULTS),
        "all_frozen_predictions_evaluated_exactly_once": True,
        "selective_retry_or_revaluation": False,
    }
    attestation["merge_payload_sha256"] = payload_sha256(attestation)
    _new_json(root / MERGE_ATTESTATION, attestation)
    return merged, {"attestation": attestation, "contracts": run_contracts}


def _group_metrics(summary: dict[str, Any], name: str) -> dict[str, Any]:
    group = summary["groups"][name]
    conservative = group["conservative_all_selected"]
    if name == "test_156":
        selected_rows = [row for row in summary["per_task"] if row["split"] == "test"]
    elif name == "all_220":
        selected_rows = list(summary["per_task"])
    else:
        raise ValueError("V2.43.15 unsupported result group")
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
        "quality_composite": sum(float(conservative[key]) for key in ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")) / 4,
        "score": float(conservative["score"]),
    }


def validate_final_result(root: Path, protocol: dict[str, Any], value: dict[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    expected_keys = {
        "artifact_version", "role", "protocol_id", "created_at_unix", "status",
        "selected", "failure_as_zero", "exact220_prediction_freeze_before_evaluator",
        "metrics", "efficiency", "provenance", "source_policy", "authorization",
        "claims", "result_payload_sha256",
    }
    contract = validate_forward_contract(root)
    validate_forward_barrier(root, contract)
    if (
        set(value) != expected_keys
        or value.get("artifact_version") != 1
        or value.get("role") != "v24315_exact220_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("status") != "exact220_single_rollout_complete"
        or value.get("selected") != SELECTED_COUNT
        or value.get("failure_as_zero") is not True
        or value.get("exact220_prediction_freeze_before_evaluator") is not True
        or value.get("claims")
        != {"public_exact220_single_rollout": True, "cold_execution": True, "unseen_or_held_out": False, "avg_at_4": False, "leaderboard_submitted": False, "sota": False}
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.15 final result identity drifted")
    summary = read_object(root / SUMMARY)
    expected = {"test_156": _group_metrics(summary, "test_156"), "all_220": _group_metrics(summary, "all_220")}
    forward = read_object(root / FORWARD_RESULT)
    expected["all_220"].update({"model_generated_tables": forward["model_generated_tables"], "fallback_tables": forward["fallback_tables"], "system_total_tokens": forward["system_total_tokens"]})
    if value.get("metrics") != expected:
        raise RuntimeError("V2.43.15 final metrics are not bound to conservative summary")
    merge = read_object(root / MERGE_ATTESTATION)
    merge_unsigned = dict(merge)
    merge_seal = merge_unsigned.pop("merge_payload_sha256", None)
    provenance = value.get("provenance") or {}
    efficiency = value.get("efficiency") or {}
    live = validate_live_evaluator_identity(root, protocol)
    worker_reports = merge.get("worker_reports") or []
    partitions = merge.get("fixed_contiguous_partitions") or []
    expected_partitions = [
        {"worker": index + 1, "start": start, "end": end}
        for index, (start, end) in enumerate(fixed_partitions())
    ]
    if (
        merge.get("selected") != SELECTED_COUNT
        or merge.get("workers") != EVALUATOR_WORKERS
        or partitions != expected_partitions
        or not isinstance(worker_reports, list)
        or len(worker_reports) != EVALUATOR_WORKERS
        or [report.get("worker") for report in worker_reports] != list(range(1, EVALUATOR_WORKERS + 1))
        or any(
            report.get("returncode") != 0
            or report.get("start") != expected_partitions[index]["start"]
            or report.get("end") != expected_partitions[index]["end"]
            or report.get("selected") != expected_partitions[index]["end"] - expected_partitions[index]["start"]
            for index, report in enumerate(worker_reports)
        )
        or merge.get("all_frozen_predictions_evaluated_exactly_once") is not True
        or merge.get("selective_retry_or_revaluation") is not False
        or merge.get("merged_results_sha256") != sha256(root / MERGED_RESULTS)
        or merge_seal != payload_sha256(merge_unsigned)
        or efficiency
        != {
            "forward_wall_seconds": forward["forward_wall_seconds"],
            "evaluator_parallel_wall_seconds": merge["parallel_wall_seconds"],
            "evaluator_workers": EVALUATOR_WORKERS,
        }
        or provenance.get("protocol_sha256") != sha256(root / PROTOCOL)
        or provenance.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or provenance.get("forward_result_sha256") != sha256(root / FORWARD_RESULT)
        or provenance.get("prediction_freeze_sha256") != sha256(root / PREDICTION_FREEZE)
        or provenance.get("mapping_sha256") != sha256(root / MAPPING_PATH)
        or provenance.get("query_data_sha256") != live["query_data_sha256"]
        or provenance.get("answer_corpus_manifest_sha256") != live["answer_corpus_manifest_sha256"]
        or provenance.get("evaluator_source_manifest_sha256") != live["evaluator_source_manifest_sha256"]
        or provenance.get("judge") != live["judge"]
        or provenance.get("recovery_policy") != live["recovery_policy"]
        or provenance.get("merged_official_eval_results_sha256") != sha256(root / MERGED_RESULTS)
        or provenance.get("parallel_merge_attestation_sha256") != sha256(root / MERGE_ATTESTATION)
        or provenance.get("conservative_summary_sha256") != sha256(root / SUMMARY)
        or value.get("source_policy")
        != {"runtime_boundary": ["opaque_id", "question"], "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False, "mapping_opened_only_after_exact220_prediction_freeze": True, "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False}
        or value.get("authorization")
        != {"additional_rollout_or_avg4": False, "leaderboard_submission": False, "sota_claim": False}
    ):
        raise RuntimeError("V2.43.15 final provenance or evaluator merge drifted")


def finalize(
    root: Path = ROOT,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, PROTOCOL)
    contract = validate_forward_contract(root)
    if (root / FINAL_RESULT).exists() or (root / FINAL_RESULT).is_symlink():
        raise FileExistsError(root / FINAL_RESULT)
    barrier = validate_forward_barrier(root, contract)
    with acquire_deepwide_api_lease(root, owner=EVALUATOR_OWNER, purpose=EVALUATOR_PURPOSE, path=root / LEASE_PATH):
        live = validate_live_evaluator_identity(root, protocol)
        prepared = prepare_evaluator_inputs(root, protocol, barrier)
        eval_rows, parallel = run_parallel_evaluator(root, protocol, prepared["official"], command_runner=command_runner)
    summary = summarize_rollout(prepared["joined"], eval_rows, rollout_id=1)
    _new_json(root / SUMMARY, summary)
    metrics = {"test_156": _group_metrics(summary, "test_156"), "all_220": _group_metrics(summary, "all_220")}
    metrics["all_220"].update({"model_generated_tables": barrier["forward"]["model_generated_tables"], "fallback_tables": barrier["forward"]["fallback_tables"], "system_total_tokens": barrier["forward"]["system_total_tokens"]})
    result = {
        "artifact_version": 1,
        "role": "v24315_exact220_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "exact220_single_rollout_complete",
        "selected": SELECTED_COUNT,
        "failure_as_zero": True,
        "exact220_prediction_freeze_before_evaluator": True,
        "metrics": metrics,
        "efficiency": {"forward_wall_seconds": barrier["forward"]["forward_wall_seconds"], "evaluator_parallel_wall_seconds": parallel["attestation"]["parallel_wall_seconds"], "evaluator_workers": EVALUATOR_WORKERS},
        "provenance": {"protocol_sha256": sha256(root / PROTOCOL), "forward_contract_sha256": sha256(root / FORWARD_CONTRACT), "forward_result_sha256": sha256(root / FORWARD_RESULT), "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE), "mapping_sha256": sha256(root / MAPPING_PATH), "query_data_sha256": live["query_data_sha256"], "answer_corpus_manifest_sha256": live["answer_corpus_manifest_sha256"], "evaluator_source_manifest_sha256": live["evaluator_source_manifest_sha256"], "judge": live["judge"], "recovery_policy": live["recovery_policy"], "merged_official_eval_results_sha256": sha256(root / MERGED_RESULTS), "parallel_merge_attestation_sha256": sha256(root / MERGE_ATTESTATION), "conservative_summary_sha256": sha256(root / SUMMARY)},
        "source_policy": {"runtime_boundary": ["opaque_id", "question"], "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False, "mapping_opened_only_after_exact220_prediction_freeze": True, "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False},
        "authorization": {"additional_rollout_or_avg4": False, "leaderboard_submission": False, "sota_claim": False},
        "claims": {"public_exact220_single_rollout": True, "cold_execution": True, "unseen_or_held_out": False, "avg_at_4": False, "leaderboard_submitted": False, "sota": False},
    }
    result["result_payload_sha256"] = payload_sha256(result)
    validate_final_result(root, protocol, result)
    _new_json(root / FINAL_RESULT, result)
    return result


if __name__ == "__main__":
    value = finalize()
    print(json.dumps({"result": str(FINAL_RESULT), "status": value["status"]}, sort_keys=True))
