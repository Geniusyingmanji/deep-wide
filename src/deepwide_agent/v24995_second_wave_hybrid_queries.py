"""Visible-only hybrid queries confined to the second retrieval wave.

V2.49.94 preserved only the first completed query and changed the second query
inside the six-fetch first wave.  Hosted search then exposed substantially more
action sources but much less query-local citation binding.  This pure successor
keeps the first two completed queries byte-for-byte and replaces only slots
three and four with ``identity + requested fields`` and
``authority + visible schema`` queries.

The component fails closed to the completed query vector unless the provider
query vector was valid and nonempty, all visible facets are present, the input
contains exactly four unique completed queries, and the two generated queries
remain unique.  It performs no I/O, assigns no entropy/information-gain credit,
and grants no benchmark or evaluator authority.
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .v24257_score_first_runtime import _normalize_text
from .v24263_global_model_limiter import payload_sha256
from .v24286_visible_schema_runtime import extract_robust_visible_columns
from .v24992_hybrid_authority_queries import (
    AUTHORITY_COUNT_CAP,
    GENERATED_QUERY_CHARACTER_CAP,
    IDENTITY_CAP,
    PROVIDER_QUERY_CHARACTER_CAP,
    _authorities,
    _clean,
    _identities,
    _quoted,
)


POLICY_ID = "v24995_shared_first_wave_second_wave_hybrid_queries_v1"
RECEIPT_ROLE = "v24995_content_free_second_wave_hybrid_query_receipt"
QUERY_CAP = 4
SHARED_PREFIX_QUERY_COUNT = 2


def _completed(values: Sequence[object]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = _normalize_text(raw)[:PROVIDER_QUERY_CHARACTER_CAP]
        folded = value.casefold()
        if value and folded not in seen:
            output.append(value)
            seen.add(folded)
        if len(output) >= QUERY_CAP:
            break
    return output


def _generated(question: str) -> tuple[list[str], int, int, int]:
    identities = _identities(question)
    authorities = _authorities(question)
    columns = extract_robust_visible_columns(question)
    if not identities or not authorities or len(columns) < 2:
        return [], len(identities), len(authorities), len(columns)
    identity = " ".join(_quoted(value) for value in identities[:3])
    targets = " ".join(_quoted(value) for value in columns[1:4])
    authority = _quoted(authorities[0])
    schema = " ".join(_quoted(value) for value in columns[:4])
    values = [
        _clean(f"{identity} {targets}", GENERATED_QUERY_CHARACTER_CAP),
        _clean(f"{authority} {schema}", GENERATED_QUERY_CHARACTER_CAP),
    ]
    return values, len(identities), len(authorities), len(columns)


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "tagged_identity_count": int(value["tagged_identity_count"]),
        "explicit_authority_phrase_count": int(
            value["explicit_authority_phrase_count"]
        ),
        "selected_authority_ordinal": int(value["selected_authority_ordinal"]),
        "robust_visible_schema_column_count": int(
            value["robust_visible_schema_column_count"]
        ),
        "provider_unique_query_count": int(value["provider_unique_query_count"]),
        "completed_query_count": int(value["completed_query_count"]),
        "output_query_count": int(value["output_query_count"]),
        "maximum_output_query_characters": int(
            value["maximum_output_query_characters"]
        ),
        "shared_prefix_query_count": SHARED_PREFIX_QUERY_COUNT,
        "replaced_second_wave_query_count": int(
            value["replaced_second_wave_query_count"]
        ),
        "provider_query_vector_valid": bool(value["provider_query_vector_valid"]),
        "strategy_applied": bool(value["strategy_applied"]),
        "first_two_completed_queries_preserved": bool(
            value["first_two_completed_queries_preserved"]
        ),
        "all_output_queries_unique": bool(value["all_output_queries_unique"]),
        "only_second_wave_query_slots_replaced": True,
        "identity_fields_and_authority_schema_only": True,
        "first_explicit_authority_phrase_selected_when_applied": True,
        "hard_query_cap_preserved": True,
        "additional_model_search_fetch_token_context_byte_or_wall_budget": False,
        "contains_question_identity_authority_column_query_url_page_prediction_answer_hash_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    output["receipt_payload_sha256"] = payload_sha256(output)
    return validate_receipt(output)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = (
        "tagged_identity_count",
        "explicit_authority_phrase_count",
        "selected_authority_ordinal",
        "robust_visible_schema_column_count",
        "provider_unique_query_count",
        "completed_query_count",
        "output_query_count",
        "maximum_output_query_characters",
        "shared_prefix_query_count",
        "replaced_second_wave_query_count",
    )
    bool_fields = (
        "provider_query_vector_valid",
        "strategy_applied",
        "first_two_completed_queries_preserved",
        "all_output_queries_unique",
    )
    true_flags = (
        "only_second_wave_query_slots_replaced",
        "identity_fields_and_authority_schema_only",
        "first_explicit_authority_phrase_selected_when_applied",
        "hard_query_cap_preserved",
    )
    false_flags = (
        "additional_model_search_fetch_token_context_byte_or_wall_budget",
        "contains_question_identity_authority_column_query_url_page_prediction_answer_hash_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
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
        "receipt_payload_sha256",
    }
    applied = copied.get("strategy_applied")
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
        or any(not isinstance(copied.get(name), bool) for name in bool_fields)
        or copied["tagged_identity_count"] > IDENTITY_CAP
        or copied["explicit_authority_phrase_count"] > AUTHORITY_COUNT_CAP
        or copied["selected_authority_ordinal"]
        not in ({1} if copied["explicit_authority_phrase_count"] else {0})
        or copied["robust_visible_schema_column_count"] > 20
        or copied["provider_unique_query_count"] > QUERY_CAP
        or copied["completed_query_count"] > QUERY_CAP
        or copied["provider_unique_query_count"] > copied["completed_query_count"]
        or copied["output_query_count"] > QUERY_CAP
        or copied["maximum_output_query_characters"]
        > PROVIDER_QUERY_CHARACTER_CAP
        or copied["shared_prefix_query_count"] != SHARED_PREFIX_QUERY_COUNT
        or copied["replaced_second_wave_query_count"] not in {0, 2}
        or copied["first_two_completed_queries_preserved"]
        is not (
            copied["completed_query_count"] >= SHARED_PREFIX_QUERY_COUNT
            and copied["output_query_count"] >= SHARED_PREFIX_QUERY_COUNT
        )
        or applied
        is not (
            copied["provider_query_vector_valid"]
            and copied["provider_unique_query_count"] > 0
            and copied["completed_query_count"] == QUERY_CAP
            and copied["output_query_count"] == QUERY_CAP
            and copied["tagged_identity_count"] > 0
            and copied["explicit_authority_phrase_count"] > 0
            and copied["selected_authority_ordinal"] == 1
            and copied["robust_visible_schema_column_count"] >= 2
            and copied["first_two_completed_queries_preserved"]
            and copied["all_output_queries_unique"]
            and copied["replaced_second_wave_query_count"] == 2
        )
        or (not applied and copied["replaced_second_wave_query_count"] != 0)
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.95 second-wave hybrid receipt drifted")
    return copied


def _compute(
    question: str,
    completed_queries: Sequence[object],
    provider_unique_query_count: int,
    provider_query_vector_valid: bool,
) -> dict[str, Any]:
    completed = _completed(completed_queries)
    generated, identity_count, authority_count, column_count = _generated(question)
    candidate = [*completed[:SHARED_PREFIX_QUERY_COUNT], *generated]
    unique_candidate = (
        len(candidate) == QUERY_CAP
        and len({value.casefold() for value in candidate}) == QUERY_CAP
    )
    applied = (
        provider_query_vector_valid
        and provider_unique_query_count > 0
        and len(completed) == QUERY_CAP
        and len(generated) == 2
        and all(generated)
        and unique_candidate
    )
    queries = candidate if applied else completed
    unique_output = len({value.casefold() for value in queries}) == len(queries)
    prefix_preserved = (
        len(completed) >= SHARED_PREFIX_QUERY_COUNT
        and len(queries) >= SHARED_PREFIX_QUERY_COUNT
        and queries[:SHARED_PREFIX_QUERY_COUNT]
        == completed[:SHARED_PREFIX_QUERY_COUNT]
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "policy_id": POLICY_ID,
        "queries": queries,
        "content_free_receipt": _receipt(
            {
                "tagged_identity_count": identity_count,
                "explicit_authority_phrase_count": authority_count,
                "selected_authority_ordinal": int(bool(authority_count)),
                "robust_visible_schema_column_count": column_count,
                "provider_unique_query_count": provider_unique_query_count,
                "completed_query_count": len(completed),
                "output_query_count": len(queries),
                "maximum_output_query_characters": max(
                    (len(item) for item in queries), default=0
                ),
                "provider_query_vector_valid": provider_query_vector_valid,
                "strategy_applied": applied,
                "first_two_completed_queries_preserved": prefix_preserved,
                "all_output_queries_unique": unique_output,
                "replaced_second_wave_query_count": 2 if applied else 0,
            }
        ),
        "question_query_or_facets_persisted_or_emitted": False,
    }
    value["artifact_payload_sha256"] = hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return value


def build_second_wave_hybrid_queries(
    question: str,
    completed_queries: Sequence[object],
    *,
    provider_unique_query_count: int,
    provider_query_vector_valid: bool = True,
    query_cap: int = QUERY_CAP,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.49.95 visible question is absent")
    if (
        query_cap != QUERY_CAP
        or isinstance(completed_queries, (str, bytes))
        or isinstance(provider_unique_query_count, bool)
        or not isinstance(provider_unique_query_count, int)
        or not 0 <= provider_unique_query_count <= QUERY_CAP
        or not isinstance(provider_query_vector_valid, bool)
    ):
        raise ValueError("V2.49.95 query boundary drifted")
    value = _compute(
        question,
        completed_queries,
        provider_unique_query_count,
        provider_query_vector_valid,
    )
    return validate_result(
        value,
        question=question,
        completed_queries=completed_queries,
        provider_unique_query_count=provider_unique_query_count,
        provider_query_vector_valid=provider_query_vector_valid,
    )


def validate_result(
    value: Mapping[str, Any],
    *,
    question: str,
    completed_queries: Sequence[object],
    provider_unique_query_count: int,
    provider_query_vector_valid: bool = True,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    queries = copied.get("queries")
    receipt = copied.get("content_free_receipt")
    expected = {
        "artifact_version",
        "policy_id",
        "queries",
        "content_free_receipt",
        "question_query_or_facets_persisted_or_emitted",
        "artifact_payload_sha256",
    }
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(queries, list)
        or any(not isinstance(item, str) or not item for item in queries)
        or len(queries) > QUERY_CAP
        or not isinstance(receipt, Mapping)
        or validate_receipt(receipt) != dict(receipt)
        or receipt["output_query_count"] != len(queries)
        or copied.get("question_query_or_facets_persisted_or_emitted") is not False
        or seal
        != hashlib.sha256(
            json.dumps(
                unsigned,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        or copied
        != _compute(
            question,
            completed_queries,
            provider_unique_query_count,
            provider_query_vector_valid,
        )
    ):
        raise ValueError("V2.49.95 second-wave hybrid artifact drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "QUERY_CAP",
    "RECEIPT_ROLE",
    "SHARED_PREFIX_QUERY_COUNT",
    "build_second_wave_hybrid_queries",
    "validate_receipt",
    "validate_result",
]
