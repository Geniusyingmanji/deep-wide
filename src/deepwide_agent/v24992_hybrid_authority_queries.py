"""Visible-only provider-anchor-preserving hybrid query construction.

V2.49.91 showed that replacing every provider query with a short query greatly
increased action-trace pages while destroying query-local result binding and
target-record retention.  This pure successor preserves the first normalized
provider query byte-for-byte as the semantic anchor.  It fills only the other
three slots from the visible tagged identity, the *first* explicit authority
phrase in text order, and the robust visible schema.

The component fails closed to the provider query vector unless all facets are
present and the four hybrid queries are nonempty and unique.  It performs no
I/O, assigns no entropy/information-gain credit, and grants no benchmark or
evaluator authority.
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


POLICY_ID = "v24992_provider_anchor_first_authority_hybrid_queries_v1"
RECEIPT_ROLE = "v24992_content_free_hybrid_query_receipt"
QUERY_CAP = 4
GENERATED_QUERY_CHARACTER_CAP = 320
PROVIDER_QUERY_CHARACTER_CAP = 900
IDENTITY_CAP = 8
IDENTITY_CHARACTER_CAP = 160
AUTHORITY_CHARACTER_CAP = 180
AUTHORITY_COUNT_CAP = 8
_TAGGED = re.compile(
    r"<(?P<tag>[A-Z][A-Z0-9_]{1,31})>\s*(?P<value>[^<>\r\n]{1,200}?)\s*</(?P=tag)>",
    re.IGNORECASE,
)
_AUTHORITY = (
    re.compile(
        r"\bofficial\s+(?P<value>.{2,180}?)\s+(?:public\s+)?"
        r"(?P<kind>page|website|site|database|directory|registry|record|source)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:from|using|use)\s+(?:the\s+)?(?P<value>.{2,180}?)\s+"
        r"(?:official\s+)?(?P<kind>page|website|site|database|directory|registry)\b",
        re.IGNORECASE,
    ),
)
_AUTHORITY_NAME_KINDS = frozenset({"database", "directory", "registry"})
_LEADING_AUTHORITY_NOISE = re.compile(
    r"^(?:use|using|from|web\s+search\s+and|the|official)\s+",
    re.IGNORECASE,
)
_GENERIC_AUTHORITY = frozenset(
    {"official", "official public", "public", "the official", "web search"}
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


def _strip_authority_noise(value: object) -> str:
    text = _clean(value, AUTHORITY_CHARACTER_CAP)
    for _index in range(8):
        updated = _LEADING_AUTHORITY_NOISE.sub("", text, count=1).strip()
        if updated == text:
            break
        text = updated
    return _clean(text, AUTHORITY_CHARACTER_CAP)


def _authorities(question: str) -> list[str]:
    candidates: list[tuple[int, int, str]] = []
    for priority, pattern in enumerate(_AUTHORITY):
        for match in pattern.finditer(question):
            value = _strip_authority_noise(match.group("value"))
            raw_kind = str(match.group("kind") or "")
            if value and raw_kind.casefold() in _AUTHORITY_NAME_KINDS:
                value = _clean(f"{value} {raw_kind}", AUTHORITY_CHARACTER_CAP)
            if value and value.casefold() not in _GENERIC_AUTHORITY:
                candidates.append((match.start(), priority, value))
    candidates.sort(key=lambda item: (item[0], item[1]))
    output: list[str] = []
    seen: set[str] = set()
    for _offset, _priority, value in candidates:
        key = value.casefold()
        if key not in seen:
            output.append(value)
            seen.add(key)
        if len(output) >= AUTHORITY_COUNT_CAP:
            break
    return output


def _quoted(value: str) -> str:
    clean = value.replace('"', " ").strip()
    return f'"{clean}"' if " " in clean or clean.startswith(".") else clean


def _hybrid_queries(
    *, anchor: str, identities: Sequence[str], authority: str, columns: Sequence[str]
) -> list[str]:
    identity = " ".join(_quoted(value) for value in identities[:3])
    source = _quoted(authority)
    targets = " ".join(_quoted(value) for value in columns[1:4])
    schema = " ".join(_quoted(value) for value in columns[:4])
    generated = (
        f"{identity} {source}",
        f"{identity} {targets}",
        f"{source} {schema}",
    )
    return [
        anchor,
        *[_clean(value, GENERATED_QUERY_CHARACTER_CAP) for value in generated],
    ]


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
        "provider_query_vector_valid": bool(value["provider_query_vector_valid"]),
        "output_query_count": int(value["output_query_count"]),
        "maximum_output_query_characters": int(
            value["maximum_output_query_characters"]
        ),
        "strategy_applied": bool(value["strategy_applied"]),
        "provider_anchor_preserved_in_first_slot": bool(
            value["provider_anchor_preserved_in_first_slot"]
        ),
        "all_output_queries_unique": bool(value["all_output_queries_unique"]),
        "first_explicit_authority_phrase_selected": True,
        "only_non_anchor_slots_replaced": True,
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
        "selected_authority_ordinal",
        "robust_visible_schema_column_count",
        "provider_unique_query_count",
        "output_query_count",
        "maximum_output_query_characters",
    )
    true_flags = (
        "first_explicit_authority_phrase_selected",
        "only_non_anchor_slots_replaced",
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
    bool_fields = (
        "provider_query_vector_valid",
        "strategy_applied",
        "provider_anchor_preserved_in_first_slot",
        "all_output_queries_unique",
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
        or copied["output_query_count"] > QUERY_CAP
        or copied["maximum_output_query_characters"] > PROVIDER_QUERY_CHARACTER_CAP
        or copied["provider_anchor_preserved_in_first_slot"]
        is not (
            copied["provider_unique_query_count"] > 0
            and copied["output_query_count"] > 0
        )
        or copied["strategy_applied"]
        is not (
            copied["provider_query_vector_valid"]
            and copied["tagged_identity_count"] > 0
            and copied["explicit_authority_phrase_count"] > 0
            and copied["selected_authority_ordinal"] == 1
            and copied["robust_visible_schema_column_count"] >= 2
            and copied["provider_unique_query_count"] > 0
            and copied["output_query_count"] == QUERY_CAP
            and copied["provider_anchor_preserved_in_first_slot"]
            and copied["all_output_queries_unique"]
        )
        or any(copied.get(name) is not True for name in true_flags)
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.92 hybrid-query receipt drifted")
    return copied


def _compute(
    question: str,
    provider_queries: Sequence[object],
    provider_query_vector_valid: bool,
) -> dict[str, Any]:
    planner = _provider_queries(provider_queries)
    identities = _identities(question)
    authorities = _authorities(question)
    columns = extract_robust_visible_columns(question)
    generated = (
        _hybrid_queries(
            anchor=planner[0],
            identities=identities,
            authority=authorities[0],
            columns=columns,
        )
        if planner and identities and authorities and len(columns) >= 2
        else []
    )
    unique_generated = len({value.casefold() for value in generated}) == len(generated)
    applied = (
        provider_query_vector_valid
        and len(generated) == QUERY_CAP
        and unique_generated
        and all(generated)
    )
    queries = generated if applied else planner
    unique = len({value.casefold() for value in queries}) == len(queries)
    anchor_preserved = bool(planner and queries and queries[0] == planner[0])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "policy_id": POLICY_ID,
        "queries": queries,
        "content_free_receipt": _receipt(
            {
                "tagged_identity_count": len(identities),
                "explicit_authority_phrase_count": len(authorities),
                "selected_authority_ordinal": int(bool(authorities)),
                "robust_visible_schema_column_count": len(columns),
                "provider_unique_query_count": len(planner),
                "provider_query_vector_valid": provider_query_vector_valid,
                "output_query_count": len(queries),
                "maximum_output_query_characters": max(
                    (len(item) for item in queries), default=0
                ),
                "strategy_applied": applied,
                "provider_anchor_preserved_in_first_slot": anchor_preserved,
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


def build_hybrid_queries(
    question: str,
    provider_queries: Sequence[object],
    *,
    query_cap: int = QUERY_CAP,
    provider_query_vector_valid: bool = True,
) -> dict[str, Any]:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("V2.49.92 visible question is absent")
    if (
        query_cap != QUERY_CAP
        or isinstance(provider_queries, (str, bytes))
        or not isinstance(provider_query_vector_valid, bool)
    ):
        raise ValueError("V2.49.92 query boundary drifted")
    value = _compute(question, provider_queries, provider_query_vector_valid)
    return validate_result(
        value,
        question=question,
        provider_queries=provider_queries,
        provider_query_vector_valid=provider_query_vector_valid,
    )


def validate_result(
    value: Mapping[str, Any],
    *,
    question: str,
    provider_queries: Sequence[object],
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
                unsigned, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode()
        ).hexdigest()
        or copied
        != _compute(question, provider_queries, provider_query_vector_valid)
    ):
        raise ValueError("V2.49.92 hybrid-query artifact drifted")
    return copied


__all__ = [
    "POLICY_ID",
    "QUERY_CAP",
    "RECEIPT_ROLE",
    "build_hybrid_queries",
    "validate_receipt",
    "validate_result",
]
