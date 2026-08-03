#!/usr/bin/env python3
"""Seal V2.43.01 zero-effect rejection and gate its corrected successor."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import validate_visible_task  # noqa: E402
from scripts import v24301_neutral_concurrent_synthesis_recovery as parent  # noqa: E402


PROTOCOL_ID = "v24302_corrected_neutral_concurrent_bounded_synthesis_recovery_v1"
FAILURE = Path(
    "results/v24301_neutral_concurrent_synthesis_recovery_zero_effect_failure_v1_20260803.json"
)
PROTOCOL = Path(
    "results/v24302_neutral_concurrent_synthesis_recovery_preregistration_v1_20260803.json"
)
PREAUDIT = Path(
    "results/v24302_neutral_concurrent_synthesis_recovery_preactivation_audit_v1_20260803.json"
)
RESULT = Path(
    "results/v24302_neutral_concurrent_synthesis_recovery_probe_v1_20260803.json"
)
DECISION = Path(
    "results/v24302_neutral_concurrent_synthesis_recovery_decision_v1_20260803.json"
)
POSTAUDIT = Path(
    "results/v24302_neutral_concurrent_synthesis_recovery_postresult_audit_v1_20260803.json"
)
TASK_COUNT = parent.TASK_COUNT
SLOT_CAP = parent.SLOT_CAP
TOTAL_EFFECTS = parent.TOTAL_EFFECTS
EXPECTED_FAILURE = "invalid opaque task identifier"
PROTECTED_WATCHERS = {
    795336: "scripts/watch_v2415_r1_checkpoint_liveness.py",
    3061652: "scripts/watch_v24218_exact220_executor.py",
}
SOURCE_FILES = (
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24299_synthesis_recovery.py",
    "scripts/v24300_neutral_synthesis_recovery.py",
    "scripts/v24301_neutral_concurrent_synthesis_recovery.py",
    "scripts/v24302_neutral_concurrent_synthesis_recovery.py",
    "tests/test_v24299_synthesis_recovery.py",
    "tests/test_v24300_neutral_synthesis_recovery.py",
    "tests/test_v24301_neutral_concurrent_synthesis_recovery.py",
    "tests/test_v24302_neutral_concurrent_synthesis_recovery.py",
)
GATES = dict(parent.GATES)
GATES["required_validated_visible_tasks_before_effect"] = TASK_COUNT


sha256 = parent.sha256
payload_sha256 = parent.payload_sha256
publish = parent.publish


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
        raise RuntimeError(f"V2.43.02 expected ordinary file: {relative}")
    return path


def _read(root: Path, relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(root, relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.43.02 expected object: {relative}")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if parent.SECRET.search(source):
            raise RuntimeError(f"V2.43.02 credential literal in {relative}")
        output[relative] = sha256(path)
    return output


def corrected_neutral_task(index: int) -> dict[str, str]:
    if isinstance(index, bool) or not isinstance(index, int) or not 1 <= index <= TASK_COUNT:
        raise ValueError("invalid V2.43.02 neutral task index")
    return {
        "opaque_id": f"task_{index:024x}",
        "question": str(parent.parent_gate.NEUTRAL_TASK["question"]),
    }


def _parent_protocol(root: Path) -> dict[str, Any]:
    return parent.validate_protocol(root)


def _parent_preaudit(root: Path) -> dict[str, Any]:
    return parent.validate_preactivation_audit(root)


def _protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for pid, marker in PROTECTED_WATCHERS.items():
        stat_path = proc_root / str(pid) / "stat"
        cmdline_path = proc_root / str(pid) / "cmdline"
        if not stat_path.is_file() or not cmdline_path.is_file():
            raise RuntimeError("V2.43.02 protected watcher is absent")
        raw = stat_path.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        cmdline = cmdline_path.read_bytes().replace(b"\x00", b" ").decode(
            "utf-8", errors="replace"
        )
        if len(suffix) <= 19 or marker not in cmdline:
            raise RuntimeError("V2.43.02 protected watcher identity drifted")
        output.append(
            {"pid": pid, "marker": marker, "start_ticks": int(suffix[19])}
        )
    return output


def _released_parent_lease(root: Path) -> dict[str, Any]:
    protocol = _parent_protocol(root)
    path = root / str(protocol["lease"]["path"])
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.43.02 parent lease observation is absent")
    with path.open("r+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("V2.43.02 shared API lease remains active") from exc
        try:
            handle.seek(0)
            value = json.loads(handle.read(4096))
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    if (
        not isinstance(value, dict)
        or value.get("owner") != protocol["lease"]["owner"]
        or value.get("purpose") != protocol["lease"]["purpose"]
        or value.get("active") is not False
        or not isinstance(value.get("pid"), int)
        or not isinstance(value.get("acquired_at_unix"), int)
        or not isinstance(value.get("released_at_unix"), int)
        or value["released_at_unix"] < value["acquired_at_unix"]
        or (Path("/proc") / str(value["pid"])).exists()
    ):
        raise RuntimeError("V2.43.02 parent lease release record drifted")
    return value


def build_failure_receipt(
    root: Path = ROOT,
    *,
    now: int | None = None,
    lease_record: Mapping[str, Any] | None = None,
    protected_watchers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    protocol = _parent_protocol(root)
    _parent_preaudit(root)
    residue = [
        str(path)
        for path in (parent.RESULT, parent.DECISION, parent.POSTAUDIT)
        if (root / path).exists() or (root / path).is_symlink()
    ]
    effects = {
        "model_calls": 0,
        "provider_requests": 0,
        "slot_acquisitions": 0,
        "search_calls": 0,
        "fetch_calls": 0,
        "evaluator_calls": 0,
    }
    lease = (
        _released_parent_lease(root)
        if lease_record is None
        else dict(lease_record)
    )
    watchers = (
        _protected_watcher_snapshot()
        if protected_watchers is None
        else [dict(value) for value in protected_watchers]
    )
    if (
        residue
        or lease.get("owner") != protocol["lease"]["owner"]
        or lease.get("purpose") != protocol["lease"]["purpose"]
        or lease.get("active") is not False
        or len(watchers) != len(PROTECTED_WATCHERS)
        or {row.get("pid"): row.get("marker") for row in watchers}
        != PROTECTED_WATCHERS
    ):
        raise RuntimeError("V2.43.02 zero-effect failure boundary is not clean")
    try:
        validate_visible_task(parent.neutral_task(1))
    except ValueError as exc:
        if str(exc) != EXPECTED_FAILURE:
            raise RuntimeError("V2.43.02 parent rejection signature drifted") from exc
    else:
        raise RuntimeError("V2.43.02 parent invalid task unexpectedly validated")
    value = {
        "artifact_version": 1,
        "role": "v24301_neutral_concurrent_synthesis_recovery_zero_effect_failure",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_protocol": {
            "path": str(parent.PROTOCOL),
            "sha256": sha256(root / parent.PROTOCOL),
            "protocol_payload_sha256": protocol["protocol_payload_sha256"],
        },
        "parent_preactivation_audit": {
            "path": str(parent.PREAUDIT),
            "sha256": sha256(root / parent.PREAUDIT),
        },
        "failure": {
            "class": "ValueError",
            "message": EXPECTED_FAILURE,
            "stage": "visible_task_validation_before_first_effect",
            "rejected_field": "opaque_id",
            "invalid_value_or_hash_persisted": False,
            "runner_traceback_or_task_content_persisted": False,
        },
        "effect_ledger": effects,
        "shared_api_lease": {
            "acquisitions": 1,
            "owner": lease["owner"],
            "purpose": lease["purpose"],
            "acquired_at_unix": lease.get("acquired_at_unix"),
            "released_at_unix": lease.get("released_at_unix"),
            "active_after_failure": False,
            "observation_sha256": payload_sha256(lease),
        },
        "result_decision_or_postaudit_created": False,
        "shared_api_lease_released_and_nonblocking_probe_free": True,
        "protected_watchers_preserved": watchers,
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "same_protocol_retry_or_resume_authorized": False,
        "new_versioned_successor_required": True,
    }
    value["failure_payload_sha256"] = payload_sha256(value)
    validate_failure(value)
    return value


def validate_failure(value: Mapping[str, Any]) -> None:
    ledger = value.get("effect_ledger")
    if (
        value.get("role")
        != "v24301_neutral_concurrent_synthesis_recovery_zero_effect_failure"
        or not _sealed(value, "failure_payload_sha256")
        or value.get("failure", {}).get("message") != EXPECTED_FAILURE
        or value.get("failure", {}).get("stage")
        != "visible_task_validation_before_first_effect"
        or not isinstance(ledger, Mapping)
        or any(ledger.values())
        or value.get("result_decision_or_postaudit_created") is not False
        or value.get("shared_api_lease_released_and_nonblocking_probe_free") is not True
        or not isinstance(value.get("protected_watchers_preserved"), list)
        or len(value["protected_watchers_preserved"]) != len(PROTECTED_WATCHERS)
        or value.get("shared_api_lease", {}).get("acquisitions") != 1
        or value.get("shared_api_lease", {}).get("active_after_failure") is not False
        or value.get("same_protocol_retry_or_resume_authorized") is not False
        or value.get("new_versioned_successor_required") is not True
    ):
        raise RuntimeError("V2.43.02 failure receipt drifted")


def _failure(root: Path) -> dict[str, Any]:
    value = _read(root, FAILURE)
    validate_failure(value)
    return value


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    failure = _failure(root)
    if require_pristine:
        present = [
            str(path)
            for path in (PREAUDIT, RESULT, DECISION, POSTAUDIT)
            if (root / path).exists() or (root / path).is_symlink()
        ]
        if present:
            raise RuntimeError(f"V2.43.02 future surface is not pristine: {present}")
    for index in range(1, TASK_COUNT + 1):
        validate_visible_task(corrected_neutral_task(index))
    manifest = _manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24302_neutral_concurrent_synthesis_recovery_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "corrected_eight_independent_fault_injected_neutral_real_provider_recoveries",
        "parents": {
            "v24301_protocol": {
                "path": str(parent.PROTOCOL),
                "sha256": sha256(root / parent.PROTOCOL),
            },
            "v24301_preactivation_audit": {
                "path": str(parent.PREAUDIT),
                "sha256": sha256(root / parent.PREAUDIT),
            },
            "v24301_zero_effect_failure": {
                "path": str(FAILURE),
                "sha256": sha256(root / FAILURE),
                "failure_payload_sha256": failure["failure_payload_sha256"],
            },
        },
        "correction": {
            "single_change": "replace_invalid_readable_neutral_opaque_ids_with_task_plus_24_lowercase_hex_digits",
            "all_eight_corrected_tasks_pass_validate_visible_task_before_activation": True,
            "task_questions_model_prompt_fault_injection_provider_budget_concurrency_slots_barrier_and_gates_unchanged": True,
            "parent_protocol_retry_or_resume": False,
            "append_only_successor": True,
        },
        "task_contract": {
            "task_count": TASK_COUNT,
            "runtime_input_keys_exactly_opaque_id_and_question": True,
            "validated_visible_tasks_before_effect": TASK_COUNT,
            "synthetic_neutral_tasks_only": True,
            "task_identifier_question_prompt_plan_response_prediction_or_hash_persisted": False,
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_or_score_opened": False,
        },
        "concurrency_contract": {
            "executor_workers": TASK_COUNT,
            "shared_global_model_slot_cap": SLOT_CAP,
            "barrier_inside_recovery_complete_after_global_slot_acquisition": True,
            "all_workers_must_hold_one_shared_slot_before_real_recovery": True,
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
            "model_calls_per_task": 3,
            "model_calls_total": TOTAL_EFFECTS,
            "search_queries_per_task": 4,
            "fetch_targets_per_task": 10,
            "recovery_may_use_only_unused_third_model_call": True,
            "fourth_model_effect_allowed": False,
        },
        "gates": dict(GATES),
        "lease": {
            "path": "outputs/deepwide_benchmark_api.lease.lock",
            "owner": "v24302_neutral_concurrent_synthesis_recovery_probe_v1",
            "purpose": "corrected_neutral_concurrent_real_provider_bounded_synthesis_recovery",
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
            "one_corrected_neutral_concurrency_probe": True,
            "parent_retry_or_resume": False,
            "benchmark_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
            "training_credit_assignment": False,
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
    source = protocol.get("source_policy")
    auth = protocol.get("authorization")
    task = protocol.get("task_contract")
    concurrency = protocol.get("concurrency_contract")
    correction = protocol.get("correction")
    if (
        protocol.get("role")
        != "v24302_neutral_concurrent_synthesis_recovery_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope")
        != "corrected_eight_independent_fault_injected_neutral_real_provider_recoveries"
        or protocol.get("gates") != GATES
        or not _sealed(protocol, "protocol_payload_sha256")
        or not isinstance(manifest, Mapping)
        or set(manifest) != set(SOURCE_FILES)
        or protocol.get("surface_manifest_sha256") != payload_sha256(manifest)
        or any(
            sha256(_ordinary(root, relative)) != digest
            for relative, digest in manifest.items()
        )
        or not isinstance(correction, Mapping)
        or correction.get("all_eight_corrected_tasks_pass_validate_visible_task_before_activation")
        is not True
        or correction.get("parent_protocol_retry_or_resume") is not False
        or not isinstance(task, Mapping)
        or task.get("task_count") != TASK_COUNT
        or task.get("validated_visible_tasks_before_effect") != TASK_COUNT
        or task.get("runtime_input_keys_exactly_opaque_id_and_question") is not True
        or not isinstance(concurrency, Mapping)
        or concurrency.get("executor_workers") != TASK_COUNT
        or concurrency.get("shared_global_model_slot_cap") != SLOT_CAP
        or not isinstance(source, Mapping)
        or any(source.values())
        or not isinstance(auth, Mapping)
        or auth.get("one_corrected_neutral_concurrency_probe") is not True
        or any(
            setting
            for key, setting in auth.items()
            if key != "one_corrected_neutral_concurrency_probe"
        )
    ):
        raise RuntimeError("V2.43.02 protocol drifted")
    _failure(root)
    for index in range(1, TASK_COUNT + 1):
        validate_visible_task(corrected_neutral_task(index))
    return protocol


def build_preactivation_audit(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validated = 0
    for index in range(1, TASK_COUNT + 1):
        visible = validate_visible_task(corrected_neutral_task(index))
        if set(visible) == {"opaque_id", "question"}:
            validated += 1
    future_pristine = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in (RESULT, DECISION, POSTAUDIT)
    )
    findings: list[str] = []
    if validated != TASK_COUNT:
        findings.append("visible_task_validation_incomplete")
    if not future_pristine:
        findings.append("future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24302_neutral_concurrent_synthesis_recovery_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "checks": {
            "protocol_valid_and_sealed": True,
            "parent_zero_effect_failure_sealed": True,
            "parent_protocol_retry_or_resume": False,
            "validated_visible_tasks_before_effect": validated,
            "runtime_input_exactly_opaque_id_and_question": True,
            "credential_literal_scan_clear": True,
            "benchmark_or_evaluator_surface_authorized": False,
            "future_surface_pristine": future_pristine,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "one_corrected_neutral_concurrency_probe": not findings,
            "benchmark_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
        },
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "failure_sha256": sha256(root / FAILURE),
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
    auth = audit.get("authorization")
    if (
        audit.get("role")
        != "v24302_neutral_concurrent_synthesis_recovery_preactivation_audit"
        or audit.get("protocol_id") != PROTOCOL_ID
        or not _sealed(audit, "audit_payload_sha256")
        or audit.get("findings") != []
        or audit.get("audit_valid") is not True
        or audit.get("checks", {}).get("validated_visible_tasks_before_effect")
        != TASK_COUNT
        or not isinstance(auth, Mapping)
        or auth.get("one_corrected_neutral_concurrency_probe") is not True
        or any(
            setting
            for key, setting in auth.items()
            if key != "one_corrected_neutral_concurrency_probe"
        )
        or audit.get("provenance", {}).get("protocol_sha256")
        != sha256(root / PROTOCOL)
    ):
        raise RuntimeError("V2.43.02 preactivation audit drifted")
    return audit


def _worker(
    index: int,
    *,
    provider: Mapping[str, Any],
    slot_directory: Path,
    output_root: Path,
    barrier: Any,
) -> dict[str, Any]:
    started = time.monotonic()
    real = parent.ResponsesClient(
        str(provider["proxy_url"]),
        str(provider["model"]),
        reasoning_effort=str(provider["reasoning_effort"]),
        service_tier=str(provider["service_tier"]),
        timeout=int(provider["timeout_seconds"]),
        max_retries=int(provider["max_retries"]),
    )
    injected = parent.ConcurrentNeutralFaultInjectedModel(real, barrier)
    model = parent.GlobalModelSlotLimiter(
        injected,
        slot_directory=slot_directory,
        output_root=output_root,
        slot_cap=SLOT_CAP,
        pool_id=parent.POOL_ID,
    )
    search = parent.parent_gate.NoEffectSearch()
    result = parent.run_v24299_task(
        corrected_neutral_task(index),
        arm="candidate",
        model=model,
        search=search,
        limits=parent.ScoreFirstLimits(
            wall_seconds=180,
            model_calls=3,
            search_queries=4,
            fetch_targets=10,
            search_results_per_query=3,
            evidence_chars=60_000,
            page_chars=5_000,
        ),
        two_wave_policy=parent.TwoWavePolicy(),
        reserve_policy=parent.StagedReservePolicy(),
    )
    parent.validate_v24299_result(result, "candidate")
    receipt = parent.validate_slot_receipt(
        model.receipt(), expected_cap=SLOT_CAP, expected_acquisitions=3
    )
    recovery = result["synthesis_recovery"]
    value = {
        "worker_index": index,
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "completion_kind": result["completion_kind"],
        "model_budget": {
            "limit": result["budget"]["limits"]["model_calls"],
            "admitted": result["budget"]["admitted_model_calls"],
            "logical_provider_requests": result["cost"]["model"]["requests"],
            "provider_attempts": result["cost"]["model"]["attempts"],
            "slot_acquisitions": receipt["acquisitions"],
            "slot_acquisition_counts": receipt["slot_acquisition_counts"],
            "slot_wait_seconds": receipt["total_wait_seconds"],
            "fourth_provider_effect": result["budget"]["admitted_model_calls"] > 3,
        },
        "recovery": {
            "effects_by_stage": dict(recovery["effects_by_stage"]),
            "total_effects_admitted": recovery["total_effects_admitted"],
            "initial_synthesis_model_request_error": recovery[
                "synthesis_initial_model_request_error"
            ],
            "recovery_attempted": recovery["synthesis_recovery_attempted"],
            "recovery_succeeded": recovery["synthesis_recovery_succeeded"],
            "recovery_model_request_error": recovery[
                "synthesis_recovery_model_request_error"
            ],
            "real_recovery_requests": injected.real_recovery_requests,
        },
        "shared_slot_barrier": {
            "arrivals": injected.shared_slot_barrier_arrivals,
            "passes": injected.shared_slot_barrier_passes,
            "failures": injected.shared_slot_barrier_failures,
        },
        "search": {"calls": search.calls, "fetch_calls": search.fetch_calls},
    }
    parent.validate_worker_projection(value)
    return value


def project(
    workers: Any,
    *,
    wall_seconds: float,
    barrier_broken: bool,
    now: int | None = None,
) -> dict[str, Any]:
    value = parent.project(
        workers,
        wall_seconds=wall_seconds,
        barrier_broken=barrier_broken,
        now=now,
    )
    value["role"] = "v24302_neutral_concurrent_synthesis_recovery_probe"
    value["protocol_id"] = PROTOCOL_ID
    value["scope"] = "corrected_eight_fault_injected_neutral_real_provider_recoveries_only"
    value["validated_visible_tasks_before_effect"] = TASK_COUNT
    value["parent_protocol_retry_or_resume"] = False
    value.pop("result_payload_sha256", None)
    value["result_payload_sha256"] = payload_sha256(value)
    validate_projection(value)
    return value


def validate_projection(value: Mapping[str, Any]) -> None:
    parent_value = dict(value)
    parent_value["role"] = "v24301_neutral_concurrent_synthesis_recovery_probe"
    parent_value["protocol_id"] = parent.PROTOCOL_ID
    parent_value["scope"] = "eight_fault_injected_neutral_real_provider_recoveries_only"
    parent_value.pop("validated_visible_tasks_before_effect", None)
    parent_value.pop("parent_protocol_retry_or_resume", None)
    parent_value.pop("result_payload_sha256", None)
    parent_value["result_payload_sha256"] = payload_sha256(parent_value)
    parent.validate_projection(parent_value)
    if (
        value.get("role") != "v24302_neutral_concurrent_synthesis_recovery_probe"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("scope")
        != "corrected_eight_fault_injected_neutral_real_provider_recoveries_only"
        or value.get("validated_visible_tasks_before_effect") != TASK_COUNT
        or value.get("parent_protocol_retry_or_resume") is not False
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.43.02 projection drifted")


def run_probe(root: Path = ROOT) -> dict[str, Any]:
    import concurrent.futures
    import tempfile
    import threading

    from scripts.deepwide_api_lease import acquire_deepwide_api_lease

    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preactivation_audit(root)
    if any(
        (root / path).exists() or (root / path).is_symlink()
        for path in (RESULT, DECISION, POSTAUDIT)
    ):
        raise RuntimeError("V2.43.02 result surface is not pristine")
    output_root = root / "outputs"
    lease = protocol["lease"]
    started = time.monotonic()
    with acquire_deepwide_api_lease(
        root,
        owner=str(lease["owner"]),
        purpose=str(lease["purpose"]),
        path=root / str(lease["path"]),
    ):
        with tempfile.TemporaryDirectory(dir=output_root) as directory:
            slots = Path(directory)
            for index in range(1, SLOT_CAP + 1):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            barrier = threading.Barrier(TASK_COUNT)
            workers: list[dict[str, Any]] = []
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=TASK_COUNT, thread_name_prefix="v24302-neutral"
            ) as executor:
                futures = {
                    executor.submit(
                        _worker,
                        index,
                        provider=protocol["provider"],
                        slot_directory=slots,
                        output_root=output_root,
                        barrier=barrier,
                    ): index
                    for index in range(1, TASK_COUNT + 1)
                }
                for future in concurrent.futures.as_completed(futures):
                    workers.append(future.result())
            barrier_broken = barrier.broken
    value = project(
        workers,
        wall_seconds=max(0.0, time.monotonic() - started),
        barrier_broken=barrier_broken,
    )
    publish(root / RESULT, value)
    return value


def _checks(result: Mapping[str, Any], gates: Mapping[str, Any]) -> dict[str, bool]:
    parent_gates = {key: value for key, value in gates.items() if key in parent.GATES}
    checks = parent._checks(result, parent_gates)
    checks["validated_visible_tasks_before_effect"] = (
        result.get("validated_visible_tasks_before_effect")
        == gates["required_validated_visible_tasks_before_effect"]
    )
    return checks


def build_decision(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_preactivation_audit(root)
    result = _read(root, RESULT)
    validate_projection(result)
    checks = _checks(result, protocol["gates"])
    failed = sorted(name for name, passed in checks.items() if not passed)
    passed = not failed
    value = {
        "artifact_version": 1,
        "role": "v24302_neutral_concurrent_synthesis_recovery_decision",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "corrected_neutral_concurrency_go" if passed else "corrected_neutral_concurrency_no_go",
        "passed": passed,
        "checks": checks,
        "failed_checks": failed,
        "observed": {
            "wall_seconds": result["wall_seconds"],
            "validated_visible_tasks_before_effect": result[
                "validated_visible_tasks_before_effect"
            ],
            **dict(result["observed"]),
        },
        "provenance": {
            "failure_sha256": sha256(root / FAILURE),
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "result_sha256": sha256(root / RESULT),
            "surface_manifest_sha256": protocol["surface_manifest_sha256"],
        },
        "claim_scope": {
            "corrected_eight_way_fault_injected_real_provider_recovery_robustness": True,
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
            "training_credit_assignment": False,
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
        value.get("role") != "v24302_neutral_concurrent_synthesis_recovery_decision"
        or value.get("protocol_id") != PROTOCOL_ID
        or not _sealed(value, "decision_payload_sha256")
        or not isinstance(checks, Mapping)
        or not isinstance(failed, list)
        or value.get("passed") is not all(checks.values())
        or failed != sorted(name for name, passed in checks.items() if not passed)
        or value.get("status")
        != (
            "corrected_neutral_concurrency_go"
            if value["passed"]
            else "corrected_neutral_concurrency_no_go"
        )
        or not isinstance(claim, Mapping)
        or claim.get(
            "corrected_eight_way_fault_injected_real_provider_recovery_robustness"
        )
        is not True
        or any(
            setting
            for key, setting in claim.items()
            if key
            != "corrected_eight_way_fault_injected_real_provider_recovery_robustness"
        )
        or not isinstance(auth, Mapping)
        or auth.get("successor_fresh_paired_dev64_design") is not value["passed"]
        or any(
            setting
            for key, setting in auth.items()
            if key != "successor_fresh_paired_dev64_design"
        )
    ):
        raise RuntimeError("V2.43.02 decision drifted")


def build_postresult_audit(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    validate_protocol(root)
    validate_preactivation_audit(root)
    result = _read(root, RESULT)
    decision = _read(root, DECISION)
    validate_projection(result)
    validate_decision(decision)
    findings: list[str] = []
    encoded = json.dumps({"result": result, "decision": decision}, ensure_ascii=False)
    if parent.SECRET.search(encoded):
        findings.append("credential_literal_persisted")
    if any(literal in encoded for literal in parent.CONTENT_LITERALS):
        findings.append("task_content_or_identifier_persisted")
    if "task_00000000000000000000000" in encoded:
        findings.append("corrected_opaque_identifier_persisted")
    if decision.get("provenance", {}).get("result_sha256") != sha256(root / RESULT):
        findings.append("decision_result_binding_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24302_neutral_concurrent_synthesis_recovery_postresult_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "findings": findings,
        "audit_valid": not findings,
        "execution_closure": {
            "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "task_identifier_question_prompt_response_prediction_answer_or_hash_persisted": False,
            "credential_value_persisted_hashed_or_emitted": False,
            "official_evaluator_called": False,
            "invalid_result_path": None,
        },
        "authorization": {
            "successor_fresh_paired_dev64_design": bool(decision["passed"] and not findings),
            "successor_fresh_paired_dev64_launch": False,
            "exact220_launch": False,
            "evaluator_call": False,
        },
        "provenance": {
            "failure_sha256": sha256(root / FAILURE),
            "protocol_sha256": sha256(root / PROTOCOL),
            "preactivation_audit_sha256": sha256(root / PREAUDIT),
            "result_sha256": sha256(root / RESULT),
            "decision_sha256": sha256(root / DECISION),
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    validate_postresult_audit(value)
    return value


def validate_postresult_audit(value: Mapping[str, Any]) -> None:
    auth = value.get("authorization")
    if (
        value.get("role")
        != "v24302_neutral_concurrent_synthesis_recovery_postresult_audit"
        or value.get("protocol_id") != PROTOCOL_ID
        or not _sealed(value, "audit_payload_sha256")
        or value.get("findings") != []
        or value.get("audit_valid") is not True
        or value.get("execution_closure", {}).get("invalid_result_path") is not None
        or not isinstance(auth, Mapping)
        or auth.get("successor_fresh_paired_dev64_design") is not True
        or any(
            setting
            for key, setting in auth.items()
            if key != "successor_fresh_paired_dev64_design"
        )
    ):
        raise RuntimeError("V2.43.02 postresult audit drifted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("seal-failure", "preregister", "preaudit", "probe", "finalize", "postaudit"),
    )
    args = parser.parse_args()
    if args.action == "seal-failure":
        value, path = build_failure_receipt(), FAILURE
    elif args.action == "preregister":
        value, path = build_protocol(), PROTOCOL
    elif args.action == "preaudit":
        value, path = build_preactivation_audit(), PREAUDIT
    elif args.action == "probe":
        value = run_probe()
        print(
            json.dumps(
                {
                    "path": str(RESULT),
                    "wall_seconds": value["wall_seconds"],
                    "primary_tasks": value["observed"]["primary_tasks"],
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
