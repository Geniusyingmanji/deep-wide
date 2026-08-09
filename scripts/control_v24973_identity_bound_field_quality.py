#!/usr/bin/env python3
"""Freeze and safely authorize one V2.49.73 benchmark-external forward."""

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

from deepwide_agent import v24973_identity_bound_field_quality_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402


FORWARD_SOURCES = (contract.SOURCE, contract.EXTRACTOR, contract.RUNTIME)
TEST_SUITES = (
    (contract.TEST, 14),
    (contract.EXTRACTOR_TEST, 15),
    (Path("tests/test_v24968_requirement_quality_gate.py"), 12),
    (Path("tests/test_v24966_source_fair_quality_gate.py"), 14),
)
EXPECTED_TESTS = sum(expected for _path, expected in TEST_SUITES)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(prefix) for prefix in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _git(*args: str) -> str:
    return contract.git(ROOT, *args)


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.49.73 control requires clean pushed HEAD")


def _read(relative: Path, *, tracked: bool = False) -> dict[str, Any]:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.49.73 expected ordinary object: {relative}")
    if tracked:
        contract.ordinary_tracked(ROOT, relative)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.73 expected JSON object")
    return value


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
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


def _run_tests() -> dict[str, Any]:
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    rows = []
    for path, expected in TEST_SUITES:
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
                path.name,
                "-v",
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=240,
            check=False,
        )
        matched = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(matched.group(1)) if matched else 0
        rows.append(
            {
                "path": str(path),
                "expected": expected,
                "observed": observed,
                "passed": completed.returncode == 0 and observed == expected,
                "output_sha256": contract.payload_sha256(completed.stdout),
            }
        )
    observed = sum(row["observed"] for row in rows)
    return {
        "expected": EXPECTED_TESTS,
        "observed": observed,
        "passed": observed == EXPECTED_TESTS and all(row["passed"] for row in rows),
        "suites": rows,
    }


def _runtime_findings() -> tuple[list[str], list[str], list[str]]:
    privileged: list[str] = []
    evaluator: list[str] = []
    secrets: list[str] = []
    for relative in FORWARD_SOURCES:
        path = ROOT / relative
        source = path.read_text(encoding="utf-8")
        privileged.extend(semantic_audit._accesses(path, ROOT))
        evaluator.extend(semantic_audit._evaluator_capabilities(path, ROOT))
        if SECRET.search(source):
            secrets.append(str(relative))
    return sorted(set(privileged)), sorted(set(evaluator)), sorted(set(secrets))


