#!/usr/bin/env python3
"""Preregister, audit, and authorize one V2.47.98 exact-220 forward."""

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

from deepwide_agent import v24798_exact220_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


RUNTIME_SOURCES = (
    contract.RUNNER,
    contract.CHILD,
    contract.TRANSPORT,
    Path("scripts/run_v24635_exact220.py"),
    Path("scripts/run_v24635_exact220_task.py"),
)
TEST_SUITES = (
    (Path("tests/test_v24798_exact220.py"), 12, 240),
    (Path("tests/test_v24796_deadline_tavily_search.py"), 6, 240),
    (Path("tests/test_v24635_exact220.py"), 10, 240),
    (Path("tests/test_v24630_thin_backfill_search.py"), 2, 180),
    (Path("tests/test_v24319_runner_integration.py"), 7, 180),
    (Path("tests/test_v24468_total_wall_transport.py"), 8, 180),
)
EXPECTED_TESTS = 45
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(item) for item in SECRET_PREFIXES) + r")[A-Za-z0-9_-]{16,}")
PREAUDIT_AUTH = {
    "execution_start_generation": True,
    "single_fresh_exact220_forward": False,
    "evaluator_call": False,
    "retry_resume_skip_or_selective_rerun": False,
}
START_AUTH = {
    "single_fresh_exact220_forward": True,
    "evaluator_call": False,
    "retry_resume_skip_or_selective_rerun": False,
}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
        raise RuntimeError("V2.47.98 control requires clean pushed HEAD")


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"V2.47.98 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.98 expected JSON object")
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
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", path.name, "-v"],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=timeout, check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append({
            "path": str(path), "expected": expected, "observed": observed,
            "passed": completed.returncode == 0 and observed == expected,
            "output_sha256": contract.payload_sha256(completed.stdout),
        })
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


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=False,
    )
    markers = (
        contract.RUNNER_MARKER,
        contract.CHILD_MARKER,
        "scripts/run_v24791_exact220.py",
        "scripts/run_v24791_exact220_task.py",
        "scripts/run_v24792_exact220.py",
        "scripts/run_v24792_exact220_task.py",
        "scripts/run_v24635_exact220.py",
        "scripts/run_v24635_exact220_task.py",
        "scripts/run_official_eval_local.py",
    )
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 3 and "python" in parts[1].casefold() and any(marker in parts[2] for marker in markers):
            output.append(int(parts[0]))
    return sorted(output)


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in paths)


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    protocol = _protocol()
    _clean_pushed()
    fields, evaluator, secrets = _runtime_findings()
    observed, tests_passed, suites = _run_tests()
    endpoint = _endpoint()
    lease = _lease_inactive()
    conflicts = _active_conflicts()
    watchers = contract.protected_watcher_snapshot()
    future = _future_pristine((contract.PREAUDIT, contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.OUTPUT_ROOT))
    findings: list[str] = []
    if fields: findings.append("privileged_runtime_field_access")
    if evaluator: findings.append("evaluator_capability_in_forward_surface")
    if secrets: findings.append("credential_literal_in_forward_surface")
    if not tests_passed: findings.append("focused_tests_failed_or_count_drifted")
    if not endpoint: findings.append("gpt56_endpoint_unreachable")
    if not lease: findings.append("shared_api_lease_active")
    if conflicts: findings.append("conflicting_benchmark_or_evaluator_active")
    if watchers != protocol["execution"]["protected_watchers"]: findings.append("protected_watcher_drifted")
    if not future: findings.append("future_surface_not_pristine")
    valid = not findings
    value = {
        "artifact_version": 1,
        "role": "v24798_exact220_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "dependency_manifest_sha256": protocol["dependency_manifest_sha256"],
        "git": {"head": _git("rev-parse", "HEAD"), "target_main": _git("rev-parse", "target/main"), "head_equals_target_main": True, "worktree_clean": True},
        "tests": {"expected": EXPECTED_TESTS, "observed": observed, "passed": tests_passed, "suites": suites},
        "label_blind_audit": {"privileged_runtime_field_accesses": fields, "evaluator_capabilities": evaluator, "credential_literal_hits": secrets, "passed": not fields and not evaluator and not secrets},
        "runtime_state": {"gpt56_endpoint_reachable_without_provider_request": endpoint, "shared_api_lease_inactive": lease, "conflicting_process_pids": conflicts, "protected_watchers": watchers, "future_surface_pristine": future},
        "neutral_transport_gate": protocol["neutral_transport_gate"],
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "prior_v24791_output_prediction_result_score_or_evaluator_opened_or_hashed": False,
            "network_model_search_fetch_or_evaluator_called_by_audit": False,
            "credential_values_read_persisted_hashed_or_emitted_by_audit": False,
        },
        "findings": findings,
        "audit_valid": valid,
        "authorization": dict(PREAUDIT_AUTH) if valid else {**PREAUDIT_AUTH, "execution_start_generation": False},
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    protocol = _protocol()
    if (
        copied.get("role") != "v24798_exact220_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True or copied.get("findings") != []
        or copied.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or copied.get("dependency_manifest_sha256") != protocol["dependency_manifest_sha256"]
        or copied.get("neutral_transport_gate") != protocol["neutral_transport_gate"]
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("gpt56_endpoint_reachable_without_provider_request") is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("runtime_state", {}).get("conflicting_process_pids") != []
        or copied.get("runtime_state", {}).get("future_surface_pristine") is not True
        or copied.get("runtime_state", {}).get("protected_watchers") != protocol["execution"]["protected_watchers"]
        or copied.get("authorization") != PREAUDIT_AUTH
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.98 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    protocol = _protocol()
    audit = validate_preaudit(_read(ROOT / contract.PREAUDIT))
    _clean_pushed()
    endpoint = _endpoint()
    lease = _lease_inactive()
    conflicts = _active_conflicts()
    watchers = contract.protected_watcher_snapshot()
    future = _future_pristine((contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.OUTPUT_ROOT))
    findings: list[str] = []
    if audit.get("authorization") != PREAUDIT_AUTH: findings.append("preactivation_chain_invalid")
    if not endpoint: findings.append("gpt56_endpoint_unreachable")
    if not lease: findings.append("shared_api_lease_active")
    if conflicts: findings.append("conflicting_benchmark_or_evaluator_active")
    if watchers != protocol["execution"]["protected_watchers"]: findings.append("protected_watcher_drifted")
    if not future: findings.append("future_surface_not_pristine")
    valid = not findings
    value = {
        "artifact_version": 1,
        "role": "v24798_exact220_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "status": "authorized_not_started" if valid else "not_authorized",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "dependency_manifest_sha256": protocol["dependency_manifest_sha256"],
        "selected": contract.SELECTED_COUNT,
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "model_slot_cap": contract.MODEL_SLOT_CAP,
        "tavily_key_slot_cap": contract.TAVILY_KEY_SLOT_CAP,
        "protected_watchers": watchers,
        "checks": {"gpt56_endpoint_reachable_without_provider_request": endpoint, "shared_api_lease_inactive": lease, "conflicting_process_pids": conflicts, "future_surface_pristine": future},
        "first_network_model_search_or_fetch_effect_started": False,
        "credential_values_read_persisted_hashed_or_emitted": False,
        "findings": findings,
        "authorization": dict(START_AUTH) if valid else {**START_AUTH, "single_fresh_exact220_forward": False},
    }
    value["execution_start_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    protocol = _protocol()
    if (
        copied.get("role") != "v24798_exact220_execution_start"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("status") != "authorized_not_started"
        or copied.get("findings") != []
        or copied.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or copied.get("preactivation_audit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or copied.get("dependency_manifest_sha256") != protocol["dependency_manifest_sha256"]
        or copied.get("selected") != 220 or copied.get("executor_concurrency") != 20
        or copied.get("model_slot_cap") != 8 or copied.get("tavily_key_slot_cap") != 12
        or copied.get("protected_watchers") != protocol["execution"]["protected_watchers"]
        or copied.get("first_network_model_search_or_fetch_effect_started") is not False
        or copied.get("credential_values_read_persisted_hashed_or_emitted") is not False
        or copied.get("authorization") != START_AUTH
        or not _sealed(copied, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.47.98 execution start drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
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
        value = validate_start(build_start())
        path = contract.EXECUTION_START
    publish_new(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"], "authorization": value["authorization"]}, sort_keys=True))


if __name__ == "__main__":
    main()
