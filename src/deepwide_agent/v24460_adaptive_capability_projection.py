"""Minimal capability-only projection for V2.44.59 adaptive support.

The public surface is deliberately limited to stop, threshold, effect, and
entropy/decision-credit counts.  It contains no lead/page fields or hashes.
Only the opaque capability minted by the proof validator is accepted.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from .v24447_third_source_entropy_to_decision import THRESHOLD_PARTITION_FIELDS
from .v24457_adaptive_entropy_support import (
    MAXIMUM_ACTIVE_SOURCES,
    MAXIMUM_ADDITIONAL_FETCHES,
    MAXIMUM_TOTAL_FETCHES,
)
from .v24459_proof_carrying_adaptive_entropy_support import (
    ValidatedProofCarryingAdaptiveEnvelope,
)


POLICY_ID = "v24460_adaptive_capability_counts_projection_v1"
PUBLIC_STOP_REASONS = frozenset(
    {"safe_decision", "support_unreachable", "pool_exhausted", "budget_exhausted"}
)
PUBLIC_STOP_BY_PRIVATE = {
    "safe_decision": "safe_decision",
    "support_unreachable": "support_unreachable",
    "lead_pool_exhausted": "pool_exhausted",
    "budget_exhausted": "budget_exhausted",
}
THRESHOLD_FIELDS = {
    name: f"adaptive_{name}" for name in THRESHOLD_PARTITION_FIELDS
}
COUNT_FIELDS = (
    "adaptive_selected_target_count",
    *THRESHOLD_FIELDS.values(),
    "adaptive_baseline_confirmed_count",
    "adaptive_unresolved_count",
    "adaptive_positive_epistemic_target_count",
    "adaptive_credit_record_count",
    "adaptive_candidate_changed_cell_count",
    "adaptive_known_baseline_minimum_support_sources",
    "adaptive_unknown_baseline_minimum_support_sources",
    "adaptive_required_support_margin",
    "adaptive_active_source_cap",
    "adaptive_parent_total_fetch_cap",
    "adaptive_maximum_additional_fetches",
    "adaptive_additional_fetch_calls",
    "adaptive_total_fetch_cap",
    "adaptive_additional_model_requests",
    "adaptive_additional_logical_queries",
    "adaptive_additional_search_batches",
    "adaptive_additional_provider_search_calls",
    "adaptive_additional_model_acquisitions",
    "adaptive_additional_model_attempts",
    "adaptive_additional_hosted_search_attempts",
    "adaptive_additional_hosted_search_deadline_failures",
    "adaptive_additional_hard_fetch_helper_calls",
    "adaptive_additional_fetch_deadline_rejections",
    "adaptive_additional_hard_fetch_deadline_failures",
    "adaptive_additional_fetch_helper_failures",
    "adaptive_additional_fetch_effects",
)
NUMERIC_FIELDS = (
    "adaptive_acquisition_credit_total_nats",
    "adaptive_pre_active_entropy_total_nats",
    "adaptive_final_combined_entropy_total_nats",
    "adaptive_final_positive_information_gain_total_nats",
    "adaptive_final_epistemic_credit_total_nats",
    "adaptive_final_decision_credit_total_nats",
    "adaptive_minimum_alternative_posterior",
)
BOOLEAN_FIELDS = (
    "adaptive_threshold_partition_exact",
    "adaptive_stop_replayed_exactly",
    "adaptive_safe_change_thresholds_preserved",
    "adaptive_final_credit_is_leave_one_out_information_gain",
    "adaptive_decision_credit_requires_safe_output_change",
    "adaptive_credit_not_used_for_same_run_routing_or_training",
    "adaptive_effect_policy_attested",
    "adaptive_complete_envelope_validated_once",
    "adaptive_projection_consumed_only_validated_capability",
)
CHECK_NAMES = (
    "threshold_partition",
    "stop_and_support",
    "entropy_decision_credit",
    "effect_conservation",
    "single_validation",
)
TASK_KEYS = frozenset(
    {
        "ordinal",
        "adaptive_stop_reason",
        "checks",
        "passed",
        *COUNT_FIELDS,
        *NUMERIC_FIELDS,
        *BOOLEAN_FIELDS,
    }
)
AGGREGATE_COUNT_INPUTS = (
    "adaptive_safe_change_count",
    "adaptive_candidate_changed_cell_count",
    "adaptive_additional_fetch_calls",
    "adaptive_additional_fetch_effects",
    "adaptive_additional_hard_fetch_deadline_failures",
    "adaptive_additional_fetch_helper_failures",
)
AGGREGATE_NUMERIC_INPUTS = (
    "adaptive_acquisition_credit_total_nats",
    "adaptive_final_positive_information_gain_total_nats",
    "adaptive_final_epistemic_credit_total_nats",
    "adaptive_final_decision_credit_total_nats",
)
AGGREGATE_KEYS = frozenset(
    {
        "selected",
        "exact_ordinal_vector",
        "passed_tasks",
        "failed_tasks",
        "stop_reason_counts",
        "all_threshold_partitions_exact",
        "all_effects_conserved",
        "all_single_validation_attested",
        "all_projections_consumed_validated_capabilities",
        "private_task_content_emitted",
        "privileged_evaluator_content_read",
        *(f"total_{name}" for name in AGGREGATE_COUNT_INPUTS),
        *(f"total_{name}" for name in AGGREGATE_NUMERIC_INPUTS),
    }
)


def _count(value: Mapping[str, Any], name: str) -> int:
    item = value.get(name)
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        raise ValueError(f"V2.44.60 invalid count: {name}")
    return item


def _number(value: Mapping[str, Any], name: str) -> float:
    item = value.get(name)
    if (
        isinstance(item, bool)
        or not isinstance(item, (int, float))
        or not math.isfinite(float(item))
        or float(item) < 0
    ):
        raise ValueError(f"V2.44.60 invalid numeric field: {name}")
    return float(item)


def task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    selected = int(value.get("adaptive_selected_target_count", -1))
    safe = int(value.get("adaptive_safe_change_count", -1))
    confirmed = int(value.get("adaptive_baseline_confirmed_count", -1))
    unresolved = int(value.get("adaptive_unresolved_count", -1))
    effects = int(value.get("adaptive_additional_fetch_effects", -1))
    calls = int(value.get("adaptive_additional_fetch_calls", -1))
    partition_total = sum(
        int(value.get(field, -1)) for field in THRESHOLD_FIELDS.values()
    )
    checks = {
        "threshold_partition": (
            value.get("adaptive_threshold_partition_exact") is True
            and partition_total == selected
            and safe == value.get(THRESHOLD_FIELDS["safe_change_count"])
            and safe + confirmed + unresolved == selected
        ),
        "stop_and_support": (
            value.get("adaptive_stop_reason") in PUBLIC_STOP_REASONS
            and calls <= MAXIMUM_ADDITIONAL_FETCHES
            and value.get("adaptive_maximum_additional_fetches")
            == MAXIMUM_ADDITIONAL_FETCHES
            and value.get("adaptive_total_fetch_cap") == MAXIMUM_TOTAL_FETCHES
            and value.get("adaptive_active_source_cap") == MAXIMUM_ACTIVE_SOURCES
            and (value.get("adaptive_stop_reason") == "safe_decision") is (safe > 0)
            and value.get("adaptive_stop_replayed_exactly") is True
        ),
        "entropy_decision_credit": (
            0.0
            <= float(value.get("adaptive_final_decision_credit_total_nats", -1.0))
            <= float(value.get("adaptive_final_epistemic_credit_total_nats", -1.0))
            + 1e-12
            <= float(
                value.get(
                    "adaptive_final_positive_information_gain_total_nats", -1.0
                )
            )
            + 1e-12
            and (
                float(value.get("adaptive_final_decision_credit_total_nats", 0.0))
                == 0.0
                or safe > 0
            )
            and value.get("adaptive_final_credit_is_leave_one_out_information_gain")
            is True
            and value.get("adaptive_decision_credit_requires_safe_output_change")
            is True
            and value.get(
                "adaptive_credit_not_used_for_same_run_routing_or_training"
            )
            is True
        ),
        "effect_conservation": (
            effects == calls
            and effects
            == value.get("adaptive_additional_hard_fetch_helper_calls")
            + value.get("adaptive_additional_fetch_deadline_rejections")
            and all(
                value.get(name) == 0
                for name in (
                    "adaptive_additional_model_requests",
                    "adaptive_additional_logical_queries",
                    "adaptive_additional_search_batches",
                    "adaptive_additional_provider_search_calls",
                    "adaptive_additional_model_acquisitions",
                    "adaptive_additional_model_attempts",
                    "adaptive_additional_hosted_search_attempts",
                    "adaptive_additional_hosted_search_deadline_failures",
                )
            )
            and value.get("adaptive_effect_policy_attested") is True
        ),
        "single_validation": (
            value.get("adaptive_complete_envelope_validated_once") is True
            and value.get(
                "adaptive_projection_consumed_only_validated_capability"
            )
            is True
        ),
    }
    if tuple(checks) != CHECK_NAMES:
        raise RuntimeError("V2.44.60 check order drifted")
    return checks


def task_projection(
    ordinal: int,
    validated: ValidatedProofCarryingAdaptiveEnvelope,
) -> dict[str, Any]:
    if not isinstance(validated, ValidatedProofCarryingAdaptiveEnvelope):
        raise TypeError("V2.44.60 requires a V2.44.59 validated capability")
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.44.60 ordinal is invalid")
    receipts = validated.counts_only_receipts()
    receipt = receipts["adaptive_support_receipt"]
    effect = receipts["effect_delta_receipt"]
    partition = receipt["threshold_failure_partition"]
    value = {
        "ordinal": ordinal,
        "adaptive_stop_reason": PUBLIC_STOP_BY_PRIVATE[str(receipt["stop_reason"])],
        "adaptive_selected_target_count": int(receipt["selected_target_count"]),
        **{
            field: int(partition[name])
            for name, field in THRESHOLD_FIELDS.items()
        },
        "adaptive_baseline_confirmed_count": int(
            receipt["baseline_confirmed_count"]
        ),
        "adaptive_unresolved_count": int(receipt["unresolved_count"]),
        "adaptive_positive_epistemic_target_count": int(
            receipt["positive_epistemic_target_count"]
        ),
        "adaptive_credit_record_count": int(receipt["source_credit_record_count"]),
        "adaptive_candidate_changed_cell_count": int(
            receipt["candidate_changed_cell_count"]
        ),
        "adaptive_known_baseline_minimum_support_sources": int(
            receipt["known_baseline_minimum_support_sources"]
        ),
        "adaptive_unknown_baseline_minimum_support_sources": int(
            receipt["unknown_baseline_minimum_support_sources"]
        ),
        "adaptive_required_support_margin": int(receipt["required_support_margin"]),
        "adaptive_active_source_cap": int(receipt["active_source_cap"]),
        "adaptive_parent_total_fetch_cap": int(receipt["parent_total_fetch_cap"]),
        "adaptive_maximum_additional_fetches": int(
            receipt["maximum_additional_fetches"]
        ),
        "adaptive_additional_fetch_calls": int(receipt["additional_fetch_calls"]),
        "adaptive_total_fetch_cap": int(receipt["total_fetch_cap"]),
        "adaptive_additional_model_requests": int(
            receipt["additional_model_requests"]
        ),
        "adaptive_additional_logical_queries": int(
            receipt["additional_logical_queries"]
        ),
        "adaptive_additional_search_batches": int(
            receipt["additional_search_batches"]
        ),
        "adaptive_additional_provider_search_calls": int(
            receipt["additional_provider_search_calls"]
        ),
        "adaptive_additional_model_acquisitions": int(
            effect["additional_model_acquisitions"]
        ),
        "adaptive_additional_model_attempts": int(
            effect["additional_model_attempts"]
        ),
        "adaptive_additional_hosted_search_attempts": int(
            effect["additional_hosted_search_attempts"]
        ),
        "adaptive_additional_hosted_search_deadline_failures": int(
            effect["additional_hosted_search_deadline_failures"]
        ),
        "adaptive_additional_hard_fetch_helper_calls": int(
            effect["additional_hard_fetch_helper_calls"]
        ),
        "adaptive_additional_fetch_deadline_rejections": int(
            effect["additional_fetch_deadline_rejections"]
        ),
        "adaptive_additional_hard_fetch_deadline_failures": int(
            effect["additional_hard_fetch_deadline_failures"]
        ),
        "adaptive_additional_fetch_helper_failures": int(
            effect["additional_fetch_helper_failures"]
        ),
        "adaptive_additional_fetch_effects": int(effect["additional_fetch_effects"]),
        "adaptive_acquisition_credit_total_nats": float(
            receipt["adaptive_acquisition_credit_total_nats"]
        ),
        "adaptive_pre_active_entropy_total_nats": float(
            receipt["pre_active_entropy_total_nats"]
        ),
        "adaptive_final_combined_entropy_total_nats": float(
            receipt["final_combined_entropy_total_nats"]
        ),
        "adaptive_final_positive_information_gain_total_nats": float(
            receipt["final_positive_information_gain_total_nats"]
        ),
        "adaptive_final_epistemic_credit_total_nats": float(
            receipt["final_epistemic_credit_total_nats"]
        ),
        "adaptive_final_decision_credit_total_nats": float(
            receipt["final_decision_credit_total_nats"]
        ),
        "adaptive_minimum_alternative_posterior": float(
            receipt["minimum_alternative_posterior"]
        ),
        "adaptive_threshold_partition_exact": (
            sum(int(partition[name]) for name in THRESHOLD_PARTITION_FIELDS)
            == int(receipt["selected_target_count"])
        ),
        "adaptive_stop_replayed_exactly": bool(
            receipt["adaptive_stop_replayed_exactly"]
        ),
        "adaptive_safe_change_thresholds_preserved": bool(
            receipt["safe_change_thresholds_preserved"]
        ),
        "adaptive_final_credit_is_leave_one_out_information_gain": bool(
            receipt[
                "final_source_credit_uses_normalized_leave_one_out_information_gain"
            ]
        ),
        "adaptive_decision_credit_requires_safe_output_change": bool(
            receipt["decision_credit_requires_safe_output_change"]
        ),
        "adaptive_credit_not_used_for_same_run_routing_or_training": not bool(
            receipt["allocated_credit_used_for_same_run_routing_or_training"]
        ),
        "adaptive_effect_policy_attested": all(
            effect[name] is True
            for name in (
                "model_effect_and_static_fields_equal",
                "model_remaining_seconds_nonincreasing",
                "model_deadline_state_monotonic",
                "search_shape_fields_equal",
                "transport_deadline_state_monotonic",
                "only_frozen_source_disjoint_page_fetch_effects_allowed",
            )
        ),
        "adaptive_complete_envelope_validated_once": True,
        "adaptive_projection_consumed_only_validated_capability": True,
    }
    value["checks"] = task_checks(value)
    value["passed"] = all(value["checks"].values())
    return validate_task_projection(value)


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    checks = copied.get("checks")
    if (
        set(copied) != TASK_KEYS
        or isinstance(copied.get("ordinal"), bool)
        or not isinstance(copied.get("ordinal"), int)
        or copied["ordinal"] < 1
        or copied.get("adaptive_stop_reason") not in PUBLIC_STOP_REASONS
        or any(_count(copied, name) < 0 for name in COUNT_FIELDS)
        or any(_number(copied, name) < 0 for name in NUMERIC_FIELDS)
        or any(not isinstance(copied.get(name), bool) for name in BOOLEAN_FIELDS)
        or not isinstance(checks, Mapping)
        or tuple(checks) != CHECK_NAMES
        or dict(checks) != task_checks(copied)
        or copied.get("passed") is not all(checks.values())
    ):
        raise ValueError("V2.44.60 task projection drifted")
    return copy.deepcopy(copied)


def local_failure(ordinal: int) -> dict[str, Any]:
    if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 1:
        raise ValueError("V2.44.60 ordinal is invalid")
    value = {
        "ordinal": ordinal,
        "adaptive_stop_reason": "pool_exhausted",
        **{name: 0 for name in COUNT_FIELDS},
        **{name: 0.0 for name in NUMERIC_FIELDS},
        **{name: False for name in BOOLEAN_FIELDS},
    }
    value["checks"] = task_checks(value)
    value["passed"] = False
    return validate_task_projection(value)


def aggregate_projections(
    projections: Sequence[Mapping[str, Any]], *, selected: int
) -> dict[str, Any]:
    values = sorted(
        (validate_task_projection(item) for item in projections),
        key=lambda item: item["ordinal"],
    )
    if (
        isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or len(values) != selected
        or [item["ordinal"] for item in values] != list(range(1, selected + 1))
    ):
        raise ValueError("V2.44.60 aggregate selection drifted")
    stop_counts = {name: 0 for name in sorted(PUBLIC_STOP_REASONS)}
    for item in values:
        stop_counts[str(item["adaptive_stop_reason"])] += 1
    passed = sum(bool(item["passed"]) for item in values)
    value = {
        "selected": selected,
        "exact_ordinal_vector": True,
        "passed_tasks": passed,
        "failed_tasks": selected - passed,
        "stop_reason_counts": stop_counts,
        "all_threshold_partitions_exact": all(
            item["adaptive_threshold_partition_exact"] for item in values
        ),
        "all_effects_conserved": all(
            item["checks"]["effect_conservation"] for item in values
        ),
        "all_single_validation_attested": all(
            item["adaptive_complete_envelope_validated_once"] for item in values
        ),
        "all_projections_consumed_validated_capabilities": all(
            item["adaptive_projection_consumed_only_validated_capability"]
            for item in values
        ),
        **{
            f"total_{name}": sum(int(item[name]) for item in values)
            for name in AGGREGATE_COUNT_INPUTS
        },
        **{
            f"total_{name}": round(
                sum(float(item[name]) for item in values), 12
            )
            for name in AGGREGATE_NUMERIC_INPUTS
        },
        "private_task_content_emitted": False,
        "privileged_evaluator_content_read": False,
    }
    return validate_aggregate(value)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    selected = copied.get("selected")
    stop_counts = copied.get("stop_reason_counts")
    integer_fields = (
        "passed_tasks",
        "failed_tasks",
        *(f"total_{name}" for name in AGGREGATE_COUNT_INPUTS),
    )
    numeric_fields = tuple(
        f"total_{name}" for name in AGGREGATE_NUMERIC_INPUTS
    )
    if (
        set(copied) != AGGREGATE_KEYS
        or isinstance(selected, bool)
        or not isinstance(selected, int)
        or selected < 1
        or copied.get("exact_ordinal_vector") is not True
        or any(_count(copied, name) < 0 for name in integer_fields)
        or any(_number(copied, name) < 0 for name in numeric_fields)
        or copied["passed_tasks"] + copied["failed_tasks"] != selected
        or not isinstance(stop_counts, Mapping)
        or set(stop_counts) != PUBLIC_STOP_REASONS
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in stop_counts.values()
        )
        or sum(stop_counts.values()) != selected
        or any(
            not isinstance(copied.get(name), bool)
            for name in (
                "all_threshold_partitions_exact",
                "all_effects_conserved",
                "all_single_validation_attested",
                "all_projections_consumed_validated_capabilities",
            )
        )
        or copied.get("private_task_content_emitted") is not False
        or copied.get("privileged_evaluator_content_read") is not False
    ):
        raise ValueError("V2.44.60 aggregate projection drifted")
    return copy.deepcopy(copied)


__all__ = [
    "POLICY_ID",
    "aggregate_projections",
    "local_failure",
    "task_projection",
    "validate_aggregate",
    "validate_task_projection",
]
