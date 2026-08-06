#!/usr/bin/env python3
"""Append-only staged activation control for frozen V2.46.71."""

from __future__ import annotations

import argparse
import ast
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

from deepwide_agent.v24671_ror_external_contract import (  # noqa: E402
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
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402


DATE = "20260806"
CONTROL_BUILD = Path(
    f"results/v24673_v24671_activation_control_build_audit_v1_{DATE}.json"
)
PACKAGE_BUILD = Path(f"results/v24672_external_package_build_audit_v1_{DATE}.json")
FORWARD_FILES = (
    Path("src/deepwide_agent/v24655_unknown_cell_targeted_runtime.py"),
    Path("src/deepwide_agent/v24659_support_closure_runtime.py"),
    Path("src/deepwide_agent/v24661_support_closure_task_runtime.py"),
    Path("src/deepwide_agent/v24668_visible_surface_information_gain_runtime.py"),
    Path("src/deepwide_agent/v24671_ror_external_contract.py"),
    Path("src/deepwide_agent/v24671_runner_integration.py"),
    Path("scripts/run_v24671_ror_task.py"),
    Path("scripts/run_v24671_information_gain.py"),
    Path("scripts/audit_v24671_forward.py"),
)
CONTROL_TESTS = (
    (Path("tests/test_v24668_visible_surface_information_gain_runtime.py"), 8, 180),
    (Path("tests/test_v24671_forward_package.py"), 6, 180),
    (Path("tests/test_preregister_v24671_information_gain.py"), 5, 120),
    (Path("tests/test_control_v24673_v24671_activation.py"), 8, 120),
    (Path("tests/test_audit_v24673_v24671_activation_control_build.py"), 5, 120),
)
EXPECTED_TESTS = 32
RUNNER_MARKERS = (
    "scripts/run_v24671_information_gain.py",
    "scripts/run_v24671_ror_task.py",
)
FORBIDDEN_MARKERS = (
    "evaluation/",
    "v24671_ror_external_evaluator",
    "v24671_ror_gold_v1",
    "v24671_ror_gold_provenance",
    "v24670_ror_population_private",
)
PRIVILEGED = frozenset(
    {
        "question_type",
        "category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "mapping",
        "score",
        "reward",
        "results.csv",
    }
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _clean_remote() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.46.73 control requires clean pushed HEAD")


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.73 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.73 expected object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _validate_protocol() -> dict[str, Any]:
    value = _read(ROOT / PROTOCOL)
    manifest = value.get("dependency_manifest")
    mechanism = value.get("mechanism", {})
    if (
        value.get("role") != "v24671_information_gain_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or not _sealed(value, "protocol_sha256")
        or value.get("authorization")
        != {
            "preactivation_audit_generation": False,
            "activation_or_launch": False,
            "evaluator": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        or value.get("task_contract", {}).get("runtime_input_keys")
        != ["opaque_id", "question"]
        or mechanism.get(
            "postfreeze_outer_utility_design_requires_positive_epistemic_credit_and_safe_admission"
        )
        is not True
        or mechanism.get("support_threshold_relaxed") is not False
        or mechanism.get(
            "positive_decision_credit_before_safe_change_and_postfreeze_outer_utility"
        )
        is not False
        or not isinstance(manifest, dict)
        or value.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or any(sha256(ROOT / path) != digest for path, digest in manifest.items())
    ):
        raise RuntimeError("V2.46.73 protocol drifted")
    return value


def _validate_package() -> dict[str, Any]:
    value = _read(ROOT / PACKAGE_BUILD)
    if (
        value.get("role") != "v24672_external_package_build_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization")
        != {
            "external_protocol_publication": True,
            "preactivation_audit": False,
            "activation_or_launch": False,
            "evaluator": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.73 package audit drifted")
    return value


def _validate_control_build() -> dict[str, Any]:
    value = _read(ROOT / CONTROL_BUILD)
    if (
        value.get("role") != "v24673_v24671_activation_control_build_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "activation_or_launch": False,
            "evaluator": False,
            "dev64_or_exact220": False,
            "leaderboard_or_sota": False,
        }
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.46.73 control build drifted")
    return value


def _forward_findings() -> tuple[list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    markers: list[str] = []
    for relative in FORWARD_FILES:
        source = (ROOT / relative).read_text(encoding="utf-8")
        markers.extend(
            f"{relative}:{marker}" for marker in FORBIDDEN_MARKERS if marker in source
        )
        tree = ast.parse(source)
        for node in ast.walk(tree):
            key = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                key = node.args[0].value
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value
            if isinstance(key, str) and key.casefold() in PRIVILEGED:
                fields.append(f"{relative}:{node.lineno}:{key}")
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                names = []
            imports.extend(
                f"{relative}:{name}"
                for name in names
                if any(token in name.casefold() for token in ("external_evaluator", "gold"))
            )
    return sorted(fields), sorted(imports), sorted(markers)


def _run_tests() -> tuple[int, bool]:
    observed = 0
    passed = True
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
            timeout=timeout,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        count = int(match.group(1)) if match else 0
        observed += count
        passed = passed and completed.returncode == 0 and count == expected
    return observed, passed and observed == EXPECTED_TESTS


def _endpoint() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=0.5):
            return True
    except OSError:
        return False


def _lease_inactive() -> bool:
    return lease_observation(ROOT, Path("/proc")).get("active") is False


def _active_runners(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            command = (
                (entry / "cmdline")
                .read_bytes()
                .replace(b"\0", b" ")
                .decode(errors="replace")
            )
        except OSError:
            continue
        for marker in RUNNER_MARKERS:
            if marker in command:
                output.append({"pid": int(entry.name), "marker": marker})
                break
    return sorted(output, key=lambda value: value["pid"])


def _pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


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


def _preaudit_value(*, now: int | None = None) -> dict[str, Any]:
    protocol = _validate_protocol()
    _validate_package()
    _validate_control_build()
    fields, imports, markers = _forward_findings()
    count, tests_passed = _run_tests()
    watchers = protected_watcher_snapshot()
    runners = _active_runners()
    endpoint_reachable = _endpoint()
    lease_inactive = _lease_inactive()
    pristine = _pristine(
        (PREAUDIT, ACTIVATION, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    )
    findings: list[str] = []
    if not tests_passed:
        findings.append("focused_tests_failed")
    if fields:
        findings.append("privileged_forward_field_access")
    if imports:
        findings.append("evaluator_or_gold_import_in_forward")
    if markers:
        findings.append("private_or_evaluator_marker_in_forward")
    if not endpoint_reachable:
        findings.append("gpt56_endpoint_unreachable")
    if not lease_inactive:
        findings.append("shared_api_lease_active")
    if runners:
        findings.append("v24671_runner_already_active")
    if not pristine:
        findings.append("future_surface_not_pristine")
    if watchers != protocol["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24673_v24671_information_gain_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "focused_test_count": count,
            "focused_tests_passed": tests_passed,
            "forward_label_blind": not fields and not imports and not markers,
            "gpt56_endpoint_reachable_without_api_request": endpoint_reachable,
            "shared_api_lease_inactive": lease_inactive,
            "active_runners": runners,
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
        raise RuntimeError("V2.46.73 preaudit rejected")
    return value


def _activation_value(*, now: int | None = None) -> dict[str, Any]:
    protocol = _validate_protocol()
    _validate_control_build()
    audit = _read(ROOT / PREAUDIT)
    watchers = protected_watcher_snapshot()
    runners = _active_runners()
    findings: list[str] = []
    if (
        audit.get("role") != "v24673_v24671_information_gain_preactivation_audit"
        or not _sealed(audit, "audit_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("authorization", {}).get("activation_generation") is not True
        or audit.get("protocol_file_sha256") != sha256(ROOT / PROTOCOL)
        or audit.get("package_build_sha256") != sha256(ROOT / PACKAGE_BUILD)
        or audit.get("control_build_sha256") != sha256(ROOT / CONTROL_BUILD)
    ):
        findings.append("preactivation_chain_invalid")
    if watchers != protocol["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    if not _lease_inactive():
        findings.append("shared_api_lease_active")
    if runners:
        findings.append("v24671_runner_already_active")
    if not _pristine(
        (ACTIVATION, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    ):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24673_v24671_information_gain_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "preaudit_sha256": sha256(ROOT / PREAUDIT),
        "control_build_sha256": sha256(ROOT / CONTROL_BUILD),
        "protected_watchers": watchers,
        "active_runners": runners,
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
        raise RuntimeError("V2.46.73 activation rejected")
    return value


def _start_value(*, now: int | None = None) -> dict[str, Any]:
    protocol = _validate_protocol()
    _validate_control_build()
    audit = _read(ROOT / PREAUDIT)
    activation = _read(ROOT / ACTIVATION)
    watchers = protected_watcher_snapshot()
    runners = _active_runners()
    findings: list[str] = []
    if (
        not _sealed(audit, "audit_sha256")
        or not _sealed(activation, "activation_sha256")
        or audit.get("launch_authorized") is not True
        or activation.get("launch_authorized") is not True
        or activation.get("authorization", {}).get("execution_start_generation")
        is not True
        or activation.get("protocol_sha256") != sha256(ROOT / PROTOCOL)
        or activation.get("preaudit_sha256") != sha256(ROOT / PREAUDIT)
        or activation.get("control_build_sha256") != sha256(ROOT / CONTROL_BUILD)
    ):
        findings.append("activation_chain_invalid")
    if watchers != protocol["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    if not _lease_inactive():
        findings.append("shared_api_lease_active")
    if not _endpoint():
        findings.append("gpt56_endpoint_unreachable")
    if runners:
        findings.append("v24671_runner_already_active")
    if not _pristine((EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)):
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24673_v24671_information_gain_execution_start",
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
        "active_runners": runners,
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
        raise RuntimeError("V2.46.73 start rejected")
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
