"""Programmatic support-catalog gate for table revisions.

The model can propose a table and choose a precomputed support-set ID, but the
deterministic gate owns target/value/evidence binding and entropy credit.  It
never accepts arbitrary model-declared evidence membership.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

from .v24333_programmatic_support_catalog import (
    resolve_support_selection,
    validate_catalog_identity,
    validate_resolution_receipt,
)


POLICY_ID = "v24334_programmatic_support_catalog_revision_gate_v1"
RESULT_ROLE = "v24334_support_catalog_revision_gate_result"
UNKNOWN = frozenset(
    {"", "-", "—", "?", "n/a", "na", "none", "null", "unknown", "未知", "不详", "无法确认"}
)
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "candidate_table",
        "candidate_identity_handoff",
        "baseline_rows_never_deleted",
        "proposed_cell_changes",
        "admitted_cell_changes",
        "credited_conditional_entropy_reduction_nats",
        "cell_resolution_receipts",
        "model_declared_arbitrary_evidence_membership_trusted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "file_environment_network_model_search_fetch_or_process_accessed",
        "benchmark_launch_or_evaluator_authorized",
        "result_sha256",
    }
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _normalize(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())


def _support_normalize(value: object) -> str:
    return "".join(
        character
        for character in _normalize(value)
        if character.isalnum() or "\u4e00" <= character <= "\u9fff"
    )


def _split_row(line: str) -> list[str]:
    text = line.strip()
    if not text.startswith("|") or not text.endswith("|"):
        raise ValueError("V2.43.34 table row boundary drifted")
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in text[1:-1]:
        if escaped:
            current.append(character)
            escaped = False
        elif character == "\\":
            current.append(character)
            escaped = True
        elif character == "|":
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
    cells.append("".join(current).strip())
    return cells


def _matrix(table: str) -> tuple[list[str], list[list[str]]]:
    rows = [
        _split_row(line)
        for line in table.replace("\r\n", "\n").splitlines()
        if line.strip().startswith("|") and line.strip().endswith("|")
    ]
    if len(rows) < 3 or len(rows[0]) < 1:
        raise ValueError("V2.43.34 canonical table is absent")
    width = len(rows[0])
    if any(len(row) != width for row in rows):
        raise ValueError("V2.43.34 table width drifted")
    return rows[0], rows[2:]


def _render(columns: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )


def _declarations(raw: object, columns: Sequence[str]) -> dict[tuple[str, int], dict[str, Any]]:
    if not isinstance(raw, list) or len(raw) > 500:
        return {}
    column_map = {_normalize(value): index for index, value in enumerate(columns)}
    output: dict[tuple[str, int], dict[str, Any]] = {}
    for item in raw:
        if not isinstance(item, Mapping) or set(item) != {
            "row_key",
            "column",
            "support_set_id",
            "evidence_ids",
        }:
            continue
        row = _support_normalize(item.get("row_key"))
        column = column_map.get(_normalize(item.get("column")))
        support_id = item.get("support_set_id")
        evidence_ids = item.get("evidence_ids")
        if (
            not row
            or column is None
            or not isinstance(support_id, str)
            or re.fullmatch(r"[0-9a-f]{64}", support_id) is None
            or not isinstance(evidence_ids, list)
            or not 1 <= len(evidence_ids) <= 16
            or any(
                not isinstance(value, str) or re.fullmatch(r"R\d{4}", value) is None
                for value in evidence_ids
            )
        ):
            continue
        output[(row, column)] = {
            "support_set_id": support_id,
            "evidence_ids": list(evidence_ids),
        }
    return output


def apply_catalog_revision(
    *,
    baseline: str,
    proposed: str,
    cell_support: object,
    catalog: Mapping[str, Any],
) -> dict[str, Any]:
    validate_catalog_identity(catalog)
    columns, baseline_rows = _matrix(baseline)
    proposed_columns, proposed_rows = _matrix(proposed)
    if [_normalize(value) for value in columns] != [
        _normalize(value) for value in proposed_columns
    ]:
        raise ValueError("V2.43.34 proposed columns drifted")
    baseline_by_key: dict[str, list[str]] = {}
    for row in baseline_rows:
        key = _support_normalize(row[0])
        if not key or key in baseline_by_key:
            raise ValueError("V2.43.34 baseline row key drifted")
        baseline_by_key[key] = list(row)
    proposed_by_key: dict[str, list[str]] = {}
    proposed_order: list[str] = []
    for row in proposed_rows:
        key = _support_normalize(row[0])
        if not key or key in proposed_by_key:
            raise ValueError("V2.43.34 proposed row key drifted")
        proposed_by_key[key] = list(row)
        proposed_order.append(key)
    declarations = _declarations(cell_support, columns)
    output_rows = [list(row) for row in baseline_rows]
    output_index = {_support_normalize(row[0]): index for index, row in enumerate(output_rows)}
    receipts: list[dict[str, Any]] = []
    proposed_changes = 0
    admitted_changes = 0
    credit = 0.0

    def evaluate(*, row_key: str, column_index: int, new_value: str) -> bool:
        nonlocal proposed_changes, admitted_changes, credit
        proposed_changes += 1
        declaration = declarations.get((_support_normalize(row_key), column_index))
        support_set_id = declaration["support_set_id"] if declaration else ""
        evidence_ids = declaration["evidence_ids"] if declaration else []
        receipt = resolve_support_selection(
            catalog,
            row_key=row_key,
            column=columns[column_index],
            new_value=new_value,
            support_set_id=support_set_id,
            declared_evidence_ids=evidence_ids,
        )
        validate_resolution_receipt(receipt)
        receipts.append(receipt)
        if receipt["admitted"]:
            admitted_changes += 1
            credit += float(receipt["conditional_entropy_reduction_nats"])
            return True
        return False

    for key, baseline_row in baseline_by_key.items():
        proposed_row = proposed_by_key.get(key)
        if proposed_row is None:
            continue
        target = output_rows[output_index[key]]
        for column_index in range(1, len(columns)):
            if _support_normalize(proposed_row[column_index]) == _support_normalize(
                baseline_row[column_index]
            ):
                continue
            if evaluate(
                row_key=baseline_row[0],
                column_index=column_index,
                new_value=proposed_row[column_index],
            ):
                target[column_index] = proposed_row[column_index]

    for key in proposed_order:
        if key in baseline_by_key:
            continue
        row = proposed_by_key[key]
        start = len(receipts)
        before_admitted = admitted_changes
        before_credit = credit
        row_ok = True
        for column_index in range(1, len(columns)):
            if not evaluate(
                row_key=row[0],
                column_index=column_index,
                new_value=row[column_index],
            ):
                row_ok = False
        if row_ok:
            output_rows.append(row)
        else:
            admitted_changes = before_admitted
            credit = before_credit
            for receipt in receipts[start:]:
                if receipt["admitted"]:
                    receipt["admitted"] = False
                    receipt["disposition"] = "quarantine_target_binding"
                    receipt["conditional_entropy_reduction_nats"] = 0.0
                    unsigned = dict(receipt)
                    unsigned.pop("receipt_sha256", None)
                    receipt["receipt_sha256"] = payload_sha256(unsigned)

    candidate = _render(columns, output_rows)
    identity = candidate == baseline
    value = {
        "artifact_version": 1,
        "role": RESULT_ROLE,
        "policy_id": POLICY_ID,
        "candidate_table": candidate,
        "candidate_identity_handoff": identity,
        "baseline_rows_never_deleted": True,
        "proposed_cell_changes": proposed_changes,
        "admitted_cell_changes": admitted_changes,
        "credited_conditional_entropy_reduction_nats": round(credit, 12),
        "cell_resolution_receipts": receipts,
        "model_declared_arbitrary_evidence_membership_trusted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "file_environment_network_model_search_fetch_or_process_accessed": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["result_sha256"] = payload_sha256(value)
    validate_revision_result(value)
    return value


def validate_revision_result(value: Mapping[str, Any]) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("result_sha256", None)
    receipts = value.get("cell_resolution_receipts")
    if not isinstance(receipts, list):
        raise ValueError("V2.43.34 resolution receipt vector is absent")
    for receipt in receipts:
        validate_resolution_receipt(receipt)
    admitted = sum(receipt["admitted"] for receipt in receipts)
    credit = round(
        sum(
            float(receipt["conditional_entropy_reduction_nats"])
            for receipt in receipts
            if receipt["admitted"]
        ),
        12,
    )
    if (
        set(value) != RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != RESULT_ROLE
        or value.get("policy_id") != POLICY_ID
        or not isinstance(value.get("candidate_table"), str)
        or not isinstance(value.get("candidate_identity_handoff"), bool)
        or value.get("baseline_rows_never_deleted") is not True
        or value.get("admitted_cell_changes") != admitted
        or value.get("credited_conditional_entropy_reduction_nats") != credit
        or value.get("model_declared_arbitrary_evidence_membership_trusted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or value.get("file_environment_network_model_search_fetch_or_process_accessed") is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.43.34 revision result drifted")
    return dict(value)


__all__ = [
    "POLICY_ID",
    "RESULT_ROLE",
    "apply_catalog_revision",
    "payload_sha256",
    "validate_revision_result",
]
