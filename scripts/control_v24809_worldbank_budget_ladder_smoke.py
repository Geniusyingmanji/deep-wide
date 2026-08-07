#!/usr/bin/env python3
"""Build audit and staged activation for the V2.48.09 external smoke."""

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

from deepwide_agent import v24809_worldbank_budget_ladder_smoke_contract as contract  # noqa: E402


TESTS = (
    (Path("tests/test_v24804_shared_prefix_budget_ladder.py"), 6),
    (Path("tests/test_v24809_worldbank_budget_ladder_smoke.py"), 5),
    (Path("tests/test_evaluate_v24809_worldbank_budget_ladder_smoke.py"), 3),
)
EXPECTED_TESTS = 14
PREDECESSOR_BUILD_AUDIT = Path(
    f"results/v24809_worldbank_budget_ladder_smoke_build_audit_v1_{contract.DATE}.json"
)
PRIVILEGED = frozenset(
    {
        "benchmark_question_type",
        "question_type",
        "task_category",
        "category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "mapping",
        "evaluator",
        "reward",
    }
)
EVALUATOR_IMPORT_MARKERS = (
    "official_eval",
    "official_evaluator",
    "external_evaluator",
    "evaluator_mapping",
    "finalize_v24",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.48.09 control requires clean pushed HEAD")


def _read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.48.09 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.09 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _run_tests() -> tuple[int, bool, list[dict[str, Any]]]:
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
    for path, expected in TESTS:
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"), "-I", "-B", "-m",
                "unittest", "discover", "-s", "tests", "-p", path.name, "-v",
            ],
            cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=300, check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append(
            {
                "path": str(path),
                "expected": expected,
                "observed": observed,
                "passed": completed.returncode == 0 and observed == expected,
                "output_sha256": contract.payload_sha256(completed.stdout),
            }
        )
    total = sum(row["observed"] for row in rows)
    return total, total == EXPECTED_TESTS and all(row["passed"] for row in rows), rows


