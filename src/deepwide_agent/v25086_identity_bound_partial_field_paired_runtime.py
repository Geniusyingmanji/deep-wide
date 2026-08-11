"""Matched-cost paired runtime for V2.50.85 identity-bound partial-field verification.

Both arms share one visible-only plan, four queries, at most ten fetched pages,
and one identity-bound partial-field record proposal.  The control receives inherited raw
evidence.  The candidate receives a same-length representation only when
V2.50.85 verifies one or more records.  Each arm is charged the shared plan and
proposal plus its own synthesis: at most three effective model calls per arm.

This module accepts injected bounded clients and has no file, environment,
process, benchmark-label, mapping, gold, evaluator, score, reward, credential,
or historical-result capability.  It grants no launch authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24982_paired_production_runtime as counters
from . import v24986_robust_paired_runtime as robust
from . import v24990_query_vector_paired_runtime as compact
from . import v24996_shared_first_wave_paired_runtime as wave
from . import v25085_identity_bound_partial_field_record as binding
from .clients import parse_json_object
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25086_matched_cost_identity_bound_partial_field_record_representation_v1"
ROLE = "v25086_identity_bound_partial_field_record_paired_runtime_result"
RECEIPT_ROLE = "v25086_content_free_identity_bound_partial_field_record_paired_runtime_receipt"
ARMS = ("raw_fetched_evidence", "identity_bound_partial_field_record_representation")
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = (wave.SHARED_PHASE, wave.CANDIDATE_ARM)
FIRST_PHASE, SECOND_PHASE = PHASES


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _arm_order(opaque_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"v25086:{opaque_id}".encode()).digest()[0]
    return ARMS if digest % 2 == 0 else ARMS[::-1]


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{
            name: int(value[name])
            for name in (
                "planned_query_count",
                "physical_query_count",
                "physical_fetch_count",
                "usable_page_count",
                "shared_model_logical_call_count",
                "physical_model_logical_call_count",
                "model_provider_request_count",
                "model_provider_attempt_count",
                "control_evidence_characters",
                "candidate_evidence_characters",
            )
        },
        "first_synthesis_arm": str(value["first_synthesis_arm"]),
        "proposal_model_call_attempted": bool(value["proposal_model_call_attempted"]),
        "proposal_model_call_success": bool(value["proposal_model_call_success"]),
        "candidate_evidence_changed": bool(value["candidate_evidence_changed"]),
        "prediction_changed": bool(value["prediction_changed"]),
        "arm_metrics": copy.deepcopy(dict(value["arm_metrics"])),
        "phase_effect_counts": copy.deepcopy(dict(value["phase_effect_counts"])),
        "record_binding_receipt": copy.deepcopy(dict(value["record_binding_receipt"])),
        "first_wave_receipt": copy.deepcopy(value["first_wave_receipt"]),
        "second_wave_receipt": copy.deepcopy(value["second_wave_receipt"]),
        "both_arms_share_plan_queries_search_responses_fetched_pages_and_proposal_cost": True,
        "query_vector_is_visible_plan_only_and_shared_by_both_arms": True,
        "candidate_only_treatment_is_same_length_identity_bound_partial_field_record_representation": True,
        "each_arm_effective_model_call_cap": 3,
        "physical_paired_model_call_cap": 4,
        "query_cap": 4,
        "fetch_cap": 10,
        "evidence_character_cap": 60_000,
        "wall_second_cap": 240,
        "page_text_treated_as_untrusted_data": True,
        "contains_question_query_url_title_page_quote_anchor_identity_field_value_prediction_answer_hash_opaque_id_or_credential": False,
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
    integer_fields = (
        "planned_query_count",
        "physical_query_count",
        "physical_fetch_count",
        "usable_page_count",
        "shared_model_logical_call_count",
        "physical_model_logical_call_count",
        "model_provider_request_count",
        "model_provider_attempt_count",
        "control_evidence_characters",
        "candidate_evidence_characters",
        "each_arm_effective_model_call_cap",
        "physical_paired_model_call_cap",
        "query_cap",
        "fetch_cap",
        "evidence_character_cap",
        "wall_second_cap",
    )
    bool_fields = (
        "proposal_model_call_attempted",
        "proposal_model_call_success",
        "candidate_evidence_changed",
        "prediction_changed",
    )
    true_flags = (
        "both_arms_share_plan_queries_search_responses_fetched_pages_and_proposal_cost",
        "query_vector_is_visible_plan_only_and_shared_by_both_arms",
        "candidate_only_treatment_is_same_length_identity_bound_partial_field_record_representation",
        "page_text_treated_as_untrusted_data",
    )
    false_flags = (
        "contains_question_query_url_title_page_quote_anchor_identity_field_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *integer_fields,
        *bool_fields,
        "first_synthesis_arm",
        "arm_metrics",
        "phase_effect_counts",
        "record_binding_receipt",
        "first_wave_receipt",
        "second_wave_receipt",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    arms = copied.get("arm_metrics")
    effects = copied.get("phase_effect_counts")
    first = copied.get("first_wave_receipt")
    second = copied.get("second_wave_receipt")
    record = copied.get("record_binding_receipt")
    metric_keys = {
        "effective_model_logical_call_count",
        "synthesis_attempted",
        "model_success",
        "normalizer_status",
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
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or copied["planned_query_count"] != 4
        or copied["physical_query_count"] > 4
        or copied["physical_fetch_count"] > 10
        or copied["usable_page_count"] > copied["physical_fetch_count"]
        or copied["shared_model_logical_call_count"]
        != 1 + int(copied["proposal_model_call_attempted"])
        or copied["physical_model_logical_call_count"]
        != copied["shared_model_logical_call_count"]
        + sum(int(arms[arm]["synthesis_attempted"]) for arm in ARMS)
        or copied["model_provider_request_count"] > copied["physical_model_logical_call_count"]
        or copied["model_provider_attempt_count"] < copied["model_provider_request_count"]
        or copied["control_evidence_characters"] != copied["candidate_evidence_characters"]
        or copied["control_evidence_characters"] > 60_000
        or copied["each_arm_effective_model_call_cap"] != 3
        or copied["physical_paired_model_call_cap"] != 4
        or copied["query_cap"] != 4
        or copied["fetch_cap"] != 10
        or copied["evidence_character_cap"] != 60_000
        or copied["wall_second_cap"] != 240
        or copied.get("first_synthesis_arm") not in {*ARMS, "none"}
        or set(arms or {}) != set(ARMS)
        or any(set(arms[arm]) != metric_keys for arm in ARMS)
        or any(
            isinstance(arms[arm]["effective_model_logical_call_count"], bool)
            or not isinstance(arms[arm]["effective_model_logical_call_count"], int)
            or arms[arm]["effective_model_logical_call_count"]
            != copied["shared_model_logical_call_count"]
            + int(arms[arm]["synthesis_attempted"])
            or arms[arm]["effective_model_logical_call_count"] > 3
            or not isinstance(arms[arm]["synthesis_attempted"], bool)
            or not isinstance(arms[arm]["model_success"], bool)
            or arms[arm]["normalizer_status"]
            not in {"not_attempted", "exact", "normalized", "unrecoverable"}
            for arm in ARMS
        )
        or copied["first_synthesis_arm"] == "none"
        and any(arms[arm]["synthesis_attempted"] for arm in ARMS)
        or copied["first_synthesis_arm"] in ARMS
        and not all(arms[arm]["synthesis_attempted"] for arm in ARMS)
        or not isinstance(effects, Mapping)
        or set(effects) != set(PHASES)
        or not isinstance(record, Mapping)
        or binding.validate_receipt(record) != dict(record)
        or copied["proposal_model_call_attempted"] is not record["model_call_attempted"]
        or copied["candidate_evidence_changed"] is not record["candidate_evidence_changed"]
        or copied["proposal_model_call_success"] and not copied["proposal_model_call_attempted"]
        or first is not None and wave.validate_wave_receipt(first) != first
        or second is not None and wave.validate_wave_receipt(second) != second
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.86 paired receipt drifted")
    wave_values = {FIRST_PHASE: first, SECOND_PHASE: second}
    for phase in PHASES:
        effect = effects[phase]
        nested = wave_values[phase]
        if (
            set(effect)
            != {
                "attempted",
                "failed",
                "physical_query_count",
                "physical_fetch_count",
                "wave_receipt_present",
            }
            or not isinstance(effect["attempted"], bool)
            or not isinstance(effect["failed"], bool)
            or not isinstance(effect["wave_receipt_present"], bool)
            or effect["wave_receipt_present"] is not (nested is not None)
            or effect["physical_query_count"] < 0
            or effect["physical_query_count"] > 2
            or effect["physical_fetch_count"] < 0
            or effect["physical_fetch_count"] > (6 if phase == FIRST_PHASE else 4)
            or nested is not None
            and (
                effect["attempted"] is not True
                or effect["failed"] is not False
                or effect["physical_query_count"] != nested["executed_queries"]
                or effect["physical_fetch_count"] != nested["fetch_attempts"]
            )
        ):
            raise ValueError("V2.50.86 phase effect drifted")
    if (
        copied["physical_query_count"]
        != sum(effects[phase]["physical_query_count"] for phase in PHASES)
        or copied["physical_fetch_count"]
        != sum(effects[phase]["physical_fetch_count"] for phase in PHASES)
        or copied["usable_page_count"]
        != sum(int(item["usable_pages"]) for item in (first, second) if item is not None)
    ):
        raise ValueError("V2.50.86 effect accounting drifted")
    return copied


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    searches: Mapping[str, RobustLatePageBoundSearchClient],
    limits: score.ScoreFirstLimits,
    arm_order: Sequence[str] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    started = monotonic()
    visible = score.validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.50.86 requires bounded global model limiter")
    if set(searches) != set(PHASES) or len({id(searches[p]) for p in PHASES}) != 2:
        raise ValueError("V2.50.86 requires two distinct search clients")
    limits.validate()
    if (
        limits.wall_seconds != 240
        or limits.model_calls != 3
        or limits.search_queries != 4
        or limits.fetch_targets != 10
        or limits.search_results_per_query != 3
        or limits.evidence_chars != 60_000
        or limits.page_chars != 5_000
    ):
        raise ValueError("V2.50.86 production budget drifted")
    chosen_order = tuple(arm_order or _arm_order(visible["opaque_id"]))
    if len(chosen_order) != 2 or set(chosen_order) != set(ARMS):
        raise ValueError("V2.50.86 arm order drifted")

    model_before = counters._counter(model, counters._MODEL_COUNTERS)
    search_before = {
        phase: counters._counter(searches[phase], counters._SEARCH_COUNTERS)
        for phase in PHASES
    }
    observers = {phase: compact._EffectObserver(searches[phase]) for phase in PHASES}
    failures: dict[str, Any] = {
        "plan": None,
        "retrieval": {phase: None for phase in PHASES},
        "proposal": None,
        **{arm: None for arm in ARMS},
    }
    logical_model_calls = 1
    plan = robust.validated_robust_plan({}, visible["question"], limits)
    try:
        response = model.complete(
            score.PLAN_SYSTEM,
            score.PLAN_USER.format(question=visible["question"], query_limit=limits.search_queries),
            max_output_tokens=limits.plan_output_tokens,
            json_mode=True,
        )
        plan = robust.validated_robust_plan(
            parse_json_object(counters._model_text(response)), visible["question"], limits
        )
    except BaseException as exc:
        failures["plan"] = _safe_failure(exc)

    queries = list(plan["queries"])
    first = second = None
    phase_attempted = {phase: False for phase in PHASES}
    first_pages: list[dict[str, str]] = []
    second_pages: list[dict[str, str]] = []
    try:
        phase_attempted[FIRST_PHASE] = True
        first = wave._run_wave(
            queries[:2],
            phase=FIRST_PHASE,
            search=observers[FIRST_PHASE],
            fetch_cap=6,
            search_results_per_query=3,
        )
        first_pages = counters._pages(first["page_batches"])
    except BaseException as exc:
        failures["retrieval"][FIRST_PHASE] = _safe_failure(exc)
    if first is not None:
        try:
            phase_attempted[SECOND_PHASE] = True
            second = wave._run_wave(
                queries[2:],
                phase=SECOND_PHASE,
                search=observers[SECOND_PHASE],
                fetch_cap=4,
                search_results_per_query=3,
                exclude_urls=first["selected_urls"],
            )
            second_pages = counters._pages(second["page_batches"])
        except BaseException as exc:
            failures["retrieval"][SECOND_PHASE] = _safe_failure(exc)
    else:
        failures["retrieval"][SECOND_PHASE] = "SharedFirstWaveFailure"

    pages = [*first_pages, *second_pages]
    control_evidence = compact._compact_evidence(pages, limits)
    prepared = binding.prepare_record_proposal(visible["question"], plan["columns"], pages)
    proposal_attempted = bool(pages)
    proposal_success = False
    proposal_output = ""
    if proposal_attempted:
        logical_model_calls += 1
        try:
            response = model.complete(
                str(prepared["system"]),
                str(prepared["user"]),
                max_output_tokens=binding.PROPOSAL_OUTPUT_TOKEN_CAP,
                json_mode=True,
            )
            proposal_output = counters._model_text(response)
            proposal_success = True
        except BaseException as exc:
            failures["proposal"] = _safe_failure(exc)
    representation = binding.build_representation(
        prepared,
        proposal_output,
        control_evidence=control_evidence,
        model_call_attempted=proposal_attempted,
    )
    evidence = {
        CONTROL_ARM: control_evidence,
        CANDIDATE_ARM: str(representation["candidate_evidence"]),
    }
    predictions = {arm: counters._fallback(plan["columns"]) for arm in ARMS}
    success = {arm: False for arm in ARMS}
    attempted = {arm: False for arm in ARMS}
    normalizer = {arm: "not_attempted" for arm in ARMS}
    first_synthesis = "none"
    if pages:
        first_synthesis = chosen_order[0]
        for arm in chosen_order:
            attempted[arm] = True
            logical_model_calls += 1
            try:
                response = model.complete(
                    score.SYNTHESIS_SYSTEM,
                    score.SYNTHESIS_USER.format(
                        question=visible["question"],
                        columns=json.dumps(plan["columns"], ensure_ascii=False),
                        evidence=evidence[arm],
                    ),
                    max_output_tokens=limits.synthesis_output_tokens,
                    json_mode=False,
                )
                parsed, status = robust._normalize_synthesis(
                    counters._model_text(response), plan["columns"], visible["question"]
                )
                normalizer[arm] = status
                if parsed is None:
                    raise ValueError("V2.50.86 synthesis table contract failed")
                predictions[arm] = parsed
                success[arm] = True
            except BaseException as exc:
                normalizer[arm] = "unrecoverable"
                failures[arm] = _safe_failure(exc)

    model_cost = counters._delta(counters._counter(model, counters._MODEL_COUNTERS), model_before)
    search_cost = {
        phase: counters._delta(
            counters._counter(searches[phase], counters._SEARCH_COUNTERS), search_before[phase]
        )
        for phase in PHASES
    }
    physical_queries = sum(observer.logical_query_count for observer in observers.values())
    physical_fetches = sum(observer.fetch_request_count for observer in observers.values())
    binding_receipt = representation["content_free_receipt"]
    arms = {
        arm: {
            "effective_model_logical_call_count": 1
            + int(proposal_attempted)
            + int(attempted[arm]),
            "synthesis_attempted": attempted[arm],
            "model_success": success[arm],
            "normalizer_status": normalizer[arm],
        }
        for arm in ARMS
    }
    waves = {FIRST_PHASE: first, SECOND_PHASE: second}
    effects = {
        phase: {
            "attempted": phase_attempted[phase],
            "failed": phase_attempted[phase] and waves[phase] is None,
            "physical_query_count": observers[phase].logical_query_count,
            "physical_fetch_count": observers[phase].fetch_request_count,
            "wave_receipt_present": waves[phase] is not None,
        }
        for phase in PHASES
    }
    receipt = _receipt(
        {
            "planned_query_count": len(queries),
            "physical_query_count": physical_queries,
            "physical_fetch_count": physical_fetches,
            "usable_page_count": len(pages),
            "shared_model_logical_call_count": 1 + int(proposal_attempted),
            "physical_model_logical_call_count": logical_model_calls,
            "model_provider_request_count": model_cost["requests"],
            "model_provider_attempt_count": model_cost["attempts"],
            "control_evidence_characters": len(evidence[CONTROL_ARM]),
            "candidate_evidence_characters": len(evidence[CANDIDATE_ARM]),
            "first_synthesis_arm": first_synthesis,
            "proposal_model_call_attempted": proposal_attempted,
            "proposal_model_call_success": proposal_success,
            "candidate_evidence_changed": binding_receipt["candidate_evidence_changed"],
            "prediction_changed": predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM],
            "arm_metrics": arms,
            "phase_effect_counts": effects,
            "record_binding_receipt": binding_receipt,
            "first_wave_receipt": None if first is None else first["receipt"],
            "second_wave_receipt": None if second is None else second["receipt"],
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "status": "terminal",
        "predictions": predictions,
        "prediction_sha256": {
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest() for arm in ARMS
        },
        "model_success": success,
        "normalizer_status": normalizer,
        "prediction_changed": predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM],
        "candidate_evidence_changed": binding_receipt["candidate_evidence_changed"],
        "failure_types": failures,
        "elapsed_seconds": round(max(0.0, monotonic() - started), 6),
        "cost": {
            "model": model_cost,
            "search": search_cost,
            "system_total_tokens": model_cost["total_tokens"]
            + sum(item["total_tokens"] for item in search_cost.values()),
        },
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
    predictions = copied.get("predictions")
    hashes = copied.get("prediction_sha256")
    success = copied.get("model_success")
    normalizer = copied.get("normalizer_status")
    failures = copied.get("failure_types")
    costs = copied.get("cost")
    receipt = copied.get("content_free_receipt")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or set(predictions or {}) != set(ARMS)
        or any(not isinstance(predictions[arm], str) or not predictions[arm] for arm in ARMS)
        or set(hashes or {}) != set(ARMS)
        or any(hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest() for arm in ARMS)
        or set(success or {}) != set(ARMS)
        or set(normalizer or {}) != set(ARMS)
        or set(failures or {}) != {"plan", "retrieval", "proposal", *ARMS}
        or set((failures or {}).get("retrieval") or {}) != set(PHASES)
        or not isinstance(costs, Mapping)
        or set(costs) != {"model", "search", "system_total_tokens"}
        or set(costs["model"]) != set(counters._MODEL_COUNTERS)
        or set(costs["search"]) != set(PHASES)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or copied.get("prediction_changed")
        is not (predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM])
        or copied.get("candidate_evidence_changed") is not receipt["candidate_evidence_changed"]
        or any(
            receipt["arm_metrics"][arm]["model_success"] is not success[arm]
            or receipt["arm_metrics"][arm]["normalizer_status"] != normalizer[arm]
            for arm in ARMS
        )
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.86 paired result drifted")
    return copied


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "PHASES",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "run_paired_task",
    "validate_receipt",
    "validate_result",
]
