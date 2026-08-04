"""Content-free external projection for V2.44.23 envelopes.

The adapter validates the complete V2.44.23 wrapper, delegates all existing
mechanism and effect-equivalence algebra to the frozen V2.44.17 projector, and
adds only integer counts from the V2.44.21 rejection receipt.  No task-private
entity, page, source, value, URL, text, or content hash enters the task or
aggregate projection.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from typing import Any

from deepwide_agent.v24421_structured_projection_observability import (
    REASONS,
    validate_projection_observability,
)
from deepwide_agent.v24423_projection_observable_runner import (
    validate_envelope as validate_projection_observable_envelope,
)
from scripts import v24417_effect_equivalent_external_projection as base


SELECTED = base.SELECTED
MODEL_SLOT_CAP = base.MODEL_SLOT_CAP
COMPLETION_KINDS = base.COMPLETION_KINDS
REASON_TASK_FIELDS = {
    "unsupported_column_kind": "projection_unsupported_column_kind_pairs",
    "exact_structured_entity_anchor_absent": (
        "projection_exact_structured_entity_anchor_absent_pairs"
    ),
    "exact_label_absent_in_entity_scope": (
        "projection_exact_label_absent_in_entity_scope_pairs"
    ),
    "exact_label_value_year_absent": (
        "projection_exact_label_value_year_absent_pairs"
    ),
    "structured_projection_emitted": "projection_emitted_pairs",
}
TASK_COUNT_FIELDS = (
    "projection_page_count",
    "projection_selected_target_count",
    "projection_page_target_pair_count",
    *REASON_TASK_FIELDS.values(),
    "projection_structured_projection_pair_count",
    "projection_structured_observation_count",
    "projection_structured_observation_duplicate_legacy_count",
)
TASK_BOOLEAN_FIELDS = (
    "projection_observability_valid",
    "projection_reason_partition_exact",
)
TASK_CHECK_NAMES = (*base.TASK_CHECK_NAMES, "projection_observability_attested")
TASK_KEYS = frozenset(
    {*base.TASK_KEYS, *TASK_COUNT_FIELDS, *TASK_BOOLEAN_FIELDS}
)
AGGREGATE_REASON_FIELDS = {
    reason: field.replace("projection_", "projection_total_", 1)
    for reason, field in REASON_TASK_FIELDS.items()
}
AGGREGATE_COUNT_FIELDS = (
    "projection_observable_tasks",
    "projection_total_pages",
    "projection_total_selected_targets",
    "projection_total_page_target_pairs",
    *AGGREGATE_REASON_FIELDS.values(),
    "projection_total_structured_projection_pairs",
    "projection_total_structured_observations",
    "projection_total_structured_observation_duplicates",
)
AGGREGATE_BOOLEAN_FIELDS = (
    "all_projection_reason_partitions_exact",
    "all_projection_observability_attested",
)
AGGREGATE_CHECK_NAMES = (
    *base.AGGREGATE_CHECK_NAMES,
    "all_projection_observability_attested",
)
AGGREGATE_KEYS = frozenset(
    {
        *base.AGGREGATE_KEYS,
        *AGGREGATE_COUNT_FIELDS,
        *AGGREGATE_BOOLEAN_FIELDS,
    }
)

_BASE_TASK_DERIVED_KEYS = frozenset({"checks", "passed"})
_BASE_AGGREGATE_DERIVED_KEYS = frozenset({"checks", "passed"})


def _base_task_view(value: Mapping[str, Any]) -> dict[str, Any]:
    required = base.TASK_KEYS - _BASE_TASK_DERIVED_KEYS
    if not required <= set(value):
        raise RuntimeError("V2.44.25 base task fields are incomplete")
    projected = {key: copy.deepcopy(value[key]) for key in required}
    projected["checks"] = base.task_checks(projected)
    projected["passed"] = all(projected["checks"].values())
    return projected


def _base_aggregate_view(
    value: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, Any]:
    required = base.AGGREGATE_KEYS - _BASE_AGGREGATE_DERIVED_KEYS
    if not required <= set(value):
        raise RuntimeError("V2.44.25 base aggregate fields are incomplete")
    projected = {key: copy.deepcopy(value[key]) for key in required}
    projected["checks"] = base.aggregate_checks(projected, gates)
    projected["passed"] = all(projected["checks"].values())
    return projected


def _reason_total(value: Mapping[str, Any]) -> int:
    return sum(int(value.get(field, -1)) for field in REASON_TASK_FIELDS.values())


def task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    base_value = _base_task_view(value)
    checks = {
        **base.task_checks(base_value),
        "projection_observability_attested": (
            value.get("projection_observability_valid") is True
            and value.get("projection_reason_partition_exact") is True
            and value.get("projection_page_count") == value.get("active_page_count")
            and value.get("projection_selected_target_count")
            == value.get("selected_uncertainty_target_count")
            and value.get("projection_page_target_pair_count")
            == value.get("projection_page_count")
            * value.get("projection_selected_target_count")
            and _reason_total(value)
            == value.get("projection_page_target_pair_count")
            and value.get("projection_structured_projection_pair_count")
            == value.get("projection_emitted_pairs")
            and value.get("projection_structured_observation_count")
            == value.get("novel_structured_observation_count")
            + value.get("projection_structured_observation_duplicate_legacy_count")
            and value.get("projection_structured_observation_count")
            <= value.get("structured_projection_count")
        ),
    }
    if tuple(checks) != TASK_CHECK_NAMES:
        raise RuntimeError("V2.44.25 task check order drifted")
    return checks


def task_projection(
    ordinal: int,
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        raise ValueError("V2.44.25 successful parent is missing its envelope")
    wrapped = validate_projection_observable_envelope(envelope)
    receipt = validate_projection_observability(
        wrapped["projection_observability_receipt"]
    )
    legacy = base.task_projection(ordinal, parent, wrapped["parent_envelope"])
    legacy.pop("checks")
    legacy.pop("passed")
    value = {
        **legacy,
        "projection_page_count": receipt["page_count"],
        "projection_selected_target_count": receipt["selected_target_count"],
        "projection_page_target_pair_count": receipt["page_target_pair_count"],
        **{
            field: receipt["reason_counts"][reason]
            for reason, field in REASON_TASK_FIELDS.items()
        },
        "projection_structured_projection_pair_count": receipt[
            "structured_projection_pair_count"
        ],
        "projection_structured_observation_count": receipt[
            "structured_observation_count"
        ],
        "projection_structured_observation_duplicate_legacy_count": receipt[
            "structured_observation_duplicate_legacy_count"
        ],
        "projection_observability_valid": True,
        "projection_reason_partition_exact": receipt["reason_partition_exact"],
    }
    value["checks"] = task_checks(value)
    value["passed"] = all(value["checks"].values())
    validate_task_projection(value)
    return value


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    checks = value.get("checks")
    base_value = _base_task_view(value)
    base.validate_task_projection(base_value)
    if (
        set(value) != TASK_KEYS
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in TASK_COUNT_FIELDS
        )
        or any(not isinstance(value.get(name), bool) for name in TASK_BOOLEAN_FIELDS)
        or not isinstance(checks, Mapping)
        or tuple(checks) != TASK_CHECK_NAMES
        or dict(checks) != task_checks(value)
        or value.get("passed") is not all(checks.values())
    ):
        raise RuntimeError("V2.44.25 task projection drifted")
    return copy.deepcopy(dict(value))


def local_failure(ordinal: int) -> dict[str, Any]:
    legacy = base.local_failure(ordinal)
    legacy.pop("checks")
    legacy.pop("passed")
    value = {
        **legacy,
        **{name: 0 for name in TASK_COUNT_FIELDS},
        **{name: False for name in TASK_BOOLEAN_FIELDS},
    }
    value["checks"] = task_checks(value)
    value["passed"] = False
    validate_task_projection(value)
    return value


def aggregate_checks(
    summary: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, bool]:
    base_value = _base_aggregate_view(summary, gates)
    reason_total = sum(
        int(summary.get(field, -1)) for field in AGGREGATE_REASON_FIELDS.values()
    )
    checks = {
        **base.aggregate_checks(base_value, gates),
        "all_projection_observability_attested": (
            summary.get("projection_observable_tasks") == summary.get("selected")
            and summary.get("projection_total_pages") == summary.get("active_pages")
            and reason_total == summary.get("projection_total_page_target_pairs")
            and summary.get("projection_total_structured_projection_pairs")
            == summary.get("projection_total_emitted_pairs")
            and summary.get("projection_total_structured_observations")
            == summary.get("novel_structured_observations")
            + summary.get("projection_total_structured_observation_duplicates")
            and summary.get("all_projection_reason_partitions_exact") is True
            and summary.get("all_projection_observability_attested") is True
        ),
    }
    if tuple(checks) != AGGREGATE_CHECK_NAMES:
        raise RuntimeError("V2.44.25 aggregate check order drifted")
    return checks


def aggregate_tasks(
    tasks: Sequence[Mapping[str, Any]],
    batch_wall_seconds: float,
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    values = sorted(
        (validate_task_projection(item) for item in tasks),
        key=lambda item: item["ordinal"],
    )
    legacy = base.aggregate_tasks(
        [_base_task_view(item) for item in values], batch_wall_seconds, gates
    )
    legacy.pop("checks")
    legacy.pop("passed")
    summary = {
        **legacy,
        "projection_observable_tasks": sum(
            item["projection_observability_valid"] for item in values
        ),
        "projection_total_pages": sum(
            item["projection_page_count"] for item in values
        ),
        "projection_total_selected_targets": sum(
            item["projection_selected_target_count"] for item in values
        ),
        "projection_total_page_target_pairs": sum(
            item["projection_page_target_pair_count"] for item in values
        ),
        **{
            aggregate_field: sum(item[task_field] for item in values)
            for reason, aggregate_field in AGGREGATE_REASON_FIELDS.items()
            for task_field in (REASON_TASK_FIELDS[reason],)
        },
        "projection_total_structured_projection_pairs": sum(
            item["projection_structured_projection_pair_count"] for item in values
        ),
        "projection_total_structured_observations": sum(
            item["projection_structured_observation_count"] for item in values
        ),
        "projection_total_structured_observation_duplicates": sum(
            item["projection_structured_observation_duplicate_legacy_count"]
            for item in values
        ),
        "all_projection_reason_partitions_exact": all(
            item["projection_reason_partition_exact"] for item in values
        ),
        "all_projection_observability_attested": all(
            item["checks"]["projection_observability_attested"] for item in values
        ),
    }
    summary["checks"] = aggregate_checks(summary, gates)
    summary["passed"] = all(summary["checks"].values())
    validate_aggregate(summary, gates)
    return summary


def validate_aggregate(
    value: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, Any]:
    checks = value.get("checks")
    base_value = _base_aggregate_view(value, gates)
    base.validate_aggregate(base_value, gates)
    if (
        set(value) != AGGREGATE_KEYS
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in AGGREGATE_COUNT_FIELDS
        )
        or any(
            not isinstance(value.get(name), bool)
            for name in AGGREGATE_BOOLEAN_FIELDS
        )
        or not isinstance(checks, Mapping)
        or tuple(checks) != AGGREGATE_CHECK_NAMES
        or dict(checks) != aggregate_checks(value, gates)
        or value.get("passed") is not all(checks.values())
    ):
        raise RuntimeError("V2.44.25 aggregate drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "AGGREGATE_KEYS",
    "TASK_KEYS",
    "aggregate_checks",
    "aggregate_tasks",
    "local_failure",
    "task_checks",
    "task_projection",
    "validate_aggregate",
    "validate_task_projection",
]
