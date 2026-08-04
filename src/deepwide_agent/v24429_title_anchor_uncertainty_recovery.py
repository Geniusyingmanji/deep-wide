"""Zero-effect uncertainty recovery from unique page-title anchors.

The frozen V2.44.07 parent replays V2.44.05 over already-fetched active pages,
but V2.44.05 deliberately discards page titles.  V2.44.29 preserves the full
parent result and replays V2.44.28 over the exact same private page vector.
It then applies the unchanged V2.43.88 posterior/credit rule and the unchanged
V2.43.90 candidate merge.  No target is reselected and no external effect is
performed.

The component has no file, environment, network, model, search, fetch,
process, benchmark, evaluator, reward, or score access.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from typing import Any

from . import v24390_uncertainty_active_evidence_runtime as runtime
from . import v24407_structured_uncertainty_recovery as parent
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24388_uncertainty_credit import (
    POLICY_ID as ENTROPY_POLICY_ID,
    apply_active_evidence,
    validate_active_evidence_result,
)
from .v24428_unique_title_anchor_projection import (
    POLICY_ID as TITLE_PROJECTION_POLICY_ID,
    build_unique_title_anchor_projection,
    validate_unique_title_anchor_projection,
)


POLICY_ID = "v24429_zero_effect_title_anchor_uncertainty_recovery_v1"
ROLE = "v24429_title_anchor_uncertainty_recovery_result"
RECEIPT_ROLE = "v24429_title_anchor_uncertainty_recovery_receipt"
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "candidate_prediction",
        "title_anchor_projection",
        "title_anchor_active_evidence_result",
        "title_anchor_recovery_receipt",
        "result_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "title_projection_policy_id",
        "entropy_policy_id",
        "selected_target_count",
        "active_page_count",
        "parent_legacy_observation_count",
        "parent_structured_projection_count",
        "parent_novel_structured_observation_count",
        "parent_combined_observation_count",
        "unique_title_anchor_page_count",
        "ambiguous_or_absent_title_anchor_page_count",
        "title_anchor_projection_count",
        "novel_title_anchor_observation_count",
        "combined_title_anchor_observation_count",
        "parent_recovered_safe_change_count",
        "title_recovered_safe_change_count",
        "title_recovered_baseline_confirmed_count",
        "title_recovered_unresolved_count",
        "title_recovered_positive_epistemic_target_count",
        "title_recovered_source_credit_record_count",
        "parent_recovered_epistemic_credit_total_nats",
        "title_recovered_pre_active_entropy_total_nats",
        "title_recovered_combined_entropy_total_nats",
        "title_recovered_positive_information_gain_total_nats",
        "title_recovered_bayesian_surprise_total_nats",
        "title_recovered_epistemic_credit_total_nats",
        "title_recovered_decision_credit_total_nats",
        "parent_candidate_changed_cell_count",
        "title_candidate_changed_cell_count",
        "title_recovery_changed_parent_output",
        "parent_model_requests",
        "parent_total_logical_queries",
        "parent_total_search_batches",
        "parent_total_fetch_calls",
        "additional_model_requests",
        "additional_logical_queries",
        "additional_search_batches",
        "additional_fetch_calls",
        "parent_target_query_source_and_effects_reused_without_reexecution",
        "parent_structured_projection_preserved_exactly",
        "unique_title_anchor_projection_private_replay_valid",
        "frozen_uncertainty_catalog_reused_without_target_reselection",
        "posterior_and_credit_recomputed_from_combined_observations",
        "decision_credit_requires_safe_output_change",
        "task_private_title_page_observation_value_prediction_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


def _finite(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and float(value) >= 0
    )


def _selected_identities(catalog: Mapping[str, Any]) -> set[tuple[str, str]]:
    return {
        runtime._target_identity(item["row_key"], item["column"])
        for item in runtime._selected_targets(catalog)
    }


def _compute(parent_result: Mapping[str, Any]) -> dict[str, Any]:
    structured = parent.validate_result(parent_result)
    legacy = structured["parent_result"]
    baseline = str(legacy["baseline_prediction"])
    private = legacy["private_replay_state"]
    uncertainty_catalog = private["uncertainty_catalog"]
    projection = build_unique_title_anchor_projection(
        baseline,
        private["active_pages"],
        selected_identities=_selected_identities(uncertainty_catalog),
    )
    validate_unique_title_anchor_projection(projection)
    if projection["parent_projection"] != structured["structured_active_projection"]:
        raise ValueError("V2.44.29 parent structured projection drifted")
    active = apply_active_evidence(uncertainty_catalog, projection["observations"])
    validate_active_evidence_result(active)
    candidate, _ = runtime._merge_parent_candidate(legacy["parent_result"], active)
    parent_receipt = structured["structured_recovery_receipt"]
    entropy = active["receipt"]
    parent_changes = runtime._changed_cells(
        baseline, structured["candidate_prediction"]
    )
    title_changes = runtime._changed_cells(baseline, candidate)
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "title_projection_policy_id": TITLE_PROJECTION_POLICY_ID,
        "entropy_policy_id": ENTROPY_POLICY_ID,
        "selected_target_count": int(entropy["selected_target_count"]),
        "active_page_count": len(projection["pages"]),
        "parent_legacy_observation_count": int(
            parent_receipt["legacy_active_observation_count"]
        ),
        "parent_structured_projection_count": int(
            parent_receipt["structured_projection_count"]
        ),
        "parent_novel_structured_observation_count": int(
            parent_receipt["novel_structured_observation_count"]
        ),
        "parent_combined_observation_count": int(
            parent_receipt["combined_active_observation_count"]
        ),
        "unique_title_anchor_page_count": int(
            projection["unique_title_anchor_page_count"]
        ),
        "ambiguous_or_absent_title_anchor_page_count": int(
            projection["ambiguous_or_absent_title_anchor_page_count"]
        ),
        "title_anchor_projection_count": int(
            projection["title_anchor_projection_count"]
        ),
        "novel_title_anchor_observation_count": int(
            projection["novel_title_anchor_observation_count"]
        ),
        "combined_title_anchor_observation_count": int(
            projection["combined_observation_count"]
        ),
        "parent_recovered_safe_change_count": int(
            parent_receipt["recovered_safe_change_count"]
        ),
        "title_recovered_safe_change_count": int(entropy["safe_change_count"]),
        "title_recovered_baseline_confirmed_count": int(
            entropy["baseline_confirmed_count"]
        ),
        "title_recovered_unresolved_count": int(entropy["unresolved_count"]),
        "title_recovered_positive_epistemic_target_count": int(
            entropy["positive_epistemic_target_count"]
        ),
        "title_recovered_source_credit_record_count": int(
            entropy["source_credit_record_count"]
        ),
        "parent_recovered_epistemic_credit_total_nats": float(
            parent_receipt["recovered_epistemic_credit_total_nats"]
        ),
        "title_recovered_pre_active_entropy_total_nats": float(
            entropy["pre_active_entropy_total_nats"]
        ),
        "title_recovered_combined_entropy_total_nats": float(
            entropy["combined_entropy_total_nats"]
        ),
        "title_recovered_positive_information_gain_total_nats": float(
            entropy["positive_information_gain_total_nats"]
        ),
        "title_recovered_bayesian_surprise_total_nats": float(
            entropy["bayesian_surprise_total_nats"]
        ),
        "title_recovered_epistemic_credit_total_nats": float(
            entropy["epistemic_credit_total_nats"]
        ),
        "title_recovered_decision_credit_total_nats": float(
            entropy["decision_credit_total_nats"]
        ),
        "parent_candidate_changed_cell_count": len(parent_changes),
        "title_candidate_changed_cell_count": len(title_changes),
        "title_recovery_changed_parent_output": (
            candidate != structured["candidate_prediction"]
        ),
        "parent_model_requests": int(parent_receipt["parent_model_requests"]),
        "parent_total_logical_queries": int(
            parent_receipt["parent_total_logical_queries"]
        ),
        "parent_total_search_batches": int(
            parent_receipt["parent_total_search_batches"]
        ),
        "parent_total_fetch_calls": int(
            parent_receipt["parent_total_fetch_calls"]
        ),
        "additional_model_requests": 0,
        "additional_logical_queries": 0,
        "additional_search_batches": 0,
        "additional_fetch_calls": 0,
        "parent_target_query_source_and_effects_reused_without_reexecution": True,
        "parent_structured_projection_preserved_exactly": True,
        "unique_title_anchor_projection_private_replay_valid": True,
        "frozen_uncertainty_catalog_reused_without_target_reselection": True,
        "posterior_and_credit_recomputed_from_combined_observations": True,
        "decision_credit_requires_safe_output_change": True,
        "task_private_title_page_observation_value_prediction_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    receipt["receipt_sha256"] = payload_sha256(receipt)
    validate_receipt(receipt)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(structured),
        "candidate_prediction": candidate,
        "title_anchor_projection": projection,
        "title_anchor_active_evidence_result": active,
        "title_anchor_recovery_receipt": receipt,
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def recover_title_anchor_uncertainty(
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    value = _compute(parent_result)
    validate_result(value)
    return value


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    count_fields = (
        "selected_target_count",
        "active_page_count",
        "parent_legacy_observation_count",
        "parent_structured_projection_count",
        "parent_novel_structured_observation_count",
        "parent_combined_observation_count",
        "unique_title_anchor_page_count",
        "ambiguous_or_absent_title_anchor_page_count",
        "title_anchor_projection_count",
        "novel_title_anchor_observation_count",
        "combined_title_anchor_observation_count",
        "parent_recovered_safe_change_count",
        "title_recovered_safe_change_count",
        "title_recovered_baseline_confirmed_count",
        "title_recovered_unresolved_count",
        "title_recovered_positive_epistemic_target_count",
        "title_recovered_source_credit_record_count",
        "parent_candidate_changed_cell_count",
        "title_candidate_changed_cell_count",
        "parent_model_requests",
        "parent_total_logical_queries",
        "parent_total_search_batches",
        "parent_total_fetch_calls",
        "additional_model_requests",
        "additional_logical_queries",
        "additional_search_batches",
        "additional_fetch_calls",
    )
    numeric_fields = (
        "parent_recovered_epistemic_credit_total_nats",
        "title_recovered_pre_active_entropy_total_nats",
        "title_recovered_combined_entropy_total_nats",
        "title_recovered_positive_information_gain_total_nats",
        "title_recovered_bayesian_surprise_total_nats",
        "title_recovered_epistemic_credit_total_nats",
        "title_recovered_decision_credit_total_nats",
    )
    true_fields = (
        "parent_target_query_source_and_effects_reused_without_reexecution",
        "parent_structured_projection_preserved_exactly",
        "unique_title_anchor_projection_private_replay_valid",
        "frozen_uncertainty_catalog_reused_without_target_reselection",
        "posterior_and_credit_recomputed_from_combined_observations",
        "decision_credit_requires_safe_output_change",
    )
    false_fields = (
        "task_private_title_page_observation_value_prediction_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("parent_policy_id") != parent.POLICY_ID
        or value.get("title_projection_policy_id") != TITLE_PROJECTION_POLICY_ID
        or value.get("entropy_policy_id") != ENTROPY_POLICY_ID
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in count_fields
        )
        or any(not _finite(value.get(name)) for name in numeric_fields)
        or not isinstance(value.get("title_recovery_changed_parent_output"), bool)
        or any(value.get(name) is not True for name in true_fields)
        or any(value.get(name) is not False for name in false_fields)
        or any(
            value[name] != 0
            for name in (
                "additional_model_requests",
                "additional_logical_queries",
                "additional_search_batches",
                "additional_fetch_calls",
            )
        )
        or value["unique_title_anchor_page_count"]
        + value["ambiguous_or_absent_title_anchor_page_count"]
        != value["active_page_count"]
        or value["combined_title_anchor_observation_count"]
        < value["parent_combined_observation_count"]
        or value["novel_title_anchor_observation_count"]
        > value["combined_title_anchor_observation_count"]
        or value["title_recovered_safe_change_count"]
        + value["title_recovered_baseline_confirmed_count"]
        + value["title_recovered_unresolved_count"]
        != value["selected_target_count"]
        or value["title_recovered_decision_credit_total_nats"]
        > value["title_recovered_epistemic_credit_total_nats"] + 1e-12
        or (
            value["title_recovered_decision_credit_total_nats"] > 0
            and value["title_recovered_safe_change_count"] == 0
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.29 title-anchor recovery receipt drifted")
    return copy.deepcopy(dict(value))


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(value.get("parent_result"), Mapping)
        or not isinstance(value.get("candidate_prediction"), str)
        or not isinstance(value.get("title_anchor_projection"), Mapping)
        or not isinstance(value.get("title_anchor_active_evidence_result"), Mapping)
        or not isinstance(value.get("title_anchor_recovery_receipt"), Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.29 title-anchor recovery identity drifted")
    parent.validate_result(value["parent_result"])
    validate_unique_title_anchor_projection(value["title_anchor_projection"])
    validate_active_evidence_result(value["title_anchor_active_evidence_result"])
    validate_receipt(value["title_anchor_recovery_receipt"])
    expected = _compute(value["parent_result"])
    if dict(value) != expected:
        raise ValueError("V2.44.29 title-anchor recovery replay drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "POLICY_ID",
    "ROLE",
    "recover_title_anchor_uncertainty",
    "validate_receipt",
    "validate_result",
]
