"""Shared-response paired runtime for identity/authority action selection.

One visible-only planning call produces the unchanged completed four-query
vector.  The first two legacy queries and at-most-six fetched pages execute
once and are shared by both arms.  The last two legacy queries also execute
once.  From that exact same second-wave response, the control keeps stable
query-local-then-action ordering while the candidate applies V2.49.98's
visible identity/authority binding only inside the action-source suffix.

The two at-most-four URL prefixes are fetched as one deduplicated physical
union and split back by canonical requested URL.  Thus each arm retains the
production logical envelope of four queries, ten fetches, and one synthesis;
the paired experiment performs at most four physical queries and fourteen
physical fetches.  Page text from an unselected URL never enters that arm.

Runtime task input is exactly ``opaque_id`` and ``question`` plus injected
bounded clients.  No benchmark label, mapping, gold, evaluator, score, reward,
historical result, or credential capability is accepted.  Entropy and
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
from .v24998_identity_authority_action_selection import (
    select_matched_prefixes,
    validate_receipt as validate_selection_receipt,
)


POLICY_ID = "v24999_shared_response_identity_authority_selection_runtime_v1"
ROLE = "v24999_shared_response_selection_runtime_result"
RECEIPT_ROLE = "v24999_content_free_shared_response_selection_receipt"
FIRST_WAVE_RECEIPT_ROLE = "v24999_content_free_first_wave_receipt"
SECOND_WAVE_RECEIPT_ROLE = "v24999_content_free_second_wave_union_receipt"
FIRST_PHASE = "shared_first_wave"
SECOND_PHASE = "shared_second_wave_union"
PHASES = (FIRST_PHASE, SECOND_PHASE)
ARMS = ("stable_first_seen", "identity_authority_action_selection")
CONTROL_ARM, CANDIDATE_ARM = ARMS
ARM_METRIC_KEYS = frozenset(
    {
        "planned_queries",
        "executed_queries",
        "logical_fetch_attempts",
        "usable_pages",
        "second_wave_selected_urls",
        "second_wave_bound_urls",
        "second_wave_target_bound_projected_pages",
        "second_wave_target_bound_records",
        "evidence_characters",
        "synthesis_attempted",
        "model_success",
        "normalizer_status",
    }
)


def _arm_order(opaque_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"v24999:{opaque_id}".encode()).digest()[0]
    return ARMS if digest % 2 == 0 else ARMS[::-1]


def _match_evidence(values: Mapping[str, str]) -> dict[str, str]:
    if set(values) != set(ARMS):
        raise ValueError("V2.49.99 evidence arm drifted")
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


def _mapping_failures(batches: object) -> int:
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return 0
    return sum(
        isinstance(batch, Mapping)
        and str(batch.get("error") or "")
        == "hosted search returned no query-local URL citation"
        and not bool(batch.get("results"))
        for batch in batches
    )


def _unrecoverable_failures(batches: object) -> int:
    if not isinstance(batches, Sequence) or isinstance(batches, (str, bytes)):
        return 0
    return sum(
        isinstance(batch, Mapping)
        and bool(batch.get("error"))
        and str(batch.get("error") or "")
        != "hosted search returned no query-local URL citation"
        for batch in batches
    )


def _first_receipt(
    *,
    discovery: Mapping[str, Any],
    fetch: Mapping[str, Any],
    selected_urls: int,
    usable_pages: int,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": FIRST_WAVE_RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "logical_query_count": int(discovery["logical_query_count"]),
        "query_local_result_count": int(discovery["raw_query_local_result_count"]),
        "action_source_count": int(discovery["raw_action_source_count"]),
        "query_local_mapping_failure_count": int(
            discovery["raw_query_local_mapping_failure_count"]
        ),
        "unrecoverable_search_failure_count": int(
            discovery["raw_unrecoverable_failure_count"]
        ),
        "union_source_count": int(discovery["union_source_count"]),
        "selected_url_count": int(selected_urls),
        "physical_fetch_count": int(discovery["fetch_requested_source_count"]),
        "usable_page_count": int(usable_pages),
        "projected_page_count": int(fetch["projected_page_count"]),
        "retained_record_count": int(fetch["retained_record_count"]),
        "stable_query_local_then_action_order": True,
        "shared_byte_equal_between_arms": True,
        "provider_narrative_or_snippet_forwarded": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "contains_question_query_url_host_title_page_record_value_prediction_answer_hash_opaque_id_or_credential": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
        "discovery_receipt": copy.deepcopy(dict(discovery)),
        "fetch_receipt": copy.deepcopy(dict(fetch)),
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_first_receipt(value)


def validate_first_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    discovery = copied.get("discovery_receipt")
    fetch = copied.get("fetch_receipt")
    counts = (
        "logical_query_count",
        "query_local_result_count",
        "action_source_count",
        "query_local_mapping_failure_count",
        "unrecoverable_search_failure_count",
        "union_source_count",
        "selected_url_count",
        "physical_fetch_count",
        "usable_page_count",
        "projected_page_count",
        "retained_record_count",
    )
    true_flags = (
        "stable_query_local_then_action_order",
        "shared_byte_equal_between_arms",
    )
    false_flags = (
        "provider_narrative_or_snippet_forwarded",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "contains_question_query_url_host_title_page_record_value_prediction_answer_hash_opaque_id_or_credential",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
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
        or copied.get("role") != FIRST_WAVE_RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in counts
        )
        or copied["logical_query_count"] != 2
        or copied["selected_url_count"] > 6
        or copied["physical_fetch_count"] != copied["selected_url_count"]
        or copied["usable_page_count"] > copied["physical_fetch_count"]
        or copied["projected_page_count"] > copied["physical_fetch_count"]
        or copied["retained_record_count"] > copied["projected_page_count"] * 128
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or not isinstance(discovery, Mapping)
        or not isinstance(fetch, Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.99 first-wave receipt drifted")
    validate_discovery_receipt(discovery)
    validate_fetch_receipt(fetch)
    if (
        discovery["logical_query_count"] != copied["logical_query_count"]
        or discovery["raw_query_local_result_count"]
        != copied["query_local_result_count"]
        or discovery["raw_action_source_count"] != copied["action_source_count"]
        or discovery["raw_query_local_mapping_failure_count"]
        != copied["query_local_mapping_failure_count"]
        or discovery["raw_unrecoverable_failure_count"]
        != copied["unrecoverable_search_failure_count"]
        or discovery["union_source_count"] != copied["union_source_count"]
        or discovery["fetch_requested_source_count"]
        != copied["physical_fetch_count"]
        or discovery["fetch_usable_page_count"] != copied["usable_page_count"]
        or fetch["fetch_calls_snapshot"] != copied["physical_fetch_count"]
        or fetch["projected_page_count"] != copied["projected_page_count"]
        or fetch["retained_record_count"] != copied["retained_record_count"]
    ):
        raise ValueError("V2.49.99 first-wave nested receipt drifted")
    return copied


def _second_receipt(
    *,
    selection: Mapping[str, Any],
    fetch: Mapping[str, Any],
    mapping_failures: int,
    unrecoverable_failures: int,
    union_fetches: int,
    union_usable_pages: int,
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
        "control_bound_action_url_count": int(
            selection["control_bound_action_url_count"]
        ),
        "candidate_bound_action_url_count": int(
            selection["candidate_bound_action_url_count"]
        ),
        "bound_action_url_gain": int(selection["bound_action_url_gain"]),
        "physical_union_fetch_count": int(union_fetches),
        "physical_union_usable_page_count": int(union_usable_pages),
        "projected_page_count": int(fetch["projected_page_count"]),
        "retained_record_count": int(fetch["retained_record_count"]),
        "selection_changed": bool(selection["selection_changed"]),
        "one_legacy_second_wave_search_response_shared": True,
        "query_local_prefix_preserved_in_both_arms": True,
        "two_arm_url_union_fetched_once": True,
        "unselected_page_text_never_enters_arm_evidence": True,
        "provider_narrative_or_snippet_forwarded": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "contains_question_identity_authority_query_url_host_title_page_record_value_prediction_answer_hash_opaque_id_or_credential": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
        "selection_receipt": copy.deepcopy(dict(selection)),
        "fetch_receipt": copy.deepcopy(dict(fetch)),
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_second_receipt(value)


def validate_second_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
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
        "control_bound_action_url_count",
        "candidate_bound_action_url_count",
        "bound_action_url_gain",
        "physical_union_fetch_count",
        "physical_union_usable_page_count",
        "projected_page_count",
        "retained_record_count",
    )
    bool_fields = ("selection_changed",)
    true_flags = (
        "one_legacy_second_wave_search_response_shared",
        "query_local_prefix_preserved_in_both_arms",
        "two_arm_url_union_fetched_once",
        "unselected_page_text_never_enters_arm_evidence",
    )
    false_flags = (
        "provider_narrative_or_snippet_forwarded",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "contains_question_identity_authority_query_url_host_title_page_record_value_prediction_answer_hash_opaque_id_or_credential",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *counts,
        *bool_fields,
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
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or copied["logical_query_count"] != 2
        or copied["control_selected_url_count"]
        != copied["candidate_selected_url_count"]
        or copied["control_selected_url_count"] > 4
        or copied["control_bound_action_url_count"]
        > copied["control_selected_url_count"]
        or copied["candidate_bound_action_url_count"]
        > copied["candidate_selected_url_count"]
        or copied["bound_action_url_gain"]
        != copied["candidate_bound_action_url_count"]
        - copied["control_bound_action_url_count"]
        or copied["physical_union_fetch_count"] > 8
        or copied["physical_union_usable_page_count"]
        > copied["physical_union_fetch_count"]
        or copied["projected_page_count"] > copied["physical_union_fetch_count"]
        or copied["retained_record_count"] > copied["projected_page_count"] * 128
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or not isinstance(selection, Mapping)
        or not isinstance(fetch, Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.99 second-wave receipt drifted")
    validate_selection_receipt(selection)
    validate_fetch_receipt(fetch)
    if (
        selection["control_selected_url_count"]
        != copied["control_selected_url_count"]
        or selection["candidate_selected_url_count"]
        != copied["candidate_selected_url_count"]
        or selection["control_bound_action_url_count"]
        != copied["control_bound_action_url_count"]
        or selection["candidate_bound_action_url_count"]
        != copied["candidate_bound_action_url_count"]
        or selection["bound_action_url_gain"] != copied["bound_action_url_gain"]
        or bool(selection["selection_changed"]) != copied["selection_changed"]
        or fetch["fetch_calls_snapshot"] != copied["physical_union_fetch_count"]
        or fetch["projected_page_count"] != copied["projected_page_count"]
        or fetch["retained_record_count"] != copied["retained_record_count"]
    ):
        raise ValueError("V2.49.99 second-wave nested receipt drifted")
    return copied


def _run_first_wave(
    queries: Sequence[str],
    *,
    search: Any,
    search_results_per_query: int,
) -> dict[str, Any]:
    if len(queries) != 2 or search_results_per_query != 3:
        raise ValueError("V2.49.99 first-wave boundary drifted")
    union = TaskUnionDiscoverySearchClient(search)
    batches = union.search_many(
        list(queries),
        max_results=search_results_per_query,
        search_depth="advanced",
        include_raw_content=False,
    )
    leads = score._lead_requests(batches, 1_000_000)
    selected = leads[:6]
    pages = union.fetch_urls(selected) if selected else []
    discovery = union.receipt()
    fetch = search.late_page_projection_receipt()
    return {
        "receipt": _first_receipt(
            discovery=discovery,
            fetch=fetch,
            selected_urls=len(selected),
            usable_pages=_usable_pages(pages),
        ),
        "page_batches": pages,
        "selected_urls": frozenset(
            canonicalize_url(str(item.get("url") or ""))
            for item in selected
            if canonicalize_url(str(item.get("url") or ""))
        ),
    }


def _union_requests(selection: Mapping[str, Any]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for arm in ("control", "candidate"):
        for raw in selection.get(arm) or []:
            if not isinstance(raw, Mapping):
                continue
            canonical = canonicalize_url(str(raw.get("url") or ""))
            if not canonical or canonical in seen:
                continue
            output.append(
                {
                    "url": str(raw.get("fetch_url") or raw.get("url") or ""),
                    "query": "shared second-wave selected public page",
                    "title": str(raw.get("title") or "")[:500],
                    "member_label": "",
                }
            )
            seen.add(canonical)
    return output


def _page_map(page_batches: object) -> dict[str, dict[str, str]]:
    output: dict[str, dict[str, str]] = {}
    if not isinstance(page_batches, Sequence) or isinstance(
        page_batches, (str, bytes)
    ):
        return output
    for batch in page_batches:
        if not isinstance(batch, Mapping):
            continue
        for result in batch.get("results") or []:
            if not isinstance(result, Mapping):
                continue
            requested = canonicalize_url(
                str(
                    result.get("requested_url")
                    or result.get("fetch_url")
                    or result.get("url")
                    or ""
                )
            )
            final = canonicalize_url(str(result.get("url") or ""))
            content = str(result.get("raw_content") or result.get("content") or "")
            if not requested or not final or not content or requested in output:
                continue
            output[requested] = {
                "requested_url": requested,
                "url": final,
                "title": str(result.get("title") or ""),
                "content": content,
            }
    return output


def _arm_second_pages(
    selected: Sequence[Mapping[str, Any]],
    pages: Mapping[str, Mapping[str, str]],
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen_final: set[str] = set()
    for lead in selected:
        requested = canonicalize_url(str(lead.get("url") or ""))
        page = pages.get(requested)
        if not isinstance(page, Mapping):
            continue
        final = canonicalize_url(str(page.get("url") or ""))
        if not final or final in seen_final:
            continue
        output.append(
            {
                "requested_url": requested,
                "url": final,
                "title": str(page.get("title") or ""),
                "content": str(page.get("content") or ""),
            }
        )
        seen_final.add(final)
    return output


def _target_bound_record_count(page: Mapping[str, str], search: Any) -> int:
    requested = str(page.get("requested_url") or "")
    content = str(page.get("content") or "")
    parent = str(search.parent_prefix_for(requested) or "")
    if (
        not requested
        or not content
        or not parent
        or content == parent
        or not content.startswith("[IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]\n")
    ):
        return 0
    lines = content.splitlines()
    try:
        header_end = next(
            index for index, line in enumerate(lines) if line.startswith("target_columns=")
        )
        footer = lines.index("[/IDENTITY-TARGET-BOUND LATE-PAGE RECORDS]")
    except (StopIteration, ValueError):
        return 0
    if footer <= header_end + 1:
        return 0
    count = 0
    for line in lines[header_end + 1 : footer]:
        try:
            record = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            return 0
        if (
            not isinstance(record, Mapping)
            or set(record) != {"record_id", "row", "cells"}
            or not isinstance(record.get("record_id"), str)
            or not record["record_id"]
            or not isinstance(record.get("row"), str)
            or not record["row"]
            or not isinstance(record.get("cells"), list)
            or not record["cells"]
            or any(
                not isinstance(cell, list)
                or len(cell) != 2
                or any(not isinstance(value, str) or not value for value in cell)
                for cell in record["cells"]
            )
        ):
            return 0
        count += 1
    return count


def _run_second_wave(
    queries: Sequence[str],
    *,
    question: str,
    search: Any,
    search_results_per_query: int,
    exclude_urls: frozenset[str],
) -> dict[str, Any]:
    if len(queries) != 2 or search_results_per_query != 3:
        raise ValueError("V2.49.99 second-wave boundary drifted")
    raw = search.search_many(
        list(queries),
        max_results=search_results_per_query,
        search_depth="advanced",
        include_raw_content=False,
    )
    selection = select_matched_prefixes(
        raw,
        question=question,
        cap=4,
        exclude_urls=exclude_urls,
    )
    requests = _union_requests(selection)
    fetched = search.fetch_urls(requests) if requests else []
    page_map = _page_map(fetched)
    pages = {
        CONTROL_ARM: _arm_second_pages(selection["control"], page_map),
        CANDIDATE_ARM: _arm_second_pages(selection["candidate"], page_map),
    }
    fetch = search.late_page_projection_receipt()
    selection_receipt = selection["content_free_receipt"]
    return {
        "receipt": _second_receipt(
            selection=selection_receipt,
            fetch=fetch,
            mapping_failures=_mapping_failures(raw),
            unrecoverable_failures=_unrecoverable_failures(raw),
            union_fetches=len(requests),
            union_usable_pages=_usable_pages(fetched),
        ),
        "selection_receipt": copy.deepcopy(selection_receipt),
        "selected": {
            CONTROL_ARM: copy.deepcopy(selection["control"]),
            CANDIDATE_ARM: copy.deepcopy(selection["candidate"]),
        },
        "pages": pages,
        "target_bound_records": {
            arm: sum(_target_bound_record_count(page, search) for page in pages[arm])
            for arm in ARMS
        },
        "target_bound_pages": {
            arm: sum(
                _target_bound_record_count(page, search) > 0 for page in pages[arm]
            )
            for arm in ARMS
        },
    }


def _empty_arm_metric() -> dict[str, Any]:
    return {
        "planned_queries": 4,
        "executed_queries": 0,
        "logical_fetch_attempts": 0,
        "usable_pages": 0,
        "second_wave_selected_urls": 0,
        "second_wave_bound_urls": 0,
        "second_wave_target_bound_projected_pages": 0,
        "second_wave_target_bound_records": 0,
        "evidence_characters": 0,
        "synthesis_attempted": False,
        "model_success": False,
        "normalizer_status": "not_attempted",
    }


def _main_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "provider_unique_query_count": int(value["provider_unique_query_count"]),
        "shared_first_wave_completed": bool(value["shared_first_wave_completed"]),
        "shared_second_wave_completed": bool(value["shared_second_wave_completed"]),
        "selection_strategy_eligible": bool(value["selection_strategy_eligible"]),
        "selection_changed": bool(value["selection_changed"]),
        "bound_action_url_gain": int(value["bound_action_url_gain"]),
        "candidate_target_bound_projected_page_gain": int(
            value["candidate_target_bound_projected_page_gain"]
        ),
        "candidate_target_bound_record_gain": int(
            value["candidate_target_bound_record_gain"]
        ),
        "target_bound_record_mechanism_engaged": bool(
            value["target_bound_record_mechanism_engaged"]
        ),
        "first_synthesis_arm": str(value["first_synthesis_arm"]),
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
        "one_visible_only_planning_call": True,
        "same_completed_legacy_query_vector_both_arms": True,
        "one_physical_first_wave_reused_by_both_arms": True,
        "one_physical_second_wave_response_reused_by_both_arms": True,
        "query_local_citation_prefix_preserved": True,
        "two_arm_second_wave_url_union_fetched_once": True,
        "page_text_partitioned_by_selected_canonical_url": True,
        "per_arm_logical_query_cap": 4,
        "per_arm_logical_fetch_cap": 10,
        "per_arm_synthesis_call_cap": 1,
        "physical_query_cap": 4,
        "physical_fetch_cap": 14,
        "same_projector_evidence_prompt_model_output_and_deadline": True,
        "external_gate_not_production_latency_or_throughput": True,
        "production_runtime_or_exact220_authorized": False,
        "contains_question_identity_authority_query_url_host_title_page_record_value_prediction_answer_hash_opaque_id_or_credential": False,
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
    counts = (
        "provider_unique_query_count",
        "bound_action_url_gain",
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
        "shared_first_wave_completed",
        "shared_second_wave_completed",
        "selection_strategy_eligible",
        "selection_changed",
        "target_bound_record_mechanism_engaged",
        "prediction_changed",
        "both_arms_model_success",
    )
    true_flags = (
        "one_visible_only_planning_call",
        "same_completed_legacy_query_vector_both_arms",
        "one_physical_first_wave_reused_by_both_arms",
        "one_physical_second_wave_response_reused_by_both_arms",
        "query_local_citation_prefix_preserved",
        "two_arm_second_wave_url_union_fetched_once",
        "page_text_partitioned_by_selected_canonical_url",
        "same_projector_evidence_prompt_model_output_and_deadline",
        "external_gate_not_production_latency_or_throughput",
    )
    false_flags = (
        "production_runtime_or_exact220_authorized",
        "contains_question_identity_authority_query_url_host_title_page_record_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *counts,
        "candidate_target_bound_projected_page_gain",
        "candidate_target_bound_record_gain",
        *bool_fields,
        "first_synthesis_arm",
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
            for name in counts
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or not -4 <= copied[name] <= 4 * 128
            for name in (
                "candidate_target_bound_projected_page_gain",
                "candidate_target_bound_record_gain",
            )
        )
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or copied["provider_unique_query_count"] > 4
        or copied["physical_query_count"] > 4
        or copied["physical_fetch_count"] > 14
        or copied["model_logical_call_count"] > 3
        or copied["model_provider_request_count"]
        > copied["model_logical_call_count"]
        or copied["model_provider_attempt_count"]
        < copied["model_provider_request_count"]
        or copied["per_arm_logical_query_cap"] != 4
        or copied["per_arm_logical_fetch_cap"] != 10
        or copied["per_arm_synthesis_call_cap"] != 1
        or copied["physical_query_cap"] != 4
        or copied["physical_fetch_cap"] != 14
        or copied.get("first_synthesis_arm") not in {*ARMS, "none"}
        or copied["selection_changed"] and not copied["selection_strategy_eligible"]
        or copied["target_bound_record_mechanism_engaged"]
        is not bool(
            copied["selection_changed"]
            and copied["bound_action_url_gain"] > 0
            and copied["candidate_target_bound_projected_page_gain"] > 0
            and copied["candidate_target_bound_record_gain"] > 0
        )
        or not isinstance(metrics, Mapping)
        or set(metrics) != set(ARMS)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.99 shared-response receipt drifted")
    attempts = successes = 0
    evidence: list[int] = []
    for arm in ARMS:
        metric = metrics[arm]
        if not isinstance(metric, Mapping) or set(metric) != ARM_METRIC_KEYS:
            raise ValueError("V2.49.99 arm metric schema drifted")
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
            raise ValueError("V2.49.99 arm metric count drifted")
        if (
            metric["planned_queries"] != 4
            or metric["executed_queries"] > 4
            or metric["logical_fetch_attempts"] > 10
            or metric["usable_pages"] > metric["logical_fetch_attempts"]
            or metric["second_wave_selected_urls"] > 4
            or metric["second_wave_bound_urls"]
            > metric["second_wave_selected_urls"]
            or metric["second_wave_target_bound_projected_pages"]
            > metric["second_wave_selected_urls"]
            or metric["second_wave_target_bound_records"]
            < metric["second_wave_target_bound_projected_pages"]
            or metric["evidence_characters"] > 60_000
            or not isinstance(metric.get("synthesis_attempted"), bool)
            or not isinstance(metric.get("model_success"), bool)
            or metric["model_success"] and not metric["synthesis_attempted"]
            or metric.get("normalizer_status")
            not in {"not_attempted", "exact", "normalized", "unrecoverable"}
        ):
            raise ValueError("V2.49.99 arm metric invariant drifted")
        attempts += int(metric["synthesis_attempted"])
        successes += int(metric["model_success"])
        evidence.append(metric["evidence_characters"])
    control = metrics[CONTROL_ARM]
    candidate = metrics[CANDIDATE_ARM]
    if (
        len(set(evidence)) != 1
        or copied["bound_action_url_gain"]
        != candidate["second_wave_bound_urls"]
        - control["second_wave_bound_urls"]
        or copied["candidate_target_bound_projected_page_gain"]
        != candidate["second_wave_target_bound_projected_pages"]
        - control["second_wave_target_bound_projected_pages"]
        or copied["candidate_target_bound_record_gain"]
        != candidate["second_wave_target_bound_records"]
        - control["second_wave_target_bound_records"]
        or copied["model_logical_call_count"] != 1 + attempts
        or copied["both_arms_model_success"] is not (successes == 2)
    ):
        raise ValueError("V2.49.99 paired accounting drifted")
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
    del monotonic
    visible = score.validate_visible_task(task)
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.49.99 requires the bounded global model limiter")
    if (
        not isinstance(searches, Mapping)
        or set(searches) != set(PHASES)
        or any(
            not isinstance(searches[phase], RobustLatePageBoundSearchClient)
            for phase in PHASES
        )
        or len({id(searches[phase]) for phase in PHASES}) != len(PHASES)
    ):
        raise ValueError("V2.49.99 requires two distinct robust search clients")
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
        raise ValueError("V2.49.99 production-shaped budget drifted")
    order = tuple(arm_order or _arm_order(visible["opaque_id"]))
    if len(order) != 2 or set(order) != set(ARMS):
        raise ValueError("V2.49.99 arm order drifted")

    model_before = paired._counter(model, paired._MODEL_COUNTERS)
    search_before = {
        phase: paired._counter(searches[phase], paired._SEARCH_COUNTERS)
        for phase in PHASES
    }
    if any(any(snapshot.values()) for snapshot in search_before.values()):
        raise ValueError("V2.49.99 requires pristine physical search clients")
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

    queries = list(plan["queries"])
    first: dict[str, Any] | None = None
    second: dict[str, Any] | None = None
    shared_pages: list[dict[str, str]] = []
    second_pages: dict[str, list[dict[str, str]]] = {arm: [] for arm in ARMS}
    empty_selection = select_matched_prefixes(
        [], question=visible["question"], cap=4
    )["content_free_receipt"]
    selection_receipt = copy.deepcopy(empty_selection)
    target_bound_records = {arm: 0 for arm in ARMS}
    target_bound_pages = {arm: 0 for arm in ARMS}
    try:
        first = _run_first_wave(
            queries[:2],
            search=observers[FIRST_PHASE],
            search_results_per_query=limits.search_results_per_query,
        )
        shared_pages = paired._pages(first["page_batches"])
    except BaseException as exc:
        failures["retrieval"][FIRST_PHASE] = paired._safe_failure(exc)

    if first is not None:
        try:
            second = _run_second_wave(
                queries[2:],
                question=visible["question"],
                search=observers[SECOND_PHASE],
                search_results_per_query=limits.search_results_per_query,
                exclude_urls=first["selected_urls"],
            )
            selection_receipt = copy.deepcopy(second["selection_receipt"])
            second_pages = {
                arm: copy.deepcopy(second["pages"][arm]) for arm in ARMS
            }
            target_bound_records = dict(second["target_bound_records"])
            target_bound_pages = dict(second["target_bound_pages"])
        except BaseException as exc:
            failures["retrieval"][SECOND_PHASE] = paired._safe_failure(exc)
    else:
        failures["retrieval"][SECOND_PHASE] = "SharedFirstWaveFailure"

    arm_pages = {arm: [*shared_pages, *second_pages[arm]] for arm in ARMS}
    evidence = _match_evidence(
        {
            arm: compact._compact_evidence(arm_pages[arm], limits) for arm in ARMS
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
                raise ValueError("V2.49.99 synthesis table contract failed")
            predictions[arm] = parsed
            success[arm] = True
        except BaseException as exc:
            normalizer_status[arm] = "unrecoverable"
            failures["synthesis"][arm] = paired._safe_failure(exc)

    phase_receipts = {
        FIRST_PHASE: None if first is None else copy.deepcopy(first["receipt"]),
        SECOND_PHASE: None if second is None else copy.deepcopy(second["receipt"]),
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
    first_selected = 0 if first is None else int(first["receipt"]["selected_url_count"])
    first_usable = len(shared_pages)
    arm_metrics = {arm: _empty_arm_metric() for arm in ARMS}
    for arm in ARMS:
        arm_metrics[arm].update(
            {
                "executed_queries": sum(
                    effect["logical_queries"] for effect in physical_effects.values()
                ),
                "logical_fetch_attempts": first_selected
                + int(selection_receipt[
                    "control_selected_url_count"
                    if arm == CONTROL_ARM
                    else "candidate_selected_url_count"
                ]),
                "usable_pages": first_usable + len(second_pages[arm]),
                "second_wave_selected_urls": int(
                    selection_receipt[
                        "control_selected_url_count"
                        if arm == CONTROL_ARM
                        else "candidate_selected_url_count"
                    ]
                ),
                "second_wave_bound_urls": int(
                    selection_receipt[
                        "control_bound_action_url_count"
                        if arm == CONTROL_ARM
                        else "candidate_bound_action_url_count"
                    ]
                ),
                "second_wave_target_bound_projected_pages": int(
                    target_bound_pages[arm]
                ),
                "second_wave_target_bound_records": int(
                    target_bound_records[arm]
                ),
                "evidence_characters": len(evidence[arm]),
                "synthesis_attempted": attempted[arm],
                "model_success": success[arm],
                "normalizer_status": normalizer_status[arm],
            }
        )
    physical_queries = sum(
        effect["logical_queries"] for effect in physical_effects.values()
    )
    physical_fetches = sum(
        effect["fetch_requests"] for effect in physical_effects.values()
    )
    page_gain = (
        target_bound_pages[CANDIDATE_ARM] - target_bound_pages[CONTROL_ARM]
    )
    record_gain = (
        target_bound_records[CANDIDATE_ARM] - target_bound_records[CONTROL_ARM]
    )
    content_free = _main_receipt(
        {
            "provider_unique_query_count": plan["provider_unique_query_count"],
            "shared_first_wave_completed": first is not None,
            "shared_second_wave_completed": second is not None,
            "selection_strategy_eligible": selection_receipt["strategy_eligible"],
            "selection_changed": selection_receipt["selection_changed"] == 1,
            "bound_action_url_gain": selection_receipt["bound_action_url_gain"],
            "candidate_target_bound_projected_page_gain": page_gain,
            "candidate_target_bound_record_gain": record_gain,
            "target_bound_record_mechanism_engaged": bool(
                selection_receipt["selection_changed"]
                and selection_receipt["bound_action_url_gain"] > 0
                and page_gain > 0
                and record_gain > 0
            ),
            "first_synthesis_arm": synthesis_order[0] if synthesis_order else "none",
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
        "selection_receipt": copy.deepcopy(selection_receipt),
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
    selection = copied.get("selection_receipt")
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
        or not isinstance(selection, Mapping)
        or validate_selection_receipt(selection) != dict(selection)
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
            > (6 if phase == FIRST_PHASE else 8)
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
        or receipt["selection_strategy_eligible"]
        != selection["strategy_eligible"]
        or receipt["selection_changed"] is not bool(selection["selection_changed"])
        or receipt["bound_action_url_gain"] != selection["bound_action_url_gain"]
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
        raise ValueError("V2.49.99 shared-response result drifted")
    for phase, validator in (
        (FIRST_PHASE, validate_first_receipt),
        (SECOND_PHASE, validate_second_receipt),
    ):
        phase_receipt = phases[phase]
        if phase_receipt is not None:
            if not isinstance(phase_receipt, Mapping):
                raise ValueError("V2.49.99 phase receipt absent")
            validator(phase_receipt)
            if failures["retrieval"][phase] is not None:
                raise ValueError("V2.49.99 successful phase retained failure")
        elif failures["retrieval"][phase] is None:
            raise ValueError("V2.49.99 missing phase without failure")
    if phases[SECOND_PHASE] is not None and (
        phases[SECOND_PHASE]["selection_receipt"] != selection
    ):
        raise ValueError("V2.49.99 selection receipt binding drifted")
    if phases[FIRST_PHASE] is None and (
        effects[FIRST_PHASE]["logical_queries"] != 2
        or phases[SECOND_PHASE] is not None
        or effects[SECOND_PHASE] != {"logical_queries": 0, "fetch_requests": 0}
        or failures["retrieval"][SECOND_PHASE] != "SharedFirstWaveFailure"
    ):
        raise ValueError("V2.49.99 first-wave failure boundary drifted")
    physical_queries = sum(effect["logical_queries"] for effect in effects.values())
    physical_fetches = sum(effect["fetch_requests"] for effect in effects.values())
    if (
        receipt["physical_query_count"] != physical_queries
        or receipt["physical_fetch_count"] != physical_fetches
        or receipt["shared_first_wave_completed"]
        is not (phases[FIRST_PHASE] is not None)
        or receipt["shared_second_wave_completed"]
        is not (phases[SECOND_PHASE] is not None)
        or evidence
        != {
            arm: receipt["arm_metrics"][arm]["evidence_characters"]
            for arm in ARMS
        }
        or any(
            successes[arm] != receipt["arm_metrics"][arm]["model_success"]
            for arm in ARMS
        )
    ):
        raise ValueError("V2.49.99 nested accounting drifted")
    for arm in ARMS:
        metric = receipt["arm_metrics"][arm]
        if (
            metric["synthesis_attempted"]
            is not (metric["normalizer_status"] != "not_attempted")
            or (
                not metric["synthesis_attempted"]
                and (successes[arm] or failures["synthesis"][arm] is not None)
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
            raise ValueError("V2.49.99 synthesis accounting drifted")
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
    "validate_first_receipt",
    "validate_receipt",
    "validate_result",
    "validate_second_receipt",
]
