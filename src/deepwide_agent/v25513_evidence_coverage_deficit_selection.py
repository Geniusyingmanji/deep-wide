"""Pure row-local evidence-coverage scheduling for one detail fetch.

V2.55.11 established that several rows can have admissible visible detail
links while a completed model table contains no literal ``Unknown`` cells.
Literal output text is therefore not a reliable epistemic-uncertainty signal.

This successor preserves V2.54.91 public/same-origin/path+anchor/one-URL-per-
row admissibility.  It constructs a local shadow copy of the completed table
whose non-key cells are all ``Unknown`` and replays the frozen V2.54.99 parser
over the already fetched parent pages.  A shadow candidate proves that one
row/field coordinate has one unique, safe, source-bound observation,
regardless of whether that observation equals the completed control value.
For every row with an admissible detail link, the scheduling priority is the
number of visible non-key fields without such coverage.  Maximum deficit wins;
ties use frozen table order and canonical URL.

The shadow table is never scored or returned.  No value, correctness, label,
truth, evaluator, reward, historical outcome, model confidence, or literal
``Unknown`` count enters scheduling.  The module performs no I/O, assigns zero
entropy/information-gain signed credit, and authorizes no run or evaluator.
"""

from __future__ import annotations

import copy
import hashlib
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import canonicalize_url
from . import v25432_source_authoritative_field_candidate as source
from . import v25491_visible_row_key_detail_selection as parent
from . import v25499_generic_mechanical_field_candidate as coverage


POLICY_ID = "v25513_evidence_coverage_deficit_selection_v1"
ROLE = "v25513_evidence_coverage_deficit_selection"
RECEIPT_ROLE = "v25513_content_free_evidence_coverage_selection_receipt"
MAXIMUM_DIRECT_REQUESTS = parent.MAXIMUM_DIRECT_REQUESTS
REQUEST_QUERY = "same-run visible row-key-bound evidence-deficit detail page"

_CANDIDATE_KEYS = frozenset(
    {
        "url",
        "row_identity",
        "anchor_text",
        "attesting_page_url",
        "row_index",
        "covered_nonkey_cell_count",
        "evidence_deficit_count",
    }
)
_REQUEST_KEYS = frozenset({"url", "query", "title", "member_label"})
_COUNT_FIELDS = (
    "base_row_count",
    "visible_column_count",
    "parent_page_count",
    "raw_fetched_page_count",
    "raw_page_visible_link_count",
    "joint_bound_link_count",
    "eligible_unique_link_count",
    "parent_joint_bound_link_count",
    "parent_unique_joint_bound_link_count",
    "parent_eligible_unique_link_count",
    "coverage_probe_unique_coordinate_count",
    "coverage_probe_covered_row_count",
    "candidate_row_count",
    "candidate_covered_nonkey_cell_count_total",
    "candidate_evidence_deficit_count_total",
    "positive_evidence_deficit_candidate_count",
    "maximum_evidence_deficit_count",
    "maximum_evidence_deficit_tie_count",
    "stable_row_order_tiebreak_count",
    "logical_request_count",
    "positive_signed_credit_count",
)


payload_sha256 = parent.payload_sha256


def _coverage_probe(
    base_prediction: str,
    *,
    columns: Sequence[str],
    pages: Sequence[Mapping[str, Any]],
) -> tuple[tuple[str, ...], list[list[str]], str, dict[str, Any]]:
    required, rows = source._canonical_table(str(base_prediction), columns)
    probe_rows = [
        [str(row[0]), *("Unknown" for _ in required[1:])] for row in rows
    ]
    probe = source.table_parent._render_table(required, probe_rows)
    registry = coverage.build_candidate_registry(
        probe, columns=required, pages=pages
    )
    checked = coverage.validate_registry(
        registry, base_prediction=probe, columns=required, pages=pages
    )
    return required, rows, probe, checked


