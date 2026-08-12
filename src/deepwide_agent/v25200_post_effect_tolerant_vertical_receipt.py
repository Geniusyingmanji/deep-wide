"""Exact compatibility for one safe V2.51.58 post-effect fallback state.

V2.51.35 can catch an exception after effects but before the V2.51.58
candidate provider is entered.  It then publishes a validated terminal parent
result whose prediction equals the completed production prediction and whose
``post_effect_failure_present`` flag is true.  The frozen V2.51.58 receipt
validator incorrectly required every dynamic flag, including that independent
parent flag, to be false whenever candidate entry was zero.

This append-only validator preserves the frozen validator for every existing
valid state and every invalid state except exactly:

* candidate entry and all candidate counts are zero;
* all candidate/provider/revision dynamics are false;
* the independent parent post-effect flag alone is true;
* production preservation is true and final prediction change is false; and
* changing only the independent parent flag to false yields a receipt accepted
  by the exact frozen validator.

The original receipt bytes are returned unchanged.  No prediction, routing,
effect, content, or credit signal is changed.
"""

from __future__ import annotations

import copy
import contextvars
import threading
from collections.abc import Mapping
from typing import Any

from . import v25158_vertical_key_value_candidate_runtime as parent
from . import v25196_vertical_receipt_invariant_observer as coarse_observer
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25200_post_effect_tolerant_vertical_receipt_v1"
ROLE = "v25200_content_free_post_effect_compatibility_observation"
SAFE_STATE_CODE = "inactive_parent_post_effect_failure_only"
_FROZEN_VALIDATE = parent.validate_receipt
_APPLIED: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "v25200_post_effect_compatibility_applied", default=False
)
_INSTALL_LOCK = threading.Lock()
_INSTALLED = False


def begin_task() -> contextvars.Token[bool]:
    return _APPLIED.set(False)


def end_task(token: contextvars.Token[bool]) -> None:
    _APPLIED.reset(token)


def compatibility_applied() -> bool:
    return bool(_APPLIED.get())


def _candidate_counts() -> tuple[str, ...]:
    return (
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


def _candidate_dynamics() -> tuple[str, ...]:
    return (
        "selector_prompt_built",
        "production_table_conditioned",
        "selection_response_strict_json",
        "candidate_projection_valid",
        "projection_failure_present",
        "provider_failure_present",
        "final_prediction_changed_from_production",
        "parent_revision_eligible",
        "parent_revision_failure_present",
    )


def observe_compatibility_state(value: Mapping[str, Any]) -> dict[str, Any]:
    """Return a content-free decision; never validate or mutate ``value``."""

    if not isinstance(value, Mapping):
        raise TypeError("V2.52.00 compatibility observer requires a mapping")
    copied = copy.deepcopy(dict(value))
    coarse = coarse_observer.observe_receipt_invariants(copied)
    exact_safe = bool(
        coarse["violation_codes"] == ["inactive_dynamic_zero"]
        and copied.get("candidate_revision_entry_count") == 0
        and copied.get("parent_post_effect_failure_present") is True
        and copied.get("production_prediction_preserved_on_failure") is True
        and copied.get("only_verified_incremental_evidence_supplied") is True
        and copied.get("context_cap_preserved") is True
        and all(copied.get(name) == 0 for name in _candidate_counts())
        and all(copied.get(name) is False for name in _candidate_dynamics())
    )
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "safe_state_code": SAFE_STATE_CODE if exact_safe else None,
        "exact_safe_post_effect_state": exact_safe,
        "frozen_violation_codes": copy.deepcopy(coarse["violation_codes"]),
        "compatibility_can_change_receipt_prediction_routing_effect_budget_or_credit": False,
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
    codes = copied.get("frozen_violation_codes")
    safe = copied.get("exact_safe_post_effect_state")
    false_flags = (
        "compatibility_can_change_receipt_prediction_routing_effect_budget_or_credit",
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
            "safe_state_code",
            "exact_safe_post_effect_state",
            "frozen_violation_codes",
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(safe, bool)
        or not isinstance(codes, list)
        or codes
        != [
            code
            for code in coarse_observer.VIOLATION_CODES
            if code in set(codes)
        ]
        or any(code not in coarse_observer.VIOLATION_CODES for code in codes)
        or copied.get("safe_state_code")
        != (SAFE_STATE_CODE if safe else None)
        or safe and codes != ["inactive_dynamic_zero"]
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.00 compatibility observation drifted")
    return copied


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    """Call frozen validation first; accept only the exact safe exception."""

    try:
        return _FROZEN_VALIDATE(value)
    except ValueError as exc:
        if str(exc) != "V2.51.58 vertical key-value candidate receipt drifted":
            raise
    observation = observe_compatibility_state(value)
    if not observation["exact_safe_post_effect_state"]:
        return _FROZEN_VALIDATE(value)
    surrogate = copy.deepcopy(dict(value))
    surrogate["parent_post_effect_failure_present"] = False
    surrogate.pop("receipt_payload_sha256", None)
    surrogate["receipt_payload_sha256"] = payload_sha256(surrogate)
    _FROZEN_VALIDATE(surrogate)
    _APPLIED.set(True)
    return copy.deepcopy(dict(value))


def install_compatibility() -> None:
    global _INSTALLED
    with _INSTALL_LOCK:
        if not _INSTALLED:
            if parent.validate_receipt is not _FROZEN_VALIDATE:
                raise RuntimeError("V2.52.00 frozen validator identity drifted")
            parent.validate_receipt = validate_receipt
            _INSTALLED = True
        elif parent.validate_receipt is not validate_receipt:
            raise RuntimeError("V2.52.00 installed validator identity drifted")


__all__ = [
    "POLICY_ID",
    "ROLE",
    "SAFE_STATE_CODE",
    "begin_task",
    "compatibility_applied",
    "end_task",
    "install_compatibility",
    "observe_compatibility_state",
    "validate_observation",
    "validate_receipt",
]
