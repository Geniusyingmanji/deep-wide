"""Visible-only legacy-query compatibility for V2.51.19.

V2.51.21 exposed a boundary mismatch after its first search/fetch wave: the
parent visible-only planner may retain markup from the visible question in a
fallback query, while V2.51.17 applies its stricter model-generated-query
grammar to all four already-authorized legacy queries.  This append-only
wrapper rewrites only the first plan envelope.  It removes visible markup,
unsafe controls and forbidden search/control syntax, bounds seed queries, and
lets the frozen visible-only parent complete the four-query vector.  If the
first model effect or JSON parsing fails, one seed is deterministically derived
from the visible question.

The grounded-plan model output is not relaxed or rewritten.  V2.51.17 still
requires every nonvisible pivot/target to occur verbatim in same-forward first
wave pages and still validates its two generated queries with the original
strict grammar.  No query, target, page, prediction, credential, label, gold,
evaluator result, score, reward, or historical result is persisted in the
content-free stage receipt.  No model/search/fetch/token/context/wall budget is
added and entropy/information gain assigns no signed credit.
"""

from __future__ import annotations

import copy
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v25110_exact_visible_schema as schema
from . import v25117_grounded_target_record_plan as target_plan
from . import v25119_grounded_target_record_paired_runtime as parent
from .clients import ModelRequestError, parse_json_object
from .v24259_deterministic_table_normalizer import _replace_text
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25123_visible_legacy_query_compatible_paired_runtime_v1"
ROLE = "v25123_visible_legacy_query_compatible_paired_runtime_result"
STAGE_RECEIPT_ROLE = "v25123_content_free_visible_legacy_query_stage_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES
MAXIMUM_SEED_QUERY_CHARACTERS = 240

_TAG = re.compile(r"</?[A-Za-z][^<>\r\n]{0,160}>")
_URL = re.compile(r"(?i)(?:https?://|www\.)\S+")
_OUTPUT_CLAUSE = re.compile(
    r"(?i)\b(?:return exactly|columns exactly|output format|please output)\b"
)
_UNSAFE = frozenset("\x00\r\n<>`{}[]")


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _truncate(value: str, maximum: int) -> str:
    text = value[:maximum]
    if len(value) <= maximum or " " not in text:
        return text
    prefix = text.rsplit(" ", 1)[0].strip()
    return prefix or text


def compatible_visible_query(value: object) -> str | None:
    """Project one visible/same-pass seed into V2.51.17 legacy grammar."""

    if not isinstance(value, str):
        return None
    text = unicodedata.normalize("NFKC", value)
    text = _TAG.sub(" ", text)
    text = _URL.sub(" ", text)
    text = "".join(" " if character in _UNSAFE else character for character in text)
    text = target_plan._FORBIDDEN.sub(" ", text)
    text = " ".join(text.split()).strip(" |:;,，。；：")
    text = _truncate(text, MAXIMUM_SEED_QUERY_CHARACTERS)
    return target_plan._safe_query(text)


def _visible_fallback(question: str) -> str:
    prefix = _OUTPUT_CLAUSE.split(str(question), maxsplit=1)[0]
    for raw in (prefix, question, "public Python package official source"):
        value = compatible_visible_query(raw)
        if value is not None:
            return value
    raise ValueError("V2.51.23 could not derive a safe visible query seed")


def _query_seeds(plan: Mapping[str, Any], question: str) -> tuple[list[str], dict[str, Any]]:
    raw = plan.get("queries")
    values = list(raw) if isinstance(raw, list) else []
    output: list[str] = []
    seen: set[str] = set()
    transformed = 0
    input_strings = 0
    for item in values[:4]:
        if not isinstance(item, str):
            continue
        input_strings += 1
        value = compatible_visible_query(item)
        if value is None or value.casefold() in seen:
            transformed += 1
            continue
        transformed += int(value != " ".join(item.split()).strip(" |:;,，。；："))
        output.append(value)
        seen.add(value.casefold())
    fallback = False
    if not output:
        output = [_visible_fallback(question)]
        fallback = True
    return output, {
        "input_provider_query_string_count": input_strings,
        "compatible_provider_query_seed_count": 0 if fallback else len(output),
        "transformed_or_rejected_provider_query_count": transformed,
        "emitted_query_seed_count": len(output),
        "visible_fallback_query_seed_used": fallback,
    }


