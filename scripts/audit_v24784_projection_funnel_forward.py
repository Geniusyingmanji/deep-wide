#!/usr/bin/env python3
"""Post-freeze, label-blind mechanism audit for the V2.47.84 forward.

The audit runs only after all predictions are frozen.  It reads the public
visible task, public trusted-child projection, and content-free process/model/
transport receipts for each fixed ordinal, then replays the summary exactly.
It never opens the V2.47.83 private population, benchmark mapping, truth,
quality, score, reward, category, split, or evaluator surfaces.

Mechanism GO requires one *same task* to jointly contain a validated funnel,
an emitted projection, a projection-backed two-source Unknown proposal, and a
safe Unknown-only cell change.  Cross-task aggregate co-occurrence cannot
substitute.  GO authorizes only design of a task-cluster-disjoint paired dev64;
it does not authorize evaluation, another forward, dev64 execution, exact-220,
entropy credit, leaderboard, or SOTA claims.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import validate_parent_receipt  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import validate_receipt as validate_model_receipt  # noqa: E402
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24784_projection_funnel_integration import validate_projection  # noqa: E402
from deepwide_agent import v24784_projection_funnel_execution_contract as contract  # noqa: E402
from scripts import preregister_v24784_projection_funnel_external as protocol_module  # noqa: E402


TASK_RECEIPT_KEYS = frozenset(
    {
        "ordinal",
        "parent_receipt_sha256",
        "parent_receipt_valid",
        "failure_taxonomy",
        "model_receipt_sha256",
        "model_receipt_present",
        "model_receipt_valid",
        "model_acquisitions",
        "model_slot_timeouts",
        "transport_receipt_sha256",
        "transport_receipt_present",
        "transport_receipt_valid",
        "hosted_search_attempts",
        "hard_fetch_helper_calls",
        "fetch_deadline_rejections",
        "parent_effect_receipt_flags_match",
        "result_projection_sha256",
        "result_projection_valid",
        "observation",
        "funnel_reason_counts",
        "strict_task_local_joint",
    }
)
EFFECT_METRIC_NAMES = frozenset(
    {
        "task_receipt_count",
        "valid_parent_receipt_count",
        "valid_model_receipt_count",
        "valid_transport_receipt_count",
        "model_acquisition_count",
        "model_slot_timeout_count",
        "hosted_search_attempt_count",
        "hard_fetch_helper_call_count",
        "fetch_deadline_rejection_count",
        "all_task_fetch_request_count",
        "strict_task_local_joint_count",
    }
)
HEALTH_CHECK_NAMES = frozenset(
    {
        "eight_of_eight_terminal_ordinals",
        "fixed_denominator_failure_as_zero",
        "parent_taxonomy_matches_run_summary",
        "summary_exact_task_local_replay",
        "all_task_ordinals_submitted_once",
        "within_experiment_wall_ceiling",
        "eight_of_eight_content_free_effect_receipt_pairs_valid",
        "effect_receipts_match_parent_flags",
        "model_acquisitions_within_frozen_caps",
        "model_logical_attempts_within_frozen_caps",
        "hosted_search_attempts_within_transport_retry_cap",
        "physical_fetch_helpers_within_frozen_caps",
        "all_task_fetch_requests_within_frozen_caps",
        "successful_result_fetches_do_not_exceed_all_task_transport_requests",
        "prediction_freeze_chain_valid",
        "no_resume_retry_skip_or_selective_rerun",
        "protected_watchers_preserved",
    }
)
MECHANISM_CHECK_NAMES = frozenset(
    {
        "all_eight_funnel_receipts_validated",
        "private_catalog_absent_count_zero",
        "base_runtime_failure_count_zero",
        "funnel_validation_failure_count_zero",
        "parent_failure_count_zero",
        "minimum_projection_emitted_task_count",
        "minimum_projection_backed_support_task_count",
        "minimum_unconflicted_projection_backed_unknown_proposal_task_count",
        "minimum_changed_task_count",
        "minimum_changed_cell_count",
        "nonunknown_changed_cell_count_zero",
        "scheduler_contract_all_valid",
        "candidate_changes_only_unknown",
        "semantic_safety_contract_all_valid",
        "summary_task_local_joint_replay_exact",
        "minimum_strict_task_local_joint_projection_backed_safe_change",
        "cross_task_aggregate_cooccurrence_not_used",
    }
)
GATE_CHECK_NAMES = HEALTH_CHECK_NAMES | MECHANISM_CHECK_NAMES
SOURCE_POLICY = {
    "prediction_jsonl_opened_or_parsed": False,
    "prediction_jsonl_bytes_hashed_for_freeze_integrity": True,
    "public_visible_tasks_and_trusted_child_projections_opened_for_task_local_replay": True,
    "v24783_private_population_truth_provenance_or_quality_opened_or_hashed": False,
    "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    "network_model_search_fetch_or_evaluator_called_by_audit": False,
}


def _read(path: Path) -> dict[str, Any]:
    target = path.resolve(strict=False)
    if (
        path.is_symlink()
        or not path.is_file()
        or not target.is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError(f"V2.47.84 forward audit expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.47.84 forward audit expected JSON object")
    return value


def _present(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def _zero_observation() -> dict[str, Any]:
    return {
        "status": "parent_failure",
        "base_result_valid": False,
        "funnel_receipt_valid": False,
        "prediction_changed": False,
        "changed_cell_count": 0,
        "founded_changed_cell_count": 0,
        "country_changed_cell_count": 0,
        "nonunknown_changed_cell_count": 0,
        "projection_backed_support_set_count": 0,
        "initial_fetch_request_count": 0,
        "reserve_fetch_request_count": 0,
        "actual_fetch_request_count": 0,
        "initial_usable_page_count": 0,
        "reserve_usable_page_count": 0,
        "actual_usable_page_count": 0,
        "final_entity_slots_with_two_usable_identity_sources": 0,
        "entity_slots_brought_to_two_sources_by_reserve": 0,
        "reserve_target_entity_count": 0,
        "failed_url_retry_count": 0,
        "scheduler_contract": False,
        "candidate_changes_only_unknown": False,
        "semantic_safety_contract": False,
        "funnel_counts": None,
        "task_local_joint_projection_backed_safe_change": False,
    }


def _strict_joint(observation: Mapping[str, Any]) -> bool:
    counts = observation.get("funnel_counts")
    return bool(
        observation.get("status") == "validated"
        and observation.get("funnel_receipt_valid") is True
        and isinstance(counts, Mapping)
        and counts.get("projection_emitted_pair_count", 0) >= 1
        and counts.get("projection_backed_eligible_support_set_count", 0) >= 1
        and counts.get(
            "unconflicted_projection_backed_unknown_proposal_count", 0
        )
        >= 1
        and observation.get("changed_cell_count", 0) >= 1
        and observation.get("nonunknown_changed_cell_count") == 0
        and observation.get("candidate_changes_only_unknown") is True
        and observation.get("semantic_safety_contract") is True
        and observation.get("task_local_joint_projection_backed_safe_change")
        is True
    )


def _collect_task_receipts() -> list[dict[str, Any]]:
    """Replay only fixed visible inputs, public projections, and safe receipts."""

    tasks = contract.task_vector()
    rows: list[dict[str, Any]] = []
    for ordinal, expected_task in enumerate(tasks, 1):
        directory = ROOT / contract.TASK_ROOT / f"task_{ordinal:04d}"
        if directory.is_symlink() or not directory.resolve(
            strict=False
        ).is_relative_to((ROOT / contract.OUTPUT_ROOT).resolve()):
            raise RuntimeError("V2.47.84 task output path escaped")
        visible = _read(directory / contract.VISIBLE_TASK_NAME)
        if visible != expected_task or set(visible) != {"opaque_id", "question"}:
            raise RuntimeError("V2.47.84 visible task replay drifted")

        parent_path = directory / contract.PARENT_RECEIPT_NAME
        model_path = directory / contract.MODEL_RECEIPT_NAME
        transport_path = directory / contract.TRANSPORT_RECEIPT_NAME
        result_path = directory / contract.RESULT_NAME
        parent: dict[str, Any] | None = None
        try:
            parent = validate_parent_receipt(_read(parent_path))
            parent_valid = True
            parent_digest: str | None = contract.sha256(parent_path)
            taxonomy = str(parent["failure_taxonomy"])
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            parent_valid = False
            parent_digest = None
            taxonomy = "parent_receipt_missing_or_invalid"

        model_present = _present(model_path)
        try:
            model = validate_model_receipt(
                _read(model_path), expected_cap=contract.MODEL_SLOT_CAP
            )
            model_valid = True
            model_digest: str | None = contract.sha256(model_path)
            acquisitions: int | None = int(model["acquisitions"])
            slot_timeouts: int | None = int(model["slot_timeouts"])
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            model_valid = False
            model_digest = None
            acquisitions = None
            slot_timeouts = None

        transport_present = _present(transport_path)
        try:
            transport = validate_transport_health(_read(transport_path))
            transport_valid = True
            transport_digest: str | None = contract.sha256(transport_path)
            hosted_attempts: int | None = int(transport["hosted_search_attempts"])
            hard_fetches: int | None = int(transport["hard_fetch_helper_calls"])
            rejected_fetches: int | None = int(transport["fetch_deadline_rejections"])
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            transport_valid = False
            transport_digest = None
            hosted_attempts = None
            hard_fetches = None
            rejected_fetches = None

        parent_flags_match = bool(
            parent_valid
            and parent is not None
            and parent["model_receipt_present"] is model_present
            and parent["model_receipt_valid"] is model_valid
            and parent["transport_receipt_present"] is transport_present
            and parent["transport_receipt_valid"] is transport_valid
        )
        projection_valid = False
        projection_digest: str | None = None
        observation = _zero_observation()
        reason_counts: dict[str, int] | None = None
        if parent_valid and taxonomy == "success":
            try:
                result = validate_projection(_read(result_path))
                observation = contract.content_free_observation(result, expected_task)
                projection_valid = True
                projection_digest = contract.sha256(result_path)
                if observation["funnel_receipt_valid"]:
                    reason_counts = {
                        name: int(result["projection_funnel_receipt"]["reason_counts"][name])
                        for name in contract.funnel.REASONS
                    }
            except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
                projection_valid = False
                projection_digest = None
                observation = _zero_observation()
                taxonomy = "result_projection_missing_or_invalid"

        rows.append(
            {
                "ordinal": ordinal,
                "parent_receipt_sha256": parent_digest,
                "parent_receipt_valid": parent_valid,
                "failure_taxonomy": taxonomy,
                "model_receipt_sha256": model_digest,
                "model_receipt_present": model_present,
                "model_receipt_valid": model_valid,
                "model_acquisitions": acquisitions,
                "model_slot_timeouts": slot_timeouts,
                "transport_receipt_sha256": transport_digest,
                "transport_receipt_present": transport_present,
                "transport_receipt_valid": transport_valid,
                "hosted_search_attempts": hosted_attempts,
                "hard_fetch_helper_calls": hard_fetches,
                "fetch_deadline_rejections": rejected_fetches,
                "parent_effect_receipt_flags_match": parent_flags_match,
                "result_projection_sha256": projection_digest,
                "result_projection_valid": projection_valid,
                "observation": observation,
                "funnel_reason_counts": reason_counts,
                "strict_task_local_joint": _strict_joint(observation),
            }
        )
    return rows


def _replay_summary(rows: list[Mapping[str, Any]]) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    statuses: Counter[str] = Counter(
        str(row["observation"]["status"]) for row in rows
    )
    observations = [row["observation"] for row in rows]
    valid_funnels = [
        row for row in rows if isinstance(row["observation"].get("funnel_counts"), Mapping)
    ]
    reasons: Counter[str] = Counter()
    for row in valid_funnels:
        reasons.update(row["funnel_reason_counts"] or {})
    counts: dict[str, int] = {
        "selected_tasks": contract.SELECTED_COUNT,
        "selected_arm_predictions": contract.SELECTED_COUNT * contract.ARM_COUNT,
        "valid_projection_results": sum(bool(row["result_projection_valid"]) for row in rows),
        "base_valid_task_results": sum(bool(item["base_result_valid"]) for item in observations),
        "validated_funnel_task_count": len(valid_funnels),
        "projected_failure_tasks": statuses["base_runtime_failure"] + statuses["parent_failure"],
        "changed_task_count": sum(bool(item["prediction_changed"]) for item in observations),
        "changed_cell_count": sum(int(item["changed_cell_count"]) for item in observations),
        "founded_changed_cell_count": sum(int(item["founded_changed_cell_count"]) for item in observations),
        "country_changed_cell_count": sum(int(item["country_changed_cell_count"]) for item in observations),
        "nonunknown_changed_cell_count": sum(int(item["nonunknown_changed_cell_count"]) for item in observations),
        "projection_backed_support_set_count": sum(int(item["projection_backed_support_set_count"]) for item in observations),
        "initial_fetch_request_count": sum(int(item["initial_fetch_request_count"]) for item in observations),
        "reserve_fetch_request_count": sum(int(item["reserve_fetch_request_count"]) for item in observations),
        "actual_fetch_request_count": sum(int(item["actual_fetch_request_count"]) for item in observations),
        "initial_usable_page_count": sum(int(item["initial_usable_page_count"]) for item in observations),
        "reserve_usable_page_count": sum(int(item["reserve_usable_page_count"]) for item in observations),
        "actual_usable_page_count": sum(int(item["actual_usable_page_count"]) for item in observations),
        "final_entity_slots_with_two_usable_identity_sources": sum(int(item["final_entity_slots_with_two_usable_identity_sources"]) for item in observations),
        "entity_slots_brought_to_two_sources_by_reserve": sum(int(item["entity_slots_brought_to_two_sources_by_reserve"]) for item in observations),
        "reserve_target_entity_count": sum(int(item["reserve_target_entity_count"]) for item in observations),
        "failed_url_retry_count": sum(int(item["failed_url_retry_count"]) for item in observations),
        "scheduler_contract_failed_task_count": sum(bool(item["base_result_valid"]) and not item["scheduler_contract"] for item in observations),
        "candidate_not_only_unknown_task_count": sum(bool(item["base_result_valid"]) and not item["candidate_changes_only_unknown"] for item in observations),
        "semantic_safety_contract_failed_task_count": sum(bool(item["base_result_valid"]) and not item["semantic_safety_contract"] for item in observations),
        **{f"status_{name}_count": int(statuses[name]) for name in contract.FORWARD_STATUSES},
        "projection_emitted_task_count": sum(int(row["observation"]["funnel_counts"]["projection_emitted_pair_count"] > 0) for row in valid_funnels),
        "projection_backed_support_task_count": sum(int(row["observation"]["funnel_counts"]["projection_backed_eligible_support_set_count"] > 0) for row in valid_funnels),
        "unconflicted_projection_backed_unknown_proposal_task_count": sum(int(row["observation"]["funnel_counts"]["unconflicted_projection_backed_unknown_proposal_count"] > 0) for row in valid_funnels),
        "task_local_joint_projection_backed_safe_change_task_count": sum(int(row["observation"]["task_local_joint_projection_backed_safe_change"]) for row in valid_funnels),
        **{
            name: sum(int(row["observation"]["funnel_counts"][name]) for row in valid_funnels)
            for name in contract.FUNNEL_SUM_FIELDS
        },
    }
    effects = {
        "task_receipt_count": len(rows),
        "valid_parent_receipt_count": sum(bool(row["parent_receipt_valid"]) for row in rows),
        "valid_model_receipt_count": sum(bool(row["model_receipt_valid"]) for row in rows),
        "valid_transport_receipt_count": sum(bool(row["transport_receipt_valid"]) for row in rows),
        "model_acquisition_count": sum(int(row["model_acquisitions"] or 0) for row in rows),
        "model_slot_timeout_count": sum(int(row["model_slot_timeouts"] or 0) for row in rows),
        "hosted_search_attempt_count": sum(int(row["hosted_search_attempts"] or 0) for row in rows),
        "hard_fetch_helper_call_count": sum(int(row["hard_fetch_helper_calls"] or 0) for row in rows),
        "fetch_deadline_rejection_count": sum(int(row["fetch_deadline_rejections"] or 0) for row in rows),
        "all_task_fetch_request_count": sum(int(row["hard_fetch_helper_calls"] or 0) + int(row["fetch_deadline_rejections"] or 0) for row in rows),
        "strict_task_local_joint_count": sum(bool(row["strict_task_local_joint"]) for row in rows),
    }
    return counts, {name: int(reasons[name]) for name in contract.funnel.REASONS}, effects


def _gate_checks(
    rows: list[Mapping[str, Any]],
    summary: Mapping[str, Any],
    freeze: Mapping[str, Any],
    forward: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> tuple[dict[str, bool], dict[str, int], dict[str, int], dict[str, int]]:
    replayed, reasons, effects = _replay_summary(rows)
    summary_counts = {name: int(summary[name]) for name in contract.SUMMARY_COUNT_FIELDS}
    mechanism = protocol["mechanism_gate_before_private_truth"]
    checks = {
        "eight_of_eight_terminal_ordinals": len(rows) == contract.SELECTED_COUNT
        and [row["ordinal"] for row in rows] == list(range(1, contract.SELECTED_COUNT + 1))
        and all(row["parent_receipt_valid"] for row in rows),
        "fixed_denominator_failure_as_zero": summary["selected_tasks"] == contract.SELECTED_COUNT,
        "parent_taxonomy_matches_run_summary": dict(sorted(Counter(str(row["failure_taxonomy"]) for row in rows).items()))
        == summary["parent_failure_taxonomy_counts"],
        "summary_exact_task_local_replay": replayed == summary_counts
        and reasons == summary["funnel_reason_counts"],
        "all_task_ordinals_submitted_once": summary["all_task_ordinals_submitted_once"] is True,
        "within_experiment_wall_ceiling": summary["within_experiment_wall_ceiling"] is True,
        "eight_of_eight_content_free_effect_receipt_pairs_valid": effects["valid_model_receipt_count"] == contract.SELECTED_COUNT
        and effects["valid_transport_receipt_count"] == contract.SELECTED_COUNT,
        "effect_receipts_match_parent_flags": all(row["parent_effect_receipt_flags_match"] for row in rows),
        "model_acquisitions_within_frozen_caps": all(row["model_receipt_valid"] and row["model_acquisitions"] is not None and row["model_acquisitions"] <= contract.LIMITS["model_calls"] for row in rows)
        and effects["model_acquisition_count"] <= contract.SELECTED_COUNT * contract.LIMITS["model_calls"],
        "model_logical_attempts_within_frozen_caps": all(row["model_receipt_valid"] and row["model_acquisitions"] is not None and row["model_slot_timeouts"] is not None and row["model_acquisitions"] + row["model_slot_timeouts"] <= contract.LIMITS["model_calls"] for row in rows),
        "hosted_search_attempts_within_transport_retry_cap": all(row["transport_receipt_valid"] and row["hosted_search_attempts"] is not None and row["hosted_search_attempts"] <= contract.SEARCH["max_retries"] for row in rows)
        and effects["hosted_search_attempt_count"] <= contract.SELECTED_COUNT * contract.SEARCH["max_retries"],
        "physical_fetch_helpers_within_frozen_caps": all(row["transport_receipt_valid"] and row["hard_fetch_helper_calls"] is not None and row["hard_fetch_helper_calls"] <= contract.LIMITS["fetch_targets"] for row in rows)
        and effects["hard_fetch_helper_call_count"] <= contract.SELECTED_COUNT * contract.LIMITS["fetch_targets"],
        "all_task_fetch_requests_within_frozen_caps": all(row["transport_receipt_valid"] and row["hard_fetch_helper_calls"] is not None and row["fetch_deadline_rejections"] is not None and row["hard_fetch_helper_calls"] + row["fetch_deadline_rejections"] <= contract.LIMITS["fetch_targets"] for row in rows)
        and effects["all_task_fetch_request_count"] <= contract.SELECTED_COUNT * contract.LIMITS["fetch_targets"],
        "successful_result_fetches_do_not_exceed_all_task_transport_requests": summary["actual_fetch_request_count"] <= effects["all_task_fetch_request_count"],
        "prediction_freeze_chain_valid": freeze["predictions_sha256"] == contract.sha256(ROOT / contract.PREDICTIONS)
        and freeze["run_summary_sha256"] == contract.sha256(ROOT / contract.RUN_SUMMARY)
        and forward["prediction_freeze_sha256"] == contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        and forward["run_summary_sha256"] == contract.sha256(ROOT / contract.RUN_SUMMARY)
        and forward["execution_start_sha256"] == contract.sha256(ROOT / contract.EXECUTION_START)
        and freeze["all_predictions_terminal_before_private_truth_or_quality_open"] is True
        and freeze["private_truth_or_quality_path_opened_or_hashed"] is False,
        "no_resume_retry_skip_or_selective_rerun": summary["resume_retry_skip_or_selective_rerun"] is False
        and forward["resume_retry_skip_or_selective_rerun"] is False,
        "protected_watchers_preserved": contract.protected_watcher_snapshot()
        == protocol["forward_health_gate"]["protected_watchers"],
        "all_eight_funnel_receipts_validated": summary["status_validated_count"] == mechanism["validated_funnel_receipt_count_required"],
        "private_catalog_absent_count_zero": summary["status_private_catalog_absent_count"] == mechanism["private_catalog_absent_count_required"],
        "base_runtime_failure_count_zero": summary["status_base_runtime_failure_count"] == mechanism["base_runtime_failure_count_required"],
        "funnel_validation_failure_count_zero": summary["status_funnel_validation_failure_count"] == mechanism["funnel_validation_failure_count_required"],
        "parent_failure_count_zero": summary["status_parent_failure_count"] == 0,
        "minimum_projection_emitted_task_count": summary["projection_emitted_task_count"] >= mechanism["minimum_projection_emitted_task_count"],
        "minimum_projection_backed_support_task_count": summary["projection_backed_support_task_count"] >= mechanism["minimum_projection_backed_support_task_count"],
        "minimum_unconflicted_projection_backed_unknown_proposal_task_count": summary["unconflicted_projection_backed_unknown_proposal_task_count"] >= mechanism["minimum_unconflicted_projection_backed_unknown_proposal_task_count"],
        "minimum_changed_task_count": summary["changed_task_count"] >= mechanism["minimum_changed_task_count"],
        "minimum_changed_cell_count": summary["changed_cell_count"] >= mechanism["minimum_changed_cell_count"],
        "nonunknown_changed_cell_count_zero": summary["nonunknown_changed_cell_count"] == mechanism["nonunknown_changed_cell_count_required"],
        "scheduler_contract_all_valid": summary["scheduler_contract_failed_task_count"] == 0,
        "candidate_changes_only_unknown": summary["candidate_not_only_unknown_task_count"] == 0,
        "semantic_safety_contract_all_valid": summary["semantic_safety_contract_failed_task_count"] == 0,
        "summary_task_local_joint_replay_exact": summary["task_local_joint_projection_backed_safe_change_task_count"]
        == sum(bool(row["observation"]["task_local_joint_projection_backed_safe_change"]) for row in rows),
        "minimum_strict_task_local_joint_projection_backed_safe_change": effects["strict_task_local_joint_count"]
        >= mechanism["minimum_task_local_joint_projection_backed_safe_change_task_count"],
        "cross_task_aggregate_cooccurrence_not_used": mechanism["cross_task_aggregate_cooccurrence_may_substitute_for_task_local_joint"] is False,
    }
    if set(checks) != GATE_CHECK_NAMES:
        raise RuntimeError("V2.47.84 forward gate surface drifted")
    return checks, replayed, reasons, effects


def _load_parent_state() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    protocol = _read(ROOT / contract.PROTOCOL)
    summary = contract.validate_run_summary(_read(ROOT / contract.RUN_SUMMARY))
    freeze = contract.validate_prediction_freeze(_read(ROOT / contract.PREDICTION_FREEZE))
    forward = contract.validate_forward_result(_read(ROOT / contract.FORWARD_RESULT))
    if (
        protocol_module.validate_protocol(protocol) != protocol
        or protocol.get("protocol_id") != contract.PROTOCOL_ID
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.47.84 forward audit protocol drifted")
    return protocol, summary, freeze, forward


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    protocol, summary, freeze, forward = _load_parent_state()
    rows = _collect_task_receipts()
    checks, replayed, reasons, effects = _gate_checks(
        rows, summary, freeze, forward, protocol
    )
    health_go = all(checks[name] for name in HEALTH_CHECK_NAMES)
    mechanism_go = health_go and all(checks[name] for name in MECHANISM_CHECK_NAMES)
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v24784_projection_funnel_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
        "task_receipts": rows,
        "replayed_summary_counts": replayed,
        "replayed_funnel_reason_counts": reasons,
        "content_free_effect_metrics": effects,
        "gate_checks": checks,
        "forward_health_go": health_go,
        "mechanism_go": mechanism_go,
        "findings": findings,
        "protected_watchers": contract.protected_watcher_snapshot(),
        "source_policy": dict(SOURCE_POLICY),
        "authorization": {
            "task_cluster_disjoint_paired_dev64_design": mechanism_go,
            "private_truth_or_quality_surface_open": False,
            "additional_forward_retry_resume_or_rerun": False,
            "paired_dev64_execution": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return validate_audit(value)


def _bound_state_matches(value: Mapping[str, Any]) -> bool:
    try:
        protocol, summary, freeze, forward = _load_parent_state()
        rows = _collect_task_receipts()
        checks, replayed, reasons, effects = _gate_checks(
            rows, summary, freeze, forward, protocol
        )
        health = all(checks[name] for name in HEALTH_CHECK_NAMES)
        mechanism = health and all(checks[name] for name in MECHANISM_CHECK_NAMES)
        return bool(
            value.get("protocol_sha256") == contract.sha256(ROOT / contract.PROTOCOL)
            and value.get("forward_result_sha256") == contract.sha256(ROOT / contract.FORWARD_RESULT)
            and value.get("prediction_freeze_sha256") == contract.sha256(ROOT / contract.PREDICTION_FREEZE)
            and value.get("run_summary_sha256") == contract.sha256(ROOT / contract.RUN_SUMMARY)
            and value.get("execution_start_sha256") == contract.sha256(ROOT / contract.EXECUTION_START)
            and value.get("task_receipts") == rows
            and value.get("replayed_summary_counts") == replayed
            and value.get("replayed_funnel_reason_counts") == reasons
            and value.get("content_free_effect_metrics") == effects
            and value.get("gate_checks") == checks
            and value.get("forward_health_go") is health
            and value.get("mechanism_go") is mechanism
            and replayed == {name: int(summary[name]) for name in contract.SUMMARY_COUNT_FIELDS}
            and reasons == summary["funnel_reason_counts"]
            and value.get("protected_watchers") == contract.protected_watcher_snapshot()
        )
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        return False


def validate_audit(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("audit_payload_sha256", None)
    checks = copied.get("gate_checks")
    rows = copied.get("task_receipts")
    health = copied.get("forward_health_go")
    mechanism = copied.get("mechanism_go")
    valid_rows = isinstance(rows, list) and all(isinstance(row, Mapping) for row in rows)
    derived_replayed: dict[str, int] | None = None
    derived_reasons: dict[str, int] | None = None
    derived_effects: dict[str, int] | None = None
    if valid_rows:
        try:
            derived_replayed, derived_reasons, derived_effects = _replay_summary(rows)
        except (KeyError, TypeError, ValueError):
            valid_rows = False
    expected_findings = (
        sorted(name for name, passed in checks.items() if not passed)
        if isinstance(checks, Mapping)
        else None
    )
    if (
        copied.get("role") != "v24784_projection_funnel_forward_audit"
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or not isinstance(checks, Mapping)
        or set(checks) != GATE_CHECK_NAMES
        or not all(isinstance(passed, bool) for passed in checks.values())
        or copied.get("findings") != expected_findings
        or not isinstance(health, bool)
        or not isinstance(mechanism, bool)
        or health != all(checks[name] for name in HEALTH_CHECK_NAMES)
        or mechanism != (health and all(checks[name] for name in MECHANISM_CHECK_NAMES))
        or not valid_rows
        or len(rows) != contract.SELECTED_COUNT
        or [row.get("ordinal") for row in rows] != list(range(1, contract.SELECTED_COUNT + 1))
        or any(set(row) != TASK_RECEIPT_KEYS for row in rows)
        or any(set(row.get("observation", {})) != contract.OBSERVATION_KEYS for row in rows)
        or any(row.get("strict_task_local_joint") is not _strict_joint(row["observation"]) for row in rows)
        or derived_replayed != copied.get("replayed_summary_counts")
        or derived_reasons != copied.get("replayed_funnel_reason_counts")
        or derived_effects != copied.get("content_free_effect_metrics")
        or not isinstance(derived_effects, Mapping)
        or set(derived_effects) != EFFECT_METRIC_NAMES
        or copied.get("source_policy") != SOURCE_POLICY
        or copied.get("authorization")
        != {
            "task_cluster_disjoint_paired_dev64_design": bool(mechanism),
            "private_truth_or_quality_surface_open": False,
            "additional_forward_retry_resume_or_rerun": False,
            "paired_dev64_execution": False,
            "exact220": False,
            "entropy_or_credit_experiment": False,
            "leaderboard_or_sota": False,
        }
        or not _bound_state_matches(copied)
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.47.84 forward audit drifted")
    return copied


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
    audit = build_audit()
    publish_new(ROOT / contract.FORWARD_AUDIT, audit)
    print(
        json.dumps(
            {
                "path": str(contract.FORWARD_AUDIT),
                "forward_health_go": audit["forward_health_go"],
                "mechanism_go": audit["mechanism_go"],
                "strict_task_local_joint_count": audit[
                    "content_free_effect_metrics"
                ]["strict_task_local_joint_count"],
                "findings": audit["findings"],
            },
            sort_keys=True,
        )
    )
