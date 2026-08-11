"""Select target-record pages from one shared search/link frontier.

Control preserves stable query-local, action-source, then same-run page-link
order.  Candidate may reorder that exact complete public URL set, at the same
prefix length, only when URL and source metadata jointly improve a strict
target-record utility derived from a V2.51.17 grounded plan:

* the URL path binds to exactly one grounded row target or pivot;
* the URL host/path binds to a grounded visible authority term; and
* the URL/source-title surface exposes a requested field, a structured data
  endpoint, or a narrow record/detail endpoint marker.

The candidate covers distinct targets first and otherwise preserves stable
order.  If its lexicographic target-record utility does not strictly improve,
it is an exact copy of control.  Page bodies, queries, provider prose, scores,
predictions, labels, gold, evaluator output, rewards, and history are not
ranking inputs.  This pure component performs no I/O and assigns no signed
entropy/information-gain credit.
"""

from __future__ import annotations

import copy
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import unquote, urlsplit

from .clients import canonicalize_url
from .v24263_global_model_limiter import payload_sha256
from .v24269_task_union_discovery import _source_lead
from .v25001_page_visible_link_selection import (
    _page_results,
    _page_urls,
    _public_link,
    _sequence,
)


POLICY_ID = "v25118_grounded_target_record_frontier_selection_v1"
RECEIPT_ROLE = "v25118_content_free_target_record_frontier_selection_receipt"
MAXIMUM_TARGETS = 20
MAXIMUM_AUTHORITIES = 8
MAXIMUM_COLUMNS = 20
MAXIMUM_LINK_LABEL_CHARACTERS = 1_000

_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)
_GENERIC_AUTHORITY = frozenset(
    {
        "and",
        "database",
        "directory",
        "from",
        "index",
        "list",
        "official",
        "page",
        "public",
        "record",
        "registry",
        "source",
        "table",
        "the",
        "using",
        "web",
        "website",
    }
)
_STRUCTURED_MARKERS = frozenset(
    {"api", "csv", "data", "dataset", "json", "rdf", "tsv", "xml"}
)
_RECORD_MARKERS = frozenset(
    {
        "detail",
        "details",
        "entry",
        "item",
        "metadata",
        "profile",
        "project",
        "record",
        "records",
        "release",
        "releases",
        "show",
    }
)
_COUNT_FIELDS = (
    "prefix_cap",
    "grounded_target_count",
    "grounded_authority_term_count",
    "visible_non_key_column_count",
    "raw_query_local_source_count",
    "raw_action_source_count",
    "raw_first_wave_page_count",
    "raw_page_visible_link_count",
    "resolved_public_http_link_count",
    "rejected_invalid_or_non_http_link_count",
    "rejected_private_or_credential_link_count",
    "unique_search_url_count",
    "unique_page_link_url_count",
    "complete_unique_url_count_before_exclusion",
    "excluded_url_count",
    "available_unique_url_count",
    "ambiguous_target_url_count",
    "unique_target_bound_url_count",
    "target_authority_bound_url_count",
    "target_field_bearing_url_count",
    "target_structured_record_url_count",
    "target_record_url_count",
    "control_selected_url_count",
    "candidate_selected_url_count",
    "control_distinct_target_record_count",
    "candidate_distinct_target_record_count",
    "distinct_target_record_gain",
    "control_target_field_pair_count",
    "candidate_target_field_pair_count",
    "target_field_pair_gain",
    "control_structured_record_count",
    "candidate_structured_record_count",
    "structured_record_gain",
    "control_target_record_url_count",
    "candidate_target_record_url_count",
    "target_record_url_gain",
    "selection_changed",
)


def _text(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).split())


def _tokens(value: object) -> tuple[str, ...]:
    return tuple(token.casefold() for token in _TOKEN.findall(_text(value)) if token)


def _phrase_key(value: object) -> str:
    return "".join(
        character.casefold()
        for character in unicodedata.normalize("NFKC", str(value or ""))
        if character.isalnum() or "\u3400" <= character <= "\u9fff"
    )


