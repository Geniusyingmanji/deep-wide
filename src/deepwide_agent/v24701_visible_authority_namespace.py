"""Visible-only authority namespace and target-address signatures.

This module recognizes only a small preregistered allowlist of public source
names that appear literally in a user question.  It never infers a benchmark
category, never reads files or evaluator metadata, and never selects an answer.
The returned signature is suitable for aggregate reachability audits and for
later fail-closed adapter routing from ``{opaque_id, question}`` only.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .v24675_expanded_visible_schema import extract_expanded_visible_columns


POLICY_ID = "v24701_visible_authority_namespace_v1"
NAMESPACE_PATTERNS = (
    ("world_bank", re.compile(r"World Bank|api\.worldbank", re.IGNORECASE)),
    (
        "who",
        re.compile(r"World Health Organi[sz]ation|\bWHO\b", re.IGNORECASE),
    ),
    ("github", re.compile(r"GitHub|github\.com", re.IGNORECASE)),
    ("wikipedia", re.compile(r"Wikipedia|wikipedia\.org", re.IGNORECASE)),
    ("iso", re.compile(r"\bISO(?:[- ]\d+)?\b", re.IGNORECASE)),
)
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
ADDRESS_COLUMN = re.compile(
    r"\b(?:ID|identifier|code|ISO|DOI|ORCID|ISBN|LEI|ticker|year|date)\b|"
    r"标识符|代码|年份|日期",
    re.IGNORECASE,
)
NUMERIC_COLUMN = re.compile(
    r"\b(?:population|GDP|revenue|rate|percent|percentage|number|count|"
    r"amount|price|value|score|capacity|area|length|height|weight|"
    r"temperature|cases|deaths|mortality|incidence|prevalence)\b|"
    r"人口|比例|率|数量|金额|价格|面积|长度|高度|重量|温度|病例|死亡",
    re.IGNORECASE,
)


def visible_authority_signature(question: str) -> dict[str, Any]:
    visible = str(question or "")
    columns = extract_expanded_visible_columns(visible)
    joined = " | ".join(columns)
    namespaces = [name for name, pattern in NAMESPACE_PATTERNS if pattern.search(visible)]
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
        or copied.get("runtime_input_keys") != ["opaque_id", "question"]
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
    ):
        raise ValueError("V2.47.01 visible authority signature drifted")
    return copied


__all__ = [
    "NAMESPACE_PATTERNS",
    "POLICY_ID",
    "validate_signature",
    "visible_authority_signature",
]
