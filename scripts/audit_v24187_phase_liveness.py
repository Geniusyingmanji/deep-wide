#!/usr/bin/env python3
"""Phase-aware, label-blind liveness audit for the DeepWide campaign.

Only attested safe state envelopes, file metadata, exact executable identity,
and the shared lease record are consumed.  Benchmark task state, questions,
answers, evidence, predictions, mapping/gold, evaluator artifacts, scores,
credentials, and network resources are outside this audit's input surface.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
ROLE = "v24187_phase_liveness_audit"
OPAQUE_ID = re.compile(r"task_[0-9a-f]{24}")
CREDENTIAL_LIKE = re.compile(
    r"(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)

R1_STATE = "outputs/v24118_r1_finalization_watchdog_state_v1_20260728.json"
CAPACITY_STATE = "outputs/v24164_scope_capacity_liveness_state_v1_20260729.json"
AVG4_GUARD_STATE = "outputs/v24155_avg4_after_scope_combined_watcher_state_v1_20260729.json"
AVG4_STATE = "outputs/v2410_rank_slot_official_avg4_v8_watcher_state.json"
PAIRED_STATE = "outputs/v24107_paired_dev_liveness_watcher_state_v1_20260729.json"
SCHEMA77_STATE = "outputs/v24176_predicate_completion_paired_dev_watcher_state_v1_20260730.json"
SEARCH_LAUNCH_STATE = "outputs/v24183_search_yield_launcher_state_v1_20260730.json"
SEARCH_STATE = "outputs/v24180_predicate_search_yield_watcher_state_v1_20260730.json"
MARKDOWN_LAUNCH_STATE = "outputs/v24185_markdown_priority_launcher_state_v1_20260730.json"
MARKDOWN_STATE = "outputs/v24103_markdown_paired_dev_watcher_state_v1_20260728.json"
SCOPE_STATE = "outputs/v24105_scope_open_paired_dev_watcher_state_v1_20260729.json"
OWIC_LAUNCH_STATE = "outputs/v24186_owic_after_quality_chain_launcher_state_v1_20260730.json"
OWIC_STATE = "outputs/v2411_post_p12_owic_watcher_state_v8_20260727.json"
TAXONOMY_STATE = "outputs/v2410_p13_failure_taxonomy_v2_watcher_state.json"
LEADERBOARD_STATE = "outputs/v2410_leaderboard_postprocess_v4_watcher_state.json"
HANDOFF_STATE = "outputs/v24110_leaderboard_handoff_watcher_state_v1_20260728.json"
LEASE = "outputs/deepwide_benchmark_api.lease.lock"

R1_TERMINAL = {
    "complete_existing_release_pair",
    "complete_recovered_release_pair",
}
SCHEMA77_TERMINAL = {"complete_paired_dev_go", "complete_paired_dev_no_go"}
SEARCH_TERMINAL = {
    "complete_search_yield_go",
    "complete_search_yield_no_go",
    "terminal_incomplete_attempt_no_rerun",
}
MARKDOWN_TERMINAL = {"complete_paired_dev_go", "complete_paired_dev_no_go"}
SCOPE_TERMINAL = {
    "complete_paired_dev_go",
    "complete_paired_dev_no_go",
    "complete_parent_v24103_no_go_no_p12_3_api",
}
OWIC_TERMINAL = {"gate1_no_go", "gate1_go_interventions_pending"}
TAXONOMY_ALLOWED = {
    "monitoring_all_failures_covered_or_excluded",
    "monitoring_uncovered_singleton_no_p13",
    "repeated_uncovered_evidence_requires_manual_audit",
    "waiting_for_consistent_forward_snapshot",
}


@dataclass(frozen=True)
class ExecutorSpec:
    name: str
    markers: tuple[str, ...]
    python_flags_required: bool = True


EXECUTORS = {
    "r1_finalization": ExecutorSpec(
        "r1_finalization", ("scripts/watch_v24118_r1_finalization.py",)
    ),
    "capacity_liveness": ExecutorSpec(
        "capacity_liveness", ("scripts/watch_v24164_scope_capacity_liveness.py",)
    ),
    "paired_liveness": ExecutorSpec(
        "paired_liveness", ("scripts/watch_v24107_paired_dev_liveness.py",)
    ),
    "schema77": ExecutorSpec(
        "schema77", ("scripts/watch_v24176_predicate_completion_paired_dev.py",)
    ),
    "search_yield": ExecutorSpec(
        "search_yield",
        (
            "scripts/launch_v24183_search_yield_after_schema77.py",
            "scripts/exec_v24183_isolated_v24180.py",
            "scripts/watch_v24180_predicate_search_yield.py",
        ),
    ),
    "markdown": ExecutorSpec(
        "markdown",
        (
            "scripts/launch_v24185_markdown_after_search_yield.py",
            "scripts/watch_v24103_markdown_paired_dev.py",
        ),
    ),
    "scope_open": ExecutorSpec(
        "scope_open", ("scripts/watch_v24105_scope_open_paired_dev.py",)
    ),
    "owic": ExecutorSpec(
        "owic",
        (
            "scripts/launch_v24186_owic_after_quality_chain.py",
            "scripts/watch_v24116_post_p12_owic.py",
        ),
    ),
    "taxonomy": ExecutorSpec(
        "taxonomy", ("scripts/watch_v2410_failure_taxonomy_v2.py",), False
    ),
    "leaderboard": ExecutorSpec(
        "leaderboard", ("scripts/watch_v2410_leaderboard_readiness.py",)
    ),
    "handoff": ExecutorSpec(
        "handoff",
        (
            "scripts/watch_v24114_scheduling_disclosure_handoff.py",
            "scripts/watch_v24110_leaderboard_handoff.py",
        ),
    ),
}


EXPECTED_LEASE_OWNERS = {
    "v24118_r1_finalization_recovery_v1",
    "v2410_rank_slot_p12_dev64_gate_parallel_test156_v4",
    "v24154_p12_vs_scope_combined_dev64_exact220_v1",
    "v2410_rank_slot_official_avg4_v8",
    "v24176_schema76_vs_schema77_predicate_completion_dev64_v1",
    "v24180_specific_vs_shared_predicate_search_yield_v1",
    "v24103_p12_vs_p12_2_post_avg4_paired_dev64_v1",
    "v24105_p12_2_vs_p12_3_scope_open_paired_dev64_v1",
    "v24125_true_continuation_release_truth_liveness_v1",
    "v2411_post_p12_owic_capture_v8",
    "v2412_post_gate1_equal_cost_interventions_v1",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _canonical_file(root: Path, relative: str) -> Path:
    raw = root / relative
    path = raw.resolve(strict=False)
    if (
        path != raw.absolute()
        or raw.is_symlink()
        or not path.is_file()
        or not path.is_relative_to(root)
    ):
        raise RuntimeError(f"V2.41.87 safe source is noncanonical: {relative}")
    return path


def _read(root: Path, relative: str) -> tuple[dict[str, Any], Path]:
    path = _canonical_file(root, relative)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.41.87 safe source is not an object: {relative}")
    return value, path


def process_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    if not proc_root.is_dir():
        raise RuntimeError("V2.41.87 proc root is unavailable")
    rows: list[dict[str, Any]] = []
    for child in proc_root.iterdir():
        if not child.name.isdigit() or not child.is_dir():
            continue
        try:
            argv = [
                item.decode("utf-8", errors="replace")
                for item in (child / "cmdline").read_bytes().split(b"\0")
                if item
            ]
        except OSError:
            continue
        if argv:
            rows.append({"pid": int(child.name), "argv": argv})
    return rows


def actual_python_script(argv: list[str]) -> str | None:
    if not argv:
        return None
    if Path(argv[0]).name.endswith(".py"):
        return argv[0]
    python_index = next(
        (
            index
            for index, token in enumerate(argv)
            if re.fullmatch(r"(?:python|python3|python3\.\d+)", Path(token).name)
        ),
        None,
    )
    if python_index is None:
        return None
    index = python_index + 1
    value_flags = {"-W", "-X", "--check-hash-based-pycs"}
    while index < len(argv):
        token = argv[index]
        if token == "--":
            index += 1
            return argv[index] if index < len(argv) and argv[index].endswith(".py") else None
        if token in {"-b", "-B", "-d", "-E", "-h", "-i", "-I", "-O", "-OO", "-P", "-q", "-s", "-S", "-u", "-v", "-V"}:
            index += 1
            continue
        if token in value_flags:
            index += 2
            continue
        if token in {"-c", "-m"}:
            return None
        if token.startswith("-"):
            index += 1
            continue
        return token if token.endswith(".py") else None
    return None


def executor_report(
    rows: Iterable[dict[str, Any]], spec: ExecutorSpec
) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    for row in rows:
        argv = [str(value) for value in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is None:
            continue
        if any(script == marker or script.endswith("/" + marker) for marker in spec.markers):
            matches.append(row)
    return {
        "present": bool(matches),
        "match_count": len(matches),
        "pids": sorted(int(row["pid"]) for row in matches),
        "isolated_no_bytecode_count": sum(
            "-I" in (row.get("argv") or []) and "-B" in (row.get("argv") or [])
            for row in matches
        ),
        "python_flags_required": spec.python_flags_required,
        "command_lines_emitted": False,
    }


def _age(path: Path, now: int) -> int:
    return max(0, now - int(path.stat().st_mtime))


def _phase_state(
    relative: str,
    value: dict[str, Any],
    path: Path,
    *,
    now: int,
    freshness_seconds: int,
    phase: str,
    terminal: bool,
    process: dict[str, Any],
    valid: bool,
    active_lease_pid: int | None = None,
) -> tuple[dict[str, Any], list[str]]:
    age = _age(path, now)
    owner_exemption = bool(
        not terminal
        and active_lease_pid is not None
        and active_lease_pid in process.get("pids", [])
    )
    findings: list[str] = []
    if not valid:
        findings.append("safe_state_contract")
    if not terminal and age > freshness_seconds and not owner_exemption:
        findings.append("state_stale")
    if not terminal and process.get("match_count") != 1:
        findings.append("executor_process_identity")
    if terminal and process.get("match_count", 0) > 1:
        findings.append("terminal_executor_duplicate")
    if (
        process.get("python_flags_required")
        and process.get("isolated_no_bytecode_count") != process.get("match_count")
    ):
        findings.append("executor_python_flags")
    return {
        "path": relative,
        "phase": phase,
        "status": value.get("status"),
        "terminal": terminal,
        "mtime_unix": int(path.stat().st_mtime),
        "age_seconds": age,
        "freshness_seconds": freshness_seconds,
        "fresh": age <= freshness_seconds,
        "active_lease_owner_freshness_exemption": owner_exemption,
        "process": process,
        "valid": valid and not findings,
        "findings": sorted(set(findings)),
        "contents_emitted": False,
    }, findings


def _lease(root: Path, proc_root: Path) -> dict[str, Any]:
    path = root / LEASE
    if not path.exists() and not path.is_symlink():
        return {
            "present": False,
            "active": False,
            "ordinary": True,
            "consistent": True,
            "owner_registered": True,
            "pid": None,
            "contents_emitted": False,
        }
    if path.is_symlink() or not path.is_file():
        return {
            "present": True,
            "active": None,
            "ordinary": False,
            "consistent": False,
            "owner_registered": False,
            "pid": None,
            "contents_emitted": False,
        }
    with path.open("r", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            active = True
        else:
            active = False
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.seek(0)
        try:
            value = json.loads(handle.read(4096) or "{}")
        except json.JSONDecodeError:
            value = {}
    owner = value.get("owner")
    pid = value.get("pid")
    alive = isinstance(pid, int) and (proc_root / str(pid)).is_dir()
    return {
        "present": True,
        "active": active,
        "ordinary": True,
        "consistent": bool(not active or (alive and isinstance(owner, str) and owner)),
        "owner_registered": bool(not active or owner in EXPECTED_LEASE_OWNERS),
        "pid": pid if active and isinstance(pid, int) else None,
        "owner_emitted": False,
        "contents_emitted": False,
    }


def build_report(
    root: Path = ROOT,
    *,
    now: int | None = None,
    freshness_seconds: int = 180,
    transition_grace_seconds: int = 180,
    proc_root: Path = Path("/proc"),
    processes: list[dict[str, Any]] | None = None,
    protocol_record: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if freshness_seconds <= 0 or transition_grace_seconds <= 0:
        raise ValueError("V2.41.87 freshness and grace must be positive")
    root = root.resolve()
    created = int(time.time()) if now is None else int(now)
    rows = process_snapshot(proc_root) if processes is None else processes
    executors = {
        name: executor_report(rows, spec) for name, spec in EXECUTORS.items()
    }
    lease = _lease(root, proc_root)

    safe: dict[str, tuple[dict[str, Any], Path]] = {}
    for name, relative in {
        "r1": R1_STATE,
        "capacity": CAPACITY_STATE,
        "avg4_guard": AVG4_GUARD_STATE,
        "avg4": AVG4_STATE,
        "paired": PAIRED_STATE,
        "schema77": SCHEMA77_STATE,
        "search_launch": SEARCH_LAUNCH_STATE,
        "search": SEARCH_STATE,
        "markdown_launch": MARKDOWN_LAUNCH_STATE,
        "markdown": MARKDOWN_STATE,
        "scope": SCOPE_STATE,
        "owic_launch": OWIC_LAUNCH_STATE,
        "owic": OWIC_STATE,
        "taxonomy": TAXONOMY_STATE,
        "leaderboard": LEADERBOARD_STATE,
        "handoff": HANDOFF_STATE,
    }.items():
        safe[name] = _read(root, relative)

    r1, r1_path = safe["r1"]
    aggregate = r1.get("aggregate") or {}
    r1_status = r1.get("status")
    r1_terminal = r1_status in R1_TERMINAL
    if r1_status in {
        "critical_noncanonical_release_artifact",
        "critical_release_artifact_before_exact220",
        "critical_exact220_regressed_after_lease",
        "critical_finalization_recovery_failed",
    }:
        r1_terminal = False

    capacity, capacity_path = safe["capacity"]
    avg4_guard = safe["avg4_guard"][0]
    avg4 = safe["avg4"][0]
    capacity_terminal = bool(
        avg4.get("role") == "v2410_avg4_watcher_state"
        and avg4.get("status") == "complete_four_exact220_trials_local_pack"
        and str(avg4_guard.get("status") or "").startswith(
            "complete_delegated_complete_four_exact220_trials_local_pack"
        )
    )
    schema77, schema77_path = safe["schema77"]
    schema77_terminal = schema77.get("status") in SCHEMA77_TERMINAL
    search, search_path = safe["search"]
    search_terminal = search.get("status") in SEARCH_TERMINAL
    markdown, markdown_path = safe["markdown"]
    markdown_terminal = markdown.get("status") in MARKDOWN_TERMINAL
    scope, scope_path = safe["scope"]
    scope_terminal = scope.get("status") in SCOPE_TERMINAL
    owic, owic_path = safe["owic"]
    owic_terminal = owic.get("status") in OWIC_TERMINAL

    if not r1_terminal:
        current_phase, authority, value, path, terminal, executor = (
            "r1_full220",
            R1_STATE,
            r1,
            r1_path,
            False,
            "r1_finalization",
        )
    elif not capacity_terminal:
        current_phase, authority, value, path, terminal, executor = (
            "p12_schema76_and_official_avg4",
            CAPACITY_STATE,
            capacity,
            capacity_path,
            False,
            "capacity_liveness",
        )
    elif not schema77_terminal:
        current_phase, authority, value, path, terminal, executor = (
            "schema77_paired_dev64",
            SCHEMA77_STATE,
            schema77,
            schema77_path,
            False,
            "schema77",
        )
    elif not search_terminal:
        current_phase, authority, value, path, terminal, executor = (
            "predicate_search_yield",
            SEARCH_STATE,
            search,
            search_path,
            False,
            "search_yield",
        )
    elif not markdown_terminal:
        current_phase, authority, value, path, terminal, executor = (
            "markdown_paired_dev64",
            MARKDOWN_STATE,
            markdown,
            markdown_path,
            False,
            "markdown",
        )
    elif not scope_terminal:
        current_phase, authority, value, path, terminal, executor = (
            "conditional_scope_open",
            SCOPE_STATE,
            scope,
            scope_path,
            False,
            "scope_open",
        )
    elif not owic_terminal:
        current_phase, authority, value, path, terminal, executor = (
            "owic_gate1",
            OWIC_STATE,
            owic,
            owic_path,
            False,
            "owic",
        )
    else:
        current_phase, authority, value, path, terminal, executor = (
            "post_gate1_and_leaderboard_handoff",
            HANDOFF_STATE,
            safe["handoff"][0],
            safe["handoff"][1],
            str(safe["handoff"][0].get("status") or "").startswith("complete"),
            "handoff",
        )

    aggregate_consistent = (
        aggregate.get("selected") == 220
        and aggregate.get("terminal")
        == int(aggregate.get("completed", -1)) + int(aggregate.get("failed", -1))
        and aggregate.get("remaining") == 220 - int(aggregate.get("terminal", -1))
        and 0 <= int(aggregate.get("terminal", -1)) <= 220
    )
    common_false = (
        r1.get("process_signal_restart_resume_rerun_skip_or_selective_retry") is False
        and r1.get("leaderboard_submission_performed") is False
        and r1.get("sota_claim") is False
        and aggregate_consistent
    )
    current_valid = True
    if current_phase == "r1_full220":
        current_valid = bool(
            common_false
            and r1.get("role") == "v24118_r1_finalization_watchdog_state"
            and r1.get("label_blind_before_exact220") is True
            and r1_status == "waiting_for_r1_exact_terminal_220"
            and aggregate.get("exact_terminal_220") is False
            and r1.get("mapping_or_gold_read") is False
            and r1.get("evaluator_or_score_read") is False
            and r1.get("benchmark_forward_api_called") is False
        )
    elif current_phase == "p12_schema76_and_official_avg4":
        current_valid = bool(
            capacity.get("role") == "v24164_scope_capacity_liveness_audit"
            and capacity.get("activation_ready") is True
            and capacity.get("critical_findings") == []
            and capacity.get("source_policy", {}).get(
                "runtime_task_state_prediction_question_answer_or_evidence_opened"
            )
            is False
            and capacity.get("claims", {}).get("benchmark_score_available") is False
            and capacity.get("claims", {}).get("sota") is False
            and avg4_guard.get("role")
            == "v24155_avg4_after_scope_combined_watcher_state"
            and avg4_guard.get("leaderboard_submission_performed") is False
            and avg4_guard.get("sota_claim") is False
            and avg4.get("role") == "v2410_avg4_watcher_state"
            and avg4.get("leaderboard_submission_performed") is False
            and avg4.get("sota_claim") is False
        )
    elif current_phase == "schema77_paired_dev64":
        current_valid = bool(
            schema77.get("role")
            == "v24176_predicate_completion_paired_dev_watcher_state"
            and schema77.get("status")
            in {
                "waiting_for_official_avg4_terminal_serial_barrier",
                "waiting_for_shared_api_lease_after_official_avg4",
                "running_schema77_exact_dev64",
            }
            and schema77.get("test156_or_full220_launch_allowed") is False
            and schema77.get("test156_or_full220_api_called") is False
            and schema77.get("forward_resume_used") is False
            and schema77.get("selective_rerun_used") is False
            and schema77.get("leaderboard_submission_or_sota_claim") is False
        )
    elif current_phase == "predicate_search_yield":
        search_launch_call = safe["search_launch"][0].get(
            "network_model_search_fetch_or_benchmark_forward_called_by_launcher",
            False,
        )
        current_valid = bool(
            search.get("role") == "v24180_predicate_search_yield_watcher_state"
            and search.get("status")
            in {
                "waiting_for_schema77_paired_dev_terminal",
                "waiting_for_shared_api_lease_after_schema77",
                "running_sealed_search_yield_experiment",
            }
            and search.get("resume_or_selective_rerun_used") is False
            and search.get("leaderboard_submission_or_sota_claim") is False
            and safe["search_launch"][0].get("role")
            == "v24183_search_yield_launcher_state"
            and search_launch_call is False
        )
    elif current_phase == "markdown_paired_dev64":
        current_valid = bool(
            markdown.get("role") == "v24103_markdown_paired_dev_watcher_state"
            and markdown.get("status")
            in {
                "waiting_for_p12_four_trial_avg4_and_local_pack",
                "waiting_for_shared_api_lease_after_avg4",
                "running_p12_2_exact_dev64",
            }
            and markdown.get("test156_or_full220_launch_allowed") is False
            and markdown.get("test156_or_full220_api_called") is False
            and markdown.get("leaderboard_submission_or_sota_claim") is False
            and safe["markdown_launch"][0].get("role")
            == "v24185_markdown_priority_launcher_state"
            and safe["markdown_launch"][0].get(
                "shared_lease_model_search_fetch_evaluator_network_or_benchmark_forward_called_by_launcher"
            )
            is False
        )
    elif current_phase == "conditional_scope_open":
        current_valid = bool(
            scope.get("role") == "v24105_scope_open_paired_dev_watcher_state"
            and scope.get("status")
            in {
                "waiting_for_v24103_terminal_paired_go",
                "waiting_for_shared_api_lease_after_v24103_go",
                "running_p12_3_exact_dev64",
            }
            and scope.get("test156_or_full220_launch_allowed") is False
            and scope.get("test156_or_full220_api_called") is False
            and scope.get("leaderboard_submission_or_sota_claim") is False
        )
    elif current_phase == "owic_gate1":
        current_valid = bool(
            owic.get("role") == "v2411_post_p12_owic_watcher_state"
            and owic.get("status")
            in {
                "waiting_for_p12_trial2_exact220_release",
                "waiting_for_avg4_four_exact220_release",
                "waiting_for_shared_api_lease",
            }
            and owic.get("controller_enabled") is False
            and owic.get("training_credit_enabled") is False
            and owic.get("quality_leaderboard_or_sota_claim") is False
            and safe["owic_launch"][0].get("role")
            == "v24186_owic_after_quality_chain_launcher_state"
            and safe["owic_launch"][0].get(
                "shared_lease_model_search_fetch_evaluator_network_or_benchmark_forward_called_by_launcher"
            )
            is False
        )
    else:
        current_valid = bool(
            value.get("role") == "v24110_deepwide_leaderboard_handoff_watcher_state"
            and value.get("leaderboard_submission_performed") is False
            and value.get("sota_claim") is False
        )

    phase_report, phase_findings = _phase_state(
        authority,
        value,
        path,
        now=created,
        freshness_seconds=freshness_seconds,
        phase=current_phase,
        terminal=terminal,
        process=executors[executor],
        valid=current_valid,
        active_lease_pid=lease.get("pid") if lease.get("active") else None,
    )

    critical = [f"current_phase:{finding}" for finding in phase_findings]
    if not aggregate_consistent:
        critical.append("r1:safe_aggregate_contract")
    if not all(
        lease.get(key) is True for key in ("ordinary", "consistent", "owner_registered")
    ):
        critical.append("shared_api_lease_identity")

    capacity_critical = list(capacity.get("critical_findings") or [])
    if current_phase in {"r1_full220", "p12_schema76_and_official_avg4"}:
        critical.extend(f"capacity:{finding}" for finding in capacity_critical)
    paired = safe["paired"][0]
    if current_phase in {"markdown_paired_dev64", "conditional_scope_open"}:
        critical.extend(
            f"paired:{finding}" for finding in (paired.get("critical_findings") or [])
        )

    taxonomy = safe["taxonomy"][0]
    taxonomy_path = safe["taxonomy"][1]
    taxonomy_status = taxonomy.get("status")
    taxonomy_valid = bool(
        taxonomy.get("role")
        == "v2410_p13_failure_taxonomy_v2_evidence_watcher_state"
        and taxonomy_status in TAXONOMY_ALLOWED
        and taxonomy.get("new_p13_failure_mechanism_supported") is False
        and taxonomy.get("p13_design_allowed") is False
        and taxonomy.get("p13_implementation_allowed") is False
        and taxonomy.get("p13_forward_launch_allowed") is False
        and taxonomy.get("active_r1_or_frozen_p12_policy_change_allowed") is False
        and taxonomy.get("mapping_gold_category_evaluator_score_artifact_read") is False
        and taxonomy.get("runtime_prediction_values_used") is False
        and taxonomy.get("api_or_benchmark_forward_called") is False
        and taxonomy.get("leaderboard_or_sota_claim") is False
    )
    taxonomy_age = _age(taxonomy_path, created)
    if not taxonomy_valid:
        critical.append("taxonomy:safe_state_contract")
    if taxonomy_age > freshness_seconds:
        critical.append("taxonomy:state_stale")
    if executors["taxonomy"]["match_count"] != 1:
        critical.append("taxonomy:executor_process_identity")
    manual_review = taxonomy_status == "repeated_uncovered_evidence_requires_manual_audit"

    leaderboard = safe["leaderboard"][0]
    handoff = safe["handoff"][0]
    leaderboard_valid = bool(
        leaderboard.get("role") == "v2410_leaderboard_postprocess_watcher_state"
        and leaderboard.get("status")
        in {
            "waiting_for_four_exact220_trial_aggregate",
            "waiting_for_live_validated_local_submission_pack",
            "complete_local_pack_and_external_reference_audit",
        }
        and leaderboard.get("leaderboard_submission_performed") is False
        and leaderboard.get("sota_claim") is False
        and leaderboard.get(
            "mapping_gold_evaluator_task_prediction_or_current_task_score_read"
        )
        is False
        and leaderboard.get("api_or_benchmark_forward_called") is False
        and handoff.get("role")
        == "v24110_deepwide_leaderboard_handoff_watcher_state"
        and handoff.get("leaderboard_submission_performed") is False
        and handoff.get("sota_claim") is False
    )
    if not leaderboard_valid:
        critical.append("leaderboard:safe_state_contract")
    terminal_by_observer = {
        "leaderboard": str(leaderboard.get("status") or "").startswith("complete"),
        "handoff": str(handoff.get("status") or "").startswith("complete"),
    }
    for name in ("leaderboard", "handoff"):
        report = executors[name]
        if not terminal_by_observer[name] and report["match_count"] != 1:
            critical.append(f"{name}:executor_process_identity")
        if terminal_by_observer[name] and report["match_count"] > 1:
            critical.append(f"{name}:terminal_executor_duplicate")
        if report["isolated_no_bytecode_count"] != report["match_count"]:
            critical.append(f"{name}:executor_python_flags")

    launchers = {
        "search_yield": safe["search_launch"][0],
        "markdown": safe["markdown_launch"][0],
        "owic": safe["owic_launch"][0],
    }
    launcher_valid = bool(
        launchers["search_yield"].get("role")
        == "v24183_search_yield_launcher_state"
        and launchers["search_yield"].get(
            "mapping_gold_category_question_type_evaluator_score_prediction_or_outcome_read_by_launcher",
            False,
        )
        is False
        and launchers["search_yield"].get(
            "network_model_search_fetch_or_benchmark_forward_called_by_launcher"
        )
        is False
        and launchers["markdown"].get("role")
        == "v24185_markdown_priority_launcher_state"
        and launchers["markdown"].get(
            "mapping_gold_category_question_type_evaluator_score_prediction_or_outcome_read_by_launcher",
            False,
        )
        is False
        and launchers["markdown"].get(
            "shared_lease_model_search_fetch_evaluator_network_or_benchmark_forward_called_by_launcher"
        )
        is False
        and launchers["owic"].get("role")
        == "v24186_owic_after_quality_chain_launcher_state"
        and launchers["owic"].get(
            "mapping_gold_category_question_type_evaluator_score_prediction_or_outcome_read_by_launcher",
            False,
        )
        is False
        and launchers["owic"].get(
            "shared_lease_model_search_fetch_evaluator_network_or_benchmark_forward_called_by_launcher"
        )
        is False
    )
    if not launcher_valid:
        critical.append("serial_launchers:safe_state_contract")

    critical = sorted(set(critical))
    degraded: list[str] = []
    if manual_review:
        degraded.append("taxonomy:repeated_uncovered_manual_review_only")
    degraded.extend(
        f"capacity:{item}" for item in (capacity.get("degraded_findings") or [])
    )
    degraded = sorted(set(degraded))

    terminal_count = int(aggregate.get("terminal", 0))
    result: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": created,
        "label_blind": True,
        "protocol": protocol_record,
        "current_phase": phase_report,
        "r1_progress": {
            "selected": aggregate.get("selected"),
            "terminal": terminal_count,
            "completed": aggregate.get("completed"),
            "failed": aggregate.get("failed"),
            "remaining": aggregate.get("remaining"),
            "exact_terminal_220": aggregate.get("exact_terminal_220"),
            "contents_emitted": False,
        },
        "serial_chain": {
            "r1_terminal": r1_terminal,
            "p12_schema76_avg4_terminal": capacity_terminal,
            "schema77_terminal": schema77_terminal,
            "search_yield_terminal": search_terminal,
            "markdown_terminal": markdown_terminal,
            "scope_open_terminal": scope_terminal,
            "owic_gate1_terminal": owic_terminal,
            "launchers_safe_envelopes_valid": launcher_valid,
            "contents_emitted": False,
        },
        "taxonomy": {
            "status": taxonomy_status,
            "terminal": taxonomy.get("terminal"),
            "mapped_failure_count": taxonomy.get("mapped_failure_count"),
            "excluded_failure_count": taxonomy.get("excluded_failure_count"),
            "uncovered_failure_count": taxonomy.get("uncovered_failure_count"),
            "manual_review_only": manual_review,
            "automatic_design_implementation_or_launch_allowed": False,
            "active_policy_change_allowed": False,
            "fresh": taxonomy_age <= freshness_seconds,
            "valid": taxonomy_valid,
            "contents_emitted": False,
        },
        "leaderboard": {
            "postprocess_status": leaderboard.get("status"),
            "handoff_status": handoff.get("status"),
            "aggregate_present": leaderboard.get("aggregate_present"),
            "comparison_available": leaderboard.get("comparison_available"),
            "local_handoff_available": handoff.get("local_handoff_available"),
            "leaderboard_submission_performed": False,
            "sota": False,
            "valid": leaderboard_valid,
            "contents_emitted": False,
        },
        "shared_api_lease": lease,
        "executors": {
            name: report
            for name, report in executors.items()
            if name
            in {
                "r1_finalization",
                "capacity_liveness",
                "paired_liveness",
                "schema77",
                "search_yield",
                "markdown",
                "scope_open",
                "owic",
                "taxonomy",
                "leaderboard",
                "handoff",
            }
        },
        "overall_status": (
            "critical_manual_audit_required_no_automatic_mutation"
            if critical
            else "degraded_forward_healthy_manual_review_only"
            if degraded
            else "healthy"
        ),
        "critical_findings": critical,
        "degraded_findings": degraded,
        "source_policy": {
            "safe_json_envelopes_file_metadata_proc_identity_and_lease_only": True,
            "runtime_task_state_question_answer_evidence_or_prediction_rows_opened": False,
            "mapping_gold_category_question_type_evaluator_or_score_read": False,
            "credential_value_or_keyring_read": False,
            "network_or_api_called": False,
            "mutable_source_contents_hashed_or_emitted": False,
            "process_command_lines_or_environment_emitted": False,
        },
        "authorization": {
            "automatic_process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "forward_code_prompt_model_search_budget_gate_threshold_or_controller_change": False,
            "credential_or_network_access": False,
            "mapping_gold_category_question_type_evaluator_or_score_read": False,
            "benchmark_model_search_fetch_evaluator_or_api_call": False,
            "candidate_prepare_or_downstream_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "benchmark_score_available": leaderboard.get("aggregate_present") is True,
            "benchmark_improvement_observed": False,
            "avg_at_4_available": leaderboard.get("aggregate_present") is True,
            "entropy_or_credit_effect_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
        "next_action": (
            "manual_read_only_audit_without_process_mutation"
            if critical
            else "continue_existing_frozen_execution"
        ),
    }
    encoded = json.dumps(result, ensure_ascii=False)
    if OPAQUE_ID.search(encoded) or CREDENTIAL_LIKE.search(encoded):
        raise RuntimeError("V2.41.87 audit emitted forbidden content")
    result["audit_payload_sha256"] = payload_sha(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--proc-root", default="/proc")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output)
    output = output if output.is_absolute() else root / output
    value = build_report(root, proc_root=Path(args.proc_root))
    output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "overall_status": value["overall_status"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
