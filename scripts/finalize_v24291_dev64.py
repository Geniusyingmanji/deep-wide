#!/usr/bin/env python3
"""Post-freeze full-both-arm evaluation for the V2.42.91 dev64 gate."""

from __future__ import annotations

import concurrent.futures
import json
import math
import os
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

from deepwide_agent import v24287_forward_contract as control_contract  # noqa: E402
from deepwide_agent.v24291_forward_contract import (  # noqa: E402
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
from scripts.finalize_v24287_exact220 import (  # noqa: E402
    validate_final_result as validate_control_final_result,
)
from scripts.preregister_v24291_dev64 import (  # noqa: E402
    CONTROL_FORWARD_CONTRACT,
    CONTROL_FORWARD_RESULT,
    CONTROL_PREDICTION_FREEZE,
    CONTROL_PROTOCOL,
    CONTROL_RUNTIME,
    CONTROL_RUN_SUMMARY,
    EVALUATOR_WORKERS_PER_ARM,
    MAPPING_PATH,
    TOTAL_EVALUATOR_WORKERS,
    validate_protocol,
)
from scripts.run_official_eval_local import validate_committed_eval_rows  # noqa: E402
from scripts.run_v24287_exact220 import (  # noqa: E402
    validate_forward_result as validate_control_forward_result,
    validate_prediction_freeze as validate_control_prediction_freeze,
)
from scripts.run_v24291_dev64 import (  # noqa: E402
    validate_forward_result,
    validate_prediction_freeze,
)


ARMS = ("control", "candidate")
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
    freeze = read_object(root / PREDICTION_FREEZE)
    rows = validate_prediction_freeze(root, contract, freeze)
    summary = read_object(root / RUN_SUMMARY)
    if (
        len(rows) != SELECTED_COUNT
        or forward.get("candidate_exact64_before_control_or_evaluator_open") is not True
        or freeze.get("exact_terminal_before_control_mapping_gold_or_evaluator_open") is not True
        or freeze.get("control_mapping_gold_or_evaluator_opened_or_hashed") is not False
    ):
        raise RuntimeError("V2.42.91 candidate freeze barrier is incomplete")
    return {"contract": contract, "forward": forward, "freeze": freeze, "rows": rows, "summary": summary}


def load_control_after_candidate(root: Path, protocol: Mapping[str, Any], candidate: Mapping[str, Any]) -> dict[str, Any]:
    if len(candidate.get("rows") or []) != SELECTED_COUNT:
        raise RuntimeError("V2.42.91 candidate barrier was not supplied")
    expected = protocol["control_sources_post_candidate_freeze_only"]
    if (
        expected.get("prediction_freeze_runtime_and_summary_opened_or_hashed_during_preregistration") is not False
        or expected.get("forward_contract") != str(CONTROL_FORWARD_CONTRACT)
        or expected.get("forward_result") != str(CONTROL_FORWARD_RESULT)
        or expected.get("prediction_freeze") != str(CONTROL_PREDICTION_FREEZE)
        or expected.get("runtime_predictions") != str(CONTROL_RUNTIME)
        or expected.get("run_summary") != str(CONTROL_RUN_SUMMARY)
    ):
        raise RuntimeError("V2.42.91 control path contract drifted")
    frozen_contract = control_contract.validate_forward_contract(root, CONTROL_FORWARD_CONTRACT)
    frozen_forward = read_object(root / CONTROL_FORWARD_RESULT)
    validate_control_forward_result(root, frozen_contract, frozen_forward)
    control_protocol = read_object(root / CONTROL_PROTOCOL)
    control_result = read_object(root / CONTROL_RESULT)
    control_postaudit = read_object(root / CONTROL_POSTAUDIT)
    validate_control_final_result(root, control_protocol, control_result)
    parent = candidate["contract"].get("parent_evidence") or {}
    post_unsigned = dict(control_postaudit)
    post_seal = post_unsigned.pop("audit_payload_sha256", None)
    if (
        parent.get("control_aggregate_result")
        != {"path": str(CONTROL_RESULT), "sha256": sha256(root / CONTROL_RESULT)}
        or parent.get("control_postresult_audit")
        != {"path": str(CONTROL_POSTAUDIT), "sha256": sha256(root / CONTROL_POSTAUDIT)}
        or control_result.get("status") != "exact220_single_rollout_complete"
        or control_result.get("selected") != 220
        or control_result.get("claims", {}).get("sota") is not False
        or control_postaudit.get("audit_valid") is not True
        or control_postaudit.get("findings") != []
        or control_postaudit.get("final_result_sha256") != sha256(root / CONTROL_RESULT)
        or post_seal != payload_sha256(post_unsigned)
    ):
        raise RuntimeError("V2.42.91 frozen control aggregate or audit drifted")
    frozen_freeze = read_object(root / CONTROL_PREDICTION_FREEZE)
    all_rows = validate_control_prediction_freeze(root, frozen_contract, frozen_freeze)
    all_summary = read_object(root / CONTROL_RUN_SUMMARY)
    ids = selected_ids(candidate["contract"])
    by_id = {row["opaque_id"]: row for row in all_rows}
    if len(by_id) != 220 or any(opaque_id not in by_id for opaque_id in ids):
        raise RuntimeError("V2.42.91 control rows do not cover frozen dev64")
    rows = [by_id[opaque_id] for opaque_id in ids]
    kinds: dict[str, int] = {}
    for row in rows:
        kind = str(row["completion_kind"])
        kinds[kind] = kinds.get(kind, 0) + 1
    model_generated = sum(kind in {"primary", "repaired", "normalized_primary", "normalized_repaired"} for kind in (row["completion_kind"] for row in rows))
    summary = {
        "artifact_version": 1,
        "role": "v24291_control_dev64_projection_summary",
        "selected": SELECTED_COUNT,
        "completed": SELECTED_COUNT,
        "failed": 0,
        "model_generated_tables": model_generated,
        "fallback_tables": SELECTED_COUNT - model_generated,
        "completion_kinds": kinds,
        "system_total_tokens": sum(int(row["cost"]["system_total_tokens"]) for row in rows),
        "task_wall_seconds_sum": round(sum(float(row["elapsed_seconds"]) for row in rows), 6),
        "source_all220_summary_sha256": sha256(root / CONTROL_RUN_SUMMARY),
        "source_all220_system_total_tokens": all_summary["system_total_tokens"],
        "label_blind_forward": True,
    }
    return {
        "ids": ids,
        "rows": rows,
        "summary": summary,
        "sources": {
            "protocol_sha256": sha256(root / CONTROL_PROTOCOL),
            "aggregate_result_sha256": sha256(root / CONTROL_RESULT),
            "postresult_audit_sha256": sha256(root / CONTROL_POSTAUDIT),
            "forward_contract_sha256": sha256(root / CONTROL_FORWARD_CONTRACT),
            "forward_result_sha256": sha256(root / CONTROL_FORWARD_RESULT),
            "prediction_freeze_sha256": sha256(root / CONTROL_PREDICTION_FREEZE),
            "runtime_predictions_sha256": sha256(root / CONTROL_RUNTIME),
            "run_summary_sha256": sha256(root / CONTROL_RUN_SUMMARY),
        },
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
        raise RuntimeError("V2.42.91 live evaluator identity drifted")
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
    candidate: Mapping[str, Any],
    control: Mapping[str, Any],
    arm: str,
) -> dict[str, Any]:
    rows = control["rows"] if arm == "control" else candidate["rows"]
    summary = control["summary"] if arm == "control" else candidate["summary"]
    source_hashes = control["sources"] if arm == "control" else {
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS),
        "run_summary_sha256": sha256(root / RUN_SUMMARY),
    }
    joined, official, base = prepare_rollout(
        manifest_rows=read_jsonl(root / SOURCE_MANIFEST),
        mapping_rows=read_jsonl(root / MAPPING_PATH),
        shards=[("devval", control["ids"], rows, summary)],
        rollout_id=1,
    )
    if len(joined) != SELECTED_COUNT or len(official) != SELECTED_COUNT:
        raise RuntimeError(f"V2.42.91 {arm} evaluator prepare is not full64")
    (root / ARM_ROOTS[arm]).mkdir(mode=0o700, parents=True, exist_ok=False)
    _write_jsonl_new(root / JOINED[arm], joined)
    _write_jsonl_new(root / OFFICIAL[arm], official)
    attestation = {
        **base,
        "phase": "post_candidate_exact64_freeze_fresh_full_arm_evaluator_prepare",
        "arm": arm,
        "protocol_sha256": sha256(root / FULL_PROTOCOL),
        "candidate_prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "candidate_exact64_before_control_mapping_gold_or_evaluator_open": True,
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
    candidate: Mapping[str, Any],
    control: Mapping[str, Any],
    arm: str,
) -> tuple[list[dict[str, Any]], Mapping[str, Any], dict[str, str]]:
    if arm not in ARMS:
        raise RuntimeError(f"V2.42.91 unknown evaluator arm: {arm}")
    if arm == "control":
        return list(control["rows"]), control["summary"], dict(control["sources"])
    return (
        list(candidate["rows"]),
        candidate["summary"],
        {
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
            "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS),
            "run_summary_sha256": sha256(root / RUN_SUMMARY),
        },
    )