def _receipt(counts: Mapping[str, int]) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        **{name: int(counts.get(name, 0)) for name in _COUNT_FIELDS},
        "parent_public_same_origin_child_and_joint_row_binding_preserved": True,
        "parent_one_url_per_row_ambiguity_rejection_preserved": True,
        "coverage_probe_uses_same_rows_schema_and_parent_pages_only": True,
        "coverage_requires_unique_safe_source_bound_coordinate": True,
        "unchanged_source_bound_observation_counts_as_covered": True,
        "conflicting_or_ambiguous_coordinate_counts_as_uncovered": True,
        "different_rows_are_bounded_scheduling_alternatives_not_merged_evidence": True,
        "only_row_local_missing_evidence_coordinates_create_positive_priority": True,
        "maximum_deficit_then_stable_table_order_and_url": True,
        "selected_url_value_or_answer_not_synthesized": True,
        "zero_deficit_or_no_admissible_candidate_yields_no_request": True,
        "receipt_contains_question_url_anchor_row_identity_cell_value_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    true_flags = (
        "parent_public_same_origin_child_and_joint_row_binding_preserved",
        "parent_one_url_per_row_ambiguity_rejection_preserved",
        "coverage_probe_uses_same_rows_schema_and_parent_pages_only",
        "coverage_requires_unique_safe_source_bound_coordinate",
        "unchanged_source_bound_observation_counts_as_covered",
        "conflicting_or_ambiguous_coordinate_counts_as_uncovered",
        "different_rows_are_bounded_scheduling_alternatives_not_merged_evidence",
        "only_row_local_missing_evidence_coordinates_create_positive_priority",
        "maximum_deficit_then_stable_table_order_and_url",
        "selected_url_value_or_answer_not_synthesized",
        "zero_deficit_or_no_admissible_candidate_yields_no_request",
    )
    false_flags = (
        "receipt_contains_question_url_anchor_row_identity_cell_value_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "file_environment_process_network_model_search_fetch_or_evaluator_accessed",
        "benchmark_launch_or_evaluator_authorized",
    )
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        *_COUNT_FIELDS,
        *true_flags,
        *false_flags,
        "receipt_payload_sha256",
    }
    nonkey = max(0, int(copied.get("visible_column_count", 0)) - 1)
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
        or copied["candidate_row_count"]
        != copied["parent_eligible_unique_link_count"]
        or copied["joint_bound_link_count"]
        != copied["parent_joint_bound_link_count"]
        or copied["eligible_unique_link_count"]
        != copied["parent_eligible_unique_link_count"]
        or copied["coverage_probe_covered_row_count"]
        > copied["base_row_count"]
        or copied["coverage_probe_unique_coordinate_count"]
        > copied["base_row_count"] * nonkey
        or copied["candidate_covered_nonkey_cell_count_total"]
        + copied["candidate_evidence_deficit_count_total"]
        != copied["candidate_row_count"] * nonkey
        or copied["positive_evidence_deficit_candidate_count"]
        > copied["candidate_row_count"]
        or copied["maximum_evidence_deficit_count"] > nonkey
        or copied["maximum_evidence_deficit_tie_count"]
        > copied["positive_evidence_deficit_candidate_count"]
        or copied["stable_row_order_tiebreak_count"] not in {0, 1}
        or copied["stable_row_order_tiebreak_count"]
        != int(copied["maximum_evidence_deficit_tie_count"] > 1)
        or copied["logical_request_count"] not in {0, 1}
        or copied["logical_request_count"]
        != int(copied["positive_evidence_deficit_candidate_count"] > 0)
        or (copied["logical_request_count"] == 0)
        != (copied["maximum_evidence_deficit_count"] == 0)
        or copied["positive_signed_credit_count"] != 0
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.13 evidence coverage receipt drifted")
    return copied


