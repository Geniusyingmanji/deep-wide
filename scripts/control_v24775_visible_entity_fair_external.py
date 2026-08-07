#!/usr/bin/env python3
"""Staged, fail-closed control for the V2.47.75 visible-only forward.

The three commands only build authorization artifacts.  They never launch the
forward and have no evaluator or private-population capability.  In
particular, every command validates the future V2.47.75 package audit before
checking an endpoint, lease, watcher, or runner state.  Therefore the control
is inert until that separately authorized audit artifact exists.
"""

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

from deepwide_agent.v24775_visible_entity_fair_execution_contract import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    LEASE_PATH,
    OUTPUT_ROOT,
    PACKAGE_BUILD,
    PREAUDIT,
    PROTOCOL,
    PROTOCOL_ID,
    protected_watcher_snapshot,
    payload_sha256,
    sha256,
)


FORWARD_FILES = (
    Path("src/deepwide_agent/v24775_visible_entity_fair_execution_contract.py"),
    Path("scripts/run_v24775_visible_entity_fair_task.py"),
    Path("scripts/run_v24775_visible_entity_fair_external.py"),
    Path("scripts/audit_v24775_visible_entity_fair_forward.py"),
)
RUNNER_MARKERS = (
    "scripts/run_v24775_visible_entity_fair_external.py",
    "scripts/run_v24775_visible_entity_fair_task.py",
)
CONTROL_TESTS = (
    (Path("tests/test_v24775_visible_entity_fair_package.py"), 10, 180),
    (Path("tests/test_v24775_visible_entity_fair_control.py"), 8, 120),
    (Path("tests/test_audit_v24775_visible_entity_fair_package.py"), 6, 120),
)
EXPECTED_CONTROL_TESTS = 24
PRIVILEGED = frozenset(
    {
        "answer",
        "answer_key",
        "category",
        "evaluator",
        "gold",
        "ground_truth",
        "mapping",
        "question_type",
        "reward",
        "score",
        "split",
        "task_category",
    }
)
FORBIDDEN_FORWARD_MARKERS = (
    "evaluation" + "/",
    "official_" + "evaluator",
    "v24774_visible_entity_fair_" + "population_private",
    "private_" + "truth.json",
    "evaluator_" + "mapping.jsonl",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _clean_remote() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.75 control requires clean pushed HEAD")


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.47.75 control expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.75 control expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _validate_protocol() -> dict[str, Any]:
    value = _read(ROOT / PROTOCOL)
    runtime = value.get("runtime", {})
    if (
        value.get("role")
        != "v24775_visible_entity_fair_external_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or not _sealed(value, "protocol_payload_sha256")
        or value.get("task_contract", {}).get("runtime_input_keys")
        != ["opaque_id", "question"]
        or value.get("task_contract", {}).get("task_count") != 8
        or runtime.get("task_executors") != 8
        or runtime.get("global_model_slot_cap") != 8
        or runtime.get("parent_timeout_seconds") != 195
        or runtime.get("experiment_wall_ceiling_seconds") != 210
        or runtime.get("experiment_level_resume_retry_skip_or_selective_rerun")
        is not False
        or runtime.get("scheduler_additional_model_query_search_fetch_or_token_effect")
        != 0
        or runtime.get("semantic_replay_additional_model_query_search_fetch_or_token_effect")
        != 0
        or value.get("authorization", {}).get("one_external_forward_launch")
        is not False
        or value.get("authorization", {}).get("quality_surface_open") is not False
    ):
        raise RuntimeError("V2.47.75 corrected protocol drifted")
    return value


def _validate_package() -> dict[str, Any]:
    """Validate the future package audit; absence is an intentional hard stop."""

    value = _read(ROOT / PACKAGE_BUILD)
    manifest = value.get("source_manifest")
    manifest_valid = isinstance(manifest, Mapping)
    if manifest_valid:
        for raw, digest in list(manifest.items()):
            relative = Path(str(raw))
            path = ROOT / relative
            if (
                not isinstance(raw, str)
                or not isinstance(digest, str)
                or relative.is_absolute()
                or ".." in relative.parts
                or relative.parts[:1] == ("evaluation",)
                or any(
                    token in relative.as_posix().casefold()
                    for token in ("private_population", "private_truth", "evaluator_mapping")
                )
                or path.is_symlink()
                or not path.is_file()
                or not path.resolve().is_relative_to(ROOT.resolve())
                or sha256(path) != digest
            ):
                manifest_valid = False
                break
    if (
        value.get("role") != "v24775_visible_entity_fair_package_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or not _sealed(value, "audit_payload_sha256")
        or value.get("label_blind_audit", {}).get("passed") is not True
        or value.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "activation": False,
            "execution_start": False,
            "external_launch": False,
            "private_truth_or_quality_surface_open": False,
            "paired_dev64": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not manifest_valid
    ):
        raise RuntimeError("V2.47.66 package audit drifted")
    return value


def _forward_findings() -> tuple[list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    markers: list[str] = []
    for relative in FORWARD_FILES:
        path = ROOT / relative
        if relative.is_absolute() or ".." in relative.parts or path.is_symlink():
            raise RuntimeError("V2.47.75 forward source path drifted")
        source = path.read_text(encoding="utf-8")
        markers.extend(
            f"{relative}:{marker}"
            for marker in FORBIDDEN_FORWARD_MARKERS
            if marker in source
        )
        tree = ast.parse(source)
        for node in ast.walk(tree):
            key: str | None = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value
            if key is not None and key.casefold() in PRIVILEGED:
                fields.append(f"{relative}:{node.lineno}:{key}")
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or "", *(alias.name for alias in node.names)]
            else:
                names = []
            imports.extend(
                f"{relative}:{node.lineno}:{name}"
                for name in names
                if any(token in name.casefold() for token in ("evaluator", "gold"))
            )
    return sorted(set(fields)), sorted(set(imports)), sorted(set(markers))


def _run_tests() -> tuple[int, bool]:
    observed = 0
    passed = True
    environment = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    for path, expected, timeout in CONTROL_TESTS:
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
            ],
            cwd=ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        count = int(match.group(1)) if match else 0
        observed += count
        passed = passed and completed.returncode == 0 and count == expected
    return observed, passed and observed == EXPECTED_CONTROL_TESTS


