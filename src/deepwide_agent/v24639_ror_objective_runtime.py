"""Append-only ROR harder-task adapter for the V2.46.37 paired runtime.

The adapter changes no effect budget.  It derives four entity-specific queries
from the visible question and deterministically projects both model tables onto
the visible entity vector.  Missing rows are explicit Unknown rows; facts are
never invented by the projector.  Gold, ROR IDs, country codes, evaluator
metadata, and scores are unavailable to this module.
"""

from __future__ import annotations

import copy
import hashlib
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24637_objective_alignment_runtime as base
from .v24257_score_first_runtime import ScoreFirstLimits, _normalize_column, validate_visible_task


POLICY_ID = "v24639_ror_visible_entity_completion_adapter_v1"
ROLE = "v24639_ror_objective_alignment_task_result"
RECEIPT_ROLE = "v24639_ror_content_free_completion_receipt"
EXPECTED_COLUMNS = ("Organization", "ROR ID", "Country code")


def extract_visible_entities(question: str) -> list[str]:
    match = re.fullmatch(
        r"Use public web sources to return one Markdown table about these organizations:\n"
        r"<ENTITIES>\n(.*)\n</ENTITIES>\n"
        r"The column names are: Organization, ROR ID, Country code\. "
        r"Return one table only\.",
        str(question).strip(),
        flags=re.DOTALL,
    )
    if match is None:
        raise ValueError("V2.46.39 visible ROR task syntax drifted")
    lines = match.group(1).splitlines()
    values = []
    for index, line in enumerate(lines, 1):
        prefix = f"{index}. "
        if not line.startswith(prefix):
            raise ValueError("V2.46.39 visible ROR entity numbering drifted")
        values.append(line[len(prefix) :].strip())
    if len(values) != 4 or len(set(values)) != 4 or any(not item for item in values):
        raise ValueError("V2.46.39 visible ROR entity vector drifted")
    return values


def visible_query_vector(question: str, limit: int) -> list[str]:
    if limit != 4:
        raise ValueError("V2.46.39 requires the unchanged four-query cap")
    return [f'"{entity}" ROR ID country code' for entity in extract_visible_entities(question)]


def _matrix(table: str) -> tuple[list[str], list[list[str]]]:
    canonical, _ = base.extract_valid_markdown_table(table, EXPECTED_COLUMNS)
    if canonical is None:
        return list(EXPECTED_COLUMNS), []
    lines = [line.strip() for line in canonical.splitlines() if line.strip().startswith("|")]
    return (
        [cell.strip() for cell in lines[0][1:-1].split("|")],
        [[cell.strip() for cell in line[1:-1].split("|")] for line in lines[2:]],
    )


def project_visible_rows(table: str, entities: Sequence[str]) -> tuple[str, dict[str, int | bool]]:
    columns, rows = _matrix(table)
    by_key: dict[str, list[str]] = {}
    duplicate = 0
    for row in rows:
        key = re.sub(r"[^a-z0-9]+", "", row[0].casefold()) if row else ""
        if not key:
            continue
        if key in by_key:
            duplicate += 1
            continue
        by_key[key] = row
    output = []
    recovered = 0
    for entity in entities:
        key = re.sub(r"[^a-z0-9]+", "", entity.casefold())
        row = by_key.get(key)
        if row is None:
            output.append([entity, "Unknown", "Unknown"])
        else:
            recovered += 1
            output.append([entity, row[1] or "Unknown", row[2] or "Unknown"])
    rendered = (
        "```markdown\n| " + " | ".join(columns) + " |\n| "
        + " | ".join("---" for _ in columns) + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in output)
        + "\n```"
    )
    return rendered, {
        "input_row_count": len(rows), "output_row_count": len(output),
        "matched_visible_rows": recovered, "inserted_unknown_rows": len(output) - recovered,
        "duplicate_identity_rows_ignored": duplicate, "visible_order_exact": True,
    }


def run_v24639_task(
    task: Mapping[str, Any], *, model: Any, search: Any, limits: ScoreFirstLimits,
    monotonic: Any,
) -> dict[str, Any]:
    visible = validate_visible_task(task)
    entities = extract_visible_entities(visible["question"])
    original_extract = base.extract_visible_entities
    original_queries = base._complete_query_vector
    base.extract_visible_entities = extract_visible_entities
    base._complete_query_vector = lambda question, planned, limit: visible_query_vector(question, limit)
    try:
        parent = base.run_v24637_task(
            visible, model=model, search=search, limits=limits, monotonic=monotonic
        )
    finally:
        base.extract_visible_entities = original_extract
        base._complete_query_vector = original_queries
    projected = {}
    projections = {}
    for arm in base.ARMS:
        projected[arm], projections[arm] = project_visible_rows(parent["predictions"][arm], entities)
    value = copy.deepcopy(parent)
    value["role"] = ROLE
    value["policy_id"] = POLICY_ID
    value["predictions"] = projected
    value["prediction_sha256"] = {
        arm: hashlib.sha256(projected[arm].encode()).hexdigest() for arm in base.ARMS
    }
    value["ror_completion_receipt"] = {
        "artifact_version": 1, "role": RECEIPT_ROLE, "policy_id": POLICY_ID,
        "entity_specific_visible_query_vector": True,
        "queries_equal_visible_entity_count": True,
        "model_search_fetch_or_token_budget_changed": False,
        "arm_projection": projections,
        "fact_value_created_by_projector": False,
        "missing_rows_project_to_explicit_unknown": True,
        "question_query_prediction_entity_or_credential_emitted": False,
        "mapping_gold_ror_id_country_code_evaluator_score_or_reward_read": False,
    }
    value.pop("result_sha256", None)
    value["result_sha256"] = base.payload_sha256(value)
    return validate_result(value)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied); seal = unsigned.pop("result_sha256", None)
    receipt = copied.get("ror_completion_receipt", {})
    if (
        copied.get("role") != ROLE or copied.get("policy_id") != POLICY_ID
        or seal != base.payload_sha256(unsigned)
        or receipt.get("role") != RECEIPT_ROLE
        or receipt.get("entity_specific_visible_query_vector") is not True
        or receipt.get("model_search_fetch_or_token_budget_changed") is not False
        or receipt.get("fact_value_created_by_projector") is not False
        or receipt.get("missing_rows_project_to_explicit_unknown") is not True
        or receipt.get("mapping_gold_ror_id_country_code_evaluator_score_or_reward_read") is not False
    ):
        raise ValueError("V2.46.39 ROR task result drifted")
    entities = extract_visible_entities(
        "Use public web sources to return one Markdown table about these organizations:\n"
        "<ENTITIES>\n1. a\n2. b\n3. c\n4. d\n</ENTITIES>\n"
        "The column names are: Organization, ROR ID, Country code. Return one table only."
    )
    if len(entities) != 4:
        raise ValueError("V2.46.39 parser self-check drifted")
    for arm in base.ARMS:
        columns, rows = _matrix(copied["predictions"][arm])
        if tuple(columns) != EXPECTED_COLUMNS or len(rows) != 4:
            raise ValueError("V2.46.39 projected table drifted")
        if copied["prediction_sha256"][arm] != hashlib.sha256(copied["predictions"][arm].encode()).hexdigest():
            raise ValueError("V2.46.39 prediction hash drifted")
    return copied


__all__ = ["EXPECTED_COLUMNS", "extract_visible_entities", "project_visible_rows", "run_v24639_task", "validate_result", "visible_query_vector"]