def build_selection(
    base_prediction: str,
    *,
    columns: Sequence[str],
    fetch_batches: object,
    pages: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    required, rows, probe, registry = _coverage_probe(
        str(base_prediction), columns=columns, pages=pages
    )
    parent_selection = parent.build_selection(
        str(base_prediction), columns=required, fetch_batches=fetch_batches
    )
    checked_parent = parent.validate_selection(
        parent_selection,
        base_prediction=str(base_prediction),
        columns=required,
        fetch_batches=fetch_batches,
    )
    parent_receipt = parent.validate_receipt(
        checked_parent["content_free_receipt"]
    )
    row_map = {source._key(row[0]): index for index, row in enumerate(rows)}
    covered: Counter[int] = Counter()
    for candidate in registry["candidates"]:
        row_index = row_map.get(source._key(candidate["row_identity"]))
        if row_index is None:
            raise ValueError("V2.55.13 coverage row is absent")
        covered[row_index] += 1
    nonkey = len(required) - 1
    enriched: list[dict[str, Any]] = []
    for raw in checked_parent["private_candidates"]:
        row_index = row_map.get(source._key(raw["row_identity"]))
        if row_index is None:
            raise ValueError("V2.55.13 parent candidate row is absent")
        coverage_count = int(covered[row_index])
        if coverage_count > nonkey:
            raise ValueError("V2.55.13 coverage exceeds visible schema")
        enriched.append(
            {
                **copy.deepcopy(dict(raw)),
                "row_index": int(row_index),
                "covered_nonkey_cell_count": coverage_count,
                "evidence_deficit_count": nonkey - coverage_count,
            }
        )
    enriched.sort(
        key=lambda item: (
            -int(item["evidence_deficit_count"]),
            int(item["row_index"]),
            str(item["url"]),
        )
    )
    positive = [item for item in enriched if item["evidence_deficit_count"] > 0]
    maximum = int(positive[0]["evidence_deficit_count"]) if positive else 0
    top_ties = sum(
        int(item["evidence_deficit_count"] == maximum) for item in positive
    )
    selected = positive[0] if positive else None
    requests = (
        [
            {
                "url": str(selected["url"]),
                "query": REQUEST_QUERY,
                "title": str(selected["row_identity"]),
                "member_label": str(selected["row_identity"]),
            }
        ]
        if selected is not None
        else []
    )
    counts: Counter[str] = Counter(
        base_row_count=len(rows),
        visible_column_count=len(required),
        parent_page_count=len(pages),
        raw_fetched_page_count=parent_receipt["raw_fetched_page_count"],
        raw_page_visible_link_count=parent_receipt[
            "raw_page_visible_link_count"
        ],
        joint_bound_link_count=parent_receipt["joint_bound_link_count"],
        eligible_unique_link_count=parent_receipt[
            "eligible_unique_link_count"
        ],
        parent_joint_bound_link_count=parent_receipt["joint_bound_link_count"],
        parent_unique_joint_bound_link_count=parent_receipt[
            "unique_joint_bound_link_count"
        ],
        parent_eligible_unique_link_count=parent_receipt[
            "eligible_unique_link_count"
        ],
        coverage_probe_unique_coordinate_count=len(registry["candidates"]),
        coverage_probe_covered_row_count=len(covered),
        candidate_row_count=len(enriched),
        candidate_covered_nonkey_cell_count_total=sum(
            int(item["covered_nonkey_cell_count"]) for item in enriched
        ),
        candidate_evidence_deficit_count_total=sum(
            int(item["evidence_deficit_count"]) for item in enriched
        ),
        positive_evidence_deficit_candidate_count=len(positive),
        maximum_evidence_deficit_count=maximum,
        maximum_evidence_deficit_tie_count=top_ties,
        stable_row_order_tiebreak_count=int(top_ties > 1),
        logical_request_count=len(requests),
        positive_signed_credit_count=0,
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "base_prediction_sha256": hashlib.sha256(
            str(base_prediction).encode()
        ).hexdigest(),
        "columns": list(required),
        "input_page_vector_sha256": payload_sha256(list(pages)),
        "coverage_probe_prediction_sha256": hashlib.sha256(
            probe.encode()
        ).hexdigest(),
        "coverage_registry_payload_sha256": registry["artifact_payload_sha256"],
        "private_parent_selection": copy.deepcopy(checked_parent),
        "private_candidates": enriched,
        "requests": requests,
        "content_free_receipt": _receipt(counts),
    }
    value["artifact_payload_sha256"] = payload_sha256(value)
    return validate_selection(value)


def validate_selection(
    value: Mapping[str, Any],
    *,
    base_prediction: str | None = None,
    columns: Sequence[str] | None = None,
    fetch_batches: object | None = None,
    pages: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    raw_parent = copied.get("private_parent_selection")
    candidates = copied.get("private_candidates")
    requests = copied.get("requests")
    receipt = copied.get("content_free_receipt")
    if not isinstance(raw_parent, Mapping):
        raise ValueError("V2.55.13 parent selection absent")
    checked_parent = parent.validate_selection(raw_parent)
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "base_prediction_sha256",
        "columns",
        "input_page_vector_sha256",
        "coverage_probe_prediction_sha256",
        "coverage_registry_payload_sha256",
        "private_parent_selection",
        "private_candidates",
        "requests",
        "content_free_receipt",
        "artifact_payload_sha256",
    }
    parent_by_url = {
        item["url"]: item for item in checked_parent["private_candidates"]
    }
    hashes = (
        "base_prediction_sha256",
        "input_page_vector_sha256",
        "coverage_probe_prediction_sha256",
        "coverage_registry_payload_sha256",
    )
    nonkey = max(0, len(copied.get("columns") or []) - 1)
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            not isinstance(copied.get(name), str) or len(copied[name]) != 64
            for name in hashes
        )
        or not isinstance(copied.get("columns"), list)
        or len(copied["columns"]) < 2
        or any(not isinstance(item, str) or not item for item in copied["columns"])
        or not isinstance(candidates, list)
        or any(
            not isinstance(item, Mapping)
            or set(item) != _CANDIDATE_KEYS
            or canonicalize_url(str(item.get("url") or "")) != item.get("url")
            or canonicalize_url(str(item.get("attesting_page_url") or ""))
            != item.get("attesting_page_url")
            or item.get("url") not in parent_by_url
            or any(
                item.get(name) != parent_by_url[item["url"]].get(name)
                for name in parent._CANDIDATE_KEYS
            )
            or isinstance(item.get("row_index"), bool)
            or not isinstance(item.get("row_index"), int)
            or item["row_index"] < 0
            or item["row_index"] >= receipt["base_row_count"]
            or isinstance(item.get("covered_nonkey_cell_count"), bool)
            or not isinstance(item.get("covered_nonkey_cell_count"), int)
            or not 0 <= item["covered_nonkey_cell_count"] <= nonkey
            or isinstance(item.get("evidence_deficit_count"), bool)
            or not isinstance(item.get("evidence_deficit_count"), int)
            or item["evidence_deficit_count"]
            != nonkey - item["covered_nonkey_cell_count"]
            for item in candidates
        )
        or len({item["url"] for item in candidates}) != len(candidates)
        or len({item["row_index"] for item in candidates}) != len(candidates)
        or {item["url"] for item in candidates} != set(parent_by_url)
        or candidates
        != sorted(
            candidates,
            key=lambda item: (
                -int(item["evidence_deficit_count"]),
                int(item["row_index"]),
                str(item["url"]),
            ),
        )
        or not isinstance(requests, list)
        or len(requests) > MAXIMUM_DIRECT_REQUESTS
        or any(
            not isinstance(request, Mapping)
            or set(request) != _REQUEST_KEYS
            or request.get("query") != REQUEST_QUERY
            or canonicalize_url(str(request.get("url") or ""))
            != request.get("url")
            or request.get("title") != request.get("member_label")
            for request in requests
        )
        or (
            requests
            and (
                not candidates
                or candidates[0]["evidence_deficit_count"] <= 0
                or requests[0]["url"] != candidates[0]["url"]
                or requests[0]["title"] != candidates[0]["row_identity"]
            )
        )
        or (
            not requests
            and any(item["evidence_deficit_count"] > 0 for item in candidates)
        )
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["candidate_row_count"] != len(candidates)
        or receipt["logical_request_count"] != len(requests)
        or receipt["parent_eligible_unique_link_count"]
        != len(checked_parent["private_candidates"])
        or receipt["candidate_covered_nonkey_cell_count_total"]
        != sum(item["covered_nonkey_cell_count"] for item in candidates)
        or receipt["candidate_evidence_deficit_count_total"]
        != sum(item["evidence_deficit_count"] for item in candidates)
        or receipt["positive_evidence_deficit_candidate_count"]
        != sum(item["evidence_deficit_count"] > 0 for item in candidates)
        or receipt["maximum_evidence_deficit_count"]
        != max((item["evidence_deficit_count"] for item in candidates), default=0)
        or receipt["maximum_evidence_deficit_tie_count"]
        != sum(
            item["evidence_deficit_count"]
            == receipt["maximum_evidence_deficit_count"]
            and item["evidence_deficit_count"] > 0
            for item in candidates
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.13 evidence coverage selection drifted")
    if base_prediction is not None:
        if columns is None or fetch_batches is None or pages is None:
            raise ValueError("V2.55.13 selection replay inputs incomplete")
        replay = build_selection(
            str(base_prediction),
            columns=columns,
            fetch_batches=fetch_batches,
            pages=pages,
        )
        if replay != copied:
            raise ValueError("V2.55.13 selection replay drifted")
    return copied


def integration_contract() -> dict[str, Any]:
    return {
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "coverage_parser_policy_id": coverage.POLICY_ID,
        "source_admissibility_and_one_url_per_row_inherited": True,
        "scheduling_signal": "row_local_missing_unique_source_bound_coordinate_count",
        "coverage_probe": "same_rows_schema_all_nonkey_unknown_parent_pages_only",
        "priority": "maximum_deficit_then_stable_table_order_then_url",
        "maximum_direct_requests": MAXIMUM_DIRECT_REQUESTS,
        "runtime_input_keys": [
            "base_prediction",
            "columns",
            "same_forward_fetch_batches",
            "same_forward_parent_pages",
        ],
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }


__all__ = [
    "MAXIMUM_DIRECT_REQUESTS",
    "POLICY_ID",
    "RECEIPT_ROLE",
    "REQUEST_QUERY",
    "ROLE",
    "build_selection",
    "integration_contract",
    "payload_sha256",
    "validate_receipt",
    "validate_selection",
]