class VisibleLegacyQueryStageModel(DeadlineAwareGlobalModelSlotLimiter):
    """Transparent bounded proxy that repairs only the first plan envelope."""

    def __init__(
        self,
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        question: str,
    ) -> None:
        if not isinstance(bounded, DeadlineAwareGlobalModelSlotLimiter):
            raise TypeError("V2.51.23 requires a bounded global model limiter")
        columns = schema.extract_exact_visible_columns(question)
        if not columns:
            raise ValueError("V2.51.23 visible exact schema is absent or ambiguous")
        self._bounded = bounded
        self._question = str(question)
        self._columns = tuple(columns)
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
        seeds, observation = _query_seeds(plan, self._question)
        self.query_observation = observation
        plan["columns"] = list(self._columns)
        plan["queries"] = seeds
        return _replace_text(
            value,
            json.dumps(plan, ensure_ascii=False, separators=(",", ":")),
        )


def _stage_receipt(
    model: VisibleLegacyQueryStageModel,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    observation = model.query_observation
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": parent.ROLE,
        "parent_policy_id": parent.POLICY_ID,
        "parent_result_payload_sha256": str(parent_result["result_payload_sha256"]),
        "logical_model_call_count": model.logical_call_count,
        "visible_schema_column_count": model.visible_schema_column_count,
        "input_provider_query_string_count": int(
            observation["input_provider_query_string_count"]
        ),
        "compatible_provider_query_seed_count": int(
            observation["compatible_provider_query_seed_count"]
        ),
        "transformed_or_rejected_provider_query_count": int(
            observation["transformed_or_rejected_provider_query_count"]
        ),
        "emitted_query_seed_count": int(observation["emitted_query_seed_count"]),
        "plan_model_effect_failed": model.plan_model_effect_failure_type is not None,
        "plan_model_effect_failure_type": model.plan_model_effect_failure_type,
        "plan_transport_failed": model.plan_transport_failed,
        "plan_output_validation_failed": model.plan_output_validation_failure_type
        is not None,
        "plan_output_validation_failure_type": model.plan_output_validation_failure_type,
        "visible_fallback_query_seed_used": bool(
            observation["visible_fallback_query_seed_used"]
        ),
        "first_plan_envelope_only_rewritten": True,
        "visible_legacy_query_seed_markup_controls_urls_and_forbidden_syntax_removed": True,
        "visible_legacy_query_seed_character_cap": MAXIMUM_SEED_QUERY_CHARACTERS,
        "frozen_parent_completes_four_query_vector": True,
        "grounded_plan_output_and_strict_query_grammar_unchanged": True,
        "all_nonvisible_targets_still_require_verbatim_first_wave_grounding": True,
        "additional_model_search_fetch_token_context_wall_or_network_budget": False,
        "contains_question_query_target_authority_column_url_title_page_prediction_answer_hash_opaque_id_or_credential": False,
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
    count_fields = (
        "logical_model_call_count",
        "visible_schema_column_count",
        "input_provider_query_string_count",
        "compatible_provider_query_seed_count",
        "transformed_or_rejected_provider_query_count",
        "emitted_query_seed_count",
        "visible_legacy_query_seed_character_cap",
    )
    nullable = (
        "plan_model_effect_failure_type",
        "plan_output_validation_failure_type",
    )
    bool_fields = (
        "plan_model_effect_failed",
        "plan_transport_failed",
        "plan_output_validation_failed",
        "visible_fallback_query_seed_used",
    )
    true_flags = (
        "first_plan_envelope_only_rewritten",
        "visible_legacy_query_seed_markup_controls_urls_and_forbidden_syntax_removed",
        "frozen_parent_completes_four_query_vector",
        "grounded_plan_output_and_strict_query_grammar_unchanged",
        "all_nonvisible_targets_still_require_verbatim_first_wave_grounding",
    )
    false_flags = (
        "additional_model_search_fetch_token_context_wall_or_network_budget",
        "contains_question_query_target_authority_column_url_title_page_prediction_answer_hash_opaque_id_or_credential",
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
        *count_fields,
        *nullable,
        *bool_fields,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_role") != parent.ROLE
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_fields
        )
        or not 1 <= copied["logical_model_call_count"] <= 4
        or not 1 <= copied["visible_schema_column_count"] <= 20
        or copied["input_provider_query_string_count"] > 4
        or copied["compatible_provider_query_seed_count"]
        > copied["input_provider_query_string_count"]
        or copied["transformed_or_rejected_provider_query_count"]
        > copied["input_provider_query_string_count"]
        or not 1 <= copied["emitted_query_seed_count"] <= 4
        or copied["visible_legacy_query_seed_character_cap"]
        != MAXIMUM_SEED_QUERY_CHARACTERS
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or any(
            copied.get(name) is not None
            and (
                not isinstance(copied[name], str)
                or not copied[name]
                or len(copied[name]) > 128
            )
            for name in nullable
        )
        or copied["plan_model_effect_failed"]
        is not (copied["plan_model_effect_failure_type"] is not None)
        or copied["plan_transport_failed"]
        is not (copied["plan_model_effect_failure_type"] == "ModelRequestError")
        or copied["plan_output_validation_failed"]
        is not (copied["plan_output_validation_failure_type"] is not None)
        or copied["visible_fallback_query_seed_used"]
        is not (
            copied["compatible_provider_query_seed_count"] == 0
            and copied["emitted_query_seed_count"] == 1
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.23 visible legacy-query stage receipt drifted")
    return copied


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: score.ScoreFirstLimits,
    arm_order: Sequence[str] | None = None,
    monotonic: Any = None,
) -> dict[str, Any]:
    visible = score.validate_visible_task(task)
    stage_model = VisibleLegacyQueryStageModel(model, visible["question"])
    kwargs: dict[str, Any] = {
        "model": stage_model,
        "searches": searches,
        "limits": limits,
        "arm_order": arm_order,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    parent_result = parent.validate_result(parent.run_paired_task(visible, **kwargs))
    value = copy.deepcopy(parent_result)
    value["role"] = ROLE
    value["policy_id"] = POLICY_ID
    value["stage_failure_accounting"] = _stage_receipt(stage_model, parent_result)
    value.pop("result_payload_sha256", None)
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    stage = copied.get("stage_failure_accounting")
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(stage, Mapping)
        or validate_stage_receipt(stage) != dict(stage)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.23 result envelope drifted")
    parent_value = copy.deepcopy(copied)
    parent_value.pop("stage_failure_accounting")
    parent_value["role"] = parent.ROLE
    parent_value["policy_id"] = parent.POLICY_ID
    parent_value["result_payload_sha256"] = stage["parent_result_payload_sha256"]
    parent_checked = parent.validate_result(parent_value)
    if (
        stage["logical_model_call_count"]
        != parent_checked["content_free_receipt"]["physical_model_logical_call_count"]
        or stage["visible_schema_column_count"]
        != parent_checked["grounded_plan_receipt"]["visible_column_count"]
        or stage["plan_model_effect_failed"]
        and parent_checked["cost"]["model"]["requests"] == 0
    ):
        raise ValueError("V2.51.23 stage-to-parent binding drifted")
    return copied


validate_parent_receipt = parent.validate_receipt
validate_parent_result = parent.validate_result


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "FIRST_PHASE",
    "PHASES",
    "POLICY_ID",
    "ROLE",
    "SECOND_PHASE",
    "STAGE_RECEIPT_ROLE",
    "VisibleLegacyQueryStageModel",
    "compatible_visible_query",
    "run_paired_task",
    "validate_parent_receipt",
    "validate_parent_result",
    "validate_result",
    "validate_stage_receipt",
]
