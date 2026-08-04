"""Zero-effect uncertainty recovery from narrative title-anchored evidence.

The frozen V2.44.29 parent already replays strict key/value title records over
the exact active-page vector.  This append-only successor preserves that full
result, replays V2.44.36 over the same pages and selected targets, then applies
the unchanged V2.43.88 posterior/credit rule and V2.43.90 candidate merge.
No target is reselected and no external effect is performed.

The component has no file, environment, network, model, search, fetch,
process, benchmark, evaluator, reward, or score access.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from typing import Any

from . import v24390_uncertainty_active_evidence_runtime as runtime
from . import v24429_title_anchor_uncertainty_recovery as parent
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24388_uncertainty_credit import (
    POLICY_ID as ENTROPY_POLICY_ID,
    apply_active_evidence,
    validate_active_evidence_result,
)
from .v24436_narrative_title_anchor_projection import (
    POLICY_ID as NARRATIVE_PROJECTION_POLICY_ID,
    REASONS,
    build_narrative_title_anchor_projection,
    validate_narrative_title_anchor_projection,
)


POLICY_ID = "v24437_zero_effect_narrative_title_uncertainty_recovery_v1"
ROLE = "v24437_narrative_title_uncertainty_recovery_result"
RECEIPT_ROLE = "v24437_narrative_title_uncertainty_recovery_receipt"
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "candidate_prediction",
        "narrative_title_projection",
        "narrative_active_evidence_result",
        "narrative_recovery_receipt",
        "result_sha256",
    }
)
COUNT_FIELDS = (
    "selected_target_count",
    "active_page_count",
    "parent_title_anchor_projection_count",
    "parent_novel_title_anchor_observation_count",
    "parent_combined_title_anchor_observation_count",
    "narrative_page_target_pair_count",
    "narrative_projection_count",
    "novel_narrative_observation_count",
    "combined_narrative_observation_count",
    "parent_title_recovered_safe_change_count",
    "narrative_recovered_safe_change_count",
    "narrative_recovered_baseline_confirmed_count",
    "narrative_recovered_unresolved_count",
    "narrative_recovered_positive_epistemic_target_count",
    "narrative_recovered_source_credit_record_count",
    "parent_candidate_changed_cell_count",
    "narrative_candidate_changed_cell_count",
    "parent_model_requests",
    "parent_total_logical_queries",
    "parent_total_search_batches",
    "parent_total_fetch_calls",
    "additional_model_requests",
    "additional_logical_queries",
    "additional_search_batches",
    "additional_fetch_calls",
)
NUMERIC_FIELDS = (
    "parent_title_recovered_epistemic_credit_total_nats",
    "narrative_recovered_pre_active_entropy_total_nats",
    "narrative_recovered_combined_entropy_total_nats",
    "narrative_recovered_positive_information_gain_total_nats",
    "narrative_recovered_bayesian_surprise_total_nats",
    "narrative_recovered_epistemic_credit_total_nats",
    "narrative_recovered_decision_credit_total_nats",
)
TRUE_FIELDS = (
    "parent_target_query_source_and_effects_reused_without_reexecution",
    "parent_title_projection_preserved_exactly",
    "narrative_projection_private_replay_valid",
    "narrative_reason_partition_exact",
    "frozen_uncertainty_catalog_reused_without_target_reselection",
    "posterior_and_credit_recomputed_from_combined_observations",
    "decision_credit_requires_safe_output_change",
)
FALSE_FIELDS = (
    "task_private_title_page_observation_value_prediction_or_source_emitted",
    "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
    "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
    "benchmark_launch_or_evaluator_authorized",
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "narrative_projection_policy_id",
        "entropy_policy_id",
        *COUNT_FIELDS,
        *NUMERIC_FIELDS,
        "narrative_reason_counts",
        "narrative_recovery_changed_parent_output",
        *TRUE_FIELDS,
        *FALSE_FIELDS,
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
    anchored = parent.validate_result(parent_result)
    structured = anchored["parent_result"]
    legacy = structured["parent_result"]
    baseline = str(legacy["baseline_prediction"])
    private = legacy["private_replay_state"]
    uncertainty_catalog = private["uncertainty_catalog"]
    projection = build_narrative_title_anchor_projection(
        baseline,
        private["active_pages"],
        selected_identities=_selected_identities(uncertainty_catalog),
    )
    validate_narrative_title_anchor_projection(projection)
    if projection["parent_projection"] != anchored["title_anchor_projection"]:
        raise ValueError("V2.44.37 parent title projection drifted")
    active = apply_active_evidence(uncertainty_catalog, projection["observations"])
    validate_active_evidence_result(active)
    candidate, _ = runtime._merge_parent_candidate(legacy["parent_result"], active)
    parent_receipt = anchored["title_anchor_recovery_receipt"]
    entropy = active["receipt"]
    parent_changes = runtime._changed_cells(
        baseline, anchored["candidate_prediction"]
    )
    narrative_changes = runtime._changed_cells(baseline, candidate)
    reason_counts = {
        name: int(projection["reason_counts"][name]) for name in REASONS
    }
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "narrative_projection_policy_id": NARRATIVE_PROJECTION_POLICY_ID,
        "entropy_policy_id": ENTROPY_POLICY_ID,
        "selected_target_count": int(entropy["selected_target_count"]),
        "active_page_count": int(parent_receipt["active_page_count"]),
        "parent_title_anchor_projection_count": int(
            parent_receipt["title_anchor_projection_count"]
        ),
        "parent_novel_title_anchor_observation_count": int(
            parent_receipt["novel_title_anchor_observation_count"]
        ),
        "parent_combined_title_anchor_observation_count": int(
            parent_receipt["combined_title_anchor_observation_count"]
        ),
        "narrative_page_target_pair_count": int(
            projection["page_target_pair_count"]
        ),
        "narrative_projection_count": int(projection["narrative_projection_count"]),
        "novel_narrative_observation_count": int(
            projection["novel_narrative_observation_count"]
        ),
        "combined_narrative_observation_count": int(
            projection["combined_observation_count"]
        ),
        "narrative_reason_counts": reason_counts,
        "parent_title_recovered_safe_change_count": int(
            parent_receipt["title_recovered_safe_change_count"]
        ),
        "narrative_recovered_safe_change_count": int(entropy["safe_change_count"]),
        "narrative_recovered_baseline_confirmed_count": int(
            entropy["baseline_confirmed_count"]
        ),
        "narrative_recovered_unresolved_count": int(entropy["unresolved_count"]),
        "narrative_recovered_positive_epistemic_target_count": int(
            entropy["positive_epistemic_target_count"]
        ),
        "narrative_recovered_source_credit_record_count": int(
            entropy["source_credit_record_count"]
        ),
        "parent_title_recovered_epistemic_credit_total_nats": float(
            parent_receipt["title_recovered_epistemic_credit_total_nats"]
        ),
        "narrative_recovered_pre_active_entropy_total_nats": float(
            entropy["pre_active_entropy_total_nats"]
        ),
        "narrative_recovered_combined_entropy_total_nats": float(
            entropy["combined_entropy_total_nats"]
        ),
        "narrative_recovered_positive_information_gain_total_nats": float(
            entropy["positive_information_gain_total_nats"]
        ),
        "narrative_recovered_bayesian_surprise_total_nats": float(
            entropy["bayesian_surprise_total_nats"]
        ),
        "narrative_recovered_epistemic_credit_total_nats": float(
            entropy["epistemic_credit_total_nats"]
        ),
        "narrative_recovered_decision_credit_total_nats": float(
            entropy["decision_credit_total_nats"]
        ),
        "parent_candidate_changed_cell_count": len(parent_changes),
        "narrative_candidate_changed_cell_count": len(narrative_changes),
        "narrative_recovery_changed_parent_output": (
            candidate != anchored["candidate_prediction"]
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
        "parent_title_projection_preserved_exactly": True,
        "narrative_projection_private_replay_valid": True,
        "narrative_reason_partition_exact": True,
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
        "parent_result": copy.deepcopy(anchored),
        "candidate_prediction": candidate,
        "narrative_title_projection": projection,
        "narrative_active_evidence_result": active,
        "narrative_recovery_receipt": receipt,
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def recover_narrative_title_uncertainty(
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    value = _compute(parent_result)
    validate_result(value)
    return value


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_sha256", None)
    reasons = value.get("narrative_reason_counts")
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RECEIPT_ROLE
        or value.get("policy_id") != POLICY_ID
        or value.get("parent_policy_id") != parent.POLICY_ID
        or value.get("narrative_projection_policy_id")
        != NARRATIVE_PROJECTION_POLICY_ID
        or value.get("entropy_policy_id") != ENTROPY_POLICY_ID
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in COUNT_FIELDS
        )
        or any(not _finite(value.get(name)) for name in NUMERIC_FIELDS)
        or not isinstance(reasons, Mapping)
        or tuple(reasons) != REASONS
        or any(
            isinstance(reasons.get(name), bool)
            or not isinstance(reasons.get(name), int)
            or reasons[name] < 0
            for name in REASONS
        )
        or not isinstance(value.get("narrative_recovery_changed_parent_output"), bool)
        or any(value.get(name) is not True for name in TRUE_FIELDS)
        or any(value.get(name) is not False for name in FALSE_FIELDS)
        or any(
            value[name] != 0
            for name in (
                "additional_model_requests",
                "additional_logical_queries",
                "additional_search_batches",
                "additional_fetch_calls",
            )
        )
        or sum(int(reasons[name]) for name in REASONS)
        != value["narrative_page_target_pair_count"]
        or value["combined_narrative_observation_count"]
        < value["parent_combined_title_anchor_observation_count"]
        or value["novel_narrative_observation_count"]
        > value["combined_narrative_observation_count"]
        or value["narrative_recovered_safe_change_count"]
        + value["narrative_recovered_baseline_confirmed_count"]
        + value["narrative_recovered_unresolved_count"]
        != value["selected_target_count"]
        or value["narrative_recovered_decision_credit_total_nats"]
        > value["narrative_recovered_epistemic_credit_total_nats"] + 1e-12
        or (
            value["narrative_recovered_decision_credit_total_nats"] > 0
            and value["narrative_recovered_safe_change_count"] == 0
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.37 narrative recovery receipt drifted")
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
        or not isinstance(value.get("narrative_title_projection"), Mapping)
        or not isinstance(value.get("narrative_active_evidence_result"), Mapping)
        or not isinstance(value.get("narrative_recovery_receipt"), Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.37 narrative recovery identity drifted")
    parent.validate_result(value["parent_result"])
    validate_narrative_title_anchor_projection(value["narrative_title_projection"])
    validate_active_evidence_result(value["narrative_active_evidence_result"])
    validate_receipt(value["narrative_recovery_receipt"])
    expected = _compute(value["parent_result"])
    if dict(value) != expected:
        raise ValueError("V2.44.37 narrative recovery replay drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "POLICY_ID",
    "recover_narrative_title_uncertainty",
    "validate_receipt",
    "validate_result",
]
