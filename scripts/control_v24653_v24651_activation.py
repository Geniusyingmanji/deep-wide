#!/usr/bin/env python3
"""Append-only staged activation control for the frozen V2.46.51 protocol.

The V2.46.51 protocol intentionally grants no preactivation or launch
authority.  This successor control may advance it only through three separately
published, exact-SHA-bound stages: preactivation audit, activation, and
execution start.  The first two stages authorize only the next control stage;
only a valid execution-start artifact authorizes the single frozen forward.

No stage imports, opens, hashes, or validates the evaluator-only population,
gold, provenance, or evaluator.  No stage calls a model, search provider,
fetcher, benchmark, or evaluator.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24651_ror_external_contract import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    OUTPUT_ROOT,
    PREAUDIT,
    PROTOCOL,
    PROTOCOL_ID,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts import audit_v24495_targeted_conversion_projection_build as common  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)


DATE = "20260806"
CONTROL_BUILD = Path(
    f"results/v24653_v24651_activation_control_build_audit_v1_{DATE}.json"
)
PACKAGE_BUILD = Path(f"results/v24652_external_package_build_audit_v1_{DATE}.json")
FORWARD_FILES = (
    Path("src/deepwide_agent/v24644_primary_identity_pair_runtime.py"),
    Path("src/deepwide_agent/v24648_unknown_target_structured_runtime.py"),
    Path("src/deepwide_agent/v24651_ror_external_contract.py"),
    Path("scripts/run_v24651_ror_task.py"),
    Path("scripts/run_v24651_unknown_target_structured.py"),
    Path("scripts/audit_v24651_unknown_target_forward.py"),
)
CONTROL_TESTS = (
    (Path("tests/test_v24648_unknown_target_structured_runtime.py"), 6, 180),
    (Path("tests/test_v24651_forward_package.py"), 5, 180),
    (Path("tests/test_control_v24653_v24651_activation.py"), 8, 120),
    (
        Path("tests/test_audit_v24653_v24651_activation_control_build.py"),
        5,
        120,
    ),
)
EXPECTED_FOCUSED_TESTS = 24
RUNNER_MARKERS = (
    "scripts/run_v24651_unknown_target_structured.py",
    "scripts/run_v24651_ror_task.py",
)
FORBIDDEN_FORWARD_MARKERS = (
    "evaluation/",
    "v24651_ror_external_evaluator",
    "v24650_ror_population_private",
    "v24651_ror_gold_v1",
    "v24651_ror_gold_provenance",
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
        raise RuntimeError("V2.46.53 control requires clean HEAD == target/main")


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.53 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.53 expected object")
    return value


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _validate_protocol() -> dict[str, Any]:
    value = _read(ROOT / PROTOCOL)
    manifest = value.get("dependency_manifest")
    authorization = value.get("authorization", {})
    if (
        value.get("role") != "v24651_unknown_target_structured_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or not _sealed(value, "protocol_sha256")
        or not isinstance(manifest, dict)
        or value.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or any(sha256(ROOT / path) != digest for path, digest in manifest.items())
        or value.get("task_contract", {}).get("runtime_input_keys")
        != ["opaque_id", "question"]
        or value.get("task_contract", {}).get("selected_tasks") != 12
        or value.get("task_contract", {}).get("selected_arm_predictions") != 24
        or value.get("execution", {}).get(
            "one_wave_no_resume_retry_skip_or_selective_rerun"
        )
        is not True
        or value.get("execution", {}).get("failure_as_zero") is not True
        or authorization
        != {
            "protocol_published": True,
            "preactivation_audit": False,
            "activation": False,
            "execution_start": False,
            "one_external_forward_launch": False,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
    ):
        raise RuntimeError("V2.46.53 protocol drifted")
    return value


def _validate_package_build() -> dict[str, Any]:
    value = _read(ROOT / PACKAGE_BUILD)
    if (
        value.get("role") != "v24652_external_package_build_audit"
        or not _sealed(value, "audit_payload_sha256")
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get("external_protocol_publication")
        is not True
        or value.get("authorization", {}).get("activation_or_launch") is not False
        or value.get("label_blind_audit", {}).get("runtime_input_contract")
        != ["opaque_id", "question"]
        or value.get("label_blind_audit", {}).get("passed") is not True
    ):
        raise RuntimeError("V2.46.53 package build drifted")
    return value


def _validate_control_build() -> dict[str, Any]:
    value = _read(ROOT / CONTROL_BUILD)
    if (
        value.get("role") != "v24653_v24651_activation_control_build_audit"
        or not _sealed(value, "audit_payload_sha256")
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get("preactivation_audit_generation")
        is not True
        or value.get("authorization", {}).get("activation_or_launch") is not False
        or value.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or value.get("package_build_sha256") != sha256(ROOT / PACKAGE_BUILD)
    ):
        raise RuntimeError("V2.46.53 control build drifted")
    return value


def _future_pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _forward_findings() -> tuple[list[str], list[str], list[str]]:
    accesses: list[str] = []
    imports: list[str] = []
    literals: list[str] = []
    for path in FORWARD_FILES:
        current_accesses, current_imports = common.ast_findings(path)
        accesses.extend(current_accesses)
        imports.extend(current_imports)
        source = common._ordinary(path).read_text(encoding="utf-8")
        tree = ast.parse(source)
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.extend([node.module or "", *(alias.name for alias in node.names)])
        for name in names:
            if "evaluator" in name.casefold() or "gold" in name.casefold():
                imports.append(f"{path}:{name}")
        for marker in FORBIDDEN_FORWARD_MARKERS:
            if marker in source:
                literals.append(f"{path}:{marker}")
    return sorted(set(accesses)), sorted(set(imports)), sorted(set(literals))


def _run_focused_tests() -> tuple[int, bool]:
    passed = True
    count = 0
    for path, expected, timeout in CONTROL_TESTS:
        count += expected
        passed = common._run_test(path, timeout) and passed
    return count, passed and count == EXPECTED_FOCUSED_TESTS


def _endpoint_reachable() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=1):
            return True
    except OSError:
        return False


def _active_runners(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    try:
        entries = list(proc_root.iterdir())
    except OSError:
        return [{"pid": -1, "marker": "proc_unreadable"}]
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            command = (entry / "cmdline").read_bytes().replace(b"\0", b" ").decode(
                "utf-8", errors="replace"
            )
        except OSError:
            continue
        for marker in RUNNER_MARKERS:
            if marker in command:
                values.append({"pid": int(entry.name), "marker": marker})
    return sorted(values, key=lambda item: (item["pid"], item["marker"]))


def _lease_inactive() -> bool:
    return lease_observation(ROOT, Path("/proc")).get("active") is False


def _preaudit_value(*, now: int | None = None) -> dict[str, Any]:
    protocol = _validate_protocol()
    _validate_package_build()
    control_build = _validate_control_build()
    accesses, imports, literals = _forward_findings()
    test_count, tests_passed = _run_focused_tests()
    endpoint = _endpoint_reachable()
    watchers = protected_watcher_snapshot()
    lease_inactive = _lease_inactive()
    runners = _active_runners()
    pristine = _future_pristine(
        (PREAUDIT, ACTIVATION, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    )
    findings: list[str] = []
    if not tests_passed:
        findings.append("focused_tests_failed_or_count_drifted")
    if accesses:
        findings.append("privileged_field_access_in_forward")
    if imports:
        findings.append("evaluator_or_gold_import_in_forward")
    if literals:
        findings.append("private_or_evaluator_literal_in_forward")
    if not endpoint:
        findings.append("gpt56_endpoint_unreachable")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if watchers != protocol.get("execution", {}).get("protected_watchers"):
        findings.append("protected_watcher_identity_drifted")
    if runners:
        findings.append("v24651_runner_already_active")
    if not pristine:
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24653_v24651_unknown_target_structured_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_manifest_exact": True,
            "package_build_valid": True,
            "control_build_valid": control_build.get("audit_valid") is True,
            "focused_non_evaluator_tests": test_count,
            "focused_non_evaluator_tests_passed": tests_passed,
            "forward_privileged_field_accesses": accesses,
            "forward_evaluator_or_gold_imports": imports,
            "forward_private_or_evaluator_literal_hits": literals,
            "gpt56_endpoint_reachable_without_provider_request": endpoint,
            "shared_api_lease_inactive": lease_inactive,
            "protected_watchers_unchanged": watchers
            == protocol.get("execution", {}).get("protected_watchers"),
            "active_v24651_runners": runners,
            "future_surface_pristine": pristine,
            "private_population_gold_provenance_or_evaluator_opened_or_hashed": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
        },
        "protected_watchers": watchers,
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
        "protocol_file_sha256": sha256(ROOT / PROTOCOL),
        "package_build_sha256": sha256(ROOT / PACKAGE_BUILD),
        "control_build_sha256": sha256(ROOT / CONTROL_BUILD),
        "authorization": {
            "activation_generation": not findings,
            "execution_start_generation": False,
            "one_external_forward_launch": False,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
        },
    }
    value["audit_sha256"] = payload_sha256(value)
    return value


def preaudit() -> dict[str, Any]:
    _clean_remote()
    value = _preaudit_value()
    if value["findings"]:
        raise RuntimeError("V2.46.53 preactivation audit rejected")
    return value


def _activation_value(*, now: int | None = None) -> dict[str, Any]:
    protocol = _validate_protocol()
    _validate_control_build()
    audit = _read(ROOT / PREAUDIT)
    findings: list[str] = []
    if (
        audit.get("role")
        != "v24653_v24651_unknown_target_structured_preactivation_audit"
        or not _sealed(audit, "audit_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("launch_authorized") is not True
        or audit.get("protocol_file_sha256") != sha256(ROOT / PROTOCOL)
        or audit.get("authorization", {}).get("activation_generation") is not True
    ):
        findings.append("preactivation_chain_invalid")
    watchers = protected_watcher_snapshot()
    if watchers != protocol.get("execution", {}).get("protected_watchers"):
        findings.append("protected_watcher_identity_drifted")
    if not _lease_inactive():
        findings.append("shared_api_lease_active")
    runners = _active_runners()
    if runners:
        findings.append("v24651_runner_already_active")
    if not _future_pristine(
        (ACTIVATION, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    ):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24653_v24651_unknown_target_structured_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "preaudit_sha256": sha256(ROOT / PREAUDIT),
        "control_build_sha256": sha256(ROOT / CONTROL_BUILD),
        "protected_watchers": watchers,
        "active_v24651_runners": runners,
        "private_population_gold_provenance_or_evaluator_opened_or_hashed": False,
        "network_model_search_fetch_benchmark_or_evaluator_called": False,
        "authorization": {
            "execution_start_generation": not findings,
            "one_external_forward_launch": False,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
        },
    }
    value["activation_sha256"] = payload_sha256(value)
    return value


def activate() -> dict[str, Any]:
    _clean_remote()
    value = _activation_value()
    if value["findings"]:
        raise RuntimeError("V2.46.53 activation rejected")
    return value


def _start_value(*, now: int | None = None) -> dict[str, Any]:
    protocol = _validate_protocol()
    _validate_control_build()
    audit = _read(ROOT / PREAUDIT)
    activation = _read(ROOT / ACTIVATION)
    findings: list[str] = []
    if (
        not _sealed(audit, "audit_sha256")
        or not _sealed(activation, "activation_sha256")
        or audit.get("launch_authorized") is not True
        or activation.get("launch_authorized") is not True
        or activation.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or activation.get("preaudit_sha256") != sha256(ROOT / PREAUDIT)
        or activation.get("authorization", {}).get("execution_start_generation")
        is not True
    ):
        findings.append("activation_chain_invalid")
    watchers = protected_watcher_snapshot()
    if watchers != protocol.get("execution", {}).get("protected_watchers"):
        findings.append("protected_watcher_identity_drifted")
    if not _lease_inactive():
        findings.append("shared_api_lease_active")
    if not _endpoint_reachable():
        findings.append("gpt56_endpoint_unreachable")
    runners = _active_runners()
    if runners:
        findings.append("v24651_runner_already_active")
    if not _future_pristine(
        (EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    ):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24653_v24651_unknown_target_structured_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "authorized" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "preaudit_sha256": sha256(ROOT / PREAUDIT),
        "activation_sha256": sha256(ROOT / ACTIVATION),
        "control_build_sha256": sha256(ROOT / CONTROL_BUILD),
        "protected_watchers": watchers,
        "active_v24651_runners": runners,
        "first_network_model_search_or_fetch_effect_started": False,
        "private_population_gold_provenance_or_evaluator_opened_or_hashed": False,
        "authorization": {
            "one_external_forward_launch": not findings,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
        },
    }
    value["execution_start_sha256"] = payload_sha256(value)
    return value


def start() -> dict[str, Any]:
    _clean_remote()
    value = _start_value()
    if value["findings"]:
        raise RuntimeError("V2.46.53 execution start rejected")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit", "activate", "start"))
    args = parser.parse_args()
    builders = {
        "audit": (preaudit, PREAUDIT),
        "activate": (activate, ACTIVATION),
        "start": (start, EXECUTION_START),
    }
    function, path = builders[args.command]
    value = function()
    _publish(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "audit_valid": value.get("audit_valid"),
                "launch_authorized": value.get("launch_authorized"),
                "findings": value.get("findings"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
