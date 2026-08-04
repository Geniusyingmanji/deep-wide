#!/usr/bin/env python3
"""Counts-only projection for one completely validated V2.44.47 envelope.

The public projector accepts only the opaque capability returned by V2.44.48.
It therefore cannot trigger a second private replay or accidentally project an
unvalidated JSON mapping.  It emits only the mutually exclusive
threshold-failure partition, bounded third-source effects, and
entropy-to-decision counts.  No task text, opaque
identifier, query, URL, page, source, value, prediction, candidate, content
hash, benchmark label, gold answer, evaluator state, reward, or score is
emitted.
"""

from __future__ import annotations

import copy
import math
from collections.abc import Mapping, Sequence
from typing import Any

from deepwide_agent.v24447_third_source_entropy_to_decision import (
    MAXIMUM_ACTIVE_SOURCES,
    MAXIMUM_TOTAL_FETCHES,
    THRESHOLD_PARTITION_FIELDS,
)
from deepwide_agent.v24448_serialized_third_source_envelope import (
    ValidatedSerializedThirdSourceEnvelope,
)


THRESHOLD_TASK_FIELDS = {
    name: f"third_source_{name}" for name in THRESHOLD_PARTITION_FIELDS
}
THRESHOLD_AGGREGATE_FIELDS = {
    name: f"third_source_total_{name}" for name in THRESHOLD_PARTITION_FIELDS
}
THIRD_COUNT_FIELDS = (
    "third_source_selected_target_count",
    "third_source_frozen_active_lead_count",
    "third_source_parent_selected_active_source_count",
    "third_source_candidate_count",
    "third_source_fetch_attempt_count",
    "third_source_usable_page_count",
    "third_source_parent_active_page_count",
    "third_source_extended_active_page_count",
    "third_source_extended_narrative_projection_count",
    "third_source_extended_novel_observation_count",
    *THRESHOLD_TASK_FIELDS.values(),
    "third_source_baseline_confirmed_count",
    "third_source_unresolved_count",
    "third_source_positive_epistemic_target_count",
    "third_source_credit_record_count",
    "third_source_parent_candidate_changed_cell_count",
    "third_source_candidate_changed_cell_count",
    "third_source_known_baseline_minimum_support_sources",
    "third_source_unknown_baseline_minimum_support_sources",
    "third_source_required_support_margin",
    "third_source_active_source_cap",
    "third_source_parent_total_fetch_cap",
    "third_source_additional_model_requests",
    "third_source_additional_logical_queries",
    "third_source_additional_search_batches",
    "third_source_additional_provider_search_calls",
    "third_source_additional_fetch_calls",
    "third_source_total_fetch_cap",
    "third_source_additional_model_acquisitions",
    "third_source_additional_model_attempts",
    "third_source_additional_hosted_search_attempts",
    "third_source_additional_hosted_search_deadline_failures",
    "third_source_additional_hard_fetch_helper_calls",
    "third_source_additional_fetch_deadline_rejections",
    "third_source_additional_hard_fetch_deadline_failures",
    "third_source_additional_fetch_helper_failures",
    "third_source_additional_fetch_effects",
)
THIRD_NUMERIC_FIELDS = (
    "third_source_pre_active_entropy_total_nats",
    "third_source_combined_entropy_total_nats",
    "third_source_positive_information_gain_total_nats",
    "third_source_epistemic_credit_total_nats",
    "third_source_decision_credit_total_nats",
    "third_source_parent_epistemic_credit_total_nats",
    "third_source_parent_decision_credit_total_nats",
    "third_source_minimum_alternative_posterior",
)
THIRD_BOOLEAN_FIELDS = (
    "third_source_threshold_partition_exact",
    "third_source_frozen_active_lead_ranking_reused",
    "third_source_proposal_and_existing_active_sources_excluded",
    "third_source_parent_narrative_projection_replayed_exactly",
    "third_source_safe_change_thresholds_preserved",
    "third_source_posterior_and_credit_recomputed_without_model_or_search",
    "third_source_model_effect_and_static_fields_equal",
    "third_source_model_remaining_seconds_nonincreasing",
    "third_source_model_deadline_state_monotonic",
    "third_source_search_shape_fields_equal",
    "third_source_transport_deadline_state_monotonic",
    "third_source_only_one_public_page_fetch_effect_allowed",
    "third_source_complete_envelope_validated_once",
    "third_source_projection_consumed_only_validated_capability",
)
TASK_CHECK_NAMES = (
    "third_source_threshold_partition_attested",
    "third_source_page_and_fetch_conservation",
    "third_source_entropy_credit_conservation",
    "third_source_effect_conservation",
    "third_source_single_validation_attested",
)
TASK_KEYS = frozenset(
    {
        "ordinal",
        "checks",
        "passed",
        *THIRD_COUNT_FIELDS,
        *THIRD_NUMERIC_FIELDS,
        *THIRD_BOOLEAN_FIELDS,
    }
)

