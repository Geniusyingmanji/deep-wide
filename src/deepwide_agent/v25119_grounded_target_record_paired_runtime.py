"""Matched shared-response runtime for grounded target-record page selection.

One visible-only planning call creates the completed four-query vector.  The
first two queries and at-most-six fetched pages execute once.  One shared
V2.51.17 call grounds clue pivots, row targets, authority terms, and the final
two queries in those pages.  The final two queries then execute once.  Control
keeps the stable complete URL-frontier prefix; candidate applies V2.51.18 to
the exact same search response and same-run first-wave links.  The union of
the two four-URL prefixes is fetched once and partitioned by requested URL.

Each arm is charged the shared plan, shared grounded-plan, and its own single
synthesis: at most three effective model calls, four queries, ten fetches,
60k evidence characters, and 240 seconds.  The paired experiment performs at
most four physical model calls, four physical queries, and fourteen physical
fetches.  Runtime task input is exactly ``opaque_id`` and ``question`` plus
injected bounded clients.  Benchmark labels, mapping, gold, evaluator output,
scores, rewards, history, and credentials are unavailable.  Entropy/IG assign
no signed credit.
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
from . import v25118_target_record_frontier_selection as selector
from .clients import parse_json_object
from .v24263_global_model_limiter import payload_sha256
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24981_late_page_bound_fetch import validate_receipt as validate_fetch_receipt
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25119_matched_grounded_target_record_frontier_paired_runtime_v1"
ROLE = "v25119_grounded_target_record_frontier_paired_runtime_result"
RECEIPT_ROLE = "v25119_content_free_grounded_target_record_paired_receipt"
SECOND_WAVE_RECEIPT_ROLE = "v25119_content_free_shared_second_wave_receipt"
ARMS = ("stable_complete_frontier_prefix", "grounded_target_record_frontier")
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = shared.PHASES
FIRST_PHASE, SECOND_PHASE = PHASES

_ARM_COUNT_FIELDS = (
    "effective_model_logical_call_count",
    "executed_query_count",
    "logical_fetch_count",
    "usable_page_count",
    "second_wave_selected_url_count",
    "second_wave_usable_page_count",
    "target_authority_page_count",
    "target_field_page_count",
    "target_field_pair_count",
    "complete_target_field_page_count",
    "evidence_characters",
)


def _safe_failure(exc: BaseException) -> str:
    name = type(exc).__name__
    return name if name and len(name) <= 128 else "Exception"


def _arm_order(opaque_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"v25119:{opaque_id}".encode()).digest()[0]
    return ARMS if digest % 2 == 0 else ARMS[::-1]


def _match_evidence(values: Mapping[str, str]) -> dict[str, str]:
    """Pad only the two V2.51.19 arms to the same character budget."""

    if set(values) != set(ARMS):
        raise ValueError("V2.51.19 evidence arm drifted")
    maximum = max(len(str(values[arm])) for arm in ARMS)
    return {
        arm: str(values[arm]) + " " * (maximum - len(str(values[arm])))
        for arm in ARMS
    }


def _page_field_counts(
    pages: Sequence[Mapping[str, Any]],
    *,
    row_targets: Sequence[str],
    pivots: Sequence[str],
    authority_terms: Sequence[str],
    columns: Sequence[str],
) -> dict[str, int]:
    required = selector._safe_columns(columns)
    targets = selector._vectors(
        [*row_targets, *pivots], cap=selector.MAXIMUM_TARGETS
    )
    authorities = selector._authority_tokens(authority_terms)
    target_authority = field_pages = field_pairs = complete = 0
    non_key = required[1:]
    for raw in pages:
        if not isinstance(raw, Mapping):
            continue
        url = str(raw.get("url") or "")
        title = str(raw.get("title") or "")
        classified = selector._classify(
            {
                "url": url,
                "fetch_url": url,
                "title": title,
                "member_label": "",
                "source_type": "same_forward_fetched_page",
            },
            targets=targets,
            authorities=authorities,
            columns=required,
        )
        if classified["unique_target"] is None or not classified["authority_bound"]:
            continue
        target_authority += 1
        surface = selector._phrase_key(
            title
            + " "
            + str(raw.get("content") or raw.get("raw_content") or "")
        )
        matched = sum(
            bool(
                (phrase := selector._phrase_key(column))
                and len(phrase) >= 2
                and phrase in surface
            )
            for column in non_key
        )
        field_pairs += matched
        field_pages += int(matched > 0)
        complete += int(bool(non_key) and matched == len(non_key))
    return {
        "target_authority_page_count": target_authority,
        "target_field_page_count": field_pages,
        "target_field_pair_count": field_pairs,
        "complete_target_field_page_count": complete,
    }


def _second_receipt(
    *,
    selection: Mapping[str, Any],
    fetch: Mapping[str, Any],
    mapping_failures: int,
    unrecoverable_failures: int,
    physical_union_fetches: int,
    physical_union_usable_pages: int,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": SECOND_WAVE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "logical_query_count": 2,
        "query_local_mapping_failure_count": int(mapping_failures),
        "unrecoverable_search_failure_count": int(unrecoverable_failures),
        "control_selected_url_count": int(selection["control_selected_url_count"]),
        "candidate_selected_url_count": int(selection["candidate_selected_url_count"]),
        "physical_union_fetch_count": int(physical_union_fetches),
        "physical_union_usable_page_count": int(physical_union_usable_pages),
        "projected_page_count": int(fetch["projected_page_count"]),
        "selection_changed": bool(selection["selection_changed"]),
        "one_grounded_second_wave_query_vector_shared_by_both_arms": True,
        "one_search_response_and_complete_url_frontier_shared_by_both_arms": True,
        "two_arm_selected_url_union_fetched_once": True,
        "unselected_page_text_never_enters_arm_evidence": True,
        "provider_narrative_or_snippet_forwarded": False,
        "contains_question_target_authority_column_query_url_title_page_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
        "selection_receipt": copy.deepcopy(dict(selection)),
        "fetch_receipt": copy.deepcopy(dict(fetch)),
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_second_wave_receipt(value)


def validate_second_wave_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    selection = copied.get("selection_receipt")
    fetch = copied.get("fetch_receipt")
    counts = (
        "logical_query_count",
        "query_local_mapping_failure_count",
        "unrecoverable_search_failure_count",
        "control_selected_url_count",
        "candidate_selected_url_count",
        "physical_union_fetch_count",
        "physical_union_usable_page_count",
        "projected_page_count",
    )
    true_flags = (
        "one_grounded_second_wave_query_vector_shared_by_both_arms",
        "one_search_response_and_complete_url_frontier_shared_by_both_arms",
        "two_arm_selected_url_union_fetched_once",
        "unselected_page_text_never_enters_arm_evidence",
    )
    false_flags = (
        "provider_narrative_or_snippet_forwarded",
        "contains_question_target_authority_column_query_url_title_page_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *counts,
        "selection_changed",
        *true_flags,
        *false_flags,
        "selection_receipt",
        "fetch_receipt",
        "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != SECOND_WAVE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or not isinstance(copied.get("selection_changed"), bool)
        or copied["logical_query_count"] != 2
        or copied["control_selected_url_count"]
        != copied["candidate_selected_url_count"]
        or copied["control_selected_url_count"] > 4
        or copied["physical_union_fetch_count"] > 8
        or copied["physical_union_usable_page_count"]
        > copied["physical_union_fetch_count"]
        or copied["projected_page_count"] > copied["physical_union_fetch_count"]
        or not isinstance(selection, Mapping)
        or selector.validate_receipt(selection) != dict(selection)
        or not isinstance(fetch, Mapping)
        or validate_fetch_receipt(fetch) != dict(fetch)
        or selection["control_selected_url_count"]
        != copied["control_selected_url_count"]
        or selection["candidate_selected_url_count"]
        != copied["candidate_selected_url_count"]
        or bool(selection["selection_changed"]) is not copied["selection_changed"]
        or fetch["fetch_calls_snapshot"] != copied["physical_union_fetch_count"]
        or fetch["projected_page_count"] != copied["projected_page_count"]
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.19 shared second-wave receipt drifted")
    return copied


def _run_second_wave(
    queries: Sequence[str],
    *,
    search: Any,
    first_wave_page_batches: object,
    plan: Mapping[str, Any],
    columns: Sequence[str],
    search_results_per_query: int,
    exclude_urls: frozenset[str],
) -> dict[str, Any]:
    if len(queries) != 2 or search_results_per_query != 3:
        raise ValueError("V2.51.19 second-wave boundary drifted")
    raw = search.search_many(
        list(queries),
        max_results=search_results_per_query,
        search_depth="advanced",
        include_raw_content=False,
    )
    selection = selector.select_target_record_frontier(
        first_wave_page_batches,
        raw,
        row_targets=list(plan.get("row_targets") or []),
        pivots=list(plan.get("pivots") or []),
        authority_terms=list(plan.get("authority_terms") or []),
        columns=list(columns),
        cap=4,
        exclude_urls=exclude_urls,
    )
    requests = shared._union_requests(selection)
    fetched = search.fetch_urls(requests) if requests else []
    page_map = shared._page_map(fetched)
    pages = {
        CONTROL_ARM: shared._arm_second_pages(selection["control"], page_map),
        CANDIDATE_ARM: shared._arm_second_pages(selection["candidate"], page_map),
    }
    fetch = search.late_page_projection_receipt()
    selection_receipt = selection["content_free_receipt"]
    return {
        "receipt": _second_receipt(
            selection=selection_receipt,
            fetch=fetch,
            mapping_failures=shared._mapping_failures(raw),
            unrecoverable_failures=shared._unrecoverable_failures(raw),
            physical_union_fetches=len(requests),
            physical_union_usable_pages=shared._usable_pages(fetched),
        ),
        "selection_receipt": copy.deepcopy(selection_receipt),
        "selected": {
            CONTROL_ARM: copy.deepcopy(selection["control"]),
            CANDIDATE_ARM: copy.deepcopy(selection["candidate"]),
        },
        "pages": pages,
    }


def _empty_arm_metric() -> dict[str, Any]:
    return {
        **{name: 0 for name in _ARM_COUNT_FIELDS},
        "synthesis_attempted": False,
        "model_success": False,
        "normalizer_status": "not_attempted",
    }


def _arm_metric(value: Mapping[str, Any]) -> dict[str, Any]:
    output = {name: int(value[name]) for name in _ARM_COUNT_FIELDS}
    output.update(
        {
            "synthesis_attempted": bool(value["synthesis_attempted"]),
            "model_success": bool(value["model_success"]),
            "normalizer_status": str(value["normalizer_status"]),
        }
    )
    return output


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "provider_unique_query_count": int(value["provider_unique_query_count"]),
        "shared_first_wave_completed": bool(value["shared_first_wave_completed"]),
        "grounded_plan_model_call_attempted": bool(
            value["grounded_plan_model_call_attempted"]
        ),
        "grounded_plan_strategy_applied": bool(
            value["grounded_plan_strategy_applied"]
        ),
        "shared_second_wave_completed": bool(value["shared_second_wave_completed"]),
        "selection_strategy_eligible": bool(value["selection_strategy_eligible"]),
        "selection_changed": bool(value["selection_changed"]),
        "target_field_page_gain": int(value["target_field_page_gain"]),
        "target_field_pair_gain": int(value["target_field_pair_gain"]),
        "complete_target_field_page_gain": int(
            value["complete_target_field_page_gain"]
        ),
        "retrieval_mechanism_engaged": bool(value["retrieval_mechanism_engaged"]),
        "attributable_prediction_change": bool(
            value["attributable_prediction_change"]
        ),
        "first_synthesis_arm": str(value["first_synthesis_arm"]),
        "physical_query_count": int(value["physical_query_count"]),
        "physical_fetch_count": int(value["physical_fetch_count"]),
        "physical_model_logical_call_count": int(
            value["physical_model_logical_call_count"]
        ),
        "model_provider_request_count": int(value["model_provider_request_count"]),
        "model_provider_attempt_count": int(value["model_provider_attempt_count"]),
        "control_evidence_characters": int(value["control_evidence_characters"]),
        "candidate_evidence_characters": int(value["candidate_evidence_characters"]),
        "arm_metrics": {
            arm: _arm_metric(value["arm_metrics"][arm]) for arm in ARMS
        },
        "prediction_changed": bool(value["prediction_changed"]),
        "both_arms_model_success": bool(value["both_arms_model_success"]),
        "grounded_plan_receipt": copy.deepcopy(dict(value["grounded_plan_receipt"])),
        "selection_receipt": copy.deepcopy(dict(value["selection_receipt"])),
        "one_visible_only_plan_and_one_grounded_plan_shared_by_both_arms": True,
        "same_completed_grounded_query_vector_and_search_response_both_arms": True,
        "one_physical_first_wave_and_one_physical_second_wave": True,
        "two_arm_second_wave_url_union_fetched_once": True,
        "page_text_partitioned_by_selected_canonical_url": True,
        "per_arm_effective_model_call_cap": 3,
        "per_arm_logical_query_cap": 4,
        "per_arm_logical_fetch_cap": 10,
        "physical_model_call_cap": 4,
        "physical_query_cap": 4,
        "physical_fetch_cap": 14,
        "evidence_character_cap": 60_000,
        "wall_second_cap": 240,
        "same_projector_synthesis_prompt_model_output_cap_and_deadline": True,
        "contains_question_target_authority_column_query_url_title_page_prediction_answer_hash_opaque_id_or_credential": False,
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
    plan_receipt = copied.get("grounded_plan_receipt")
    selection_receipt = copied.get("selection_receipt")
    metrics = copied.get("arm_metrics")
    counts = (
        "provider_unique_query_count",
        "physical_query_count",
        "physical_fetch_count",
        "physical_model_logical_call_count",
        "model_provider_request_count",
        "model_provider_attempt_count",
        "control_evidence_characters",
        "candidate_evidence_characters",
        "per_arm_effective_model_call_cap",
        "per_arm_logical_query_cap",
        "per_arm_logical_fetch_cap",
        "physical_model_call_cap",
        "physical_query_cap",
        "physical_fetch_cap",
        "evidence_character_cap",
        "wall_second_cap",
    )
    signed_bounds = {
        "target_field_page_gain": 4,
        "target_field_pair_gain": 4 * (selector.MAXIMUM_COLUMNS - 1),
        "complete_target_field_page_gain": 4,
    }
    bool_fields = (
        "shared_first_wave_completed",
        "grounded_plan_model_call_attempted",
        "grounded_plan_strategy_applied",
        "shared_second_wave_completed",
        "selection_strategy_eligible",
        "selection_changed",
        "retrieval_mechanism_engaged",
        "attributable_prediction_change",
        "prediction_changed",
        "both_arms_model_success",
    )
    true_flags = (
        "one_visible_only_plan_and_one_grounded_plan_shared_by_both_arms",
        "same_completed_grounded_query_vector_and_search_response_both_arms",
        "one_physical_first_wave_and_one_physical_second_wave",
        "two_arm_second_wave_url_union_fetched_once",
        "page_text_partitioned_by_selected_canonical_url",
        "same_projector_synthesis_prompt_model_output_cap_and_deadline",
    )
    false_flags = (
        "contains_question_target_authority_column_query_url_title_page_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *counts,
        *signed_bounds,
        *bool_fields,
        "first_synthesis_arm",
        "arm_metrics",
        "grounded_plan_receipt",
        "selection_receipt",
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
            for name in counts
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or not -bound <= copied[name] <= bound
            for name, bound in signed_bounds.items()
        )
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or copied.get("first_synthesis_arm") not in {*ARMS, "none"}
        or copied["provider_unique_query_count"] > 4
        or copied["physical_query_count"] > 4
        or copied["physical_fetch_count"] > 14
        or copied["physical_model_logical_call_count"] > 4
        or copied["model_provider_request_count"]
        > copied["physical_model_logical_call_count"]
        or copied["model_provider_attempt_count"]
        < copied["model_provider_request_count"]
        or copied["control_evidence_characters"]
        != copied["candidate_evidence_characters"]
        or copied["control_evidence_characters"] > 60_000
        or copied["per_arm_effective_model_call_cap"] != 3
        or copied["per_arm_logical_query_cap"] != 4
        or copied["per_arm_logical_fetch_cap"] != 10
        or copied["physical_model_call_cap"] != 4
        or copied["physical_query_cap"] != 4
        or copied["physical_fetch_cap"] != 14
        or copied["evidence_character_cap"] != 60_000
        or copied["wall_second_cap"] != 240
        or not isinstance(plan_receipt, Mapping)
        or target_plan.validate_receipt(plan_receipt) != dict(plan_receipt)
        or not isinstance(selection_receipt, Mapping)
        or selector.validate_receipt(selection_receipt) != dict(selection_receipt)
        or copied["grounded_plan_model_call_attempted"]
        is not plan_receipt["model_call_attempted"]
        or copied["grounded_plan_strategy_applied"]
        is not plan_receipt["strategy_applied"]
        or copied["grounded_plan_model_call_attempted"]
        and not copied["shared_first_wave_completed"]
        or copied["grounded_plan_strategy_applied"]
        and not copied["grounded_plan_model_call_attempted"]
        or copied["shared_second_wave_completed"]
        and not copied["shared_first_wave_completed"]
        or copied["selection_strategy_eligible"]
        is not selection_receipt["strategy_eligible"]
        or copied["selection_changed"]
        is not bool(selection_receipt["selection_changed"])
        or copied["selection_strategy_eligible"]
        and not copied["shared_second_wave_completed"]
        or copied["selection_changed"]
        and not (
            copied["shared_second_wave_completed"]
            and copied["grounded_plan_strategy_applied"]
        )
        or copied["retrieval_mechanism_engaged"]
        is not bool(copied["selection_changed"] and copied["target_field_page_gain"] > 0)
        or copied["attributable_prediction_change"]
        is not bool(copied["retrieval_mechanism_engaged"] and copied["prediction_changed"])
        or not isinstance(metrics, Mapping)
        or set(metrics) != set(ARMS)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.19 paired receipt drifted")
    attempts = successes = 0
    shared_fetch_bases: list[int] = []
    shared_usable_bases: list[int] = []
    non_key_columns = int(selection_receipt["visible_non_key_column_count"])
    for arm in ARMS:
        metric = metrics[arm]
        selected_name = (
            "control_selected_url_count"
            if arm == CONTROL_ARM
            else "candidate_selected_url_count"
        )
        if (
            not isinstance(metric, Mapping)
            or set(metric)
            != {*_ARM_COUNT_FIELDS, "synthesis_attempted", "model_success", "normalizer_status"}
            or any(
                isinstance(metric.get(name), bool)
                or not isinstance(metric.get(name), int)
                or metric[name] < 0
                for name in _ARM_COUNT_FIELDS
            )
            or not isinstance(metric.get("synthesis_attempted"), bool)
            or not isinstance(metric.get("model_success"), bool)
            or metric["model_success"] and not metric["synthesis_attempted"]
            or metric.get("normalizer_status")
            not in {"not_attempted", "exact", "normalized", "unrecoverable"}
            or metric["effective_model_logical_call_count"] > 3
            or metric["executed_query_count"] > 4
            or metric["logical_fetch_count"] > 10
            or metric["usable_page_count"] > metric["logical_fetch_count"]
            or metric["second_wave_selected_url_count"] > 4
            or metric["second_wave_usable_page_count"]
            > metric["second_wave_selected_url_count"]
            or metric["second_wave_selected_url_count"]
            != selection_receipt[selected_name]
            or metric["target_authority_page_count"]
            > metric["second_wave_usable_page_count"]
            or metric["target_field_page_count"]
            > metric["target_authority_page_count"]
            or metric["target_field_pair_count"]
            > metric["target_field_page_count"] * non_key_columns
            or metric["complete_target_field_page_count"]
            > metric["target_field_page_count"]
            or metric["evidence_characters"] > 60_000
            or metric["effective_model_logical_call_count"]
            != 1
            + int(copied["grounded_plan_model_call_attempted"])
            + int(metric["synthesis_attempted"])
            or metric["executed_query_count"] != copied["physical_query_count"]
            or metric["logical_fetch_count"]
            < metric["second_wave_selected_url_count"]
            or metric["usable_page_count"]
            < metric["second_wave_usable_page_count"]
        ):
            raise ValueError("V2.51.19 arm metric drifted")
        attempts += int(metric["synthesis_attempted"])
        successes += int(metric["model_success"])
        shared_fetch_bases.append(
            metric["logical_fetch_count"]
            - metric["second_wave_selected_url_count"]
        )
        shared_usable_bases.append(
            metric["usable_page_count"]
            - metric["second_wave_usable_page_count"]
        )
    control = metrics[CONTROL_ARM]
    candidate = metrics[CANDIDATE_ARM]
    if (
        copied["target_field_page_gain"]
        != candidate["target_field_page_count"] - control["target_field_page_count"]
        or copied["target_field_pair_gain"]
        != candidate["target_field_pair_count"] - control["target_field_pair_count"]
        or copied["complete_target_field_page_gain"]
        != candidate["complete_target_field_page_count"]
        - control["complete_target_field_page_count"]
        or copied["physical_model_logical_call_count"]
        != 1 + int(copied["grounded_plan_model_call_attempted"]) + attempts
        or copied["both_arms_model_success"] is not (successes == 2)
        or copied["control_evidence_characters"] != control["evidence_characters"]
        or copied["candidate_evidence_characters"] != candidate["evidence_characters"]
        or len(set(shared_fetch_bases)) != 1
        or len(set(shared_usable_bases)) != 1
        or (attempts == 0) is not (copied["first_synthesis_arm"] == "none")
        or attempts > 0
        and not metrics[copied["first_synthesis_arm"]]["synthesis_attempted"]
    ):
        raise ValueError("V2.51.19 paired accounting drifted")
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
        raise ValueError("V2.51.19 requires a bounded global model limiter")
    if (
        not isinstance(searches, Mapping)
        or set(searches) != set(PHASES)
        or any(
            not isinstance(searches[phase], RobustLatePageBoundSearchClient)
            for phase in PHASES
        )
        or len({id(searches[phase]) for phase in PHASES}) != len(PHASES)
    ):
        raise ValueError("V2.51.19 requires two distinct robust search clients")
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
        raise ValueError("V2.51.19 production-shaped budget drifted")
    order = tuple(arm_order or _arm_order(visible["opaque_id"]))
    if len(order) != 2 or set(order) != set(ARMS):
        raise ValueError("V2.51.19 arm order drifted")

    model_before = counters._counter(model, counters._MODEL_COUNTERS)
    search_before = {
        phase: counters._counter(searches[phase], counters._SEARCH_COUNTERS)
        for phase in PHASES
    }
    if any(any(snapshot.values()) for snapshot in search_before.values()):
        raise ValueError("V2.51.19 requires pristine search clients")
    observers = {phase: compact._EffectObserver(searches[phase]) for phase in PHASES}
    failures: dict[str, Any] = {
        "plan": None,
        "grounded_plan": None,
        "retrieval": {phase: None for phase in PHASES},
        "synthesis": {arm: None for arm in ARMS},
    }
    logical_model_calls = 1
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
    shared_pages: list[dict[str, str]] = []
    try:
        first = shared._run_first_wave(
            queries[:2],
            search=observers[FIRST_PHASE],
            search_results_per_query=limits.search_results_per_query,
        )
        shared_pages = counters._pages(first["page_batches"])
    except BaseException as exc:
        failures["retrieval"][FIRST_PHASE] = _safe_failure(exc)

    prepared = target_plan.prepare_plan(
        visible["question"], plan["columns"], queries, shared_pages
    )
    grounded_output = ""
    grounded_attempted = bool(shared_pages)
    if grounded_attempted:
        logical_model_calls += 1
        try:
            response = model.complete(
                str(prepared["system"]),
                str(prepared["user"]),
                max_output_tokens=target_plan.PLAN_OUTPUT_TOKEN_CAP,
                json_mode=True,
            )
            grounded_output = counters._model_text(response)
        except BaseException as exc:
            failures["grounded_plan"] = _safe_failure(exc)
    grounded = target_plan.select_plan(
        prepared,
        grounded_output,
        model_call_attempted=grounded_attempted,
    )
    grounded_receipt = grounded["content_free_receipt"]
    second_queries = list(grounded["queries"])

    second_pages: dict[str, list[dict[str, str]]] = {arm: [] for arm in ARMS}
    empty_selection = selector.select_target_record_frontier(
        [],
        [],
        row_targets=[],
        pivots=[],
        authority_terms=[],
        columns=plan["columns"],
        cap=4,
    )["content_free_receipt"]
    selection_receipt = copy.deepcopy(empty_selection)
    if first is not None:
        try:
            second = _run_second_wave(
                second_queries,
                search=observers[SECOND_PHASE],
                first_wave_page_batches=first["page_batches"],
                plan=grounded,
                columns=plan["columns"],
                search_results_per_query=limits.search_results_per_query,
                exclude_urls=first["selected_urls"],
            )
            selection_receipt = copy.deepcopy(second["selection_receipt"])
            second_pages = {
                arm: copy.deepcopy(second["pages"][arm]) for arm in ARMS
            }
        except BaseException as exc:
            failures["retrieval"][SECOND_PHASE] = _safe_failure(exc)
    else:
        failures["retrieval"][SECOND_PHASE] = "SharedFirstWaveFailure"

    arm_pages = {arm: [*shared_pages, *second_pages[arm]] for arm in ARMS}
    evidence = _match_evidence(
        {arm: compact._compact_evidence(arm_pages[arm], limits) for arm in ARMS}
    )
    observations = {
        arm: _page_field_counts(
            second_pages[arm],
            row_targets=grounded["row_targets"],
            pivots=grounded["pivots"],
            authority_terms=grounded["authority_terms"],
            columns=plan["columns"],
        )
        for arm in ARMS
    }
    predictions = {arm: counters._fallback(plan["columns"]) for arm in ARMS}
    attempted = {arm: False for arm in ARMS}
    success = {arm: False for arm in ARMS}
    normalizer = {arm: "not_attempted" for arm in ARMS}
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
                counters._model_text(response), plan["columns"], visible["question"]
            )
            normalizer[arm] = status
            if parsed is None:
                raise ValueError("V2.51.19 synthesis table contract failed")
            predictions[arm] = parsed
            success[arm] = True
        except BaseException as exc:
            normalizer[arm] = "unrecoverable"
            failures["synthesis"][arm] = _safe_failure(exc)

    first_receipt = None if first is None else copy.deepcopy(first["receipt"])
    second_receipt = None if second is None else copy.deepcopy(second["receipt"])
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
    physical_effects = {
        phase: {
            "logical_queries": int(observers[phase].logical_query_count),
            "fetch_requests": int(observers[phase].fetch_request_count),
        }
        for phase in PHASES
    }
    first_selected = 0 if first is None else int(first["receipt"]["selected_url_count"])
    first_usable = len(shared_pages)
    arm_metrics = {arm: _empty_arm_metric() for arm in ARMS}
    for arm in ARMS:
        arm_metrics[arm].update(
            {
                "effective_model_logical_call_count": 1
                + int(grounded_attempted)
                + int(attempted[arm]),
                "executed_query_count": sum(
                    effect["logical_queries"] for effect in physical_effects.values()
                ),
                "logical_fetch_count": first_selected
                + int(selection_receipt["control_selected_url_count" if arm == CONTROL_ARM else "candidate_selected_url_count"]),
                "usable_page_count": first_usable + len(second_pages[arm]),
                "second_wave_selected_url_count": int(
                    selection_receipt["control_selected_url_count" if arm == CONTROL_ARM else "candidate_selected_url_count"]
                ),
                "second_wave_usable_page_count": len(second_pages[arm]),
                **observations[arm],
                "evidence_characters": len(evidence[arm]),
                "synthesis_attempted": attempted[arm],
                "model_success": success[arm],
                "normalizer_status": normalizer[arm],
            }
        )
    page_gain = (
        observations[CANDIDATE_ARM]["target_field_page_count"]
        - observations[CONTROL_ARM]["target_field_page_count"]
    )
    pair_gain = (
        observations[CANDIDATE_ARM]["target_field_pair_count"]
        - observations[CONTROL_ARM]["target_field_pair_count"]
    )
    complete_gain = (
        observations[CANDIDATE_ARM]["complete_target_field_page_count"]
        - observations[CONTROL_ARM]["complete_target_field_page_count"]
    )
    changed = predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM]
    mechanism = bool(selection_receipt["selection_changed"] and page_gain > 0)
    receipt = _receipt(
        {
            "provider_unique_query_count": plan["provider_unique_query_count"],
            "shared_first_wave_completed": first is not None,
            "grounded_plan_model_call_attempted": grounded_attempted,
            "grounded_plan_strategy_applied": grounded_receipt["strategy_applied"],
            "shared_second_wave_completed": second is not None,
            "selection_strategy_eligible": selection_receipt["strategy_eligible"],
            "selection_changed": bool(selection_receipt["selection_changed"]),
            "target_field_page_gain": page_gain,
            "target_field_pair_gain": pair_gain,
            "complete_target_field_page_gain": complete_gain,
            "retrieval_mechanism_engaged": mechanism,
            "attributable_prediction_change": bool(mechanism and changed),
            "first_synthesis_arm": synthesis_order[0] if synthesis_order else "none",
            "physical_query_count": sum(
                effect["logical_queries"] for effect in physical_effects.values()
            ),
            "physical_fetch_count": sum(
                effect["fetch_requests"] for effect in physical_effects.values()
            ),
            "physical_model_logical_call_count": logical_model_calls,
            "model_provider_request_count": model_cost["requests"],
            "model_provider_attempt_count": model_cost["attempts"],
            "control_evidence_characters": len(evidence[CONTROL_ARM]),
            "candidate_evidence_characters": len(evidence[CANDIDATE_ARM]),
            "arm_metrics": arm_metrics,
            "prediction_changed": changed,
            "both_arms_model_success": all(success.values()),
            "grounded_plan_receipt": grounded_receipt,
            "selection_receipt": selection_receipt,
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
        "failure_types": failures,
        "prediction_changed": changed,
        "elapsed_seconds": round(max(0.0, monotonic() - started), 6),
        "grounded_plan_receipt": copy.deepcopy(grounded_receipt),
        "selection_receipt": copy.deepcopy(selection_receipt),
        "physical_wave_receipts": {
            FIRST_PHASE: first_receipt,
            SECOND_PHASE: second_receipt,
        },
        "physical_effects": physical_effects,
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
    plan_receipt = copied.get("grounded_plan_receipt")
    selection_receipt = copied.get("selection_receipt")
    waves = copied.get("physical_wave_receipts")
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
        "prediction_sha256",
        "model_success",
        "normalizer_status",
        "failure_types",
        "prediction_changed",
        "elapsed_seconds",
        "grounded_plan_receipt",
        "selection_receipt",
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
        or set(hashes or {}) != set(ARMS)
        or any(
            hashes[arm] != hashlib.sha256(predictions[arm].encode()).hexdigest()
            for arm in ARMS
        )
        or set(success or {}) != set(ARMS)
        or any(not isinstance(success[arm], bool) for arm in ARMS)
        or set(normalizer or {}) != set(ARMS)
        or any(
            normalizer[arm]
            not in {"not_attempted", "exact", "normalized", "unrecoverable"}
            for arm in ARMS
        )
        or not isinstance(failures, Mapping)
        or set(failures) != {"plan", "grounded_plan", "retrieval", "synthesis"}
        or set(failures.get("retrieval") or {}) != set(PHASES)
        or set(failures.get("synthesis") or {}) != set(ARMS)
        or copied.get("prediction_changed")
        is not (predictions[CONTROL_ARM] != predictions[CANDIDATE_ARM])
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or copied["elapsed_seconds"] < 0
        or not isinstance(plan_receipt, Mapping)
        or target_plan.validate_receipt(plan_receipt) != dict(plan_receipt)
        or not isinstance(selection_receipt, Mapping)
        or selector.validate_receipt(selection_receipt) != dict(selection_receipt)
        or not isinstance(waves, Mapping)
        or set(waves) != set(PHASES)
        or not isinstance(effects, Mapping)
        or set(effects) != set(PHASES)
        or any(
            set(effect) != {"logical_queries", "fetch_requests"}
            or any(
                isinstance(number, bool)
                or not isinstance(number, int)
                or number < 0
                for number in effect.values()
            )
            for effect in effects.values()
        )
        or not isinstance(costs, Mapping)
        or set(costs) != {"model", "search", "system_total_tokens"}
        or not isinstance(costs.get("model"), Mapping)
        or set(costs["model"]) != set(counters._MODEL_COUNTERS)
        or any(
            isinstance(costs["model"].get(name), bool)
            or not isinstance(costs["model"].get(name), int)
            or costs["model"][name] < 0
            for name in counters._MODEL_COUNTERS
        )
        or set(costs.get("search") or {}) != set(PHASES)
        or any(
            not isinstance(costs["search"].get(phase), Mapping)
            or set(costs["search"][phase]) != set(counters._SEARCH_COUNTERS)
            or any(
                isinstance(costs["search"][phase].get(name), bool)
                or not isinstance(costs["search"][phase].get(name), int)
                or costs["search"][phase][name] < 0
                for name in counters._SEARCH_COUNTERS
            )
            for phase in PHASES
        )
        or isinstance(costs.get("system_total_tokens"), bool)
        or not isinstance(costs.get("system_total_tokens"), int)
        or costs["system_total_tokens"] < 0
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["grounded_plan_receipt"] != plan_receipt
        or receipt["selection_receipt"] != selection_receipt
        or receipt["prediction_changed"] != copied["prediction_changed"]
        or receipt["both_arms_model_success"] != all(success.values())
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read") is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.19 result envelope drifted")
    failure_values = (
        failures["plan"],
        failures["grounded_plan"],
        *failures["retrieval"].values(),
        *failures["synthesis"].values(),
    )
    if any(
        value is not None
        and (not isinstance(value, str) or not value or len(value) > 128)
        for value in failure_values
    ):
        raise ValueError("V2.51.19 failure accounting drifted")
    if (
        receipt["physical_query_count"]
        != sum(effects[phase]["logical_queries"] for phase in PHASES)
        or receipt["physical_fetch_count"]
        != sum(effects[phase]["fetch_requests"] for phase in PHASES)
        or effects[FIRST_PHASE]["logical_queries"] not in {0, 2}
        or effects[SECOND_PHASE]["logical_queries"] not in {0, 2}
        or effects[FIRST_PHASE]["fetch_requests"] > 6
        or effects[SECOND_PHASE]["fetch_requests"] > 8
        or receipt["model_provider_request_count"] != costs["model"]["requests"]
        or receipt["model_provider_attempt_count"] != costs["model"]["attempts"]
        or costs["system_total_tokens"]
        != costs["model"]["total_tokens"]
        + sum(costs["search"][phase]["total_tokens"] for phase in PHASES)
        or any(
            costs["search"][phase]["calls"]
            != int(effects[phase]["logical_queries"] > 0)
            or costs["search"][phase]["fetch_calls"]
            != effects[phase]["fetch_requests"]
            for phase in PHASES
        )
        or receipt["shared_first_wave_completed"] is not (waves[FIRST_PHASE] is not None)
        or receipt["shared_second_wave_completed"] is not (waves[SECOND_PHASE] is not None)
        or (waves[FIRST_PHASE] is None)
        is not (failures["retrieval"][FIRST_PHASE] is not None)
        or (waves[SECOND_PHASE] is None)
        is not (failures["retrieval"][SECOND_PHASE] is not None)
        or effects[SECOND_PHASE]["logical_queries"] > 0
        and waves[FIRST_PHASE] is None
    ):
        raise ValueError("V2.51.19 effect or cost replay drifted")
    if waves[FIRST_PHASE] is not None:
        first_wave = shared.validate_first_receipt(waves[FIRST_PHASE])
        if (
            first_wave["logical_query_count"]
            != effects[FIRST_PHASE]["logical_queries"]
            or first_wave["physical_fetch_count"]
            != effects[FIRST_PHASE]["fetch_requests"]
            or any(
                receipt["arm_metrics"][arm]["logical_fetch_count"]
                - receipt["arm_metrics"][arm]["second_wave_selected_url_count"]
                != first_wave["selected_url_count"]
                or receipt["arm_metrics"][arm]["usable_page_count"]
                - receipt["arm_metrics"][arm]["second_wave_usable_page_count"]
                != first_wave["usable_page_count"]
                for arm in ARMS
            )
        ):
            raise ValueError("V2.51.19 first-wave replay drifted")
    if waves[SECOND_PHASE] is not None:
        second_wave = validate_second_wave_receipt(waves[SECOND_PHASE])
        if (
            second_wave["logical_query_count"]
            != effects[SECOND_PHASE]["logical_queries"]
            or second_wave["physical_union_fetch_count"]
            != effects[SECOND_PHASE]["fetch_requests"]
            or second_wave["selection_receipt"] != selection_receipt
        ):
            raise ValueError("V2.51.19 second-wave replay drifted")
    for arm in ARMS:
        metric = receipt["arm_metrics"][arm]
        attempted = metric["synthesis_attempted"]
        succeeded = success[arm]
        failed = failures["synthesis"][arm]
        if (
            metric["model_success"] is not succeeded
            or metric["normalizer_status"] != normalizer[arm]
            or (not attempted and (succeeded or failed is not None or normalizer[arm] != "not_attempted"))
            or (
                attempted
                and succeeded
                and (failed is not None or normalizer[arm] not in {"exact", "normalized"})
            )
            or (
                attempted
                and not succeeded
                and (failed is None or normalizer[arm] != "unrecoverable")
            )
        ):
            raise ValueError("V2.51.19 synthesis replay drifted")
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
    "SECOND_WAVE_RECEIPT_ROLE",
    "run_paired_task",
    "validate_receipt",
    "validate_result",
    "validate_second_wave_receipt",
]
