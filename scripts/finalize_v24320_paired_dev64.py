#!/usr/bin/env python3
"""Post-freeze full-both-arm evaluation for the V2.43.20 paired-dev64 gate."""

from __future__ import annotations

import concurrent.futures
import json
import math
import os
import random
import statistics
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    ARMS,
    EVALUATOR_ROOT,
    FINAL_RESULT,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    FULL_PROTOCOL,
    LEASE_PATH,
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
from scripts.preregister_v24320_paired_dev64 import (  # noqa: E402
    EVALUATOR_WORKERS_PER_ARM,
    MAPPING_PATH,
    TOTAL_EVALUATOR_WORKERS,
    validate_protocol,
)
from scripts.run_official_eval_local import validate_committed_eval_rows  # noqa: E402
from scripts.run_v24320_paired_dev64 import (  # noqa: E402
    validate_forward_result,
    validate_prediction_freeze,
)


ARM_ROOTS = {arm: EVALUATOR_ROOT / arm for arm in ARMS}
JOINED = {arm: ARM_ROOTS[arm] / "terminal_outcomes_evaluator_joined.jsonl" for arm in ARMS}
OFFICIAL = {arm: ARM_ROOTS[arm] / "official_predictions.jsonl" for arm in ARMS}
PREPARE = {arm: ARM_ROOTS[arm] / "prepare_attestation.json" for arm in ARMS}
RUNS = {arm: ARM_ROOTS[arm] / "official_eval_workers" for arm in ARMS}
LOGS = {arm: ARM_ROOTS[arm] / "logs" for arm in ARMS}
MERGED = {arm: ARM_ROOTS[arm] / "official_eval_results.jsonl" for arm in ARMS}
MERGE = {arm: ARM_ROOTS[arm] / "merge_attestation.json" for arm in ARMS}
SUMMARY = {arm: ARM_ROOTS[arm] / "conservative_summary.json" for arm in ARMS}
QUALITY = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")


def _new_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
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


def validate_candidate_barrier(root: Path) -> dict[str, Any]:
    contract = validate_forward_contract(root)
    forward = read_object(root / FORWARD_RESULT)
    validate_forward_result(root, contract, forward)
    arms: dict[str, Any] = {}
    for arm in ARMS:
        freeze = read_object(root / PREDICTION_FREEZE[arm])
        rows = validate_prediction_freeze(root, contract, arm, freeze)
        summary = read_object(root / RUN_SUMMARY[arm])
        if (
            len(rows) != SELECTED_COUNT
            or freeze.get("arm_terminal_before_mapping_gold_or_evaluator_open") is not True
            or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        ):
            raise RuntimeError(f"V2.43.20 {arm} freeze barrier is incomplete")
        arms[arm] = {
            "rows": rows,
            "summary": summary,
            "sources": {
                "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
                "forward_result_sha256": sha256(root / FORWARD_RESULT),
                "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE[arm]),
                "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS[arm]),
                "run_summary_sha256": sha256(root / RUN_SUMMARY[arm]),
            },
        }
    if forward.get("both_arms_exact64_before_mapping_gold_or_evaluator_open") is not True:
        raise RuntimeError("V2.43.20 both-arm freeze barrier is incomplete")
    return {
        "contract": contract,
        "forward": forward,
        "ids": selected_ids(contract),
        "arms": arms,
    }


def validate_live_evaluator_identity(root: Path, protocol: Mapping[str, Any]) -> dict[str, Any]:
    evaluator = protocol["evaluator_contract"]
    query = evaluator["query_data"]
    answers = evaluator["answer_corpus"]
    source = evaluator["evaluator_source"]
    mapping = root / evaluator["mapping"]["path"]
    query_path = root / query["path"]
    answer_root = root / answers["root"]
    if (
        mapping.is_symlink() or not mapping.is_file() or sha256(mapping) != evaluator["mapping"]["sha256"]
        or query_path.is_symlink() or not query_path.is_file() or sha256(query_path) != query["sha256"]
        or answer_root.is_symlink() or not answer_root.is_dir()
        or _live_answer_corpus_manifest_sha256(answer_root) != answers["manifest_sha256"]
        or _live_evaluator_source_manifest_sha256() != source["manifest_sha256"]
    ):
        raise RuntimeError("V2.43.20 live evaluator identity drifted")
    return {
        "mapping_sha256": evaluator["mapping"]["sha256"],
        "query_data_sha256": query["sha256"],
        "answer_corpus_manifest_sha256": answers["manifest_sha256"],
        "evaluator_source_manifest_sha256": source["manifest_sha256"],
        "judge": dict(evaluator["judge"]),
        "recovery_policy": dict(evaluator["recovery_policy"]),
    }


def prepare_arm(
    root: Path,
    protocol: Mapping[str, Any],
    barrier: Mapping[str, Any],
    arm: str,
) -> dict[str, Any]:
    arm_state = barrier["arms"][arm]
    rows = arm_state["rows"]
    summary = arm_state["summary"]
    source_hashes = arm_state["sources"]
    joined, official, base = prepare_rollout(
        manifest_rows=read_jsonl(root / SOURCE_MANIFEST),
        mapping_rows=read_jsonl(root / MAPPING_PATH),
        shards=[("devval", barrier["ids"], rows, summary)],
        rollout_id=1,
    )
    if len(joined) != SELECTED_COUNT or len(official) != SELECTED_COUNT:
        raise RuntimeError(f"V2.43.20 {arm} evaluator prepare is not full64")
    (root / ARM_ROOTS[arm]).mkdir(mode=0o700, parents=True, exist_ok=False)
    _write_jsonl_new(root / JOINED[arm], joined)
    _write_jsonl_new(root / OFFICIAL[arm], official)
    attestation = {
        **base,
        "phase": "post_both_arm_exact64_freeze_fresh_full_arm_evaluator_prepare",
        "arm": arm,
        "protocol_sha256": sha256(root / FULL_PROTOCOL),
        "both_arm_prediction_freeze_sha256": {
            name: sha256(root / PREDICTION_FREEZE[name]) for name in ARMS
        },
        "both_arms_exact64_before_mapping_gold_or_evaluator_open": True,
        "selective_changed_prediction_evaluation": False,
        "old_evaluator_rows_reused": False,
        "mapping_sha256": sha256(root / MAPPING_PATH),
        "manifest_sha256": sha256(root / SOURCE_MANIFEST),
        "source_hashes": source_hashes,
        "terminal_outcomes_sha256": sha256(root / JOINED[arm]),
        "official_predictions_sha256": sha256(root / OFFICIAL[arm]),
    }
    attestation["prepare_payload_sha256"] = payload_sha256(attestation)
    _new_json(root / PREPARE[arm], attestation)
    return {"joined": joined, "official": official, "attestation": attestation}


def _arm_forward_inputs(
    root: Path,
    barrier: Mapping[str, Any],
    arm: str,
) -> tuple[list[dict[str, Any]], Mapping[str, Any], dict[str, str]]:
    if arm not in ARMS:
        raise RuntimeError(f"V2.43.20 unknown evaluator arm: {arm}")
    state = barrier["arms"][arm]
    return list(state["rows"]), state["summary"], dict(state["sources"])