AGGREGATE_COUNT_FIELDS = (
    "third_source_candidate_tasks",
    "third_source_fetch_attempt_tasks",
    "third_source_usable_page_tasks",
    "third_source_safe_change_tasks",
    "third_source_decision_credit_tasks",
    "third_source_effect_conserved_tasks",
    "third_source_validated_once_tasks",
    "third_source_total_selected_targets",
    "third_source_total_candidates",
    "third_source_total_fetch_attempts",
    "third_source_total_usable_pages",
    "third_source_total_extended_active_pages",
    "third_source_total_extended_narrative_projections",
    "third_source_total_extended_novel_observations",
    *THRESHOLD_AGGREGATE_FIELDS.values(),
    "third_source_total_baseline_confirmed",
    "third_source_total_unresolved",
    "third_source_total_positive_epistemic_targets",
    "third_source_total_credit_records",
    "third_source_total_parent_candidate_changed_cells",
    "third_source_total_candidate_changed_cells",
    "third_source_total_additional_fetch_effects",
    "third_source_total_additional_hard_fetch_deadline_failures",
    "third_source_total_additional_fetch_helper_failures",
)
AGGREGATE_NUMERIC_FIELDS = (
    "third_source_pre_active_entropy_total_nats",
    "third_source_combined_entropy_total_nats",
    "third_source_positive_information_gain_total_nats",
    "third_source_epistemic_credit_total_nats",
    "third_source_decision_credit_total_nats",
    "third_source_parent_epistemic_credit_total_nats",
    "third_source_parent_decision_credit_total_nats",
)
AGGREGATE_BOOLEAN_FIELDS = (
    "all_third_source_threshold_partitions_exact",
    "all_third_source_effects_conserved",
    "all_third_source_source_policies_attested",
    "all_third_source_envelopes_validated_once",
    "all_third_source_projections_consumed_validated_capabilities",
)
AGGREGATE_CHECK_NAMES = (
    "third_source_safe_change_tasks",
    "third_source_positive_decision_credit",
    "third_source_threshold_partition_attested",
    "third_source_effect_conservation",
    "all_third_source_single_validation_attested",
)
AGGREGATE_KEYS = frozenset(
    {
        "selected",
        "exact_ordinal_vector",
        "checks",
        "passed",
        *AGGREGATE_COUNT_FIELDS,
        *AGGREGATE_NUMERIC_FIELDS,
        *AGGREGATE_BOOLEAN_FIELDS,
    }
)

def _threshold_total(value: Mapping[str, Any]) -> int:
    return sum(int(value.get(field, -1)) for field in THRESHOLD_TASK_FIELDS.values())


def _source_policy_attested(value: Mapping[str, Any]) -> bool:
    return all(
        value.get(name) is True
        for name in (
            "third_source_frozen_active_lead_ranking_reused",
            "third_source_proposal_and_existing_active_sources_excluded",
            "third_source_parent_narrative_projection_replayed_exactly",
            "third_source_safe_change_thresholds_preserved",
            "third_source_posterior_and_credit_recomputed_without_model_or_search",
        )
    )


def _effect_attested(value: Mapping[str, Any]) -> bool:
    return all(
        value.get(name) is True
        for name in (
            "third_source_model_effect_and_static_fields_equal",
            "third_source_model_remaining_seconds_nonincreasing",
            "third_source_model_deadline_state_monotonic",
            "third_source_search_shape_fields_equal",
            "third_source_transport_deadline_state_monotonic",
            "third_source_only_one_public_page_fetch_effect_allowed",
        )
    )


