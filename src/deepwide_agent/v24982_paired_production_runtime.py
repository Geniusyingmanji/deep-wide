"""Production-isomorphic paired runtime for late-page bound evidence.

One visible task consumes the unchanged V2.48.57 hard envelope: one planning
model call, at most four logical queries, at most ten deterministic public-page
fetches, and two synthesis calls.  Both synthesis arms share the exact plan,
search responses, fetched response bytes, page order, prompt template, model,
output cap, evidence cap, and task deadline.  The only treatment is each
fetched page's representation: inherited raw 5k prefix versus the V2.49.80
identity/target-bound 5k projection produced inside the same fetch helper.

This module accepts injected bounded clients and has no filesystem,
environment, process, benchmark-label, mapping, gold, evaluator, score,
reward, or credential capability.  It grants no benchmark launch authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24257_score_first_runtime as score
from .clients import canonicalize_url, parse_json_object
from .v24272_two_wave_retrieval import (
    run_two_wave_retrieval,
    validate_retrieval_receipt,
)
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24799_fixed_full_budget_control import POLICY_VALUES, fixed_full_budget_policy
from .v24981_late_page_bound_fetch import (
    LatePageBoundSearchClient,
    validate_receipt as validate_fetch_projection_receipt,
)


POLICY_ID = "v24982_shared_fetch_paired_production_runtime_v1"
ROLE = "v24982_shared_fetch_paired_runtime_result"
RECEIPT_ROLE = "v24982_content_free_paired_production_receipt"
ARMS = ("raw_parent_prefix", "identity_target_bound_projection")
CONTROL_ARM, CANDIDATE_ARM = ARMS
FALLBACK_TABLE = "```markdown\n| Result |\n|---|\n| Unknown |\n```"

_MODEL_COUNTERS = (
    "requests",
    "attempts",
    "input_tokens",
    "output_tokens",
    "total_tokens",
)
_SEARCH_COUNTERS = (
    "calls",
    "failures",
    "tool_calls",
    "fetch_calls",
    "fetch_failures",
    "input_tokens",
    "output_tokens",
    "total_tokens",
)


def _counter(client: Any, names: Sequence[str]) -> dict[str, int]:
    output: dict[str, int] = {}
    for name in names:
        value = getattr(client, name, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("V2.49.82 client counter drifted")
        output[name] = value
    return output


def _delta(after: Mapping[str, int], before: Mapping[str, int]) -> dict[str, int]:
    output = {name: int(after[name]) - int(before[name]) for name in before}
    if any(value < 0 for value in output.values()):
        raise ValueError("V2.49.82 client counter regressed")
    return output


def _model_text(value: Any) -> str:
    return score._model_text(value)


def _fallback(columns: Sequence[str]) -> str:
    safe = [str(value).strip().replace("|", "\\|") or "Result" for value in columns]
    return (
        "```markdown\n| "
        + " | ".join(safe)
        + " |\n|"
        + "|".join("---" for _ in safe)
        + "|\n| "
        + " | ".join("Unknown" for _ in safe)
        + " |\n```"
    )


def _pages(page_batches: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for batch in page_batches:
        if not isinstance(batch, Mapping):
            continue
        for result in batch.get("results") or []:
            if not isinstance(result, Mapping):
                continue
            url = canonicalize_url(str(result.get("url") or ""))
            content = str(result.get("raw_content") or result.get("content") or "")
            if not url or not content or url in seen:
                continue
            seen.add(url)
            output.append(
                {
                    "title": str(result.get("title") or ""),
                    "url": url,
                    "content": content,
                }
            )
    return output


def _evidence(
    pages: Sequence[Mapping[str, str]],
    *,
    search: LatePageBoundSearchClient,
    limits: score.ScoreFirstLimits,
    arm: str,
) -> str:
    if arm not in ARMS:
        raise ValueError("V2.49.82 arm drifted")

    def render(chosen: str) -> str:
        records: list[str] = []
        used = 0
        for ordinal, page in enumerate(pages, 1):
            if used >= limits.evidence_chars:
                break
            if chosen == CONTROL_ARM:
                content = search.parent_prefix_for(str(page["url"]))
                if not content:
                    raise RuntimeError("V2.49.82 parent-prefix shadow is absent")
            else:
                content = str(page["content"])
            content = content.replace("\x00", "").strip()
            remaining = limits.evidence_chars - used
            content = content[: min(limits.page_chars, remaining)]
            if not content:
                continue
            records.append(
                f"[E{ordinal:04d}] kind=fetched_page\n"
                f"title={score._normalize_text(page['title'])[:500]}\n"
                f"url={page['url']}\ncontent={content}"
            )
            used += len(content)
        return "\n\n".join(records) or "No usable web material was retrieved within budget."

    control = render(CONTROL_ARM)
    if arm == CONTROL_ARM:
        return control
    candidate = render(CANDIDATE_ARM)
    # Preserve the inherited control byte-for-byte.  Match its total prompt
    # allocation by trimming only the candidate's final raw tail or padding
    # the candidate after its final page.  Compact records are page prefixes,
    # so this operation cannot split a retained compact record.
    if len(candidate) >= len(control):
        return candidate[: len(control)]
    return candidate + " " * (len(control) - len(candidate))


def _arm_order(opaque_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"v24982:{opaque_id}".encode()).digest()[0]
    return ARMS if digest % 2 == 0 else ARMS[::-1]


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "planned_query_count": int(value["planned_query_count"]),
        "executed_query_count": int(value["executed_query_count"]),
        "fetch_attempt_count": int(value["fetch_attempt_count"]),
        "usable_page_count": int(value["usable_page_count"]),
        "model_logical_call_count": int(value["model_logical_call_count"]),
        "model_provider_request_count": int(value["model_provider_request_count"]),
        "model_provider_attempt_count": int(value["model_provider_attempt_count"]),
        "control_evidence_characters": int(value["control_evidence_characters"]),
        "candidate_evidence_characters": int(value["candidate_evidence_characters"]),
        "candidate_changed_page_count": int(value["candidate_changed_page_count"]),
        "mechanism_engaged_page_count": int(value["mechanism_engaged_page_count"]),
        "prediction_changed": bool(value["prediction_changed"]),
        "both_arms_model_success": bool(value["both_arms_model_success"]),
        "same_plan_queries_search_responses_and_page_bytes": True,
        "same_page_order_prompt_model_output_and_evidence_caps": True,
        "one_plan_and_one_synthesis_per_arm": True,
        "query_fetch_model_token_context_wall_and_network_byte_caps_preserved": True,
        "control_is_exact_inherited_page_prefix": True,
        "candidate_is_same_fetch_late_page_projection": True,
        "entropy_information_gain_shadow_only": True,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "contains_question_query_url_title_page_record_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    integers = (
        "planned_query_count",
        "executed_query_count",
        "fetch_attempt_count",
        "usable_page_count",
        "model_logical_call_count",
        "model_provider_request_count",
        "model_provider_attempt_count",
        "control_evidence_characters",
        "candidate_evidence_characters",
        "candidate_changed_page_count",
        "mechanism_engaged_page_count",
    )
    true_flags = (
        "same_plan_queries_search_responses_and_page_bytes",
        "same_page_order_prompt_model_output_and_evidence_caps",
        "one_plan_and_one_synthesis_per_arm",
        "query_fetch_model_token_context_wall_and_network_byte_caps_preserved",
        "control_is_exact_inherited_page_prefix",
        "candidate_is_same_fetch_late_page_projection",
        "entropy_information_gain_shadow_only",
    )
    false_flags = (
        "entropy_or_information_gain_assigns_signed_credit",
        "contains_question_query_url_title_page_record_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *integers,
        "prediction_changed",
        "both_arms_model_success",
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
            for name in integers
        )
        or not isinstance(copied.get("prediction_changed"), bool)
        or not isinstance(copied.get("both_arms_model_success"), bool)
        or copied["planned_query_count"] > 4
        or copied["executed_query_count"] > copied["planned_query_count"]
        or copied["fetch_attempt_count"] > 10
        or copied["usable_page_count"] > copied["fetch_attempt_count"]
        or copied["model_logical_call_count"] > 3
        or copied["model_provider_request_count"] > copied["model_logical_call_count"]
        or copied["candidate_changed_page_count"] > copied["usable_page_count"]
        or copied["mechanism_engaged_page_count"]
        > copied["candidate_changed_page_count"]
        or copied["control_evidence_characters"] > 60_000
        or copied["candidate_evidence_characters"] > 60_000
        or copied["control_evidence_characters"]
        != copied["candidate_evidence_characters"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.82 paired receipt drifted")
    return copied


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    predictions = copied.get("predictions")
    successes = copied.get("model_success")
    failures = copied.get("failure_types")
    evidence = copied.get("evidence_characters")
    costs = copied.get("cost")
    retrieval = copied.get("retrieval_receipt")
    fetch_projection = copied.get("late_page_fetch_receipt")
    receipt = copied.get("content_free_receipt")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") != "terminal"
        or set(predictions or {}) != set(ARMS)
        or any(not isinstance(predictions[arm], str) or not predictions[arm] for arm in ARMS)
        or set(successes or {}) != set(ARMS)
        or any(not isinstance(successes[arm], bool) for arm in ARMS)
        or set(failures or {}) != {"plan", "retrieval", *ARMS}
        or any(value is not None and (not isinstance(value, str) or not value) for value in failures.values())
        or set(evidence or {}) != set(ARMS)
        or any(isinstance(evidence[arm], bool) or not isinstance(evidence[arm], int) or evidence[arm] < 0 for arm in ARMS)
        or not isinstance(costs, Mapping)
        or set(costs) != {"model", "search"}
        or any(not isinstance(costs[name], Mapping) for name in costs)
        or retrieval is not None and not isinstance(retrieval, Mapping)
        or not isinstance(fetch_projection, Mapping)
        or not isinstance(receipt, Mapping)
        or validate_fetch_projection_receipt(fetch_projection) != dict(fetch_projection)
        or validate_receipt(receipt) != dict(receipt)
        or copied.get("prediction_changed")
        is not (predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM])
        or receipt["prediction_changed"] != copied["prediction_changed"]
        or receipt["both_arms_model_success"] != all(successes.values())
        or receipt["control_evidence_characters"] != evidence[CONTROL_ARM]
        or receipt["candidate_evidence_characters"] != evidence[CANDIDATE_ARM]
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_read") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.82 paired result drifted")
    if retrieval is not None:
        validate_retrieval_receipt(retrieval)
    elif failures.get("retrieval") is None:
        raise ValueError("V2.49.82 missing retrieval receipt without failure")
    return copied


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
        raise ValueError("V2.49.82 requires the bounded global model limiter")
    if not isinstance(search, LatePageBoundSearchClient):
        raise ValueError("V2.49.82 requires the late-page bounded search client")
    limits.validate()
    if (
        limits.wall_seconds != 240
        or limits.model_calls != 3
        or limits.search_queries != 4
        or limits.fetch_targets != 10
        or limits.evidence_chars != 60_000
        or limits.page_chars != 5_000
    ):
        raise ValueError("V2.49.82 production hard budget drifted")
    fixed = fixed_full_budget_policy()
    if POLICY_VALUES != {
        field: getattr(fixed, field) for field in POLICY_VALUES
    }:
        raise RuntimeError("V2.49.82 fixed no-entropy controller drifted")

    model_before = _counter(model, _MODEL_COUNTERS)
    search_before = _counter(search, _SEARCH_COUNTERS)
    failures: dict[str, str | None] = {
        "plan": None,
        "retrieval": None,
        CONTROL_ARM: None,
        CANDIDATE_ARM: None,
    }
    logical_model_calls = 0
    plan = score._validated_plan({}, visible["question"], limits)
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
        plan = score._validated_plan(
            parse_json_object(_model_text(response)), visible["question"], limits
        )
    except BaseException as exc:
        failures["plan"] = _safe_failure(exc)

    queries = list(plan["queries"])[: limits.search_queries]
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
        pages = _pages(retrieval["page_batches"])
    except BaseException as exc:
        failures["retrieval"] = _safe_failure(exc)

    evidence = {
        CONTROL_ARM: "No usable web material was retrieved within budget.",
        CANDIDATE_ARM: "No usable web material was retrieved within budget.",
    }
    if pages:
        try:
            for arm in ARMS:
                evidence[arm] = _evidence(
                    pages, search=search, limits=limits, arm=arm
                )
        except BaseException as exc:
            failures["retrieval"] = failures["retrieval"] or _safe_failure(exc)
            pages = []

    predictions = {arm: _fallback(plan["columns"]) for arm in ARMS}
    success = {arm: False for arm in ARMS}
    if pages:
        for arm in _arm_order(visible["opaque_id"]):
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
                candidate = _model_text(response)
                parsed, _errors = score.extract_valid_markdown_table(
                    candidate, plan["columns"]
                )
                if parsed is None:
                    raise ValueError("V2.49.82 synthesis table contract failed")
                predictions[arm] = parsed
                success[arm] = True
            except BaseException as exc:
                failures[arm] = _safe_failure(exc)

    if retrieval is None:
        # A structurally valid zero-effect receipt is needed for downstream
        # validators only when retrieval was never entered.  The paired gate
        # treats such a task as failure-as-zero and does not validate a nested
        # retrieval receipt.
        retrieval_receipt: dict[str, Any] | None = None
    else:
        retrieval_receipt = copy.deepcopy(retrieval["receipt"])
    fetch_projection = search.late_page_projection_receipt()
    model_cost = _delta(_counter(model, _MODEL_COUNTERS), model_before)
    search_cost = _delta(_counter(search, _SEARCH_COUNTERS), search_before)
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
    receipt = _receipt(
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
        "evidence_characters": {
            arm: len(evidence[arm]) for arm in ARMS
        },
        "retrieval_receipt": retrieval_receipt,
        "late_page_fetch_receipt": fetch_projection,
        "cost": {"model": model_cost, "search": search_cost},
        "content_free_receipt": receipt,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_result(value)


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
