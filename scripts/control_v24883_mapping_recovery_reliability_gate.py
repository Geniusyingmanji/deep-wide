#!/usr/bin/env python3
"""Preregister, audit, and authorize the neutral V2.48.83 gate."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24883_mapping_recovery_reliability_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _read(path: Path) -> dict:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.83 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.83 expected object")
    return value


def _sealed(value: dict, field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _clean_pushed() -> None:
    if (
        contract.git(ROOT, "status", "--porcelain")
        or contract.git(ROOT, "rev-parse", "HEAD")
        != contract.git(ROOT, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.48.83 control requires clean pushed HEAD")


def _new_json(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


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
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = (
        contract.RUNNER_MARKER,
        contract.CHILD_MARKER,
        "scripts/run_official_eval_local.py",
        "scripts/run_v24878_keyless_coverage_exact220.py",
        "scripts/run_v24878_keyless_coverage_exact220_task.py",
    )
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _runtime_findings() -> tuple[list[str], list[str], list[str]]:
    fields: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in contract.RUNTIME_SOURCES:
        path = ROOT / relative
        source = path.read_text(encoding="utf-8")
        fields.extend(semantic_audit._accesses(path.resolve(), ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path.resolve(), ROOT))
        if SECRET.search(source):
            secrets.append(str(relative))
    return sorted(set(fields)), sorted(set(evaluator)), sorted(set(secrets))


def _run_tests() -> tuple[int, bool, list[dict]]:
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
    for path, expected in contract.TEST_SUITES:
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
                path.name,
                "-v",
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=300,
            check=False,
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
    return (
        total,
        all(row["passed"] for row in rows)
        and total == contract.EXPECTED_TESTS,
        rows,
    )


def build_protocol() -> dict:
    _clean_pushed()
    future = (
        contract.PROTOCOL,
        contract.PREAUDIT,
        contract.EXECUTION_START,
        contract.RESULT,
        contract.OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise FileExistsError("V2.48.83 future surface exists")
    manifest = contract.source_manifest(ROOT)
    value = {
        "artifact_version": 1,
        "role": "v24883_mapping_recovery_reliability_preregistration",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "git_head": contract.git(ROOT, "rev-parse", "HEAD"),
        "task_count": contract.TASK_COUNT,
        "task_vector_sha256": contract.payload_sha256(contract.task_vector()),
        "execution": {
            "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
            "model_slot_cap": contract.MODEL_SLOT_CAP,
            "task_wall_seconds": contract.TASK_WALL_SECONDS,
            "limits": dict(contract.LIMITS),
            "model": dict(contract.MODEL),
            "search": dict(contract.SEARCH),
            "output_root": str(contract.OUTPUT_ROOT),
            "single_fresh_no_retry_resume_or_selective_rerun": True,
        },
        "gate": {
            "minimum_valid_bundles": contract.MINIMUM_VALID_BUNDLES,
            "minimum_valid_bundle_rate": (
                contract.MINIMUM_VALID_BUNDLES / contract.TASK_COUNT
            ),
            "maximum_hard_timeouts": contract.MAXIMUM_HARD_TIMEOUTS,
            "maximum_subprocess_exceptions": 0,
        },
        "protected_watchers": contract.protected_watcher_snapshot(),
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "source_policy": {
            "neutral_nonbenchmark_tasks_only": True,
            "runtime_input_keys": ["opaque_id", "question"],
            "benchmark_task_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "historical_prediction_correctness_or_score_read": False,
            "private_task_query_url_page_prediction_answer_or_credential_persisted": False,
            "entropy_or_information_gain_used_for_admission_or_routing": False,
        },
        "authorization": {
            "preactivation_audit": True,
            "execution_start": False,
            "neutral_gate": False,
            "exact220": False,
            "evaluator": False,
        },
    }
    value["protocol_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_protocol(value: dict) -> dict:
    manifest = contract.source_manifest(ROOT)
    if (
        value.get("role")
        != "v24883_mapping_recovery_reliability_preregistration"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("task_count") != 20
        or value.get("task_vector_sha256")
        != contract.payload_sha256(contract.task_vector())
        or value.get("execution", {}).get("executor_concurrency") != 20
        or value.get("execution", {}).get("model_slot_cap") != 8
        or value.get("gate", {}).get("minimum_valid_bundles") != 19
        or value.get("source_manifest") != manifest
        or value.get("source_manifest_sha256")
        != contract.payload_sha256(manifest)
        or value.get("protected_watchers")
        != contract.protected_watcher_snapshot()
        or value.get("source_policy", {}).get(
            "benchmark_task_mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or value.get("authorization")
        != {
            "preactivation_audit": True,
            "execution_start": False,
            "neutral_gate": False,
            "exact220": False,
            "evaluator": False,
        }
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.48.83 protocol drifted")
    return value


def build_audit() -> dict:
    protocol = validate_protocol(_read(ROOT / contract.PROTOCOL))
    _clean_pushed()
    fields, evaluator, secrets = _runtime_findings()
    observed, passed, suites = _run_tests()
    endpoint = _endpoint()
    lease = _lease_inactive()
    conflicts = _active_conflicts()
    watchers = contract.protected_watcher_snapshot()
    future = all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in (
            contract.PREAUDIT,
            contract.EXECUTION_START,
            contract.RESULT,
            contract.OUTPUT_ROOT,
        )
    )
    findings = []
    if fields:
        findings.append("privileged_runtime_field_access")
    if evaluator:
        findings.append("evaluator_capability")
    if secrets:
        findings.append("credential_literal")
    if not passed:
        findings.append("focused_tests_failed")
    if not endpoint:
        findings.append("gpt56_endpoint_unreachable")
    if not lease:
        findings.append("shared_api_lease_active")
    if conflicts:
        findings.append("conflicting_process_active")
    if watchers != protocol["protected_watchers"]:
        findings.append("protected_watcher_drifted")
    if not future:
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24883_mapping_recovery_reliability_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "tests": {
            "expected": contract.EXPECTED_TESTS,
            "observed": observed,
            "passed": passed,
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
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "execution_start": not findings,
            "neutral_gate": False,
            "exact220": False,
            "evaluator": False,
        },
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
        "benchmark_task_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_audit(value: dict) -> dict:
    if (
        value.get("role")
        != "v24883_mapping_recovery_reliability_preactivation_audit"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("tests", {}).get("expected") != contract.EXPECTED_TESTS
        or value.get("tests", {}).get("observed") != contract.EXPECTED_TESTS
        or value.get("tests", {}).get("passed") is not True
        or value.get("label_blind_audit", {}).get("passed") is not True
        or value.get("runtime_state", {}).get("shared_api_lease_inactive")
        is not True
        or value.get("runtime_state", {}).get("conflicting_process_pids") != []
        or value.get("authorization", {}).get("execution_start") is not True
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.48.83 audit drifted")
    return value


def build_start() -> dict:
    protocol = validate_protocol(_read(ROOT / contract.PROTOCOL))
    audit = validate_audit(_read(ROOT / contract.PREAUDIT))
    _clean_pushed()
    checks = {
        "gpt56_endpoint_reachable_without_provider_request": _endpoint(),
        "shared_api_lease_inactive": _lease_inactive(),
        "conflicting_process_pids": _active_conflicts(),
        "protected_watchers_unchanged": (
            contract.protected_watcher_snapshot() == protocol["protected_watchers"]
        ),
        "future_surface_pristine": all(
            not (ROOT / path).exists() and not (ROOT / path).is_symlink()
            for path in (
                contract.EXECUTION_START,
                contract.RESULT,
                contract.OUTPUT_ROOT,
            )
        ),
    }
    valid = bool(
        checks["gpt56_endpoint_reachable_without_provider_request"]
        and checks["shared_api_lease_inactive"]
        and checks["conflicting_process_pids"] == []
        and checks["protected_watchers_unchanged"]
        and checks["future_surface_pristine"]
        and audit["audit_valid"]
    )
    value = {
        "artifact_version": 1,
        "role": "v24883_mapping_recovery_reliability_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "authorized_not_started" if valid else "not_authorized",
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_count": 20,
        "executor_concurrency": 20,
        "model_slot_cap": 8,
        "runtime_input_contract": ["opaque_id", "question"],
        "checks": checks,
        "first_network_model_search_or_fetch_effect_started": False,
        "authorization": {
            "single_fresh_neutral_gate": valid,
            "retry_resume_skip_or_selective_rerun": False,
            "exact220": False,
            "evaluator": False,
        },
    }
    value["execution_start_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_start(value: dict) -> dict:
    if (
        value.get("role")
        != "v24883_mapping_recovery_reliability_execution_start"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("status") != "authorized_not_started"
        or value.get("task_count") != 20
        or value.get("executor_concurrency") != 20
        or value.get("model_slot_cap") != 8
        or value.get("runtime_input_contract") != ["opaque_id", "question"]
        or value.get("authorization")
        != {
            "single_fresh_neutral_gate": True,
            "retry_resume_skip_or_selective_rerun": False,
            "exact220": False,
            "evaluator": False,
        }
        or not _sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.48.83 execution start drifted")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "audit", "start"))
    args = parser.parse_args()
    if args.command == "protocol":
        value = validate_protocol(build_protocol())
        path = contract.PROTOCOL
    elif args.command == "audit":
        value = validate_audit(build_audit())
        path = contract.PREAUDIT
    else:
        value = validate_start(build_start())
        path = contract.EXECUTION_START
    _new_json(ROOT / path, value)
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