def task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    selected = int(value.get("third_source_selected_target_count", -1))
    safe = int(value.get("third_source_safe_change_count", -1))
    confirmed = int(value.get("third_source_baseline_confirmed_count", -1))
    unresolved = int(value.get("third_source_unresolved_count", -1))
    attempted = int(value.get("third_source_fetch_attempt_count", -1))
    checks = {
        "third_source_threshold_partition_attested": (
            value.get("third_source_threshold_partition_exact") is True
            and _threshold_total(value) == selected
            and value.get("third_source_safe_change_count")
            == value.get(THRESHOLD_TASK_FIELDS["safe_change_count"])
            and safe + confirmed + unresolved == selected
        ),
        "third_source_page_and_fetch_conservation": (
            value.get("third_source_candidate_count") in {0, 1}
            and attempted == value.get("third_source_candidate_count")
            == value.get("third_source_additional_fetch_calls")
            == value.get("third_source_additional_fetch_effects")
            and 0 <= value.get("third_source_usable_page_count", -1) <= attempted
            and value.get("third_source_extended_active_page_count")
            == value.get("third_source_parent_active_page_count")
            + value.get("third_source_usable_page_count")
            and value.get("third_source_parent_total_fetch_cap") == 10
            and value.get("third_source_total_fetch_cap") == MAXIMUM_TOTAL_FETCHES
            and value.get("third_source_active_source_cap")
            == MAXIMUM_ACTIVE_SOURCES
        ),
        "third_source_entropy_credit_conservation": (
            0.0
            <= float(value.get("third_source_decision_credit_total_nats", -1.0))
            <= float(value.get("third_source_epistemic_credit_total_nats", -1.0))
            + 1e-12
            <= float(
                value.get("third_source_positive_information_gain_total_nats", -1.0)
            )
            + 1e-12
            and (
                float(value.get("third_source_decision_credit_total_nats", 0.0))
                == 0.0
                or safe > 0
            )
            and float(
                value.get("third_source_parent_epistemic_credit_total_nats", -1.0)
            )
            <= float(value.get("third_source_epistemic_credit_total_nats", -1.0))
            + 1e-12
            and float(
                value.get("third_source_parent_decision_credit_total_nats", -1.0)
            )
            <= float(value.get("third_source_decision_credit_total_nats", -1.0))
            + 1e-12
        ),
        "third_source_effect_conservation": (
            _source_policy_attested(value)
            and _effect_attested(value)
            and all(
                value.get(name) == 0
                for name in (
                    "third_source_additional_model_requests",
                    "third_source_additional_logical_queries",
                    "third_source_additional_search_batches",
                    "third_source_additional_provider_search_calls",
                    "third_source_additional_model_acquisitions",
                    "third_source_additional_model_attempts",
                    "third_source_additional_hosted_search_attempts",
                    "third_source_additional_hosted_search_deadline_failures",
                )
            )
            and value.get("third_source_additional_fetch_effects")
            == value.get("third_source_additional_hard_fetch_helper_calls")
            + value.get("third_source_additional_fetch_deadline_rejections")
        ),
        "third_source_single_validation_attested": (
            value.get("third_source_complete_envelope_validated_once") is True
            and value.get(
                "third_source_projection_consumed_only_validated_capability"
            )
            is True
        ),
    }
    if tuple(checks) != TASK_CHECK_NAMES:
        raise RuntimeError("V2.44.49 task check order drifted")
    return checks


