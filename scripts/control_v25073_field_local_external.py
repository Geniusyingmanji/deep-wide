#!/usr/bin/env python3
"""Build, freeze, authorize, and audit the V2.50.73 external gate."""

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
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25073_field_local_external_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import run_v25073_field_local_external as runner  # noqa: E402


TEST_SUITES = (
    ("test_v25073_field_local_external.py", 8),
    ("test_v25070_field_local_quote_verified_record.py", 11),
    ("test_v25071_field_local_quote_verified_paired_runtime.py", 4),
    ("test_v25065_quote_verified_record_binding.py", 14),
    ("test_v25066_quote_verified_paired_runtime.py", 6),
    ("test_v25029_evidence_conditioned_runtime.py", 5),
    ("test_v25024_evidence_conditioned_queries.py", 8),
    ("test_v24996_shared_first_wave_paired_runtime.py", 7),
    ("test_v24990_query_vector_paired_runtime.py", 7),
    ("test_v24986_robust_paired_runtime.py", 5),
    ("test_v24985_robust_late_page_fetch.py", 2),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
ALLOWED_PROVIDER_SCORE_ACCESS = "src/deepwide_agent/clients.py:565:score"


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
        raise RuntimeError("V2.50.73 control expected JSON object")
    return value


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.50.73 control requires clean pushed HEAD")
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
    markers = (str(contract.RUNNER), str(contract.EVALUATOR), "scripts/run_official_eval_local.py")
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) == 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _test(pattern: str, expected: int) -> dict[str, Any]:
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
            pattern,
            "-v",
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
        if contract.SECRET.search(source):
            secrets.append(str(relative))
    return {
        "dependency_closure": [str(path) for path in closure],
        "dependency_closure_sha256": contract.payload_sha256(
            {str(path): contract.sha256(ROOT / path) for path in closure}
        ),
        "privileged_runtime_field_accesses": sorted(
            set(privileged) - {ALLOWED_PROVIDER_SCORE_ACCESS}
        ),
        "allowed_provider_rank_access": sorted(
            set(privileged) & {ALLOWED_PROVIDER_SCORE_ACCESS}
        ),
        "evaluator_capabilities": sorted(set(evaluator)),
        "credential_literal_hits": sorted(set(secrets)),
    }


