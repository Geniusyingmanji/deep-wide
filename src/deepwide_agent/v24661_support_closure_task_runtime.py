"""Strict, runnable successor to the inert V2.46.59 support closure.

The successor preserves every model-declared evidence ID, including unresolved
or non-supporting IDs, so the frozen parent gate continues to fail closed.  It
only appends already-fetched pages with exact local row/value support.  The
parent and closure gates are both evaluated on the same proposal and pages,
providing content-free within-pass intervention accounting without another
model, search, fetch, evaluator, or entropy-directed effect.
"""

from __future__ import annotations

import copy
import types
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v24325_shared_prefix_revision_runtime as base
from . import v24637_objective_alignment_runtime as paired
from . import v24655_unknown_cell_targeted_runtime as parent
from . import v24659_support_closure_runtime as precursor
from .v24257_score_first_runtime import ScoreFirstLimits


POLICY_ID = "v24661_strict_deterministic_support_closure_v1"
ROLE = "v24661_strict_support_closure_task_result"
RECEIPT_ROLE = "v24661_strict_support_closure_content_free_receipt"
ARMS = parent.ARMS
MINIMUM_INDEPENDENT_SUPPORT_SOURCES = 2
CLOSURE_FIELDS = frozenset(
    {
        "support_closure_invocation_count",
        "support_closure_added_evidence_id_count",
        "support_closure_eligible_change_count",
        "counterfactual_parent_admitted_cell_change_count",
        "strict_closure_admitted_cell_change_count",
        "incremental_strict_closure_admitted_cell_change_count",
        "minimum_independent_support_sources",
        "unresolved_declared_evidence_ids_preserved",
        "non_supporting_declared_evidence_ids_preserved",
        "uses_only_already_fetched_targeted_pages",
        "proposal_value_changed_by_closure",
        "support_threshold_relaxed",
        "new_model_search_fetch_or_evaluator_effect",
        "entropy_or_task_credit_used_by_closure",
        "v24659_design_only_precursor_superseded",
    }
)


