"""Deterministic local-support closure for Unknown-cell revisions.

V2.46.57 showed that retrieval produced usable independent pages, while model
revision objects usually named only one evidence ID.  This module changes only
that binding step: for a proposed selected Unknown-cell fill, it deterministically
adds every already-fetched targeted page whose local text contains the exact row
key and exact proposed value.  It never changes the proposal, fetch set, source
independence rule, or two-source support threshold.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24325_shared_prefix_revision_runtime as base
from . import v24655_unknown_cell_targeted_runtime as parent


POLICY_ID = "v24659_deterministic_support_closure_v1"
MINIMUM_INDEPENDENT_SUPPORT_SOURCES = parent.MINIMUM_INDEPENDENT_SUPPORT_SOURCES


def _supporting_evidence_ids(
    row_key: str,
    new_value: str,
    targeted_pages: Sequence[Mapping[str, str]],
) -> tuple[str, ...]:
    """Return stable page IDs with exact local row/value support."""

    output: list[str] = []
    seen_sources: set[str] = set()
    for page in targeted_pages:
        evidence_id = str(page.get("evidence_id", "")).strip()
        source = str(page.get("host", "")).strip()
        if not evidence_id or not source or source in seen_sources:
            continue
        if source not in parent._local_exact_support_sources(
            row_key, new_value, [page]
        ):
            continue
        output.append(evidence_id)
        seen_sources.add(source)
    return tuple(output)


def deterministic_support_closure(
    *,
    row_key: str,
    new_value: str,
    declared_evidence_ids: Sequence[str],
    targeted_pages: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Close model citations over fetched pages without weakening support."""

    page_ids = {
        str(page.get("evidence_id", "")).strip()
        for page in targeted_pages
        if str(page.get("evidence_id", "")).strip()
    }
    declared = tuple(
        value
        for value in (str(item).strip() for item in declared_evidence_ids)
        if value and value in page_ids
    )
    supporting = _supporting_evidence_ids(row_key, new_value, targeted_pages)
    closed = tuple(dict.fromkeys((*declared, *supporting)))
    return {
        "declared_evidence_ids": list(declared),
        "locally_supporting_evidence_ids": list(supporting),
        "closed_evidence_ids": list(closed),
        "added_evidence_id_count": len(set(closed) - set(declared)),
        "minimum_independent_support_sources_unchanged": (
            MINIMUM_INDEPENDENT_SUPPORT_SOURCES
            == parent.MINIMUM_INDEPENDENT_SUPPORT_SOURCES
            == 2
        ),
        "uses_only_already_fetched_targeted_pages": True,
        "proposal_value_changed": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "entropy_or_task_credit_used": False,
    }


def gate_unknown_candidate_with_support_closure(
    *,
    baseline: str,
    proposed: str,
    evidence_declarations: object,
    targeted_pages: Sequence[Mapping[str, str]],
    targets: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, Any]], dict[str, int]]:
    """Run the frozen parent gate after deterministic evidence closure."""

    columns, baseline_rows = base._table_matrix(baseline)
    candidate_columns, candidate_rows = base._table_matrix(proposed)
    if (
        columns != candidate_columns
        or len(baseline_rows) != len(candidate_rows)
        or any(len(row) != len(columns) for row in [*baseline_rows, *candidate_rows])
    ):
        return parent._gate_unknown_candidate(
            baseline=baseline,
            proposed=proposed,
            evidence_declarations=evidence_declarations,
            targeted_pages=targeted_pages,
            targets=targets,
        )

    declared = base._evidence_map(evidence_declarations, columns)
    closure_rows: list[dict[str, Any]] = []
    closure_added = closure_eligible = 0
    allowed = {
        (int(target["row_ordinal"]), int(target["column_index"]))
        for target in targets
    }
    for row_ordinal, (source, candidate) in enumerate(
        zip(baseline_rows, candidate_rows, strict=True)
    ):
        row_key = str(source[0]).strip()
        normalized_row = base._support_normalize(row_key)
        for column_index in range(1, len(columns)):
            old = source[column_index]
            new = candidate[column_index]
            if base._support_normalize(old) == base._support_normalize(new):
                continue
            if (
                (row_ordinal, column_index) not in allowed
                or not base._is_unknown(old)
                or base._is_unknown(new)
            ):
                continue
            closure = deterministic_support_closure(
                row_key=row_key,
                new_value=new,
                declared_evidence_ids=declared.get(
                    (normalized_row, column_index), ()
                ),
                targeted_pages=targeted_pages,
            )
            closure_added += int(closure["added_evidence_id_count"])
            closure_eligible += int(
                len(closure["locally_supporting_evidence_ids"])
                >= MINIMUM_INDEPENDENT_SUPPORT_SOURCES
            )
            closure_rows.append(
                {
                    "row_key": row_key,
                    "column": columns[column_index],
                    "evidence_ids": closure["closed_evidence_ids"],
                }
            )

    candidate, admissions, counts = parent._gate_unknown_candidate(
        baseline=baseline,
        proposed=proposed,
        evidence_declarations=closure_rows,
        targeted_pages=targeted_pages,
        targets=targets,
    )
    output = copy.deepcopy(counts)
    output.update(
        {
            "support_closure_added_evidence_id_count": closure_added,
            "support_closure_eligible_change_count": closure_eligible,
            "support_threshold_relaxed": 0,
            "proposal_value_changed_by_closure": 0,
        }
    )
    return candidate, admissions, output


__all__ = [
    "MINIMUM_INDEPENDENT_SUPPORT_SOURCES",
    "POLICY_ID",
    "deterministic_support_closure",
    "gate_unknown_candidate_with_support_closure",
]
