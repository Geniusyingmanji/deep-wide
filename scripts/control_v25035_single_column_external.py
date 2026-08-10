#!/usr/bin/env python3
"""Freeze and audit each V2.50.35 external-gate stage."""

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

from deepwide_agent import v25035_single_column_external_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import finalize_v25035_single_column_external as finalizer  # noqa: E402
from scripts import run_v25035_single_column_external as runner  # noqa: E402


TEST_SUITES = (
    ("test_v24259_deterministic_table_normalizer.py", 11),
    ("test_v24986_robust_paired_runtime.py", 5),
    ("test_v25029_evidence_conditioned_runtime.py", 5),
    ("test_v25032_single_column_table_normalizer.py", 8),
    ("test_v25033_single_column_evidence_conditioned_runtime.py", 6),
    ("test_v25035_single_column_external.py", 12),
)
EXPECTED_TESTS = sum(expected for _pattern, expected in TEST_SUITES)
SECRET_PREFIXES = (
    "gh" + "p_",
    "github_" + "pat_",
    "tvly-" + "dev-",
    "s" + "k-",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.35 control expected JSON object")
    return value


def _jsonl(relative: Path, *, tracked: bool = True) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.50.35 control expected JSONL objects")
    return rows


def _publish(relative: Path, value: Mapping[str, Any]) -> None:
    path = ROOT / relative
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> tuple[str, str]:
    status = contract.git(ROOT, "status", "--porcelain")
    head = contract.git(ROOT, "rev-parse", "HEAD")
    target = contract.git(ROOT, "rev-parse", "target/main")
    if status or head != target:
        raise RuntimeError("V2.50.35 control requires clean pushed HEAD")
    return head, target


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
    rows = [_test(pattern, expected) for pattern, expected in TEST_SUITES]
    observed = sum(int(row["observed"]) for row in rows)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in rows),
        "suites": rows,
    }


