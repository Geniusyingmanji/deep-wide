#!/usr/bin/env python3
"""Gate real-provider synthesis recovery with eight workers and two GPT slots."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import re
import sys
import tempfile
import threading
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelRequestError, ResponsesClient  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import validate_visible_task  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    GlobalModelSlotLimiter,
    POOL_ID,
    validate_receipt as validate_slot_receipt,
)
from deepwide_agent.v24299_synthesis_recovery import (  # noqa: E402
    BoundedSynthesisRecoveryModel,
    validate_recovery_receipt,
)
from deepwide_agent.v24303_forward_contract import (  # noqa: E402
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
)
from scripts import v24300_neutral_synthesis_recovery as neutral  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


PROTOCOL_ID = "v24305_lowcap_neutral_recovery_reliability_v1"
PARENT = Path(
    "results/v24304_v24303_recovery_transport_postterminal_diagnosis_v1_20260803.json"
)
PROTOCOL = Path(
    "results/v24305_lowcap_neutral_recovery_preregistration_v1_20260803.json"
)
PREAUDIT = Path(
    "results/v24305_lowcap_neutral_recovery_preactivation_audit_v1_20260803.json"
)
ACTIVATION = Path(
    "results/v24305_lowcap_neutral_recovery_activation_v1_20260803.json"
)
EXECUTION_START = Path(
    "results/v24305_lowcap_neutral_recovery_execution_start_v1_20260803.json"
)
RESULT = Path(
    "results/v24305_lowcap_neutral_recovery_probe_v1_20260803.json"
)
DECISION = Path(
    "results/v24305_lowcap_neutral_recovery_decision_v1_20260803.json"
)
POSTAUDIT = Path(
    "results/v24305_lowcap_neutral_recovery_postresult_audit_v1_20260803.json"
)
LEASE_PATH = Path("outputs/deepwide_benchmark_api.lease.lock")
LEASE_OWNER = "v24305_lowcap_neutral_recovery_probe_v1"
LEASE_PURPOSE = "benchmark_external_lowcap_real_provider_recovery_reliability"
TASK_COUNT = 8
EXECUTOR_WORKERS = 8
SLOT_CAP = 2
MODEL_CALLS_PER_TASK = 3
TOTAL_EFFECTS = TASK_COUNT * MODEL_CALLS_PER_TASK
NONTRIVIAL_WAIT_SECONDS = 0.01
SOURCE_FILES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24299_synthesis_recovery.py",
    "src/deepwide_agent/v24303_forward_contract.py",
    "scripts/deepwide_api_lease.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/v24300_neutral_synthesis_recovery.py",
    "scripts/v24305_lowcap_neutral_recovery_reliability.py",
    "tests/test_v24299_synthesis_recovery.py",
    "tests/test_v24305_lowcap_neutral_recovery_reliability.py",
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")
CONTENT_LITERALS = (
    "NeutralWidget",
    "Return one Markdown table about this synthetic example only",
    "You create exact Markdown tables from synthetic facts only",
)
GATES = {
    "maximum_wall_seconds": 180.0,
    "required_task_count": TASK_COUNT,
    "required_executor_workers": EXECUTOR_WORKERS,
    "required_global_model_slot_cap": SLOT_CAP,
    "required_start_barrier_participants": TASK_COUNT,
    "required_recovery_tracker_entries": TASK_COUNT,
    "required_recovery_tracker_exits": TASK_COUNT,
    "required_recovery_tracker_active_final": 0,
    "required_peak_real_recovery_concurrency": SLOT_CAP,
    "maximum_peak_real_recovery_concurrency": SLOT_CAP,
    "required_recovery_successes": TASK_COUNT,
    "required_recovery_provider_failures": 0,
    "required_total_effects_admitted": TOTAL_EFFECTS,
    "required_logical_provider_requests": TOTAL_EFFECTS,
    "minimum_provider_attempts": TOTAL_EFFECTS,
    "required_slot_acquisitions": TOTAL_EFFECTS,
    "minimum_workers_with_nontrivial_slot_wait": 1,
    "required_fourth_provider_effects": 0,
    "required_search_calls": 0,
    "required_fetch_calls": 0,
}


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.43.05 path is noncanonical")
    path = root / raw
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.43.05 expected ordinary file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.43.05 expected object: {relative}")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise RuntimeError(f"V2.43.05 {label} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise RuntimeError(f"V2.43.05 {label} is invalid")
    return number


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
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            raise RuntimeError(f"V2.43.05 credential literal in {relative}")
        output[relative] = sha256(path)
    return output


def neutral_task(index: int) -> dict[str, str]:
    if isinstance(index, bool) or not isinstance(index, int) or not 1 <= index <= 8:
        raise ValueError("invalid V2.43.05 neutral task index")
    return {
        "opaque_id": f"task_{0x500 + index:024x}",
        "question": str(neutral.NEUTRAL_TASK["question"]),
    }


def _parent(root: Path) -> dict[str, Any]:
    value = _read(root, PARENT)
    if (
        value.get("role")
        != "v24304_v24303_recovery_transport_postterminal_diagnosis"
        or value.get("conclusions", {}).get("new_paired_dev64_authorized")
        is not False
        or value.get("conclusions", {}).get("exact220_authorized") is not False
        or value.get("concurrency_evidence", {}).get(
            "cap2_is_best_supported_next_transport_setting"
        )
        is not True
        or value.get("authorization", {}).get(
            "one_benchmark_external_low_cap_reliability_gate_design"
        )
        is not True
        or value.get("authorization", {}).get(
            "one_benchmark_external_low_cap_reliability_gate_launch"
        )
        is not False
        or not _sealed(value, "diagnosis_payload_sha256")
    ):
        raise RuntimeError("V2.43.05 parent diagnosis drifted")
    return value


class RecoveryConcurrencyTracker:
    """Count only real third-call recovery work while its GPT slot is held."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.active = 0
        self.peak = 0
        self.entries = 0
        self.exits = 0

    def enter(self) -> None:
        with self._lock:
            self.active += 1
            self.entries += 1
            self.peak = max(self.peak, self.active)

    def exit(self) -> None:
        with self._lock:
            if self.active <= 0:
                raise RuntimeError("V2.43.05 recovery tracker underflow")
            self.active -= 1
            self.exits += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                "entries": self.entries,
                "exits": self.exits,
                "active_final": self.active,
                "peak": self.peak,
            }