def validate_prepared_arm(
    root: Path,
    protocol: Mapping[str, Any],
    barrier: Mapping[str, Any],
    arm: str,
) -> dict[str, Any]:
    """Rebuild one evaluator join from frozen sources and validate it byte-for-byte."""

    rows, summary, source_hashes = _arm_forward_inputs(root, barrier, arm)
    expected_joined, expected_official, base = prepare_rollout(
        manifest_rows=read_jsonl(root / SOURCE_MANIFEST),
        mapping_rows=read_jsonl(root / MAPPING_PATH),
        shards=[("devval", list(barrier["ids"]), rows, dict(summary))],
        rollout_id=1,
    )
    joined = read_jsonl(root / JOINED[arm])
    official = read_jsonl(root / OFFICIAL[arm])
    if (
        len(joined) != SELECTED_COUNT
        or len(official) != SELECTED_COUNT
        or joined != expected_joined
        or official != expected_official
    ):
        raise RuntimeError(f"V2.43.20 {arm} prepared evaluator rows drifted")
    expected = {
        **base,
        "phase": "post_both_arm_exact64_freeze_fresh_full_arm_evaluator_prepare",
        "arm": arm,
        "protocol_sha256": sha256(root / FULL_PROTOCOL),
        "both_arm_prediction_freeze_sha256": {
            name: sha256(root / PREDICTION_FREEZE[name]) for name in ARMS
        },
        "both_arms_exact64_before_mapping_gold_or_evaluator_open": True,
        "selective_changed_prediction_evaluation": False,
        "old_evaluator_rows_reused": False,
        "mapping_sha256": sha256(root / MAPPING_PATH),
        "manifest_sha256": sha256(root / SOURCE_MANIFEST),
        "source_hashes": source_hashes,
        "terminal_outcomes_sha256": sha256(root / JOINED[arm]),
        "official_predictions_sha256": sha256(root / OFFICIAL[arm]),
    }
    attestation = read_object(root / PREPARE[arm])
    unsigned = dict(attestation)
    seal = unsigned.pop("prepare_payload_sha256", None)
    if unsigned != expected or seal != payload_sha256(unsigned):
        raise RuntimeError(f"V2.43.20 {arm} prepare attestation drifted")
    return {"joined": joined, "official": official, "attestation": attestation}


def fixed_partitions() -> list[tuple[int, int]]:
    if SELECTED_COUNT != 64 or EVALUATOR_WORKERS_PER_ARM != 4:
        raise ValueError("V2.43.20 evaluator partition identity drifted")
    return [(0, 16), (16, 32), (32, 48), (48, 64)]


def evaluator_command(root: Path, protocol: Mapping[str, Any], arm: str, worker: int, predictions: Path) -> list[str]:
    evaluator = protocol["evaluator_contract"]
    judge = evaluator["judge"]
    return [
        str(root / ".venv-eval/bin/python"), "-I", "-B",
        str(root / "scripts/run_official_eval_local.py"),
        "--predictions", str(predictions),
        "--out-dir", str(root / RUNS[arm] / f"worker_{worker:02d}"),
        "--query-path", str(root / evaluator["query_data"]["path"]),
        "--answer-root", str(root / evaluator["answer_corpus"]["root"]),
        "--proxy-url", judge["proxy_url"],
        "--model", judge["model"],
        "--reasoning-effort", judge["reasoning_effort"],
        "--judge-max-output-tokens", str(judge["max_output_tokens"]),
        "--judge-timeout", str(judge["timeout_seconds"]),
        "--judge-max-retries", str(judge["max_retries"]),
    ]


def _run_worker(
    arm: str,
    worker: int,
    command: list[str],
    root: Path,
    runner: Callable[..., subprocess.CompletedProcess[Any]],
) -> dict[str, Any]:
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"})
    log = root / LOGS[arm] / f"worker_{worker:02d}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    with log.open("xb") as handle:
        completed = runner(command, cwd=root, env=environment, stdout=handle, stderr=subprocess.STDOUT, check=False)
        handle.flush()
        os.fsync(handle.fileno())
    return {
        "arm": arm,
        "worker": worker,
        "returncode": completed.returncode,
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "log_sha256": sha256(log),
    }


def _run_all_evaluators_under_lease(
    root: Path,
    protocol: Mapping[str, Any],
    prepared: Mapping[str, Mapping[str, Any]],
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    partitions = fixed_partitions()
    commands: list[dict[str, Any]] = []
    for arm in ARMS:
        (root / RUNS[arm]).mkdir(mode=0o700, parents=True, exist_ok=False)
        for worker, (start, end) in enumerate(partitions, start=1):
            rows = prepared[arm]["official"][start:end]
            shard = root / RUNS[arm] / f"worker_{worker:02d}_predictions.jsonl"
            _write_jsonl_new(shard, rows)
            commands.append(
                {
                    "arm": arm,
                    "worker": worker,
                    "start": start,
                    "end": end,
                    "ids": [row["instance_id"] for row in rows],
                    "shard": shard,
                    "command": evaluator_command(root, protocol, arm, worker, shard),
                }
            )
    started = time.monotonic()
    reports: dict[tuple[str, int], dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=TOTAL_EVALUATOR_WORKERS, thread_name_prefix="v24320-eval") as executor:
        futures = {
            executor.submit(_run_worker, item["arm"], item["worker"], item["command"], root, command_runner): (item["arm"], item["worker"])
            for item in commands
        }
        for future in concurrent.futures.as_completed(futures):
            report = future.result()
            reports[(report["arm"], report["worker"])] = report
    parallel_wall = round(max(0.0, time.monotonic() - started), 6)
    output: dict[str, Any] = {"parallel_wall_seconds": parallel_wall, "arms": {}}
    live = validate_live_evaluator_identity(root, protocol)
    for arm in ARMS:
        merged: list[dict[str, Any]] = []
        worker_reports: list[dict[str, Any]] = []
        for item in [value for value in commands if value["arm"] == arm]:
            report = reports[(arm, item["worker"])]
            if report["returncode"] != 0:
                raise RuntimeError(f"V2.43.20 {arm} evaluator worker {item['worker']} failed")
            run_root = root / RUNS[arm] / f"worker_{item['worker']:02d}"
            rows = read_jsonl(run_root / "official_eval_results.jsonl")
            validate_committed_eval_rows(rows, item["ids"])
            if len(rows) != 16:
                raise RuntimeError("V2.43.20 evaluator worker is not exact16")
            contract = validate_evaluator_contract(
                run_root / "run_config.json",
                expected_predictions_path=item["shard"],
                expected_predictions_sha256=sha256(item["shard"]),
                expected_selected_count=16,
            )
            for key in ("query_data_sha256", "answer_corpus_manifest_sha256", "evaluator_source_manifest_sha256", "judge", "recovery_policy"):
                if contract.get(key) != live.get(key):
                    raise RuntimeError(f"V2.43.20 {arm} evaluator {key} drifted")
            merged.extend(rows)
            worker_reports.append(
                {
                    **report,
                    "start": item["start"],
                    "end": item["end"],
                    "selected": 16,
                    "prediction_shard_sha256": sha256(item["shard"]),
                    "results_sha256": sha256(run_root / "official_eval_results.jsonl"),
                    "run_config_sha256": sha256(run_root / "run_config.json"),
                    "run_contract_sha256": contract["run_contract_sha256"],
                }
            )
        expected_ids = [row["instance_id"] for row in prepared[arm]["official"]]
        validate_committed_eval_rows(merged, expected_ids)
        if len(merged) != SELECTED_COUNT:
            raise RuntimeError(f"V2.43.20 {arm} merged evaluator is not exact64")
        _write_jsonl_new(root / MERGED[arm], merged)
        attestation = {
            "artifact_version": 1,
            "role": "v24320_parallel_arm_evaluator_merge_attestation",
            "arm": arm,
            "selected": SELECTED_COUNT,
            "workers": EVALUATOR_WORKERS_PER_ARM,
            "fixed_contiguous_partitions": [
                {"worker": index + 1, "start": start, "end": end}
                for index, (start, end) in enumerate(partitions)
            ],
            "worker_reports": worker_reports,
            "shared_both_arm_parallel_wall_seconds": parallel_wall,
            "merged_results_sha256": sha256(root / MERGED[arm]),
            "all_frozen_predictions_evaluated_exactly_once": True,
            "selective_retry_or_error_revaluation": False,
        }
        attestation["merge_payload_sha256"] = payload_sha256(attestation)
        _new_json(root / MERGE[arm], attestation)
        output["arms"][arm] = {"rows": merged, "attestation": attestation}
    return output


def run_all_evaluators(
    root: Path,
    protocol: Mapping[str, Any],
    prepared: Mapping[str, Mapping[str, Any]],
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
    lease_already_held: bool = False,
) -> dict[str, Any]:
    if not isinstance(lease_already_held, bool):
        raise TypeError("V2.43.20 evaluator lease state drifted")
    if lease_already_held:
        return _run_all_evaluators_under_lease(
            root, protocol, prepared, command_runner=command_runner
        )
    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["evaluator_owner"],
        purpose=lease["evaluator_purpose"],
        path=root / lease["path"],
    ):
        return _run_all_evaluators_under_lease(
            root, protocol, prepared, command_runner=command_runner
        )


