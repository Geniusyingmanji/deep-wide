#!/usr/bin/env python3
"""One-shot benchmark-external real transport smoke for V2.43.26."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    validate_visible_task,
)
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_parent_receipt,
)
from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_child_with_terminal_receipt,
    run_observed_subprocess,
)
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model_receipt,
)
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
    validate_transport_health,
)
from deepwide_agent.v24320_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from deepwide_agent.v24326_runner_integration import (  # noqa: E402
    build_envelope,
    run_v24326_task,
    validate_envelope,
    validate_observed_bundle,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    _matching,
)


DATE = "20260803"
PROTOCOL_ID = "v24327_neutral_real_shared_prefix_transport_smoke_v1"
PROTOCOL = Path(f"results/v24327_neutral_transport_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24327_neutral_transport_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24327_neutral_transport_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24327_neutral_transport_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24327_neutral_transport_probe_v1_{DATE}.json")
DECISION = Path(f"results/v24327_neutral_transport_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24327_neutral_transport_postresult_audit_v1_{DATE}.json")
PARENT = Path(f"results/v24326_runner_integration_build_audit_v1_{DATE}.json")
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24327_neutral_transport_smoke_v1"
LEASE_PURPOSE = "benchmark_external_real_shared_prefix_transport_smoke"
RUNNER_MARKER = "scripts/v24327_neutral_transport_smoke.py"
MODEL_SLOT_CAP = 2
WALL_SECONDS = 180
PARENT_TIMEOUT_SECONDS = 200
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 9878
SOURCE_FILES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24313_runner_integration.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24326_runner_integration.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/deepwide_api_lease.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/v24327_neutral_transport_smoke.py",
    "tests/test_v24327_neutral_transport_smoke.py",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
URL = re.compile(r"https?://", re.IGNORECASE)
CONTENT_LITERALS = (
    "Python Software Foundation",
    "Linux Foundation",
    "Apache Software Foundation",
    "Headquarters country",
)
LIMITS = ScoreFirstLimits(
    wall_seconds=WALL_SECONDS,
    model_calls=3,
    search_queries=4,
    fetch_targets=10,
    search_results_per_query=3,
    evidence_chars=60_000,
    page_chars=5_000,
    plan_output_tokens=4_000,
    synthesis_output_tokens=30_000,
    repair_output_tokens=12_000,
)
GATES = {
    "maximum_wall_seconds": PARENT_TIMEOUT_SECONDS,
    "required_parent_taxonomy": "success",
    "required_result_status": "completed",
    "required_effect_accounting_complete": True,
    "required_prefix_status": "frozen",
    "required_prefix_producer_execution_count": 1,
    "required_repeated_upstream_effects": 0,
    "required_logical_model_admissions": 3,
    "required_provider_model_requests": 3,
    "minimum_provider_model_attempts": 3,
    "required_pre_provider_model_rejections": 0,
    "required_slot_acquisitions": 3,
    "required_slot_timeouts": 0,
    "required_core_logical_queries": 4,
    "minimum_search_provider_effects": 1,
    "maximum_search_provider_effects": 2,
    "required_core_fetch_targets": 7,
    "required_reserve_fetch_targets": 3,
    "minimum_core_usable_pages": 1,
    "minimum_reserve_usable_pages": 1,
    "maximum_hard_fetch_deadline_failures": 3,
    "maximum_fetch_helper_failures": 5,
    "required_deadline_exhausted": False,
}


def neutral_task() -> dict[str, str]:
    value = {
        "opaque_id": f"task_{0x243027:024x}",
        "question": (
            "Use public web sources to return one Markdown table about these three "
            "organizations: Python Software Foundation, Linux Foundation, and Apache "
            "Software Foundation. The column names are: Organization, Headquarters "
            "country. Return one table only."
        ),
    }
    return validate_visible_task(value)


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError("V2.43.27 expected an ordinary repository file")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.27 expected a JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.43.27 credential literal in source surface")
        output[relative] = sha256(path)
    return output


def _port_listening() -> bool:
    try:
        with socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=0.5):
            return True
    except OSError:
        return False


def _parent(root: Path) -> dict[str, Any]:
    value = _read(root, PARENT)
    if (
        value.get("role") != "v24326_runner_integration_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(
            "one_benchmark_external_neutral_transport_smoke_design"
        )
        is not True
        or value.get("authorization", {}).get("neutral_transport_smoke_launch")
        is not False
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.27 parent audit drifted")
    return value


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    _parent(root)
    LIMITS.validate()
    validate_visible_task(neutral_task())
    if require_pristine:
        present = [
            str(path)
            for path in (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
            if (root / path).exists() or (root / path).is_symlink()
        ]
        if present:
            raise RuntimeError(f"V2.43.27 future surface is not pristine: {present}")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24327_neutral_transport_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "scope": "one_benchmark_external_real_gpt_search_fetch_shared_prefix_task",
        "task_contract": {
            "task_count": 1,
            "synthetic_identifier_not_selected_from_benchmark": True,
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "task_validated_before_activation": True,
            "task_identifier_question_query_url_page_prediction_response_or_hash_persisted": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_opened": False,
        },
        "provider": {
            "proxy_url": f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "service_tier": "priority",
            "timeout_seconds": WALL_SECONDS,
            "max_retries": 2,
        },
        "search": {
            "same_keyless_proxy": True,
            "batch_size": 8,
            "workers": 1,
            "context_size": "medium",
            "max_output_tokens": 7_000,
            "fetch_workers": 8,
            "fetch_timeout_seconds": 20,
            "hard_fetch_deadline_seconds": 25,
            "server_auto_fetch_enabled": False,
        },
        "budget": {
            "wall_seconds": WALL_SECONDS,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "model_calls": LIMITS.model_calls,
            "search_queries": LIMITS.search_queries,
            "fetch_targets": LIMITS.fetch_targets,
            "core_fetch_targets": 7,
            "reserve_fetch_targets": 3,
            "model_slot_cap": MODEL_SLOT_CAP,
            "fixed_single_task_no_resume_or_retry": True,
        },
        "gates": dict(GATES),
        "lease": {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_single_owner": True,
        },
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "task_identifier_question_query_url_page_prediction_response_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "one_neutral_transport_smoke_design": True,
            "neutral_transport_smoke_launch": False,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    validate_protocol(root, value=value)
    return value


def validate_protocol(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else _read(root, PROTOCOL)
    manifest = protocol.get("surface_manifest")
    authorization = protocol.get("authorization")
    source = protocol.get("source_policy")
    if (
        protocol.get("role") != "v24327_neutral_transport_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope")
        != "one_benchmark_external_real_gpt_search_fetch_shared_prefix_task"
        or protocol.get("gates") != GATES
        or protocol.get("budget", {}).get("model_slot_cap") != MODEL_SLOT_CAP
        or protocol.get("budget", {}).get("core_fetch_targets") != 7
        or protocol.get("budget", {}).get("reserve_fetch_targets") != 3
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or authorization.get("one_neutral_transport_smoke_design") is not True
        or any(
            enabled
            for key, enabled in authorization.items()
            if key != "one_neutral_transport_smoke_design"
        )
        or protocol.get("parent")
        != {"path": str(PARENT), "sha256": sha256(root / PARENT)}
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.27 protocol drifted")
    _parent(root)
    validate_visible_task(neutral_task())
    return protocol


def _run_test() -> bool:
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
            "test_v24327_neutral_transport_smoke.py",
        ],
        cwd=ROOT,
        env={
            "HOME": str(Path.home()),
            "USER": os.environ.get("USER", "azureuser"),
            "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONSAFEPATH": "1",
        },
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=180,
        check=False,
    )
    return completed.returncode == 0


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    future = (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    pristine = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in future
    )
    tests_passed = _run_test()
    port = _port_listening()
    lease = lease_observation(root, Path("/proc"))
    watchers = protected_watcher_snapshot()
    findings: list[str] = []
    if not pristine:
        findings.append("future_surface_not_pristine")
    if not tests_passed:
        findings.append("focused_tests_failed")
    if not port:
        findings.append("keyless_proxy_not_listening")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24327_neutral_transport_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": True,
            "surface_manifest_exact": True,
            "focused_tests_passed": tests_passed,
            "synthetic_visible_task_validated": True,
            "keyless_proxy_listening_without_api_request": port,
            "shared_api_lease_inactive": lease.get("active") is False,
            "future_surface_pristine": pristine,
            "benchmark_or_evaluator_surface_authorized": False,
        },
        "protected_watchers": watchers,
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
        "provenance": {
            "parent_sha256": sha256(root / PARENT),
            "protocol_sha256": sha256(root / PROTOCOL),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
        "authorization": {
            "one_neutral_transport_smoke_launch": not findings,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_preaudit(root, value=value)
    return value


def validate_preaudit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    audit = dict(value) if value is not None else _read(root, PREAUDIT)
    if (
        audit.get("role") != "v24327_neutral_transport_preactivation_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or audit.get("findings") != []
        or audit.get("audit_valid") is not True
        or audit.get("launch_authorized") is not True
        or audit.get("checks", {}).get("focused_tests_passed") is not True
        or audit.get("checks", {}).get("keyless_proxy_listening_without_api_request")
        is not True
        or audit.get("provenance", {}).get("protocol_sha256")
        != sha256(root / PROTOCOL)
        or audit.get("protected_watchers") != protected_watcher_snapshot()
        or audit.get("authorization", {}).get("one_neutral_transport_smoke_launch")
        is not True
        or any(
            enabled
            for key, enabled in audit.get("authorization", {}).items()
            if key != "one_neutral_transport_smoke_launch"
        )
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.27 preactivation audit drifted")
    validate_protocol(root)
    return audit


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    audit = validate_preaudit(root)
    lease = lease_observation(root, Path("/proc"))
    future = (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    findings: list[str] = []
    if any((root / path).exists() or (root / path).is_symlink() for path in future):
        findings.append("activation_or_execution_surface_not_pristine")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24327_neutral_transport_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": audit["protected_watchers"],
        "shared_api_lease_active_before_activation": lease.get("active") is True,
        "local_proxy_listening_without_api_request": True,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "authorization": {
            "one_neutral_transport_smoke_launch": not findings,
            "benchmark_launch": False,
            "additional_dev64_or_exact220": False,
            "evaluator": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    validate_activation(root, value=value)
    return value


def validate_activation(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    activation = dict(value) if value is not None else _read(root, ACTIVATION)
    if (
        activation.get("role") != "v24327_neutral_transport_activation"
        or activation.get("protocol_id") != PROTOCOL_ID
        or activation.get("status") != "active"
        or activation.get("findings") != []
        or activation.get("launch_authorized") is not True
        or activation.get("protocol_sha256") != sha256(root / PROTOCOL)
        or activation.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or activation.get("protected_watchers") != protected_watcher_snapshot()
        or activation.get("network_model_search_fetch_evaluator_or_api_called")
        is not False
        or activation.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or activation.get("authorization", {}).get("one_neutral_transport_smoke_launch")
        is not True
        or any(
            enabled
            for key, enabled in activation.get("authorization", {}).items()
            if key != "one_neutral_transport_smoke_launch"
        )
        or not _sealed(activation, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.43.27 activation drifted")
    validate_preaudit(root)
    return activation


def _git_output(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def build_execution_start(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    activation = validate_activation(root)
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.43.27 execution surface is not pristine")
    head = _git_output(root, "rev-parse", "HEAD")
    remote = _git_output(root, "rev-parse", "target/main")
    lease = lease_observation(root, Path("/proc"))
    findings: list[str] = []
    if head != remote:
        findings.append("activation_commit_not_pushed")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24327_neutral_transport_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "ready" if not findings else "rejected",
        "findings": findings,
        "execution_authorized": not findings,
        "activation_base_commit": head,
        "target_main_at_start": remote,
        "protocol_sha256": sha256(root / PROTOCOL),
        "activation_sha256": sha256(root / ACTIVATION),
        "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        "protected_watchers": activation["protected_watchers"],
        "shared_api_lease_active_before_execution_start": lease.get("active") is True,
        "api_called_before_execution_start": False,
        "runtime_input_exactly_opaque_id_and_question": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_or_evaluator_authorized": False,
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    validate_execution_start(root, value=value)
    return value


def validate_execution_start(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    start = dict(value) if value is not None else _read(root, EXECUTION_START)
    if (
        start.get("role") != "v24327_neutral_transport_execution_start"
        or start.get("protocol_id") != PROTOCOL_ID
        or start.get("status") != "ready"
        or start.get("findings") != []
        or start.get("execution_authorized") is not True
        or start.get("protocol_sha256") != sha256(root / PROTOCOL)
        or start.get("activation_sha256") != sha256(root / ACTIVATION)
        or start.get("protected_watchers") != protected_watcher_snapshot()
        or start.get("api_called_before_execution_start") is not False
        or start.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
        is not False
        or start.get("benchmark_or_evaluator_authorized") is not False
        or not _sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.43.27 execution-start drifted")
    validate_activation(root)
    return start


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _child(args: argparse.Namespace) -> None:
    output_root = Path(args.output_root)
    directory = Path(args.directory)
    result_path = directory / "result.json"
    model_path = directory / "model_slot_receipt.json"
    transport_path = directory / "transport_health.json"
    terminal_path = directory / "child_terminal_receipt.json"

    def action() -> None:
        started = time.monotonic()
        deadline = started + WALL_SECONDS
        model = build_deadline_model(
            url=f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            model_name="gpt-5.6-sol",
            reasoning_effort="low",
            service_tier="priority",
            static_timeout_seconds=WALL_SECONDS,
            max_retries=2,
            slot_directory=Path(args.slots),
            output_root=output_root,
            slot_cap=MODEL_SLOT_CAP,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5.0,
            minimum_attempt_seconds=0.05,
        )
        search = DeadlineAwareNativeSearchClient(
            f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            "gpt-5.6-sol",
            reasoning_effort="low",
            service_tier="priority",
            timeout=WALL_SECONDS,
            max_retries=2,
            max_workers=1,
            batch_size=8,
            search_context_size="medium",
            max_output_tokens=7_000,
            fetch_pages=False,
            fetch_workers=8,
            fetch_timeout=20,
            max_page_chars=LIMITS.page_chars,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5.0,
            minimum_attempt_seconds=0.05,
        )
        outcome = run_v24326_task(
            neutral_task(),
            model=model,
            search=search,
            limits=LIMITS,
            monotonic=time.monotonic,
        )
        _write_new(model_path, outcome.model_slot_receipt)
        _write_new(transport_path, outcome.transport_health)
        _write_new(result_path, build_envelope(outcome))

    run_child_with_terminal_receipt(
        output_root=output_root,
        directory=directory,
        action=action,
        result_name=result_path.name,
        model_receipt_name=model_path.name,
        transport_receipt_name=transport_path.name,
        terminal_name=terminal_path.name,
    )


def _environment() -> dict[str, str]:
    return {
        "HOME": str(Path.home()),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def _project(
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any] | None,
    *,
    wall_seconds: float,
) -> dict[str, Any]:
    validate_parent_receipt(parent)
    result = envelope.get("result") if isinstance(envelope, Mapping) else None
    slot = envelope.get("model_slot_receipt") if isinstance(envelope, Mapping) else None
    transport = envelope.get("transport_health") if isinstance(envelope, Mapping) else None
    receipt = (
        result.get("shared_prefix_revision_receipt")
        if isinstance(result, Mapping)
        else None
    )
    prefix = receipt.get("prefix_bundle") if isinstance(receipt, Mapping) else None
    cost = result.get("cost") if isinstance(result, Mapping) else None
    model_cost = cost.get("model") if isinstance(cost, Mapping) else None
    search_cost = cost.get("search") if isinstance(cost, Mapping) else None
    value = {
        "artifact_version": 1,
        "role": "v24327_neutral_transport_probe",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "parent_exit": {
            key: parent[key]
            for key in (
                "failure_taxonomy",
                "child_terminal_receipt_present",
                "child_terminal_receipt_valid",
                "result_envelope_present",
                "result_envelope_valid",
                "model_receipt_present",
                "model_receipt_valid",
                "transport_receipt_present",
                "transport_receipt_valid",
            )
        },
        "observed": {
            "result_status": result.get("status") if isinstance(result, Mapping) else None,
            "completion_kind": result.get("completion_kind") if isinstance(result, Mapping) else None,
            "effect_accounting_complete": receipt.get("effect_accounting_complete") if isinstance(receipt, Mapping) else None,
            "prefix_status": receipt.get("prefix_status") if isinstance(receipt, Mapping) else None,
            "prefix_producer_execution_count": prefix.get("producer_execution_count") if isinstance(prefix, Mapping) else None,
            "candidate_identity_handoff": receipt.get("candidate_identity_handoff") if isinstance(receipt, Mapping) else None,
            "proposed_cell_changes": receipt.get("proposed_cell_changes") if isinstance(receipt, Mapping) else None,
            "admitted_cell_changes": receipt.get("admitted_cell_changes") if isinstance(receipt, Mapping) else None,
            "credited_entropy_positive": bool(receipt.get("credited_conditional_entropy_reduction_nats", 0) > 0) if isinstance(receipt, Mapping) else None,
            "logical_model_admissions": receipt.get("logical_model_admissions") if isinstance(receipt, Mapping) else None,
            "provider_model_requests": receipt.get("provider_model_requests") if isinstance(receipt, Mapping) else None,
            "provider_model_attempts": receipt.get("provider_model_attempts") if isinstance(receipt, Mapping) else None,
            "pre_provider_model_rejections": receipt.get("pre_provider_model_rejections") if isinstance(receipt, Mapping) else None,
            "slot_acquisitions": slot.get("acquisitions") if isinstance(slot, Mapping) else None,
            "slot_timeouts": slot.get("slot_timeouts") if isinstance(slot, Mapping) else None,
            "core_logical_queries": receipt.get("core_logical_queries") if isinstance(receipt, Mapping) else None,
            "search_provider_effects": (receipt.get("core_search_provider_effects", 0) + receipt.get("reserve_search_provider_effects", 0)) if isinstance(receipt, Mapping) else None,
            "core_fetch_targets": receipt.get("core_fetch_targets") if isinstance(receipt, Mapping) else None,
            "reserve_fetch_targets": receipt.get("reserve_fetch_targets") if isinstance(receipt, Mapping) else None,
            "core_network_fetch_effects": receipt.get("core_network_fetch_effects") if isinstance(receipt, Mapping) else None,
            "reserve_network_fetch_effects": receipt.get("reserve_network_fetch_effects") if isinstance(receipt, Mapping) else None,
            "core_usable_pages": receipt.get("core_usable_pages") if isinstance(receipt, Mapping) else None,
            "reserve_usable_pages": receipt.get("reserve_usable_pages") if isinstance(receipt, Mapping) else None,
            "repeated_upstream_effects": sum(receipt.get(name, 0) for name in ("repeated_plan_model_effects_by_branches", "repeated_core_search_effects_by_branches", "repeated_core_fetch_effects_by_branches")) if isinstance(receipt, Mapping) else None,
            "model_requests": model_cost.get("requests") if isinstance(model_cost, Mapping) else None,
            "model_attempts": model_cost.get("attempts") if isinstance(model_cost, Mapping) else None,
            "model_total_tokens": model_cost.get("total_tokens") if isinstance(model_cost, Mapping) else None,
            "search_calls": search_cost.get("calls") if isinstance(search_cost, Mapping) else None,
            "search_failures": search_cost.get("failures") if isinstance(search_cost, Mapping) else None,
            "fetch_calls": search_cost.get("fetch_calls") if isinstance(search_cost, Mapping) else None,
            "fetch_failures": search_cost.get("fetch_failures") if isinstance(search_cost, Mapping) else None,
            "search_total_tokens": search_cost.get("total_tokens") if isinstance(search_cost, Mapping) else None,
            "transport_health": dict(transport) if isinstance(transport, Mapping) else None,
            "model_slot_cap": slot.get("slot_cap") if isinstance(slot, Mapping) else None,
        },
        "temporary_execution_directory_remaining": False,
        "task_identifier_question_query_url_page_prediction_response_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "official_evaluator_called": False,
        "resume_retry_skip_or_revaluation": False,
    }
    value["probe_payload_sha256"] = payload_sha256(value)
    validate_projection(value)
    return value


def validate_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "wall_seconds",
        "parent_exit",
        "observed",
        "temporary_execution_directory_remaining",
        "task_identifier_question_query_url_page_prediction_response_or_hash_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "official_evaluator_called",
        "resume_retry_skip_or_revaluation",
        "probe_payload_sha256",
    }
    parent_expected = {
        "failure_taxonomy",
        "child_terminal_receipt_present",
        "child_terminal_receipt_valid",
        "result_envelope_present",
        "result_envelope_valid",
        "model_receipt_present",
        "model_receipt_valid",
        "transport_receipt_present",
        "transport_receipt_valid",
    }
    observed_expected = {
        "result_status",
        "completion_kind",
        "effect_accounting_complete",
        "prefix_status",
        "prefix_producer_execution_count",
        "candidate_identity_handoff",
        "proposed_cell_changes",
        "admitted_cell_changes",
        "credited_entropy_positive",
        "logical_model_admissions",
        "provider_model_requests",
        "provider_model_attempts",
        "pre_provider_model_rejections",
        "slot_acquisitions",
        "slot_timeouts",
        "core_logical_queries",
        "search_provider_effects",
        "core_fetch_targets",
        "reserve_fetch_targets",
        "core_network_fetch_effects",
        "reserve_network_fetch_effects",
        "core_usable_pages",
        "reserve_usable_pages",
        "repeated_upstream_effects",
        "model_requests",
        "model_attempts",
        "model_total_tokens",
        "search_calls",
        "search_failures",
        "fetch_calls",
        "fetch_failures",
        "search_total_tokens",
        "transport_health",
        "model_slot_cap",
    }
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != "v24327_neutral_transport_probe"
        or value.get("protocol_id") != PROTOCOL_ID
        or not isinstance(value.get("parent_exit"), Mapping)
        or set(value["parent_exit"]) != parent_expected
        or not isinstance(value.get("observed"), Mapping)
        or set(value["observed"]) != observed_expected
        or value.get("temporary_execution_directory_remaining") is not False
        or value.get("task_identifier_question_query_url_page_prediction_response_or_hash_persisted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("official_evaluator_called") is not False
        or value.get("resume_retry_skip_or_revaluation") is not False
        or not _sealed(value, "probe_payload_sha256")
    ):
        raise RuntimeError("V2.43.27 projection drifted")
    encoded = json.dumps(value, ensure_ascii=False)
    if (
        OPAQUE.search(encoded)
        or URL.search(encoded)
        or SECRET.search(encoded)
        or any(literal in encoded for literal in CONTENT_LITERALS)
    ):
        raise RuntimeError("V2.43.27 projection contains task content")
    return dict(value)


def _checks(result: Mapping[str, Any], gates: Mapping[str, Any]) -> dict[str, bool]:
    observed = result["observed"]
    parent = result["parent_exit"]
    health = observed.get("transport_health") or {}
    return {
        "wall_seconds": float(result["wall_seconds"]) <= gates["maximum_wall_seconds"],
        "parent_taxonomy": parent["failure_taxonomy"] == gates["required_parent_taxonomy"],
        "all_parent_artifacts_valid": all(parent[name] is True for name in ("child_terminal_receipt_valid", "result_envelope_valid", "model_receipt_valid", "transport_receipt_valid")),
        "result_status": observed["result_status"] == gates["required_result_status"],
        "effect_accounting_complete": observed["effect_accounting_complete"] is gates["required_effect_accounting_complete"],
        "prefix_status": observed["prefix_status"] == gates["required_prefix_status"],
        "prefix_producer_execution_count": observed["prefix_producer_execution_count"] == gates["required_prefix_producer_execution_count"],
        "repeated_upstream_effects": observed["repeated_upstream_effects"] == gates["required_repeated_upstream_effects"],
        "logical_model_admissions": observed["logical_model_admissions"] == gates["required_logical_model_admissions"],
        "provider_model_requests": observed["provider_model_requests"] == gates["required_provider_model_requests"],
        "provider_model_attempts": observed["provider_model_attempts"] >= gates["minimum_provider_model_attempts"],
        "pre_provider_model_rejections": observed["pre_provider_model_rejections"] == gates["required_pre_provider_model_rejections"],
        "slot_acquisitions": observed["slot_acquisitions"] == gates["required_slot_acquisitions"],
        "slot_timeouts": observed["slot_timeouts"] == gates["required_slot_timeouts"],
        "model_conservation": observed["logical_model_admissions"] == observed["slot_acquisitions"] + observed["slot_timeouts"] and observed["provider_model_requests"] == observed["slot_acquisitions"],
        "core_logical_queries": observed["core_logical_queries"] == gates["required_core_logical_queries"],
        "search_provider_effects": gates["minimum_search_provider_effects"] <= observed["search_provider_effects"] <= gates["maximum_search_provider_effects"],
        "core_fetch_targets": observed["core_fetch_targets"] == gates["required_core_fetch_targets"],
        "reserve_fetch_targets": observed["reserve_fetch_targets"] == gates["required_reserve_fetch_targets"],
        "core_usable_pages": observed["core_usable_pages"] >= gates["minimum_core_usable_pages"],
        "reserve_usable_pages": observed["reserve_usable_pages"] >= gates["minimum_reserve_usable_pages"],
        "fetch_conservation": observed["fetch_calls"] == health.get("hard_fetch_helper_calls", -1) + health.get("fetch_deadline_rejections", -1),
        "hard_fetch_deadline_failures": health.get("hard_fetch_deadline_failures", 10**9) <= gates["maximum_hard_fetch_deadline_failures"],
        "fetch_helper_failures": health.get("fetch_helper_failures", 10**9) <= gates["maximum_fetch_helper_failures"],
        "deadline_exhausted": health.get("deadline_exhausted") is gates["required_deadline_exhausted"],
    }


def _git_execution_ready(root: Path) -> bool:
    head = _git_output(root, "rev-parse", "HEAD")
    remote = _git_output(root, "rev-parse", "target/main")
    if head != remote or _git_output(root, "status", "--porcelain"):
        return False
    try:
        _git_output(root, "ls-files", "--error-unmatch", str(EXECUTION_START))
    except subprocess.CalledProcessError:
        return False
    return True


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preaudit(root)
    activation = validate_activation(root)
    validate_execution_start(root)
    if any((root / path).exists() or (root / path).is_symlink() for path in (RESULT, DECISION, POSTAUDIT)):
        raise RuntimeError("V2.43.27 result surface is not pristine")
    if not _git_execution_ready(root):
        raise RuntimeError("V2.43.27 execution-start is not committed and pushed")
    if not _port_listening():
        raise RuntimeError("V2.43.27 keyless proxy is unavailable")
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        root,
        owner=LEASE_OWNER,
        purpose=LEASE_PURPOSE,
        path=root / LEASE_PATH,
    ):
        with tempfile.TemporaryDirectory(dir=root / "outputs") as temporary:
            output_root = Path(temporary)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, MODEL_SLOT_CAP + 1):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            directory = output_root / "task"
            directory.mkdir()
            result_path = directory / "result.json"
            model_path = directory / "model_slot_receipt.json"
            transport_path = directory / "transport_health.json"

            def validate_result(value: Mapping[str, Any]) -> object:
                envelope = validate_envelope(value)
                if not model_path.is_file() or not transport_path.is_file():
                    return envelope
                model = json.loads(model_path.read_text(encoding="utf-8"))
                transport = json.loads(transport_path.read_text(encoding="utf-8"))
                validate_model_receipt(model, expected_cap=MODEL_SLOT_CAP)
                validate_transport_health(transport)
                return validate_observed_bundle(
                    envelope,
                    model_slot_receipt=model,
                    transport_health=transport,
                    expected_cap=MODEL_SLOT_CAP,
                )

            outcome = run_observed_subprocess(
                cwd=root,
                output_root=output_root,
                directory=directory,
                command=[
                    str(root / ".venv-eval/bin/python"),
                    "-I",
                    "-B",
                    str(root / RUNNER_MARKER),
                    "child",
                    "--output-root",
                    str(output_root),
                    "--directory",
                    str(directory),
                    "--slots",
                    str(slots),
                ],
                environment=_environment(),
                timeout_seconds=PARENT_TIMEOUT_SECONDS,
                result_validator=validate_result,
                model_receipt_validator=lambda value: validate_model_receipt(
                    value, expected_cap=MODEL_SLOT_CAP
                ),
                transport_receipt_validator=validate_transport_health,
                result_name=result_path.name,
                model_receipt_name=model_path.name,
                transport_receipt_name=transport_path.name,
                terminal_name="child_terminal_receipt.json",
                parent_name="parent_exit_receipt.json",
            )
            parent = validate_parent_receipt(outcome.receipt)
            envelope = (
                json.loads(result_path.read_text(encoding="utf-8"))
                if parent["failure_taxonomy"] == "success"
                else None
            )
            projected = _project(
                parent,
                envelope,
                wall_seconds=max(0.0, time.monotonic() - started),
            )
        publish(root / RESULT, projected)
    if protected_watcher_snapshot() != activation["protected_watchers"]:
        raise RuntimeError("V2.43.27 protected watcher identity drifted")
    return projected


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preaudit(root)
    validate_activation(root)
    validate_execution_start(root)
    result = _read(root, RESULT)
    validate_projection(result)
    checks = _checks(result, protocol["gates"])
    failed = sorted(name for name, passed in checks.items() if not passed)
    passed = not failed
    value = {
        "artifact_version": 1,
        "role": "v24327_neutral_transport_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "neutral_transport_go" if passed else "neutral_transport_no_go",
        "passed": passed,
        "checks": checks,
        "failed_checks": failed,
        "observed": {
            "wall_seconds": result["wall_seconds"],
            "parent_taxonomy": result["parent_exit"]["failure_taxonomy"],
            **dict(result["observed"]),
        },
        "provenance": {
            "parent_sha256": sha256(root / PARENT),
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "result_sha256": sha256(root / RESULT),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
        "claim_scope": {
            "one_neutral_real_gpt_search_fetch_shared_prefix_transport": True,
            "benchmark_quality_measured": False,
            "entropy_quality_improvement_proven": False,
            "future_population_or_sota_supported": False,
        },
        "authorization": {
            "fresh_uncontaminated_paired_benchmark_design": passed,
            "paired_benchmark_launch": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    validate_decision(value)
    return value


def validate_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "status",
        "passed",
        "checks",
        "failed_checks",
        "observed",
        "provenance",
        "claim_scope",
        "authorization",
        "decision_payload_sha256",
    }
    checks = value.get("checks")
    failed = value.get("failed_checks")
    passed = value.get("passed")
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != "v24327_neutral_transport_decision"
        or value.get("protocol_id") != PROTOCOL_ID
        or not isinstance(checks, Mapping)
        or not isinstance(failed, list)
        or not isinstance(passed, bool)
        or passed is not all(checks.values())
        or failed != sorted(name for name, okay in checks.items() if not okay)
        or value.get("status") != ("neutral_transport_go" if passed else "neutral_transport_no_go")
        or value.get("claim_scope", {}).get("one_neutral_real_gpt_search_fetch_shared_prefix_transport") is not True
        or any(enabled for key, enabled in value.get("claim_scope", {}).items() if key != "one_neutral_real_gpt_search_fetch_shared_prefix_transport")
        or value.get("authorization", {}).get("fresh_uncontaminated_paired_benchmark_design") is not passed
        or any(enabled for key, enabled in value.get("authorization", {}).items() if key != "fresh_uncontaminated_paired_benchmark_design")
        or not _sealed(value, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.43.27 decision drifted")
    return dict(value)


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    validate_preaudit(root)
    activation = validate_activation(root)
    validate_execution_start(root)
    result = _read(root, RESULT)
    decision = _read(root, DECISION)
    validate_projection(result)
    validate_decision(decision)
    lease = lease_observation(root, Path("/proc"))
    encoded = json.dumps({"result": result, "decision": decision}, ensure_ascii=False)
    process_present = any(
        pid != os.getpid()
        for pid in _matching(process_snapshot(), RUNNER_MARKER)
    )
    findings: list[str] = []
    if OPAQUE.search(encoded) or URL.search(encoded) or SECRET.search(encoded):
        findings.append("task_identifier_url_or_credential_persisted")
    if any(literal in encoded for literal in CONTENT_LITERALS):
        findings.append("task_content_persisted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active_after_result")
    if protected_watcher_snapshot() != activation["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    if process_present:
        findings.append("neutral_transport_process_remained_active")
    if decision.get("provenance", {}).get("result_sha256") != sha256(root / RESULT):
        findings.append("decision_result_binding_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24327_neutral_transport_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "findings": findings,
        "audit_valid": not findings,
        "execution_closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers_unchanged": protected_watcher_snapshot() == activation["protected_watchers"],
            "neutral_transport_process_present": process_present,
            "temporary_execution_directory_remaining": False,
            "task_identifier_question_query_url_page_prediction_response_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "credential_value_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_revaluation": False,
            "invalid_result_path": None,
        },
        "authorization": {
            "fresh_uncontaminated_paired_benchmark_design": bool(decision["passed"] and not findings),
            "paired_benchmark_launch": False,
            "exact220": False,
            "evaluator": False,
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "result_sha256": sha256(root / RESULT),
            "decision_sha256": sha256(root / DECISION),
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_postaudit(value)
    return value


def validate_postaudit(value: Mapping[str, Any]) -> dict[str, Any]:
    expected = {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "findings",
        "audit_valid",
        "execution_closure",
        "authorization",
        "provenance",
        "audit_payload_sha256",
    }
    if (
        set(value) != expected
        or value.get("artifact_version") != 1
        or value.get("role") != "v24327_neutral_transport_postresult_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("execution_closure", {}).get("shared_api_lease_active") is not False
        or value.get("execution_closure", {}).get("protected_watchers_unchanged") is not True
        or value.get("execution_closure", {}).get("neutral_transport_process_present") is not False
        or any(enabled for key, enabled in value.get("authorization", {}).items() if key != "fresh_uncontaminated_paired_benchmark_design")
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.27 postresult audit drifted")
    return dict(value)


def finalize(root: Path = ROOT) -> None:
    root = root.resolve()
    if not (root / DECISION).exists():
        publish(root / DECISION, build_decision(root))
    else:
        validate_decision(_read(root, DECISION))
    if not (root / POSTAUDIT).exists():
        publish(root / POSTAUDIT, build_postaudit(root))
    else:
        validate_postaudit(_read(root, POSTAUDIT))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("protocol", "activation", "start", "run", "finalize", "child"),
    )
    parser.add_argument("--output-root")
    parser.add_argument("--directory")
    parser.add_argument("--slots")
    args = parser.parse_args()
    if args.command == "protocol":
        publish(ROOT / PROTOCOL, build_protocol())
        publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation":
        publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start":
        publish(ROOT / EXECUTION_START, build_execution_start())
    elif args.command == "run":
        run_probe(ROOT)
        finalize(ROOT)
    elif args.command == "finalize":
        finalize(ROOT)
    else:
        if not args.output_root or not args.directory or not args.slots:
            raise SystemExit("child paths are required")
        _child(args)
    print(json.dumps({"command": args.command, "status": "ok"}, sort_keys=True))


if __name__ == "__main__":
    main()
