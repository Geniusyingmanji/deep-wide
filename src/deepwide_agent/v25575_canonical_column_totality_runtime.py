"""Canonical-column binding totality over the frozen V2.55.69 runtime.

V2.55.74 proved that the eleven persistent public exact-220 outer failures
are exactly the tasks whose visible schema contains a Unicode or whitespace
spelling that changes under the quote verifier's existing NFKC canonicalizer.
V2.53.95 prepares quote-verifier columns through that canonicalizer, but then
compares them bytewise with the raw runtime column vector.  The mismatch
escapes the editor's fallback boundary after all provider effects complete.

This append-only successor changes only that task-local equality check.  Both
the prepared vector and requested vector must pass the same frozen
``v25065._safe_columns`` contract and their canonical tuples must match.
Invalid, duplicate, overlong, empty, or forbidden columns remain fail-closed.
Question binding, source priority, quote verification, editor behavior,
prompts, model/search/fetch effects, physical caps, and every sealed result and
stage schema remain unchanged.

The corrected V2.54.01 parent objects are passed to the frozen V2.55.69
projection/handoff logic without adapting either sealed surface.  Runtime
input remains visible ``opaque_id`` and ``question`` plus injected same-pass
clients.  No benchmark label, mapping, gold, evaluator, score, reward,
historical outcome, filesystem, environment, process, credential, or direct
network capability is introduced.  Entropy/information gain neither routes
nor assigns signed credit.  This build authorizes no external execution.
"""

from __future__ import annotations

import copy
import hashlib
import types
from collections.abc import Callable, Mapping, Sequence
from types import SimpleNamespace
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25065_quote_verified_record_binding as quote
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25370_shared_synthesis_changed_safe_runtime as changed_parent
from . import v25375_schema_total_changed_safe_runtime as schema_parent
from . import v25389_hybrid_record_fallback_runtime as hybrid_parent
from . import v25395_visible_membership_synthesis_runtime as visible_parent
from . import v25401_grounded_record_membership_runtime as membership_parent
from . import v25569_constraint_totality_safe_handoff_runtime as totality
from . import v25541_visible_output_constraint_contract as contracts
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter


POLICY_ID = "v25575_canonical_column_binding_totality_runtime_v1"
HANDOFF_ROLE = "v25575_canonical_column_handoff_runtime_result"
HANDOFF_RECEIPT_ROLE = "v25575_content_free_canonical_column_handoff_receipt"
HANDOFF_STAGE_RECEIPT_ROLE = (
    "v25575_content_free_canonical_column_handoff_stage_receipt"
)
CANONICAL_COLUMN_NONADMISSION = "contract_column_canonicalization_drift"
PHASES = totality.PHASES
CONTROL_ARM = totality.CONTROL_ARM
CANDIDATE_ARM = totality.CANDIDATE_ARM
ARMS = totality.ARMS
CANONICAL_PROJECTION = totality.CANONICAL_PROJECTION
BYTE_EXACT_PARENT_HANDOFF = totality.BYTE_EXACT_PARENT_HANDOFF
ProductionOnlyStageError = membership_parent.ProductionOnlyStageError


def _canonical_column_nonadmission(
    prediction: object,
) -> tuple[tuple[str, ...] | None, tuple[str, ...] | None]:
    """Return raw/canonical columns only for the newly diagnosed drift."""

    columns, reason = totality._projection_columns(prediction)
    if reason is not None or columns is None:
        return None, None
    canonical = contracts._safe_columns(columns)
    return (columns, canonical) if columns != canonical else (None, None)


def _handoff_receipt_value(parent_result: Mapping[str, Any]) -> dict[str, Any]:
    checked = membership_parent.validate_result(parent_result)
    raw, canonical = _canonical_column_nonadmission(checked["prediction"])
    if raw is None or canonical is None:
        raise ValueError("V2.55.75 canonical column handoff is unjustified")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": HANDOFF_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "mode": BYTE_EXACT_PARENT_HANDOFF,
        "nonadmission_reason": CANONICAL_COLUMN_NONADMISSION,
        "raw_column_count": len(raw),
        "canonical_column_count": len(canonical),
        "candidate_prediction_changed": False,
        "positive_signed_credit_count": 0,
        "parent_result_payload_sha256": checked["result_payload_sha256"],
        "parent_prediction_is_exact_canonical_under_raw_columns": True,
        "raw_and_contract_canonical_columns_differ_bytewise": True,
        "raw_and_contract_columns_are_nfkc_semantically_equivalent": True,
        "parent_prediction_is_returned_byte_exact": True,
        "no_projection_contract_or_editor_is_executed_after_nonadmission": True,
        "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "historical_per_task_outcome_runtime_routing": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed_by_handoff": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return value


