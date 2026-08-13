"""Matched shared-prefix mechanism runtime for grounded fact bootstrap.

One visible-only planning call creates four queries.  The first two queries
and at most six pages execute once.  One existing grounded-plan call is
extended by V2.53.46 to propose both the second-wave plan and optional source
facts.  The final two queries execute once and at most eight union pages are
fetched.  Both arms then receive the exact same fetched-page evidence bytes;
the candidate differs only by an equal-length prefix containing mechanically
quote-verified facts from the first-wave pages.  Each arm gets one production
synthesis, so the physical ceiling remains 4 queries, 14 fetches, and 4 model
calls.

This module accepts only a visible ``opaque_id``/``question`` task and injected
hard-capped clients.  It has no filesystem, process, environment, network,
credential, evaluator, benchmark-label, mapping, gold, score, reward, or
historical-result capability.  Entropy/information gain remains shadow-only
and assigns no signed credit.  This build authorizes no external launch.
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
from . import v24999_shared_response_selection_runtime as shared
from . import v25110_exact_visible_schema as schema
from . import v25117_grounded_target_record_plan as target_plan
from . import v25119_grounded_target_record_paired_runtime as frontier
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25346_grounded_fact_bootstrap as bootstrap
from .clients import canonicalize_url, parse_json_object
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v25349_shared_prefix_grounded_fact_paired_runtime_v1"
ROLE = "v25349_shared_prefix_grounded_fact_paired_runtime_result"
RECEIPT_ROLE = "v25349_content_free_shared_prefix_grounded_fact_paired_receipt"
ARMS = ("raw_shared_page_evidence", "grounded_fact_prefix")
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = frontier.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _arm_order(opaque_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"v25349:{opaque_id}".encode()).digest()[0]
    return ARMS if digest % 2 == 0 else ARMS[::-1]


def _shared_union_pages(
    first_pages: Sequence[Mapping[str, Any]],
    second_pages: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, str]]:
    """Return one deterministic URL-deduplicated page vector for both arms."""

    if set(second_pages) != set(frontier.ARMS):
        raise ValueError("V2.53.49 second-wave page arms drifted")
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    vectors: list[Sequence[Mapping[str, Any]]] = [first_pages]
    vectors.extend(second_pages[arm] for arm in frontier.ARMS)
    for values in vectors:
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
            raise ValueError("V2.53.49 page vector drifted")
        for raw in values:
            if not isinstance(raw, Mapping):
                continue
            url = canonicalize_url(str(raw.get("url") or ""))
            content = str(raw.get("content") or raw.get("raw_content") or "")
            if not url or not content or url in seen:
                continue
            seen.add(url)
            output.append(
                {
                    "url": url,
                    "title": str(raw.get("title") or ""),
                    "content": content,
                }
            )
    return output


def _empty_bootstrap_receipt(
    *,
    question: str,
    columns: Sequence[str],
    first_pages: Sequence[Mapping[str, Any]],
    grounded_output: object,
    production_user: str,
    attempted: bool,
) -> dict[str, Any]:
    value = bootstrap.build_bootstrap(
        question=question,
        columns=columns,
        first_wave_pages=first_pages,
        grounded_model_output=grounded_output,
        production_user=production_user,
        model_call_attempted=attempted,
    )
    return bootstrap.validate_receipt(value["content_free_receipt"])


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    grounded = target_plan.validate_receipt(value["grounded_plan_receipt"])
    fact = bootstrap.validate_receipt(value["grounded_fact_receipt"])
    first = value.get("first_wave_receipt")
    second = value.get("second_wave_receipt")
    budget = cap.validate_budget_receipt(value["outer_physical_budget_receipt"])
    arms = {
        arm: {
            "effective_model_logical_call_count": int(
                value["arm_metrics"][arm]["effective_model_logical_call_count"]
            ),
            "synthesis_attempted": bool(
                value["arm_metrics"][arm]["synthesis_attempted"]
            ),
            "model_success": bool(value["arm_metrics"][arm]["model_success"]),
            "normalizer_status": str(
                value["arm_metrics"][arm]["normalizer_status"]
            ),
        }
        for arm in ARMS
    }
    failures = {
        "plan": value["failure_types"]["plan"],
        "grounded_plan": value["failure_types"]["grounded_plan"],
        "bootstrap": value["failure_types"]["bootstrap"],
        "retrieval": {
            phase: value["failure_types"]["retrieval"][phase]
            for phase in PHASES
        },
        "synthesis": {
            arm: value["failure_types"]["synthesis"][arm] for arm in ARMS
        },
    }
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "planned_query_count": 4,
        "physical_query_count": int(value["physical_query_count"]),
        "physical_fetch_count": int(value["physical_fetch_count"]),
        "physical_model_forward_count": int(
            value["physical_model_forward_count"]
        ),
        "model_provider_request_count": int(
            value["model_provider_request_count"]
        ),
        "model_provider_attempt_count": int(
            value["model_provider_attempt_count"]
        ),
        "system_total_tokens": int(value["system_total_tokens"]),
        "shared_page_count": int(value["shared_page_count"]),
        "control_production_prompt_characters": int(
            value["control_production_prompt_characters"]
        ),
        "candidate_production_prompt_characters": int(
            value["candidate_production_prompt_characters"]
        ),
        "control_prediction_characters": int(
            value["control_prediction_characters"]
        ),
        "candidate_prediction_characters": int(
            value["candidate_prediction_characters"]
        ),
        "first_synthesis_arm": str(value["first_synthesis_arm"]),
        "first_wave_completed": bool(value["first_wave_completed"]),
        "grounded_plan_model_call_attempted": bool(
            value["grounded_plan_model_call_attempted"]
        ),
        "grounded_plan_model_call_success": bool(
            value["grounded_plan_model_call_success"]
        ),
        "grounded_plan_strategy_applied": bool(
            grounded["strategy_applied"]
        ),
        "second_wave_completed": bool(value["second_wave_completed"]),
        "candidate_production_prompt_changed": bool(
            value["candidate_production_prompt_changed"]
        ),
        "both_arms_model_success": bool(value["both_arms_model_success"]),
        "prediction_changed": bool(value["prediction_changed"]),
        "attributable_prediction_change": bool(
            value["attributable_prediction_change"]
        ),
        "unattributable_prediction_change": bool(
            value["unattributable_prediction_change"]
        ),
        "arm_metrics": arms,
        "failure_types": failures,
        "grounded_plan_receipt": copy.deepcopy(grounded),
        "grounded_fact_receipt": copy.deepcopy(fact),
        "first_wave_receipt": copy.deepcopy(first),
        "second_wave_receipt": copy.deepcopy(second),
        "outer_physical_budget_receipt": copy.deepcopy(budget),
        "one_visible_plan_and_one_joint_grounded_plan_call_shared_by_both_arms": True,
        "both_arms_share_queries_search_responses_fetched_pages_and_page_bytes": True,
        "candidate_only_treatment_is_equal_length_quote_verified_fact_prefix": True,
        "same_forward_first_wave_exact_quote_source_binding_required": True,
        "invalid_conflicting_or_unrenderable_fact_is_parent_prompt_noop": True,
        "query4_fetch14_model4_physical_caps_enforced_before_effect": True,
        "page_text_treated_as_untrusted_data": True,
        "additional_model_call_for_fact_proposal": False,
        "contains_question_query_url_title_page_quote_record_identity_field_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    grounded = copied.get("grounded_plan_receipt")
    fact = copied.get("grounded_fact_receipt")
    first = copied.get("first_wave_receipt")
    second = copied.get("second_wave_receipt")
    budget = copied.get("outer_physical_budget_receipt")
    arms = copied.get("arm_metrics")
    failures = copied.get("failure_types")
    counts = (
        "planned_query_count",
        "physical_query_count",
        "physical_fetch_count",
        "physical_model_forward_count",
        "model_provider_request_count",
        "model_provider_attempt_count",
        "system_total_tokens",
        "shared_page_count",
        "control_production_prompt_characters",
        "candidate_production_prompt_characters",
        "control_prediction_characters",
        "candidate_prediction_characters",
        "positive_signed_credit_count",
    )
    dynamic = (
        "first_wave_completed",
        "grounded_plan_model_call_attempted",
        "grounded_plan_model_call_success",
        "grounded_plan_strategy_applied",
        "second_wave_completed",
        "candidate_production_prompt_changed",
        "both_arms_model_success",
        "prediction_changed",
        "attributable_prediction_change",
        "unattributable_prediction_change",
    )
    true_flags = (
        "one_visible_plan_and_one_joint_grounded_plan_call_shared_by_both_arms",
        "both_arms_share_queries_search_responses_fetched_pages_and_page_bytes",
        "candidate_only_treatment_is_equal_length_quote_verified_fact_prefix",
        "same_forward_first_wave_exact_quote_source_binding_required",
        "invalid_conflicting_or_unrenderable_fact_is_parent_prompt_noop",
        "query4_fetch14_model4_physical_caps_enforced_before_effect",
        "page_text_treated_as_untrusted_data",
    )
    false_flags = (
        "additional_model_call_for_fact_proposal",
        "contains_question_query_url_title_page_quote_record_identity_field_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *counts,
        *dynamic,
        "first_synthesis_arm",
        "arm_metrics",
        "failure_types",
        "grounded_plan_receipt",
        "grounded_fact_receipt",
        "first_wave_receipt",
        "second_wave_receipt",
        "outer_physical_budget_receipt",
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
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
            for name in counts
        )
        or any(not isinstance(copied.get(name), bool) for name in dynamic)
        or copied["planned_query_count"] != 4
        or copied["physical_query_count"] > cap.QUERY_CAP
        or copied["physical_fetch_count"] > cap.FETCH_CAP
        or copied["physical_model_forward_count"] > cap.MODEL_CAP
        or copied["model_provider_request_count"]
        > copied["physical_model_forward_count"]
        or copied["model_provider_attempt_count"]
        < copied["model_provider_request_count"]
        or set(arms or {}) != set(ARMS)
        or copied["physical_model_forward_count"]
        != 1
        + int(copied["grounded_plan_model_call_attempted"])
        + sum(int(arms[arm]["synthesis_attempted"]) for arm in ARMS)
        or copied["control_production_prompt_characters"]
        != copied["candidate_production_prompt_characters"]
        or copied["positive_signed_credit_count"] != 0
        or copied.get("first_synthesis_arm") not in {*ARMS, "none"}
        or not isinstance(grounded, Mapping)
        or target_plan.validate_receipt(grounded) != dict(grounded)
        or not isinstance(fact, Mapping)
        or bootstrap.validate_receipt(fact) != dict(fact)
        or copied["grounded_plan_model_call_attempted"]
        is not grounded["model_call_attempted"]
        or copied["grounded_plan_strategy_applied"]
        is not grounded["strategy_applied"]
        or copied["candidate_production_prompt_changed"]
        is not fact["candidate_production_prompt_changed"]
        or fact["additional_model_call_count"] != 0
        or fact["positive_signed_credit_count"] != 0
        or (first is not None and shared.validate_first_receipt(first) != dict(first))
        or (
            second is not None
            and frontier.validate_second_wave_receipt(second) != dict(second)
        )
        or copied["first_wave_completed"] is not (first is not None)
        or copied["second_wave_completed"] is not (second is not None)
        or copied["second_wave_completed"] and not copied["first_wave_completed"]
        or copied["grounded_plan_model_call_success"]
        and not copied["grounded_plan_model_call_attempted"]
        or not isinstance(budget, Mapping)
        or cap.validate_budget_receipt(budget) != dict(budget)
        or copied["physical_query_count"] != budget["query_admitted_count"]
        or copied["physical_fetch_count"] != budget["fetch_admitted_count"]
        or copied["physical_model_forward_count"] != budget["model_admitted_count"]
        or budget["query_rejected_count"]
        + budget["fetch_rejected_count"]
        + budget["model_rejected_count"]
        != 0
        or any(
            not isinstance(arms[arm], Mapping)
            or set(arms[arm]) != metric_keys
            or isinstance(
                arms[arm].get("effective_model_logical_call_count"), bool
            )
            or not isinstance(
                arms[arm].get("effective_model_logical_call_count"), int
            )
            or arms[arm]["effective_model_logical_call_count"]
            != 1
            + int(copied["grounded_plan_model_call_attempted"])
            + int(arms[arm]["synthesis_attempted"])
            or arms[arm]["effective_model_logical_call_count"] > 3
            or not isinstance(arms[arm].get("synthesis_attempted"), bool)
            or not isinstance(arms[arm].get("model_success"), bool)
            or arms[arm]["model_success"] and not arms[arm]["synthesis_attempted"]
            or arms[arm].get("normalizer_status")
            not in {"not_attempted", "exact", "normalized", "unrecoverable"}
            for arm in ARMS
        )
        or copied["both_arms_model_success"]
        is not all(arms[arm]["model_success"] for arm in ARMS)
        or (copied["first_synthesis_arm"] == "none")
        is not (not any(arms[arm]["synthesis_attempted"] for arm in ARMS))
        or copied["first_synthesis_arm"] in ARMS
        and not all(arms[arm]["synthesis_attempted"] for arm in ARMS)
        or not isinstance(failures, Mapping)
        or set(failures)
        != {"plan", "grounded_plan", "bootstrap", "retrieval", "synthesis"}
        or set(failures.get("retrieval") or {}) != set(PHASES)
        or set(failures.get("synthesis") or {}) != set(ARMS)
        or any(
            item is not None
            and (not isinstance(item, str) or not item or len(item) > 128)
            for name, item in failures.items()
            if name not in {"retrieval", "synthesis"}
        )
        or any(
            item is not None
            and (not isinstance(item, str) or not item or len(item) > 128)
            for group in (failures["retrieval"], failures["synthesis"])
            for item in group.values()
        )
        or copied["attributable_prediction_change"]
        is not bool(
            copied["candidate_production_prompt_changed"]
            and copied["both_arms_model_success"]
            and copied["prediction_changed"]
        )
        or copied["unattributable_prediction_change"]
        is not bool(
            copied["prediction_changed"]
            and not copied["attributable_prediction_change"]
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.49 paired receipt drifted")
    return copied


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: cap.HardCappedModelLimiter,
    searches: Mapping[str, cap.HardCappedSearchClient],
    limits: score.ScoreFirstLimits,
    budget: cap.PhysicalEffectBudget,
    arm_order: Sequence[str] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    started = monotonic()
    visible = score.validate_visible_task(task)
    if not isinstance(budget, cap.PhysicalEffectBudget):
        raise ValueError("V2.53.49 requires one physical effect budget")
    initial_budget = cap.validate_budget_receipt(budget.receipt())
    if any(
        initial_budget[name] != 0
        for name in (
            "query_requested_count",
            "fetch_requested_count",
            "model_requested_count",
        )
    ):
        raise ValueError("V2.53.49 requires a pristine physical budget")
    if (
        not isinstance(model, cap.HardCappedModelLimiter)
        or model._budget is not budget
        or not isinstance(searches, Mapping)
        or set(searches) != set(PHASES)
        or any(
            not isinstance(searches[phase], cap.HardCappedSearchClient)
            or searches[phase]._budget is not budget
            or searches[phase]._phase != phase
            for phase in PHASES
        )
        or len({id(searches[phase]) for phase in PHASES}) != len(PHASES)
    ):
        raise ValueError("V2.53.49 hard-capped client wiring drifted")
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
        raise ValueError("V2.53.49 production-shaped logical budget drifted")
    order = tuple(arm_order or _arm_order(visible["opaque_id"]))
    if len(order) != 2 or set(order) != set(ARMS):
        raise ValueError("V2.53.49 arm order drifted")

    model_before = counters._counter(model, counters._MODEL_COUNTERS)
    search_before = {
        phase: counters._counter(searches[phase], counters._SEARCH_COUNTERS)
        for phase in PHASES
    }
    observers = {
        phase: compact._EffectObserver(searches[phase]) for phase in PHASES
    }
    failures: dict[str, Any] = {
        "plan": None,
        "grounded_plan": None,
        "bootstrap": None,
        "retrieval": {phase: None for phase in PHASES},
        "synthesis": {arm: None for arm in ARMS},
    }
    plan = schema.validated_exact_plan({}, visible["question"], limits)
    try:
        response = model.complete(
            score.PLAN_SYSTEM,
            score.PLAN_USER.format(
                question=visible["question"], query_limit=limits.search_queries
            ),
            max_output_tokens=limits.plan_output_tokens,
            json_mode=True,
        )
        plan = schema.validated_exact_plan(
            parse_json_object(counters._model_text(response)),
            visible["question"],
            limits,
        )
    except BaseException as exc:
        failures["plan"] = _safe_failure(exc)

    queries = list(plan["queries"])
    first: dict[str, Any] | None = None
    second: dict[str, Any] | None = None
    first_pages: list[dict[str, str]] = []
    try:
        first = shared._run_first_wave(
            queries[:2],
            search=observers[FIRST_PHASE],
            search_results_per_query=limits.search_results_per_query,
        )
        first_pages = counters._pages(first["page_batches"])
    except BaseException as exc:
        failures["retrieval"][FIRST_PHASE] = _safe_failure(exc)

    prepared = target_plan.prepare_plan(
        visible["question"], plan["columns"], queries, first_pages
    )
    grounded_output = ""
    grounded_attempted = bool(first_pages)
    grounded_success = False
    if grounded_attempted:
        try:
            response = model.complete(
                bootstrap.joint_system(str(prepared["system"])),
                str(prepared["user"]),
                max_output_tokens=target_plan.PLAN_OUTPUT_TOKEN_CAP,
                json_mode=True,
            )
            grounded_output = counters._model_text(response)
            grounded_success = True
        except BaseException as exc:
            failures["grounded_plan"] = _safe_failure(exc)
    parent_grounded = bootstrap.parent_grounded_output(grounded_output)
    grounded = target_plan.select_plan(
        prepared,
        parent_grounded,
        model_call_attempted=grounded_attempted,
    )
    grounded_receipt = grounded["content_free_receipt"]

    empty_second_pages = {arm: [] for arm in frontier.ARMS}
    second_pages: dict[str, list[dict[str, str]]] = copy.deepcopy(
        empty_second_pages
    )
    if first is not None:
        try:
            second = frontier._run_second_wave(
                grounded["queries"],
                search=observers[SECOND_PHASE],
                first_wave_page_batches=first["page_batches"],
                plan=grounded,
                columns=plan["columns"],
                search_results_per_query=limits.search_results_per_query,
                exclude_urls=first["selected_urls"],
            )
            second_pages = {
                arm: copy.deepcopy(second["pages"][arm])
                for arm in frontier.ARMS
            }
        except BaseException as exc:
            failures["retrieval"][SECOND_PHASE] = _safe_failure(exc)
    else:
        failures["retrieval"][SECOND_PHASE] = "SharedFirstWaveFailure"

    pages = _shared_union_pages(first_pages, second_pages)
    evidence = compact._compact_evidence(pages, limits)
    control_user = score.SYNTHESIS_USER.format(
        question=visible["question"],
        columns=json.dumps(plan["columns"], ensure_ascii=False),
        evidence=evidence,
    )
    candidate_user = control_user
    fact_receipt: dict[str, Any]
    try:
        built = bootstrap.build_bootstrap(
            question=visible["question"],
            columns=plan["columns"],
            first_wave_pages=first_pages,
            grounded_model_output=grounded_output,
            production_user=control_user,
            model_call_attempted=grounded_attempted,
        )
        fact_receipt = bootstrap.validate_receipt(
            built["content_free_receipt"]
        )
        candidate_user = str(built["candidate_production_user"])
    except BaseException as exc:
        failures["bootstrap"] = _safe_failure(exc)
        fact_receipt = _empty_bootstrap_receipt(
            question=visible["question"],
            columns=plan["columns"],
            first_pages=first_pages,
            grounded_output="",
            production_user=control_user,
            attempted=False,
        )
    if len(candidate_user) != len(control_user):
        raise RuntimeError("V2.53.49 production prompt length drifted")

    users = {CONTROL_ARM: control_user, CANDIDATE_ARM: candidate_user}
    predictions = {arm: counters._fallback(plan["columns"]) for arm in ARMS}
    attempted = {arm: False for arm in ARMS}
    success = {arm: False for arm in ARMS}
    normalizer = {arm: "not_attempted" for arm in ARMS}
    synthesis_order: list[str] = []
    if pages:
        for arm in order:
            attempted[arm] = True
            synthesis_order.append(arm)
            try:
                response = model.complete(
                    score.SYNTHESIS_SYSTEM,
                    users[arm],
                    max_output_tokens=limits.synthesis_output_tokens,
                    json_mode=False,
                )
                parsed, status = robust._normalize_synthesis(
                    counters._model_text(response),
                    plan["columns"],
                    visible["question"],
                )
                normalizer[arm] = status
                if parsed is None:
                    raise ValueError("V2.53.49 synthesis table contract failed")
                predictions[arm] = parsed
                success[arm] = True
            except BaseException as exc:
                normalizer[arm] = "unrecoverable"
                failures["synthesis"][arm] = _safe_failure(exc)

    model_cost = counters._delta(
        counters._counter(model, counters._MODEL_COUNTERS), model_before
    )
    search_cost = {
        phase: counters._delta(
            counters._counter(searches[phase], counters._SEARCH_COUNTERS),
            search_before[phase],
        )
        for phase in PHASES
    }
    cost = {
        "model": model_cost,
        "search": search_cost,
        "system_total_tokens": model_cost["total_tokens"]
        + sum(search_cost[phase]["total_tokens"] for phase in PHASES),
    }
    budget_receipt = cap.validate_budget_receipt(budget.receipt())
    changed = predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM]
    treatment = fact_receipt["candidate_production_prompt_changed"]
    both_success = all(success.values())
    attributable = bool(treatment and both_success and changed)
    arm_metrics = {
        arm: {
            "effective_model_logical_call_count": 1
            + int(grounded_attempted)
            + int(attempted[arm]),
            "synthesis_attempted": attempted[arm],
            "model_success": success[arm],
            "normalizer_status": normalizer[arm],
        }
        for arm in ARMS
    }
    receipt = _receipt(
        {
            "physical_query_count": budget_receipt["query_admitted_count"],
            "physical_fetch_count": budget_receipt["fetch_admitted_count"],
            "physical_model_forward_count": budget_receipt["model_admitted_count"],
            "model_provider_request_count": model_cost["requests"],
            "model_provider_attempt_count": model_cost["attempts"],
            "system_total_tokens": cost["system_total_tokens"],
            "shared_page_count": len(pages),
            "control_production_prompt_characters": len(control_user),
            "candidate_production_prompt_characters": len(candidate_user),
            "control_prediction_characters": len(predictions[CONTROL_ARM]),
            "candidate_prediction_characters": len(predictions[CANDIDATE_ARM]),
            "first_synthesis_arm": synthesis_order[0] if synthesis_order else "none",
            "first_wave_completed": first is not None,
            "grounded_plan_model_call_attempted": grounded_attempted,
            "grounded_plan_model_call_success": grounded_success,
            "second_wave_completed": second is not None,
            "candidate_production_prompt_changed": treatment,
            "both_arms_model_success": both_success,
            "prediction_changed": changed,
            "attributable_prediction_change": attributable,
            "unattributable_prediction_change": bool(changed and not attributable),
            "arm_metrics": arm_metrics,
            "failure_types": failures,
            "grounded_plan_receipt": grounded_receipt,
            "grounded_fact_receipt": fact_receipt,
            "first_wave_receipt": None if first is None else first["receipt"],
            "second_wave_receipt": None if second is None else second["receipt"],
            "outer_physical_budget_receipt": budget_receipt,
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
            arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        },
        "model_success": success,
        "normalizer_status": normalizer,
        "failure_types": copy.deepcopy(failures),
        "prediction_changed": changed,
        "candidate_production_prompt_changed": treatment,
        "attributable_prediction_change": attributable,
        "unattributable_prediction_change": bool(changed and not attributable),
        "elapsed_seconds": round(max(0.0, monotonic() - started), 6),
        "cost": cost,
        "content_free_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
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
    cost = copied.get("cost")
    receipt = copied.get("content_free_receipt")
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "opaque_id",
            "status",
            "predictions",
            "prediction_sha256",
            "model_success",
            "normalizer_status",
            "failure_types",
            "prediction_changed",
            "candidate_production_prompt_changed",
            "attributable_prediction_change",
            "unattributable_prediction_change",
            "elapsed_seconds",
            "cost",
            "content_free_receipt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit",
            "benchmark_launch_or_evaluator_authorized",
            "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or not isinstance(copied.get("opaque_id"), str)
        or score.OPAQUE_ID.fullmatch(copied["opaque_id"]) is None
        or set(predictions or {}) != set(ARMS)
        or any(
            not isinstance(predictions[arm], str) or not predictions[arm]
            for arm in ARMS
        )
        or set(hashes or {}) != set(ARMS)
        or any(
            hashes[arm]
            != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or set(success or {}) != set(ARMS)
        or any(not isinstance(success[arm], bool) for arm in ARMS)
        or set(normalizer or {}) != set(ARMS)
        or not isinstance(failures, Mapping)
        or not isinstance(cost, Mapping)
        or set(cost) != {"model", "search", "system_total_tokens"}
        or set(cost.get("model") or {}) != set(counters._MODEL_COUNTERS)
        or set(cost.get("search") or {}) != set(PHASES)
        or any(
            set(cost["search"][phase]) != set(counters._SEARCH_COUNTERS)
            for phase in PHASES
        )
        or cost["system_total_tokens"]
        != cost["model"]["total_tokens"]
        + sum(cost["search"][phase]["total_tokens"] for phase in PHASES)
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["model_provider_request_count"] != cost["model"]["requests"]
        or receipt["model_provider_attempt_count"] != cost["model"]["attempts"]
        or receipt["system_total_tokens"] != cost["system_total_tokens"]
        or receipt["control_prediction_characters"]
        != len(predictions[CONTROL_ARM])
        or receipt["candidate_prediction_characters"]
        != len(predictions[CANDIDATE_ARM])
        or copied.get("prediction_changed")
        is not (predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM])
        or copied.get("candidate_production_prompt_changed")
        is not receipt["candidate_production_prompt_changed"]
        or copied.get("attributable_prediction_change")
        is not receipt["attributable_prediction_change"]
        or copied.get("unattributable_prediction_change")
        is not receipt["unattributable_prediction_change"]
        or failures != receipt["failure_types"]
        or any(
            receipt["arm_metrics"][arm]["model_success"] is not success[arm]
            or receipt["arm_metrics"][arm]["normalizer_status"]
            != normalizer[arm]
            for arm in ARMS
        )
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or copied["elapsed_seconds"] < 0
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.49 paired result drifted")
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
    "SECOND_PHASE",
    "run_paired_task",
    "validate_receipt",
    "validate_result",
]