def task_projection(
    ordinal: int,
    validated: ValidatedSerializedThirdSourceEnvelope,
) -> dict[str, Any]:
    if not isinstance(validated, ValidatedSerializedThirdSourceEnvelope):
        raise TypeError("V2.44.49 requires a V2.44.48 validated capability")
    receipts = validated.counts_only_receipts()
    receipt = receipts["third_source_recovery_receipt"]
    effect = receipts["effect_delta_receipt"]
    partition = receipt["threshold_failure_partition"]
    value = {
        "ordinal": ordinal,
        "third_source_selected_target_count": int(receipt["selected_target_count"]),
        "third_source_frozen_active_lead_count": int(receipt["frozen_active_lead_count"]),
        "third_source_parent_selected_active_source_count": int(
            receipt["parent_selected_active_source_count"]
        ),
        "third_source_candidate_count": int(receipt["third_source_candidate_count"]),
        "third_source_fetch_attempt_count": int(
            receipt["third_source_fetch_attempt_count"]
        ),
        "third_source_usable_page_count": int(receipt["third_source_usable_page_count"]),
        "third_source_parent_active_page_count": int(receipt["parent_active_page_count"]),
        "third_source_extended_active_page_count": int(
            receipt["extended_active_page_count"]
        ),
        "third_source_extended_narrative_projection_count": int(
            receipt["extended_narrative_projection_count"]
        ),
        "third_source_extended_novel_observation_count": int(
            receipt["extended_novel_observation_count"]
        ),
        **{
            field: int(partition[name])
            for name, field in THRESHOLD_TASK_FIELDS.items()
        },
        "third_source_baseline_confirmed_count": int(receipt["baseline_confirmed_count"]),
        "third_source_unresolved_count": int(receipt["unresolved_count"]),
        "third_source_positive_epistemic_target_count": int(
            receipt["positive_epistemic_target_count"]
        ),
        "third_source_credit_record_count": int(receipt["source_credit_record_count"]),
        "third_source_parent_candidate_changed_cell_count": int(
            receipt["parent_candidate_changed_cell_count"]
        ),
        "third_source_candidate_changed_cell_count": int(
            receipt["candidate_changed_cell_count"]
        ),
        "third_source_known_baseline_minimum_support_sources": int(
            receipt["known_baseline_minimum_support_sources"]
        ),
        "third_source_unknown_baseline_minimum_support_sources": int(
            receipt["unknown_baseline_minimum_support_sources"]
        ),
        "third_source_required_support_margin": int(receipt["required_support_margin"]),
        "third_source_active_source_cap": int(receipt["active_source_cap"]),
        "third_source_parent_total_fetch_cap": int(receipt["parent_total_fetch_cap"]),
        "third_source_additional_model_requests": int(receipt["additional_model_requests"]),
        "third_source_additional_logical_queries": int(receipt["additional_logical_queries"]),
        "third_source_additional_search_batches": int(receipt["additional_search_batches"]),
        "third_source_additional_provider_search_calls": int(
            receipt["additional_provider_search_calls"]
        ),
        "third_source_additional_fetch_calls": int(receipt["additional_fetch_calls"]),
        "third_source_total_fetch_cap": int(receipt["total_fetch_cap"]),
        "third_source_additional_model_acquisitions": int(
            effect["additional_model_acquisitions"]
        ),
        "third_source_additional_model_attempts": int(effect["additional_model_attempts"]),
        "third_source_additional_hosted_search_attempts": int(
            effect["additional_hosted_search_attempts"]
        ),
        "third_source_additional_hosted_search_deadline_failures": int(
            effect["additional_hosted_search_deadline_failures"]
        ),
        "third_source_additional_hard_fetch_helper_calls": int(
            effect["additional_hard_fetch_helper_calls"]
        ),
        "third_source_additional_fetch_deadline_rejections": int(
            effect["additional_fetch_deadline_rejections"]
        ),
        "third_source_additional_hard_fetch_deadline_failures": int(
            effect["additional_hard_fetch_deadline_failures"]
        ),
        "third_source_additional_fetch_helper_failures": int(
            effect["additional_fetch_helper_failures"]
        ),
        "third_source_additional_fetch_effects": int(effect["additional_fetch_effects"]),
        "third_source_pre_active_entropy_total_nats": float(
            receipt["pre_active_entropy_total_nats"]
        ),
        "third_source_combined_entropy_total_nats": float(
            receipt["combined_entropy_total_nats"]
        ),
        "third_source_positive_information_gain_total_nats": float(
            receipt["positive_information_gain_total_nats"]
        ),
        "third_source_epistemic_credit_total_nats": float(
            receipt["epistemic_credit_total_nats"]
        ),
        "third_source_decision_credit_total_nats": float(
            receipt["decision_credit_total_nats"]
        ),
        "third_source_parent_epistemic_credit_total_nats": float(
            receipt["parent_epistemic_credit_total_nats"]
        ),
        "third_source_parent_decision_credit_total_nats": float(
            receipt["parent_decision_credit_total_nats"]
        ),
        "third_source_minimum_alternative_posterior": float(
            receipt["minimum_alternative_posterior"]
        ),
        "third_source_threshold_partition_exact": (
            sum(int(partition[name]) for name in THRESHOLD_PARTITION_FIELDS)
            == int(receipt["selected_target_count"])
        ),
        "third_source_frozen_active_lead_ranking_reused": bool(
            receipt["frozen_active_lead_ranking_reused"]
        ),
        "third_source_proposal_and_existing_active_sources_excluded": bool(
            receipt["proposal_and_existing_active_sources_excluded"]
        ),
        "third_source_parent_narrative_projection_replayed_exactly": bool(
            receipt["parent_narrative_projection_replayed_exactly"]
        ),
        "third_source_safe_change_thresholds_preserved": bool(
            receipt["safe_change_thresholds_preserved"]
        ),
        "third_source_posterior_and_credit_recomputed_without_model_or_search": bool(
            receipt["posterior_and_credit_recomputed_without_model_or_search"]
        ),
        "third_source_model_effect_and_static_fields_equal": bool(
            effect["model_effect_and_static_fields_equal"]
        ),
        "third_source_model_remaining_seconds_nonincreasing": bool(
            effect["model_remaining_seconds_nonincreasing"]
        ),
        "third_source_model_deadline_state_monotonic": bool(
            effect["model_deadline_state_monotonic"]
        ),
        "third_source_search_shape_fields_equal": bool(effect["search_shape_fields_equal"]),
        "third_source_transport_deadline_state_monotonic": bool(
            effect["transport_deadline_state_monotonic"]
        ),
        "third_source_only_one_public_page_fetch_effect_allowed": bool(
            effect["only_one_public_page_fetch_effect_allowed"]
        ),
        "third_source_complete_envelope_validated_once": True,
        "third_source_projection_consumed_only_validated_capability": True,
    }
    value["checks"] = task_checks(value)
    value["passed"] = all(value["checks"].values())
    validate_task_projection(value)
    return value


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    checks = value.get("checks")
    if (
        set(value) != TASK_KEYS
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in THIRD_COUNT_FIELDS
        )
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in THIRD_NUMERIC_FIELDS
        )
        or any(not isinstance(value.get(name), bool) for name in THIRD_BOOLEAN_FIELDS)
        or not isinstance(checks, Mapping)
        or tuple(checks) != TASK_CHECK_NAMES
        or dict(checks) != task_checks(value)
        or value.get("passed") is not all(checks.values())
    ):
        raise RuntimeError("V2.44.49 task projection drifted")
    return copy.deepcopy(dict(value))


