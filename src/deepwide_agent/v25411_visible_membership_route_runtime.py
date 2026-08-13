"""Label-blind visible-membership route over two frozen runtimes.

V2.54.06 sent every public task through the V2.54.01 adapter even though
only eleven of 220 visible questions declared strict row membership.  Eleven
membership-absent tasks then failed after all provider effects had completed,
while the same tasks were terminal under the frozen V2.53.75 runtime.  The
available content-free artifacts do not identify the exact failing function,
so this successor does not speculate about or relax any validator.

Instead, the already-audited strict visible-question membership parser is the
only route signal.  A task with no unambiguous visible membership calls
V2.53.75 exactly once.  A task with visible membership calls V2.54.01 exactly
once.  The selected parent's result and stage objects are returned directly:
there is no wrapper, copy, reseal, post-processing, or fallback into the other
branch.  Union validators recognize both frozen sealed surfaces without
changing either one.

Runtime inputs remain visible ``opaque_id``/``question`` plus injected
same-forward clients.  No benchmark label, mapping, gold, evaluator, score,
reward, historical outcome, filesystem, environment, process, credential, or
network capability is introduced.  Entropy/information gain does not route
and assigns no signed credit.  This build authorizes no external forward or
benchmark execution.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25375_schema_total_changed_safe_runtime as stable_parent
from . import v25395_visible_membership_synthesis_runtime as visible_membership
from . import v25401_grounded_record_membership_runtime as membership_parent
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25411_visible_membership_route_runtime_v1"
STABLE_BRANCH = "v25375_membership_absent"
MEMBERSHIP_BRANCH = "v25401_membership_present"
BRANCHES = frozenset({STABLE_BRANCH, MEMBERSHIP_BRANCH})
FAILURE_STAGE_RECEIPT_ROLE = (
    "v25411_content_free_visible_membership_route_failure_stage_receipt"
)
PHASES = stable_parent.PHASES
CONTROL_ARM = stable_parent.CONTROL_ARM
CANDIDATE_ARM = stable_parent.CANDIDATE_ARM


class ProductionOnlyStageError(RuntimeError):
    """Finite outer signal for a failed route or selected parent call."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        self.stage_receipt = validate_failure_stage_receipt(receipt)
        super().__init__("V2.54.11 selected runtime branch failed")


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _failure_stage_receipt(
    *,
    branch: str | None,
    failure_stage: str,
    exc: BaseException,
    budget: cap.PhysicalEffectBudget,
) -> dict[str, Any]:
    route_completed = branch in BRANCHES
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": FAILURE_STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": True,
        "failure_stage": failure_stage,
        "failure_type": _safe_failure(exc),
        "selected_branch": branch,
        "visible_membership_route_completed": route_completed,
        "selected_parent_entered": route_completed,
        "selected_parent_returned": False,
        "outer_physical_budget_receipt": copy.deepcopy(budget.receipt()),
        "successful_parent_result_and_stage_objects_are_returned_unchanged": True,
        "at_most_one_parent_runtime_call": True,
        "cross_branch_retry_fallback_or_replay": False,
        "route_uses_entropy_information_gain_or_historical_outcome": False,
        "contains_question_membership_identity_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_failure_stage_receipt(value)


