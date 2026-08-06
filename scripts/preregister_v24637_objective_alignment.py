#!/usr/bin/env python3
"""Freeze the one-shot V2.46.37 external objective-alignment protocol."""

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

from deepwide_agent.v24637_external_contract import (  # noqa: E402
    ACTIVATION, ARM_COUNT, CHILD_MARKER, CLEANUP_RESERVE_SECONDS, EXECUTION_START,
    EXECUTOR_CONCURRENCY, FORWARD_RESULT, FORWARD_ROLE, LEASE_OWNER, LEASE_PATH,
    LEASE_PURPOSE, LIMITS, MINIMUM_MODEL_ATTEMPT_SECONDS, MODEL, MODEL_SLOT_CAP,
    OUTPUT_ROOT, PARENT_TIMEOUT_SECONDS, PREAUDIT, PROTECTED_WATCHERS, PROTOCOL,
    PROTOCOL_ID, RUNNER_MARKER, SEARCH, SELECTED_COUNT, payload_sha256,
    protected_watcher_snapshot, sha256, task_vector,
)

PREDECESSOR_PROTOCOL = Path("results/v24637_objective_alignment_preregistration_v1_20260806.json")
PREDECESSOR_NO_GO = Path("results/v24637_objective_alignment_preregistration_v1_20260806_NO_GO.json")


DEPENDENCIES = (
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24272_two_wave_entropy_voc.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24468_total_wall_transport.py",
    "src/deepwide_agent/v24630_thin_backfill_search.py",
    "src/deepwide_agent/v24637_objective_alignment_runtime.py",
    "src/deepwide_agent/v24637_external_contract.py",
    "scripts/deepwide_api_lease.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/v24468_total_wall_http_helper.py",
    "scripts/run_v24637_objective_alignment_task.py",
    "scripts/run_v24637_objective_alignment.py",
    "scripts/preregister_v24637_objective_alignment.py",
    "scripts/audit_v24637_objective_alignment.py",
    "scripts/activate_v24637_objective_alignment.py",
    "scripts/authorize_v24637_objective_alignment_start.py",
)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout.strip()


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


def build_protocol(*, now: int | None = None, require_pristine: bool = True) -> dict[str, Any]:
    if require_pristine:
        if _git("status", "--porcelain") or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main"):
            raise RuntimeError("V2.46.37 protocol requires clean HEAD == target/main")
        if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (PROTOCOL, PREAUDIT, ACTIVATION, EXECUTION_START, FORWARD_RESULT, OUTPUT_ROOT)):
            raise RuntimeError("V2.46.37 future surface is not pristine")
    manifest = {}
    for relative in DEPENDENCIES:
        path = ROOT / relative
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(f"V2.46.37 dependency absent: {relative}")
        manifest[relative] = sha256(path)
    tasks = task_vector()
    ids = [task["opaque_id"] for task in tasks]
    questions = [task["question"] for task in tasks]
    value = {
        "artifact_version": 1,
        "role": FORWARD_ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "scope": "benchmark_external_ourairports_exact_table_objective_alignment",
        "append_only_successor": {
            "predecessor_protocol_path": str(PREDECESSOR_PROTOCOL),
            "predecessor_protocol_sha256": sha256(ROOT / PREDECESSOR_PROTOCOL),
            "predecessor_no_go_path": str(PREDECESSOR_NO_GO),
            "predecessor_no_go_sha256": sha256(ROOT / PREDECESSOR_NO_GO),
            "predecessor_activation_execution_or_effect_reused": False,
            "only_change": "credential_prefix_scanner_requires_left_token_boundary",
            "runtime_tasks_budgets_gold_and_gate_unchanged": True,
        },
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_tasks": SELECTED_COUNT,
            "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT,
            "selected_opaque_ids": ids,
            "selected_opaque_ids_sha256": payload_sha256(ids),
            "visible_question_vector_sha256": payload_sha256(questions),
            "fresh_entity_count": 96,
            "fresh_entities_disjoint_from_prior_4192_external_entities": True,
            "gold_code_values_absent_from_forward_contract": True,
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
            "runner_marker": RUNNER_MARKER,
            "child_marker": CHILD_MARKER,
            "output_root": str(OUTPUT_ROOT),
            "protected_watchers": protected_watcher_snapshot(),
            "balanced_arm_order_by_opaque_id_parity": True,
        },
        "paired_design": {
            "shared_plan_search_fetch_evidence_prefix": True,
            "baseline": "frozen_score_first_synthesis_prompt",
            "candidate": "visible_schema_entity_coverage_ledger_and_completion_check_prompt",
            "candidate_additional_query_fetch_model_or_token_cap": False,
            "entropy_is_shadow_only": True,
            "entropy_routes_forward_or_assigns_positive_credit": False,
            "postfreeze_outer_utility_required_for_credit": True,
        },
        "limits": LIMITS,
        "model": MODEL,
        "search": SEARCH,
        "deadline": {
            "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
            "minimum_attempt_seconds": MINIMUM_MODEL_ATTEMPT_SECONDS,
            "model_and_search_share_absolute_deadline": True,
        },
        "lease": {"path": str(LEASE_PATH), "owner": LEASE_OWNER, "purpose": LEASE_PURPOSE, "nonblocking": True},
        "evaluator_separation": {
            "all_predictions_frozen_before_evaluator_protocol_or_gold_open": True,
            "forward_dependency_manifest_excludes_external_evaluator_and_gold": True,
            "fixed_denominator_failure_as_zero": True,
            "primary_metric": "exact_table_successes",
            "guardrail": "candidate_composite_not_lower",
            "go_requires_strict_exact_table_gain_and_nonnegative_composite_delta": True,
        },
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read_by_forward": False,
            "question_prediction_query_url_page_entity_or_credential_emitted_in_content_free_receipts": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "deepwidebench_task_prediction_gold_or_error_pattern_used_for_task_design": False,
        },
        "authorization": {
            "preactivation_audit_design": True,
            "one_external_forward_launch": False,
            "postfreeze_evaluator_design": False,
            "dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
    }
    value["protocol_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    protocol = build_protocol()
    publish_new(ROOT / PROTOCOL, protocol)
    print(json.dumps({"path": str(PROTOCOL), "tasks": SELECTED_COUNT}, sort_keys=True))