def local_failure(ordinal: int) -> dict[str, Any]:
    value = {
        "ordinal": ordinal,
        **{name: 0 for name in THIRD_COUNT_FIELDS},
        **{name: 0.0 for name in THIRD_NUMERIC_FIELDS},
        **{name: False for name in THIRD_BOOLEAN_FIELDS},
    }
    value["checks"] = task_checks(value)
    value["passed"] = False
    validate_task_projection(value)
    return value


def aggregate_checks(
    summary: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, bool]:
    partition_total = sum(
        int(summary.get(field, -1))
        for field in THRESHOLD_AGGREGATE_FIELDS.values()
    )
    checks = {
        "third_source_safe_change_tasks": summary["third_source_safe_change_tasks"]
        >= gates["minimum_third_source_safe_change_tasks"],
        "third_source_positive_decision_credit": summary[
            "third_source_decision_credit_total_nats"
        ]
        >= gates["minimum_third_source_decision_credit_nats"],
        "third_source_threshold_partition_attested": (
            summary["all_third_source_threshold_partitions_exact"] is True
            and partition_total == summary["third_source_total_selected_targets"]
            and summary[THRESHOLD_AGGREGATE_FIELDS["safe_change_count"]]
            <= summary["third_source_total_selected_targets"]
        ),
        "third_source_effect_conservation": (
            summary["third_source_effect_conserved_tasks"] == summary["selected"]
            and summary["all_third_source_effects_conserved"] is True
            and summary["all_third_source_source_policies_attested"] is True
            and summary["third_source_total_additional_fetch_effects"]
            == summary["third_source_total_fetch_attempts"]
        ),
        "all_third_source_single_validation_attested": (
            summary["third_source_validated_once_tasks"] == summary["selected"]
            and summary["all_third_source_envelopes_validated_once"] is True
            and summary[
                "all_third_source_projections_consumed_validated_capabilities"
            ]
            is True
        ),
    }
    if tuple(checks) != AGGREGATE_CHECK_NAMES:
        raise RuntimeError("V2.44.49 aggregate check order drifted")
    return checks


