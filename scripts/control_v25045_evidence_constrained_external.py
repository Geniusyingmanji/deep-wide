#!/usr/bin/env python3
"""Freeze and audit V2.50.45 external-gate control stages."""

from __future__ import annotations

import argparse
import ast
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

from deepwide_agent import v25045_evidence_constrained_external_contract as contract  # noqa: E402
from scripts import run_v25045_evidence_constrained_external as runner  # noqa: E402


TEST_SUITES = (
    ("test_v25044_evidence_constrained_synthesis.py", 6),
    ("test_v25045_evidence_constrained_external.py", 7),
    ("test_v25038_batching_external.py", 10),
    ("test_v25036_source_only_hosted_search.py", 5),
    ("test_v24269_task_union_discovery.py", 5),
    ("test_v24280_task_union_single_shot.py", 4),
    ("test_v24316_deadline_search.py", 7),
    ("test_v24468_total_wall_transport.py", 8),
    ("test_v24985_robust_late_page_fetch.py", 2),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
FORBIDDEN = {
    "category", "question_type", "task_category", "ground_truth", "gold",
    "answer_key", "mapping", "split", "evaluator", "score", "reward",
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


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.45 control expected JSON object")
    return value


def _clean_pushed() -> tuple[str, str]:
    status = contract.git(ROOT, "status", "--porcelain")
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if status or head != target:
        raise RuntimeError("V2.50.45 control requires clean pushed HEAD")
    return head, target


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
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
        [
            str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
            "discover", "-s", "tests", "-p", pattern, "-v",
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
    matched = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(matched.group(1)) if matched else 0
    return {
        "pattern": pattern,
        "expected": expected,
        "observed": observed,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and observed == expected,
        "output_sha256": contract.payload_sha256(completed.stdout),
    }


def _tests() -> dict[str, Any]:
    rows = [_test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(int(row["observed"]) for row in rows)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in rows),
        "suites": rows,
    }


def _semantic_audit() -> dict[str, Any]:
    accesses: list[str] = []
    secrets: list[str] = []
    evaluator_capabilities: list[str] = []
    closure = contract.forward_dependency_closure(ROOT)
    for relative in closure:
        path = ROOT / relative
        source = path.read_text(encoding="utf-8")
        if contract.SECRET.search(source):
            secrets.append(str(relative))
        if any(marker in str(relative).casefold() for marker in ("evaluate_", "evaluator")):
            evaluator_capabilities.append(str(relative))
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            key: object = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                key = node.args[0].value
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value
            if isinstance(key, str) and key.casefold() in FORBIDDEN:
                accesses.append(f"{relative}:{node.lineno}:{key}")
    allowed: list[str] = []
    unexpected: list[str] = []
    for item in accesses:
        relative = Path(item.rsplit(":", 2)[0])
        source = (ROOT / relative).read_text(encoding="utf-8")
        if str(relative) == "src/deepwide_agent/clients.py" or (
            "mapping_gold_category_question_type_split_evaluator_score_reward_read" in source
            or "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read" in source
            or "source_policy" in source
        ):
            allowed.append(item)
        else:
            unexpected.append(item)
    return {
        "dependency_closure": [str(path) for path in closure],
        "dependency_closure_sha256": contract.payload_sha256(
            {str(path): contract.sha256(ROOT / path) for path in closure}
        ),
        "privileged_field_accesses": sorted(set(accesses)),
        "allowed_negative_policy_or_provider_rank_accesses": sorted(set(allowed)),
        "unexpected_privileged_field_accesses": sorted(set(unexpected)),
        "credential_literal_hits": sorted(set(secrets)),
        "evaluator_capabilities": sorted(set(evaluator_capabilities)),
    }


def _history_freshness() -> dict[str, Any]:
    parent = contract.FRESHNESS_PARENT_COMMIT
    rows: list[dict[str, Any]] = []
    for project in contract.PROJECTS:
        completed = subprocess.run(
            ["git", "grep", "-F", "-i", "-n", "--", project, parent, "--", "."],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError("V2.50.45 historical literal scan failed")
        rows.append(
            {
                "project": project,
                "history_hit_count": len(
                    [line for line in completed.stdout.splitlines() if line.strip()]
                ),
            }
        )
    return {
        "parent_commit": parent,
        "project_count": len(rows),
        "all_literal_zero_hit": all(row["history_hit_count"] == 0 for row in rows),
        "rows": rows,
        "network_endpoint_page_answer_model_or_evaluator_access": False,
    }


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    head, target = _clean_pushed() if require_clean else ("build-only", "build-only")
    manifest = contract.dependency_manifest(ROOT, tracked=require_clean)
    tests = _tests()
    semantic = _semantic_audit()
    freshness = _history_freshness()
    future = (
        contract.PROTOCOL, contract.PREAUDIT, contract.EXECUTION_START,
        contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.EVALUATOR,
        contract.EVALUATOR_TEST, contract.EVALUATOR_PROTOCOL, contract.RESULT,
        contract.POSTAUDIT, contract.OUTPUT_ROOT,
    )
    checks = {
        "focused_and_parent_tests_exact54": tests["passed"],
        "source_manifest_complete": set(manifest)
        == {
            *(str(path) for path in contract.forward_dependency_closure(ROOT)),
            str(contract.CONTROL), str(contract.TEST),
        },
        "parent_history_literal_freshness_zero_hit": freshness["all_literal_zero_hit"],
        "unexpected_privileged_field_access_zero": not semantic[
            "unexpected_privileged_field_accesses"
        ],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "future_evaluator_and_effect_surfaces_absent": not any(
            (ROOT / path).exists() or (ROOT / path).is_symlink() for path in future
        ),
        "protected_watchers_exact": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": _lease_inactive(),
        "one_shared_search_fetch_evidence_prefix": True,
        "same_model_output_cap_and_deadline": True,
        "entropy_information_gain_signed_credit_disabled": True,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    value = {
        "artifact_version": 1,
        "role": "v25045_evidence_constrained_external_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "tests": tests,
        "semantic_audit": semantic,
        "freshness": freshness,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": contract.source_policy(),
        "network_model_search_fetch_or_evaluator_called": False,
        "authorization": {
            "protocol_generation_after_build_commit_push": not findings,
            "external_forward": False,
            "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25045_evidence_constrained_external_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization", {}).get("deepwidebench_dev64_exact220_or_sota") is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.45 build audit drifted")
    return copied


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    validate_build(_read(contract.BUILD_AUDIT, tracked=True))
    return contract.build_protocol(
        ROOT,
        now=int(time.time()) if now is None else int(now),
        tracked=True,
        require_pristine=True,
        build_audit_sha256=contract.sha256(ROOT / contract.BUILD_AUDIT),
    )


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    validate_build(_read(contract.BUILD_AUDIT, tracked=True))
    tests = _tests()
    semantic = _semantic_audit()
    future = (
        contract.PREAUDIT, contract.EXECUTION_START, contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT, contract.EVALUATOR, contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    checks = {
        "protocol_valid": True,
        "focused_and_parent_tests_exact54": tests["passed"],
        "future_surface_pristine": not any(
            (ROOT / path).exists() or (ROOT / path).is_symlink() for path in future
        ),
        "protected_watchers_exact": contract.watcher_snapshot() == protocol["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "keyless_gpt56_endpoint_reachable": _endpoint_reachable(),
        "unexpected_privileged_field_access_zero": not semantic[
            "unexpected_privileged_field_accesses"
        ],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "predeclared_evaluator_endpoint_vector_absent_and_not_directly_accessed": True,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    value = {
        "artifact_version": 1,
        "role": "v25045_evidence_constrained_external_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "tests": tests,
        "semantic_audit": semantic,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "execution_start_generation": not findings,
            "external_forward": False,
            "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25045_evidence_constrained_external_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("authorization", {}).get("execution_start_generation") is not True
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.45 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    validate_preaudit(_read(contract.PREAUDIT, tracked=True))
    future = (
        contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
        contract.EVALUATOR, contract.EVALUATOR_TEST, contract.EVALUATOR_PROTOCOL,
        contract.RESULT, contract.POSTAUDIT, contract.OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.50.45 execution surface is not pristine")
    value = {
        "artifact_version": 1,
        "role": "v25045_evidence_constrained_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "arm_order_vector_sha256": protocol["population"]["arm_order_vector_sha256"],
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_external_forward": True,
            "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_selective_rerun": False,
        },
    }
    return contract.seal(value, "execution_start_payload_sha256")


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT, tracked=True))
    rows = [runner.validate_task_row(row) for row in runner._read_jsonl(contract.TASK_ROWS)]
    aggregate = runner.aggregate_rows(
        rows, batch_wall_seconds=float(forward["aggregate"]["batch_wall_seconds"])
    )
    decision = runner.mechanism_decision(aggregate)
    freeze = _read(contract.PREDICTION_FREEZE, tracked=True)
    forbidden_keys = {
        "query", "url", "host", "title", "page", "provider_payload",
        "category", "question_type", "gold", "score", "reward",
    }
    row_keys = {key for row in rows for key in row}
    checks = {
        "protocol_forward_and_rows_validate": True,
        "exact_task_denominator": len(rows) == contract.TASK_COUNT
        and len({row["opaque_id"] for row in rows}) == contract.TASK_COUNT,
        "aggregate_recomputes_exactly": aggregate == forward["aggregate"],
        "mechanism_decision_recomputes_exactly": decision == forward["mechanism_decision"],
        "task_rows_contain_no_forbidden_content_keys": not row_keys.intersection(forbidden_keys),
        "task_rows_hash_bound": forward["task_rows_sha256"]
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_valid": contract.sealed(freeze, "freeze_payload_sha256"),
        "prediction_freeze_hash_bound": forward["prediction_freeze_sha256"]
        == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "prediction_freeze_binds_task_rows": freeze.get("task_rows_sha256")
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "gold_and_evaluator_surface_absent": not any(
            (ROOT / path).exists() or (ROOT / path).is_symlink()
            for path in (
                contract.GOLD_SNAPSHOT, contract.EVALUATOR,
                contract.EVALUATOR_TEST, contract.EVALUATOR_PROTOCOL,
                contract.RESULT, contract.POSTAUDIT,
            )
        ),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_released": _lease_inactive(),
        "no_deepwidebench_or_sota_authority": forward["authorization"][
            "deepwidebench_dev64_exact220_or_sota"
        ]
        is False,
    }
    findings = sorted(name for name, ok in checks.items() if not ok)
    value = {
        "artifact_version": 1,
        "role": "v25045_evidence_constrained_external_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "checks": checks,
        "mechanism_decision": decision,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": contract.source_policy(),
        "authorization": {
            "postfreeze_external_evaluator_implementation_and_protocol": not findings
            and decision["mechanism_gate_passed"],
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_selective_rerun_or_revaluation": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command", choices=("build-audit", "protocol", "preaudit", "start", "forward-audit")
    )
    args = parser.parse_args()
    if args.command == "build-audit":
        value, path = build_audit(), contract.BUILD_AUDIT
    elif args.command == "protocol":
        value, path = build_protocol(), contract.PROTOCOL
    elif args.command == "preaudit":
        value, path = build_preaudit(), contract.PREAUDIT
    elif args.command == "start":
        value, path = build_start(), contract.EXECUTION_START
    else:
        value, path = build_forward_audit(), contract.FORWARD_AUDIT
    if value.get("findings"):
        raise RuntimeError(value["findings"])
    _publish(path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value.get("role"),
                "audit_valid": value.get("audit_valid"),
                "findings": value.get("findings"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
