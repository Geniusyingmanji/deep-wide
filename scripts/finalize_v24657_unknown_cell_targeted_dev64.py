#!/usr/bin/env python3
"""Post-freeze both-arm evaluator and decision for V2.46.57 dev64."""

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
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24657_forward_contract import (  # noqa: E402
    ARMS,
    EVALUATOR_GATE,
    EVALUATOR_LEASE_OWNER,
    EVALUATOR_LEASE_PURPOSE,
    EVALUATOR_ROOT,
    EVALUATOR_START,
    EXECUTION_START,
    FINAL_RESULT,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    LEASE_PATH,
    OUTPUT_ROOT,
    PAIR_SUMMARY,
    POSTAUDIT,
    PREDICTION_FREEZE,
    PROTOCOL,
    PROTOCOL_ID,
    RUNTIME_PREDICTIONS,
    RUNNER_MARKER,
    RUN_SUMMARY,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    selected_ids,
    sha256,
    validate_forward_contract,
)
from scripts.audit_v24187_phase_liveness import actual_python_script, process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.finalize_fullset_rollout import (  # noqa: E402
    _live_answer_corpus_manifest_sha256,
    _live_evaluator_source_manifest_sha256,
    prepare_rollout,
    read_jsonl,
    summarize_rollout,
    validate_evaluator_contract,
)
from scripts.run_official_eval_local import validate_committed_eval_rows  # noqa: E402
from scripts.run_v24657_unknown_cell_targeted_dev64 import (  # noqa: E402
    validate_forward_result,
    validate_pair_summary,
    validate_prediction_freeze,
)
from scripts.v24657_unknown_cell_targeted_dev64_control import (  # noqa: E402
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    DECISION_CONTRACT,
    EVALUATOR_WORKERS_PER_ARM,
    MAPPING_PATH,
    TOTAL_EVALUATOR_WORKERS,
    validate_protocol,
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
GATE_AUTHORIZATION = {
    "evaluator_start_design": True,
    "evaluator_execution": False,
    "additional_forward_or_rerun": False,
    "exact220": False,
}
START_AUTHORIZATION = {
    "one_postfreeze_both_arm_evaluator_execution": True,
    "additional_evaluator_retry_or_revaluation": False,
    "additional_forward_resume_retry_or_rerun": False,
    "exact220": False,
}
RESULT_SOURCE_POLICY = {
    "runtime_boundary": ["opaque_id", "question"],
    "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
    "both_arm_prediction_freezes_before_mapping_or_evaluator_open": True,
    "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
    "selective_retry_or_error_revaluation": False,
}
RESULT_CLAIMS = {
    "development_gate_only": True,
    "unknown_cell_targeted_quality_cost_pareto_gate": True,
    "entropy_or_credit_ablation": False,
    "public_full220_result": False,
    "avg_at_4": False,
    "leaderboard_submitted": False,
    "sota": False,
}


def _new_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def _write_jsonl_new(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows: handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush(); os.fsync(handle.fileno())


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value); seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20).stdout.strip()


def _tracked(root: Path, path: Path) -> bool:
    return subprocess.run(["git", "ls-files", "--error-unmatch", str(path)], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20, check=False).returncode == 0


def _process_present(marker: str) -> bool:
    for item in process_snapshot():
        argv = item.get("argv")
        script = actual_python_script(argv) if isinstance(argv, list) else None
        if isinstance(script, str) and script.endswith(marker): return True
    return False


