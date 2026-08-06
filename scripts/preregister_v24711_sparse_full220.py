#!/usr/bin/env python3
"""Freeze the build-audited V2.47.11 sparse full-220 protocol."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24709_sparse_worldbank_adapter import TARGETS  # noqa: E402
from deepwide_agent.v24711_sparse_full220_contract import (  # noqa: E402
    ACTIVATION,
    AUTHORITY_SCOPE,
    BUILD_AUDIT,
    CONTROL_FREEZE,
    CONTROL_PREDICTIONS,
    CONTROL_RUN_SUMMARY,
    DESIGN,
    DOWNLOAD_CAP,
    DOWNLOAD_TIMEOUT_SECONDS,
    DOWNLOAD_WORKERS,
    EXECUTION_START,
    EXPECTED_APPLIED_TASKS,
    EXPECTED_ROUTE_ELIGIBLE,
    EXPECTED_TARGET_VALUES,
    EXPECTED_UNCHANGED_TASKS,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    INCIDENT,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    OUTPUT_ROOT,
    PREAUDIT,
    PROTOCOL,
    PROTOCOL_ID,
    ROLE,
    RUNNER_MARKER,
    SELECTED_COUNT,
    VISIBLE_MANIFEST,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    sealed,
    sha256,
    validate_control_rows,
    validate_visible_rows,
)


PACKAGE_BUILD = Path("results/v24712_sparse_full220_package_build_audit_v1_20260806.json")
DEPENDENCIES = (
    "src/deepwide_agent/__init__.py",
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24675_expanded_visible_schema.py",
    "src/deepwide_agent/v24701_visible_authority_namespace.py",
    "src/deepwide_agent/v24705_visible_authority_scope_repair.py",
    "src/deepwide_agent/v24709_sparse_worldbank_adapter.py",
    "src/deepwide_agent/v24711_sparse_full220_contract.py",
    "scripts/deepwide_api_lease.py",
    "scripts/preregister_v24711_sparse_full220.py",
    "scripts/control_v24711_sparse_full220.py",
    "scripts/run_v24711_sparse_full220.py",
    "scripts/audit_v24711_sparse_full220_forward.py",
    str(PACKAGE_BUILD),
    str(BUILD_AUDIT),
    str(DESIGN),
    str(INCIDENT),
    str(AUTHORITY_SCOPE),
    str(CONTROL_FREEZE),
    str(CONTROL_RUN_SUMMARY),
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


def _validate_build_parent(path: Path, role: str, authorization: str) -> dict[str, Any]:
    value = read_object(ROOT / path)
    if (
        value.get("role") != role
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(authorization) is not True
        or value.get("authorization", {}).get("activation_or_forward_launch")
        is not False
        or not sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError(f"V2.47.11 build parent drifted: {path}")
    return value


def build_protocol(
    *, now: int | None = None, require_clean: bool = True, require_pristine: bool = True
) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.47.11 protocol requires clean pushed HEAD")
    if require_pristine and any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (
            PROTOCOL,
            PREAUDIT,
            ACTIVATION,
            EXECUTION_START,
            FORWARD_RESULT,
            FORWARD_AUDIT,
            OUTPUT_ROOT,
        )
    ):
        raise RuntimeError("V2.47.11 future surface is not pristine")
    _validate_build_parent(
        BUILD_AUDIT,
        "v24710_sparse_worldbank_build_audit",
        "sparse_full220_forward_contract_and_protocol_design",
    )
    _validate_build_parent(
        PACKAGE_BUILD,
        "v24712_sparse_full220_package_build_audit",
        "protocol_publication",
    )
    control_rows = validate_control_rows(ROOT)
    visible_rows = validate_visible_rows(ROOT)
    control_ids = [row["opaque_id"] for row in control_rows]
    visible_ids = [row["opaque_id"] for row in visible_rows]
    if control_ids != visible_ids:
        raise RuntimeError("V2.47.11 control/visible order drifted")
    manifest: dict[str, str] = {}
    for relative in DEPENDENCIES:
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"V2.47.11 dependency is absent: {relative}")
        manifest[relative] = sha256(path)
    urls = [spec.url for spec in TARGETS]
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "runtime_build_audit_path": str(BUILD_AUDIT),
            "runtime_build_audit_sha256": sha256(ROOT / BUILD_AUDIT),
            "package_build_audit_path": str(PACKAGE_BUILD),
            "package_build_audit_sha256": sha256(ROOT / PACKAGE_BUILD),
            "design_path": str(DESIGN),
            "design_sha256": sha256(ROOT / DESIGN),
            "incident_path": str(INCIDENT),
            "incident_sha256": sha256(ROOT / INCIDENT),
            "authority_scope_path": str(AUTHORITY_SCOPE),
            "authority_scope_sha256": sha256(ROOT / AUTHORITY_SCOPE),
        },
        "task_contract": {
            "runtime_boundary": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "selected_ids_sha256": payload_sha256(control_ids),
            "visible_manifest_path": str(VISIBLE_MANIFEST),
            "visible_manifest_sha256": sha256(ROOT / VISIBLE_MANIFEST),
            "control_predictions_path": str(CONTROL_PREDICTIONS),
            "control_predictions_sha256": sha256(ROOT / CONTROL_PREDICTIONS),
            "control_freeze_path": str(CONTROL_FREEZE),
            "control_freeze_sha256": sha256(ROOT / CONTROL_FREEZE),
            "control_rows_are_prior_label_blind_frozen_forward_outputs": True,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_used_for_routing": False,
        },
        "mechanism": {
            "runtime_policy": "v24709_sparse_worldbank_bulk_adapter_v1",
            "full_denominator": SELECTED_COUNT,
            "expected_route_eligible_tasks": EXPECTED_ROUTE_ELIGIBLE,
            "expected_applied_tasks": EXPECTED_APPLIED_TASKS,
            "expected_unchanged_prediction_hash_tasks": EXPECTED_UNCHANGED_TASKS,
            "expected_official_target_values": EXPECTED_TARGET_VALUES,
            "nontrigger_control_prediction_byte_reuse": True,
            "whole_task_fail_closed_if_any_binding_or_value_missing": True,
            "country_and_capital_cells_preserved": True,
            "entropy_credit_assigned": False,
            "exploratory_due_to_preimplementation_incident": True,
        },
        "execution": {
            "runner_marker": RUNNER_MARKER,
            "output_root": str(OUTPUT_ROOT),
            "download_urls": urls,
            "download_urls_sha256": payload_sha256(urls),
            "download_cap": DOWNLOAD_CAP,
            "download_workers": DOWNLOAD_WORKERS,
            "download_timeout_seconds": DOWNLOAD_TIMEOUT_SECONDS,
            "per_country_requests": 0,
            "model_calls": 0,
            "search_calls": 0,
            "one_shot_no_resume_retry_skip_or_selective_rerun": True,
            "protected_watchers": protected_watcher_snapshot(),
        },
        "lease": {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "single_owner_nonblocking": True,
        },
        "prediction_freeze_contract": {
            "required_terminal_predictions": SELECTED_COUNT,
            "all_predictions_frozen_before_mapping_gold_evaluator_or_score_open": True,
            "unchanged_rows_selected_only_by_prediction_hash_after_freeze": True,
            "historical_evaluator_rows_may_only_be_reused_postfreeze": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "raw_benchmark_dataset_in_forward_manifest": False,
            "mapping_gold_evaluator_score_or_reward_in_forward_manifest": False,
            "forward_task_input_keys": ["opaque_id", "question"],
            "same_run_evaluator_feedback_used_for_forward": False,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "activation_or_forward_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        },
        "non_claims": {
            "fresh_full220_forward": False,
            "unseen_or_heldout": False,
            "avg_at_4": False,
            "generic_namespace_transfer": False,
            "entropy_credit_validated": False,
            "sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return value


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


if __name__ == "__main__":
    protocol = build_protocol()
    publish_new(ROOT / PROTOCOL, protocol)
    print(
        json.dumps(
            {
                "path": str(PROTOCOL),
                "selected": SELECTED_COUNT,
                "authorization": protocol["authorization"],
            },
            sort_keys=True,
        )
    )
