"""Totality-safe deterministic visible-constraint runtime.

V2.55.45 correctly refuses to transform a parent prediction unless that
prediction is an exact canonical markdown table.  Its former failure boundary,
however, turned that *projection nonadmission* into an outer task failure and
discarded an otherwise terminal V2.54.01 parent prediction.  This successor
keeps the strict projector unchanged and makes nonadmission an explicit,
byte-exact parent handoff.

Only three representation failures are contained.  Receipt, binding, contract,
or projector validation failures still raise.  The wrapper performs no model,
search, fetch, file, environment, process, evaluator, or benchmark-label
access.  Entropy/information gain remains shadow-only with zero signed credit.
"""

from __future__ import annotations

import copy
import hashlib
from collections.abc import Callable, Mapping
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25401_grounded_record_membership_runtime as parent
from . import v25541_visible_output_constraint_contract as contracts
from . import v25545_deterministic_visible_constraint_runtime as constrained
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25569_constraint_totality_safe_handoff_runtime_v1"
ROLE = "v25569_constraint_totality_safe_handoff_runtime_result"
RECEIPT_ROLE = "v25569_content_free_constraint_totality_receipt"
STAGE_RECEIPT_ROLE = "v25569_content_free_constraint_totality_stage_receipt"
CANONICAL_PROJECTION = "canonical_projection"
BYTE_EXACT_PARENT_HANDOFF = "byte_exact_parent_handoff"
ARMS = constrained.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
ProductionOnlyStageError = parent.ProductionOnlyStageError

_NONADMISSION_REASONS = {
    "V2.55.45 visible table header is absent": "visible_table_header_absent",
    "V2.55.44 expected exact canonical parent table": (
        "parent_prediction_not_exact_canonical_table"
    ),
    "V2.55.44 canonical matrix drifted": "parent_canonical_matrix_invalid",
}


def _projection_columns(prediction: object) -> tuple[tuple[str, ...] | None, str | None]:
    """Return strict projection columns or a narrowly allowlisted nonadmission."""

    try:
        return constrained._visible_columns(prediction), None
    except ValueError as exc:
        reason = _NONADMISSION_REASONS.get(str(exc))
        if reason is None:
            raise
        return None, reason


def _receipt_value(
    checked_parent: Mapping[str, Any],
    checked_constrained: Mapping[str, Any] | None,
    *,
    mode: str,
    nonadmission_reason: str | None,
) -> dict[str, Any]:
    """Construct a receipt from objects already validated by the caller."""

    nested = (
        checked_constrained["deterministic_visible_constraint_receipt"]
        if checked_constrained is not None
        else None
    )
    admitted = mode == CANONICAL_PROJECTION
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "mode": mode,
        "projection_admitted": admitted,
        "byte_exact_parent_handoff": not admitted,
        "nonadmission_reason": nonadmission_reason,
        "candidate_prediction_changed": bool(
            checked_constrained["candidate_prediction_changed"]
            if checked_constrained is not None
            else False
        ),
        "active_family_count": int(
            nested["active_family_count"] if nested is not None else 0
        ),
        "date_cell_changed_count": int(
            nested["date_cell_changed_count"] if nested is not None else 0
        ),
        "scale_cell_changed_count": int(
            nested["scale_cell_changed_count"] if nested is not None else 0
        ),
        "sort_applied_count": int(
            nested["sort_applied_count"] if nested is not None else 0
        ),
        "positive_signed_credit_count": 0,
        "parent_result_payload_sha256": checked_parent["result_payload_sha256"],
        "constrained_result_payload_sha256": (
            checked_constrained["result_payload_sha256"]
            if checked_constrained is not None
            else None
        ),
        "one_v25401_parent_forward_only": True,
        "projection_nonadmission_preserves_parent_prediction_byte_exact": True,
        "internal_validation_failure_is_not_contained": True,
        "query_fetch_model_token_context_and_wall_caps_unchanged": True,
        "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed_by_wrapper": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return value


