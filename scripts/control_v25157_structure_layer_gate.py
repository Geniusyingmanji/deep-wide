#!/usr/bin/env python3
"""Build, stage, and post-forward audit control for V2.51.57."""

from __future__ import annotations

import argparse
import ast
import copy
import json
import os
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

from deepwide_agent import v25157_structure_layer_gate_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import run_v25157_structure_layer_gate as runner  # noqa: E402


TEST_SUITES = (
    ("test_v25157_structure_layer_gate.py", 10),
    ("test_audit_v25157_structure_population_selection.py", 3),
    ("test_v25155_projection_structure_observer.py", 8),
    ("test_native_search.py", 17),
    ("test_v24984_robust_late_page_projection.py", 4),
    ("test_v24980_late_page_bound_projection.py", 8),
)
EXPECTED_TESTS = sum(count for _suite, count in TEST_SUITES)


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.57 expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = True) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    values = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError("V2.51.57 expected JSONL objects")
    return values


def _publish(path: Path, value: Mapping[str, Any]) -> None:
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


def _clean_pushed() -> tuple[str, str]:
    head = contract.git(ROOT, "rev-parse", "HEAD")
    remote = contract.git(ROOT, "rev-parse", "target/main")
    if contract.git(ROOT, "status", "--porcelain") or head != remote:
        raise RuntimeError("V2.51.57 control requires clean pushed HEAD")
    return head, remote


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
            "HOME": str(Path.home()),
            "USER": "azureuser",
            "LOGNAME": "azureuser",
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
    observed = completed.stdout.count(" ... ok")
    return {
        "pattern": pattern,
        "expected": expected,
        "observed": observed,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and observed == expected,
    }


def _tests() -> dict[str, Any]:
    suites = [_test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(value["observed"] for value in suites)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "suites": suites,
        "passed": observed == EXPECTED_TESTS
        and all(value["passed"] for value in suites),
    }


