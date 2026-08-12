"""Pure content-free observer for V2.51.35 and V2.51.80 receipts.

Both frozen validators collapse all receipt invariant failures to one static
exception.  This module mirrors their receipt-only predicates and publishes a
finite ordered code set.  It never returns or hashes receipt values, task
content, predictions, pages, URLs, exception text, or credentials.  It cannot
validate a compatibility, replace a validator, or change runtime behavior.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping
from typing import Any


POLICY_ID = "v25210_receipt_disposition_observer_v1"
ROLE = "v25210_content_free_receipt_disposition_observation"
SPARSE_KIND = "v25135_sparse_production_receipt"
QUOTE_KIND = "v25180_quote_aware_receipt"
RECEIPT_KINDS = (SPARSE_KIND, QUOTE_KIND)

# These identifiers are frozen mirrors, not runtime imports.  The clean-build
# audit binds their defining parent sources by SHA-256 and the tests compare
# every observed disposition directly with the frozen validators.
SPARSE_PARENT_POLICY_ID = "v25135_schema_total_sparse_production_runtime_v1"
SPARSE_PARENT_RECEIPT_ROLE = "v25135_content_free_sparse_production_receipt"
SPARSE_SCHEMA_SOURCES = frozenset(
    {"exact_visible", "provider_plan", "generic_result"}
)
QUOTE_PARENT_POLICY_ID = "v25180_quote_aware_production_runtime_v1"
QUOTE_PARENT_RECEIPT_ROLE = "v25180_content_free_quote_aware_production_receipt"
QUOTE_INNER_PARENT_POLICY_ID = "v25165_observed_vertical_key_value_runtime_v1"
QUOTE_INNER_PARENT_ROLE = "v25165_observed_vertical_key_value_runtime_result"

_NORMALIZER_OBSERVATION_POLICY_ID = (
    "v25170_production_normalizer_disposition_observer_v1"
)
_NORMALIZER_OBSERVATION_ROLE = (
    "v25170_content_free_production_normalizer_disposition_observation"
)
_NORMALIZER_DISPOSITIONS = (
    "exact_table_accepted",
    "normalized_table_accepted",
    "invalid_required_columns_reject",
    "no_pipe_group_reject",
    "no_separator_row_reject",
    "no_bindable_header_reject",
    "separator_width_mismatch_reject",
    "missing_data_rows_reject",
    "malformed_row_or_escaped_pipe_reject",
)
_NORMALIZER_COUNTS = (
    "pipe_group_count",
    "separator_row_count",
    "header_bound_separator_count",
    "width_bound_separator_count",
    "data_bearing_separator_count",
    "malformed_candidate_count",
    "normalizer_candidate_count",
)
_QUOTE_REPAIR_POLICY_ID = "v25177_quote_aware_pipe_normalizer_v1"
_QUOTE_REPAIR_RECEIPT_ROLE = (
    "v25177_content_free_quote_aware_pipe_normalizer_receipt"
)

SPARSE_VIOLATION_CODES = (
    "schema_key_set",
    "envelope_identity",
    "schema_source",
    "count_type_or_range",
    "signed_count_type",
    "dynamic_type",
    "effective_column_range",
    "plan_forward_count",
    "grounded_plan_forward_count",
    "production_entry_count",
    "production_entry_forward_parity",
    "revision_entry_count",
    "revision_forward_count",
    "provider_forward_accounting",
    "provider_forward_cap",
    "model_request_accounting",
    "model_attempt_accounting",
    "query_cap",
    "fetch_cap",
    "verified_gain_contract",
    "production_valid_contract",
    "production_fallback_complement",
    "revision_eligible_contract",
    "revision_forward_contract",
    "revision_valid_contract",
    "identity_replay_contract",
    "no_gain_revision_forward",
    "post_effect_prediction_change",
    "failure_preservation_contract",
    "prediction_change_revision_valid",
    "fixed_budget_caps",
    "no_gain_provider_cap",
    "policy_true_flag",
    "policy_false_flag",
    "payload_seal",
)

QUOTE_VIOLATION_CODES = (
    "schema_key_set",
    "envelope_identity",
    "parent_hash_shape",
    "count_type_or_range",
    "dynamic_type",
    "observer_entry_count",
    "observer_completion_failure_partition",
    "observer_failure_type_contract",
    "nested_observation_contract",
    "repair_attempt_contract",
    "repair_application_contract",
    "repair_failure_contract",
    "export_count_range",
    "export_attempt_contract",
    "export_completion_contract",
    "export_failure_contract",
    "export_fallback_contract",
    "export_failure_type_contract",
    "repair_failure_type_contract",
    "nested_repair_contract",
    "applied_entity_binding_contract",
    "inactive_zero_contract",
    "export_failure_candidate_fallback",
    "production_fallback_complement",
    "published_entity_bounds",
    "csv_entity_bounds",
    "policy_true_flag",
    "policy_false_flag",
    "payload_seal",
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _integer(value: object, *, nonnegative: bool = True) -> bool:
    return bool(
        isinstance(value, int)
        and not isinstance(value, bool)
        and (not nonnegative or value >= 0)
    )


def _ordered(codes: set[str], order: tuple[str, ...]) -> list[str]:
    return [code for code in order if code in codes]


def _observation(kind: str, codes: list[str]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "receipt_kind": kind,
        "primary_violation_code": codes[0] if codes else None,
        "violation_codes": list(codes),
        "violation_count": len(codes),
        "frozen_validator_expected_to_accept": not codes,
        "observer_can_validate_compatibility_or_change_parent_behavior": False,
        "contains_receipt_value_hash_task_question_query_url_title_page_identity_column_key_value_prediction_semantic_hash_exception_message_traceback_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_observation(value)


def observe_sparse_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    """Mirror the frozen V2.51.35 receipt predicates without deciding runtime."""

    if not isinstance(value, Mapping):
        raise TypeError("V2.52.10 sparse observer requires a mapping")
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "effective_column_count",
        "plan_provider_forward_count",
        "grounded_plan_provider_forward_count",
        "production_synthesis_entry_count",
        "production_synthesis_provider_forward_count",
        "revision_synthesis_entry_count",
        "revision_synthesis_provider_forward_count",
        "provider_forward_count",
        "model_provider_request_count",
        "model_provider_attempt_count",
        "physical_query_count",
        "physical_fetch_count",
        "system_total_tokens",
        "physical_model_forward_cap",
        "no_gain_physical_model_forward_cap",
        "physical_query_cap",
        "physical_fetch_cap",
        "per_task_wall_second_cap",
        "per_task_evidence_character_cap",
    )
    signed = (
        "target_field_page_gain",
        "target_field_pair_gain",
        "complete_target_field_page_gain",
    )
    dynamics = (
        "selection_changed",
        "verified_source_identity_field_gain",
        "production_provider_output_valid",
        "production_fallback_used",
        "revision_eligible",
        "revision_provider_output_valid",
        "identity_replay_used",
        "gain_verification_failure_present",
        "revision_failure_present",
        "post_effect_failure_present",
        "production_prediction_preserved",
        "final_prediction_changed_from_production",
    )
    true_flags = (
        "one_production_synthesis_without_verified_gain",
        "second_provider_synthesis_only_after_same_forward_verified_gain",
        "revision_or_posteffect_failure_preserves_production_prediction",
        "same_forward_source_identity_field_binding_required",
        "provider_replay_is_not_counted_as_provider_effect",
    )
    false_flags = (
        "contains_question_column_query_url_title_page_target_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "schema_source",
        *counts,
        *signed,
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
        or copied.get("role") != SPARSE_PARENT_RECEIPT_ROLE
        or copied.get("policy_id") != SPARSE_PARENT_POLICY_ID
    ):
        violations.add("envelope_identity")
    schema_source = copied.get("schema_source")
    if (
        not isinstance(schema_source, str)
        or schema_source not in SPARSE_SCHEMA_SOURCES
    ):
        violations.add("schema_source")
    counts_valid = all(_integer(copied.get(name)) for name in counts)
    signed_valid = all(_integer(copied.get(name), nonnegative=False) for name in signed)
    dynamics_valid = all(isinstance(copied.get(name), bool) for name in dynamics)
    if not counts_valid:
        violations.add("count_type_or_range")
    if not signed_valid:
        violations.add("signed_count_type")
    if not dynamics_valid:
        violations.add("dynamic_type")
    if counts_valid:
        if not 1 <= copied["effective_column_count"] <= 20:
            violations.add("effective_column_range")
        if copied["plan_provider_forward_count"] != 1:
            violations.add("plan_forward_count")
        if copied["grounded_plan_provider_forward_count"] not in {0, 1}:
            violations.add("grounded_plan_forward_count")
        if copied["production_synthesis_entry_count"] not in {0, 1}:
            violations.add("production_entry_count")
        if (
            copied["production_synthesis_provider_forward_count"]
            != copied["production_synthesis_entry_count"]
        ):
            violations.add("production_entry_forward_parity")
        if copied["revision_synthesis_entry_count"] not in {0, 1}:
            violations.add("revision_entry_count")
        if copied["revision_synthesis_provider_forward_count"] not in {0, 1}:
            violations.add("revision_forward_count")
        expected_forwards = (
            copied["plan_provider_forward_count"]
            + copied["grounded_plan_provider_forward_count"]
            + copied["production_synthesis_provider_forward_count"]
            + copied["revision_synthesis_provider_forward_count"]
        )
        if copied["provider_forward_count"] != expected_forwards:
            violations.add("provider_forward_accounting")
        if copied["provider_forward_count"] > 4:
            violations.add("provider_forward_cap")
        if copied["model_provider_request_count"] > copied["provider_forward_count"]:
            violations.add("model_request_accounting")
        if copied["model_provider_attempt_count"] < copied["model_provider_request_count"]:
            violations.add("model_attempt_accounting")
        if copied["physical_query_count"] > 4:
            violations.add("query_cap")
        if copied["physical_fetch_count"] > 14:
            violations.add("fetch_cap")
        if (
            copied["physical_model_forward_cap"] != 4
            or copied["no_gain_physical_model_forward_cap"] != 3
            or copied["physical_query_cap"] != 4
            or copied["physical_fetch_cap"] != 14
            or copied["per_task_wall_second_cap"] != 240
            or copied["per_task_evidence_character_cap"] != 60_000
        ):
            violations.add("fixed_budget_caps")
    if counts_valid and signed_valid and dynamics_valid:
        gain = bool(
            copied["selection_changed"] and copied["target_field_page_gain"] > 0
        )
        if copied["verified_source_identity_field_gain"] is not gain:
            violations.add("verified_gain_contract")
        if (
            copied["production_provider_output_valid"]
            and copied["production_synthesis_provider_forward_count"] != 1
        ):
            violations.add("production_valid_contract")
        if (
            copied["production_fallback_used"]
            is copied["production_provider_output_valid"]
        ):
            violations.add("production_fallback_complement")
        eligible = bool(
            copied["revision_synthesis_entry_count"]
            and copied["verified_source_identity_field_gain"]
            and copied["production_provider_output_valid"]
        )
        if copied["revision_eligible"] is not eligible:
            violations.add("revision_eligible_contract")
        if copied["revision_synthesis_provider_forward_count"] != int(eligible):
            violations.add("revision_forward_contract")
        if copied["revision_provider_output_valid"] and (
            not copied["revision_eligible"] or copied["revision_failure_present"]
        ):
            violations.add("revision_valid_contract")
        replay = bool(
            copied["revision_synthesis_entry_count"]
            and not copied["revision_provider_output_valid"]
        )
        if copied["identity_replay_used"] is not replay:
            violations.add("identity_replay_contract")
        if (
            not copied["verified_source_identity_field_gain"]
            and copied["revision_synthesis_provider_forward_count"] != 0
        ):
            violations.add("no_gain_revision_forward")
        if (
            copied["post_effect_failure_present"]
            and copied["final_prediction_changed_from_production"]
        ):
            violations.add("post_effect_prediction_change")
        if (
            copied["revision_failure_present"]
            or copied["post_effect_failure_present"]
        ) and not copied["production_prediction_preserved"]:
            violations.add("failure_preservation_contract")
        if (
            copied["final_prediction_changed_from_production"]
            and not copied["revision_provider_output_valid"]
        ):
            violations.add("prediction_change_revision_valid")
        if (
            not copied["verified_source_identity_field_gain"]
            and copied["provider_forward_count"] > 3
        ):
            violations.add("no_gain_provider_cap")
    if any(copied.get(name) is not True for name in true_flags):
        violations.add("policy_true_flag")
    if any(copied.get(name) is not False for name in false_flags):
        violations.add("policy_false_flag")
    if seal != payload_sha256(unsigned):
        violations.add("payload_seal")
    return _observation(
        SPARSE_KIND, _ordered(violations, SPARSE_VIOLATION_CODES)
    )


def _normalizer_observation_valid(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    dispositions = copied.get("disposition_counts")
    count_names = ("required_column_count", *_NORMALIZER_COUNTS)
    false_names = (
        "observer_changes_response_fallback_prediction_candidate_routing_or_budget",
        "contains_response_cell_column_question_identity_url_page_key_value_prediction_semantic_hash_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    booleans = (
        "exact_parser_accepted",
        "normalizer_accepted_after_exact_failure",
        "frozen_synthesis_contract_accepted",
        "provider_output_truncated",
        *false_names,
    )
    active = (
        {
            name
            for name, count in dispositions.items()
            if count == 1
        }
        if isinstance(dispositions, Mapping)
        else set()
    )
    accepted = {"exact_table_accepted", "normalized_table_accepted"}
    return bool(
        set(copied)
        == {
            "artifact_version",
            "role",
            "policy_id",
            *count_names,
            "disposition_counts",
            *booleans,
            "receipt_payload_sha256",
        }
        and copied.get("artifact_version") == 1
        and copied.get("role") == _NORMALIZER_OBSERVATION_ROLE
        and copied.get("policy_id") == _NORMALIZER_OBSERVATION_POLICY_ID
        and all(_integer(copied.get(name)) for name in count_names)
        and isinstance(dispositions, Mapping)
        and set(dispositions) == set(_NORMALIZER_DISPOSITIONS)
        and all(
            _integer(count) and count in {0, 1}
            for count in dispositions.values()
        )
        and sum(dispositions.values()) == 1
        and all(isinstance(copied.get(name), bool) for name in booleans)
        and copied["exact_parser_accepted"]
        is (active == {"exact_table_accepted"})
        and copied["normalizer_accepted_after_exact_failure"]
        is (active == {"normalized_table_accepted"})
        and copied["frozen_synthesis_contract_accepted"]
        is bool(active.intersection(accepted))
        and (
            not copied["normalizer_accepted_after_exact_failure"]
            or copied["normalizer_candidate_count"] > 0
        )
        and (
            active != {"no_pipe_group_reject"}
            or copied["pipe_group_count"] == 0
        )
        and (
            active != {"no_separator_row_reject"}
            or copied["separator_row_count"] == 0
        )
        and (
            active != {"no_bindable_header_reject"}
            or copied["header_bound_separator_count"] == 0
        )
        and (
            active != {"separator_width_mismatch_reject"}
            or copied["width_bound_separator_count"] == 0
        )
        and (
            active != {"missing_data_rows_reject"}
            or copied["data_bearing_separator_count"] == 0
        )
        and (
            active != {"malformed_row_or_escaped_pipe_reject"}
            or copied["data_bearing_separator_count"] > 0
        )
        and all(copied.get(name) is False for name in false_names)
        and seal == payload_sha256(unsigned)
    )


def _quote_repair_receipt_valid(value: object) -> bool:
    if not isinstance(value, Mapping):
        return False
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "row_count",
        "escaped_pipe_cell_count",
        "escaped_pipe_occurrence_count",
        "internal_entity_cell_count",
        "csv_quoted_cell_count",
        "adjacent_pipe_whitespace_count",
    )
    true_flags = (
        "repair_applied",
        "single_exact_header_table_only",
        "all_rows_nonempty_and_width_exact",
        "internal_entity_collision_absent",
        "internal_frozen_parser_compatible",
        "internal_entity_roundtrip_exact_before_public_loader",
        "final_public_loader_column_shape_compatible",
        "public_loader_adjacent_pipe_whitespace_canonicalization_measured",
        "header_row_count_row_order_nonpipe_cells_and_decoded_values_preserved",
    )
    false_flags = (
        "question_response_cell_column_prediction_or_semantic_hash_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "network_model_search_fetch_or_evaluator_effect",
        "benchmark_launch_or_external_protocol_authorized",
    )
    return bool(
        set(copied)
        == {
            "artifact_version",
            "role",
            "policy_id",
            *counts,
            *true_flags,
            *false_flags,
            "receipt_payload_sha256",
        }
        and copied.get("artifact_version") == 1
        and copied.get("role") == _QUOTE_REPAIR_RECEIPT_ROLE
        and copied.get("policy_id") == _QUOTE_REPAIR_POLICY_ID
        and all(_integer(copied.get(name)) for name in counts)
        and copied["row_count"] >= 1
        and copied["escaped_pipe_cell_count"] >= 1
        and copied["escaped_pipe_occurrence_count"]
        >= copied["escaped_pipe_cell_count"]
        and copied["internal_entity_cell_count"]
        == copied["escaped_pipe_cell_count"]
        and copied["csv_quoted_cell_count"]
        >= copied["escaped_pipe_cell_count"]
        and all(copied.get(name) is True for name in true_flags)
        and all(copied.get(name) is False for name in false_flags)
        and seal == payload_sha256(unsigned)
    )


def observe_quote_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    """Mirror the frozen V2.51.80 receipt predicates without parent binding."""

    if not isinstance(value, Mapping):
        raise TypeError("V2.52.10 quote observer requires a mapping")
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    observation = copied.get("raw_normalizer_observation")
    repair_receipt = copied.get("quote_aware_repair_receipt")
    counts = (
        "raw_normalizer_observer_entry_count",
        "raw_normalizer_observer_completed_count",
        "quote_aware_repair_attempt_count",
        "quote_aware_repair_applied_count",
        "public_export_attempt_count",
        "public_export_completed_count",
        "production_entity_cell_count",
        "production_entity_occurrence_count",
        "internal_final_entity_cell_count",
        "internal_final_entity_occurrence_count",
        "published_final_entity_cell_count",
        "published_final_entity_occurrence_count",
        "production_csv_quoted_cell_count",
        "final_csv_quoted_cell_count",
        "production_adjacent_pipe_whitespace_count",
        "final_adjacent_pipe_whitespace_count",
    )
    dynamics = (
        "raw_normalizer_observer_failure_present",
        "quote_aware_repair_failure_present",
        "public_export_failure_present",
        "public_export_fallback_to_completed_production",
        "parent_production_provider_output_valid",
        "parent_production_fallback_used",
        "final_entity_coordinates_subset",
        "row_identity_order_shape_invariant",
        "candidate_publication_fallback",
    )
    true_flags = (
        "raw_observation_precedes_repair_and_sparse_parent_normalization",
        "repair_only_after_frozen_raw_contract_rejection",
        "internal_parent_result_cost_effect_failure_and_candidate_receipts_bound",
        "public_export_only_after_internal_parent_terminal_validation",
        "candidate_publication_fails_closed_on_entity_or_shape_drift",
        "public_export_failure_preserves_completed_production",
        "query_fetch_model_context_token_wall_network_and_concurrency_caps_unchanged",
    )
    false_flags = (
        "contains_raw_response_cell_column_question_identity_url_page_key_value_prediction_or_semantic_hash",
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
        "raw_normalizer_observer_failure_type",
        "raw_normalizer_observation",
        "quote_aware_repair_failure_type",
        "quote_aware_repair_receipt",
        "public_export_failure_type",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    violations: set[str] = set()
    if set(copied) != expected:
        violations.add("schema_key_set")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != QUOTE_PARENT_RECEIPT_ROLE
        or copied.get("policy_id") != QUOTE_PARENT_POLICY_ID
        or copied.get("parent_role") != QUOTE_INNER_PARENT_ROLE
        or copied.get("parent_policy_id") != QUOTE_INNER_PARENT_POLICY_ID
    ):
        violations.add("envelope_identity")
    parent_hash = copied.get("parent_result_payload_sha256")
    if not isinstance(parent_hash, str) or len(parent_hash) != 64:
        violations.add("parent_hash_shape")
    counts_valid = all(_integer(copied.get(name)) for name in counts)
    dynamics_valid = all(isinstance(copied.get(name), bool) for name in dynamics)
    if not counts_valid:
        violations.add("count_type_or_range")
    if not dynamics_valid:
        violations.add("dynamic_type")

    entered = bool(
        counts_valid and copied["raw_normalizer_observer_entry_count"] == 1
    )
    completed = bool(
        counts_valid and copied["raw_normalizer_observer_completed_count"] == 1
    )
    attempted = bool(
        counts_valid and copied["quote_aware_repair_attempt_count"] == 1
    )
    applied = bool(
        counts_valid and copied["quote_aware_repair_applied_count"] == 1
    )
    export_attempted = bool(
        counts_valid and copied["public_export_attempt_count"] == 1
    )
    export_completed = bool(
        counts_valid and copied["public_export_completed_count"] == 1
    )
    observer_failed = bool(
        dynamics_valid and copied["raw_normalizer_observer_failure_present"]
    )
    repair_failed = bool(
        dynamics_valid and copied["quote_aware_repair_failure_present"]
    )
    export_failed = bool(
        dynamics_valid and copied["public_export_failure_present"]
    )
    export_fallback = bool(
        dynamics_valid and copied["public_export_fallback_to_completed_production"]
    )
    if counts_valid and copied["raw_normalizer_observer_entry_count"] != 1:
        violations.add("observer_entry_count")
    if counts_valid and dynamics_valid and completed is observer_failed:
        violations.add("observer_completion_failure_partition")
    if dynamics_valid:
        failure_type = copied.get("raw_normalizer_observer_failure_type")
        failure_type_valid = bool(
            isinstance(failure_type, str) and failure_type
        )
        if (observer_failed and not failure_type_valid) or (
            not observer_failed and failure_type is not None
        ):
            violations.add("observer_failure_type_contract")

    nested_observation_valid = False
    if completed:
        if isinstance(observation, Mapping):
            try:
                nested_observation_valid = _normalizer_observation_valid(
                    observation
                )
            except BaseException:
                nested_observation_valid = False
        if not nested_observation_valid:
            violations.add("nested_observation_contract")
    elif observation is not None:
        violations.add("nested_observation_contract")
    if counts_valid and nested_observation_valid:
        should_attempt = bool(
            completed and not observation["frozen_synthesis_contract_accepted"]
        )
        if attempted is not should_attempt:
            violations.add("repair_attempt_contract")
    if counts_valid and applied and not attempted:
        violations.add("repair_application_contract")
    if counts_valid and dynamics_valid:
        if repair_failed and not attempted:
            violations.add("repair_failure_contract")
        if applied and repair_failed:
            violations.add("repair_application_contract")
    if counts_valid:
        if copied["public_export_attempt_count"] not in {0, 1} or copied[
            "public_export_completed_count"
        ] not in {0, 1}:
            violations.add("export_count_range")
        if export_attempted is not applied:
            violations.add("export_attempt_contract")
        if export_completed and not export_attempted:
            violations.add("export_completion_contract")
    if counts_valid and dynamics_valid:
        if export_failed is not bool(export_attempted and not export_completed):
            violations.add("export_failure_contract")
        if export_fallback is not export_failed:
            violations.add("export_fallback_contract")
        export_type = copied.get("public_export_failure_type")
        export_type_valid = bool(isinstance(export_type, str) and export_type)
        if (export_failed and not export_type_valid) or (
            not export_failed and export_type is not None
        ):
            violations.add("export_failure_type_contract")
        repair_type = copied.get("quote_aware_repair_failure_type")
        repair_type_valid = bool(isinstance(repair_type, str) and repair_type)
        if (repair_failed and not repair_type_valid) or (
            not repair_failed and repair_type is not None
        ):
            violations.add("repair_failure_type_contract")

    nested_repair_valid = False
    if applied:
        if isinstance(repair_receipt, Mapping):
            try:
                nested_repair_valid = _quote_repair_receipt_valid(
                    repair_receipt
                )
            except BaseException:
                nested_repair_valid = False
        if not nested_repair_valid:
            violations.add("nested_repair_contract")
    elif repair_receipt is not None:
        violations.add("nested_repair_contract")
    if applied and counts_valid and dynamics_valid and nested_repair_valid:
        if (
            copied["production_entity_cell_count"]
            != repair_receipt["internal_entity_cell_count"]
            or copied["production_entity_occurrence_count"]
            != repair_receipt["escaped_pipe_occurrence_count"]
            or not copied["parent_production_provider_output_valid"]
            or copied["parent_production_fallback_used"]
        ):
            violations.add("applied_entity_binding_contract")
    if not applied and counts_valid and dynamics_valid:
        exempt = {
            "raw_normalizer_observer_entry_count",
            "raw_normalizer_observer_completed_count",
            "quote_aware_repair_attempt_count",
            "quote_aware_repair_applied_count",
            "public_export_attempt_count",
            "public_export_completed_count",
        }
        if (
            repair_receipt is not None
            or any(copied[name] for name in counts if name not in exempt)
            or copied["final_entity_coordinates_subset"]
            or copied["row_identity_order_shape_invariant"]
            or copied["candidate_publication_fallback"]
            or copied["public_export_fallback_to_completed_production"]
        ):
            violations.add("inactive_zero_contract")
    if dynamics_valid:
        if export_failed and not copied["candidate_publication_fallback"]:
            violations.add("export_failure_candidate_fallback")
        if (
            copied["parent_production_fallback_used"]
            is copied["parent_production_provider_output_valid"]
        ):
            violations.add("production_fallback_complement")
    if counts_valid:
        if (
            copied["published_final_entity_cell_count"]
            > copied["production_entity_cell_count"]
            or copied["published_final_entity_occurrence_count"]
            > copied["production_entity_occurrence_count"]
        ):
            violations.add("published_entity_bounds")
        if (
            copied["final_csv_quoted_cell_count"]
            < copied["published_final_entity_cell_count"]
            or copied["production_csv_quoted_cell_count"]
            < copied["production_entity_cell_count"]
        ):
            violations.add("csv_entity_bounds")
    if any(copied.get(name) is not True for name in true_flags):
        violations.add("policy_true_flag")
    if any(copied.get(name) is not False for name in false_flags):
        violations.add("policy_false_flag")
    if seal != payload_sha256(unsigned):
        violations.add("payload_seal")
    return _observation(
        QUOTE_KIND, _ordered(violations, QUOTE_VIOLATION_CODES)
    )


def observe_receipt_invariants(
    value: Mapping[str, Any], *, receipt_kind: str
) -> dict[str, Any]:
    if receipt_kind == SPARSE_KIND:
        return observe_sparse_receipt(value)
    if receipt_kind == QUOTE_KIND:
        return observe_quote_receipt(value)
    raise ValueError("V2.52.10 receipt kind drifted")


def validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    kind = copied.get("receipt_kind")
    codes = copied.get("violation_codes")
    order = (
        SPARSE_VIOLATION_CODES
        if kind == SPARSE_KIND
        else QUOTE_VIOLATION_CODES
        if kind == QUOTE_KIND
        else ()
    )
    false_flags = (
        "observer_can_validate_compatibility_or_change_parent_behavior",
        "contains_receipt_value_hash_task_question_query_url_title_page_identity_column_key_value_prediction_semantic_hash_exception_message_traceback_or_credential",
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
            "receipt_kind",
            "primary_violation_code",
            "violation_codes",
            "violation_count",
            "frozen_validator_expected_to_accept",
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or kind not in RECEIPT_KINDS
        or not isinstance(codes, list)
        or codes != [code for code in order if code in set(codes)]
        or len(set(codes)) != len(codes)
        or any(code not in order for code in codes)
        or copied.get("primary_violation_code") != (codes[0] if codes else None)
        or copied.get("violation_count") != len(codes)
        or copied.get("frozen_validator_expected_to_accept") is not (not codes)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.10 receipt disposition observation drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "QUOTE_KIND",
    "QUOTE_VIOLATION_CODES",
    "RECEIPT_KINDS",
    "ROLE",
    "SPARSE_KIND",
    "SPARSE_VIOLATION_CODES",
    "observe_quote_receipt",
    "observe_receipt_invariants",
    "observe_sparse_receipt",
    "validate_observation",
]