def strict_deterministic_support_closure(
    *,
    row_key: str,
    new_value: str,
    declared_evidence_ids: Sequence[str],
    targeted_pages: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Append exact-local support while preserving all declared IDs."""

    declared = tuple(
        dict.fromkeys(
            value
            for value in (str(item).strip() for item in declared_evidence_ids)
            if value
        )
    )
    supporting = precursor._supporting_evidence_ids(
        row_key, new_value, targeted_pages
    )
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
        "unresolved_declared_evidence_ids_preserved": True,
        "non_supporting_declared_evidence_ids_preserved": True,
        "uses_only_already_fetched_targeted_pages": True,
        "proposal_value_changed": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "entropy_or_task_credit_used": False,
    }


def gate_unknown_candidate_with_strict_support_closure(
    *,
    baseline: str,
    proposed: str,
    evidence_declarations: object,
    targeted_pages: Sequence[Mapping[str, str]],
    targets: Sequence[Mapping[str, Any]],
) -> tuple[str, list[dict[str, Any]], dict[str, int]]:
    """Apply the parent gate after strict evidence closure."""

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
    added = eligible = 0
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
            closure = strict_deterministic_support_closure(
                row_key=row_key,
                new_value=new,
                declared_evidence_ids=declared.get(
                    (normalized_row, column_index), ()
                ),
                targeted_pages=targeted_pages,
            )
            added += int(closure["added_evidence_id_count"])
            eligible += int(
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
    output = dict(counts)
    output.update(
        {
            "support_closure_added_evidence_id_count": added,
            "support_closure_eligible_change_count": eligible,
        }
    )
    return candidate, admissions, output


def _parent_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    copied.pop("receipt_sha256", None)
    for field in CLOSURE_FIELDS:
        copied.pop(field, None)
    copied["role"] = parent.RECEIPT_ROLE
    copied["policy_id"] = parent.POLICY_ID
    copied["receipt_sha256"] = paired.payload_sha256(copied)
    return parent.validate_receipt(copied)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    counts = (
        "support_closure_invocation_count",
        "support_closure_added_evidence_id_count",
        "support_closure_eligible_change_count",
        "counterfactual_parent_admitted_cell_change_count",
        "strict_closure_admitted_cell_change_count",
        "incremental_strict_closure_admitted_cell_change_count",
        "minimum_independent_support_sources",
    )
    if (
        copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied.get(name, -1) < 0
            for name in counts
        )
        or copied["support_closure_invocation_count"] not in (0, 1)
        or copied["minimum_independent_support_sources"] != 2
        or copied["strict_closure_admitted_cell_change_count"]
        != copied.get("admitted_cell_change_count")
        or copied["counterfactual_parent_admitted_cell_change_count"]
        > copied["strict_closure_admitted_cell_change_count"]
        or copied["incremental_strict_closure_admitted_cell_change_count"]
        != copied["strict_closure_admitted_cell_change_count"]
        - copied["counterfactual_parent_admitted_cell_change_count"]
        or copied["strict_closure_admitted_cell_change_count"]
        > copied["support_closure_eligible_change_count"]
        or copied.get("unresolved_declared_evidence_ids_preserved") is not True
        or copied.get("non_supporting_declared_evidence_ids_preserved") is not True
        or copied.get("uses_only_already_fetched_targeted_pages") is not True
        or copied.get("proposal_value_changed_by_closure") is not False
        or copied.get("support_threshold_relaxed") is not False
        or copied.get("new_model_search_fetch_or_evaluator_effect") is not False
        or copied.get("entropy_or_task_credit_used_by_closure") is not False
        or copied.get("v24659_design_only_precursor_superseded") is not True
        or seal != paired.payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.61 strict closure receipt drifted")
    parent_receipt = _parent_receipt(copied)
    if copied["support_closure_invocation_count"] == 0 and any(
        copied[name]
        for name in (
            "support_closure_added_evidence_id_count",
            "support_closure_eligible_change_count",
            "counterfactual_parent_admitted_cell_change_count",
            "strict_closure_admitted_cell_change_count",
            "incremental_strict_closure_admitted_cell_change_count",
        )
    ):
        raise ValueError("V2.46.61 unused closure has nonzero effects")
    if parent_receipt["admitted_cell_change_count"] != copied[
        "strict_closure_admitted_cell_change_count"
    ]:
        raise ValueError("V2.46.61 parent receipt projection drifted")
    return copied


def _isolated_parent_run(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
    gate: Callable[..., tuple[str, list[dict[str, Any]], dict[str, int]]],
) -> dict[str, Any]:
    namespace = dict(vars(parent))
    namespace["_gate_unknown_candidate"] = gate
    isolated = types.FunctionType(
        parent.run_v24655_task.__code__,
        namespace,
        name="run_v24661_isolated_parent_task",
        argdefs=parent.run_v24655_task.__defaults__,
        closure=parent.run_v24655_task.__closure__,
    )
    isolated.__kwdefaults__ = dict(parent.run_v24655_task.__kwdefaults__ or {})
    return isolated(
        task, model=model, search=search, limits=limits, monotonic=monotonic
    )


def run_v24661_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    monotonic: Callable[[], float],
) -> dict[str, Any]:
    interventions: list[dict[str, int]] = []

    def gate(**kwargs: Any) -> tuple[str, list[dict[str, Any]], dict[str, int]]:
        _parent_candidate, _parent_admissions, parent_counts = (
            parent._gate_unknown_candidate(**kwargs)
        )
        candidate, admissions, closure_counts = (
            gate_unknown_candidate_with_strict_support_closure(**kwargs)
        )
        parent_admitted = int(parent_counts["admitted_cell_change_count"])
        closure_admitted = int(closure_counts["admitted_cell_change_count"])
        if closure_admitted < parent_admitted:
            raise RuntimeError("V2.46.61 strict closure is not monotone")
        interventions.append(
            {
                "added": int(
                    closure_counts["support_closure_added_evidence_id_count"]
                ),
                "eligible": int(
                    closure_counts["support_closure_eligible_change_count"]
                ),
                "parent_admitted": parent_admitted,
                "closure_admitted": closure_admitted,
            }
        )
        return candidate, admissions, closure_counts

    result = parent.validate_result(
        _isolated_parent_run(
            task,
            model=model,
            search=search,
            limits=limits,
            monotonic=monotonic,
            gate=gate,
        )
    )
    copied = copy.deepcopy(result)
    copied["role"] = ROLE
    copied["policy_id"] = POLICY_ID
    receipt = copied["receipt"]
    receipt.pop("receipt_sha256", None)
    receipt["role"] = RECEIPT_ROLE
    receipt["policy_id"] = POLICY_ID
    parent_admitted = sum(item["parent_admitted"] for item in interventions)
    closure_admitted = sum(item["closure_admitted"] for item in interventions)
    receipt.update(
        {
            "support_closure_invocation_count": len(interventions),
            "support_closure_added_evidence_id_count": sum(
                item["added"] for item in interventions
            ),
            "support_closure_eligible_change_count": sum(
                item["eligible"] for item in interventions
            ),
            "counterfactual_parent_admitted_cell_change_count": parent_admitted,
            "strict_closure_admitted_cell_change_count": closure_admitted,
            "incremental_strict_closure_admitted_cell_change_count": (
                closure_admitted - parent_admitted
            ),
            "minimum_independent_support_sources": 2,
            "unresolved_declared_evidence_ids_preserved": True,
            "non_supporting_declared_evidence_ids_preserved": True,
            "uses_only_already_fetched_targeted_pages": True,
            "proposal_value_changed_by_closure": False,
            "support_threshold_relaxed": False,
            "new_model_search_fetch_or_evaluator_effect": False,
            "entropy_or_task_credit_used_by_closure": False,
            "v24659_design_only_precursor_superseded": True,
        }
    )
    receipt["receipt_sha256"] = paired.payload_sha256(receipt)
    copied.pop("result_sha256", None)
    copied["result_sha256"] = paired.payload_sha256(copied)
    return validate_result(copied)


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    if (
        copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or seal != paired.payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.61 strict closure result drifted")
    receipt = validate_receipt(copied.get("receipt", {}))
    parent_copy = copy.deepcopy(copied)
    parent_copy["role"] = parent.ROLE
    parent_copy["policy_id"] = parent.POLICY_ID
    parent_copy["receipt"] = _parent_receipt(receipt)
    parent_copy.pop("result_sha256", None)
    parent_copy["result_sha256"] = paired.payload_sha256(parent_copy)
    parent.validate_result(parent_copy)
    return copied


__all__ = [
    "ARMS",
    "MINIMUM_INDEPENDENT_SUPPORT_SOURCES",
    "POLICY_ID",
    "ROLE",
    "gate_unknown_candidate_with_strict_support_closure",
    "run_v24661_task",
    "strict_deterministic_support_closure",
    "validate_receipt",
    "validate_result",
]
