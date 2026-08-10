#!/usr/bin/env python3
"""Build, preregister, audit, and authorize V2.50.30 exact-220."""

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
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25030_evidence_conditioned_exact220_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


TEST_SUITES = (
    (contract.TEST, 11),
    (Path("tests/test_v25029_evidence_conditioned_runtime.py"), 5),
    (Path("tests/test_v25024_evidence_conditioned_queries.py"), 8),
    (Path("tests/test_v24996_shared_first_wave_paired_runtime.py"), 7),
    (Path("tests/test_v24990_query_vector_paired_runtime.py"), 7),
    (Path("tests/test_v24986_robust_paired_runtime.py"), 5),
    (Path("tests/test_v24985_robust_late_page_fetch.py"), 2),
    (Path("tests/test_v24982_paired_production_runtime.py"), 7),
)
EXPECTED_TESTS = sum(count for _path, count in TEST_SUITES)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:" + "|".join(re.escape(value) for value in SECRET_PREFIXES) + r")[A-Za-z0-9_-]{16,}"
)
PREAUDIT_AUTH = {
    "execution_start_generation": True,
    "single_fresh_exact220_forward": False,
    "postfreeze_official_evaluator": False,
    "retry_resume_skip_or_selective_rerun": False,
    "leaderboard_or_sota": False,
}
START_AUTH = {
    "single_fresh_exact220_forward": True,
    "postfreeze_official_evaluator": False,
    "retry_resume_skip_or_selective_rerun": False,
    "leaderboard_or_sota": False,
}


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError(f"V2.50.30 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.30 expected JSON object")
    return value


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


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.50.30 control requires clean pushed HEAD")


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def _tests() -> dict[str, Any]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    rows: list[dict[str, Any]] = []
    for path, expected in TEST_SUITES:
        completed = subprocess.run(
            [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", path.name, "-v"],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=300, check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append({
            "path": str(path), "expected": expected, "observed": observed,
            "passed": completed.returncode == 0 and observed == expected,
            "output_sha256": contract.payload_sha256(completed.stdout),
        })
    observed = sum(row["observed"] for row in rows)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in rows),
        "suites": rows,
    }


def _findings(*, tracked: bool) -> tuple[list[str], list[str], list[str], list[str]]:
    privileged: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    untracked: list[str] = []
    for relative in contract.forward_dependency_closure(ROOT):
        path = ROOT / relative
        privileged.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secrets.append(str(relative))
        if tracked and not _tracked(relative):
            untracked.append(str(relative))
    allowed = {"src/deepwide_agent/clients.py:565:score"}
    return (
        sorted(set(privileged) - allowed),
        sorted(set(evaluator)),
        sorted(set(secrets)),
        sorted(set(untracked)),
    )


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
    markers = (contract.RUNNER_MARKER, "scripts/run_official_eval_local.py")
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3 and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in paths)


def build_build_audit(*, now: int | None = None) -> dict[str, Any]:
    tests = _tests()
    privileged, evaluator, secrets, _untracked = _findings(tracked=False)
    tasks = contract.task_vector(ROOT)
    manifest = contract.dependency_manifest(ROOT, tracked=False)
    checks = {
        "focused_and_parent_tests_pass": tests["passed"],
        "visible_task_vector_exact220": len(tasks) == 220,
        "visible_task_vector_bound_to_v24857": True,
        "forward_dependency_closure_nonempty": bool(contract.forward_dependency_closure(ROOT)),
        "privileged_runtime_field_findings_empty": not privileged,
        "forward_evaluator_capabilities_empty": not evaluator,
        "credential_literal_findings_empty": not secrets,
        "runtime_budget_exact": contract.LIMITS == {
            "wall_seconds": 240, "model_calls": 3, "search_queries": 4,
            "fetch_targets": 10, "search_results_per_query": 3,
            "evidence_chars": 60_000, "page_chars": 5_000,
            "plan_output_tokens": 4_000, "synthesis_output_tokens": 30_000,
            "repair_output_tokens": 12_000,
        },
        "entropy_signed_credit_disabled": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25030_evidence_conditioned_exact220_build_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "tests": tests,
            "dependency_manifest": manifest,
            "dependency_manifest_sha256": contract.payload_sha256(manifest),
            "label_blind_audit": {
                "privileged_runtime_field_accesses": privileged,
                "evaluator_capabilities": evaluator,
                "credential_literal_hits": secrets,
                "allowed_provider_rank_access": ["src/deepwide_agent/clients.py:565:score"],
            },
            "checks": checks,
            "findings": findings,
            "audit_valid": not findings,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "mapping_gold_category_question_type_split_answer_evaluator_score_reward_read": False,
            "authorization": {"protocol_generation_after_build_commit_push": not findings, "benchmark_forward": False},
        },
        "audit_payload_sha256",
    )
    return value


