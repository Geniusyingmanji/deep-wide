"""Robust-schema, full-budget paired runtime for late-page evidence.

This append-only successor addresses the two content-free control failures
observed in V2.49.83 while preserving its production envelope and paired
counterfactual.  A sentence/bracket-aware parser fixes the visible schema.
When the planning model returns fewer than four unique queries, deterministic
generic official/list/index/database variants derived only from the visible
question and same-pass plan fill the existing four-query cap.  Finally, both
synthesis arms receive the same conservative deterministic table normalizer;
it never rewrites a non-empty factual cell and consumes no model call.

The runtime accepts only ``opaque_id`` and ``question`` plus clients injected
by the caller.  It has no filesystem, environment, process, benchmark-label,
mapping, gold, evaluator, score, reward, historical-result, or credential
capability.  Entropy and information gain remain shadow-only and assign no
signed credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from . import v24982_paired_production_runtime as parent
from .clients import parse_json_object
from .v24259_deterministic_table_normalizer import normalize_candidate_table
from .v24263_global_model_limiter import payload_sha256
from .v24272_two_wave_retrieval import (
    run_two_wave_retrieval,
    validate_retrieval_receipt,
)
from .v24286_visible_schema_runtime import extract_robust_visible_columns
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24799_fixed_full_budget_control import POLICY_VALUES, fixed_full_budget_policy
from .v24981_late_page_bound_fetch import LatePageBoundSearchClient


POLICY_ID = "v24986_robust_schema_full_budget_paired_runtime_v1"
ROLE = "v24986_robust_schema_full_budget_paired_result"
RECEIPT_ROLE = "v24986_content_free_robust_runtime_receipt"
ARMS = parent.ARMS
CONTROL_ARM = parent.CONTROL_ARM
CANDIDATE_ARM = parent.CANDIDATE_ARM


def _normalized_unique(values: Sequence[Any], limit: int) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = score._normalize_text(raw)[:900]
        key = value.casefold()
        if value and key not in seen:
            output.append(value)
            seen.add(key)
        if len(output) >= limit:
            break
    return output


def complete_visible_queries(
    question: str, planned: Sequence[Any], *, limit: int
) -> list[str]:
    """Fill the frozen query cap using visible-only generic source variants."""

    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.49.86 visible question is absent")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 4:
        raise ValueError("V2.49.86 query limit drifted")
    values = _normalized_unique(planned, limit)
    defaults = score._default_queries(question, limit)
    base = values[0] if values else (defaults[0] if defaults else "")
    if not base:
        raise ValueError("V2.49.86 visible query base is absent")
    generic = (
        f"{base[:870]} official source",
        f"{base[:860]} official list index",
        f"{base[:870]} official database",
        *defaults,
    )
    values = _normalized_unique([*values, *generic], limit)
    if len(values) != limit:
        raise RuntimeError("V2.49.86 could not fill the frozen query budget")
    return values


def validated_robust_plan(
    value: Mapping[str, Any], question: str, limits: score.ScoreFirstLimits
) -> dict[str, Any]:
    columns = extract_robust_visible_columns(question)
    raw_columns = value.get("columns")
    provider_columns = (
        [score._normalize_text(item) for item in raw_columns]
        if isinstance(raw_columns, list)
        else []
    )
    provider_columns = [
        item for item in provider_columns if item and len(item) <= 80
    ][:20]
    chosen = columns or provider_columns or ["Result"]
    if len({score._normalize_column(item) for item in chosen}) != len(chosen):
        chosen = ["Result"]
    raw_queries = value.get("queries")
    provider_queries = list(raw_queries) if isinstance(raw_queries, list) else []
    before = _normalized_unique(provider_queries, limits.search_queries)
    queries = complete_visible_queries(
        question, before, limit=limits.search_queries
    )
    language = score._normalize_text(value.get("language")) or (
        "中文" if re.search(r"[\u4e00-\u9fff]", question) else "English"
    )
    return {
        "language": language,
        "columns": chosen,
        "row_target_hint": score._normalize_text(value.get("row_target_hint"))[:200],
        "queries": queries,
        "provider_unique_query_count": len(before),
        "robust_visible_schema_column_count": len(columns),
    }


def _runtime_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "provider_unique_query_count": int(value["provider_unique_query_count"]),
        "completed_query_count": int(value["completed_query_count"]),
        "deterministically_added_query_count": int(
            value["deterministically_added_query_count"]
        ),
        "robust_visible_schema_column_count": int(
            value["robust_visible_schema_column_count"]
        ),
        "normalizer_attempt_count": int(value["normalizer_attempt_count"]),
        "exact_table_count": int(value["exact_table_count"]),
        "normalizer_recovery_count": int(value["normalizer_recovery_count"]),
        "normalizer_unrecoverable_count": int(
            value["normalizer_unrecoverable_count"]
        ),
        "sentence_bracket_quote_aware_visible_schema_used": True,
        "query_completion_uses_visible_question_and_same_pass_plan_only": True,
        "generic_official_list_index_database_suffixes_only": True,
        "query_search_fetch_model_token_context_wall_and_network_byte_caps_preserved": True,
        "normalizer_shared_by_both_arms": True,
        "normalizer_additional_model_calls": 0,
        "normalizer_nonempty_factual_cell_rewritten": False,
        "contains_question_query_url_title_page_record_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_runtime_receipt(output)


def validate_runtime_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "provider_unique_query_count",
        "completed_query_count",
        "deterministically_added_query_count",
        "robust_visible_schema_column_count",
        "normalizer_attempt_count",
        "exact_table_count",
        "normalizer_recovery_count",
        "normalizer_unrecoverable_count",
        "normalizer_additional_model_calls",
    )
    true_flags = (
        "sentence_bracket_quote_aware_visible_schema_used",
        "query_completion_uses_visible_question_and_same_pass_plan_only",
        "generic_official_list_index_database_suffixes_only",
        "query_search_fetch_model_token_context_wall_and_network_byte_caps_preserved",
        "normalizer_shared_by_both_arms",
    )
    false_flags = (
        "normalizer_nonempty_factual_cell_rewritten",
        "contains_question_query_url_title_page_record_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["provider_unique_query_count"] > 4
        or copied["completed_query_count"] != 4
        or copied["deterministically_added_query_count"]
        != 4 - copied["provider_unique_query_count"]
        or copied["robust_visible_schema_column_count"] > 20
        or copied["normalizer_attempt_count"] > 2
        or copied["exact_table_count"]
        + copied["normalizer_recovery_count"]
        + copied["normalizer_unrecoverable_count"]
        != copied["normalizer_attempt_count"]
        or copied["normalizer_additional_model_calls"] != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.86 robust runtime receipt drifted")
    return copied


def _normalize_synthesis(
    text: str, columns: Sequence[str], question: str
) -> tuple[str | None, str]:
    exact, _errors = score.extract_valid_markdown_table(text, columns)
    if exact is not None:
        return exact, "exact"
    marker = "未知" if re.search(r"[\u4e00-\u9fff]", question) else "Unknown"
    normalized, diagnostics = normalize_candidate_table(
        text, columns, unknown_marker=marker
    )
    return normalized, str(diagnostics["status"])


def run_paired_task(
    task: Mapping[str, Any],
    *,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: LatePageBoundSearchClient,
    limits: score.ScoreFirstLimits,
    monotonic: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    visible = score.validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.49.86 requires the bounded global model limiter")
    if not isinstance(search, LatePageBoundSearchClient):
        raise ValueError("V2.49.86 requires the late-page bounded search client")
    limits.validate()
    if (
        limits.wall_seconds != 240
        or limits.model_calls != 3
        or limits.search_queries != 4
        or limits.fetch_targets != 10
        or limits.evidence_chars != 60_000
        or limits.page_chars != 5_000
    ):
        raise ValueError("V2.49.86 production hard budget drifted")
    fixed = fixed_full_budget_policy()
    if POLICY_VALUES != {
        field: getattr(fixed, field) for field in POLICY_VALUES
    }:
        raise RuntimeError("V2.49.86 fixed no-entropy controller drifted")

    model_before = parent._counter(model, parent._MODEL_COUNTERS)
    search_before = parent._counter(search, parent._SEARCH_COUNTERS)
    failures: dict[str, str | None] = {
        "plan": None,
        "retrieval": None,
        CONTROL_ARM: None,
        CANDIDATE_ARM: None,
    }
    logical_model_calls = 0
    plan = validated_robust_plan({}, visible["question"], limits)
    try:
        logical_model_calls += 1
        response = model.complete(
            score.PLAN_SYSTEM,
            score.PLAN_USER.format(
                question=visible["question"], query_limit=limits.search_queries
            ),
            max_output_tokens=limits.plan_output_tokens,
            json_mode=True,
        )
        plan = validated_robust_plan(
            parse_json_object(parent._model_text(response)),
            visible["question"],
            limits,
        )
    except BaseException as exc:
        failures["plan"] = parent._safe_failure(exc)

    queries = list(plan["queries"])
    retrieval: dict[str, Any] | None = None
    pages: list[dict[str, str]] = []
    try:
        retrieval = run_two_wave_retrieval(
            queries,
            search=search,
            required_column_count=len(plan["columns"]),
            explicit_row_target=0,
            search_results_per_query=limits.search_results_per_query,
            policy=fixed,
            monotonic=monotonic,
        )
        validate_retrieval_receipt(retrieval["receipt"])
        pages = parent._pages(retrieval["page_batches"])
    except BaseException as exc:
        failures["retrieval"] = parent._safe_failure(exc)

    evidence = {
        CONTROL_ARM: "No usable web material was retrieved within budget.",
        CANDIDATE_ARM: "No usable web material was retrieved within budget.",
    }
    if pages:
        try:
            for arm in ARMS:
                evidence[arm] = parent._evidence(
                    pages, search=search, limits=limits, arm=arm
                )
        except BaseException as exc:
            failures["retrieval"] = failures["retrieval"] or parent._safe_failure(exc)
            pages = []

    predictions = {arm: parent._fallback(plan["columns"]) for arm in ARMS}
    success = {arm: False for arm in ARMS}
    normalizer_statuses: list[str] = []
    if pages:
        for arm in parent._arm_order(visible["opaque_id"]):
            try:
                logical_model_calls += 1
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
                parsed, status = _normalize_synthesis(
                    parent._model_text(response),
                    plan["columns"],
                    visible["question"],
                )
                normalizer_statuses.append(status)
                if parsed is None:
                    raise ValueError("V2.49.86 synthesis table contract failed")
                predictions[arm] = parsed
                success[arm] = True
            except BaseException as exc:
                if len(normalizer_statuses) < logical_model_calls - 1:
                    normalizer_statuses.append("unrecoverable")
                failures[arm] = parent._safe_failure(exc)

    retrieval_receipt = (
        None if retrieval is None else copy.deepcopy(retrieval["receipt"])
    )
    fetch_projection = search.late_page_projection_receipt()
    model_cost = parent._delta(
        parent._counter(model, parent._MODEL_COUNTERS), model_before
    )
    search_cost = parent._delta(
        parent._counter(search, parent._SEARCH_COUNTERS), search_before
    )
    executed_queries = (
        int(retrieval_receipt["total"]["queries_executed"])
        if retrieval_receipt is not None
        else 0
    )
    fetch_attempts = (
        int(retrieval_receipt["total"]["fetches_attempted"])
        if retrieval_receipt is not None
        else int(search_cost["fetch_calls"])
    )
    usable = (
        int(retrieval_receipt["total"]["usable_pages"])
        if retrieval_receipt is not None
        else 0
    )
    content_free = parent._receipt(
        {
            "planned_query_count": len(queries),
            "executed_query_count": executed_queries,
            "fetch_attempt_count": fetch_attempts,
            "usable_page_count": usable,
            "model_logical_call_count": logical_model_calls,
            "model_provider_request_count": model_cost["requests"],
            "model_provider_attempt_count": model_cost["attempts"],
            "control_evidence_characters": len(evidence[CONTROL_ARM]),
            "candidate_evidence_characters": len(evidence[CANDIDATE_ARM]),
            "candidate_changed_page_count": int(
                fetch_projection["candidate_evidence_changed_page_count"]
            ),
            "mechanism_engaged_page_count": int(
                fetch_projection["mechanism_engaged_page_count"]
            ),
            "prediction_changed": predictions[CONTROL_ARM]
            != predictions[CANDIDATE_ARM],
            "both_arms_model_success": all(success.values()),
        }
    )
    provider_count = int(plan["provider_unique_query_count"])
    robust_receipt = _runtime_receipt(
        {
            "provider_unique_query_count": provider_count,
            "completed_query_count": len(queries),
            "deterministically_added_query_count": len(queries) - provider_count,
            "robust_visible_schema_column_count": int(
                plan["robust_visible_schema_column_count"]
            ),
            "normalizer_attempt_count": len(normalizer_statuses),
            "exact_table_count": sum(
                status == "exact" for status in normalizer_statuses
            ),
            "normalizer_recovery_count": sum(
                status == "normalized" for status in normalizer_statuses
            ),
            "normalizer_unrecoverable_count": sum(
                status == "unrecoverable" for status in normalizer_statuses
            ),
        }
    )
    base: dict[str, Any] = {
        "artifact_version": 1,
        "role": parent.ROLE,
        "policy_id": parent.POLICY_ID,
        "opaque_id": visible["opaque_id"],
        "status": "terminal",
        "predictions": predictions,
        "model_success": success,
        "failure_types": failures,
        "prediction_changed": predictions[CONTROL_ARM]
        != predictions[CANDIDATE_ARM],
        "evidence_characters": {arm: len(evidence[arm]) for arm in ARMS},
        "retrieval_receipt": retrieval_receipt,
        "late_page_fetch_receipt": fetch_projection,
        "cost": {"model": model_cost, "search": search_cost},
        "content_free_receipt": content_free,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    base["result_payload_sha256"] = payload_sha256(base)
    parent.validate_result(base)
    result = copy.deepcopy(base)
    result["role"] = ROLE
    result["policy_id"] = POLICY_ID
    result["robust_runtime_receipt"] = robust_receipt
    result["result_payload_sha256"] = payload_sha256(
        {name: value for name, value in result.items() if name != "result_payload_sha256"}
    )
    return validate_result(result)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    robust = copied.get("robust_runtime_receipt")
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(robust, Mapping)
        or validate_runtime_receipt(robust) != dict(robust)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.86 paired result drifted")
    base = copy.deepcopy(copied)
    base.pop("robust_runtime_receipt", None)
    base["role"] = parent.ROLE
    base["policy_id"] = parent.POLICY_ID
    base.pop("result_payload_sha256", None)
    base["result_payload_sha256"] = payload_sha256(base)
    parent.validate_result(base)
    receipt = copied["content_free_receipt"]
    if (
        robust["completed_query_count"] != receipt["planned_query_count"]
        or robust["normalizer_attempt_count"]
        != max(0, receipt["model_logical_call_count"] - 1)
    ):
        raise ValueError("V2.49.86 paired/robust receipt binding drifted")
    return copied


__all__ = [
    "ARMS",
    "CANDIDATE_ARM",
    "CONTROL_ARM",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "ROLE",
    "complete_visible_queries",
    "run_paired_task",
    "validate_result",
    "validate_runtime_receipt",
    "validated_robust_plan",
]
