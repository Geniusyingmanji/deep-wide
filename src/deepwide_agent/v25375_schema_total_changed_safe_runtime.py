"""Schema-total adapter for the V2.53.70 changed-safe runtime.

The frozen V2.53.70 runtime requires one exact visible column declaration
before its first provider/search effect.  A content-free pass over the fixed
DeepWideBench visible task vector found that this boundary is reachable for
194/220 questions and deterministically rejects the remaining 26 before any
retrieval.  This append-only successor changes only that pre-effect schema
seam:

* the frozen exact parser keeps first priority;
* the already-audited conservative expanded explicit parser is second;
* otherwise safe columns from the same planning effect are used; and
* an absent/invalid planning effect falls back to the generic two-column
  ``Result | Value`` key/value schema required by the changed-safe editor,
  keeping the task terminal without inventing task-specific fields.

V2.53.70 is executed through a task-local cloned function namespace, so no
module global is patched and concurrent tasks cannot observe one another's
schema projector.  The scored prediction is the changed-safe candidate.  The
shared control remains only inside the private runtime result/receipt.  Query,
fetch, model, token, context, and wall limits are unchanged.  Runtime inputs
remain exactly ``opaque_id`` and ``question`` plus injected same-forward
clients.  No benchmark label, mapping, gold, evaluator, score, reward,
history, credential, filesystem, environment, process, or network capability
is introduced.  Entropy/information gain remains shadow-only and assigns no
signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import types
from collections.abc import Callable, Mapping, Sequence
from types import SimpleNamespace
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25110_exact_visible_schema as exact_schema
from . import v25117_grounded_target_record_plan as target_plan
from . import v25123_visible_legacy_query_compatible_runtime as compatibility
from . import v25134_schema_total_causal_salience_runtime as schema_total
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25370_shared_synthesis_changed_safe_runtime as parent
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24675_expanded_visible_schema import extract_expanded_visible_columns


POLICY_ID = "v25375_schema_total_changed_safe_runtime_v1"
ROLE = "v25375_schema_total_changed_safe_runtime_result"
STAGE_RECEIPT_ROLE = "v25375_content_free_schema_total_changed_safe_stage_receipt"
SCHEMA_RECEIPT_ROLE = "v25375_content_free_schema_totality_receipt"
PHASES = parent.PHASES
CONTROL_ARM = parent.CONTROL_ARM
CANDIDATE_ARM = parent.CANDIDATE_ARM
SCHEMA_SOURCES = frozenset(
    {"exact_visible", "expanded_visible", "provider_plan", "generic_result"}
)


class ProductionOnlyStageError(RuntimeError):
    """Finite outer signal accepted by the fixed-denominator runner."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        self.stage_receipt = validate_stage_receipt(receipt)
        super().__init__("V2.53.75 schema-total changed-safe stage failed")


def _total_columns(
    plan: Mapping[str, Any], question: str
) -> tuple[tuple[str, ...], str]:
    """Choose columns from visible text, same-effect plan, or safe fallback."""

    exact = exact_schema.extract_exact_visible_columns(question)
    expanded = extract_expanded_visible_columns(question)
    if exact:
        return tuple(exact), "exact_visible"
    if expanded:
        return tuple(expanded), "expanded_visible"
    columns, source = schema_total._total_columns(plan, question)
    if source not in {"provider_plan", "generic_result"}:
        raise ValueError("V2.53.75 schema hierarchy drifted")
    if source == "generic_result":
        columns = ("Result", "Value")
    return tuple(columns), source


