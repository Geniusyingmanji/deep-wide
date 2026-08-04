"""Content-free external projection for V2.44.30 title-anchor envelopes.

The adapter validates the complete V2.44.30 wrapper, reuses V2.44.25 for all
parent search/entropy/rejection counts, and adds only nonnegative title-anchor
counts, entropy/credit scalars, and effect-equivalence booleans.  No task,
title, query, URL, page, source, value, prediction, candidate, or content hash
is emitted.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from deepwide_agent.v24413_effect_equivalence import (
    validate_effect_equivalence_receipt,
)
from deepwide_agent.v24430_title_anchor_effect_runner import (
    validate_envelope as validate_title_anchor_envelope,
)
from scripts import v24425_projection_observable_external_projection as base


SELECTED = base.SELECTED
MODEL_SLOT_CAP = base.MODEL_SLOT_CAP
COMPLETION_KINDS = base.COMPLETION_KINDS
TITLE_COUNT_FIELDS = (
    "title_unique_anchor_page_count",
    "title_ambiguous_or_absent_anchor_page_count",
    "title_projection_count",
    "title_novel_observation_count",
    "title_combined_observation_count",
    "title_safe_change_count",
    "title_baseline_confirmed_count",
    "title_unresolved_count",
    "title_positive_epistemic_target_count",
    "title_source_credit_record_count",
    "title_candidate_changed_cell_count",
)
TITLE_NUMERIC_FIELDS = (
    "title_pre_active_entropy_total_nats",
    "title_combined_entropy_total_nats",
    "title_positive_information_gain_total_nats",
    "title_bayesian_surprise_total_nats",
    "title_epistemic_credit_total_nats",
    "title_decision_credit_total_nats",
)
TITLE_BOOLEAN_FIELDS = (
    "title_recovery_changed_parent_output",
    "title_projection_private_replay_valid",
    "title_parent_projection_preserved",
    "title_effect_equivalence_valid",
    "title_model_remaining_seconds_nonincreasing",
    "title_model_deadline_state_monotonic",
    "title_transport_deadline_state_monotonic",
)
TASK_CHECK_NAMES = (
    *base.TASK_CHECK_NAMES,
    "title_anchor_observation_conservation",
    "title_anchor_posterior_conservation",
    "title_anchor_entropy_credit_conservation",
    "title_anchor_effect_equivalence_attested",
)
TASK_KEYS = frozenset(
    {
        *base.TASK_KEYS,
        *TITLE_COUNT_FIELDS,
        *TITLE_NUMERIC_FIELDS,
        *TITLE_BOOLEAN_FIELDS,
    }
)
AGGREGATE_COUNT_FIELDS = (
    "title_unique_anchor_tasks",
    "title_projection_tasks",
    "title_novel_observation_tasks",
    "title_positive_epistemic_tasks",
    "title_safe_change_tasks",
    "title_decision_credit_tasks",
    "title_effect_equivalent_tasks",
    "title_unique_anchor_pages",
    "title_ambiguous_or_absent_anchor_pages",
    "title_projections",
    "title_novel_observations",
    "title_combined_observations",
    "title_safe_change_count",
    "title_baseline_confirmed_count",
    "title_unresolved_count",
    "title_positive_epistemic_target_count",
    "title_source_credit_record_count",
    "title_candidate_changed_cell_count",
)
AGGREGATE_NUMERIC_FIELDS = (
    "title_pre_active_entropy_total_nats",
    "title_combined_entropy_total_nats",
    "title_positive_information_gain_total_nats",
    "title_bayesian_surprise_total_nats",
    "title_epistemic_credit_total_nats",
    "title_decision_credit_total_nats",
)
AGGREGATE_BOOLEAN_FIELDS = (
    "all_title_projection_private_replay_valid",
    "all_title_parent_projections_preserved",
    "all_title_effect_equivalence_attested",
    "all_title_model_remaining_seconds_nonincreasing",
    "all_title_model_deadline_states_monotonic",
    "all_title_transport_deadline_states_monotonic",
)
AGGREGATE_CHECK_NAMES = (
    *base.AGGREGATE_CHECK_NAMES,
    "title_anchor_observation_tasks",
    "title_anchor_positive_epistemic_tasks",
    "title_anchor_safe_change_tasks",
    "title_anchor_positive_decision_credit",
    "title_anchor_credit_consistency",
    "all_title_effect_equivalence_attested",
)
AGGREGATE_KEYS = frozenset(
    {
        *base.AGGREGATE_KEYS,
        *AGGREGATE_COUNT_FIELDS,
        *AGGREGATE_NUMERIC_FIELDS,
        *AGGREGATE_BOOLEAN_FIELDS,
    }
)


_BASE_TASK_DERIVED_KEYS = frozenset({"checks", "passed"})
_BASE_AGGREGATE_DERIVED_KEYS = frozenset({"checks", "passed"})


def _base_task_view(value: Mapping[str, Any]) -> dict[str, Any]:
    required = base.TASK_KEYS - _BASE_TASK_DERIVED_KEYS
    if not required <= set(value):
        raise RuntimeError("V2.44.32 base task fields are incomplete")
    projected = {key: copy.deepcopy(value[key]) for key in required}
    projected["checks"] = base.task_checks(projected)
    projected["passed"] = all(projected["checks"].values())
    return projected


def _base_aggregate_view(
    value: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, Any]:
    required = base.AGGREGATE_KEYS - _BASE_AGGREGATE_DERIVED_KEYS
    if not required <= set(value):
        raise RuntimeError("V2.44.32 base aggregate fields are incomplete")
    projected = {key: copy.deepcopy(value[key]) for key in required}
    projected["checks"] = base.aggregate_checks(projected, gates)
    projected["passed"] = all(projected["checks"].values())
    return projected


def task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    base_value = _base_task_view(value)
    selected = int(value.get("selected_uncertainty_target_count", -1))
    safe = int(value.get("title_safe_change_count", -1))
    confirmed = int(value.get("title_baseline_confirmed_count", -1))
    unresolved = int(value.get("title_unresolved_count", -1))
    checks = {
        **base.task_checks(base_value),
        "title_anchor_observation_conservation": (
            value.get("title_unique_anchor_page_count", -1)
            + value.get("title_ambiguous_or_absent_anchor_page_count", -1)
            == value.get("active_page_count", -1)
            and value.get("title_combined_observation_count", -1)
            >= value.get("combined_active_observation_count", -1)
            and value.get("title_novel_observation_count", -1)
            <= value.get("title_combined_observation_count", -1)
            and value.get("title_source_credit_record_count", -1)
            <= value.get("title_combined_observation_count", -1)
            and value.get("title_projection_private_replay_valid") is True
            and value.get("title_parent_projection_preserved") is True
        ),
        "title_anchor_posterior_conservation": (
            safe + confirmed + unresolved == selected
            and value.get("title_positive_epistemic_target_count", -1) <= selected
        ),
        "title_anchor_entropy_credit_conservation": (
            0.0
            <= float(value.get("title_decision_credit_total_nats", -1.0))
            <= float(value.get("title_epistemic_credit_total_nats", -1.0))
            + 1e-12
            <= float(
                value.get("title_positive_information_gain_total_nats", -1.0)
            )
            + 1e-12
            and (
                float(value.get("title_decision_credit_total_nats", 0.0)) == 0
                or safe > 0
            )
        ),
        "title_anchor_effect_equivalence_attested": all(
            value.get(name) is True
            for name in (
                "title_effect_equivalence_valid",
                "title_model_remaining_seconds_nonincreasing",
                "title_model_deadline_state_monotonic",
                "title_transport_deadline_state_monotonic",
            )
        ),
    }
    if tuple(checks) != TASK_CHECK_NAMES:
        raise RuntimeError("V2.44.32 task check order drifted")
    return checks


def task_projection(
    ordinal: int,
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        raise ValueError("V2.44.32 successful parent is missing its envelope")
    wrapped = validate_title_anchor_envelope(envelope)
    legacy = base.task_projection(ordinal, parent, wrapped["parent_envelope"])
    legacy.pop("checks")
    legacy.pop("passed")
    receipt = wrapped["title_anchor_result"]["title_anchor_recovery_receipt"]
    equivalence = validate_effect_equivalence_receipt(
        wrapped["effect_equivalence_receipt"]
    )
    value = {
        **legacy,
        "title_unique_anchor_page_count": int(
            receipt["unique_title_anchor_page_count"]
        ),
        "title_ambiguous_or_absent_anchor_page_count": int(
            receipt["ambiguous_or_absent_title_anchor_page_count"]
        ),
        "title_projection_count": int(receipt["title_anchor_projection_count"]),
        "title_novel_observation_count": int(
            receipt["novel_title_anchor_observation_count"]
        ),
        "title_combined_observation_count": int(
            receipt["combined_title_anchor_observation_count"]
        ),
        "title_safe_change_count": int(
            receipt["title_recovered_safe_change_count"]
        ),
        "title_baseline_confirmed_count": int(
            receipt["title_recovered_baseline_confirmed_count"]
        ),
        "title_unresolved_count": int(receipt["title_recovered_unresolved_count"]),
        "title_positive_epistemic_target_count": int(
            receipt["title_recovered_positive_epistemic_target_count"]
        ),
        "title_source_credit_record_count": int(
            receipt["title_recovered_source_credit_record_count"]
        ),
        "title_candidate_changed_cell_count": int(
            receipt["title_candidate_changed_cell_count"]
        ),
        "title_pre_active_entropy_total_nats": float(
            receipt["title_recovered_pre_active_entropy_total_nats"]
        ),
        "title_combined_entropy_total_nats": float(
            receipt["title_recovered_combined_entropy_total_nats"]
        ),
        "title_positive_information_gain_total_nats": float(
            receipt["title_recovered_positive_information_gain_total_nats"]
        ),
        "title_bayesian_surprise_total_nats": float(
            receipt["title_recovered_bayesian_surprise_total_nats"]
        ),
        "title_epistemic_credit_total_nats": float(
            receipt["title_recovered_epistemic_credit_total_nats"]
        ),
        "title_decision_credit_total_nats": float(
            receipt["title_recovered_decision_credit_total_nats"]
        ),
        "title_recovery_changed_parent_output": bool(
            receipt["title_recovery_changed_parent_output"]
        ),
        "title_projection_private_replay_valid": bool(
            receipt["unique_title_anchor_projection_private_replay_valid"]
        ),
        "title_parent_projection_preserved": bool(
            receipt["parent_structured_projection_preserved_exactly"]
        ),
        "title_effect_equivalence_valid": True,
        "title_model_remaining_seconds_nonincreasing": equivalence[
            "model_remaining_seconds_nonincreasing"
        ],
        "title_model_deadline_state_monotonic": equivalence[
            "model_deadline_state_monotonic"
        ],
        "title_transport_deadline_state_monotonic": equivalence[
            "transport_deadline_state_monotonic"
        ],
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
            for name in TITLE_COUNT_FIELDS
        )
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in TITLE_NUMERIC_FIELDS
        )
        or any(
            not isinstance(value.get(name), bool) for name in TITLE_BOOLEAN_FIELDS
        )
        or not isinstance(checks, Mapping)
        or tuple(checks) != TASK_CHECK_NAMES
        or dict(checks) != task_checks(value)
        or value.get("passed") is not all(checks.values())
    ):
        raise RuntimeError("V2.44.32 task projection drifted")
    return copy.deepcopy(dict(value))


def local_failure(ordinal: int) -> dict[str, Any]:
    legacy = base.local_failure(ordinal)
    legacy.pop("checks")
    legacy.pop("passed")
    value = {
        **legacy,
        **{name: 0 for name in TITLE_COUNT_FIELDS},
        **{name: 0.0 for name in TITLE_NUMERIC_FIELDS},
        **{name: False for name in TITLE_BOOLEAN_FIELDS},
    }
    value["checks"] = task_checks(value)
    value["passed"] = False
    validate_task_projection(value)
    return value


def aggregate_checks(
    summary: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, bool]:
    base_value = _base_aggregate_view(summary, gates)
    checks = {
        **base.aggregate_checks(base_value, gates),
        "title_anchor_observation_tasks": summary["title_novel_observation_tasks"]
        >= gates["minimum_title_novel_observation_tasks"],
        "title_anchor_positive_epistemic_tasks": summary[
            "title_positive_epistemic_tasks"
        ]
        >= gates["minimum_title_positive_epistemic_tasks"],
        "title_anchor_safe_change_tasks": summary["title_safe_change_tasks"]
        >= gates["minimum_title_safe_change_tasks"],
        "title_anchor_positive_decision_credit": summary[
            "title_decision_credit_total_nats"
        ]
        >= gates["minimum_title_decision_credit_nats"],
        "title_anchor_credit_consistency": (
            0.0
            <= summary["title_decision_credit_total_nats"]
            <= summary["title_epistemic_credit_total_nats"] + 1e-12
            and (
                summary["title_decision_credit_total_nats"] == 0
                or summary["title_safe_change_count"] > 0
            )
            and summary["title_unique_anchor_pages"]
            + summary["title_ambiguous_or_absent_anchor_pages"]
            == summary["active_pages"]
        ),
        "all_title_effect_equivalence_attested": (
            summary["title_effect_equivalent_tasks"] == summary["selected"]
            and summary["all_title_projection_private_replay_valid"] is True
            and summary["all_title_parent_projections_preserved"] is True
            and summary["all_title_effect_equivalence_attested"] is True
            and summary["all_title_model_remaining_seconds_nonincreasing"] is True
            and summary["all_title_model_deadline_states_monotonic"] is True
            and summary["all_title_transport_deadline_states_monotonic"] is True
        ),
    }
    if tuple(checks) != AGGREGATE_CHECK_NAMES:
        raise RuntimeError("V2.44.32 aggregate check order drifted")
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
        "title_unique_anchor_tasks": sum(
            item["title_unique_anchor_page_count"] > 0 for item in values
        ),
        "title_projection_tasks": sum(
            item["title_projection_count"] > 0 for item in values
        ),
        "title_novel_observation_tasks": sum(
            item["title_novel_observation_count"] > 0 for item in values
        ),
        "title_positive_epistemic_tasks": sum(
            item["title_epistemic_credit_total_nats"] > 0 for item in values
        ),
        "title_safe_change_tasks": sum(
            item["title_safe_change_count"] > 0 for item in values
        ),
        "title_decision_credit_tasks": sum(
            item["title_decision_credit_total_nats"] > 0 for item in values
        ),
        "title_effect_equivalent_tasks": sum(
            item["title_effect_equivalence_valid"] for item in values
        ),
        "title_unique_anchor_pages": sum(
            item["title_unique_anchor_page_count"] for item in values
        ),
        "title_ambiguous_or_absent_anchor_pages": sum(
            item["title_ambiguous_or_absent_anchor_page_count"] for item in values
        ),
        "title_projections": sum(item["title_projection_count"] for item in values),
        "title_novel_observations": sum(
            item["title_novel_observation_count"] for item in values
        ),
        "title_combined_observations": sum(
            item["title_combined_observation_count"] for item in values
        ),
        "title_safe_change_count": sum(
            item["title_safe_change_count"] for item in values
        ),
        "title_baseline_confirmed_count": sum(
            item["title_baseline_confirmed_count"] for item in values
        ),
        "title_unresolved_count": sum(
            item["title_unresolved_count"] for item in values
        ),
        "title_positive_epistemic_target_count": sum(
            item["title_positive_epistemic_target_count"] for item in values
        ),
        "title_source_credit_record_count": sum(
            item["title_source_credit_record_count"] for item in values
        ),
        "title_candidate_changed_cell_count": sum(
            item["title_candidate_changed_cell_count"] for item in values
        ),
        "all_title_projection_private_replay_valid": all(
            item["title_projection_private_replay_valid"] for item in values
        ),
        "all_title_parent_projections_preserved": all(
            item["title_parent_projection_preserved"] for item in values
        ),
        "all_title_effect_equivalence_attested": all(
            item["checks"]["title_anchor_effect_equivalence_attested"]
            for item in values
        ),
        "all_title_model_remaining_seconds_nonincreasing": all(
            item["title_model_remaining_seconds_nonincreasing"] for item in values
        ),
        "all_title_model_deadline_states_monotonic": all(
            item["title_model_deadline_state_monotonic"] for item in values
        ),
        "all_title_transport_deadline_states_monotonic": all(
            item["title_transport_deadline_state_monotonic"] for item in values
        ),
    }
    for name in AGGREGATE_NUMERIC_FIELDS:
        summary[name] = round(sum(float(item[name]) for item in values), 12)
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
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in AGGREGATE_NUMERIC_FIELDS
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
        raise RuntimeError("V2.44.32 aggregate drifted")
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