def validate_failure_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    branch = copied.get("selected_branch")
    stage = copied.get("failure_stage")
    failure_type = copied.get("failure_type")
    route_completed = copied.get("visible_membership_route_completed") is True
    true_flags = (
        "successful_parent_result_and_stage_objects_are_returned_unchanged",
        "at_most_one_parent_runtime_call",
    )
    false_flags = (
        "cross_branch_retry_fallback_or_replay",
        "route_uses_entropy_information_gain_or_historical_outcome",
        "contains_question_membership_identity_query_url_page_prediction_answer_opaque_id_or_credential",
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
        "selected_branch",
        "visible_membership_route_completed",
        "selected_parent_entered",
        "selected_parent_returned",
        "outer_physical_budget_receipt",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    budget = copied.get("outer_physical_budget_receipt")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != FAILURE_STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("failure_present") is not True
        or stage not in {"visible_membership_route", "selected_parent_runtime"}
        or not isinstance(failure_type, str)
        or not 0 < len(failure_type) <= 128
        or (branch in BRANCHES) is not route_completed
        or (stage == "visible_membership_route")
        is not (not route_completed and branch is None)
        or copied.get("selected_parent_entered") is not route_completed
        or copied.get("selected_parent_returned") is not False
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.11 route failure stage receipt drifted")
    return copied


def route_for_visible_question(question: str) -> str:
    """Choose a frozen parent using only strict visible membership syntax."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.54.11 visible question is absent")
    members, _source = visible_membership.visible_membership(question.strip())
    return MEMBERSHIP_BRANCH if members else STABLE_BRANCH


def _result_branch(value: Mapping[str, Any]) -> str:
    role = value.get("role") if isinstance(value, Mapping) else None
    policy = value.get("policy_id") if isinstance(value, Mapping) else None
    if role == stable_parent.ROLE and policy == stable_parent.POLICY_ID:
        return STABLE_BRANCH
    if role == membership_parent.ROLE and policy == membership_parent.POLICY_ID:
        return MEMBERSHIP_BRANCH
    raise ValueError("V2.54.11 result branch is not recognized")


def _stage_branch(value: Mapping[str, Any]) -> str:
    role = value.get("role") if isinstance(value, Mapping) else None
    policy = value.get("policy_id") if isinstance(value, Mapping) else None
    if (
        role == stable_parent.STAGE_RECEIPT_ROLE
        and policy == stable_parent.POLICY_ID
    ):
        return STABLE_BRANCH
    if (
        role == membership_parent.STAGE_RECEIPT_ROLE
        and policy == membership_parent.POLICY_ID
    ):
        return MEMBERSHIP_BRANCH
    raise ValueError("V2.54.11 stage branch is not recognized")


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate either parent result without adapting its sealed surface."""

    branch = _result_branch(value)
    if branch == STABLE_BRANCH:
        return stable_parent.validate_result(value)
    return membership_parent.validate_result(value)


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate either parent stage receipt without adapting its surface."""

    if (
        isinstance(value, Mapping)
        and value.get("role") == FAILURE_STAGE_RECEIPT_ROLE
    ):
        return validate_failure_stage_receipt(value)
    branch = _stage_branch(value)
    if branch == STABLE_BRANCH:
        return stable_parent.validate_stage_receipt(value)
    return membership_parent.validate_stage_receipt(value)


def validate_runtime_pair(
    result: Mapping[str, Any], stage: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate one same-branch sealed result/stage pair."""

    result_branch = _result_branch(result)
    if _stage_branch(stage) != result_branch:
        raise ValueError("V2.54.11 result/stage branch mismatch")
    checked_result = validate_result(result)
    checked_stage = validate_stage_receipt(stage)
    if result_branch == STABLE_BRANCH:
        if (
            checked_stage["parent_result_payload_sha256"]
            != checked_result["private_parent_result_payload_sha256"]
            or checked_stage["schema_totality_receipt"]
            != checked_result["schema_totality_receipt"]
        ):
            raise ValueError("V2.54.11 stable result/stage binding drifted")
    elif (
        checked_stage["runtime_result_payload_sha256"]
        != checked_result["result_payload_sha256"]
        or checked_stage["parent_runtime_result_payload_sha256"]
        != checked_result["private_parent_result_payload_sha256"]
    ):
        raise ValueError("V2.54.11 membership result/stage binding drifted")
    return checked_result, checked_stage


def run_task(
    task: Mapping[str, Any],
    *,
    model: cap.HardCappedModelLimiter,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run exactly one frozen parent and return its objects unchanged."""

    visible = score.validate_visible_task(task)
    try:
        branch = route_for_visible_question(visible["question"])
    except BaseException as exc:
        raise ProductionOnlyStageError(
            _failure_stage_receipt(
                branch=None,
                failure_stage="visible_membership_route",
                exc=exc,
                budget=budget,
            )
        ) from None
    selected = (
        membership_parent if branch == MEMBERSHIP_BRANCH else stable_parent
    )
    try:
        return selected.run_task(
            visible,
            model=model,
            searches=searches,
            limits=limits,
            budget=budget,
            monotonic=monotonic,
        )
    except BaseException as exc:
        raise ProductionOnlyStageError(
            _failure_stage_receipt(
                branch=branch,
                failure_stage="selected_parent_runtime",
                exc=exc,
                budget=budget,
            )
        ) from None


__all__ = [
    "BRANCHES",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "FAILURE_STAGE_RECEIPT_ROLE",
    "MEMBERSHIP_BRANCH",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "STABLE_BRANCH",
    "route_for_visible_question",
    "run_task",
    "validate_result",
    "validate_failure_stage_receipt",
    "validate_runtime_pair",
    "validate_stage_receipt",
]