def validate_evaluator_merge(
    root: Path,
    protocol: Mapping[str, Any],
    prepared: Mapping[str, Any],
    arm: str,
) -> dict[str, Any]:
    """Validate the complete four-worker evaluator lineage for one arm."""

    if arm not in ARMS:
        raise RuntimeError(f"V2.43.20 unknown evaluator arm: {arm}")
    live = validate_live_evaluator_identity(root, protocol)
    partitions = fixed_partitions()
    expected_ids = [str(row["instance_id"]) for row in prepared["official"]]
    if len(expected_ids) != SELECTED_COUNT or len(set(expected_ids)) != SELECTED_COUNT:
        raise RuntimeError(f"V2.43.20 {arm} official prediction identity drifted")
    attestation = read_object(root / MERGE[arm])
    unsigned = dict(attestation)
    seal = unsigned.pop("merge_payload_sha256", None)
    reports = attestation.get("worker_reports")
    expected_partitions = [
        {"worker": index + 1, "start": start, "end": end}
        for index, (start, end) in enumerate(partitions)
    ]
    if (
        attestation.get("artifact_version") != 1
        or attestation.get("role") != "v24320_parallel_arm_evaluator_merge_attestation"
        or attestation.get("arm") != arm
        or attestation.get("selected") != SELECTED_COUNT
        or attestation.get("workers") != EVALUATOR_WORKERS_PER_ARM
        or attestation.get("fixed_contiguous_partitions") != expected_partitions
        or not isinstance(reports, list)
        or len(reports) != EVALUATOR_WORKERS_PER_ARM
        or attestation.get("all_frozen_predictions_evaluated_exactly_once") is not True
        or attestation.get("selective_retry_or_error_revaluation") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError(f"V2.43.20 {arm} merge attestation identity drifted")
    parallel_wall = attestation.get("shared_both_arm_parallel_wall_seconds")
    if (
        isinstance(parallel_wall, bool)
        or not isinstance(parallel_wall, (int, float))
        or not math.isfinite(float(parallel_wall))
        or float(parallel_wall) < 0
    ):
        raise RuntimeError(f"V2.43.20 {arm} evaluator wall time drifted")

    merged_from_workers: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(partitions):
        worker = index + 1
        report = reports[index]
        if not isinstance(report, Mapping):
            raise RuntimeError(f"V2.43.20 {arm} worker report is malformed")
        shard = root / RUNS[arm] / f"worker_{worker:02d}_predictions.jsonl"
        expected_shard = list(prepared["official"][start:end])
        if read_jsonl(shard) != expected_shard:
            raise RuntimeError(f"V2.43.20 {arm} evaluator worker {worker} prediction shard drifted")
        run_root = root / RUNS[arm] / f"worker_{worker:02d}"
        result_path = run_root / "official_eval_results.jsonl"
        config_path = run_root / "run_config.json"
        log_path = root / LOGS[arm] / f"worker_{worker:02d}.log"
        rows = read_jsonl(result_path)
        ids = expected_ids[start:end]
        validate_committed_eval_rows(rows, ids)
        if len(rows) != end - start:
            raise RuntimeError(f"V2.43.20 {arm} evaluator worker {worker} is not exact16")
        contract = validate_evaluator_contract(
            config_path,
            expected_predictions_path=shard,
            expected_predictions_sha256=sha256(shard),
            expected_selected_count=end - start,
        )
        for key in (
            "query_data_sha256",
            "answer_corpus_manifest_sha256",
            "evaluator_source_manifest_sha256",
            "judge",
            "recovery_policy",
        ):
            if contract.get(key) != live.get(key):
                raise RuntimeError(f"V2.43.20 {arm} evaluator {key} drifted")
        wall = report.get("wall_seconds")
        if (
            isinstance(wall, bool)
            or not isinstance(wall, (int, float))
            or not math.isfinite(float(wall))
            or float(wall) < 0
            or report.get("arm") != arm
            or report.get("worker") != worker
            or report.get("returncode") != 0
            or report.get("start") != start
            or report.get("end") != end
            or report.get("selected") != end - start
            or report.get("prediction_shard_sha256") != sha256(shard)
            or report.get("results_sha256") != sha256(result_path)
            or report.get("run_config_sha256") != sha256(config_path)
            or report.get("run_contract_sha256") != contract["run_contract_sha256"]
            or report.get("log_sha256") != sha256(log_path)
        ):
            raise RuntimeError(f"V2.43.20 {arm} evaluator worker {worker} provenance drifted")
        merged_from_workers.extend(rows)

    merged = read_jsonl(root / MERGED[arm])
    validate_committed_eval_rows(merged, expected_ids)
    if (
        len(merged) != SELECTED_COUNT
        or merged != merged_from_workers
        or attestation.get("merged_results_sha256") != sha256(root / MERGED[arm])
    ):
        raise RuntimeError(f"V2.43.20 {arm} merged evaluator rows drifted")
    return {"rows": merged, "attestation": attestation}


def validate_arm_summary(
    root: Path,
    prepared: Mapping[str, Any],
    evaluated: Mapping[str, Any],
    arm: str,
) -> dict[str, Any]:
    expected = summarize_rollout(prepared["joined"], evaluated["rows"], rollout_id=1)
    stored = read_object(root / SUMMARY[arm])
    if stored != expected:
        raise RuntimeError(f"V2.43.20 {arm} conservative summary drifted")
    return stored


def _arm_metrics(summary: Mapping[str, Any], forward: Mapping[str, Any]) -> dict[str, Any]:
    group = summary["groups"]["dev_validation_64"]
    conservative = group["conservative_all_selected"]
    value = {
        "runtime_completed": int(group["runtime_completed"]),
        "runtime_failed": int(group["runtime_failed"]),
        "evaluator_valid": int(group["evaluator_valid"]),
        "evaluator_invalid_or_not_run": int(group["evaluator_invalid_or_not_run"]),
        "whole_table_successes": sum(
            row["evaluator_valid"] and float(row["metrics"]["score"]) > 0
            for row in summary["per_task"]
        ),
        **{name: float(conservative[name]) for name in QUALITY},
        "quality_composite": sum(float(conservative[name]) for name in QUALITY) / len(QUALITY),
        "score": float(conservative["score"]),
        "model_generated_tables": int(forward["model_generated_tables"]),
        "fallback_tables": int(forward["fallback_tables"]),
        "system_total_tokens": int(forward["system_total_tokens"]),
        "task_wall_sum_seconds": float(forward["task_wall_seconds_sum"]),
    }
    validate_arm_metrics(value)
    return value


def validate_arm_metrics(value: Mapping[str, Any]) -> None:
    expected = {
        "runtime_completed", "runtime_failed", "evaluator_valid", "evaluator_invalid_or_not_run",
        "whole_table_successes", *QUALITY, "quality_composite", "score", "model_generated_tables",
        "fallback_tables", "system_total_tokens", "task_wall_sum_seconds",
    }
    if set(value) != expected:
        raise RuntimeError("V2.43.20 arm metric schema drifted")
    integer_counts = expected - set(QUALITY) - {
        "quality_composite", "score", "task_wall_sum_seconds",
    }
    if any(
        isinstance(value[name], bool)
        or not isinstance(value[name], int)
        or value[name] < 0
        for name in integer_counts
    ):
        raise RuntimeError("V2.43.20 arm count metric drifted")
    if (
        value["runtime_completed"] + value["runtime_failed"] != SELECTED_COUNT
        or value["evaluator_valid"] + value["evaluator_invalid_or_not_run"] != SELECTED_COUNT
        or value["model_generated_tables"] + value["fallback_tables"] != SELECTED_COUNT
        or value["whole_table_successes"] > value["evaluator_valid"]
    ):
        raise RuntimeError("V2.43.20 arm denominator drifted")
    for name in (*QUALITY, "quality_composite", "score"):
        number = value[name]
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(float(number)) or not 0 <= float(number) <= 1:
            raise RuntimeError("V2.43.20 arm quality metric drifted")
    wall = value["task_wall_sum_seconds"]
    if (
        isinstance(wall, bool)
        or not isinstance(wall, (int, float))
        or not math.isfinite(float(wall))
        or float(wall) < 0
    ):
        raise RuntimeError("V2.43.20 arm wall metric drifted")


def validate_arm_health(value: Mapping[str, Any], arm: str) -> None:
    expected = {
        "retrieval_completed", "controller_stop", "controller_expand",
        "reserved_stage_executed", "low_coverage_diversity_tail",
        "selected_tail_count", "reserved_fetches", "reserved_usable_pages",
        "hosted_search_requests_added_by_reserved",
        "cache_miss_count", "cache_serve_network_fetches", "hard_fetch_deadline_failures",
        "fetch_helper_failures", "hosted_search_attempts",
        "hosted_search_deadline_failures", "fetch_deadline_rejections",
        "deadline_exhausted_tasks", "recovery_enabled",
        "effect_attribution_complete", "effect_count_complete",
        "provider_attempt_count_complete",
        "synthesis_initial_model_request_error", "synthesis_recovery_attempted",
        "synthesis_recovery_succeeded", "synthesis_recovery_model_request_error",
        "repair_blocked_after_recovery", "fourth_model_effect",
        "total_model_effects_lower_bound", "admitted_model_effects_upper_bound",
        "provider_requests_lower_bound", "provider_attempts_lower_bound",
        "pre_provider_rejections_lower_bound",
        "unattributed_model_effects", "parent_exit_receipts_present",
        "parent_exit_receipts_valid", "valid_child_terminal_receipts",
        "model_slot_receipts_present", "valid_model_slot_receipts",
        "valid_transport_receipts", "successful_parent_exits",
        "non_success_parent_exits", "incomplete_effect_counts",
    }
    if (
        arm not in ARMS
        or set(value) != expected
        or any(
            isinstance(number, bool) or not isinstance(number, int) or number < 0
            for number in value.values()
        )
        or value["controller_stop"] + value["controller_expand"] != value["retrieval_completed"]
        or value["retrieval_completed"] > SELECTED_COUNT
        or value["reserved_stage_executed"] > value["controller_expand"]
        or value["low_coverage_diversity_tail"] > value["reserved_stage_executed"]
        or value["hosted_search_requests_added_by_reserved"] != 0
        or value["recovery_enabled"] != SELECTED_COUNT
        or value["effect_attribution_complete"] > value["effect_count_complete"]
        or value["provider_attempt_count_complete"] > value["effect_count_complete"]
        or value["effect_count_complete"] + value["incomplete_effect_counts"]
        != SELECTED_COUNT
        or value["total_model_effects_lower_bound"]
        > value["admitted_model_effects_upper_bound"]
        or value["provider_requests_lower_bound"]
        + value["pre_provider_rejections_lower_bound"]
        > value["total_model_effects_lower_bound"]
        or value["provider_attempts_lower_bound"]
        < value["provider_requests_lower_bound"]
        or value["admitted_model_effects_upper_bound"] > SELECTED_COUNT * 3
        or value["unattributed_model_effects"]
        > value["total_model_effects_lower_bound"]
        or value["parent_exit_receipts_present"] > SELECTED_COUNT
        or value["parent_exit_receipts_valid"]
        > value["parent_exit_receipts_present"]
        or value["valid_child_terminal_receipts"]
        > value["parent_exit_receipts_valid"]
        or value["model_slot_receipts_present"] > SELECTED_COUNT
        or value["valid_model_slot_receipts"]
        > value["model_slot_receipts_present"]
        or value["valid_transport_receipts"] > SELECTED_COUNT
        or value["successful_parent_exits"] + value["non_success_parent_exits"]
        != SELECTED_COUNT
        or value["fourth_model_effect"] > SELECTED_COUNT
        or value["synthesis_recovery_succeeded"] > value["synthesis_recovery_attempted"]
        or value["synthesis_recovery_model_request_error"] > value["synthesis_recovery_attempted"]
        or value["hosted_search_deadline_failures"]
        > value["hosted_search_attempts"]
        or value["deadline_exhausted_tasks"] > SELECTED_COUNT
        or arm == "baseline" and any(
            value[name] for name in (
                "reserved_stage_executed", "low_coverage_diversity_tail",
                "selected_tail_count", "reserved_fetches", "reserved_usable_pages",
            )
        )
    ):
        raise RuntimeError("V2.43.20 arm health drifted")


def _arm_health(summary: Mapping[str, Any], arm: str) -> dict[str, Any]:
    mechanism = summary.get("mechanism_totals")
    observability = summary.get("parent_exit_observability")
    taxonomy = observability.get("taxonomy") if isinstance(observability, Mapping) else None
    if not isinstance(mechanism, Mapping) or not isinstance(observability, Mapping) or not isinstance(taxonomy, Mapping):
        raise RuntimeError("V2.43.20 arm health source is incomplete")
    value = {
        **dict(mechanism),
        "hard_fetch_deadline_failures": int(summary["hard_fetch_deadline_failures"]),
        "fetch_helper_failures": int(summary["fetch_helper_failures"]),
        "hosted_search_attempts": int(summary["hosted_search_attempts"]),
        "hosted_search_deadline_failures": int(
            summary["hosted_search_deadline_failures"]
        ),
        "fetch_deadline_rejections": int(summary["fetch_deadline_rejections"]),
        "deadline_exhausted_tasks": int(summary["deadline_exhausted_tasks"]),
        "parent_exit_receipts_present": int(observability["receipts_present"]),
        "parent_exit_receipts_valid": int(observability["receipts_valid"]),
        "valid_child_terminal_receipts": int(
            observability["valid_child_terminal_receipts"]
        ),
        "model_slot_receipts_present": int(
            observability["model_slot_receipts_present"]
        ),
        "valid_model_slot_receipts": int(
            observability["valid_model_slot_receipts"]
        ),
        "valid_transport_receipts": int(
            observability["valid_transport_receipts"]
        ),
        "successful_parent_exits": int(
            observability["accepted_parent_successes"]
        ),
        "non_success_parent_exits": int(
            observability["non_success_parent_exits"]
        ),
        "incomplete_effect_counts": int(
            observability["incomplete_effect_counts"]
        ),
    }
    validate_arm_health(value, arm)
    return value


def paired_uncertainty(
    summaries: Mapping[str, Mapping[str, Any]],
    *,
    seed: int,
    resamples: int,
) -> dict[str, Any]:
    if (
        set(summaries) != set(ARMS)
        or isinstance(seed, bool)
        or not isinstance(seed, int)
        or isinstance(resamples, bool)
        or not isinstance(resamples, int)
        or resamples != 10_000
    ):
        raise RuntimeError("V2.43.20 paired uncertainty contract drifted")
    by_arm: dict[str, dict[str, Mapping[str, Any]]] = {}
    order: list[str] = []
    for arm in ARMS:
        rows = summaries[arm].get("per_task")
        if not isinstance(rows, list) or len(rows) != SELECTED_COUNT:
            raise RuntimeError("V2.43.20 paired uncertainty task count drifted")
        mapping: dict[str, Mapping[str, Any]] = {}
        for row in rows:
            if not isinstance(row, Mapping) or not isinstance(row.get("opaque_id"), str):
                raise RuntimeError("V2.43.20 paired uncertainty row drifted")
            opaque_id = str(row["opaque_id"])
            metrics = row.get("metrics")
            if not isinstance(metrics, Mapping):
                raise RuntimeError("V2.43.20 paired uncertainty metrics are absent")
            for name in QUALITY:
                number = metrics.get(name)
                if (
                    isinstance(number, bool)
                    or not isinstance(number, (int, float))
                    or not math.isfinite(float(number))
                    or not 0 <= float(number) <= 1
                ):
                    raise RuntimeError("V2.43.20 paired uncertainty metric drifted")
            if opaque_id in mapping:
                raise RuntimeError("V2.43.20 paired uncertainty duplicate task")
            mapping[opaque_id] = row
        by_arm[arm] = mapping
        if arm == "baseline":
            order = [str(row["opaque_id"]) for row in rows]
    if set(by_arm["candidate"]) != set(order):
        raise RuntimeError("V2.43.20 paired uncertainty task identity drifted")
    deltas = [
        sum(
            float(by_arm["candidate"][opaque_id]["metrics"][name])
            - float(by_arm["baseline"][opaque_id]["metrics"][name])
            for name in QUALITY
        )
        / len(QUALITY)
        for opaque_id in order
    ]
    generator = random.Random(seed)
    estimates = sorted(
        sum(deltas[generator.randrange(len(deltas))] for _ in deltas) / len(deltas)
        for _ in range(resamples)
    )
    interval = [estimates[249], estimates[9749]]
    value = {
        "task_count": SELECTED_COUNT,
        "bootstrap_unit": "paired_frozen_task",
        "seed": seed,
        "resamples": resamples,
        "estimand": "mean paired failure-as-zero quality composite delta on fresh dev64",
        "mean": sum(deltas) / len(deltas),
        "median": statistics.median(deltas),
        "positive": sum(delta > 0 for delta in deltas),
        "zero": sum(delta == 0 for delta in deltas),
        "negative": sum(delta < 0 for delta in deltas),
        "minimum": min(deltas),
        "maximum": max(deltas),
        "percentile_95_interval": interval,
        "interval_width": interval[1] - interval[0],
        "fixed_denominator_failure_as_zero": True,
        "predictions_frozen_before_evaluator": True,
        "confirmatory_development_gate": True,
        "future_population_or_sota_inference": False,
    }
    validate_paired_uncertainty(value, seed=seed, resamples=resamples)
    return value


def validate_paired_uncertainty(
    value: Mapping[str, Any], *, seed: int, resamples: int
) -> None:
    counts = (value.get("positive"), value.get("zero"), value.get("negative"))
    interval = value.get("percentile_95_interval")
    numeric = (
        value.get("mean"), value.get("median"), value.get("minimum"),
        value.get("maximum"), value.get("interval_width"),
    )
    if (
        value.get("task_count") != SELECTED_COUNT
        or value.get("bootstrap_unit") != "paired_frozen_task"
        or value.get("seed") != seed
        or value.get("resamples") != resamples
        or any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in counts)
        or sum(counts) != SELECTED_COUNT
        or not isinstance(interval, list)
        or len(interval) != 2
        or any(
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not math.isfinite(float(number))
            for number in (*numeric, *interval)
        )
        or float(interval[0]) > float(interval[1])
        or not math.isclose(
            float(value["interval_width"]),
            float(interval[1]) - float(interval[0]),
            abs_tol=1e-12,
        )
        or value.get("fixed_denominator_failure_as_zero") is not True
        or value.get("predictions_frozen_before_evaluator") is not True
        or value.get("confirmatory_development_gate") is not True
        or value.get("future_population_or_sota_inference") is not False
    ):
        raise RuntimeError("V2.43.20 paired uncertainty drifted")


