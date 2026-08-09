"""Content-free reachability receipt for evidence-conditioned second waves.

This observer is deliberately outside the retrieval policy.  It receives the
visible question plus private same-forward query/page traces and emits counts
only.  A resolved token must be absent from the question, present in the
shared first-wave pages, present in an arm's second-wave query, and present in
that arm's fetched second-wave page.  A page is schema-bearing only when it
also contains tokens from at least two visible requested columns.

The receipt therefore measures ``first-wave supported pivot -> second-wave
schema page`` without retaining the pivot, query, URL, title, page, value,
prediction, task identity, or a hash of any of them.  It neither selects pages
nor assigns entropy/information-gain credit.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from .v24286_visible_schema_runtime import extract_robust_visible_columns


POLICY_ID = "v25026_same_forward_resolved_schema_reachability_v1"
ROLE = "v25026_content_free_resolved_schema_reachability_receipt"
SHARED_PHASE = "shared_first_wave"
CONTROL_ARM = "legacy_completed_queries"
CANDIDATE_ARM = "second_wave_hybrid_queries"
ARMS = (CONTROL_ARM, CANDIDATE_ARM)
PHASES = (SHARED_PHASE, *ARMS)
MAXIMUM_PAGE_COUNT_PER_PHASE = 10
MAXIMUM_PAGE_CHARACTERS = 5_000

_TOKEN = re.compile(
    r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,62}[A-Za-z0-9])|[\u3400-\u9fff]{2,16}"
)
_GENERIC = frozenset(
    {
        "about", "answer", "data", "database", "domain", "exact", "facts",
        "fields", "find", "from", "list", "official", "page", "public",
        "record", "records", "result", "results", "return", "search",
        "source", "sources", "table", "value", "values", "web",
    }
)
_COUNT_FIELDS = (
    "shared_page_count",
    "shared_evidence_token_count",
    "visible_question_token_count",
    "visible_schema_column_count",
    "minimum_schema_columns_per_page",
    "control_second_wave_query_count",
    "control_second_wave_page_count",
    "control_supported_novel_query_token_count",
    "control_pivot_supported_page_count",
    "control_schema_bearing_page_count",
    "control_resolved_schema_page_count",
    "candidate_second_wave_query_count",
    "candidate_second_wave_page_count",
    "candidate_supported_novel_query_token_count",
    "candidate_pivot_supported_page_count",
    "candidate_schema_bearing_page_count",
    "candidate_resolved_schema_page_count",
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _text(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def _all_tokens(value: object) -> frozenset[str]:
    return frozenset(
        match.group(0).casefold()
        for match in _TOKEN.finditer(_text(value))
    )


def _tokens(value: object) -> frozenset[str]:
    return frozenset(token for token in _all_tokens(value) if token not in _GENERIC)


def _page_text(page: Mapping[str, Any]) -> str:
    return " ".join(
        (
            _text(page.get("title")),
            _text(page.get("content") or page.get("raw_content"))[
                :MAXIMUM_PAGE_CHARACTERS
            ],
        )
    )


def _bounded_pages(value: object) -> list[Mapping[str, Any]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("V2.50.26 page trace is not a sequence")
    output: list[Mapping[str, Any]] = []
    for page in value:
        if not isinstance(page, Mapping):
            raise ValueError("V2.50.26 page trace contains a non-mapping")
        if len(output) < MAXIMUM_PAGE_COUNT_PER_PHASE and _page_text(page).strip():
            output.append(page)
    return output


def _queries(value: object) -> tuple[str, str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        raise ValueError("V2.50.26 requires exactly two queries per phase")
    output = tuple(_text(item) for item in value)
    if any(not item for item in output):
        raise ValueError("V2.50.26 query trace contains an empty query")
    return output  # type: ignore[return-value]


def _schema_signatures(question: str) -> tuple[frozenset[str], ...]:
    columns = extract_robust_visible_columns(question)
    return tuple(tokens for column in columns if (tokens := _all_tokens(column)))


def _arm_counts(
    *,
    queries: tuple[str, str],
    pages: Sequence[Mapping[str, Any]],
    question_tokens: frozenset[str],
    shared_tokens: frozenset[str],
    schema: Sequence[frozenset[str]],
) -> dict[str, int]:
    query_tokens = set().union(*(_tokens(query) for query in queries))
    supported = frozenset(query_tokens & (shared_tokens - question_tokens))
    pivot_pages = 0
    schema_pages = 0
    resolved_schema_pages = 0
    required_schema = min(2, len(schema))
    for page in pages:
        tokens = _tokens(_page_text(page))
        all_tokens = _all_tokens(_page_text(page))
        pivot = bool(tokens & supported)
        schema_count = sum(bool(all_tokens & signature) for signature in schema)
        schema_bearing = required_schema > 0 and schema_count >= required_schema
        pivot_pages += int(pivot)
        schema_pages += int(schema_bearing)
        resolved_schema_pages += int(pivot and schema_bearing)
    return {
        "second_wave_query_count": len(queries),
        "second_wave_page_count": len(pages),
        "supported_novel_query_token_count": len(supported),
        "pivot_supported_page_count": pivot_pages,
        "schema_bearing_page_count": schema_pages,
        "resolved_schema_page_count": resolved_schema_pages,
    }


def build_receipt(
    question: str,
    phase_queries: Mapping[str, Sequence[str]],
    phase_pages: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    visible = _text(question)
    if not visible or set(phase_queries) != set(PHASES) or set(phase_pages) != set(PHASES):
        raise ValueError("V2.50.26 phase boundary drifted")
    queries = {phase: _queries(phase_queries[phase]) for phase in PHASES}
    pages = {phase: _bounded_pages(phase_pages[phase]) for phase in PHASES}
    question_tokens = _tokens(visible)
    shared_tokens = frozenset(
        set().union(*(_tokens(_page_text(page)) for page in pages[SHARED_PHASE]))
        if pages[SHARED_PHASE]
        else set()
    )
    schema = _schema_signatures(visible)
    counts = {
        arm: _arm_counts(
            queries=queries[arm],
            pages=pages[arm],
            question_tokens=question_tokens,
            shared_tokens=shared_tokens,
            schema=schema,
        )
        for arm in ARMS
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "shared_page_count": len(pages[SHARED_PHASE]),
        "shared_evidence_token_count": len(shared_tokens),
        "visible_question_token_count": len(question_tokens),
        "visible_schema_column_count": len(schema),
        "minimum_schema_columns_per_page": min(2, len(schema)),
        **{
            f"{arm_name}_{name}": count
            for arm, arm_name in ((CONTROL_ARM, "control"), (CANDIDATE_ARM, "candidate"))
            for name, count in counts[arm].items()
        },
        "candidate_resolved_schema_page_strict_advantage": (
            counts[CANDIDATE_ARM]["resolved_schema_page_count"]
            > counts[CONTROL_ARM]["resolved_schema_page_count"]
        ),
        "same_forward_private_trace_only": True,
        "observer_changes_query_selection_fetch_projection_evidence_or_prediction": False,
        "contains_question_query_url_title_page_pivot_schema_value_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    true_flags = ("same_forward_private_trace_only",)
    false_flags = (
        "observer_changes_query_selection_fetch_projection_evidence_or_prediction",
        "contains_question_query_url_title_page_pivot_schema_value_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "file_environment_network_model_search_fetch_process_or_evaluator_accessed",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version", "role", "policy_id", *_COUNT_FIELDS,
        "candidate_resolved_schema_page_strict_advantage", *true_flags,
        *false_flags, "receipt_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _COUNT_FIELDS
        )
        or copied["shared_page_count"] > MAXIMUM_PAGE_COUNT_PER_PHASE
        or copied["visible_schema_column_count"] < 1
        or copied["minimum_schema_columns_per_page"]
        != min(2, copied["visible_schema_column_count"])
        or copied["control_second_wave_query_count"] != 2
        or copied["candidate_second_wave_query_count"] != 2
        or copied["control_second_wave_page_count"] > MAXIMUM_PAGE_COUNT_PER_PHASE
        or copied["candidate_second_wave_page_count"] > MAXIMUM_PAGE_COUNT_PER_PHASE
        or any(
            copied[f"{arm}_resolved_schema_page_count"]
            > min(
                copied[f"{arm}_pivot_supported_page_count"],
                copied[f"{arm}_schema_bearing_page_count"],
            )
            for arm in ("control", "candidate")
        )
        or any(
            copied[f"{arm}_supported_novel_query_token_count"] == 0
            and (
                copied[f"{arm}_pivot_supported_page_count"] != 0
                or copied[f"{arm}_resolved_schema_page_count"] != 0
            )
            for arm in ("control", "candidate")
        )
        or copied.get("candidate_resolved_schema_page_strict_advantage")
        is not (
            copied["candidate_resolved_schema_page_count"]
            > copied["control_resolved_schema_page_count"]
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.50.26 resolved-schema reachability receipt drifted")
    return copied


__all__ = [
    "ARMS", "CANDIDATE_ARM", "CONTROL_ARM", "PHASES", "POLICY_ID", "ROLE",
    "SHARED_PHASE", "build_receipt", "payload_sha256", "validate_receipt",
]
