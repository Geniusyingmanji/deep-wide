"""Visible-only short authority/identity query construction.

V2.49.87 executed all four logical queries, yet 38 query-local hosted-search
results failed.  The deterministic completion had merely appended source words
to one long planner query.  This pure component instead extracts only explicit
tagged identities, an explicit ``official ... page/source/database`` authority
phrase, and robust visible columns.  It composes four short complementary
queries without reading page content, benchmark labels, answers, evaluator
feedback, scores, rewards, historical results, or credentials.

The private return value contains query text for the same forward pass.  Its
public receipt contains counts and booleans only.  It performs no I/O and does
not change any model, search, fetch, token, context, byte, or wall budget.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from .v24257_score_first_runtime import _normalize_text
from .v24263_global_model_limiter import payload_sha256
from .v24286_visible_schema_runtime import extract_robust_visible_columns


POLICY_ID = "v24988_visible_short_authority_identity_queries_v1"
RECEIPT_ROLE = "v24988_content_free_short_query_receipt"
QUERY_CAP = 4
QUERY_CHARACTER_CAP = 320
PROVIDER_QUERY_CHARACTER_CAP = 900
IDENTITY_CAP = 8
IDENTITY_CHARACTER_CAP = 160
AUTHORITY_CHARACTER_CAP = 180
_TAGGED = re.compile(
    r"<(?P<tag>[A-Z][A-Z0-9_]{1,31})>\s*(?P<value>[^<>\r\n]{1,200}?)\s*</(?P=tag)>",
    re.IGNORECASE,
)
_AUTHORITY = (
    re.compile(
        r"\bofficial\s+(?P<value>.{2,180}?)\s+(?:public\s+)?"
        r"(?:page|website|site|database|directory|registry|record|source)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:from|using|use)\s+(?:the\s+)?(?P<value>.{2,180}?)\s+"
        r"(?:official\s+)?(?:page|website|site|database|directory|registry)\b",
        re.IGNORECASE,
    ),
)
_GENERIC_AUTHORITY = frozenset(
    {
        "official",
        "official public",
        "public",
        "the official",
        "web search and the official",
    }
)


def _clean(value: object, maximum: int) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = " ".join(text.replace("\x00", " ").split()).strip(" ,;:。；：")
    return text[:maximum].strip()


def _unique(values: Sequence[object], *, maximum: int, cap: int) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = _clean(raw, maximum)
        key = value.casefold()
        if value and key not in seen:
            output.append(value)
            seen.add(key)
        if len(output) >= cap:
            break
    return output


def _provider_queries(values: Sequence[object]) -> list[str]:
    """Mirror the parent runtime's provider-query normalization exactly."""

    output: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = _normalize_text(raw)[:PROVIDER_QUERY_CHARACTER_CAP]
        key = value.casefold()
        if value and key not in seen:
            output.append(value)
            seen.add(key)
        if len(output) >= QUERY_CAP:
            break
    return output


def _identities(question: str) -> list[str]:
    return _unique(
        [match.group("value") for match in _TAGGED.finditer(question)],
        maximum=IDENTITY_CHARACTER_CAP,
        cap=IDENTITY_CAP,
    )


def _authority(question: str) -> str:
    candidates: list[str] = []
    for pattern in _AUTHORITY:
        for match in pattern.finditer(question):
            value = _clean(match.group("value"), AUTHORITY_CHARACTER_CAP)
            value = re.sub(
                r"^(?:use|using|from|web\s+search\s+and|the)\s+",
                "",
                value,
                flags=re.IGNORECASE,
            ).strip()
            if value.casefold() not in _GENERIC_AUTHORITY:
                candidates.append(value)
    if not candidates:
        return ""
    return min(candidates, key=lambda value: (len(value), value.casefold()))


def _quoted(value: str) -> str:
    clean = value.replace('"', " ").strip()
    return f'"{clean}"' if " " in clean or clean.startswith(".") else clean


def _candidate_queries(
    *, identities: Sequence[str], authority: str, columns: Sequence[str]
) -> list[str]:
    identity = " ".join(_quoted(value) for value in identities[:3])
    source = _quoted(authority) if authority else "official source"
    targets = " ".join(_quoted(value) for value in columns[1:4])
    schema = " ".join(_quoted(value) for value in columns[:4])
    values = [
        f"{identity} {source}",
        f"{identity} {targets}",
        f"{source} {schema}",
        f"{source} official list {identity}",
    ]
    return [_clean(value, QUERY_CHARACTER_CAP) for value in values]