class LowCapNeutralFaultInjectedModel(neutral.NeutralFaultInjectedModel):
    """Add shared concurrency accounting around the real recovery request."""

    def __init__(self, real: Any, tracker: RecoveryConcurrencyTracker) -> None:
        super().__init__(real)
        self.tracker = tracker
        self.real_recovery_calls = 0
        self.real_recovery_failures = 0

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        if self._invocations < 2:
            return super().complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        self.real_recovery_calls += 1
        self.tracker.enter()
        try:
            return super().complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        except ModelRequestError:
            self.real_recovery_failures += 1
            raise
        finally:
            self.tracker.exit()


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    _parent(root)
    if require_pristine:
        present = [
            str(path)
            for path in (
                PREAUDIT,
                ACTIVATION,
                EXECUTION_START,
                RESULT,
                DECISION,
                POSTAUDIT,
            )
            if (root / path).exists() or (root / path).is_symlink()
        ]
        if present:
            raise RuntimeError(f"V2.43.05 future surface is not pristine: {present}")
    for index in range(1, TASK_COUNT + 1):
        validate_visible_task(neutral_task(index))
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24305_lowcap_neutral_recovery_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "eight_executor_two_global_gpt_slot_fault_injected_real_recoveries",
        "parent": {"path": str(PARENT), "sha256": sha256(root / PARENT)},
        "task_contract": {
            "task_count": TASK_COUNT,
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "all_tasks_validate_before_activation": True,
            "synthetic_neutral_tasks_only": True,
            "task_identifier_question_prompt_response_prediction_or_hash_persisted": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_opened": False,
        },
        "concurrency_contract": {
            "executor_workers": EXECUTOR_WORKERS,
            "shared_global_model_slot_cap": SLOT_CAP,
            "start_barrier_before_any_model_effect": True,
            "real_recovery_peak_measured_inside_global_slot": True,
            "recovery_only_independent_cap": None,
            "recovery_cooldown_seconds": 0,
        },
        "provider": {
            "proxy_url": "http://127.0.0.1:9878/responses",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "low",
            "service_tier": "priority",
            "timeout_seconds": 180,
            "max_retries": 2,
        },
        "budget_contract": {
            "model_calls_per_task": MODEL_CALLS_PER_TASK,
            "model_calls_total": TOTAL_EFFECTS,
            "recovery_may_use_only_unused_third_model_call": True,
            "fourth_model_effect_allowed": False,
            "search_calls_total": 0,
            "fetch_calls_total": 0,
            "token_budget_increased": False,
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
            "question_prompt_response_prediction_answer_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
        },
        "authorization": {
            "one_benchmark_external_lowcap_probe_design": True,
            "one_benchmark_external_lowcap_probe_launch": False,
            "benchmark_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "leaderboard_submission_or_sota_claim": False,
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
    auth = protocol.get("authorization")
    source = protocol.get("source_policy")
    if (
        protocol.get("role")
        != "v24305_lowcap_neutral_recovery_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope")
        != "eight_executor_two_global_gpt_slot_fault_injected_real_recoveries"
        or protocol.get("gates") != GATES
        or protocol.get("concurrency_contract", {}).get("executor_workers")
        != EXECUTOR_WORKERS
        or protocol.get("concurrency_contract", {}).get(
            "shared_global_model_slot_cap"
        )
        != SLOT_CAP
        or protocol.get("budget_contract", {}).get("model_calls_total")
        != TOTAL_EFFECTS
        or not _sealed(protocol, "protocol_payload_sha256")
        or not isinstance(manifest, Mapping)
        or set(manifest) != set(SOURCE_FILES)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or any(
            sha256(_ordinary(root, relative)) != digest
            for relative, digest in manifest.items()
        )
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(auth, Mapping)
        or auth.get("one_benchmark_external_lowcap_probe_design") is not True
        or any(
            setting
            for key, setting in auth.items()
            if key != "one_benchmark_external_lowcap_probe_design"
        )
    ):
        raise RuntimeError("V2.43.05 protocol drifted")
    _parent(root)
    if protocol.get("parent") != {
        "path": str(PARENT),
        "sha256": sha256(root / PARENT),
    }:
        raise RuntimeError("V2.43.05 parent binding drifted")
    for index in range(1, TASK_COUNT + 1):
        validate_visible_task(neutral_task(index))
    return protocol


