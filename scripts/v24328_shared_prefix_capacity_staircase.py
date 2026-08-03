#!/usr/bin/env python3
"""Benchmark-external 1/2/4/8 capacity ladder for shared-prefix pairs.

The probe deliberately uses synthetic visible-only tasks.  Every worker runs
the complete V2.43.26 transport path, while a shared cross-process pool caps
GPT provider concurrency at two.  Persistent artifacts contain only
content-free accounting and timing; task text, identifiers, queries, URLs,
pages, predictions, evaluator data, and credentials are never published.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
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
    parent_receipt,
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


DATE = "20260803"
PROTOCOL_ID = "v24328_shared_prefix_capacity_staircase_v1"
PROTOCOL = Path(f"results/v24328_capacity_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24328_capacity_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24328_capacity_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24328_capacity_execution_start_v1_{DATE}.json")
RESULT = Path(f"results/v24328_capacity_result_v1_{DATE}.json")
DECISION = Path(f"results/v24328_capacity_decision_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v24328_capacity_postresult_audit_v1_{DATE}.json")
PARENT_DECISION = Path(f"results/v24327_neutral_transport_decision_v1_{DATE}.json")
PARENT_AUDIT = Path(
    f"results/v24327_neutral_transport_postresult_audit_v1_{DATE}.json"
)
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24328_shared_prefix_capacity_staircase_v1"
LEASE_PURPOSE = "benchmark_external_shared_prefix_capacity_staircase"
RUNNER_MARKER = "scripts/v24328_shared_prefix_capacity_staircase.py"
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 9878
MODEL_SLOT_CAP = 2
LEVELS = (1, 2, 4, 8)
TASK_WALL_SECONDS = 180
PARENT_TIMEOUT_SECONDS = 200
LEVEL_BATCH_WALL_CEILINGS = {1: 90.0, 2: 120.0, 4: 180.0, 8: 300.0}
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
    "src/deepwide_agent/v24323_shared_prefix_cell_entropy.py",
    "src/deepwide_agent/v24324_shared_prefix_runner.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24326_runner_integration.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/deepwide_api_lease.py",
    "scripts/v24328_shared_prefix_capacity_staircase.py",
    "tests/test_v24328_shared_prefix_capacity_staircase.py",
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
)
NEUTRAL_QUESTION = (
    "Use public web sources to return one Markdown table about these three "
    "organizations: Python Software Foundation, Linux Foundation, and Apache "
    "Software Foundation. The column names are: Organization, Headquarters "
    "country. Return one table only."
)
LIMITS = ScoreFirstLimits(
    wall_seconds=TASK_WALL_SECONDS,
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


def neutral_task(ordinal: int) -> dict[str, str]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or not 1 <= ordinal <= 8:
        raise ValueError("V2.43.28 neutral ordinal is invalid")
    return validate_visible_task(
        {
            "opaque_id": f"task_{0x243280 + ordinal:024x}",
            "question": NEUTRAL_QUESTION,
        }
    )


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError("V2.43.28 expected an ordinary repository file")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.43.28 expected a JSON object")
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


def _write_new(path: Path, value: Mapping[str, Any]) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.43.28 credential literal in source surface")
        output[relative] = sha256(path)
    return output


def _port_listening() -> bool:
    try:
        with socket.create_connection((PROXY_HOST, PROXY_PORT), timeout=0.5):
            return True
    except OSError:
        return False


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


def _parent(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    decision = _read(root, PARENT_DECISION)
    audit = _read(root, PARENT_AUDIT)
    if (
        decision.get("role") != "v24327_neutral_transport_decision"
        or decision.get("status") != "neutral_transport_go"
        or decision.get("passed") is not True
        or decision.get("failed_checks") != []
        or decision.get("authorization", {}).get(
            "fresh_uncontaminated_paired_benchmark_design"
        )
        is not True
        or not _sealed(decision, "decision_payload_sha256")
        or audit.get("role") != "v24327_neutral_transport_postresult_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("execution_closure", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.28 parent evidence drifted")
    return decision, audit


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    _parent(root)
    LIMITS.validate()
    tasks = [neutral_task(index) for index in range(1, 9)]
    if len({task["opaque_id"] for task in tasks}) != 8:
        raise RuntimeError("V2.43.28 neutral identifiers are not unique")
    if require_pristine:
        present = [
            str(path)
            for path in (PREAUDIT, ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
            if (root / path).exists() or (root / path).is_symlink()
        ]
        if present:
            raise RuntimeError(f"V2.43.28 future surface is not pristine: {present}")
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24328_capacity_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            str(PARENT_DECISION): sha256(root / PARENT_DECISION),
            str(PARENT_AUDIT): sha256(root / PARENT_AUDIT),
        },
        "scope": "benchmark_external_shared_prefix_pair_capacity_only",
        "task_contract": {
            "levels": list(LEVELS),
            "level_task_counts": {str(level): level for level in LEVELS},
            "synthetic_tasks_not_selected_from_benchmark": True,
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "task_text_identifier_query_url_page_prediction_or_hash_persisted": False,
            "same_neutral_workload_prefix_repeated_across_levels_for_capacity": True,
            "no_resume_retry_skip_or_selective_rerun": True,
        },
        "provider": {
            "proxy_url": f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "service_tier": "priority",
            "model_slot_cap": MODEL_SLOT_CAP,
        },
        "runtime": {
            "policy": "v24326_deadline_shared_prefix_runner_integration_v1",
            "model_slot_cap": MODEL_SLOT_CAP,
            "model_calls_per_task_maximum": LIMITS.model_calls,
            "logical_queries_per_task_maximum": LIMITS.search_queries,
            "fetch_targets_per_task_maximum": LIMITS.fetch_targets,
            "core_fetch_target": 7,
            "reserve_fetch_target": 3,
            "task_wall_seconds": TASK_WALL_SECONDS,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "batch_wall_ceilings_seconds": {
                str(level): LEVEL_BATCH_WALL_CEILINGS[level] for level in LEVELS
            },
            "stop_on_first_failed_level": True,
            "recommended_executor_rule": "maximum_observed_throughput_among_passing_levels_tie_lower_executor",
        },
        "gates": {
            "all_levels_required": True,
            "all_tasks_parent_success_and_artifacts_valid": True,
            "all_tasks_effect_accounting_complete": True,
            "all_tasks_prefix_frozen_once": True,
            "all_tasks_core_reserve_fetch_targets_exactly_7_3": True,
            "all_tasks_core_and_reserve_have_usable_pages": True,
            "all_tasks_zero_slot_timeout_or_provider_deadline_failure": True,
            "all_tasks_zero_hard_fetch_deadline_or_helper_failure": True,
            "all_tasks_zero_repeated_upstream_effect": True,
            "all_tasks_model_and_fetch_conservation": True,
            "batch_wall_within_frozen_ceiling": True,
        },
        "surface_manifest": manifest,
        "surface_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "task_text_identifier_query_url_page_prediction_response_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "capacity_staircase_design": True,
            "capacity_staircase_launch": False,
            "paired_benchmark_launch": False,
            "exact220": False,
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
        protocol.get("role") != "v24328_capacity_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope")
        != "benchmark_external_shared_prefix_pair_capacity_only"
        or protocol.get("task_contract", {}).get("levels") != list(LEVELS)
        or protocol.get("runtime", {}).get("model_slot_cap") != MODEL_SLOT_CAP
        or protocol.get("runtime", {}).get("core_fetch_target") != 7
        or protocol.get("runtime", {}).get("reserve_fetch_target") != 3
        or not isinstance(manifest, Mapping)
        or dict(manifest) != _manifest(root)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(authorization, Mapping)
        or authorization.get("capacity_staircase_design") is not True
        or any(
            enabled
            for key, enabled in authorization.items()
            if key != "capacity_staircase_design"
        )
        or protocol.get("parents")
        != {
            str(PARENT_DECISION): sha256(root / PARENT_DECISION),
            str(PARENT_AUDIT): sha256(root / PARENT_AUDIT),
        }
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.28 protocol drifted")
    _parent(root)
    for index in range(1, 9):
        neutral_task(index)
    return protocol


def _run_tests() -> bool:
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
            "test_v24328_shared_prefix_capacity_staircase.py",
        ],
        cwd=ROOT,
        env=_environment(),
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
    tests_passed = _run_tests()
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
        "role": "v24328_capacity_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": True,
            "surface_manifest_exact": True,
            "focused_tests_passed": tests_passed,
            "eight_synthetic_visible_tasks_validated": True,
            "runtime_input_keys_exactly_opaque_id_and_question": True,
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
            "protocol_sha256": sha256(root / PROTOCOL),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
        "authorization": {
            "one_capacity_staircase_launch": not findings,
            "paired_benchmark_launch": False,
            "exact220": False,
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
        audit.get("role") != "v24328_capacity_preactivation_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or audit.get("findings") != []
        or audit.get("audit_valid") is not True
        or audit.get("launch_authorized") is not True
        or audit.get("checks", {}).get("focused_tests_passed") is not True
        or audit.get("checks", {}).get("runtime_input_keys_exactly_opaque_id_and_question")
        is not True
        or audit.get("provenance", {}).get("protocol_sha256")
        != sha256(root / PROTOCOL)
        or audit.get("protected_watchers") != protected_watcher_snapshot()
        or audit.get("authorization", {}).get("one_capacity_staircase_launch")
        is not True
        or any(
            enabled
            for key, enabled in audit.get("authorization", {}).items()
            if key != "one_capacity_staircase_launch"
        )
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.28 preactivation audit drifted")
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
        "role": "v24328_capacity_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        "levels": list(LEVELS),
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": audit["protected_watchers"],
        "shared_api_lease_active_before_activation": lease.get("active") is True,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "runtime_input_exactly_opaque_id_and_question": True,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "authorization": {
            "one_capacity_staircase_launch": not findings,
            "paired_benchmark_launch": False,
            "exact220": False,
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
        activation.get("role") != "v24328_capacity_activation"
        or activation.get("protocol_id") != PROTOCOL_ID
        or activation.get("status") != "active"
        or activation.get("findings") != []
        or activation.get("launch_authorized") is not True
        or activation.get("protocol_sha256") != sha256(root / PROTOCOL)
        or activation.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or activation.get("levels") != list(LEVELS)
        or activation.get("model_slot_cap") != MODEL_SLOT_CAP
        or activation.get("protected_watchers") != protected_watcher_snapshot()
        or activation.get("network_model_search_fetch_evaluator_or_api_called")
        is not False
        or activation.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or activation.get("authorization", {}).get("one_capacity_staircase_launch")
        is not True
        or any(
            enabled
            for key, enabled in activation.get("authorization", {}).items()
            if key != "one_capacity_staircase_launch"
        )
        or not _sealed(activation, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.43.28 activation drifted")
    validate_preaudit(root)
    return activation


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
        raise RuntimeError("V2.43.28 execution surface is not pristine")
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
        "role": "v24328_capacity_execution_start",
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
        "levels": list(LEVELS),
        "model_slot_cap": MODEL_SLOT_CAP,
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
        start.get("role") != "v24328_capacity_execution_start"
        or start.get("protocol_id") != PROTOCOL_ID
        or start.get("status") != "ready"
        or start.get("findings") != []
        or start.get("execution_authorized") is not True
        or start.get("protocol_sha256") != sha256(root / PROTOCOL)
        or start.get("activation_sha256") != sha256(root / ACTIVATION)
        or start.get("levels") != list(LEVELS)
        or start.get("model_slot_cap") != MODEL_SLOT_CAP
        or start.get("protected_watchers") != protected_watcher_snapshot()
        or start.get("api_called_before_execution_start") is not False
        or start.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or start.get("benchmark_or_evaluator_authorized") is not False
        or not _sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.43.28 execution-start drifted")
    validate_activation(root)
    return start


def _child(args: argparse.Namespace) -> None:
    ordinal = int(args.ordinal)
    task = neutral_task(ordinal)
    output_root = Path(args.output_root)
    directory = Path(args.directory)
    result_path = directory / "result.json"
    model_path = directory / "model_slot_receipt.json"
    transport_path = directory / "transport_health.json"
    terminal_path = directory / "child_terminal_receipt.json"

    def action() -> None:
        started = time.monotonic()
        deadline = started + TASK_WALL_SECONDS
        model = build_deadline_model(
            url=f"http://{PROXY_HOST}:{PROXY_PORT}/responses",
            model_name="gpt-5.6-sol",
            reasoning_effort="low",
            service_tier="priority",
            static_timeout_seconds=TASK_WALL_SECONDS,
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
            timeout=TASK_WALL_SECONDS,
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
            task,
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


def _task_projection(
    ordinal: int,
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any] | None,
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

    def integer(source: object, name: str) -> int:
        raw = source.get(name) if isinstance(source, Mapping) else None
        return int(raw) if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 0 else 0

    def number(source: object, name: str) -> float:
        raw = source.get(name) if isinstance(source, Mapping) else None
        return float(raw) if isinstance(raw, (int, float)) and not isinstance(raw, bool) and math.isfinite(float(raw)) and float(raw) >= 0 else 0.0

    raw_slot_counts = slot.get("slot_acquisition_counts") if isinstance(slot, Mapping) else None
    slot_counts = (
        [int(item) for item in raw_slot_counts]
        if isinstance(raw_slot_counts, list)
        and len(raw_slot_counts) == MODEL_SLOT_CAP
        and all(isinstance(item, int) and not isinstance(item, bool) and item >= 0 for item in raw_slot_counts)
        else [0] * MODEL_SLOT_CAP
    )
    value = {
        "ordinal": ordinal,
        "wall_seconds": round(float(parent.get("elapsed_seconds", 0.0)), 6),
        "parent_taxonomy": parent.get("failure_taxonomy"),
        "all_parent_artifacts_valid": all(
            parent.get(name) is True
            for name in (
                "child_terminal_receipt_present",
                "child_terminal_receipt_valid",
                "result_envelope_present",
                "result_envelope_valid",
                "model_receipt_present",
                "model_receipt_valid",
                "transport_receipt_present",
                "transport_receipt_valid",
            )
        ),
        "result_status": result.get("status") if isinstance(result, Mapping) else None,
        "completion_kind": result.get("completion_kind") if isinstance(result, Mapping) else None,
        "effect_accounting_complete": receipt.get("effect_accounting_complete") if isinstance(receipt, Mapping) else None,
        "prefix_status": receipt.get("prefix_status") if isinstance(receipt, Mapping) else None,
        "prefix_producer_execution_count": prefix.get("producer_execution_count") if isinstance(prefix, Mapping) else None,
        "candidate_identity_handoff": receipt.get("candidate_identity_handoff") if isinstance(receipt, Mapping) else None,
        "proposed_cell_changes": integer(receipt, "proposed_cell_changes"),
        "admitted_cell_changes": integer(receipt, "admitted_cell_changes"),
        "credited_entropy_positive": bool(number(receipt, "credited_conditional_entropy_reduction_nats") > 0),
        "logical_model_admissions": integer(receipt, "logical_model_admissions"),
        "provider_model_requests": integer(receipt, "provider_model_requests"),
        "provider_model_attempts": integer(receipt, "provider_model_attempts"),
        "pre_provider_model_rejections": integer(receipt, "pre_provider_model_rejections"),
        "slot_acquisitions": integer(slot, "acquisitions"),
        "slot_timeouts": integer(slot, "slot_timeouts"),
        "provider_deadline_failures": integer(slot, "provider_deadline_failures"),
        "slot_total_wait_seconds": number(slot, "total_wait_seconds"),
        "slot_max_wait_seconds": number(slot, "max_wait_seconds"),
        "slot_acquisition_counts": slot_counts,
        "core_logical_queries": integer(receipt, "core_logical_queries"),
        "search_provider_effects": integer(receipt, "core_search_provider_effects") + integer(receipt, "reserve_search_provider_effects"),
        "core_fetch_targets": integer(receipt, "core_fetch_targets"),
        "reserve_fetch_targets": integer(receipt, "reserve_fetch_targets"),
        "core_network_fetch_effects": integer(receipt, "core_network_fetch_effects"),
        "reserve_network_fetch_effects": integer(receipt, "reserve_network_fetch_effects"),
        "core_usable_pages": integer(receipt, "core_usable_pages"),
        "reserve_usable_pages": integer(receipt, "reserve_usable_pages"),
        "repeated_upstream_effects": sum(
            receipt.get(name, 0)
            for name in (
                "repeated_plan_model_effects_by_branches",
                "repeated_core_search_effects_by_branches",
                "repeated_core_fetch_effects_by_branches",
            )
        ) if isinstance(receipt, Mapping) else 0,
        "model_requests": integer(model_cost, "requests"),
        "model_attempts": integer(model_cost, "attempts"),
        "model_total_tokens": integer(model_cost, "total_tokens"),
        "search_calls": integer(search_cost, "calls"),
        "fetch_calls": integer(search_cost, "fetch_calls"),
        "fetch_failures": integer(search_cost, "fetch_failures"),
        "search_total_tokens": integer(search_cost, "total_tokens"),
        "hosted_search_attempts": integer(transport, "hosted_search_attempts"),
        "hosted_search_deadline_failures": integer(transport, "hosted_search_deadline_failures"),
        "hard_fetch_helper_calls": integer(transport, "hard_fetch_helper_calls"),
        "hard_fetch_deadline_failures": integer(transport, "hard_fetch_deadline_failures"),
        "fetch_deadline_rejections": integer(transport, "fetch_deadline_rejections"),
        "fetch_helper_failures": integer(transport, "fetch_helper_failures"),
        "deadline_exhausted": transport.get("deadline_exhausted") if isinstance(transport, Mapping) and isinstance(transport.get("deadline_exhausted"), bool) else True,
        "model_slot_cap": integer(slot, "slot_cap"),
        "task_text_identifier_query_url_page_prediction_response_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    value["checks"] = _task_checks(value)
    value["passed"] = all(value["checks"].values())
    validate_task_projection(value)
    return value


def _task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    acquisitions = value.get("slot_acquisitions")
    timeouts = value.get("slot_timeouts")
    fetch_calls = value.get("fetch_calls")
    helper_calls = value.get("hard_fetch_helper_calls")
    rejected_fetches = value.get("fetch_deadline_rejections")
    return {
        "parent_success": value.get("parent_taxonomy") == "success",
        "all_parent_artifacts_valid": value.get("all_parent_artifacts_valid") is True,
        "result_completed": value.get("result_status") == "completed",
        "effect_accounting_complete": value.get("effect_accounting_complete") is True,
        "prefix_frozen_once": value.get("prefix_status") == "frozen" and value.get("prefix_producer_execution_count") == 1,
        "model_effect_range": isinstance(value.get("logical_model_admissions"), int) and 2 <= int(value["logical_model_admissions"]) <= 3,
        "model_conservation": isinstance(acquisitions, int) and isinstance(timeouts, int) and value.get("logical_model_admissions") == acquisitions + timeouts and value.get("provider_model_requests") == acquisitions and value.get("pre_provider_model_rejections") == timeouts,
        "no_model_retry": value.get("provider_model_attempts") == value.get("provider_model_requests"),
        "no_slot_or_provider_deadline_failure": timeouts == 0 and value.get("provider_deadline_failures") == 0,
        "slot_cap_two": value.get("model_slot_cap") == MODEL_SLOT_CAP,
        "four_logical_queries": value.get("core_logical_queries") == 4,
        "hosted_search_effect": isinstance(value.get("search_provider_effects"), int) and 1 <= int(value["search_provider_effects"]) <= 2,
        "exact_core_reserve_fetch_targets": value.get("core_fetch_targets") == 7 and value.get("reserve_fetch_targets") == 3,
        "core_and_reserve_usable": isinstance(value.get("core_usable_pages"), int) and int(value["core_usable_pages"]) >= 1 and isinstance(value.get("reserve_usable_pages"), int) and int(value["reserve_usable_pages"]) >= 1,
        "fetch_conservation": isinstance(fetch_calls, int) and isinstance(helper_calls, int) and isinstance(rejected_fetches, int) and fetch_calls == helper_calls + rejected_fetches,
        "no_hard_fetch_deadline_or_helper_failure": value.get("hard_fetch_deadline_failures") == 0 and value.get("fetch_helper_failures") == 0 and rejected_fetches == 0,
        "deadline_not_exhausted": value.get("deadline_exhausted") is False,
        "no_repeated_upstream_effect": value.get("repeated_upstream_effects") == 0,
        "within_parent_wall": isinstance(value.get("wall_seconds"), (int, float)) and float(value["wall_seconds"]) <= PARENT_TIMEOUT_SECONDS,
    }


TASK_KEYS = frozenset(
    {
        "ordinal", "wall_seconds", "parent_taxonomy", "all_parent_artifacts_valid",
        "result_status", "completion_kind", "effect_accounting_complete", "prefix_status",
        "prefix_producer_execution_count", "candidate_identity_handoff", "proposed_cell_changes",
        "admitted_cell_changes", "credited_entropy_positive", "logical_model_admissions",
        "provider_model_requests", "provider_model_attempts", "pre_provider_model_rejections",
        "slot_acquisitions", "slot_timeouts", "provider_deadline_failures",
        "slot_total_wait_seconds", "slot_max_wait_seconds", "slot_acquisition_counts",
        "core_logical_queries", "search_provider_effects", "core_fetch_targets",
        "reserve_fetch_targets", "core_network_fetch_effects", "reserve_network_fetch_effects",
        "core_usable_pages", "reserve_usable_pages", "repeated_upstream_effects",
        "model_requests", "model_attempts", "model_total_tokens", "search_calls",
        "fetch_calls", "fetch_failures", "search_total_tokens", "hosted_search_attempts",
        "hosted_search_deadline_failures", "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures", "fetch_deadline_rejections", "fetch_helper_failures",
        "deadline_exhausted", "model_slot_cap",
        "task_text_identifier_query_url_page_prediction_response_or_hash_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "checks", "passed",
    }
)


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(value, ensure_ascii=False)
    numeric_nonnegative = (
        "wall_seconds", "proposed_cell_changes", "admitted_cell_changes",
        "logical_model_admissions", "provider_model_requests", "provider_model_attempts",
        "pre_provider_model_rejections", "slot_acquisitions", "slot_timeouts",
        "provider_deadline_failures", "slot_total_wait_seconds", "slot_max_wait_seconds",
        "core_logical_queries", "search_provider_effects", "core_fetch_targets",
        "reserve_fetch_targets", "core_network_fetch_effects", "reserve_network_fetch_effects",
        "core_usable_pages", "reserve_usable_pages", "repeated_upstream_effects",
        "model_requests", "model_attempts", "model_total_tokens", "search_calls",
        "fetch_calls", "fetch_failures", "search_total_tokens", "hosted_search_attempts",
        "hosted_search_deadline_failures", "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures", "fetch_deadline_rejections", "fetch_helper_failures",
    )
    if (
        set(value) != TASK_KEYS
        or isinstance(value.get("ordinal"), bool)
        or not isinstance(value.get("ordinal"), int)
        or not 1 <= int(value["ordinal"]) <= 8
        or not isinstance(value.get("checks"), Mapping)
        or not all(isinstance(item, bool) for item in value["checks"].values())
        or value.get("passed") is not all(value["checks"].values())
        or value.get("task_text_identifier_query_url_page_prediction_response_or_hash_persisted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or OPAQUE.search(encoded)
        or URL.search(encoded)
        or SECRET.search(encoded)
        or any(literal in encoded for literal in CONTENT_LITERALS)
    ):
        raise RuntimeError("V2.43.28 task projection drifted")
    for name in numeric_nonnegative:
        number = value.get(name)
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(float(number)) or float(number) < 0:
            raise RuntimeError("V2.43.28 task numeric projection drifted")
    counts = value.get("slot_acquisition_counts")
    if (
        not isinstance(counts, list)
        or len(counts) != MODEL_SLOT_CAP
        or any(isinstance(item, bool) or not isinstance(item, int) or item < 0 for item in counts)
        or sum(counts) != value.get("slot_acquisitions")
    ):
        raise RuntimeError("V2.43.28 slot projection drifted")
    return dict(value)


def _percentile(values: Sequence[float], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    rank = max(0, min(len(ordered) - 1, math.ceil(percentile * len(ordered)) - 1))
    return ordered[rank]


def summarize_level(
    *, level: int, tasks: Sequence[Mapping[str, Any]], batch_wall_seconds: float
) -> dict[str, Any]:
    if level not in LEVELS or len(tasks) != level:
        raise RuntimeError("V2.43.28 level shape drifted")
    values = [dict(task) for task in tasks]
    for task in values:
        validate_task_projection(task)
    values.sort(key=lambda item: item["ordinal"])
    walls = [float(task["wall_seconds"]) for task in values]
    slot_counts = [
        sum(int(task["slot_acquisition_counts"][index]) for task in values)
        for index in range(MODEL_SLOT_CAP)
    ]
    batch = max(0.0, float(batch_wall_seconds))
    throughput = level / batch if batch > 0 else 0.0
    checks = {
        "exact_ordinals": [task["ordinal"] for task in values] == list(range(1, level + 1)),
        "all_tasks_passed": all(task["passed"] for task in values),
        "batch_wall_within_ceiling": batch <= LEVEL_BATCH_WALL_CEILINGS[level],
        "aggregate_slot_conservation": sum(slot_counts) == sum(int(task["slot_acquisitions"]) for task in values),
    }
    value = {
        "executor_count": level,
        "selected": level,
        "model_slot_cap": MODEL_SLOT_CAP,
        "batch_wall_seconds": round(batch, 6),
        "batch_wall_ceiling_seconds": LEVEL_BATCH_WALL_CEILINGS[level],
        "throughput_tasks_per_minute": round(throughput * 60.0, 6),
        "task_wall_sum_seconds": round(sum(walls), 6),
        "task_wall_mean_seconds": round(sum(walls) / level, 6),
        "task_wall_p95_seconds": round(_percentile(walls, 0.95), 6),
        "task_wall_max_seconds": round(max(walls), 6),
        "model_requests": sum(int(task["model_requests"]) for task in values),
        "model_attempts": sum(int(task["model_attempts"]) for task in values),
        "slot_acquisitions": sum(int(task["slot_acquisitions"]) for task in values),
        "slot_timeouts": sum(int(task["slot_timeouts"]) for task in values),
        "slot_total_wait_seconds": round(sum(float(task["slot_total_wait_seconds"]) for task in values), 6),
        "slot_max_wait_seconds": round(max(float(task["slot_max_wait_seconds"]) for task in values), 6),
        "slot_acquisition_counts": slot_counts,
        "search_provider_effects": sum(int(task["search_provider_effects"]) for task in values),
        "fetch_calls": sum(int(task["fetch_calls"]) for task in values),
        "fetch_failures": sum(int(task["fetch_failures"]) for task in values),
        "hard_fetch_deadline_failures": sum(int(task["hard_fetch_deadline_failures"]) for task in values),
        "fetch_helper_failures": sum(int(task["fetch_helper_failures"]) for task in values),
        "model_total_tokens": sum(int(task["model_total_tokens"]) for task in values),
        "search_total_tokens": sum(int(task["search_total_tokens"]) for task in values),
        "entropy_positive_tasks": sum(task["credited_entropy_positive"] is True for task in values),
        "candidate_nonidentity_tasks": sum(task["candidate_identity_handoff"] is False for task in values),
        "tasks": values,
        "checks": checks,
        "passed": all(checks.values()),
    }
    validate_level(value)
    return value


def validate_level(value: Mapping[str, Any]) -> dict[str, Any]:
    level = value.get("executor_count")
    tasks = value.get("tasks")
    checks = value.get("checks")
    if (
        level not in LEVELS
        or value.get("selected") != level
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or not isinstance(tasks, list)
        or len(tasks) != level
        or not isinstance(checks, Mapping)
        or value.get("passed") is not all(checks.values())
        or value.get("batch_wall_ceiling_seconds") != LEVEL_BATCH_WALL_CEILINGS[level]
        or value.get("slot_timeouts") != 0 and value.get("passed") is True
    ):
        raise RuntimeError("V2.43.28 level projection drifted")
    for task in tasks:
        validate_task_projection(task)
    return dict(value)


def _run_one(root: Path, output_root: Path, slots: Path, directory: Path, ordinal: int) -> dict[str, Any]:
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
            "-I", "-B", str(root / RUNNER_MARKER), "child",
            "--output-root", str(output_root),
            "--directory", str(directory),
            "--slots", str(slots),
            "--ordinal", str(ordinal),
        ],
        environment=_environment(),
        timeout_seconds=PARENT_TIMEOUT_SECONDS,
        result_validator=validate_result,
        model_receipt_validator=lambda value: validate_model_receipt(value, expected_cap=MODEL_SLOT_CAP),
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
    return _task_projection(ordinal, parent, envelope)


def _local_failure_projection(ordinal: int) -> dict[str, Any]:
    """Publish a zero-attribution terminal if local orchestration itself fails."""

    receipt = parent_receipt(
        return_code=None,
        timed_out=False,
        elapsed_seconds=0.0,
        subprocess_exception=True,
        child_terminal_receipt_present=False,
        child_terminal_receipt_valid=False,
        result_envelope_present=False,
        result_envelope_valid=False,
        model_receipt_present=False,
        model_receipt_valid=False,
        transport_receipt_present=False,
        transport_receipt_valid=False,
    )
    return _task_projection(ordinal, receipt, None)


def _git_execution_ready(root: Path) -> bool:
    if (
        _git_output(root, "rev-parse", "HEAD")
        != _git_output(root, "rev-parse", "target/main")
        or _git_output(root, "status", "--porcelain")
    ):
        return False
    try:
        _git_output(root, "ls-files", "--error-unmatch", str(EXECUTION_START))
    except subprocess.CalledProcessError:
        return False
    return True


def build_result(
    *, levels: Sequence[Mapping[str, Any]], activation: Mapping[str, Any], now: int | None = None
) -> dict[str, Any]:
    values = [dict(level) for level in levels]
    for level in values:
        validate_level(level)
    expected_prefix = list(LEVELS[: len(values)])
    actual = [level["executor_count"] for level in values]
    if actual != expected_prefix:
        raise RuntimeError("V2.43.28 capacity levels are not a strict prefix")
    for index, level in enumerate(values[:-1]):
        if not level["passed"]:
            raise RuntimeError("V2.43.28 continued after a failed capacity level")
    passing = [level for level in values if level["passed"]]
    highest = max((level["executor_count"] for level in passing), default=0)
    all_passed = len(values) == len(LEVELS) and all(level["passed"] for level in values)
    best = max(
        passing,
        key=lambda item: (
            float(item["throughput_tasks_per_minute"]),
            -int(item["executor_count"]),
        ),
        default=None,
    )
    projection = (
        round(220.0 / (float(best["throughput_tasks_per_minute"]) / 60.0), 6)
        if best is not None and float(best["throughput_tasks_per_minute"]) > 0
        else None
    )
    value = {
        "artifact_version": 1,
        "role": "v24328_capacity_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "levels_requested": list(LEVELS),
        "model_slot_cap": MODEL_SLOT_CAP,
        "levels": values,
        "highest_passing_executor_count": highest,
        "recommended_executor_count": (
            int(best["executor_count"]) if best is not None else 0
        ),
        "maximum_observed_throughput_tasks_per_minute": (
            float(best["throughput_tasks_per_minute"])
            if best is not None
            else 0.0
        ),
        "all_requested_levels_passed": all_passed,
        "capacity_only_exact220_projection_seconds": projection,
        "projection_is_not_a_benchmark_eta_or_quality_claim": True,
        "protected_watchers_unchanged": protected_watcher_snapshot() == activation["protected_watchers"],
        "task_text_identifier_query_url_page_prediction_response_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "credential_value_persisted_hashed_or_emitted": False,
        "official_evaluator_called": False,
        "resume_retry_skip_or_revaluation": False,
        "authorization": {
            "fresh_shared_prefix_paired_benchmark_protocol_design": all_passed,
            "paired_benchmark_launch": False,
            "exact220": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_result(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    levels = value.get("levels")
    authorization = value.get("authorization")
    encoded = json.dumps(value, ensure_ascii=False)
    if not isinstance(levels, list):
        raise RuntimeError("V2.43.28 result levels are absent")
    for level in levels:
        validate_level(level)
    actual = [level["executor_count"] for level in levels]
    expected = list(LEVELS[: len(levels)])
    all_passed = len(levels) == len(LEVELS) and all(level["passed"] for level in levels)
    passing = [level["executor_count"] for level in levels if level["passed"]]
    passing_levels = [level for level in levels if level["passed"]]
    best = max(
        passing_levels,
        key=lambda item: (
            float(item["throughput_tasks_per_minute"]),
            -int(item["executor_count"]),
        ),
        default=None,
    )
    if (
        value.get("role") != "v24328_capacity_result"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("levels_requested") != list(LEVELS)
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or actual != expected
        or any(not level["passed"] for level in levels[:-1])
        or value.get("highest_passing_executor_count") != (max(passing) if passing else 0)
        or value.get("recommended_executor_count")
        != (int(best["executor_count"]) if best is not None else 0)
        or value.get("maximum_observed_throughput_tasks_per_minute")
        != (
            float(best["throughput_tasks_per_minute"])
            if best is not None
            else 0.0
        )
        or value.get("all_requested_levels_passed") is not all_passed
        or value.get("projection_is_not_a_benchmark_eta_or_quality_claim") is not True
        or value.get("protected_watchers_unchanged") is not True
        or value.get("task_text_identifier_query_url_page_prediction_response_or_hash_persisted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("credential_value_persisted_hashed_or_emitted") is not False
        or value.get("official_evaluator_called") is not False
        or value.get("resume_retry_skip_or_revaluation") is not False
        or not isinstance(authorization, Mapping)
        or authorization.get("fresh_shared_prefix_paired_benchmark_protocol_design") is not all_passed
        or any(enabled for key, enabled in authorization.items() if key != "fresh_shared_prefix_paired_benchmark_protocol_design")
        or OPAQUE.search(encoded)
        or URL.search(encoded)
        or SECRET.search(encoded)
        or any(literal in encoded for literal in CONTENT_LITERALS)
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.43.28 capacity result drifted")
    return dict(value)


def run_capacity(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    validate_preaudit(root)
    activation = validate_activation(root)
    validate_execution_start(root)
    if any((root / path).exists() or (root / path).is_symlink() for path in (RESULT, DECISION, POSTAUDIT)):
        raise RuntimeError("V2.43.28 result surface is not pristine")
    if not _git_execution_ready(root):
        raise RuntimeError("V2.43.28 execution-start is not committed and pushed")
    if not _port_listening():
        raise RuntimeError("V2.43.28 keyless proxy is unavailable")
    levels: list[dict[str, Any]] = []
    with acquire_deepwide_api_lease(
        root, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=root / LEASE_PATH
    ):
        with tempfile.TemporaryDirectory(dir=root / "outputs") as temporary:
            output_root = Path(temporary)
            slots = output_root / "slots"
            slots.mkdir()
            for index in range(1, MODEL_SLOT_CAP + 1):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            for executor_count in LEVELS:
                level_root = output_root / f"level_{executor_count:02d}"
                level_root.mkdir()
                directories: list[Path] = []
                for ordinal in range(1, executor_count + 1):
                    directory = level_root / f"task_{ordinal:02d}"
                    directory.mkdir()
                    directories.append(directory)
                started = time.monotonic()
                with concurrent.futures.ThreadPoolExecutor(max_workers=executor_count) as pool:
                    futures = [
                        pool.submit(_run_one, root, output_root, slots, directory, ordinal)
                        for ordinal, directory in enumerate(directories, start=1)
                    ]
                    tasks = []
                    for ordinal, future in enumerate(futures, start=1):
                        try:
                            tasks.append(future.result())
                        except Exception:
                            tasks.append(_local_failure_projection(ordinal))
                level = summarize_level(
                    level=executor_count,
                    tasks=tasks,
                    batch_wall_seconds=max(0.0, time.monotonic() - started),
                )
                levels.append(level)
                if not level["passed"]:
                    break
    if protected_watcher_snapshot() != activation["protected_watchers"]:
        raise RuntimeError("V2.43.28 protected watcher identity drifted")
    value = build_result(levels=levels, activation=activation)
    publish(root / RESULT, value)
    return value


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preaudit(root)
    validate_activation(root)
    validate_execution_start(root)
    result = validate_result(_read(root, RESULT))
    passed = result["all_requested_levels_passed"] is True
    value = {
        "artifact_version": 1,
        "role": "v24328_capacity_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "capacity_go" if passed else "capacity_no_go",
        "passed": passed,
        "highest_passing_executor_count": result["highest_passing_executor_count"],
        "recommended_executor_count": result["recommended_executor_count"],
        "maximum_observed_throughput_tasks_per_minute": result[
            "maximum_observed_throughput_tasks_per_minute"
        ],
        "capacity_only_exact220_projection_seconds": result["capacity_only_exact220_projection_seconds"],
        "projection_is_not_a_benchmark_eta_or_quality_claim": True,
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "result_sha256": sha256(root / RESULT),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
        "claim_scope": {
            "benchmark_external_shared_prefix_capacity_measured": True,
            "benchmark_quality_measured": False,
            "entropy_quality_improvement_proven": False,
            "future_population_or_sota_supported": False,
        },
        "authorization": {
            "fresh_shared_prefix_paired_benchmark_protocol_design": passed,
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
    passed = value.get("passed")
    authorization = value.get("authorization")
    scope = value.get("claim_scope")
    if (
        value.get("role") != "v24328_capacity_decision"
        or value.get("protocol_id") != PROTOCOL_ID
        or not isinstance(passed, bool)
        or value.get("status") != ("capacity_go" if passed else "capacity_no_go")
        or value.get("projection_is_not_a_benchmark_eta_or_quality_claim") is not True
        or not isinstance(scope, Mapping)
        or scope.get("benchmark_external_shared_prefix_capacity_measured") is not True
        or any(enabled for key, enabled in scope.items() if key != "benchmark_external_shared_prefix_capacity_measured")
        or not isinstance(authorization, Mapping)
        or authorization.get("fresh_shared_prefix_paired_benchmark_protocol_design") is not passed
        or any(enabled for key, enabled in authorization.items() if key != "fresh_shared_prefix_paired_benchmark_protocol_design")
        or not _sealed(value, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.43.28 capacity decision drifted")
    return dict(value)


def _capacity_child_present() -> bool:
    for item in process_snapshot():
        argv = item.get("argv")
        command = " ".join(str(token) for token in argv) if isinstance(argv, list) else ""
        if RUNNER_MARKER in command and " child " in f" {command} ":
            return True
    return False


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    validate_preaudit(root)
    activation = validate_activation(root)
    validate_execution_start(root)
    result = validate_result(_read(root, RESULT))
    decision = validate_decision(_read(root, DECISION))
    lease = lease_observation(root, Path("/proc"))
    encoded = json.dumps({"result": result, "decision": decision}, ensure_ascii=False)
    process_present = _capacity_child_present()
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
        findings.append("capacity_child_remained_active")
    if decision.get("provenance", {}).get("result_sha256") != sha256(root / RESULT):
        findings.append("decision_result_binding_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24328_capacity_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "findings": findings,
        "audit_valid": not findings,
        "execution_closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers_unchanged": protected_watcher_snapshot() == activation["protected_watchers"],
            "capacity_child_present": process_present,
            "temporary_execution_directory_remaining": False,
            "task_text_identifier_query_url_page_prediction_response_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "credential_value_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_revaluation": False,
            "invalid_result_path": None,
        },
        "authorization": {
            "fresh_shared_prefix_paired_benchmark_protocol_design": bool(decision["passed"] and not findings),
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
    if (
        value.get("role") != "v24328_capacity_postresult_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("execution_closure", {}).get("shared_api_lease_active") is not False
        or value.get("execution_closure", {}).get("protected_watchers_unchanged") is not True
        or value.get("execution_closure", {}).get("capacity_child_present") is not False
        or any(enabled for key, enabled in value.get("authorization", {}).items() if key != "fresh_shared_prefix_paired_benchmark_protocol_design")
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.28 postresult audit drifted")
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
        "command", choices=("protocol", "activation", "start", "run", "finalize", "child")
    )
    parser.add_argument("--output-root")
    parser.add_argument("--directory")
    parser.add_argument("--slots")
    parser.add_argument("--ordinal", type=int)
    args = parser.parse_args()
    if args.command == "protocol":
        publish(ROOT / PROTOCOL, build_protocol())
        publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation":
        publish(ROOT / ACTIVATION, build_activation())
    elif args.command == "start":
        publish(ROOT / EXECUTION_START, build_execution_start())
    elif args.command == "run":
        run_capacity(ROOT)
        finalize(ROOT)
    elif args.command == "finalize":
        finalize(ROOT)
    else:
        if not args.output_root or not args.directory or not args.slots or args.ordinal is None:
            raise SystemExit("child paths and ordinal are required")
        _child(args)
    print(json.dumps({"command": args.command, "status": "ok"}, sort_keys=True))


if __name__ == "__main__":
    main()