def _ast_findings() -> tuple[list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    secrets: list[str] = []
    for relative in contract.RUNTIME_SOURCES:
        source = (ROOT / relative).read_text(encoding="utf-8")
        if SECRET.search(source):
            secrets.append(str(relative))
        tree = ast.parse(source)
        for node in ast.walk(tree):
            key = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value.casefold()
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value.casefold()
            if key in PRIVILEGED:
                fields.append(f"{relative}:{node.lineno}:{key}")
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            for name in names:
                if any(marker in name.casefold() for marker in EVALUATOR_IMPORT_MARKERS):
                    imports.append(f"{relative}:{node.lineno}:{name}")
    return sorted(fields), sorted(imports), sorted(secrets)


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


def _endpoint() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=0.5):
            return True
    except OSError:
        return False


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="], stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
        timeout=20, check=False,
    )
    markers = (contract.RUNNER_MARKER, contract.CHILD_MARKER, "scripts/run_official_eval_local.py")
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    predecessor = _read(ROOT / PREDECESSOR_BUILD_AUDIT)
    if (
        predecessor.get("role")
        != "v24809_worldbank_budget_ladder_smoke_build_audit"
        or predecessor.get("audit_valid") is not True
        or predecessor.get("findings") != []
        or not _sealed(predecessor, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.48.09 predecessor build audit drifted")
    fields, imports, secrets = _ast_findings()
    observed, tests_passed, suites = _run_tests()
    value = {
        "artifact_version": 1,
        "role": "v24809_worldbank_budget_ladder_smoke_build_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "git_head": _git("rev-parse", "HEAD"),
        "append_only_control_repair": {
            "predecessor_path": str(PREDECESSOR_BUILD_AUDIT),
            "predecessor_sha256": contract.sha256(ROOT / PREDECESSOR_BUILD_AUDIT),
            "only_change": "remove_impossible_build_commit_equals_protocol_commit_cycle_and_bind_audited_source_manifest",
            "forward_algorithm_task_population_model_search_budget_or_evaluator_changed": False,
            "predecessor_launch_or_effect_started": False,
        },
        "source_manifest": {
            str(path): contract.sha256(ROOT / path)
            for path in (
                Path("src/deepwide_agent/v24809_worldbank_budget_ladder_smoke_contract.py"),
                Path("src/deepwide_agent/v24809_worldbank_budget_ladder_runner_integration.py"),
                Path("scripts/design_v24809_worldbank_budget_ladder_smoke_protocol.py"),
                Path("scripts/control_v24809_worldbank_budget_ladder_smoke.py"),
                Path("scripts/run_v24809_worldbank_budget_ladder_smoke_task.py"),
                Path("scripts/run_v24809_worldbank_budget_ladder_smoke_forward.py"),
                Path("scripts/audit_v24809_worldbank_budget_ladder_smoke_forward.py"),
                Path("scripts/evaluate_v24809_worldbank_budget_ladder_smoke.py"),
                Path("tests/test_v24809_worldbank_budget_ladder_smoke.py"),
                Path("tests/test_evaluate_v24809_worldbank_budget_ladder_smoke.py"),
            )
        },
        "tests": {
            "expected": EXPECTED_TESTS,
            "observed": observed,
            "passed": tests_passed,
            "suites": suites,
        },
        "label_blind_audit": {
            "privileged_accesses": fields,
            "evaluator_imports": imports,
            "credential_literal_hits": secrets,
            "passed": not fields and not imports and not secrets,
        },
        "checks": {
            "shared_prefix_and_suffix_blind_tests_passed": tests_passed,
            "runtime_label_blind": not fields and not imports and not secrets,
            "runtime_dependency_manifest_has_no_evaluation_path": all(
                path.parts[:1] != ("evaluation",) for path in contract.RUNTIME_SOURCES
            ),
            "future_surface_pristine": _future_pristine(
                (
                    contract.BUILD_AUDIT, contract.PROTOCOL, contract.PREAUDIT, contract.ACTIVATION,
                    contract.EXECUTION_START, contract.FORWARD_RESULT,
                    contract.FORWARD_AUDIT, contract.OUTPUT_ROOT,
                )
            ),
        },
        "effect_boundary": {
            "private_population_opened": False,
            "network_model_search_fetch_or_evaluator_called": False,
            "benchmark_forward_started": False,
        },
    }
    value["findings"] = sorted(
        name for name, passed in value["checks"].items() if not passed
    )
    value["audit_valid"] = not value["findings"]
    value["authorization"] = {
        "protocol_generation": value["audit_valid"],
        "preactivation_audit_generation": False,
        "single_smoke_forward": False,
        "evaluator": False,
        "main_calibration_lock_validation_or_confirmatory": False,
        "public_dev64_or_exact220": False,
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def _validate_build(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    if (
        copied.get("role") != "v24809_worldbank_budget_ladder_smoke_build_audit"
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.48.09 build audit drifted")
    return copied


def build_preaudit(*, now: int | None = None) -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT, _read(ROOT / contract.PROTOCOL))
    build = _validate_build(_read(ROOT / contract.BUILD_AUDIT))
    watchers = contract.protected_watcher_snapshot()
    findings: list[str] = []
    observed, tests_passed, suites = _run_tests()
    fields, imports, secrets = _ast_findings()
    if observed != EXPECTED_TESTS or not tests_passed:
        findings.append("focused_tests_failed")
    if fields or imports or secrets:
        findings.append("runtime_label_blind_audit_failed")
    if protocol.get("build_audit_sha256") != contract.sha256(
        ROOT / contract.BUILD_AUDIT
    ):
        findings.append("protocol_build_audit_binding_drifted")
    source_manifest = build.get("source_manifest")
    if (
        not isinstance(source_manifest, Mapping)
        or any(
            contract.sha256(ROOT / relative) != digest
            for relative, digest in source_manifest.items()
        )
    ):
        findings.append("audited_source_manifest_drifted")
    if watchers != protocol["execution"]["protected_watchers"]:
        findings.append("protected_watcher_drifted")
    if not _endpoint():
        findings.append("gpt56_endpoint_unreachable")
    if not _lease_inactive():
        findings.append("shared_api_lease_active")
    conflicts = _active_conflicts()
    if conflicts:
        findings.append("conflicting_runner_or_evaluator_active")
    if not _future_pristine(
        (contract.PREAUDIT, contract.ACTIVATION, contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.OUTPUT_ROOT)
    ):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24809_worldbank_budget_ladder_smoke_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        "tests": {"expected": EXPECTED_TESTS, "observed": observed, "passed": tests_passed, "suites": suites},
        "runtime": {
            "endpoint_reachable_without_request": _endpoint(),
            "shared_api_lease_inactive": _lease_inactive(),
            "active_conflicts": conflicts,
            "protected_watchers": watchers,
        },
        "label_blind_audit": {"privileged_accesses": fields, "evaluator_imports": imports, "credential_literal_hits": secrets},
        "private_population_gold_provenance_or_evaluator_opened_or_hashed": False,
        "network_model_search_fetch_or_evaluator_called": False,
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "activation_generation": not findings,
            "single_smoke_forward": False,
            "evaluator": False,
            "main_calibration_lock_validation_or_confirmatory": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def build_activation(*, now: int | None = None) -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT, _read(ROOT / contract.PROTOCOL))
    audit = _read(ROOT / contract.PREAUDIT)
    findings: list[str] = []
    if (
        audit.get("role") != "v24809_worldbank_budget_ladder_smoke_preactivation_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("activation_generation") is not True
        or not _sealed(audit, "audit_payload_sha256")
    ):
        findings.append("preactivation_chain_invalid")
    if contract.protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        findings.append("protected_watcher_drifted")
    if not _lease_inactive() or _active_conflicts():
        findings.append("runtime_conflict")
    if not _future_pristine((contract.ACTIVATION, contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.OUTPUT_ROOT)):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24809_worldbank_budget_ladder_smoke_activation",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "activated_not_started" if not findings else "rejected",
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "protected_watchers": contract.protected_watcher_snapshot(),
        "findings": findings,
        "private_population_gold_provenance_or_evaluator_opened_or_hashed": False,
        "network_model_search_fetch_or_evaluator_called": False,
        "authorization": {
            "execution_start_generation": not findings,
            "single_smoke_forward": False,
            "evaluator": False,
            "main_calibration_lock_validation_or_confirmatory": False,
            "public_dev64_or_exact220": False,
        },
    }
    value["activation_payload_sha256"] = contract.payload_sha256(value)
    return value


def build_start(*, now: int | None = None) -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT, _read(ROOT / contract.PROTOCOL))
    audit, activation = _read(ROOT / contract.PREAUDIT), _read(ROOT / contract.ACTIVATION)
    findings: list[str] = []
    if (
        not _sealed(audit, "audit_payload_sha256")
        or not _sealed(activation, "activation_payload_sha256")
        or activation.get("status") != "activated_not_started"
        or activation.get("authorization", {}).get("execution_start_generation") is not True
    ):
        findings.append("activation_chain_invalid")
    if contract.protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        findings.append("protected_watcher_drifted")
    if not _endpoint() or not _lease_inactive() or _active_conflicts():
        findings.append("runtime_not_ready")
    if not _future_pristine((contract.EXECUTION_START, contract.FORWARD_RESULT, contract.FORWARD_AUDIT, contract.OUTPUT_ROOT)):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24809_worldbank_budget_ladder_smoke_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "authorized_not_started" if not findings else "rejected",
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "preactivation_audit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "activation_sha256": contract.sha256(ROOT / contract.ACTIVATION),
        "protected_watchers": contract.protected_watcher_snapshot(),
        "findings": findings,
        "first_network_model_search_or_fetch_effect_started": False,
        "private_population_gold_provenance_or_evaluator_opened_or_hashed": False,
        "authorization": {
            "single_smoke_forward": not findings,
            "evaluator": False,
            "main_calibration_lock_validation_or_confirmatory": False,
            "public_dev64_or_exact220": False,
            "retry_resume_skip_or_selective_rerun": False,
        },
    }
    value["execution_start_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("build", "audit", "activate", "start"))
    args = parser.parse_args()
    _clean_pushed()
    if args.command == "build":
        value, path = build_audit(), contract.BUILD_AUDIT
    elif args.command == "audit":
        value, path = build_preaudit(), contract.PREAUDIT
    elif args.command == "activate":
        value, path = build_activation(), contract.ACTIVATION
    else:
        value, path = build_start(), contract.EXECUTION_START
    if value.get("findings"):
        raise RuntimeError(f"V2.48.09 {args.command} rejected: {value['findings']}")
    _publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"], "authorization": value["authorization"]}, sort_keys=True))


if __name__ == "__main__":
    main()
