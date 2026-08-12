#!/usr/bin/env python3
"""Build, authorize, and audit the V2.51.91 same-response quality gate."""

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

from deepwide_agent import v25110_exact_visible_schema as parser_impl  # noqa: E402
from deepwide_agent import v25191_export_tolerant_quality_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import control_v25183_quote_aware_external as parent_control  # noqa: E402
from scripts import run_v25191_export_tolerant_quality as runner  # noqa: E402


TEST_SUITES = (
    ("test_v25191_export_tolerant_quality.py", 7),
    ("test_v25188_export_failure_tolerant_same_response_runtime.py", 13),
    ("test_audit_v25190_export_tolerant_quality_population_selection.py", 3),
    *parent_control.TEST_SUITES,
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
ALLOWED_PROVIDER_SCORE_ACCESS = parent_control.ALLOWED_PROVIDER_SCORE_ACCESS


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
        raise RuntimeError("V2.51.91 control expected JSON object")
    return value


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != target:
        raise RuntimeError("V2.51.91 control requires clean pushed HEAD")
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
        ["ps", "-eo", "pid=,comm=,args="], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=False,
    )
    markers = (str(contract.RUNNER), str(contract.EVALUATOR), "scripts/run_" + "official_eval_local.py")
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3 and int(parts[0]) != os.getpid() and "python" in parts[1].casefold() and any(marker in parts[2] for marker in markers):
            output.append(int(parts[0]))
    return sorted(output)


