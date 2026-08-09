"""Shared-first-wave paired runtime for second-wave hybrid queries.

One visible-only planning call produces the completed four-query vector.  The
first two queries and their at-most-six fetched pages execute exactly once and
are reused byte-for-byte by both arms.  Only the two-query, four-fetch second
wave branches: the control keeps completed slots three and four, while the
candidate uses V2.49.95's identity-fields and authority-schema queries.

Each arm therefore retains the production-shaped logical envelope of four
queries, ten fetches, and one synthesis, while the paired experiment performs
at most six physical queries and fourteen physical fetches.  Runtime task input
is exactly ``opaque_id`` and ``question`` plus injected bounded clients.  No
benchmark label, mapping, gold, evaluator, score, reward, historical result, or
credential capability is accepted.  Entropy and information gain assign no
signed credit.
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
from .clients import canonicalize_url, parse_json_object
from .v24263_global_model_limiter import payload_sha256
from .v24269_task_union_discovery import (
    TaskUnionDiscoverySearchClient,
    validate_receipt as validate_discovery_receipt,
)
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24981_late_page_bound_fetch import validate_receipt as validate_fetch_receipt
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient
from .v24995_second_wave_hybrid_queries import (
    build_second_wave_hybrid_queries,
    validate_receipt as validate_query_receipt,
)


POLICY_ID = "v24996_shared_first_wave_second_wave_hybrid_paired_runtime_v1"
ROLE = "v24996_shared_first_wave_paired_runtime_result"
RECEIPT_ROLE = "v24996_content_free_shared_first_wave_paired_receipt"
WAVE_RECEIPT_ROLE = "v24996_content_free_physical_wave_receipt"
SHARED_PHASE = "shared_first_wave"
ARMS = ("legacy_completed_queries", "second_wave_hybrid_queries")
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = (SHARED_PHASE, *ARMS)

ARM_METRIC_KEYS = frozenset(
    {
        "planned_queries",
        "executed_queries",
        "union_sources",
        "query_local_results",
        "action_sources",
        "query_local_mapping_failures",
        "unrecoverable_search_failures",
        "excluded_shared_sources",
        "fetch_attempts",
        "usable_pages",
        "projected_pages",
        "discovered_records",
        "admissible_records",
        "retained_records",
        "evidence_characters",
        "synthesis_attempted",
        "model_success",
        "normalizer_status",
    }
)


def _arm_order(opaque_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"v24996:{opaque_id}".encode()).digest()[0]
    return ARMS if digest % 2 == 0 else ARMS[::-1]


def _match_evidence(values: Mapping[str, str]) -> dict[str, str]:
    if set(values) != set(ARMS):
        raise ValueError("V2.49.96 evidence arm drifted")
    maximum = max(len(str(values[arm])) for arm in ARMS)
    return {
        arm: str(values[arm]) + " " * (maximum - len(str(values[arm])))
        for arm in ARMS
    }


def _usable_pages(batches: object) -> int:
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return 0
    return sum(
        bool(str(result.get("raw_content") or result.get("content") or "").strip())
        for batch in batches
        if isinstance(batch, Mapping)
        for result in (batch.get("results") or [])
        if isinstance(result, Mapping)
    )


def _phase_receipt(
    *,
    phase: str,
    query_cap: int,
    fetch_cap: int,
    discovery: Mapping[str, Any],
    fetch: Mapping[str, Any],
    pre_exclusion_sources: int,
    excluded_shared_sources: int,
    admitted_sources: int,
    usable_pages: int,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": WAVE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "phase": phase,
        "query_cap": int(query_cap),
        "fetch_cap": int(fetch_cap),
        "executed_queries": int(discovery["logical_query_count"]),
        "query_local_results": int(discovery["raw_query_local_result_count"]),
        "action_sources": int(discovery["raw_action_source_count"]),
        "query_local_mapping_failures": int(
            discovery["raw_query_local_mapping_failure_count"]
        ),
        "unrecoverable_search_failures": int(
            discovery["raw_unrecoverable_failure_count"]
        ),
        "union_sources": int(discovery["union_source_count"]),
        "pre_exclusion_sources": int(pre_exclusion_sources),
        "excluded_shared_sources": int(excluded_shared_sources),
        "admitted_sources": int(admitted_sources),
        "fetch_attempts": int(discovery["fetch_requested_source_count"]),
        "usable_pages": int(usable_pages),
        "projected_pages": int(fetch["projected_page_count"]),
        "discovered_records": int(fetch["discovered_record_count"]),
        "admissible_records": int(fetch["admissible_record_count"]),
        "retained_records": int(fetch["retained_record_count"]),
        "stable_first_seen_selection_without_content_score_or_metadata": True,
        "shared_source_urls_excluded_before_delta_fetch_cap": True,
        "provider_narrative_or_snippet_forwarded": False,
        "fetched_page_text_is_only_active_evidence": True,
        "contains_question_query_url_host_page_record_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
        "discovery_receipt": copy.deepcopy(dict(discovery)),
        "fetch_receipt": copy.deepcopy(dict(fetch)),
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_wave_receipt(value)


def validate_wave_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    discovery = copied.get("discovery_receipt")
    fetch = copied.get("fetch_receipt")
    counts = (
        "query_cap",
        "fetch_cap",
        "executed_queries",
        "query_local_results",
        "action_sources",
        "query_local_mapping_failures",
        "unrecoverable_search_failures",
        "union_sources",
        "pre_exclusion_sources",
        "excluded_shared_sources",
        "admitted_sources",
        "fetch_attempts",
        "usable_pages",
        "projected_pages",
        "discovered_records",
        "admissible_records",
        "retained_records",
    )
    true_flags = (
        "stable_first_seen_selection_without_content_score_or_metadata",
        "shared_source_urls_excluded_before_delta_fetch_cap",
        "fetched_page_text_is_only_active_evidence",
    )
    false_flags = (
        "provider_narrative_or_snippet_forwarded",
        "contains_question_query_url_host_page_record_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "phase",
        *counts,
        *true_flags,
        *false_flags,
        "discovery_receipt",
        "fetch_receipt",
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != WAVE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("phase") not in PHASES
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["query_cap"] != 2
        or copied["fetch_cap"]
        != (6 if copied["phase"] == SHARED_PHASE else 4)
        or copied["executed_queries"] != 2
        or copied["fetch_attempts"] > copied["fetch_cap"]
        or copied["admitted_sources"] != copied["fetch_attempts"]
        or copied["usable_pages"] > copied["fetch_attempts"]
        or copied["projected_pages"] > copied["fetch_attempts"]
        or copied["admissible_records"] > copied["discovered_records"]
        or copied["retained_records"] > copied["admissible_records"]
        or copied["pre_exclusion_sources"] != copied["union_sources"]
        or copied["excluded_shared_sources"] > copied["pre_exclusion_sources"]
        or copied["admitted_sources"]
        > copied["pre_exclusion_sources"] - copied["excluded_shared_sources"]
        or (copied["phase"] == SHARED_PHASE and copied["excluded_shared_sources"])
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or not isinstance(discovery, Mapping)
        or not isinstance(fetch, Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.96 physical wave receipt drifted")
    validate_discovery_receipt(discovery)
    validate_fetch_receipt(fetch)
    if (
        discovery["logical_query_count"] != copied["executed_queries"]
        or discovery["raw_query_local_result_count"]
        != copied["query_local_results"]
        or discovery["raw_action_source_count"] != copied["action_sources"]
        or discovery["raw_query_local_mapping_failure_count"]
        != copied["query_local_mapping_failures"]
        or discovery["raw_unrecoverable_failure_count"]
        != copied["unrecoverable_search_failures"]
        or discovery["union_source_count"] != copied["union_sources"]
        or discovery["fetch_requested_source_count"] != copied["fetch_attempts"]
        or discovery["fetch_usable_page_count"] != copied["usable_pages"]
        or fetch["fetch_calls_snapshot"] != copied["fetch_attempts"]
        or fetch["projected_page_count"] != copied["projected_pages"]
        or fetch["discovered_record_count"] != copied["discovered_records"]
        or fetch["admissible_record_count"] != copied["admissible_records"]
        or fetch["retained_record_count"] != copied["retained_records"]
    ):
        raise ValueError("V2.49.96 physical wave nested receipt drifted")
    return copied


def _run_wave(
    queries: Sequence[str],
    *,
    phase: str,
    search: Any,
    fetch_cap: int,
    search_results_per_query: int,
    exclude_urls: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    if (
        phase not in PHASES
        or len(queries) != 2
        or fetch_cap != (6 if phase == SHARED_PHASE else 4)
        or search_results_per_query != 3
    ):
        raise ValueError("V2.49.96 physical wave boundary drifted")
    union = TaskUnionDiscoverySearchClient(search)
    batches = union.search_many(
        list(queries),
        max_results=search_results_per_query,
        search_depth="advanced",
        include_raw_content=False,
    )
    leads = score._lead_requests(batches, 1_000_000)
    filtered: list[dict[str, str]] = []
    excluded = 0
    for lead in leads:
        canonical = canonicalize_url(str(lead.get("url") or ""))
        if canonical and canonical in exclude_urls:
            excluded += 1
            continue
        filtered.append(lead)
    admitted = filtered[:fetch_cap]
    pages = union.fetch_urls(admitted) if admitted else []
    discovery = union.receipt()
    fetch = search.late_page_projection_receipt()
    receipt = _phase_receipt(
        phase=phase,
        query_cap=2,
        fetch_cap=fetch_cap,
        discovery=discovery,
        fetch=fetch,
        pre_exclusion_sources=len(leads),
        excluded_shared_sources=excluded,
        admitted_sources=len(admitted),
        usable_pages=_usable_pages(pages),
    )
    return {
        "receipt": receipt,
        "page_batches": pages,
        "selected_urls": frozenset(
            canonicalize_url(str(item.get("url") or ""))
            for item in admitted
            if canonicalize_url(str(item.get("url") or ""))
        ),
    }


def _empty_arm_metric() -> dict[str, Any]:
    return {
        "planned_queries": 4,
        "executed_queries": 0,
        "union_sources": 0,
        "query_local_results": 0,
        "action_sources": 0,
        "query_local_mapping_failures": 0,
        "unrecoverable_search_failures": 0,
        "excluded_shared_sources": 0,
        "fetch_attempts": 0,
        "usable_pages": 0,
        "projected_pages": 0,
        "discovered_records": 0,
        "admissible_records": 0,
        "retained_records": 0,
        "evidence_characters": 0,
        "synthesis_attempted": False,
        "model_success": False,
        "normalizer_status": "not_attempted",
    }


def _arm_metric(
    shared: Mapping[str, Any] | None,
    delta: Mapping[str, Any] | None,
    *,
    shared_effect: Mapping[str, int],
    delta_effect: Mapping[str, int],
    evidence_characters: int,
    synthesis_attempted: bool,
    model_success: bool,
    normalizer_status: str,
) -> dict[str, Any]:
    output = _empty_arm_metric()
    additive = (
        "executed_queries",
        "union_sources",
        "query_local_results",
        "action_sources",
        "query_local_mapping_failures",
        "unrecoverable_search_failures",
        "excluded_shared_sources",
        "fetch_attempts",
        "usable_pages",
        "projected_pages",
        "discovered_records",
        "admissible_records",
        "retained_records",
    )
    for receipt, effect in (
        (shared, shared_effect),
        (delta, delta_effect),
    ):
        if receipt is not None:
            for name in additive:
                output[name] += int(receipt[name])
        else:
            output["executed_queries"] += int(effect["logical_queries"])
            output["fetch_attempts"] += int(effect["fetch_requests"])
    output.update(
        {
            "evidence_characters": int(evidence_characters),
            "synthesis_attempted": bool(synthesis_attempted),
            "model_success": bool(model_success),
            "normalizer_status": str(normalizer_status),
        }
    )
    return output


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "provider_unique_query_count": int(value["provider_unique_query_count"]),
        "second_wave_strategy_applied": bool(value["second_wave_strategy_applied"]),
        "first_two_completed_queries_preserved": bool(
            value["first_two_completed_queries_preserved"]
        ),
        "query_vectors_differ_only_in_second_wave": bool(
            value["query_vectors_differ_only_in_second_wave"]
        ),
        "shared_first_wave_completed": bool(value["shared_first_wave_completed"]),
        "shared_prefix_byte_equal_between_arms": bool(
            value["shared_prefix_byte_equal_between_arms"]
        ),
        "shared_prefix_page_count": int(value["shared_prefix_page_count"]),
        "first_delta_arm": str(value["first_delta_arm"]),
        "actual_first_synthesis_arm": str(value["actual_first_synthesis_arm"]),
        "physical_query_count": int(value["physical_query_count"]),
        "physical_fetch_count": int(value["physical_fetch_count"]),
        "model_logical_call_count": int(value["model_logical_call_count"]),
        "model_provider_request_count": int(value["model_provider_request_count"]),
        "model_provider_attempt_count": int(value["model_provider_attempt_count"]),
        "arm_metrics": {
            arm: copy.deepcopy(dict(value["arm_metrics"][arm])) for arm in ARMS
        },
        "prediction_changed": bool(value["prediction_changed"]),
        "both_arms_model_success": bool(value["both_arms_model_success"]),
        "one_shared_visible_only_planning_call": True,
        "one_physical_first_wave_reused_by_both_arms": True,
        "independent_equal_second_wave_budgets": True,
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
    count_fields = (
        "provider_unique_query_count",
        "shared_prefix_page_count",
        "physical_query_count",
        "physical_fetch_count",
        "model_logical_call_count",
        "model_provider_request_count",
        "model_provider_attempt_count",
        "per_arm_logical_query_cap",
        "per_arm_logical_fetch_cap",
        "per_arm_synthesis_call_cap",
        "physical_query_cap",
        "physical_fetch_cap",
    )
    bool_fields = (
        "second_wave_strategy_applied",
        "first_two_completed_queries_preserved",
        "query_vectors_differ_only_in_second_wave",
        "shared_first_wave_completed",
        "shared_prefix_byte_equal_between_arms",
        "prediction_changed",
        "both_arms_model_success",
    )
    true_flags = (
        "one_shared_visible_only_planning_call",
        "one_physical_first_wave_reused_by_both_arms",
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
        or copied["model_logical_call_count"] > 3
        or copied["model_provider_request_count"] > copied["model_logical_call_count"]
        or copied["model_provider_attempt_count"] < copied["model_provider_request_count"]
        or copied["per_arm_logical_query_cap"] != 4
        or copied["per_arm_logical_fetch_cap"] != 10
        or copied["per_arm_synthesis_call_cap"] != 1
        or copied["physical_query_cap"] != 6
        or copied["physical_fetch_cap"] != 14
        or copied.get("first_delta_arm") not in ARMS
        or copied.get("actual_first_synthesis_arm") not in {*ARMS, "none"}
        or copied["query_vectors_differ_only_in_second_wave"]
        is not copied["second_wave_strategy_applied"]
        or copied["shared_prefix_byte_equal_between_arms"]
        is not copied["shared_first_wave_completed"]
        or not isinstance(metrics, Mapping)
        or set(metrics) != set(ARMS)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.96 shared-first-wave receipt drifted")
    attempts = 0
    successes = 0
    evidence: list[int] = []
    for arm in ARMS:
        metric = metrics[arm]
        if not isinstance(metric, Mapping) or set(metric) != ARM_METRIC_KEYS:
            raise ValueError("V2.49.96 arm metric schema drifted")
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
            raise ValueError("V2.49.96 arm metric count drifted")
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
            raise ValueError("V2.49.96 arm metric invariant drifted")
        attempts += int(metric["synthesis_attempted"])
        successes += int(metric["model_success"])
        evidence.append(metric["evidence_characters"])
    if (
        len(set(evidence)) != 1
        or copied["model_logical_call_count"] != 1 + attempts
        or copied["both_arms_model_success"] is not (successes == 2)
        or copied["physical_query_count"]
        > max(metric["executed_queries"] for metric in metrics.values()) + 2
    ):
        raise ValueError("V2.49.96 paired resource accounting drifted")
    ordered = (copied["first_delta_arm"],)
    ordered += tuple(arm for arm in ARMS if arm not in ordered)
    actual = next(
        (arm for arm in ordered if metrics[arm]["synthesis_attempted"]), "none"
    )
    if copied["actual_first_synthesis_arm"] != actual:
        raise ValueError("V2.49.96 synthesis order drifted")
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
        raise ValueError("V2.49.96 requires the bounded global model limiter")
    if (
        not isinstance(searches, Mapping)
        or set(searches) != set(PHASES)
        or any(
            not isinstance(searches[phase], RobustLatePageBoundSearchClient)
            for phase in PHASES
        )
        or len({id(searches[phase]) for phase in PHASES}) != len(PHASES)
    ):
        raise ValueError("V2.49.96 requires three distinct robust search clients")
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
        raise ValueError("V2.49.96 production-shaped budget drifted")
    order = tuple(arm_order or _arm_order(visible["opaque_id"]))
    if len(order) != 2 or set(order) != set(ARMS):
        raise ValueError("V2.49.96 arm order drifted")

    model_before = paired._counter(model, paired._MODEL_COUNTERS)
    search_before = {
        phase: paired._counter(searches[phase], paired._SEARCH_COUNTERS)
        for phase in PHASES
    }
    if any(any(snapshot.values()) for snapshot in search_before.values()):
        raise ValueError("V2.49.96 requires pristine physical search clients")
    observers = {
        phase: compact._EffectObserver(searches[phase]) for phase in PHASES
    }

    failures: dict[str, Any] = {
        "plan": None,
        "retrieval": {phase: None for phase in PHASES},
        "synthesis": {arm: None for arm in ARMS},
    }
    logical_model_calls = 1
    raw_plan: dict[str, Any] = {}
    provider_vector_valid = False
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
        provider_vector_valid = isinstance(raw_plan.get("queries"), list)
        plan = robust.validated_robust_plan(raw_plan, visible["question"], limits)
    except BaseException as exc:
        failures["plan"] = paired._safe_failure(exc)

    completed_queries = list(plan["queries"])
    hybrid = build_second_wave_hybrid_queries(
        visible["question"],
        completed_queries,
        provider_unique_query_count=int(plan["provider_unique_query_count"]),
        provider_query_vector_valid=provider_vector_valid,
    )
    query_receipt = hybrid["content_free_receipt"]
    queries = {
        CONTROL_ARM: completed_queries,
        CANDIDATE_ARM: (
            list(hybrid["queries"])
            if query_receipt["strategy_applied"]
            else completed_queries
        ),
    }
    vectors_differ_only_second = (
        queries[CONTROL_ARM][:2] == queries[CANDIDATE_ARM][:2]
        and queries[CONTROL_ARM][2:] != queries[CANDIDATE_ARM][2:]
    )

    phases: dict[str, dict[str, Any] | None] = {phase: None for phase in PHASES}
    shared_pages: list[dict[str, str]] = []
    delta_pages: dict[str, list[dict[str, str]]] = {arm: [] for arm in ARMS}
    try:
        phases[SHARED_PHASE] = _run_wave(
            completed_queries[:2],
            phase=SHARED_PHASE,
            search=observers[SHARED_PHASE],
            fetch_cap=6,
            search_results_per_query=limits.search_results_per_query,
        )
        shared_pages = paired._pages(phases[SHARED_PHASE]["page_batches"])
    except BaseException as exc:
        failures["retrieval"][SHARED_PHASE] = paired._safe_failure(exc)

    if phases[SHARED_PHASE] is not None:
        shared_urls = phases[SHARED_PHASE]["selected_urls"]
        for arm in order:
            try:
                phases[arm] = _run_wave(
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

    arm_pages = {
        arm: [*shared_pages, *delta_pages[arm]] for arm in ARMS
    }
    shared_prefix_equal = bool(
        phases[SHARED_PHASE] is not None
        and all(
            arm_pages[arm][: len(shared_pages)] == shared_pages for arm in ARMS
        )
    )
    evidence = _match_evidence(
        {
            arm: compact._compact_evidence(arm_pages[arm], limits)
            for arm in ARMS
        }
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
                raise ValueError("V2.49.96 synthesis table contract failed")
            predictions[arm] = parsed
            success[arm] = True
        except BaseException as exc:
            normalizer_status[arm] = "unrecoverable"
            failures["synthesis"][arm] = paired._safe_failure(exc)

    phase_receipts = {
        phase: (
            None
            if phases[phase] is None
            else copy.deepcopy(phases[phase]["receipt"])
        )
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
        arm: _arm_metric(
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
    physical_queries = sum(
        effect["logical_queries"] for effect in physical_effects.values()
    )
    physical_fetches = sum(
        effect["fetch_requests"] for effect in physical_effects.values()
    )
    content_free = _receipt(
        {
            "provider_unique_query_count": plan["provider_unique_query_count"],
            "second_wave_strategy_applied": query_receipt["strategy_applied"],
            "first_two_completed_queries_preserved": query_receipt[
                "first_two_completed_queries_preserved"
            ],
            "query_vectors_differ_only_in_second_wave": vectors_differ_only_second,
            "shared_first_wave_completed": shared_receipt is not None,
            "shared_prefix_byte_equal_between_arms": shared_prefix_equal,
            "shared_prefix_page_count": len(shared_pages),
            "first_delta_arm": order[0],
            "actual_first_synthesis_arm": (
                synthesis_order[0] if synthesis_order else "none"
            ),
            "physical_query_count": physical_queries,
            "physical_fetch_count": physical_fetches,
            "model_logical_call_count": logical_model_calls,
            "model_provider_request_count": model_cost["requests"],
            "model_provider_attempt_count": model_cost["attempts"],
            "arm_metrics": arm_metrics,
            "prediction_changed": predictions[CONTROL_ARM]
            != predictions[CANDIDATE_ARM],
            "both_arms_model_success": all(success.values()),
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
        "prediction_changed": predictions[CONTROL_ARM]
        != predictions[CANDIDATE_ARM],
        "evidence_characters": {arm: len(evidence[arm]) for arm in ARMS},
        "second_wave_query_receipt": copy.deepcopy(query_receipt),
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
    query = copied.get("second_wave_query_receipt")
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
        "second_wave_query_receipt",
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
        or not isinstance(copied.get("opaque_id"), str)
        or set(predictions or {}) != set(ARMS)
        or any(not isinstance(predictions[arm], str) or not predictions[arm] for arm in ARMS)
        or set(successes or {}) != set(ARMS)
        or any(not isinstance(successes[arm], bool) for arm in ARMS)
        or not isinstance(failures, Mapping)
        or set(failures) != {"plan", "retrieval", "synthesis"}
        or not isinstance(failures.get("retrieval"), Mapping)
        or set(failures["retrieval"]) != set(PHASES)
        or not isinstance(failures.get("synthesis"), Mapping)
        or set(failures["synthesis"]) != set(ARMS)
        or any(
            item is not None and (not isinstance(item, str) or not item)
            for item in (
                failures.get("plan"),
                *failures["retrieval"].values(),
                *failures["synthesis"].values(),
            )
        )
        or set(evidence or {}) != set(ARMS)
        or any(
            isinstance(evidence[arm], bool)
            or not isinstance(evidence[arm], int)
            or evidence[arm] < 0
            for arm in ARMS
        )
        or not isinstance(query, Mapping)
        or validate_query_receipt(query) != dict(query)
        or not isinstance(phases, Mapping)
        or set(phases) != set(PHASES)
        or not isinstance(effects, Mapping)
        or set(effects) != set(PHASES)
        or any(
            not isinstance(effects[phase], Mapping)
            or set(effects[phase]) != {"logical_queries", "fetch_requests"}
            or any(
                isinstance(effects[phase].get(name), bool)
                or not isinstance(effects[phase].get(name), int)
                or effects[phase][name] < 0
                for name in ("logical_queries", "fetch_requests")
            )
            or effects[phase]["logical_queries"] > 2
            or effects[phase]["fetch_requests"]
            > (6 if phase == SHARED_PHASE else 4)
            for phase in PHASES
        )
        or not isinstance(costs, Mapping)
        or set(costs) != {"model", "search"}
        or not isinstance(costs.get("model"), Mapping)
        or set(costs["model"]) != set(paired._MODEL_COUNTERS)
        or any(
            isinstance(costs["model"].get(name), bool)
            or not isinstance(costs["model"].get(name), int)
            or costs["model"][name] < 0
            for name in paired._MODEL_COUNTERS
        )
        or not isinstance(costs.get("search"), Mapping)
        or set(costs["search"]) != set(PHASES)
        or any(
            not isinstance(costs["search"][phase], Mapping)
            or set(costs["search"][phase]) != set(paired._SEARCH_COUNTERS)
            or any(
                isinstance(costs["search"][phase].get(name), bool)
                or not isinstance(costs["search"][phase].get(name), int)
                or costs["search"][phase][name] < 0
                for name in paired._SEARCH_COUNTERS
            )
            for phase in PHASES
        )
        or any(
            costs["search"][phase]["fetch_calls"]
            != effects[phase]["fetch_requests"]
            for phase in PHASES
        )
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or query["strategy_applied"] != receipt["second_wave_strategy_applied"]
        or query["provider_unique_query_count"]
        != receipt["provider_unique_query_count"]
        or query["first_two_completed_queries_preserved"]
        != receipt["first_two_completed_queries_preserved"]
        or costs["model"]["requests"] != receipt["model_provider_request_count"]
        or costs["model"]["attempts"] != receipt["model_provider_attempt_count"]
        or copied.get("prediction_changed")
        is not (predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM])
        or receipt["prediction_changed"] != copied["prediction_changed"]
        or receipt["both_arms_model_success"] != all(successes.values())
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.96 shared-first-wave result drifted")
    physical_queries = sum(
        int(effects[phase]["logical_queries"]) for phase in PHASES
    )
    physical_fetches = sum(
        int(effects[phase]["fetch_requests"]) for phase in PHASES
    )
    for phase in PHASES:
        phase_receipt = phases[phase]
        if phase_receipt is not None:
            if not isinstance(phase_receipt, Mapping):
                raise ValueError("V2.49.96 physical wave receipt absent")
            validate_wave_receipt(phase_receipt)
            if failures["retrieval"][phase] is not None:
                raise ValueError("V2.49.96 successful wave retained failure")
            if (
                effects[phase]["logical_queries"]
                != phase_receipt["executed_queries"]
                or effects[phase]["fetch_requests"]
                != phase_receipt["fetch_attempts"]
            ):
                raise ValueError("V2.49.96 physical search cost drifted")
        elif failures["retrieval"][phase] is None:
            raise ValueError("V2.49.96 missing wave without failure")
    if phases[SHARED_PHASE] is None:
        if (
            effects[SHARED_PHASE]["logical_queries"] != 2
            or any(
                phases[arm] is not None
                or effects[arm] != {"logical_queries": 0, "fetch_requests": 0}
                or failures["retrieval"][arm] != "SharedFirstWaveFailure"
                for arm in ARMS
            )
        ):
            raise ValueError("V2.49.96 shared-wave failure boundary drifted")
    elif any(effects[arm]["logical_queries"] != 2 for arm in ARMS):
        raise ValueError("V2.49.96 delta-wave attempt boundary drifted")
    if (
        receipt["physical_query_count"] != physical_queries
        or receipt["physical_fetch_count"] != physical_fetches
        or receipt["shared_first_wave_completed"]
        is not (phases[SHARED_PHASE] is not None)
        or receipt["shared_prefix_byte_equal_between_arms"]
        is not (phases[SHARED_PHASE] is not None)
        or receipt["shared_prefix_page_count"]
        != (
            0
            if phases[SHARED_PHASE] is None
            else phases[SHARED_PHASE]["usable_pages"]
        )
        or evidence != {
            arm: receipt["arm_metrics"][arm]["evidence_characters"]
            for arm in ARMS
        }
        or any(
            successes[arm] != receipt["arm_metrics"][arm]["model_success"]
            for arm in ARMS
        )
    ):
        raise ValueError("V2.49.96 nested accounting drifted")
    shared = phases[SHARED_PHASE]
    for arm in ARMS:
        metric = receipt["arm_metrics"][arm]
        expected_metric = _arm_metric(
            shared,
            phases[arm],
            shared_effect=effects[SHARED_PHASE],
            delta_effect=effects[arm],
            evidence_characters=evidence[arm],
            synthesis_attempted=metric["synthesis_attempted"],
            model_success=successes[arm],
            normalizer_status=metric["normalizer_status"],
        )
        if metric != expected_metric:
            raise ValueError("V2.49.96 logical arm accounting drifted")
        if (
            metric["synthesis_attempted"]
            is not (metric["normalizer_status"] != "not_attempted")
            or (
                not metric["synthesis_attempted"]
                and (
                    successes[arm]
                    or failures["synthesis"][arm] is not None
                )
            )
            or (
                successes[arm]
                and (
                    failures["synthesis"][arm] is not None
                    or metric["normalizer_status"] not in {"exact", "normalized"}
                )
            )
            or (
                metric["synthesis_attempted"]
                and not successes[arm]
                and (
                    failures["synthesis"][arm] is None
                    or metric["normalizer_status"] != "unrecoverable"
                )
            )
        ):
            raise ValueError("V2.49.96 synthesis accounting drifted")
    return copied


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "PHASES",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "SHARED_PHASE",
    "run_paired_task",
    "validate_receipt",
    "validate_result",
    "validate_wave_receipt",
]
