"""Total identity passthrough for parent-valid revision-parser mismatches.

The parent score-first contract parses canonical Markdown rows without NFKC
normalization.  V2.48.59 normalizes the complete table before splitting rows.
Consequently a parent-valid cell containing a compatibility character such as
the fullwidth vertical line can become a new delimiter only inside the
optional revision kernel.  V2.48.86 handled over-512-row tables but still
allowed that parser mismatch to escape as a fatal task exception.

This pure append-only successor first validates the already-canonical parent
table with the parent parser semantics.  Tables understood by V2.48.86 retain
its exact candidate semantics.  Any parent-valid table outside that revision
parser envelope is identity-only: no proposal, evidence, support check, row
deletion, entropy decision, or model effect is permitted.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24886_revision_envelope_passthrough as frozen


POLICY_ID = "v24897_revision_parser_total_identity_v1"
ROLE = "v24897_revision_parser_total_identity_receipt"
MAXIMUM_ACTIVE_REVISION_ROWS = frozen.MAXIMUM_ACTIVE_REVISION_ROWS


def _parent_matrix(table: str) -> tuple[list[str], list[list[str]]]:
    """Parse exact parent-canonical bytes without compatibility folding."""

    groups: list[list[list[str]]] = []
    current: list[list[str]] = []
    for raw in str(table or "").replace("\r\n", "\n").splitlines():
        stripped = raw.strip()
        cells = (
            [cell.strip() for cell in stripped[1:-1].split("|")]
            if stripped.startswith("|") and stripped.endswith("|")
            else []
        )
        if cells:
            current.append(cells)
        elif current:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    if len(groups) != 1 or len(groups[0]) < 3:
        raise ValueError("V2.48.97 parent canonical grouping drifted")
    matrix = groups[0]
    columns = matrix[0]
    if not columns or any(len(row) != len(columns) for row in matrix):
        raise ValueError("V2.48.97 parent canonical width drifted")
    if any(
        re.fullmatch(r":?-{3,}:?", value.replace(" ", "")) is None
        for value in matrix[1]
    ):
        raise ValueError("V2.48.97 parent canonical separator drifted")
    rows = matrix[2:]
    if not rows or any(not cell for row in rows for cell in row):
        raise ValueError("V2.48.97 parent canonical data drifted")
    rendered = (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n"
        + "\n".join("| " + " | ".join(row) + " |" for row in rows)
        + "\n```"
    )
    if rendered != table:
        raise ValueError("V2.48.97 parent table is not byte canonical")
    return list(columns), [list(row) for row in rows]


def _reseal(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied["role"] = ROLE
    copied["policy_id"] = POLICY_ID
    copied.pop("receipt_payload_sha256", None)
    copied["receipt_payload_sha256"] = frozen.frozen.payload_sha256(copied)
    return validate_receipt(copied)


def revision_envelope_eligible(table: str) -> bool:
    _parent_matrix(table)
    try:
        return frozen.revision_envelope_eligible(table)
    except (TypeError, ValueError):
        return False


def apply_full_evidence_revision(
    *,
    baseline: str,
    proposed: str,
    pages: Sequence[frozen.frozen.EvidencePage | Mapping[str, Any]],
) -> dict[str, Any]:
    columns, rows = _parent_matrix(baseline)
    try:
        eligible = frozen.revision_envelope_eligible(baseline)
    except (TypeError, ValueError):
        eligible = False
    if eligible:
        value = frozen.apply_full_evidence_revision(
            baseline=baseline, proposed=proposed, pages=pages
        )
        return {
            "candidate_table": value["candidate_table"],
            "receipt": _reseal(value["receipt"]),
        }
    if str(proposed).strip() or len(pages) != 0:
        raise ValueError("V2.48.97 parser-incompatible table is identity-only")
    receipt = frozen._identity_receipt(rows=len(rows), columns=len(columns))
    return {"candidate_table": baseline, "receipt": _reseal(receipt)}


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or seal != frozen.frozen.payload_sha256(unsigned)
    ):
        raise ValueError("V2.48.97 receipt identity drifted")
    projected = copy.deepcopy(copied)
    projected["role"] = frozen.ROLE
    projected["policy_id"] = frozen.POLICY_ID
    projected.pop("receipt_payload_sha256", None)
    projected["receipt_payload_sha256"] = frozen.frozen.payload_sha256(projected)
    frozen.validate_receipt(projected)
    return copied


__all__ = [
    "MAXIMUM_ACTIVE_REVISION_ROWS",
    "POLICY_ID",
    "ROLE",
    "apply_full_evidence_revision",
    "revision_envelope_eligible",
    "validate_receipt",
]