def decision(
    protocol: Mapping[str, Any],
    baseline: Mapping[str, Any],
    candidate: Mapping[str, Any],
    health: Mapping[str, Mapping[str, Any]],
    uncertainty: Mapping[str, Any],
    *,
    shared_forward_wall_seconds: float,
) -> dict[str, Any]:
    validate_arm_metrics(baseline)
    validate_arm_metrics(candidate)
    for arm in ARMS:
        validate_arm_health(health[arm], arm)
    gate = protocol["decision_contract"]
    validate_paired_uncertainty(
        uncertainty,
        seed=gate["paired_bootstrap_seed"],
        resamples=gate["paired_bootstrap_resamples"],
    )
    deltas = {
        name: candidate[name] - baseline[name]
        for name in (
            "quality_composite", "entity_acc", "f1_by_row", "f1_by_item", "column_f1",
            "whole_table_successes", "model_generated_tables",
        )
    }
    token_ratio = candidate["system_total_tokens"] / max(1, baseline["system_total_tokens"])
    wall_ratio = candidate["task_wall_sum_seconds"] / max(1e-9, baseline["task_wall_sum_seconds"])
    shared_forward_wall = float(shared_forward_wall_seconds)
    predecessor_forward_wall = float(
        protocol["predecessor_efficiency_contract"][
            "v24314_shared_forward_wall_seconds"
        ]
    )
    shared_forward_wall_ratio = shared_forward_wall / predecessor_forward_wall
    if (
        not math.isfinite(shared_forward_wall)
        or shared_forward_wall < 0
        or not math.isfinite(predecessor_forward_wall)
        or predecessor_forward_wall <= 0
    ):
        raise RuntimeError("V2.43.20 forward wall evidence drifted")
    checks = {
        "quality_composite_delta": deltas["quality_composite"] >= gate["minimum_quality_composite_delta"],
        "entity_acc_delta": deltas["entity_acc"] >= gate["minimum_entity_acc_delta"],
        "f1_by_row_delta": deltas["f1_by_row"] >= gate["minimum_f1_by_row_delta"],
        "f1_by_item_delta": deltas["f1_by_item"] >= gate["minimum_f1_by_item_delta"],
        "column_f1_delta": deltas["column_f1"] >= gate["minimum_column_f1_delta"],
        "whole_table_success_delta": deltas["whole_table_successes"] >= gate["minimum_whole_table_success_delta"],
        "model_generated_table_delta": deltas["model_generated_tables"] >= gate["minimum_candidate_minus_baseline_model_generated_tables"],
        "system_token_ratio": token_ratio <= gate["maximum_system_token_ratio"],
        "task_wall_sum_ratio": wall_ratio <= gate["maximum_task_wall_sum_ratio"],
        "shared_forward_wall_seconds_vs_v24314_ratio": shared_forward_wall_ratio
        <= gate["maximum_shared_forward_wall_seconds_vs_v24314_ratio"],
        "candidate_evaluator_invalid_or_not_run": candidate["evaluator_invalid_or_not_run"] <= gate["maximum_candidate_evaluator_invalid_or_not_run"],
        "baseline_evaluator_invalid_or_not_run": baseline["evaluator_invalid_or_not_run"] <= gate["maximum_baseline_evaluator_invalid_or_not_run"],
        "candidate_fallback_tables": candidate["fallback_tables"] <= gate["maximum_candidate_fallback_tables"],
        "fallback_table_delta": candidate["fallback_tables"] - baseline["fallback_tables"] <= gate["maximum_candidate_minus_baseline_fallback_tables"],
        "recovery_enabled_both_arms": all(
            health[arm]["recovery_enabled"]
            == gate["required_recovery_enabled_per_arm"]
            for arm in ARMS
        ),
        "recovery_provider_failures": all(
            health[arm]["synthesis_recovery_model_request_error"]
            <= gate["maximum_recovery_provider_failures_per_arm"]
            for arm in ARMS
        ),
        "repair_blocked_after_recovery": all(
            health[arm]["repair_blocked_after_recovery"]
            <= gate["maximum_repair_blocked_after_recovery_per_arm"]
            for arm in ARMS
        ),
        "fourth_model_effects": all(
            health[arm]["fourth_model_effect"] <= gate["maximum_fourth_model_effects_per_arm"]
            for arm in ARMS
        ),
        "candidate_low_coverage_diversity_tail_tasks": health["candidate"]["low_coverage_diversity_tail"] >= gate["minimum_candidate_low_coverage_diversity_tail_tasks"],
        "candidate_selected_tail_count": health["candidate"]["selected_tail_count"] >= gate["minimum_candidate_selected_tail_count"],
        "candidate_reserved_usable_pages": health["candidate"]["reserved_usable_pages"] >= gate["minimum_candidate_reserved_usable_pages"],
        "hosted_search_requests_added_by_reserved": all(health[arm]["hosted_search_requests_added_by_reserved"] <= gate["maximum_hosted_search_requests_added_by_reserved"] for arm in ARMS),
        "cache_misses": all(health[arm]["cache_miss_count"] <= gate["maximum_cache_misses"] for arm in ARMS),
        "cache_serve_network_fetches": all(health[arm]["cache_serve_network_fetches"] <= gate["maximum_cache_serve_network_fetches"] for arm in ARMS),
        "hard_fetch_deadline_failures": all(health[arm]["hard_fetch_deadline_failures"] <= gate["maximum_hard_fetch_deadline_failures"] for arm in ARMS),
        "fetch_helper_failures": all(health[arm]["fetch_helper_failures"] <= gate["maximum_fetch_helper_failures"] for arm in ARMS),
        "hosted_search_deadline_failures": all(
            health[arm]["hosted_search_deadline_failures"]
            <= gate["maximum_hosted_search_deadline_failures_per_arm"]
            for arm in ARMS
        ),
        "fetch_deadline_rejections": all(
            health[arm]["fetch_deadline_rejections"]
            <= gate["maximum_fetch_deadline_rejections_per_arm"]
            for arm in ARMS
        ),
        "deadline_exhausted_tasks": all(
            health[arm]["deadline_exhausted_tasks"]
            <= gate["maximum_deadline_exhausted_tasks_per_arm"]
            for arm in ARMS
        ),
        "parent_exit_receipts": all(
            health[arm]["parent_exit_receipts_present"]
            == gate["required_parent_exit_receipts_per_arm"]
            and health[arm]["parent_exit_receipts_valid"]
            == gate["required_parent_exit_receipts_per_arm"]
            for arm in ARMS
        ),
        "valid_child_terminal_receipts": all(
            health[arm]["valid_child_terminal_receipts"]
            >= gate["minimum_valid_child_terminal_receipts_per_arm"]
            for arm in ARMS
        ),
        "valid_model_slot_receipts": all(
            health[arm]["valid_model_slot_receipts"]
            >= gate["minimum_valid_model_slot_receipts_per_arm"]
            for arm in ARMS
        ),
        "valid_transport_receipts": all(
            health[arm]["valid_transport_receipts"]
            >= gate["minimum_valid_transport_receipts_per_arm"]
            for arm in ARMS
        ),
        "non_success_parent_exits": all(
            health[arm]["non_success_parent_exits"]
            <= gate["maximum_non_success_parent_exits_per_arm"]
            for arm in ARMS
        ),
        "incomplete_effect_counts": all(
            health[arm]["incomplete_effect_counts"]
            <= gate["maximum_incomplete_effect_counts_per_arm"]
            for arm in ARMS
        ),
        "paired_bootstrap_lower_bound": uncertainty["percentile_95_interval"][0] >= gate["minimum_paired_bootstrap_95_lower_bound"],
        "paired_bootstrap_interval_width": uncertainty["interval_width"] <= gate["maximum_paired_bootstrap_95_interval_width"],
        "paired_median_composite_delta": uncertainty["median"] >= gate["minimum_paired_median_composite_delta"],
    }
    passed = all(checks.values())
    return {
        "status": "go" if passed else "no_go",
        "passed": passed,
        "checks": checks,
        "failed_checks": sorted(name for name, passed_ in checks.items() if not passed_),
        "candidate_minus_baseline": deltas,
        "system_token_ratio": token_ratio,
        "task_wall_sum_ratio": wall_ratio,
        "shared_forward_wall_seconds_vs_v24314_ratio": shared_forward_wall_ratio,
        "gate": dict(gate),
        "paired_uncertainty": dict(uncertainty),
        "go_scope": "fresh_exact220_design_only_not_launch",
    }


