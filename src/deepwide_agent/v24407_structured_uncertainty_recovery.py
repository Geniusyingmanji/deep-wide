"""Zero-effect structured-observation recovery for V2.43.90 results.

The frozen V2.43.90 forward pass already chooses one label-blind uncertainty
target, searches one active query, fetches at most two source-disjoint pages,
and seals every model/search/fetch effect.  V2.44.07 does not repeat or alter
any of those effects.  It deterministically reprojects the already-private
active pages with V2.44.05, reapplies the frozen V2.43.88 posterior and credit
rule, and merges only a safely resolved target into the parent candidate.

This separation makes the next external test diagnostic: any gain is due to
page-to-observation conversion, not extra search, tokens, retries, or target
selection.  The component has no file, environment, network, model, search,
fetch, process, benchmark, evaluator, reward, or score access.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping
from typing import Any

from . import v24390_uncertainty_active_evidence_runtime as parent
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24388_uncertainty_credit import (
    POLICY_ID as ENTROPY_POLICY_ID,
    apply_active_evidence,
    validate_active_evidence_result,
)
from .v24405_structured_label_projection import (
    POLICY_ID as PROJECTION_POLICY_ID,
    build_structured_label_projection,
    validate_structured_label_projection,
)


POLICY_ID = "v24407_zero_effect_structured_uncertainty_recovery_v1"
ROLE = "v24407_structured_uncertainty_recovery_result"
RECEIPT_ROLE = "v24407_structured_uncertainty_recovery_receipt"
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "candidate_prediction",
        "structured_active_projection",
        "structured_active_evidence_result",
        "structured_recovery_receipt",
        "result_sha256",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "projection_policy_id",
        "entropy_policy_id",
        "selected_target_count",
        "active_page_count",
        "legacy_active_observation_count",
        "structured_projection_count",
        "novel_structured_observation_count",
        "combined_active_observation_count",
        "legacy_safe_change_count",
        "recovered_safe_change_count",
        "recovered_baseline_confirmed_count",
        "recovered_unresolved_count",
        "recovered_positive_epistemic_target_count",
        "recovered_source_credit_record_count",
        "legacy_epistemic_credit_total_nats",
        "recovered_pre_active_entropy_total_nats",
        "recovered_combined_entropy_total_nats",
        "recovered_positive_information_gain_total_nats",
        "recovered_bayesian_surprise_total_nats",
        "recovered_epistemic_credit_total_nats",
        "recovered_decision_credit_total_nats",
        "legacy_candidate_changed_cell_count",
        "recovered_candidate_changed_cell_count",
        "structured_recovery_changed_output",
        "parent_model_requests",
        "parent_total_logical_queries",
        "parent_total_search_batches",
        "parent_total_fetch_calls",
        "additional_model_requests",
        "additional_logical_queries",
        "additional_search_batches",
        "additional_fetch_calls",
        "parent_target_query_source_and_effects_reused_without_reexecution",
        "structured_projection_private_replay_valid",
        "frozen_uncertainty_catalog_reused_without_target_reselection",
        "posterior_and_credit_recomputed_from_combined_observations",
        "decision_credit_requires_safe_output_change",
        "task_private_page_observation_value_prediction_or_source_emitted",
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
        parent._target_identity(item["row_key"], item["column"])
        for item in parent._selected_targets(catalog)
    }


def _compute(validated_parent: Mapping[str, Any]) -> dict[str, Any]:
    legacy = parent.validate_result(validated_parent)
    baseline = str(legacy["baseline_prediction"])
    private = legacy["private_replay_state"]
    catalog = private["uncertainty_catalog"]
    projection = build_structured_label_projection(
        baseline,
        private["active_pages"],
        selected_identities=_selected_identities(catalog),
    )
    validate_structured_label_projection(projection)
    active = apply_active_evidence(catalog, projection["observations"])
    validate_active_evidence_result(active)
    candidate, merge = parent._merge_parent_candidate(
        legacy["parent_result"], active
    )
    legacy_receipt = legacy["uncertainty_active_receipt"]
    entropy = active["receipt"]
    legacy_changes = parent._changed_cells(
        baseline, legacy["candidate_prediction"]
    )
    recovered_changes = parent._changed_cells(baseline, candidate)
    receipt = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "projection_policy_id": PROJECTION_POLICY_ID,
        "entropy_policy_id": ENTROPY_POLICY_ID,
        "selected_target_count": int(entropy["selected_target_count"]),
        "active_page_count": len(projection["pages"]),
        "legacy_active_observation_count": int(
            projection["legacy_observation_count"]
        ),
        "structured_projection_count": int(
            projection["structured_projection_count"]
        ),
        "novel_structured_observation_count": int(
            projection["novel_structured_observation_count"]
        ),
        "combined_active_observation_count": int(
            projection["combined_observation_count"]
        ),
        "legacy_safe_change_count": int(legacy_receipt["safe_change_count"]),
        "recovered_safe_change_count": int(entropy["safe_change_count"]),
        "recovered_baseline_confirmed_count": int(
            entropy["baseline_confirmed_count"]
        ),
        "recovered_unresolved_count": int(entropy["unresolved_count"]),
        "recovered_positive_epistemic_target_count": int(
            entropy["positive_epistemic_target_count"]
        ),
        "recovered_source_credit_record_count": int(
            entropy["source_credit_record_count"]
        ),
        "legacy_epistemic_credit_total_nats": float(
            legacy_receipt["epistemic_credit_total_nats"]
        ),
        "recovered_pre_active_entropy_total_nats": float(
            entropy["pre_active_entropy_total_nats"]
        ),
        "recovered_combined_entropy_total_nats": float(
            entropy["combined_entropy_total_nats"]
        ),
        "recovered_positive_information_gain_total_nats": float(
            entropy["positive_information_gain_total_nats"]
        ),
        "recovered_bayesian_surprise_total_nats": float(
            entropy["bayesian_surprise_total_nats"]
        ),
        "recovered_epistemic_credit_total_nats": float(
            entropy["epistemic_credit_total_nats"]
        ),
        "recovered_decision_credit_total_nats": float(
            entropy["decision_credit_total_nats"]
        ),
        "legacy_candidate_changed_cell_count": len(legacy_changes),
        "recovered_candidate_changed_cell_count": len(recovered_changes),
        "structured_recovery_changed_output": candidate
        != legacy["candidate_prediction"],
        "parent_model_requests": int(legacy_receipt["parent_model_requests"]),
        "parent_total_logical_queries": int(
            legacy_receipt["total_logical_query_count"]
        ),
        "parent_total_search_batches": int(
            legacy_receipt["total_search_batch_count"]
        ),
        "parent_total_fetch_calls": int(legacy_receipt["total_fetch_calls"]),
        "additional_model_requests": 0,
        "additional_logical_queries": 0,
        "additional_search_batches": 0,
        "additional_fetch_calls": 0,
        "parent_target_query_source_and_effects_reused_without_reexecution": True,
        "structured_projection_private_replay_valid": True,
        "frozen_uncertainty_catalog_reused_without_target_reselection": True,
        "posterior_and_credit_recomputed_from_combined_observations": True,
        "decision_credit_requires_safe_output_change": True,
        "task_private_page_observation_value_prediction_or_source_emitted": False,
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
        "parent_result": copy.deepcopy(legacy),
        "candidate_prediction": candidate,
        "structured_active_projection": projection,
        "structured_active_evidence_result": active,
        "structured_recovery_receipt": receipt,
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def recover_structured_uncertainty(
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
        "legacy_active_observation_count",
        "structured_projection_count",
        "novel_structured_observation_count",
        "combined_active_observation_count",
        "legacy_safe_change_count",
        "recovered_safe_change_count",
        "recovered_baseline_confirmed_count",
        "recovered_unresolved_count",
        "recovered_positive_epistemic_target_count",
        "recovered_source_credit_record_count",
        "legacy_candidate_changed_cell_count",
        "recovered_candidate_changed_cell_count",
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
        "legacy_epistemic_credit_total_nats",
        "recovered_pre_active_entropy_total_nats",
        "recovered_combined_entropy_total_nats",
        "recovered_positive_information_gain_total_nats",
        "recovered_bayesian_surprise_total_nats",
        "recovered_epistemic_credit_total_nats",
        "recovered_decision_credit_total_nats",
    )
    true_fields = (
        "parent_target_query_source_and_effects_reused_without_reexecution",
        "structured_projection_private_replay_valid",
        "frozen_uncertainty_catalog_reused_without_target_reselection",
        "posterior_and_credit_recomputed_from_combined_observations",
        "decision_credit_requires_safe_output_change",
    )
    false_fields = (
        "task_private_page_observation_value_prediction_or_source_emitted",
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
        or value.get("projection_policy_id") != PROJECTION_POLICY_ID
        or value.get("entropy_policy_id") != ENTROPY_POLICY_ID
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in count_fields
        )
        or any(not _finite(value.get(name)) for name in numeric_fields)
        or not isinstance(value.get("structured_recovery_changed_output"), bool)
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
        or value["combined_active_observation_count"]
        < value["legacy_active_observation_count"]
        or value["novel_structured_observation_count"]
        > value["combined_active_observation_count"]
        or value["recovered_safe_change_count"]
        + value["recovered_baseline_confirmed_count"]
        + value["recovered_unresolved_count"]
        != value["selected_target_count"]
        or value["recovered_decision_credit_total_nats"]
        > value["recovered_epistemic_credit_total_nats"] + 1e-12
        or (
            value["recovered_decision_credit_total_nats"] > 0
            and value["recovered_safe_change_count"] == 0
        )
        or (
            value["structured_recovery_changed_output"]
            and value["recovered_candidate_changed_cell_count"] == 0
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.07 structured recovery receipt drifted")
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
        or not isinstance(value.get("structured_active_projection"), Mapping)
        or not isinstance(value.get("structured_active_evidence_result"), Mapping)
        or not isinstance(value.get("structured_recovery_receipt"), Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.07 structured recovery identity drifted")
    parent.validate_result(value["parent_result"])
    validate_structured_label_projection(value["structured_active_projection"])
    validate_active_evidence_result(value["structured_active_evidence_result"])
    validate_receipt(value["structured_recovery_receipt"])
    expected = _compute(value["parent_result"])
    if dict(value) != expected:
        raise ValueError("V2.44.07 structured recovery replay drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "POLICY_ID",
    "ROLE",
    "recover_structured_uncertainty",
    "validate_receipt",
    "validate_result",
]