def _vectors(values: Sequence[str], *, cap: int) -> tuple[tuple[str, ...], ...]:
    if isinstance(values, (str, bytes)) or len(values) > cap:
        raise ValueError("V2.51.18 grounded phrase vector drifted")
    output: list[tuple[str, ...]] = []
    seen: set[tuple[str, ...]] = set()
    for raw in values:
        if not isinstance(raw, str) or not 1 <= len(raw) <= 180:
            raise ValueError("V2.51.18 grounded phrase is invalid")
        vector = tuple(dict.fromkeys(_tokens(raw)))
        if not vector or vector in seen:
            continue
        output.append(vector)
        seen.add(vector)
    return tuple(output)


def _safe_columns(values: Sequence[str]) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not 1 <= len(values) <= MAXIMUM_COLUMNS:
        raise ValueError("V2.51.18 visible column vector drifted")
    output: list[str] = []
    for raw in values:
        if not isinstance(raw, str) or any(character in raw for character in "|\x00\r\n"):
            raise ValueError("V2.51.18 visible column is unsafe")
        value = _text(raw)
        if not value or len(value) > 80:
            raise ValueError("V2.51.18 visible column is invalid")
        output.append(value)
    return tuple(output)


def _raw_batches(raw: object) -> list[Mapping[str, Any]]:
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return []
    return [value for value in raw if isinstance(value, Mapping)]