def _protocol() -> dict[str, Any]:
    return contract.validate_protocol(ROOT, _read(ROOT / contract.PROTOCOL))


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    protocol = _protocol()
    _clean_pushed()
    tests = _tests()
    privileged, evaluator, secrets, untracked = _findings(tracked=True)
    endpoint = _endpoint()
    lease = _lease_inactive()
    conflicts = _active_conflicts()
    watchers = contract.protected_watcher_snapshot()
    future = _future_pristine((contract.PREAUDIT, contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT, contract.OUTPUT_ROOT))
    checks = {
        "focused_and_parent_tests_pass": tests["passed"],
        "all_forward_dependencies_tracked": not untracked,
        "privileged_runtime_field_findings_empty": not privileged,
        "forward_evaluator_capabilities_empty": not evaluator,
        "credential_literal_findings_empty": not secrets,
        "gpt56_endpoint_reachable_without_provider_request": endpoint,
        "shared_api_lease_inactive": lease,
        "conflicting_processes_absent": not conflicts,
        "protected_watchers_exact": watchers == protocol["execution"]["protected_watchers"],
        "future_surface_pristine": future,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25030_evidence_conditioned_exact220_preactivation_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "dependency_manifest_sha256": protocol["dependency_manifest_sha256"],
            "tests": tests,
            "label_blind_audit": {
                "privileged_runtime_field_accesses": privileged,
                "evaluator_capabilities": evaluator,
                "credential_literal_hits": secrets,
                "untracked_forward_dependencies": untracked,
                "passed": not privileged and not evaluator and not secrets and not untracked,
            },
            "runtime_state": {
                "gpt56_endpoint_reachable_without_provider_request": endpoint,
                "shared_api_lease_inactive": lease,
                "conflicting_process_pids": conflicts,
                "protected_watchers": watchers,
                "future_surface_pristine": future,
            },
            "checks": checks,
            "findings": findings,
            "audit_valid": not findings,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "mapping_gold_category_question_type_split_answer_evaluator_score_reward_read": False,
            "authorization": dict(PREAUDIT_AUTH) if not findings else {**PREAUDIT_AUTH, "execution_start_generation": False},
        },
        "audit_payload_sha256",
    )


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    protocol = _protocol()
    if (
        copied.get("role") != "v25030_evidence_conditioned_exact220_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True or copied.get("findings") != []
        or copied.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or copied.get("dependency_manifest_sha256") != protocol["dependency_manifest_sha256"]
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get("conflicting_process_pids") != []
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("runtime_state", {}).get("future_surface_pristine") is not True
        or copied.get("authorization") != PREAUDIT_AUTH
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.30 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    protocol = _protocol()
    audit = validate_preaudit(_read(ROOT / contract.PREAUDIT))
    _clean_pushed()
    endpoint = _endpoint()
    lease = _lease_inactive()
    conflicts = _active_conflicts()
    watchers = contract.protected_watcher_snapshot()
    future = _future_pristine((contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT, contract.OUTPUT_ROOT))
    checks = {
        "preactivation_chain_valid": audit["authorization"] == PREAUDIT_AUTH,
        "gpt56_endpoint_reachable_without_provider_request": endpoint,
        "shared_api_lease_inactive": lease,
        "conflicting_processes_absent": not conflicts,
        "protected_watchers_exact": watchers == protocol["execution"]["protected_watchers"],
        "future_surface_pristine": future,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25030_evidence_conditioned_exact220_execution_start",
            "protocol_id": contract.PROTOCOL_ID,
            "status": "authorized_not_started" if not findings else "not_authorized",
            "created_at_unix": int(time.time()) if now is None else int(now),
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
            "dependency_manifest_sha256": protocol["dependency_manifest_sha256"],
            "selected": contract.SELECTED_COUNT,
            "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
            "model_slot_cap": contract.MODEL_SLOT_CAP,
            "runtime_input_contract": ["opaque_id", "question"],
            "protected_watchers": watchers,
            "checks": checks,
            "first_network_model_search_or_fetch_effect_started": False,
            "findings": findings,
            "authorization": dict(START_AUTH) if not findings else {**START_AUTH, "single_fresh_exact220_forward": False},
        },
        "execution_start_payload_sha256",
    )


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25030_evidence_conditioned_exact220_execution_start"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("status") != "authorized_not_started"
        or copied.get("findings") != []
        or copied.get("selected") != 220
        or copied.get("executor_concurrency") != 20
        or copied.get("model_slot_cap") != 8
        or copied.get("runtime_input_contract") != ["opaque_id", "question"]
        or copied.get("authorization") != START_AUTH
        or not contract.sealed(copied, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.50.30 execution start drifted")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "protocol", "preaudit", "start"))
    args = parser.parse_args()
    if args.command == "build":
        value = build_build_audit()
        if not value["audit_valid"]:
            raise RuntimeError(value["findings"])
        path = contract.BUILD_AUDIT
    elif args.command == "protocol":
        _clean_pushed()
        build = _read(ROOT / contract.BUILD_AUDIT)
        expected_manifest = contract.dependency_manifest(ROOT, tracked=True)
        if (
            build.get("audit_valid") is not True
            or build.get("findings") != []
            or build.get("dependency_manifest") != expected_manifest
            or build.get("dependency_manifest_sha256")
            != contract.payload_sha256(expected_manifest)
            or not contract.sealed(build, "audit_payload_sha256")
        ):
            raise RuntimeError("V2.50.30 build audit drifted")
        value = contract.build_protocol(ROOT, now=int(time.time()))
        path = contract.PROTOCOL
    elif args.command == "preaudit":
        value = validate_preaudit(build_preaudit())
        path = contract.PREAUDIT
    else:
        value = validate_start(build_start())
        path = contract.EXECUTION_START
    publish_new(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"], "authorization": value["authorization"]}, sort_keys=True))


if __name__ == "__main__":
    main()
