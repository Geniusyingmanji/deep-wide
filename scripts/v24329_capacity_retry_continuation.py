#!/usr/bin/env python3
"""Append-only V2.43.28 capacity continuation without repeating level one.

V2.43.28 stopped after a complete level-one task because its implementation
added a zero-provider-retry check that was absent from the frozen protocol.
This successor binds that immutable result, changes only the mechanical
interpretation to accept attempts within the already frozen max_retries=2,
and runs the previously untouched 2/4/8 executor levels.  It never evaluates
benchmark content and never repeats the level-one remote effects.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import copy
import json
import math
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts import v24328_shared_prefix_capacity_staircase as parent  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


DATE = "20260803"
PROTOCOL_ID = "v24329_capacity_retry_continuation_v1"
PROTOCOL = Path(f"results/v24329_capacity_continuation_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24329_capacity_continuation_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24329_capacity_continuation_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24329_capacity_continuation_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24329_capacity_continuation_result_v1_{DATE}.json")
DECISION = Path(f"results/v24329_capacity_continuation_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24329_capacity_continuation_postresult_audit_v1_{DATE}.json")
PARENT_PROTOCOL = parent.PROTOCOL
PARENT_RESULT = parent.RESULT
PARENT_DECISION = parent.DECISION
PARENT_POSTAUDIT = parent.POSTAUDIT
PARENT_ARTIFACTS = (
    PARENT_PROTOCOL,
    parent.PREAUDIT,
    parent.ACTIVATION,
    parent.EXECUTION_START,
    PARENT_RESULT,
    PARENT_DECISION,
    PARENT_POSTAUDIT,
)
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24329_capacity_retry_continuation_v1"
LEASE_PURPOSE = "benchmark_external_capacity_retry_continuation_2_4_8"
RUNNER_MARKER = "scripts/v24329_capacity_retry_continuation.py"
REMOTE_LEVELS = (2, 4, 8)
ALL_LEVELS = parent.LEVELS
MODEL_MAX_RETRIES = 2
SOURCE_FILES = (
    "scripts/v24328_shared_prefix_capacity_staircase.py",
    "scripts/v24329_capacity_retry_continuation.py",
    "tests/test_v24329_capacity_retry_continuation.py",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
URL = re.compile(r"https?://", re.IGNORECASE)


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError("V2.43.29 expected an ordinary repository file")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.29 expected a JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def publish(path: Path, value: Mapping[str, Any]) -> None:
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


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.43.29 credential literal in source surface")
        output[relative] = sha256(path)
    return output


def _port_listening() -> bool:
    try:
        with socket.create_connection(
            (parent.PROXY_HOST, parent.PROXY_PORT), timeout=0.5
        ):
            return True
    except OSError:
        return False


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


def _environment() -> dict[str, str]:
    return parent._environment()


def _parent_evidence(root: Path) -> dict[str, Any]:
    protocol = parent.validate_protocol(root)
    result = parent.validate_result(_read(root, PARENT_RESULT))
    decision = parent.validate_decision(_read(root, PARENT_DECISION))
    audit = parent.validate_postaudit(_read(root, PARENT_POSTAUDIT))
    levels = result.get("levels")
    if not isinstance(levels, list) or len(levels) != 1:
        raise RuntimeError("V2.43.29 parent did not stop exactly after level one")
    level = levels[0]
    parent.validate_level(level)
    tasks = level.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 1:
        raise RuntimeError("V2.43.29 parent level-one task is absent")
    task = tasks[0]
    parent.validate_task_projection(task)
    failed_task_checks = sorted(
        name for name, passed in task["checks"].items() if not passed
    )
    failed_level_checks = sorted(
        name for name, passed in level["checks"].items() if not passed
    )
    if (
        protocol.get("provider", {}).get("model_slot_cap") != parent.MODEL_SLOT_CAP
        or protocol.get("provider", {}).get("model") != "gpt-5.6-sol"
        or protocol.get("runtime", {}).get("stop_on_first_failed_level") is not True
        or decision.get("status") != "capacity_no_go"
        or decision.get("passed") is not False
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or failed_task_checks != ["no_model_retry"]
        or failed_level_checks != ["all_tasks_passed"]
        or task.get("parent_taxonomy") != "success"
        or task.get("all_parent_artifacts_valid") is not True
        or task.get("effect_accounting_complete") is not True
        or task.get("provider_model_requests") != 3
        or task.get("provider_model_attempts") != 4
        or task.get("slot_timeouts") != 0
        or task.get("provider_deadline_failures") != 0
        or task.get("hard_fetch_deadline_failures") != 0
        or task.get("fetch_helper_failures") != 0
        or task.get("core_fetch_targets") != 7
        or task.get("reserve_fetch_targets") != 3
    ):
        raise RuntimeError("V2.43.29 parent failure was not retry-only")
    return {
        "protocol": protocol,
        "result": result,
        "decision": decision,
        "audit": audit,
        "level": level,
        "task": task,
    }


def corrected_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    parent.validate_task_projection(value)
    output = copy.deepcopy(dict(value))
    checks = parent._task_checks(output)
    checks.pop("no_model_retry")
    requests = int(output["provider_model_requests"])
    attempts = int(output["provider_model_attempts"])
    checks["provider_attempts_within_frozen_retry_budget"] = (
        requests <= attempts <= requests * (MODEL_MAX_RETRIES + 1)
    )
    output["checks"] = checks
    output["passed"] = all(checks.values())
    parent.validate_task_projection(output)
    return output


def inherited_level_one(root: Path = ROOT) -> dict[str, Any]:
    evidence = _parent_evidence(root.resolve())
    task = corrected_task_projection(evidence["task"])
    if task["passed"] is not True:
        raise RuntimeError("V2.43.29 corrected parent task did not pass")
    level = parent.summarize_level(
        level=1,
        tasks=[task],
        batch_wall_seconds=float(evidence["level"]["batch_wall_seconds"]),
    )
    if level["passed"] is not True:
        raise RuntimeError("V2.43.29 inherited level one did not pass")
    return level


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    inherited = inherited_level_one(root)
    if require_pristine:
        present = [
            str(path)
            for path in (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
            if (root / path).exists() or (root / path).is_symlink()
        ]
        if present:
            raise RuntimeError(f"V2.43.29 future surface is not pristine: {present}")
    manifest = _manifest(root)
    parent_hashes = {
        str(path): sha256(root / path) for path in PARENT_ARTIFACTS
    }
    value = {
        "artifact_version": 1,
        "role": "v24329_capacity_continuation_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "append_only_capacity_retry_continuation_without_level_one_rerun",
        "parent_artifacts": parent_hashes,
        "parent_diagnosis": {
            "levels_present": [1],
            "level_one_parent_success": True,
            "level_one_failed_task_checks": ["no_model_retry"],
            "level_one_failed_level_checks": ["all_tasks_passed"],
            "provider_model_requests": 3,
            "provider_model_attempts": 4,
            "retry_count": 1,
            "all_non_retry_task_checks_passed": True,
            "parent_postaudit_findings": [],
        },
        "continuation_contract": {
            "inherited_levels": [1],
            "new_remote_levels": list(REMOTE_LEVELS),
            "all_levels": list(ALL_LEVELS),
            "level_one_remote_effect_repeated": False,
            "level_one_projection_recomputed_from_content_free_frozen_parent": True,
            "single_changed_check": "no_model_retry_to_provider_attempts_within_frozen_retry_budget",
            "provider_max_retries_unchanged": MODEL_MAX_RETRIES,
            "provider_requests_attempts_and_wall_cost_all_retained": True,
            "stop_on_first_failed_new_level": True,
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "no_resume_retry_task_skip_or_selective_rerun": True,
        },
        "inherited_level_one": {
            "batch_wall_seconds": inherited["batch_wall_seconds"],
            "throughput_tasks_per_minute": inherited[
                "throughput_tasks_per_minute"
            ],
            "passed_under_corrected_check": inherited["passed"],
        },
        "provider": {
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "service_tier": "priority",
            "model_slot_cap": parent.MODEL_SLOT_CAP,
            "max_retries": MODEL_MAX_RETRIES,
        },
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "task_text_identifier_query_url_page_prediction_response_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "capacity_continuation_design": True,
            "capacity_continuation_launch": False,
            "paired_benchmark_launch": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value=value)
    return value


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else _read(root, PROTOCOL)
    manifest = protocol.get("surface_manifest")
    source = protocol.get("source_policy")
    authorization = protocol.get("authorization")
    expected_parents = {
        str(path): sha256(root / path) for path in PARENT_ARTIFACTS
    }
    if (
        protocol.get("role")
        != "v24329_capacity_continuation_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope")
        != "append_only_capacity_retry_continuation_without_level_one_rerun"
        or protocol.get("parent_artifacts") != expected_parents
        or protocol.get("continuation_contract", {}).get("inherited_levels") != [1]
        or protocol.get("continuation_contract", {}).get("new_remote_levels")
        != list(REMOTE_LEVELS)
        or protocol.get("continuation_contract", {}).get(
            "level_one_remote_effect_repeated"
        )
        is not False
        or protocol.get("continuation_contract", {}).get(
            "single_changed_check"
        )
        != "no_model_retry_to_provider_attempts_within_frozen_retry_budget"
        or protocol.get("provider", {}).get("model_slot_cap")
        != parent.MODEL_SLOT_CAP
        or protocol.get("provider", {}).get("max_retries")
        != MODEL_MAX_RETRIES
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or authorization.get("capacity_continuation_design") is not True
        or any(
            enabled
            for key, enabled in authorization.items()
            if key != "capacity_continuation_design"
        )
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.29 protocol drifted")
    _parent_evidence(root)
    inherited_level_one(root)
    return protocol


def _run_tests() -> bool:
    completed = subprocess.run(
        [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-p",
            "test_v24329_capacity_retry_continuation.py",
        ],
        cwd=ROOT,
        env=_environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=180,
        check=False,
    )
    return completed.returncode == 0


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    future = (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    pristine = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in future
    )
    tests_passed = _run_tests()
    port = _port_listening()
    lease = lease_observation(root, Path("/proc"))
    watchers = protected_watcher_snapshot()
    findings: list[str] = []
    if not pristine:
        findings.append("future_surface_not_pristine")
    if not tests_passed:
        findings.append("focused_tests_failed")
    if not port:
        findings.append("keyless_proxy_not_listening")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24329_capacity_continuation_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": True,
            "parent_retry_only_failure_proven": True,
            "level_one_frozen_projection_passes_corrected_check": True,
            "level_one_remote_effect_will_not_repeat": True,
            "focused_tests_passed": tests_passed,
            "keyless_proxy_listening_without_api_request": port,
            "shared_api_lease_inactive": lease.get("active") is False,
            "future_surface_pristine": pristine,
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "benchmark_or_evaluator_surface_authorized": False,
        },
        "protected_watchers": watchers,
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "parent_result_sha256": sha256(root / PARENT_RESULT),
            "parent_decision_sha256": sha256(root / PARENT_DECISION),
            "parent_postaudit_sha256": sha256(root / PARENT_POSTAUDIT),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
        "authorization": {
            "one_capacity_continuation_launch": not findings,
            "paired_benchmark_launch": False,
            "exact220": False,
            "evaluator": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_preaudit(root, value=value)
    return value


def validate_preaudit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    audit = dict(value) if value is not None else _read(root, PREAUDIT)
    if (
        audit.get("role")
        != "v24329_capacity_continuation_preactivation_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or audit.get("findings") != []
        or audit.get("audit_valid") is not True
        or audit.get("launch_authorized") is not True
        or audit.get("checks", {}).get("focused_tests_passed") is not True
        or audit.get("checks", {}).get("level_one_remote_effect_will_not_repeat")
        is not True
        or audit.get("provenance", {}).get("protocol_sha256")
        != sha256(root / PROTOCOL)
        or audit.get("protected_watchers") != protected_watcher_snapshot()
        or audit.get("authorization", {}).get(
            "one_capacity_continuation_launch"
        )
        is not True
        or any(
            enabled
            for key, enabled in audit.get("authorization", {}).items()
            if key != "one_capacity_continuation_launch"
        )
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.29 preactivation audit drifted")
    validate_protocol(root)
    return audit


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    audit = validate_preaudit(root)
    lease = lease_observation(root, Path("/proc"))
    future = (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    findings: list[str] = []
    if any((root / path).exists() or (root / path).is_symlink() for path in future):
        findings.append("activation_or_execution_surface_not_pristine")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24329_capacity_continuation_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        "new_remote_levels": list(REMOTE_LEVELS),
        "level_one_remote_effect_repeated": False,
        "model_slot_cap": parent.MODEL_SLOT_CAP,
        "protected_watchers": audit["protected_watchers"],
        "shared_api_lease_active_before_activation": lease.get("active") is True,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "runtime_input_exactly_opaque_id_and_question": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "authorization": {
            "one_capacity_continuation_launch": not findings,
            "paired_benchmark_launch": False,
            "exact220": False,
            "evaluator": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    validate_activation(root, value=value)
    return value


def validate_activation(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    activation = dict(value) if value is not None else _read(root, ACTIVATION)
    if (
        activation.get("role") != "v24329_capacity_continuation_activation"
        or activation.get("protocol_id") != PROTOCOL_ID
        or activation.get("status") != "active"
        or activation.get("findings") != []
        or activation.get("launch_authorized") is not True
        or activation.get("protocol_sha256") != sha256(root / PROTOCOL)
        or activation.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or activation.get("new_remote_levels") != list(REMOTE_LEVELS)
        or activation.get("level_one_remote_effect_repeated") is not False
        or activation.get("model_slot_cap") != parent.MODEL_SLOT_CAP
        or activation.get("protected_watchers") != protected_watcher_snapshot()
        or activation.get("network_model_search_fetch_evaluator_or_api_called")
        is not False
        or activation.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or activation.get("authorization", {}).get(
            "one_capacity_continuation_launch"
        )
        is not True
        or any(
            enabled
            for key, enabled in activation.get("authorization", {}).items()
            if key != "one_capacity_continuation_launch"
        )
        or not _sealed(activation, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.43.29 activation drifted")
    validate_preaudit(root)
    return activation


def build_execution_start(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    activation = validate_activation(root)
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.43.29 execution surface is not pristine")
    head = _git_output(root, "rev-parse", "HEAD")
    remote = _git_output(root, "rev-parse", "target/main")
    lease = lease_observation(root, Path("/proc"))
    findings: list[str] = []
    if head != remote:
        findings.append("activation_commit_not_pushed")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24329_capacity_continuation_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "ready" if not findings else "rejected",
        "findings": findings,
        "execution_authorized": not findings,
        "activation_base_commit": head,
        "target_main_at_start": remote,
        "protocol_sha256": sha256(root / PROTOCOL),
        "activation_sha256": sha256(root / ACTIVATION),
        "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        "new_remote_levels": list(REMOTE_LEVELS),
        "level_one_remote_effect_repeated": False,
        "model_slot_cap": parent.MODEL_SLOT_CAP,
        "protected_watchers": activation["protected_watchers"],
        "shared_api_lease_active_before_execution_start": lease.get("active") is True,
        "api_called_before_execution_start": False,
        "runtime_input_exactly_opaque_id_and_question": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_or_evaluator_authorized": False,
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    validate_execution_start(root, value=value)
    return value


def validate_execution_start(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    start = dict(value) if value is not None else _read(root, EXECUTION_START)
    if (
        start.get("role")
        != "v24329_capacity_continuation_execution_start"
        or start.get("protocol_id") != PROTOCOL_ID
        or start.get("status") != "ready"
        or start.get("findings") != []
        or start.get("execution_authorized") is not True
        or start.get("protocol_sha256") != sha256(root / PROTOCOL)
        or start.get("activation_sha256") != sha256(root / ACTIVATION)
        or start.get("new_remote_levels") != list(REMOTE_LEVELS)
        or start.get("level_one_remote_effect_repeated") is not False
        or start.get("model_slot_cap") != parent.MODEL_SLOT_CAP
        or start.get("protected_watchers") != protected_watcher_snapshot()
        or start.get("api_called_before_execution_start") is not False
        or start.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or start.get("benchmark_or_evaluator_authorized") is not False
        or not _sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.43.29 execution-start drifted")
    validate_activation(root)
    return start


def _git_execution_ready(root: Path) -> bool:
    if (
        _git_output(root, "rev-parse", "HEAD")
        != _git_output(root, "rev-parse", "target/main")
        or _git_output(root, "status", "--porcelain")
    ):
        return False
    try:
        _git_output(root, "ls-files", "--error-unmatch", str(EXECUTION_START))
    except subprocess.CalledProcessError:
        return False
    return True


def _best_level(levels: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    passing = [level for level in levels if level.get("passed") is True]
    return max(
        passing,
        key=lambda item: (
            float(item["throughput_tasks_per_minute"]),
            -int(item["executor_count"]),
        ),
        default=None,
    )


def build_result(
    *,
    levels: Sequence[Mapping[str, Any]],
    activation: Mapping[str, Any],
    now: int | None = None,
) -> dict[str, Any]:
    values = [copy.deepcopy(dict(level)) for level in levels]
    for level in values:
        parent.validate_level(level)
    actual = [int(level["executor_count"]) for level in values]
    if actual != list(ALL_LEVELS[: len(values)]):
        raise RuntimeError("V2.43.29 levels are not a strict 1/2/4/8 prefix")
    if not values or values[0]["passed"] is not True:
        raise RuntimeError("V2.43.29 inherited level one is not passing")
    if any(level["passed"] is not True for level in values[:-1]):
        raise RuntimeError("V2.43.29 continued after a failed level")
    all_passed = len(values) == len(ALL_LEVELS) and all(
        level["passed"] for level in values
    )
    passing = [int(level["executor_count"]) for level in values if level["passed"]]
    best = _best_level(values)
    projection = (
        round(
            220.0
            / (float(best["throughput_tasks_per_minute"]) / 60.0),
            6,
        )
        if best is not None
        and float(best["throughput_tasks_per_minute"]) > 0
        else None
    )
    origins = {
        "1": "v24328_frozen_content_free_projection_no_remote_rerun",
        **{
            str(level): "v24329_new_remote_capacity_execution"
            for level in actual
            if level != 1
        },
    }
    value = {
        "artifact_version": 1,
        "role": "v24329_capacity_continuation_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "levels_requested": list(ALL_LEVELS),
        "new_remote_levels_requested": list(REMOTE_LEVELS),
        "model_slot_cap": parent.MODEL_SLOT_CAP,
        "provider_max_retries": MODEL_MAX_RETRIES,
        "levels": values,
        "level_execution_origins": origins,
        "level_one_remote_effect_repeated": False,
        "highest_passing_executor_count": max(passing) if passing else 0,
        "recommended_executor_count": (
            int(best["executor_count"]) if best is not None else 0
        ),
        "maximum_observed_throughput_tasks_per_minute": (
            float(best["throughput_tasks_per_minute"])
            if best is not None
            else 0.0
        ),
        "all_requested_levels_passed": all_passed,
        "capacity_only_exact220_projection_seconds": projection,
        "projection_is_not_a_benchmark_eta_or_quality_claim": True,
        "protected_watchers_unchanged": protected_watcher_snapshot()
        == activation["protected_watchers"],
        "task_text_identifier_query_url_page_prediction_response_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "credential_value_persisted_hashed_or_emitted": False,
        "official_evaluator_called": False,
        "resume_retry_task_skip_or_revaluation": False,
        "authorization": {
            "fresh_shared_prefix_paired_benchmark_protocol_design": all_passed,
            "paired_benchmark_launch": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_result(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    levels = value.get("levels")
    origins = value.get("level_execution_origins")
    authorization = value.get("authorization")
    if not isinstance(levels, list):
        raise RuntimeError("V2.43.29 result levels are absent")
    for level in levels:
        parent.validate_level(level)
    actual = [int(level["executor_count"]) for level in levels]
    all_passed = len(levels) == len(ALL_LEVELS) and all(
        level["passed"] for level in levels
    )
    passing = [int(level["executor_count"]) for level in levels if level["passed"]]
    best = _best_level(levels)
    expected_origins = {
        "1": "v24328_frozen_content_free_projection_no_remote_rerun",
        **{
            str(level): "v24329_new_remote_capacity_execution"
            for level in actual
            if level != 1
        },
    }
    encoded = json.dumps(value, ensure_ascii=False)
    if (
        value.get("role") != "v24329_capacity_continuation_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("levels_requested") != list(ALL_LEVELS)
        or value.get("new_remote_levels_requested") != list(REMOTE_LEVELS)
        or value.get("model_slot_cap") != parent.MODEL_SLOT_CAP
        or value.get("provider_max_retries") != MODEL_MAX_RETRIES
        or actual != list(ALL_LEVELS[: len(actual)])
        or not levels
        or levels[0]["passed"] is not True
        or any(level["passed"] is not True for level in levels[:-1])
        or origins != expected_origins
        or value.get("level_one_remote_effect_repeated") is not False
        or value.get("highest_passing_executor_count")
        != (max(passing) if passing else 0)
        or value.get("recommended_executor_count")
        != (int(best["executor_count"]) if best is not None else 0)
        or value.get("maximum_observed_throughput_tasks_per_minute")
        != (
            float(best["throughput_tasks_per_minute"])
            if best is not None
            else 0.0
        )
        or value.get("all_requested_levels_passed") is not all_passed
        or value.get("projection_is_not_a_benchmark_eta_or_quality_claim")
        is not True
        or value.get("protected_watchers_unchanged") is not True
        or value.get("task_text_identifier_query_url_page_prediction_response_or_hash_persisted")
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or value.get("credential_value_persisted_hashed_or_emitted") is not False
        or value.get("official_evaluator_called") is not False
        or value.get("resume_retry_task_skip_or_revaluation") is not False
        or not isinstance(authorization, Mapping)
        or authorization.get(
            "fresh_shared_prefix_paired_benchmark_protocol_design"
        )
        is not all_passed
        or any(
            enabled
            for key, enabled in authorization.items()
            if key != "fresh_shared_prefix_paired_benchmark_protocol_design"
        )
        or OPAQUE.search(encoded)
        or URL.search(encoded)
        or SECRET.search(encoded)
        or any(literal in encoded for literal in parent.CONTENT_LITERALS)
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.43.29 capacity result drifted")
    return dict(value)


def run_capacity_continuation(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    validate_preaudit(root)
    activation = validate_activation(root)
    validate_execution_start(root)
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.43.29 result surface is not pristine")
    if not _git_execution_ready(root):
        raise RuntimeError("V2.43.29 execution-start is not committed and pushed")
    if not _port_listening():
        raise RuntimeError("V2.43.29 keyless proxy is unavailable")
    levels = [inherited_level_one(root)]
    with acquire_deepwide_api_lease(
        root,
        owner=LEASE_OWNER,
        purpose=LEASE_PURPOSE,
        path=root / LEASE_PATH,
    ):
        with tempfile.TemporaryDirectory(dir=root / "outputs") as temporary:
            output_root = Path(temporary)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, parent.MODEL_SLOT_CAP + 1):
                (slots / f"slot_{index:02d}.lock").write_text(
                    "{}\n", encoding="utf-8"
                )
            for executor_count in REMOTE_LEVELS:
                level_root = output_root / f"level_{executor_count:02d}"
                level_root.mkdir()
                directories: list[Path] = []
                for ordinal in range(1, executor_count + 1):
                    directory = level_root / f"task_{ordinal:02d}"
                    directory.mkdir()
                    directories.append(directory)
                started = time.monotonic()
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=executor_count
                ) as pool:
                    futures = [
                        pool.submit(
                            parent._run_one,
                            root,
                            output_root,
                            slots,
                            directory,
                            ordinal,
                        )
                        for ordinal, directory in enumerate(directories, start=1)
                    ]
                    tasks: list[dict[str, Any]] = []
                    for ordinal, future in enumerate(futures, start=1):
                        try:
                            raw = future.result()
                        except Exception:
                            raw = parent._local_failure_projection(ordinal)
                        tasks.append(corrected_task_projection(raw))
                level = parent.summarize_level(
                    level=executor_count,
                    tasks=tasks,
                    batch_wall_seconds=max(0.0, time.monotonic() - started),
                )
                levels.append(level)
                if not level["passed"]:
                    break
    if protected_watcher_snapshot() != activation["protected_watchers"]:
        raise RuntimeError("V2.43.29 protected watcher identity drifted")
    value = build_result(levels=levels, activation=activation)
    publish(root / RESULT, value)
    return value


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preaudit(root)
    validate_activation(root)
    validate_execution_start(root)
    result = validate_result(_read(root, RESULT))
    passed = result["all_requested_levels_passed"] is True
    value = {
        "artifact_version": 1,
        "role": "v24329_capacity_continuation_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "capacity_continuation_go" if passed else "capacity_continuation_no_go",
        "passed": passed,
        "level_one_remote_effect_repeated": False,
        "highest_passing_executor_count": result[
            "highest_passing_executor_count"
        ],
        "recommended_executor_count": result["recommended_executor_count"],
        "maximum_observed_throughput_tasks_per_minute": result[
            "maximum_observed_throughput_tasks_per_minute"
        ],
        "capacity_only_exact220_projection_seconds": result[
            "capacity_only_exact220_projection_seconds"
        ],
        "projection_is_not_a_benchmark_eta_or_quality_claim": True,
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "result_sha256": sha256(root / RESULT),
            "parent_result_sha256": sha256(root / PARENT_RESULT),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
        "claim_scope": {
            "benchmark_external_shared_prefix_capacity_measured": True,
            "benchmark_quality_measured": False,
            "entropy_quality_improvement_proven": False,
            "future_population_or_sota_supported": False,
        },
        "authorization": {
            "fresh_shared_prefix_paired_benchmark_protocol_design": passed,
            "paired_benchmark_launch": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    validate_decision(value)
    return value


def validate_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    passed = value.get("passed")
    scope = value.get("claim_scope")
    authorization = value.get("authorization")
    if (
        value.get("role") != "v24329_capacity_continuation_decision"
        or value.get("protocol_id") != PROTOCOL_ID
        or not isinstance(passed, bool)
        or value.get("status")
        != (
            "capacity_continuation_go"
            if passed
            else "capacity_continuation_no_go"
        )
        or value.get("level_one_remote_effect_repeated") is not False
        or value.get("projection_is_not_a_benchmark_eta_or_quality_claim")
        is not True
        or not isinstance(scope, Mapping)
        or scope.get("benchmark_external_shared_prefix_capacity_measured")
        is not True
        or any(
            enabled
            for key, enabled in scope.items()
            if key != "benchmark_external_shared_prefix_capacity_measured"
        )
        or not isinstance(authorization, Mapping)
        or authorization.get(
            "fresh_shared_prefix_paired_benchmark_protocol_design"
        )
        is not passed
        or any(
            enabled
            for key, enabled in authorization.items()
            if key != "fresh_shared_prefix_paired_benchmark_protocol_design"
        )
        or not _sealed(value, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.43.29 capacity decision drifted")
    return dict(value)


def _continuation_child_present() -> bool:
    for item in process_snapshot():
        argv = item.get("argv")
        command = (
            " ".join(str(token) for token in argv)
            if isinstance(argv, list)
            else ""
        )
        if (
            (RUNNER_MARKER in command or parent.RUNNER_MARKER in command)
            and " child " in f" {command} "
        ):
            return True
    return False


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    validate_preaudit(root)
    activation = validate_activation(root)
    validate_execution_start(root)
    result = validate_result(_read(root, RESULT))
    decision = validate_decision(_read(root, DECISION))
    lease = lease_observation(root, Path("/proc"))
    encoded = json.dumps({"result": result, "decision": decision}, ensure_ascii=False)
    process_present = _continuation_child_present()
    findings: list[str] = []
    if OPAQUE.search(encoded) or URL.search(encoded) or SECRET.search(encoded):
        findings.append("task_identifier_url_or_credential_persisted")
    if any(literal in encoded for literal in parent.CONTENT_LITERALS):
        findings.append("task_content_persisted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active_after_result")
    if protected_watcher_snapshot() != activation["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    if process_present:
        findings.append("capacity_child_remained_active")
    if decision.get("provenance", {}).get("result_sha256") != sha256(root / RESULT):
        findings.append("decision_result_binding_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24329_capacity_continuation_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "findings": findings,
        "audit_valid": not findings,
        "execution_closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers_unchanged": protected_watcher_snapshot()
            == activation["protected_watchers"],
            "capacity_child_present": process_present,
            "temporary_execution_directory_remaining": False,
            "level_one_remote_effect_repeated": False,
            "task_text_identifier_query_url_page_prediction_response_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "credential_value_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "resume_retry_task_skip_or_revaluation": False,
            "invalid_result_path": None,
        },
        "authorization": {
            "fresh_shared_prefix_paired_benchmark_protocol_design": bool(
                decision["passed"] and not findings
            ),
            "paired_benchmark_launch": False,
            "exact220": False,
            "evaluator": False,
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "result_sha256": sha256(root / RESULT),
            "decision_sha256": sha256(root / DECISION),
            "parent_result_sha256": sha256(root / PARENT_RESULT),
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_postaudit(value)
    return value


def validate_postaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    if (
        value.get("role")
        != "v24329_capacity_continuation_postresult_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("execution_closure", {}).get("shared_api_lease_active")
        is not False
        or value.get("execution_closure", {}).get("protected_watchers_unchanged")
        is not True
        or value.get("execution_closure", {}).get("capacity_child_present")
        is not False
        or value.get("execution_closure", {}).get(
            "level_one_remote_effect_repeated"
        )
        is not False
        or any(
            enabled
            for key, enabled in value.get("authorization", {}).items()
            if key != "fresh_shared_prefix_paired_benchmark_protocol_design"
        )
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.29 postresult audit drifted")
    return dict(value)


def finalize(root: Path = ROOT) -> None:
    root = root.resolve()
    if not (root / DECISION).exists():
        publish(root / DECISION, build_decision(root))
    else:
        validate_decision(_read(root, DECISION))
    if not (root / POSTAUDIT).exists():
        publish(root / POSTAUDIT, build_postaudit(root))
    else:
        validate_postaudit(_read(root, POSTAUDIT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("protocol", "activation", "start", "run", "finalize")
    )
    args = parser.parse_args()
    if args.command == "protocol":
        publish(ROOT / PROTOCOL, build_protocol())
        publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation":
        publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start":
        publish(ROOT / EXECUTION_START, build_execution_start())
    elif args.command == "run":
        run_capacity_continuation(ROOT)
        finalize(ROOT)
    else:
        finalize(ROOT)
    print(json.dumps({"command": args.command, "status": "ok"}, sort_keys=True))


if __name__ == "__main__":
    main()