def _recompute(root: Path, protocol: Mapping[str, Any]) -> dict[str, Any]:
    barrier = validate_candidate_barrier(root)
    live = validate_live_evaluator_identity(root, protocol)
    prepared = {
        arm: validate_prepared_arm(root, protocol, barrier, arm) for arm in ARMS
    }
    evaluated = {
        arm: validate_evaluator_merge(root, protocol, prepared[arm], arm)
        for arm in ARMS
    }
    summaries = {
        arm: validate_arm_summary(root, prepared[arm], evaluated[arm], arm)
        for arm in ARMS
    }
    walls = {
        evaluated[arm]["attestation"]["shared_both_arm_parallel_wall_seconds"]
        for arm in ARMS
    }
    if len(walls) != 1:
        raise RuntimeError("V2.43.20 both-arm evaluator wall identity drifted")
    metrics: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        projection = barrier["arms"][arm]["summary"]
        metrics[arm] = _arm_metrics(
            summaries[arm],
            {
                "model_generated_tables": projection["model_generated_tables"],
                "fallback_tables": projection["fallback_tables"],
                "system_total_tokens": projection["system_total_tokens"],
                "task_wall_seconds_sum": projection["task_wall_seconds_sum"],
            },
        )
    health = {
        arm: _arm_health(barrier["arms"][arm]["summary"], arm)
        for arm in ARMS
    }
    uncertainty = paired_uncertainty(
        summaries,
        seed=protocol["decision_contract"]["paired_bootstrap_seed"],
        resamples=protocol["decision_contract"]["paired_bootstrap_resamples"],
    )
    gate = decision(
        protocol,
        metrics["baseline"],
        metrics["candidate"],
        health,
        uncertainty,
        shared_forward_wall_seconds=barrier["forward"][
            "shared_forward_wall_seconds"
        ],
    )
    return {
        "barrier": barrier,
        "live": live,
        "prepared": prepared,
        "evaluated": evaluated,
        "metrics": metrics,
        "health": health,
        "uncertainty": uncertainty,
        "decision": gate,
        "parallel_wall": next(iter(walls)),
    }