def _semantic_audit() -> dict[str, Any]:
    closure = contract.forward_dependency_closure(ROOT)
    accesses: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    dormant_model_or_hosted_search: list[str] = []
    module_level_model_or_hosted_search: list[str] = []
    for relative in closure:
        path = ROOT / relative
        source = path.read_text(encoding="utf-8")
        accesses.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if contract.SECRET.search(source):
            secrets.append(str(relative))
        tree = ast.parse(source, filename=str(path))

        class EffectCallVisitor(ast.NodeVisitor):
            def __init__(self) -> None:
                self.function_depth = 0

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self.function_depth += 1
                self.generic_visit(node)
                self.function_depth -= 1

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self.function_depth += 1
                self.generic_visit(node)
                self.function_depth -= 1

            def visit_Call(self, node: ast.Call) -> None:
                function = node.func
                name = ""
                if isinstance(function, ast.Name):
                    name = function.id
                elif isinstance(function, ast.Attribute):
                    name = function.attr
                if name in {
                    "complete",
                    "search_many",
                    "create",
                    "responses_create",
                    "run_official_eval",
                }:
                    marker = f"{relative}:{getattr(node, 'lineno', 0)}:{name}"
                    dormant_model_or_hosted_search.append(marker)
                    if self.function_depth == 0:
                        module_level_model_or_hosted_search.append(marker)
                self.generic_visit(node)

        EffectCallVisitor().visit(tree)
    direct_model_or_hosted_search: list[str] = []
    for relative in contract.FORWARD_SOURCES:
        tree = ast.parse(
            (ROOT / relative).read_text(encoding="utf-8"), filename=str(relative)
        )
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            name = (
                function.id
                if isinstance(function, ast.Name)
                else function.attr
                if isinstance(function, ast.Attribute)
                else ""
            )
            if name in {
                "complete",
                "search_many",
                "create",
                "responses_create",
                "run_official_eval",
            }:
                direct_model_or_hosted_search.append(
                    f"{relative}:{getattr(node, 'lineno', 0)}:{name}"
                )
    permitted = {
        value for value in accesses if value.endswith("clients.py:565:score")
    }
    return {
        "dependency_closure": [str(path) for path in closure],
        "dependency_closure_sha256": contract.payload_sha256(
            {str(path): contract.sha256(ROOT / path) for path in closure}
        ),
        "privileged_field_accesses": sorted(set(accesses) - permitted),
        "permitted_provider_relevance_accesses": sorted(permitted),
        "evaluator_capabilities": sorted(set(evaluator)),
        "credential_literal_hits": sorted(set(secrets)),
        "direct_forward_source_model_or_hosted_search_calls": sorted(
            set(direct_model_or_hosted_search)
        ),
        "module_level_model_or_hosted_search_calls": sorted(
            set(module_level_model_or_hosted_search)
        ),
        "dormant_dependency_model_or_hosted_search_call_definitions": sorted(
            set(dormant_model_or_hosted_search)
        ),
    }


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _runner_absent() -> bool:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=10,
        check=True,
    )
    marker = str(contract.RUNNER)
    return not any(
        marker in line and "ps -eo" not in line
        for line in completed.stdout.splitlines()
    )


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    head, remote = _clean_pushed() if require_clean else ("build-only", "build-only")
    manifest = contract.dependency_manifest(ROOT, tracked=require_clean)
    tests = _tests()
    semantic = _semantic_audit()
    selection = contract.validate_population_selection(ROOT, tracked=require_clean)
    future = (
        contract.BUILD_AUDIT,
        contract.PROTOCOL,
        contract.PREAUDIT,
        contract.EXECUTION_START,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    )
    checks = {
        "focused_and_parent_tests_exact50": tests["passed"],
        "source_manifest_complete": set(manifest)
        == {
            *(str(path) for path in contract.forward_dependency_closure(ROOT)),
            str(contract.CONTROL),
            str(contract.TEST),
            str(contract.POPULATION_SOURCE),
            str(contract.POPULATION_TEST),
            str(contract.POPULATION_AUDIT),
            str(contract.PARENT_BUILD_AUDIT),
        },
        "parent_observer_build_audit_exact_hash": contract.sha256(
            ROOT / contract.PARENT_BUILD_AUDIT
        )
        == contract.PARENT_BUILD_AUDIT_SHA256,
        "population_selection_bound_and_history_zero": selection[
            "identity_history_zero_hit_count"
        ]
        == contract.TASK_COUNT,
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_field_accesses"
        ],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "direct_forward_source_model_or_hosted_search_calls_absent": not semantic[
            "direct_forward_source_model_or_hosted_search_calls"
        ],
        "module_level_model_or_hosted_search_calls_absent": not semantic[
            "module_level_model_or_hosted_search_calls"
        ],
        "future_effect_surfaces_absent": _future_pristine(future),
        "protected_watchers_exact": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
        "fixed_population_denominator_and_zero_model_gate": len(
            contract.PACKAGES
        )
        == contract.TASK_COUNT
        and contract.gates()["fixed_denominator"] == 20
        and contract.build_protocol(
            ROOT,
            now=1,
            tracked=require_clean,
            require_pristine=False,
            build_audit_sha256="0" * 64,
        )["execution"]["model_calls"]
        == 0,
        "structure_only_no_quality_or_credit_authority": contract.gates()[
            "quality_or_evaluator_authorization"
        ]
        is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25157_structure_layer_gate_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": remote, "equal": head == remote},
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "tests": tests,
        "semantic_audit": semantic,
        "population_selection_sha256": contract.sha256(
            ROOT / contract.POPULATION_AUDIT
        ),
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": contract.source_policy(),
        "network_model_fetch_search_or_evaluator_called": False,
        "authorization": {
            "protocol_generation_after_build_commit_push": not findings,
            "external_forward": False,
            "model_or_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25157_structure_layer_gate_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("authorization", {}).get("external_forward") is not False
        or copied.get("authorization", {}).get("model_or_evaluator") is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.51.57 build audit drifted")
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
    head, remote = _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    tests = _tests()
    semantic = _semantic_audit()
    checks = {
        "protocol_valid": True,
        "git_head_equals_target_main": head == remote,
        "focused_and_parent_tests_exact50": tests["passed"],
        "source_manifest_unchanged": protocol["source_manifest"]
        == contract.dependency_manifest(ROOT, tracked=True),
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_field_accesses"
        ],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "direct_forward_source_model_or_hosted_search_calls_absent": not semantic[
            "direct_forward_source_model_or_hosted_search_calls"
        ],
        "module_level_model_or_hosted_search_calls_absent": not semantic[
            "module_level_model_or_hosted_search_calls"
        ],
        "execution_surfaces_pristine": _future_pristine(
            (
                contract.EXECUTION_START,
                contract.FORWARD_RESULT,
                contract.FORWARD_AUDIT,
                contract.OUTPUT_ROOT,
            )
        ),
        "runner_absent": _runner_absent(),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25157_structure_layer_gate_preactivation_audit",
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
            "model_or_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v25157_structure_layer_gate_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("authorization", {}).get("execution_start_generation")
        is not True
        or copied.get("authorization", {}).get("external_forward") is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.51.57 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    head, remote = _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    validate_preaudit(_read(contract.PREAUDIT))
    if head != remote or not _future_pristine(
        (
            contract.EXECUTION_START,
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.OUTPUT_ROOT,
        )
    ):
        raise RuntimeError("V2.51.57 start surface is not pristine")
    if not _runner_absent() or contract.watcher_snapshot() != protocol[
        "protected_watchers"
    ]:
        raise RuntimeError("V2.51.57 runtime state drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25157_structure_layer_gate_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "endpoint_vector_sha256": protocol["population"]["endpoint_vector_sha256"],
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_fixed_denominator_external_structure_forward": True,
            "model_hosted_search_or_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "execution_start_payload_sha256")


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    rows = [
        runner.validate_task_row(row)
        for row in _read_jsonl(contract.TASK_ROWS, tracked=False)
    ]
    aggregate = runner.aggregate(rows)
    decision = runner.mechanism_decision(aggregate)
    checks = {
        "fixed_content_free_task_rows": len(rows) == contract.TASK_COUNT,
        "aggregate_recomputes_exactly": aggregate == forward["aggregate"],
        "mechanism_decision_recomputes_exactly": decision
        == forward["mechanism_decision"],
        "task_rows_hash_bound": forward["task_rows_sha256"]
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "runner_absent": _runner_absent(),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "model_search_evaluator_and_benchmark_absent": all(
            row["model_hosted_search_or_evaluator_called"] is False
            for row in rows
        ),
        "no_sensitive_task_or_page_content_persisted": all(
            row[
                "contains_opaque_id_package_endpoint_question_page_title_label_value_text_prediction_or_content_hash"
            ]
            is False
            for row in rows
        ),
        "same_population_model_or_evaluator_forbidden": decision[
            "model_or_evaluator_on_this_population_authorized"
        ]
        is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25157_structure_layer_gate_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "aggregate": aggregate,
        "mechanism_decision": decision,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "next_layer_repair_design": not findings
            and decision["structure_localization_gate_passed"],
            "model_or_evaluator_on_this_population": False,
            "deepwidebench_dev64_exact220_or_sota": False,
            "retry_resume_population_replacement_or_selective_revaluation": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("build-audit", "protocol", "preaudit", "start", "forward-audit"),
    )
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
    _publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value["role"],
                "audit_valid": value.get("audit_valid"),
                "findings": value.get("findings"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
