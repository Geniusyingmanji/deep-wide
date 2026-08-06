#!/usr/bin/env python3
"""Append-only, zero-effect recovery controls for V2.46.79."""

from __future__ import annotations

import argparse
import ast
import builtins
import json
import os
import re
import socket
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
from scripts import audit_v24681_v24679_zero_effect_start_failure as failure_audit  # noqa: E402
from scripts import v24679_schema_dev64_control as old_control  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260806"
ROLE = "v24682_v24679_zero_effect_binding_recovery"
BUILD_AUDIT = Path(f"results/v24682_v24679_recovery_build_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24682_v24679_recovery_activation_v1_{DATE}.json")
EXECUTION_START = Path(
    f"results/v24682_v24679_recovery_execution_start_v1_{DATE}.json"
)
WRAPPER = Path("scripts/run_v24682_v24679_schema_dev64_recovery.py")
CONTROL = Path("scripts/v24682_v24679_schema_dev64_recovery_control.py")
TEST = Path("tests/test_v24682_v24679_schema_dev64_recovery.py")
FROZEN_RUNNER = Path("scripts/run_v24679_schema_dev64.py")
FROZEN_CHILD = Path("scripts/run_v24679_schema_dev64_task.py")
RECOVERY_SESSION = "deepwide-v24682-v24679-schema-dev64-recovery-v1"
FOCUSED_TESTS = (
    ("test_v24318_deadline_conservation_runtime.py", 8),
    ("test_v24319_runner_integration.py", 7),
    ("test_v24630_exact220.py", 5),
    ("test_v24677_expanded_visible_schema_runtime.py", 8),
    ("test_v24679_schema_dev64.py", 9),
    ("test_v24679_schema_dev64_control.py", 10),
    ("test_audit_v24681_v24679_zero_effect_start_failure.py", 4),
    ("test_v24682_v24679_schema_dev64_recovery.py", 8),
)
EXPECTED_TEST_COUNT = 59
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == contract.payload_sha256(unsigned)


def _read(path: Path) -> dict[str, Any]:
    return contract.read_object(ROOT / path)


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
        if "ps -eo" not in line and str(CONTROL) not in line
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


def _port_listening() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=0.5):
            return True
    except OSError:
        return False


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _run_tests() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for filename, expected in FOCUSED_TESTS:
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
                filename,
            ],
            cwd=ROOT,
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
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        output.append(
            {
                "file": filename,
                "expected_test_count": expected,
                "observed_test_count": observed,
                "passed": completed.returncode == 0 and observed == expected,
            }
        )
    return output


def _module_unbound_globals(path: Path) -> list[str]:
    tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    module_defs = set(dir(builtins)) | {"__file__", "__name__"}
    module_uses: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module_defs.add(node.name)
        elif isinstance(node, ast.Import):
            module_defs.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module_defs.update(alias.asname or alias.name for alias in node.names)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    module_defs.add(target.id)
    for function in [node for node in tree.body if isinstance(node, ast.FunctionDef)]:
        local = {
            argument.arg
            for argument in (
                *function.args.posonlyargs,
                *function.args.args,
                *function.args.kwonlyargs,
            )
        }
        if function.args.vararg:
            local.add(function.args.vararg.arg)
        if function.args.kwarg:
            local.add(function.args.kwarg.arg)
        for node in ast.walk(function):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                local.add(node.id)
            elif isinstance(node, ast.arg):
                # Includes parameters of nested lambdas/functions traversed by
                # ast.walk; their loads are not module-global dependencies.
                local.add(node.arg)
            elif isinstance(node, ast.ExceptHandler) and isinstance(node.name, str):
                local.add(node.name)
            elif isinstance(node, ast.comprehension) and isinstance(node.target, ast.Name):
                local.add(node.target.id)
        for node in ast.walk(function):
            if (
                isinstance(node, ast.Name)
                and isinstance(node.ctx, ast.Load)
                and node.id not in local
                and node.id not in module_defs
            ):
                module_uses.add(node.id)
    return sorted(module_uses)


def _wrapper_contract() -> bool:
    path = ROOT / WRAPPER
    if path.is_symlink() or not path.is_file():
        return False
    tree = ast.parse(path.read_text(encoding="utf-8"))
    assignments: list[tuple[str, str]] = []
    calls: list[str] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Attribute)
            and isinstance(node.targets[0].value, ast.Name)
            and node.targets[0].value.id == "frozen"
            and isinstance(node.value, ast.Attribute)
        ):
            assignments.append((node.targets[0].attr, node.value.attr))
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.append(node.func.id)
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                calls.append(f"{node.func.value.id}.{node.func.attr}")
    return (
        sorted(assignments)
        == [("EXECUTION_START", "EXECUTION_START"), ("FORWARD_AUDIT", "FORWARD_AUDIT")]
        and calls.count("recovery.validate_execution_start") == 1
        and calls.count("frozen.main") == 1
    )