def validate_final_result(root: Path, protocol: Mapping[str, Any], value: Mapping[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    if (
        value.get("artifact_version") != 1
        or value.get("role") != "v24320_synthesis_recovery_paired_dev64_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("status") not in {"development_gate_go", "development_gate_no_go"}
        or value.get("selected_per_arm") != SELECTED_COUNT
        or value.get("conservative_denominator_per_arm") != SELECTED_COUNT
        or value.get("failure_as_zero") is not True
        or value.get("both_arms_exact64_before_mapping_or_evaluator_open") is not True
        or value.get("both_arms_fully_evaluated_with_same_current_judge") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.20 final result identity drifted")
    frozen = validate_protocol(root)
    if dict(protocol) != frozen:
        raise RuntimeError("V2.43.20 final protocol input drifted")
    expected = _recompute(root, frozen)
    if (
        value.get("baseline") != expected["metrics"]["baseline"]
        or value.get("candidate") != expected["metrics"]["candidate"]
        or value.get("arm_health") != expected["health"]
        or value.get("paired_uncertainty") != expected["uncertainty"]
        or value.get("decision") != expected["decision"]
        or value.get("status")
        != ("development_gate_go" if expected["decision"]["passed"] else "development_gate_no_go")
    ):
        raise RuntimeError("V2.43.20 final metrics or decision drifted")
    expected_efficiency = {
        "shared_both_arm_forward_wall_seconds": expected["barrier"]["forward"]["shared_forward_wall_seconds"],
        "both_arm_evaluator_parallel_wall_seconds": expected["parallel_wall"],
        "evaluator_workers_total": TOTAL_EVALUATOR_WORKERS,
    }
    live = expected["live"]
    expected_provenance = {
        "protocol_sha256": sha256(root / FULL_PROTOCOL),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "prediction_freeze_sha256": {
            arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS
        },
        "mapping_sha256": live["mapping_sha256"],
        "query_data_sha256": live["query_data_sha256"],
        "answer_corpus_manifest_sha256": live["answer_corpus_manifest_sha256"],
        "evaluator_source_manifest_sha256": live["evaluator_source_manifest_sha256"],
        "judge": live["judge"],
        "recovery_policy": live["recovery_policy"],
        **{f"{arm}_terminal_outcomes_sha256": sha256(root / JOINED[arm]) for arm in ARMS},
        **{f"{arm}_official_predictions_sha256": sha256(root / OFFICIAL[arm]) for arm in ARMS},
        **{f"{arm}_prepare_attestation_sha256": sha256(root / PREPARE[arm]) for arm in ARMS},
        **{f"{arm}_merged_eval_results_sha256": sha256(root / MERGED[arm]) for arm in ARMS},
        **{f"{arm}_merge_attestation_sha256": sha256(root / MERGE[arm]) for arm in ARMS},
        **{f"{arm}_conservative_summary_sha256": sha256(root / SUMMARY[arm]) for arm in ARMS},
    }
    if value.get("efficiency") != expected_efficiency or value.get("provenance") != expected_provenance:
        raise RuntimeError("V2.43.20 final efficiency or provenance drifted")
    if value.get("source_policy") != {
        "runtime_boundary": ["opaque_id", "question"],
        "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
        "both_arm_prediction_freezes_before_mapping_or_evaluator_open": True,
        "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        "selective_retry_or_error_revaluation": False,
    }:
        raise RuntimeError("V2.43.20 final source policy drifted")
    if value.get("authorization") != {
        "fresh_exact220_design": expected["decision"]["passed"],
        "fresh_exact220_launch": False,
        "additional_dev64_or_avg4": False,
        "leaderboard_submission": False,
        "sota_claim": False,
    }:
        raise RuntimeError("V2.43.20 final authorization drifted")
    if value.get("claims") != {
        "development_gate_only": True,
        "fresh_interleaved_both_arms": True,
        "strict_shared_random_prefix_causal_ablation": False,
        "public_full220_result": False,
        "avg_at_4": False,
        "leaderboard_submitted": False,
        "sota": False,
    }:
        raise RuntimeError("V2.43.20 final claims drifted")


def finalize(
    root: Path = ROOT,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    root = root.resolve()
    if (root / FINAL_RESULT).exists() or (root / FINAL_RESULT).is_symlink():
        raise FileExistsError(root / FINAL_RESULT)
    barrier = validate_candidate_barrier(root)
    protocol = validate_protocol(root)
    if (root / EVALUATOR_ROOT).exists() or (root / EVALUATOR_ROOT).is_symlink():
        raise RuntimeError("V2.43.20 evaluator surface exists; resume and rerun are forbidden")
    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["evaluator_owner"],
        purpose=lease["evaluator_purpose"],
        path=root / lease["path"],
    ):
        live = validate_live_evaluator_identity(root, protocol)
        (root / EVALUATOR_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        prepared = {
            arm: prepare_arm(root, protocol, barrier, arm)
            for arm in ARMS
        }
        evaluated = run_all_evaluators(
            root,
            protocol,
            prepared,
            command_runner=command_runner,
            lease_already_held=True,
        )
    arm_summaries: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        arm_summaries[arm] = summarize_rollout(prepared[arm]["joined"], evaluated["arms"][arm]["rows"], rollout_id=1)
        _new_json(root / SUMMARY[arm], arm_summaries[arm])
    baseline_projection = barrier["arms"]["baseline"]["summary"]
    candidate_summary = barrier["arms"]["candidate"]["summary"]
    baseline_metrics = _arm_metrics(
        arm_summaries["baseline"],
        {
            "model_generated_tables": baseline_projection["model_generated_tables"],
            "fallback_tables": baseline_projection["fallback_tables"],
            "system_total_tokens": baseline_projection["system_total_tokens"],
            "task_wall_seconds_sum": baseline_projection["task_wall_seconds_sum"],
        },
    )
    candidate_metrics = _arm_metrics(
        arm_summaries["candidate"],
        {
            "model_generated_tables": candidate_summary["model_generated_tables"],
            "fallback_tables": candidate_summary["fallback_tables"],
            "system_total_tokens": candidate_summary["system_total_tokens"],
            "task_wall_seconds_sum": candidate_summary["task_wall_seconds_sum"],
        },
    )
    health = {
        "baseline": _arm_health(baseline_projection, "baseline"),
        "candidate": _arm_health(candidate_summary, "candidate"),
    }
    uncertainty = paired_uncertainty(
        arm_summaries,
        seed=protocol["decision_contract"]["paired_bootstrap_seed"],
        resamples=protocol["decision_contract"]["paired_bootstrap_resamples"],
    )
    gate = decision(
        protocol,
        baseline_metrics,
        candidate_metrics,
        health,
        uncertainty,
        shared_forward_wall_seconds=barrier["forward"][
            "shared_forward_wall_seconds"
        ],
    )
    result = {
        "artifact_version": 1,
        "role": "v24320_synthesis_recovery_paired_dev64_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "development_gate_go" if gate["passed"] else "development_gate_no_go",
        "selected_per_arm": SELECTED_COUNT,
        "conservative_denominator_per_arm": SELECTED_COUNT,
        "failure_as_zero": True,
        "both_arms_exact64_before_mapping_or_evaluator_open": True,
        "both_arms_fully_evaluated_with_same_current_judge": True,
        "baseline": baseline_metrics,
        "candidate": candidate_metrics,
        "arm_health": health,
        "paired_uncertainty": uncertainty,
        "decision": gate,
        "efficiency": {
            "shared_both_arm_forward_wall_seconds": barrier["forward"]["shared_forward_wall_seconds"],
            "both_arm_evaluator_parallel_wall_seconds": evaluated["parallel_wall_seconds"],
            "evaluator_workers_total": TOTAL_EVALUATOR_WORKERS,
        },
        "provenance": {
            "protocol_sha256": sha256(root / FULL_PROTOCOL),
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "prediction_freeze_sha256": {
                arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS
            },
            "mapping_sha256": live["mapping_sha256"],
            "query_data_sha256": live["query_data_sha256"],
            "answer_corpus_manifest_sha256": live["answer_corpus_manifest_sha256"],
            "evaluator_source_manifest_sha256": live["evaluator_source_manifest_sha256"],
            "judge": live["judge"],
            "recovery_policy": live["recovery_policy"],
            **{f"{arm}_terminal_outcomes_sha256": sha256(root / JOINED[arm]) for arm in ARMS},
            **{f"{arm}_official_predictions_sha256": sha256(root / OFFICIAL[arm]) for arm in ARMS},
            **{f"{arm}_prepare_attestation_sha256": sha256(root / PREPARE[arm]) for arm in ARMS},
            **{f"{arm}_merged_eval_results_sha256": sha256(root / MERGED[arm]) for arm in ARMS},
            **{f"{arm}_merge_attestation_sha256": sha256(root / MERGE[arm]) for arm in ARMS},
            **{f"{arm}_conservative_summary_sha256": sha256(root / SUMMARY[arm]) for arm in ARMS},
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "both_arm_prediction_freezes_before_mapping_or_evaluator_open": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
            "selective_retry_or_error_revaluation": False,
        },
        "authorization": {
            "fresh_exact220_design": gate["passed"],
            "fresh_exact220_launch": False,
            "additional_dev64_or_avg4": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "claims": {
            "development_gate_only": True,
            "fresh_interleaved_both_arms": True,
            "strict_shared_random_prefix_causal_ablation": False,
            "public_full220_result": False,
            "avg_at_4": False,
            "leaderboard_submitted": False,
            "sota": False,
        },
    }
    result["result_payload_sha256"] = payload_sha256(result)
    validate_final_result(root, protocol, result)
    _new_json(root / FINAL_RESULT, result)
    return result


if __name__ == "__main__":
    value = finalize()
    print(json.dumps({"result": str(FINAL_RESULT), "status": value["status"], "failed_checks": value["decision"]["failed_checks"]}, sort_keys=True))
