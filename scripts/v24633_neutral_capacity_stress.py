#!/usr/bin/env python3
"""Preregister and run the V2.46.33 neutral GPT-5.6 capacity stress.

The experiment never opens a benchmark manifest or task.  Each arm executes
the same 220 anonymous jobs and 462 synthetic model effects while varying only
active-child admission, task deadline, and the frozen slot policy selected by
V2.46.32.  Prompts and responses are ephemeral; persistent artifacts contain
aggregate content-free accounting only.
"""

from __future__ import annotations

import argparse
import ast
import concurrent.futures
import functools
import json
import math
import os
import re
import socket
import statistics
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelRequestError  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallResponsesClient,
)
from deepwide_agent.v24630_exact220_contract import (  # noqa: E402
    MODEL,
    MODEL_SLOT_POOL_ID,
    protected_watcher_snapshot,
    payload_sha256,
    read_object,
    sha256,
)
from scripts import simulate_v24632_capacity_schedules as parent  # noqa: E402
from scripts.audit_v24187_phase_liveness import (  # noqa: E402
    actual_python_script,
    process_snapshot,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260806"
PROTOCOL_ID = "v24633_neutral_exact_shape_gpt56_capacity_stress_v1"
PROTOCOL = Path(
    f"results/v24633_neutral_capacity_stress_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24633_neutral_capacity_stress_preactivation_audit_v1_{DATE}.json"
)
ACTIVATION = Path(
    f"results/v24633_neutral_capacity_stress_activation_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24633_neutral_capacity_stress_execution_start_v1_{DATE}.json"
)
RESULT = Path(f"results/v24633_neutral_capacity_stress_result_v1_{DATE}.json")
ABORT = Path(f"results/v24633_neutral_capacity_stress_abort_v1_{DATE}.json")
DECISION = Path(f"results/v24633_neutral_capacity_stress_decision_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v24633_neutral_capacity_stress_postresult_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24633_neutral_capacity_stress_v1_{DATE}")
SAFE_PROGRESS = OUTPUT_ROOT / "safe_progress.json"
PARENT_AUDIT = Path(
    f"results/v24632_content_free_capacity_simulation_audit_v1_{DATE}.json"
)
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24633_neutral_capacity_stress_v1"
LEASE_PURPOSE = "neutral_exact_shape_gpt56_capacity_validation"
RUNNER_MARKER = "scripts/v24633_neutral_capacity_stress.py"

ANONYMOUS_JOBS = 220
MODEL_SLOT_CAP = 8
PLAN_EFFECTS = 220
SYNTHESIS_EFFECTS = 220
RECOVERY_EFFECTS = 20
REPAIR_EFFECTS = 2
TOTAL_EFFECTS = 462
RETRIEVAL_DELAY_SECONDS = 52.638272
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_ATTEMPT_SECONDS = 0.05
TAIL_WALL_CEILING_SECONDS = 1800.0
INTER_ARM_COOLDOWN_SECONDS = 5.0
PLAN_INPUT_CHARS = 1_900
POSTPLAN_INPUT_CHARS = 25_000
PLAN_OUTPUT_TOKENS = 4_000
POSTPLAN_OUTPUT_TOKENS = 30_000
MIN_PLAN_INPUT_TOKENS_PER_SUCCESS = 350
MIN_PLAN_OUTPUT_TOKENS_PER_SUCCESS = 100
MIN_POSTPLAN_INPUT_TOKENS_PER_SUCCESS = 3_000
MIN_POSTPLAN_OUTPUT_TOKENS_PER_SUCCESS = 500

ARMS = (
    {
        "name": "control_32_active_8_slots_150s_fifo",
        "active_child_cap": 32,
        "task_deadline_seconds": 150,
        "model_slot_policy": "fifo",
    },
    {
        "name": "selected_20_active_8_slots_240s_fifo",
        "active_child_cap": 20,
        "task_deadline_seconds": 240,
        "model_slot_policy": "fifo",
    },
    {
        "name": "conservative_16_active_8_slots_210s_fifo",
        "active_child_cap": 16,
        "task_deadline_seconds": 210,
        "model_slot_policy": "fifo",
    },
    {
        "name": "conservative_16_active_6_general_2_postplan_reserved_210s",
        "active_child_cap": 16,
        "task_deadline_seconds": 210,
        "model_slot_policy": "reserve2",
    },
)
ARM_NAMES = tuple(str(value["name"]) for value in ARMS)
CANDIDATE_ARM_NAMES = ARM_NAMES[1:]

SOURCE = Path("scripts/v24633_neutral_capacity_stress.py")
TEST = Path("tests/test_v24633_neutral_capacity_stress.py")
SOURCE_FILES = (
    SOURCE,
    TEST,
    Path("scripts/deepwide_api_lease.py"),
    Path("scripts/simulate_v24632_capacity_schedules.py"),
    Path("src/deepwide_agent/v24312_deadline_reliability.py"),
    Path("src/deepwide_agent/v24468_total_wall_transport.py"),
    Path("src/deepwide_agent/v24630_exact220_contract.py"),
    Path("scripts/v24468_total_wall_http_helper.py"),
)

SECRET_PREFIXES = (
    "gh" + "p_",
    "github_" + "pat_",
    "tvly-" + "dev-",
    "s" + "k-",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
FORBIDDEN_FIELDS = frozenset(
    {
        "benchmark_question_type",
        "question_type",
        "task_category",
        "category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "mapping",
        "evaluator",
        "score",
        "reward",
    }
)
FORBIDDEN_CALLS = frozenset(
    {
        "execute_forward",
        "run_one_task",
        "run_all_evaluators",
        "evaluator_command",
    }
)
BENCHMARK_RUNNER_MARKERS = (
    "scripts/run_v24630_exact220.py",
    "scripts/run_v24630_exact220_task.py",
    "scripts/finalize_v24630_exact220.py",
    "scripts/run_official_eval_local.py",
)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _ordinary(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.46.33 expected ordinary repository file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = read_object(_ordinary(root, relative))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.46.33 expected JSON object: {relative}")
    return value


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _tracked(root: Path, relative: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            raise RuntimeError(f"V2.46.33 credential literal in {relative}")
        output[str(relative)] = sha256(path)
    return output


def _parents(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    simulation = _read(root, parent.OUTPUT)
    audit = _read(root, PARENT_AUDIT)
    if (
        not _sealed(simulation, "simulation_payload_sha256")
        or simulation.get("role")
        != "v24632_content_free_capacity_schedule_simulation"
        or simulation.get("authorization", {}).get(
            "neutral_provider_stress_protocol_design"
        )
        is not True
        or simulation.get("authorization", {}).get("neutral_provider_stress_launch")
        is not False
        or not _sealed(audit, "audit_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("simulation", {}).get("sha256")
        != sha256(root / parent.OUTPUT)
        or audit.get("authorization", {}).get(
            "neutral_provider_stress_protocol_design"
        )
        is not True
    ):
        raise RuntimeError("V2.46.33 parent simulation or audit drifted")
    selected = simulation.get("simulation", {}).get("selected_schedule", {})
    if (
        selected.get("active_child_cap") != 20
        or selected.get("task_deadline_seconds") != 240
        or selected.get("model_slot_policy") != "fifo"
        or selected.get("scenario_results", {}).get("p95", {}).get(
            "effect_window_deadline_misses"
        )
        != 0
        or selected.get("scenario_results", {}).get("p95", {}).get(
            "task_deadline_misses"
        )
        != 0
        or selected.get("scenario_results", {}).get("p95", {}).get(
            "projected_forward_wall_seconds"
        )
        != 1621.49778
    ):
        raise RuntimeError("V2.46.33 selected parent schedule drifted")
    return simulation, audit


def _future_paths() -> tuple[Path, ...]:
    return (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, ABORT, DECISION, POSTAUDIT)


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    simulation, audit = _parents(root)
    if require_pristine:
        present = [
            str(path)
            for path in _future_paths()
            if (root / path).exists() or (root / path).is_symlink()
        ]
        if present:
            raise RuntimeError(f"V2.46.33 future surface is not pristine: {present}")
    manifest = _manifest(root)
    p95 = simulation["calibration"]["scenarios"]["p95"]
    if float(p95["retrieval_seconds"]) != RETRIEVAL_DELAY_SECONDS:
        raise RuntimeError("V2.46.33 p95 retrieval calibration drifted")
    value = {
        "artifact_version": 1,
        "role": "v24633_neutral_capacity_stress_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "simulation": {
                "path": str(parent.OUTPUT),
                "sha256": sha256(root / parent.OUTPUT),
                "payload_sha256": simulation["simulation_payload_sha256"],
            },
            "simulation_audit": {
                "path": str(PARENT_AUDIT),
                "sha256": sha256(root / PARENT_AUDIT),
                "payload_sha256": audit["audit_payload_sha256"],
            },
        },
        "scope": {
            "benchmark_external_synthetic_neutral_only": True,
            "anonymous_jobs_per_arm": ANONYMOUS_JOBS,
            "arms": len(ARMS),
            "single_frozen_execution_per_arm": True,
            "arm_order": list(ARM_NAMES),
            "same_protocol_retry_resume_or_selective_rerun": False,
        },
        "workload": {
            "plan_effects_per_arm": PLAN_EFFECTS,
            "initial_synthesis_effects_per_arm": SYNTHESIS_EFFECTS,
            "recovery_effects_per_arm": RECOVERY_EFFECTS,
            "repair_effects_per_arm": REPAIR_EFFECTS,
            "total_logical_model_effects_per_arm": TOTAL_EFFECTS,
            "total_logical_model_effects_all_arms": TOTAL_EFFECTS * len(ARMS),
            "retrieval_delay_seconds_per_job": RETRIEVAL_DELAY_SECONDS,
            "retrieval_delay_source": "v24632_frozen_p95_content_free_calibration",
            "network_search_or_fetch_effects": 0,
            "official_evaluator_effects": 0,
        },
        "neutral_payload": {
            "plan_input_target_chars": PLAN_INPUT_CHARS,
            "postplan_input_target_chars": POSTPLAN_INPUT_CHARS,
            "plan_max_output_tokens": PLAN_OUTPUT_TOKENS,
            "postplan_max_output_tokens": POSTPLAN_OUTPUT_TOKENS,
            "synthetic_generic_material_only": True,
            "prompt_or_response_persisted_or_hashed": False,
            "response_content_used_for_routing_or_credit": False,
            "minimum_plan_input_tokens_per_success": MIN_PLAN_INPUT_TOKENS_PER_SUCCESS,
            "minimum_plan_output_tokens_per_success": MIN_PLAN_OUTPUT_TOKENS_PER_SUCCESS,
            "minimum_postplan_input_tokens_per_success": MIN_POSTPLAN_INPUT_TOKENS_PER_SUCCESS,
            "minimum_postplan_output_tokens_per_success": MIN_POSTPLAN_OUTPUT_TOKENS_PER_SUCCESS,
            "minimums_are_below_v24630_frozen_successful_request_medians": True,
        },
        "arms": [dict(value) for value in ARMS],
        "provider": {
            "proxy_url": MODEL["proxy_url"],
            "model": MODEL["name"],
            "reasoning_effort": MODEL["reasoning_effort"],
            "service_tier": MODEL["service_tier"],
            "timeout_seconds": MODEL["timeout_seconds"],
            "max_retries": MODEL["max_retries"],
            "hard_total_wall_per_attempt": True,
        },
        "capacity": {
            "shared_model_slot_cap": MODEL_SLOT_CAP,
            "slot_pool_id": MODEL_SLOT_POOL_ID,
            "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
            "minimum_attempt_seconds": MINIMUM_ATTEMPT_SECONDS,
            "inter_arm_cooldown_seconds": INTER_ARM_COOLDOWN_SECONDS,
            "tail_wall_ceiling_seconds": TAIL_WALL_CEILING_SECONDS,
        },
        "gate": {
            "candidate_arms": list(CANDIDATE_ARM_NAMES),
            "logical_effects_exact_per_arm": TOTAL_EFFECTS,
            "zero_slot_timeout": True,
            "zero_provider_or_deadline_failure": True,
            "zero_failed_job": True,
            "exact_effect_conservation": True,
            "identical_logical_work_across_arms": True,
            "candidate_wall_at_most_seconds": TAIL_WALL_CEILING_SECONDS,
            "pass_rule": "selected arm or at least one conservative arm passes every frozen mechanism check",
            "control_arm_required_to_pass": False,
        },
        "claim_boundary": {
            "mechanism_capacity_only": True,
            "benchmark_quality_measured": False,
            "causal_quality_improvement_proven": False,
            "entropy_credit_assignment_tested": False,
            "sota_supported": False,
        },
        "source_policy": {
            "runtime_benchmark_manifest_task_question_prediction_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "task_identifier_prompt_response_prediction_answer_url_page_or_credential_persisted_or_hashed": False,
            "network_search_fetch_or_evaluator_called": False,
        },
        "lease": {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_single_owner": True,
        },
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "authorization": {
            "preactivation_audit_design": True,
            "neutral_capacity_stress_launch": False,
            "benchmark_dev_or_exact220_launch": False,
            "official_evaluator_call": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return value


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else _read(root, PROTOCOL)
    expected = build_protocol(
        root,
        now=int(protocol.get("created_at_unix", -1)),
        require_pristine=False,
    )
    if protocol != expected or not _sealed(protocol, "protocol_payload_sha256"):
        raise RuntimeError("V2.46.33 protocol drifted")
    return protocol


def _source_findings(root: Path, relative: Path) -> tuple[list[str], list[str]]:
    tree = ast.parse(_ordinary(root, relative).read_text(encoding="utf-8"))
    accesses: list[str] = []
    calls: list[str] = []
    for node in ast.walk(tree):
        key: str | None = None
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            key = node.args[0].value
        elif (
            isinstance(node, ast.Subscript)
            and isinstance(node.slice, ast.Constant)
            and isinstance(node.slice.value, str)
        ):
            key = node.slice.value
        if key is not None and key.casefold() in FORBIDDEN_FIELDS:
            accesses.append(f"{relative}:{node.lineno}:{key}")
        if isinstance(node, ast.Call):
            name: str | None = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in FORBIDDEN_CALLS:
                calls.append(f"{relative}:{node.lineno}:{name}")
    return sorted(accesses), sorted(calls)


def _process_present(marker: str) -> bool:
    for row in process_snapshot():
        argv = row.get("argv")
        script = actual_python_script(argv) if isinstance(argv, list) else None
        if isinstance(script, str) and script.endswith(marker):
            return True
    return False


def build_preactivation_audit(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    accesses: list[str] = []
    calls: list[str] = []
    for relative in (SOURCE, TEST):
        found_accesses, found_calls = _source_findings(root, relative)
        accesses.extend(found_accesses)
        calls.extend(found_calls)
    credential_hits = [
        str(relative)
        for relative in (SOURCE, TEST)
        if SECRET.search(_ordinary(root, relative).read_text(encoding="utf-8"))
    ]
    focused = subprocess.run(
        [
            str(root / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(root / TEST),
            "-v",
        ],
        cwd=root,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=120,
        check=False,
    )
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    tracked = all(_tracked(root, path) for path in (*SOURCE_FILES, PROTOCOL))
    watcher = protected_watcher_snapshot()
    parent_audit = _read(root, PARENT_AUDIT)
    expected_watchers = parent_audit["closure"]["protected_watchers"]
    runner_present = any(
        _process_present(marker) for marker in BENCHMARK_RUNNER_MARKERS
    )
    lease = lease_observation(root, Path("/proc"))
    future_pristine = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in (ACTIVATION, EXECUTION_START, RESULT, ABORT, DECISION, POSTAUDIT)
    )
    findings: list[str] = []
    if head != remote:
        findings.append("protocol_commit_not_pushed")
    if not tracked:
        findings.append("protocol_source_test_or_dependency_not_tracked")
    if accesses:
        findings.append("privileged_field_access_in_runtime_surface")
    if calls:
        findings.append("benchmark_or_evaluator_execution_call_in_runtime_surface")
    if credential_hits:
        findings.append("credential_literal_in_runtime_surface")
    if focused.returncode != 0:
        findings.append("focused_tests_failed")
    if watcher != expected_watchers:
        findings.append("protected_watcher_identity_drifted")
    if runner_present:
        findings.append("benchmark_forward_or_evaluator_process_present")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if not future_pristine:
        findings.append("future_execution_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24633_neutral_capacity_stress_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol": {
            "path": str(PROTOCOL),
            "sha256": sha256(root / PROTOCOL),
            "payload_sha256": protocol["protocol_payload_sha256"],
        },
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "protocol_source_test_and_dependencies_tracked": tracked,
        },
        "privileged_field_accesses": sorted(accesses),
        "forbidden_execution_calls": sorted(calls),
        "credential_literal_hits": sorted(credential_hits),
        "focused_tests": {
            "command": "python -I -B tests/test_v24633_neutral_capacity_stress.py -v",
            "passed": focused.returncode == 0,
            "test_count": 6,
            "network_model_search_fetch_or_evaluator_called": False,
        },
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "benchmark_forward_or_evaluator_present": runner_present,
            "protected_watchers": watcher,
            "protected_watchers_unchanged": watcher == expected_watchers,
            "future_execution_surface_pristine": future_pristine,
            "active_run_killed_or_quarantined": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "activation_design": not findings,
            "neutral_capacity_stress_launch": False,
            "benchmark_dev_or_exact220_launch": False,
            "official_evaluator_call": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_preactivation_audit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    audit = dict(value) if value is not None else _read(root, PREAUDIT)
    if (
        audit.get("role")
        != "v24633_neutral_capacity_stress_preactivation_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or not _sealed(audit, "audit_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("protocol", {}).get("sha256") != sha256(root / PROTOCOL)
        or audit.get("authorization", {}).get("activation_design") is not True
        or any(
            setting
            for key, setting in audit.get("authorization", {}).items()
            if key != "activation_design"
        )
    ):
        raise RuntimeError("V2.46.33 preactivation audit drifted")
    validate_protocol(root)
    return audit


def _loopback_reachable(url: str, timeout_seconds: float = 2.0) -> bool:
    match = re.fullmatch(r"http://127\.0\.0\.1:(\d+)/responses", str(url))
    if match is None:
        return False
    try:
        with socket.create_connection(
            ("127.0.0.1", int(match.group(1))), timeout=timeout_seconds
        ):
            return True
    except OSError:
        return False


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    audit = validate_preactivation_audit(root)
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    tracked = all(_tracked(root, path) for path in (*SOURCE_FILES, PROTOCOL, PREAUDIT))
    watcher = protected_watcher_snapshot()
    expected_watchers = audit["closure"]["protected_watchers"]
    lease = lease_observation(root, Path("/proc"))
    endpoint_reachable = _loopback_reachable(protocol["provider"]["proxy_url"])
    future_pristine = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in (EXECUTION_START, RESULT, ABORT, DECISION, POSTAUDIT)
    )
    findings: list[str] = []
    if head != remote:
        findings.append("preactivation_audit_commit_not_pushed")
    if not tracked:
        findings.append("activation_dependency_not_tracked")
    if watcher != expected_watchers:
        findings.append("protected_watcher_identity_drifted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if not endpoint_reachable:
        findings.append("loopback_gpt56_endpoint_unreachable")
    if not future_pristine:
        findings.append("execution_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24633_neutral_capacity_stress_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "dependencies_tracked": tracked,
        },
        "checks": {
            "protected_watchers": watcher,
            "protected_watchers_unchanged": watcher == expected_watchers,
            "shared_api_lease_inactive": lease.get("active") is False,
            "loopback_gpt56_endpoint_reachable": endpoint_reachable,
            "execution_surface_pristine": future_pristine,
            "provider_model_search_or_evaluator_called": False,
        },
        "findings": findings,
        "activation_valid": not findings,
        "authorization": {
            "one_neutral_capacity_stress": not findings,
            "same_protocol_retry_resume_or_selective_rerun": False,
            "benchmark_dev_or_exact220_launch": False,
            "official_evaluator_call": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


def validate_activation(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    activation = dict(value) if value is not None else _read(root, ACTIVATION)
    if (
        activation.get("role") != "v24633_neutral_capacity_stress_activation"
        or activation.get("protocol_id") != PROTOCOL_ID
        or not _sealed(activation, "activation_payload_sha256")
        or activation.get("findings") != []
        or activation.get("activation_valid") is not True
        or activation.get("protocol_sha256") != sha256(root / PROTOCOL)
        or activation.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or activation.get("authorization", {}).get("one_neutral_capacity_stress")
        is not True
        or any(
            setting
            for key, setting in activation.get("authorization", {}).items()
            if key != "one_neutral_capacity_stress"
        )
    ):
        raise RuntimeError("V2.46.33 activation drifted")
    validate_preactivation_audit(root)
    return activation


def _effect_sets() -> tuple[frozenset[int], frozenset[int]]:
    recoveries = {
        min(
            ANONYMOUS_JOBS - 1,
            int((index + 0.5) * ANONYMOUS_JOBS / RECOVERY_EFFECTS),
        )
        for index in range(RECOVERY_EFFECTS)
    }
    repairs: set[int] = set()
    for index in range(REPAIR_EFFECTS):
        ordinal = min(
            ANONYMOUS_JOBS - 1,
            int((index + 0.25) * ANONYMOUS_JOBS / REPAIR_EFFECTS),
        )
        while ordinal in recoveries or ordinal in repairs:
            ordinal = (ordinal + 1) % ANONYMOUS_JOBS
        repairs.add(ordinal)
    if len(recoveries) != RECOVERY_EFFECTS or len(repairs) != REPAIR_EFFECTS:
        raise RuntimeError("V2.46.33 effect assignment drifted")
    return frozenset(recoveries), frozenset(repairs)


def _neutral_material(target_chars: int) -> str:
    if target_chars < 100:
        raise ValueError("V2.46.33 neutral material target is too small")
    rows: list[str] = []
    index = 1
    while sum(len(value) + 1 for value in rows) < target_chars:
        rows.append(
            f"Neutral record {index:05d}: amber birch cobalt delta ember field "
            "granite harbor iris juniper kinetic linen meadow north orbit plain."
        )
        index += 1
    return "\n".join(rows)[:target_chars]


@functools.lru_cache(maxsize=8)
def _neutral_prompt(stage: str) -> tuple[str, str, int, bool]:
    system = (
        "You are serving a synthetic provider-capacity measurement. The input "
        "contains generic generated words only. Do not browse, identify real "
        "entities, infer hidden data, or discuss benchmarks. Follow the requested "
        "neutral output shape exactly."
    )
    if stage == "plan":
        user = (
            _neutral_material(PLAN_INPUT_CHARS)
            + "\nReturn one JSON object with a notes array of exactly 24 entries. "
            "Each entry must be one distinct eight-word neutral sentence."
        )
        return system, user, PLAN_OUTPUT_TOKENS, True
    if stage not in {"synthesis", "recovery", "repair"}:
        raise ValueError("V2.46.33 unknown neutral stage")
    user = (
        _neutral_material(POSTPLAN_INPUT_CHARS)
        + f"\nThis is the synthetic {stage} phase. Return one Markdown table with "
        "exactly 80 data rows and columns Index, Neutral Label, Neutral Note. "
        "Use a distinct label and an eight-word generic note in every row."
    )
    return system, user, POSTPLAN_OUTPUT_TOKENS, False


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        raise ValueError("V2.46.33 empty metric vector")
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _run_effect(stage: str, limiter: Any) -> dict[str, Any]:
    system, user, max_output_tokens, json_mode = _neutral_prompt(stage)
    started = time.monotonic()
    try:
        result = limiter.complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=json_mode,
        )
        if not isinstance(getattr(result, "text", None), str) or not result.text:
            raise RuntimeError("V2.46.33 provider returned empty settled text")
        usage = result.usage if isinstance(result.usage, Mapping) else {}
        input_tokens = int(usage.get("input_tokens", 0) or 0)
        output_tokens = int(usage.get("output_tokens", 0) or 0)
        total_tokens = int(usage.get("total_tokens", 0) or 0)
        return {
            "success": True,
            "wall_seconds": max(0.0, time.monotonic() - started),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens or input_tokens + output_tokens,
        }
    except ModelRequestError:
        return {
            "success": False,
            "wall_seconds": max(0.0, time.monotonic() - started),
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }


def _worker(
    ordinal: int,
    *,
    arm: Mapping[str, Any],
    provider: Mapping[str, Any],
    slot_directory: Path,
    output_root: Path,
) -> dict[str, Any]:
    recoveries, repairs = _effect_sets()
    started = time.monotonic()
    deadline = started + float(arm["task_deadline_seconds"])
    inner = HardTotalWallResponsesClient(
        str(provider["proxy_url"]),
        str(provider["model"]),
        reasoning_effort=str(provider["reasoning_effort"]),
        service_tier=str(provider["service_tier"]),
        timeout=int(provider["timeout_seconds"]),
        max_retries=int(provider["max_retries"]),
        absolute_deadline=deadline,
        cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=MINIMUM_ATTEMPT_SECONDS,
        stage_callback=lambda _stage: None,
    )
    shared = DeadlineAwareGlobalModelSlotLimiter(
        inner,
        slot_directory=slot_directory,
        output_root=output_root,
        absolute_deadline=deadline,
        slot_cap=MODEL_SLOT_CAP,
        pool_id=MODEL_SLOT_POOL_ID,
        cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds=MINIMUM_ATTEMPT_SECONDS,
    )
    if arm["model_slot_policy"] == "reserve2":
        plan_limiter = DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=slot_directory,
            output_root=output_root,
            absolute_deadline=deadline,
            slot_cap=MODEL_SLOT_CAP - 2,
            pool_id=MODEL_SLOT_POOL_ID,
            cleanup_reserve_seconds=CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=MINIMUM_ATTEMPT_SECONDS,
        )
        postplan_limiter = shared
        limiters = (plan_limiter, postplan_limiter)
    else:
        plan_limiter = shared
        postplan_limiter = shared
        limiters = (shared,)
    stages = ["plan", "synthesis"]
    if ordinal in recoveries:
        stages.append("recovery")
    elif ordinal in repairs:
        stages.append("repair")
    stage_success: Counter[str] = Counter()
    stage_failure: Counter[str] = Counter()
    stage_input_tokens: Counter[str] = Counter()
    stage_output_tokens: Counter[str] = Counter()
    stage_total_tokens: Counter[str] = Counter()
    effect_seconds: list[float] = []

    def execute(stage: str, limiter: Any) -> None:
        observation = _run_effect(stage, limiter)
        effect_seconds.append(float(observation["wall_seconds"]))
        (stage_success if observation["success"] else stage_failure)[stage] += 1
        stage_input_tokens[stage] += int(observation["input_tokens"])
        stage_output_tokens[stage] += int(observation["output_tokens"])
        stage_total_tokens[stage] += int(observation["total_tokens"])

    execute("plan", plan_limiter)
    time.sleep(RETRIEVAL_DELAY_SECONDS)
    for stage in stages[1:]:
        execute(stage, postplan_limiter)
    receipts = [limiter.receipt() for limiter in limiters]
    slot_acquisitions = sum(int(value["acquisitions"]) for value in receipts)
    slot_timeouts = sum(int(value["slot_timeouts"]) for value in receipts)
    slot_total_wait = sum(float(value["total_wait_seconds"]) for value in receipts)
    slot_max_wait = max(float(value["max_wait_seconds"]) for value in receipts)
    logical = len(stages)
    successes = sum(stage_success.values())
    value = {
        "logical_effects": logical,
        "successful_effects": successes,
        "failed_effects": logical - successes,
        "stage_scheduled": dict(Counter(stages)),
        "stage_success": dict(stage_success),
        "stage_failure": dict(stage_failure),
        "stage_input_tokens": dict(stage_input_tokens),
        "stage_output_tokens": dict(stage_output_tokens),
        "stage_total_tokens": dict(stage_total_tokens),
        "provider_requests": int(inner.requests),
        "provider_attempts": int(inner.attempts),
        "provider_successes": int(inner.calls),
        "provider_failures": int(inner.failures),
        "provider_deadline_failures": int(inner.deadline_failures),
        "hard_total_wall_timeouts": int(inner.hard_total_wall_timeouts),
        "input_tokens": int(inner.input_tokens),
        "output_tokens": int(inner.output_tokens),
        "total_tokens": int(inner.total_tokens),
        "slot_acquisitions": slot_acquisitions,
        "slot_timeouts": slot_timeouts,
        "slot_total_wait_seconds": slot_total_wait,
        "slot_max_wait_seconds": slot_max_wait,
        "task_wall_seconds": max(0.0, time.monotonic() - started),
        "effect_wall_seconds": sum(effect_seconds),
        "deadline_exhausted": any(bool(value["deadline_exhausted"]) for value in receipts),
    }
    if (
        value["provider_requests"] != slot_acquisitions
        or value["provider_successes"] != successes
        or slot_acquisitions + slot_timeouts != logical
        or sum(stage_input_tokens.values()) != value["input_tokens"]
        or sum(stage_output_tokens.values()) != value["output_tokens"]
        or sum(stage_total_tokens.values()) != value["total_tokens"]
    ):
        raise RuntimeError("V2.46.33 worker effect conservation failed")
    return value


def _aggregate_arm(
    arm: Mapping[str, Any],
    workers: Sequence[Mapping[str, Any]],
    *,
    wall_seconds: float,
    maximum_active_workers: int,
) -> dict[str, Any]:
    if len(workers) != ANONYMOUS_JOBS:
        raise RuntimeError("V2.46.33 anonymous job denominator drifted")
    integer_fields = (
        "logical_effects",
        "successful_effects",
        "failed_effects",
        "provider_requests",
        "provider_attempts",
        "provider_successes",
        "provider_failures",
        "provider_deadline_failures",
        "hard_total_wall_timeouts",
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "slot_acquisitions",
        "slot_timeouts",
    )
    totals = {
        name: sum(int(worker[name]) for worker in workers) for name in integer_fields
    }
    scheduled: Counter[str] = Counter()
    succeeded: Counter[str] = Counter()
    failed: Counter[str] = Counter()
    stage_input_tokens: Counter[str] = Counter()
    stage_output_tokens: Counter[str] = Counter()
    stage_total_tokens: Counter[str] = Counter()
    for worker in workers:
        scheduled.update(worker["stage_scheduled"])
        succeeded.update(worker["stage_success"])
        failed.update(worker["stage_failure"])
        stage_input_tokens.update(worker["stage_input_tokens"])
        stage_output_tokens.update(worker["stage_output_tokens"])
        stage_total_tokens.update(worker["stage_total_tokens"])
    task_walls = [float(worker["task_wall_seconds"]) for worker in workers]
    effect_walls = [float(worker["effect_wall_seconds"]) for worker in workers]
    slot_waits = [float(worker["slot_total_wait_seconds"]) for worker in workers]
    expected_stages = {
        "plan": PLAN_EFFECTS,
        "synthesis": SYNTHESIS_EFFECTS,
        "recovery": RECOVERY_EFFECTS,
        "repair": REPAIR_EFFECTS,
    }
    failed_jobs = sum(int(worker["failed_effects"]) > 0 for worker in workers)
    deadline_exhausted_jobs = sum(bool(worker["deadline_exhausted"]) for worker in workers)
    postplan_stages = ("synthesis", "recovery", "repair")
    postplan_successes = sum(int(succeeded[name]) for name in postplan_stages)
    postplan_input_tokens = sum(int(stage_input_tokens[name]) for name in postplan_stages)
    postplan_output_tokens = sum(int(stage_output_tokens[name]) for name in postplan_stages)
    checks = {
        "anonymous_jobs_exact": len(workers) == ANONYMOUS_JOBS,
        "active_admission_bounded": 1
        <= int(maximum_active_workers)
        <= int(arm["active_child_cap"]),
        "logical_effects_exact": totals["logical_effects"] == TOTAL_EFFECTS,
        "stage_effects_exact": dict(scheduled) == expected_stages,
        "stage_outcome_conservation": all(
            int(succeeded[name]) + int(failed[name]) == expected_stages[name]
            for name in expected_stages
        ),
        "effect_conservation": totals["slot_acquisitions"]
        + totals["slot_timeouts"]
        == totals["logical_effects"],
        "provider_request_conservation": totals["provider_requests"]
        == totals["slot_acquisitions"],
        "provider_outcome_conservation": totals["provider_successes"]
        + totals["provider_failures"]
        == totals["provider_requests"]
        and totals["provider_successes"] == totals["successful_effects"],
        "all_effects_successful": totals["successful_effects"] == TOTAL_EFFECTS
        and totals["failed_effects"] == 0,
        "zero_slot_timeout": totals["slot_timeouts"] == 0,
        "zero_provider_failure": totals["provider_failures"] == 0,
        "zero_provider_deadline_failure": totals["provider_deadline_failures"] == 0,
        "zero_hard_total_wall_timeout": totals["hard_total_wall_timeouts"] == 0,
        "zero_failed_job": failed_jobs == 0,
        "zero_deadline_exhausted_job": deadline_exhausted_jobs == 0,
        "provider_usage_conservation": sum(stage_input_tokens.values())
        == totals["input_tokens"]
        and sum(stage_output_tokens.values()) == totals["output_tokens"]
        and sum(stage_total_tokens.values()) == totals["total_tokens"],
        "plan_input_load_fidelity": int(stage_input_tokens["plan"])
        >= int(succeeded["plan"]) * MIN_PLAN_INPUT_TOKENS_PER_SUCCESS,
        "plan_output_load_fidelity": int(stage_output_tokens["plan"])
        >= int(succeeded["plan"]) * MIN_PLAN_OUTPUT_TOKENS_PER_SUCCESS,
        "postplan_input_load_fidelity": postplan_input_tokens
        >= postplan_successes * MIN_POSTPLAN_INPUT_TOKENS_PER_SUCCESS,
        "postplan_output_load_fidelity": postplan_output_tokens
        >= postplan_successes * MIN_POSTPLAN_OUTPUT_TOKENS_PER_SUCCESS,
        "zero_task_deadline_miss": max(task_walls)
        <= float(arm["task_deadline_seconds"]) + 1e-6,
        "wall_within_ceiling": float(wall_seconds) <= TAIL_WALL_CEILING_SECONDS,
    }
    mechanism_gate = all(checks.values())
    value = {
        "name": arm["name"],
        "active_child_cap": arm["active_child_cap"],
        "task_deadline_seconds": arm["task_deadline_seconds"],
        "model_slot_policy": arm["model_slot_policy"],
        "anonymous_jobs": len(workers),
        "maximum_active_workers": maximum_active_workers,
        "wall_seconds": round(float(wall_seconds), 6),
        "throughput_jobs_per_minute": round(
            len(workers) * 60.0 / max(float(wall_seconds), 1e-9), 6
        ),
        "logical_effects": totals["logical_effects"],
        "stage_scheduled": expected_stages,
        "stage_success": {name: int(succeeded[name]) for name in expected_stages},
        "stage_failure": {name: int(failed[name]) for name in expected_stages},
        "stage_input_tokens": {
            name: int(stage_input_tokens[name]) for name in expected_stages
        },
        "stage_output_tokens": {
            name: int(stage_output_tokens[name]) for name in expected_stages
        },
        "stage_total_tokens": {
            name: int(stage_total_tokens[name]) for name in expected_stages
        },
        "successful_effects": totals["successful_effects"],
        "failed_effects": totals["failed_effects"],
        "failed_jobs": failed_jobs,
        "deadline_exhausted_jobs": deadline_exhausted_jobs,
        "provider": {
            "requests": totals["provider_requests"],
            "attempts": totals["provider_attempts"],
            "successes": totals["provider_successes"],
            "failures": totals["provider_failures"],
            "deadline_failures": totals["provider_deadline_failures"],
            "hard_total_wall_timeouts": totals["hard_total_wall_timeouts"],
            "input_tokens": totals["input_tokens"],
            "output_tokens": totals["output_tokens"],
            "total_tokens": totals["total_tokens"],
        },
        "slots": {
            "acquisitions": totals["slot_acquisitions"],
            "timeouts": totals["slot_timeouts"],
            "total_wait_seconds": round(sum(slot_waits), 6),
            "maximum_worker_wait_seconds": round(max(slot_waits), 6),
            "maximum_single_acquisition_wait_seconds": round(
                max(float(worker["slot_max_wait_seconds"]) for worker in workers), 6
            ),
        },
        "task_wall_seconds": {
            "mean": round(statistics.fmean(task_walls), 6),
            "p50": round(_quantile(task_walls, 0.50), 6),
            "p95": round(_quantile(task_walls, 0.95), 6),
            "maximum": round(max(task_walls), 6),
        },
        "effect_wall_seconds": {
            "sum": round(sum(effect_walls), 6),
            "mean_per_job": round(statistics.fmean(effect_walls), 6),
            "maximum_per_job": round(max(effect_walls), 6),
        },
        "checks": checks,
        "mechanism_gate_passed": mechanism_gate,
    }
    _validate_arm_projection(value)
    return value


def _validate_arm_projection(value: Mapping[str, Any]) -> None:
    name = value.get("name")
    if name not in ARM_NAMES:
        raise RuntimeError("V2.46.33 unknown arm projection")
    arm = next(item for item in ARMS if item["name"] == name)
    checks = value.get("checks")
    stage_scheduled = value.get("stage_scheduled")
    stage_success = value.get("stage_success")
    stage_failure = value.get("stage_failure")
    stage_input = value.get("stage_input_tokens")
    stage_output = value.get("stage_output_tokens")
    stage_total = value.get("stage_total_tokens")
    provider = value.get("provider")
    slots = value.get("slots")
    task_wall = value.get("task_wall_seconds")
    expected_stages = {
        "plan": PLAN_EFFECTS,
        "synthesis": SYNTHESIS_EFFECTS,
        "recovery": RECOVERY_EFFECTS,
        "repair": REPAIR_EFFECTS,
    }
    mappings = (
        stage_scheduled,
        stage_success,
        stage_failure,
        stage_input,
        stage_output,
        stage_total,
        provider,
        slots,
        task_wall,
    )
    if (
        value.get("active_child_cap") != arm["active_child_cap"]
        or value.get("task_deadline_seconds") != arm["task_deadline_seconds"]
        or value.get("model_slot_policy") != arm["model_slot_policy"]
        or value.get("anonymous_jobs") != ANONYMOUS_JOBS
        or value.get("logical_effects") != TOTAL_EFFECTS
        or stage_scheduled != expected_stages
        or any(not isinstance(item, Mapping) for item in mappings)
        or not isinstance(checks, Mapping)
        or not checks
    ):
        raise RuntimeError("V2.46.33 arm projection drifted")
    postplan_stages = ("synthesis", "recovery", "repair")
    postplan_successes = sum(int(stage_success[name]) for name in postplan_stages)
    expected_checks = {
        "anonymous_jobs_exact": value["anonymous_jobs"] == ANONYMOUS_JOBS,
        "active_admission_bounded": 1
        <= int(value["maximum_active_workers"])
        <= int(arm["active_child_cap"]),
        "logical_effects_exact": value["logical_effects"] == TOTAL_EFFECTS,
        "stage_effects_exact": stage_scheduled == expected_stages,
        "stage_outcome_conservation": all(
            int(stage_success[name]) + int(stage_failure[name])
            == expected_stages[name]
            for name in expected_stages
        ),
        "effect_conservation": int(slots["acquisitions"])
        + int(slots["timeouts"])
        == int(value["logical_effects"]),
        "provider_request_conservation": int(provider["requests"])
        == int(slots["acquisitions"]),
        "provider_outcome_conservation": int(provider["successes"])
        + int(provider["failures"])
        == int(provider["requests"])
        and int(provider["successes"]) == int(value["successful_effects"]),
        "all_effects_successful": int(value["successful_effects"]) == TOTAL_EFFECTS
        and int(value["failed_effects"]) == 0,
        "zero_slot_timeout": int(slots["timeouts"]) == 0,
        "zero_provider_failure": int(provider["failures"]) == 0,
        "zero_provider_deadline_failure": int(provider["deadline_failures"]) == 0,
        "zero_hard_total_wall_timeout": int(provider["hard_total_wall_timeouts"])
        == 0,
        "zero_failed_job": int(value["failed_jobs"]) == 0,
        "zero_deadline_exhausted_job": int(value["deadline_exhausted_jobs"]) == 0,
        "provider_usage_conservation": sum(int(stage_input[name]) for name in expected_stages)
        == int(provider["input_tokens"])
        and sum(int(stage_output[name]) for name in expected_stages)
        == int(provider["output_tokens"])
        and sum(int(stage_total[name]) for name in expected_stages)
        == int(provider["total_tokens"]),
        "plan_input_load_fidelity": int(stage_input["plan"])
        >= int(stage_success["plan"]) * MIN_PLAN_INPUT_TOKENS_PER_SUCCESS,
        "plan_output_load_fidelity": int(stage_output["plan"])
        >= int(stage_success["plan"]) * MIN_PLAN_OUTPUT_TOKENS_PER_SUCCESS,
        "postplan_input_load_fidelity": sum(
            int(stage_input[name]) for name in postplan_stages
        )
        >= postplan_successes * MIN_POSTPLAN_INPUT_TOKENS_PER_SUCCESS,
        "postplan_output_load_fidelity": sum(
            int(stage_output[name]) for name in postplan_stages
        )
        >= postplan_successes * MIN_POSTPLAN_OUTPUT_TOKENS_PER_SUCCESS,
        "zero_task_deadline_miss": float(task_wall["maximum"])
        <= float(arm["task_deadline_seconds"]) + 1e-6,
        "wall_within_ceiling": float(value["wall_seconds"])
        <= TAIL_WALL_CEILING_SECONDS,
    }
    if (
        dict(checks) != expected_checks
        or value.get("mechanism_gate_passed") is not all(expected_checks.values())
    ):
        raise RuntimeError("V2.46.33 arm check projection drifted")


def _run_arm(
    root: Path,
    arm: Mapping[str, Any],
    provider: Mapping[str, Any],
    *,
    worker: Callable[..., dict[str, Any]] = _worker,
) -> dict[str, Any]:
    output_root = (root / "outputs").resolve()
    run_root = root / OUTPUT_ROOT
    run_root.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    active = 0
    maximum_active = 0
    active_lock = threading.Lock()

    def wrapped(ordinal: int, slot_directory: Path) -> dict[str, Any]:
        nonlocal active, maximum_active
        with active_lock:
            active += 1
            maximum_active = max(maximum_active, active)
        try:
            return worker(
                ordinal,
                arm=arm,
                provider=provider,
                slot_directory=slot_directory,
                output_root=output_root,
            )
        finally:
            with active_lock:
                active -= 1

    with tempfile.TemporaryDirectory(dir=run_root) as directory:
        slots = Path(directory)
        for index in range(1, MODEL_SLOT_CAP + 1):
            path = slots / f"slot_{index:02d}.lock"
            descriptor = os.open(
                path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
            )
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write("{}\n")
        values: list[dict[str, Any]] = []
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=int(arm["active_child_cap"]),
            thread_name_prefix="v24633-neutral",
        ) as executor:
            futures = [
                executor.submit(wrapped, ordinal, slots)
                for ordinal in range(ANONYMOUS_JOBS)
            ]
            for future in concurrent.futures.as_completed(futures):
                values.append(future.result())
    return _aggregate_arm(
        arm,
        values,
        wall_seconds=max(0.0, time.monotonic() - started),
        maximum_active_workers=maximum_active,
    )


def project_result(
    arms: Sequence[Mapping[str, Any]],
    *,
    execution_start_sha256: str,
    wall_seconds: float,
    now: int | None = None,
) -> dict[str, Any]:
    copied = [dict(value) for value in arms]
    if [value.get("name") for value in copied] != list(ARM_NAMES):
        raise RuntimeError("V2.46.33 arm order drifted")
    for value in copied:
        _validate_arm_projection(value)
    signatures = {
        (
            value["logical_effects"],
            tuple(sorted(value["stage_scheduled"].items())),
        )
        for value in copied
    }
    identical_work = len(signatures) == 1 and next(iter(signatures))[0] == TOTAL_EFFECTS
    candidates = [value for value in copied if value["name"] in CANDIDATE_ARM_NAMES]
    passing_candidates = [value["name"] for value in candidates if value["mechanism_gate_passed"]]
    checks = {
        "four_frozen_arms_completed": len(copied) == len(ARMS),
        "identical_logical_work_across_arms": identical_work,
        "selected_or_conservative_candidate_passed": bool(passing_candidates),
        "no_benchmark_search_fetch_or_evaluator_effect": True,
    }
    value = {
        "artifact_version": 1,
        "role": "v24633_neutral_capacity_stress_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "execution_start_sha256": execution_start_sha256,
        "wall_seconds": round(float(wall_seconds), 6),
        "arms": copied,
        "passing_candidate_arms": passing_candidates,
        "checks": checks,
        "mechanism_gate_passed": all(checks.values()),
        "source_policy": {
            "benchmark_manifest_task_question_prediction_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "network_search_fetch_or_evaluator_called": False,
            "prompt_response_identifier_prediction_answer_url_page_or_credential_persisted_or_hashed": False,
        },
        "claim_boundary": {
            "provider_capacity_mechanism_measured": True,
            "benchmark_quality_measured": False,
            "quality_improvement_or_sota_supported": False,
        },
        "authorization": {
            "mechanism_decision_design": True,
            "benchmark_dev_or_exact220_launch": False,
            "official_evaluator_call": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if SECRET.search(encoded) or OPAQUE.search(encoded) or "| Result |" in encoded:
        raise RuntimeError("V2.46.33 result emitted prohibited content")
    value["result_payload_sha256"] = payload_sha256(value)
    validate_result(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    arms = copied.get("arms")
    checks = copied.get("checks")
    source_policy = copied.get("source_policy")
    claim = copied.get("claim_boundary")
    authorization = copied.get("authorization")
    if (
        copied.get("role") != "v24633_neutral_capacity_stress_result"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not _sealed(copied, "result_payload_sha256")
        or not isinstance(arms, list)
        or [item.get("name") for item in arms] != list(ARM_NAMES)
        or not isinstance(checks, Mapping)
        or not checks
        or copied.get("mechanism_gate_passed") is not all(checks.values())
        or source_policy
        != {
            "benchmark_manifest_task_question_prediction_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "network_search_fetch_or_evaluator_called": False,
            "prompt_response_identifier_prediction_answer_url_page_or_credential_persisted_or_hashed": False,
        }
        or claim
        != {
            "provider_capacity_mechanism_measured": True,
            "benchmark_quality_measured": False,
            "quality_improvement_or_sota_supported": False,
        }
        or not isinstance(authorization, Mapping)
        or authorization.get("mechanism_decision_design") is not True
        or any(
            setting
            for key, setting in authorization.items()
            if key != "mechanism_decision_design"
        )
    ):
        raise RuntimeError("V2.46.33 result drifted")
    for arm in arms:
        _validate_arm_projection(arm)
    expected_passing = [
        arm["name"]
        for arm in arms
        if arm["name"] in CANDIDATE_ARM_NAMES and arm["mechanism_gate_passed"]
    ]
    signatures = {
        (
            arm["logical_effects"],
            tuple(sorted(arm["stage_scheduled"].items())),
        )
        for arm in arms
    }
    expected_checks = {
        "four_frozen_arms_completed": len(arms) == len(ARMS),
        "identical_logical_work_across_arms": len(signatures) == 1
        and next(iter(signatures))[0] == TOTAL_EFFECTS,
        "selected_or_conservative_candidate_passed": bool(expected_passing),
        "no_benchmark_search_fetch_or_evaluator_effect": True,
    }
    if (
        copied.get("passing_candidate_arms") != expected_passing
        or dict(checks) != expected_checks
        or copied.get("mechanism_gate_passed") is not all(expected_checks.values())
    ):
        raise RuntimeError("V2.46.33 passing-arm projection drifted")
    return copied


def _publish_new(path: Path, value: Mapping[str, Any]) -> None:
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


def _publish_progress(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _execution_start(
    root: Path, lease: Mapping[str, Any], *, now: int | None = None
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24633_neutral_capacity_stress_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git(root, "rev-parse", "HEAD"),
        "git_target_main": _git(root, "rev-parse", "target/main"),
        "activation_sha256": sha256(root / ACTIVATION),
        "lease": {
            "owner": lease.get("owner"),
            "purpose": lease.get("purpose"),
            "pid": lease.get("pid"),
            "acquired_at_unix": lease.get("acquired_at_unix"),
        },
        "protected_watchers": protected_watcher_snapshot(),
        "arms": list(ARM_NAMES),
        "anonymous_jobs_per_arm": ANONYMOUS_JOBS,
        "logical_effects_per_arm": TOTAL_EFFECTS,
        "provider_model_search_or_evaluator_called_before_start": False,
        "benchmark_manifest_task_mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    return value


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    activation = validate_activation(root)
    if _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main"):
        raise RuntimeError("V2.46.33 launch HEAD is not pushed")
    if _git(root, "status", "--porcelain"):
        raise RuntimeError("V2.46.33 launch worktree is not clean")
    if not all(
        _tracked(root, path)
        for path in (*SOURCE_FILES, PROTOCOL, PREAUDIT, ACTIVATION)
    ):
        raise RuntimeError("V2.46.33 launch dependency is not tracked")
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (EXECUTION_START, RESULT, ABORT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.46.33 execution surface is not pristine")
    if not _loopback_reachable(protocol["provider"]["proxy_url"]):
        raise RuntimeError("V2.46.33 loopback GPT-5.6 endpoint is unavailable")
    if protected_watcher_snapshot() != activation["checks"]["protected_watchers"]:
        raise RuntimeError("V2.46.33 protected watcher identity drifted before launch")
    if any(_process_present(marker) for marker in BENCHMARK_RUNNER_MARKERS):
        raise RuntimeError("V2.46.33 benchmark forward or evaluator is active")
    if lease_observation(root, Path("/proc")).get("active") is not False:
        raise RuntimeError("V2.46.33 shared API lease is active before launch")
    started = time.monotonic()
    completed: list[dict[str, Any]] = []
    try:
        with acquire_deepwide_api_lease(
            root,
            owner=LEASE_OWNER,
            purpose=LEASE_PURPOSE,
            path=root / LEASE_PATH,
        ) as lease:
            execution = _execution_start(root, lease)
            _publish_new(root / EXECUTION_START, execution)
            for index, arm in enumerate(ARMS):
                completed.append(_run_arm(root, arm, protocol["provider"]))
                _publish_progress(
                    root / SAFE_PROGRESS,
                    {
                        "artifact_version": 1,
                        "role": "v24633_neutral_capacity_stress_safe_progress",
                        "protocol_id": PROTOCOL_ID,
                        "completed_arm_count": len(completed),
                        "completed_arm_names": [value["name"] for value in completed],
                        "latest_arm": completed[-1],
                        "prompt_response_identifier_prediction_answer_url_page_or_credential_persisted_or_hashed": False,
                        "benchmark_manifest_task_question_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
                    },
                )
                if index + 1 < len(ARMS):
                    time.sleep(INTER_ARM_COOLDOWN_SECONDS)
        value = project_result(
            completed,
            execution_start_sha256=sha256(root / EXECUTION_START),
            wall_seconds=max(0.0, time.monotonic() - started),
        )
        _publish_new(root / RESULT, value)
        return value
    except BaseException as exc:
        if not (root / ABORT).exists() and not (root / ABORT).is_symlink():
            abort = {
                "artifact_version": 1,
                "role": "v24633_neutral_capacity_stress_abort",
                "protocol_id": PROTOCOL_ID,
                "created_at_unix": int(time.time()),
                "exception_class": type(exc).__name__,
                "completed_arm_names": [value["name"] for value in completed],
                "completed_arm_count": len(completed),
                "same_protocol_retry_resume_or_selective_rerun_authorized": False,
                "prompt_response_task_identifier_or_credential_persisted": False,
            }
            abort["abort_payload_sha256"] = payload_sha256(abort)
            _publish_new(root / ABORT, abort)
        raise


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    result = validate_result(_read(root, RESULT))
    if (root / ABORT).exists() or (root / ABORT).is_symlink():
        raise RuntimeError("V2.46.33 aborted execution cannot produce a GO decision")
    arms = {value["name"]: value for value in result["arms"]}
    passing = list(result["passing_candidate_arms"])
    selected_name: str | None = None
    preferred = "selected_20_active_8_slots_240s_fifo"
    if preferred in passing:
        selected_name = preferred
    elif passing:
        selected_name = min(
            passing,
            key=lambda name: (
                float(arms[name]["wall_seconds"]), CANDIDATE_ARM_NAMES.index(name)
            ),
        )
    passed = bool(result["mechanism_gate_passed"] and selected_name)
    value = {
        "artifact_version": 1,
        "role": "v24633_neutral_capacity_stress_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "result_sha256": sha256(root / RESULT),
        "status": "mechanism_go" if passed else "mechanism_no_go",
        "passed": passed,
        "passing_candidate_arms": passing,
        "selected_arm": selected_name,
        "selection_rule": "prefer frozen V2.46.32 selected 20/8/240 FIFO when it passes; otherwise choose minimum-wall passing conservative arm",
        "observed": {
            name: {
                "wall_seconds": arms[name]["wall_seconds"],
                "failed_jobs": arms[name]["failed_jobs"],
                "slot_timeouts": arms[name]["slots"]["timeouts"],
                "provider_failures": arms[name]["provider"]["failures"],
                "mechanism_gate_passed": arms[name]["mechanism_gate_passed"],
            }
            for name in ARM_NAMES
        },
        "claim_boundary": {
            "neutral_provider_capacity_mechanism_supported": passed,
            "benchmark_quality_or_improvement_measured": False,
            "sota_supported": False,
        },
        "authorization": {
            "next_label_blind_exact220_protocol_design": passed,
            "exact220_launch": False,
            "official_evaluator_call": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    validate_decision(value)
    return value


def validate_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    passed = copied.get("passed")
    selected = copied.get("selected_arm")
    authorization = copied.get("authorization")
    if (
        copied.get("role") != "v24633_neutral_capacity_stress_decision"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not _sealed(copied, "decision_payload_sha256")
        or not isinstance(passed, bool)
        or copied.get("status") != ("mechanism_go" if passed else "mechanism_no_go")
        or (passed and selected not in CANDIDATE_ARM_NAMES)
        or (not passed and selected is not None)
        or not isinstance(authorization, Mapping)
        or authorization.get("next_label_blind_exact220_protocol_design") is not passed
        or any(
            setting
            for key, setting in authorization.items()
            if key != "next_label_blind_exact220_protocol_design"
        )
    ):
        raise RuntimeError("V2.46.33 decision drifted")
    return copied


def build_postresult_audit(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    result = validate_result(_read(root, RESULT))
    decision = validate_decision(_read(root, DECISION))
    head = _git(root, "rev-parse", "HEAD")
    remote = _git(root, "rev-parse", "target/main")
    tracked_paths = (
        *SOURCE_FILES,
        PROTOCOL,
        PREAUDIT,
        ACTIVATION,
        EXECUTION_START,
        RESULT,
        DECISION,
    )
    tracked = all(_tracked(root, path) for path in tracked_paths)
    watcher = protected_watcher_snapshot()
    expected_watchers = _read(root, PARENT_AUDIT)["closure"]["protected_watchers"]
    runner_present = any(
        _process_present(marker) for marker in BENCHMARK_RUNNER_MARKERS
    )
    lease = lease_observation(root, Path("/proc"))
    encoded = json.dumps({"result": result, "decision": decision}, ensure_ascii=False)
    findings: list[str] = []
    if head != remote:
        findings.append("result_or_decision_commit_not_pushed")
    if not tracked:
        findings.append("source_protocol_execution_result_or_decision_not_tracked")
    if SECRET.search(encoded):
        findings.append("credential_literal_persisted")
    if OPAQUE.search(encoded):
        findings.append("benchmark_like_identifier_persisted")
    if watcher != expected_watchers:
        findings.append("protected_watcher_identity_drifted")
    if runner_present:
        findings.append("benchmark_forward_or_evaluator_process_present")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if decision.get("result_sha256") != sha256(root / RESULT):
        findings.append("decision_result_binding_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24633_neutral_capacity_stress_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "result": {"path": str(RESULT), "sha256": sha256(root / RESULT)},
        "decision": {"path": str(DECISION), "sha256": sha256(root / DECISION)},
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "all_required_artifacts_tracked": tracked,
        },
        "closure": {
            "shared_api_lease_active": lease.get("active"),
            "benchmark_forward_or_evaluator_present": runner_present,
            "protected_watchers": watcher,
            "protected_watchers_unchanged": watcher == expected_watchers,
            "active_run_killed_or_quarantined": False,
            "same_protocol_retry_resume_or_selective_rerun": False,
        },
        "source_policy": {
            "benchmark_manifest_task_question_prediction_mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "network_search_fetch_or_evaluator_called": False,
            "prompt_response_identifier_prediction_answer_url_page_or_credential_persisted_or_hashed": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "next_label_blind_exact220_protocol_design": bool(
                decision["passed"] and not findings
            ),
            "exact220_launch": False,
            "official_evaluator_call": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_postresult_audit(value)
    return value


def validate_postresult_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    authorization = copied.get("authorization")
    if (
        copied.get("role")
        != "v24633_neutral_capacity_stress_postresult_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or not _sealed(copied, "audit_payload_sha256")
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or copied.get("git", {}).get("head_equals_target_main") is not True
        or copied.get("git", {}).get("all_required_artifacts_tracked") is not True
        or copied.get("closure", {}).get("shared_api_lease_active") is not False
        or copied.get("closure", {}).get("benchmark_forward_or_evaluator_present")
        is not False
        or copied.get("closure", {}).get("protected_watchers_unchanged") is not True
        or not isinstance(authorization, Mapping)
        or any(
            setting
            for key, setting in authorization.items()
            if key != "next_label_blind_exact220_protocol_design"
        )
    ):
        raise RuntimeError("V2.46.33 postresult audit drifted")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("preregister", "preaudit", "activate", "probe", "finalize", "postaudit"),
    )
    args = parser.parse_args()
    if args.action == "preregister":
        value, path = build_protocol(), PROTOCOL
    elif args.action == "preaudit":
        value, path = build_preactivation_audit(), PREAUDIT
    elif args.action == "activate":
        value, path = build_activation(), ACTIVATION
    elif args.action == "probe":
        value = run_probe()
        print(
            json.dumps(
                {
                    "path": str(RESULT),
                    "mechanism_gate_passed": value["mechanism_gate_passed"],
                    "passing_candidate_arms": value["passing_candidate_arms"],
                },
                sort_keys=True,
            )
        )
        return
    elif args.action == "finalize":
        value, path = build_decision(), DECISION
    else:
        value, path = build_postresult_audit(), POSTAUDIT
    _publish_new(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
