"""Concurrency-safe runtime integration for partial-field grounded facts.

The frozen V2.53.54 runtime calls the model four times: visible plan, joint
grounded plan/fact proposal, and two matched syntheses.  This append-only
successor wraps only per-task injected clients.  It captures the same first
wave fetch result already returned to the parent and, after the second model
response, removes fields that fail V2.53.60 while preserving the four plan
members.  The frozen V2.53.46 bootstrap then independently re-verifies every
remaining record and builds the treatment exactly as before.

There is no module-global mutation, so concurrent tasks cannot share pages or
responses.  Page, unique-verbatim-quote, row identity, and same-coordinate
column-conflict rejection remain fail closed.  No query, fetch, model,
context, token, wall, or network budget is added.  Runtime inputs remain the
visible ``opaque_id``/``question`` task and injected bounded clients only;
entropy/information gain assigns no signed credit.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24982_paired_production_runtime as counters
from . import v25117_grounded_target_record_plan as target_plan
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25346_grounded_fact_bootstrap as frozen_bootstrap
from . import v25354_pre_effect_query_compatible_grounded_fact_runtime as parent
from . import v25360_quote_coordinate_partial_field_record as partial
from . import v25361_partial_field_grounded_fact_bootstrap as successor_bootstrap
from .clients import parse_json_object
from .v24259_deterministic_table_normalizer import _replace_text
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25362_partial_field_grounded_fact_runtime_v1"
ROLE = "v25362_partial_field_grounded_fact_runtime_result"
STAGE_RECEIPT_ROLE = "v25362_content_free_partial_field_sanitizer_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = parent.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES


class FirstWavePageCaptureHardCappedSearch(cap.HardCappedSearchClient):
    """Per-task first-wave client that retains only its already-returned pages."""

    def __init__(
        self,
        inner: RobustLatePageBoundSearchClient,
        budget: cap.PhysicalEffectBudget,
    ) -> None:
        super().__init__(inner, budget, phase=FIRST_PHASE)
        self.fetch_return_count = 0
        self.first_wave_pages: tuple[dict[str, str], ...] = ()

    def fetch_urls(self, requests: Sequence[Mapping[str, str]]) -> Any:
        output = super().fetch_urls(requests)
        self.fetch_return_count += 1
        if self.fetch_return_count != 1:
            raise RuntimeError("V2.53.62 first-wave fetch multiplicity drifted")
        self.first_wave_pages = tuple(copy.deepcopy(counters._pages(output)))
        return output


def _sanitize_joint_output(
    model_output: object,
    *,
    question: str,
    columns: Sequence[str],
    first_wave_pages: Sequence[Mapping[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Return a parent-compatible joint response and content-free counters."""

    raw = score._model_text(model_output)
    split = frozen_bootstrap._joint_output(raw)
    pages, page_counts = frozen_bootstrap._grounded_visible_pages(first_wave_pages)
    parsed_records = 0
    parsed_fields = 0
    verified: list[dict[str, Any]] = []
    disposition: dict[str, int] = {}
    strict = False
    attempted = bool(split["records_member_present"] and len(columns) >= 2 and pages)
    if attempted:
        prepared = partial.prepare_record_proposal(question, columns, pages)
        proposals = partial.parent._parse_proposals(split["record_output"])
        strict = proposals is not None
        if proposals is not None:
            parsed_records = len(proposals)
            parsed_fields = sum(len(record["fields"]) for record in proposals)
            verified, disposition = partial._field_dispositions(prepared, proposals)

    sanitized = raw
    if strict:
        parent_plan = json.loads(str(split["parent_output"]))
        sanitized = json.dumps(
            {**parent_plan, "records": verified},
            ensure_ascii=False,
            separators=(",", ":"),
        )
    counts = {
        "input_first_wave_page_count": int(
            page_counts["input_first_wave_page_count"]
        ),
        "grounded_visible_page_count": int(
            page_counts["grounded_visible_page_count"]
        ),
        "grounded_visible_page_characters": int(
            page_counts["grounded_visible_page_characters"]
        ),
        "parsed_record_count": parsed_records,
        "parsed_field_count": parsed_fields,
        "field_accepted_count": int(disposition.get("field_accepted_count", 0)),
        "field_unknown_rejection_count": int(
            disposition.get("field_unknown_rejection_count", 0)
        ),
        "field_label_or_value_binding_rejection_count": int(
            disposition.get("field_label_or_value_binding_rejection_count", 0)
        ),
        "field_quote_coordinate_rejection_count": int(
            disposition.get("field_quote_coordinate_rejection_count", 0)
        ),
        "field_row_identity_rejection_count": int(
            disposition.get("field_row_identity_rejection_count", 0)
        ),
        "field_page_reference_rejection_count": int(
            disposition.get("field_page_reference_rejection_count", 0)
        ),
        "field_exact_duplicate_rejection_count": int(
            disposition.get("field_exact_duplicate_rejection_count", 0)
        ),
        "field_conflict_rejection_count": int(
            disposition.get("field_conflict_rejection_count", 0)
        ),
        "record_conflict_count": int(disposition.get("record_conflict_count", 0)),
        "record_zero_accepted_field_count": int(
            disposition.get("record_zero_accepted_field_count", 0)
        ),
        "verified_partial_record_count": len(verified),
        "verified_field_count": sum(len(record["fields"]) for record in verified),
        "sanitizer_attempted": attempted,
        "record_output_strictly_valid": strict,
        "response_changed": sanitized != raw,
    }
    return sanitized, counts


