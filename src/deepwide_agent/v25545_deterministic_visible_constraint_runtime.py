"""One-parent runtime with a deterministic visible-constraint projection.

This wrapper invokes V2.54.01 exactly once and treats its scored production
prediction as the shared control.  It derives the V2.55.41 contract from the
visible question and the exact canonical parent columns, then applies the
pure V2.55.44 projector locally.  Control and candidate therefore share all
model, search, fetch, page-byte, sampling, token, context, and wall effects.

No active or safely applicable transform is a byte-exact handoff.  The
projector never deletes rows for temporal ranges, never creates rank slots,
and never repairs unsupported facts.  Runtime input remains visible
``opaque_id``/``question`` plus injected same-forward clients.  No benchmark
label, mapping, gold, evaluator, score, reward, truth, credential, or
historical result is available.  Entropy/information gain is shadow-only and
assigns zero signed credit.  This build grants no launch.
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
from . import v25544_deterministic_visible_constraint_projector as projector
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25545_deterministic_visible_constraint_runtime_v1"
ROLE = "v25545_deterministic_visible_constraint_runtime_result"
RECEIPT_ROLE = "v25545_content_free_deterministic_constraint_runtime_receipt"
STAGE_RECEIPT_ROLE = (
    "v25545_content_free_deterministic_constraint_runtime_stage_receipt"
)
ARMS = ("shared_parent_control", "deterministic_constraint_candidate")
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
ProductionOnlyStageError = parent.ProductionOnlyStageError


def _visible_columns(prediction: object) -> tuple[str, ...]:
    lines = [
        line.strip()
        for line in str(prediction).splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if not lines:
        raise ValueError("V2.55.45 visible table header is absent")
    columns = tuple(score._split_table_row(lines[0]))
    projector._matrix(prediction, columns)
    return columns


def _receipt(
    parent_result: Mapping[str, Any],
    contract: Mapping[str, Any],
    projection: Mapping[str, Any],
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    constraint = contracts.validate_contract(contract)
    projected = projector.validate_projection(projection, contract=constraint)
    projection_receipt = projector.validate_receipt(
        projected["content_free_receipt"]
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "active_family_count": constraint["active_family_count"],
        "date_cell_changed_count": projection_receipt[
            "date_cell_changed_count"
        ],
        "scale_cell_changed_count": projection_receipt[
            "scale_cell_changed_count"
        ],
        "sort_applied_count": projection_receipt["sort_applied_count"],
        "positive_signed_credit_count": 0,
        "constraint_active": constraint["active_family_count"] > 0,
        "candidate_prediction_changed": projected[
            "candidate_prediction_changed"
        ],
        "constraint_contract_payload_sha256": constraint[
            "contract_payload_sha256"
        ],
        "projection_artifact_payload_sha256": projected[
            "artifact_payload_sha256"
        ],
        "parent_result_payload_sha256": checked["result_payload_sha256"],
        "projection_receipt": copy.deepcopy(projection_receipt),
        "one_v25401_parent_forward_only": True,
        "base_and_candidate_share_all_provider_retrieval_and_sampling_effects": True,
        "candidate_is_only_v25544_pure_deterministic_projection": True,
        "no_safe_projection_returns_parent_prediction_byte_exact": True,
        "query4_fetch14_model3_caps_unchanged": True,
        "contains_question_column_value_prediction_query_url_page_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed_by_wrapper": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(
        value,
        parent_result=checked,
        contract=constraint,
        projection=projected,
    )


def validate_receipt(
    value: Mapping[str, Any],
    *,
    parent_result: Mapping[str, Any] | None = None,
    contract: Mapping[str, Any] | None = None,
    projection: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    nested = copied.get("projection_receipt")
    integer_fields = (
        "active_family_count",
        "date_cell_changed_count",
        "scale_cell_changed_count",
        "sort_applied_count",
        "positive_signed_credit_count",
    )
    dynamic_flags = ("constraint_active", "candidate_prediction_changed")
    true_flags = (
        "one_v25401_parent_forward_only",
        "base_and_candidate_share_all_provider_retrieval_and_sampling_effects",
        "candidate_is_only_v25544_pure_deterministic_projection",
        "no_safe_projection_returns_parent_prediction_byte_exact",
        "query4_fetch14_model3_caps_unchanged",
    )
    false_flags = (
        "contains_question_column_value_prediction_query_url_page_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed_by_wrapper",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *integer_fields,
        *dynamic_flags,
        "constraint_contract_payload_sha256",
        "projection_artifact_payload_sha256",
        "parent_result_payload_sha256",
        "projection_receipt",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamic_flags)
        or copied["constraint_active"]
        is not (copied["active_family_count"] > 0)
        or copied["positive_signed_credit_count"] != 0
        or any(
            not isinstance(copied.get(name), str) or len(copied[name]) != 64
            for name in (
                "constraint_contract_payload_sha256",
                "projection_artifact_payload_sha256",
                "parent_result_payload_sha256",
            )
        )
        or not isinstance(nested, Mapping)
        or projector.validate_receipt(nested) != dict(nested)
        or copied["date_cell_changed_count"]
        != nested["date_cell_changed_count"]
        or copied["scale_cell_changed_count"]
        != nested["scale_cell_changed_count"]
        or copied["sort_applied_count"] != nested["sort_applied_count"]
        or copied["candidate_prediction_changed"]
        is not nested["candidate_prediction_changed"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.45 deterministic runtime receipt drifted")
    if contract is not None:
        checked_contract = contracts.validate_contract(contract)
        if (
            copied["constraint_contract_payload_sha256"]
            != checked_contract["contract_payload_sha256"]
            or copied["active_family_count"]
            != checked_contract["active_family_count"]
        ):
            raise ValueError("V2.55.45 receipt/contract binding drifted")
    if parent_result is not None:
        checked_parent = parent.validate_result(parent_result)
        if copied["parent_result_payload_sha256"] != checked_parent["result_payload_sha256"]:
            raise ValueError("V2.55.45 receipt/parent binding drifted")
    if projection is not None:
        if contract is None:
            raise ValueError("V2.55.45 projection requires bound contract")
        checked_projection = projector.validate_projection(
            projection, contract=contract
        )
        if (
            copied["projection_artifact_payload_sha256"]
            != checked_projection["artifact_payload_sha256"]
            or dict(nested) != checked_projection["content_free_receipt"]
        ):
            raise ValueError("V2.55.45 receipt/projection binding drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    constraint = contracts.validate_contract(contract)
    projected = projector.build_projection(checked["prediction"], constraint)
    receipt = _receipt(checked, constraint, projected)
    control = projected["control_prediction"]
    candidate = projected["candidate_prediction"]
    predictions = {CONTROL_ARM: control, CANDIDATE_ARM: candidate}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked["opaque_id"],
        "status": "terminal",
        "prediction": candidate,
        "prediction_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "prediction_kind": checked["prediction_kind"],
        "predictions": predictions,
        "prediction_sha256_by_arm": {
            arm: hashlib.sha256(prediction.encode()).hexdigest()
            for arm, prediction in predictions.items()
        },
        "candidate_prediction_changed": control != candidate,
        "deterministic_visible_constraint_receipt": copy.deepcopy(receipt),
        "private_visible_constraint_contract": copy.deepcopy(constraint),
        "private_parent_result": copy.deepcopy(checked),
        "private_parent_result_payload_sha256": checked["result_payload_sha256"],
        "cost": copy.deepcopy(checked["cost"]),
        "scored_prediction_is_deterministic_constraint_candidate": True,
        "both_arms_share_one_v25401_parent_forward": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    raw = copied.get("private_parent_result")
    contract = copied.get("private_visible_constraint_contract")
    receipt = copied.get("deterministic_visible_constraint_receipt")
    if (
        not isinstance(raw, Mapping)
        or not isinstance(contract, Mapping)
        or not isinstance(receipt, Mapping)
    ):
        raise ValueError("V2.55.45 private parent/contract/receipt is absent")
    expected = _wrap_result(raw, contract)
    if copied != expected:
        raise ValueError("V2.55.45 result adapter drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any], parent_stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    contract = contracts.validate_contract(
        checked["private_visible_constraint_contract"]
    )
    projection = projector.build_projection(
        checked["predictions"][CONTROL_ARM], contract
    )
    receipt = validate_receipt(
        checked["deterministic_visible_constraint_receipt"],
        parent_result=checked["private_parent_result"],
        contract=contract,
        projection=projection,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "deterministic_visible_constraint_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(
            stage["outer_physical_budget_receipt"]
        ),
        "one_parent_forward_and_pure_local_projection": True,
        "query_fetch_model_token_context_and_wall_caps_unchanged": True,
        "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_stage_receipt(value)


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    receipt = copied.get("deterministic_visible_constraint_receipt")
    stage = copied.get("parent_stage_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "failure_present",
        "failure_stage",
        "failure_type",
        "deterministic_visible_constraint_receipt",
        "parent_stage_receipt",
        "parent_runtime_result_payload_sha256",
        "runtime_result_payload_sha256",
        "outer_physical_budget_receipt",
        "one_parent_forward_and_pure_local_projection",
        "query_fetch_model_token_context_and_wall_caps_unchanged",
        "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("failure_present") is not False
        or copied.get("failure_stage") is not None
        or copied.get("failure_type") is not None
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or not isinstance(stage, Mapping)
        or parent.validate_stage_receipt(stage) != dict(stage)
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or stage["outer_physical_budget_receipt"] != budget
        or not isinstance(copied.get("parent_runtime_result_payload_sha256"), str)
        or len(copied["parent_runtime_result_payload_sha256"]) != 64
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or copied.get("one_parent_forward_and_pure_local_projection") is not True
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
        raise ValueError("V2.55.45 stage receipt drifted")
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
    checked = parent.validate_result(parent_result)
    contract = contracts.build_contract(
        visible["question"], _visible_columns(checked["prediction"])
    )
    result = validate_result(_wrap_result(checked, contract))
    return result, _stage_receipt(result, parent_stage)


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "constraint_policy_id": contracts.POLICY_ID,
        "projector_policy_id": projector.POLICY_ID,
        "runtime_input_keys": ["opaque_id", "question"],
        "arms": list(ARMS),
        "one_parent_forward_shared_by_both_arms": True,
        "candidate_has_no_independent_model_or_sampling_effect": True,
        "candidate_only_effect_is_pure_deterministic_projection": True,
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
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "RECEIPT_ROLE",
    "ROLE",
    "STAGE_RECEIPT_ROLE",
    "integration_contract",
    "run_task",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
