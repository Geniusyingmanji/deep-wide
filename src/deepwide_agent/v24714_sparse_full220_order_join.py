"""Append-only order-join repair for the V2.47.11 sparse full-220 package."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from . import v24711_sparse_full220_contract as base


DATE = base.DATE
PROTOCOL_ID = "v24714_sparse_worldbank_opaque_join_full220_v1"
ROLE = "v24714_sparse_full220_preregistration"
PROTOCOL = Path(f"results/v24714_sparse_full220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24714_sparse_full220_preactivation_audit_v1_{DATE}.json")
ACTIVATION = Path(f"results/v24714_sparse_full220_activation_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24714_sparse_full220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24714_sparse_full220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24714_sparse_full220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24714_sparse_full220_v1_{DATE}")
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
DOWNLOAD_RECEIPT = OUTPUT_ROOT / "bulk_download_receipt.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
ORDER_FAILURE = Path(f"results/v24713_v24711_protocol_order_failure_v1_{DATE}.json")
PACKAGE_BUILD = Path(f"results/v24715_order_join_package_build_audit_v1_{DATE}.json")
RUNNER_MARKER = "scripts/run_v24714_sparse_full220.py"
LEASE_OWNER = "v24714_sparse_full220_forward_v1"
LEASE_PURPOSE = "label_blind_sparse_worldbank_opaque_join_full220"

SELECTED_COUNT = base.SELECTED_COUNT
EXPECTED_ROUTE_ELIGIBLE = base.EXPECTED_ROUTE_ELIGIBLE
EXPECTED_APPLIED_TASKS = base.EXPECTED_APPLIED_TASKS
EXPECTED_UNCHANGED_TASKS = base.EXPECTED_UNCHANGED_TASKS
EXPECTED_TARGET_VALUES = base.EXPECTED_TARGET_VALUES
DOWNLOAD_WORKERS = base.DOWNLOAD_WORKERS
DOWNLOAD_TIMEOUT_SECONDS = base.DOWNLOAD_TIMEOUT_SECONDS
DOWNLOAD_CAP = base.DOWNLOAD_CAP
VISIBLE_MANIFEST = base.VISIBLE_MANIFEST
CONTROL_PREDICTIONS = base.CONTROL_PREDICTIONS
CONTROL_FREEZE = base.CONTROL_FREEZE
CONTROL_RUN_SUMMARY = base.CONTROL_RUN_SUMMARY
BUILD_AUDIT = base.BUILD_AUDIT
DESIGN = base.DESIGN
INCIDENT = base.INCIDENT
AUTHORITY_SCOPE = base.AUTHORITY_SCOPE
LEASE_PATH = base.LEASE_PATH
PREAUDIT_AUTHORIZATION = base.PREAUDIT_AUTHORIZATION
ACTIVATION_AUTHORIZATION = base.ACTIVATION_AUTHORIZATION
START_AUTHORIZATION = base.START_AUTHORIZATION
payload_sha256 = base.payload_sha256
sha256 = base.sha256
read_object = base.read_object
read_jsonl = base.read_jsonl
sealed = base.sealed
protected_watcher_snapshot = base.protected_watcher_snapshot
validate_control_rows = base.validate_control_rows
validate_control_freeze = base.validate_control_freeze
validate_visible_rows = base.validate_visible_rows


def ordered_visible_rows(root: Path) -> list[dict[str, str]]:
    """Uniquely join visible rows to the frozen control prediction order."""

    visible = validate_visible_rows(root)
    control = validate_control_rows(root)
    by_id = {row["opaque_id"]: row for row in visible}
    control_ids = [row["opaque_id"] for row in control]
    if (
        len(by_id) != SELECTED_COUNT
        or len(control_ids) != SELECTED_COUNT
        or len(set(control_ids)) != SELECTED_COUNT
        or set(by_id) != set(control_ids)
    ):
        raise RuntimeError("V2.47.14 visible/control opaque-ID set drifted")
    ordered = [by_id[opaque_id] for opaque_id in control_ids]
    if [row["opaque_id"] for row in ordered] != control_ids:
        raise RuntimeError("V2.47.14 visible/control order join drifted")
    return ordered


def validate_protocol(root: Path, path: Path = PROTOCOL) -> dict[str, Any]:
    value = read_object(root / path)
    manifest = value.get("dependency_manifest")
    task = value.get("task_contract", {})
    execution = value.get("execution", {})
    ordered = ordered_visible_rows(root)
    control = validate_control_rows(root)
    control_ids = [row["opaque_id"] for row in control]
    if (
        value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or not sealed(value, "protocol_payload_sha256")
        or not isinstance(manifest, dict)
        or value.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or any(sha256(root / relative) != digest for relative, digest in manifest.items())
        or task.get("runtime_boundary") != ["opaque_id", "question"]
        or task.get("selected_count") != SELECTED_COUNT
        or task.get("selected_ids_sha256") != payload_sha256(control_ids)
        or task.get("visible_manifest_sha256") != sha256(root / VISIBLE_MANIFEST)
        or task.get("control_predictions_sha256") != sha256(root / CONTROL_PREDICTIONS)
        or task.get("control_freeze_sha256") != sha256(root / CONTROL_FREEZE)
        or task.get("join_key") != "opaque_id"
        or task.get("canonical_output_order") != "frozen_control_prediction_order"
        or [row["opaque_id"] for row in ordered] != control_ids
        or execution.get("runner_marker") != RUNNER_MARKER
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("download_cap") != DOWNLOAD_CAP
        or execution.get("download_workers") != DOWNLOAD_WORKERS
        or execution.get("download_timeout_seconds") != DOWNLOAD_TIMEOUT_SECONDS
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "activation_or_forward_launch": False,
            "evaluator": False,
            "leaderboard_or_sota": False,
        }
    ):
        raise RuntimeError("V2.47.14 protocol drifted")
    return value


def validate_stage(
    root: Path,
    path: Path,
    *,
    role: str,
    seal_field: str,
    authorization: Mapping[str, bool],
) -> dict[str, Any]:
    value = read_object(root / path)
    if (
        value.get("artifact_version") != 1
        or value.get("role") != role
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("authorization") != dict(authorization)
        or not sealed(value, seal_field)
    ):
        raise RuntimeError(f"V2.47.14 {role} drifted")
    return value


__all__ = [name for name in globals() if name.isupper()] + [
    "ordered_visible_rows",
    "payload_sha256",
    "protected_watcher_snapshot",
    "read_jsonl",
    "read_object",
    "sealed",
    "sha256",
    "validate_control_rows",
    "validate_protocol",
    "validate_stage",
]