def _action_sources(batch: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    trace = batch.get("hosted_search_trace")
    if not isinstance(trace, Mapping):
        return []
    output: list[Mapping[str, Any]] = []
    for action in trace.get("actions") or []:
        if not isinstance(action, Mapping):
            continue
        output.extend(
            source
            for source in (action.get("sources") or [])
            if isinstance(source, Mapping)
        )
    return output


def _search_lead(value: Mapping[str, Any]) -> dict[str, str] | None:
    projected = _source_lead(value)
    if projected is None:
        return None
    canonical = canonicalize_url(str(projected.get("url") or ""))
    if not canonical:
        return None
    return {
        "url": canonical,
        "fetch_url": str(projected.get("fetch_url") or value.get("fetch_url") or value.get("url") or canonical),
        "title": _text(value.get("title") or projected.get("title") or "")[:500],
        "member_label": "",
        "source_type": "shared_search_frontier",
    }


def _stable_unique(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw in values:
        lead = _search_lead(raw)
        if lead is None or lead["url"] in seen:
            continue
        output.append(lead)
        seen.add(lead["url"])
    return output


def _page_link_frontier(
    first_wave_page_batches: object,
) -> tuple[list[dict[str, str]], dict[str, int], set[str]]:
    pages = _page_results(first_wave_page_batches)
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    page_urls: set[str] = set()
    raw_count = resolved = invalid = private = 0
    for page in pages:
        page_urls.update(_page_urls(page))
        base = ""
        for name in ("url", "requested_url", "fetch_url"):
            raw_base = str(page.get(name) or "").strip()
            if canonicalize_url(raw_base):
                base = raw_base
                break
        links = _sequence(page.get("page_links"))
        if not base:
            raw_count += len(links)
            invalid += len(links)
            continue
        for raw in links:
            raw_count += 1
            if not isinstance(raw, Mapping):
                invalid += 1
                continue
            canonical, status = _public_link(raw.get("url"), base_url=base)
            if status == "private_or_credential":
                private += 1
                continue
            if status != "ok":
                invalid += 1
                continue
            resolved += 1
            if canonical in seen:
                continue
            label = _text(raw.get("text") or "")[:MAXIMUM_LINK_LABEL_CHARACTERS]
            output.append(
                {
                    "url": canonical,
                    "fetch_url": canonical,
                    "title": label[:500],
                    "member_label": label,
                    "source_type": "same_run_page_link_frontier",
                }
            )
            seen.add(canonical)
    return output, {
        "raw_first_wave_page_count": len(pages),
        "raw_page_visible_link_count": raw_count,
        "resolved_public_http_link_count": resolved,
        "rejected_invalid_or_non_http_link_count": invalid,
        "rejected_private_or_credential_link_count": private,
    }, page_urls


def _url_tokens(url: str) -> tuple[frozenset[str], frozenset[str], str]:
    canonical = canonicalize_url(url)
    if not canonical:
        return frozenset(), frozenset(), ""
    parsed = urlsplit(canonical)
    host = unquote(parsed.hostname or "")
    path = unquote(parsed.path or "")
    query = unquote(parsed.query or "")
    return (
        frozenset(_tokens(path + " " + query)),
        frozenset(_tokens(host + " " + path + " " + query)),
        path,
    )


def _authority_tokens(values: Sequence[str]) -> frozenset[str]:
    output: set[str] = set()
    for vector in _vectors(values, cap=MAXIMUM_AUTHORITIES):
        output.update(
            token
            for token in vector
            if len(token) >= 3 and token not in _GENERIC_AUTHORITY
        )
    return frozenset(output)


def _field_signals(lead: Mapping[str, str], columns: Sequence[str]) -> int:
    surface = " ".join(
        (
            str(lead.get("url") or ""),
            str(lead.get("title") or ""),
            str(lead.get("member_label") or ""),
        )
    )
    key = _phrase_key(surface)
    count = 0
    for column in columns[1:]:
        phrase = _phrase_key(column)
        tokens = set(_tokens(column))
        surface_tokens = set(_tokens(surface))
        if (len(phrase) >= 2 and phrase in key) or (tokens and tokens.issubset(surface_tokens)):
            count += 1
    return count


def _classify(
    lead: Mapping[str, str],
    *,
    targets: Sequence[tuple[str, ...]],
    authorities: frozenset[str],
    columns: Sequence[str],
) -> dict[str, Any]:
    path_tokens, all_tokens, path = _url_tokens(str(lead.get("url") or ""))
    matches = tuple(
        index for index, vector in enumerate(targets) if set(vector).issubset(path_tokens)
    )
    unique_target = matches[0] if len(matches) == 1 else None
    authority_bound = bool(authorities and authorities.intersection(all_tokens))
    fields = _field_signals(lead, columns)
    lower_path = path.casefold()
    suffix_structured = lower_path.endswith((".json", ".xml", ".csv", ".tsv", ".rdf"))
    structured = bool(suffix_structured or _STRUCTURED_MARKERS.intersection(path_tokens))
    record_hint = bool(_RECORD_MARKERS.intersection(path_tokens))
    target_authority = unique_target is not None and authority_bound
    record = bool(target_authority and (fields > 0 or structured or record_hint))
    return {
        "target_matches": matches,
        "unique_target": unique_target,
        "authority_bound": authority_bound,
        "field_signals": fields if target_authority else 0,
        "structured": bool(target_authority and structured),
        "record": record,
    }


def _utility(
    selected: Sequence[Mapping[str, str]],
    classifications: Mapping[str, Mapping[str, Any]],
) -> tuple[int, int, int, int]:
    distinct: set[int] = set()
    field_pairs = structured = records = 0
    for lead in selected:
        value = classifications[str(lead["url"])]
        if not value["record"]:
            continue
        records += 1
        distinct.add(int(value["unique_target"]))
        field_pairs += int(value["field_signals"])
        structured += int(value["structured"])
    return len(distinct), field_pairs, structured, records


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(value[name]) for name in _COUNT_FIELDS},
        "strategy_eligible": bool(value["strategy_eligible"]),
        "mechanism_engaged": bool(value["mechanism_engaged"]),
        "control_preserves_query_local_action_then_page_link_order": True,
        "same_complete_public_url_set_before_cap": True,
        "same_matched_prefix_length": True,
        "target_binding_requires_exactly_one_grounded_path_vector": True,
        "authority_binding_requires_grounded_distinctive_url_token": True,
        "record_signal_requires_visible_field_or_narrow_endpoint_surface": True,
        "candidate_covers_distinct_grounded_targets_before_duplicates": True,
        "candidate_published_only_for_strict_lexicographic_record_utility_gain": True,
        "relative_links_resolved_against_same_run_attesting_page": True,
        "stable_order_preserved_inside_equal_utility_partitions": True,
        "source_title_or_anchor_used_only_for_visible_field_lexical_signal": True,
        "page_body_query_provider_narrative_score_prediction_or_answer_used_for_ranking": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "additional_query_fetch_model_token_context_wall_or_network_budget": False,
        "contains_question_target_authority_column_query_url_title_anchor_page_prediction_answer_hash_opaque_id_or_credential": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def select_target_record_frontier(
    first_wave_page_batches: object,
    second_wave_raw: object,
    *,
    row_targets: Sequence[str],
    pivots: Sequence[str],
    authority_terms: Sequence[str],
    columns: Sequence[str],
    cap: int,
    exclude_urls: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
        raise ValueError("V2.51.18 prefix cap is invalid")
    if isinstance(exclude_urls, (str, bytes)):
        raise ValueError("V2.51.18 exclusion vector is invalid")
    required = _safe_columns(columns)
    targets = _vectors([*row_targets, *pivots], cap=MAXIMUM_TARGETS)
    authorities = _authority_tokens(authority_terms)
    batches = _raw_batches(second_wave_raw)
    local_values = [
        result
        for batch in batches
        for result in (batch.get("results") or [])
        if isinstance(result, Mapping)
    ]
    action_values = [source for batch in batches for source in _action_sources(batch)]
    local = _stable_unique(local_values)
    local_urls = {lead["url"] for lead in local}
    action = [lead for lead in _stable_unique(action_values) if lead["url"] not in local_urls]
    links, link_counts, page_urls = _page_link_frontier(first_wave_page_batches)
    search_urls = {lead["url"] for lead in (*local, *action)}
    unique_links = [lead for lead in links if lead["url"] not in search_urls]
    complete = [*local, *action, *unique_links]
    excluded = {
        canonicalize_url(str(value))
        for value in exclude_urls
        if canonicalize_url(str(value))
    } | page_urls
    available = [lead for lead in complete if lead["url"] not in excluded]
    classifications = {
        lead["url"]: _classify(
            lead,
            targets=targets,
            authorities=authorities,
            columns=required,
        )
        for lead in available
    }
    control = copy.deepcopy(available[:cap])
    records = [lead for lead in available if classifications[lead["url"]]["record"]]

    def rank(lead: Mapping[str, str]) -> tuple[int, int, int]:
        value = classifications[str(lead["url"])]
        return (
            -int(value["field_signals"]),
            -int(value["structured"]),
            available.index(lead),
        )

    first_per_target: list[dict[str, str]] = []
    selected_targets: set[int] = set()
    for lead in sorted(records, key=rank):
        target = int(classifications[lead["url"]]["unique_target"])
        if target in selected_targets:
            continue
        first_per_target.append(lead)
        selected_targets.add(target)
    first_urls = {lead["url"] for lead in first_per_target}
    remaining_records = [lead for lead in sorted(records, key=rank) if lead["url"] not in first_urls]
    record_urls = {lead["url"] for lead in records}
    remainder = [lead for lead in available if lead["url"] not in record_urls]
    candidate = copy.deepcopy([*first_per_target, *remaining_records, *remainder][: len(control)])
    control_utility = _utility(control, classifications)
    candidate_utility = _utility(candidate, classifications)
    if candidate_utility <= control_utility:
        candidate = copy.deepcopy(control)
        candidate_utility = control_utility
    changed = candidate != control
    if (
        len(control) != len(candidate)
        or len(control) > cap
        or changed is not (candidate_utility > control_utility)
        or {lead["url"] for lead in candidate}.difference(lead["url"] for lead in available)
    ):
        raise RuntimeError("V2.51.18 matched frontier invariant drifted")
    ambiguous = sum(len(value["target_matches"]) > 1 for value in classifications.values())
    unique_target = sum(value["unique_target"] is not None for value in classifications.values())
    target_authority = sum(
        value["unique_target"] is not None and value["authority_bound"]
        for value in classifications.values()
    )
    field_bearing = sum(
        value["unique_target"] is not None
        and value["authority_bound"]
        and value["field_signals"] > 0
        for value in classifications.values()
    )
    structured = sum(value["structured"] for value in classifications.values())
    record_count = sum(value["record"] for value in classifications.values())
    receipt = _receipt(
        {
            "prefix_cap": cap,
            "grounded_target_count": len(targets),
            "grounded_authority_term_count": len(authorities),
            "visible_non_key_column_count": max(0, len(required) - 1),
            "raw_query_local_source_count": len(local_values),
            "raw_action_source_count": len(action_values),
            **link_counts,
            "unique_search_url_count": len(local) + len(action),
            "unique_page_link_url_count": len(unique_links),
            "complete_unique_url_count_before_exclusion": len(complete),
            "excluded_url_count": len(complete) - len(available),
            "available_unique_url_count": len(available),
            "ambiguous_target_url_count": ambiguous,
            "unique_target_bound_url_count": unique_target,
            "target_authority_bound_url_count": target_authority,
            "target_field_bearing_url_count": field_bearing,
            "target_structured_record_url_count": structured,
            "target_record_url_count": record_count,
            "control_selected_url_count": len(control),
            "candidate_selected_url_count": len(candidate),
            "control_distinct_target_record_count": control_utility[0],
            "candidate_distinct_target_record_count": candidate_utility[0],
            "distinct_target_record_gain": candidate_utility[0] - control_utility[0],
            "control_target_field_pair_count": control_utility[1],
            "candidate_target_field_pair_count": candidate_utility[1],
            "target_field_pair_gain": candidate_utility[1] - control_utility[1],
            "control_structured_record_count": control_utility[2],
            "candidate_structured_record_count": candidate_utility[2],
            "structured_record_gain": candidate_utility[2] - control_utility[2],
            "control_target_record_url_count": control_utility[3],
            "candidate_target_record_url_count": candidate_utility[3],
            "target_record_url_gain": candidate_utility[3] - control_utility[3],
            "selection_changed": int(changed),
            "strategy_eligible": bool(targets and authorities and records and control),
            "mechanism_engaged": changed,
        }
    )
    return {
        "artifact_version": 1,
        "policy_id": POLICY_ID,
        "control": control,
        "candidate": candidate,
        "content_free_receipt": receipt,
    }


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    bool_fields = ("strategy_eligible", "mechanism_engaged")
    true_flags = (
        "control_preserves_query_local_action_then_page_link_order",
        "same_complete_public_url_set_before_cap",
        "same_matched_prefix_length",
        "target_binding_requires_exactly_one_grounded_path_vector",
        "authority_binding_requires_grounded_distinctive_url_token",
        "record_signal_requires_visible_field_or_narrow_endpoint_surface",
        "candidate_covers_distinct_grounded_targets_before_duplicates",
        "candidate_published_only_for_strict_lexicographic_record_utility_gain",
        "relative_links_resolved_against_same_run_attesting_page",
        "stable_order_preserved_inside_equal_utility_partitions",
        "source_title_or_anchor_used_only_for_visible_field_lexical_signal",
    )
    false_flags = (
        "page_body_query_provider_narrative_score_prediction_or_answer_used_for_ranking",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "additional_query_fetch_model_token_context_wall_or_network_budget",
        "contains_question_target_authority_column_query_url_title_anchor_page_prediction_answer_hash_opaque_id_or_credential",
        "entropy_or_information_gain_assigns_signed_credit",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_COUNT_FIELDS,
        *bool_fields,
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
            for name in _COUNT_FIELDS
        )
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or copied["grounded_target_count"] > MAXIMUM_TARGETS
        or copied["grounded_authority_term_count"] > MAXIMUM_AUTHORITIES * 8
        or copied["visible_non_key_column_count"] >= MAXIMUM_COLUMNS
        or copied["resolved_public_http_link_count"]
        + copied["rejected_invalid_or_non_http_link_count"]
        + copied["rejected_private_or_credential_link_count"]
        != copied["raw_page_visible_link_count"]
        or copied["unique_search_url_count"]
        + copied["unique_page_link_url_count"]
        != copied["complete_unique_url_count_before_exclusion"]
        or copied["complete_unique_url_count_before_exclusion"]
        != copied["excluded_url_count"] + copied["available_unique_url_count"]
        or copied["ambiguous_target_url_count"] > copied["available_unique_url_count"]
        or copied["unique_target_bound_url_count"] > copied["available_unique_url_count"]
        or copied["target_authority_bound_url_count"]
        > copied["unique_target_bound_url_count"]
        or copied["target_field_bearing_url_count"]
        > copied["target_authority_bound_url_count"]
        or copied["target_structured_record_url_count"]
        > copied["target_authority_bound_url_count"]
        or copied["target_record_url_count"]
        > copied["target_authority_bound_url_count"]
        or copied["control_selected_url_count"]
        != copied["candidate_selected_url_count"]
        or copied["control_selected_url_count"] > copied["prefix_cap"]
        or copied["candidate_distinct_target_record_count"]
        < copied["control_distinct_target_record_count"]
        or copied["distinct_target_record_gain"]
        != copied["candidate_distinct_target_record_count"]
        - copied["control_distinct_target_record_count"]
        or copied["target_field_pair_gain"]
        != copied["candidate_target_field_pair_count"]
        - copied["control_target_field_pair_count"]
        or copied["structured_record_gain"]
        != copied["candidate_structured_record_count"]
        - copied["control_structured_record_count"]
        or copied["target_record_url_gain"]
        != copied["candidate_target_record_url_count"]
        - copied["control_target_record_url_count"]
        or copied["selection_changed"] not in {0, 1}
        or copied["mechanism_engaged"] is not bool(copied["selection_changed"])
        or copied["mechanism_engaged"]
        and not copied["strategy_eligible"]
        or copied["selection_changed"]
        is not int(
            (
                copied["candidate_distinct_target_record_count"],
                copied["candidate_target_field_pair_count"],
                copied["candidate_structured_record_count"],
                copied["candidate_target_record_url_count"],
            )
            > (
                copied["control_distinct_target_record_count"],
                copied["control_target_field_pair_count"],
                copied["control_structured_record_count"],
                copied["control_target_record_url_count"],
            )
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.51.18 target-record frontier receipt drifted")
    return copied


def validate_result(
    value: Mapping[str, Any],
    *,
    first_wave_page_batches: object,
    second_wave_raw: object,
    row_targets: Sequence[str],
    pivots: Sequence[str],
    authority_terms: Sequence[str],
    columns: Sequence[str],
    cap: int,
    exclude_urls: Sequence[str] | set[str] | frozenset[str] = (),
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    receipt = copied.get("content_free_receipt")
    if (
        set(copied)
        != {"artifact_version", "policy_id", "control", "candidate", "content_free_receipt"}
        or copied.get("artifact_version") != 1
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or copied
        != select_target_record_frontier(
            first_wave_page_batches,
            second_wave_raw,
            row_targets=row_targets,
            pivots=pivots,
            authority_terms=authority_terms,
            columns=columns,
            cap=cap,
            exclude_urls=exclude_urls,
        )
    ):
        raise ValueError("V2.51.18 target-record selection replay drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "RECEIPT_ROLE",
    "select_target_record_frontier",
    "validate_receipt",
    "validate_result",
]
