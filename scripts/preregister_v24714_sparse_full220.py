#!/usr/bin/env python3
"""Freeze the append-only V2.47.14 opaque-ID join successor protocol."""

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
from deepwide_agent import v24714_sparse_full220_order_join as contract  # noqa: E402


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
    "src/deepwide_agent/v24714_sparse_full220_order_join.py",
    "scripts/deepwide_api_lease.py",
    "scripts/run_v24711_sparse_full220.py",
    "scripts/preregister_v24714_sparse_full220.py",
    "scripts/control_v24714_sparse_full220.py",
    "scripts/run_v24714_sparse_full220.py",
    "scripts/audit_v24714_sparse_full220_forward.py",
    str(contract.PACKAGE_BUILD),
    str(contract.ORDER_FAILURE),
    str(contract.BUILD_AUDIT),
    str(contract.DESIGN),
    str(contract.INCIDENT),
    str(contract.AUTHORITY_SCOPE),
    str(contract.CONTROL_FREEZE),
    str(contract.CONTROL_RUN_SUMMARY),
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _parent(path: Path, role: str, authorization: str) -> dict[str, Any]:
    value = contract.read_object(ROOT / path)
    if (
        value.get("role") != role
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("authorization", {}).get(authorization) is not True
        or value.get("authorization", {}).get("activation_or_forward_launch") is not False
        or not contract.sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError(f"V2.47.14 build parent drifted: {path}")
    return value


def _failure_parent() -> dict[str, Any]:
    value = contract.read_object(ROOT / contract.ORDER_FAILURE)
    if (
        value.get("role") != "v24713_v24711_protocol_order_failure"
        or value.get("status")
        != "zero_effect_protocol_build_failure_append_only_repair_required"
        or value.get("authorization", {}).get("append_only_order_join_repair_build")
        is not True
        or value.get("authorization", {}).get("activation_or_forward_launch") is not False
        or value.get("repair_contract", {}).get("join_key") != "opaque_id"
    ):
        raise RuntimeError("V2.47.14 order-failure parent drifted")
    return value


def build_protocol(
    *, now: int | None = None, require_clean: bool = True, require_pristine: bool = True
) -> dict[str, Any]:
    if require_clean and (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
    ):
        raise RuntimeError("V2.47.14 protocol requires clean pushed HEAD")
    if require_pristine and any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (
            contract.PROTOCOL, contract.PREAUDIT, contract.ACTIVATION,
            contract.EXECUTION_START, contract.FORWARD_RESULT,
            contract.FORWARD_AUDIT, contract.OUTPUT_ROOT,
        )
    ):
        raise RuntimeError("V2.47.14 future surface is not pristine")
    _parent(
        contract.PACKAGE_BUILD,
        "v24715_order_join_package_build_audit",
        "protocol_publication",
    )
    _failure_parent()
    visible = contract.ordered_visible_rows(ROOT)
    control = contract.validate_control_rows(ROOT)
    ids = [row["opaque_id"] for row in control]
    if [row["opaque_id"] for row in visible] != ids:
        raise RuntimeError("V2.47.14 ordered join drifted")
    manifest: dict[str, str] = {}
    for relative in DEPENDENCIES:
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"V2.47.14 dependency absent: {relative}")
        manifest[relative] = contract.sha256(path)
    urls = [spec.url for spec in TARGETS]
    value = {
        "artifact_version": 1,
        "role": contract.ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "order_failure_path": str(contract.ORDER_FAILURE),
            "order_failure_sha256": contract.sha256(ROOT / contract.ORDER_FAILURE),
            "package_build_path": str(contract.PACKAGE_BUILD),
            "package_build_sha256": contract.sha256(ROOT / contract.PACKAGE_BUILD),
            "v24710_build_audit_path": str(contract.BUILD_AUDIT),
            "v24710_build_audit_sha256": contract.sha256(ROOT / contract.BUILD_AUDIT),
        },
        "task_contract": {
            "runtime_boundary": ["opaque_id", "question"],
            "selected_count": contract.SELECTED_COUNT,
            "selected_ids_sha256": contract.payload_sha256(ids),
            "visible_manifest_path": str(contract.VISIBLE_MANIFEST),
            "visible_manifest_sha256": contract.sha256(ROOT / contract.VISIBLE_MANIFEST),
            "control_predictions_path": str(contract.CONTROL_PREDICTIONS),
            "control_predictions_sha256": contract.sha256(ROOT / contract.CONTROL_PREDICTIONS),
            "control_freeze_path": str(contract.CONTROL_FREEZE),
            "control_freeze_sha256": contract.sha256(ROOT / contract.CONTROL_FREEZE),
            "join_key": "opaque_id",
            "canonical_output_order": "frozen_control_prediction_order",
            "raw_file_order_equality_required": False,
            "unique_id_set_equality_required": True,
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_used_for_join": False,
        },
        "mechanism": {
            "runtime_policy": "v24709_sparse_worldbank_bulk_adapter_v1",
            "full_denominator": contract.SELECTED_COUNT,
            "expected_route_eligible_tasks": contract.EXPECTED_ROUTE_ELIGIBLE,
            "expected_applied_tasks": contract.EXPECTED_APPLIED_TASKS,
            "expected_unchanged_prediction_hash_tasks": contract.EXPECTED_UNCHANGED_TASKS,
            "expected_official_target_values": contract.EXPECTED_TARGET_VALUES,
            "nontrigger_control_prediction_byte_reuse": True,
            "whole_task_fail_closed_if_any_binding_or_value_missing": True,
            "country_and_capital_cells_preserved": True,
            "entropy_credit_assigned": False,
            "only_change_from_v24711": "opaque_id_unique_join_replaces_raw_file_order_equality",
        },
        "execution": {
            "runner_marker": contract.RUNNER_MARKER,
            "output_root": str(contract.OUTPUT_ROOT),
            "download_urls": urls,
            "download_urls_sha256": contract.payload_sha256(urls),
            "download_cap": contract.DOWNLOAD_CAP,
            "download_workers": contract.DOWNLOAD_WORKERS,
            "download_timeout_seconds": contract.DOWNLOAD_TIMEOUT_SECONDS,
            "per_country_requests": 0,
            "model_calls": 0,
            "search_calls": 0,
            "one_shot_no_resume_retry_skip_or_selective_rerun": True,
            "protected_watchers": contract.protected_watcher_snapshot(),
        },
        "lease": {
            "path": str(contract.LEASE_PATH),
            "owner": contract.LEASE_OWNER,
            "purpose": contract.LEASE_PURPOSE,
            "single_owner_nonblocking": True,
        },
        "prediction_freeze_contract": {
            "required_terminal_predictions": contract.SELECTED_COUNT,
            "all_predictions_frozen_before_mapping_gold_evaluator_or_score_open": True,
            "unchanged_rows_selected_only_by_prediction_hash_after_freeze": True,
            "historical_evaluator_rows_may_only_be_reused_postfreeze": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": contract.payload_sha256(manifest),
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
    value["protocol_payload_sha256"] = contract.payload_sha256(value)
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_protocol()
    publish(ROOT / contract.PROTOCOL, value)
    print(json.dumps({"path": str(contract.PROTOCOL), "selected": contract.SELECTED_COUNT, "authorization": value["authorization"]}, sort_keys=True))