def _receipt(
    parent_result: Mapping[str, Any],
    constrained_result: Mapping[str, Any] | None,
    *,
    mode: str,
    nonadmission_reason: str | None,
) -> dict[str, Any]:
    checked_parent = parent.validate_result(parent_result)
    checked_constrained = (
        constrained.validate_result(constrained_result)
        if isinstance(constrained_result, Mapping)
        else None
    )
    value = _receipt_value(
        checked_parent,
        checked_constrained,
        mode=mode,
        nonadmission_reason=nonadmission_reason,
    )
    return validate_receipt(
        value,
        parent_result=checked_parent,
        constrained_result=checked_constrained,
    )


def validate_receipt(
    value: Mapping[str, Any],
    *,
    parent_result: Mapping[str, Any] | None = None,
    constrained_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    integer_fields = (
        "active_family_count",
        "date_cell_changed_count",
        "scale_cell_changed_count",
        "sort_applied_count",
        "positive_signed_credit_count",
    )
    true_flags = (
        "one_v25401_parent_forward_only",
        "projection_nonadmission_preserves_parent_prediction_byte_exact",
        "internal_validation_failure_is_not_contained",
        "query_fetch_model_token_context_and_wall_caps_unchanged",
    )
    false_flags = (
        "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed_by_wrapper",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "mode",
        "projection_admitted",
        "byte_exact_parent_handoff",
        "nonadmission_reason",
        "candidate_prediction_changed",
        *integer_fields,
        "parent_result_payload_sha256",
        "constrained_result_payload_sha256",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    admitted = copied.get("mode") == CANONICAL_PROJECTION
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("mode")
        not in {CANONICAL_PROJECTION, BYTE_EXACT_PARENT_HANDOFF}
        or copied.get("projection_admitted") is not admitted
        or copied.get("byte_exact_parent_handoff") is not (not admitted)
        or not isinstance(copied.get("candidate_prediction_changed"), bool)
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or copied.get("positive_signed_credit_count") != 0
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.69 constraint totality receipt drifted")
    if admitted:
        if (
            copied.get("nonadmission_reason") is not None
            or not isinstance(
                copied.get("constrained_result_payload_sha256"), str
            )
            or len(copied["constrained_result_payload_sha256"]) != 64
        ):
            raise ValueError("V2.55.69 admitted receipt drifted")
    elif (
        copied.get("nonadmission_reason") not in set(_NONADMISSION_REASONS.values())
        or copied.get("constrained_result_payload_sha256") is not None
        or copied.get("candidate_prediction_changed") is not False
        or any(copied[name] != 0 for name in integer_fields)
    ):
        raise ValueError("V2.55.69 handoff receipt drifted")
    if parent_result is not None:
        checked_parent = parent.validate_result(parent_result)
        if (
            copied["parent_result_payload_sha256"]
            != checked_parent["result_payload_sha256"]
        ):
            raise ValueError("V2.55.69 receipt/parent binding drifted")
    if constrained_result is not None:
        checked = constrained.validate_result(constrained_result)
        nested = checked["deterministic_visible_constraint_receipt"]
        if (
            not admitted
            or copied["constrained_result_payload_sha256"]
            != checked["result_payload_sha256"]
            or copied["parent_result_payload_sha256"]
            != checked["private_parent_result_payload_sha256"]
            or copied["candidate_prediction_changed"]
            is not checked["candidate_prediction_changed"]
            or copied["active_family_count"] != nested["active_family_count"]
            or copied["date_cell_changed_count"]
            != nested["date_cell_changed_count"]
            or copied["scale_cell_changed_count"]
            != nested["scale_cell_changed_count"]
            or copied["sort_applied_count"] != nested["sort_applied_count"]
        ):
            raise ValueError("V2.55.69 receipt/constrained binding drifted")
    return copied


def _result_value(
    checked_parent: Mapping[str, Any],
    checked_constrained: Mapping[str, Any] | None,
    *,
    mode: str,
    nonadmission_reason: str | None,
) -> dict[str, Any]:
    """Construct a result from objects already validated by the caller."""

    prediction = (
        checked_constrained["prediction"]
        if checked_constrained is not None
        else checked_parent["prediction"]
    )
    control = checked_parent["prediction"]
    predictions = {CONTROL_ARM: control, CANDIDATE_ARM: prediction}
    receipt = _receipt_value(
        checked_parent,
        checked_constrained,
        mode=mode,
        nonadmission_reason=nonadmission_reason,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked_parent["opaque_id"],
        "status": "terminal",
        "prediction": prediction,
        "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
        "prediction_kind": checked_parent["prediction_kind"],
        "predictions": predictions,
        "prediction_sha256_by_arm": {
            arm: hashlib.sha256(text.encode()).hexdigest()
            for arm, text in predictions.items()
        },
        "candidate_prediction_changed": control != prediction,
        "mode": mode,
        "projection_admitted": mode == CANONICAL_PROJECTION,
        "byte_exact_parent_handoff": mode == BYTE_EXACT_PARENT_HANDOFF,
        "nonadmission_reason": nonadmission_reason,
        "constraint_totality_receipt": copy.deepcopy(receipt),
        "private_constrained_result": copy.deepcopy(checked_constrained),
        "private_constrained_result_payload_sha256": (
            checked_constrained["result_payload_sha256"]
            if checked_constrained is not None
            else None
        ),
        "private_parent_result": copy.deepcopy(checked_parent),
        "private_parent_result_payload_sha256": checked_parent[
            "result_payload_sha256"
        ],
        "cost": copy.deepcopy(checked_parent["cost"]),
        "scored_prediction_is_constraint_candidate_or_safe_parent_handoff": True,
        "one_parent_forward_shared_by_both_arms": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def build_result(
    parent_result: Mapping[str, Any], visible_question: str
) -> dict[str, Any]:
    """Apply the strict projection or preserve the terminal parent byte-exact."""

    checked = parent.validate_result(parent_result)
    columns, reason = _projection_columns(checked["prediction"])
    if reason is not None:
        value = _result_value(
            checked,
            None,
            mode=BYTE_EXACT_PARENT_HANDOFF,
            nonadmission_reason=reason,
        )
        return _validate_result_with_checked(value, checked, None)
    contract = contracts.build_contract(visible_question, columns or ())
    nested = constrained.validate_result(constrained._wrap_result(checked, contract))
    value = _result_value(
        checked,
        nested,
        mode=CANONICAL_PROJECTION,
        nonadmission_reason=None,
    )
    return _validate_result_with_checked(value, checked, nested)


def _validate_result_with_checked(
    value: Mapping[str, Any],
    checked_parent: Mapping[str, Any],
    checked_constrained: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Validate exact reconstruction without revalidating nested objects."""

    copied = copy.deepcopy(dict(value))
    if checked_constrained is not None:
        if (
            checked_constrained["private_parent_result_payload_sha256"]
            != checked_parent["result_payload_sha256"]
        ):
            raise ValueError("V2.55.69 constrained/parent binding drifted")
        expected = _result_value(
            checked_parent,
            checked_constrained,
            mode=CANONICAL_PROJECTION,
            nonadmission_reason=None,
        )
    else:
        _columns, reason = _projection_columns(checked_parent["prediction"])
        if reason is None:
            raise ValueError("V2.55.69 unjustified parent handoff")
        expected = _result_value(
            checked_parent,
            None,
            mode=BYTE_EXACT_PARENT_HANDOFF,
            nonadmission_reason=reason,
        )
    if copied != expected:
        raise ValueError("V2.55.69 result adapter drifted")
    return copied


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    raw_parent = copied.get("private_parent_result")
    raw_constrained = copied.get("private_constrained_result")
    if not isinstance(raw_parent, Mapping):
        raise ValueError("V2.55.69 private parent result is absent")
    checked_parent = parent.validate_result(raw_parent)
    checked_constrained = (
        constrained.validate_result(raw_constrained)
        if isinstance(raw_constrained, Mapping)
        else None
    )
    return _validate_result_with_checked(
        copied, checked_parent, checked_constrained
    )


def _stage_receipt(
    result: Mapping[str, Any], parent_stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    nested_result = checked["private_constrained_result"]
    nested_stage = (
        constrained._stage_receipt(nested_result, stage)
        if isinstance(nested_result, Mapping)
        else None
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "mode": checked["mode"],
        "constraint_totality_receipt": copy.deepcopy(
            checked["constraint_totality_receipt"]
        ),
        "constrained_stage_receipt": copy.deepcopy(nested_stage),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(
            stage["outer_physical_budget_receipt"]
        ),
        "one_parent_forward_and_totality_safe_local_projection": True,
        "query_fetch_model_token_context_and_wall_caps_unchanged": True,
        "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    # ``result`` and ``parent_stage`` were validated above.  The public runner
    # validates the returned stage once at its trust boundary; revalidating it
    # here would recursively recompute the same deep parent graph.
    return value


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    receipt = copied.get("constraint_totality_receipt")
    parent_stage = copied.get("parent_stage_receipt")
    nested_stage = copied.get("constrained_stage_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "failure_present",
        "failure_stage",
        "failure_type",
        "mode",
        "constraint_totality_receipt",
        "constrained_stage_receipt",
        "parent_stage_receipt",
        "parent_runtime_result_payload_sha256",
        "runtime_result_payload_sha256",
        "outer_physical_budget_receipt",
        "one_parent_forward_and_totality_safe_local_projection",
        "query_fetch_model_token_context_and_wall_caps_unchanged",
        "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
    admitted = copied.get("mode") == CANONICAL_PROJECTION
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("failure_present") is not False
        or copied.get("failure_stage") is not None
        or copied.get("failure_type") is not None
        or copied.get("mode")
        not in {CANONICAL_PROJECTION, BYTE_EXACT_PARENT_HANDOFF}
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["mode"] != copied["mode"]
        or not isinstance(parent_stage, Mapping)
        or parent.validate_stage_receipt(parent_stage) != dict(parent_stage)
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or parent_stage["outer_physical_budget_receipt"] != budget
        or (isinstance(nested_stage, Mapping)) is not admitted
        or (
            admitted
            and constrained.validate_stage_receipt(nested_stage) != dict(nested_stage)
        )
        or (
            admitted
            and (
                nested_stage["parent_stage_receipt"] != parent_stage
                or nested_stage["parent_runtime_result_payload_sha256"]
                != receipt["parent_result_payload_sha256"]
                or nested_stage["runtime_result_payload_sha256"]
                != receipt["constrained_result_payload_sha256"]
            )
        )
        or not isinstance(copied.get("parent_runtime_result_payload_sha256"), str)
        or len(copied["parent_runtime_result_payload_sha256"]) != 64
        or copied["parent_runtime_result_payload_sha256"]
        != receipt["parent_result_payload_sha256"]
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or copied.get("one_parent_forward_and_totality_safe_local_projection")
        is not True
        or copied.get("query_fetch_model_token_context_and_wall_caps_unchanged")
        is not True
        or any(
            copied.get(name) is not False
            for name in (
                "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.69 stage receipt drifted")
    return copied


def run_task(
    task: Mapping[str, Any],
    *,
    model: cap.HardCappedModelLimiter,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    visible = score.validate_visible_task(task)
    parent_result, parent_stage = parent.run_task(
        visible,
        model=model,
        searches=searches,
        limits=limits,
        budget=budget,
        monotonic=monotonic,
    )
    result = build_result(parent_result, visible["question"])
    return result, _stage_receipt(result, parent_stage)


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "constraint_policy_id": contracts.POLICY_ID,
        "strict_projection_policy_id": constrained.POLICY_ID,
        "runtime_input_keys": ["opaque_id", "question"],
        "arms": list(ARMS),
        "one_parent_forward_shared_by_both_arms": True,
        "canonical_projection_behavior_unchanged": True,
        "projection_nonadmission_is_byte_exact_parent_handoff": True,
        "internal_validation_failure_is_not_contained": True,
        "maximum_physical_queries": 4,
        "maximum_physical_fetches": 14,
        "normal_path_model_forwards": 3,
        "additional_model_search_fetch_token_context_wall_or_network_budget": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "ARMS",
    "BYTE_EXACT_PARENT_HANDOFF",
    "CANONICAL_PROJECTION",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "RECEIPT_ROLE",
    "ROLE",
    "STAGE_RECEIPT_ROLE",
    "build_result",
    "integration_contract",
    "run_task",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
