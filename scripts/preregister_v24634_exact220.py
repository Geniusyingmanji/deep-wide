#!/usr/bin/env python3
"""Freeze the one-shot V2.46.34 exact-220 forward contract."""

from __future__ import annotations

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

from deepwide_agent.v24634_exact220_contract import (  # noqa: E402
    ACTIVATION,
    ARM,
    CHILD_MARKER,
    CHILD_TERMINAL_NAME,
    CLEANUP_RESERVE_SECONDS,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    LIMITS,
    MINIMUM_MODEL_ATTEMPT_SECONDS,
    MODEL,
    MODEL_SLOT_CAP,
    MODEL_SLOT_POOL_ID,
    OUTPUT_ROOT,
    PARENT_DEADLINE_GRACE_SECONDS,
    PARENT_EXIT_NAME,
    PREAUDIT,
    PROTOCOL_ID,
    ROLE,
    RUNNER_MARKER,
    SEARCH,
    SELECTED_COUNT,
    SINGLE_CHANGE_CONTRACT,
    SOURCE_MANIFEST,
    TWO_WAVE_POLICY,
    CROSS_VERSION_POPULATION_POLICY,
    validate_capacity_parent,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
    source_selected_ids,
)


DEPENDENCIES = (
    "src/deepwide_agent/__init__.py",
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24267_total_fallback.py",
    "src/deepwide_agent/v24268_keyless_batched_runtime.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24272_two_wave_entropy_voc.py",
    "src/deepwide_agent/v24272_two_wave_retrieval.py",
    "src/deepwide_agent/v24273_two_wave_task_runtime.py",
    "src/deepwide_agent/v24270_budget_equivalent_union.py",
    "src/deepwide_agent/v24275_forward_contract.py",
    "src/deepwide_agent/v24275_hard_deadline_fetch.py",
    "src/deepwide_agent/v24280_task_union_single_shot.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24287_forward_contract.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24289_low_coverage_rescue.py",
    "src/deepwide_agent/v24290_low_coverage_task_runtime.py",
    "src/deepwide_agent/v24294_staged_reserve.py",
    "src/deepwide_agent/v24296_staged_reserve_task_runtime.py",
    "src/deepwide_agent/v24299_synthesis_recovery.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24310_paired_dev_runtime.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24318_deadline_conservation_runtime.py",
    "src/deepwide_agent/v24319_runner_integration.py",
    "src/deepwide_agent/v24468_total_wall_transport.py",
    "src/deepwide_agent/v24630_thin_backfill_search.py",
    "src/deepwide_agent/v24630_exact220_task_integration.py",
    "src/deepwide_agent/v24634_exact220_contract.py",
    "scripts/deepwide_api_lease.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/v24468_total_wall_http_helper.py",
    "scripts/preregister_v24634_exact220.py",
    "scripts/audit_v24634_exact220.py",
    "scripts/activate_v24634_exact220.py",
    "scripts/authorize_v24634_exact220_start.py",
    "scripts/run_v24634_exact220_task.py",
    "scripts/run_v24634_exact220.py",
    "scripts/audit_v24634_exact220_forward.py",
)


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=True,
    ).stdout.strip()


def build_forward_contract(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    if require_pristine:
        status = _git(root, "status", "--porcelain")
        head = _git(root, "rev-parse", "HEAD")
        target = _git(root, "rev-parse", "target/main")
        if status or head != target:
            raise RuntimeError("V2.46.34 contract requires clean HEAD == target/main")
        if any(
            (root / path).exists() or (root / path).is_symlink()
            for path in (FORWARD_CONTRACT, PREAUDIT, ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)
        ):
            raise RuntimeError("V2.46.34 future surface is not pristine")
    manifest = {}
    for relative in DEPENDENCIES:
        path = root / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"V2.46.34 dependency is absent: {relative}")
        manifest[relative] = sha256(path)
    ids = source_selected_ids(root)
    capacity_parent = validate_capacity_parent(root)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "task_contract": {
            "runtime_boundary": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "selected_opaque_ids": ids,
            "selected_opaque_ids_sha256": payload_sha256(ids),
            "manifest_path": str(SOURCE_MANIFEST),
            "manifest_sha256": sha256(root / SOURCE_MANIFEST),
            "mapping_split_category_gold_score_used_for_selection": False,
        },
        "execution": {
            "arm": ARM,
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model_slot_pool_id": MODEL_SLOT_POOL_ID,
            "child_terminal_receipt_name": CHILD_TERMINAL_NAME,
            "parent_exit_receipt_name": PARENT_EXIT_NAME,
            "runner_marker": RUNNER_MARKER,
            "child_marker": CHILD_MARKER,
            "output_root": str(OUTPUT_ROOT),
            "protected_watchers": protected_watcher_snapshot(),
        },
        "capacity_parent": capacity_parent,
        "single_change_contract": SINGLE_CHANGE_CONTRACT,
        "cross_version_population_policy": CROSS_VERSION_POPULATION_POLICY,
        "deadline_contract": {
            "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
            "minimum_attempt_seconds": MINIMUM_MODEL_ATTEMPT_SECONDS,
            "parent_deadline_grace_seconds": PARENT_DEADLINE_GRACE_SECONDS,
            "model_and_search_share_absolute_deadline": True,
            "provider_requests_use_process_enforced_total_wall": True,
        },
        "limits": LIMITS,
        "two_wave_policy": TWO_WAVE_POLICY,
        "model": MODEL,
        "search": SEARCH,
        "lease": {
            "path": str(LEASE_PATH), "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE, "nonblocking_single_owner": True,
        },
        "fixed_denominator_contract": {
            "required_terminal_predictions": SELECTED_COUNT,
            "parent_timeout_or_failure_projects_fallback": True,
            "all_220_predictions_frozen_before_evaluator_resources_open": True,
            "child_success_or_receipt_completeness_not_required_for_postfreeze_evaluator": True,
            "no_selective_retry_resume_skip_or_revaluation": True,
        },
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "evaluator_surface_absent_from_forward_dependency_manifest": True,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "preactivation_audit_design": True,
            "single_fresh_exact220_forward": False,
            "resume_retry_skip_or_rerun": False,
        },
        "claims": {
            "benchmark_score_before_postfreeze_evaluation": False,
            "avg_at_4": False,
            "leaderboard_submission": False,
            "sota": False,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
    }
    value["forward_contract_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    contract = build_forward_contract()
    publish_new(ROOT / FORWARD_CONTRACT, contract)
    print(json.dumps({"path": str(FORWARD_CONTRACT), "selected": SELECTED_COUNT}, sort_keys=True))