class PartialFieldPreEffectHardCappedModel(
    parent.PreEffectQueryCompatibleHardCappedModel
):
    """Per-task model proxy sanitizing only the second response."""

    def __init__(
        self,
        bounded: DeadlineAwareGlobalModelSlotLimiter,
        budget: cap.PhysicalEffectBudget,
        *,
        question: str,
        limits: score.ScoreFirstLimits,
        first_wave_search: FirstWavePageCaptureHardCappedSearch,
    ) -> None:
        if (
            not isinstance(first_wave_search, FirstWavePageCaptureHardCappedSearch)
            or first_wave_search._budget is not budget
        ):
            raise TypeError("V2.53.62 first-wave capture boundary drifted")
        super().__init__(bounded, budget, question=question, limits=limits)
        self._v25362_first_wave_search = first_wave_search
        self._v25362_columns: tuple[str, ...] = ()
        self._v25362_sanitizer: dict[str, Any] | None = None
        self._v25362_grounded_effect_failed = False

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        before = self.logical_call_count
        try:
            value = super().complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        except BaseException:
            if before == 1:
                self._v25362_grounded_effect_failed = True
            raise
        if self.logical_call_count == 1:
            plan = parse_json_object(score._model_text(value))
            self._v25362_columns = tuple(str(item) for item in plan["columns"])
            return value
        if self.logical_call_count != 2:
            return value
        if not str(system).startswith(target_plan.SYSTEM_PROMPT):
            raise ValueError("V2.53.62 second model call is not grounded plan")
        sanitized, counters_ = _sanitize_joint_output(
            value,
            question=self._v25354_question,
            columns=self._v25362_columns,
            first_wave_pages=self._v25362_first_wave_search.first_wave_pages,
        )
        self._v25362_sanitizer = counters_
        return _replace_text(value, sanitized)


_INTEGER_FIELDS = (
    "logical_model_call_count",
    "first_wave_fetch_return_count",
    "input_first_wave_page_count",
    "grounded_visible_page_count",
    "grounded_visible_page_characters",
    "parsed_record_count",
    "parsed_field_count",
    "field_accepted_count",
    "field_unknown_rejection_count",
    "field_label_or_value_binding_rejection_count",
    "field_quote_coordinate_rejection_count",
    "field_row_identity_rejection_count",
    "field_page_reference_rejection_count",
    "field_exact_duplicate_rejection_count",
    "field_conflict_rejection_count",
    "record_conflict_count",
    "record_zero_accepted_field_count",
    "verified_partial_record_count",
    "verified_field_count",
    "parent_verified_record_count",
    "parent_verified_field_count",
    "positive_signed_credit_count",
)