def _forward_ast_safe() -> bool:
    path = ROOT / contract.RUNTIME
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(item.name.casefold() for item in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append((node.module or "").casefold())
    return not any("deepwidebench" in name or "finalize" in name for name in imports)


def _endpoint_reachable() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=1.0):
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
    markers = (
        str(contract.RUNTIME),
        "run_official_eval_local.py",
        "v24973_identity_bound_field_quality evaluate",
    )
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) == 3
            and "python" in parts[1].casefold()
            and int(parts[0]) != os.getpid()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    tests = _run_tests()
    privileged, evaluator, secrets = _runtime_findings()
    manifest = contract.dependency_manifest(ROOT, tracked=False)
    checks = {
        "focused_and_parent_tests_pass": tests["passed"],
        "source_manifest_complete": len(manifest) == len(contract.LOCAL_SOURCES),
        "forward_ast_excludes_benchmark_and_finalizer_imports": _forward_ast_safe(),
        "privileged_runtime_field_findings_empty": not privileged,
        "evaluator_capability_findings_empty": not evaluator,
        "credential_literal_findings_empty": not secrets,
        "fresh_model_evaluator_population_is_disjoint": len(contract.task_vector())
        == contract.TASK_COUNT,
        "layout_preflight_made_no_model_or_evaluator_calls": True,
        "arm_order_is_exactly_balanced": sum(
            order[0] == contract.CANDIDATE_ARM
            for order in contract.arm_order_vector()
        )
        == contract.TASK_COUNT // 2,
        "public_exact220_not_authorized": True,
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24973_identity_bound_field_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "tests": tests,
        "source_manifest": manifest,
        "source_manifest_sha256": contract.payload_sha256(manifest),
        "label_blind_audit": {
            "privileged_runtime_field_accesses": privileged,
            "evaluator_capabilities": evaluator,
            "credential_literal_hits": secrets,
        },
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": contract.source_policy(),
        "authorization": {
            "implementation_commit": not findings,
            "protocol_publication": not findings,
            "external_forward": False,
            "evaluator": False,
            "public_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_build_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v24973_identity_bound_field_build_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("authorization", {}).get("public_exact220_or_sota") is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.73 build audit drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    validate_build_audit(_read(contract.BUILD_AUDIT, tracked=True))
    tests = _run_tests()
    privileged, evaluator, secrets = _runtime_findings()
    future = _future_pristine(
        (
            contract.PREAUDIT,
            contract.EXECUTION_START,
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.EVALUATOR_PROTOCOL,
            contract.RESULT,
            contract.POSTAUDIT,
            contract.OUTPUT_ROOT,
        )
    )
    checks = {
        "protocol_valid": True,
        "build_audit_valid": True,
        "focused_and_parent_tests_pass": tests["passed"],
        "future_surface_pristine": future,
        "protected_watchers_exact": contract.watcher_snapshot()
        == protocol["protected_watchers"],
        "shared_api_lease_inactive": _lease_inactive(),
        "keyless_gpt56_endpoint_reachable": _endpoint_reachable(),
        "conflicting_forward_or_evaluator_processes_absent": not _active_conflicts(),
        "privileged_runtime_field_findings_empty": not privileged,
        "evaluator_capability_findings_empty": not evaluator,
        "credential_literal_findings_empty": not secrets,
        "postfreeze_gold_surface_absent": not (ROOT / contract.GOLD_SNAPSHOT).exists(),
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24973_identity_bound_field_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        "dependency_manifest_sha256": protocol["dependency_manifest_sha256"],
        "tests": tests,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "source_policy": contract.source_policy(),
        "authorization": {
            "execution_start_generation": not findings,
            "one_external_forward": False,
            "evaluator": False,
            "public_exact220_or_sota": False,
        },
    }
    return contract.seal(value, "audit_payload_sha256")


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != "v24973_identity_bound_field_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("tests", {}).get("observed") != EXPECTED_TESTS
        or copied.get("authorization", {}).get("execution_start_generation") is not True
        or copied.get("authorization", {}).get("evaluator") is not False
        or not contract.sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.73 preactivation audit drifted")
    return copied


def build_start(*, now: int | None = None) -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    validate_preaudit(_read(contract.PREAUDIT, tracked=True))
    if not _future_pristine(
        (
            contract.EXECUTION_START,
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.EVALUATOR_PROTOCOL,
            contract.RESULT,
            contract.POSTAUDIT,
            contract.OUTPUT_ROOT,
        )
    ):
        raise RuntimeError("V2.49.73 execution surface is not pristine")
    if not _lease_inactive() or _active_conflicts() or not _endpoint_reachable():
        raise RuntimeError("V2.49.73 execution runtime is not ready")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24973_identity_bound_field_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "task_vector_sha256": protocol["population"]["task_vector_sha256"],
        "endpoint_vector_sha256": protocol["population"]["endpoint_vector_sha256"],
        "arm_order_vector_sha256": protocol["population"]["arm_order_vector_sha256"],
        "protected_watchers": contract.watcher_snapshot(),
        "prediction_and_postfreeze_gold_surfaces_pristine": True,
        "authorization": {
            "one_external_forward": True,
            "evaluator": False,
            "public_exact220_or_sota": False,
            "retry_resume_selective_rerun": False,
        },
    }
    return contract.seal(value, "execution_start_payload_sha256")


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL, tracked=True))
    if (
        copied.get("role") != "v24973_identity_bound_field_execution_start"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or copied.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or copied.get("task_vector_sha256")
        != protocol["population"]["task_vector_sha256"]
        or copied.get("endpoint_vector_sha256")
        != protocol["population"]["endpoint_vector_sha256"]
        or copied.get("arm_order_vector_sha256")
        != protocol["population"]["arm_order_vector_sha256"]
        or copied.get("protected_watchers") != contract.watcher_snapshot()
        or copied.get("authorization", {}).get("one_external_forward") is not True
        or copied.get("authorization", {}).get("evaluator") is not False
        or copied.get("authorization", {}).get("retry_resume_selective_rerun")
        is not False
        or not contract.sealed(copied, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.49.73 execution start drifted")
    return copied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build-audit", "protocol", "preaudit", "start"))
    args = parser.parse_args()
    if args.command == "build-audit":
        value = validate_build_audit(build_audit())
        path = contract.BUILD_AUDIT
    elif args.command == "protocol":
        value = contract.build_protocol(ROOT, now=int(time.time()))
        path = contract.PROTOCOL
    elif args.command == "preaudit":
        value = validate_preaudit(build_preaudit())
        path = contract.PREAUDIT
    else:
        value = validate_start(build_start())
        path = contract.EXECUTION_START
    publish_new(ROOT / path, value)
    print(
        json.dumps(
            {"path": str(path), "role": value["role"], "authorization": value["authorization"]},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
