"""Counts-only external projection for V2.44.38 narrative envelopes.

The adapter validates the complete V2.44.38 wrapper, reuses V2.44.32 for all
parent search/title/entropy counts, and adds only the six narrative rejection
counts, posterior/credit scalars, effect-cap values, and equivalence booleans.
No task, title, query, URL, page, source, entity, value, prediction, candidate,
or content hash is emitted.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from deepwide_agent.v24413_effect_equivalence import (
    validate_effect_equivalence_receipt,
)
from deepwide_agent.v24436_narrative_title_anchor_projection import REASONS
from deepwide_agent.v24438_bounded_narrative_effect_runner import (
    MAXIMUM_PROVIDER_EFFECT_SECONDS,
    validate_effect_timeout_contract,
    validate_envelope as validate_narrative_envelope,
)
from scripts import v24432_title_anchor_external_projection as base


SELECTED = base.SELECTED
MODEL_SLOT_CAP = base.MODEL_SLOT_CAP
COMPLETION_KINDS = base.COMPLETION_KINDS
REASON_TASK_FIELDS = {
    reason: f"narrative_{reason}_pair_count" for reason in REASONS
}
NARRATIVE_COUNT_FIELDS = (
    "narrative_page_target_pair_count",
    *REASON_TASK_FIELDS.values(),
    "narrative_projection_count",
    "narrative_novel_observation_count",
    "narrative_combined_observation_count",
    "narrative_safe_change_count",
    "narrative_baseline_confirmed_count",
    "narrative_unresolved_count",
    "narrative_positive_epistemic_target_count",
    "narrative_source_credit_record_count",
    "narrative_candidate_changed_cell_count",
)
NARRATIVE_NUMERIC_FIELDS = (
    "narrative_pre_active_entropy_total_nats",
    "narrative_combined_entropy_total_nats",
    "narrative_positive_information_gain_total_nats",
    "narrative_bayesian_surprise_total_nats",
    "narrative_epistemic_credit_total_nats",
    "narrative_decision_credit_total_nats",
    "model_provider_effect_timeout_seconds",
    "hosted_search_effect_timeout_seconds",
)
NARRATIVE_BOOLEAN_FIELDS = (
    "narrative_recovery_changed_parent_output",
    "narrative_projection_private_replay_valid",
    "narrative_parent_title_projection_preserved",
    "narrative_reason_partition_exact",
    "effect_timeout_contract_valid",
    "narrative_effect_equivalence_valid",
    "narrative_model_remaining_seconds_nonincreasing",
    "narrative_model_deadline_state_monotonic",
    "narrative_transport_deadline_state_monotonic",
)
TASK_CHECK_NAMES = (
    *base.TASK_CHECK_NAMES,
    "narrative_rejection_partition_attested",
    "narrative_observation_conservation",
    "narrative_posterior_conservation",
    "narrative_entropy_credit_conservation",
    "provider_effect_cap_attested",
    "narrative_effect_equivalence_attested",
)
TASK_KEYS = frozenset(
    {
        *base.TASK_KEYS,
        *NARRATIVE_COUNT_FIELDS,
        *NARRATIVE_NUMERIC_FIELDS,
        *NARRATIVE_BOOLEAN_FIELDS,
    }
)
AGGREGATE_REASON_FIELDS = {
    reason: f"narrative_total_{reason}_pairs" for reason in REASONS
}
AGGREGATE_COUNT_FIELDS = (
    "narrative_projection_tasks",
    "narrative_novel_observation_tasks",
    "narrative_positive_epistemic_tasks",
    "narrative_safe_change_tasks",
    "narrative_decision_credit_tasks",
    "narrative_effect_equivalent_tasks",
    "narrative_total_page_target_pairs",
    *AGGREGATE_REASON_FIELDS.values(),
    "narrative_projections",
    "narrative_novel_observations",
    "narrative_combined_observations",
    "narrative_safe_change_count",
    "narrative_baseline_confirmed_count",
    "narrative_unresolved_count",
    "narrative_positive_epistemic_target_count",
    "narrative_source_credit_record_count",
    "narrative_candidate_changed_cell_count",
)
AGGREGATE_NUMERIC_FIELDS = (
    "narrative_pre_active_entropy_total_nats",
    "narrative_combined_entropy_total_nats",
    "narrative_positive_information_gain_total_nats",
    "narrative_bayesian_surprise_total_nats",
    "narrative_epistemic_credit_total_nats",
    "narrative_decision_credit_total_nats",
    "maximum_observed_model_provider_effect_timeout_seconds",
    "maximum_observed_hosted_search_effect_timeout_seconds",
)
AGGREGATE_BOOLEAN_FIELDS = (
    "all_narrative_projection_private_replay_valid",
    "all_narrative_parent_title_projections_preserved",
    "all_narrative_reason_partitions_exact",
    "all_effect_timeout_contracts_valid",
    "all_narrative_effect_equivalence_attested",
    "all_narrative_model_remaining_seconds_nonincreasing",
    "all_narrative_model_deadline_states_monotonic",
    "all_narrative_transport_deadline_states_monotonic",
)
AGGREGATE_CHECK_NAMES = (
    *base.AGGREGATE_CHECK_NAMES,
    "narrative_observation_tasks",
    "narrative_positive_epistemic_tasks",
    "narrative_safe_change_tasks",
    "narrative_positive_decision_credit",
    "narrative_credit_consistency",
    "provider_effect_cap_attested",
    "all_narrative_effect_equivalence_attested",
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
        raise RuntimeError("V2.44.40 base task fields are incomplete")
    projected = {key: copy.deepcopy(value[key]) for key in required}
    projected["checks"] = base.task_checks(projected)
    projected["passed"] = all(projected["checks"].values())
    return projected


def _base_aggregate_view(
    value: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, Any]:
    required = base.AGGREGATE_KEYS - _BASE_AGGREGATE_DERIVED_KEYS
    if not required <= set(value):
        raise RuntimeError("V2.44.40 base aggregate fields are incomplete")
    projected = {key: copy.deepcopy(value[key]) for key in required}
    projected["checks"] = base.aggregate_checks(projected, gates)
    projected["passed"] = all(projected["checks"].values())
    return projected


def _reason_total(value: Mapping[str, Any]) -> int:
    return sum(int(value.get(field, -1)) for field in REASON_TASK_FIELDS.values())


def task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    base_value = _base_task_view(value)
    selected = int(value.get("selected_uncertainty_target_count", -1))
    safe = int(value.get("narrative_safe_change_count", -1))
    confirmed = int(value.get("narrative_baseline_confirmed_count", -1))
    unresolved = int(value.get("narrative_unresolved_count", -1))
    checks = {
        **base.task_checks(base_value),
        "narrative_rejection_partition_attested": (
            value.get("narrative_reason_partition_exact") is True
            and _reason_total(value)
            == value.get("narrative_page_target_pair_count", -1)
            and value.get(REASON_TASK_FIELDS["narrative_projection_emitted"], -1)
            >= value.get("narrative_projection_count", -1)
        ),
        "narrative_observation_conservation": (
            value.get("narrative_combined_observation_count", -1)
            >= value.get("title_combined_observation_count", -1)
            and value.get("narrative_novel_observation_count", -1)
            <= value.get("narrative_combined_observation_count", -1)
            and value.get("narrative_source_credit_record_count", -1)
            <= value.get("narrative_combined_observation_count", -1)
            and value.get("narrative_projection_private_replay_valid") is True
            and value.get("narrative_parent_title_projection_preserved") is True
        ),
        "narrative_posterior_conservation": (
            safe + confirmed + unresolved == selected
            and value.get("narrative_positive_epistemic_target_count", -1)
            <= selected
        ),
        "narrative_entropy_credit_conservation": (
            0.0
            <= float(value.get("narrative_decision_credit_total_nats", -1.0))
            <= float(value.get("narrative_epistemic_credit_total_nats", -1.0))
            + 1e-12
            <= float(
                value.get("narrative_positive_information_gain_total_nats", -1.0)
            )
            + 1e-12
            and (
                float(value.get("narrative_decision_credit_total_nats", 0.0))
                == 0
                or safe > 0
            )
        ),
        "provider_effect_cap_attested": (
            value.get("effect_timeout_contract_valid") is True
            and 0.0
            < float(value.get("model_provider_effect_timeout_seconds", -1.0))
            <= MAXIMUM_PROVIDER_EFFECT_SECONDS
            and float(value.get("model_provider_effect_timeout_seconds", -1.0))
            == float(value.get("hosted_search_effect_timeout_seconds", -2.0))
        ),
        "narrative_effect_equivalence_attested": all(
            value.get(name) is True
            for name in (
                "narrative_effect_equivalence_valid",
                "narrative_model_remaining_seconds_nonincreasing",
                "narrative_model_deadline_state_monotonic",
                "narrative_transport_deadline_state_monotonic",
            )
        ),
    }
    if tuple(checks) != TASK_CHECK_NAMES:
        raise RuntimeError("V2.44.40 task check order drifted")
    return checks


def task_projection(
    ordinal: int,
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        raise ValueError("V2.44.40 successful parent is missing its envelope")
    wrapped = validate_narrative_envelope(envelope)
    legacy = base.task_projection(ordinal, parent, wrapped["parent_envelope"])
    legacy.pop("checks")
    legacy.pop("passed")
    receipt = wrapped["narrative_title_result"]["narrative_recovery_receipt"]
    contract = validate_effect_timeout_contract(wrapped["effect_timeout_contract"])
    equivalence = validate_effect_equivalence_receipt(
        wrapped["effect_equivalence_receipt"]
    )
    value = {
        **legacy,
        "narrative_page_target_pair_count": int(
            receipt["narrative_page_target_pair_count"]
        ),
        **{
            field: int(receipt["narrative_reason_counts"][reason])
            for reason, field in REASON_TASK_FIELDS.items()
        },
        "narrative_projection_count": int(receipt["narrative_projection_count"]),
        "narrative_novel_observation_count": int(
            receipt["novel_narrative_observation_count"]
        ),
        "narrative_combined_observation_count": int(
            receipt["combined_narrative_observation_count"]
        ),
        "narrative_safe_change_count": int(
            receipt["narrative_recovered_safe_change_count"]
        ),
        "narrative_baseline_confirmed_count": int(
            receipt["narrative_recovered_baseline_confirmed_count"]
        ),
        "narrative_unresolved_count": int(
            receipt["narrative_recovered_unresolved_count"]
        ),
        "narrative_positive_epistemic_target_count": int(
            receipt["narrative_recovered_positive_epistemic_target_count"]
        ),
        "narrative_source_credit_record_count": int(
            receipt["narrative_recovered_source_credit_record_count"]
        ),
        "narrative_candidate_changed_cell_count": int(
            receipt["narrative_candidate_changed_cell_count"]
        ),
        "narrative_pre_active_entropy_total_nats": float(
            receipt["narrative_recovered_pre_active_entropy_total_nats"]
        ),
        "narrative_combined_entropy_total_nats": float(
            receipt["narrative_recovered_combined_entropy_total_nats"]
        ),
        "narrative_positive_information_gain_total_nats": float(
            receipt["narrative_recovered_positive_information_gain_total_nats"]
        ),
        "narrative_bayesian_surprise_total_nats": float(
            receipt["narrative_recovered_bayesian_surprise_total_nats"]
        ),
        "narrative_epistemic_credit_total_nats": float(
            receipt["narrative_recovered_epistemic_credit_total_nats"]
        ),
        "narrative_decision_credit_total_nats": float(
            receipt["narrative_recovered_decision_credit_total_nats"]
        ),
        "model_provider_effect_timeout_seconds": float(
            contract["model_provider_timeout_seconds"]
        ),
        "hosted_search_effect_timeout_seconds": float(
            contract["hosted_search_timeout_seconds"]
        ),
        "narrative_recovery_changed_parent_output": bool(
            receipt["narrative_recovery_changed_parent_output"]
        ),
        "narrative_projection_private_replay_valid": bool(
            receipt["narrative_projection_private_replay_valid"]
        ),
        "narrative_parent_title_projection_preserved": bool(
            receipt["parent_title_projection_preserved_exactly"]
        ),
        "narrative_reason_partition_exact": bool(
            receipt["narrative_reason_partition_exact"]
        ),
        "effect_timeout_contract_valid": True,
        "narrative_effect_equivalence_valid": True,
        "narrative_model_remaining_seconds_nonincreasing": equivalence[
            "model_remaining_seconds_nonincreasing"
        ],
        "narrative_model_deadline_state_monotonic": equivalence[
            "model_deadline_state_monotonic"
        ],
        "narrative_transport_deadline_state_monotonic": equivalence[
            "transport_deadline_state_monotonic"
        ],
    }
    value["checks"] = task_checks(value)
    value["passed"] = all(value["checks"].values())
    validate_task_projection(value)
    return value


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    checks = value.get("checks")
    base.validate_task_projection(_base_task_view(value))
    if (
        set(value) != TASK_KEYS
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in NARRATIVE_COUNT_FIELDS
        )
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in NARRATIVE_NUMERIC_FIELDS
        )
        or any(
            not isinstance(value.get(name), bool)
            for name in NARRATIVE_BOOLEAN_FIELDS
        )
        or not isinstance(checks, Mapping)
        or tuple(checks) != TASK_CHECK_NAMES
        or dict(checks) != task_checks(value)
        or value.get("passed") is not all(checks.values())
    ):
        raise RuntimeError("V2.44.40 task projection drifted")
    return copy.deepcopy(dict(value))


def local_failure(ordinal: int) -> dict[str, Any]:
    legacy = base.local_failure(ordinal)
    legacy.pop("checks")
    legacy.pop("passed")
    value = {
        **legacy,
        **{name: 0 for name in NARRATIVE_COUNT_FIELDS},
        **{name: 0.0 for name in NARRATIVE_NUMERIC_FIELDS},
        **{name: False for name in NARRATIVE_BOOLEAN_FIELDS},
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
        "narrative_observation_tasks": summary["narrative_novel_observation_tasks"]
        >= gates["minimum_narrative_novel_observation_tasks"],
        "narrative_positive_epistemic_tasks": summary[
            "narrative_positive_epistemic_tasks"
        ]
        >= gates["minimum_narrative_positive_epistemic_tasks"],
        "narrative_safe_change_tasks": summary["narrative_safe_change_tasks"]
        >= gates["minimum_narrative_safe_change_tasks"],
        "narrative_positive_decision_credit": summary[
            "narrative_decision_credit_total_nats"
        ]
        >= gates["minimum_narrative_decision_credit_nats"],
        "narrative_credit_consistency": (
            0.0
            <= summary["narrative_decision_credit_total_nats"]
            <= summary["narrative_epistemic_credit_total_nats"] + 1e-12
            and (
                summary["narrative_decision_credit_total_nats"] == 0
                or summary["narrative_safe_change_count"] > 0
            )
            and sum(
                summary[AGGREGATE_REASON_FIELDS[reason]] for reason in REASONS
            )
            == summary["narrative_total_page_target_pairs"]
        ),
        "provider_effect_cap_attested": (
            summary["all_effect_timeout_contracts_valid"] is True
            and 0.0
            < summary[
                "maximum_observed_model_provider_effect_timeout_seconds"
            ]
            <= MAXIMUM_PROVIDER_EFFECT_SECONDS
            and summary[
                "maximum_observed_model_provider_effect_timeout_seconds"
            ]
            == summary[
                "maximum_observed_hosted_search_effect_timeout_seconds"
            ]
        ),
        "all_narrative_effect_equivalence_attested": (
            summary["narrative_effect_equivalent_tasks"] == summary["selected"]
            and summary["all_narrative_projection_private_replay_valid"] is True
            and summary["all_narrative_parent_title_projections_preserved"] is True
            and summary["all_narrative_reason_partitions_exact"] is True
            and summary["all_narrative_effect_equivalence_attested"] is True
            and summary[
                "all_narrative_model_remaining_seconds_nonincreasing"
            ]
            is True
            and summary["all_narrative_model_deadline_states_monotonic"] is True
            and summary["all_narrative_transport_deadline_states_monotonic"]
            is True
        ),
    }
    if tuple(checks) != AGGREGATE_CHECK_NAMES:
        raise RuntimeError("V2.44.40 aggregate check order drifted")
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
        "narrative_projection_tasks": sum(
            item["narrative_projection_count"] > 0 for item in values
        ),
        "narrative_novel_observation_tasks": sum(
            item["narrative_novel_observation_count"] > 0 for item in values
        ),
        "narrative_positive_epistemic_tasks": sum(
            item["narrative_epistemic_credit_total_nats"] > 0 for item in values
        ),
        "narrative_safe_change_tasks": sum(
            item["narrative_safe_change_count"] > 0 for item in values
        ),
        "narrative_decision_credit_tasks": sum(
            item["narrative_decision_credit_total_nats"] > 0 for item in values
        ),
        "narrative_effect_equivalent_tasks": sum(
            item["narrative_effect_equivalence_valid"] for item in values
        ),
        "narrative_total_page_target_pairs": sum(
            item["narrative_page_target_pair_count"] for item in values
        ),
        **{
            aggregate: sum(item[task] for item in values)
            for reason, task in REASON_TASK_FIELDS.items()
            for aggregate in (AGGREGATE_REASON_FIELDS[reason],)
        },
        "narrative_projections": sum(
            item["narrative_projection_count"] for item in values
        ),
        "narrative_novel_observations": sum(
            item["narrative_novel_observation_count"] for item in values
        ),
        "narrative_combined_observations": sum(
            item["narrative_combined_observation_count"] for item in values
        ),
        "narrative_safe_change_count": sum(
            item["narrative_safe_change_count"] for item in values
        ),
        "narrative_baseline_confirmed_count": sum(
            item["narrative_baseline_confirmed_count"] for item in values
        ),
        "narrative_unresolved_count": sum(
            item["narrative_unresolved_count"] for item in values
        ),
        "narrative_positive_epistemic_target_count": sum(
            item["narrative_positive_epistemic_target_count"] for item in values
        ),
        "narrative_source_credit_record_count": sum(
            item["narrative_source_credit_record_count"] for item in values
        ),
        "narrative_candidate_changed_cell_count": sum(
            item["narrative_candidate_changed_cell_count"] for item in values
        ),
        "all_narrative_projection_private_replay_valid": all(
            item["narrative_projection_private_replay_valid"] for item in values
        ),
        "all_narrative_parent_title_projections_preserved": all(
            item["narrative_parent_title_projection_preserved"] for item in values
        ),
        "all_narrative_reason_partitions_exact": all(
            item["narrative_reason_partition_exact"] for item in values
        ),
        "all_effect_timeout_contracts_valid": all(
            item["effect_timeout_contract_valid"] for item in values
        ),
        "all_narrative_effect_equivalence_attested": all(
            item["checks"]["narrative_effect_equivalence_attested"]
            for item in values
        ),
        "all_narrative_model_remaining_seconds_nonincreasing": all(
            item["narrative_model_remaining_seconds_nonincreasing"]
            for item in values
        ),
        "all_narrative_model_deadline_states_monotonic": all(
            item["narrative_model_deadline_state_monotonic"] for item in values
        ),
        "all_narrative_transport_deadline_states_monotonic": all(
            item["narrative_transport_deadline_state_monotonic"]
            for item in values
        ),
    }
    for name in NARRATIVE_NUMERIC_FIELDS[:6]:
        aggregate_name = name
        summary[aggregate_name] = round(
            sum(float(item[name]) for item in values), 12
        )
    summary["maximum_observed_model_provider_effect_timeout_seconds"] = max(
        (float(item["model_provider_effect_timeout_seconds"]) for item in values),
        default=0.0,
    )
    summary["maximum_observed_hosted_search_effect_timeout_seconds"] = max(
        (float(item["hosted_search_effect_timeout_seconds"]) for item in values),
        default=0.0,
    )
    summary["checks"] = aggregate_checks(summary, gates)
    summary["passed"] = all(summary["checks"].values())
    validate_aggregate(summary, gates)
    return summary


def validate_aggregate(
    value: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, Any]:
    checks = value.get("checks")
    base.validate_aggregate(_base_aggregate_view(value, gates), gates)
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
        raise RuntimeError("V2.44.40 aggregate drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "AGGREGATE_KEYS",
    "REASON_TASK_FIELDS",
    "TASK_KEYS",
    "aggregate_checks",
    "aggregate_tasks",
    "local_failure",
    "task_checks",
    "task_projection",
    "validate_aggregate",
    "validate_task_projection",
]
