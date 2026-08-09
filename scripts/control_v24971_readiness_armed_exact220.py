#!/usr/bin/env python3
"""Freeze V2.49.71 and authorize only its already-armed live runner."""

from __future__ import annotations

import argparse
import copy
import fcntl
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

from deepwide_agent import v24971_readiness_armed_exact220_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


RUNTIME_SOURCES = (
    contract.SOURCE,
    contract.RUNNER,
    contract.CHILD,
    contract.READINESS_SOURCE,
    Path("scripts/run_v24857_pacing_aware_exact220.py"),
    Path("scripts/run_v24857_pacing_aware_exact220_task.py"),
    contract.TRANSPORT_SOURCE,
    contract.ADMISSION_SOURCE,
    Path("scripts/run_v24800_exact220.py"),
    Path("scripts/run_v24635_exact220.py"),
    Path("scripts/run_v24635_exact220_task.py"),
    Path("src/deepwide_agent/v24796_deadline_tavily_search.py"),
    Path("src/deepwide_agent/v24799_fixed_full_budget_control.py"),
    Path("src/deepwide_agent/v24272_two_wave_entropy_voc.py"),
    Path("src/deepwide_agent/v24272_two_wave_retrieval.py"),
    Path("src/deepwide_agent/v24273_two_wave_task_runtime.py"),
)
TEST_SUITES = (
    (contract.TEST, 20, 300),
    (contract.READINESS_TEST, 10, 240),
    (Path("tests/test_v24857_pacing_aware_exact220.py"), 13, 240),
    (Path("tests/test_v24856_pacing_aware_admission.py"), 7, 240),
    (Path("tests/test_v24854_rate_aware_exact220.py"), 11, 240),
    (Path("tests/test_v24852_rate_aware_tavily_search.py"), 11, 240),
    (Path("tests/test_v24800_exact220.py"), 12, 240),
    (Path("tests/test_v24799_fixed_full_budget_control.py"), 5, 240),
    (Path("tests/test_v24796_deadline_tavily_search.py"), 6, 240),
    (Path("tests/test_v24635_exact220.py"), 10, 240),
    (Path("tests/test_v24630_thin_backfill_search.py"), 2, 180),
    (Path("tests/test_v24319_runner_integration.py"), 7, 180),
    (Path("tests/test_v24468_total_wall_transport.py"), 8, 180),
)
EXPECTED_TESTS = sum(item[1] for item in TEST_SUITES)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(item) for item in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.49.71 control requires clean pushed HEAD")


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.49.71 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.71 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _protocol() -> dict[str, Any]:
    return contract.validate_protocol(ROOT, _read(ROOT / contract.PROTOCOL))


def _runtime_findings() -> tuple[list[str], list[str], list[str]]:
    fields: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in RUNTIME_SOURCES:
        path = ROOT / relative
        source = path.read_text(encoding="utf-8")
        fields.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if SECRET.search(source):
            secrets.append(str(relative))
    return sorted(set(fields)), sorted(set(evaluator)), sorted(set(secrets))


def _run_tests() -> tuple[int, bool, list[dict[str, Any]]]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    rows = []
    for path, expected, timeout in TEST_SUITES:
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m",
                "unittest", "discover", "-s", "tests", "-p", path.name, "-v",
            ],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=timeout, check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append(
            {
                "path": str(path),
                "expected": expected,
                "observed": observed,
                "passed": completed.returncode == 0 and observed == expected,
                "output_sha256": contract.payload_sha256(completed.stdout),
            }
        )
    total = sum(row["observed"] for row in rows)
    return total, all(row["passed"] for row in rows) and total == EXPECTED_TESTS, rows


def _endpoint() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=0.5):
            return True
    except OSError:
        return False


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _lease_held_by(pid: int) -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink() or not path.is_file():
        return False
    try:
        with path.open("r", encoding="utf-8") as observation:
            value = json.loads(observation.read(4096))
        with path.open("a+", encoding="utf-8") as handle:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                return (
                    value.get("pid") == pid
                    and value.get("owner") == contract.LEASE_OWNER
                    and value.get("purpose") == contract.LEASE_PURPOSE
                )
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                return False
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def _process_rows() -> list[tuple[int, str, str]]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=False,
    )
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 3 and "python" in parts[1].casefold():
            output.append((int(parts[0]), parts[1], parts[2]))
    return output