def _receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "tagged_identity_count": int(value["tagged_identity_count"]),
        "explicit_authority_phrase_count": int(
            value["explicit_authority_phrase_count"]
        ),
        "robust_visible_schema_column_count": int(
            value["robust_visible_schema_column_count"]
        ),
        "provider_unique_query_count": int(value["provider_unique_query_count"]),
        "provider_query_vector_valid": bool(value["provider_query_vector_valid"]),
        "output_query_count": int(value["output_query_count"]),
        "maximum_output_query_characters": int(
            value["maximum_output_query_characters"]
        ),
        "strategy_applied": bool(value["strategy_applied"]),
        "all_output_queries_unique": bool(value["all_output_queries_unique"]),
        "tagged_identity_authority_and_visible_schema_only": True,
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
        "robust_visible_schema_column_count",
        "provider_unique_query_count",
        "output_query_count",
        "maximum_output_query_characters",
    )
    true_flags = (
        "tagged_identity_authority_and_visible_schema_only",
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
    applied = copied.get("strategy_applied")
    unique = copied.get("all_output_queries_unique")
    provider_valid = copied.get("provider_query_vector_valid")
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
        or copied["tagged_identity_count"] > IDENTITY_CAP
        or copied["explicit_authority_phrase_count"] > 1
        or copied["robust_visible_schema_column_count"] > 20
        or copied["provider_unique_query_count"] > QUERY_CAP
        or copied["output_query_count"] > QUERY_CAP
        or copied["maximum_output_query_characters"]
        > (
            QUERY_CHARACTER_CAP
            if copied.get("strategy_applied") is True
            else PROVIDER_QUERY_CHARACTER_CAP
        )
        or not isinstance(applied, bool)
        or not isinstance(unique, bool)
        or not isinstance(provider_valid, bool)
        or applied
        is not (
            provider_valid
            and copied["provider_unique_query_count"] > 0
            and copied["tagged_identity_count"] > 0
            and copied["explicit_authority_phrase_count"] == 1
            and copied["robust_visible_schema_column_count"] >= 2
            and copied["output_query_count"] == QUERY_CAP
            and unique
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.88 short-query receipt drifted")
    return copied


def build_short_queries(
    question: str,
    planner_queries: Sequence[object],
    *,
    query_cap: int = QUERY_CAP,
    provider_query_vector_valid: bool = True,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.49.88 visible question is absent")
    if (
        query_cap != QUERY_CAP
        or isinstance(planner_queries, (str, bytes))
        or not isinstance(provider_query_vector_valid, bool)
    ):
        raise ValueError("V2.49.88 query boundary drifted")
    identities = _identities(question)
    authority = _authority(question)
    columns = extract_robust_visible_columns(question)
    planner = _provider_queries(planner_queries)
    generated = _unique(
        _candidate_queries(
            identities=identities,
            authority=authority,
            columns=columns,
        )
        if identities and authority and len(columns) >= 2
        else [],
        maximum=QUERY_CHARACTER_CAP,
        cap=QUERY_CAP,
    )
    applied = (
        provider_query_vector_valid
        and bool(planner)
        and len(generated) == QUERY_CAP
    )
    queries = generated if applied else planner
    unique = len({value.casefold() for value in queries}) == len(queries)
    receipt = _receipt(
        {
            "tagged_identity_count": len(identities),
            "explicit_authority_phrase_count": int(bool(authority)),
            "robust_visible_schema_column_count": len(columns),
            "provider_unique_query_count": len(planner),
            "provider_query_vector_valid": provider_query_vector_valid,
            "output_query_count": len(queries),
            "maximum_output_query_characters": max(
                (len(value) for value in queries), default=0
            ),
            "strategy_applied": applied,
            "all_output_queries_unique": unique,
        }
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "policy_id": POLICY_ID,
        "queries": queries,
        "content_free_receipt": receipt,
        "question_query_or_facets_persisted_or_emitted": False,
    }
    value["artifact_payload_sha256"] = hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()
    return validate_result(
        value,
        question=question,
        planner_queries=planner_queries,
        provider_query_vector_valid=provider_query_vector_valid,
    )


def validate_result(
    value: Mapping[str, Any],
    *,
    question: str,
    planner_queries: Sequence[object],
    provider_query_vector_valid: bool = True,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("artifact_payload_sha256", None)
    queries = copied.get("queries")
    receipt = copied.get("content_free_receipt")
    if (
        copied.get("artifact_version") != 1
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
                unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
    ):
        raise ValueError("V2.49.88 short-query artifact drifted")
    if copied != _compute_replay(
        question, planner_queries, provider_query_vector_valid
    ):
        raise ValueError("V2.49.88 short-query artifact is not reproducible")
    return copied


def _compute_replay(
    question: str,
    planner_queries: Sequence[object],
    provider_query_vector_valid: bool,
) -> dict[str, Any]:
    # Avoid recursive validation while rebuilding the deterministic artifact.
    identities = _identities(question)
    authority = _authority(question)
    columns = extract_robust_visible_columns(question)
    planner = _provider_queries(planner_queries)
    generated = _unique(
        _candidate_queries(
            identities=identities, authority=authority, columns=columns
        )
        if identities and authority and len(columns) >= 2
        else [],
        maximum=QUERY_CHARACTER_CAP,
        cap=QUERY_CAP,
    )
    applied = (
        provider_query_vector_valid
        and bool(planner)
        and len(generated) == QUERY_CAP
    )
    queries = generated if applied else planner
    unique = len({value.casefold() for value in queries}) == len(queries)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "policy_id": POLICY_ID,
        "queries": queries,
        "content_free_receipt": _receipt(
            {
                "tagged_identity_count": len(identities),
                "explicit_authority_phrase_count": int(bool(authority)),
                "robust_visible_schema_column_count": len(columns),
                "provider_unique_query_count": len(planner),
                "provider_query_vector_valid": provider_query_vector_valid,
                "output_query_count": len(queries),
                "maximum_output_query_characters": max(
                    (len(item) for item in queries), default=0
                ),
                "strategy_applied": applied,
                "all_output_queries_unique": unique,
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


__all__ = [
    "POLICY_ID",
    "PROVIDER_QUERY_CHARACTER_CAP",
    "QUERY_CAP",
    "QUERY_CHARACTER_CAP",
    "RECEIPT_ROLE",
    "build_short_queries",
    "validate_receipt",
    "validate_result",
]
