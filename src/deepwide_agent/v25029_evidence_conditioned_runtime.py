"""Single-arm production runtime for evidence-conditioned resolve-then-expand.

One task uses exactly one visible-only planning call, a two-query/at-most-six-
fetch first wave, one bounded refinement call, a two-query/at-most-four-fetch
second wave, and one synthesis call.  This is the production counterpart of
V2.50.25: there is no control arm, duplicated retrieval, or fourth model call.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from collections.abc import Callable, Mapping
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24982_paired_production_runtime as counters
from . import v24986_robust_paired_runtime as robust
from . import v24990_query_vector_paired_runtime as compact
from . import v24996_shared_first_wave_paired_runtime as wave
from . import v25024_evidence_conditioned_queries as refinement
from .clients import parse_json_object
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25029_single_arm_evidence_conditioned_resolve_expand_v1"
ROLE = "v25029_evidence_conditioned_runtime_result"
RECEIPT_ROLE = "v25029_content_free_evidence_conditioned_runtime_receipt"
PHASES = (wave.SHARED_PHASE, wave.CANDIDATE_ARM)
SHARED_PHASE, SECOND_PHASE = PHASES


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "physical_query_count": int(value["physical_query_count"]),
        "physical_fetch_count": int(value["physical_fetch_count"]),
        "model_logical_call_count": int(value["model_logical_call_count"]),
        "model_provider_request_count": int(value["model_provider_request_count"]),
        "model_provider_attempt_count": int(value["model_provider_attempt_count"]),
        "usable_page_count": int(value["usable_page_count"]),
        "evidence_characters": int(value["evidence_characters"]),
        "refinement_model_call_attempted": bool(value["refinement_model_call_attempted"]),
        "refinement_strategy_applied": bool(value["refinement_strategy_applied"]),
        "exact_legacy_second_wave_handoff": bool(value["exact_legacy_second_wave_handoff"]),
        "model_success": bool(value["model_success"]),
        "normalizer_status": str(value["normalizer_status"]),
        "refinement_receipt": copy.deepcopy(dict(value["refinement_receipt"])),
        "first_wave_receipt": copy.deepcopy(value["first_wave_receipt"]),
        "second_wave_receipt": copy.deepcopy(value["second_wave_receipt"]),
        "one_visible_only_planning_call": True,
        "one_evidence_conditioned_refinement_call_if_first_wave_nonempty": True,
        "one_synthesis_call_if_any_page": True,
        "model_call_cap": 3,
        "query_cap": 4,
        "fetch_cap": 10,
        "evidence_character_cap": 60_000,
        "wall_second_cap": 240,
        "page_text_treated_as_untrusted_data": True,
        "contains_question_query_url_title_page_record_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    refine = copied.get("refinement_receipt")
    first = copied.get("first_wave_receipt")
    second = copied.get("second_wave_receipt")
    counts = (
        "physical_query_count", "physical_fetch_count", "model_logical_call_count",
        "model_provider_request_count", "model_provider_attempt_count",
        "usable_page_count", "evidence_characters", "model_call_cap", "query_cap",
        "fetch_cap", "evidence_character_cap", "wall_second_cap",
    )
    bools = (
        "refinement_model_call_attempted", "refinement_strategy_applied",
        "exact_legacy_second_wave_handoff", "model_success",
    )
    true_flags = (
        "one_visible_only_planning_call",
        "one_evidence_conditioned_refinement_call_if_first_wave_nonempty",
        "one_synthesis_call_if_any_page", "page_text_treated_as_untrusted_data",
    )
    false_flags = (
        "contains_question_query_url_title_page_record_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version", "role", "policy_id", *counts, *bools,
        "normalizer_status", "refinement_receipt", "first_wave_receipt",
        "second_wave_receipt", *true_flags, *false_flags, "receipt_payload_sha256",
    }
    if (
        set(copied) != expected or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE or copied.get("policy_id") != POLICY_ID
        or any(isinstance(copied.get(name), bool) or not isinstance(copied.get(name), int) or copied[name] < 0 for name in counts)
        or any(not isinstance(copied.get(name), bool) for name in bools)
        or copied["physical_query_count"] > 4 or copied["physical_fetch_count"] > 10
        or copied["model_logical_call_count"] > 3
        or copied["model_provider_request_count"] > 3
        or copied["model_provider_attempt_count"] < copied["model_provider_request_count"]
        or copied["evidence_characters"] > 60_000
        or copied["model_call_cap"] != 3 or copied["query_cap"] != 4
        or copied["fetch_cap"] != 10 or copied["evidence_character_cap"] != 60_000
        or copied["wall_second_cap"] != 240
        or copied["refinement_strategy_applied"] is copied["exact_legacy_second_wave_handoff"]
        or not isinstance(refine, Mapping) or refinement.validate_receipt(refine) != dict(refine)
        or copied["refinement_model_call_attempted"] is not refine["model_call_attempted"]
        or copied["refinement_strategy_applied"] is not refine["strategy_applied"]
        or copied["exact_legacy_second_wave_handoff"] is not refine["exact_legacy_second_wave_handoff"]
        or first is not None and wave.validate_wave_receipt(first) != first
        or second is not None and wave.validate_wave_receipt(second) != second
        or copied["model_logical_call_count"]
        != 1
        + int(copied["refinement_model_call_attempted"])
        + int(copied["normalizer_status"] != "not_attempted")
        or copied["physical_query_count"]
        != sum(
            int(item["executed_queries"])
            for item in (first, second)
            if item is not None
        )
        or copied["physical_fetch_count"]
        != sum(
            int(item["fetch_attempts"])
            for item in (first, second)
            if item is not None
        )
        or copied["usable_page_count"]
        != sum(
            int(item["usable_pages"])
            for item in (first, second)
            if item is not None
        )
        or copied.get("normalizer_status") not in {"not_attempted", "exact", "normalized", "unrecoverable"}
        or copied["model_success"] and copied["normalizer_status"] not in {"exact", "normalized"}
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.29 runtime receipt drifted")
    return copied


def run_task(
    task: Mapping[str, Any], *, model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: score.ScoreFirstLimits, monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    started = monotonic()
    visible = score.validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.50.29 requires bounded global model limiter")
    if set(searches) != set(PHASES) or len({id(searches[p]) for p in PHASES}) != 2:
        raise ValueError("V2.50.29 requires two distinct search clients")
    limits.validate()
    if (
        limits.wall_seconds != 240 or limits.model_calls != 3
        or limits.search_queries != 4 or limits.fetch_targets != 10
        or limits.search_results_per_query != 3 or limits.evidence_chars != 60_000
        or limits.page_chars != 5_000
    ):
        raise ValueError("V2.50.29 production budget drifted")
    model_before = counters._counter(model, counters._MODEL_COUNTERS)
    search_before = {phase: counters._counter(searches[phase], counters._SEARCH_COUNTERS) for phase in PHASES}
    observers = {phase: compact._EffectObserver(searches[phase]) for phase in PHASES}
    failures: dict[str, Any] = {"plan": None, "refinement": None, "retrieval": {p: None for p in PHASES}, "synthesis": None}
    logical_model_calls = 1
    plan = robust.validated_robust_plan({}, visible["question"], limits)
    try:
        response = model.complete(
            score.PLAN_SYSTEM,
            score.PLAN_USER.format(question=visible["question"], query_limit=limits.search_queries),
            max_output_tokens=limits.plan_output_tokens, json_mode=True,
        )
        plan = robust.validated_robust_plan(parse_json_object(counters._model_text(response)), visible["question"], limits)
    except BaseException as exc:
        failures["plan"] = counters._safe_failure(exc)
    queries = list(plan["queries"])
    first = second = None
    first_pages: list[dict[str, str]] = []
    second_pages: list[dict[str, str]] = []
    try:
        first = wave._run_wave(queries[:2], phase=SHARED_PHASE, search=observers[SHARED_PHASE], fetch_cap=6, search_results_per_query=3)
        first_pages = counters._pages(first["page_batches"])
    except BaseException as exc:
        failures["retrieval"][SHARED_PHASE] = counters._safe_failure(exc)
    prepared = refinement.prepare_refinement(visible["question"], queries, first_pages)
    refinement_attempted = bool(first_pages)
    refinement_output = ""
    if refinement_attempted:
        logical_model_calls += 1
        try:
            response = model.complete(str(prepared["system"]), str(prepared["user"]), max_output_tokens=refinement.REFINEMENT_OUTPUT_TOKEN_CAP, json_mode=True)
            refinement_output = counters._model_text(response)
        except BaseException as exc:
            failures["refinement"] = counters._safe_failure(exc)
    refined = refinement.select_refined_queries(prepared, refinement_output, model_call_attempted=refinement_attempted)
    selected = [*queries[:2], *refined["queries"]]
    if first is not None:
        try:
            second = wave._run_wave(selected[2:], phase=SECOND_PHASE, search=observers[SECOND_PHASE], fetch_cap=4, search_results_per_query=3, exclude_urls=first["selected_urls"])
            second_pages = counters._pages(second["page_batches"])
        except BaseException as exc:
            failures["retrieval"][SECOND_PHASE] = counters._safe_failure(exc)
    else:
        failures["retrieval"][SECOND_PHASE] = "SharedFirstWaveFailure"
    pages = [*first_pages, *second_pages]
    evidence = compact._compact_evidence(pages, limits)
    prediction = counters._fallback(plan["columns"])
    success = False
    status = "not_attempted"
    if pages:
        logical_model_calls += 1
        try:
            response = model.complete(
                score.SYNTHESIS_SYSTEM,
                score.SYNTHESIS_USER.format(question=visible["question"], columns=json.dumps(plan["columns"], ensure_ascii=False), evidence=evidence),
                max_output_tokens=limits.synthesis_output_tokens, json_mode=False,
            )
            parsed, status = robust._normalize_synthesis(counters._model_text(response), plan["columns"], visible["question"])
            if parsed is None:
                raise ValueError("V2.50.29 synthesis table contract failed")
            prediction = parsed
            success = True
        except BaseException as exc:
            status = "unrecoverable"
            failures["synthesis"] = counters._safe_failure(exc)
    model_cost = counters._delta(counters._counter(model, counters._MODEL_COUNTERS), model_before)
    search_cost = {phase: counters._delta(counters._counter(searches[phase], counters._SEARCH_COUNTERS), search_before[phase]) for phase in PHASES}
    physical_queries = sum(observer.logical_query_count for observer in observers.values())
    physical_fetches = sum(observer.fetch_request_count for observer in observers.values())
    receipt = _receipt({
        "physical_query_count": physical_queries,
        "physical_fetch_count": physical_fetches,
        "model_logical_call_count": logical_model_calls,
        "model_provider_request_count": model_cost["requests"],
        "model_provider_attempt_count": model_cost["attempts"],
        "usable_page_count": len(pages),
        "evidence_characters": len(evidence),
        "refinement_model_call_attempted": refinement_attempted,
        "refinement_strategy_applied": refined["content_free_receipt"]["strategy_applied"],
        "exact_legacy_second_wave_handoff": refined["content_free_receipt"]["exact_legacy_second_wave_handoff"],
        "model_success": success,
        "normalizer_status": status,
        "refinement_receipt": refined["content_free_receipt"],
        "first_wave_receipt": None if first is None else first["receipt"],
        "second_wave_receipt": None if second is None else second["receipt"],
    })
    value = {
        "artifact_version": 1, "role": ROLE, "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"], "status": "terminal",
        "prediction": prediction,
        "prediction_sha256": hashlib.sha256(prediction.encode()).hexdigest(),
        "completion_kind": "primary" if success else "best_effort_fallback",
        "elapsed_seconds": round(max(0.0, monotonic() - started), 6),
        "model_success": success, "failure_types": failures,
        "cost": {"model": model_cost, "search": search_cost, "system_total_tokens": model_cost["total_tokens"] + sum(item["total_tokens"] for item in search_cost.values())},
        "content_free_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    prediction = copied.get("prediction")
    receipt = copied.get("content_free_receipt")
    if (
        copied.get("artifact_version") != 1 or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID or copied.get("status") != "terminal"
        or not isinstance(prediction, str) or not prediction
        or copied.get("prediction_sha256") != hashlib.sha256(prediction.encode()).hexdigest()
        or copied.get("completion_kind") not in {"primary", "best_effort_fallback"}
        or isinstance(copied.get("elapsed_seconds"), bool) or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or not isinstance(receipt, Mapping) or validate_receipt(receipt) != dict(receipt)
        or copied.get("model_success") is not receipt["model_success"]
        or copied.get("completion_kind")
        != ("primary" if copied["model_success"] else "best_effort_fallback")
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.29 runtime result drifted")
    return copied


__all__ = ["PHASES", "POLICY_ID", "ROLE", "run_task", "validate_receipt", "validate_result"]
