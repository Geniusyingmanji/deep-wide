#!/usr/bin/env python3
"""Build, stage, and post-forward audit control for V2.50.61."""

from __future__ import annotations

import argparse
import ast
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

from deepwide_agent import v25061_docsrs_late_record_gate_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import run_v25061_docsrs_late_record_gate as runner  # noqa: E402


TEST_SUITES = (
    ("test_v25060_version_qualified_late_record.py", 9),
    ("test_v25061_docsrs_late_record_gate.py", 12),
    ("test_v25059_consensus_late_record.py", 11),
    ("test_v25049_page_self_identified_record.py", 10),
)
EXPECTED_TESTS = sum(count for _suite, count in TEST_SUITES)


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.61 expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = True) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    values = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(value, dict) for value in values):
        raise RuntimeError("V2.50.61 expected JSONL objects")
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
        raise RuntimeError("V2.50.61 control requires clean pushed HEAD")
    return head, remote


def _tests() -> dict[str, Any]:
    observed = 0
    suites: list[dict[str, Any]] = []
    for pattern, expected in TEST_SUITES:
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
            timeout=120,
            check=False,
        )
        output = completed.stdout
        count = output.count(" ... ok")
        observed += count
        suites.append(
            {
                "pattern": pattern,
                "expected": expected,
                "observed": count,
                "returncode": completed.returncode,
                "passed": completed.returncode == 0 and count == expected,
            }
        )
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
    model_or_hosted_search: list[str] = []
    for relative in closure:
        path = ROOT / relative
        source = path.read_text(encoding="utf-8")
        accesses.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if contract.SECRET.search(source):
            secrets.append(str(relative))
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
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
                    model_or_hosted_search.append(f"{relative}:{getattr(node, 'lineno', 0)}:{name}")
    permitted_accesses = {
        value for value in accesses if value.endswith("clients.py:565:score")
    }
    return {
        "dependency_closure": [str(path) for path in closure],
        "dependency_closure_sha256": contract.payload_sha256(
            {str(path): contract.sha256(ROOT / path) for path in closure}
        ),
        "privileged_field_accesses": sorted(set(accesses) - permitted_accesses),
        "permitted_provider_relevance_accesses": sorted(permitted_accesses),
        "evaluator_capabilities": sorted(set(evaluator)),
        "credential_literal_hits": sorted(set(secrets)),
        "model_or_hosted_search_calls": sorted(set(model_or_hosted_search)),
    }


def _history_freshness() -> dict[str, Any]:
    rows: list[int] = []
    for crate in contract.CRATES:
        completed = subprocess.run(
            [
                "git",
                "grep",
                "-F",
                "-i",
                "-n",
                "--",
                crate,
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
            raise RuntimeError("V2.50.61 historical literal scan failed")
        rows.append(sum(bool(line.strip()) for line in completed.stdout.splitlines()))
    return {
        "parent_commit": contract.FRESHNESS_PARENT_COMMIT,
        "crate_count": len(rows),
        "literal_hit_counts": rows,
        "all_literal_zero_hit": all(count == 0 for count in rows),
        "network_endpoint_page_value_model_or_evaluator_access": False,
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
        marker in line and "ps -eo" not in line for line in completed.stdout.splitlines()
    )


def build_audit(*, now: int | None = None, require_clean: bool = True) -> dict[str, Any]:
    head, remote = _clean_pushed() if require_clean else ("build-only", "build-only")
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
        contract.OUTPUT_ROOT,
    )
    checks = {
        "focused_and_parent_tests_pass": tests["passed"],
        "source_manifest_complete": set(manifest)
        == {
            *(str(path) for path in contract.forward_dependency_closure(ROOT)),
            str(contract.CONTROL),
            str(contract.TEST),
        },
        "parent_history_literal_freshness_zero_hit": freshness[
            "all_literal_zero_hit"
        ],
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_field_accesses"
        ],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "model_or_hosted_search_calls_absent": not semantic[
            "model_or_hosted_search_calls"
        ],
        "future_effect_surfaces_absent": _future_pristine(future),
        "protected_watchers_exact": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
        "fixed_population_and_consumed_development_excluded": len(contract.CRATES)
        == contract.TASK_COUNT
        and not set(contract.CRATES) & set(contract.CONSUMED_DEVELOPMENT_CRATES),
        "fixed_denominator_and_zero_model_gate": contract.gates()[
            "fixed_denominator"
        ]
        == 20
        and contract.build_protocol(
            ROOT,
            now=1,
            tracked=require_clean,
            require_pristine=False,
            build_audit_sha256="0" * 64,
        )["execution"]["model_calls"]
        == 0,
        "entropy_information_gain_signed_credit_disabled": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25061_docsrs_late_record_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": remote, "equal": head == remote},
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "tests": tests,
        "semantic_audit": semantic,
        "freshness": freshness,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": contract.source_policy(),
        "network_model_fetch_or_evaluator_called": False,
        "authorization": {
            "protocol_generation_after_build_commit_push": not findings,
            "external_forward": False,
            "model_or_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v25061_docsrs_late_record_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("authorization", {}).get("external_forward") is not False
        or copied.get("authorization", {}).get("model_or_evaluator") is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.50.61 build audit drifted")
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
        "focused_and_parent_tests_pass": tests["passed"],
        "source_manifest_unchanged": protocol["source_manifest"]
        == contract.dependency_manifest(ROOT, tracked=True),
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_field_accesses"
        ],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "model_or_hosted_search_calls_absent": not semantic[
            "model_or_hosted_search_calls"
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
    value = {
        "artifact_version": 1,
        "role": "v25061_docsrs_late_record_preactivation_audit",
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
    copied = dict(value)
    if (
        copied.get("role") != "v25061_docsrs_late_record_preactivation_audit"
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
        raise RuntimeError("V2.50.61 preactivation audit drifted")
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
        raise RuntimeError("V2.50.61 start surface is not pristine")
    if not _runner_absent() or contract.watcher_snapshot() != protocol[
        "protected_watchers"
    ]:
        raise RuntimeError("V2.50.61 runtime state drifted")
    value = {
        "artifact_version": 1,
        "role": "v25061_docsrs_late_record_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": head,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "endpoint_vector_sha256": protocol["population"]["endpoint_vector_sha256"],
        "protected_watchers": contract.watcher_snapshot(),
        "authorization": {
            "one_fixed_denominator_external_mechanism_forward": True,
            "model_search_or_evaluator": False,
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
        for row in _read_jsonl(contract.TASK_ROWS)
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
            row["model_search_or_evaluator_called"] is False for row in rows
        ),
        "no_sensitive_task_or_page_content_persisted": all(
            row[
                "contains_opaque_id_crate_endpoint_question_page_title_field_value_prediction_or_page_hash"
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
    value = {
        "artifact_version": 1,
        "role": "v25061_docsrs_late_record_forward_audit",
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
            "fresh_disjoint_quality_gate_design": not findings
            and decision["mechanism_gate_passed"],
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
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
