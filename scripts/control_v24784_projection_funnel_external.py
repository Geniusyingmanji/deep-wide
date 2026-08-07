#!/usr/bin/env python3
"""Three-stage, fail-closed control for the V2.47.84 mechanism forward.

The commands only create authorization artifacts.  They never launch a
forward and have no evaluator or private-population capability.  Every stage
validates the frozen package and its complete source manifest before probing
the local endpoint, shared lease, watcher, or runner state.
"""

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

from deepwide_agent import v24784_projection_funnel_execution_contract as contract  # noqa: E402
from scripts import audit_v24784_projection_funnel_package as package_audit  # noqa: E402
from scripts import preregister_v24784_projection_funnel_external as protocol_module  # noqa: E402


FORWARD_SOURCES = (
    Path("src/deepwide_agent/v24784_projection_funnel_integration.py"),
    Path("src/deepwide_agent/v24784_projection_funnel_execution_contract.py"),
    Path("scripts/run_v24784_projection_funnel_task.py"),
    Path("scripts/run_v24784_projection_funnel_external.py"),
)
CONTROL_TESTS = (
    (Path("tests/test_v24784_projection_funnel_execution_contract.py"), 6, 180),
    (Path("tests/test_v24784_projection_funnel_package.py"), 7, 180),
    (Path("tests/test_v24784_projection_funnel_integration.py"), 7, 180),
    (Path("tests/test_audit_v24784_projection_funnel_package.py"), 7, 180),
    (Path("tests/test_v24784_projection_funnel_control.py"), 9, 180),
    (Path("tests/test_audit_v24784_projection_funnel_forward.py"), 8, 180),
)
EXPECTED_CONTROL_TESTS = 44
RUNNER_MARKERS = (
    "scripts/run_v24784_projection_funnel_external.py",
    "scripts/run_v24784_projection_funnel_task.py",
)
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
    "population_" + "private",
    "private_" + "truth.json",
    "evaluator_" + "mapping",
    "outputs/v24780_" + "staged_fallback_external",
)
SECRET_PREFIXES = ("gh" + "p_", "github_" + "pat_", "tvly-" + "dev-", "s" + "k-")
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    + "|".join(re.escape(value) for value in SECRET_PREFIXES)
    + r")[A-Za-z0-9_-]{16,}"
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _clean_remote() -> None:
    if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git(
        "rev-parse", "target/main"
    ):
        raise RuntimeError("V2.47.84 control requires clean pushed HEAD")