def validate_handoff_receipt(
    value: Mapping[str, Any],
    *,
    parent_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    integer_fields = (
        "raw_column_count",
        "canonical_column_count",
        "positive_signed_credit_count",
    )
    true_flags = (
        "parent_prediction_is_exact_canonical_under_raw_columns",
        "raw_and_contract_canonical_columns_differ_bytewise",
        "raw_and_contract_columns_are_nfkc_semantically_equivalent",
        "parent_prediction_is_returned_byte_exact",
        "no_projection_contract_or_editor_is_executed_after_nonadmission",
    )
    false_flags = (
        "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "historical_per_task_outcome_runtime_routing",
        "entropy_or_information_gain_assigns_signed_credit",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed_by_handoff",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "mode",
        "nonadmission_reason",
        *integer_fields,
        "candidate_prediction_changed",
        "parent_result_payload_sha256",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != HANDOFF_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("mode") != BYTE_EXACT_PARENT_HANDOFF
        or copied.get("nonadmission_reason") != CANONICAL_COLUMN_NONADMISSION
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or copied.get("raw_column_count")
        != copied.get("canonical_column_count")
        or not 1 <= copied.get("raw_column_count", 0) <= 20
        or copied.get("candidate_prediction_changed") is not False
        or copied.get("positive_signed_credit_count") != 0
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.75 canonical column handoff receipt drifted")
    if parent_result is not None:
        checked = membership_parent.validate_result(parent_result)
        expected_value = _handoff_receipt_value(checked)
        if copied != expected_value:
            raise ValueError("V2.55.75 handoff/parent binding drifted")
    return copied


def _handoff_result_value(parent_result: Mapping[str, Any]) -> dict[str, Any]:
    checked = membership_parent.validate_result(parent_result)
    receipt = validate_handoff_receipt(
        _handoff_receipt_value(checked), parent_result=checked
    )
    prediction = checked["prediction"]
    predictions = {CONTROL_ARM: prediction, CANDIDATE_ARM: prediction}
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": HANDOFF_ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked["opaque_id"],
        "status": "terminal",
        "prediction": prediction,
        "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
        "prediction_kind": checked["prediction_kind"],
        "predictions": predictions,
        "prediction_sha256_by_arm": {
            arm: hashlib.sha256(text.encode()).hexdigest()
            for arm, text in predictions.items()
        },
        "candidate_prediction_changed": False,
        "mode": BYTE_EXACT_PARENT_HANDOFF,
        "projection_admitted": False,
        "byte_exact_parent_handoff": True,
        "nonadmission_reason": CANONICAL_COLUMN_NONADMISSION,
        "canonical_column_handoff_receipt": copy.deepcopy(receipt),
        "private_parent_result": copy.deepcopy(checked),
        "private_parent_result_payload_sha256": checked[
            "result_payload_sha256"
        ],
        "cost": copy.deepcopy(checked["cost"]),
        "scored_prediction_is_byte_exact_corrected_parent_handoff": True,
        "one_corrected_parent_forward_only": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "historical_per_task_outcome_runtime_routing": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_handoff_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    raw_parent = copied.get("private_parent_result")
    if not isinstance(raw_parent, Mapping):
        raise ValueError("V2.55.75 private handoff parent is absent")
    checked_parent = membership_parent.validate_result(raw_parent)
    expected = _handoff_result_value(checked_parent)
    if copied != expected:
        raise ValueError("V2.55.75 canonical column handoff result drifted")
    return copied


def _handoff_stage_value(
    result: Mapping[str, Any], parent_stage: Mapping[str, Any]
) -> dict[str, Any]:
    checked = validate_handoff_result(result)
    stage = membership_parent.validate_stage_receipt(parent_stage)
    receipt = validate_handoff_receipt(
        checked["canonical_column_handoff_receipt"],
        parent_result=checked["private_parent_result"],
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": HANDOFF_STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "mode": BYTE_EXACT_PARENT_HANDOFF,
        "canonical_column_handoff_receipt": copy.deepcopy(receipt),
        "parent_stage_receipt": copy.deepcopy(stage),
        "parent_runtime_result_payload_sha256": checked[
            "private_parent_result_payload_sha256"
        ],
        "runtime_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(
            stage["outer_physical_budget_receipt"]
        ),
        "one_corrected_parent_forward_and_byte_exact_handoff": True,
        "query_fetch_model_token_context_and_wall_caps_unchanged": True,
        "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "historical_per_task_outcome_runtime_routing": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return value


def validate_handoff_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    receipt = copied.get("canonical_column_handoff_receipt")
    parent_stage = copied.get("parent_stage_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    true_flags = (
        "one_corrected_parent_forward_and_byte_exact_handoff",
        "query_fetch_model_token_context_and_wall_caps_unchanged",
    )
    false_flags = (
        "contains_question_column_value_prediction_query_url_page_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "historical_per_task_outcome_runtime_routing",
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
        "mode",
        "canonical_column_handoff_receipt",
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
        or copied.get("role") != HANDOFF_STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("failure_present") is not False
        or copied.get("failure_stage") is not None
        or copied.get("failure_type") is not None
        or copied.get("mode") != BYTE_EXACT_PARENT_HANDOFF
        or not isinstance(receipt, Mapping)
        or validate_handoff_receipt(receipt) != dict(receipt)
        or not isinstance(parent_stage, Mapping)
        or membership_parent.validate_stage_receipt(parent_stage)
        != dict(parent_stage)
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or parent_stage["outer_physical_budget_receipt"] != budget
        or copied.get("parent_runtime_result_payload_sha256")
        != receipt["parent_result_payload_sha256"]
        or not isinstance(copied.get("runtime_result_payload_sha256"), str)
        or len(copied["runtime_result_payload_sha256"]) != 64
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.75 canonical column handoff stage drifted")
    return copied


class _CanonicalColumnVerifier(visible_parent._TaskLocalVerifier):
    """Use one frozen canonicalizer on both sides of the column binding."""

    def prepare_record_proposal(
        self,
        question: str,
        columns: Sequence[str],
        pages: Sequence[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if len(columns) == 1:
            # Preserve the frozen identity-only no-op.  No non-key coordinate
            # exists and no quote-verifier state can be consumed by the editor.
            del question, pages
            return {"v25395_one_column_identity_noop": True}
        grounded = visible_parent.verifier.prepare_record_proposal(
            question, columns, pages
        )
        self._hybrid.grounded_prepared_records = copy.deepcopy(grounded)
        source = self._hybrid.choose_record_source()
        if source == "joint":
            prepared = self._hybrid.prepared_records
            if prepared is None:
                raise ValueError("V2.55.75 joint verifier state is absent")
        else:
            prepared = grounded
        prepared_columns = prepared.get("columns")
        if not isinstance(prepared_columns, Sequence) or isinstance(
            prepared_columns, (str, bytes)
        ):
            raise ValueError("V2.55.75 prepared columns are absent")
        if (
            quote._text(prepared.get("question")) != quote._text(question)
            or quote._safe_columns(tuple(prepared_columns))
            != quote._safe_columns(columns)
        ):
            raise ValueError("V2.55.75 selected verifier state drifted")
        return copy.deepcopy(dict(prepared))


def _isolated_parent(
    projector: schema_parent._TaskLocalProjector,
    hybrid: visible_parent._VisibleMembershipHybridInner,
) -> Callable[..., dict[str, Any]]:
    """Clone the frozen shared parent with only the corrected verifier."""

    local_verifier = _CanonicalColumnVerifier(hybrid)
    local_editor = hybrid_parent._TaskLocalEditor(hybrid)
    empty_namespace = dict(changed_parent._empty_editor.__globals__)
    empty_namespace.update({"verifier": local_verifier, "editor": local_editor})
    empty_editor = types.FunctionType(
        changed_parent._empty_editor.__code__,
        empty_namespace,
        name="v25575_task_local_empty_editor",
        argdefs=changed_parent._empty_editor.__defaults__,
        closure=changed_parent._empty_editor.__closure__,
    )
    empty_editor.__kwdefaults__ = dict(
        changed_parent._empty_editor.__kwdefaults__ or {}
    )
    namespace = dict(changed_parent.run_paired_task.__globals__)
    namespace.update(
        {
            "query_parent": SimpleNamespace(
                projected_plan=projector.projected_plan
            ),
            "verifier": local_verifier,
            "editor": local_editor,
            "_empty_editor": empty_editor,
        }
    )
    cloned = types.FunctionType(
        changed_parent.run_paired_task.__code__,
        namespace,
        name="v25575_task_local_canonical_column_parent",
        argdefs=changed_parent.run_paired_task.__defaults__,
        closure=changed_parent.run_paired_task.__closure__,
    )
    cloned.__kwdefaults__ = dict(
        changed_parent.run_paired_task.__kwdefaults__ or {}
    )
    cloned.__annotations__ = dict(changed_parent.run_paired_task.__annotations__)
    return cloned


def _run_corrected_membership_parent(
    task: Mapping[str, Any],
    *,
    model: cap.HardCappedModelLimiter,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Rebuild the frozen V2.54.01 chain with one local verifier fix."""

    visible = score.validate_visible_task(task)
    if (
        not isinstance(model, cap.HardCappedModelLimiter)
        or model._budget is not budget
        or not isinstance(
            model._inner_limiter, DeadlineAwareGlobalModelSlotLimiter
        )
        or model._synthesis_entry_count != 0
    ):
        raise ValueError("V2.55.75 hard-capped model wiring drifted")
    projector = schema_parent._TaskLocalProjector(visible["question"])
    hybrid = membership_parent._GroundedRecordMembershipHybridInner(
        model._inner_limiter, question=visible["question"]
    )
    hybrid_model = cap.HardCappedModelLimiter(hybrid, budget)
    isolated = _isolated_parent(projector, hybrid)
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
    membership_receipt = visible_parent._receipt(hybrid, hybrid_result)
    membership_result = visible_parent.validate_result(
        visible_parent._wrap_result(
            hybrid_result,
            visible["question"],
            hybrid.visible_members,
            hybrid.membership_source,
            membership_receipt,
        )
    )
    membership_stage = visible_parent._stage_receipt(
        membership_result, hybrid_stage
    )
    record_receipt = membership_parent._receipt(hybrid, membership_result)
    result = membership_parent.validate_result(
        membership_parent._wrap_result(membership_result, record_receipt)
    )
    return result, membership_parent._stage_receipt(result, membership_stage)


def run_task(
    task: Mapping[str, Any],
    *,
    model: cap.HardCappedModelLimiter,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    monotonic: Callable[[], float],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run one corrected parent and preserve the V2.55.69 sealed surface."""

    visible = score.validate_visible_task(task)
    parent_result, parent_stage = _run_corrected_membership_parent(
        visible,
        model=model,
        searches=searches,
        limits=limits,
        budget=budget,
        monotonic=monotonic,
    )
    raw_columns, canonical_columns = _canonical_column_nonadmission(
        parent_result["prediction"]
    )
    if raw_columns is not None and canonical_columns is not None:
        result = validate_handoff_result(
            _handoff_result_value(parent_result)
        )
        return result, validate_handoff_stage_receipt(
            _handoff_stage_value(result, parent_stage)
        )
    result = totality.build_result(parent_result, visible["question"])
    return result, totality._stage_receipt(result, parent_stage)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    if (
        isinstance(value, Mapping)
        and value.get("role") == HANDOFF_ROLE
        and value.get("policy_id") == POLICY_ID
    ):
        return validate_handoff_result(value)
    return totality.validate_result(value)


def validate_stage_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    if (
        isinstance(value, Mapping)
        and value.get("role") == HANDOFF_STAGE_RECEIPT_ROLE
        and value.get("policy_id") == POLICY_ID
    ):
        return validate_handoff_stage_receipt(value)
    return totality.validate_stage_receipt(value)


def validate_runtime_pair(
    result: Mapping[str, Any], stage: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Validate one same-branch result/stage pair and bind both payloads."""

    checked = validate_result(result)
    checked_stage = validate_stage_receipt(stage)
    handoff = checked.get("role") == HANDOFF_ROLE
    if handoff is not (checked_stage.get("role") == HANDOFF_STAGE_RECEIPT_ROLE):
        raise ValueError("V2.55.75 result/stage branch mismatch")
    if (
        checked_stage["runtime_result_payload_sha256"]
        != checked["result_payload_sha256"]
        or checked_stage["parent_runtime_result_payload_sha256"]
        != checked["private_parent_result_payload_sha256"]
    ):
        raise ValueError("V2.55.75 result/stage payload binding drifted")
    return checked, checked_stage


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "output_result_policy_id": totality.POLICY_ID,
        "corrected_parent_policy_id": membership_parent.POLICY_ID,
        "runtime_input_keys": ["opaque_id", "question"],
        "arms": list(ARMS),
        "one_corrected_parent_forward_only": True,
        "prepared_and_requested_columns_use_same_v25065_safe_columns": True,
        "invalid_duplicate_overlong_empty_or_forbidden_columns_fail_closed": True,
        "question_binding_source_priority_quote_verification_and_editor_unchanged": True,
        "v25401_result_and_stage_schemas_unchanged": True,
        "v25569_projection_handoff_result_and_stage_schemas_unchanged": True,
        "canonical_column_drift_has_narrow_byte_exact_handoff_schema": True,
        "maximum_physical_queries": 4,
        "maximum_physical_fetches": 14,
        "normal_path_model_forwards": 3,
        "additional_model_search_fetch_token_context_wall_or_network_budget": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "historical_per_task_outcome_runtime_routing": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "ARMS",
    "BYTE_EXACT_PARENT_HANDOFF",
    "CANONICAL_PROJECTION",
    "CANDIDATE_ARM",
    "CANONICAL_COLUMN_NONADMISSION",
    "CONTROL_ARM",
    "HANDOFF_RECEIPT_ROLE",
    "HANDOFF_ROLE",
    "HANDOFF_STAGE_RECEIPT_ROLE",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "integration_contract",
    "run_task",
    "validate_handoff_receipt",
    "validate_handoff_result",
    "validate_handoff_stage_receipt",
    "validate_result",
    "validate_runtime_pair",
    "validate_stage_receipt",
]
