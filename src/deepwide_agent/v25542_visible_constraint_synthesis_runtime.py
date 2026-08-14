"""Inject the V2.55.41 visible constraint into one shared synthesis call.

This append-only runtime preserves V2.54.01's exact planning, grounded-record,
retrieval, synthesis, membership, verifier, and changed-safe editor chain.  A
task-local subclass intercepts only the already-paid third synthesis call. It
parses a pure V2.55.41 contract from the visible question and exact selected
columns, and appends bounded trusted JSON when at least one constraint is
unambiguous.  With no active constraint, the parent third-call system/user
prompts are byte-identical.

The provider response still passes through the frozen parent normalization,
record verification, membership observation, and changed-safe editor.  The
new post-return observer is content-free and non-mutating; it measures only
format/domain adherence and never judges factual correctness.  Physical caps
remain ``4 query / 14 fetch / 3 model``.

Runtime input remains visible ``opaque_id``/``question`` plus injected
same-forward clients.  No benchmark label, mapping, gold, evaluator, score,
reward, truth, credential, or historical result is available.  Entropy and
information gain remain shadow-only with zero signed credit.  This build
grants no launch.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25135_sparse_production_runtime as sparse
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25370_shared_synthesis_changed_safe_runtime as changed_parent
from . import v25375_schema_total_changed_safe_runtime as schema_parent
from . import v25389_hybrid_record_fallback_runtime as hybrid_parent
from . import v25395_visible_membership_synthesis_runtime as membership_parent
from . import v25401_grounded_record_membership_runtime as parent
from . import v25541_visible_output_constraint_contract as constraints
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter


POLICY_ID = "v25542_visible_constraint_synthesis_runtime_v1"
ROLE = "v25542_visible_constraint_synthesis_runtime_result"
RECEIPT_ROLE = "v25542_content_free_visible_constraint_synthesis_receipt"
STAGE_RECEIPT_ROLE = (
    "v25542_content_free_visible_constraint_synthesis_stage_receipt"
)
PHASES = parent.PHASES
CONTROL_ARM = parent.CONTROL_ARM
CANDIDATE_ARM = parent.CANDIDATE_ARM
SCHEMA_SOURCES = parent.SCHEMA_SOURCES
ProductionOnlyStageError = parent.ProductionOnlyStageError


class _VisibleConstraintHybrid(parent._GroundedRecordMembershipHybridInner):
    """Append only a task-local visible contract to call three."""

    def __init__(
        self,
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        *,
        question: str,
    ) -> None:
        super().__init__(bounded, question=question)
        self.constraint_contract: dict[str, Any] | None = None
        self.constraint_suffix = ""
        self.constraint_columns: tuple[str, ...] = ()
        self.parent_third_user_forwarded_byte_exact = False

    def _synthesis(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
    ) -> Any:
        original = str(user)
        columns = tuple(
            sparse._prompt_columns(original, ("Result", "Value"))
        )
        contract = constraints.build_contract(self._question, columns)
        suffix = constraints.contract_suffix(contract)
        self.constraint_contract = contract
        self.constraint_suffix = suffix
        self.constraint_columns = columns
        forwarded = original + suffix
        self.parent_third_user_forwarded_byte_exact = (
            not suffix and forwarded == original
        )
        return super()._synthesis(
            system,
            forwarded,
            max_output_tokens=max_output_tokens,
        )


_INTEGER_FIELDS = (
    "active_family_count",
    "constraint_suffix_characters",
    "selected_column_count",
    "positive_signed_credit_count",
)
_DYNAMIC_FLAGS = (
    "constraint_prompt_applied",
    "temporal_year_range_active",
    "date_format_active",
    "numeric_scale_active",
    "rank_slots_active",
    "explicit_order_active",
    "parent_third_user_forwarded_byte_exact",
)
_TRUE_FLAGS = (
    "contract_uses_only_visible_question_and_exact_selected_columns",
    "constraint_precedes_the_existing_third_model_call",
    "no_active_constraint_preserves_parent_third_call_system_and_user_bytes",
    "provider_response_replays_parent_normalizer_verifier_membership_and_editor",
    "post_return_constraint_observer_is_content_free_and_non_mutating",
    "query4_fetch14_model3_caps_unchanged",
    "task_local_model_projector_verifier_editor_and_constraint_state",
)
_FALSE_FLAGS = (
    "additional_model_search_fetch_token_context_wall_or_network_budget",
    "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential",
    "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
    "entropy_or_information_gain_assigns_signed_credit",
    "module_global_state_mutated",
    "benchmark_launch_or_evaluator_authorized",
)


def _receipt(
    hybrid: _VisibleConstraintHybrid,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    if hybrid.constraint_contract is None or not hybrid.constraint_columns:
        raise ValueError("V2.55.42 constraint synthesis trace is absent")
    contract = constraints.validate_contract(hybrid.constraint_contract)
    observation = constraints.observe_prediction(
        contract, checked["prediction"]
    )
    active = contract["active_family_count"] > 0
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "active_family_count": contract["active_family_count"],
        "constraint_suffix_characters": len(hybrid.constraint_suffix),
        "selected_column_count": len(hybrid.constraint_columns),
        "positive_signed_credit_count": 0,
        "constraint_prompt_applied": active,
        "temporal_year_range_active": contract["temporal_year_range"]
        is not None,
        "date_format_active": contract["date_format"] is not None,
        "numeric_scale_active": contract["numeric_scale"] is not None,
        "rank_slots_active": contract["rank_slots"] is not None,
        "explicit_order_active": contract["explicit_order"] is not None,
        "parent_third_user_forwarded_byte_exact": bool(
            hybrid.parent_third_user_forwarded_byte_exact
        ),
        "constraint_contract_payload_sha256": contract[
            "contract_payload_sha256"
        ],
        "parent_result_payload_sha256": checked["result_payload_sha256"],
        "constraint_observation": copy.deepcopy(observation),
        **{name: True for name in _TRUE_FLAGS},
        **{name: False for name in _FALSE_FLAGS},
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(
        value, parent_result=checked, contract=contract
    )


def validate_receipt(
    value: Mapping[str, Any],
    *,
    parent_result: Mapping[str, Any] | None = None,
    contract: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    observation = copied.get("constraint_observation")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_INTEGER_FIELDS,
        *_DYNAMIC_FLAGS,
        "constraint_contract_payload_sha256",
        "parent_result_payload_sha256",
        "constraint_observation",
        *_TRUE_FLAGS,
        *_FALSE_FLAGS,
        "receipt_payload_sha256",
    }
    active = copied.get("constraint_prompt_applied") is True
    family_flags = (
        "temporal_year_range_active",
        "date_format_active",
        "numeric_scale_active",
        "rank_slots_active",
        "explicit_order_active",
    )
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _INTEGER_FIELDS
        )
        or not 1 <= copied["selected_column_count"] <= 20
        or any(
            not isinstance(copied.get(name), bool)
            for name in _DYNAMIC_FLAGS
        )
        or copied["active_family_count"]
        != sum(int(copied[name]) for name in family_flags)
        or active is not (copied["active_family_count"] > 0)
        or active is not (copied["constraint_suffix_characters"] > 0)
        or copied["parent_third_user_forwarded_byte_exact"] is not (not active)
        or copied["positive_signed_credit_count"] != 0
        or not isinstance(copied.get("constraint_contract_payload_sha256"), str)
        or len(copied["constraint_contract_payload_sha256"]) != 64
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or not isinstance(observation, Mapping)
        or constraints.validate_observation(observation) != dict(observation)
        or observation["active_family_count"] != copied["active_family_count"]
        or any(copied.get(name) is not True for name in _TRUE_FLAGS)
        or any(copied.get(name) is not False for name in _FALSE_FLAGS)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.42 visible constraint receipt drifted")
    if contract is not None:
        checked_contract = constraints.validate_contract(contract)
        if (
            copied["constraint_contract_payload_sha256"]
            != checked_contract["contract_payload_sha256"]
            or copied["active_family_count"]
            != checked_contract["active_family_count"]
            or copied["selected_column_count"]
            != len(checked_contract["columns"])
            or copied["constraint_suffix_characters"]
            != len(constraints.contract_suffix(checked_contract))
            or any(
                copied[flag]
                is not (checked_contract[family] is not None)
                for flag, family in zip(family_flags, constraints.FAMILY_ORDER)
            )
        ):
            raise ValueError("V2.55.42 receipt/contract binding drifted")
    if parent_result is not None:
        checked_parent = parent.validate_result(parent_result)
        if (
            copied["parent_result_payload_sha256"]
            != checked_parent["result_payload_sha256"]
            or contract is None
            or observation
            != constraints.observe_prediction(
                constraints.validate_contract(contract),
                checked_parent["prediction"],
            )
        ):
            raise ValueError("V2.55.42 receipt/parent binding drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any],
    contract: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    constraint = constraints.validate_contract(contract)
    observed = validate_receipt(
        receipt, parent_result=checked, contract=constraint
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked["opaque_id"],
        "status": "terminal",
        "prediction": checked["prediction"],
        "prediction_sha256": checked["prediction_sha256"],
        "prediction_kind": checked["prediction_kind"],
        "control_prediction_sha256": checked["control_prediction_sha256"],
        "prediction_changed": checked["prediction_changed"],
        "changed_safe_coordinate_count": checked[
            "changed_safe_coordinate_count"
        ],
        "attributable_prediction_change": checked[
            "attributable_prediction_change"
        ],
        "visible_constraint_synthesis_receipt": copy.deepcopy(observed),
        "private_visible_constraint_contract": copy.deepcopy(constraint),
        "private_parent_result": copy.deepcopy(checked),
        "private_parent_result_payload_sha256": checked[
            "result_payload_sha256"
        ],
        "cost": copy.deepcopy(checked["cost"]),
        "scored_prediction_is_parent_changed_safe_candidate": True,
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
    receipt = copied.get("visible_constraint_synthesis_receipt")
    if (
        not isinstance(raw, Mapping)
        or not isinstance(contract, Mapping)
        or not isinstance(receipt, Mapping)
    ):
        raise ValueError("V2.55.42 private result surface is absent")
    expected = _wrap_result(raw, contract, receipt)
    if copied != expected:
        raise ValueError("V2.55.42 result adapter drifted")
    return copied


def _stage_receipt(
    result: Mapping[str, Any], parent_stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = validate_result(result)
    stage = parent.validate_stage_receipt(parent_stage)
    contract = constraints.validate_contract(
        checked["private_visible_constraint_contract"]
    )
    receipt = validate_receipt(
        checked["visible_constraint_synthesis_receipt"],
        parent_result=checked["private_parent_result"],
        contract=contract,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "visible_constraint_synthesis_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(
            stage["outer_physical_budget_receipt"]
        ),
        "visible_constraint_precedes_existing_third_call": True,
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
    receipt = copied.get("visible_constraint_synthesis_receipt")
    stage = copied.get("parent_stage_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    true_flags = (
        "visible_constraint_precedes_existing_third_call",
        "query_fetch_model_token_context_and_wall_caps_unchanged",
    )
    false_flags = (
        "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "failure_present",
        "failure_stage",
        "failure_type",
        "visible_constraint_synthesis_receipt",
        "parent_stage_receipt",
        "parent_runtime_result_payload_sha256",
        "runtime_result_payload_sha256",
        "outer_physical_budget_receipt",
        *true_flags,
        *false_flags,
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
        or receipt["parent_result_payload_sha256"]
        != copied.get("parent_runtime_result_payload_sha256")
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.42 stage receipt drifted")
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
    if (
        not isinstance(model, cap.HardCappedModelLimiter)
        or model._budget is not budget
        or not isinstance(
            model._inner_limiter, DeadlineAwareGlobalModelSlotLimiter
        )
        or model._synthesis_entry_count != 0
    ):
        raise ValueError("V2.55.42 hard-capped model wiring drifted")
    projector = schema_parent._TaskLocalProjector(visible["question"])
    hybrid = _VisibleConstraintHybrid(
        model._inner_limiter, question=visible["question"]
    )
    hybrid_model = cap.HardCappedModelLimiter(hybrid, budget)
    isolated = membership_parent._isolated_parent(projector, hybrid)
    changed = changed_parent.validate_result(
        isolated(
            visible,
            model=hybrid_model,
            searches=searches,
            limits=limits,
            budget=budget,
            monotonic=monotonic,
        )
    )
    schema_receipt = schema_parent._schema_receipt(
        projector, visible["question"]
    )
    hybrid_receipt = hybrid_parent._receipt(hybrid, changed)
    hybrid_result = hybrid_parent.validate_result(
        hybrid_parent._wrap_result(changed, schema_receipt, hybrid_receipt)
    )
    hybrid_stage = hybrid_parent._stage_receipt(hybrid_result)
    membership_receipt = membership_parent._receipt(hybrid, hybrid_result)
    membership_result = membership_parent.validate_result(
        membership_parent._wrap_result(
            hybrid_result,
            visible["question"],
            hybrid.visible_members,
            hybrid.membership_source,
            membership_receipt,
        )
    )
    membership_stage = membership_parent._stage_receipt(
        membership_result, hybrid_stage
    )
    record_receipt = parent._receipt(hybrid, membership_result)
    parent_result = parent.validate_result(
        parent._wrap_result(membership_result, record_receipt)
    )
    parent_stage = parent._stage_receipt(parent_result, membership_stage)
    if hybrid.constraint_contract is None:
        raise ValueError("V2.55.42 provider did not enter synthesis")
    receipt = _receipt(hybrid, parent_result)
    result = validate_result(
        _wrap_result(parent_result, hybrid.constraint_contract, receipt)
    )
    return result, _stage_receipt(result, parent_stage)


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "constraint_policy_id": constraints.POLICY_ID,
        "runtime_input_keys": ["opaque_id", "question"],
        "one_existing_third_model_call_receives_constraint": True,
        "no_active_constraint_parent_prompt_byte_exact": True,
        "parent_normalizer_verifier_membership_and_editor_replayed": True,
        "post_return_observer_changes_prediction": False,
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
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "RECEIPT_ROLE",
    "ROLE",
    "SCHEMA_SOURCES",
    "STAGE_RECEIPT_ROLE",
    "integration_contract",
    "run_task",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