def aggregate_tasks(
    tasks: Sequence[Mapping[str, Any]],
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    values = sorted(
        (validate_task_projection(item) for item in tasks),
        key=lambda item: item["ordinal"],
    )
    count_sources = {
        "third_source_total_selected_targets": "third_source_selected_target_count",
        "third_source_total_candidates": "third_source_candidate_count",
        "third_source_total_fetch_attempts": "third_source_fetch_attempt_count",
        "third_source_total_usable_pages": "third_source_usable_page_count",
        "third_source_total_extended_active_pages": "third_source_extended_active_page_count",
        "third_source_total_extended_narrative_projections": "third_source_extended_narrative_projection_count",
        "third_source_total_extended_novel_observations": "third_source_extended_novel_observation_count",
        "third_source_total_baseline_confirmed": "third_source_baseline_confirmed_count",
        "third_source_total_unresolved": "third_source_unresolved_count",
        "third_source_total_positive_epistemic_targets": "third_source_positive_epistemic_target_count",
        "third_source_total_credit_records": "third_source_credit_record_count",
        "third_source_total_parent_candidate_changed_cells": "third_source_parent_candidate_changed_cell_count",
        "third_source_total_candidate_changed_cells": "third_source_candidate_changed_cell_count",
        "third_source_total_additional_fetch_effects": "third_source_additional_fetch_effects",
        "third_source_total_additional_hard_fetch_deadline_failures": "third_source_additional_hard_fetch_deadline_failures",
        "third_source_total_additional_fetch_helper_failures": "third_source_additional_fetch_helper_failures",
    }
    summary = {
        "selected": len(values),
        "exact_ordinal_vector": [item["ordinal"] for item in values]
        == list(range(1, len(values) + 1)),
        "third_source_candidate_tasks": sum(
            item["third_source_candidate_count"] > 0 for item in values
        ),
        "third_source_fetch_attempt_tasks": sum(
            item["third_source_fetch_attempt_count"] > 0 for item in values
        ),
        "third_source_usable_page_tasks": sum(
            item["third_source_usable_page_count"] > 0 for item in values
        ),
        "third_source_safe_change_tasks": sum(
            item["third_source_safe_change_count"] > 0 for item in values
        ),
        "third_source_decision_credit_tasks": sum(
            item["third_source_decision_credit_total_nats"] > 0 for item in values
        ),
        "third_source_effect_conserved_tasks": sum(
            item["checks"]["third_source_effect_conservation"] for item in values
        ),
        "third_source_validated_once_tasks": sum(
            item["third_source_complete_envelope_validated_once"] for item in values
        ),
        **{
            output: sum(item[source] for item in values)
            for output, source in count_sources.items()
        },
        **{
            aggregate: sum(item[task] for item in values)
            for reason, aggregate in THRESHOLD_AGGREGATE_FIELDS.items()
            for task in (THRESHOLD_TASK_FIELDS[reason],)
        },
        "all_third_source_threshold_partitions_exact": all(
            item["third_source_threshold_partition_exact"] for item in values
        ),
        "all_third_source_effects_conserved": all(
            item["checks"]["third_source_effect_conservation"] for item in values
        ),
        "all_third_source_source_policies_attested": all(
            _source_policy_attested(item) for item in values
        ),
        "all_third_source_envelopes_validated_once": all(
            item["third_source_complete_envelope_validated_once"] for item in values
        ),
        "all_third_source_projections_consumed_validated_capabilities": all(
            item["third_source_projection_consumed_only_validated_capability"]
            for item in values
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
        raise RuntimeError("V2.44.49 aggregate drifted")
    return copy.deepcopy(dict(value))


__all__ = [
    "AGGREGATE_KEYS",
    "TASK_KEYS",
    "THRESHOLD_AGGREGATE_FIELDS",
    "THRESHOLD_TASK_FIELDS",
    "aggregate_checks",
    "aggregate_tasks",
    "local_failure",
    "task_checks",
    "task_projection",
    "validate_aggregate",
    "validate_task_projection",
]