def _ordinary(path: Path) -> Path:
    target = path.resolve(strict=False)
    if (
        path.is_symlink()
        or not path.is_file()
        or not target.is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.47.84 control expected ordinary object: {path}")
    return path


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.84 control expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _validate_protocol() -> dict[str, Any]:
    value = _read(ROOT / contract.PROTOCOL)
    tasks = contract.task_vector()
    if (
        protocol_module.validate_protocol(value) != value
        or value.get("role")
        != "v24784_projection_funnel_external_preregistration"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("task_contract", {}).get("runtime_input_keys")
        != ["opaque_id", "question"]
        or value.get("task_contract", {}).get("task_count") != 8
        or value.get("task_contract", {}).get("opaque_id_vector_sha256")
        != contract.payload_sha256([task["opaque_id"] for task in tasks])
        or value.get("task_contract", {}).get("visible_question_vector_sha256")
        != contract.payload_sha256([task["question"] for task in tasks])
        or value.get("base_runtime_effect_envelope", {}).get("task_executors") != 8
        or value.get("base_runtime_effect_envelope", {}).get(
            "global_model_slot_cap"
        )
        != 8
        or value.get("base_runtime_effect_envelope", {}).get(
            "maximum_physical_fetches_per_task"
        )
        != 10
        or value.get("base_runtime_effect_envelope", {}).get(
            "failed_url_retry_cap_per_task"
        )
        != 0
        or value.get("base_runtime_effect_envelope", {}).get(
            "experiment_level_resume_retry_skip_or_selective_rerun"
        )
        is not False
        or value.get("mechanism_gate_before_private_truth", {}).get(
            "cross_task_aggregate_cooccurrence_may_substitute_for_task_local_joint"
        )
        is not False
        or value.get("authorization", {}).get("one_external_forward_launch")
        is not False
        or value.get("authorization", {}).get("quality_or_evaluator_surface_open")
        is not False
        or not _sealed(value, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.47.84 protocol drifted")
    return value


def _validate_package() -> dict[str, Any]:
    """Validate package and source manifest before any mutable state probe."""

    value = _read(ROOT / contract.PACKAGE_BUILD)
    package_audit.validate_audit(value)
    if (
        value.get("role") != "v24784_projection_funnel_package_audit"
        or value.get("protocol_id") != contract.PROTOCOL_ID
        or value.get("audit_valid") is not True
        or value.get("findings") != []
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
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.47.84 package audit drifted")
    return value


def _forward_findings() -> tuple[list[str], list[str], list[str], list[str]]:
    fields: list[str] = []
    imports: list[str] = []
    markers: list[str] = []
    secrets: list[str] = []
    for relative in FORWARD_SOURCES:
        path = ROOT / relative
        if relative.is_absolute() or ".." in relative.parts or path.is_symlink():
            raise RuntimeError("V2.47.84 forward source path drifted")
        source = path.read_text(encoding="utf-8")
        markers.extend(
            f"{relative}:{marker}"
            for marker in FORBIDDEN_FORWARD_MARKERS
            if marker in source
        )
        if SECRET.search(source):
            secrets.append(str(relative))
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
    return tuple(
        sorted(set(values)) for values in (fields, imports, markers, secrets)
    )  # type: ignore[return-value]


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
    for path, expected, timeout_seconds in CONTROL_TESTS:
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
            timeout=timeout_seconds,
            check=False,
        )
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        observed = int(match.group(1)) if match else 0
        rows.append(
            {
                "path": str(path),
                "expected": expected,
                "observed": observed,
                "passed": completed.returncode == 0 and observed == expected,
            }
        )
    total = sum(row["observed"] for row in rows)
    return total, all(row["passed"] for row in rows) and total == EXPECTED_CONTROL_TESTS, rows


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


def _active_runners() -> list[int]:
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
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in RUNNER_MARKERS)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def _pristine(paths: tuple[Path, ...]) -> bool:
    return all(
        not (ROOT / path).exists() and not (ROOT / path).is_symlink()
        for path in paths
    )


def _watchers_match(protocol: Mapping[str, Any], watchers: list[dict[str, Any]]) -> bool:
    return watchers == protocol.get("forward_health_gate", {}).get("protected_watchers")


PREAUTH = {
    "activation_generation": True,
    "execution_start_generation": False,
    "one_external_forward_launch": False,
    "private_truth_or_quality_surface_open": False,
    "evaluator": False,
    "paired_dev64": False,
    "exact220": False,
}
ACTIVATION_AUTH = {
    "execution_start_generation": True,
    "one_external_forward_launch": False,
    "private_truth_or_quality_surface_open": False,
    "evaluator": False,
    "paired_dev64": False,
    "exact220": False,
}
START_AUTH = {
    "one_external_forward_launch": True,
    "private_truth_or_quality_surface_open": False,
    "evaluator": False,
    "paired_dev64": False,
    "exact220": False,
}
SOURCE_POLICY = {
    "v24780_output_prediction_task_result_page_or_visible_task_opened_or_hashed": False,
    "v24783_private_population_truth_provenance_or_quality_opened_or_hashed": False,
    "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    "credential_read_hashed_persisted_or_emitted": False,
    "network_model_search_fetch_benchmark_forward_or_evaluator_called": False,
}


def _preaudit_value(*, now: int | None = None) -> dict[str, Any]:
    package = _validate_package()
    protocol = _validate_protocol()
    _clean_remote()
    fields, imports, markers, secrets = _forward_findings()
    observed, tests_passed, suites = _run_tests()
    watchers = contract.protected_watcher_snapshot()
    endpoint = _endpoint()
    lease = _lease_inactive()
    runners = _active_runners()
    pristine = _pristine(
        (
            contract.PREAUDIT,
            contract.ACTIVATION,
            contract.EXECUTION_START,
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.OUTPUT_ROOT,
        )
    )
    findings: list[str] = []
    if not tests_passed:
        findings.append("focused_tests_failed_or_count_drifted")
    if fields:
        findings.append("privileged_forward_field_access")
    if imports:
        findings.append("evaluator_or_gold_import_in_forward")
    if markers:
        findings.append("private_or_old_output_marker_in_forward")
    if secrets:
        findings.append("credential_literal_in_forward")
    if not endpoint:
        findings.append("gpt56_endpoint_unreachable")
    if not lease:
        findings.append("shared_api_lease_active")
    if runners:
        findings.append("v24784_runner_already_active")
    if not pristine:
        findings.append("future_surface_not_pristine")
    if not _watchers_match(protocol, watchers):
        findings.append("protected_watcher_identity_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24784_projection_funnel_preactivation_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "package_build_sha256": contract.sha256(ROOT / contract.PACKAGE_BUILD),
        "package_manifest_sha256": contract.payload_sha256(package["source_manifest"]),
        "checks": {
            "focused_test_count": observed,
            "focused_tests_passed": tests_passed,
            "focused_test_suites": suites,
            "forward_label_blind": not fields and not imports and not markers and not secrets,
            "gpt56_endpoint_reachable_without_provider_request": endpoint,
            "shared_api_lease_inactive": lease,
            "active_runner_pids": runners,
            "future_surface_pristine": pristine,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
        },
        "protected_watchers": watchers,
        "source_policy": dict(SOURCE_POLICY),
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
        "authorization": dict(PREAUTH) if not findings else {**PREAUTH, "activation_generation": False},
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_preaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    if (
        copied.get("role") != "v24784_projection_funnel_preactivation_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("audit_valid") is not True
        or copied.get("launch_authorized") is not True
        or copied.get("findings") != []
        or copied.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or copied.get("package_build_sha256")
        != contract.sha256(ROOT / contract.PACKAGE_BUILD)
        or copied.get("package_manifest_sha256")
        != contract.payload_sha256(_validate_package()["source_manifest"])
        or copied.get("checks", {}).get("focused_test_count") != EXPECTED_CONTROL_TESTS
        or copied.get("checks", {}).get("focused_tests_passed") is not True
        or copied.get("checks", {}).get("forward_label_blind") is not True
        or copied.get("checks", {}).get(
            "gpt56_endpoint_reachable_without_provider_request"
        )
        is not True
        or copied.get("checks", {}).get("shared_api_lease_inactive") is not True
        or copied.get("checks", {}).get("active_runner_pids") != []
        or copied.get("checks", {}).get("future_surface_pristine") is not True
        or copied.get("source_policy") != SOURCE_POLICY
        or copied.get("authorization") != PREAUTH
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.84 preactivation audit drifted")
    return copied


def preaudit() -> dict[str, Any]:
    _clean_remote()
    _validate_package()
    return validate_preaudit(_preaudit_value())


def _activation_value(*, now: int | None = None) -> dict[str, Any]:
    _validate_package()
    protocol = _validate_protocol()
    _clean_remote()
    audit = validate_preaudit(_read(ROOT / contract.PREAUDIT))
    watchers = contract.protected_watcher_snapshot()
    endpoint = _endpoint()
    lease = _lease_inactive()
    runners = _active_runners()
    pristine = _pristine(
        (
            contract.ACTIVATION,
            contract.EXECUTION_START,
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.OUTPUT_ROOT,
        )
    )
    findings: list[str] = []
    if audit.get("authorization") != PREAUTH:
        findings.append("preactivation_chain_invalid")
    if not _watchers_match(protocol, watchers):
        findings.append("protected_watcher_identity_drifted")
    if not endpoint:
        findings.append("gpt56_endpoint_unreachable")
    if not lease:
        findings.append("shared_api_lease_active")
    if runners:
        findings.append("v24784_runner_already_active")
    if not pristine:
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24784_projection_funnel_activation",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "package_build_sha256": contract.sha256(ROOT / contract.PACKAGE_BUILD),
        "preaudit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "protected_watchers": watchers,
        "checks": {
            "gpt56_endpoint_reachable_without_provider_request": endpoint,
            "shared_api_lease_inactive": lease,
            "active_runner_pids": runners,
            "future_surface_pristine": pristine,
            "first_network_model_search_or_fetch_effect_started": False,
        },
        "source_policy": dict(SOURCE_POLICY),
        "findings": findings,
        "launch_authorized": not findings,
        "authorization": dict(ACTIVATION_AUTH)
        if not findings
        else {**ACTIVATION_AUTH, "execution_start_generation": False},
    }
    value["activation_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_activation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("activation_payload_sha256", None)
    if (
        copied.get("role") != "v24784_projection_funnel_activation"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("launch_authorized") is not True
        or copied.get("findings") != []
        or copied.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or copied.get("package_build_sha256")
        != contract.sha256(ROOT / contract.PACKAGE_BUILD)
        or copied.get("preaudit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or copied.get("checks", {}).get(
            "gpt56_endpoint_reachable_without_provider_request"
        )
        is not True
        or copied.get("checks", {}).get("shared_api_lease_inactive") is not True
        or copied.get("checks", {}).get("active_runner_pids") != []
        or copied.get("checks", {}).get("future_surface_pristine") is not True
        or copied.get("checks", {}).get(
            "first_network_model_search_or_fetch_effect_started"
        )
        is not False
        or copied.get("source_policy") != SOURCE_POLICY
        or copied.get("authorization") != ACTIVATION_AUTH
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.84 activation drifted")
    return copied


def activate() -> dict[str, Any]:
    _clean_remote()
    _validate_package()
    return validate_activation(_activation_value())


def _start_value(*, now: int | None = None) -> dict[str, Any]:
    _validate_package()
    protocol = _validate_protocol()
    _clean_remote()
    preaudit_value = validate_preaudit(_read(ROOT / contract.PREAUDIT))
    activation = validate_activation(_read(ROOT / contract.ACTIVATION))
    watchers = contract.protected_watcher_snapshot()
    endpoint = _endpoint()
    lease = _lease_inactive()
    runners = _active_runners()
    pristine = _pristine(
        (
            contract.EXECUTION_START,
            contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT,
            contract.OUTPUT_ROOT,
        )
    )
    findings: list[str] = []
    if preaudit_value.get("authorization") != PREAUTH:
        findings.append("preactivation_chain_invalid")
    if activation.get("authorization") != ACTIVATION_AUTH:
        findings.append("activation_chain_invalid")
    if not _watchers_match(protocol, watchers):
        findings.append("protected_watcher_identity_drifted")
    if not endpoint:
        findings.append("gpt56_endpoint_unreachable")
    if not lease:
        findings.append("shared_api_lease_active")
    if runners:
        findings.append("v24784_runner_already_active")
    if not pristine:
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24784_projection_funnel_execution_start",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "package_build_sha256": contract.sha256(ROOT / contract.PACKAGE_BUILD),
        "preaudit_sha256": contract.sha256(ROOT / contract.PREAUDIT),
        "activation_sha256": contract.sha256(ROOT / contract.ACTIVATION),
        "protected_watchers": watchers,
        "checks": {
            "gpt56_endpoint_reachable_without_provider_request": endpoint,
            "shared_api_lease_inactive": lease,
            "active_runner_pids": runners,
            "future_surface_pristine": pristine,
        },
        "first_network_model_search_or_fetch_effect_started": False,
        "source_policy": dict(SOURCE_POLICY),
        "findings": findings,
        "launch_authorized": not findings,
        "authorization": dict(START_AUTH)
        if not findings
        else {**START_AUTH, "one_external_forward_launch": False},
    }
    value["execution_start_payload_sha256"] = contract.payload_sha256(value)
    return value


def validate_start(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("execution_start_payload_sha256", None)
    if (
        copied.get("role") != "v24784_projection_funnel_execution_start"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("launch_authorized") is not True
        or copied.get("findings") != []
        or copied.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or copied.get("package_build_sha256")
        != contract.sha256(ROOT / contract.PACKAGE_BUILD)
        or copied.get("preaudit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or copied.get("activation_sha256") != contract.sha256(ROOT / contract.ACTIVATION)
        or copied.get("checks", {}).get(
            "gpt56_endpoint_reachable_without_provider_request"
        )
        is not True
        or copied.get("checks", {}).get("shared_api_lease_inactive") is not True
        or copied.get("checks", {}).get("active_runner_pids") != []
        or copied.get("checks", {}).get("future_surface_pristine") is not True
        or copied.get("first_network_model_search_or_fetch_effect_started") is not False
        or copied.get("source_policy") != SOURCE_POLICY
        or copied.get("authorization") != START_AUTH
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.84 execution start drifted")
    return copied


def start() -> dict[str, Any]:
    _clean_remote()
    _validate_package()
    return validate_start(_start_value())


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit", "activate", "start"))
    args = parser.parse_args()
    if args.command == "audit":
        value, path = preaudit(), contract.PREAUDIT
    elif args.command == "activate":
        value, path = activate(), contract.ACTIVATION
    else:
        value, path = start(), contract.EXECUTION_START
    publish_new(ROOT / path, value)
    print(
        json.dumps(
            {
                "path": str(path),
                "launch_authorized": value["launch_authorized"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
