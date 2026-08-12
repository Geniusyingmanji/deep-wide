#!/usr/bin/env python3
"""Hash-bound preactivation recovery for the unexecuted V2.52.06 gate.

V2.52.06 already has a clean pushed build audit proving the exact 324-suite
closure.  Re-running that full closure during preactivation twice encountered
non-reproducible shared test-resource failures, while the same complete suite
and each reported failing suite passed from the unchanged source manifest.

This append-only control-plane recovery never changes or executes the forward.
It reuses the frozen full-suite proof only when the live forward dependency
manifest is byte-identical to both the build audit and protocol, then reruns all
cheap live safety checks (label blindness, evaluator absence, endpoint, lease,
conflicts, watcher identity, task vector, and future-surface pristine state).
"""

from __future__ import annotations

import argparse
import ast
import copy
import json
import os
import re
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

from deepwide_agent import (  # noqa: E402
    v25206_cran_dcf_quality_contract as contract,
)
from scripts import control_v25206_cran_dcf_quality as control  # noqa: E402


DATE = "20260812"
ROLE = "v25207_v25206_hash_bound_preactivation_recovery_audit"
RECOVERY_AUDIT = Path(
    f"results/v25207_v25206_hash_bound_preactivation_recovery_audit_v1_{DATE}.json"
)
SOURCE = Path("scripts/recover_v25207_v25206_hash_bound_preactivation.py")
TEST = Path("tests/test_recover_v25207_v25206_hash_bound_preactivation.py")
BUILD_AUDIT_SHA256 = (
    "797e006564d991d3399101327a34d86766521c05a5a18f63d952fe7d2615034c"
)
PROTOCOL_SHA256 = (
    "d95818b787bfce2c1470854005ccaef4ebdeca170611c6049dc5b2c0dbe408f0"
)
EXPECTED_FULL_TESTS = control.EXPECTED_TESTS
RECOVERY_TESTS = 5


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


