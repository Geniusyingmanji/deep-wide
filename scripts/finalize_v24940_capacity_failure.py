#!/usr/bin/env python3
"""Seal the pre-model V2.49.40 source-capacity failure."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24940_open_world_ledger_external_contract as contract  # noqa: E402
from scripts import run_v24923_target_value_external as engine  # noqa: E402
from scripts import run_v24940_open_world_ledger_external as runner  # noqa: E402


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
        raise RuntimeError("V2.49.40 finalizer expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.40 finalizer expected JSON object")
    return value


def _publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _lease_free() -> bool:
    path = ROOT / contract.LEASE_PATH
    with path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return True


def main() -> None:
    if subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, stdout=subprocess.PIPE, text=True, check=True).stdout.strip():
        raise RuntimeError("V2.49.40 finalizer requires clean worktree")
    if contract.FORWARD_RESULT.exists() or contract.FORWARD_AUDIT.exists():
        raise FileExistsError("V2.49.40 failure artifact already exists")
    protocol = _read(ROOT / contract.PROTOCOL)
    start = _read(ROOT / contract.EXECUTION_START)
    snapshot = ROOT / contract.SNAPSHOT_ROOT
    catalog_path = ROOT / contract.CATALOG_RESPONSE
    target_path = ROOT / contract.TARGET_RESPONSE_ROOT / "response_01.bin"
    observed_files = sorted(
        str(path.relative_to(ROOT / contract.OUTPUT_ROOT))
        for path in (ROOT / contract.OUTPUT_ROOT).rglob("*")
        if path.is_file()
    )
    expected_files = [
        "snapshot/country_catalog.bin",
        "snapshot/target_responses/response_01.bin",
    ]
    catalog = engine.parse_catalog(catalog_path.read_bytes())
    _page, values = runner.parse_target(
        target_path.read_bytes(), dict(contract.TARGETS[0]), contract.TARGET_URLS[0]
    )
    common = set(catalog).intersection(values)
    eligible = {
        iso3 for iso3 in common if catalog[iso3]["region_id"] not in {"NA", ""}
    }
    checks = {
        "protocol_sealed": contract.sealed(protocol, "protocol_payload_sha256"),
        "execution_start_sealed": contract.sealed(start, "execution_start_payload_sha256"),
        "single_external_forward_was_authorized": start.get("authorization", {}).get("single_external_forward") is True,
        "snapshot_files_exactly_catalog_and_one_target_response": observed_files == expected_files,
        "capacity_below_preregistered_requirement": len(eligible) < contract.SELECTED_RECORD_COUNT,
        "no_visible_tasks_materialized": not (ROOT / contract.VISIBLE_TASKS).exists(),
        "task_directory_created_but_empty": (ROOT / contract.TASK_ROOT).is_dir()
        and not any((ROOT / contract.TASK_ROOT).iterdir()),
        "model_slot_directory_created_but_empty": (ROOT / contract.MODEL_SLOT_DIRECTORY).is_dir()
        and not any((ROOT / contract.MODEL_SLOT_DIRECTORY).iterdir()),
        "no_predictions_or_projections_materialized": not any((ROOT / path).exists() for path in (contract.PREDICTIONS, contract.PROJECTIONS, contract.PREDICTION_FREEZE, contract.RUN_SUMMARY)),
        "no_evaluator_surface_materialized": not any((ROOT / path).exists() for path in (contract.EVALUATOR_PROTOCOL, contract.RESULT, contract.POSTAUDIT)),
        "shared_api_lease_released": _lease_free(),
        "protected_watchers_unchanged": contract.protected_watcher_snapshot() == protocol["execution"]["protected_watchers"],
    }
    if not all(checks.values()):
        raise RuntimeError(f"V2.49.40 capacity failure audit failed: {[name for name, passed in checks.items() if not passed]}")
    result: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24940_open_world_ledger_external_capacity_failure",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "status": "capacity_precondition_failed_before_task_materialization",
        "catalog_response_sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        "target_response_sha256": hashlib.sha256(target_path.read_bytes()).hexdigest(),
        "catalog_record_count": len(catalog),
        "target_nonnull_record_count": len(values),
        "common_record_count": len(common),
        "eligible_real_record_count": len(eligible),
        "preregistered_required_record_count": contract.SELECTED_RECORD_COUNT,
        "capacity_shortfall": contract.SELECTED_RECORD_COUNT - len(eligible),
        "effects": {
            "official_http_requests": 1 + len(contract.TARGETS),
            "visible_tasks_materialized": 0,
            "model_requests": 0,
            "predictions": 0,
            "evaluator_calls": 0,
        },
        "failure_as_zero_quality_result_created": False,
        "same_population_retry_resume_or_rerun_authorized": False,
        "deepwidebench_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "claim_scope": {
            "external_quality_measured": False,
            "deepwidebench_quality_measured": False,
            "entropy_or_signed_credit_validated": False,
            "sota_supported": False,
        },
        "authorization": {
            "same_population_retry_resume_or_rerun": False,
            "evaluator": False,
            "public_exact220": False,
            "sota_claim": False,
        },
    }
    result["result_payload_sha256"] = contract.payload_sha256(result)
    _publish(ROOT / contract.FORWARD_RESULT, result)
    audit: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24940_open_world_ledger_external_capacity_failure_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "forward_failure_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "checks": checks,
        "findings": [],
        "audit_valid": True,
        "observed_output_files": observed_files,
        "no_model_prediction_or_evaluator_effect": True,
        "network_model_or_evaluator_called_by_audit": False,
        "authorization": {
            "fresh_disjoint_successor_design": True,
            "same_population_retry_resume_or_rerun": False,
            "evaluator": False,
            "public_exact220": False,
        },
    }
    audit["audit_payload_sha256"] = contract.payload_sha256(audit)
    _publish(ROOT / contract.FORWARD_AUDIT, audit)
    print(json.dumps({"result": str(contract.FORWARD_RESULT), "audit": str(contract.FORWARD_AUDIT), "eligible": len(eligible), "required": contract.SELECTED_RECORD_COUNT}, sort_keys=True))


if __name__ == "__main__":
    main()
