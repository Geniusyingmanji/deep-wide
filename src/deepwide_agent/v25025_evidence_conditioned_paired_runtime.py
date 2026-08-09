"""Matched shared-first-wave gate for evidence-conditioned query refinement.

The runtime reuses V2.49.96's audited physical-wave execution.  One visible-
only planning call and one first wave are shared.  A single bounded refinement
call sees only the visible question and those same-forward public pages.  The
control ignores its output and retains the legacy second wave; the candidate
uses it only when V2.50.24's strict support gate passes.  Both arms are charged
the shared plan and refinement calls, then receive one synthesis call each.

Thus each arm has at most three logical model calls, four queries, ten fetches,
60k evidence characters, and the same 240-second deadline.  The paired causal
gate has at most four physical model calls, six queries, and fourteen fetches.
No benchmark label, mapping, gold, evaluator, score, reward, historical result,
or credential enters the runtime.  Entropy/IG assign no signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24982_paired_production_runtime as paired
from . import v24986_robust_paired_runtime as robust
from . import v24990_query_vector_paired_runtime as compact
from . import v24996_shared_first_wave_paired_runtime as parent
from . import v25024_evidence_conditioned_queries as refinement
from .clients import parse_json_object
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25025_evidence_conditioned_shared_first_wave_paired_runtime_v1"
ROLE = "v25025_evidence_conditioned_paired_runtime_result"
RECEIPT_ROLE = "v25025_content_free_evidence_conditioned_paired_receipt"
ARMS = parent.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
SHARED_PHASE = parent.SHARED_PHASE
PHASES = parent.PHASES
ARM_METRIC_KEYS = parent.ARM_METRIC_KEYS


def _arm_order(opaque_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"v25025:{opaque_id}".encode()).digest()[0]
    return ARMS if digest % 2 == 0 else ARMS[::-1]


def _metric(value: Mapping[str, Any]) -> dict[str, Any]:
    if set(value) != ARM_METRIC_KEYS:
        raise ValueError("V2.50.25 arm metric schema drifted")
    output = {
        name: int(value[name])
        for name in ARM_METRIC_KEYS
        if name not in {"synthesis_attempted", "model_success", "normalizer_status"}
    }
    output["synthesis_attempted"] = bool(value["synthesis_attempted"])
    output["model_success"] = bool(value["model_success"])
    output["normalizer_status"] = str(value["normalizer_status"])
    return output


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "provider_unique_query_count": int(value["provider_unique_query_count"]),
        "shared_prefix_page_count": int(value["shared_prefix_page_count"]),
        "physical_query_count": int(value["physical_query_count"]),
        "physical_fetch_count": int(value["physical_fetch_count"]),
        "model_logical_call_count": int(value["model_logical_call_count"]),
        "model_provider_request_count": int(value["model_provider_request_count"]),
        "model_provider_attempt_count": int(value["model_provider_attempt_count"]),
        "shared_model_call_count": int(value["shared_model_call_count"]),
        "refinement_model_call_attempted": bool(
            value["refinement_model_call_attempted"]
        ),
        "refinement_strategy_applied": bool(value["refinement_strategy_applied"]),
        "exact_legacy_second_wave_handoff": bool(
            value["exact_legacy_second_wave_handoff"]
        ),
        "query_vectors_differ_only_in_second_wave": bool(
            value["query_vectors_differ_only_in_second_wave"]
        ),
        "shared_first_wave_completed": bool(value["shared_first_wave_completed"]),
        "shared_prefix_byte_equal_between_arms": bool(
            value["shared_prefix_byte_equal_between_arms"]
        ),
        "first_delta_arm": str(value["first_delta_arm"]),
        "actual_first_synthesis_arm": str(value["actual_first_synthesis_arm"]),
        "arm_metrics": {arm: _metric(value["arm_metrics"][arm]) for arm in ARMS},
        "prediction_changed": bool(value["prediction_changed"]),
        "both_arms_model_success": bool(value["both_arms_model_success"]),
        "refinement_receipt": copy.deepcopy(dict(value["refinement_receipt"])),
        "one_shared_visible_only_planning_call": True,
        "one_shared_evidence_conditioned_refinement_call_charged_to_both_arms": True,
        "one_physical_first_wave_reused_by_both_arms": True,
        "control_ignores_refinement_and_replays_legacy_second_wave": True,
        "candidate_uses_refinement_only_after_strict_support_gate": True,
        "independent_equal_second_wave_budgets": True,
        "per_arm_logical_model_call_cap": 3,
        "physical_model_call_cap": 4,
        "per_arm_logical_query_cap": 4,
        "per_arm_logical_fetch_cap": 10,
        "per_arm_synthesis_call_cap": 1,
        "physical_query_cap": 6,
        "physical_fetch_cap": 14,
        "same_projector_evidence_prompt_model_output_and_deadline": True,
        "external_gate_not_production_latency_or_throughput": True,
        "production_runtime_or_exact220_authorized": False,
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
    metrics = copied.get("arm_metrics")
    refine = copied.get("refinement_receipt")
    count_fields = (
        "provider_unique_query_count",
        "shared_prefix_page_count",
        "physical_query_count",
        "physical_fetch_count",
        "model_logical_call_count",
        "model_provider_request_count",
        "model_provider_attempt_count",
        "shared_model_call_count",
        "per_arm_logical_model_call_cap",
        "physical_model_call_cap",
        "per_arm_logical_query_cap",
        "per_arm_logical_fetch_cap",
        "per_arm_synthesis_call_cap",
        "physical_query_cap",
        "physical_fetch_cap",
    )
    bool_fields = (
        "refinement_model_call_attempted",
        "refinement_strategy_applied",
        "exact_legacy_second_wave_handoff",
        "query_vectors_differ_only_in_second_wave",
        "shared_first_wave_completed",
        "shared_prefix_byte_equal_between_arms",
        "prediction_changed",
        "both_arms_model_success",
    )
    true_flags = (
        "one_shared_visible_only_planning_call",
        "one_shared_evidence_conditioned_refinement_call_charged_to_both_arms",
        "one_physical_first_wave_reused_by_both_arms",
        "control_ignores_refinement_and_replays_legacy_second_wave",
        "candidate_uses_refinement_only_after_strict_support_gate",
        "independent_equal_second_wave_budgets",
        "same_projector_evidence_prompt_model_output_and_deadline",
        "external_gate_not_production_latency_or_throughput",
    )
    false_flags = (
        "production_runtime_or_exact220_authorized",
        "contains_question_query_url_title_page_record_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *count_fields,
        *bool_fields,
        "first_delta_arm",
        "actual_first_synthesis_arm",
        "arm_metrics",
        "refinement_receipt",
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
            for name in count_fields
        )
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or copied["provider_unique_query_count"] > 4
        or copied["physical_query_count"] > 6
        or copied["physical_fetch_count"] > 14
        or copied["model_logical_call_count"] > 4
        or copied["model_provider_request_count"] > copied["model_logical_call_count"]
        or copied["model_provider_attempt_count"] < copied["model_provider_request_count"]
        or copied["shared_model_call_count"]
        != 1 + int(copied["refinement_model_call_attempted"])
        or copied["per_arm_logical_model_call_cap"] != 3
        or copied["physical_model_call_cap"] != 4
        or copied["per_arm_logical_query_cap"] != 4
        or copied["per_arm_logical_fetch_cap"] != 10
        or copied["per_arm_synthesis_call_cap"] != 1
        or copied["physical_query_cap"] != 6
        or copied["physical_fetch_cap"] != 14
        or copied.get("first_delta_arm") not in ARMS
        or copied.get("actual_first_synthesis_arm") not in {*ARMS, "none"}
        or copied["refinement_strategy_applied"]
        is copied["exact_legacy_second_wave_handoff"]
        or copied["query_vectors_differ_only_in_second_wave"]
        is not copied["refinement_strategy_applied"]
        or copied["shared_prefix_byte_equal_between_arms"]
        is not copied["shared_first_wave_completed"]
        or not isinstance(refine, Mapping)
        or refinement.validate_receipt(refine) != dict(refine)
        or refine["model_call_attempted"]
        is not copied["refinement_model_call_attempted"]
        or refine["strategy_applied"] is not copied["refinement_strategy_applied"]
        or refine["exact_legacy_second_wave_handoff"]
        is not copied["exact_legacy_second_wave_handoff"]
        or not isinstance(metrics, Mapping)
        or set(metrics) != set(ARMS)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.25 paired receipt drifted")
    synth_attempts = 0
    successes = 0
    evidence: list[int] = []
    for arm in ARMS:
        metric = metrics[arm]
        if not isinstance(metric, Mapping) or set(metric) != ARM_METRIC_KEYS:
            raise ValueError("V2.50.25 arm metric schema drifted")
        integer_names = ARM_METRIC_KEYS - {
            "synthesis_attempted",
            "model_success",
            "normalizer_status",
        }
        if any(
            isinstance(metric.get(name), bool)
            or not isinstance(metric.get(name), int)
            or metric[name] < 0
            for name in integer_names
        ):
            raise ValueError("V2.50.25 arm metric count drifted")
        if (
            metric["planned_queries"] != 4
            or metric["executed_queries"] > 4
            or metric["fetch_attempts"] > 10
            or metric["usable_pages"] > metric["fetch_attempts"]
            or metric["projected_pages"] > metric["fetch_attempts"]
            or metric["admissible_records"] > metric["discovered_records"]
            or metric["retained_records"] > metric["admissible_records"]
            or metric["evidence_characters"] > 60_000
            or not isinstance(metric.get("synthesis_attempted"), bool)
            or not isinstance(metric.get("model_success"), bool)
            or metric["model_success"] and not metric["synthesis_attempted"]
            or metric.get("normalizer_status")
            not in {"not_attempted", "exact", "normalized", "unrecoverable"}
        ):
            raise ValueError("V2.50.25 arm metric invariant drifted")
        synth_attempts += int(metric["synthesis_attempted"])
        successes += int(metric["model_success"])
        evidence.append(metric["evidence_characters"])
        if copied["shared_model_call_count"] + int(metric["synthesis_attempted"]) > 3:
            raise ValueError("V2.50.25 per-arm model cap exceeded")
    if (
        len(set(evidence)) != 1
        or copied["model_logical_call_count"]
        != copied["shared_model_call_count"] + synth_attempts
        or copied["both_arms_model_success"] is not (successes == 2)
        or copied["physical_query_count"]
        > max(metric["executed_queries"] for metric in metrics.values()) + 2
    ):
        raise ValueError("V2.50.25 paired resource accounting drifted")
    ordered = (copied["first_delta_arm"],)
    ordered += tuple(arm for arm in ARMS if arm not in ordered)
    actual = next((arm for arm in ordered if metrics[arm]["synthesis_attempted"]), "none")
    if copied["actual_first_synthesis_arm"] != actual:
        raise ValueError("V2.50.25 synthesis order drifted")
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
    visible = score.validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.50.25 requires the bounded global model limiter")
    if (
        not isinstance(searches, Mapping)
        or set(searches) != set(PHASES)
        or any(
            not isinstance(searches[phase], RobustLatePageBoundSearchClient)
            for phase in PHASES
        )
        or len({id(searches[phase]) for phase in PHASES}) != len(PHASES)
    ):
        raise ValueError("V2.50.25 requires three distinct robust search clients")
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
        raise ValueError("V2.50.25 production-shaped budget drifted")
    order = tuple(arm_order or _arm_order(visible["opaque_id"]))
    if len(order) != 2 or set(order) != set(ARMS):
        raise ValueError("V2.50.25 arm order drifted")

    model_before = paired._counter(model, paired._MODEL_COUNTERS)
    search_before = {
        phase: paired._counter(searches[phase], paired._SEARCH_COUNTERS)
        for phase in PHASES
    }
    if any(any(snapshot.values()) for snapshot in search_before.values()):
        raise ValueError("V2.50.25 requires pristine physical search clients")
    observers = {phase: compact._EffectObserver(searches[phase]) for phase in PHASES}
    failures: dict[str, Any] = {
        "plan": None,
        "refinement": None,
        "retrieval": {phase: None for phase in PHASES},
        "synthesis": {arm: None for arm in ARMS},
    }

    logical_model_calls = 1
    raw_plan: dict[str, Any] = {}
    plan = robust.validated_robust_plan({}, visible["question"], limits)
    try:
        response = model.complete(
            score.PLAN_SYSTEM,
            score.PLAN_USER.format(
                question=visible["question"], query_limit=limits.search_queries
            ),
            max_output_tokens=limits.plan_output_tokens,
            json_mode=True,
        )
        raw_plan = parse_json_object(paired._model_text(response))
        plan = robust.validated_robust_plan(raw_plan, visible["question"], limits)
    except BaseException as exc:
        failures["plan"] = paired._safe_failure(exc)

    completed_queries = list(plan["queries"])
    phases: dict[str, dict[str, Any] | None] = {phase: None for phase in PHASES}
    shared_pages: list[dict[str, str]] = []
    delta_pages: dict[str, list[dict[str, str]]] = {arm: [] for arm in ARMS}
    try:
        phases[SHARED_PHASE] = parent._run_wave(
            completed_queries[:2],
            phase=SHARED_PHASE,
            search=observers[SHARED_PHASE],
            fetch_cap=6,
            search_results_per_query=limits.search_results_per_query,
        )
        shared_pages = paired._pages(phases[SHARED_PHASE]["page_batches"])
    except BaseException as exc:
        failures["retrieval"][SHARED_PHASE] = paired._safe_failure(exc)

    prepared = refinement.prepare_refinement(
        visible["question"], completed_queries, shared_pages
    )
    refinement_output = ""
    refinement_attempted = bool(shared_pages)
    if refinement_attempted:
        logical_model_calls += 1
        try:
            response = model.complete(
                str(prepared["system"]),
                str(prepared["user"]),
                max_output_tokens=refinement.REFINEMENT_OUTPUT_TOKEN_CAP,
                json_mode=True,
            )
            refinement_output = paired._model_text(response)
        except BaseException as exc:
            failures["refinement"] = paired._safe_failure(exc)
    refined = refinement.select_refined_queries(
        prepared,
        refinement_output,
        model_call_attempted=refinement_attempted,
    )
    refinement_receipt = refined["content_free_receipt"]
    queries = {
        CONTROL_ARM: completed_queries,
        CANDIDATE_ARM: [*completed_queries[:2], *refined["queries"]],
    }
    vectors_differ_only_second = bool(
        queries[CONTROL_ARM][:2] == queries[CANDIDATE_ARM][:2]
        and queries[CONTROL_ARM][2:] != queries[CANDIDATE_ARM][2:]
    )

    if phases[SHARED_PHASE] is not None:
        shared_urls = phases[SHARED_PHASE]["selected_urls"]
        for arm in order:
            try:
                phases[arm] = parent._run_wave(
                    queries[arm][2:],
                    phase=arm,
                    search=observers[arm],
                    fetch_cap=4,
                    search_results_per_query=limits.search_results_per_query,
                    exclude_urls=shared_urls,
                )
                delta_pages[arm] = paired._pages(phases[arm]["page_batches"])
            except BaseException as exc:
                failures["retrieval"][arm] = paired._safe_failure(exc)
    else:
        for arm in ARMS:
            failures["retrieval"][arm] = "SharedFirstWaveFailure"

    arm_pages = {arm: [*shared_pages, *delta_pages[arm]] for arm in ARMS}
    shared_prefix_equal = bool(
        phases[SHARED_PHASE] is not None
        and all(arm_pages[arm][: len(shared_pages)] == shared_pages for arm in ARMS)
    )
    evidence = parent._match_evidence(
        {arm: compact._compact_evidence(arm_pages[arm], limits) for arm in ARMS}
    )
    predictions = {arm: paired._fallback(plan["columns"]) for arm in ARMS}
    success = {arm: False for arm in ARMS}
    attempted = {arm: False for arm in ARMS}
    normalizer_status = {arm: "not_attempted" for arm in ARMS}
    synthesis_order: list[str] = []
    for arm in order:
        if not arm_pages[arm]:
            continue
        attempted[arm] = True
        synthesis_order.append(arm)
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
                paired._model_text(response), plan["columns"], visible["question"]
            )
            normalizer_status[arm] = status
            if parsed is None:
                raise ValueError("V2.50.25 synthesis table contract failed")
            predictions[arm] = parsed
            success[arm] = True
        except BaseException as exc:
            normalizer_status[arm] = "unrecoverable"
            failures["synthesis"][arm] = paired._safe_failure(exc)

    phase_receipts = {
        phase: None if phases[phase] is None else copy.deepcopy(phases[phase]["receipt"])
        for phase in PHASES
    }
    model_cost = paired._delta(
        paired._counter(model, paired._MODEL_COUNTERS), model_before
    )
    search_cost = {
        phase: paired._delta(
            paired._counter(searches[phase], paired._SEARCH_COUNTERS),
            search_before[phase],
        )
        for phase in PHASES
    }
    physical_effects = {
        phase: {
            "logical_queries": int(observers[phase].logical_query_count),
            "fetch_requests": int(observers[phase].fetch_request_count),
        }
        for phase in PHASES
    }
    shared_receipt = phase_receipts[SHARED_PHASE]
    arm_metrics = {
        arm: parent._arm_metric(
            shared_receipt,
            phase_receipts[arm],
            shared_effect=physical_effects[SHARED_PHASE],
            delta_effect=physical_effects[arm],
            evidence_characters=len(evidence[arm]),
            synthesis_attempted=attempted[arm],
            model_success=success[arm],
            normalizer_status=normalizer_status[arm],
        )
        for arm in ARMS
    }
    physical_queries = sum(effect["logical_queries"] for effect in physical_effects.values())
    physical_fetches = sum(effect["fetch_requests"] for effect in physical_effects.values())
    content_free = _receipt(
        {
            "provider_unique_query_count": plan["provider_unique_query_count"],
            "shared_prefix_page_count": len(shared_pages),
            "physical_query_count": physical_queries,
            "physical_fetch_count": physical_fetches,
            "model_logical_call_count": logical_model_calls,
            "model_provider_request_count": model_cost["requests"],
            "model_provider_attempt_count": model_cost["attempts"],
            "shared_model_call_count": 1 + int(refinement_attempted),
            "refinement_model_call_attempted": refinement_attempted,
            "refinement_strategy_applied": refinement_receipt["strategy_applied"],
            "exact_legacy_second_wave_handoff": refinement_receipt[
                "exact_legacy_second_wave_handoff"
            ],
            "query_vectors_differ_only_in_second_wave": vectors_differ_only_second,
            "shared_first_wave_completed": shared_receipt is not None,
            "shared_prefix_byte_equal_between_arms": shared_prefix_equal,
            "first_delta_arm": order[0],
            "actual_first_synthesis_arm": synthesis_order[0] if synthesis_order else "none",
            "arm_metrics": arm_metrics,
            "prediction_changed": predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM],
            "both_arms_model_success": all(success.values()),
            "refinement_receipt": refinement_receipt,
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "status": "terminal",
        "predictions": predictions,
        "model_success": success,
        "failure_types": failures,
        "prediction_changed": predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM],
        "evidence_characters": {arm: len(evidence[arm]) for arm in ARMS},
        "refinement_receipt": copy.deepcopy(refinement_receipt),
        "physical_wave_receipts": phase_receipts,
        "physical_effects": physical_effects,
        "cost": {"model": model_cost, "search": search_cost},
        "content_free_receipt": content_free,
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
    successes = copied.get("model_success")
    failures = copied.get("failure_types")
    evidence = copied.get("evidence_characters")
    refine = copied.get("refinement_receipt")
    phases = copied.get("physical_wave_receipts")
    effects = copied.get("physical_effects")
    costs = copied.get("cost")
    receipt = copied.get("content_free_receipt")
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "opaque_id",
        "status",
        "predictions",
        "model_success",
        "failure_types",
        "prediction_changed",
        "evidence_characters",
        "refinement_receipt",
        "physical_wave_receipts",
        "physical_effects",
        "cost",
        "content_free_receipt",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "benchmark_launch_or_evaluator_authorized",
        "result_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or set(predictions or {}) != set(ARMS)
        or any(not isinstance(predictions[arm], str) or not predictions[arm] for arm in ARMS)
        or set(successes or {}) != set(ARMS)
        or any(not isinstance(successes[arm], bool) for arm in ARMS)
        or not isinstance(failures, Mapping)
        or set(failures) != {"plan", "refinement", "retrieval", "synthesis"}
        or set(failures.get("retrieval") or {}) != set(PHASES)
        or set(failures.get("synthesis") or {}) != set(ARMS)
        or set(evidence or {}) != set(ARMS)
        or any(
            isinstance(evidence[arm], bool)
            or not isinstance(evidence[arm], int)
            or evidence[arm] < 0
            for arm in ARMS
        )
        or not isinstance(refine, Mapping)
        or refinement.validate_receipt(refine) != dict(refine)
        or not isinstance(phases, Mapping)
        or set(phases) != set(PHASES)
        or not isinstance(effects, Mapping)
        or set(effects) != set(PHASES)
        or any(
            set(effect) != {"logical_queries", "fetch_requests"}
            or any(isinstance(number, bool) or not isinstance(number, int) or number < 0 for number in effect.values())
            for effect in effects.values()
        )
        or not isinstance(costs, Mapping)
        or set(costs) != {"model", "search"}
        or set(costs.get("search") or {}) != set(PHASES)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["refinement_receipt"] != refine
        or copied.get("prediction_changed")
        is not (predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM])
        or receipt["prediction_changed"] != copied["prediction_changed"]
        or receipt["both_arms_model_success"] != all(successes.values())
        or any(receipt["arm_metrics"][arm]["evidence_characters"] != evidence[arm] for arm in ARMS)
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.25 paired result drifted")
    for phase in PHASES:
        if phases[phase] is not None:
            parent.validate_wave_receipt(phases[phase])
    if costs["model"]["requests"] != receipt["model_provider_request_count"]:
        raise ValueError("V2.50.25 model request accounting drifted")
    return copied


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "PHASES",
    "POLICY_ID",
    "ROLE",
    "run_paired_task",
    "validate_receipt",
    "validate_result",
]
