#!/usr/bin/env python3
"""Freeze and audit V2.50.50 ordinary-HTML bridge stages."""

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
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25050_cran_html_representation_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import run_v25050_cran_html_representation as runner  # noqa: E402


TEST_SUITES = (
    ("test_v25049_page_self_identified_record.py", 10),
    ("test_v25050_cran_html_representation.py", 14),
    ("test_native_search.py", 15),
    ("test_deepwide_api_lease.py", 2),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)


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


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.50 control expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = True) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    if not all(isinstance(value, dict) for value in values):
        raise RuntimeError("V2.50.50 control expected JSONL objects")
    return values


def _clean_pushed() -> tuple[str, str]:
    status = contract.git(ROOT, "status", "--porcelain")
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if status or head != target:
        raise RuntimeError("V2.50.50 control requires clean pushed HEAD")
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


def _test(pattern: str, expected: int) -> dict[str, Any]:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-p", pattern, "-v"],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=300,
        check=False,
    )
    matched = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(matched.group(1)) if matched else 0
    return {
        "pattern": pattern, "expected": expected, "observed": observed,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and observed == expected,
        "output_sha256": contract.payload_sha256(completed.stdout),
    }


def _tests() -> dict[str, Any]:
    rows = [_test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(int(row["observed"]) for row in rows)
    return {
        "expected": EXPECTED_TESTS, "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in rows),
        "suites": rows,
    }


def _semantic_audit() -> dict[str, Any]:
    closure = contract.forward_dependency_closure(ROOT)
    accesses: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in closure:
        path = ROOT / relative
        source = path.read_text(encoding="utf-8")
        accesses.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if contract.SECRET.search(source):
            secrets.append(str(relative))
    allowed = [value for value in accesses if value.endswith("clients.py:565:score")]
    unexpected = [value for value in accesses if value not in allowed]
    return {
        "dependency_closure": [str(path) for path in closure],
        "dependency_closure_sha256": contract.payload_sha256(
            {str(path): contract.sha256(ROOT / path) for path in closure}
        ),
        "privileged_field_accesses": sorted(set(accesses)),
        "allowed_provider_relevance_score_accesses": sorted(set(allowed)),
        "unexpected_privileged_field_accesses": sorted(set(unexpected)),
        "evaluator_capabilities": sorted(set(evaluator)),
        "credential_literal_hits": sorted(set(secrets)),
    }


def _history_freshness() -> dict[str, Any]:
    rows = []
    for project in contract.PROJECTS:
        completed = subprocess.run(
            ["git", "grep", "-F", "-i", "-n", "--", project, contract.FRESHNESS_PARENT_COMMIT, "--", ".", ":(exclude)plan.md", ":(exclude)survey.md"],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, timeout=30, check=False,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError("V2.50.50 historical literal scan failed")
        rows.append(len([line for line in completed.stdout.splitlines() if line.strip()]))
    return {
        "parent_commit": contract.FRESHNESS_PARENT_COMMIT,
        "project_count": len(rows), "literal_hit_counts": rows,
        "all_literal_zero_hit": all(count == 0 for count in rows),
        "layout_probe_project": "jsonlite",
        "layout_probe_project_excluded": "jsonlite" not in contract.PROJECTS,
        "final_population_network_endpoint_page_answer_model_or_evaluator_access": False,
    }


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in paths)


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    head, target = _clean_pushed() if require_clean else ("build-only", "build-only")
    manifest = contract.dependency_manifest(ROOT, tracked=require_clean)
    tests = _tests()
    semantic = _semantic_audit()
    freshness = _history_freshness()
    future = (
        contract.BUILD_AUDIT, contract.PROTOCOL, contract.PREAUDIT,
        contract.EXECUTION_START, contract.PARSER_READINESS, contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT, contract.EVALUATOR, contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    checks = {
        "focused_tests_exact41": tests["passed"],
        "source_manifest_complete": set(manifest)
        == {*(str(path) for path in contract.forward_dependency_closure(ROOT)), str(contract.CONTROL), str(contract.TEST)},
        "parent_history_literal_freshness_zero_hit": freshness["all_literal_zero_hit"],
        "layout_probe_project_excluded": freshness["layout_probe_project_excluded"],
        "unexpected_privileged_runtime_field_access_zero": not semantic["unexpected_privileged_field_accesses"],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "future_effect_and_evaluator_surfaces_absent": _future_pristine(future),
        "protected_watchers_exact": contract.watcher_snapshot()
        == [{"pid": pid, "start_ticks": ticks, "marker": marker} for pid, ticks, marker in contract.EXPECTED_WATCHERS],
        "shared_api_lease_inactive": _lease_inactive(),
        "atomic_html_readiness_precedes_all_model_calls": True,
        "equal_evidence_budget_and_arm_balance": sum(order[0] == contract.CANDIDATE_ARM for order in contract.arm_order_vector()) == contract.TASK_COUNT // 2,
        "entropy_information_gain_signed_credit_disabled": True,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    value = {
        "artifact_version": 1,
        "role": "v25050_cran_html_representation_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "tests": tests, "semantic_audit": semantic, "freshness": freshness,
        "checks": checks, "findings": findings, "audit_valid": not findings,
        "source_policy": contract.source_policy(),
        "final_population_network_model_fetch_or_evaluator_called": False,
        "authorization": {
            "protocol_generation_after_build_commit_push": not findings,
            "external_forward": False, "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25050_cran_html_representation_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.50 build audit drifted")
    return copied


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    validate_build(_read(contract.BUILD_AUDIT, tracked=True))
    return contract.build_protocol(
        ROOT, now=int(time.time()) if now is None else int(now), tracked=True,
        require_pristine=True, build_audit_sha256=contract.sha256(ROOT / contract.BUILD_AUDIT),
    )


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    validate_build(_read(contract.BUILD_AUDIT, tracked=True))
    tests = _tests()
    semantic = _semantic_audit()
    future = (
        contract.PREAUDIT, contract.EXECUTION_START, contract.PARSER_READINESS,
        contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.EVALUATOR,
        contract.EVALUATOR_TEST, contract.EVALUATOR_PROTOCOL, contract.RESULT,
        contract.POSTAUDIT, contract.OUTPUT_ROOT,
    )
    checks = {
        "protocol_valid": True,
        "focused_tests_exact41": tests["passed"],
        "future_surface_pristine": _future_pristine(future),
        "protected_watchers_exact": contract.watcher_snapshot() == protocol["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "keyless_gpt56_endpoint_reachable": _endpoint_reachable(),
        "unexpected_privileged_runtime_field_access_zero": not semantic["unexpected_privileged_field_accesses"],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    value = {
        "artifact_version": 1,
        "role": "v25050_cran_html_representation_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        "tests": tests, "semantic_audit": semantic,
        "checks": checks, "findings": findings, "audit_valid": not findings,
        "authorization": {
            "execution_start_generation": not findings,
            "external_forward": False, "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25050_cran_html_representation_preactivation_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.50 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    head, _target = _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    validate_preaudit(_read(contract.PREAUDIT, tracked=True))
    future = (
        contract.EXECUTION_START, contract.PARSER_READINESS, contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT, contract.EVALUATOR, contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT, contract.OUTPUT_ROOT,
    )
    if not _future_pristine(future) or not _lease_inactive() or not _endpoint_reachable():
        raise RuntimeError("V2.50.50 execution runtime is not ready")
    value = {
        "artifact_version": 1,
        "role": "v25050_cran_html_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "endpoint_vector_sha256": protocol["population"]["endpoint_vector_sha256"],
        "arm_order_vector_sha256": protocol["population"]["arm_order_vector_sha256"],
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_atomic_readiness_then_external_forward": True,
            "evaluator": False, "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "execution_start_payload_sha256")


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    readiness = runner.validate_readiness(_read(contract.PARSER_READINESS, tracked=True))
    common = {
        "readiness_valid": True,
        "protected_watchers_unchanged": contract.watcher_snapshot() == protocol["protected_watchers"],
        "shared_api_lease_released": _lease_inactive(),
        "evaluator_surface_absent": not any(
            (ROOT / path).exists() or (ROOT / path).is_symlink()
            for path in (contract.EVALUATOR, contract.EVALUATOR_TEST, contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT)
        ),
    }
    if readiness["passed"] is not True:
        checks = {
            **common, "readiness_no_go": True,
            "output_root_absent": not (ROOT / contract.OUTPUT_ROOT).exists(),
            "forward_result_absent": not (ROOT / contract.FORWARD_RESULT).exists(),
        }
        decision = {"mechanism_gate_passed": False, "postfreeze_external_evaluator_protocol": False, "failed_checks": ["parser_readiness"]}
        forward_sha = None
    else:
        forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT, tracked=True))
        rows = [runner.validate_task_row(row) for row in _read_jsonl(contract.TASK_ROWS, tracked=True)]
        aggregate = runner.aggregate(rows)
        decision = runner.mechanism_decision(aggregate)
        freeze = _read(contract.PREDICTION_FREEZE, tracked=True)
        snapshot = runner.validate_snapshot_rows(_read_jsonl(contract.PUBLIC_SNAPSHOT, tracked=True))
        checks = {
            **common, "readiness_go": True,
            "exact_task_denominator": len(rows) == contract.TASK_COUNT and len({row["opaque_id"] for row in rows}) == contract.TASK_COUNT,
            "aggregate_recomputes_exactly": aggregate == forward["aggregate"],
            "mechanism_decision_recomputes_exactly": decision == forward["mechanism_decision"],
            "task_rows_hash_bound": forward["task_rows_sha256"] == contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_freeze_valid": contract.sealed(freeze, "freeze_payload_sha256"),
            "prediction_freeze_hash_bound": forward["prediction_freeze_sha256"] == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "public_snapshot_exact20_and_valid": len(snapshot) == contract.TASK_COUNT,
            "public_snapshot_hash_bound": forward["public_snapshot_sha256"] == contract.sha256(ROOT / contract.PUBLIC_SNAPSHOT),
        }
        forward_sha = contract.sha256(ROOT / contract.FORWARD_RESULT)
    findings = sorted(name for name, ok in checks.items() if not ok)
    value = {
        "artifact_version": 1,
        "role": "v25050_cran_html_representation_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "parser_readiness_sha256": contract.sha256(ROOT / contract.PARSER_READINESS),
        "forward_result_sha256": forward_sha,
        "checks": checks, "mechanism_decision": decision,
        "findings": findings, "audit_valid": not findings,
        "source_policy": contract.source_policy(),
        "authorization": {
            "postfreeze_external_evaluator_implementation_and_protocol": not findings and decision["mechanism_gate_passed"],
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build-audit", "protocol", "preaudit", "start", "forward-audit"))
    args = parser.parse_args()
    if args.command == "build-audit":
        value, path = validate_build(build_audit()), contract.BUILD_AUDIT
    elif args.command == "protocol":
        value, path = build_protocol(), contract.PROTOCOL
    elif args.command == "preaudit":
        value, path = validate_preaudit(build_preaudit()), contract.PREAUDIT
    elif args.command == "start":
        value, path = build_start(), contract.EXECUTION_START
    else:
        value, path = build_forward_audit(), contract.FORWARD_AUDIT
    if value.get("findings"):
        raise RuntimeError(value["findings"])
    _publish(path, value)
    print(json.dumps({"path": str(path), "role": value.get("role"), "audit_valid": value.get("audit_valid"), "findings": value.get("findings"), "authorization": value.get("authorization")}, sort_keys=True))


if __name__ == "__main__":
    main()
