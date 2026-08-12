"""Content-free outer failure observability for quality-gate runners.

The frozen V2.51.91 runner retained only an exception class around three
different boundaries.  That was insufficient to distinguish a runtime
failure from conversion or final row validation.  This pure observer accepts
an explicit boundary and maps only exact, repository-static exception
messages to a finite safe code vocabulary.  Unknown messages collapse by
exception class.  Exception messages, reprs, traceback frames, task content,
and semantic hashes are never emitted or hashed.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25192_content_free_outer_failure_observer_v1"
ROLE = "v25192_content_free_outer_failure_observation"
OUTER_FAILURE_STAGES = ("runtime", "conversion", "row_validation")

# Only exact source-static messages are classified.  Codes disclose the
# failing invariant but never task, provider, page, URL, value, or traceback
# content.  This covers every literal failure surface in the V2.51.35/39/43/
# 47/51/58/65/80/88 runtime chain that can escape to an outer runner.
STATIC_MESSAGE_TO_CODE = {
    # V2.51.35 sparse production.
    "V2.51.35 requires a bounded global model limiter": "v25135_model_limiter_required",
    "V2.51.35 requires two distinct robust search clients": "v25135_search_clients_required",
    "V2.51.35 production-shaped budget drifted": "v25135_budget_drift",
    "V2.51.35 requires pristine search clients": "v25135_search_client_state_drift",
    "V2.51.35 synthesis prompt boundary drifted": "v25135_prompt_boundary_drift",
    "V2.51.35 evidence record grammar drifted": "v25135_evidence_grammar_drift",
    "V2.51.35 evidence URL drifted": "v25135_evidence_url_invariant",
    "V2.51.35 first-wave projection count drifted": "v25135_first_wave_projection_count",
    "V2.51.35 first-wave page count exceeds evidence": "v25135_first_wave_page_count",
    "V2.51.35 production synthesis contract failed": "v25135_production_synthesis_contract",
    "V2.51.35 revision preceded production": "v25135_revision_order",
    "V2.51.35 revision synthesis contract failed": "v25135_revision_synthesis_contract",
    "V2.51.35 too many synthesis entrypoints": "v25135_synthesis_entry_count",
    "V2.51.35 unexpected model stage": "v25135_model_stage",
    "V2.51.35 sparse production receipt drifted": "v25135_receipt_validation",
    "V2.51.35 sparse production result envelope drifted": "v25135_result_envelope_validation",
    "V2.51.35 preservation fallback drifted": "v25135_preservation_fallback_validation",
    "V2.51.35 sparse production parent binding drifted": "v25135_parent_binding_validation",
    # V2.51.39 targeted revision.
    "V2.51.39 canonical table is missing": "v25139_canonical_table_missing",
    "V2.51.39 canonical table shape drifted": "v25139_canonical_table_shape",
    "V2.51.39 row identity or table shape changed": "v25139_row_identity_or_shape",
    "V2.51.39 key-column mutation is forbidden": "v25139_key_column_mutation",
    "V2.51.39 projected table contract drifted": "v25139_projected_table_contract",
    "V2.51.39 first-wave projection count drifted": "v25139_first_wave_projection_count",
    "V2.51.39 first-wave pages exceed evidence": "v25139_first_wave_page_count",
    "V2.51.39 inherited verified gain is absent": "v25139_verified_gain_absent",
    "V2.51.39 no independently verified incremental page": "v25139_incremental_page_absent",
    "V2.51.39 targeted revision preceded production": "v25139_revision_order",
    "V2.51.39 inherited prompt has no delta capacity": "v25139_prompt_delta_capacity",
    "V2.51.39 verified delta does not fit inherited context": "v25139_delta_context_capacity",
    "V2.51.39 prompt context cap expanded": "v25139_context_cap",
    "V2.51.39 unexpected provider stage": "v25139_provider_stage",
    "V2.51.39 too many synthesis provider entries": "v25139_provider_entry_count",
    "V2.51.39 revision table contract failed": "v25139_revision_table_contract",
    "V2.51.39 targeted revision receipt drifted": "v25139_receipt_validation",
    "V2.51.39 targeted revision result envelope drifted": "v25139_result_envelope_validation",
    "V2.51.39 targeted revision parent binding drifted": "v25139_parent_binding_validation",
    # V2.51.43 quote-attested cell edit.
    "V2.51.43 duplicate JSON key": "v25143_duplicate_json_key",
    "V2.51.43 non-standard JSON constant": "v25143_nonstandard_json_constant",
    "V2.51.43 edit response is not a JSON object": "v25143_edit_response_type",
    "V2.51.43 edit response schema drifted": "v25143_edit_response_schema",
    "V2.51.43 projected table drifted": "v25143_projected_table_contract",
    "V2.51.43 cell edit preceded production": "v25143_edit_order",
    "V2.51.43 inherited prompt has no edit capacity": "v25143_prompt_edit_capacity",
    "V2.51.43 no verified page fits inherited context": "v25143_verified_page_context_capacity",
    "V2.51.43 prompt context cap expanded": "v25143_context_cap",
    "V2.51.43 quote-attested receipt drifted": "v25143_receipt_validation",
    "V2.51.43 result envelope drifted": "v25143_result_envelope_validation",
    "V2.51.43 parent binding drifted": "v25143_parent_binding_validation",
    # V2.51.47 deterministic quote candidate.
    "V2.51.47 candidate accounting drifted": "v25147_candidate_accounting",
    "V2.51.47 candidate selection drifted": "v25147_candidate_selection",
    "V2.51.47 selection preceded production": "v25147_selection_order",
    "V2.51.47 inherited prompt has no selector capacity": "v25147_prompt_selector_capacity",
    "V2.51.47 selector context cap expanded": "v25147_context_cap",
    "V2.51.47 deterministic quote-candidate receipt drifted": "v25147_receipt_validation",
    "V2.51.47 result envelope drifted": "v25147_result_envelope_validation",
    "V2.51.47 parent binding drifted": "v25147_parent_binding_validation",
    # V2.51.51 generic record candidate.
    "V2.51.51 grammar accounting drifted": "v25151_grammar_accounting",
    "V2.51.51 candidate accounting drifted": "v25151_candidate_accounting",
    "V2.51.51 generic record candidate receipt drifted": "v25151_receipt_validation",
    "V2.51.51 result envelope drifted": "v25151_result_envelope_validation",
    "V2.51.51 parent binding drifted": "v25151_parent_binding_validation",
    # V2.51.58 vertical key-value candidate.
    "V2.51.58 visible schema is not uniquely keyed": "v25158_visible_schema_keying",
    "V2.51.58 grammar accounting drifted": "v25158_grammar_accounting",
    "V2.51.58 vertical block accounting drifted": "v25158_vertical_block_accounting",
    "V2.51.58 candidate accounting drifted": "v25158_candidate_accounting",
    "V2.51.58 vertical key-value candidate receipt drifted": "v25158_receipt_validation",
    "V2.51.58 result envelope drifted": "v25158_result_envelope_validation",
    "V2.51.58 parent binding drifted": "v25158_parent_binding_validation",
    # V2.51.65 behavior-preserving observer integration.
    "V2.51.65 observed vertical receipt drifted": "v25165_receipt_validation",
    "V2.51.65 observation-parent parity drifted": "v25165_observation_parent_parity",
    "V2.51.65 result envelope drifted": "v25165_result_envelope_validation",
    "V2.51.65 behavior-preserving parent binding drifted": "v25165_parent_binding_validation",
    # V2.51.80 quote-aware production.
    "V2.51.80 repair-public binding drifted": "v25180_repair_public_binding",
    "V2.51.80 internal prediction is not canonical": "v25180_internal_prediction_canonicality",
    "V2.51.80 internal table is missing": "v25180_internal_table_missing",
    "V2.51.80 internal table shape drifted": "v25180_internal_table_shape",
    "V2.51.80 internal prediction fence drifted": "v25180_internal_prediction_fence",
    "V2.51.80 internal prediction is incomplete": "v25180_internal_prediction_completeness",
    "V2.51.80 canonical internal header drifted": "v25180_internal_header",
    "V2.51.80 public loader value drifted": "v25180_public_loader_value",
    "V2.51.80 safe production entity binding drifted": "v25180_safe_production_entity_binding",
    "V2.51.80 production entity binding drifted": "v25180_production_entity_binding",
    "V2.51.80 quote-aware receipt drifted": "v25180_receipt_validation",
    "V2.51.80 receipt-parent binding drifted": "v25180_receipt_parent_binding",
    "V2.51.80 repair lost safe public production": "v25180_safe_production_lost",
    "V2.51.80 safe public production drifted": "v25180_safe_public_production_validation",
    "V2.51.80 result envelope drifted": "v25180_result_envelope_validation",
    "V2.51.80 public export binding drifted": "v25180_public_export_binding",
    "V2.51.80 inactive repair changed prediction": "v25180_inactive_repair_prediction_change",
    "V2.51.80 parent binding drifted": "v25180_parent_binding_validation",
    # V2.51.88 export-tolerant same-response counterfactual.
    "V2.51.88 same-response receipt drifted": "v25188_receipt_validation",
    "V2.51.88 same-response result drifted": "v25188_result_envelope_validation",
    "V2.51.88 parent/counterfactual binding drifted": "v25188_parent_counterfactual_binding",
}

SAFE_EXCEPTION_TYPES = {
    "AssertionError",
    "ConnectionError",
    "KeyError",
    "OSError",
    "RuntimeError",
    "TimeoutError",
    "TypeError",
    "ValueError",
}
FALLBACK_CODE_BY_TYPE = {
    "AssertionError": "unclassified_assertion_error",
    "ConnectionError": "unclassified_connection_error",
    "KeyError": "unclassified_key_error",
    "OSError": "unclassified_os_error",
    "RuntimeError": "unclassified_runtime_error",
    "TimeoutError": "unclassified_timeout_error",
    "TypeError": "unclassified_type_error",
    "ValueError": "unclassified_value_error",
    "Exception": "unclassified_exception",
}
MAPPED_CODES = frozenset(STATIC_MESSAGE_TO_CODE.values())
FALLBACK_CODES = frozenset(FALLBACK_CODE_BY_TYPE.values())
FAILURE_CODES = MAPPED_CODES | FALLBACK_CODES


def _safe_exception_type(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name in SAFE_EXCEPTION_TYPES else "Exception"


def observe_outer_failure(
    exc: BaseException, *, outer_failure_stage: str
) -> dict[str, Any]:
    """Classify an outer failure without retaining its dynamic message."""

    if not isinstance(exc, BaseException):
        raise TypeError("V2.51.92 observer requires an exception")
    if outer_failure_stage not in OUTER_FAILURE_STAGES:
        raise ValueError("V2.51.92 outer failure stage drifted")
    exception_type = _safe_exception_type(exc)
    message = str(exc)
    mapped = message in STATIC_MESSAGE_TO_CODE
    code = (
        STATIC_MESSAGE_TO_CODE[message]
        if mapped
        else FALLBACK_CODE_BY_TYPE[exception_type]
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "outer_failure_stage": outer_failure_stage,
        "failure_code": code,
        "outer_failure_type": exception_type,
        "static_exception_message_mapped": mapped,
        "raw_exception_message_repr_traceback_or_frame_persisted_or_hashed": False,
        "contains_task_question_query_url_title_page_identity_column_key_value_prediction_semantic_hash_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_observation(value)


def validate_observation(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    mapped = copied.get("static_exception_message_mapped")
    false_flags = (
        "raw_exception_message_repr_traceback_or_frame_persisted_or_hashed",
        "contains_task_question_query_url_title_page_identity_column_key_value_prediction_semantic_hash_or_credential",
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
            "outer_failure_stage",
            "failure_code",
            "outer_failure_type",
            "static_exception_message_mapped",
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("outer_failure_stage") not in OUTER_FAILURE_STAGES
        or copied.get("failure_code") not in FAILURE_CODES
        or copied.get("outer_failure_type") not in {*SAFE_EXCEPTION_TYPES, "Exception"}
        or not isinstance(mapped, bool)
        or mapped is not (copied["failure_code"] in MAPPED_CODES)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.92 outer failure observation drifted")
    return copied


__all__ = [
    "FAILURE_CODES",
    "FALLBACK_CODES",
    "MAPPED_CODES",
    "OUTER_FAILURE_STAGES",
    "POLICY_ID",
    "ROLE",
    "STATIC_MESSAGE_TO_CODE",
    "observe_outer_failure",
    "validate_observation",
]
