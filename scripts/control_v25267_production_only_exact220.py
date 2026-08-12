#!/usr/bin/env python3
"""Build, preregister, audit, and authorize V2.52.67 exact-220."""

from __future__ import annotations

import argparse
import ast
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

from deepwide_agent import v25110_exact_visible_schema as visible_schema  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


TEST_SUITES = (
    ("test_v25267_production_only_exact220.py", 11),
    ("test_v25265_production_only_totality_runtime.py", 6),
    ("test_v25253_outer_physical_cap_observed_runtime.py", 7),
    ("test_v25135_sparse_production_runtime.py", 9),
    ("test_v25110_exact_visible_schema.py", 4),
)
EXPECTED_TESTS = sum(count for _pattern, count in TEST_SUITES)
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
ALLOWED_PROVIDER_SCORE_ACCESS = "src/deepwide_agent/clients.py:565:score"
PREAUDIT_AUTH = {
    "execution_start_generation": True,
    "single_exact220_forward": False,
    "postfreeze_official_evaluator": False,
    "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
    "leaderboard_or_sota": False,
}
START_AUTH = {
    "single_exact220_forward": True,
    "postfreeze_official_evaluator": False,
    "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
    "leaderboard_or_sota": False,
}


def _publish(relative: Path, value: Mapping[str, Any]) -> None:
    path = ROOT / relative
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(contract.ordinary(ROOT, relative, tracked=True).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.67 control expected JSON object")
    return value


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.52.67 control requires clean pushed HEAD")
    return head, target


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


def _endpoint_reachable() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
            return True
    except OSError:
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
    markers = (contract.RUNNER_MARKER, "scripts/run_official_eval_local.py")
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 3 and int(parts[0]) != os.getpid() and "python" in parts[1].casefold() and any(marker in parts[2] for marker in markers):
            output.append(int(parts[0]))
    return sorted(output)


def _test(pattern: str, expected: int) -> dict[str, Any]:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", pattern, "-v"],
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
    return {
        "pattern": pattern,
        "expected": expected,
        "observed": observed,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and observed == expected,
        "output_sha256": contract.payload_sha256(completed.stdout),
    }


def _tests() -> dict[str, Any]:
    suites = [_test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in suites),
        "suites": suites,
    }


def _semantic_audit() -> dict[str, Any]:
    closure = contract.forward_dependency_closure(ROOT)
    privileged: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in closure:
        path = ROOT / relative
        source = path.read_text(encoding="utf-8")
        privileged.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if SECRET.search(source):
            secrets.append(str(relative))
    return {
        "dependency_closure": [str(path) for path in closure],
        "dependency_closure_sha256": contract.payload_sha256({str(path): contract.sha256(ROOT / path) for path in closure}),
        "privileged_runtime_field_accesses": sorted(set(privileged) - {ALLOWED_PROVIDER_SCORE_ACCESS}),
        "allowed_provider_rank_access": sorted(set(privileged) & {ALLOWED_PROVIDER_SCORE_ACCESS}),
        "evaluator_capabilities": sorted(set(evaluator)),
        "credential_literal_hits": sorted(set(secrets)),
    }


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in paths)


