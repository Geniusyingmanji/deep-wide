"""Grounded-fact bootstrap with quote-coordinate partial-field verification.

This append-only successor keeps the frozen V2.53.46 joint grounded-plan
surface, parent-plan projection, same-forward visible-page projection, and
equal-length production treatment.  It changes one representation seam: the
record-atomic V2.50.65 verifier is replaced by V2.53.60, which keeps page,
unique-verbatim-quote, row-identity, and coordinate-conflict checks fail
closed while omitting only independently invalid fields.

No model, query, search, fetch, context, token, wall, network, or evaluator
budget is added.  Invalid output and unrenderable verified fields return the
parent production prompt byte-for-byte.  The module is pure and label-blind;
entropy/information gain assigns no signed credit.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Mapping, Sequence
from typing import Any

from . import v25346_grounded_fact_bootstrap as parent
from . import v25360_quote_coordinate_partial_field_record as partial
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25361_partial_field_grounded_fact_bootstrap_v1"
ROLE = "v25361_partial_field_grounded_fact_bootstrap"
RECEIPT_ROLE = "v25361_content_free_partial_field_grounded_fact_receipt"

JOINT_SYSTEM_SUFFIX = parent.JOINT_SYSTEM_SUFFIX
PARENT_PLAN_KEYS = parent.PARENT_PLAN_KEYS
JOINT_KEYS = parent.JOINT_KEYS
EVIDENCE_HEADER = parent.EVIDENCE_HEADER
EVIDENCE_SUFFIX = parent.EVIDENCE_SUFFIX

_COUNT_FIELDS = (
    "input_first_wave_page_count",
    "grounded_visible_page_count",
    "grounded_visible_page_characters",
    "parsed_record_count",
    "parsed_field_count",
    "field_accepted_count",
    "field_unknown_rejection_count",
    "field_label_or_value_binding_rejection_count",
    "field_quote_coordinate_rejection_count",
    "field_row_identity_rejection_count",
    "field_page_reference_rejection_count",
    "field_exact_duplicate_rejection_count",
    "field_conflict_rejection_count",
    "record_conflict_count",
    "record_zero_accepted_field_count",
    "verified_record_count",
    "verified_field_count",
    "rendered_record_count",
    "rendered_field_count",
    "compact_prefix_characters",
    "production_prompt_characters",
    "parent_grounded_output_characters",
    "additional_model_call_count",
    "positive_signed_credit_count",
)


def joint_system(parent_system: str) -> str:
    """Preserve the frozen joint prompt byte-for-byte."""

    return parent.joint_system(parent_system)


def parent_grounded_output(model_output: object) -> str:
    """Preserve the frozen four-member parent-plan projection byte-for-byte."""

    return parent.parent_grounded_output(model_output)


def _empty_binding_receipt(
    *,
    page_counts: Mapping[str, int],
    control_characters: int,
    model_call_attempted: bool,
) -> dict[str, Any]:
    return partial._receipt(
        {
            "input_page_count": int(page_counts["input_first_wave_page_count"]),
            "bounded_page_count": int(page_counts["grounded_visible_page_count"]),
            "bounded_page_characters": int(
                page_counts["grounded_visible_page_characters"]
            ),
            "control_evidence_characters": int(control_characters),
            "candidate_evidence_characters": int(control_characters),
            "proposal_input_character_cap": partial.MAXIMUM_PROPOSAL_INPUT_CHARACTERS,
            "proposal_output_token_cap": partial.PROPOSAL_OUTPUT_TOKEN_CAP,
            "record_prefix_character_cap": partial.MAXIMUM_RECORD_PREFIX_CHARACTERS,
            "model_call_attempted": bool(model_call_attempted),
            "model_output_strictly_valid": False,
            "candidate_evidence_changed": False,
        }
    )


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    binding = partial.validate_receipt(value["record_binding_receipt"])
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_bootstrap_policy_id": parent.POLICY_ID,
        "partial_field_verifier_policy_id": partial.POLICY_ID,
        **{name: int(value[name]) for name in _COUNT_FIELDS},
        "model_call_attempted": bool(value["model_call_attempted"]),
        "parent_schema_exact": bool(value["parent_schema_exact"]),
        "joint_envelope_exact": bool(value["joint_envelope_exact"]),
        "records_member_present": bool(value["records_member_present"]),
        "record_binding_attempted": bool(value["record_binding_attempted"]),
        "record_output_strictly_valid": bool(
            binding["model_output_strictly_valid"]
        ),
        "candidate_production_prompt_changed": bool(
            value["candidate_production_prompt_changed"]
        ),
        "record_binding_receipt": copy.deepcopy(binding),
        "one_existing_grounded_plan_call_proposes_plan_and_facts": True,
        "parent_receives_exact_four_member_grounded_plan_schema": True,
        "joint_prompt_and_parent_plan_projection_byte_exact_to_v25346": True,
        "facts_verify_against_exact_grounded_visible_text_and_same_forward_source_url": True,
        "page_quote_row_coordinate_checks_remain_fail_closed": True,
        "invalid_fields_omitted_only_after_independent_same_quote_verification": True,
        "same_coordinate_column_conflicts_reject_entire_coordinate": True,
        "only_quote_verified_row_field_value_records_enter_candidate_prompt": True,
        "candidate_and_parent_production_prompt_character_counts_equal": True,
        "invalid_or_unrenderable_fact_output_returns_parent_prompt_byte_exact": True,
        "page_text_treated_as_untrusted_data": True,
        "additional_query_fetch_model_token_context_wall_or_network_budget": False,
        "model_proposal_rejected_field_or_entropy_drop_assigns_signed_credit": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "contains_question_query_url_title_page_quote_record_identity_field_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def build_bootstrap(
    *,
    question: str,
    columns: Sequence[str],
    first_wave_pages: Sequence[Mapping[str, Any]],
    grounded_model_output: object,
    production_user: str,
    model_call_attempted: bool,
) -> dict[str, Any]:
    """Build one equal-length treatment using independently verified fields."""

    user = str(production_user)
    if not user or "\x00" in user:
        raise ValueError("V2.53.61 production prompt drifted")
    start, end = parent._evidence_bounds(user)
    control = user[start:end]
    if (
        not control
        or len(control) > partial.MAXIMUM_CONTROL_EVIDENCE_CHARACTERS
    ):
        raise ValueError("V2.53.61 production evidence boundary drifted")

    split = parent._joint_output(grounded_model_output)
    pages, page_counts = parent._grounded_visible_pages(first_wave_pages)
    required = tuple(str(value) for value in columns)
    representation: dict[str, Any] | None = None
    attempted = bool(
        model_call_attempted
        and split["records_member_present"]
        and len(required) >= 2
        and pages
    )
    if attempted:
        try:
            prepared = partial.prepare_record_proposal(question, required, pages)
            representation = partial.build_representation(
                prepared,
                split["record_output"],
                control_evidence=control,
                model_call_attempted=True,
            )
        except (TypeError, ValueError, RuntimeError, KeyError, IndexError):
            representation = None

    if representation is None:
        binding = _empty_binding_receipt(
            page_counts=page_counts,
            control_characters=len(control),
            model_call_attempted=attempted,
        )
        candidate = control
    else:
        binding = partial.validate_receipt(representation["content_free_receipt"])
        candidate = str(representation["candidate_evidence"])

    if len(candidate) != len(control):
        raise RuntimeError("V2.53.61 evidence character conservation drifted")
    candidate_user = user[:start] + candidate + user[end:]
    changed = candidate_user != user
    if changed is not binding["candidate_evidence_changed"]:
        raise RuntimeError("V2.53.61 candidate prompt binding drifted")

    receipt = _receipt(
        {
            **page_counts,
            "parsed_record_count": binding["parsed_record_count"],
            "parsed_field_count": binding["parsed_field_count"],
            "field_accepted_count": binding["field_accepted_count"],
            "field_unknown_rejection_count": binding[
                "field_unknown_rejection_count"
            ],
            "field_label_or_value_binding_rejection_count": binding[
                "field_label_or_value_binding_rejection_count"
            ],
            "field_quote_coordinate_rejection_count": binding[
                "field_quote_coordinate_rejection_count"
            ],
            "field_row_identity_rejection_count": binding[
                "field_row_identity_rejection_count"
            ],
            "field_page_reference_rejection_count": binding[
                "field_page_reference_rejection_count"
            ],
            "field_exact_duplicate_rejection_count": binding[
                "field_exact_duplicate_rejection_count"
            ],
            "field_conflict_rejection_count": binding[
                "field_conflict_rejection_count"
            ],
            "record_conflict_count": binding["record_conflict_count"],
            "record_zero_accepted_field_count": binding[
                "record_zero_accepted_field_count"
            ],
            "verified_record_count": binding["verified_partial_record_count"],
            "verified_field_count": binding["verified_field_count"],
            "rendered_record_count": binding["rendered_record_count"],
            "rendered_field_count": binding["rendered_field_count"],
            "compact_prefix_characters": binding["compact_prefix_characters"],
            "production_prompt_characters": len(user),
            "parent_grounded_output_characters": len(split["parent_output"]),
            "additional_model_call_count": 0,
            "positive_signed_credit_count": 0,
            "model_call_attempted": model_call_attempted,
            "parent_schema_exact": split["parent_schema_exact"],
            "joint_envelope_exact": split["joint_envelope_exact"],
            "records_member_present": split["records_member_present"],
            "record_binding_attempted": attempted,
            "candidate_production_prompt_changed": changed,
            "record_binding_receipt": binding,
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "parent_grounded_output": str(split["parent_output"]),
        "parent_grounded_output_sha256": hashlib.sha256(
            str(split["parent_output"]).encode("utf-8")
        ).hexdigest(),
        "candidate_production_user": candidate_user,
        "candidate_production_user_sha256": hashlib.sha256(
            candidate_user.encode("utf-8")
        ).hexdigest(),
        "content_free_receipt": receipt,
        "additional_model_call_count": 0,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_bootstrap(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    binding = copied.get("record_binding_receipt")
    dynamic = (
        "model_call_attempted",
        "parent_schema_exact",
        "joint_envelope_exact",
        "records_member_present",
        "record_binding_attempted",
        "record_output_strictly_valid",
        "candidate_production_prompt_changed",
    )
    true_flags = (
        "one_existing_grounded_plan_call_proposes_plan_and_facts",
        "parent_receives_exact_four_member_grounded_plan_schema",
        "joint_prompt_and_parent_plan_projection_byte_exact_to_v25346",
        "facts_verify_against_exact_grounded_visible_text_and_same_forward_source_url",
        "page_quote_row_coordinate_checks_remain_fail_closed",
        "invalid_fields_omitted_only_after_independent_same_quote_verification",
        "same_coordinate_column_conflicts_reject_entire_coordinate",
        "only_quote_verified_row_field_value_records_enter_candidate_prompt",
        "candidate_and_parent_production_prompt_character_counts_equal",
        "invalid_or_unrenderable_fact_output_returns_parent_prompt_byte_exact",
        "page_text_treated_as_untrusted_data",
    )
    false_flags = (
        "additional_query_fetch_model_token_context_wall_or_network_budget",
        "model_proposal_rejected_field_or_entropy_drop_assigns_signed_credit",
        "entropy_or_information_gain_assigns_signed_credit",
        "contains_question_query_url_title_page_quote_record_identity_field_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "parent_bootstrap_policy_id",
        "partial_field_verifier_policy_id",
        *_COUNT_FIELDS,
        *dynamic,
        "record_binding_receipt",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_bootstrap_policy_id") != parent.POLICY_ID
        or copied.get("partial_field_verifier_policy_id") != partial.POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _COUNT_FIELDS
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamic)
        or copied["grounded_visible_page_count"]
        > min(copied["input_first_wave_page_count"], partial.MAXIMUM_PAGE_COUNT)
        or copied["grounded_visible_page_characters"]
        > partial.MAXIMUM_PROPOSAL_INPUT_CHARACTERS
        or copied["additional_model_call_count"] != 0
        or copied["positive_signed_credit_count"] != 0
        or not isinstance(binding, Mapping)
        or partial.validate_receipt(binding) != dict(binding)
        or any(
            copied[name] != binding[name]
            for name in (
                "parsed_record_count",
                "parsed_field_count",
                "field_accepted_count",
                "field_unknown_rejection_count",
                "field_label_or_value_binding_rejection_count",
                "field_quote_coordinate_rejection_count",
                "field_row_identity_rejection_count",
                "field_page_reference_rejection_count",
                "field_exact_duplicate_rejection_count",
                "field_conflict_rejection_count",
                "record_conflict_count",
                "record_zero_accepted_field_count",
                "verified_field_count",
                "rendered_record_count",
                "rendered_field_count",
                "compact_prefix_characters",
            )
        )
        or copied["verified_record_count"]
        != binding["verified_partial_record_count"]
        or copied["record_output_strictly_valid"]
        is not binding["model_output_strictly_valid"]
        or copied["candidate_production_prompt_changed"]
        is not binding["candidate_evidence_changed"]
        or copied["joint_envelope_exact"]
        and not (copied["parent_schema_exact"] and copied["records_member_present"])
        or copied["record_binding_attempted"]
        and not (
            copied["model_call_attempted"]
            and copied["records_member_present"]
            and copied["grounded_visible_page_count"] > 0
        )
        or binding["model_call_attempted"]
        is not copied["record_binding_attempted"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.61 partial-field grounded fact receipt drifted")
    return copied


def validate_bootstrap(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    parent_output = copied.get("parent_grounded_output")
    candidate_user = copied.get("candidate_production_user")
    receipt = copied.get("content_free_receipt")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "parent_grounded_output",
            "parent_grounded_output_sha256",
            "candidate_production_user",
            "candidate_production_user_sha256",
            "content_free_receipt",
            "additional_model_call_count",
            "entropy_or_information_gain_assigns_signed_credit",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
            "benchmark_launch_or_evaluator_authorized",
            "artifact_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(parent_output, str)
        or not isinstance(candidate_user, str)
        or copied.get("parent_grounded_output_sha256")
        != hashlib.sha256(parent_output.encode("utf-8")).hexdigest()
        or copied.get("candidate_production_user_sha256")
        != hashlib.sha256(candidate_user.encode("utf-8")).hexdigest()
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["production_prompt_characters"] != len(candidate_user)
        or receipt["parent_grounded_output_characters"] != len(parent_output)
        or copied.get("additional_model_call_count") != 0
        or any(
            copied.get(name) is not False
            for name in (
                "entropy_or_information_gain_assigns_signed_credit",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.61 partial-field grounded fact bootstrap drifted")
    return copied


__all__ = [
    "JOINT_SYSTEM_SUFFIX",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "build_bootstrap",
    "joint_system",
    "parent_grounded_output",
    "validate_bootstrap",
    "validate_receipt",
]
