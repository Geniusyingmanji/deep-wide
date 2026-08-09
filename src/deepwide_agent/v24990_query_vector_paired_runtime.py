"""Label-blind paired query-vector mechanism runtime.

This build-only external-gate runtime isolates the V2.49.88 query treatment.
It makes one shared planning call, then compares the inherited V2.49.86
visible-only query completion with four short authority/identity queries.
Each arm receives its own otherwise-identical production-shaped retrieval
budget (four queries and ten fetches), the same robust late-page projector,
the same compact-evidence renderer, and one synthesis call.  Retrieval and
synthesis order are explicitly supplied so an external population can balance
order before outcomes exist.

The doubled *total* retrieval allowance is intentional for a causal external
gate; it is not a production configuration and cannot authorize DeepWideBench,
an evaluator, or a SOTA claim.  Runtime inputs remain exactly ``opaque_id`` and
``question`` plus injected bounded clients.  No label, mapping, gold, score,
reward, historical result, or credential capability is accepted.  Entropy and
information gain assign no signed credit.
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
from .clients import parse_json_object
from .v24263_global_model_limiter import payload_sha256
from .v24272_two_wave_retrieval import (
    run_two_wave_retrieval,
    validate_retrieval_receipt,
)
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24799_fixed_full_budget_control import (
    POLICY_VALUES,
    fixed_full_budget_policy,
)
from .v24981_late_page_bound_fetch import validate_receipt as validate_fetch_receipt
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient
from .v24988_short_authority_queries import (
    build_short_queries,
    validate_receipt as validate_short_query_receipt,
)


POLICY_ID = "v24990_label_blind_query_vector_paired_runtime_v1"
ROLE = "v24990_query_vector_paired_runtime_result"
RECEIPT_ROLE = "v24990_content_free_query_vector_paired_receipt"
ARMS = ("legacy_completed_queries", "short_authority_identity_queries")
CONTROL_ARM, CANDIDATE_ARM = ARMS
ARM_METRIC_KEYS = frozenset(
    {
        "planned_queries",
        "executed_queries",
        "sources_discovered",
        "query_local_results",
        "action_sources",
        "query_local_mapping_failures",
        "unrecoverable_search_failures",
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


class _EffectObserver:
    """Content-free logical-effect counter around one pristine search client."""

    def __init__(self, inner: RobustLatePageBoundSearchClient) -> None:
        self.inner = inner
        self.search_invocations = 0
        self.logical_query_count = 0
        self.fetch_invocations = 0
        self.fetch_request_count = 0

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def search_many(self, queries: Sequence[str], **kwargs: Any) -> Any:
        values = list(queries)
        self.search_invocations += 1
        self.logical_query_count += len(values)
        return self.inner.search_many(values, **kwargs)

    def fetch_urls(self, requests: Sequence[Mapping[str, str]]) -> Any:
        values = list(requests)
        self.fetch_invocations += 1
        self.fetch_request_count += len(values)
        return self.inner.fetch_urls(values)


def _arm_order(opaque_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"v24990:{opaque_id}".encode()).digest()[0]
    return ARMS if digest % 2 == 0 else ARMS[::-1]


def _compact_evidence(
    pages: Sequence[Mapping[str, str]], limits: score.ScoreFirstLimits
) -> str:
    records: list[str] = []
    used = 0
    for ordinal, page in enumerate(pages, 1):
        content = str(page.get("content") or "").replace("\x00", "").strip()
        if not content:
            continue
        record = (
            f"[E{ordinal:04d}] kind=fetched_page\n"
            f"title={score._normalize_text(page.get('title'))[:500]}\n"
            f"url={page.get('url', '')}\ncontent={content[:limits.page_chars]}"
        )
        separator = "\n\n" if records else ""
        if used + len(separator) + len(record) > limits.evidence_chars:
            break
        records.append(record)
        used += len(separator) + len(record)
    return (
        "\n\n".join(records)
        if records
        else "No usable web material was retrieved within budget."
    )


def _match_evidence(values: Mapping[str, str]) -> dict[str, str]:
    if set(values) != set(ARMS):
        raise ValueError("V2.49.90 evidence arm drifted")
    maximum = max(len(values[arm]) for arm in ARMS)
    return {
        arm: str(values[arm]) + " " * (maximum - len(str(values[arm])))
        for arm in ARMS
    }


def _metric(value: Mapping[str, Any]) -> dict[str, Any]:
    output = {
        name: int(value[name])
        for name in ARM_METRIC_KEYS
        if name
        not in {"synthesis_attempted", "model_success", "normalizer_status"}
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
        "short_query_strategy_applied": bool(value["short_query_strategy_applied"]),
        "query_vectors_differ": bool(value["query_vectors_differ"]),
        "first_retrieval_arm": str(value["first_retrieval_arm"]),
        "actual_first_synthesis_arm": str(value["actual_first_synthesis_arm"]),
        "model_logical_call_count": int(value["model_logical_call_count"]),
        "model_provider_request_count": int(value["model_provider_request_count"]),
        "model_provider_attempt_count": int(value["model_provider_attempt_count"]),
        "arm_metrics": {
            arm: _metric(value["arm_metrics"][arm]) for arm in ARMS
        },
        "prediction_changed": bool(value["prediction_changed"]),
        "both_arms_model_success": bool(value["both_arms_model_success"]),
        "one_shared_planning_call": True,
        "independent_equal_per_arm_retrieval_budgets": True,
        "per_arm_query_cap": 4,
        "per_arm_fetch_cap": 10,
        "per_arm_synthesis_call_cap": 1,
        "same_robust_compact_projector_and_evidence_renderer": True,
        "same_columns_prompt_model_output_cap_and_task_deadline": True,
        "retrieval_and_synthesis_order_frozen_before_outcomes": True,
        "external_gate_total_retrieval_budget_doubles_production": True,
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
    true_flags = (
        "one_shared_planning_call",
        "independent_equal_per_arm_retrieval_budgets",
        "same_robust_compact_projector_and_evidence_renderer",
        "same_columns_prompt_model_output_cap_and_task_deadline",
        "retrieval_and_synthesis_order_frozen_before_outcomes",
        "external_gate_total_retrieval_budget_doubles_production",
    )
    false_flags = (
        "production_runtime_or_exact220_authorized",
        "contains_question_query_url_title_page_record_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    count_fields = (
        "provider_unique_query_count",
        "model_logical_call_count",
        "model_provider_request_count",
        "model_provider_attempt_count",
        "per_arm_query_cap",
        "per_arm_fetch_cap",
        "per_arm_synthesis_call_cap",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "provider_unique_query_count",
        "short_query_strategy_applied",
        "query_vectors_differ",
        "first_retrieval_arm",
        "actual_first_synthesis_arm",
        "model_logical_call_count",
        "model_provider_request_count",
        "model_provider_attempt_count",
        "arm_metrics",
        "prediction_changed",
        "both_arms_model_success",
        *true_flags,
        "per_arm_query_cap",
        "per_arm_fetch_cap",
        "per_arm_synthesis_call_cap",
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
        or copied["provider_unique_query_count"] > 4
        or copied["model_logical_call_count"] > 3
        or copied["model_provider_request_count"]
        > copied["model_logical_call_count"]
        or copied["model_provider_attempt_count"]
        < copied["model_provider_request_count"]
        or copied["per_arm_query_cap"] != 4
        or copied["per_arm_fetch_cap"] != 10
        or copied["per_arm_synthesis_call_cap"] != 1
        or not isinstance(copied.get("short_query_strategy_applied"), bool)
        or not isinstance(copied.get("query_vectors_differ"), bool)
        or copied.get("first_retrieval_arm") not in ARMS
        or copied.get("actual_first_synthesis_arm") not in {*ARMS, "none"}
        or not isinstance(copied.get("prediction_changed"), bool)
        or not isinstance(copied.get("both_arms_model_success"), bool)
        or not isinstance(metrics, Mapping)
        or set(metrics) != set(ARMS)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.90 query-vector receipt drifted")
    attempted = 0
    successes = 0
    evidence_counts: list[int] = []
    for arm in ARMS:
        metric = metrics[arm]
        if not isinstance(metric, Mapping) or set(metric) != ARM_METRIC_KEYS:
            raise ValueError("V2.49.90 arm metric schema drifted")
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
            raise ValueError("V2.49.90 arm metric count drifted")
        if (
            metric["planned_queries"] != 4
            or metric["executed_queries"] > 4
            or metric["sources_discovered"] != metric["fetch_attempts"]
            or metric["query_local_mapping_failures"]
            > metric["executed_queries"]
            or metric["unrecoverable_search_failures"]
            > metric["executed_queries"]
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
            raise ValueError("V2.49.90 arm metric invariant drifted")
        attempted += int(metric["synthesis_attempted"])
        successes += int(metric["model_success"])
        evidence_counts.append(metric["evidence_characters"])
    if (
        len(set(evidence_counts)) != 1
        or copied["model_logical_call_count"] != 1 + attempted
        or copied["both_arms_model_success"] is not (successes == 2)
    ):
        raise ValueError("V2.49.90 paired resource accounting drifted")
    ordered = (copied["first_retrieval_arm"],)
    ordered += tuple(arm for arm in ARMS if arm not in ordered)
    actual = next(
        (arm for arm in ordered if metrics[arm]["synthesis_attempted"]), "none"
    )
    if copied["actual_first_synthesis_arm"] != actual:
        raise ValueError("V2.49.90 actual synthesis order drifted")
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
        raise ValueError("V2.49.90 requires the bounded global model limiter")
    if (
        not isinstance(searches, Mapping)
        or set(searches) != set(ARMS)
        or any(
            not isinstance(searches[arm], RobustLatePageBoundSearchClient)
            for arm in ARMS
        )
        or searches[CONTROL_ARM] is searches[CANDIDATE_ARM]
    ):
        raise ValueError("V2.49.90 requires two distinct robust search clients")
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
        raise ValueError("V2.49.90 per-arm production-shaped budget drifted")
    fixed = fixed_full_budget_policy()
    if POLICY_VALUES != {field: getattr(fixed, field) for field in POLICY_VALUES}:
        raise RuntimeError("V2.49.90 fixed no-entropy controller drifted")
    order = tuple(arm_order or _arm_order(visible["opaque_id"]))
    if len(order) != 2 or set(order) != set(ARMS):
        raise ValueError("V2.49.90 arm order drifted")

    model_before = paired._counter(model, paired._MODEL_COUNTERS)
    search_before = {
        arm: paired._counter(searches[arm], paired._SEARCH_COUNTERS)
        for arm in ARMS
    }
    if any(any(snapshot.values()) for snapshot in search_before.values()):
        raise ValueError("V2.49.90 requires pristine per-arm search clients")
    observers = {arm: _EffectObserver(searches[arm]) for arm in ARMS}
    failures: dict[str, Any] = {
        "plan": None,
        "retrieval": {arm: None for arm in ARMS},
        "synthesis": {arm: None for arm in ARMS},
    }
    logical_model_calls = 1
    raw_plan: dict[str, Any] = {}
    provider_query_vector_valid = False
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
        provider_query_vector_valid = isinstance(raw_plan.get("queries"), list)
        plan = robust.validated_robust_plan(raw_plan, visible["question"], limits)
    except BaseException as exc:
        failures["plan"] = paired._safe_failure(exc)

    provider_queries = (
        list(raw_plan["queries"])
        if provider_query_vector_valid
        else []
    )
    short = build_short_queries(
        visible["question"],
        provider_queries,
        provider_query_vector_valid=provider_query_vector_valid,
    )
    short_receipt = short["content_free_receipt"]
    queries = {
        CONTROL_ARM: list(plan["queries"]),
        CANDIDATE_ARM: (
            list(short["queries"])
            if short_receipt["strategy_applied"]
            else list(plan["queries"])
        ),
    }
    query_vectors_differ = queries[CONTROL_ARM] != queries[CANDIDATE_ARM]
    retrievals: dict[str, dict[str, Any] | None] = {arm: None for arm in ARMS}
    pages: dict[str, list[dict[str, str]]] = {arm: [] for arm in ARMS}
    for arm in order:
        try:
            retrieval = run_two_wave_retrieval(
                queries[arm],
                search=observers[arm],
                required_column_count=len(plan["columns"]),
                explicit_row_target=0,
                search_results_per_query=limits.search_results_per_query,
                policy=fixed,
                monotonic=monotonic,
            )
            validate_retrieval_receipt(retrieval["receipt"])
            retrievals[arm] = retrieval
            pages[arm] = paired._pages(retrieval["page_batches"])
        except BaseException as exc:
            failures["retrieval"][arm] = paired._safe_failure(exc)

    evidence = _match_evidence(
        {arm: _compact_evidence(pages[arm], limits) for arm in ARMS}
    )
    predictions = {arm: paired._fallback(plan["columns"]) for arm in ARMS}
    success = {arm: False for arm in ARMS}
    attempted = {arm: False for arm in ARMS}
    normalizer_status = {arm: "not_attempted" for arm in ARMS}
    synthesis_order: list[str] = []
    for arm in order:
        if not pages[arm]:
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
                raise ValueError("V2.49.90 synthesis table contract failed")
            predictions[arm] = parsed
            success[arm] = True
        except BaseException as exc:
            normalizer_status[arm] = "unrecoverable"
            failures["synthesis"][arm] = paired._safe_failure(exc)

    retrieval_receipts = {
        arm: (
            None
            if retrievals[arm] is None
            else copy.deepcopy(retrievals[arm]["receipt"])
        )
        for arm in ARMS
    }
    fetch_receipts = {
        arm: searches[arm].late_page_projection_receipt() for arm in ARMS
    }
    search_cost = {
        arm: paired._delta(
            paired._counter(searches[arm], paired._SEARCH_COUNTERS),
            search_before[arm],
        )
        for arm in ARMS
    }
    model_cost = paired._delta(
        paired._counter(model, paired._MODEL_COUNTERS), model_before
    )
    arm_metrics: dict[str, dict[str, Any]] = {}
    for arm in ARMS:
        retrieval_receipt = retrieval_receipts[arm]
        total = retrieval_receipt["total"] if retrieval_receipt is not None else {}
        discovery = (
            retrieval_receipt["discovery_union"]
            if retrieval_receipt is not None
            else {}
        )
        fetch = fetch_receipts[arm]
        arm_metrics[arm] = {
            "planned_queries": len(queries[arm]),
            "executed_queries": int(
                total.get("queries_executed", observers[arm].logical_query_count)
            ),
            "sources_discovered": int(
                total.get("sources_discovered", observers[arm].fetch_request_count)
            ),
            "query_local_results": int(
                discovery.get("raw_query_local_result_count", 0)
            ),
            "action_sources": int(discovery.get("raw_action_source_count", 0)),
            "query_local_mapping_failures": int(
                discovery.get("raw_query_local_mapping_failure_count", 0)
            ),
            "unrecoverable_search_failures": int(
                total.get("unrecoverable_search_failures", 0)
            ),
            "fetch_attempts": int(
                total.get("fetches_attempted", observers[arm].fetch_request_count)
            ),
            "usable_pages": int(
                total.get("usable_pages", fetch["projected_page_count"])
            ),
            "projected_pages": int(fetch["projected_page_count"]),
            "discovered_records": int(fetch["discovered_record_count"]),
            "admissible_records": int(fetch["admissible_record_count"]),
            "retained_records": int(fetch["retained_record_count"]),
            "evidence_characters": len(evidence[arm]),
            "synthesis_attempted": attempted[arm],
            "model_success": success[arm],
            "normalizer_status": normalizer_status[arm],
        }
    content_free = _receipt(
        {
            "provider_unique_query_count": short_receipt[
                "provider_unique_query_count"
            ],
            "short_query_strategy_applied": short_receipt["strategy_applied"],
            "query_vectors_differ": query_vectors_differ,
            "first_retrieval_arm": order[0],
            "actual_first_synthesis_arm": (
                synthesis_order[0] if synthesis_order else "none"
            ),
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
        "short_query_receipt": copy.deepcopy(short_receipt),
        "retrieval_receipts": retrieval_receipts,
        "late_page_fetch_receipts": fetch_receipts,
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
    short = copied.get("short_query_receipt")
    retrievals = copied.get("retrieval_receipts")
    fetches = copied.get("late_page_fetch_receipts")
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
        "short_query_receipt",
        "retrieval_receipts",
        "late_page_fetch_receipts",
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
        or set(failures["retrieval"]) != set(ARMS)
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
        or not isinstance(short, Mapping)
        or validate_short_query_receipt(short) != dict(short)
        or not isinstance(retrievals, Mapping)
        or set(retrievals) != set(ARMS)
        or not isinstance(fetches, Mapping)
        or set(fetches) != set(ARMS)
        or not isinstance(costs, Mapping)
        or set(costs) != {"model", "search"}
        or not isinstance(costs.get("model"), Mapping)
        or not isinstance(costs.get("search"), Mapping)
        or set(costs["search"]) != set(ARMS)
        or set(costs["model"]) != set(paired._MODEL_COUNTERS)
        or any(
            isinstance(costs["model"].get(name), bool)
            or not isinstance(costs["model"].get(name), int)
            or costs["model"][name] < 0
            for name in paired._MODEL_COUNTERS
        )
        or any(
            not isinstance(costs["search"][arm], Mapping)
            or set(costs["search"][arm]) != set(paired._SEARCH_COUNTERS)
            or any(
                isinstance(costs["search"][arm].get(name), bool)
                or not isinstance(costs["search"][arm].get(name), int)
                or costs["search"][arm][name] < 0
                for name in paired._SEARCH_COUNTERS
            )
            for arm in ARMS
        )
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or short["provider_unique_query_count"]
        != receipt["provider_unique_query_count"]
        or short["strategy_applied"]
        != receipt["short_query_strategy_applied"]
        or costs["model"]["requests"]
        != receipt["model_provider_request_count"]
        or costs["model"]["attempts"]
        != receipt["model_provider_attempt_count"]
        or copied.get("prediction_changed")
        is not (predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM])
        or receipt["prediction_changed"] != copied["prediction_changed"]
        or receipt["both_arms_model_success"] != all(successes.values())
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.90 query-vector result drifted")
    for arm in ARMS:
        retrieval = retrievals[arm]
        metric = receipt["arm_metrics"][arm]
        search_cost = costs["search"][arm]
        if retrieval is not None:
            if not isinstance(retrieval, Mapping):
                raise ValueError("V2.49.90 retrieval receipt drifted")
            validate_retrieval_receipt(retrieval)
            if failures["retrieval"][arm] is not None:
                raise ValueError("V2.49.90 successful retrieval retained failure")
            total = retrieval["total"]
            discovery = retrieval["discovery_union"]
            if (
                retrieval["planned_query_count"] != metric["planned_queries"]
                or total["queries_executed"] != metric["executed_queries"]
                or total["sources_discovered"] != metric["sources_discovered"]
                or total["fetches_attempted"] != metric["fetch_attempts"]
                or total["usable_pages"] != metric["usable_pages"]
                or total["unrecoverable_search_failures"]
                != metric["unrecoverable_search_failures"]
                or discovery["raw_query_local_result_count"]
                != metric["query_local_results"]
                or discovery["raw_action_source_count"]
                != metric["action_sources"]
                or discovery["raw_query_local_mapping_failure_count"]
                != metric["query_local_mapping_failures"]
            ):
                raise ValueError("V2.49.90 retrieval/metric binding drifted")
        elif failures["retrieval"][arm] is None:
            raise ValueError("V2.49.90 missing retrieval receipt without failure")
        if (
            not isinstance(fetches[arm], Mapping)
            or validate_fetch_receipt(fetches[arm]) != dict(fetches[arm])
            or search_cost["fetch_calls"] != metric["fetch_attempts"]
            or fetches[arm]["fetch_calls_snapshot"]
            != metric["fetch_attempts"]
            or fetches[arm]["projected_page_count"]
            != metric["projected_pages"]
            or fetches[arm]["discovered_record_count"]
            != metric["discovered_records"]
            or fetches[arm]["admissible_record_count"]
            != metric["admissible_records"]
            or fetches[arm]["retained_record_count"]
            != metric["retained_records"]
            or evidence[arm] != metric["evidence_characters"]
            or successes[arm] != metric["model_success"]
            or metric["synthesis_attempted"]
            is not (metric["normalizer_status"] != "not_attempted")
            or (
                not metric["synthesis_attempted"]
                and (
                    successes[arm]
                    or failures["synthesis"][arm] is not None
                    or metric["normalizer_status"] != "not_attempted"
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
            raise ValueError("V2.49.90 nested arm binding drifted")
    return copied


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "run_paired_task",
    "validate_receipt",
    "validate_result",
]
