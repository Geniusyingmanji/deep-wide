#!/usr/bin/env python3
"""Post-freeze, pre-evaluator audit for V2.46.79/V2.46.82 forward."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24679_schema_dev64_contract as contract  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
    validate_parent_receipt,
)
from scripts import run_v24679_schema_dev64 as runner  # noqa: E402
from scripts import v24679_schema_dev64_control as protocol_control  # noqa: E402
from scripts import v24682_v24679_schema_dev64_recovery_control as recovery  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260806"
AUDIT = contract.FORWARD_AUDIT
RECOVERY_SESSION = recovery.RECOVERY_SESSION
FORWARD_LOG = Path(
    f"outputs/v24682_v24679_schema_dev64_recovery_runner_v1_{DATE}.log"
)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == contract.payload_sha256(unsigned)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _active(marker: str) -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "cmd="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    return any(
        marker in line
        for line in completed.stdout.splitlines()
        if "ps -eo" not in line and "audit_v24683" not in line
    )


def _session_absent() -> bool:
    return subprocess.run(
        ["tmux", "has-session", "-t", RECOVERY_SESSION],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode != 0


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.46.83 expected ordinary JSONL: {path}")
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise RuntimeError("V2.46.83 expected JSONL object")
        rows.append(value)
    return rows


def _read(path: Path) -> dict[str, Any]:
    return contract.read_object(ROOT / path)


def _validate_freeze(
    arm: str,
    selected_ids: list[str],
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, Any]]:
    rows = _read_jsonl(ROOT / contract.RUNTIME_PREDICTIONS[arm])
    for row in rows:
        runner.validate_runtime_row(row, arm)
    summary = _read(contract.RUN_SUMMARY[arm])
    freeze = _read(contract.PREDICTION_FREEZE[arm])
    if (
        len(rows) != contract.SELECTED_COUNT
        or [row["opaque_id"] for row in rows] != selected_ids
        or any(row["status"] != "completed" or not row["prediction"] for row in rows)
        or summary.get("role") != "v24679_schema_dev64_run_summary"
        or summary.get("arm") != arm
        or summary.get("selected") != contract.SELECTED_COUNT
        or summary.get("completed") != contract.SELECTED_COUNT
        or summary.get("failed") != 0
        or summary.get("runtime_failures") != 0
        or summary.get("fallback_tables") != 0
        or not _sealed(summary, "summary_payload_sha256")
        or freeze.get("role") != "v24679_schema_dev64_prediction_freeze"
        or freeze.get("arm") != arm
        or freeze.get("selected") != contract.SELECTED_COUNT
        or freeze.get("terminal") != contract.SELECTED_COUNT
        or freeze.get("runtime_predictions_sha256")
        != contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS[arm])
        or freeze.get("run_summary_sha256")
        != contract.sha256(ROOT / contract.RUN_SUMMARY[arm])
        or freeze.get("prediction_hashes_sha256")
        != contract.payload_sha256([row["prediction_sha256"] for row in rows])
        or freeze.get("both_arms_terminal_before_mapping_gold_or_evaluator_open")
        is not True
        or freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is not False
        or freeze.get("label_blind") is not True
        or not _sealed(freeze, "freeze_payload_sha256")
    ):
        raise RuntimeError(f"V2.46.83 {arm} prediction freeze drifted")
    return rows, summary, freeze


def _task_receipts() -> dict[str, Any]:
    real = []
    for position in range(1, contract.SELECTED_COUNT + 1):
        real.append(("baseline", position))
    treated_positions: list[int] = []
    forward = contract.validate_forward_contract(ROOT)
    for position, task in enumerate(contract.selected_tasks(ROOT, forward), start=1):
        if contract.is_treated_task(task):
            treated_positions.append(position)
            real.append(("candidate", position))
    if len(treated_positions) != contract.EXPECTED_TREATED_COUNT:
        raise RuntimeError("V2.46.83 treated position count drifted")
    parent_successes = child_terminals = model = transport = single = backfill = 0
    for arm, position in real:
        directory = ROOT / contract.TASK_ROOT / arm / f"task_{position:04d}"
        parent = validate_parent_receipt(
            contract.read_object(directory / contract.PARENT_EXIT_NAME)
        )
        if parent["failure_taxonomy"] == "success":
            parent_successes += 1
        validate_child_receipt(
            contract.read_object(directory / contract.CHILD_TERMINAL_NAME)
        )
        child_terminals += 1
        for name, validator, counter in (
            (runner.RECEIPT_NAME, lambda value: runner.validate_model(value, expected_cap=contract.MODEL_SLOT_CAP), "model"),
            (runner.TRANSPORT_NAME, runner.validate_transport_health, "transport"),
            (runner.SINGLE_NAME, runner.validate_single, "single"),
            (runner.BACKFILL_NAME, runner.validate_backfill, "backfill"),
        ):
            value = contract.read_object(directory / name)
            validator(value)
            if counter == "model":
                model += 1
            elif counter == "transport":
                transport += 1
            elif counter == "single":
                single += 1
            else:
                backfill += 1
    return {
        "real_child_runs": len(real),
        "treated_positions_count": len(treated_positions),
        "parent_successes": parent_successes,
        "valid_child_terminal_receipts": child_terminals,
        "valid_model_receipts": model,
        "valid_transport_receipts": transport,
        "valid_single_shot_receipts": single,
        "valid_backfill_receipts": backfill,
    }


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    forward_contract = contract.validate_forward_contract(ROOT)
    protocol = protocol_control.validate_protocol(ROOT)
    start = recovery.validate_execution_start()
    forward = _read(contract.FORWARD_RESULT)
    pair = _read(contract.PAIR_SUMMARY)
    selected = forward_contract["task_contract"]["selected_opaque_ids"]
    arms: dict[str, Any] = {}
    for arm in contract.ARMS:
        rows, summary, freeze = _validate_freeze(arm, selected)
        arms[arm] = {"rows": rows, "summary": summary, "freeze": freeze}
    baseline = arms["baseline"]["rows"]
    candidate = arms["candidate"]["rows"]
    changed = sum(
        left["prediction_sha256"] != right["prediction_sha256"]
        for left, right in zip(baseline, candidate, strict=True)
    )
    reused = sum(row["candidate_reused_same_run_baseline"] for row in candidate)
    reused_exact = sum(
        right["candidate_reused_same_run_baseline"]
        and left["prediction_sha256"] == right["prediction_sha256"]
        and left["completion_kind"] == right["completion_kind"]
        and left["cost"] == right["cost"]
        for left, right in zip(baseline, candidate, strict=True)
    )
    child = _task_receipts()
    lease = lease_observation(ROOT, Path("/proc"))
    active = any(
        _active(marker)
        for marker in (
            contract.RUNNER_MARKER,
            contract.CHILD_MARKER,
            str(recovery.WRAPPER),
        )
    )
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = _tracked(contract.FORWARD_RESULT)
    watchers = contract.protected_watcher_snapshot()
    log = (ROOT / FORWARD_LOG).read_text(encoding="utf-8")
    log_terminal = (
        f'"changed_candidate_tasks": {changed}' in log
        and '"real_child_runs": 72' in log
        and '"terminal_per_arm": 64' in log
    )
    forward_valid = (
        forward.get("role") == "v24679_schema_dev64_forward_result"
        and forward.get("selected_pair_tasks") == contract.SELECTED_COUNT
        and forward.get("terminal_prediction_rows_per_arm")
        == {arm: contract.SELECTED_COUNT for arm in contract.ARMS}
        and forward.get("real_child_runs") == contract.TOTAL_CHILD_RUNS
        and forward.get("changed_candidate_tasks") == changed
        and forward.get("baseline_runtime_failures") == 0
        and forward.get("candidate_runtime_failures") == 0
        and forward.get("pair_summary_sha256")
        == contract.sha256(ROOT / contract.PAIR_SUMMARY)
        and forward.get("prediction_freeze_sha256")
        == {
            arm: contract.sha256(ROOT / contract.PREDICTION_FREEZE[arm])
            for arm in contract.ARMS
        }
        and forward.get("execution_start_sha256")
        == contract.sha256(ROOT / recovery.EXECUTION_START)
        and forward.get("both_arms_exact64_before_mapping_gold_or_evaluator_open")
        is True
        and forward.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is False
        and forward.get("official_evaluator_called") is False
        and forward.get("resume_retry_skip_or_selective_rerun") is False
        and _sealed(forward, "result_payload_sha256")
    )
    pair_valid = (
        pair.get("role") == "v24679_schema_dev64_pair_summary"
        and pair.get("real_child_runs") == contract.TOTAL_CHILD_RUNS
        and pair.get("expected_real_child_runs") == contract.TOTAL_CHILD_RUNS
        and pair.get("changed_candidate_tasks") == changed
        and pair.get("same_run_baseline_reused_candidate_tasks") == reused
        and pair.get("baseline_runtime_failures") == 0
        and pair.get("candidate_runtime_failures") == 0
        and pair.get("accepted_real_child_successes") == contract.TOTAL_CHILD_RUNS
        and pair.get("valid_model_receipts") == contract.TOTAL_CHILD_RUNS
        and pair.get("valid_transport_receipts") == contract.TOTAL_CHILD_RUNS
        and pair.get("valid_single_shot_receipts") == contract.TOTAL_CHILD_RUNS
        and pair.get("valid_backfill_receipts") == contract.TOTAL_CHILD_RUNS
        and pair.get("model_slot_timeouts") == 0
        and pair.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is False
        and pair.get("official_evaluator_called") is False
        and pair.get("resume_retry_skip_or_selective_rerun") is False
        and _sealed(pair, "summary_payload_sha256")
    )
    decision = protocol["decision_contract"]
    reliability_gate = (
        changed >= decision["minimum_changed_candidate_tasks_for_evaluator_gate"]
        and pair["baseline_runtime_failures"]
        <= decision["maximum_baseline_runtime_failures_for_evaluator_gate"]
        and pair["candidate_runtime_failures"]
        <= decision["maximum_candidate_runtime_failures_for_evaluator_gate"]
        and contract.TOTAL_CHILD_RUNS - pair["accepted_real_child_successes"]
        <= decision["maximum_real_child_runtime_failures_for_evaluator_gate"]
        and pair["model_slot_timeouts"]
        <= decision["maximum_model_slot_timeouts_for_evaluator_gate"]
    )
    findings: list[str] = []
    if not forward_valid:
        findings.append("forward_result_drifted")
    if not pair_valid:
        findings.append("pair_summary_drifted")
    if reused != 56 or reused_exact != 56:
        findings.append("same_run_baseline_reuse_not_exact")
    if any(value != contract.TOTAL_CHILD_RUNS for key, value in child.items() if key not in {"treated_positions_count"}):
        findings.append("real_child_receipt_or_success_count_drifted")
    if child["treated_positions_count"] != contract.EXPECTED_TREATED_COUNT:
        findings.append("treated_position_count_drifted")
    if not reliability_gate:
        findings.append("postforward_reliability_gate_failed")
    if not log_terminal:
        findings.append("runner_terminal_log_drifted")
    if head != remote:
        findings.append("forward_result_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if not tracked:
        findings.append("forward_result_not_tracked")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("forward_or_recovery_process_active")
    if not _session_absent():
        findings.append("recovery_tmux_session_active")
    if watchers != forward_contract["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24683_v24679_schema_dev64_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "pair_summary_sha256": contract.sha256(ROOT / contract.PAIR_SUMMARY),
        "prediction_freeze_sha256": {
            arm: contract.sha256(ROOT / contract.PREDICTION_FREEZE[arm])
            for arm in contract.ARMS
        },
        "runtime_predictions_sha256": {
            arm: contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS[arm])
            for arm in contract.ARMS
        },
        "recovery_execution_start_sha256": contract.sha256(
            ROOT / recovery.EXECUTION_START
        ),
        "forward": {
            "selected_pair_tasks": contract.SELECTED_COUNT,
            "terminal_prediction_rows_per_arm": {
                arm: contract.SELECTED_COUNT for arm in contract.ARMS
            },
            "real_child_runs": contract.TOTAL_CHILD_RUNS,
            "incremental_schema_tasks": contract.EXPECTED_TREATED_COUNT,
            "same_run_baseline_reused_candidate_tasks": reused,
            "same_run_baseline_exact_reuse_tasks": reused_exact,
            "changed_candidate_tasks": changed,
            "baseline_runtime_failures": pair["baseline_runtime_failures"],
            "candidate_runtime_failures": pair["candidate_runtime_failures"],
            "model_slot_timeouts": pair["model_slot_timeouts"],
            "forward_wall_seconds": forward["forward_wall_seconds"],
            "forward_result_valid": forward_valid,
            "pair_summary_valid": pair_valid,
            "runner_terminal_log_valid": log_terminal,
        },
        "real_child_receipts": child,
        "reliability_gate": {
            "decision_contract": decision,
            "passed": reliability_gate,
        },
        "runtime_state": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "forward_result_tracked": tracked,
            "shared_api_lease_active": lease.get("active"),
            "forward_or_recovery_process_active": active,
            "recovery_tmux_session_absent": _session_absent(),
            "protected_watchers": watchers,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "both_arm_predictions_frozen_before_mapping_gold_or_evaluator_open": True,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_opened_hashed_or_imported_by_forward": False,
            "official_evaluator_called": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "claims": {
            "development_population_not_unseen": True,
            "benchmark_score_available": False,
            "public_full220_result": False,
            "sota": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "postfreeze_evaluator_gate_design": not findings,
            "evaluator_resource_open_or_execution": False,
            "additional_forward_resume_retry_or_rerun": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24683_v24679_schema_dev64_forward_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("forward", {}).get("selected_pair_tasks")
        != contract.SELECTED_COUNT
        or copied.get("forward", {}).get("real_child_runs")
        != contract.TOTAL_CHILD_RUNS
        or copied.get("forward", {}).get("same_run_baseline_exact_reuse_tasks") != 56
        or copied.get("forward", {}).get("changed_candidate_tasks") != 7
        or copied.get("forward", {}).get("baseline_runtime_failures") != 0
        or copied.get("forward", {}).get("candidate_runtime_failures") != 0
        or copied.get("forward", {}).get("model_slot_timeouts") != 0
        or copied.get("reliability_gate", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_active") is not False
        or copied.get("runtime_state", {}).get("forward_or_recovery_process_active")
        is not False
        or copied.get("runtime_state", {}).get("recovery_tmux_session_absent")
        is not True
        or copied.get("source_policy", {}).get("official_evaluator_called") is not False
        or copied.get("claims", {}).get("benchmark_score_available") is not False
        or copied.get("claims", {}).get("sota") is not False
        or copied.get("authorization")
        != {
            "postfreeze_evaluator_gate_design": True,
            "evaluator_resource_open_or_execution": False,
            "additional_forward_resume_retry_or_rerun": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.83 forward audit drifted")
    return copied


def publish(path: Path, value: Mapping[str, Any]) -> None:
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
    audit = build_audit()
    validate_audit(audit)
    publish(ROOT / AUDIT, audit)
    print(
        json.dumps(
            {
                "path": str(AUDIT),
                "audit_valid": audit["audit_valid"],
                "findings": audit["findings"],
                "changed_candidate_tasks": audit["forward"]["changed_candidate_tasks"],
            },
            sort_keys=True,
        )
    )