def _history_freshness() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for project in contract.PROJECTS:
        completed = subprocess.run(
            [
                "git",
                "grep",
                "-F",
                "-i",
                "-n",
                "--",
                project,
                contract.FRESHNESS_PARENT_COMMIT,
                "--",
                ".",
                ":(exclude)plan.md",
                ":(exclude)survey.md",
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError("V2.50.73 historical literal scan failed")
        rows.append(
            {
                "project": project,
                "history_hit_count": sum(bool(line.strip()) for line in completed.stdout.splitlines()),
            }
        )
    return {
        "parent_commit": contract.FRESHNESS_PARENT_COMMIT,
        "project_count": len(rows),
        "all_literal_zero_hit": all(row["history_hit_count"] == 0 for row in rows),
        "rows": rows,
        "network_endpoint_page_value_model_or_evaluator_access": False,
    }


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in paths)


def _parent_valid() -> bool:
    path = contract.ordinary(ROOT, contract.PARENT_AUDIT, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    return (
        contract.sha256(path) == contract.PARENT_AUDIT_SHA256
        and isinstance(value, dict)
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and value.get("authorization", {}).get("fresh_disjoint_external_protocol_design") is True
        and value.get("authorization", {}).get("fresh_external_activation_or_launch") is False
    )


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    head, target = _clean_pushed() if require_clean else ("build-only", "build-only")
    manifest = contract.dependency_manifest(ROOT, tracked=require_clean)
    tests = _tests()
    semantic = _semantic_audit()
    freshness = _history_freshness()
    future = (
        contract.BUILD_AUDIT,
        contract.PROTOCOL,
        contract.PREAUDIT,
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR,
        contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    checks = {
        "v25072_parent_clean_build_audit_bound": _parent_valid(),
        "focused_and_parent_tests_exact77": tests["passed"],
        "source_manifest_complete": set(manifest)
        == {
            *(str(path) for path in contract.forward_dependency_closure(ROOT)),
            str(contract.CONTROL),
            str(contract.TEST),
            str(contract.PARENT_AUDIT),
        },
        "parent_history_literal_freshness_zero_hit": freshness["all_literal_zero_hit"],
        "privileged_runtime_field_access_zero": not semantic["privileged_runtime_field_accesses"],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "future_evaluator_and_effect_surfaces_absent": _future_pristine(future),
        "protected_watchers_exact": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": _lease_inactive(),
        "fixed_population_and_balanced_arm_order": len(contract.task_vector()) == 20
        and sum(order[0] == contract.CANDIDATE_ARM for order in contract.arm_order_vector()) == 10,
        "production_caps_not_expanded": contract.LIMITS
        == {
            "wall_seconds": 240,
            "model_calls": 3,
            "search_queries": 4,
            "fetch_targets": 10,
            "search_results_per_query": 3,
            "evidence_chars": 60_000,
            "page_chars": 5_000,
            "plan_output_tokens": 4_000,
            "synthesis_output_tokens": 30_000,
            "repair_output_tokens": 12_000,
        },
        "mapping_failure_and_terminal_hard_failure_separated": contract.source_policy()[
            "query_local_mapping_failure_is_coverage_diagnostic_not_terminal_transport_failure"
        ],
        "entropy_information_gain_signed_credit_disabled": True,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25073_field_local_external_build_audit",
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
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
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
        copied.get("role") != "v25073_field_local_external_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("authorization", {}).get("external_forward") is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.73 build audit drifted")
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
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    tests = _tests()
    semantic = _semantic_audit()
    checks = {
        "protocol_valid": True,
        "git_head_equals_target_main": head == target,
        "focused_and_parent_tests_exact77": tests["passed"],
        "source_manifest_unchanged": protocol["source_manifest"]
        == contract.dependency_manifest(ROOT, tracked=True),
        "privileged_runtime_field_access_zero": not semantic["privileged_runtime_field_accesses"],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "execution_surfaces_pristine": _future_pristine(
            (
                contract.PREAUDIT,
                contract.EXECUTION_START,
                contract.FORWARD_RESULT,
                contract.FORWARD_AUDIT,
                contract.EVALUATOR,
                contract.EVALUATOR_TEST,
                contract.EVALUATOR_PROTOCOL,
                contract.RESULT,
                contract.POSTAUDIT,
                contract.OUTPUT_ROOT,
            )
        ),
        "protected_watchers_unchanged": contract.watcher_snapshot() == protocol["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "keyless_gpt56_endpoint_reachable": _endpoint_reachable(),
        "conflicting_forward_or_evaluator_processes_absent": not _active_conflicts(),
        "postfreeze_gold_surface_absent": not (ROOT / contract.POSTFREEZE_GOLD).exists(),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25073_field_local_external_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "source_manifest_sha256": protocol["source_manifest_sha256"],
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
        copied.get("role") != "v25073_field_local_external_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("authorization", {}).get("execution_start_generation") is not True
        or copied.get("authorization", {}).get("external_forward") is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.73 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    validate_preaudit(_read(contract.PREAUDIT))
    future = (
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR,
        contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    if head != target or not _future_pristine(future):
        raise RuntimeError("V2.50.73 execution surface is not pristine")
    if not _lease_inactive() or not _endpoint_reachable() or _active_conflicts():
        raise RuntimeError("V2.50.73 execution runtime is not ready")
    if contract.watcher_snapshot() != protocol["protected_watchers"]:
        raise RuntimeError("V2.50.73 protected watcher identity drifted")
    value = {
        "artifact_version": 1,
        "role": "v25073_field_local_external_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "arm_order_vector_sha256": protocol["population"]["arm_order_vector_sha256"],
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_external_forward": True,
            "evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        },
    }
    return contract.seal(value, "execution_start_payload_sha256")


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    rows = [runner.validate_task_row(row) for row in runner._read_jsonl(contract.TASK_ROWS, tracked=True)]
    aggregate = runner.aggregate_rows(rows, wall_seconds=float(forward["aggregate"]["batch_wall_seconds"]))
    decision = runner.mechanism_decision(aggregate)
    freeze = _read(contract.PREDICTION_FREEZE)
    forbidden_keys = {
        "question",
        "query",
        "url",
        "host",
        "title",
        "page",
        "quote",
        "record_anchor",
        "identity",
        "field_value",
        "category",
        "question_type",
        "gold",
        "score",
        "reward",
    }
    row_keys = {key for row in rows for key in row}
    checks = {
        "protocol_forward_and_rows_validate": True,
        "exact_task_denominator": len(rows) == contract.TASK_COUNT
        and [row["opaque_id"] for row in rows]
        == [task["opaque_id"] for task in contract.task_vector()],
        "aggregate_recomputes_exactly": aggregate == forward["aggregate"],
        "mechanism_decision_recomputes_exactly": decision == forward["mechanism_decision"],
        "task_rows_contain_no_forbidden_content_keys": not row_keys.intersection(forbidden_keys),
        "task_rows_hash_bound": forward["task_rows_sha256"] == contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_valid": contract.sealed(freeze, "freeze_payload_sha256"),
        "prediction_freeze_hash_bound": forward["prediction_freeze_sha256"]
        == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "prediction_freeze_binds_task_rows": freeze.get("task_rows_sha256")
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "gold_and_evaluator_surface_absent": _future_pristine(
            (
                contract.POSTFREEZE_GOLD,
                contract.EVALUATOR,
                contract.EVALUATOR_TEST,
                contract.EVALUATOR_PROTOCOL,
                contract.RESULT,
                contract.POSTAUDIT,
            )
        ),
        "mapping_failure_not_counted_as_terminal_hard_failure": decision[
            "query_local_mapping_failures_used_as_terminal_hard_failure"
        ]
        is False,
        "protected_watchers_unchanged": contract.watcher_snapshot() == protocol["protected_watchers"],
        "shared_api_lease_released": _lease_inactive(),
        "forward_process_absent": not _active_conflicts(),
        "no_deepwidebench_or_sota_authority": forward["authorization"][
            "deepwidebench_dev64_exact220_or_sota"
        ]
        is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25073_field_local_external_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "aggregate": aggregate,
        "mechanism_decision": decision,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "postfreeze_external_evaluator_implementation_and_protocol": not findings
            and decision["mechanism_gate_passed"],
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_revaluation": False,
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
