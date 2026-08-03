#!/usr/bin/env python3
"""Post-freeze both-arm evaluation for the V2.43.30 exact-220 pair."""

from __future__ import annotations

import argparse
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

from deepwide_agent.v24330_forward_contract import (  # noqa: E402
    ARMS,
    EVALUATOR_GATE,
    EVALUATOR_LEASE_OWNER,
    EVALUATOR_LEASE_PURPOSE,
    EVALUATOR_ROOT,
    EVALUATOR_START,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FINAL_RESULT,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    LEASE_PATH,
    MODEL_SLOT_CAP,
    OUTPUT_ROOT,
    PAIR_SUMMARY,
    POSTAUDIT,
    PREDICTION_FREEZE,
    PROTOCOL,
    PROTOCOL_ID,
    RUNNER_MARKER,
    RUNTIME_PREDICTIONS,
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
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
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
from scripts.run_official_eval_local import validate_committed_eval_rows  # noqa: E402
from scripts.run_v24330_shared_prefix_exact220 import (  # noqa: E402
    validate_forward_result,
    validate_pair_summary,
    validate_prediction_freeze,
)
from scripts.v24330_shared_prefix_exact220_control import (  # noqa: E402
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    DECISION_CONTRACT,
    EVALUATOR_WORKERS_PER_ARM,
    MAPPING_PATH,
    TOTAL_EVALUATOR_WORKERS,
    validate_protocol,
)


QUALITY = ("entity_acc", "f1_by_row", "f1_by_item", "column_f1")
EVALUATOR_RUNNER_MARKER = "scripts/run_official_eval_local.py"
MECHANISM_KEYS = (
    "successful_pair_tasks",
    "failed_pair_tasks",
    "candidate_nonidentity_tasks",
    "proposed_cell_changes",
    "admitted_cell_changes",
    "credited_conditional_entropy_reduction_nats",
    "repeated_upstream_effects",
    "slot_acquisitions",
    "slot_timeouts",
    "provider_deadline_failures",
    "hard_fetch_deadline_failures",
    "fetch_helper_failures",
    "hosted_search_deadline_failures",
    "fetch_deadline_rejections",
    "deadline_exhausted_tasks",
)
RESULT_CLAIMS = {
    "fresh_execution": True,
    "public_exact220_pair": True,
    "public_task_set_reused": True,
    "historically_unseen_or_strict_held_out": False,
    "future_population_inference": False,
    "avg_at_4": False,
    "leaderboard_submitted": False,
    "sota": False,
}
RESULT_SOURCE_POLICY = {
    "runtime_boundary": ["opaque_id", "question"],
    "forward_mapping_gold_category_question_type_split_evaluator_score_read": False,
    "mapping_opened_only_after_both_exact220_prediction_freezes": True,
    "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
}
RESULT_AUTHORIZATION = {
    "additional_rollout_or_avg4": False,
    "leaderboard_submission": False,
    "sota_claim": False,
}
FINAL_RESULT_FIELDS = {
    "artifact_version", "role", "protocol_id", "created_at_unix", "status",
    "selected_pair_tasks", "prediction_rows_per_arm", "failure_as_zero",
    "both_arm_exact220_prediction_freeze_before_evaluator", "metrics",
    "test156_paired_uncertainty", "mechanism", "efficiency", "decision",
    "claims", "source_policy", "authorization", "provenance",
    "result_payload_sha256",
}
EVALUATOR_GATE_FIELDS = {
    "artifact_version", "role", "protocol_id", "created_at_unix", "status",
    "findings", "passed", "selected_pair_tasks", "prediction_rows_per_arm",
    "failed_pair_tasks", "both_arm_prediction_freeze_sha256",
    "forward_result_sha256", "pair_summary_sha256",
    "forward_result_base_commit", "target_main_at_gate",
    "git_worktree_clean_before_gate", "forward_result_tracked",
    "forward_runner_present", "shared_api_lease_active",
    "protected_watchers_unchanged",
    "mapping_query_answer_gold_evaluator_score_opened_or_hashed",
    "official_evaluator_called", "authorization", "protocol_sha256",
    "evaluator_contract_binding_sha256", "gate_payload_sha256",
}
EVALUATOR_START_FIELDS = {
    "artifact_version", "role", "protocol_id", "created_at_unix", "status",
    "findings", "execution_authorized", "gate_base_commit",
    "target_main_at_start", "git_worktree_clean_before_start",
    "evaluator_gate_tracked", "evaluator_gate_sha256", "protocol_sha256",
    "forward_result_sha256", "both_arm_prediction_freeze_sha256",
    "evaluator_workers_per_arm", "total_evaluator_workers",
    "shared_api_lease_active_before_start",
    "mapping_query_answer_gold_evaluator_score_opened_or_hashed_before_start",
    "official_evaluator_called_before_start",
    "additional_forward_resume_retry_or_rerun", "start_payload_sha256",
}
ARM_ROOTS = {arm: EVALUATOR_ROOT / arm for arm in ARMS}
JOINED = {
    arm: ARM_ROOTS[arm] / "terminal_outcomes_evaluator_joined.jsonl"
    for arm in ARMS
}
OFFICIAL = {
    arm: ARM_ROOTS[arm] / "official_predictions.jsonl" for arm in ARMS
}
PREPARE = {arm: ARM_ROOTS[arm] / "prepare_attestation.json" for arm in ARMS}
RUNS = {
    arm: ARM_ROOTS[arm] / "official_eval_workers" for arm in ARMS
}
LOGS = {arm: ARM_ROOTS[arm] / "logs" for arm in ARMS}
MERGED = {
    arm: ARM_ROOTS[arm] / "official_eval_results.jsonl" for arm in ARMS
}
MERGE = {arm: ARM_ROOTS[arm] / "merge_attestation.json" for arm in ARMS}
SUMMARY = {
    arm: ARM_ROOTS[arm] / "conservative_summary.json" for arm in ARMS
}


def _new_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_jsonl_new(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _git_output(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _git_path_tracked(root: Path, path: Path) -> bool:
    try:
        _git_output(root, "ls-files", "--error-unmatch", str(path))
    except subprocess.CalledProcessError:
        return False
    return True


def _process_present(marker: str) -> bool:
    for item in process_snapshot():
        argv = item.get("argv")
        script = actual_python_script(argv) if isinstance(argv, list) else None
        if isinstance(script, str) and script.endswith(marker):
            return True
    return False


def validate_forward_barrier(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    forward = read_object(root / FORWARD_RESULT)
    validate_forward_result(root, contract, forward)
    pair = read_object(root / PAIR_SUMMARY)
    validate_pair_summary(pair)
    arms: dict[str, Any] = {}
    for arm in ARMS:
        freeze = read_object(root / PREDICTION_FREEZE[arm])
        rows = validate_prediction_freeze(root, contract, arm, freeze)
        summary = read_object(root / RUN_SUMMARY[arm])
        if (
            len(rows) != SELECTED_COUNT
            or freeze.get("both_arms_terminal_before_mapping_gold_or_evaluator_open")
            is not True
            or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        ):
            raise RuntimeError(f"V2.43.30 {arm} freeze barrier is incomplete")
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
    if (
        forward.get("both_arms_exact220_before_mapping_gold_or_evaluator_open")
        is not True
        or pair.get("terminal_pair_tasks") != SELECTED_COUNT
        or pair.get("prediction_rows_per_arm")
        != {arm: SELECTED_COUNT for arm in ARMS}
    ):
        raise RuntimeError("V2.43.30 both-arm freeze barrier is incomplete")
    return {
        "contract": contract,
        "forward": forward,
        "pair": pair,
        "ids": selected_ids(contract),
        "arms": arms,
    }


def build_evaluator_gate(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    barrier = validate_forward_barrier(root)
    lease = lease_observation(root, Path("/proc"))
    head = _git_output(root, "rev-parse", "HEAD")
    remote = _git_output(root, "rev-parse", "target/main")
    clean = _git_output(root, "status", "--porcelain") == ""
    forward_tracked = _git_path_tracked(root, FORWARD_RESULT)
    findings: list[str] = []
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (EVALUATOR_GATE, EVALUATOR_START, FINAL_RESULT, POSTAUDIT, EVALUATOR_ROOT)
    ):
        findings.append("evaluator_surface_not_pristine")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if head != remote:
        findings.append("forward_result_commit_not_pushed")
    if not clean:
        findings.append("git_worktree_not_clean_before_evaluator_gate")
    if not forward_tracked:
        findings.append("forward_result_not_tracked")
    if _process_present(RUNNER_MARKER):
        findings.append("forward_runner_still_active")
    if protected_watcher_snapshot() != barrier["contract"]["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_evaluator_gate",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "evaluator_gate_go" if not findings else "evaluator_gate_no_go",
        "findings": findings,
        "passed": not findings,
        "selected_pair_tasks": SELECTED_COUNT,
        "prediction_rows_per_arm": {arm: SELECTED_COUNT for arm in ARMS},
        "failed_pair_tasks": barrier["pair"]["failed_pair_tasks"],
        "both_arm_prediction_freeze_sha256": {
            arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS
        },
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "pair_summary_sha256": sha256(root / PAIR_SUMMARY),
        "forward_result_base_commit": head,
        "target_main_at_gate": remote,
        "git_worktree_clean_before_gate": clean,
        "forward_result_tracked": forward_tracked,
        "forward_runner_present": _process_present(RUNNER_MARKER),
        "shared_api_lease_active": lease.get("active"),
        "protected_watchers_unchanged": protected_watcher_snapshot()
        == barrier["contract"]["execution"]["protected_watchers"],
        "mapping_query_answer_gold_evaluator_score_opened_or_hashed": False,
        "official_evaluator_called": False,
        "authorization": {
            "evaluator_start_design": not findings,
            "evaluator_execution": False,
            "additional_forward_or_rerun": False,
            "leaderboard_or_sota": False,
        },
        "protocol_sha256": sha256(root / PROTOCOL),
        "evaluator_contract_binding_sha256": payload_sha256(
            protocol["evaluator_contract"]
        ),
    }
    value["gate_payload_sha256"] = payload_sha256(value)
    validate_evaluator_gate(root, value=value)
    return value


def validate_evaluator_gate(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    gate = dict(value) if value is not None else read_object(root / EVALUATOR_GATE)
    passed = gate.get("passed")
    if (
        set(gate) != EVALUATOR_GATE_FIELDS
        or gate.get("artifact_version") != 1
        or isinstance(gate.get("created_at_unix"), bool)
        or not isinstance(gate.get("created_at_unix"), int)
        or gate.get("created_at_unix", -1) < 0
        or gate.get("role") != "v24330_shared_prefix_exact220_evaluator_gate"
        or gate.get("protocol_id") != PROTOCOL_ID
        or not isinstance(passed, bool)
        or gate.get("status")
        != ("evaluator_gate_go" if passed else "evaluator_gate_no_go")
        or (passed and gate.get("findings") != [])
        or gate.get("selected_pair_tasks") != SELECTED_COUNT
        or gate.get("prediction_rows_per_arm")
        != {arm: SELECTED_COUNT for arm in ARMS}
        or gate.get("both_arm_prediction_freeze_sha256")
        != {arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS}
        or gate.get("forward_result_sha256") != sha256(root / FORWARD_RESULT)
        or gate.get("pair_summary_sha256") != sha256(root / PAIR_SUMMARY)
        or gate.get("forward_result_base_commit")
        != gate.get("target_main_at_gate")
        or gate.get("git_worktree_clean_before_gate") is not True
        or gate.get("forward_result_tracked") is not True
        or gate.get("forward_runner_present") is not False
        or gate.get("shared_api_lease_active") is not False
        or gate.get("protected_watchers_unchanged") is not True
        or gate.get("mapping_query_answer_gold_evaluator_score_opened_or_hashed")
        is not False
        or gate.get("official_evaluator_called") is not False
        or gate.get("authorization", {}).get("evaluator_start_design") is not passed
        or any(
            enabled
            for key, enabled in gate.get("authorization", {}).items()
            if key != "evaluator_start_design"
        )
        or gate.get("protocol_sha256") != sha256(root / PROTOCOL)
        or not _sealed(gate, "gate_payload_sha256")
    ):
        raise RuntimeError("V2.43.30 evaluator gate drifted")
    validate_forward_barrier(root)
    return gate


def build_evaluator_start(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    gate = validate_evaluator_gate(root)
    if gate["passed"] is not True:
        raise RuntimeError("V2.43.30 evaluator gate is no-go")
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (EVALUATOR_START, FINAL_RESULT, POSTAUDIT, EVALUATOR_ROOT)
    ):
        raise RuntimeError("V2.43.30 evaluator execution surface is not pristine")
    head = _git_output(root, "rev-parse", "HEAD")
    remote = _git_output(root, "rev-parse", "target/main")
    clean = _git_output(root, "status", "--porcelain") == ""
    gate_tracked = _git_path_tracked(root, EVALUATOR_GATE)
    lease = lease_observation(root, Path("/proc"))
    findings: list[str] = []
    if head != remote:
        findings.append("evaluator_gate_commit_not_pushed")
    if not clean:
        findings.append("git_worktree_not_clean_before_evaluator_start")
    if not gate_tracked:
        findings.append("evaluator_gate_not_tracked")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_evaluator_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "evaluator_ready" if not findings else "evaluator_rejected",
        "findings": findings,
        "execution_authorized": not findings,
        "gate_base_commit": head,
        "target_main_at_start": remote,
        "git_worktree_clean_before_start": clean,
        "evaluator_gate_tracked": gate_tracked,
        "evaluator_gate_sha256": sha256(root / EVALUATOR_GATE),
        "protocol_sha256": sha256(root / PROTOCOL),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "both_arm_prediction_freeze_sha256": {
            arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS
        },
        "evaluator_workers_per_arm": EVALUATOR_WORKERS_PER_ARM,
        "total_evaluator_workers": TOTAL_EVALUATOR_WORKERS,
        "shared_api_lease_active_before_start": lease.get("active") is True,
        "mapping_query_answer_gold_evaluator_score_opened_or_hashed_before_start": False,
        "official_evaluator_called_before_start": False,
        "additional_forward_resume_retry_or_rerun": False,
    }
    value["start_payload_sha256"] = payload_sha256(value)
    validate_evaluator_start(root, value=value)
    return value


def validate_evaluator_start(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    start = dict(value) if value is not None else read_object(root / EVALUATOR_START)
    if (
        set(start) != EVALUATOR_START_FIELDS
        or start.get("artifact_version") != 1
        or isinstance(start.get("created_at_unix"), bool)
        or not isinstance(start.get("created_at_unix"), int)
        or start.get("created_at_unix", -1) < 0
        or start.get("role") != "v24330_shared_prefix_exact220_evaluator_start"
        or start.get("protocol_id") != PROTOCOL_ID
        or start.get("status") != "evaluator_ready"
        or start.get("findings") != []
        or start.get("execution_authorized") is not True
        or start.get("git_worktree_clean_before_start") is not True
        or start.get("evaluator_gate_tracked") is not True
        or start.get("evaluator_gate_sha256") != sha256(root / EVALUATOR_GATE)
        or start.get("protocol_sha256") != sha256(root / PROTOCOL)
        or start.get("forward_result_sha256") != sha256(root / FORWARD_RESULT)
        or start.get("both_arm_prediction_freeze_sha256")
        != {arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS}
        or start.get("evaluator_workers_per_arm") != EVALUATOR_WORKERS_PER_ARM
        or start.get("total_evaluator_workers") != TOTAL_EVALUATOR_WORKERS
        or start.get("shared_api_lease_active_before_start") is not False
        or start.get(
            "mapping_query_answer_gold_evaluator_score_opened_or_hashed_before_start"
        )
        is not False
        or start.get("official_evaluator_called_before_start") is not False
        or start.get("additional_forward_resume_retry_or_rerun") is not False
        or not _sealed(start, "start_payload_sha256")
    ):
        raise RuntimeError("V2.43.30 evaluator start drifted")
    validate_evaluator_gate(root)
    return start


def publish(path: Path, value: Mapping[str, Any]) -> None:
    _new_json(path, value)


def validate_live_evaluator_identity(
    root: Path, protocol: Mapping[str, Any]
) -> dict[str, Any]:
    evaluator = protocol["evaluator_contract"]
    mapping = root / evaluator["mapping"]["path"]
    query_path = root / evaluator["query_data"]["path"]
    answer_root = root / evaluator["answer_corpus"]["root"]
    if (
        mapping.is_symlink()
        or not mapping.is_file()
        or sha256(mapping) != evaluator["mapping"]["sha256"]
        or query_path.is_symlink()
        or not query_path.is_file()
        or sha256(query_path) != evaluator["query_data"]["sha256"]
        or answer_root.is_symlink()
        or not answer_root.is_dir()
        or _live_answer_corpus_manifest_sha256(answer_root)
        != evaluator["answer_corpus"]["manifest_sha256"]
        or _live_evaluator_source_manifest_sha256()
        != evaluator["evaluator_source"]["manifest_sha256"]
    ):
        raise RuntimeError("V2.43.30 live evaluator identity drifted")
    return {
        "mapping_sha256": evaluator["mapping"]["sha256"],
        "query_data_sha256": evaluator["query_data"]["sha256"],
        "answer_corpus_manifest_sha256": evaluator["answer_corpus"][
            "manifest_sha256"
        ],
        "evaluator_source_manifest_sha256": evaluator["evaluator_source"][
            "manifest_sha256"
        ],
        "judge": dict(evaluator["judge"]),
        "recovery_policy": dict(evaluator["recovery_policy"]),
    }


def prepare_arm(
    root: Path,
    protocol: Mapping[str, Any],
    barrier: Mapping[str, Any],
    arm: str,
) -> dict[str, Any]:
    state = barrier["arms"][arm]
    joined, official, base = prepare_rollout(
        manifest_rows=read_jsonl(root / SOURCE_MANIFEST),
        mapping_rows=read_jsonl(root / MAPPING_PATH),
        shards=[("all220", barrier["ids"], state["rows"], state["summary"])],
        rollout_id=1,
    )
    completed = sum(row["status"] == "completed" for row in state["rows"])
    if len(joined) != SELECTED_COUNT or len(official) != completed:
        raise RuntimeError(f"V2.43.30 {arm} evaluator prepare coverage drifted")
    (root / ARM_ROOTS[arm]).mkdir(mode=0o700, parents=True, exist_ok=False)
    _write_jsonl_new(root / JOINED[arm], joined)
    _write_jsonl_new(root / OFFICIAL[arm], official)
    value = {
        **base,
        "phase": "post_both_arm_exact220_freeze_evaluator_prepare",
        "arm": arm,
        "protocol_sha256": sha256(root / PROTOCOL),
        "evaluator_start_sha256": sha256(root / EVALUATOR_START),
        "both_arm_prediction_freeze_sha256": {
            name: sha256(root / PREDICTION_FREEZE[name]) for name in ARMS
        },
        "both_arms_exact220_before_mapping_gold_or_evaluator_open": True,
        "selective_changed_prediction_evaluation": False,
        "old_evaluator_rows_reused": False,
        "mapping_sha256": sha256(root / MAPPING_PATH),
        "manifest_sha256": sha256(root / SOURCE_MANIFEST),
        "source_hashes": state["sources"],
        "terminal_outcomes_sha256": sha256(root / JOINED[arm]),
        "official_predictions_sha256": sha256(root / OFFICIAL[arm]),
    }
    value["prepare_payload_sha256"] = payload_sha256(value)
    _new_json(root / PREPARE[arm], value)
    return {"joined": joined, "official": official, "attestation": value}


def validate_prepared_arm(
    root: Path,
    protocol: Mapping[str, Any],
    barrier: Mapping[str, Any],
    arm: str,
) -> dict[str, Any]:
    """Rebuild the post-freeze join and require byte-identical evaluator inputs."""

    if arm not in ARMS:
        raise RuntimeError(f"V2.43.30 unknown evaluator arm: {arm}")
    state = barrier["arms"][arm]
    expected_joined, expected_official, base = prepare_rollout(
        manifest_rows=read_jsonl(root / SOURCE_MANIFEST),
        mapping_rows=read_jsonl(root / MAPPING_PATH),
        shards=[("all220", barrier["ids"], state["rows"], state["summary"])],
        rollout_id=1,
    )
    joined = read_jsonl(root / JOINED[arm])
    official = read_jsonl(root / OFFICIAL[arm])
    completed = sum(row["status"] == "completed" for row in state["rows"])
    if (
        len(joined) != SELECTED_COUNT
        or len(official) != completed
        or joined != expected_joined
        or official != expected_official
    ):
        raise RuntimeError(f"V2.43.30 {arm} prepared evaluator rows drifted")
    expected = {
        **base,
        "phase": "post_both_arm_exact220_freeze_evaluator_prepare",
        "arm": arm,
        "protocol_sha256": sha256(root / PROTOCOL),
        "evaluator_start_sha256": sha256(root / EVALUATOR_START),
        "both_arm_prediction_freeze_sha256": {
            name: sha256(root / PREDICTION_FREEZE[name]) for name in ARMS
        },
        "both_arms_exact220_before_mapping_gold_or_evaluator_open": True,
        "selective_changed_prediction_evaluation": False,
        "old_evaluator_rows_reused": False,
        "mapping_sha256": sha256(root / MAPPING_PATH),
        "manifest_sha256": sha256(root / SOURCE_MANIFEST),
        "source_hashes": state["sources"],
        "terminal_outcomes_sha256": sha256(root / JOINED[arm]),
        "official_predictions_sha256": sha256(root / OFFICIAL[arm]),
    }
    attestation = read_object(root / PREPARE[arm])
    unsigned = dict(attestation)
    seal = unsigned.pop("prepare_payload_sha256", None)
    if unsigned != expected or seal != payload_sha256(unsigned):
        raise RuntimeError(f"V2.43.30 {arm} prepare attestation drifted")
    return {"joined": joined, "official": official, "attestation": attestation}


def fixed_partitions(selected: int) -> list[tuple[int, int]]:
    if isinstance(selected, bool) or not isinstance(selected, int) or selected < 0:
        raise ValueError("V2.43.30 evaluator selected count drifted")
    base, remainder = divmod(selected, EVALUATOR_WORKERS_PER_ARM)
    output: list[tuple[int, int]] = []
    start = 0
    for index in range(EVALUATOR_WORKERS_PER_ARM):
        size = base + (1 if index < remainder else 0)
        output.append((start, start + size))
        start += size
    if start != selected:
        raise AssertionError("V2.43.30 evaluator partition drifted")
    return output


def evaluator_command(
    root: Path,
    protocol: Mapping[str, Any],
    arm: str,
    worker: int,
    predictions: Path,
) -> list[str]:
    evaluator = protocol["evaluator_contract"]
    judge = evaluator["judge"]
    return [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / "scripts/run_official_eval_local.py"),
        "--predictions",
        str(predictions),
        "--out-dir",
        str(root / RUNS[arm] / f"worker_{worker:02d}"),
        "--query-path",
        str(root / evaluator["query_data"]["path"]),
        "--answer-root",
        str(root / evaluator["answer_corpus"]["root"]),
        "--proxy-url",
        judge["proxy_url"],
        "--model",
        judge["model"],
        "--reasoning-effort",
        judge["reasoning_effort"],
        "--judge-max-output-tokens",
        str(judge["max_output_tokens"]),
        "--judge-timeout",
        str(judge["timeout_seconds"]),
        "--judge-max-retries",
        str(judge["max_retries"]),
    ]


def _run_worker(
    arm: str,
    worker: int,
    command: Sequence[str],
    root: Path,
    runner: Callable[..., subprocess.CompletedProcess[Any]],
) -> dict[str, Any]:
    environment = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    environment.update(
        {
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        }
    )
    log = root / LOGS[arm] / f"worker_{worker:02d}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    try:
        with log.open("xb") as handle:
            completed = runner(
                list(command),
                cwd=root,
                env=environment,
                stdout=handle,
                stderr=subprocess.STDOUT,
                check=False,
            )
            handle.flush()
            os.fsync(handle.fileno())
        returncode = int(completed.returncode)
        exception = False
    except Exception:
        returncode = -1
        exception = True
        if not log.exists():
            log.write_bytes(b"")
    return {
        "arm": arm,
        "worker": worker,
        "returncode": returncode,
        "runner_exception": exception,
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "log_sha256": sha256(log),
    }


def _worker_error_rows(ids: Sequence[str]) -> list[dict[str, Any]]:
    return [
        {
            "instance_id": instance_id,
            "error": "EvaluatorWorkerFailure",
            "elapsed_seconds": 0.0,
        }
        for instance_id in ids
    ]


def run_all_evaluators(
    root: Path,
    protocol: Mapping[str, Any],
    prepared: Mapping[str, Mapping[str, Any]],
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    commands: list[dict[str, Any]] = []
    for arm in ARMS:
        (root / RUNS[arm]).mkdir(mode=0o700, parents=True, exist_ok=False)
        partitions = fixed_partitions(len(prepared[arm]["official"]))
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
                    "ids": [str(row["instance_id"]) for row in rows],
                    "shard": shard,
                    "command": evaluator_command(root, protocol, arm, worker, shard),
                }
            )
    started = time.monotonic()
    reports: dict[tuple[str, int], dict[str, Any]] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=TOTAL_EVALUATOR_WORKERS,
        thread_name_prefix="v24330-eval",
    ) as executor:
        futures = {
            executor.submit(
                _run_worker,
                item["arm"],
                item["worker"],
                item["command"],
                root,
                command_runner,
            ): (item["arm"], item["worker"])
            for item in commands
        }
        for future in concurrent.futures.as_completed(futures):
            report = future.result()
            reports[(report["arm"], report["worker"])] = report
    wall = round(max(0.0, time.monotonic() - started), 6)
    output: dict[str, Any] = {"parallel_wall_seconds": wall, "arms": {}}
    live = validate_live_evaluator_identity(root, protocol)
    for arm in ARMS:
        merged: list[dict[str, Any]] = []
        worker_reports: list[dict[str, Any]] = []
        arm_commands = [item for item in commands if item["arm"] == arm]
        for item in arm_commands:
            report = reports[(arm, item["worker"])]
            run_root = root / RUNS[arm] / f"worker_{item['worker']:02d}"
            result_path = run_root / "official_eval_results.jsonl"
            config_path = run_root / "run_config.json"
            catastrophic = report["returncode"] != 0
            rows: list[dict[str, Any]]
            contract_sha256: str | None = None
            results_sha256: str | None = None
            run_config_sha256: str | None = None
            if not catastrophic:
                try:
                    rows = read_jsonl(result_path)
                    validate_committed_eval_rows(rows, item["ids"])
                    if len(rows) != len(item["ids"]):
                        raise RuntimeError("incomplete worker rows")
                    contract = validate_evaluator_contract(
                        config_path,
                        expected_predictions_path=item["shard"],
                        expected_predictions_sha256=sha256(item["shard"]),
                        expected_selected_count=len(item["ids"]),
                    )
                    for key in (
                        "query_data_sha256",
                        "answer_corpus_manifest_sha256",
                        "evaluator_source_manifest_sha256",
                        "judge",
                        "recovery_policy",
                    ):
                        if contract.get(key) != live.get(key):
                            raise RuntimeError("worker evaluator provenance drifted")
                    contract_sha256 = str(contract["run_contract_sha256"])
                    results_sha256 = sha256(result_path)
                    run_config_sha256 = sha256(config_path)
                except Exception:
                    catastrophic = True
            if catastrophic:
                rows = _worker_error_rows(item["ids"])
            validate_committed_eval_rows(rows, item["ids"])
            merged.extend(rows)
            worker_reports.append(
                {
                    **report,
                    "start": item["start"],
                    "end": item["end"],
                    "selected": len(item["ids"]),
                    "prediction_shard_sha256": sha256(item["shard"]),
                    "catastrophic_worker_failure_as_zero": catastrophic,
                    "results_sha256": results_sha256,
                    "run_config_sha256": run_config_sha256,
                    "run_contract_sha256": contract_sha256,
                }
            )
        expected_ids = [
            str(row["instance_id"]) for row in prepared[arm]["official"]
        ]
        validate_committed_eval_rows(merged, expected_ids)
        if len(merged) != len(expected_ids):
            raise RuntimeError(f"V2.43.30 {arm} merged evaluator is incomplete")
        _write_jsonl_new(root / MERGED[arm], merged)
        partitions = fixed_partitions(len(expected_ids))
        attestation = {
            "artifact_version": 1,
            "role": "v24330_parallel_arm_evaluator_merge_attestation",
            "arm": arm,
            "selected_predictions": len(expected_ids),
            "workers": EVALUATOR_WORKERS_PER_ARM,
            "fixed_contiguous_partitions": [
                {"worker": index + 1, "start": start, "end": end}
                for index, (start, end) in enumerate(partitions)
            ],
            "worker_reports": worker_reports,
            "shared_both_arm_parallel_wall_seconds": wall,
            "merged_results_sha256": sha256(root / MERGED[arm]),
            "all_completed_predictions_evaluated_or_terminal_error_exactly_once": True,
            "catastrophic_worker_failure_count": sum(
                report["catastrophic_worker_failure_as_zero"]
                for report in worker_reports
            ),
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
    """Validate all worker shards, failure-as-zero rows, and evaluator lineage."""

    if arm not in ARMS:
        raise RuntimeError(f"V2.43.30 unknown evaluator arm: {arm}")
    live = validate_live_evaluator_identity(root, protocol)
    official = list(prepared["official"])
    expected_ids = [str(row["instance_id"]) for row in official]
    if len(set(expected_ids)) != len(expected_ids):
        raise RuntimeError(f"V2.43.30 {arm} official prediction identity drifted")
    partitions = fixed_partitions(len(official))
    expected_partitions = [
        {"worker": index + 1, "start": start, "end": end}
        for index, (start, end) in enumerate(partitions)
    ]
    attestation = read_object(root / MERGE[arm])
    unsigned = dict(attestation)
    seal = unsigned.pop("merge_payload_sha256", None)
    reports = attestation.get("worker_reports")
    wall = attestation.get("shared_both_arm_parallel_wall_seconds")
    if (
        set(attestation)
        != {
            "artifact_version", "role", "arm", "selected_predictions",
            "workers", "fixed_contiguous_partitions", "worker_reports",
            "shared_both_arm_parallel_wall_seconds", "merged_results_sha256",
            "all_completed_predictions_evaluated_or_terminal_error_exactly_once",
            "catastrophic_worker_failure_count",
            "selective_retry_or_error_revaluation", "merge_payload_sha256",
        }
        or attestation.get("artifact_version") != 1
        or attestation.get("role")
        != "v24330_parallel_arm_evaluator_merge_attestation"
        or attestation.get("arm") != arm
        or attestation.get("selected_predictions") != len(official)
        or attestation.get("workers") != EVALUATOR_WORKERS_PER_ARM
        or attestation.get("fixed_contiguous_partitions") != expected_partitions
        or not isinstance(reports, list)
        or len(reports) != EVALUATOR_WORKERS_PER_ARM
        or isinstance(wall, bool)
        or not isinstance(wall, (int, float))
        or not math.isfinite(float(wall))
        or float(wall) < 0
        or attestation.get(
            "all_completed_predictions_evaluated_or_terminal_error_exactly_once"
        )
        is not True
        or attestation.get("selective_retry_or_error_revaluation") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError(f"V2.43.30 {arm} merge attestation drifted")

    merged_from_workers: list[dict[str, Any]] = []
    catastrophic_count = 0
    report_keys = {
        "arm", "worker", "returncode", "runner_exception", "wall_seconds",
        "log_sha256", "start", "end", "selected",
        "prediction_shard_sha256", "catastrophic_worker_failure_as_zero",
        "results_sha256", "run_config_sha256", "run_contract_sha256",
    }
    for index, (start, end) in enumerate(partitions):
        worker = index + 1
        report = reports[index]
        if not isinstance(report, Mapping) or set(report) != report_keys:
            raise RuntimeError(f"V2.43.30 {arm} worker report schema drifted")
        shard = root / RUNS[arm] / f"worker_{worker:02d}_predictions.jsonl"
        expected_shard = official[start:end]
        if read_jsonl(shard) != expected_shard:
            raise RuntimeError(f"V2.43.30 {arm} worker prediction shard drifted")
        ids = expected_ids[start:end]
        log_path = root / LOGS[arm] / f"worker_{worker:02d}.log"
        run_root = root / RUNS[arm] / f"worker_{worker:02d}"
        result_path = run_root / "official_eval_results.jsonl"
        config_path = run_root / "run_config.json"
        returncode = report.get("returncode")
        runner_exception = report.get("runner_exception")
        report_wall = report.get("wall_seconds")
        catastrophic = bool(report.get("catastrophic_worker_failure_as_zero"))
        if (
            isinstance(returncode, bool)
            or not isinstance(returncode, int)
            or not isinstance(runner_exception, bool)
            or isinstance(report_wall, bool)
            or not isinstance(report_wall, (int, float))
            or not math.isfinite(float(report_wall))
            or float(report_wall) < 0
            or report.get("arm") != arm
            or report.get("worker") != worker
            or report.get("start") != start
            or report.get("end") != end
            or report.get("selected") != end - start
            or report.get("prediction_shard_sha256") != sha256(shard)
            or report.get("log_sha256") != sha256(log_path)
        ):
            raise RuntimeError(f"V2.43.30 {arm} worker provenance drifted")

        valid_rows: list[dict[str, Any]] | None = None
        contract: dict[str, Any] | None = None
        artifacts_valid = False
        if returncode == 0 and runner_exception is False:
            try:
                valid_rows = read_jsonl(result_path)
                validate_committed_eval_rows(valid_rows, ids)
                if len(valid_rows) != len(ids):
                    raise RuntimeError("incomplete worker rows")
                contract = validate_evaluator_contract(
                    config_path,
                    expected_predictions_path=shard,
                    expected_predictions_sha256=sha256(shard),
                    expected_selected_count=len(ids),
                )
                for key in (
                    "query_data_sha256", "answer_corpus_manifest_sha256",
                    "evaluator_source_manifest_sha256", "judge", "recovery_policy",
                ):
                    if contract.get(key) != live.get(key):
                        raise RuntimeError("worker evaluator provenance drifted")
                artifacts_valid = True
            except Exception:
                artifacts_valid = False
        expected_catastrophic = not artifacts_valid
        if catastrophic is not expected_catastrophic:
            raise RuntimeError(f"V2.43.30 {arm} worker failure projection drifted")
        if catastrophic:
            catastrophic_count += 1
            if any(
                report.get(name) is not None
                for name in (
                    "results_sha256", "run_config_sha256", "run_contract_sha256"
                )
            ):
                raise RuntimeError(f"V2.43.30 {arm} failed worker hashes drifted")
            rows = _worker_error_rows(ids)
        else:
            assert valid_rows is not None and contract is not None
            if (
                report.get("results_sha256") != sha256(result_path)
                or report.get("run_config_sha256") != sha256(config_path)
                or report.get("run_contract_sha256")
                != contract["run_contract_sha256"]
            ):
                raise RuntimeError(f"V2.43.30 {arm} worker artifact hash drifted")
            rows = valid_rows
        validate_committed_eval_rows(rows, ids)
        merged_from_workers.extend(rows)

    merged = read_jsonl(root / MERGED[arm])
    validate_committed_eval_rows(merged, expected_ids)
    if (
        merged != merged_from_workers
        or len(merged) != len(expected_ids)
        or attestation.get("merged_results_sha256") != sha256(root / MERGED[arm])
        or attestation.get("catastrophic_worker_failure_count")
        != catastrophic_count
    ):
        raise RuntimeError(f"V2.43.30 {arm} merged evaluator rows drifted")
    return {"rows": merged, "attestation": attestation}


def validate_arm_summary(
    root: Path,
    prepared: Mapping[str, Any],
    evaluated: Mapping[str, Any],
    arm: str,
) -> dict[str, Any]:
    expected = summarize_rollout(
        prepared["joined"], evaluated["rows"], rollout_id=1
    )
    stored = read_object(root / SUMMARY[arm])
    if stored != expected:
        raise RuntimeError(f"V2.43.30 {arm} conservative summary drifted")
    return stored


def _group_metrics(
    summary: Mapping[str, Any], group_name: str
) -> dict[str, Any]:
    group = summary["groups"][group_name]
    conservative = group["conservative_all_selected"]
    costs = group["cost_totals"]
    selected_rows = [
        row
        for row in summary["per_task"]
        if group_name == "all_220" or row["split"] == "test"
    ]
    return {
        "selected": int(group["selected"]),
        "runtime_completed": int(group["runtime_completed"]),
        "runtime_failed": int(group["runtime_failed"]),
        "evaluator_valid": int(group["evaluator_valid"]),
        "evaluator_invalid_or_not_run": int(group["evaluator_invalid_or_not_run"]),
        "whole_table_successes": sum(
            row["evaluator_valid"] and float(row["metrics"]["score"]) > 0
            for row in selected_rows
        ),
        **{name: float(conservative[name]) for name in QUALITY},
        "quality_composite": sum(
            float(conservative[name]) for name in QUALITY
        )
        / len(QUALITY),
        "score": float(conservative["score"]),
        "completed_tables": int(group["runtime_completed"]),
        "failed_tables": int(group["runtime_failed"]),
        "observable_system_total_tokens_lower_bound": int(
            costs["system_total_tokens"]
        ),
        "observable_task_wall_seconds_lower_bound": float(
            costs["wall_seconds_sum"]
        ),
        "cost_trace_complete_tasks": int(group["process_trace_complete_tasks"]),
        "shared_pair_cost_duplicated_across_arms": True,
    }


def paired_uncertainty(
    summaries: Mapping[str, Mapping[str, Any]],
    *,
    group: str,
    seed: int,
    resamples: int,
) -> dict[str, Any]:
    by_arm: dict[str, dict[str, Mapping[str, Any]]] = {}
    order: list[str] = []
    for arm in ARMS:
        selected = [
            row
            for row in summaries[arm]["per_task"]
            if group == "all_220" or row["split"] == "test"
        ]
        mapping = {str(row["opaque_id"]): row for row in selected}
        if len(mapping) != len(selected):
            raise RuntimeError("V2.43.30 paired uncertainty duplicate task")
        by_arm[arm] = mapping
        if arm == "baseline":
            order = [str(row["opaque_id"]) for row in selected]
    if set(by_arm["candidate"]) != set(order):
        raise RuntimeError("V2.43.30 paired uncertainty task identity drifted")
    expected_count = 156 if group == "test_156" else 220 if group == "all_220" else None
    if expected_count is None or len(order) != expected_count:
        raise RuntimeError("V2.43.30 paired uncertainty group denominator drifted")
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
        sum(deltas[generator.randrange(len(deltas))] for _ in deltas)
        / len(deltas)
        for _ in range(resamples)
    )
    interval = [estimates[249], estimates[9749]]
    return {
        "group": group,
        "task_count": len(deltas),
        "bootstrap_unit": "paired_frozen_task",
        "seed": seed,
        "resamples": resamples,
        "estimand": f"mean paired failure-as-zero composite delta on public {group}",
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
        "public_reused_tasks_not_future_population_inference": True,
    }


def decision(
    protocol: Mapping[str, Any],
    metrics: Mapping[str, Mapping[str, Mapping[str, Any]]],
    uncertainty: Mapping[str, Any],
    pair: Mapping[str, Any],
) -> dict[str, Any]:
    gate = protocol["decision_contract"]
    baseline_test = metrics["baseline"]["test_156"]
    candidate_test = metrics["candidate"]["test_156"]
    baseline_all = metrics["baseline"]["all_220"]
    candidate_all = metrics["candidate"]["all_220"]
    for arm in ARMS:
        for group, expected in (("test_156", 156), ("all_220", 220)):
            item = metrics[arm][group]
            if (
                item.get("selected") != expected
                or item.get("runtime_completed", -1)
                + item.get("runtime_failed", -1)
                != expected
                or item.get("evaluator_valid", -1)
                + item.get("evaluator_invalid_or_not_run", -1)
                != expected
            ):
                raise RuntimeError("V2.43.30 decision metric denominator drifted")
    validate_pair_summary(pair)
    test_delta = {
        name: candidate_test[name] - baseline_test[name]
        for name in (*QUALITY, "quality_composite")
    }
    all_delta = {
        name: candidate_all[name] - baseline_all[name]
        for name in (*QUALITY, "quality_composite", "whole_table_successes")
    }
    checks = {
        "test156_quality_composite_delta": test_delta["quality_composite"]
        >= gate["minimum_test156_quality_composite_delta"],
        "test156_entity_acc_delta": test_delta["entity_acc"]
        >= gate["minimum_test156_entity_acc_delta"],
        "test156_f1_by_row_delta": test_delta["f1_by_row"]
        >= gate["minimum_test156_f1_by_row_delta"],
        "test156_f1_by_item_delta": test_delta["f1_by_item"]
        >= gate["minimum_test156_f1_by_item_delta"],
        "test156_column_f1_delta": test_delta["column_f1"]
        >= gate["minimum_test156_column_f1_delta"],
        "all220_quality_composite_delta": all_delta["quality_composite"]
        >= gate["minimum_all220_quality_composite_delta"],
        "all220_whole_table_success_delta": all_delta["whole_table_successes"]
        >= gate["minimum_all220_whole_table_success_delta"],
        "candidate_all220_whole_table_successes": candidate_all[
            "whole_table_successes"
        ]
        >= gate["minimum_candidate_all220_whole_table_successes"],
        "candidate_all220_quality_composite": candidate_all["quality_composite"]
        >= gate["minimum_candidate_all220_quality_composite"],
        "candidate_evaluator_health": candidate_all[
            "evaluator_invalid_or_not_run"
        ]
        <= gate["maximum_candidate_evaluator_invalid_or_not_run"],
        "candidate_minus_baseline_evaluator_invalid": candidate_all[
            "evaluator_invalid_or_not_run"
        ]
        - baseline_all["evaluator_invalid_or_not_run"]
        <= gate["maximum_candidate_minus_baseline_evaluator_invalid"],
        "failed_pair_tasks": pair["failed_pair_tasks"]
        <= gate["maximum_failed_pair_tasks"],
        "candidate_nonidentity_tasks": pair["candidate_nonidentity_tasks"]
        >= gate["minimum_candidate_nonidentity_tasks"],
        "admitted_cell_changes": pair["admitted_cell_changes"]
        >= gate["minimum_admitted_cell_changes"],
        "positive_entropy_credit": pair[
            "credited_conditional_entropy_reduction_nats"
        ]
        >= gate["minimum_credited_conditional_entropy_reduction_nats"],
        "repeated_upstream_effects": pair["repeated_upstream_effects"]
        == gate["required_repeated_upstream_effects"],
        "slot_timeouts": pair["slot_timeouts"] <= gate["maximum_slot_timeouts"],
        "provider_deadline_failures": pair["provider_deadline_failures"]
        <= gate["maximum_provider_deadline_failures"],
        "hard_fetch_deadline_failures": pair["hard_fetch_deadline_failures"]
        <= gate["maximum_hard_fetch_deadline_failures"],
        "fetch_helper_failures": pair["fetch_helper_failures"]
        <= gate["maximum_fetch_helper_failures"],
        "hosted_search_deadline_failures": pair[
            "hosted_search_deadline_failures"
        ]
        <= gate["maximum_hosted_search_deadline_failures"],
        "fetch_deadline_rejections": pair["fetch_deadline_rejections"]
        <= gate["maximum_fetch_deadline_rejections"],
        "deadline_exhausted_tasks": pair["deadline_exhausted_tasks"]
        <= gate["maximum_deadline_exhausted_tasks"],
        "test156_paired_bootstrap_lower_bound": uncertainty[
            "percentile_95_interval"
        ][0]
        >= gate["minimum_test156_paired_bootstrap_95_lower_bound"],
        "test156_paired_bootstrap_interval_width": uncertainty["interval_width"]
        <= gate["maximum_test156_paired_bootstrap_95_interval_width"],
        "test156_paired_median_delta": uncertainty["median"]
        >= gate["minimum_test156_paired_median_delta"],
    }
    passed = all(checks.values())
    return {
        "status": "go" if passed else "no_go",
        "passed": passed,
        "checks": checks,
        "failed_checks": sorted(name for name, okay in checks.items() if not okay),
        "test156_candidate_minus_baseline": test_delta,
        "all220_candidate_minus_baseline": all_delta,
        "test156_paired_uncertainty": dict(uncertainty),
        "gate": dict(gate),
        "claim_scope": "public_exact220_shared_prefix_pair_not_future_population_not_avg4",
    }


def _recompute_final(root: Path, protocol: Mapping[str, Any]) -> dict[str, Any]:
    barrier = validate_forward_barrier(root)
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
    metrics: dict[str, dict[str, dict[str, Any]]] = {}
    for arm in ARMS:
        metrics[arm] = {
            group: _group_metrics(summaries[arm], group)
            for group in ("test_156", "all_220")
        }
    uncertainty = paired_uncertainty(
        summaries,
        group="test_156",
        seed=BOOTSTRAP_SEED,
        resamples=BOOTSTRAP_RESAMPLES,
    )
    gate = decision(protocol, metrics, uncertainty, barrier["pair"])
    walls = {
        float(read_object(root / MERGE[arm])["shared_both_arm_parallel_wall_seconds"])
        for arm in ARMS
    }
    if len(walls) != 1:
        raise RuntimeError("V2.43.30 evaluator wall drifted between arms")
    return {
        "barrier": barrier,
        "live": live,
        "prepared": prepared,
        "evaluated": evaluated,
        "summaries": summaries,
        "metrics": metrics,
        "uncertainty": uncertainty,
        "decision": gate,
        "evaluator_parallel_wall_seconds": walls.pop(),
    }


def validate_final_result(
    root: Path, protocol: Mapping[str, Any], value: Mapping[str, Any]
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    if (
        set(value) != FINAL_RESULT_FIELDS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24330_shared_prefix_exact220_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or isinstance(value.get("created_at_unix"), bool)
        or not isinstance(value.get("created_at_unix"), int)
        or value.get("created_at_unix", -1) < 0
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.30 final result drifted")
    recomputed = _recompute_final(root, protocol)
    barrier = recomputed["barrier"]
    expected_mechanism = {
        key: barrier["pair"][key] for key in MECHANISM_KEYS
    }
    efficiency = value.get("efficiency")
    provenance = value.get("provenance")
    live = recomputed["live"]
    if (
        value.get("status")
        != (
            "public_exact220_pair_go"
            if recomputed["decision"]["passed"]
            else "public_exact220_pair_no_go"
        )
        or value.get("selected_pair_tasks") != SELECTED_COUNT
        or value.get("prediction_rows_per_arm")
        != {arm: SELECTED_COUNT for arm in ARMS}
        or value.get("failure_as_zero") is not True
        or value.get("both_arm_exact220_prediction_freeze_before_evaluator")
        is not True
        or value.get("metrics") != recomputed["metrics"]
        or value.get("test156_paired_uncertainty") != recomputed["uncertainty"]
        or value.get("mechanism") != expected_mechanism
        or value.get("decision") != recomputed["decision"]
        or value.get("claims") != RESULT_CLAIMS
        or value.get("source_policy") != RESULT_SOURCE_POLICY
        or value.get("authorization") != RESULT_AUTHORIZATION
        or not isinstance(efficiency, Mapping)
        or set(efficiency)
        != {
            "shared_pair_forward_wall_seconds",
            "both_arm_evaluator_parallel_wall_seconds",
            "forward_executor_concurrency", "model_slot_cap",
            "evaluator_workers_total",
        }
        or efficiency.get("shared_pair_forward_wall_seconds")
        != barrier["forward"]["forward_wall_seconds"]
        or efficiency.get("both_arm_evaluator_parallel_wall_seconds")
        != recomputed["evaluator_parallel_wall_seconds"]
        or efficiency.get("forward_executor_concurrency")
        != EXECUTOR_CONCURRENCY
        or efficiency.get("model_slot_cap") != MODEL_SLOT_CAP
        or efficiency.get("evaluator_workers_total") != TOTAL_EVALUATOR_WORKERS
        or not isinstance(provenance, Mapping)
        or set(provenance)
        != {
            "protocol_sha256", "forward_contract_sha256",
            "forward_result_sha256", "evaluator_gate_sha256",
            "evaluator_start_sha256", "pair_summary_sha256",
            "both_arm_prediction_freeze_sha256",
            "both_arm_runtime_predictions_sha256",
            "both_arm_run_summary_sha256",
            "both_arm_terminal_outcomes_sha256",
            "both_arm_official_predictions_sha256",
            "both_arm_prepare_attestation_sha256",
            "both_arm_merged_eval_results_sha256",
            "both_arm_merge_attestation_sha256",
            "both_arm_conservative_summary_sha256", "mapping_sha256",
            "query_data_sha256", "answer_corpus_manifest_sha256",
            "evaluator_source_manifest_sha256", "judge", "recovery_policy",
        }
        or provenance.get("protocol_sha256") != sha256(root / PROTOCOL)
        or provenance.get("forward_contract_sha256")
        != sha256(root / FORWARD_CONTRACT)
        or provenance.get("forward_result_sha256") != sha256(root / FORWARD_RESULT)
        or provenance.get("evaluator_gate_sha256") != sha256(root / EVALUATOR_GATE)
        or provenance.get("evaluator_start_sha256") != sha256(root / EVALUATOR_START)
        or provenance.get("both_arm_prediction_freeze_sha256")
        != {arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS}
        or provenance.get("both_arm_runtime_predictions_sha256")
        != {arm: sha256(root / RUNTIME_PREDICTIONS[arm]) for arm in ARMS}
        or provenance.get("both_arm_run_summary_sha256")
        != {arm: sha256(root / RUN_SUMMARY[arm]) for arm in ARMS}
        or provenance.get("pair_summary_sha256") != sha256(root / PAIR_SUMMARY)
        or provenance.get("both_arm_terminal_outcomes_sha256")
        != {arm: sha256(root / JOINED[arm]) for arm in ARMS}
        or provenance.get("both_arm_official_predictions_sha256")
        != {arm: sha256(root / OFFICIAL[arm]) for arm in ARMS}
        or provenance.get("both_arm_prepare_attestation_sha256")
        != {arm: sha256(root / PREPARE[arm]) for arm in ARMS}
        or provenance.get("both_arm_merged_eval_results_sha256")
        != {arm: sha256(root / MERGED[arm]) for arm in ARMS}
        or provenance.get("both_arm_conservative_summary_sha256")
        != {arm: sha256(root / SUMMARY[arm]) for arm in ARMS}
        or provenance.get("both_arm_merge_attestation_sha256")
        != {arm: sha256(root / MERGE[arm]) for arm in ARMS}
        or provenance.get("mapping_sha256") != sha256(root / MAPPING_PATH)
        or provenance.get("query_data_sha256") != live["query_data_sha256"]
        or provenance.get("answer_corpus_manifest_sha256")
        != live["answer_corpus_manifest_sha256"]
        or provenance.get("evaluator_source_manifest_sha256")
        != live["evaluator_source_manifest_sha256"]
        or provenance.get("judge") != live["judge"]
        or provenance.get("recovery_policy") != live["recovery_policy"]
    ):
        raise RuntimeError("V2.43.30 final result drifted")
    return dict(value)


def build_final_result(
    root: Path,
    protocol: Mapping[str, Any],
    *,
    created_at_unix: int | None = None,
) -> dict[str, Any]:
    """Recompute and seal the final publication without running an evaluator."""

    recomputed = _recompute_final(root, protocol)
    barrier = recomputed["barrier"]
    live = recomputed["live"]
    result = {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "status": (
            "public_exact220_pair_go"
            if recomputed["decision"]["passed"]
            else "public_exact220_pair_no_go"
        ),
        "selected_pair_tasks": SELECTED_COUNT,
        "prediction_rows_per_arm": {arm: SELECTED_COUNT for arm in ARMS},
        "failure_as_zero": True,
        "both_arm_exact220_prediction_freeze_before_evaluator": True,
        "metrics": recomputed["metrics"],
        "test156_paired_uncertainty": recomputed["uncertainty"],
        "mechanism": {
            key: barrier["pair"][key] for key in MECHANISM_KEYS
        },
        "efficiency": {
            "shared_pair_forward_wall_seconds": barrier["forward"][
                "forward_wall_seconds"
            ],
            "both_arm_evaluator_parallel_wall_seconds": recomputed[
                "evaluator_parallel_wall_seconds"
            ],
            "forward_executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "evaluator_workers_total": TOTAL_EVALUATOR_WORKERS,
        },
        "decision": recomputed["decision"],
        "claims": dict(RESULT_CLAIMS),
        "source_policy": dict(RESULT_SOURCE_POLICY),
        "authorization": dict(RESULT_AUTHORIZATION),
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "evaluator_gate_sha256": sha256(root / EVALUATOR_GATE),
            "evaluator_start_sha256": sha256(root / EVALUATOR_START),
            "pair_summary_sha256": sha256(root / PAIR_SUMMARY),
            "both_arm_prediction_freeze_sha256": {
                arm: sha256(root / PREDICTION_FREEZE[arm]) for arm in ARMS
            },
            "both_arm_runtime_predictions_sha256": {
                arm: sha256(root / RUNTIME_PREDICTIONS[arm]) for arm in ARMS
            },
            "both_arm_run_summary_sha256": {
                arm: sha256(root / RUN_SUMMARY[arm]) for arm in ARMS
            },
            "both_arm_terminal_outcomes_sha256": {
                arm: sha256(root / JOINED[arm]) for arm in ARMS
            },
            "both_arm_official_predictions_sha256": {
                arm: sha256(root / OFFICIAL[arm]) for arm in ARMS
            },
            "both_arm_prepare_attestation_sha256": {
                arm: sha256(root / PREPARE[arm]) for arm in ARMS
            },
            "both_arm_merged_eval_results_sha256": {
                arm: sha256(root / MERGED[arm]) for arm in ARMS
            },
            "both_arm_merge_attestation_sha256": {
                arm: sha256(root / MERGE[arm]) for arm in ARMS
            },
            "both_arm_conservative_summary_sha256": {
                arm: sha256(root / SUMMARY[arm]) for arm in ARMS
            },
            "mapping_sha256": live["mapping_sha256"],
            "query_data_sha256": live["query_data_sha256"],
            "answer_corpus_manifest_sha256": live[
                "answer_corpus_manifest_sha256"
            ],
            "evaluator_source_manifest_sha256": live[
                "evaluator_source_manifest_sha256"
            ],
            "judge": live["judge"],
            "recovery_policy": live["recovery_policy"],
        },
    }
    result["result_payload_sha256"] = payload_sha256(result)
    validate_final_result(root, protocol, result)
    return result


def build_postaudit(
    root: Path,
    result: Mapping[str, Any],
    *,
    now: int | None = None,
) -> dict[str, Any]:
    protocol = validate_protocol(root)
    validate_final_result(root, protocol, result)
    lease = lease_observation(root, Path("/proc"))
    contract = validate_forward_contract(root)
    findings: list[str] = []
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active_after_result")
    if protected_watcher_snapshot() != contract["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    if _process_present(RUNNER_MARKER):
        findings.append("forward_runner_present_after_result")
    if _process_present(EVALUATOR_RUNNER_MARKER):
        findings.append("evaluator_worker_present_after_result")
    merge_terminal = all(
        read_object(root / MERGE[arm]).get(
            "all_completed_predictions_evaluated_or_terminal_error_exactly_once"
        )
        is True
        for arm in ARMS
    )
    if not merge_terminal:
        findings.append("evaluator_merge_not_terminal")
    value = {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "findings": findings,
        "audit_valid": not findings,
        "execution_closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers_unchanged": protected_watcher_snapshot()
            == contract["execution"]["protected_watchers"],
            "forward_runner_present": _process_present(RUNNER_MARKER),
            "evaluator_worker_present": _process_present(EVALUATOR_RUNNER_MARKER),
            "both_arm_evaluator_workers_terminal": merge_terminal,
            "both_arm_220_prediction_freeze_before_evaluator": True,
            "additional_forward_resume_retry_skip_or_rerun": False,
            "selective_evaluator_retry_or_revaluation": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "result_status": result["status"],
        "decision_status": result["decision"]["status"],
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "forward_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "mapping_opened_only_after_both_exact220_prediction_freezes": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "authorization": {
            "additional_rollout_or_avg4": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "forward_result_sha256": sha256(root / FORWARD_RESULT),
            "evaluator_gate_sha256": sha256(root / EVALUATOR_GATE),
            "evaluator_start_sha256": sha256(root / EVALUATOR_START),
            "final_result_sha256": sha256(root / FINAL_RESULT),
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_postaudit(root, value, result=result)
    return value


def validate_postaudit(
    root: Path,
    value: Mapping[str, Any],
    *,
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    frozen_result = (
        dict(result) if result is not None else read_object(root / FINAL_RESULT)
    )
    protocol = validate_protocol(root)
    validate_final_result(root, protocol, frozen_result)
    unsigned = dict(value)
    seal = unsigned.pop("audit_payload_sha256", None)
    closure = value.get("execution_closure")
    expected_provenance = {
        "protocol_sha256": sha256(root / PROTOCOL),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "evaluator_gate_sha256": sha256(root / EVALUATOR_GATE),
        "evaluator_start_sha256": sha256(root / EVALUATOR_START),
        "final_result_sha256": sha256(root / FINAL_RESULT),
    }
    if (
        set(value)
        != {
            "artifact_version", "role", "protocol_id", "created_at_unix",
            "findings", "audit_valid", "execution_closure", "result_status",
            "decision_status", "source_policy", "authorization", "provenance",
            "audit_payload_sha256",
        }
        or value.get("artifact_version") != 1
        or value.get("role")
        != "v24330_shared_prefix_exact220_postresult_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or not isinstance(closure, Mapping)
        or set(closure)
        != {
            "shared_api_lease_active", "protected_watchers_unchanged",
            "forward_runner_present", "evaluator_worker_present",
            "both_arm_evaluator_workers_terminal",
            "both_arm_220_prediction_freeze_before_evaluator",
            "additional_forward_resume_retry_skip_or_rerun",
            "selective_evaluator_retry_or_revaluation",
            "credential_value_persisted_hashed_or_emitted",
        }
        or closure.get("shared_api_lease_active") is not False
        or closure.get("protected_watchers_unchanged") is not True
        or closure.get("forward_runner_present") is not False
        or closure.get("evaluator_worker_present") is not False
        or closure.get("both_arm_evaluator_workers_terminal") is not True
        or closure.get("both_arm_220_prediction_freeze_before_evaluator") is not True
        or closure.get("additional_forward_resume_retry_skip_or_rerun") is not False
        or closure.get("selective_evaluator_retry_or_revaluation") is not False
        or closure.get("credential_value_persisted_hashed_or_emitted") is not False
        or value.get("result_status") != frozen_result["status"]
        or value.get("decision_status") != frozen_result["decision"]["status"]
        or value.get("source_policy") != RESULT_SOURCE_POLICY
        or value.get("authorization") != RESULT_AUTHORIZATION
        or value.get("provenance") != expected_provenance
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.30 postresult audit drifted")
    return dict(value)


def recover_postaudit(root: Path = ROOT) -> dict[str, Any]:
    """Recover only a missing audit; never prepare, evaluate, merge, or rerun."""

    root = root.resolve()
    if not (root / FINAL_RESULT).is_file():
        raise RuntimeError("V2.43.30 final result is absent")
    if (root / POSTAUDIT).exists() or (root / POSTAUDIT).is_symlink():
        raise RuntimeError("V2.43.30 postresult audit already exists")
    if _process_present(EVALUATOR_RUNNER_MARKER):
        raise RuntimeError("V2.43.30 evaluator worker is still active")
    result = read_object(root / FINAL_RESULT)
    validate_final_result(root, validate_protocol(root), result)
    audit = build_postaudit(root, result)
    _new_json(root / POSTAUDIT, audit)
    validate_postaudit(root, read_object(root / POSTAUDIT))
    return audit


def seal_completed_evaluation(root: Path = ROOT) -> dict[str, Any]:
    """Seal already-terminal evaluator artifacts without any remote effect."""

    root = root.resolve()
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (FINAL_RESULT, POSTAUDIT)
    ):
        raise RuntimeError("V2.43.30 final publication surface is not pristine")
    if not (root / EVALUATOR_ROOT).is_dir():
        raise RuntimeError("V2.43.30 completed evaluator artifacts are absent")
    if _process_present(EVALUATOR_RUNNER_MARKER):
        raise RuntimeError("V2.43.30 evaluator worker is still active")
    if lease_observation(root, Path("/proc")).get("active") is not False:
        raise RuntimeError("V2.43.30 shared API lease is still active")
    protocol = validate_protocol(root)
    validate_evaluator_start(root)
    result = build_final_result(root, protocol)
    validate_final_result(root, protocol, result)
    _new_json(root / FINAL_RESULT, result)
    audit = build_postaudit(root, result)
    _new_json(root / POSTAUDIT, audit)
    validate_postaudit(root, read_object(root / POSTAUDIT))
    return result


def finalize(
    root: Path = ROOT,
    *,
    command_runner: Callable[..., subprocess.CompletedProcess[Any]] = subprocess.run,
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_evaluator_start(root)
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (FINAL_RESULT, POSTAUDIT, EVALUATOR_ROOT)
    ):
        raise RuntimeError("V2.43.30 evaluator result surface is not pristine")
    if (
        _git_output(root, "rev-parse", "HEAD")
        != _git_output(root, "rev-parse", "target/main")
        or _git_output(root, "status", "--porcelain")
        or not _git_path_tracked(root, EVALUATOR_START)
    ):
        raise RuntimeError("V2.43.30 evaluator-start is not committed and pushed")
    with acquire_deepwide_api_lease(
        root,
        owner=EVALUATOR_LEASE_OWNER,
        purpose=EVALUATOR_LEASE_PURPOSE,
        path=root / LEASE_PATH,
    ):
        barrier = validate_forward_barrier(root)
        validate_live_evaluator_identity(root, protocol)
        prepared = {
            arm: prepare_arm(root, protocol, barrier, arm) for arm in ARMS
        }
        evaluated = run_all_evaluators(
            root, protocol, prepared, command_runner=command_runner
        )
        for arm in ARMS:
            summary = summarize_rollout(
                prepared[arm]["joined"],
                evaluated["arms"][arm]["rows"],
                rollout_id=1,
            )
            _new_json(root / SUMMARY[arm], summary)
        result = build_final_result(root, protocol)
        validate_final_result(root, protocol, result)
        _new_json(root / FINAL_RESULT, result)
    audit = build_postaudit(root, result)
    _new_json(root / POSTAUDIT, audit)
    validate_postaudit(root, read_object(root / POSTAUDIT))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("gate", "start", "run", "seal", "audit")
    )
    args = parser.parse_args()
    if args.command == "gate":
        publish(ROOT / EVALUATOR_GATE, build_evaluator_gate(ROOT))
    elif args.command == "start":
        publish(ROOT / EVALUATOR_START, build_evaluator_start(ROOT))
    elif args.command == "run":
        value = finalize(ROOT)
        print(
            json.dumps(
                {
                    "result": str(FINAL_RESULT),
                    "status": value["status"],
                    "failed_checks": value["decision"]["failed_checks"],
                },
                sort_keys=True,
            )
        )
        return
    elif args.command == "seal":
        value = seal_completed_evaluation(ROOT)
        print(
            json.dumps(
                {
                    "result": str(FINAL_RESULT),
                    "status": value["status"],
                    "recovered_without_evaluator_rerun": True,
                },
                sort_keys=True,
            )
        )
        return
    else:
        value = recover_postaudit(ROOT)
        print(
            json.dumps(
                {
                    "audit": str(POSTAUDIT),
                    "status": "valid" if value["audit_valid"] else "invalid",
                },
                sort_keys=True,
            )
        )
        return
    print(json.dumps({"command": args.command, "status": "ok"}, sort_keys=True))


if __name__ == "__main__":
    main()