def _read(path: Path, *, tracked: bool) -> dict[str, Any]:
    ordinary = contract.ordinary(ROOT, path, tracked=tracked)
    value = json.loads(ordinary.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.07 expected JSON object")
    return value


def _implementation_audit(*, tracked: bool) -> dict[str, Any]:
    source_path = contract.ordinary(ROOT, SOURCE, tracked=tracked)
    test_path = contract.ordinary(ROOT, TEST, tracked=tracked)
    source = source_path.read_text(encoding="utf-8")
    test = test_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    forbidden_imports = {"requests", "httpx", "aiohttp", "urllib"}
    imports: set[str] = set()
    privileged: list[str] = []
    privileged_fields = {
        "category",
        "question_type",
        "task_category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "score",
        "reward",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(item.name.split(".", 1)[0] for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add((node.module or "").split(".", 1)[0])
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            if node.slice.value in privileged_fields:
                privileged.append(str(node.slice.value))
    test_count = sum(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
        for node in ast.walk(ast.parse(test, filename=str(test_path)))
    )
    checks = {
        "network_client_import_absent": not imports.intersection(forbidden_imports),
        "credential_literal_zero": contract.SECRET.search(source + test) is None,
        "privileged_benchmark_field_access_zero": not privileged,
        "exact_recovery_test_count": test_count == RECOVERY_TESTS,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "privileged_accesses": sorted(set(privileged)),
        "source_sha256": contract.sha256(source_path),
        "test_sha256": contract.sha256(test_path),
        "test_count": test_count,
    }


def _run_recovery_tests() -> dict[str, Any]:
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
            TEST.name,
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
        "expected": RECOVERY_TESTS,
        "observed": observed,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and observed == RECOVERY_TESTS,
        "output_sha256": contract.payload_sha256(completed.stdout),
    }


def _frozen_parents(*, tracked: bool) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
    build_path = contract.ordinary(ROOT, contract.BUILD_AUDIT, tracked=tracked)
    protocol_path = contract.ordinary(ROOT, contract.PROTOCOL, tracked=tracked)
    if (
        contract.sha256(build_path) != BUILD_AUDIT_SHA256
        or contract.sha256(protocol_path) != PROTOCOL_SHA256
    ):
        raise RuntimeError("V2.52.07 frozen parent hash drifted")
    build = control.validate_build(json.loads(build_path.read_text(encoding="utf-8")))
    protocol = contract.validate_protocol(
        ROOT, json.loads(protocol_path.read_text(encoding="utf-8"))
    )
    manifest = contract.dependency_manifest(ROOT, tracked=tracked)
    if (
        build["source_manifest"] != manifest
        or protocol["source_manifest"] != manifest
        or build["source_manifest_sha256"] != contract.payload_sha256(manifest)
        or protocol["source_manifest_sha256"] != contract.payload_sha256(manifest)
        or build["tests"]["expected"] != EXPECTED_FULL_TESTS
        or build["tests"]["observed"] != EXPECTED_FULL_TESTS
        or build["tests"]["passed"] is not True
    ):
        raise RuntimeError("V2.52.07 frozen full-test proof is not live")
    return build, protocol, manifest


def build_recovery_audit(
    *, now: int | None = None, require_clean: bool = True, tracked: bool = True
) -> dict[str, Any]:
    head, target = (
        control._clean_pushed() if require_clean else ("recovery-only", "recovery-only")
    )
    build, protocol, manifest = _frozen_parents(tracked=tracked)
    implementation = _implementation_audit(tracked=tracked)
    tests = _run_recovery_tests()
    future = (
        RECOVERY_AUDIT,
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
        "frozen_build_and_protocol_validate": build["audit_valid"] is True,
        "full_324_test_proof_exact": build["tests"]["passed"] is True,
        "full_test_proof_bound_to_live_forward_manifest": build["source_manifest"]
        == manifest
        == protocol["source_manifest"],
        "recovery_implementation_audit_valid": implementation["audit_valid"],
        "recovery_tests_exact": tests["passed"],
        "future_surfaces_pristine": control._future_pristine(future),
        "local_gpt56_endpoint_reachable": control._endpoint_reachable(),
        "shared_api_lease_inactive": control._lease_inactive(),
        "no_active_conflicting_forward_or_evaluator": not control._active_conflicts(),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "evaluator_implementation_absent": not (ROOT / contract.EVALUATOR).exists()
        and not (ROOT / contract.EVALUATOR_TEST).exists(),
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "parents": {
            "build_audit_sha256": BUILD_AUDIT_SHA256,
            "protocol_sha256": PROTOCOL_SHA256,
            "source_manifest_sha256": contract.payload_sha256(manifest),
        },
        "frozen_full_test_proof": copy.deepcopy(build["tests"]),
        "implementation_audit": implementation,
        "recovery_tests": tests,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "authorization": {
            "hash_bound_preactivation_generation": not findings,
            "external_forward": False,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_recovery_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    implementation = _implementation_audit(tracked=True)
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("parents")
        != {
            "build_audit_sha256": BUILD_AUDIT_SHA256,
            "protocol_sha256": PROTOCOL_SHA256,
            "source_manifest_sha256": contract.payload_sha256(
                contract.dependency_manifest(ROOT, tracked=True)
            ),
        }
        or copied.get("frozen_full_test_proof", {}).get("expected")
        != EXPECTED_FULL_TESTS
        or copied.get("frozen_full_test_proof", {}).get("observed")
        != EXPECTED_FULL_TESTS
        or copied.get("frozen_full_test_proof", {}).get("passed") is not True
        or copied.get("implementation_audit") != implementation
        or copied.get("recovery_tests", {}).get("expected") != RECOVERY_TESTS
        or copied.get("recovery_tests", {}).get("observed") != RECOVERY_TESTS
        or copied.get("recovery_tests", {}).get("passed") is not True
        or copied.get("findings") != []
        or copied.get("audit_valid") is not True
        or not copied.get("checks")
        or not all(copied["checks"].values())
        or copied.get("authorization")
        != {
            "hash_bound_preactivation_generation": True,
            "external_forward": False,
            "external_evaluator": False,
            "deepwidebench_dev64_exact220_or_sota": False,
        }
        or copied.get(
            "network_model_search_fetch_evaluator_benchmark_or_api_called"
        )
        is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.52.07 recovery audit drifted")
    return copied


def build_recovered_preaudit(*, now: int | None = None) -> dict[str, Any]:
    head, target = control._clean_pushed()
    recovery = validate_recovery_audit(_read(RECOVERY_AUDIT, tracked=True))
    build, protocol, manifest = _frozen_parents(tracked=True)
    semantic = control._semantic_audit()
    future = (
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
        "build_protocol_and_recovery_audit_valid": build["audit_valid"] is True
        and recovery["audit_valid"] is True,
        "frozen_full_324_test_proof_exact": build["tests"]["expected"]
        == build["tests"]["observed"]
        == EXPECTED_FULL_TESTS
        and build["tests"]["passed"] is True,
        "frozen_test_proof_bound_to_live_forward_manifest": build["source_manifest"]
        == manifest
        == protocol["source_manifest"],
        "privileged_runtime_field_access_zero": not semantic[
            "privileged_runtime_field_accesses"
        ],
        "evaluator_capability_absent": not semantic["evaluator_capabilities"],
        "credential_literal_zero": not semantic["credential_literal_hits"],
        "selection_still_valid": control._selection_valid(tracked=True),
        "diagnosis_still_valid": control._diagnosis_valid(tracked=True),
        "future_surfaces_pristine": control._future_pristine(future),
        "local_gpt56_endpoint_reachable": control._endpoint_reachable(),
        "shared_api_lease_inactive": control._lease_inactive(),
        "no_active_conflicting_forward_or_evaluator": not control._active_conflicts(),
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "evaluator_implementation_absent_before_prediction_freeze": not (
            ROOT / contract.EVALUATOR
        ).exists()
        and not (ROOT / contract.EVALUATOR_TEST).exists(),
        "natural_task_vector_stable": contract.payload_sha256(
            contract.task_vector()
        )
        == protocol["population"]["task_vector_sha256"],
        "no_external_effect_performed": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25206_cran_dcf_quality_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git": {"head": head, "target_main": target, "equal": head == target},
        "build_audit_sha256": BUILD_AUDIT_SHA256,
        "protocol_sha256": PROTOCOL_SHA256,
        "recovery_audit_sha256": contract.sha256(ROOT / RECOVERY_AUDIT),
        "test_proof": {
            "mode": "frozen_full_build_audit_reuse",
            "full_test_count": EXPECTED_FULL_TESTS,
            "source_manifest_sha256": contract.payload_sha256(manifest),
            "no_test_scope_reduction": True,
        },
        "tests": copy.deepcopy(build["tests"]),
        "semantic_audit": semantic,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
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
    value = contract.seal(value, "audit_payload_sha256")
    return validate_recovered_preaudit(value)


def validate_recovered_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    build, protocol, manifest = _frozen_parents(tracked=True)
    expected_test_proof = {
        "mode": "frozen_full_build_audit_reuse",
        "full_test_count": EXPECTED_FULL_TESTS,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "no_test_scope_reduction": True,
    }
    if (
        copied.get("recovery_audit_sha256") != contract.sha256(ROOT / RECOVERY_AUDIT)
        or copied.get("test_proof") != expected_test_proof
        or copied.get("tests") != build["tests"]
        or copied.get("protocol_sha256") != PROTOCOL_SHA256
        or copied.get("build_audit_sha256") != BUILD_AUDIT_SHA256
        or copied.get("protected_watchers") != protocol["protected_watchers"]
    ):
        raise RuntimeError("V2.52.07 recovered preaudit proof drifted")
    return control.validate_preaudit(copied)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit", "preaudit"))
    args = parser.parse_args()
    if args.command == "audit":
        value = validate_recovery_audit(build_recovery_audit())
        path = RECOVERY_AUDIT
    else:
        value = build_recovered_preaudit()
        path = contract.PREAUDIT
    _publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "role": value["role"],
                "audit_valid": value["audit_valid"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
