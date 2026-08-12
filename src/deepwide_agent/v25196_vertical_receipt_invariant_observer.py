"""Pure content-free disposition observer for V2.51.58 receipt invariants.

The frozen validator raises one aggregate message for every invariant.  This
observer mirrors those predicates but emits only a finite set of violated
invariant codes.  It never emits or hashes receipt values, task content,
predictions, pages, URLs, fields, or exception text, and it cannot validate or
repair a receipt.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from . import v25158_vertical_key_value_candidate_runtime as parent
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25196_vertical_receipt_invariant_observer_v1"
ROLE = "v25196_content_free_vertical_receipt_invariant_observation"
VIOLATION_CODES = (
    "schema_key_set",
    "envelope_identity",
    "parent_hash_shape",
    "count_type_or_range",
    "entry_forward_relation",
    "candidate_page_relation",
    "vertical_structure_relation",
    "grammar_accounting",
    "candidate_partition_accounting",
    "candidate_cardinality_order",
    "dynamic_type",
    "parent_revision_entry_parity",
    "fixed_evidence_or_context_flag",
    "inactive_count_zero",
    "inactive_dynamic_zero",
    "selector_prompt_contract",
    "projection_contract",
    "prediction_change_contract",
    "failure_parent_contract",
    "failure_preservation_contract",
    "policy_true_flag",
    "policy_false_flag",
    "payload_seal",
)


def _integer(value: object, *, nonnegative: bool = True) -> bool:
    return bool(
        isinstance(value, int)
        and not isinstance(value, bool)
        and (not nonnegative or value >= 0)
    )


def observe_receipt_invariants(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("V2.51.96 observer requires a mapping")
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "candidate_revision_entry_count",
        "underlying_provider_forward_count",
        "verified_incremental_page_count",
        "candidate_source_page_count",
        "candidate_quote_character_count",
        "original_candidate_prompt_character_count",
        "candidate_prompt_character_count",
        *parent._GRAMMAR_COUNTS,
        *parent._VERTICAL_STRUCTURE_COUNTS,
        "raw_candidate_observation_count",
        "verifier_admissible_candidate_count",
        "conflicting_candidate_count",
        "duplicate_candidate_count",
        "truncated_candidate_count",
        "available_candidate_count",
        "supplied_candidate_count",
        "selected_candidate_count",
        "applied_edit_count",
        "rejected_selected_edit_count",
    )
    dynamics = (
        "selector_prompt_built",
        "production_table_conditioned",
        "only_verified_incremental_evidence_supplied",
        "context_cap_preserved",
        "selection_response_strict_json",
        "candidate_projection_valid",
        "projection_failure_present",
        "provider_failure_present",
        "parent_post_effect_failure_present",
        "final_prediction_changed_from_production",
        "production_prediction_preserved_on_failure",
        "parent_revision_eligible",
        "parent_revision_failure_present",
    )
    true_flags = (
        "vertical_blocks_require_one_unique_production_identity_and_unique_visible_keys",
        "vertical_quotes_are_same_page_unique_bounded_identity_to_field_spans",
        "duplicate_keys_multiple_identity_blocks_unknowns_and_cross_page_joins_fail_closed",
        "every_candidate_is_preverified_and_selected_edits_are_reverified",
        "model_can_only_select_candidate_ids_or_abstain",
        "conflicting_coordinates_are_omitted_before_selection",
        "row_identity_order_shape_key_and_unselected_cells_preserved",
        "query_fetch_model_context_token_wall_and_network_caps_unchanged",
    )
    false_flags = (
        "contains_question_column_query_url_title_page_quote_row_field_value_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "parent_role",
        "parent_policy_id",
        "parent_result_payload_sha256",
        *counts,
        *dynamics,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    violations: set[str] = set()
    if set(copied) != expected:
        violations.add("schema_key_set")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != parent.RECEIPT_ROLE
        or copied.get("policy_id") != parent.POLICY_ID
        or copied.get("parent_role") != parent.sparse_parent.ROLE
        or copied.get("parent_policy_id") != parent.sparse_parent.POLICY_ID
    ):
        violations.add("envelope_identity")
    parent_hash = copied.get("parent_result_payload_sha256")
    if not isinstance(parent_hash, str) or len(parent_hash) != 64:
        violations.add("parent_hash_shape")
    if any(not _integer(copied.get(name)) for name in counts):
        violations.add("count_type_or_range")
    if all(_integer(copied.get(name)) for name in counts):
        entered = copied["candidate_revision_entry_count"] == 1
        if (
            copied["candidate_revision_entry_count"] not in {0, 1}
            or copied["underlying_provider_forward_count"] not in {0, 1}
            or copied["underlying_provider_forward_count"]
            > copied["candidate_revision_entry_count"]
        ):
            violations.add("entry_forward_relation")
        if (
            copied["candidate_source_page_count"]
            > copied["verified_incremental_page_count"]
        ):
            violations.add("candidate_page_relation")
        if (
            copied["vertical_identity_bound_block_count"]
            > copied["vertical_pipe_block_count"]
            or copied["vertical_ambiguous_page_count"]
            > copied["verified_incremental_page_count"]
        ):
            violations.add("vertical_structure_relation")
        if copied["raw_candidate_observation_count"] != sum(
            copied[name] for name in parent._GRAMMAR_COUNTS
        ):
            violations.add("grammar_accounting")
        if copied["verifier_admissible_candidate_count"] != (
            copied["conflicting_candidate_count"]
            + copied["duplicate_candidate_count"]
            + copied["truncated_candidate_count"]
            + copied["available_candidate_count"]
        ):
            violations.add("candidate_partition_accounting")
        if (
            copied["available_candidate_count"] > parent.MAXIMUM_CANDIDATES
            or copied["supplied_candidate_count"]
            > copied["available_candidate_count"]
            or copied["selected_candidate_count"]
            > copied["supplied_candidate_count"]
            or copied["applied_edit_count"]
            + copied["rejected_selected_edit_count"]
            != copied["selected_candidate_count"]
        ):
            violations.add("candidate_cardinality_order")
        if not entered and any(
            copied[name] for name in counts if name != "candidate_revision_entry_count"
        ):
            violations.add("inactive_count_zero")
    else:
        entered = False
    if any(not isinstance(copied.get(name), bool) for name in dynamics):
        violations.add("dynamic_type")
    if all(isinstance(copied.get(name), bool) for name in dynamics):
        if copied["parent_revision_eligible"] is not entered:
            violations.add("parent_revision_entry_parity")
        if (
            copied["only_verified_incremental_evidence_supplied"] is not True
            or copied["context_cap_preserved"] is not True
        ):
            violations.add("fixed_evidence_or_context_flag")
        if not entered and any(
            copied[name]
            for name in (
                "selector_prompt_built",
                "production_table_conditioned",
                "selection_response_strict_json",
                "candidate_projection_valid",
                "projection_failure_present",
                "provider_failure_present",
                "parent_post_effect_failure_present",
                "final_prediction_changed_from_production",
                "parent_revision_failure_present",
            )
        ):
            violations.add("inactive_dynamic_zero")
        if copied["selector_prompt_built"] and (
            not copied["production_table_conditioned"]
            or not _integer(copied.get("candidate_prompt_character_count"))
            or not _integer(copied.get("original_candidate_prompt_character_count"))
            or copied["candidate_prompt_character_count"]
            > copied["original_candidate_prompt_character_count"]
        ):
            violations.add("selector_prompt_contract")
        if copied["candidate_projection_valid"] and (
            not copied["selection_response_strict_json"]
            or copied.get("underlying_provider_forward_count") != 1
        ):
            violations.add("projection_contract")
        applied = copied.get("applied_edit_count")
        if _integer(applied) and copied["final_prediction_changed_from_production"] is not bool(
            applied > 0 and not copied["parent_post_effect_failure_present"]
        ):
            violations.add("prediction_change_contract")
        any_provider_failure = bool(
            copied["projection_failure_present"]
            or copied["provider_failure_present"]
        )
        if any_provider_failure and not copied["parent_revision_failure_present"]:
            violations.add("failure_parent_contract")
        any_failure = bool(
            any_provider_failure or copied["parent_post_effect_failure_present"]
        )
        if any_failure and not copied["production_prediction_preserved_on_failure"]:
            violations.add("failure_preservation_contract")
    if any(copied.get(name) is not True for name in true_flags):
        violations.add("policy_true_flag")
    if any(copied.get(name) is not False for name in false_flags):
        violations.add("policy_false_flag")
    if seal != payload_sha256(unsigned):
        violations.add("payload_seal")

    ordered = [code for code in VIOLATION_CODES if code in violations]
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "violation_codes": ordered,
        "violation_count": len(ordered),
        "frozen_validator_expected_to_accept": not ordered,
        "observer_can_validate_repair_or_change_parent_behavior": False,
        "contains_receipt_value_task_question_query_url_title_page_identity_column_key_value_prediction_semantic_hash_exception_message_traceback_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_observation(output)


def validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    codes = copied.get("violation_codes")
    false_flags = (
        "observer_can_validate_repair_or_change_parent_behavior",
        "contains_receipt_value_task_question_query_url_title_page_identity_column_key_value_prediction_semantic_hash_exception_message_traceback_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "violation_codes",
            "violation_count",
            "frozen_validator_expected_to_accept",
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(codes, list)
        or codes != [code for code in VIOLATION_CODES if code in set(codes)]
        or len(set(codes)) != len(codes)
        or any(code not in VIOLATION_CODES for code in codes)
        or copied.get("violation_count") != len(codes)
        or copied.get("frozen_validator_expected_to_accept") is not (not codes)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.96 vertical receipt observation drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "ROLE",
    "VIOLATION_CODES",
    "observe_receipt_invariants",
    "validate_observation",
]
