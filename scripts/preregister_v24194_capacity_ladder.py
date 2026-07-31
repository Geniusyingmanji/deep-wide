#!/usr/bin/env python3
"""Freeze a wait-only neutral GPT-5.6 concurrency ladder."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24194_capacity_ladder import (  # noqa: E402
    ProbeSettings,
    payload_sha256,
)


ROLE = "v24194_capacity_ladder_preregistration"
PROTOCOL_ID = "v24194_neutral_gpt56_capacity_ladder_v1"
OUTPUT = Path("results/v24194_capacity_ladder_preregistration_v1_20260731.json")
STATE = Path("outputs/v24194_capacity_ladder_watcher_state_v1_20260731.json")
REPORT = Path("results/v24194_capacity_ladder_report_v1_20260731.json")
FREEZE = Path("results/v24194_next_fresh_all220_capacity_freeze_v1_20260731.json")
WAIT_ACTIVATION = Path(
    "results/v24194_capacity_ladder_wait_activation_audit_v1_20260731.json"
)
EXECUTION_ACTIVATION = Path(
    "results/v24194_capacity_ladder_execution_activation_v1_20260731.json"
)
WATCHER_MARKER = "scripts/watch_v24194_capacity_ladder.py"
LEASE_OWNER = "v24194_neutral_gpt56_capacity_ladder_v1"
LEASE_PURPOSE = "neutral_capacity_for_next_fresh_all220_freeze"
R1_STATE = Path("outputs/v24118_r1_finalization_watchdog_state_v1_20260728.json")
PHASE_STATE = Path("outputs/v24187_phase_liveness_watcher_state_v1_20260730.json")

FROZEN_PARENTS = {
    "results/v24118_r1_finalization_watchdog_preregistration_v1_20260728.json": "afced234f409356d019e087ca7d329535796a27e5d6c7a82bdf9a03b8c1fd720",
    "scripts/watch_v24118_r1_finalization.py": "659b4da8d0fcf9a4d14606fe493a9a81367de8e7104b0adf37d48c49071c7df9",
    "results/v24187_phase_liveness_preregistration_v1_20260730.json": "873f42369f6f5ac7d1b619510257f8cc7c932140b734dd14d23c4a5c6e45d34c",
    "scripts/watch_v24187_phase_liveness.py": "83789b1cc2eb1e6e87969894409b09039028e0e13b53ba8de90776171bf567d3",
    "scripts/audit_v24187_phase_liveness.py": "ff776dafe18d2455cf74dbe953d8590b7e36b43bcda658043791f3e27d4b3fd4",
    "scripts/deepwide_api_lease.py": "8d9cffa78617b458172307d3558c76e9370f045f531c2f5aaaceb866f5a78c7d",
    "src/deepwide_agent/clients.py": "339d923973f07ebcd33cb12cee2c26103df70ed3aea1fc0a737ffd675ac06fbc",
    "scripts/finalize_full220_v2403_r1.py": "dbbfb43378ee67f324bd384294b0028c67f99054a925ab8fec8ebed829023551",
}
CONTROL_FILES = (
    "src/deepwide_agent/v24194_capacity_ladder.py",
    "scripts/preregister_v24194_capacity_ladder.py",
    "scripts/watch_v24194_capacity_ladder.py",
    "scripts/audit_v24194_capacity_ladder_wait_activation.py",
    "tests/test_v24194_capacity_ladder.py",
    "tests/test_preregister_v24194_capacity_ladder.py",
    "tests/test_watch_v24194_capacity_ladder.py",
    "tests/test_audit_v24194_capacity_ladder_wait_activation.py",
)
MUST_REMAIN_ABSENT = ("scripts/__init__.py", "sitecustomize.py", "usercustomize.py")
DECISION_FIELDS = (
    "protocol_id",
    "parents",
    "capacity_contract",
    "release_and_priority_gate",
    "execution",
    "source_policy",
    "authorization",
    "control_surface",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ordinary(root: Path, relative: str | Path, expected: str | None = None) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.41.94 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.is_relative_to(root)
    ):
        raise RuntimeError(f"V2.41.94 expected an ordinary file: {relative}")
    if expected is not None and sha256(path) != expected:
        raise RuntimeError(f"V2.41.94 frozen parent drifted: {relative}")
    return path


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"V2.41.94 expected an object: {path}")
    return value


def _safe_freeze_boundary(root: Path) -> dict[str, Any]:
    r1_path = _ordinary(root, R1_STATE)
    phase_path = _ordinary(root, PHASE_STATE)
    r1 = _read_object(r1_path)
    phase = _read_object(phase_path)
    aggregate = r1.get("aggregate") or {}
    current = phase.get("current_phase") or {}
    if (
        r1.get("role") != "v24118_r1_finalization_watchdog_state"
        or r1.get("status") != "waiting_for_r1_exact_terminal_220"
        or aggregate.get("selected") != 220
        or aggregate.get("exact_terminal_220") is not False
        or aggregate.get("terminal")
        != int(aggregate.get("completed", -1)) + int(aggregate.get("failed", -1))
        or not 0 <= int(aggregate.get("terminal", -1)) < 220
        or r1.get("mapping_or_gold_read") is not False
        or r1.get("evaluator_or_score_read") is not False
        or r1.get("benchmark_forward_api_called") is not False
        or r1.get("process_signal_restart_resume_rerun_skip_or_selective_retry")
        is not False
        or r1.get("leaderboard_submission_performed") is not False
        or r1.get("sota_claim") is not False
        or r1.get("released_artifacts", {}).get("complete_pair") is not False
        or phase.get("role") != "v24187_phase_liveness_audit"
        or phase.get("overall_status")
        not in {"healthy", "degraded_forward_healthy_manual_review_only"}
        or phase.get("critical_findings") != []
        or current.get("phase") != "r1_full220"
        or current.get("valid") is not True
        or current.get("terminal") is not False
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in (OUTPUT, STATE, REPORT, FREEZE, WAIT_ACTIVATION, EXECUTION_ACTIVATION)
        )
    ):
        raise RuntimeError("V2.41.94 safe freeze boundary is invalid")
    return {
        "r1_status": r1["status"],
        "r1_terminal": aggregate["terminal"],
        "r1_state_sha256": sha256(r1_path),
        "phase": current["phase"],
        "phase_state_sha256": sha256(phase_path),
        "r1_release_pair_absent": True,
        "capacity_outputs_absent": True,
    }


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    require_pristine: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    if root != ROOT.resolve():
        raise RuntimeError("V2.41.94 may only freeze the canonical workspace")
    if any((root / name).exists() or (root / name).is_symlink() for name in MUST_REMAIN_ABSENT):
        raise RuntimeError("V2.41.94 unattested Python bootstrap path appeared")
    parents = {
        relative: {"sha256": sha256(_ordinary(root, relative, expected))}
        for relative, expected in FROZEN_PARENTS.items()
    }
    boundary = (
        _safe_freeze_boundary(root)
        if require_pristine
        else {
            "r1_status": "waiting_for_r1_exact_terminal_220",
            "r1_terminal": 0,
            "r1_state_sha256": "0" * 64,
            "phase": "r1_full220",
            "phase_state_sha256": "0" * 64,
            "r1_release_pair_absent": True,
            "capacity_outputs_absent": True,
        }
    )
    settings = ProbeSettings()
    settings.validate()
    manifest = {relative: sha256(_ordinary(root, relative)) for relative in CONTROL_FILES}
    control = {
        "file_count": len(manifest),
        "manifest": manifest,
        "manifest_sha256": payload_sha256(manifest),
        "must_remain_absent": list(MUST_REMAIN_ABSENT),
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "label_blind": True,
        "parents": parents,
        "capacity_contract": {
            "settings": settings.as_dict(),
            "settings_sha256": payload_sha256(settings.as_dict()),
            "endpoint": "http://127.0.0.1:9878/responses",
            "model": "gpt-5.6-sol",
            "reasoning_effort": "high",
            "service_tier": "priority",
            "request_timeout_seconds": 180,
            "client_max_retries": 1,
            "first_attempt_exact_nontruncated_success_required": True,
            "stop_at_first_unsafe_level": True,
            "selected_level_is_highest_consecutive_safe_level": True,
            "fixed_selected_concurrency_for_entire_future_all220": True,
            "separate_search_capacity_preflight_required": True,
        },
        "release_and_priority_gate": {
            "r1_state_path": str(R1_STATE),
            "required_r1_terminal": 220,
            "required_r1_release_pair": True,
            "phase_state_path": str(PHASE_STATE),
            "required_phase": "post_gate1_and_leaderboard_handoff",
            "required_phase_terminal": True,
            "required_phase_valid": True,
            "required_critical_findings": [],
            "quiet_observations_before_lease": 2,
            "execution_activation_path": str(EXECUTION_ACTIVATION),
            "execution_activation_requires_registered_lease_owner": True,
            "safe_freeze_boundary": boundary,
        },
        "execution": {
            "python_flags": ["-I", "-B"],
            "poll_seconds": 60,
            "proc_root": "/proc",
            "watcher_marker": WATCHER_MARKER,
            "state_path": str(STATE),
            "report_path": str(REPORT),
            "freeze_path": str(FREEZE),
            "wait_activation_path": str(WAIT_ACTIVATION),
            "shared_lease_owner": LEASE_OWNER,
            "shared_lease_purpose": LEASE_PURPOSE,
            "active_api_worker_markers": [
                "scripts/run_deepwide_agent.py",
                "scripts/run_official_eval_local.py",
                "scripts/preflight_deepwide.py",
                "scripts/run_v24123_branch.py",
                "scripts/run_v2412_post_gate1_interventions.py",
                "scripts/run_sealed_v2409_owic_capture.py",
                "scripts/run_sealed_v2411_post_p12_owic_capture.py",
            ],
        },
        "source_policy": {
            "safe_r1_and_phase_envelopes_only": True,
            "released_result_bytes_hashed_for_finalization_seal_but_not_parsed": True,
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
            "runtime_task_state_answer_evidence_or_url_opened": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "neutral_payload_only_after_all_gates": True,
            "search_fetch_or_evaluator_api_called": False,
            "response_text_or_response_id_persisted": False,
        },
        "authorization": {
            "wait_only_before_execution_activation": True,
            "current_r1_or_quality_chain_process_signal_restart_resume_rerun_skip": False,
            "current_r1_or_quality_chain_forward_config_concurrency_change": False,
            "network_model_api_before_r1_release": False,
            "network_model_api_before_quality_campaign_terminal": False,
            "network_model_api_before_execution_activation": False,
            "network_model_api_under_registered_shared_lease_only": True,
            "future_all220_freeze_generation_after_measurement": True,
            "future_all220_launch": False,
            "benchmark_forward_or_evaluator_call": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "control_surface": control,
    }
    value["decision_contract_sha256"] = payload_sha256(
        {key: value[key] for key in DECISION_FIELDS}
    )
    return value


def validate_protocol(root: Path, path: Path = OUTPUT) -> dict[str, Any]:
    root = root.resolve()
    target = path if path.is_absolute() else root / path
    if (
        target.resolve(strict=False) != (root / OUTPUT).resolve(strict=False)
        or target.is_symlink()
        or not target.is_file()
    ):
        raise RuntimeError("V2.41.94 protocol path is noncanonical")
    value = _read_object(target)
    control = value.get("control_surface") or {}
    manifest = control.get("manifest")
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or not isinstance(manifest, dict)
        or set(manifest) != set(CONTROL_FILES)
        or control.get("file_count") != len(manifest)
        or control.get("manifest_sha256") != payload_sha256(manifest)
        or set(control.get("must_remain_absent") or []) != set(MUST_REMAIN_ABSENT)
        or value.get("decision_contract_sha256")
        != payload_sha256({key: value[key] for key in DECISION_FIELDS})
    ):
        raise RuntimeError("V2.41.94 protocol contract is invalid")
    for relative, digest in manifest.items():
        if sha256(_ordinary(root, relative)) != digest:
            raise RuntimeError("V2.41.94 control bytes drifted")
    for relative, record in value.get("parents", {}).items():
        expected = record.get("sha256") if isinstance(record, dict) else None
        if not isinstance(expected, str) or sha256(_ordinary(root, relative)) != expected:
            raise RuntimeError("V2.41.94 parent bytes drifted")
    return {"path": target, "sha256": sha256(target), "value": value}


def publish_new(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.41.94 output path drifted")
    publish_new(target, build_protocol())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