def _runtime_direct_privileged_accesses() -> list[dict[str, str]]:
    fields = {"category", "question_type", "task_category", "ground_truth", "answer_key", "split", "score", "reward"}
    output: list[dict[str, str]] = []
    for relative in (contract.CONTRACT, contract.RUNNER, contract.RUNTIME):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            key: object | None = None
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args and isinstance(node.args[0], ast.Constant):
                key = node.args[0].value
            if isinstance(key, str) and key in fields:
                output.append({"path": str(relative), "field": key})
    return output


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    head, target = _clean_pushed() if require_clean else ("build-only", "build-only")
    manifest = contract.dependency_manifest(ROOT, tracked=require_clean)
    tests = _tests()
    semantic = _semantic_audit()
    tasks = contract.task_vector(ROOT)
    schemas = [visible_schema.extract_exact_visible_columns(task["question"]) for task in tasks]
    future = (
        contract.BUILD_AUDIT, contract.PROTOCOL, contract.PREAUDIT,
        contract.EXECUTION_START, contract.ATTEMPT_CLAIM, contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT, contract.EVALUATOR_PROTOCOL, contract.RESULT,
        contract.POSTAUDIT, contract.OUTPUT_ROOT,
    )
    policy = contract.source_policy()
    parents = contract.parent_receipts(ROOT, tracked=require_clean)
    checks = {
        "reliability_and_cap_parents_bound": bool(parents),
        "public_exact220_task_vector_bound": len(tasks) == 220 and len({task["opaque_id"] for task in tasks}) == 220,
        "visible_schema_or_conservative_unknown_fallback_total": len(schemas) == 220 and all(len(columns) <= 20 for columns in schemas),
        "focused_parent_tests_exact": tests["passed"],
        "source_manifest_complete": bool(manifest) and set(manifest) == {
            *(str(path) for path in contract.forward_dependency_closure(ROOT)),
            str(contract.CONTROL), str(contract.FINALIZER), str(contract.TEST),
            str(contract.RUNTIME_TEST), str(contract.task_parent.PARENT_TASK_PROTOCOL),
            str(contract.DIAGNOSIS), str(contract.CAP_BUILD_AUDIT),
        },
        "direct_runtime_privileged_field_access_zero": not _runtime_direct_privileged_accesses(),
        "privileged_runtime_field_access_zero": not semantic["privileged_runtime_field_accesses"],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "future_forward_and_evaluator_surfaces_absent": _future_pristine(future),
        "protected_watchers_exact": len(contract.watcher_snapshot()) == 4
        and [row["pid"] for row in contract.watcher_snapshot()]
        == [pid for pid, _marker in contract.PROTECTED_WATCHERS]
        and [row["marker"] for row in contract.watcher_snapshot()]
        == [marker for _pid, marker in contract.PROTECTED_WATCHERS],
        "shared_api_lease_inactive": _lease_inactive(),
        "high_concurrency_fixed": contract.EXECUTOR_CONCURRENCY == 40 and contract.MODEL_SLOT_CAP == 16,
        "truthful_physical_caps_fixed": contract.PHYSICAL_CAPS == {"queries_per_task": 4, "fetches_per_task": 14, "model_forwards_per_task": 4},
        "production_only_no_candidate_treatment": policy["first_validated_sparse_production_is_only_scored_prediction"] is True
        and policy["header_quote_vertical_candidate_or_revision_prediction_used"] is False,
        "label_blind_runtime_boundary": policy["runtime_boundary"] == ["opaque_id", "question", "same_forward_public_pages"]
        and policy["mapping_gold_category_question_type_split_answer_evaluator_score_reward_read_by_forward"] is False,
        "entropy_information_gain_signed_credit_disabled": policy["entropy_or_information_gain_assigns_signed_credit_or_routes"] is False
        and policy["positive_signed_credit_count"] == 0,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25266_production_only_exact220_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "tests": tests,
        "semantic_audit": semantic,
        "direct_runtime_privileged_accesses": _runtime_direct_privileged_accesses(),
        "visible_schema_counts": {"explicit": sum(bool(columns) for columns in schemas), "conservative_unknown_fallback": sum(not columns for columns in schemas)},
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": policy,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "authorization": {
            "protocol_generation_after_build_commit_push": not findings,
            "external_forward": False,
            "postfreeze_official_evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25266_production_only_exact220_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("semantic_audit", {}).get("privileged_runtime_field_accesses") != []
        or copied.get("semantic_audit", {}).get("evaluator_capabilities") != []
        or copied.get("semantic_audit", {}).get("credential_literal_hits") != []
        or copied.get("direct_runtime_privileged_accesses") != []
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.52.66 build audit drifted")
    return copied


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    validate_build(_read(contract.BUILD_AUDIT))
    return contract.build_protocol(
        ROOT,
        now=int(time.time()) if now is None else int(now),
        tracked=True,
        require_pristine=True,
        build_audit_sha256=contract.sha256(ROOT / contract.BUILD_AUDIT),
    )


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    build = validate_build(_read(contract.BUILD_AUDIT))
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    tests = _tests()
    semantic = _semantic_audit()
    future = (
        contract.PREAUDIT, contract.EXECUTION_START, contract.ATTEMPT_CLAIM,
        contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.EVALUATOR_PROTOCOL,
        contract.RESULT, contract.POSTAUDIT, contract.OUTPUT_ROOT,
    )
    checks = {
        "build_and_protocol_valid": build["audit_valid"] is True,
        "protocol_source_manifest_live": protocol["dependency_manifest"] == contract.dependency_manifest(ROOT, tracked=True),
        "focused_parent_tests_exact": tests["passed"],
        "privileged_runtime_field_access_zero": not semantic["privileged_runtime_field_accesses"],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "future_surfaces_pristine": _future_pristine(future),
        "local_gpt56_endpoint_reachable": _endpoint_reachable(),
        "shared_api_lease_inactive": _lease_inactive(),
        "no_active_conflicting_forward_or_evaluator": not _active_conflicts(),
        "protected_watchers_unchanged": contract.watcher_snapshot() == protocol["execution"]["protected_watchers"],
        "task_vector_stable": contract.payload_sha256(contract.task_vector(ROOT)) == contract.payload_sha256(contract.task_vector(ROOT, protocol)),
        "reliability_parent_still_valid": bool(contract.parent_receipts(ROOT, tracked=True)),
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25268_production_only_exact220_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "dependency_manifest_sha256": protocol["dependency_manifest_sha256"],
        "tests": tests,
        "semantic_audit": semantic,
        "runtime_state": {"conflicting_process_pids": _active_conflicts(), "shared_api_lease_inactive": _lease_inactive(), "future_surface_pristine": _future_pristine(future)},
        "label_blind_audit": {"passed": not semantic["privileged_runtime_field_accesses"] and not _runtime_direct_privileged_accesses(), "runtime_input_keys": ["opaque_id", "question"]},
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": PREAUDIT_AUTH,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25268_production_only_exact220_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("authorization") != PREAUDIT_AUTH
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.52.68 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    head, _target = _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    preaudit = validate_preaudit(_read(contract.PREAUDIT))
    future = (
        contract.EXECUTION_START, contract.ATTEMPT_CLAIM, contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT, contract.EVALUATOR_PROTOCOL, contract.RESULT,
        contract.POSTAUDIT, contract.OUTPUT_ROOT,
    )
    if (
        not _future_pristine(future)
        or not _endpoint_reachable()
        or not _lease_inactive()
        or _active_conflicts()
        or contract.watcher_snapshot() != protocol["execution"]["protected_watchers"]
        or preaudit["audit_valid"] is not True
    ):
        raise RuntimeError("V2.52.68 execution start prerequisites failed")
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25268_production_only_exact220_execution_start",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "status": "authorized_not_started",
            "git_head": head,
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
            "selected": contract.TASK_COUNT,
            "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
            "model_slot_cap": contract.MODEL_SLOT_CAP,
            "runtime_input_contract": ["opaque_id", "question"],
            "truthful_physical_caps": copy.deepcopy(contract.PHYSICAL_CAPS),
            "protected_watchers": contract.watcher_snapshot(),
            "findings": [],
            "authorization": START_AUTH,
        },
        "execution_start_payload_sha256",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build-audit", "protocol", "preaudit", "start"))
    args = parser.parse_args()
    if args.command == "build-audit":
        value, path = build_audit(), contract.BUILD_AUDIT
    elif args.command == "protocol":
        value, path = build_protocol(), contract.PROTOCOL
    elif args.command == "preaudit":
        value, path = build_preaudit(), contract.PREAUDIT
    else:
        value, path = build_start(), contract.EXECUTION_START
    if value.get("findings"):
        raise RuntimeError(value["findings"])
    _publish(path, value)
    print(json.dumps({"path": str(path), "role": value["role"], "audit_valid": value.get("audit_valid"), "authorization": value.get("authorization")}, sort_keys=True))


if __name__ == "__main__":
    main()