def validate_prepared_arm(
    root: Path,
    protocol: Mapping[str, Any],
    candidate: Mapping[str, Any],
    control: Mapping[str, Any],
    arm: str,
) -> dict[str, Any]:
    """Rebuild one evaluator join from frozen sources and validate it byte-for-byte."""

    rows, summary, source_hashes = _arm_forward_inputs(root, candidate, control, arm)
    expected_joined, expected_official, base = prepare_rollout(
        manifest_rows=read_jsonl(root / SOURCE_MANIFEST),
        mapping_rows=read_jsonl(root / MAPPING_PATH),
        shards=[("devval", list(control["ids"]), rows, dict(summary))],
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
        raise RuntimeError(f"V2.42.91 {arm} prepared evaluator rows drifted")
    expected = {
        **base,
        "phase": "post_candidate_exact64_freeze_fresh_full_arm_evaluator_prepare",
        "arm": arm,
        "protocol_sha256": sha256(root / FULL_PROTOCOL),
        "candidate_prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "candidate_exact64_before_control_mapping_gold_or_evaluator_open": True,
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
        raise RuntimeError(f"V2.42.91 {arm} prepare attestation drifted")
    return {"joined": joined, "official": official, "attestation": attestation}


def fixed_partitions() -> list[tuple[int, int]]:
    if SELECTED_COUNT != 64 or EVALUATOR_WORKERS_PER_ARM != 4:
        raise ValueError("V2.42.91 evaluator partition identity drifted")
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


def run_all_evaluators(
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
    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["evaluator_owner"],
        purpose=lease["evaluator_purpose"],
        path=root / lease["path"],
    ):
        with concurrent.futures.ThreadPoolExecutor(max_workers=TOTAL_EVALUATOR_WORKERS, thread_name_prefix="v24291-eval") as executor:
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
                raise RuntimeError(f"V2.42.91 {arm} evaluator worker {item['worker']} failed")
            run_root = root / RUNS[arm] / f"worker_{item['worker']:02d}"
            rows = read_jsonl(run_root / "official_eval_results.jsonl")
            validate_committed_eval_rows(rows, item["ids"])
            if len(rows) != 16:
                raise RuntimeError("V2.42.91 evaluator worker is not exact16")
            contract = validate_evaluator_contract(
                run_root / "run_config.json",
                expected_predictions_path=item["shard"],
                expected_predictions_sha256=sha256(item["shard"]),
                expected_selected_count=16,
            )
            for key in ("query_data_sha256", "answer_corpus_manifest_sha256", "evaluator_source_manifest_sha256", "judge", "recovery_policy"):
                if contract.get(key) != live.get(key):
                    raise RuntimeError(f"V2.42.91 {arm} evaluator {key} drifted")
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
            raise RuntimeError(f"V2.42.91 {arm} merged evaluator is not exact64")
        _write_jsonl_new(root / MERGED[arm], merged)
        attestation = {
            "artifact_version": 1,
            "role": "v24291_parallel_arm_evaluator_merge_attestation",
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


def validate_evaluator_merge(
    root: Path,
    protocol: Mapping[str, Any],
    prepared: Mapping[str, Any],
    arm: str,
) -> dict[str, Any]:
    """Validate the complete four-worker evaluator lineage for one arm."""

    if arm not in ARMS:
        raise RuntimeError(f"V2.42.91 unknown evaluator arm: {arm}")
    live = validate_live_evaluator_identity(root, protocol)
    partitions = fixed_partitions()
    expected_ids = [str(row["instance_id"]) for row in prepared["official"]]
    if len(expected_ids) != SELECTED_COUNT or len(set(expected_ids)) != SELECTED_COUNT:
        raise RuntimeError(f"V2.42.91 {arm} official prediction identity drifted")
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
        or attestation.get("role") != "v24291_parallel_arm_evaluator_merge_attestation"
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
        raise RuntimeError(f"V2.42.91 {arm} merge attestation identity drifted")
    parallel_wall = attestation.get("shared_both_arm_parallel_wall_seconds")
    if (
        isinstance(parallel_wall, bool)
        or not isinstance(parallel_wall, (int, float))
        or not math.isfinite(float(parallel_wall))
        or float(parallel_wall) < 0
    ):
        raise RuntimeError(f"V2.42.91 {arm} evaluator wall time drifted")

    merged_from_workers: list[dict[str, Any]] = []
    for index, (start, end) in enumerate(partitions):
        worker = index + 1
        report = reports[index]
        if not isinstance(report, Mapping):
            raise RuntimeError(f"V2.42.91 {arm} worker report is malformed")
        shard = root / RUNS[arm] / f"worker_{worker:02d}_predictions.jsonl"
        expected_shard = list(prepared["official"][start:end])
        if read_jsonl(shard) != expected_shard:
            raise RuntimeError(f"V2.42.91 {arm} evaluator worker {worker} prediction shard drifted")
        run_root = root / RUNS[arm] / f"worker_{worker:02d}"
        result_path = run_root / "official_eval_results.jsonl"
        config_path = run_root / "run_config.json"
        log_path = root / LOGS[arm] / f"worker_{worker:02d}.log"
        rows = read_jsonl(result_path)
        ids = expected_ids[start:end]
        validate_committed_eval_rows(rows, ids)
        if len(rows) != end - start:
            raise RuntimeError(f"V2.42.91 {arm} evaluator worker {worker} is not exact16")
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
                raise RuntimeError(f"V2.42.91 {arm} evaluator {key} drifted")
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
            raise RuntimeError(f"V2.42.91 {arm} evaluator worker {worker} provenance drifted")
        merged_from_workers.extend(rows)

    merged = read_jsonl(root / MERGED[arm])
    validate_committed_eval_rows(merged, expected_ids)
    if (
        len(merged) != SELECTED_COUNT
        or merged != merged_from_workers
        or attestation.get("merged_results_sha256") != sha256(root / MERGED[arm])
    ):
        raise RuntimeError(f"V2.42.91 {arm} merged evaluator rows drifted")
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
        raise RuntimeError(f"V2.42.91 {arm} conservative summary drifted")
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
        raise RuntimeError("V2.42.91 arm metric schema drifted")
    integer_counts = expected - set(QUALITY) - {
        "quality_composite", "score", "task_wall_sum_seconds",
    }
    if any(
        isinstance(value[name], bool)
        or not isinstance(value[name], int)
        or value[name] < 0
        for name in integer_counts
    ):
        raise RuntimeError("V2.42.91 arm count metric drifted")
    if (
        value["runtime_completed"] + value["runtime_failed"] != SELECTED_COUNT
        or value["evaluator_valid"] + value["evaluator_invalid_or_not_run"] != SELECTED_COUNT
        or value["model_generated_tables"] + value["fallback_tables"] != SELECTED_COUNT
        or value["whole_table_successes"] > value["evaluator_valid"]
    ):
        raise RuntimeError("V2.42.91 arm denominator drifted")
    for name in (*QUALITY, "quality_composite", "score"):
        number = value[name]
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(float(number)) or not 0 <= float(number) <= 1:
            raise RuntimeError("V2.42.91 arm quality metric drifted")
    wall = value["task_wall_sum_seconds"]
    if (
        isinstance(wall, bool)
        or not isinstance(wall, (int, float))
        or not math.isfinite(float(wall))
        or float(wall) < 0
    ):
        raise RuntimeError("V2.42.91 arm wall metric drifted")


def validate_candidate_health(value: Mapping[str, Any]) -> None:
    expected = {
        "retrieval_completed", "controller_stop", "controller_expand", "rescue_triggered",
        "rescue_fetches", "rescue_usable_pages", "hosted_search_requests_added_by_rescue",
        "cache_miss_count", "cache_serve_network_fetches", "hard_fetch_deadline_failures",
        "fetch_helper_failures",
    }
    if (
        set(value) != expected
        or any(isinstance(number, bool) or not isinstance(number, int) or number < 0 for number in value.values())
        or value["controller_stop"] + value["controller_expand"] != value["retrieval_completed"]
        or value["retrieval_completed"] > SELECTED_COUNT
        or value["rescue_triggered"] > value["controller_expand"]
        or value["hosted_search_requests_added_by_rescue"] != 0
    ):
        raise RuntimeError("V2.42.91 candidate health drifted")


def decision(
    protocol: Mapping[str, Any],
    control: Mapping[str, Any],
    candidate: Mapping[str, Any],
    health: Mapping[str, int],
) -> dict[str, Any]:
    validate_arm_metrics(control)
    validate_arm_metrics(candidate)
    validate_candidate_health(health)
    gate = protocol["decision_contract"]
    deltas = {
        name: candidate[name] - control[name]
        for name in (
            "quality_composite", "entity_acc", "f1_by_row", "f1_by_item", "column_f1",
            "whole_table_successes", "model_generated_tables",
        )
    }
    token_ratio = candidate["system_total_tokens"] / max(1, control["system_total_tokens"])
    wall_ratio = candidate["task_wall_sum_seconds"] / max(1e-9, control["task_wall_sum_seconds"])
    checks = {
        "quality_composite_delta": deltas["quality_composite"] >= gate["minimum_quality_composite_delta"],
        "entity_acc_delta": deltas["entity_acc"] >= gate["minimum_entity_acc_delta"],
        "f1_by_row_delta": deltas["f1_by_row"] >= gate["minimum_f1_by_row_delta"],
        "f1_by_item_delta": deltas["f1_by_item"] >= gate["minimum_f1_by_item_delta"],
        "column_f1_delta": deltas["column_f1"] >= gate["minimum_column_f1_delta"],
        "whole_table_success_delta": deltas["whole_table_successes"] >= gate["minimum_whole_table_success_delta"],
        "model_generated_table_delta": deltas["model_generated_tables"] >= gate["minimum_model_generated_table_delta"],
        "system_token_ratio": token_ratio <= gate["maximum_system_token_ratio"],
        "task_wall_sum_ratio": wall_ratio <= gate["maximum_task_wall_sum_ratio"],
        "candidate_evaluator_invalid_or_not_run": candidate["evaluator_invalid_or_not_run"] <= gate["maximum_candidate_evaluator_invalid_or_not_run"],
        "candidate_fallback_tables": candidate["fallback_tables"] <= gate["maximum_candidate_fallback_tables"],
        "rescue_triggered_tasks": health["rescue_triggered"] >= gate["minimum_rescue_triggered_tasks"],
        "hosted_search_requests_added_by_rescue": health["hosted_search_requests_added_by_rescue"] <= gate["maximum_hosted_search_requests_added_by_rescue"],
        "cache_misses": health["cache_miss_count"] <= gate["maximum_cache_misses"],
        "cache_serve_network_fetches": health["cache_serve_network_fetches"] <= gate["maximum_cache_serve_network_fetches"],
        "hard_fetch_deadline_failures": health["hard_fetch_deadline_failures"] <= gate["maximum_hard_fetch_deadline_failures"],
        "fetch_helper_failures": health["fetch_helper_failures"] <= gate["maximum_fetch_helper_failures"],
    }
    passed = all(checks.values())
    return {
        "status": "go" if passed else "no_go",
        "passed": passed,
        "checks": checks,
        "failed_checks": sorted(name for name, passed_ in checks.items() if not passed_),
        "candidate_minus_control": deltas,
        "system_token_ratio": token_ratio,
        "task_wall_sum_ratio": wall_ratio,
        "gate": dict(gate),
        "go_scope": "fresh_exact220_design_only_not_launch",
    }


def validate_final_result(root: Path, protocol: Mapping[str, Any], value: Mapping[str, Any]) -> None:
    expected_keys = {
        "artifact_version", "role", "protocol_id", "created_at_unix", "status",
        "selected_per_arm", "conservative_denominator_per_arm", "failure_as_zero",
        "candidate_exact64_before_control_or_evaluator_open",
        "both_arms_fully_evaluated_with_same_current_judge", "control", "candidate",
        "candidate_health", "decision", "efficiency", "provenance", "source_policy",
        "authorization", "claims", "result_payload_sha256",
    }
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    created = value.get("created_at_unix")
    if (
        set(value) != expected_keys
        or value.get("artifact_version") != 1
        or value.get("role") != "v24291_low_coverage_rescue_dev64_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("status") not in {"development_gate_go", "development_gate_no_go"}
        or isinstance(created, bool)
        or not isinstance(created, int)
        or created < 0
        or value.get("selected_per_arm") != SELECTED_COUNT
        or value.get("conservative_denominator_per_arm") != SELECTED_COUNT
        or value.get("failure_as_zero") is not True
        or value.get("candidate_exact64_before_control_or_evaluator_open") is not True
        or value.get("both_arms_fully_evaluated_with_same_current_judge") is not True
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.91 final result identity drifted")

    frozen_protocol = validate_protocol(root)
    if dict(protocol) != frozen_protocol:
        raise RuntimeError("V2.42.91 final result protocol input drifted")
    candidate = validate_candidate_barrier(root)
    control = load_control_after_candidate(root, frozen_protocol, candidate)
    live = validate_live_evaluator_identity(root, frozen_protocol)
    prepared = {
        arm: validate_prepared_arm(root, frozen_protocol, candidate, control, arm)
        for arm in ARMS
    }
    evaluated = {
        arm: validate_evaluator_merge(root, frozen_protocol, prepared[arm], arm)
        for arm in ARMS
    }
    arm_summaries = {
        arm: validate_arm_summary(root, prepared[arm], evaluated[arm], arm)
        for arm in ARMS
    }
    if (
        evaluated["control"]["attestation"]["shared_both_arm_parallel_wall_seconds"]
        != evaluated["candidate"]["attestation"]["shared_both_arm_parallel_wall_seconds"]
    ):
        raise RuntimeError("V2.42.91 both-arm evaluator wall identity drifted")

    control_projection = control["summary"]
    candidate_projection = candidate["summary"]
    expected_control = _arm_metrics(
        arm_summaries["control"],
        {
            "model_generated_tables": control_projection["model_generated_tables"],
            "fallback_tables": control_projection["fallback_tables"],
            "system_total_tokens": control_projection["system_total_tokens"],
            "task_wall_seconds_sum": control_projection["task_wall_seconds_sum"],
        },
    )
    expected_candidate = _arm_metrics(
        arm_summaries["candidate"],
        {
            "model_generated_tables": candidate_projection["model_generated_tables"],
            "fallback_tables": candidate_projection["fallback_tables"],
            "system_total_tokens": candidate_projection["system_total_tokens"],
            "task_wall_seconds_sum": candidate_projection["task_wall_seconds_sum"],
        },
    )
    expected_health = {
        **candidate_projection["rescue_totals"],
        "hard_fetch_deadline_failures": candidate_projection["hard_fetch_deadline_failures"],
        "fetch_helper_failures": candidate_projection["fetch_helper_failures"],
    }
    validate_candidate_health(expected_health)
    expected_decision = decision(
        frozen_protocol, expected_control, expected_candidate, expected_health
    )
    if (
        value.get("control") != expected_control
        or value.get("candidate") != expected_candidate
        or value.get("candidate_health") != expected_health
        or value.get("decision") != expected_decision
        or value.get("status")
        != ("development_gate_go" if expected_decision["passed"] else "development_gate_no_go")
    ):
        raise RuntimeError("V2.42.91 final metrics, health, status, or decision drifted")

    parallel_wall = evaluated["control"]["attestation"][
        "shared_both_arm_parallel_wall_seconds"
    ]
    expected_efficiency = {
        "candidate_forward_wall_seconds": candidate["forward"]["forward_wall_seconds"],
        "both_arm_evaluator_parallel_wall_seconds": parallel_wall,
        "evaluator_workers_total": TOTAL_EVALUATOR_WORKERS,
    }
    expected_provenance = {
        "protocol_sha256": sha256(root / FULL_PROTOCOL),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "candidate_prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "control_sources": control["sources"],
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
    if (
        value.get("efficiency") != expected_efficiency
        or value.get("provenance") != expected_provenance
    ):
        raise RuntimeError("V2.42.91 final efficiency or provenance drifted")
    if value.get("source_policy") != {
        "runtime_boundary": ["opaque_id", "question"],
        "control_mapping_gold_category_question_type_split_evaluator_score_read_by_candidate_forward": False,
        "candidate_prediction_freeze_before_control_or_evaluator_side_open": True,
        "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        "selective_retry_or_error_revaluation": False,
    }:
        raise RuntimeError("V2.42.91 final source policy drifted")
    if value.get("authorization") != {
        "fresh_exact220_design": expected_decision["passed"],
        "fresh_exact220_launch": False,
        "additional_dev64_or_avg4": False,
        "leaderboard_submission": False,
        "sota_claim": False,
    }:
        raise RuntimeError("V2.42.91 final authorization drifted")
    if value.get("claims") != {
        "development_gate_only": True,
        "independent_candidate_rollout_vs_frozen_control": True,
        "strict_shared_random_prefix_causal_ablation": False,
        "public_full220_result": False,
        "avg_at_4": False,
        "leaderboard_submitted": False,
        "sota": False,
    }:
        raise RuntimeError("V2.42.91 final claims drifted")


def finalize(
    root: Path = ROOT,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    root = root.resolve()
    if (root / FINAL_RESULT).exists() or (root / FINAL_RESULT).is_symlink():
        raise FileExistsError(root / FINAL_RESULT)
    candidate = validate_candidate_barrier(root)
    protocol = validate_protocol(root)
    control = load_control_after_candidate(root, protocol, candidate)
    live = validate_live_evaluator_identity(root, protocol)
    if (root / EVALUATOR_ROOT).exists() or (root / EVALUATOR_ROOT).is_symlink():
        raise RuntimeError("V2.42.91 evaluator surface exists; resume and rerun are forbidden")
    (root / EVALUATOR_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
    prepared = {
        arm: prepare_arm(root, protocol, candidate, control, arm)
        for arm in ARMS
    }
    evaluated = run_all_evaluators(root, protocol, prepared, command_runner=command_runner)
    arm_summaries: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        arm_summaries[arm] = summarize_rollout(prepared[arm]["joined"], evaluated["arms"][arm]["rows"], rollout_id=1)
        _new_json(root / SUMMARY[arm], arm_summaries[arm])
    control_projection = control["summary"]
    candidate_summary = candidate["summary"]
    control_metrics = _arm_metrics(
        arm_summaries["control"],
        {
            "model_generated_tables": control_projection["model_generated_tables"],
            "fallback_tables": control_projection["fallback_tables"],
            "system_total_tokens": control_projection["system_total_tokens"],
            "task_wall_seconds_sum": control_projection["task_wall_seconds_sum"],
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
        **candidate_summary["rescue_totals"],
        "hard_fetch_deadline_failures": candidate_summary["hard_fetch_deadline_failures"],
        "fetch_helper_failures": candidate_summary["fetch_helper_failures"],
    }
    gate = decision(protocol, control_metrics, candidate_metrics, health)
    result = {
        "artifact_version": 1,
        "role": "v24291_low_coverage_rescue_dev64_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "development_gate_go" if gate["passed"] else "development_gate_no_go",
        "selected_per_arm": SELECTED_COUNT,
        "conservative_denominator_per_arm": SELECTED_COUNT,
        "failure_as_zero": True,
        "candidate_exact64_before_control_or_evaluator_open": True,
        "both_arms_fully_evaluated_with_same_current_judge": True,
        "control": control_metrics,
        "candidate": candidate_metrics,
        "candidate_health": health,
        "decision": gate,
        "efficiency": {
            "candidate_forward_wall_seconds": candidate["forward"]["forward_wall_seconds"],
            "both_arm_evaluator_parallel_wall_seconds": evaluated["parallel_wall_seconds"],
            "evaluator_workers_total": TOTAL_EVALUATOR_WORKERS,
        },
        "provenance": {
            "protocol_sha256": sha256(root / FULL_PROTOCOL),
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "candidate_prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
            "control_sources": control["sources"],
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
            "control_mapping_gold_category_question_type_split_evaluator_score_read_by_candidate_forward": False,
            "candidate_prediction_freeze_before_control_or_evaluator_side_open": True,
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
            "independent_candidate_rollout_vs_frozen_control": True,
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