def build_preactivation_audit(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    future = (ACTIVATION, EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    pristine = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in future
    )
    validated = sum(
        set(validate_visible_task(neutral_task(index))) == {"opaque_id", "question"}
        for index in range(1, TASK_COUNT + 1)
    )
    findings: list[str] = []
    if not pristine:
        findings.append("future_surface_not_pristine")
    if validated != TASK_COUNT:
        findings.append("visible_task_validation_incomplete")
    value = {
        "artifact_version": 1,
        "role": "v24305_lowcap_neutral_recovery_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": True,
            "surface_manifest_exact": True,
            "credential_literal_scan_clear": True,
            "validated_visible_tasks_before_effect": validated,
            "runtime_input_exactly_opaque_id_and_question": True,
            "benchmark_or_evaluator_surface_authorized": False,
            "future_surface_pristine": pristine,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "one_benchmark_external_lowcap_probe_launch": not findings,
            "benchmark_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_preactivation_audit(root, value=value)
    return value


def validate_preactivation_audit(
    root: Path = ROOT, *, value: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    root = root.resolve()
    audit = dict(value) if value is not None else _read(root, PREAUDIT)
    if (
        audit.get("role")
        != "v24305_lowcap_neutral_recovery_preactivation_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or audit.get("findings") != []
        or audit.get("audit_valid") is not True
        or audit.get("checks", {}).get("validated_visible_tasks_before_effect")
        != TASK_COUNT
        or audit.get("authorization", {}).get(
            "one_benchmark_external_lowcap_probe_launch"
        )
        is not True
        or any(
            setting
            for key, setting in audit.get("authorization", {}).items()
            if key != "one_benchmark_external_lowcap_probe_launch"
        )
        or audit.get("provenance", {}).get("protocol_sha256")
        != sha256(root / PROTOCOL)
        or not _sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.05 preactivation audit drifted")
    return audit


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preactivation_audit(root)
    present = [
        str(path)
        for path in (EXECUTION_START, RESULT, DECISION, POSTAUDIT)
        if (root / path).exists() or (root / path).is_symlink()
    ]
    lease = lease_observation(root, Path("/proc"))
    watchers = protected_watcher_snapshot()
    findings: list[str] = []
    if present:
        findings.append("future_surface_not_pristine")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    value = {
        "artifact_version": 1,
        "role": "v24305_lowcap_neutral_recovery_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        "executor_workers": EXECUTOR_WORKERS,
        "model_slot_cap": SLOT_CAP,
        "protected_watchers": watchers,
        "shared_api_lease_active_before_activation": lease.get("active"),
        "network_model_search_fetch_evaluator_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "authorization": {
            "one_benchmark_external_lowcap_probe_launch": not findings,
            "benchmark_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
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
        activation.get("role") != "v24305_lowcap_neutral_recovery_activation"
        or activation.get("protocol_id") != PROTOCOL_ID
        or activation.get("status") != "active"
        or activation.get("findings") != []
        or activation.get("launch_authorized") is not True
        or activation.get("protocol_sha256") != sha256(root / PROTOCOL)
        or activation.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or activation.get("executor_workers") != EXECUTOR_WORKERS
        or activation.get("model_slot_cap") != SLOT_CAP
        or activation.get("protected_watchers") != protected_watcher_snapshot()
        or activation.get("shared_api_lease_active_before_activation") is not False
        or activation.get("network_model_search_fetch_evaluator_or_api_called")
        is not False
        or activation.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or activation.get("authorization", {}).get(
            "one_benchmark_external_lowcap_probe_launch"
        )
        is not True
        or any(
            setting
            for key, setting in activation.get("authorization", {}).items()
            if key != "one_benchmark_external_lowcap_probe_launch"
        )
        or not _sealed(activation, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.43.05 activation drifted")
    validate_protocol(root)
    validate_preactivation_audit(root)
    return activation


def _execute_worker(
    index: int,
    *,
    real: Any,
    slot_directory: Path,
    output_root: Path,
    tracker: RecoveryConcurrencyTracker,
    start_barrier: threading.Barrier,
) -> dict[str, Any]:
    started = time.monotonic()
    validate_visible_task(neutral_task(index))
    injected = LowCapNeutralFaultInjectedModel(real, tracker)
    limited = GlobalModelSlotLimiter(
        injected,
        slot_directory=slot_directory,
        output_root=output_root,
        slot_cap=SLOT_CAP,
        pool_id=POOL_ID,
    )
    model = BoundedSynthesisRecoveryModel(
        limited, arm="candidate", model_call_cap=MODEL_CALLS_PER_TASK
    )
    barrier_passed = False
    failure_type: str | None = None
    try:
        start_barrier.wait(timeout=30.0)
        barrier_passed = True
        model.complete("", "", max_output_tokens=4_000, json_mode=True)
        model.complete("", "", max_output_tokens=30_000, json_mode=False)
    except ModelRequestError:
        failure_type = "recovery_provider_model_request_error"
    except threading.BrokenBarrierError:
        failure_type = "start_barrier_broken"
    except Exception:
        failure_type = "unexpected_worker_exception"
    recovery = model.receipt()
    validate_recovery_receipt(recovery)
    slot = validate_slot_receipt(
        limited.receipt(),
        expected_cap=SLOT_CAP,
        expected_acquisitions=int(recovery["provider_requests_delta"]),
    )
    if recovery["synthesis_recovery_succeeded"]:
        outcome = "recovery_success"
    elif recovery["synthesis_recovery_model_request_error"]:
        outcome = "recovery_provider_failure"
    else:
        outcome = "unexpected_failure"
    value = {
        "worker_index": index,
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "outcome": outcome,
        "failure_type": failure_type,
        "start_barrier_passed": barrier_passed,
        "model_budget": {
            "limit": MODEL_CALLS_PER_TASK,
            "effects_by_stage": dict(recovery["effects_by_stage"]),
            "admitted": recovery["total_effects_admitted"],
            "logical_provider_requests": recovery["provider_requests_delta"],
            "provider_attempts": recovery["provider_attempts_delta"],
            "slot_cap": slot["slot_cap"],
            "slot_acquisitions": slot["acquisitions"],
            "slot_acquisition_counts": slot["slot_acquisition_counts"],
            "slot_wait_seconds": slot["total_wait_seconds"],
            "slot_max_wait_seconds": slot["max_wait_seconds"],
            "fourth_provider_effect": recovery["total_effects_admitted"] > 3,
        },
        "recovery": {
            "initial_synthesis_model_request_error": recovery[
                "synthesis_initial_model_request_error"
            ],
            "attempted": recovery["synthesis_recovery_attempted"],
            "succeeded": recovery["synthesis_recovery_succeeded"],
            "provider_failure": recovery["synthesis_recovery_model_request_error"],
            "real_calls": injected.real_recovery_calls,
            "real_successes": injected.real_recovery_requests,
            "real_failures": injected.real_recovery_failures,
        },
        "search": {"calls": 0, "fetch_calls": 0},
    }
    validate_worker_projection(value)
    return value


def _worker(
    index: int,
    *,
    provider: Mapping[str, Any],
    slot_directory: Path,
    output_root: Path,
    tracker: RecoveryConcurrencyTracker,
    start_barrier: threading.Barrier,
) -> dict[str, Any]:
    real = ResponsesClient(
        str(provider["proxy_url"]),
        str(provider["model"]),
        reasoning_effort=str(provider["reasoning_effort"]),
        service_tier=str(provider["service_tier"]),
        timeout=int(provider["timeout_seconds"]),
        max_retries=int(provider["max_retries"]),
    )
    return _execute_worker(
        index,
        real=real,
        slot_directory=slot_directory,
        output_root=output_root,
        tracker=tracker,
        start_barrier=start_barrier,
    )


def validate_worker_projection(value: Mapping[str, Any]) -> None:
    index = value.get("worker_index")
    budget = value.get("model_budget")
    recovery = value.get("recovery")
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or not 1 <= index <= TASK_COUNT
        or value.get("outcome")
        not in {"recovery_success", "recovery_provider_failure", "unexpected_failure"}
        or value.get("failure_type")
        not in {
            None,
            "recovery_provider_model_request_error",
            "start_barrier_broken",
            "unexpected_worker_exception",
        }
        or not isinstance(value.get("start_barrier_passed"), bool)
        or not isinstance(budget, Mapping)
        or not isinstance(recovery, Mapping)
        or value.get("search") != {"calls": 0, "fetch_calls": 0}
    ):
        raise RuntimeError("V2.43.05 worker projection drifted")
    _finite(value.get("wall_seconds"), "worker wall seconds")
    effects = budget.get("effects_by_stage")
    admitted = budget.get("admitted")
    requests = budget.get("logical_provider_requests")
    attempts = budget.get("provider_attempts")
    acquisitions = budget.get("slot_acquisitions")
    counts = budget.get("slot_acquisition_counts")
    if (
        budget.get("limit") != MODEL_CALLS_PER_TASK
        or not isinstance(effects, Mapping)
        or set(effects) != {"plan", "synthesis_initial", "synthesis_recovery", "repair"}
        or any(
            isinstance(number, bool) or not isinstance(number, int) or number not in {0, 1}
            for number in effects.values()
        )
        or isinstance(admitted, bool)
        or not isinstance(admitted, int)
        or admitted != sum(effects.values())
        or not 0 <= admitted <= MODEL_CALLS_PER_TASK
        or requests != admitted
        or isinstance(attempts, bool)
        or not isinstance(attempts, int)
        or attempts < requests
        or budget.get("slot_cap") != SLOT_CAP
        or acquisitions != requests
        or not isinstance(counts, list)
        or len(counts) != SLOT_CAP
        or sum(counts) != acquisitions
        or any(isinstance(count, bool) or not isinstance(count, int) or count < 0 for count in counts)
        or budget.get("fourth_provider_effect") is not False
        or recovery.get("real_calls") not in {0, 1}
        or recovery.get("real_successes") not in {0, 1}
        or recovery.get("real_failures") not in {0, 1}
        or recovery.get("real_successes") + recovery.get("real_failures")
        != recovery.get("real_calls")
        or recovery.get("succeeded")
        is not (value.get("outcome") == "recovery_success")
        or recovery.get("provider_failure")
        is not (value.get("outcome") == "recovery_provider_failure")
    ):
        raise RuntimeError("V2.43.05 worker accounting drifted")
    _finite(budget.get("slot_wait_seconds"), "slot wait seconds")
    _finite(budget.get("slot_max_wait_seconds"), "slot max wait seconds")


def _aggregate(
    workers: Sequence[Mapping[str, Any]], tracker: Mapping[str, int]
) -> dict[str, Any]:
    effects = {stage: 0 for stage in ("plan", "synthesis_initial", "synthesis_recovery", "repair")}
    for worker in workers:
        for stage, count in worker["model_budget"]["effects_by_stage"].items():
            effects[stage] += int(count)
    return {
        "task_count": len(workers),
        "executor_workers": EXECUTOR_WORKERS,
        "start_barrier_participants": sum(
            worker["start_barrier_passed"] is True for worker in workers
        ),
        "global_model_slot_cap": SLOT_CAP,
        "recovery_tracker": dict(tracker),
        "recovery_successes": sum(
            worker["outcome"] == "recovery_success" for worker in workers
        ),
        "recovery_provider_failures": sum(
            worker["outcome"] == "recovery_provider_failure" for worker in workers
        ),
        "unexpected_failures": sum(
            worker["outcome"] == "unexpected_failure" for worker in workers
        ),
        "effects_by_stage": effects,
        "total_effects_admitted": sum(
            int(worker["model_budget"]["admitted"]) for worker in workers
        ),
        "logical_provider_requests": sum(
            int(worker["model_budget"]["logical_provider_requests"])
            for worker in workers
        ),
        "provider_attempts": sum(
            int(worker["model_budget"]["provider_attempts"])
            for worker in workers
        ),
        "slot_acquisitions": sum(
            int(worker["model_budget"]["slot_acquisitions"]) for worker in workers
        ),
        "workers_with_nontrivial_slot_wait": sum(
            float(worker["model_budget"]["slot_wait_seconds"])
            >= NONTRIVIAL_WAIT_SECONDS
            for worker in workers
        ),
        "total_slot_wait_seconds": round(
            sum(float(worker["model_budget"]["slot_wait_seconds"]) for worker in workers),
            6,
        ),
        "maximum_worker_slot_wait_seconds": round(
            max(
                (float(worker["model_budget"]["slot_wait_seconds"]) for worker in workers),
                default=0.0,
            ),
            6,
        ),
        "fourth_provider_effects": sum(
            worker["model_budget"]["fourth_provider_effect"] is True
            for worker in workers
        ),
        "real_recovery_calls": sum(
            int(worker["recovery"]["real_calls"]) for worker in workers
        ),
        "real_recovery_successes": sum(
            int(worker["recovery"]["real_successes"]) for worker in workers
        ),
        "real_recovery_failures": sum(
            int(worker["recovery"]["real_failures"]) for worker in workers
        ),
        "search_calls": 0,
        "fetch_calls": 0,
        "task_wall_sum_seconds": round(
            sum(float(worker["wall_seconds"]) for worker in workers), 6
        ),
    }


def project(
    workers: Sequence[Mapping[str, Any]],
    *,
    tracker: Mapping[str, int],
    wall_seconds: float,
    now: int | None = None,
) -> dict[str, Any]:
    ordered = [
        dict(worker)
        for worker in sorted(workers, key=lambda row: int(row["worker_index"]))
    ]
    for worker in ordered:
        validate_worker_projection(worker)
    value = {
        "artifact_version": 1,
        "role": "v24305_lowcap_neutral_recovery_probe",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "eight_executor_two_global_gpt_slot_fault_injected_real_recoveries_only",
        "provider": "azure-native-keyless-gpt-5.6-sol",
        "wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "observed": _aggregate(ordered, tracker),
        "workers": ordered,
        "source_policy": {
            "synthetic_neutral_tasks_used_but_not_persisted_or_hashed": True,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "question_prompt_response_prediction_answer_opaque_id_or_hash_persisted": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "shared_api_lease_acquired": True,
        },
        "authorization": {
            "benchmark_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["result_payload_sha256"] = payload_sha256(value)
    validate_projection(value)
    return value


def validate_projection(value: Mapping[str, Any]) -> None:
    workers = value.get("workers")
    observed = value.get("observed")
    source = value.get("source_policy")
    auth = value.get("authorization")
    if (
        value.get("role") != "v24305_lowcap_neutral_recovery_probe"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("scope")
        != "eight_executor_two_global_gpt_slot_fault_injected_real_recoveries_only"
        or value.get("provider") != "azure-native-keyless-gpt-5.6-sol"
        or not _sealed(value, "result_payload_sha256")
        or not isinstance(workers, list)
        or len(workers) != TASK_COUNT
        or [worker.get("worker_index") for worker in workers]
        != list(range(1, TASK_COUNT + 1))
        or not isinstance(observed, Mapping)
        or not isinstance(source, Mapping)
        or source.get("synthetic_neutral_tasks_used_but_not_persisted_or_hashed")
        is not True
        or source.get("shared_api_lease_acquired") is not True
        or any(
            setting
            for key, setting in source.items()
            if key
            not in {
                "synthetic_neutral_tasks_used_but_not_persisted_or_hashed",
                "shared_api_lease_acquired",
            }
        )
        or not isinstance(auth, Mapping)
        or any(auth.values())
    ):
        raise RuntimeError("V2.43.05 projection drifted")
    _finite(value.get("wall_seconds"), "wall seconds")
    for worker in workers:
        validate_worker_projection(worker)
    tracker = observed.get("recovery_tracker")
    if not isinstance(tracker, Mapping) or dict(observed) != _aggregate(workers, tracker):
        raise RuntimeError("V2.43.05 aggregate projection drifted")
    encoded = json.dumps(value, ensure_ascii=False)
    if (
        SECRET.search(encoded)
        or OPAQUE.search(encoded)
        or any(literal in encoded for literal in CONTENT_LITERALS)
    ):
        raise RuntimeError("V2.43.05 result persisted prohibited content")


def _execution_start(root: Path, activation: Mapping[str, Any]) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24305_lowcap_neutral_recovery_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "activation_sha256": sha256(root / ACTIVATION),
        "executor_workers": EXECUTOR_WORKERS,
        "model_slot_cap": SLOT_CAP,
        "protected_watchers": activation["protected_watchers"],
        "shared_api_lease_acquired": True,
        "api_called_before_execution_start": False,
        "runtime_input_exactly_opaque_id_and_question": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "benchmark_dev64_exact220_evaluator_or_sota_authorized": False,
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    return value


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preactivation_audit(root)
    activation = validate_activation(root)
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (EXECUTION_START, RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.43.05 execution surface is not pristine")
    output_root = root / "outputs"
    started = time.monotonic()
    lease = protocol["lease"]
    with acquire_deepwide_api_lease(
        root,
        owner=str(lease["owner"]),
        purpose=str(lease["purpose"]),
        path=root / str(lease["path"]),
    ):
        publish(root / EXECUTION_START, _execution_start(root, activation))
        with tempfile.TemporaryDirectory(dir=output_root) as directory:
            slots = Path(directory)
            for index in range(1, SLOT_CAP + 1):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            tracker = RecoveryConcurrencyTracker()
            start_barrier = threading.Barrier(TASK_COUNT)
            workers: list[dict[str, Any]] = []
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=EXECUTOR_WORKERS, thread_name_prefix="v24305-lowcap"
            ) as executor:
                futures = {
                    executor.submit(
                        _worker,
                        index,
                        provider=protocol["provider"],
                        slot_directory=slots,
                        output_root=output_root,
                        tracker=tracker,
                        start_barrier=start_barrier,
                    ): index
                    for index in range(1, TASK_COUNT + 1)
                }
                for future in concurrent.futures.as_completed(futures):
                    workers.append(future.result())
            value = project(
                workers,
                tracker=tracker.snapshot(),
                wall_seconds=max(0.0, time.monotonic() - started),
            )
            publish(root / RESULT, value)
    return value


def _checks(result: Mapping[str, Any], gates: Mapping[str, Any]) -> dict[str, bool]:
    observed = result["observed"]
    tracker = observed["recovery_tracker"]
    return {
        "wall_seconds": float(result["wall_seconds"]) <= gates["maximum_wall_seconds"],
        "task_count": observed["task_count"] == gates["required_task_count"],
        "executor_workers": observed["executor_workers"]
        == gates["required_executor_workers"],
        "global_model_slot_cap": observed["global_model_slot_cap"]
        == gates["required_global_model_slot_cap"],
        "start_barrier_participants": observed["start_barrier_participants"]
        == gates["required_start_barrier_participants"],
        "recovery_tracker_entries": tracker["entries"]
        == gates["required_recovery_tracker_entries"],
        "recovery_tracker_exits": tracker["exits"]
        == gates["required_recovery_tracker_exits"],
        "recovery_tracker_active_final": tracker["active_final"]
        == gates["required_recovery_tracker_active_final"],
        "minimum_peak_real_recovery_concurrency": tracker["peak"]
        >= gates["required_peak_real_recovery_concurrency"],
        "maximum_peak_real_recovery_concurrency": tracker["peak"]
        <= gates["maximum_peak_real_recovery_concurrency"],
        "recovery_successes": observed["recovery_successes"]
        == gates["required_recovery_successes"],
        "recovery_provider_failures": observed["recovery_provider_failures"]
        == gates["required_recovery_provider_failures"],
        "unexpected_failures": observed["unexpected_failures"] == 0,
        "total_effects_admitted": observed["total_effects_admitted"]
        == gates["required_total_effects_admitted"],
        "logical_provider_requests": observed["logical_provider_requests"]
        == gates["required_logical_provider_requests"],
        "provider_attempts": observed["provider_attempts"]
        >= gates["minimum_provider_attempts"],
        "slot_acquisitions": observed["slot_acquisitions"]
        == gates["required_slot_acquisitions"],
        "workers_with_nontrivial_slot_wait": observed[
            "workers_with_nontrivial_slot_wait"
        ]
        >= gates["minimum_workers_with_nontrivial_slot_wait"],
        "fourth_provider_effects": observed["fourth_provider_effects"]
        == gates["required_fourth_provider_effects"],
        "search_calls": observed["search_calls"] == gates["required_search_calls"],
        "fetch_calls": observed["fetch_calls"] == gates["required_fetch_calls"],
    }


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preactivation_audit(root)
    validate_activation(root)
    result = _read(root, RESULT)
    validate_projection(result)
    checks = _checks(result, protocol["gates"])
    failed = sorted(name for name, passed in checks.items() if not passed)
    passed = not failed
    value = {
        "artifact_version": 1,
        "role": "v24305_lowcap_neutral_recovery_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "lowcap_neutral_reliability_go" if passed else "lowcap_neutral_reliability_no_go",
        "passed": passed,
        "checks": checks,
        "failed_checks": failed,
        "observed": {"wall_seconds": result["wall_seconds"], **dict(result["observed"])},
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
            "eight_executor_two_gpt_slot_fault_injected_recovery_reliability": True,
            "natural_failure_frequency_measured": False,
            "benchmark_quality_measured": False,
            "causal_quality_improvement_proven": False,
            "sota_supported": False,
        },
        "authorization": {
            "successor_fresh_paired_dev64_design": passed,
            "successor_fresh_paired_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["decision_payload_sha256"] = payload_sha256(value)
    validate_decision(value)
    return value


def validate_decision(value: Mapping[str, Any]) -> None:
    checks = value.get("checks")
    failed = value.get("failed_checks")
    claim = value.get("claim_scope")
    auth = value.get("authorization")
    if (
        value.get("role") != "v24305_lowcap_neutral_recovery_decision"
        or value.get("protocol_id") != PROTOCOL_ID
        or not isinstance(checks, Mapping)
        or not isinstance(failed, list)
        or value.get("passed") is not all(checks.values())
        or failed != sorted(name for name, passed in checks.items() if not passed)
        or value.get("status")
        != ("lowcap_neutral_reliability_go" if value["passed"] else "lowcap_neutral_reliability_no_go")
        or not isinstance(claim, Mapping)
        or claim.get("eight_executor_two_gpt_slot_fault_injected_recovery_reliability")
        is not True
        or any(
            setting
            for key, setting in claim.items()
            if key != "eight_executor_two_gpt_slot_fault_injected_recovery_reliability"
        )
        or not isinstance(auth, Mapping)
        or auth.get("successor_fresh_paired_dev64_design") is not value["passed"]
        or any(
            setting
            for key, setting in auth.items()
            if key != "successor_fresh_paired_dev64_design"
        )
        or not _sealed(value, "decision_payload_sha256")
    ):
        raise RuntimeError("V2.43.05 decision drifted")


def build_postresult_audit(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    validate_preactivation_audit(root)
    activation = validate_activation(root)
    result = _read(root, RESULT)
    decision = _read(root, DECISION)
    validate_projection(result)
    validate_decision(decision)
    lease = lease_observation(root, Path("/proc"))
    findings: list[str] = []
    encoded = json.dumps({"result": result, "decision": decision}, ensure_ascii=False)
    if SECRET.search(encoded):
        findings.append("credential_literal_persisted")
    if OPAQUE.search(encoded) or any(literal in encoded for literal in CONTENT_LITERALS):
        findings.append("task_identity_or_content_persisted")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active_after_result")
    if protected_watcher_snapshot() != activation["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    if decision.get("provenance", {}).get("result_sha256") != sha256(root / RESULT):
        findings.append("decision_result_binding_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24305_lowcap_neutral_recovery_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "findings": findings,
        "audit_valid": not findings,
        "execution_closure": {
            "shared_api_lease_active": lease.get("active"),
            "protected_watchers_unchanged": protected_watcher_snapshot()
            == activation["protected_watchers"],
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "task_identifier_question_prompt_response_prediction_answer_or_hash_persisted": False,
            "credential_value_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "resume_retry_skip_or_revaluation": False,
            "invalid_result_path": None,
        },
        "authorization": {
            "successor_fresh_paired_dev64_design": bool(decision["passed"] and not findings),
            "successor_fresh_paired_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "result_sha256": sha256(root / RESULT),
            "decision_sha256": sha256(root / DECISION),
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_postresult_audit(value, decision_passed=bool(decision["passed"]))
    return value


def validate_postresult_audit(
    value: Mapping[str, Any], *, decision_passed: bool
) -> None:
    auth = value.get("authorization")
    if (
        value.get("role") != "v24305_lowcap_neutral_recovery_postresult_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("execution_closure", {}).get("shared_api_lease_active") is not False
        or value.get("execution_closure", {}).get("protected_watchers_unchanged")
        is not True
        or value.get("execution_closure", {}).get("invalid_result_path") is not None
        or not isinstance(auth, Mapping)
        or auth.get("successor_fresh_paired_dev64_design") is not decision_passed
        or any(
            setting
            for key, setting in auth.items()
            if key != "successor_fresh_paired_dev64_design"
        )
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.05 postresult audit drifted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("preregister", "preaudit", "activate", "probe", "finalize", "postaudit"),
    )
    args = parser.parse_args()
    if args.action == "preregister":
        value, path = build_protocol(), PROTOCOL
    elif args.action == "preaudit":
        value, path = build_preactivation_audit(), PREAUDIT
    elif args.action == "activate":
        value, path = build_activation(), ACTIVATION
    elif args.action == "probe":
        value = run_probe()
        print(
            json.dumps(
                {
                    "path": str(RESULT),
                    "wall_seconds": value["wall_seconds"],
                    "recovery_successes": value["observed"]["recovery_successes"],
                    "peak_real_recovery_concurrency": value["observed"][
                        "recovery_tracker"
                    ]["peak"],
                },
                sort_keys=True,
            )
        )
        return
    elif args.action == "finalize":
        value, path = build_decision(), DECISION
    else:
        value, path = build_postresult_audit(), POSTAUDIT
    publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
