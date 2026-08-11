"""Schema-total successor for the V2.51.27 causal-salience runtime.

V2.51.30 showed 26 zero-effect outer failures because the legacy-query stage
required one narrow exact visible-column syntax before the first model call.
This append-only successor changes only that schema seam.  Explicit visible
columns retain priority; otherwise a safe column vector from the same planning
effect is used; if that effect is absent or invalid, a generic one-column
``Result`` schema keeps the task terminal instead of raising before effects.

The grounded retrieval, paired synthesis, evidence salience, causal gate,
identity handoff, query/fetch/model/context/token/wall caps, and validators are
otherwise inherited unchanged.  Runtime input remains only ``opaque_id`` and
``question`` plus injected same-forward clients.  No label, mapping, gold,
evaluator, score, reward, history, credential, file, environment, process, or
network capability is introduced.  Entropy/information gain assigns no
signed credit and this build-only module authorizes no benchmark launch.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25110_exact_visible_schema as schema
from . import v25119_grounded_target_record_paired_runtime as paired
from . import v25123_visible_legacy_query_compatible_runtime as legacy
from . import v25127_causally_coupled_target_record_runtime as causal
from .clients import ModelRequestError, parse_json_object
from .v24259_deterministic_table_normalizer import _replace_text
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25134_schema_total_causal_salience_runtime_v1"
ROLE = "v25134_schema_total_causal_salience_runtime_result"
RECEIPT_ROLE = "v25134_content_free_schema_totality_receipt"
ARMS = causal.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = causal.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES
SCHEMA_SOURCES = frozenset({"exact_visible", "provider_plan", "generic_result"})


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _total_columns(
    plan: Mapping[str, Any], question: str
) -> tuple[tuple[str, ...], str]:
    """Choose a safe nonempty column vector from visible/same-effect input."""

    exact = schema.extract_exact_visible_columns(question)
    if exact:
        return tuple(exact), "exact_visible"
    raw = plan.get("columns")
    provider = (
        [score._normalize_text(item) for item in raw]
        if isinstance(raw, list)
        else []
    )
    provider = [item for item in provider if item and len(item) <= 80][:20]
    if provider and len(
        {score._normalize_column(item) for item in provider}
    ) == len(provider):
        return tuple(provider), "provider_plan"
    return ("Result",), "generic_result"


class SchemaTotalVisibleLegacyQueryStageModel(DeadlineAwareGlobalModelSlotLimiter):
    """Transparent plan proxy with a total, visible-only schema hierarchy."""

    def __init__(
        self,
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        question: str,
    ) -> None:
        if not isinstance(bounded, DeadlineAwareGlobalModelSlotLimiter):
            raise TypeError("V2.51.34 requires a bounded global model limiter")
        self._bounded = bounded
        self._question = str(question)
        initial, source = _total_columns({}, self._question)
        self._columns = initial
        self.schema_source = source
        self.logical_call_count = 0
        self.plan_model_effect_failure_type: str | None = None
        self.plan_transport_failed = False
        self.plan_output_validation_failure_type: str | None = None
        self.query_observation: dict[str, Any] = {
            "input_provider_query_string_count": 0,
            "compatible_provider_query_seed_count": 0,
            "transformed_or_rejected_provider_query_count": 0,
            "emitted_query_seed_count": 0,
            "visible_fallback_query_seed_used": False,
        }

    def __getattr__(self, name: str) -> Any:
        return getattr(self._bounded, name)

    @property
    def visible_schema_column_count(self) -> int:
        return len(self._columns)

    def remaining_effect_seconds(self) -> float:
        return float(self._bounded.remaining_effect_seconds())

    def receipt(self) -> dict[str, Any]:
        return self._bounded.receipt()

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        self.logical_call_count += 1
        if self.logical_call_count != 1:
            return self._bounded.complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        try:
            value = self._bounded.complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
            try:
                plan = parse_json_object(score._model_text(value))
            except (TypeError, ValueError) as exc:
                plan = {}
                self.plan_output_validation_failure_type = _safe_failure(exc)
        except BaseException as exc:
            plan = {}
            value = ""
            self.plan_model_effect_failure_type = _safe_failure(exc)
            self.plan_transport_failed = isinstance(exc, ModelRequestError)
        seeds, observation = legacy._query_seeds(plan, self._question)
        self.query_observation = observation
        columns, source = _total_columns(plan, self._question)
        self._columns = columns
        self.schema_source = source
        plan["columns"] = list(columns)
        plan["queries"] = seeds
        return _replace_text(
            value,
            json.dumps(plan, ensure_ascii=False, separators=(",", ":")),
        )


def _schema_receipt(
    stage_model: SchemaTotalVisibleLegacyQueryStageModel,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    source = stage_model.schema_source
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": causal.ROLE,
        "parent_policy_id": causal.POLICY_ID,
        "parent_result_payload_sha256": str(parent_result["result_payload_sha256"]),
        "schema_source": source,
        "effective_column_count": stage_model.visible_schema_column_count,
        "exact_visible_schema_used": source == "exact_visible",
        "provider_plan_schema_used": source == "provider_plan",
        "generic_result_schema_used": source == "generic_result",
        "plan_model_effect_failed": stage_model.plan_model_effect_failure_type
        is not None,
        "plan_output_validation_failed": stage_model.plan_output_validation_failure_type
        is not None,
        "schema_nonempty_before_retrieval": True,
        "schema_absence_never_raises_outer_failure": True,
        "explicit_visible_schema_precedence_preserved": True,
        "provider_columns_are_same_effect_and_safely_normalized": True,
        "generic_result_is_last_resort_only": True,
        "grounded_retrieval_pairing_salience_and_causal_projection_unchanged": True,
        "query_fetch_model_context_token_wall_and_network_caps_unchanged": True,
        "contains_question_column_query_url_title_page_target_prediction_answer_opaque_id_or_credential": False,
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
    source = copied.get("schema_source")
    booleans = (
        "exact_visible_schema_used",
        "provider_plan_schema_used",
        "generic_result_schema_used",
        "plan_model_effect_failed",
        "plan_output_validation_failed",
    )
    true_flags = (
        "schema_nonempty_before_retrieval",
        "schema_absence_never_raises_outer_failure",
        "explicit_visible_schema_precedence_preserved",
        "provider_columns_are_same_effect_and_safely_normalized",
        "generic_result_is_last_resort_only",
        "grounded_retrieval_pairing_salience_and_causal_projection_unchanged",
        "query_fetch_model_context_token_wall_and_network_caps_unchanged",
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
        "parent_role",
        "parent_policy_id",
        "parent_result_payload_sha256",
        "schema_source",
        "effective_column_count",
        *booleans,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_role") != causal.ROLE
        or copied.get("parent_policy_id") != causal.POLICY_ID
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or source not in SCHEMA_SOURCES
        or isinstance(copied.get("effective_column_count"), bool)
        or not isinstance(copied.get("effective_column_count"), int)
        or not 1 <= copied["effective_column_count"] <= 20
        or any(not isinstance(copied.get(name), bool) for name in booleans)
        or sum(
            int(copied[name])
            for name in (
                "exact_visible_schema_used",
                "provider_plan_schema_used",
                "generic_result_schema_used",
            )
        )
        != 1
        or copied["exact_visible_schema_used"] is not (source == "exact_visible")
        or copied["provider_plan_schema_used"] is not (source == "provider_plan")
        or copied["generic_result_schema_used"] is not (source == "generic_result")
        or copied["plan_model_effect_failed"]
        and copied["schema_source"] == "provider_plan"
        or copied["plan_output_validation_failed"]
        and copied["schema_source"] == "provider_plan"
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.34 schema-totality receipt drifted")
    return copied


def _legacy_parent(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: score.ScoreFirstLimits,
    arm_order: Sequence[str],
    monotonic: Any = None,
) -> tuple[dict[str, Any], SchemaTotalVisibleLegacyQueryStageModel]:
    visible = score.validate_visible_task(task)
    stage_model = SchemaTotalVisibleLegacyQueryStageModel(
        model, visible["question"]
    )
    kwargs: dict[str, Any] = {
        "model": stage_model,
        "searches": searches,
        "limits": limits,
        "arm_order": arm_order,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    core_result = paired.validate_result(paired.run_paired_task(visible, **kwargs))
    value = copy.deepcopy(core_result)
    value["role"] = legacy.ROLE
    value["policy_id"] = legacy.POLICY_ID
    value["stage_failure_accounting"] = legacy._stage_receipt(
        stage_model, core_result
    )
    value.pop("result_payload_sha256", None)
    value["result_payload_sha256"] = payload_sha256(value)
    return legacy.validate_result(value), stage_model


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: score.ScoreFirstLimits,
    arm_order: Sequence[str] | None = None,
    monotonic: Any = None,
) -> dict[str, Any]:
    order = tuple(
        arm_order or paired._arm_order(str(task.get("opaque_id") or ""))
    )
    if len(order) != 2 or set(order) != set(ARMS):
        raise ValueError("V2.51.34 arm order drifted")
    salience_model = causal.CausalSalienceModel(
        model,
        first_wave_search=searches[FIRST_PHASE],
        arm_order=order,
    )
    parent_result, stage_model = _legacy_parent(
        task,
        model=salience_model,
        searches=searches,
        limits=limits,
        arm_order=order,
        monotonic=monotonic,
    )
    causal_result = causal._project(
        parent_result, salience_model.content_free_receipt()
    )
    value = copy.deepcopy(causal_result)
    value["role"] = ROLE
    value["policy_id"] = POLICY_ID
    value["schema_totality_receipt"] = _schema_receipt(
        stage_model, causal_result
    )
    value.pop("result_payload_sha256", None)
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    receipt = copied.get("schema_totality_receipt")
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(receipt, Mapping)
        or validate_schema_receipt(receipt) != dict(receipt)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.34 result envelope drifted")
    parent_value = copy.deepcopy(copied)
    parent_value.pop("schema_totality_receipt")
    parent_value["role"] = causal.ROLE
    parent_value["policy_id"] = causal.POLICY_ID
    parent_value["result_payload_sha256"] = receipt[
        "parent_result_payload_sha256"
    ]
    parent_checked = causal.validate_result(parent_value)
    stage = parent_checked["stage_failure_accounting"]
    if (
        receipt["effective_column_count"]
        != parent_checked["grounded_plan_receipt"]["visible_column_count"]
        or receipt["effective_column_count"] != stage["visible_schema_column_count"]
        or receipt["plan_model_effect_failed"]
        is not stage["plan_model_effect_failed"]
        or receipt["plan_output_validation_failed"]
        is not stage["plan_output_validation_failed"]
        or parent_checked[
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        ]
        is not False
        or parent_checked["benchmark_launch_or_evaluator_authorized"] is not False
    ):
        raise ValueError("V2.51.34 schema-to-parent binding drifted")
    return copied


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "FIRST_PHASE",
    "PHASES",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "SCHEMA_SOURCES",
    "SECOND_PHASE",
    "SchemaTotalVisibleLegacyQueryStageModel",
    "run_paired_task",
    "validate_result",
    "validate_schema_receipt",
]
