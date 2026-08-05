"""Total public projection for proof-carrying conversion observability.

Successful rows can be created only from the opaque V2.45.19 capability.
Failure rows are conservative zeros and do not claim private effects were
zero.  Aggregation likewise accepts opaque success capabilities (plus exact
failure-as-zero rows), so an expanded public dictionary cannot be re-ingested
as proof.

The projection exposes only fixed-vocabulary counts.  It does not expose task
content, entity names, values, queries, URLs, pages, sources, predictions,
private-content hashes, benchmark labels, evaluator state, or scores.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24504_proof_carrying_record_bound_reserve as base_proof
from . import v24513_terminal_record_bound_projection as parent
from . import v24518_conversion_observability as observability
from .v24519_proof_carrying_conversion_observability import (
    ValidatedProofCarryingConversionObservability,
)


POLICY_ID = "v24520_total_conversion_observability_projection_v1"
COUNT_FIELDS = (
    "conversion_targeted_usable_page_count",
    "conversion_reserve_usable_page_count",
    "conversion_usable_page_count",
    "conversion_selected_target_count",
    "conversion_page_target_pair_count",
    *(
        f"conversion_{name}"
        for name in observability.SIGNAL_COUNT_FIELDS
    ),
)
ROW_KEYS = frozenset(
    {
        *parent.ROW_KEYS,
        *COUNT_FIELDS,
        "conversion_scope_pair_counts",
        "conversion_reason_counts",
        "conversion_route_pair_counts",
        "conversion_receipt_consumed_validated_capability",
        "conversion_private_task_content_emitted",
        "conversion_privileged_evaluator_content_read",
    }
)


def _zero_mapping(names: Sequence[str]) -> dict[str, int]:
    return {name: 0 for name in names}


def task_projection(
    ordinal: int,
    capability: ValidatedProofCarryingConversionObservability,
) -> dict[str, Any]:
    if (
        isinstance(ordinal, bool)
        or not isinstance(ordinal, int)
        or ordinal < 1
        or not isinstance(
            capability, ValidatedProofCarryingConversionObservability
        )
    ):
        raise TypeError("V2.45.20 requires ordinal and conversion capability")
    base = parent.task_projection(ordinal, capability.parent_capability())
    receipt = observability.validate_conversion_observability(
        capability.counts_only_receipt()
    )
    value = {
        **base,
        "conversion_targeted_usable_page_count": int(
            receipt["targeted_usable_page_count"]
        ),
        "conversion_reserve_usable_page_count": int(
            receipt["reserve_usable_page_count"]
        ),
        "conversion_usable_page_count": int(receipt["usable_page_count"]),
        "conversion_selected_target_count": int(
            receipt["selected_target_count"]
        ),
        "conversion_page_target_pair_count": int(
            receipt["page_target_pair_count"]
        ),
        **{
            f"conversion_{name}": int(receipt[name])
            for name in observability.SIGNAL_COUNT_FIELDS
        },
        "conversion_scope_pair_counts": copy.deepcopy(
            receipt["scope_pair_counts"]
        ),
        "conversion_reason_counts": copy.deepcopy(receipt["reason_counts"]),
        "conversion_route_pair_counts": copy.deepcopy(
            receipt["route_pair_counts"]
        ),
        "conversion_receipt_consumed_validated_capability": True,
        "conversion_private_task_content_emitted": False,
        "conversion_privileged_evaluator_content_read": False,
    }
    return validate_total_row(value)


def failure_projection(ordinal: int) -> dict[str, Any]:
    value = {
        **parent.failure_projection(ordinal),
        **{name: 0 for name in COUNT_FIELDS},
        "conversion_scope_pair_counts": _zero_mapping(observability.SCOPES),
        "conversion_reason_counts": _zero_mapping(observability.REASONS),
        "conversion_route_pair_counts": _zero_mapping(observability.ROUTES),
        "conversion_receipt_consumed_validated_capability": False,
        "conversion_private_task_content_emitted": False,
        "conversion_privileged_evaluator_content_read": False,
    }
    return validate_total_row(value)


def _failure_unchecked(ordinal: int) -> dict[str, Any]:
    return {
        **parent.failure_projection_unchecked(ordinal),
        **{name: 0 for name in COUNT_FIELDS},
        "conversion_scope_pair_counts": _zero_mapping(observability.SCOPES),
        "conversion_reason_counts": _zero_mapping(observability.REASONS),
        "conversion_route_pair_counts": _zero_mapping(observability.ROUTES),
        "conversion_receipt_consumed_validated_capability": False,
        "conversion_private_task_content_emitted": False,
        "conversion_privileged_evaluator_content_read": False,
    }


def validate_total_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {name: copied[name] for name in parent.ROW_KEYS if name in copied}
    scopes = copied.get("conversion_scope_pair_counts")
    reasons = copied.get("conversion_reason_counts")
    routes = copied.get("conversion_route_pair_counts")
    success = copied.get("status") == "validated_capability"
    if (
        set(copied) != ROW_KEYS
        or set(base) != parent.ROW_KEYS
        or parent.validate_total_row(base) != base
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in COUNT_FIELDS
        )
        or not isinstance(scopes, Mapping)
        or set(scopes) != set(observability.SCOPES)
        or any(
            isinstance(scopes.get(name), bool)
            or not isinstance(scopes.get(name), int)
            or scopes[name] < 0
            for name in observability.SCOPES
        )
        or not isinstance(reasons, Mapping)
        or set(reasons) != set(observability.REASONS)
        or any(
            isinstance(reasons.get(name), bool)
            or not isinstance(reasons.get(name), int)
            or reasons[name] < 0
            for name in observability.REASONS
        )
        or not isinstance(routes, Mapping)
        or set(routes) != set(observability.ROUTES)
        or any(
            isinstance(routes.get(name), bool)
            or not isinstance(routes.get(name), int)
            or routes[name] < 0
            or routes[name] > copied["conversion_page_target_pair_count"]
            for name in observability.ROUTES
        )
        or copied["conversion_usable_page_count"]
        != copied["conversion_targeted_usable_page_count"]
        + copied["conversion_reserve_usable_page_count"]
        or copied["conversion_page_target_pair_count"]
        != copied["conversion_usable_page_count"]
        * copied["conversion_selected_target_count"]
        or scopes["targeted"]
        != copied["conversion_targeted_usable_page_count"]
        * copied["conversion_selected_target_count"]
        or scopes["reserve"]
        != copied["conversion_reserve_usable_page_count"]
        * copied["conversion_selected_target_count"]
        or sum(reasons.values()) != copied["conversion_page_target_pair_count"]
        or copied["conversion_grammar_projection_pair_count"]
        + copied["conversion_zero_projection_pair_count"]
        != copied["conversion_page_target_pair_count"]
        or copied["conversion_new_observation_pair_count"]
        != reasons["new_observation_emitted"]
        or copied["conversion_grammar_projection_pair_count"]
        != sum(
            reasons[name]
            for name in observability.REASONS
            if not name.startswith("no_projection_")
        )
        or copied["conversion_target_anchor_pair_count"]
        < copied["conversion_exact_body_entity_anchor_pair_count"]
        or copied["conversion_target_anchor_pair_count"]
        < copied["conversion_unique_target_title_anchor_pair_count"]
        or copied["conversion_unique_target_title_anchor_pair_count"]
        + copied["conversion_unique_other_row_title_anchor_pair_count"]
        + copied["conversion_ambiguous_or_absent_title_anchor_pair_count"]
        != copied["conversion_page_target_pair_count"]
        or copied["conversion_reserve_usable_page_count"]
        != copied["reserve_usable_page_count"]
        or copied["conversion_new_observation_pair_count"] > 0
        and copied["added_observation_count"] == 0
        or copied.get("conversion_receipt_consumed_validated_capability")
        is not success
        or copied.get("conversion_private_task_content_emitted") is not False
        or copied.get("conversion_privileged_evaluator_content_read") is not False
        or not success
        and copied != _failure_unchecked(copied["ordinal"])
    ):
        raise ValueError("V2.45.20 total conversion row drifted")
    return copied


AGGREGATE_KEYS = frozenset(
    {
        *parent.AGGREGATE_KEYS,
        "conversion_targeted_usable_page_tasks",
        "conversion_reserve_usable_page_tasks",
        "conversion_any_usable_page_tasks",
        "conversion_new_observation_tasks",
        "total_conversion_targeted_usable_page_count",
        "total_conversion_reserve_usable_page_count",
        "total_conversion_usable_page_count",
        "total_conversion_page_target_pair_count",
        "total_conversion_signal_counts",
        "conversion_reason_task_counts",
        "conversion_reason_pair_counts",
        "conversion_route_task_counts",
        "conversion_route_pair_counts",
        "all_success_rows_consumed_conversion_capabilities",
        "all_failure_rows_are_content_free_conversion_zero_projections",
        "conversion_failure_rows_claim_zero_private_effects",
        "conversion_private_task_content_emitted",
        "conversion_privileged_evaluator_content_read",
    }
)


def aggregate_projections(
    values: Sequence[
        ValidatedProofCarryingConversionObservability | Mapping[str, Any]
    ],
    *,
    selected: int,
) -> dict[str, Any]:
    if (
        isinstance(values, (str, bytes))
        or isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or len(values) != selected
    ):
        raise ValueError("V2.45.20 aggregate selection drifted")
    rows: list[dict[str, Any]] = []
    parent_inputs: list[Mapping[str, Any]] = []
    for ordinal, item in enumerate(values, start=1):
        if isinstance(item, ValidatedProofCarryingConversionObservability):
            rows.append(task_projection(ordinal, item))
            parent_inputs.append(
                base_proof.task_projection(ordinal, item.parent_capability())
            )
        elif isinstance(item, Mapping):
            row = validate_total_row(item)
            if row != _failure_unchecked(ordinal):
                raise ValueError(
                    "V2.45.20 public success row cannot be re-ingested as proof"
                )
            rows.append(row)
            parent_inputs.append(parent.failure_projection(ordinal))
        else:
            raise TypeError("V2.45.20 aggregate input is not proof or failure row")
    base = parent.aggregate_projections(parent_inputs, selected=selected)
    successes = [row for row in rows if row["status"] == "validated_capability"]
    failures = [row for row in rows if row["status"] == "failure_as_zero"]
    signal_totals = {
        name: sum(row[f"conversion_{name}"] for row in successes)
        for name in observability.SIGNAL_COUNT_FIELDS
    }
    reason_pairs = {
        name: sum(row["conversion_reason_counts"][name] for row in successes)
        for name in observability.REASONS
    }
    reason_tasks = {
        name: sum(
            row["conversion_reason_counts"][name] > 0 for row in successes
        )
        for name in observability.REASONS
    }
    route_pairs = {
        name: sum(
            row["conversion_route_pair_counts"][name] for row in successes
        )
        for name in observability.ROUTES
    }
    route_tasks = {
        name: sum(
            row["conversion_route_pair_counts"][name] > 0 for row in successes
        )
        for name in observability.ROUTES
    }
    value = {
        **base,
        "conversion_targeted_usable_page_tasks": sum(
            row["conversion_targeted_usable_page_count"] > 0
            for row in successes
        ),
        "conversion_reserve_usable_page_tasks": sum(
            row["conversion_reserve_usable_page_count"] > 0
            for row in successes
        ),
        "conversion_any_usable_page_tasks": sum(
            row["conversion_usable_page_count"] > 0 for row in successes
        ),
        "conversion_new_observation_tasks": sum(
            row["conversion_new_observation_pair_count"] > 0
            for row in successes
        ),
        "total_conversion_targeted_usable_page_count": sum(
            row["conversion_targeted_usable_page_count"] for row in successes
        ),
        "total_conversion_reserve_usable_page_count": sum(
            row["conversion_reserve_usable_page_count"] for row in successes
        ),
        "total_conversion_usable_page_count": sum(
            row["conversion_usable_page_count"] for row in successes
        ),
        "total_conversion_page_target_pair_count": sum(
            row["conversion_page_target_pair_count"] for row in successes
        ),
        "total_conversion_signal_counts": signal_totals,
        "conversion_reason_task_counts": reason_tasks,
        "conversion_reason_pair_counts": reason_pairs,
        "conversion_route_task_counts": route_tasks,
        "conversion_route_pair_counts": route_pairs,
        "all_success_rows_consumed_conversion_capabilities": all(
            row["conversion_receipt_consumed_validated_capability"]
            for row in successes
        ),
        "all_failure_rows_are_content_free_conversion_zero_projections": all(
            row == _failure_unchecked(row["ordinal"]) for row in failures
        ),
        "conversion_failure_rows_claim_zero_private_effects": False,
        "conversion_private_task_content_emitted": False,
        "conversion_privileged_evaluator_content_read": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    base = {
        name: copied[name] for name in parent.AGGREGATE_KEYS if name in copied
    }
    task_fields = (
        "conversion_targeted_usable_page_tasks",
        "conversion_reserve_usable_page_tasks",
        "conversion_any_usable_page_tasks",
        "conversion_new_observation_tasks",
    )
    count_fields = (
        *task_fields,
        "total_conversion_targeted_usable_page_count",
        "total_conversion_reserve_usable_page_count",
        "total_conversion_usable_page_count",
        "total_conversion_page_target_pair_count",
    )
    mappings = (
        ("total_conversion_signal_counts", observability.SIGNAL_COUNT_FIELDS),
        ("conversion_reason_task_counts", observability.REASONS),
        ("conversion_reason_pair_counts", observability.REASONS),
        ("conversion_route_task_counts", observability.ROUTES),
        ("conversion_route_pair_counts", observability.ROUTES),
    )
    if (
        set(copied) != AGGREGATE_KEYS
        or set(base) != parent.AGGREGATE_KEYS
        or parent.validate_aggregate(base) != base
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in count_fields
        )
        or any(copied[name] > copied["success_tasks"] for name in task_fields)
        or any(
            not isinstance(copied.get(field), Mapping)
            or set(copied[field]) != set(names)
            or any(
                isinstance(copied[field].get(name), bool)
                or not isinstance(copied[field].get(name), int)
                or copied[field][name] < 0
                for name in names
            )
            for field, names in mappings
        )
        or any(
            copied["conversion_reason_task_counts"][name]
            > copied["success_tasks"]
            for name in observability.REASONS
        )
        or any(
            copied["conversion_route_task_counts"][name]
            > copied["success_tasks"]
            for name in observability.ROUTES
        )
        or copied["total_conversion_usable_page_count"]
        != copied["total_conversion_targeted_usable_page_count"]
        + copied["total_conversion_reserve_usable_page_count"]
        or sum(copied["conversion_reason_pair_counts"].values())
        != copied["total_conversion_page_target_pair_count"]
        or copied["total_conversion_signal_counts"][
            "grammar_projection_pair_count"
        ]
        + copied["total_conversion_signal_counts"]["zero_projection_pair_count"]
        != copied["total_conversion_page_target_pair_count"]
        or copied["total_conversion_signal_counts"][
            "new_observation_pair_count"
        ]
        != copied["conversion_reason_pair_counts"]["new_observation_emitted"]
        or copied.get("all_success_rows_consumed_conversion_capabilities")
        is not True
        or copied.get(
            "all_failure_rows_are_content_free_conversion_zero_projections"
        )
        is not True
        or copied.get("conversion_failure_rows_claim_zero_private_effects")
        is not False
        or copied.get("conversion_private_task_content_emitted") is not False
        or copied.get("conversion_privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.45.20 total conversion aggregate drifted")
    return copied


__all__ = [
    "AGGREGATE_KEYS",
    "POLICY_ID",
    "ROW_KEYS",
    "aggregate_projections",
    "failure_projection",
    "task_projection",
    "validate_aggregate",
    "validate_total_row",
]