def _endpoint() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=0.5):
            return True
    except OSError:
        return False


def _lease_inactive() -> bool:
    path = ROOT / LEASE_PATH
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


def _active_runners() -> list[dict[str, Any]]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    output: list[dict[str, Any]] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or "python" not in parts[1].casefold():
            continue
        for marker in RUNNER_MARKERS:
            if marker in parts[2]:
                output.append({"pid": int(parts[0]), "marker": marker})
                break
    return sorted(output, key=lambda item: (item["pid"], item["marker"]))


def _pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _preaudit_value(*, now: int | None = None) -> dict[str, Any]:
    package = _validate_package()
    protocol = _validate_protocol()
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.75 preaudit requires clean pushed HEAD")
    fields, imports, markers = _forward_findings()
    count, tests_passed = _run_tests()
    watchers = protected_watcher_snapshot()
    endpoint = _endpoint()
    lease = _lease_inactive()
    runners = _active_runners()
    pristine = _pristine(
        (PREAUDIT, ACTIVATION, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    )
    findings: list[str] = []
    if not tests_passed:
        findings.append("focused_tests_failed_or_count_drifted")
    if fields:
        findings.append("privileged_forward_field_access")
    if imports:
        findings.append("evaluator_or_gold_import_in_forward")
    if markers:
        findings.append("private_or_evaluator_marker_in_forward")
    if not endpoint:
        findings.append("gpt56_endpoint_unreachable")
    if not lease:
        findings.append("shared_api_lease_active")
    if runners:
        findings.append("v24775_runner_already_active")
    if not pristine:
        findings.append("future_surface_not_pristine")
    if watchers != protocol["forward_health_gate"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24775_visible_entity_fair_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "package_build_sha256": sha256(ROOT / PACKAGE_BUILD),
        "package_manifest_sha256": payload_sha256(package["source_manifest"]),
        "checks": {
            "focused_test_count": count,
            "focused_tests_passed": tests_passed,
            "forward_label_blind": not fields and not imports and not markers,
            "gpt56_endpoint_reachable_without_provider_request": endpoint,
            "shared_api_lease_inactive": lease,
            "active_runners": runners,
            "future_surface_pristine": pristine,
            "private_population_truth_provenance_quality_or_evaluator_opened_or_hashed": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
        },
        "protected_watchers": watchers,
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
        "authorization": {
            "activation_generation": not findings,
            "execution_start_generation": False,
            "one_external_forward_launch": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def preaudit() -> dict[str, Any]:
    _clean_remote()
    # Package validation intentionally precedes every state or endpoint probe.
    _validate_package()
    value = _preaudit_value()
    if value["findings"]:
        raise RuntimeError("V2.47.75 preactivation audit rejected")
    return value


def _activation_value(*, now: int | None = None) -> dict[str, Any]:
    _validate_package()
    protocol = _validate_protocol()
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.75 activation requires clean pushed HEAD")
    audit = _read(ROOT / PREAUDIT)
    watchers = protected_watcher_snapshot()
    runners = _active_runners()
    findings: list[str] = []
    if (
        audit.get("role") != "v24775_visible_entity_fair_preactivation_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or not _sealed(audit, "audit_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("launch_authorized") is not True
        or audit.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or audit.get("package_build_sha256") != sha256(ROOT / PACKAGE_BUILD)
        or audit.get("authorization", {}).get("activation_generation") is not True
    ):
        findings.append("preactivation_chain_invalid")
    if watchers != protocol["forward_health_gate"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    if not _lease_inactive():
        findings.append("shared_api_lease_active")
    if runners:
        findings.append("v24775_runner_already_active")
    if not _pristine((ACTIVATION, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24775_visible_entity_fair_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "package_build_sha256": sha256(ROOT / PACKAGE_BUILD),
        "preaudit_sha256": sha256(ROOT / PREAUDIT),
        "protected_watchers": watchers,
        "active_runners": runners,
        "private_population_truth_provenance_quality_or_evaluator_opened_or_hashed": False,
        "network_model_search_fetch_benchmark_or_evaluator_called": False,
        "authorization": {
            "execution_start_generation": not findings,
            "one_external_forward_launch": False,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


def activate() -> dict[str, Any]:
    _clean_remote()
    _validate_package()
    value = _activation_value()
    if value["findings"]:
        raise RuntimeError("V2.47.75 activation rejected")
    return value


def _start_value(*, now: int | None = None) -> dict[str, Any]:
    _validate_package()
    protocol = _validate_protocol()
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.75 start requires clean pushed HEAD")
    audit = _read(ROOT / PREAUDIT)
    activation = _read(ROOT / ACTIVATION)
    watchers = protected_watcher_snapshot()
    runners = _active_runners()
    findings: list[str] = []
    if (
        not _sealed(audit, "audit_payload_sha256")
        or not _sealed(activation, "activation_payload_sha256")
        or audit.get("launch_authorized") is not True
        or activation.get("launch_authorized") is not True
        or activation.get("authorization", {}).get("execution_start_generation")
        is not True
        or activation.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or activation.get("package_build_sha256") != sha256(ROOT / PACKAGE_BUILD)
        or activation.get("preaudit_sha256") != sha256(ROOT / PREAUDIT)
    ):
        findings.append("activation_chain_invalid")
    if watchers != protocol["forward_health_gate"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    if not _lease_inactive():
        findings.append("shared_api_lease_active")
    if not _endpoint():
        findings.append("gpt56_endpoint_unreachable")
    if runners:
        findings.append("v24775_runner_already_active")
    if not _pristine((EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24775_visible_entity_fair_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "authorized" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "package_build_sha256": sha256(ROOT / PACKAGE_BUILD),
        "preaudit_sha256": sha256(ROOT / PREAUDIT),
        "activation_sha256": sha256(ROOT / ACTIVATION),
        "protected_watchers": watchers,
        "active_runners": runners,
        "first_network_model_search_or_fetch_effect_started": False,
        "private_population_truth_provenance_quality_or_evaluator_opened_or_hashed": False,
        "authorization": {
            "one_external_forward_launch": not findings,
            "private_truth_or_quality_surface_open": False,
            "evaluator": False,
            "paired_dev64": False,
            "exact220": False,
        },
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    return value


def start() -> dict[str, Any]:
    _clean_remote()
    _validate_package()
    value = _start_value()
    if value["findings"]:
        raise RuntimeError("V2.47.75 execution start rejected")
    return value


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit", "activate", "start"))
    args = parser.parse_args()
    function, relative = {
        "audit": (preaudit, PREAUDIT),
        "activate": (activate, ACTIVATION),
        "start": (start, EXECUTION_START),
    }[args.command]
    value = function()
    _publish(ROOT / relative, value)
    print(
        json.dumps(
            {
                "path": str(relative),
                "audit_valid": value.get("audit_valid"),
                "launch_authorized": value.get("launch_authorized"),
                "findings": value.get("findings"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