def _active_conflicts(*, allowed_pid: int | None = None) -> list[int]:
    markers = (
        contract.RUNNER_MARKER,
        contract.CHILD_MARKER,
        "scripts/run_v24791_exact220.py",
        "scripts/run_v24791_exact220_task.py",
        "scripts/run_v24792_exact220.py",
        "scripts/run_v24792_exact220_task.py",
        "scripts/run_v24798_exact220.py",
        "scripts/run_v24798_exact220_task.py",
        "scripts/run_v24635_exact220.py",
        "scripts/run_v24635_exact220_task.py",
        "scripts/run_official_eval_local.py",
    )
    return sorted(
        pid
        for pid, _comm, command in _process_rows()
        if pid != os.getpid()
        and pid != allowed_pid
        and any(marker in command for marker in markers)
    )


def _runner_marker_matches(pid: int) -> bool:
    return any(
        observed == pid and contract.RUNNER_MARKER in command
        for observed, _comm, command in _process_rows()
    )


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def _ancestor(parent: str, child: str) -> bool:
    return subprocess.run(
        ["git", "merge-base", "--is-ancestor", parent, child], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    protocol = _protocol()
    _clean_pushed()
    fields, evaluator, secrets = _runtime_findings()
    observed, tests_passed, suites = _run_tests()
    endpoint = _endpoint()
    lease = _lease_inactive()
    conflicts = _active_conflicts()
    watchers = contract.protected_watcher_snapshot()
    future = _future_pristine(
        (
            contract.PREAUDIT, contract.ARMED_RECEIPT, contract.EXECUTION_START,
            contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.OUTPUT_ROOT,
        )
    )
    armed_pristine = _future_pristine((contract.ARMED_RECEIPT,))
    findings: list[str] = []
    if fields:
        findings.append("privileged_runtime_field_access")
    if evaluator:
        findings.append("evaluator_capability_in_forward_surface")
    if secrets:
        findings.append("credential_literal_in_forward_surface")
    if not tests_passed:
        findings.append("focused_tests_failed_or_count_drifted")
    if not endpoint:
        findings.append("gpt56_endpoint_unreachable")
    if not lease:
        findings.append("shared_api_lease_active")
    if conflicts:
        findings.append("conflicting_benchmark_or_evaluator_active")
    if watchers != protocol["execution"]["protected_watchers"]:
        findings.append("protected_watcher_drifted")
    if not future:
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24971_readiness_armed_exact220_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "dependency_manifest_sha256": protocol["dependency_manifest_sha256"],
        "git": {
            "head": _git("rev-parse", "HEAD"),
            "target_main": _git("rev-parse", "target/main"),
            "head_equals_target_main": True,
            "worktree_clean": True,
        },
        "tests": {
            "expected": EXPECTED_TESTS,
            "observed": observed,
            "passed": tests_passed,
            "suites": suites,
        },
        "label_blind_audit": {
            "privileged_runtime_field_accesses": fields,
            "evaluator_capabilities": evaluator,
            "credential_literal_hits": secrets,
            "passed": not fields and not evaluator and not secrets,
        },
        "runtime_state": {
            "gpt56_endpoint_reachable_without_provider_request": endpoint,
            "shared_api_lease_inactive": lease,
            "conflicting_process_pids": conflicts,
            "protected_watchers": watchers,
            "future_surface_pristine": future,
            "armed_surface_pristine": armed_pristine,
        },
        "readiness_policy": contract.readiness_policy(),
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
            "credential_values_read_persisted_hashed_or_emitted_by_audit": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": (
            copy.deepcopy(contract.PREAUDIT_AUTHORIZATION)
            if not findings
            else {
                **contract.PREAUDIT_AUTHORIZATION,
                "same_process_readiness_arming": False,
            }
        ),
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = contract.validate_preaudit(ROOT, value)
    if (
        copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("git", {}).get("head_equals_target_main") is not True
        or copied.get("git", {}).get("worktree_clean") is not True
    ):
        raise RuntimeError("V2.49.71 preactivation audit evidence drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    protocol = _protocol()
    armed = contract.validate_armed_receipt(
        ROOT, _read(ROOT / contract.ARMED_RECEIPT)
    )
    _clean_pushed()
    observed_now = int(time.time()) if now is None else int(now)
    runner = armed["runner"]
    parent_head = _git("rev-parse", "HEAD")
    checks = {
        "armed_receipt_commit_pushed": (
            _tracked(contract.ARMED_RECEIPT)
            and parent_head == _git("rev-parse", "target/main")
        ),
        "arming_git_head_is_ancestor_of_armed_commit": (
            armed["arming_git_head"] != parent_head
            and _ancestor(armed["arming_git_head"], parent_head)
        ),
        "authorization_deadline_open": (
            armed["created_at_unix"] <= observed_now <= armed["authorization_deadline_unix"]
        ),
        "conflicting_process_pids_empty_except_bound_runner": (
            not _active_conflicts(allowed_pid=runner["pid"])
        ),
        "execution_surface_pristine": _future_pristine(
            (
                contract.EXECUTION_START, contract.FORWARD_RESULT,
                contract.FORWARD_AUDIT, contract.OUTPUT_ROOT,
            )
        ),
        "gpt56_endpoint_reachable_without_provider_request": _endpoint(),
        "protected_watchers_unchanged": (
            contract.protected_watcher_snapshot()
            == protocol["execution"]["protected_watchers"]
        ),
        "runner_command_marker_matches": _runner_marker_matches(runner["pid"]),
        "runner_pid_start_ticks_live": contract.process_matches(
            runner["pid"], runner["start_ticks"]
        ),
        "shared_api_lease_held_by_bound_runner": _lease_held_by(runner["pid"]),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v24971_readiness_armed_exact220_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "status": "authorized_not_started" if not findings else "not_authorized",
        "created_at_unix": observed_now,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "armed_receipt_sha256": contract.sha256(ROOT / contract.ARMED_RECEIPT),
        "armed_receipt_payload_sha256": armed["armed_receipt_payload_sha256"],
        "readiness_receipt_payload_sha256": armed[
            "readiness_receipt_payload_sha256"
        ],
        "dependency_manifest_sha256": protocol["dependency_manifest_sha256"],
        "authorization_parent_git_head": parent_head,
        "runner": copy.deepcopy(runner),
        "session_nonce": armed["readiness"]["session_nonce"],
        "selected": contract.SELECTED_COUNT,
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "model_slot_cap": contract.MODEL_SLOT_CAP,
        "tavily_key_slot_cap": contract.TAVILY_KEY_SLOT_CAP,
        "protected_watchers": contract.protected_watcher_snapshot(),
        "checks": checks,
        "findings": findings,
        "first_benchmark_model_search_fetch_effect_started": False,
        "credential_value_or_hash_persisted_emitted_or_logged": False,
        "authorization": (
            copy.deepcopy(contract.START_AUTHORIZATION)
            if not findings
            else {
                **contract.START_AUTHORIZATION,
                "single_fresh_exact220_forward": False,
            }
        ),
    }
    value["execution_start_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_start(value: Mapping[str, Any], *, now: int | None = None) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if not _sealed(copied, "execution_start_payload_sha256"):
        raise RuntimeError("V2.49.71 execution start seal drifted")
    existing = ROOT / contract.EXECUTION_START
    if existing.exists() or existing.is_symlink():
        return contract.validate_execution_start(
            ROOT, _protocol(), now=now, require_current_runner=False
        )
    temporary = existing.with_name(f".{existing.name}.{os.getpid()}.validation")
    publish_new(temporary, copied)
    try:
        original = contract.EXECUTION_START
        contract.EXECUTION_START = temporary.relative_to(ROOT)
        try:
            return contract.validate_execution_start(
                ROOT, _protocol(), now=now, require_current_runner=False
            )
        finally:
            contract.EXECUTION_START = original
    finally:
        temporary.unlink(missing_ok=True)


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
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
    parser.add_argument("command", choices=("protocol", "audit", "start"))
    args = parser.parse_args()
    if args.command == "protocol":
        value = contract.build_protocol(ROOT, now=int(time.time()))
        path = contract.PROTOCOL
    elif args.command == "audit":
        value = validate_preaudit(build_preaudit())
        path = contract.PREAUDIT
    else:
        value = build_start()
        if value["findings"]:
            raise RuntimeError(
                "V2.49.71 execution start is not authorized: "
                + ",".join(value["findings"])
            )
        validate_start(value)
        path = contract.EXECUTION_START
    publish_new(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value["role"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