def _dependency_closure(entrypoints: tuple[Path, ...]) -> tuple[Path, ...]:
    pending = list(entrypoints)
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = contract.ordinary(ROOT, relative, tracked=True)
        observed.add(relative)
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            candidates: list[Path] = []
            if isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.startswith("deepwide_agent."):
                        candidates.append(
                            Path("src")
                            / Path(*item.name.split(".")).with_suffix(".py")
                        )
                    elif item.name.startswith("scripts."):
                        candidates.append(
                            Path(*item.name.split(".")).with_suffix(".py")
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level and relative.parts[:2] == (
                    "src",
                    "deepwide_agent",
                ):
                    if module:
                        candidates.append(
                            Path("src/deepwide_agent")
                            / Path(*module.split(".")).with_suffix(".py")
                        )
                    else:
                        candidates.extend(
                            Path("src/deepwide_agent") / f"{item.name}.py"
                            for item in node.names
                        )
                elif module == "deepwide_agent":
                    candidates.extend(
                        Path("src/deepwide_agent") / f"{item.name}.py"
                        for item in node.names
                    )
                elif module.startswith("deepwide_agent."):
                    candidates.append(
                        Path("src") / Path(*module.split(".")).with_suffix(".py")
                    )
                elif module == "scripts":
                    candidates.extend(
                        Path("scripts") / f"{item.name}.py"
                        for item in node.names
                    )
                elif module.startswith("scripts."):
                    candidates.append(
                        Path(*module.split(".")).with_suffix(".py")
                    )
            for candidate in candidates:
                absolute = ROOT / candidate
                if absolute.is_file() and not absolute.is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def _semantic(closure: tuple[Path, ...]) -> dict[str, list[str]]:
    privileged: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in closure:
        path = contract.ordinary(ROOT, relative, tracked=True)
        privileged.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if SECRET.search(path.read_text(encoding="utf-8")):
            secrets.append(str(relative))
    # Public provider relevance score; not benchmark/evaluator score.
    allowed = {"src/deepwide_agent/clients.py:565:score"}
    return {
        "privileged_runtime_field_accesses": sorted(set(privileged) - allowed),
        "evaluator_capabilities": sorted(set(evaluator)),
        "credential_literal_hits": sorted(set(secrets)),
        "allowed_provider_rank_access": sorted(allowed & set(privileged)),
    }


def _historical_literal_hits() -> dict[str, int]:
    parent = contract.POPULATION_SELECTION_PARENT_COMMIT
    if contract.git(ROOT, "rev-parse", parent) != parent:
        raise RuntimeError("V2.50.35 population-selection parent is absent")
    hits: dict[str, int] = {}
    for project in contract.PROJECTS:
        completed = subprocess.run(
            ["git", "grep", "-F", "-n", "--", project, parent, "--", "."],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=20,
            check=False,
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError("V2.50.35 historical literal scan failed")
        count = len([line for line in completed.stdout.splitlines() if line.strip()])
        if count:
            hits[project] = count
    return hits


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


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _build_parent_valid() -> bool:
    value = _read(contract.BUILD_PARENT)
    return bool(
        value.get("role") == "v25034_single_column_successor_clean_build_audit"
        and value.get("audit_valid") is True
        and value.get("findings") == []
        and contract.sealed(value, "audit_payload_sha256")
        and value.get("authorization", {}).get(
            "fresh_benchmark_external_matched_gate_design"
        )
        is True
    )


def build_build_audit(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    tests = _tests()
    closure = _dependency_closure(contract.FORWARD_SOURCES)
    semantic = _semantic(closure)
    historical_hits = _historical_literal_hits()
    build_sources = tuple(
        relative
        for relative in contract.LOCAL_SOURCES
        if relative != contract.BUILD_AUDIT
    )
    manifest = {
        str(relative): contract.sha256(
            contract.ordinary(ROOT, relative, tracked=True)
        )
        for relative in build_sources
    }
    closure_manifest = {
        str(relative): contract.sha256(
            contract.ordinary(ROOT, relative, tracked=True)
        )
        for relative in closure
    }
    future = (
        contract.PROTOCOL,
        contract.PREAUDIT,
        contract.EXECUTION_START,
        contract.READINESS,
        contract.OUTPUT_ROOT,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
    )
    checks = {
        "head_equals_target_main": head == target,
        "focused_and_parent_tests_exact47": tests["passed"],
        "v25034_build_parent_valid": _build_parent_valid(),
        "population_selection_parent_is_ancestor": subprocess.run(
            [
                "git",
                "merge-base",
                "--is-ancestor",
                contract.POPULATION_SELECTION_PARENT_COMMIT,
                head,
            ],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode
        == 0,
        "population_historical_literal_hits_zero": not historical_hits,
        "population_prior_project_overlap_zero": not (
            set(contract.PROJECTS) & contract.PRIOR_PROJECTS
        ),
        "population_exact40_bilingual20_20": len(contract.PROJECTS)
        == contract.TASK_COUNT
        == 40
        and contract.ENGLISH_TASK_COUNT == contract.CHINESE_TASK_COUNT == 20,
        "runtime_dependency_closure_nonempty": bool(closure),
        "runtime_privileged_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "runtime_evaluator_capability_zero": not semantic[
            "evaluator_capabilities"
        ],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "one_shared_model_output_per_task": contract.MODEL_CALLS_PER_TASK == 1,
        "one_exact_fetch_per_task": contract.FETCH_TARGETS_PER_TASK == 1,
        "minimum_natural_recovery_strict_positive": contract.MINIMUM_NATURAL_RECOVERIES
        >= 1,
        "future_effect_surfaces_pristine": _future_pristine(future),
        "protected_watchers_exact": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
        "shared_api_lease_inactive": _lease_inactive(),
        "network_model_search_fetch_or_evaluator_not_called_by_build_audit": True,
        "entropy_information_gain_signed_credit_disabled": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25035_single_column_external_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "head": head,
        "target_main": target,
        "population_selection_parent_commit": contract.POPULATION_SELECTION_PARENT_COMMIT,
        "population_historical_literal_hits": historical_hits,
        "tests": tests,
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "runtime_dependency_manifest": closure_manifest,
        "runtime_dependency_manifest_sha256": contract.payload_sha256(
            closure_manifest
        ),
        "runtime_semantic_audit": semantic,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "network_model_search_fetch_or_evaluator_called": False,
        "authorization": {
            "protocol_generation_after_build_commit_push": not findings,
            "external_forward": False,
            "postfreeze_evaluator": False,
            "new_deepwidebench_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    protocol = contract.validate_protocol(
        ROOT, _read(contract.PROTOCOL), tracked=True
    )
    tests = _tests()
    closure = _dependency_closure(contract.FORWARD_SOURCES)
    semantic = _semantic(closure)
    future = (
        contract.EXECUTION_START,
        contract.READINESS,
        contract.OUTPUT_ROOT,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
    )
    checks = {
        "head_equals_target_main": head == target,
        "protocol_valid": True,
        "focused_and_parent_tests_exact47": tests["passed"],
        "runtime_privileged_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "runtime_evaluator_capability_zero": not semantic[
            "evaluator_capabilities"
        ],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "endpoint_tcp_healthy": _endpoint(),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "future_effect_surfaces_pristine": _future_pristine(future),
        "protocol_does_not_authorize_forward": protocol["authorization"][
            "external_forward"
        ]
        is False,
        "entropy_information_gain_signed_credit_disabled": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25035_single_column_external_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "head": head,
        "target_main": target,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "protocol_payload_sha256": protocol["protocol_payload_sha256"],
        "tests": tests,
        "runtime_semantic_audit": semantic,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "network_model_search_fetch_or_evaluator_called": False,
        "authorization": {
            "execution_start_generation_after_preactivation_commit_push": not findings,
            "external_forward": False,
            "postfreeze_evaluator": False,
            "new_deepwidebench_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def build_start(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    protocol = contract.validate_protocol(
        ROOT, _read(contract.PROTOCOL), tracked=True
    )
    preaudit = _read(contract.PREAUDIT)
    future = (
        contract.READINESS,
        contract.OUTPUT_ROOT,
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
    )
    if (
        preaudit.get("role")
        != "v25035_single_column_external_preactivation_audit"
        or preaudit.get("audit_valid") is not True
        or preaudit.get("findings") != []
        or not contract.sealed(preaudit, "audit_payload_sha256")
        or preaudit.get("authorization", {}).get(
            "execution_start_generation_after_preactivation_commit_push"
        )
        is not True
        or not _endpoint()
        or contract.watcher_snapshot() != protocol["protected_watchers"]
        or not _lease_inactive()
        or not _future_pristine(future)
    ):
        raise RuntimeError("V2.50.35 execution start barrier failed")
    value = {
        "artifact_version": 1,
        "role": "v25035_single_column_external_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "head": head,
        "target_main": target,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "endpoint_vector_sha256": protocol["population"]["endpoint_vector_sha256"],
        "protected_watchers": contract.watcher_snapshot(),
        "shared_api_lease_inactive": True,
        "effect_surface_pristine": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "authorization": {
            "one_fresh_external_forward": True,
            "postfreeze_evaluator": False,
            "retry_resume_skip_or_population_replacement": False,
            "new_deepwidebench_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "execution_start_payload_sha256")


def build_forward_audit(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    protocol = contract.validate_protocol(
        ROOT, _read(contract.PROTOCOL), tracked=True
    )
    readiness = runner.validate_readiness(_read(contract.READINESS))
    forward = _read(contract.FORWARD_RESULT)
    freeze = _read(contract.PREDICTION_FREEZE)
    rows = [runner.validate_task_row(row) for row in _jsonl(contract.TASK_ROWS)]
    aggregate = runner.aggregate(rows)
    mechanism = runner.mechanism_decision(aggregate)
    checks = {
        "head_equals_target_main": head == target,
        "protocol_valid": True,
        "readiness_passed": readiness["passed"] is True,
        "fixed_task_denominator": len(rows) == contract.TASK_COUNT,
        "unique_task_indices": {row["index"] for row in rows}
        == set(range(contract.TASK_COUNT)),
        "task_rows_hash_bound": forward.get("task_rows_sha256")
        == freeze.get("task_rows_sha256")
        == contract.sha256(ROOT / contract.TASK_ROWS),
        "prediction_freeze_hash_bound": forward.get("prediction_freeze_sha256")
        == contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "readiness_hash_bound": forward.get("readiness_sha256")
        == freeze.get("readiness_sha256")
        == contract.sha256(ROOT / contract.READINESS),
        "forward_result_sealed": contract.sealed(
            forward, "result_payload_sha256"
        ),
        "prediction_freeze_sealed": contract.sealed(
            freeze, "freeze_payload_sha256"
        ),
        "aggregate_recomputed_exact": forward.get("aggregate") == aggregate,
        "mechanism_decision_recomputed_exact": forward.get(
            "mechanism_decision"
        )
        == mechanism,
        "one_shared_model_output_per_task": all(
            row["one_model_call_shared_by_both_arms"] is True for row in rows
        ),
        "zero_candidate_extra_effect": aggregate[
            "additional_model_search_or_fetch_calls"
        ]
        == 0,
        "zero_nonempty_factual_cell_rewrite": aggregate[
            "nonempty_factual_cell_rewrite_count"
        ]
        == 0,
        "all_predictions_frozen_before_evaluator": freeze[
            "all_predictions_terminal_before_evaluator_or_gold_refetch"
        ]
        is True,
        "evaluator_gold_result_surfaces_absent": _future_pristine(
            (contract.EVALUATOR_PROTOCOL, contract.GOLD_SNAPSHOT, contract.RESULT, contract.POSTAUDIT)
        ),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": forward[
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        ]
        is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    evaluator_authorized = not findings and mechanism["mechanism_gate_passed"]
    value = {
        "artifact_version": 1,
        "role": "v25035_single_column_external_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "head": head,
        "target_main": target,
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "readiness_sha256": contract.sha256(ROOT / contract.READINESS),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "prediction_freeze_sha256": contract.sha256(
            ROOT / contract.PREDICTION_FREEZE
        ),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        "aggregate": aggregate,
        "mechanism_decision": mechanism,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "private_gold_mapping_or_evaluator_opened_or_hashed": False,
        "retry_resume_skip_or_selective_rerun": False,
        "authorization": {
            "postfreeze_external_evaluator_protocol": evaluator_authorized,
            "same_population_retry_resume_or_rerun": False,
            "new_deepwidebench_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def build_postaudit(*, now: int | None = None) -> dict[str, Any]:
    head, target = _clean_pushed()
    result = _read(contract.RESULT)
    evaluator = finalizer.validate_evaluator_protocol(
        _read(contract.EVALUATOR_PROTOCOL)
    )
    gold_rows = _jsonl(contract.GOLD_SNAPSHOT)
    task_rows = _jsonl(contract.TASK_ROWS)
    metrics = finalizer.aggregate_metrics(task_rows, gold_rows)
    forward = _read(contract.FORWARD_RESULT)
    decision = finalizer.quality_decision(
        metrics, forward["mechanism_decision"]
    )
    checks = {
        "head_equals_target_main": head == target,
        "result_sealed": contract.sealed(result, "result_payload_sha256"),
        "evaluator_protocol_valid": True,
        "gold_fixed_denominator": len(gold_rows) == contract.TASK_COUNT,
        "gold_one_attempt_per_task": sum(
            int(row["fetch_attempts"]) for row in gold_rows
        )
        == contract.TASK_COUNT,
        "metrics_recomputed_exact": result.get("metrics") == metrics,
        "quality_decision_recomputed_exact": result.get("quality_decision")
        == decision,
        "parent_hashes_bound": result.get("parents") == evaluator["parents"],
        "gold_snapshot_hash_bound": result.get("gold_snapshot_sha256")
        == contract.sha256(ROOT / contract.GOLD_SNAPSHOT),
        "fixed_denominator_failure_as_zero": result.get(
            "fixed_denominator_failure_as_zero"
        )
        is True,
        "no_retry_refetch_or_selective_revaluation": result.get(
            "retry_refetch_or_selective_revaluation"
        )
        is False,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == contract.validate_protocol(
            ROOT, _read(contract.PROTOCOL), tracked=True
        )["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "no_deepwidebench_or_sota_claim": result.get("claims", {}).get(
            "deepwidebench_score"
        )
        is False
        and result.get("claims", {}).get("leaderboard_or_sota") is False,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v25035_single_column_external_postresult_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "head": head,
        "target_main": target,
        "result_sha256": contract.sha256(ROOT / contract.RESULT),
        "evaluator_protocol_sha256": contract.sha256(
            ROOT / contract.EVALUATOR_PROTOCOL
        ),
        "gold_snapshot_sha256": contract.sha256(ROOT / contract.GOLD_SNAPSHOT),
        "metrics": metrics,
        "quality_decision": decision,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "production_integration_evidence": not findings
            and decision["single_column_external_quality_gate_go"],
            "new_deepwidebench_exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "build-audit",
            "protocol",
            "preaudit",
            "start",
            "forward-audit",
            "evaluator-protocol",
            "postaudit",
        ),
    )
    args = parser.parse_args()
    if args.command == "build-audit":
        value = build_build_audit()
        if not value["audit_valid"]:
            raise RuntimeError(value["findings"])
        _publish(contract.BUILD_AUDIT, value)
        path = contract.BUILD_AUDIT
    elif args.command == "protocol":
        _clean_pushed()
        value = contract.build_protocol(ROOT, now=int(time.time()), tracked=True)
        contract.validate_protocol(ROOT, value, tracked=True)
        _publish(contract.PROTOCOL, value)
        path = contract.PROTOCOL
    elif args.command == "preaudit":
        value = build_preaudit()
        if not value["audit_valid"]:
            raise RuntimeError(value["findings"])
        _publish(contract.PREAUDIT, value)
        path = contract.PREAUDIT
    elif args.command == "start":
        value = build_start()
        _publish(contract.EXECUTION_START, value)
        path = contract.EXECUTION_START
    elif args.command == "forward-audit":
        value = build_forward_audit()
        if not value["audit_valid"]:
            raise RuntimeError(value["findings"])
        _publish(contract.FORWARD_AUDIT, value)
        path = contract.FORWARD_AUDIT
    elif args.command == "evaluator-protocol":
        _clean_pushed()
        value = finalizer.build_evaluator_protocol()
        finalizer.validate_evaluator_protocol(value)
        _publish(contract.EVALUATOR_PROTOCOL, value)
        path = contract.EVALUATOR_PROTOCOL
    else:
        value = build_postaudit()
        if not value["audit_valid"]:
            raise RuntimeError(value["findings"])
        _publish(contract.POSTAUDIT, value)
        path = contract.POSTAUDIT
    print(
        json.dumps(
            {
                "command": args.command,
                "path": str(path),
                "audit_valid": value.get("audit_valid"),
                "authorization": value.get("authorization"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