def projected_plan(
    plan: Mapping[str, Any], question: str, limits: score.ScoreFirstLimits
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Return a downstream-safe four-query plan and its schema source."""

    seeds, observation = compatibility._query_seeds(plan, question)
    columns, source = _total_columns(plan, question)
    value = dict(plan)
    value["columns"] = list(columns)
    value["queries"] = seeds
    completed = exact_schema.validated_exact_plan(value, question, limits)
    queries = list(completed["queries"])
    if (
        tuple(completed["columns"]) != columns
        or len(queries) != limits.search_queries
        or any(target_plan._safe_query(query) != query for query in queries)
    ):
        raise ValueError("V2.53.75 projected plan violates downstream contract")
    return completed, observation, source


class _TaskLocalProjector:
    """One task's stateful facade used only by its cloned parent function."""

    def __init__(self, question: str) -> None:
        self.question = str(question)
        self.sources: list[str] = []
        self.column_counts: list[int] = []

    def projected_plan(
        self,
        plan: Mapping[str, Any],
        question: str,
        limits: score.ScoreFirstLimits,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if str(question) != self.question:
            raise ValueError("V2.53.75 task-local projector question drifted")
        completed, observation, source = projected_plan(plan, question, limits)
        self.sources.append(source)
        self.column_counts.append(len(completed["columns"]))
        return completed, observation


def _isolated_parent(projector: _TaskLocalProjector) -> Callable[..., dict[str, Any]]:
    namespace = dict(parent.run_paired_task.__globals__)
    namespace["query_parent"] = SimpleNamespace(
        projected_plan=projector.projected_plan
    )
    cloned = types.FunctionType(
        parent.run_paired_task.__code__,
        namespace,
        name="v25375_task_local_schema_total_changed_safe_parent",
        argdefs=parent.run_paired_task.__defaults__,
        closure=parent.run_paired_task.__closure__,
    )
    cloned.__kwdefaults__ = dict(parent.run_paired_task.__kwdefaults__ or {})
    cloned.__annotations__ = dict(parent.run_paired_task.__annotations__)
    return cloned


def _schema_receipt(projector: _TaskLocalProjector, question: str) -> dict[str, Any]:
    if not projector.sources or len(projector.sources) != len(projector.column_counts):
        raise ValueError("V2.53.75 schema projection trace is absent")
    exact = exact_schema.extract_exact_visible_columns(question)
    expanded = extract_expanded_visible_columns(question)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": SCHEMA_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "projection_count": len(projector.sources),
        "pre_effect_schema_source": projector.sources[0],
        "selected_schema_source": projector.sources[-1],
        "selected_column_count": projector.column_counts[-1],
        "exact_visible_schema_available": bool(exact),
        "expanded_visible_schema_incremental": bool(not exact and expanded),
        "provider_or_generic_schema_selected": projector.sources[-1]
        in {"provider_plan", "generic_result"},
        "frozen_exact_schema_preserved_when_nonempty": True,
        "expanded_parser_is_explicit_declaration_only": True,
        "provider_columns_are_from_same_planning_effect": True,
        "generic_result_is_last_resort_only": True,
        "task_local_function_namespace": True,
        "module_global_projector_mutated": False,
        "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_schema_receipt(value)


def validate_schema_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    source = copied.get("selected_schema_source")
    count = copied.get("selected_column_count")
    exact = copied.get("exact_visible_schema_available")
    expanded = copied.get("expanded_visible_schema_incremental")
    true_flags = (
        "frozen_exact_schema_preserved_when_nonempty",
        "expanded_parser_is_explicit_declaration_only",
        "provider_columns_are_from_same_planning_effect",
        "generic_result_is_last_resort_only",
        "task_local_function_namespace",
    )
    false_flags = (
        "module_global_projector_mutated",
        "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "projection_count",
        "pre_effect_schema_source",
        "selected_schema_source",
        "selected_column_count",
        "exact_visible_schema_available",
        "expanded_visible_schema_incremental",
        "provider_or_generic_schema_selected",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != SCHEMA_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or isinstance(copied.get("projection_count"), bool)
        or not isinstance(copied.get("projection_count"), int)
        or not 1 <= copied["projection_count"] <= 2
        or copied.get("pre_effect_schema_source") not in SCHEMA_SOURCES
        or source not in SCHEMA_SOURCES
        or isinstance(count, bool)
        or not isinstance(count, int)
        or not 1 <= count <= 20
        or not isinstance(exact, bool)
        or not isinstance(expanded, bool)
        or exact and expanded
        or exact and source != "exact_visible"
        or expanded and source != "expanded_visible"
        or copied.get("provider_or_generic_schema_selected")
        is not (source in {"provider_plan", "generic_result"})
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.75 schema receipt drifted")
    return copied


def _stage_receipt(
    parent_result: Mapping[str, Any], schema_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    schema = validate_schema_receipt(schema_receipt)
    budget = cap.validate_budget_receipt(
        checked["content_free_receipt"]["outer_physical_budget_receipt"]
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "failure_present": False,
        "failure_stage": None,
        "failure_type": None,
        "schema_totality_receipt": copy.deepcopy(schema),
        "parent_content_free_receipt": copy.deepcopy(
            checked["content_free_receipt"]
        ),
        "parent_result_payload_sha256": checked["result_payload_sha256"],
        "outer_physical_budget_receipt": copy.deepcopy(budget),
        "scored_prediction_is_changed_safe_candidate": True,
        "shared_control_retained_only_in_private_runtime_result": True,
        "query_fetch_model_token_context_and_wall_caps_unchanged": True,
        "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential": False,
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
    schema = copied.get("schema_totality_receipt")
    parent_receipt = copied.get("parent_content_free_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    true_flags = (
        "scored_prediction_is_changed_safe_candidate",
        "shared_control_retained_only_in_private_runtime_result",
        "query_fetch_model_token_context_and_wall_caps_unchanged",
    )
    false_flags = (
        "contains_question_column_query_url_page_prediction_answer_opaque_id_or_credential",
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
        "schema_totality_receipt",
        "parent_content_free_receipt",
        "parent_result_payload_sha256",
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
        or not isinstance(schema, Mapping)
        or validate_schema_receipt(schema) != dict(schema)
        or not isinstance(parent_receipt, Mapping)
        or parent.validate_receipt(parent_receipt) != dict(parent_receipt)
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or parent_receipt["outer_physical_budget_receipt"] != budget
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.75 stage receipt drifted")
    return copied


def _wrap_result(
    parent_result: Mapping[str, Any], schema_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    checked = parent.validate_result(parent_result)
    schema = validate_schema_receipt(schema_receipt)
    candidate = checked["predictions"][CANDIDATE_ARM]
    control = checked["predictions"][CONTROL_ARM]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": checked["opaque_id"],
        "status": "terminal",
        "prediction": candidate,
        "prediction_sha256": hashlib.sha256(candidate.encode()).hexdigest(),
        "prediction_kind": (
            "model_generated"
            if checked["model_success"][CANDIDATE_ARM]
            else "fallback"
        ),
        "control_prediction_sha256": hashlib.sha256(control.encode()).hexdigest(),
        "prediction_changed": checked["prediction_changed"],
        "changed_safe_coordinate_count": checked[
            "changed_safe_coordinate_count"
        ],
        "attributable_prediction_change": checked[
            "attributable_prediction_change"
        ],
        "schema_totality_receipt": copy.deepcopy(schema),
        "private_parent_result": copy.deepcopy(checked),
        "private_parent_result_payload_sha256": checked["result_payload_sha256"],
        "cost": copy.deepcopy(checked["cost"]),
        "scored_prediction_is_changed_safe_candidate": True,
        "shared_control_not_exported_as_scored_prediction": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    raw = copied.get("private_parent_result")
    schema = copied.get("schema_totality_receipt")
    if not isinstance(raw, Mapping) or not isinstance(schema, Mapping):
        raise ValueError("V2.53.75 private parent result is absent")
    expected = _wrap_result(raw, schema)
    if copied != expected:
        raise ValueError("V2.53.75 result adapter drifted")
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
    projector = _TaskLocalProjector(visible["question"])
    isolated = _isolated_parent(projector)
    parent_result = parent.validate_result(
        isolated(
            visible,
            model=model,
            searches=searches,
            limits=limits,
            budget=budget,
            monotonic=monotonic,
        )
    )
    schema_receipt = _schema_receipt(projector, visible["question"])
    result = validate_result(_wrap_result(parent_result, schema_receipt))
    stage = _stage_receipt(parent_result, schema_receipt)
    return result, stage


__all__ = [
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "PHASES",
    "POLICY_ID",
    "ProductionOnlyStageError",
    "ROLE",
    "SCHEMA_RECEIPT_ROLE",
    "SCHEMA_SOURCES",
    "STAGE_RECEIPT_ROLE",
    "projected_plan",
    "run_task",
    "validate_result",
    "validate_schema_receipt",
    "validate_stage_receipt",
]
