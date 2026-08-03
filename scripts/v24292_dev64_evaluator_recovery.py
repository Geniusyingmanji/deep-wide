#!/usr/bin/env python3
"""Frozen evaluator-only recovery for the pre-evaluator V2.42.91 failure."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import time
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24291_forward_contract import (  # noqa: E402
    EVALUATOR_ROOT,
    FINAL_RESULT as V91_FINAL_RESULT,
    FORWARD_RESULT as V91_FORWARD_RESULT,
    FULL_PROTOCOL as V91_PROTOCOL,
    LEASE_PATH,
    POSTAUDIT as V91_POSTAUDIT,
    PREDICTION_FREEZE,
    SELECTED_COUNT,
    payload_sha256,
    read_object,
    sha256,
)
from scripts import audit_v24291_dev64 as v91_audit  # noqa: E402
from scripts import finalize_v24291_dev64 as v91_finalizer  # noqa: E402
from scripts import preregister_v24291_dev64 as v91_preregister  # noqa: E402
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


PROTOCOL_ID = "v24292_v24291_pre_evaluator_failure_recovery_v1"
PROTOCOL = Path("results/v24292_dev64_evaluator_recovery_preregistration_v1_20260803.json")
PREAUDIT = Path("results/v24292_dev64_evaluator_recovery_preactivation_audit_v1_20260803.json")
ACTIVATION = Path("results/v24292_dev64_evaluator_recovery_activation_v1_20260803.json")
EXECUTION_START = Path("results/v24292_dev64_evaluator_recovery_execution_start_v1_20260803.json")
RECOVERY_RESULT = Path("results/v24292_dev64_evaluator_recovery_result_v1_20260803.json")
POSTAUDIT = Path("results/v24292_dev64_evaluator_recovery_postresult_audit_v1_20260803.json")
FAILURE_LOG = Path("outputs/v24291_dev64_finalizer_v1_20260803.log")
FAILURE_LOG_SHA256 = "a3d624166cc2b93fc3ca52eb7c582b17363b630f1a973756387932f08a88b9af"
FAILURE_EXCEPTION = "NameError: name 'CONTROL_RESULT' is not defined"
LEASE_OWNER = "v24292_dev64_evaluator_recovery_v1"
LEASE_PURPOSE = "fresh_full_both_arm_dev64_evaluator_after_pre_evaluator_control_failure"
RUN_MARKER = "scripts/v24292_dev64_evaluator_recovery.py"
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
SOURCE_FILES = (
    RUN_MARKER,
    "scripts/finalize_v24291_dev64.py",
    "scripts/preregister_v24291_dev64.py",
    "scripts/audit_v24291_dev64.py",
    "tests/test_v24292_dev64_evaluator_recovery.py",
)
FUTURE_PATHS = (
    PROTOCOL,
    PREAUDIT,
    ACTIVATION,
    EXECUTION_START,
    RECOVERY_RESULT,
    POSTAUDIT,
    V91_FINAL_RESULT,
    V91_POSTAUDIT,
    EVALUATOR_ROOT,
)


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
        raise RuntimeError(f"V2.42.92 expected ordinary file: {relative}")
    return path


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _source_manifest(root: Path) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in SOURCE_FILES:
        path = _ordinary(root, relative)
        if SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError(f"V2.42.92 credential literal in {relative}")
        output[relative] = sha256(path)
    return output


def _validate_failure(root: Path, *, require_live_absence: bool = True) -> dict[str, Any]:
    path = _ordinary(root, FAILURE_LOG)
    text = path.read_text(encoding="utf-8")
    source = _ordinary(root, "scripts/finalize_v24291_dev64.py").read_text(encoding="utf-8")
    load = source.index("control = load_control_after_candidate")
    live = source.index("live = validate_live_evaluator_identity", load)
    create = source.index("(root / EVALUATOR_ROOT).mkdir", live)
    evaluate = source.index("evaluated = run_all_evaluators", create)
    if (
        sha256(path) != FAILURE_LOG_SHA256
        or FAILURE_EXCEPTION not in text
        or "control = load_control_after_candidate" not in text
        or not load < live < create < evaluate
        or (
            require_live_absence
            and (
                (root / EVALUATOR_ROOT).exists()
                or (root / EVALUATOR_ROOT).is_symlink()
                or (root / V91_FINAL_RESULT).exists()
                or (root / V91_FINAL_RESULT).is_symlink()
            )
        )
    ):
        raise RuntimeError("V2.42.92 pre-evaluator failure evidence drifted")
    return {
        "path": str(FAILURE_LOG),
        "sha256": FAILURE_LOG_SHA256,
        "exception": FAILURE_EXCEPTION,
        "failed_call": "load_control_after_candidate",
        "failed_before_live_evaluator_validation": True,
        "failed_before_evaluator_root_creation": True,
        "failed_before_evaluator_worker_or_api_call": True,
        "evaluator_root_absent_after_failure": True,
    }


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    v91 = v91_preregister.validate_protocol(root)
    if require_pristine:
        present = [str(path) for path in FUTURE_PATHS if (root / path).exists() or (root / path).is_symlink()]
        if present:
            raise RuntimeError(f"V2.42.92 future surface is not pristine: {present}")
    failure = _validate_failure(root)
    manifest = _source_manifest(root)
    value = {
        "artifact_version": 1,
        "role": "v24292_dev64_evaluator_recovery_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "evaluator_only_recovery_after_fail_closed_pre_evaluator_name_error",
        "parent": {
            "v24291_protocol": {"path": str(V91_PROTOCOL), "sha256": sha256(root / V91_PROTOCOL)},
            "v24291_forward_result": {"path": str(V91_FORWARD_RESULT), "sha256": sha256(root / V91_FORWARD_RESULT)},
            "v24291_candidate_prediction_freeze": {"path": str(PREDICTION_FREEZE), "sha256": sha256(root / PREDICTION_FREEZE)},
            "selected": SELECTED_COUNT,
            "candidate_exact64_before_control_or_evaluator_open": True,
        },
        "failed_attempt": failure,
        "recovery_adapter": {
            "unmodified_frozen_finalizer": "scripts/finalize_v24291_dev64.py",
            "inject_existing_constant_CONTROL_RESULT": str(v91_preregister.CONTROL_RESULT),
            "inject_existing_constant_CONTROL_POSTAUDIT": str(v91_preregister.CONTROL_POSTAUDIT),
            "hold_outer_nonblocking_lease_before_any_recovery_surface": True,
            "replace_nested_same_process_lease_only_with_outer_lease_assertion": True,
            "forward_code_prediction_or_freeze_modified": False,
        },
        "evaluation_contract": {
            "arms": ["control", "candidate"],
            "selected_per_arm": SELECTED_COUNT,
            "fixed_denominator_per_arm": SELECTED_COUNT,
            "workers_per_arm": v91["evaluator_execution"]["workers_per_arm"],
            "total_parallel_workers": v91["evaluator_execution"]["total_parallel_workers"],
            "fixed_contiguous_partition_sizes_per_arm": [16, 16, 16, 16],
            "fresh_evaluator_root": str(EVALUATOR_ROOT),
            "resume": False,
            "selective_retry_or_error_revaluation": False,
            "old_evaluator_rows_reused": False,
        },
        "lease": {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_single_owner": True,
        },
        "result_paths": {
            "execution_start": str(EXECUTION_START),
            "v24291_final_result": str(V91_FINAL_RESULT),
            "recovery_result": str(RECOVERY_RESULT),
            "v24291_postresult_audit": str(V91_POSTAUDIT),
            "recovery_postresult_audit": str(POSTAUDIT),
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "candidate_forward_runtime_boundary": ["opaque_id", "question"],
            "candidate_prediction_freeze_precedes_recovery": True,
            "forward_rerun_resume_skip_or_prediction_mutation": False,
            "mapping_gold_evaluator_feedback_used_for_candidate_forward_or_selection": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "one_fresh_full_both_arm_dev64_evaluation": True,
            "forward_call_or_rerun": False,
            "evaluator_resume_selective_retry_or_revaluation": False,
            "additional_dev64_or_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return value


def validate_protocol(root: Path = ROOT, value: Mapping[str, Any] | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else read_object(_ordinary(root, PROTOCOL))
    manifest = protocol.get("source_manifest")
    parent = protocol.get("parent") or {}
    adapter = protocol.get("recovery_adapter") or {}
    evaluation = protocol.get("evaluation_contract") or {}
    if (
        protocol.get("artifact_version") != 1
        or protocol.get("role") != "v24292_dev64_evaluator_recovery_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("scope") != "evaluator_only_recovery_after_fail_closed_pre_evaluator_name_error"
        or not _sealed(protocol, "protocol_payload_sha256")
        or not isinstance(manifest, dict)
        or set(manifest) != set(SOURCE_FILES)
        or protocol.get("source_manifest_sha256") != payload_sha256(manifest)
        or any(sha256(_ordinary(root, relative)) != digest for relative, digest in manifest.items())
        or parent.get("v24291_protocol") != {"path": str(V91_PROTOCOL), "sha256": sha256(root / V91_PROTOCOL)}
        or parent.get("v24291_forward_result") != {"path": str(V91_FORWARD_RESULT), "sha256": sha256(root / V91_FORWARD_RESULT)}
        or parent.get("v24291_candidate_prediction_freeze") != {"path": str(PREDICTION_FREEZE), "sha256": sha256(root / PREDICTION_FREEZE)}
        or parent.get("selected") != SELECTED_COUNT
        or parent.get("candidate_exact64_before_control_or_evaluator_open") is not True
        or protocol.get("failed_attempt")
        != _validate_failure(
            root, require_live_absence=not (root / EXECUTION_START).exists()
        )
        or adapter.get("inject_existing_constant_CONTROL_RESULT") != str(v91_preregister.CONTROL_RESULT)
        or adapter.get("inject_existing_constant_CONTROL_POSTAUDIT") != str(v91_preregister.CONTROL_POSTAUDIT)
        or adapter.get("hold_outer_nonblocking_lease_before_any_recovery_surface") is not True
        or adapter.get("replace_nested_same_process_lease_only_with_outer_lease_assertion") is not True
        or adapter.get("forward_code_prediction_or_freeze_modified") is not False
        or evaluation.get("arms") != ["control", "candidate"]
        or evaluation.get("selected_per_arm") != SELECTED_COUNT
        or evaluation.get("fixed_denominator_per_arm") != SELECTED_COUNT
        or evaluation.get("fixed_contiguous_partition_sizes_per_arm") != [16, 16, 16, 16]
        or evaluation.get("resume") is not False
        or evaluation.get("selective_retry_or_error_revaluation") is not False
        or protocol.get("authorization")
        != {
            "one_fresh_full_both_arm_dev64_evaluation": True,
            "forward_call_or_rerun": False,
            "evaluator_resume_selective_retry_or_revaluation": False,
            "additional_dev64_or_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        }
    ):
        raise RuntimeError("V2.42.92 protocol drifted")
    v91_preregister.validate_protocol(root)
    return protocol


def _process_matches(rows: list[dict[str, Any]], marker: str, token: str | None = None) -> bool:
    for row in rows:
        argv = [str(item) for item in row.get("argv") or []]
        joined = " ".join(argv)
        if marker in joined and (token is None or token in argv):
            return True
    return False


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    candidate = v91_finalizer.validate_candidate_barrier(root)
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    findings: list[str] = []
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if _process_matches(rows, "scripts/finalize_v24291_dev64.py"):
        findings.append("v24291_finalizer_active")
    if _process_matches(rows, RUN_MARKER, "run"):
        findings.append("v24292_recovery_already_active")
    if _process_matches(rows, "scripts/run_official_eval_local.py"):
        findings.append("official_evaluator_active")
    present = [str(path) for path in (ACTIVATION, EXECUTION_START, RECOVERY_RESULT, POSTAUDIT, V91_FINAL_RESULT, V91_POSTAUDIT, EVALUATOR_ROOT) if (root / path).exists() or (root / path).is_symlink()]
    if present:
        findings.append("recovery_future_surface_not_pristine")
    value = {
        "artifact_version": 1,
        "role": "v24292_dev64_evaluator_recovery_preactivation_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "source_manifest_sha256": protocol["source_manifest_sha256"],
        "candidate_barrier": {
            "selected": len(candidate["rows"]),
            "forward_result_sha256": sha256(root / V91_FORWARD_RESULT),
            "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
            "exact64_before_control_or_evaluator_open": True,
        },
        "failed_attempt_verified_pre_evaluator": True,
        "evaluator_root_absent": not (root / EVALUATOR_ROOT).exists(),
        "shared_api_lease_active": lease.get("active") is True,
        "network_model_search_fetch_or_evaluator_api_called_by_audit": False,
        "protected_existing_processes_signaled_restarted_or_stopped": False,
        "forward_prediction_or_freeze_modified": False,
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_preaudit(root: Path = ROOT) -> dict[str, Any]:
    value = read_object(_ordinary(root, PREAUDIT))
    if (
        value.get("role") != "v24292_dev64_evaluator_recovery_preactivation_audit"
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("audit_valid") is not True
        or value.get("launch_authorized") is not True
        or value.get("findings") != []
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.42.92 preactivation audit drifted")
    return value


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    audit = validate_preaudit(root)
    value = {
        "artifact_version": 1,
        "role": "v24292_dev64_evaluator_recovery_activation",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active",
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "source_manifest_sha256": protocol["source_manifest_sha256"],
        "selected_per_arm": SELECTED_COUNT,
        "shared_api_lease_active_before_activation": audit["shared_api_lease_active"],
        "forward_call_rerun_or_prediction_mutation": False,
        "network_evaluator_or_api_called_by_activation": False,
        "exact220_leaderboard_or_sota_authorized": False,
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    value = read_object(_ordinary(root, ACTIVATION))
    if (
        value.get("role") != "v24292_dev64_evaluator_recovery_activation"
        or value.get("status") != "active"
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("selected_per_arm") != SELECTED_COUNT
        or value.get("shared_api_lease_active_before_activation") is not False
        or value.get("forward_call_rerun_or_prediction_mutation") is not False
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.92 activation drifted")
    return value


@contextlib.contextmanager
def _nested_lease_adapter(record: Mapping[str, Any], *args: Any, **kwargs: Any) -> Iterator[dict[str, Any]]:
    del args
    if (
        record.get("owner") != LEASE_OWNER
        or record.get("purpose") != LEASE_PURPOSE
        or record.get("pid") != os.getpid()
        or kwargs.get("owner") != "v24291_dev64_evaluator_v1"
        or kwargs.get("purpose") != "post_candidate_freeze_fresh_both_arm_full64_evaluation"
    ):
        raise RuntimeError("V2.42.92 nested evaluator lease adapter drifted")
    yield {"outer_lease_owner": LEASE_OWNER, "same_process_nested_lock_replaced": True}


def run_recovery(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    activation = validate_activation(root)
    for path in (EXECUTION_START, RECOVERY_RESULT, V91_FINAL_RESULT, V91_POSTAUDIT, EVALUATOR_ROOT):
        if (root / path).exists() or (root / path).is_symlink():
            raise RuntimeError(f"V2.42.92 recovery surface is not pristine: {path}")
    started = time.monotonic()
    lease = protocol["lease"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["owner"],
        purpose=lease["purpose"],
        path=root / lease["path"],
    ) as record:
        start = {
            "artifact_version": 1,
            "role": "v24292_dev64_evaluator_recovery_execution_start",
            "created_at_unix": int(time.time()),
            "protocol_sha256": sha256(root / PROTOCOL),
            "activation_sha256": sha256(root / ACTIVATION),
            "runner": {"pid": os.getpid(), "marker": RUN_MARKER, "command": "run"},
            "selected_per_arm": SELECTED_COUNT,
            "outer_lease_acquired_before_execution_start": True,
            "candidate_prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
            "evaluator_root_absent_before_execution_start": not (root / EVALUATOR_ROOT).exists(),
            "forward_call_rerun_or_prediction_mutation": False,
            "evaluator_api_called_before_execution_start": False,
        }
        start["execution_start_payload_sha256"] = payload_sha256(start)
        _publish(root / EXECUTION_START, start)
        original_lease = v91_finalizer.acquire_deepwide_api_lease
        missing = object()
        original_result = getattr(v91_finalizer, "CONTROL_RESULT", missing)
        original_audit = getattr(v91_finalizer, "CONTROL_POSTAUDIT", missing)
        v91_finalizer.CONTROL_RESULT = v91_preregister.CONTROL_RESULT
        v91_finalizer.CONTROL_POSTAUDIT = v91_preregister.CONTROL_POSTAUDIT
        v91_finalizer.acquire_deepwide_api_lease = lambda *args, **kwargs: _nested_lease_adapter(record, *args, **kwargs)
        try:
            result = v91_finalizer.finalize(root)
        finally:
            v91_finalizer.acquire_deepwide_api_lease = original_lease
            if original_result is missing:
                delattr(v91_finalizer, "CONTROL_RESULT")
            else:
                v91_finalizer.CONTROL_RESULT = original_result
            if original_audit is missing:
                delattr(v91_finalizer, "CONTROL_POSTAUDIT")
            else:
                v91_finalizer.CONTROL_POSTAUDIT = original_audit
    recovery = {
        "artifact_version": 1,
        "role": "v24292_dev64_evaluator_recovery_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "fresh_full_both_arm_evaluation_complete",
        "selected_per_arm": SELECTED_COUNT,
        "v24291_decision_status": result["status"],
        "v24291_decision_passed": result["decision"]["passed"],
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "provenance": {
            "protocol_sha256": sha256(root / PROTOCOL),
            "activation_sha256": sha256(root / ACTIVATION),
            "execution_start_sha256": sha256(root / EXECUTION_START),
            "failed_attempt_log_sha256": sha256(root / FAILURE_LOG),
            "candidate_prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
            "v24291_final_result_sha256": sha256(root / V91_FINAL_RESULT),
        },
        "recovery_policy": {
            "outer_lease_preceded_recovery_surface": True,
            "unmodified_v24291_finalizer_used": True,
            "only_missing_existing_control_path_constants_injected": True,
            "nested_same_process_lease_replaced_by_outer_lease_assertion": True,
            "forward_rerun_resume_skip_or_prediction_mutation": False,
            "evaluator_resume_selective_retry_or_error_revaluation": False,
            "both_arms_all_64_evaluated": True,
        },
        "authorization": {
            "additional_dev64_or_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    recovery["recovery_payload_sha256"] = payload_sha256(recovery)
    _publish(root / RECOVERY_RESULT, recovery)
    return recovery


def build_postaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root)
    validate_activation(root)
    recovery = read_object(_ordinary(root, RECOVERY_RESULT))
    result = read_object(_ordinary(root, V91_FINAL_RESULT))
    missing = object()
    original_result = getattr(v91_finalizer, "CONTROL_RESULT", missing)
    original_audit = getattr(v91_finalizer, "CONTROL_POSTAUDIT", missing)
    v91_finalizer.CONTROL_RESULT = v91_preregister.CONTROL_RESULT
    v91_finalizer.CONTROL_POSTAUDIT = v91_preregister.CONTROL_POSTAUDIT
    try:
        v91_finalizer.validate_final_result(
            root, v91_preregister.validate_protocol(root), result
        )
        if not (root / V91_POSTAUDIT).exists():
            v91_report = v91_audit.build_postresult_report(root)
            v91_preregister.publish_new(root / V91_POSTAUDIT, v91_report)
    finally:
        if original_result is missing:
            delattr(v91_finalizer, "CONTROL_RESULT")
        else:
            v91_finalizer.CONTROL_RESULT = original_result
        if original_audit is missing:
            delattr(v91_finalizer, "CONTROL_POSTAUDIT")
        else:
            v91_finalizer.CONTROL_POSTAUDIT = original_audit
    if (
        recovery.get("role") != "v24292_dev64_evaluator_recovery_result"
        or recovery.get("v24291_decision_status") != result["status"]
        or recovery.get("provenance", {}).get("v24291_final_result_sha256") != sha256(root / V91_FINAL_RESULT)
        or not _sealed(recovery, "recovery_payload_sha256")
    ):
        raise RuntimeError("V2.42.92 recovery result drifted")
    v91_report = read_object(_ordinary(root, V91_POSTAUDIT))
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    findings: list[str] = []
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active_after_result")
    if _process_matches(rows, "scripts/finalize_v24291_dev64.py") or _process_matches(rows, "scripts/run_official_eval_local.py"):
        findings.append("evaluator_process_present_after_result")
    if v91_report.get("audit_valid") is not True or v91_report.get("findings") != []:
        findings.append("v24291_postresult_audit_invalid")
    value = {
        "artifact_version": 1,
        "role": "v24292_dev64_evaluator_recovery_postresult_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "activation_sha256": sha256(root / ACTIVATION),
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "recovery_result_sha256": sha256(root / RECOVERY_RESULT),
        "v24291_final_result_sha256": sha256(root / V91_FINAL_RESULT),
        "v24291_postresult_audit_sha256": sha256(root / V91_POSTAUDIT),
        "execution_closure": {
            "shared_api_lease_active": lease.get("active") is True,
            "evaluator_process_present": "evaluator_process_present_after_result" in findings,
            "forward_rerun_resume_skip_or_prediction_mutation": False,
            "evaluator_resume_selective_retry_or_error_revaluation": False,
            "active_run_killed_or_quarantined": False,
            "invalid_result_path": None,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "additional_dev64_or_exact220": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("preregister", "audit", "activate", "run", "post-audit"))
    args = parser.parse_args()
    if args.action == "preregister":
        value = build_protocol()
        path = PROTOCOL
    elif args.action == "audit":
        value = build_preaudit()
        path = PREAUDIT
    elif args.action == "activate":
        value = build_activation()
        path = ACTIVATION
    elif args.action == "run":
        value = run_recovery()
        print(json.dumps({"path": str(RECOVERY_RESULT), "status": value["status"]}, sort_keys=True))
        return
    else:
        value = build_postaudit()
        path = POSTAUDIT
    _publish(ROOT / path, value)
    print(json.dumps({"path": str(path), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