def _test(pattern: str, expected: int) -> dict[str, Any]:
    completed = subprocess.run(
        [str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m", "unittest",
         "discover", "-s", "tests", "-p", pattern, "-v"],
        cwd=ROOT,
        env={
            "HOME": os.environ.get("HOME", str(Path.home())),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=300, check=False,
    )
    match = re.search(r"Ran (\d+) tests?", completed.stdout)
    observed = int(match.group(1)) if match else 0
    return {
        "pattern": pattern, "expected": expected, "observed": observed,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and observed == expected,
        "output_sha256": contract.payload_sha256(completed.stdout),
    }


def _tests() -> dict[str, Any]:
    suites = [_test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(row["observed"] for row in suites)
    return {
        "expected": EXPECTED_TESTS, "observed": observed,
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
        "privileged_runtime_field_accesses": sorted(set(privileged) - {ALLOWED_PROVIDER_SCORE_ACCESS}),
        "allowed_provider_rank_access": sorted(set(privileged) & {ALLOWED_PROVIDER_SCORE_ACCESS}),
        "evaluator_capabilities": sorted(set(evaluator)),
        "credential_literal_hits": sorted(set(secrets)),
    }


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(not (ROOT / path).exists() and not (ROOT / path).is_symlink() for path in paths)


def _recursive_keys(value: object) -> set[str]:
    output: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            output.add(str(key))
            output.update(_recursive_keys(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            output.update(_recursive_keys(child))
    return output


def _selection_valid(*, tracked: bool) -> bool:
    value = contract.validate_selection(ROOT, tracked=tracked)
    return bool(
        value["audit_valid"] is True and value["findings"] == []
        and value["identity_history_zero_hit_count"] == contract.TASK_COUNT
        and value["ordered_identity_vector_sha256"] == contract.IDENTITY_SELECTION_SHA256
        and value["preselection_enriched_for_license_literal_pipe"] is True
        and value["preselection_is_unconditional_natural_population"] is False
    )


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    head, target = _clean_pushed() if require_clean else ("build-only", "build-only")
    manifest = contract.dependency_manifest(ROOT, tracked=require_clean)
    tests = _tests()
    semantic = _semantic_audit()
    future = (
        contract.BUILD_AUDIT, contract.PROTOCOL, contract.PREAUDIT,
        contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
        contract.EVALUATOR, contract.EVALUATOR_TEST, contract.EVALUATOR_PROTOCOL,
        contract.RESULT, contract.POSTAUDIT, contract.OUTPUT_ROOT,
    )
    tasks = contract.task_vector()
    expected_manifest = {
        *(str(path) for path in contract.forward_dependency_closure(ROOT)),
        str(contract.CONTROL), str(contract.TEST), str(contract.SELECTION_SOURCE),
        str(contract.SELECTION_TEST), str(contract.SELECTION_AUDIT),
        str(contract.DIAGNOSIS),
    }
    checks = {
        "fresh_mechanism_enriched_selection_bound": _selection_valid(tracked=require_clean),
        "focused_and_complete_parent_tests_exact": tests["passed"],
        "source_manifest_complete": set(manifest) == expected_manifest,
        "privileged_runtime_field_access_zero": not semantic["privileged_runtime_field_accesses"],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "future_forward_evaluator_and_quality_surfaces_absent": _future_pristine(future),
        "protected_watchers_exact": contract.watcher_snapshot() == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": _lease_inactive(),
        "natural_visible_tasks_exact_four_columns": len(tasks) == 20 and all(
            parser_impl.extract_exact_visible_columns(task["question"]) == list(contract.COLUMNS)
            and r"\|" not in task["question"] and "https://" not in task["question"]
            for task in tasks
        ),
        "fixed_concurrency_and_caps": contract.EXECUTOR_CONCURRENCY == 20
        and contract.MODEL_SLOT_CAP == 8
        and contract.LIMITS == parent_control.contract.LIMITS,
        "same_response_mechanism_gate_frozen": contract.mechanism_gate()["minimum_same_raw_counterfactual_active_tasks"] == 10
        and contract.mechanism_gate()["minimum_prediction_changed_tasks"] == 10,
        "safe_export_failure_gate_frozen": contract.mechanism_gate()[
            "maximum_unsafe_public_export_failure_tasks"
        ]
        == 0
        and contract.mechanism_gate()[
            "safe_public_export_failure_must_equal_safe_production_fallback"
        ]
        is True,
        "strict_quality_gate_frozen": contract.quality_gate()["minimum_candidate_exact_gain"] == 10
        and contract.quality_gate()["minimum_candidate_exact_successes"] == 10,
        "mechanism_enriched_scope_disclosed": contract.source_policy()["population_is_history_disjoint_but_mechanism_enriched_not_unconditional"] is True,
        "entropy_information_gain_signed_credit_disabled": contract.source_policy()["entropy_or_information_gain_assigns_signed_credit"] is False,
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25191_export_tolerant_quality_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "tests": tests,
        "semantic_audit": semantic,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": contract.source_policy(),
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "authorization": {
            "protocol_generation_after_build_commit_push": not findings,
            "external_forward": False,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25191_export_tolerant_quality_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("findings") != [] or copied.get("audit_valid") is not True
        or not copied.get("checks") or not all(copied["checks"].values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("semantic_audit", {}).get("privileged_runtime_field_accesses") != []
        or copied.get("semantic_audit", {}).get("evaluator_capabilities") != []
        or copied.get("semantic_audit", {}).get("credential_literal_hits") != []
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("authorization") != {
            "protocol_generation_after_build_commit_push": True,
            "external_forward": False, "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.51.91 build audit drifted")
    return copied


def build_protocol(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    validate_build(_read(contract.BUILD_AUDIT))
    return contract.build_protocol(
        ROOT, now=int(time.time()) if now is None else int(now), tracked=True,
        require_pristine=True, build_audit_sha256=contract.sha256(ROOT / contract.BUILD_AUDIT),
    )


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    build = validate_build(_read(contract.BUILD_AUDIT))
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    tests = _tests()
    semantic = _semantic_audit()
    future = (
        contract.PREAUDIT, contract.EXECUTION_START, contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT, contract.EVALUATOR, contract.EVALUATOR_TEST,
        contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    checks = {
        "build_and_protocol_valid": build["audit_valid"] is True,
        "protocol_source_manifest_live": protocol["source_manifest"] == contract.dependency_manifest(ROOT, tracked=True),
        "focused_and_complete_parent_tests_exact": tests["passed"],
        "privileged_runtime_field_access_zero": not semantic["privileged_runtime_field_accesses"],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "selection_still_valid": _selection_valid(tracked=True),
        "future_surfaces_pristine": _future_pristine(future),
        "local_gpt56_endpoint_reachable": _endpoint_reachable(),
        "shared_api_lease_inactive": _lease_inactive(),
        "no_active_conflicting_forward_or_evaluator": not _active_conflicts(),
        "protected_watchers_unchanged": contract.watcher_snapshot() == protocol["protected_watchers"],
        "evaluator_implementation_absent_before_prediction_freeze": not (ROOT / contract.EVALUATOR).exists() and not (ROOT / contract.EVALUATOR_TEST).exists(),
        "natural_task_vector_stable": contract.payload_sha256(contract.task_vector()) == protocol["population"]["task_vector_sha256"],
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25191_export_tolerant_quality_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "tests": tests, "semantic_audit": semantic,
        "checks": checks, "findings": findings, "audit_valid": not findings,
        "protected_watchers": contract.watcher_snapshot(),
        "source_policy": contract.source_policy(),
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "authorization": {
            "one_external_forward_after_separate_clean_pushed_start": not findings,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25191_export_tolerant_quality_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("findings") != [] or copied.get("audit_valid") is not True
        or not copied.get("checks") or not all(copied["checks"].values())
        or copied.get("tests", {}).get("expected") != EXPECTED_TESTS
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called") is not False
        or copied.get("authorization") != {
            "one_external_forward_after_separate_clean_pushed_start": True,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_rerun": False,
        }
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.51.91 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    preaudit = validate_preaudit(_read(contract.PREAUDIT))
    future = (
        contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
        contract.EVALUATOR, contract.EVALUATOR_TEST, contract.EVALUATOR_PROTOCOL,
        contract.RESULT, contract.POSTAUDIT, contract.OUTPUT_ROOT,
    )
    if (
        not _future_pristine(future) or not _endpoint_reachable()
        or not _lease_inactive() or _active_conflicts()
        or contract.watcher_snapshot() != protocol["protected_watchers"]
        or preaudit["audit_valid"] is not True
    ):
        raise RuntimeError("V2.51.91 execution start prerequisites failed")
    value = {
        "artifact_version": 1,
        "role": "v25191_export_tolerant_quality_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_external_forward": True, "external_evaluator": False,
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
    forbidden = {"question", "query", "url", "host", "title", "page", "target", "authority", "column", "category", "question_type", "gold", "score", "reward"}
    checks = {
        "protocol_forward_and_rows_validate": True,
        "exact_task_denominator": len(rows) == contract.TASK_COUNT and [row["opaque_id"] for row in rows] == [task["opaque_id"] for task in contract.task_vector()],
        "aggregate_recomputes_exactly": aggregate == forward["aggregate"],
        "mechanism_decision_recomputes_exactly": decision == forward["mechanism_decision"],
        "task_rows_contain_no_forbidden_content_keys": not _recursive_keys(rows).intersection(forbidden),
        "actual_effect_counts_complete": all(runner.accounting._validate_actual_effect_snapshot(row["actual_effect_snapshot"]) == row["actual_effect_snapshot"] for row in rows),
        "same_response_receipts_validate": all(not row["runtime_completed"] or contract.runtime.validate_receipt(row["content_free_receipt"]) == row["content_free_receipt"] for row in rows),
        "task_rows_hash_bound": forward["task_rows_sha256"] == contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_valid": contract.sealed(freeze, "freeze_payload_sha256"),
        "prediction_freeze_hash_bound": forward["prediction_freeze_sha256"] == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "prediction_freeze_binds_task_rows": freeze.get("task_rows_sha256") == contract.sha256(ROOT / contract.TASK_ROWS),
        "gold_and_evaluator_surfaces_absent": _future_pristine((contract.POSTFREEZE_GOLD, contract.EVALUATOR, contract.EVALUATOR_TEST, contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT)),
        "protected_watchers_unchanged": contract.watcher_snapshot() == protocol["protected_watchers"],
        "shared_api_lease_released": _lease_inactive(),
        "forward_process_absent": not _active_conflicts(),
        "no_deepwidebench_or_sota_authority": forward["authorization"]["deepwidebench_dev64_exact220_or_sota"] is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25191_export_tolerant_quality_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "aggregate": aggregate, "mechanism_decision": decision,
        "checks": checks, "findings": findings, "audit_valid": not findings,
        "authorization": {
            "postfreeze_evaluator_implementation_and_protocol": not findings and decision["same_response_mechanism_gate_passed"],
            "external_evaluator_now": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_skip_population_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    command = argparse.ArgumentParser()
    command.add_argument("command", choices=("build-audit", "protocol", "preaudit", "start", "forward-audit"))
    args = command.parse_args()
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
    print(json.dumps({"path": str(path), "role": value["role"], "audit_valid": value.get("audit_valid"), "authorization": value.get("authorization")}, sort_keys=True))


if __name__ == "__main__":
    main()