def validate_forward_barrier(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    forward = read_object(root / FORWARD_RESULT)
    validate_forward_result(root, contract, forward)
    pair = validate_pair_summary(read_object(root / PAIR_SUMMARY))
    arms: dict[str, Any] = {}
    for arm in ARMS:
        freeze = read_object(root / PREDICTION_FREEZE[arm])
        rows = validate_prediction_freeze(root, contract, arm, freeze)
        summary = read_object(root / RUN_SUMMARY[arm])
        if (
            len(rows) != SELECTED_COUNT
            or freeze.get("both_arms_terminal_before_mapping_gold_or_evaluator_open") is not True
            or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        ):
            raise RuntimeError(f"V2.46.57 {arm} freeze barrier is incomplete")
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
        raise RuntimeError("V2.46.57 both-arm barrier is incomplete")
    return {"contract": contract, "forward": forward, "pair": pair, "ids": selected_ids(contract), "arms": arms}


def build_evaluator_gate(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve(); validate_protocol(root); barrier = validate_forward_barrier(root)
    head = _git(root, "rev-parse", "HEAD"); remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""; lease = lease_observation(root, Path("/proc"))
    findings: list[str] = []
    if any((root / path).exists() or (root / path).is_symlink() for path in (EVALUATOR_GATE, EVALUATOR_START, FINAL_RESULT, POSTAUDIT, EVALUATOR_ROOT)): findings.append("evaluator_surface_not_pristine")
    if head != remote: findings.append("forward_result_commit_not_pushed")
    if not clean: findings.append("worktree_not_clean_before_evaluator_gate")
    if not _tracked(root, FORWARD_RESULT): findings.append("forward_result_not_tracked")
    if lease.get("active") is not False: findings.append("shared_api_lease_active")
    if _process_present(RUNNER_MARKER): findings.append("forward_runner_still_active")
    if protected_watcher_snapshot() != barrier["contract"]["execution"]["protected_watchers"]: findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24657_unknown_cell_targeted_paired_dev64_evaluator_gate",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "evaluator_gate_go" if not findings else "evaluator_gate_no_go",
        "findings": findings,
        "passed": not findings,
        "selected_pair_tasks": SELECTED_COUNT,
        "prediction_rows_per_arm": {arm: SELECTED_COUNT for arm in ARMS},
        "failed_pair_tasks": barrier["pair"]["failed_pair_tasks"],
        "both_arm_prediction_freeze_sha256": {arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS},
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "pair_summary_sha256": sha256(root / PAIR_SUMMARY),
        "forward_result_base_commit": head,
        "target_main_at_gate": remote,
        "git_worktree_clean_before_gate": clean,
        "forward_result_tracked": _tracked(root, FORWARD_RESULT),
        "forward_runner_present": _process_present(RUNNER_MARKER),
        "shared_api_lease_active": lease.get("active"),
        "protected_watchers_unchanged": protected_watcher_snapshot() == barrier["contract"]["execution"]["protected_watchers"],
        "mapping_query_answer_gold_evaluator_score_opened_or_hashed": False,
        "official_evaluator_called": False,
        "authorization": {
            **GATE_AUTHORIZATION,
            "evaluator_start_design": not findings,
        },
        "protocol_sha256": sha256(root / PROTOCOL),
    }
    value["gate_payload_sha256"] = payload_sha256(value)
    return value


def validate_evaluator_gate(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = read_object(root / EVALUATOR_GATE)
    barrier = validate_forward_barrier(root)
    if (
        set(value)
        != {
            "artifact_version", "role", "protocol_id", "created_at_unix",
            "status", "findings", "passed", "selected_pair_tasks",
            "prediction_rows_per_arm", "failed_pair_tasks",
            "both_arm_prediction_freeze_sha256", "forward_result_sha256",
            "pair_summary_sha256", "forward_result_base_commit",
            "target_main_at_gate", "git_worktree_clean_before_gate",
            "forward_result_tracked", "forward_runner_present",
            "shared_api_lease_active", "protected_watchers_unchanged",
            "mapping_query_answer_gold_evaluator_score_opened_or_hashed",
            "official_evaluator_called", "authorization", "protocol_sha256",
            "gate_payload_sha256",
        }
        or value.get("artifact_version") != 1
        or value.get("role")
        != "v24657_unknown_cell_targeted_paired_dev64_evaluator_gate"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value.get("created_at_unix", -1) < 0
        or value.get("passed") is not True
        or value.get("findings") != []
        or value.get("status") != "evaluator_gate_go"
        or value.get("selected_pair_tasks") != SELECTED_COUNT
        or value.get("prediction_rows_per_arm")
        != {arm: SELECTED_COUNT for arm in ARMS}
        or value.get("failed_pair_tasks") != barrier["pair"]["failed_pair_tasks"]
        or value.get("both_arm_prediction_freeze_sha256")
        != {arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS}
        or value.get("forward_result_sha256") != sha256(root / FORWARD_RESULT)
        or value.get("pair_summary_sha256") != sha256(root / PAIR_SUMMARY)
        or value.get("forward_result_base_commit") != value.get("target_main_at_gate")
        or value.get("git_worktree_clean_before_gate") is not True
        or value.get("forward_result_tracked") is not True
        or value.get("forward_runner_present") is not False
        or value.get("shared_api_lease_active") is not False
        or value.get("protected_watchers_unchanged") is not True
        or value.get("mapping_query_answer_gold_evaluator_score_opened_or_hashed") is not False
        or value.get("official_evaluator_called") is not False
        or value.get("authorization") != GATE_AUTHORIZATION
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or not _sealed(value, "gate_payload_sha256")
    ):
        raise RuntimeError("V2.46.57 evaluator gate drifted")
    validate_protocol(root)
    return value


def build_evaluator_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve(); validate_protocol(root); gate = validate_evaluator_gate(root)
    if any((root / path).exists() or (root / path).is_symlink() for path in (EVALUATOR_START, FINAL_RESULT, POSTAUDIT, EVALUATOR_ROOT)):
        raise RuntimeError("V2.46.57 evaluator execution surface is not pristine")
    head = _git(root, "rev-parse", "HEAD"); remote = _git(root, "rev-parse", "target/main")
    clean = _git(root, "status", "--porcelain") == ""; lease = lease_observation(root, Path("/proc"))
    tracked = _tracked(root, EVALUATOR_GATE); findings: list[str] = []
    if head != remote: findings.append("evaluator_gate_commit_not_pushed")
    if not clean: findings.append("worktree_not_clean")
    if not tracked: findings.append("evaluator_gate_not_tracked")
    if lease.get("active") is not False: findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24657_unknown_cell_targeted_paired_dev64_evaluator_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "evaluator_ready" if not findings else "evaluator_rejected",
        "findings": findings,
        "execution_authorized": not findings,
        "gate_base_commit": head,
        "target_main_at_start": remote,
        "git_worktree_clean_before_start": clean,
        "evaluator_gate_tracked": tracked,
        "evaluator_gate_sha256": sha256(root / EVALUATOR_GATE),
        "protocol_sha256": sha256(root / PROTOCOL),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "both_arm_prediction_freeze_sha256": {arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS},
        "evaluator_workers_per_arm": EVALUATOR_WORKERS_PER_ARM,
        "total_evaluator_workers": TOTAL_EVALUATOR_WORKERS,
        "shared_api_lease_active_before_start": lease.get("active"),
        "mapping_query_answer_gold_evaluator_score_opened_or_hashed_before_start": False,
        "official_evaluator_called_before_start": False,
        "additional_forward_resume_retry_or_rerun": False,
        "authorization": dict(START_AUTHORIZATION),
    }
    value["start_payload_sha256"] = payload_sha256(value)
    if findings: raise RuntimeError("V2.46.57 evaluator start failed: " + ",".join(findings))
    return value


def validate_evaluator_start(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = read_object(root / EVALUATOR_START)
    if (
        set(value)
        != {
            "artifact_version", "role", "protocol_id", "created_at_unix",
            "status", "findings", "execution_authorized", "gate_base_commit",
            "target_main_at_start", "git_worktree_clean_before_start",
            "evaluator_gate_tracked", "evaluator_gate_sha256",
            "protocol_sha256", "forward_result_sha256",
            "both_arm_prediction_freeze_sha256", "evaluator_workers_per_arm",
            "total_evaluator_workers", "shared_api_lease_active_before_start",
            "mapping_query_answer_gold_evaluator_score_opened_or_hashed_before_start",
            "official_evaluator_called_before_start",
            "additional_forward_resume_retry_or_rerun", "authorization",
            "start_payload_sha256",
        }
        or value.get("artifact_version") != 1
        or value.get("role")
        != "v24657_unknown_cell_targeted_paired_dev64_evaluator_start"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value.get("created_at_unix", -1) < 0
        or value.get("status") != "evaluator_ready"
        or value.get("findings") != []
        or value.get("execution_authorized") is not True
        or value.get("gate_base_commit") != value.get("target_main_at_start")
        or value.get("git_worktree_clean_before_start") is not True
        or value.get("evaluator_gate_tracked") is not True
        or value.get("evaluator_gate_sha256") != sha256(root / EVALUATOR_GATE)
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("forward_result_sha256") != sha256(root / FORWARD_RESULT)
        or value.get("both_arm_prediction_freeze_sha256")
        != {arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS}
        or value.get("evaluator_workers_per_arm") != EVALUATOR_WORKERS_PER_ARM
        or value.get("total_evaluator_workers") != TOTAL_EVALUATOR_WORKERS
        or value.get("shared_api_lease_active_before_start") is not False
        or value.get("mapping_query_answer_gold_evaluator_score_opened_or_hashed_before_start") is not False
        or value.get("official_evaluator_called_before_start") is not False
        or value.get("additional_forward_resume_retry_or_rerun") is not False
        or value.get("authorization") != START_AUTHORIZATION
        or not _sealed(value, "start_payload_sha256")
    ):
        raise RuntimeError("V2.46.57 evaluator start drifted")
    validate_protocol(root)
    validate_evaluator_gate(root)
    return value


def validate_live_evaluator_identity(root: Path, protocol: Mapping[str, Any]) -> dict[str, Any]:
    evaluator = protocol["evaluator_contract"]
    mapping = root / evaluator["mapping"]["path"]
    query_path = root / evaluator["query_data"]["path"]
    answer_root = root / evaluator["answer_corpus"]["root"]
    if (
        mapping.is_symlink() or not mapping.is_file() or sha256(mapping) != evaluator["mapping"]["sha256"]
        or query_path.is_symlink() or not query_path.is_file() or sha256(query_path) != evaluator["query_data"]["sha256"]
        or answer_root.is_symlink() or not answer_root.is_dir()
        or _live_answer_corpus_manifest_sha256(answer_root) != evaluator["answer_corpus"]["manifest_sha256"]
        or _live_evaluator_source_manifest_sha256() != evaluator["evaluator_source"]["manifest_sha256"]
    ):
        raise RuntimeError("V2.46.57 live evaluator identity drifted")
    return {
        "mapping_sha256": evaluator["mapping"]["sha256"],
        "query_data_sha256": evaluator["query_data"]["sha256"],
        "answer_corpus_manifest_sha256": evaluator["answer_corpus"]["manifest_sha256"],
        "evaluator_source_manifest_sha256": evaluator["evaluator_source"]["manifest_sha256"],
        "judge": dict(evaluator["judge"]),
        "recovery_policy": dict(evaluator["recovery_policy"]),
    }


def prepare_arm(root: Path, protocol: Mapping[str, Any], barrier: Mapping[str, Any], arm: str) -> dict[str, Any]:
    state = barrier["arms"][arm]
    joined, official, base = prepare_rollout(
        manifest_rows=read_jsonl(root / SOURCE_MANIFEST),
        mapping_rows=read_jsonl(root / MAPPING_PATH),
        shards=[("devval", barrier["ids"], state["rows"], state["summary"])],
        rollout_id=1,
    )
    completed = sum(row["status"] == "completed" for row in state["rows"])
    if len(joined) != SELECTED_COUNT or len(official) != completed:
        raise RuntimeError(f"V2.46.57 {arm} evaluator prepare is not terminal64")
    (root / ARM_ROOTS[arm]).mkdir(mode=0o700, parents=True, exist_ok=False)
    _write_jsonl_new(root / JOINED[arm], joined); _write_jsonl_new(root / OFFICIAL[arm], official)
    value = {
        **base,
        "phase": "post_both_arm_exact64_freeze_unknown_cell_targeted_evaluator_prepare",
        "arm": arm,
        "protocol_sha256": sha256(root / PROTOCOL),
        "evaluator_start_sha256": sha256(root / EVALUATOR_START),
        "both_arm_prediction_freeze_sha256": {name: sha256(root / PREDICTION_FREEZE[name]) for name in ARMS},
        "both_arms_exact64_before_mapping_gold_or_evaluator_open": True,
        "selective_changed_prediction_evaluation": False,
        "old_evaluator_rows_reused": False,
        "mapping_sha256": sha256(root / MAPPING_PATH),
        "manifest_sha256": sha256(root / SOURCE_MANIFEST),
        "source_hashes": state["sources"],
        "terminal_outcomes_sha256": sha256(root / JOINED[arm]),
        "official_predictions_sha256": sha256(root / OFFICIAL[arm]),
    }
    value["prepare_payload_sha256"] = payload_sha256(value); _new_json(root / PREPARE[arm], value)
    return {"joined": joined, "official": official, "attestation": value}


def build_evaluation_plan(
    barrier: Mapping[str, Any],
    prepared: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    baseline_rows = barrier["arms"]["baseline"]["rows"]
    candidate_rows = barrier["arms"]["candidate"]["rows"]
    if len(baseline_rows) != SELECTED_COUNT or len(candidate_rows) != SELECTED_COUNT:
        raise RuntimeError("V2.46.57 evaluation-plan row count drifted")
    baseline_official = list(prepared["baseline"]["official"])
    candidate_official = list(prepared["candidate"]["official"])
    baseline_completed = [row for row in baseline_rows if row["status"] == "completed"]
    candidate_completed = [row for row in candidate_rows if row["status"] == "completed"]
    if (
        len(baseline_official) != len(baseline_completed)
        or len(candidate_official) != len(candidate_completed)
    ):
        raise RuntimeError("V2.46.57 evaluator-plan official coverage drifted")
    baseline_by_opaque = {
        str(row["opaque_id"]): row for row in baseline_completed
    }
    baseline_official_by_opaque = {
        str(row["opaque_id"]): official
        for row, official in zip(baseline_completed, baseline_official, strict=True)
    }
    candidate_changed: list[dict[str, Any]] = []
    identity_instance_ids: list[str] = []
    changed_instance_ids: list[str] = []
    for row, official in zip(candidate_completed, candidate_official, strict=True):
        opaque_id = str(row["opaque_id"])
        baseline = baseline_by_opaque.get(opaque_id)
        baseline_official_row = baseline_official_by_opaque.get(opaque_id)
        if baseline is None or baseline_official_row is None:
            raise RuntimeError("V2.46.57 paired evaluator task identity drifted")
        if baseline_official_row["instance_id"] != official["instance_id"]:
            raise RuntimeError("V2.46.57 paired evaluator instance identity drifted")
        if baseline["prediction_sha256"] == row["prediction_sha256"]:
            identity_instance_ids.append(str(official["instance_id"]))
        else:
            candidate_changed.append(official)
            changed_instance_ids.append(str(official["instance_id"]))
    if len(identity_instance_ids) + len(changed_instance_ids) != len(candidate_official):
        raise RuntimeError("V2.46.57 evaluator pairing partition drifted")
    value = {
        "baseline_evaluate": baseline_official,
        "candidate_evaluate": candidate_changed,
        "candidate_full": candidate_official,
        "identity_instance_ids": identity_instance_ids,
        "changed_instance_ids": changed_instance_ids,
        "routing_keys": ["instance_id", "prediction_sha256"],
        "mapping_gold_category_question_type_split_score_or_reward_used_for_routing": False,
    }
    return value


def fixed_partitions(selected: int) -> list[tuple[int, int]]:
    if isinstance(selected, bool) or not isinstance(selected, int) or selected < 0:
        raise ValueError("V2.46.57 evaluator selected count drifted")
    if selected == 0:
        return []
    workers = min(EVALUATOR_WORKERS_PER_ARM, selected)
    base, remainder = divmod(selected, workers)
    output: list[tuple[int, int]] = []
    start = 0
    for index in range(workers):
        size = base + (1 if index < remainder else 0)
        output.append((start, start + size))
        start += size
    if start != selected:
        raise AssertionError("V2.46.57 evaluator partition drifted")
    return output


def evaluator_command(root: Path, protocol: Mapping[str, Any], arm: str, worker: int, predictions: Path) -> list[str]:
    evaluator = protocol["evaluator_contract"]; judge = evaluator["judge"]
    return [
        str(root / ".venv-eval/bin/python"), "-I", "-B",
        str(root / "scripts/run_official_eval_local.py"),
        "--predictions", str(predictions),
        "--out-dir", str(root / RUNS[arm] / f"worker_{worker:02d}"),
        "--query-path", str(root / evaluator["query_data"]["path"]),
        "--answer-root", str(root / evaluator["answer_corpus"]["root"]),
        "--proxy-url", judge["proxy_url"], "--model", judge["model"],
        "--reasoning-effort", judge["reasoning_effort"],
        "--judge-max-output-tokens", str(judge["max_output_tokens"]),
        "--judge-timeout", str(judge["timeout_seconds"]),
        "--judge-max-retries", str(judge["max_retries"]),
    ]


def _run_worker(arm: str, worker: int, command: Sequence[str], root: Path, runner: Callable[..., subprocess.CompletedProcess[Any]]) -> dict[str, Any]:
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1"})
    log = root / LOGS[arm] / f"worker_{worker:02d}.log"; log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        with log.open("xb") as handle:
            completed = runner(list(command), cwd=root, env=environment, stdout=handle, stderr=subprocess.STDOUT, check=False)
            handle.flush(); os.fsync(handle.fileno())
        returncode = int(completed.returncode); exception = False
    except Exception:
        returncode = -1; exception = True
        if not log.exists(): log.write_bytes(b"")
    return {"arm": arm, "worker": worker, "returncode": returncode, "runner_exception": exception, "wall_seconds": round(max(0.0, time.monotonic() - started), 6), "log_sha256": sha256(log)}


def _worker_error_rows(ids: Sequence[str]) -> list[dict[str, Any]]:
    return [{"instance_id": value, "error": "EvaluatorWorkerFailure", "elapsed_seconds": 0.0} for value in ids]


def run_all_evaluators(root: Path, protocol: Mapping[str, Any], prepared: Mapping[str, Mapping[str, Any]], *, command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run) -> dict[str, Any]:
    plan = build_evaluation_plan(
        validate_forward_barrier(root), prepared
    )
    evaluation_rows = {
        "baseline": plan["baseline_evaluate"],
        "candidate": plan["candidate_evaluate"],
    }
    commands: list[dict[str, Any]] = []
    for arm in ARMS:
        (root / RUNS[arm]).mkdir(mode=0o700, parents=True, exist_ok=False)
        for worker, (start, end) in enumerate(
            fixed_partitions(len(evaluation_rows[arm])), start=1
        ):
            rows = evaluation_rows[arm][start:end]
            shard = root / RUNS[arm] / f"worker_{worker:02d}_predictions.jsonl"; _write_jsonl_new(shard, rows)
            commands.append({"arm": arm, "worker": worker, "start": start, "end": end, "ids": [str(row["instance_id"]) for row in rows], "shard": shard, "command": evaluator_command(root, protocol, arm, worker, shard)})
    started = time.monotonic(); reports: dict[tuple[str, int], dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=TOTAL_EVALUATOR_WORKERS, thread_name_prefix="v24657-eval") as executor:
        futures = {executor.submit(_run_worker, item["arm"], item["worker"], item["command"], root, command_runner): (item["arm"], item["worker"]) for item in commands}
        for future in concurrent.futures.as_completed(futures):
            report = future.result(); reports[(report["arm"], report["worker"])] = report
    wall = round(max(0.0, time.monotonic() - started), 6); output: dict[str, Any] = {"parallel_wall_seconds": wall, "arms": {}}
    live = validate_live_evaluator_identity(root, protocol)
    evaluated_rows: dict[str, list[dict[str, Any]]] = {}
    reports_by_arm: dict[str, list[dict[str, Any]]] = {}
    for arm in ARMS:
        merged: list[dict[str, Any]] = []; worker_reports: list[dict[str, Any]] = []
        for item in [entry for entry in commands if entry["arm"] == arm]:
            report = reports[(arm, item["worker"])]; run_root = root / RUNS[arm] / f"worker_{item['worker']:02d}"
            result_path = run_root / "official_eval_results.jsonl"; config_path = run_root / "run_config.json"
            catastrophic = report["returncode"] != 0; contract_sha = results_sha = config_sha = None
            if not catastrophic:
                try:
                    rows = read_jsonl(result_path); validate_committed_eval_rows(rows, item["ids"])
                    if len(rows) != len(item["ids"]): raise RuntimeError("incomplete evaluator worker")
                    contract = validate_evaluator_contract(config_path, expected_predictions_path=item["shard"], expected_predictions_sha256=sha256(item["shard"]), expected_selected_count=len(item["ids"]))
                    for key in ("query_data_sha256", "answer_corpus_manifest_sha256", "evaluator_source_manifest_sha256", "judge", "recovery_policy"):
                        if contract.get(key) != live.get(key): raise RuntimeError("evaluator identity drifted")
                    contract_sha = contract["run_contract_sha256"]; results_sha = sha256(result_path); config_sha = sha256(config_path)
                except Exception:
                    catastrophic = True
            if catastrophic: rows = _worker_error_rows(item["ids"])
            validate_committed_eval_rows(rows, item["ids"]); merged.extend(rows)
            worker_reports.append({**report, "start": item["start"], "end": item["end"], "selected": len(item["ids"]), "prediction_shard_sha256": sha256(item["shard"]), "catastrophic_worker_failure_as_zero": catastrophic, "results_sha256": results_sha, "run_config_sha256": config_sha, "run_contract_sha256": contract_sha})
        expected = [str(row["instance_id"]) for row in evaluation_rows[arm]]
        validate_committed_eval_rows(merged, expected)
        if len(merged) != len(expected):
            raise RuntimeError("V2.46.57 evaluator worker merge coverage drifted")
        evaluated_rows[arm] = merged
        reports_by_arm[arm] = worker_reports

    baseline_by_instance = {
        str(row["instance_id"]): row for row in evaluated_rows["baseline"]
    }
    candidate_changed_by_instance = {
        str(row["instance_id"]): row for row in evaluated_rows["candidate"]
    }
    identity = set(plan["identity_instance_ids"])
    changed = set(plan["changed_instance_ids"])
    candidate_full: list[dict[str, Any]] = []
    for official in plan["candidate_full"]:
        instance_id = str(official["instance_id"])
        if instance_id in identity:
            source = baseline_by_instance.get(instance_id)
        elif instance_id in changed:
            source = candidate_changed_by_instance.get(instance_id)
        else:
            source = None
        if source is None:
            raise RuntimeError("V2.46.57 paired evaluator reuse coverage drifted")
        candidate_full.append(dict(source))
    final_rows = {
        "baseline": evaluated_rows["baseline"],
        "candidate": candidate_full,
    }
    for arm in ARMS:
        expected_full = [str(row["instance_id"]) for row in prepared[arm]["official"]]
        validate_committed_eval_rows(final_rows[arm], expected_full)
        if len(final_rows[arm]) != len(expected_full):
            raise RuntimeError("V2.46.57 final evaluator merge coverage drifted")
        _write_jsonl_new(root / MERGED[arm], final_rows[arm])
        reports = reports_by_arm[arm]
        attestation = {
            "artifact_version": 1,
            "role": "v24657_paired_evaluator_merge_attestation",
            "arm": arm,
            "selected_runtime_tasks": SELECTED_COUNT,
            "completed_predictions": len(expected_full),
            "provider_evaluated_predictions": len(evaluation_rows[arm]),
            "identity_rows_reused_from_baseline": (
                len(plan["identity_instance_ids"]) if arm == "candidate" else 0
            ),
            "changed_candidate_predictions": (
                len(plan["changed_instance_ids"]) if arm == "candidate" else 0
            ),
            "workers_used": len(reports),
            "worker_reports": reports,
            "routing_keys": list(plan["routing_keys"]),
            "mapping_gold_category_question_type_split_score_or_reward_used_for_routing": False,
            "shared_both_arm_parallel_wall_seconds": wall,
            "merged_results_sha256": sha256(root / MERGED[arm]),
            "catastrophic_worker_failure_count": sum(
                item["catastrophic_worker_failure_as_zero"] for item in reports
            ),
            "all_completed_predictions_evaluated_or_identity_reused_exactly_once": True,
            "selective_retry_or_error_revaluation": False,
        }
        attestation["merge_payload_sha256"] = payload_sha256(attestation)
        _new_json(root / MERGE[arm], attestation)
        output["arms"][arm] = {"rows": final_rows[arm], "attestation": attestation}
    output["pairing"] = {
        "identity_instance_count": len(plan["identity_instance_ids"]),
        "changed_candidate_instance_count": len(plan["changed_instance_ids"]),
        "routing_keys": list(plan["routing_keys"]),
        "mapping_gold_category_question_type_split_score_or_reward_used_for_routing": False,
    }
    return output


def _arm_metrics(summary: Mapping[str, Any]) -> dict[str, Any]:
    group = summary["groups"]["dev_validation_64"]; conservative = group["conservative_all_selected"]
    return {
        "runtime_completed": int(group["runtime_completed"]),
        "runtime_failed": int(group["runtime_failed"]),
        "fallback_tables": int(group["runtime_failed"]),
        "evaluator_valid": int(group["evaluator_valid"]),
        "evaluator_invalid_or_not_run": int(group["evaluator_invalid_or_not_run"]),
        "whole_table_successes": sum(row["evaluator_valid"] and float(row["metrics"]["score"]) > 0 for row in summary["per_task"]),
        **{name: float(conservative[name]) for name in QUALITY},
        "quality_composite": sum(float(conservative[name]) for name in QUALITY) / len(QUALITY),
        "score": float(conservative["score"]),
    }


def _validate_arm_metrics(value: Mapping[str, Any]) -> None:
    expected = {
        "runtime_completed",
        "runtime_failed",
        "fallback_tables",
        "evaluator_valid",
        "evaluator_invalid_or_not_run",
        "whole_table_successes",
        *QUALITY,
        "quality_composite",
        "score",
    }
    count_fields = {
        "runtime_completed",
        "runtime_failed",
        "fallback_tables",
        "evaluator_valid",
        "evaluator_invalid_or_not_run",
        "whole_table_successes",
    }
    if set(value) != expected or any(
        isinstance(value.get(name), bool)
        or not isinstance(value.get(name), int)
        or value.get(name, -1) < 0
        for name in count_fields
    ):
        raise RuntimeError("V2.46.57 final arm metric schema drifted")
    if (
        value["runtime_completed"] + value["runtime_failed"] != SELECTED_COUNT
        or value["fallback_tables"] != value["runtime_failed"]
        or value["evaluator_valid"] + value["evaluator_invalid_or_not_run"]
        != SELECTED_COUNT
        or value["whole_table_successes"] > value["evaluator_valid"]
    ):
        raise RuntimeError("V2.46.57 final arm metric denominator drifted")
    for name in (*QUALITY, "quality_composite", "score"):
        number = value.get(name)
        if (
            isinstance(number, bool)
            or not isinstance(number, (int, float))
            or not math.isfinite(float(number))
            or not 0.0 <= float(number) <= 1.0
        ):
            raise RuntimeError("V2.46.57 final arm quality metric drifted")


def _stored_final_inputs(root: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    evaluated: dict[str, Any] = {"arms": {}}
    summaries: dict[str, dict[str, Any]] = {}
    walls: set[float] = set()
    for arm in ARMS:
        rows = read_jsonl(root / MERGED[arm])
        expected = [
            str(row["instance_id"])
            for row in read_jsonl(root / OFFICIAL[arm])
        ]
        validate_committed_eval_rows(rows, expected)
        if len(rows) != len(expected):
            raise RuntimeError("V2.46.57 stored evaluator coverage drifted")
        merge = read_object(root / MERGE[arm])
        if (
            merge.get("artifact_version") != 1
            or merge.get("role") != "v24657_paired_evaluator_merge_attestation"
            or merge.get("arm") != arm
            or merge.get("selected_runtime_tasks") != SELECTED_COUNT
            or merge.get("completed_predictions") != len(expected)
            or merge.get("merged_results_sha256") != sha256(root / MERGED[arm])
            or merge.get(
                "mapping_gold_category_question_type_split_score_or_reward_used_for_routing"
            )
            is not False
            or merge.get(
                "all_completed_predictions_evaluated_or_identity_reused_exactly_once"
            )
            is not True
            or merge.get("selective_retry_or_error_revaluation") is not False
            or not _sealed(merge, "merge_payload_sha256")
        ):
            raise RuntimeError("V2.46.57 evaluator merge attestation drifted")
        wall = merge.get("shared_both_arm_parallel_wall_seconds")
        if (
            isinstance(wall, bool)
            or not isinstance(wall, (int, float))
            or not math.isfinite(float(wall))
            or float(wall) < 0
        ):
            raise RuntimeError("V2.46.57 evaluator wall drifted")
        walls.add(float(wall))
        joined = read_jsonl(root / JOINED[arm])
        expected_summary = summarize_rollout(joined, rows, rollout_id=1)
        stored_summary = read_object(root / SUMMARY[arm])
        if stored_summary != expected_summary:
            raise RuntimeError("V2.46.57 conservative summary drifted")
        summaries[arm] = stored_summary
        evaluated["arms"][arm] = {"rows": rows, "attestation": merge}
    if len(walls) != 1:
        raise RuntimeError("V2.46.57 both-arm evaluator wall drifted")
    evaluated["parallel_wall_seconds"] = walls.pop()
    return evaluated, summaries


def paired_uncertainty(summaries: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    by_arm: dict[str, dict[str, Mapping[str, Any]]] = {}; order: list[str] = []
    for arm in ARMS:
        rows = summaries[arm]["per_task"]; mapping = {str(row["opaque_id"]): row for row in rows}
        if len(rows) != SELECTED_COUNT or len(mapping) != SELECTED_COUNT: raise RuntimeError("V2.46.57 uncertainty identity drifted")
        by_arm[arm] = mapping
        if arm == "baseline": order = [str(row["opaque_id"]) for row in rows]
    if set(by_arm["candidate"]) != set(order): raise RuntimeError("V2.46.57 uncertainty task mismatch")
    deltas = [sum(float(by_arm["candidate"][opaque]["metrics"][name]) - float(by_arm["baseline"][opaque]["metrics"][name]) for name in QUALITY) / len(QUALITY) for opaque in order]
    generator = random.Random(BOOTSTRAP_SEED)
    estimates = sorted(sum(deltas[generator.randrange(len(deltas))] for _ in deltas) / len(deltas) for _ in range(BOOTSTRAP_RESAMPLES))
    interval = [estimates[249], estimates[9749]]
    return {"task_count": SELECTED_COUNT, "bootstrap_unit": "paired_frozen_task", "seed": BOOTSTRAP_SEED, "resamples": BOOTSTRAP_RESAMPLES, "estimand": "mean paired failure-as-zero composite delta on fresh dev64", "mean": sum(deltas) / len(deltas), "median": statistics.median(deltas), "positive": sum(value > 0 for value in deltas), "zero": sum(value == 0 for value in deltas), "negative": sum(value < 0 for value in deltas), "minimum": min(deltas), "maximum": max(deltas), "percentile_95_interval": interval, "interval_width": interval[1] - interval[0], "fixed_denominator_failure_as_zero": True, "predictions_frozen_before_evaluator": True, "future_population_or_sota_inference": False}


def decision(protocol: Mapping[str, Any], metrics: Mapping[str, Mapping[str, Any]], uncertainty: Mapping[str, Any], pair: Mapping[str, Any]) -> dict[str, Any]:
    gate = protocol["decision_contract"]; baseline = metrics["baseline"]; candidate = metrics["candidate"]
    delta = {name: candidate[name] - baseline[name] for name in (*QUALITY, "quality_composite", "whole_table_successes")}
    checks = {
        "quality_composite_delta": delta["quality_composite"] >= gate["minimum_quality_composite_delta"],
        "entity_acc_delta": delta["entity_acc"] >= gate["minimum_entity_acc_delta"],
        "f1_by_row_delta": delta["f1_by_row"] >= gate["minimum_f1_by_row_delta"],
        "f1_by_item_delta": delta["f1_by_item"] >= gate["minimum_f1_by_item_delta"],
        "column_f1_delta": delta["column_f1"] >= gate["minimum_column_f1_delta"],
        "whole_table_success_delta": delta["whole_table_successes"] >= gate["minimum_whole_table_success_delta"],
        "candidate_evaluator_health": candidate["evaluator_invalid_or_not_run"] <= gate["maximum_candidate_evaluator_invalid_or_not_run"],
        "candidate_minus_baseline_evaluator_invalid": candidate["evaluator_invalid_or_not_run"] - baseline["evaluator_invalid_or_not_run"] <= gate["maximum_candidate_minus_baseline_evaluator_invalid"],
        "candidate_minus_baseline_runtime_failed": candidate["runtime_failed"] - baseline["runtime_failed"] <= gate["maximum_candidate_minus_baseline_runtime_failed"],
        "candidate_minus_baseline_fallback_tables": candidate["fallback_tables"] - baseline["fallback_tables"] <= gate["maximum_candidate_minus_baseline_fallback_tables"],
        "failed_pair_tasks": pair["failed_pair_tasks"] <= gate["maximum_failed_pair_tasks"],
        "effect_accounting_complete_tasks": pair["effect_accounting_complete_tasks"] >= gate["minimum_effect_accounting_complete_tasks"],
        "shared_generic_prefix_tasks": pair["shared_generic_prefix_tasks"] >= gate["minimum_shared_generic_prefix_tasks"],
        "baseline_precedes_targeted_search_tasks": pair["baseline_precedes_targeted_search_tasks"] >= gate["minimum_baseline_precedes_targeted_search_tasks"],
        "selected_unknown_target_tasks": pair["selected_unknown_target_tasks"] >= gate["minimum_selected_unknown_target_tasks"],
        "deterministic_support_tasks": pair["deterministic_support_tasks"] >= gate["minimum_eligible_support_tasks"],
        "revision_model_admitted_tasks": pair["revision_model_admitted_tasks"] >= gate["minimum_revision_model_admitted_tasks"],
        "revision_gate_tasks": pair["revision_gate_tasks"] >= gate["minimum_revision_gate_tasks"],
        "changed_candidate_tasks": pair["changed_candidate_tasks"] >= gate["minimum_changed_candidate_tasks"],
        "admitted_cell_changes": pair["admitted_cell_changes"] >= gate["minimum_admitted_cell_changes"],
        "zero_entropy_task_credit": pair["entropy_task_credit_nats"] == gate["required_credited_conditional_entropy_reduction_nats"],
        "repeated_upstream_effects": pair["repeated_upstream_effects"] == gate["required_repeated_upstream_effects"],
        "slot_timeouts": pair["slot_timeouts"] <= gate["maximum_slot_timeouts"],
        "provider_deadline_failures": pair["provider_deadline_failures"] <= gate["maximum_provider_deadline_failures"],
        "hard_fetch_deadline_failures": pair["hard_fetch_deadline_failures"] <= gate["maximum_hard_fetch_deadline_failures"],
        "fetch_helper_failures": pair["fetch_helper_failures"] <= gate["maximum_fetch_helper_failures"],
        "hosted_search_deadline_failures": pair["hosted_search_deadline_failures"] <= gate["maximum_hosted_search_deadline_failures"],
        "fetch_deadline_rejections": pair["fetch_deadline_rejections"] <= gate["maximum_fetch_deadline_rejections"],
        "deadline_exhausted_tasks": pair["deadline_exhausted_tasks"] <= gate["maximum_deadline_exhausted_tasks"],
        "paired_bootstrap_lower_bound": uncertainty["percentile_95_interval"][0] >= gate["minimum_paired_bootstrap_95_lower_bound"],
        "paired_bootstrap_interval_width": uncertainty["interval_width"] <= gate["maximum_paired_bootstrap_95_interval_width"],
        "paired_median_delta": uncertainty["median"] >= gate["minimum_paired_median_delta"],
    }
    return {"status": "go" if all(checks.values()) else "no_go", "passed": all(checks.values()), "checks": checks, "failed_checks": sorted(name for name, passed in checks.items() if not passed), "candidate_minus_baseline": delta, "paired_uncertainty": dict(uncertainty), "gate": dict(gate), "go_scope": "fresh_exact220_design_only_not_launch"}


def build_final_result(root: Path, protocol: Mapping[str, Any], barrier: Mapping[str, Any], evaluated: Mapping[str, Any], summaries: Mapping[str, Mapping[str, Any]], live: Mapping[str, Any]) -> dict[str, Any]:
    metrics = {arm: _arm_metrics(summaries[arm]) for arm in ARMS}; uncertainty = paired_uncertainty(summaries); gate = decision(protocol, metrics, uncertainty, barrier["pair"])
    value = {
        "artifact_version": 1,
        "role": "v24657_unknown_cell_targeted_paired_dev64_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "development_gate_go" if gate["passed"] else "development_gate_no_go",
        "selected_per_arm": SELECTED_COUNT,
        "conservative_denominator_per_arm": SELECTED_COUNT,
        "failure_as_zero": True,
        "both_arms_exact64_before_mapping_or_evaluator_open": True,
        "both_arms_fully_evaluated_with_same_current_judge": True,
        "baseline": metrics["baseline"], "candidate": metrics["candidate"],
        "mechanism": dict(barrier["pair"]),
        "paired_uncertainty": uncertainty, "decision": gate,
        "efficiency": {"shared_both_arm_forward_wall_seconds": barrier["forward"]["forward_wall_seconds"], "both_arm_evaluator_parallel_wall_seconds": evaluated["parallel_wall_seconds"], "evaluator_workers_total": TOTAL_EVALUATOR_WORKERS},
        "provenance": {"protocol_sha256": sha256(root / PROTOCOL), "forward_contract_sha256": sha256(root / FORWARD_CONTRACT), "forward_result_sha256": sha256(root / FORWARD_RESULT), "prediction_freeze_sha256": {arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS}, **dict(live), **{f"{arm}_merged_eval_results_sha256": sha256(root / MERGED[arm]) for arm in ARMS}},
        "source_policy": dict(RESULT_SOURCE_POLICY),
        "authorization": {"fresh_exact220_design": gate["passed"], "fresh_exact220_launch": False, "additional_dev64_or_avg4": False, "leaderboard_submission": False, "sota_claim": False},
        "claims": dict(RESULT_CLAIMS),
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_final_result(root, protocol, value)
    return value


def validate_final_result(
    root: Path,
    protocol: Mapping[str, Any] | None = None,
    value: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    frozen_protocol = validate_protocol(root)
    if protocol is not None and dict(protocol) != frozen_protocol:
        raise RuntimeError("V2.46.57 final protocol input drifted")
    result = dict(value) if value is not None else read_object(root / FINAL_RESULT)
    barrier = validate_forward_barrier(root)
    evaluated, summaries = _stored_final_inputs(root)
    metrics = {arm: _arm_metrics(summaries[arm]) for arm in ARMS}
    for arm in ARMS:
        _validate_arm_metrics(metrics[arm])
    uncertainty = paired_uncertainty(summaries)
    gate = decision(frozen_protocol, metrics, uncertainty, barrier["pair"])
    live = validate_live_evaluator_identity(root, frozen_protocol)
    expected_provenance = {
        "protocol_sha256": sha256(root / PROTOCOL),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "prediction_freeze_sha256": {
            arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS
        },
        **live,
        **{
            f"{arm}_merged_eval_results_sha256": sha256(root / MERGED[arm])
            for arm in ARMS
        },
    }
    expected_authorization = {
        "fresh_exact220_design": gate["passed"],
        "fresh_exact220_launch": False,
        "additional_dev64_or_avg4": False,
        "leaderboard_submission": False,
        "sota_claim": False,
    }
    efficiency = result.get("efficiency")
    if (
        set(result)
        != {
            "artifact_version", "role", "protocol_id", "created_at_unix",
            "status", "selected_per_arm", "conservative_denominator_per_arm",
            "failure_as_zero",
            "both_arms_exact64_before_mapping_or_evaluator_open",
            "both_arms_fully_evaluated_with_same_current_judge", "baseline",
            "candidate", "mechanism", "paired_uncertainty", "decision",
            "efficiency", "provenance", "source_policy", "authorization",
            "claims", "result_payload_sha256",
        }
        or result.get("artifact_version") != 1
        or result.get("role")
        != "v24657_unknown_cell_targeted_paired_dev64_result"
        or result.get("protocol_id") != PROTOCOL_ID
        or isinstance(result.get("created_at_unix"), bool)
        or not isinstance(result.get("created_at_unix"), int)
        or result.get("created_at_unix", -1) < 0
        or result.get("status")
        != ("development_gate_go" if gate["passed"] else "development_gate_no_go")
        or result.get("selected_per_arm") != SELECTED_COUNT
        or result.get("conservative_denominator_per_arm") != SELECTED_COUNT
        or result.get("failure_as_zero") is not True
        or result.get("both_arms_exact64_before_mapping_or_evaluator_open")
        is not True
        or result.get("both_arms_fully_evaluated_with_same_current_judge")
        is not True
        or result.get("baseline") != metrics["baseline"]
        or result.get("candidate") != metrics["candidate"]
        or result.get("mechanism") != barrier["pair"]
        or result.get("paired_uncertainty") != uncertainty
        or result.get("decision") != gate
        or not isinstance(efficiency, Mapping)
        or efficiency
        != {
            "shared_both_arm_forward_wall_seconds": barrier["forward"][
                "forward_wall_seconds"
            ],
            "both_arm_evaluator_parallel_wall_seconds": evaluated[
                "parallel_wall_seconds"
            ],
            "evaluator_workers_total": TOTAL_EVALUATOR_WORKERS,
        }
        or result.get("provenance") != expected_provenance
        or result.get("source_policy") != RESULT_SOURCE_POLICY
        or result.get("authorization") != expected_authorization
        or result.get("claims") != RESULT_CLAIMS
        or not _sealed(result, "result_payload_sha256")
    ):
        raise RuntimeError("V2.46.57 final result drifted")
    return result


def build_postaudit(root: Path, result: Mapping[str, Any]) -> dict[str, Any]:
    root = root.resolve()
    result = validate_final_result(root, value=result)
    lease = lease_observation(root, Path("/proc"))
    watchers = protected_watcher_snapshot()
    expected_watchers = validate_forward_contract(root)["execution"][
        "protected_watchers"
    ]
    findings: list[str] = []
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if watchers != expected_watchers:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24657_unknown_cell_targeted_paired_dev64_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "result_sha256": sha256(root / FINAL_RESULT),
        "result_status": result["status"],
        "shared_api_lease_active": lease.get("active"),
        "protected_watchers": watchers,
        "mapping_opened_only_after_both_arm_freeze": True,
        "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        "selective_retry_or_error_revaluation": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "fresh_exact220_design": result["decision"]["passed"] and not findings,
            "fresh_exact220_launch": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_postaudit(root, value=value, result=result)
    return value


def validate_postaudit(
    root: Path,
    *,
    value: Mapping[str, Any] | None = None,
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    audit = dict(value) if value is not None else read_object(root / POSTAUDIT)
    frozen_result = validate_final_result(root, value=result)
    expected_watchers = validate_forward_contract(root)["execution"][
        "protected_watchers"
    ]
    live_lease = lease_observation(root, Path("/proc")).get("active")
    live_watchers = protected_watcher_snapshot()
    expected_findings: list[str] = []
    if live_lease is not False:
        expected_findings.append("shared_api_lease_active")
    if live_watchers != expected_watchers:
        expected_findings.append("protected_watcher_identity_drifted")
    expected_authorization = {
        "fresh_exact220_design": frozen_result["decision"]["passed"]
        and not expected_findings,
        "fresh_exact220_launch": False,
        "leaderboard_or_sota": False,
    }
    if (
        set(audit)
        != {
            "artifact_version", "role", "protocol_id", "created_at_unix",
            "result_sha256", "result_status", "shared_api_lease_active",
            "protected_watchers", "mapping_opened_only_after_both_arm_freeze",
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection",
            "selective_retry_or_error_revaluation", "findings", "audit_valid",
            "authorization", "audit_payload_sha256",
        }
        or audit.get("artifact_version") != 1
        or audit.get("role")
        != "v24657_unknown_cell_targeted_paired_dev64_postresult_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or isinstance(audit.get("created_at_unix"), bool)
        or not isinstance(audit.get("created_at_unix"), int)
        or audit.get("created_at_unix", -1) < 0
        or audit.get("result_sha256") != sha256(root / FINAL_RESULT)
        or audit.get("result_status") != frozen_result["status"]
        or audit.get("shared_api_lease_active") is not live_lease
        or audit.get("protected_watchers") != live_watchers
        or live_watchers != expected_watchers
        or audit.get("mapping_opened_only_after_both_arm_freeze") is not True
        or audit.get(
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection"
        )
        is not False
        or audit.get("selective_retry_or_error_revaluation") is not False
        or audit.get("findings") != expected_findings
        or audit.get("audit_valid") is not (not expected_findings)
        or audit.get("authorization") != expected_authorization
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.57 postresult audit drifted")
    return audit


def finalize(root: Path = ROOT, *, command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run) -> dict[str, Any]:
    root = root.resolve(); validate_evaluator_start(root); barrier = validate_forward_barrier(root); protocol = validate_protocol(root)
    if (root / EVALUATOR_ROOT).exists() or (root / EVALUATOR_ROOT).is_symlink(): raise RuntimeError("V2.46.57 evaluator surface exists; resume forbidden")
    with acquire_deepwide_api_lease(root, owner=EVALUATOR_LEASE_OWNER, purpose=EVALUATOR_LEASE_PURPOSE, path=root / LEASE_PATH):
        live = validate_live_evaluator_identity(root, protocol); (root / EVALUATOR_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        prepared = {arm: prepare_arm(root, protocol, barrier, arm) for arm in ARMS}
        evaluated = run_all_evaluators(root, protocol, prepared, command_runner=command_runner)
    summaries: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        summaries[arm] = summarize_rollout(prepared[arm]["joined"], evaluated["arms"][arm]["rows"], rollout_id=1)
        _new_json(root / SUMMARY[arm], summaries[arm])
    result = build_final_result(root, protocol, barrier, evaluated, summaries, live)
    _new_json(root / FINAL_RESULT, result)
    validate_final_result(root, protocol, result)
    audit = build_postaudit(root, result)
    _new_json(root / POSTAUDIT, audit)
    validate_postaudit(root, value=audit, result=result)
    return result


def publish(path: Path, value: Mapping[str, Any]) -> None:
    _new_json(path, value)


def main() -> None:
    import argparse
    parser = argparse.ArgumentParser(); parser.add_argument("command", choices=("gate", "start", "run")); args = parser.parse_args()
    if args.command == "gate": publish(ROOT / EVALUATOR_GATE, build_evaluator_gate())
    elif args.command == "start": publish(ROOT / EVALUATOR_START, build_evaluator_start())
    elif args.command == "run":
        value = finalize(); print(json.dumps({"result": str(FINAL_RESULT), "status": value["status"], "failed_checks": value["decision"]["failed_checks"]}, sort_keys=True))


if __name__ == "__main__": main()