def _parent_failure() -> dict[str, Any]:
    value = _read(failure_audit.FAILURE)
    failure_audit.validate_receipt(value)
    if (
        value.get("authorization", {}).get("append_only_recovery_design") is not True
        or value.get("authorization", {}).get("reuse_v24679_execution_start") is not False
        or value.get("effect_boundary", {}).get(
            "http_api_model_search_fetch_or_evaluator_effect"
        )
        is not False
    ):
        raise RuntimeError("V2.46.82 zero-effect parent drifted")
    return value


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    parent = _parent_failure()
    forward = contract.validate_forward_contract(ROOT)
    old_control.validate_execution_start(ROOT)
    sources = (WRAPPER, CONTROL, TEST, FROZEN_RUNNER, FROZEN_CHILD, failure_audit.FAILURE)
    manifest = {str(path): contract.sha256(ROOT / path) for path in sources}
    suites = _run_tests()
    test_count = sum(item["observed_test_count"] for item in suites)
    unbound = _module_unbound_globals(FROZEN_RUNNER)
    wrapper_valid = _wrapper_contract()
    secrets = [
        str(path)
        for path in (WRAPPER, CONTROL, TEST)
        if SECRET.search((ROOT / path).read_text(encoding="utf-8"))
    ]
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    tracked = all(_tracked(path) for path in sources)
    lease = lease_observation(ROOT, Path("/proc"))
    active = any(
        _active(marker)
        for marker in (
            contract.RUNNER_MARKER,
            contract.CHILD_MARKER,
            str(WRAPPER),
        )
    )
    future = _future_pristine(
        (BUILD_AUDIT, ACTIVATION, EXECUTION_START, contract.OUTPUT_ROOT,
         contract.FORWARD_RESULT, contract.FORWARD_AUDIT)
    )
    watchers = contract.protected_watcher_snapshot()
    frozen_runner_matches_failure = (
        manifest[str(FROZEN_RUNNER)] == parent["failure"]["runner_source_sha256"]
    )
    findings: list[str] = []
    if head != remote:
        findings.append("recovery_source_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if not tracked:
        findings.append("recovery_source_not_tracked")
    if any(not item["passed"] for item in suites) or test_count != EXPECTED_TEST_COUNT:
        findings.append("recovery_regression_failed_or_count_drifted")
    if unbound != ["FORWARD_AUDIT"]:
        findings.append("frozen_runner_unbound_global_set_drifted")
    if not wrapper_valid:
        findings.append("recovery_wrapper_contract_drifted")
    if secrets:
        findings.append("credential_literal_in_recovery_surface")
    if not frozen_runner_matches_failure:
        findings.append("frozen_runner_changed_after_failure")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("v24679_or_recovery_process_active")
    if not _session_absent():
        findings.append("recovery_tmux_session_active")
    if not future:
        findings.append("recovery_or_forward_surface_not_pristine")
    if watchers != forward["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24682_v24679_recovery_build_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {
            "zero_effect_failure_path": str(failure_audit.FAILURE),
            "zero_effect_failure_sha256": contract.sha256(ROOT / failure_audit.FAILURE),
            "valid": True,
            "old_execution_start_reusable": False,
        },
        "recovery": {
            "policy": ROLE,
            "frozen_runner_source_unchanged": frozen_runner_matches_failure,
            "frozen_child_source_unchanged_from_forward_contract": (
                manifest[str(FROZEN_CHILD)]
                == forward["dependency_manifest"][str(FROZEN_CHILD)]
            ),
            "unbound_frozen_runner_globals": unbound,
            "process_private_bindings": {
                "FORWARD_AUDIT": str(contract.FORWARD_AUDIT),
                "EXECUTION_START": str(EXECUTION_START),
            },
            "wrapper_contract_valid": wrapper_valid,
            "task_budget_model_search_fetch_parser_or_child_changed": False,
            "resume_retry_skip_selective_rerun": False,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "tests": {
            "suites": suites,
            "test_count": test_count,
            "passed": all(item["passed"] for item in suites)
            and test_count == EXPECTED_TEST_COUNT,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
        },
        "git": {
            "head": head,
            "target_main": remote,
            "head_equals_target_main": head == remote,
            "worktree_clean": clean,
            "all_sources_tracked": tracked,
        },
        "runtime_state": {
            "shared_api_lease_active": lease.get("active"),
            "v24679_or_recovery_process_active": active,
            "recovery_tmux_session_absent": _session_absent(),
            "future_surface_pristine": future,
            "protected_watchers": watchers,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "remote_network_model_search_fetch_benchmark_or_evaluator_called_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "recovery_activation_design": not findings,
            "recovery_launch": False,
            "old_execution_start_reuse": False,
            "evaluator": False,
            "exact220": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24682_v24679_recovery_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("parent", {}).get("old_execution_start_reusable") is not False
        or copied.get("recovery", {}).get("unbound_frozen_runner_globals")
        != ["FORWARD_AUDIT"]
        or copied.get("recovery", {}).get("wrapper_contract_valid") is not True
        or copied.get("recovery", {}).get(
            "task_budget_model_search_fetch_parser_or_child_changed"
        )
        is not False
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("test_count") != EXPECTED_TEST_COUNT
        or copied.get("runtime_state", {}).get("shared_api_lease_active") is not False
        or copied.get("runtime_state", {}).get("v24679_or_recovery_process_active")
        is not False
        or copied.get("runtime_state", {}).get("future_surface_pristine") is not True
        or copied.get("authorization")
        != {
            "recovery_activation_design": True,
            "recovery_launch": False,
            "old_execution_start_reuse": False,
            "evaluator": False,
            "exact220": False,
        }
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.82 recovery build audit drifted")
    return copied


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    audit = validate_audit(_read(BUILD_AUDIT))
    forward = contract.validate_forward_contract(ROOT)
    old_control.validate_execution_start(ROOT)
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    lease = lease_observation(ROOT, Path("/proc"))
    active = any(
        _active(marker)
        for marker in (contract.RUNNER_MARKER, contract.CHILD_MARKER, str(WRAPPER))
    )
    future = _future_pristine(
        (ACTIVATION, EXECUTION_START, contract.OUTPUT_ROOT,
         contract.FORWARD_RESULT, contract.FORWARD_AUDIT)
    )
    proxy = _port_listening()
    watchers = contract.protected_watcher_snapshot()
    findings: list[str] = []
    if head != remote:
        findings.append("recovery_build_audit_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("v24679_or_recovery_process_active")
    if not future:
        findings.append("recovery_or_forward_surface_not_pristine")
    if not proxy:
        findings.append("keyless_proxy_not_listening")
    if watchers != forward["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24682_v24679_recovery_activation",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "build_audit_sha256": contract.sha256(ROOT / BUILD_AUDIT),
        "zero_effect_failure_sha256": contract.sha256(ROOT / failure_audit.FAILURE),
        "old_execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
        "old_execution_start_reusable": False,
        "frozen_runner_sha256": audit["source_manifest"][str(FROZEN_RUNNER)],
        "recovery_wrapper_sha256": audit["source_manifest"][str(WRAPPER)],
        "protected_watchers": watchers,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "authorization": {
            "one_recovery_forward_after_new_start": not findings,
            "old_execution_start_reuse": False,
            "evaluator": False,
            "exact220": False,
        },
    }
    value["activation_payload_sha256"] = contract.payload_sha256(value)
    if findings:
        raise RuntimeError("V2.46.82 activation failed: " + ",".join(findings))
    return value


def validate_activation(value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(ACTIVATION)
    audit = validate_audit(_read(BUILD_AUDIT))
    if (
        copied.get("role") != "v24682_v24679_recovery_activation"
        or copied.get("status") != "active"
        or copied.get("findings") != []
        or copied.get("launch_authorized") is not True
        or copied.get("build_audit_sha256") != contract.sha256(ROOT / BUILD_AUDIT)
        or copied.get("zero_effect_failure_sha256")
        != contract.sha256(ROOT / failure_audit.FAILURE)
        or copied.get("old_execution_start_sha256")
        != contract.sha256(ROOT / contract.EXECUTION_START)
        or copied.get("old_execution_start_reusable") is not False
        or copied.get("frozen_runner_sha256")
        != audit["source_manifest"][str(FROZEN_RUNNER)]
        or copied.get("recovery_wrapper_sha256")
        != audit["source_manifest"][str(WRAPPER)]
        or copied.get("protected_watchers") != contract.protected_watcher_snapshot()
        or copied.get("authorization")
        != {
            "one_recovery_forward_after_new_start": True,
            "old_execution_start_reuse": False,
            "evaluator": False,
            "exact220": False,
        }
        or not _sealed(copied, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.46.82 recovery activation drifted")
    return copied


def build_execution_start(*, now: int | None = None) -> dict[str, Any]:
    activation = validate_activation()
    head = _git("rev-parse", "HEAD")
    remote = _git("rev-parse", "target/main")
    clean = _git("status", "--porcelain") == ""
    lease = lease_observation(ROOT, Path("/proc"))
    active = any(
        _active(marker)
        for marker in (contract.RUNNER_MARKER, contract.CHILD_MARKER, str(WRAPPER))
    )
    future = _future_pristine(
        (EXECUTION_START, contract.OUTPUT_ROOT, contract.FORWARD_RESULT,
         contract.FORWARD_AUDIT)
    )
    findings: list[str] = []
    if head != remote:
        findings.append("recovery_activation_commit_not_pushed")
    if not clean:
        findings.append("worktree_not_clean")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if active:
        findings.append("v24679_or_recovery_process_active")
    if not future:
        findings.append("recovery_or_forward_surface_not_pristine")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    if activation["protected_watchers"] != contract.protected_watcher_snapshot():
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        # The frozen runner validates this compatibility role after the wrapper
        # redirects its EXECUTION_START binding to this successor receipt.
        "role": "v24679_schema_dev64_execution_start",
        "successor_role": "v24682_v24679_recovery_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "authorized" if not findings else "rejected",
        "findings": findings,
        "execution_authorized": not findings,
        "activation_base_commit": head,
        "target_main_at_start": remote,
        "forward_contract_sha256": contract.sha256(ROOT / contract.FORWARD_CONTRACT),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preaudit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        # Compatibility binding required by frozen validate_control().
        "activation_sha256": contract.sha256(ROOT / contract.ACTIVATION),
        "recovery_activation_sha256": contract.sha256(ROOT / ACTIVATION),
        "zero_effect_failure_sha256": contract.sha256(ROOT / failure_audit.FAILURE),
        "revoked_execution_start_sha256": contract.sha256(
            ROOT / contract.EXECUTION_START
        ),
        "revoked_execution_start_reusable": False,
        "selected_pair_tasks": contract.SELECTED_COUNT,
        "real_child_runs": contract.TOTAL_CHILD_RUNS,
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "model_slot_cap": contract.MODEL_SLOT_CAP,
        "protected_watchers": activation["protected_watchers"],
        "process_private_binding_patch": {
            "FORWARD_AUDIT": str(contract.FORWARD_AUDIT),
            "EXECUTION_START": str(EXECUTION_START),
        },
        "api_called_before_execution_start": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "authorization": {
            "one_fresh_paired_dev64_forward": not findings,
            "evaluator": False,
            "exact220": False,
        },
    }
    value["execution_start_payload_sha256"] = contract.payload_sha256(value)
    if findings:
        raise RuntimeError("V2.46.82 execution start failed: " + ",".join(findings))
    return value


def validate_execution_start(value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    copied = dict(value) if value is not None else _read(EXECUTION_START)
    activation = validate_activation()
    if (
        copied.get("role") != "v24679_schema_dev64_execution_start"
        or copied.get("successor_role")
        != "v24682_v24679_recovery_execution_start"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("status") != "authorized"
        or copied.get("findings") != []
        or copied.get("execution_authorized") is not True
        or copied.get("activation_base_commit") != copied.get("target_main_at_start")
        or copied.get("forward_contract_sha256")
        != contract.sha256(ROOT / contract.FORWARD_CONTRACT)
        or copied.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or copied.get("preaudit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or copied.get("activation_sha256")
        != contract.sha256(ROOT / contract.ACTIVATION)
        or copied.get("recovery_activation_sha256")
        != contract.sha256(ROOT / ACTIVATION)
        or copied.get("zero_effect_failure_sha256")
        != contract.sha256(ROOT / failure_audit.FAILURE)
        or copied.get("revoked_execution_start_sha256")
        != contract.sha256(ROOT / contract.EXECUTION_START)
        or copied.get("revoked_execution_start_reusable") is not False
        or copied.get("selected_pair_tasks") != contract.SELECTED_COUNT
        or copied.get("real_child_runs") != contract.TOTAL_CHILD_RUNS
        or copied.get("executor_concurrency") != contract.EXECUTOR_CONCURRENCY
        or copied.get("model_slot_cap") != contract.MODEL_SLOT_CAP
        or copied.get("protected_watchers") != activation["protected_watchers"]
        or copied.get("process_private_binding_patch")
        != {
            "FORWARD_AUDIT": str(contract.FORWARD_AUDIT),
            "EXECUTION_START": str(EXECUTION_START),
        }
        or copied.get("api_called_before_execution_start") is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or copied.get("authorization")
        != {
            "one_fresh_paired_dev64_forward": True,
            "evaluator": False,
            "exact220": False,
        }
        or not _sealed(copied, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.46.82 recovery execution start drifted")
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit", "activation", "start"))
    args = parser.parse_args()
    if args.command == "audit":
        value, path = build_audit(), BUILD_AUDIT
        validate_audit(value)
    elif args.command == "activation":
        value, path = build_activation(), ACTIVATION
        validate_activation(value)
    else:
        value, path = build_execution_start(), EXECUTION_START
        validate_execution_start(value)
    publish(ROOT / path, value)
    print(json.dumps({"command": args.command, "path": str(path)}, sort_keys=True))


if __name__ == "__main__":
    main()
