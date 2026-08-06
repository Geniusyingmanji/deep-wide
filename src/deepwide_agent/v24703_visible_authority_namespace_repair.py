"""Case-safe repair of the visible authority namespace signature.

V2.47.01 compiled the ``WHO`` acronym with IGNORECASE and therefore treated
ordinary interrogative ``who`` as World Health Organization.  This append-only
repair requires either the exact uppercase acronym or the full organization
name.  Other frozen namespace patterns and addressability rules are preserved.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .v24675_expanded_visible_schema import extract_expanded_visible_columns
from .v24701_visible_authority_namespace import (
    ADDRESS_COLUMN,
    NUMERIC_COLUMN,
    YEAR,
)


POLICY_ID = "v24703_case_safe_visible_authority_namespace_v1"
NAMESPACE_PATTERNS = (
    ("world_bank", re.compile(r"World Bank|api\.worldbank", re.IGNORECASE)),
    (
        "who",
        re.compile(r"World Health Organi[sz]ation", re.IGNORECASE),
    ),
    ("github", re.compile(r"GitHub|github\.com", re.IGNORECASE)),
    ("wikipedia", re.compile(r"Wikipedia|wikipedia\.org", re.IGNORECASE)),
    ("iso", re.compile(r"\bISO(?:[- ]\d+)?\b")),
)
WHO_ACRONYM = re.compile(r"\bWHO\b")


def visible_authority_signature(question: str) -> dict[str, Any]:
    visible = str(question or "")
    columns = extract_expanded_visible_columns(visible)
    joined = " | ".join(columns)
    namespaces = [name for name, pattern in NAMESPACE_PATTERNS if pattern.search(visible)]
    if WHO_ACRONYM.search(visible) and "who" not in namespaces:
        namespaces.append("who")
    namespaces = list(dict.fromkeys(namespaces))
    unique = len(namespaces) == 1
    addressable = bool(columns) and (
        bool(YEAR.search(visible)) or bool(ADDRESS_COLUMN.search(joined))
    )
    return {
        "namespace_count": len(namespaces),
        "unique_namespace": namespaces[0] if unique else None,
        "visible_schema_width": len(columns),
        "visible_year_present": bool(YEAR.search(visible)),
        "address_column_present": bool(ADDRESS_COLUMN.search(joined)),
        "numeric_column_present": bool(NUMERIC_COLUMN.search(joined)),
        "adapter_route_eligible": unique and addressable,
        "case_safe_who_matching": True,
        "runtime_input_keys": ["opaque_id", "question"],
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }


def validate_signature(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    count = copied.get("namespace_count")
    namespace = copied.get("unique_namespace")
    width = copied.get("visible_schema_width")
    if (
        set(copied)
        != {
            "namespace_count",
            "unique_namespace",
            "visible_schema_width",
            "visible_year_present",
            "address_column_present",
            "numeric_column_present",
            "adapter_route_eligible",
            "case_safe_who_matching",
            "runtime_input_keys",
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        }
        or isinstance(count, bool)
        or not isinstance(count, int)
        or not 0 <= count <= len(NAMESPACE_PATTERNS)
        or namespace is not None
        and namespace not in {name for name, _pattern in NAMESPACE_PATTERNS}
        or (count == 1) is not (namespace is not None)
        or isinstance(width, bool)
        or not isinstance(width, int)
        or not 0 <= width <= 20
        or any(
            not isinstance(copied.get(name), bool)
            for name in (
                "visible_year_present",
                "address_column_present",
                "numeric_column_present",
                "adapter_route_eligible",
            )
        )
        or copied.get("adapter_route_eligible")
        is not bool(
            count == 1
            and width > 0
            and (
                copied.get("visible_year_present") is True
                or copied.get("address_column_present") is True
            )
        )
        or copied.get("case_safe_who_matching") is not True
        or copied.get("runtime_input_keys") != ["opaque_id", "question"]
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
    ):
        raise ValueError("V2.47.03 visible authority signature drifted")
    return copied


__all__ = [
    "NAMESPACE_PATTERNS",
    "POLICY_ID",
    "WHO_ACRONYM",
    "validate_signature",
    "visible_authority_signature",
]
