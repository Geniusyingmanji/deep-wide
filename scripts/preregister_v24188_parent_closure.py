#!/usr/bin/env python3
"""Freeze the append-only V2.41.88 parent-control closure correction."""

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

ROLE = "v24188_parent_control_closure_preregistration"
PROTOCOL_ID = "v24188_parent_control_closure_correction_v1"
DEFAULT_PROTOCOL = Path(
    "results/v24188_parent_control_closure_preregistration_v1_20260730.json"
)
DEFAULT_RESULT = Path(
    "results/v24188_parent_control_closure_audit_v1_20260730.json"
)
V24187_PROTOCOL = Path(
    "results/v24187_phase_liveness_preregistration_v1_20260730.json"
)
V24187_PROTOCOL_SHA256 = (
    "873f42369f6f5ac7d1b619510257f8cc7c932140b734dd14d23c4a5c6e45d34c"
)
V24187_ACTIVATION = Path(
    "results/v24187_phase_liveness_activation_audit_v1_20260730.json"
)
V24187_ACTIVATION_SHA256 = (
    "b57bdc1fbcce3911111f9c571c77dd37f1d1ecbf1030b1658638c0062cbaa4b2"
)
CONTROL_FILES = (
    "scripts/preregister_v24188_parent_closure.py",
    "scripts/audit_v24188_parent_closure.py",
    "tests/test_preregister_v24188_parent_closure.py",
    "tests/test_audit_v24188_parent_closure.py",
)
MUST_REMAIN_ABSENT = (
    "scripts/__init__.py",
    "sitecustomize.py",
    "usercustomize.py",
)
DECISION_FIELDS = (
    "protocol_id",
    "parents",
    "correction_contract",
    "audit_contract",
    "control_surface",
    "authorization",
    "claims",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def payload_sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.41.88 expected a JSON object")
    return value


def ordinary(root: Path, relative: Path | str, digest: str | None = None) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.41.88 path is noncanonical")
    path = root / raw
    if (
        path.resolve(strict=False) != path.absolute()
        or path.is_symlink()
        or not path.is_file()
        or not path.is_relative_to(root)
    ):
        raise RuntimeError(f"V2.41.88 expected an ordinary file: {relative}")
    if digest is not None and sha256(path) != digest:
        raise RuntimeError(f"V2.41.88 frozen input drifted: {relative}")
    return path


def _v24187_inputs(root: Path) -> dict[str, Any]:
    protocol_path = ordinary(root, V24187_PROTOCOL, V24187_PROTOCOL_SHA256)
    activation_path = ordinary(root, V24187_ACTIVATION, V24187_ACTIVATION_SHA256)
    protocol = read_object(protocol_path)
    activation = read_object(activation_path)
    if (
        protocol.get("role") != "v24187_phase_liveness_preregistration"
        or protocol.get("source_contract", {}).get(
            "immutable_parent_bytes_live_revalidated"
        )
        is not True
        or activation.get("role") != "v24187_phase_liveness_activation_audit"
        or activation.get("activation_valid") is not True
        or activation.get("boundary", {}).get(
            "immutable_parent_and_control_bytes_live_revalidated"
        )
        is not True
    ):
        raise RuntimeError("V2.41.88 correction target drifted")
    return {
        "v24187_protocol": {
            "path": str(V24187_PROTOCOL),
            "sha256": V24187_PROTOCOL_SHA256,
            "role": protocol["role"],
        },
        "v24187_activation": {
            "path": str(V24187_ACTIVATION),
            "sha256": V24187_ACTIVATION_SHA256,
            "role": activation["role"],
        },
    }


def build_protocol(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    require_pristine_result: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    parents = _v24187_inputs(root)
    if any(
        (root / name).exists() or (root / name).is_symlink()
        for name in MUST_REMAIN_ABSENT
    ):
        raise RuntimeError("V2.41.88 unattested Python bootstrap path appeared")
    if require_pristine_result and (
        (root / DEFAULT_RESULT).exists() or (root / DEFAULT_RESULT).is_symlink()
    ):
        raise FileExistsError("V2.41.88 result is not pristine")
    manifest = {
        relative: sha256(ordinary(root, relative)) for relative in CONTROL_FILES
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "label_blind": True,
        "parents": parents,
        "correction_contract": {
            "v24187_parent_artifact_sha_and_role_live_validation_is_real": True,
            "v24187_own_control_manifest_live_validation_is_real": True,
            "v24187_parent_control_manifest_live_replay_is_not_implemented": True,
            "v24187_activation_control_bytes_wording_is_overbroad": True,
            "v24187_phase_state_and_process_observation_claims_remain_unchanged": True,
            "v24188_supersedes_only_the_overbroad_control_bytes_wording": True,
        },
        "audit_contract": {
            "read_only_one_shot_create_exclusive": True,
            "replay_supported_manifest_formats": [
                "control_surface.manifest",
                "stable_manifest",
                "control_manifest",
                "frozen_dependencies",
                "sealed_activation_control_records",
            ],
            "validate_all_v24187_parent_artifact_sha_and_roles": True,
            "validate_all_available_parent_manifest_entries_and_absence_guards": True,
            "validate_v24183_v24185_v24186_activation_and_handoff_payload_seals": True,
            "validate_v24187_protocol_manifest_and_activation_payload_seal": True,
            "runtime_state_task_question_answer_evidence_prediction_mapping_gold_category_evaluator_score_read": False,
            "credential_or_network_access": False,
            "process_signal_restart_resume_rerun_skip_or_launch": False,
        },
        "control_surface": {
            "file_count": len(manifest),
            "manifest": manifest,
            "manifest_sha256": payload_sha(manifest),
            "must_remain_absent": list(MUST_REMAIN_ABSENT),
        },
        "authorization": {
            "v24187_source_or_protocol_modification": False,
            "active_watcher_signal_or_restart": False,
            "forward_code_prompt_model_search_budget_gate_threshold_or_controller_change": False,
            "benchmark_model_search_fetch_evaluator_or_api_call": False,
            "candidate_prepare_or_downstream_launch": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "claims": {
            "benchmark_score_available": False,
            "benchmark_improvement_observed": False,
            "avg_at_4_available": False,
            "entropy_or_credit_effect_observed": False,
            "leaderboard_submission_performed": False,
            "sota": False,
        },
    }
    value["decision_contract_sha256"] = payload_sha(
        {key: value[key] for key in DECISION_FIELDS}
    )
    return value


def validate_protocol(
    root: Path, path: Path = DEFAULT_PROTOCOL
) -> dict[str, Any]:
    root = root.resolve()
    raw = path if path.is_absolute() else root / path
    if (
        raw.resolve(strict=False) != (root / DEFAULT_PROTOCOL).resolve(strict=False)
        or raw.is_symlink()
        or not raw.is_file()
        or not raw.is_relative_to(root / "results")
    ):
        raise RuntimeError("V2.41.88 protocol path is noncanonical")
    value = read_object(raw)
    created = value.get("created_at_unix")
    if not isinstance(created, int) or isinstance(created, bool):
        raise RuntimeError("V2.41.88 created_at is invalid")
    if value != build_protocol(
        root, created_at_unix=created, require_pristine_result=False
    ):
        raise RuntimeError("V2.41.88 protocol differs from live rebuild")
    return {"path": raw, "sha256": sha256(raw), "value": value}


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
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--output", default=str(DEFAULT_PROTOCOL))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    output = Path(args.output)
    output = output if output.is_absolute() else root / output
    if (
        root != ROOT.resolve()
        or output.resolve(strict=False)
        != (root / DEFAULT_PROTOCOL).resolve(strict=False)
        or output.is_symlink()
    ):
        raise RuntimeError("V2.41.88 output path is noncanonical")
    value = build_protocol(root)
    publish_new(output, value)
    print(
        json.dumps(
            {
                "output": str(output),
                "sha256": sha256(output),
                "decision_contract_sha256": value["decision_contract_sha256"],
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