def _stage_receipt(
    model: PartialFieldPreEffectHardCappedModel,
    parent_result: Mapping[str, Any],
) -> dict[str, Any]:
    observed = model._v25362_sanitizer or {}
    fact = parent_result["content_free_receipt"]["grounded_fact_receipt"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": STAGE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_role": parent.ROLE,
        "parent_policy_id": parent.POLICY_ID,
        "parent_result_payload_sha256": str(parent_result["result_payload_sha256"]),
        "partial_field_verifier_policy_id": partial.POLICY_ID,
        "successor_bootstrap_policy_id": successor_bootstrap.POLICY_ID,
        "logical_model_call_count": int(model.logical_call_count),
        "first_wave_fetch_return_count": int(
            model._v25362_first_wave_search.fetch_return_count
        ),
        **{
            name: int(observed.get(name, 0))
            for name in _INTEGER_FIELDS
            if name
            not in {
                "logical_model_call_count",
                "first_wave_fetch_return_count",
                "parent_verified_record_count",
                "parent_verified_field_count",
                "positive_signed_credit_count",
            }
        },
        "parent_verified_record_count": int(fact["verified_record_count"]),
        "parent_verified_field_count": int(fact["verified_field_count"]),
        "positive_signed_credit_count": 0,
        "grounded_model_effect_failed": bool(model._v25362_grounded_effect_failed),
        "sanitizer_attempted": bool(observed.get("sanitizer_attempted", False)),
        "record_output_strictly_valid": bool(
            observed.get("record_output_strictly_valid", False)
        ),
        "response_changed": bool(observed.get("response_changed", False)),
        "candidate_production_prompt_changed": bool(
            fact["candidate_production_prompt_changed"]
        ),
        "per_task_instance_state_only_no_module_global_mutation": True,
        "same_returned_first_wave_pages_only": True,
        "four_parent_plan_members_preserved": True,
        "frozen_parent_reverifies_sanitized_records": True,
        "page_quote_row_and_coordinate_conflict_checks_remain_fail_closed": True,
        "invalid_fields_only_are_omitted": True,
        "query_fetch_model_context_token_wall_and_network_caps_unchanged": True,
        "additional_model_search_fetch_or_network_effect": False,
        "contains_question_query_column_url_title_page_quote_identity_field_value_prediction_answer_hash_opaque_id_or_credential": False,
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
    dynamic = (
        "grounded_model_effect_failed",
        "sanitizer_attempted",
        "record_output_strictly_valid",
        "response_changed",
        "candidate_production_prompt_changed",
    )
    true_flags = (
        "per_task_instance_state_only_no_module_global_mutation",
        "same_returned_first_wave_pages_only",
        "four_parent_plan_members_preserved",
        "frozen_parent_reverifies_sanitized_records",
        "page_quote_row_and_coordinate_conflict_checks_remain_fail_closed",
        "invalid_fields_only_are_omitted",
        "query_fetch_model_context_token_wall_and_network_caps_unchanged",
    )
    false_flags = (
        "additional_model_search_fetch_or_network_effect",
        "contains_question_query_column_url_title_page_quote_identity_field_value_prediction_answer_hash_opaque_id_or_credential",
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
        "partial_field_verifier_policy_id",
        "successor_bootstrap_policy_id",
        *_INTEGER_FIELDS,
        *dynamic,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    disposition_total = sum(
        copied.get(name, 0)
        for name in (
            "field_accepted_count",
            "field_unknown_rejection_count",
            "field_label_or_value_binding_rejection_count",
            "field_quote_coordinate_rejection_count",
            "field_row_identity_rejection_count",
            "field_page_reference_rejection_count",
            "field_exact_duplicate_rejection_count",
            "field_conflict_rejection_count",
        )
    )
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != STAGE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_role") != parent.ROLE
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or copied.get("partial_field_verifier_policy_id") != partial.POLICY_ID
        or copied.get("successor_bootstrap_policy_id")
        != successor_bootstrap.POLICY_ID
        or not isinstance(copied.get("parent_result_payload_sha256"), str)
        or len(copied["parent_result_payload_sha256"]) != 64
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _INTEGER_FIELDS
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamic)
        or not 1 <= copied["logical_model_call_count"] <= cap.MODEL_CAP
        or copied["first_wave_fetch_return_count"] not in {0, 1}
        or copied["grounded_visible_page_count"]
        > min(
            copied["input_first_wave_page_count"],
            partial.MAXIMUM_PAGE_COUNT,
        )
        or copied["grounded_visible_page_characters"]
        > partial.MAXIMUM_PROPOSAL_INPUT_CHARACTERS
        or copied["parsed_record_count"] > partial.MAXIMUM_PROPOSED_RECORDS
        or copied["parsed_field_count"] > partial.MAXIMUM_TOTAL_FIELDS
        or disposition_total != copied["parsed_field_count"]
        or copied["verified_partial_record_count"]
        > copied["parsed_record_count"]
        or copied["verified_field_count"] != copied["field_accepted_count"]
        or copied["parent_verified_record_count"]
        != copied["verified_partial_record_count"]
        or copied["parent_verified_field_count"]
        != copied["verified_field_count"]
        or copied["positive_signed_credit_count"] != 0
        or copied["record_output_strictly_valid"]
        and not copied["sanitizer_attempted"]
        or copied["response_changed"]
        and not copied["record_output_strictly_valid"]
        or copied["candidate_production_prompt_changed"]
        and copied["parent_verified_record_count"] == 0
        or copied["grounded_model_effect_failed"]
        and copied["sanitizer_attempted"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.62 partial-field sanitizer receipt drifted")
    return copied


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: PartialFieldPreEffectHardCappedModel,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    arm_order: Sequence[str] | None = None,
    monotonic: Any = None,
) -> dict[str, Any]:
    visible = score.validate_visible_task(task)
    first = searches.get(FIRST_PHASE) if isinstance(searches, Mapping) else None
    if (
        not isinstance(model, PartialFieldPreEffectHardCappedModel)
        or model._budget is not budget
        or model._v25354_question != visible["question"]
        or not isinstance(first, FirstWavePageCaptureHardCappedSearch)
        or model._v25362_first_wave_search is not first
        or first._budget is not budget
    ):
        raise TypeError("V2.53.62 runtime boundary drifted")
    kwargs: dict[str, Any] = {
        "model": model,
        "searches": searches,
        "limits": limits,
        "budget": budget,
        "arm_order": arm_order,
    }
    if monotonic is not None:
        kwargs["monotonic"] = monotonic
    parent_result = parent.validate_result(parent.run_paired_task(visible, **kwargs))
    value = copy.deepcopy(parent_result)
    value["role"] = ROLE
    value["policy_id"] = POLICY_ID
    value["partial_field_sanitizer_receipt"] = _stage_receipt(model, parent_result)
    value.pop("result_payload_sha256", None)
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    stage = copied.get("partial_field_sanitizer_receipt")
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(stage, Mapping)
        or validate_stage_receipt(stage) != dict(stage)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.62 result envelope drifted")
    parent_value = copy.deepcopy(copied)
    parent_value.pop("partial_field_sanitizer_receipt")
    parent_value["role"] = parent.ROLE
    parent_value["policy_id"] = parent.POLICY_ID
    parent_value["result_payload_sha256"] = stage["parent_result_payload_sha256"]
    checked = parent.validate_result(parent_value)
    fact = checked["content_free_receipt"]["grounded_fact_receipt"]
    if (
        stage["logical_model_call_count"]
        != checked["content_free_receipt"]["physical_model_forward_count"]
        or stage["parent_verified_record_count"] != fact["verified_record_count"]
        or stage["parent_verified_field_count"] != fact["verified_field_count"]
        or stage["candidate_production_prompt_changed"]
        is not checked["candidate_production_prompt_changed"]
    ):
        raise ValueError("V2.53.62 stage-to-parent binding drifted")
    return copied


validate_parent_result = parent.validate_result
validate_parent_receipt = parent.validate_receipt
validate_receipt = parent.validate_receipt


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "FIRST_PHASE",
    "FirstWavePageCaptureHardCappedSearch",
    "PHASES",
    "POLICY_ID",
    "PartialFieldPreEffectHardCappedModel",
    "ROLE",
    "SECOND_PHASE",
    "STAGE_RECEIPT_ROLE",
    "run_paired_task",
    "validate_parent_receipt",
    "validate_parent_result",
    "validate_receipt",
    "validate_result",
    "validate_stage_receipt",
]
