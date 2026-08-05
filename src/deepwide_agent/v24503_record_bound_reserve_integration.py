"""Zero-effect integration of record-bound projection after targeted reserve.

The complete V2.44.96 reserve result remains the immutable parent.  This
successor replays the same already-fetched pages through V2.45.02, recomputes
the unchanged posterior, leave-one-out epistemic credit, decision credit and
candidate merge, and records both improvements and regressions.  No model,
query, search batch, provider search or fetch is added.

Because observations are source-keyed, narrative/record observations from a
source with more than one title-anchored page are conservatively removed at
integration time.  Such removals are explicit in the receipt; they cannot be
hidden by gain-only accounting.
"""

from __future__ import annotations

import copy
import math
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import v24390_uncertainty_active_evidence_runtime as runtime
from . import v24457_adaptive_entropy_support as adaptive
from . import v24490_entropy_targeted_support_search as targeted
from . import v24496_targeted_reserve_contradiction as parent
from .v24333_programmatic_support_catalog import _source_key
from .v24388_uncertainty_credit import (
    KNOWN_ALTERNATIVE_MINIMUM_SOURCES,
    MINIMUM_ALTERNATIVE_POSTERIOR,
    UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES,
    apply_active_evidence,
    validate_active_evidence_result,
    validate_uncertainty_catalog,
)
from .v24413_effect_equivalence import (
    compare_effect_snapshots,
    validate_effect_equivalence_receipt,
)
from .v24428_unique_title_anchor_projection import _unique_title_row
from .v24447_third_source_entropy_to_decision import threshold_failure_partition
from .v24485_execution_scoped_validation_memo import ExecutionValidationMemo
from .v24502_record_bound_title_projection import (
    POLICY_ID as PROJECTION_POLICY_ID,
    build_record_bound_title_projection,
    validate_record_bound_title_projection,
)
from .v24323_shared_prefix_cell_entropy import payload_sha256


POLICY_ID = "v24503_zero_effect_record_bound_reserve_integration_v1"
RESULT_ROLE = "v24503_record_bound_reserve_result"
RECEIPT_ROLE = "v24503_record_bound_reserve_receipt"
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "candidate_prediction",
        "record_bound_projection",
        "record_bound_active_evidence_result",
        "record_bound_receipt",
        "result_sha256",
    }
)
COUNT_FIELDS = (
    "selected_target_count",
    "parent_active_observation_count",
    "record_bound_active_observation_count",
    "added_observation_count",
    "removed_observation_count",
    "ambiguous_source_observation_removal_count",
    "parent_safe_change_count",
    "record_bound_safe_change_count",
    "safe_change_improvement_count",
    "safe_change_regression_count",
    "parent_candidate_changed_cell_count",
    "record_bound_candidate_changed_cell_count",
    "candidate_change_improvement_count",
    "candidate_change_regression_count",
    "parent_narrative_projection_count",
    "admitted_parent_narrative_projection_count",
    "rejected_parent_narrative_projection_count",
    "record_bound_projection_count",
    "known_baseline_minimum_support_sources",
    "unknown_baseline_minimum_support_sources",
    "required_support_margin",
    "additional_model_requests",
    "additional_logical_queries",
    "additional_search_batches",
    "additional_provider_search_calls",
    "additional_fetch_calls",
)
NUMERIC_FIELDS = (
    "parent_positive_information_gain_total_nats",
    "record_bound_positive_information_gain_total_nats",
    "positive_information_gain_gain_nats",
    "positive_information_gain_regression_nats",
    "parent_epistemic_credit_total_nats",
    "record_bound_epistemic_credit_total_nats",
    "epistemic_credit_gain_nats",
    "epistemic_credit_regression_nats",
    "parent_decision_credit_total_nats",
    "record_bound_decision_credit_total_nats",
    "decision_credit_gain_nats",
    "decision_credit_regression_nats",
    "minimum_alternative_posterior",
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "projection_policy_id",
        *COUNT_FIELDS,
        *NUMERIC_FIELDS,
        "threshold_failure_partition",
        "same_frozen_page_vector_replayed",
        "source_ambiguous_title_pages_fail_closed",
        "observation_additions_and_removals_accounted",
        "posterior_thresholds_and_credit_rules_preserved",
        "source_credit_uses_normalized_leave_one_out_information_gain",
        "decision_credit_requires_safe_output_change",
        "record_bound_pages_used_for_model_prompt_or_candidate_generation",
        "allocated_credit_used_for_same_run_training_or_policy_update",
        "task_query_url_page_prediction_candidate_value_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


@dataclass(frozen=True)
class IntegratedRecordBoundReserveOutcome:
    parent: parent.IntegratedTargetedReserveOutcome
    record_bound_result: dict[str, Any]
    model_slot_receipt_before_record_projection: dict[str, Any]
    transport_health_before_record_projection: dict[str, Any]
    search_single_shot_receipt_before_record_projection: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]
    effect_equivalence_receipt: dict[str, Any]


def _observation_key(value: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return parent._observation_key(value)


def _finite(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"V2.45.03 {label} is invalid")
    return float(value)


def _validated_context(
    validated_parent: Mapping[str, Any],
) -> dict[str, Any]:
    targeted_result = targeted.validate_result(validated_parent["parent_result"])
    adaptive_result = adaptive.validate_result(targeted_result["parent_result"])
    original = adaptive._original_parent_result(adaptive_result["parent_result"])
    anchored = original["parent_result"]
    structured = anchored["parent_result"]
    legacy = structured["parent_result"]
    baseline = str(legacy["baseline_prediction"])
    legacy_private = legacy["private_replay_state"]
    catalog = validate_uncertainty_catalog(legacy_private["uncertainty_catalog"])
    pages = [
        *copy.deepcopy(list(legacy_private["active_pages"])),
        *targeted._parent_adaptive_pages(adaptive_result),
        *copy.deepcopy(
            list(targeted_result["targeted_private_state"]["targeted_pages"])
        ),
        *copy.deepcopy(
            list(validated_parent["reserve_private_state"]["reserve_pages"])
        ),
    ]
    return {
        "baseline": baseline,
        "legacy_parent": legacy["parent_result"],
        "catalog": catalog,
        "pages": pages,
        "selected_identities": adaptive._selected_identities(catalog),
    }


def _title_source_counts(
    projection: Mapping[str, Any], baseline: str
) -> Counter[tuple[str, str]]:
    cells = runtime._baseline_cells(baseline)
    counts: Counter[tuple[str, str]] = Counter()
    for page in projection["pages"]:
        anchor = _unique_title_row(str(page["title"]), cells)
        if anchor is None:
            continue
        counts[(_source_key(str(page["host"])), runtime._target_identity(anchor[0], "")[0])] += 1
    return counts


def _ambiguity_filtered_observations(
    projection: Mapping[str, Any], baseline: str
) -> tuple[list[dict[str, Any]], int]:
    counts = _title_source_counts(projection, baseline)
    narrative_keys = {
        _observation_key(item)
        for item in projection["admitted_parent_narrative_projections"]
    }
    record_keys = {
        _observation_key(item) for item in projection["record_bound_projections"]
    }
    protected = narrative_keys | record_keys
    output: list[dict[str, Any]] = []
    removed = 0
    for raw in projection["observations"]:
        item = copy.deepcopy(dict(raw))
        key = _observation_key(item)
        identity = runtime._target_identity(item["row_key"], item["column"])[0]
        source_identity = (_source_key(str(item["source_host"])), identity)
        if key in protected and counts[source_identity] != 1:
            removed += 1
            continue
        output.append(item)
    return output, removed


def _snapshot(validated_parent: Mapping[str, Any]) -> dict[str, Any]:
    context = _validated_context(validated_parent)
    projection = build_record_bound_title_projection(
        context["baseline"],
        context["pages"],
        selected_identities=context["selected_identities"],
    )
    observations, ambiguous_removed = _ambiguity_filtered_observations(
        projection, context["baseline"]
    )
    active = apply_active_evidence(context["catalog"], observations)
    validate_active_evidence_result(active)
    candidate, _merge = runtime._merge_parent_candidate(
        context["legacy_parent"], active
    )
    return {
        **context,
        "projection": projection,
        "observations": observations,
        "ambiguous_removed": ambiguous_removed,
        "active": active,
        "candidate": candidate,
        "threshold_failure_partition": threshold_failure_partition(active),
    }


def _delta(after: float, before: float) -> tuple[float, float]:
    return max(0.0, after - before), max(0.0, before - after)


def _build_receipt(
    validated_parent: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> dict[str, Any]:
    parent_active = validate_active_evidence_result(
        validated_parent["reserve_active_evidence_result"]
    )
    after_active = validate_active_evidence_result(snapshot["active"])
    parent_observations = list(parent_active["active_observations"])
    after_observations = list(after_active["active_observations"])
    before_keys = {_observation_key(item) for item in parent_observations}
    after_keys = {_observation_key(item) for item in after_observations}
    before_receipt = parent_active["receipt"]
    after_receipt = after_active["receipt"]
    before_changes = runtime._changed_cells(
        snapshot["baseline"], validated_parent["candidate_prediction"]
    )
    after_changes = runtime._changed_cells(
        snapshot["baseline"], snapshot["candidate"]
    )
    information_gain, information_regression = _delta(
        float(after_receipt["positive_information_gain_total_nats"]),
        float(before_receipt["positive_information_gain_total_nats"]),
    )
    epistemic_gain, epistemic_regression = _delta(
        float(after_receipt["epistemic_credit_total_nats"]),
        float(before_receipt["epistemic_credit_total_nats"]),
    )
    decision_gain, decision_regression = _delta(
        float(after_receipt["decision_credit_total_nats"]),
        float(before_receipt["decision_credit_total_nats"]),
    )
    before_safe = int(before_receipt["safe_change_count"])
    after_safe = int(after_receipt["safe_change_count"])
    before_change_count = len(before_changes)
    after_change_count = len(after_changes)
    projection = snapshot["projection"]
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "projection_policy_id": PROJECTION_POLICY_ID,
        "selected_target_count": int(after_receipt["selected_target_count"]),
        "parent_active_observation_count": len(parent_observations),
        "record_bound_active_observation_count": len(after_observations),
        "added_observation_count": len(after_keys - before_keys),
        "removed_observation_count": len(before_keys - after_keys),
        "ambiguous_source_observation_removal_count": int(
            snapshot["ambiguous_removed"]
        ),
        "parent_safe_change_count": before_safe,
        "record_bound_safe_change_count": after_safe,
        "safe_change_improvement_count": max(0, after_safe - before_safe),
        "safe_change_regression_count": max(0, before_safe - after_safe),
        "parent_candidate_changed_cell_count": before_change_count,
        "record_bound_candidate_changed_cell_count": after_change_count,
        "candidate_change_improvement_count": max(
            0, after_change_count - before_change_count
        ),
        "candidate_change_regression_count": max(
            0, before_change_count - after_change_count
        ),
        "parent_narrative_projection_count": int(
            projection["parent_narrative_projection_count"]
        ),
        "admitted_parent_narrative_projection_count": int(
            projection["admitted_parent_narrative_projection_count"]
        ),
        "rejected_parent_narrative_projection_count": int(
            projection["rejected_parent_narrative_projection_count"]
        ),
        "record_bound_projection_count": int(
            projection["record_bound_projection_count"]
        ),
        "parent_positive_information_gain_total_nats": float(
            before_receipt["positive_information_gain_total_nats"]
        ),
        "record_bound_positive_information_gain_total_nats": float(
            after_receipt["positive_information_gain_total_nats"]
        ),
        "positive_information_gain_gain_nats": information_gain,
        "positive_information_gain_regression_nats": information_regression,
        "parent_epistemic_credit_total_nats": float(
            before_receipt["epistemic_credit_total_nats"]
        ),
        "record_bound_epistemic_credit_total_nats": float(
            after_receipt["epistemic_credit_total_nats"]
        ),
        "epistemic_credit_gain_nats": epistemic_gain,
        "epistemic_credit_regression_nats": epistemic_regression,
        "parent_decision_credit_total_nats": float(
            before_receipt["decision_credit_total_nats"]
        ),
        "record_bound_decision_credit_total_nats": float(
            after_receipt["decision_credit_total_nats"]
        ),
        "decision_credit_gain_nats": decision_gain,
        "decision_credit_regression_nats": decision_regression,
        "threshold_failure_partition": copy.deepcopy(
            snapshot["threshold_failure_partition"]
        ),
        "known_baseline_minimum_support_sources": KNOWN_ALTERNATIVE_MINIMUM_SOURCES,
        "unknown_baseline_minimum_support_sources": UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES,
        "minimum_alternative_posterior": MINIMUM_ALTERNATIVE_POSTERIOR,
        "required_support_margin": 1,
        "additional_model_requests": 0,
        "additional_logical_queries": 0,
        "additional_search_batches": 0,
        "additional_provider_search_calls": 0,
        "additional_fetch_calls": 0,
        "same_frozen_page_vector_replayed": True,
        "source_ambiguous_title_pages_fail_closed": True,
        "observation_additions_and_removals_accounted": True,
        "posterior_thresholds_and_credit_rules_preserved": True,
        "source_credit_uses_normalized_leave_one_out_information_gain": True,
        "decision_credit_requires_safe_output_change": True,
        "record_bound_pages_used_for_model_prompt_or_candidate_generation": False,
        "allocated_credit_used_for_same_run_training_or_policy_update": False,
        "task_query_url_page_prediction_candidate_value_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_record_bound_receipt(value)


def validate_record_bound_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    partition = copied.get("threshold_failure_partition")
    true_fields = (
        "same_frozen_page_vector_replayed",
        "source_ambiguous_title_pages_fail_closed",
        "observation_additions_and_removals_accounted",
        "posterior_thresholds_and_credit_rules_preserved",
        "source_credit_uses_normalized_leave_one_out_information_gain",
        "decision_credit_requires_safe_output_change",
    )
    false_fields = (
        "record_bound_pages_used_for_model_prompt_or_candidate_generation",
        "allocated_credit_used_for_same_run_training_or_policy_update",
        "task_query_url_page_prediction_candidate_value_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or copied.get("projection_policy_id") != PROJECTION_POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in COUNT_FIELDS
        )
        or any(_finite(copied.get(name), name) < 0 for name in NUMERIC_FIELDS)
        or copied["record_bound_active_observation_count"]
        != copied["parent_active_observation_count"]
        + copied["added_observation_count"]
        - copied["removed_observation_count"]
        or copied["ambiguous_source_observation_removal_count"]
        > copied["removed_observation_count"]
        or copied["safe_change_improvement_count"]
        != max(
            0,
            copied["record_bound_safe_change_count"]
            - copied["parent_safe_change_count"],
        )
        or copied["safe_change_regression_count"]
        != max(
            0,
            copied["parent_safe_change_count"]
            - copied["record_bound_safe_change_count"],
        )
        or copied["candidate_change_improvement_count"]
        != max(
            0,
            copied["record_bound_candidate_changed_cell_count"]
            - copied["parent_candidate_changed_cell_count"],
        )
        or copied["candidate_change_regression_count"]
        != max(
            0,
            copied["parent_candidate_changed_cell_count"]
            - copied["record_bound_candidate_changed_cell_count"],
        )
        or copied["parent_narrative_projection_count"]
        != copied["admitted_parent_narrative_projection_count"]
        + copied["rejected_parent_narrative_projection_count"]
        or not math.isclose(
            copied["positive_information_gain_gain_nats"],
            max(
                0.0,
                copied["record_bound_positive_information_gain_total_nats"]
                - copied["parent_positive_information_gain_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["positive_information_gain_regression_nats"],
            max(
                0.0,
                copied["parent_positive_information_gain_total_nats"]
                - copied["record_bound_positive_information_gain_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["epistemic_credit_gain_nats"],
            max(
                0.0,
                copied["record_bound_epistemic_credit_total_nats"]
                - copied["parent_epistemic_credit_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["epistemic_credit_regression_nats"],
            max(
                0.0,
                copied["parent_epistemic_credit_total_nats"]
                - copied["record_bound_epistemic_credit_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["decision_credit_gain_nats"],
            max(
                0.0,
                copied["record_bound_decision_credit_total_nats"]
                - copied["parent_decision_credit_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["decision_credit_regression_nats"],
            max(
                0.0,
                copied["parent_decision_credit_total_nats"]
                - copied["record_bound_decision_credit_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or copied["record_bound_decision_credit_total_nats"]
        > copied["record_bound_epistemic_credit_total_nats"] + 1e-12
        or copied["decision_credit_gain_nats"] > 0
        and (
            copied["record_bound_safe_change_count"] == 0
            or copied["record_bound_candidate_changed_cell_count"] == 0
        )
        or copied["known_baseline_minimum_support_sources"]
        != KNOWN_ALTERNATIVE_MINIMUM_SOURCES
        or copied["unknown_baseline_minimum_support_sources"]
        != UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
        or copied["minimum_alternative_posterior"]
        != MINIMUM_ALTERNATIVE_POSTERIOR
        or copied["required_support_margin"] != 1
        or any(
            copied[name] != 0
            for name in (
                "additional_model_requests",
                "additional_logical_queries",
                "additional_search_batches",
                "additional_provider_search_calls",
                "additional_fetch_calls",
            )
        )
        or not isinstance(partition, Mapping)
        or sum(int(item) for item in partition.values())
        != copied["selected_target_count"]
        or int(partition.get("safe_change_count", -1))
        != copied["record_bound_safe_change_count"]
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.03 record-bound receipt drifted")
    return copied


def _compute_result_from_validated(
    validated_parent: Mapping[str, Any]
) -> dict[str, Any]:
    snapshot = _snapshot(validated_parent)
    value = {
        "artifact_version": 1,
        "role": RESULT_ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(validated_parent),
        "candidate_prediction": snapshot["candidate"],
        "record_bound_projection": snapshot["projection"],
        "record_bound_active_evidence_result": snapshot["active"],
        "record_bound_receipt": _build_receipt(validated_parent, snapshot),
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def _recover_record_bound_reserve_in_scope(
    parent_result: Mapping[str, Any]
) -> dict[str, Any]:
    return _compute_result_from_validated(parent.validate_result(parent_result))


def recover_record_bound_reserve(
    parent_result: Mapping[str, Any]
) -> dict[str, Any]:
    """Validate one external parent and recover it inside one memo scope."""

    with ExecutionValidationMemo():
        return _recover_record_bound_reserve_in_scope(parent_result)


def _validate_result_in_scope(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("result_sha256", None)
    if (
        set(copied) != RESULT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RESULT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("parent_result"), Mapping)
        or not isinstance(copied.get("candidate_prediction"), str)
        or not isinstance(copied.get("record_bound_projection"), Mapping)
        or not isinstance(copied.get("record_bound_active_evidence_result"), Mapping)
        or not isinstance(copied.get("record_bound_receipt"), Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.03 result identity drifted")
    validated_parent = parent.validate_result(copied["parent_result"])
    validate_record_bound_title_projection(copied["record_bound_projection"])
    validate_active_evidence_result(copied["record_bound_active_evidence_result"])
    validate_record_bound_receipt(copied["record_bound_receipt"])
    expected = _compute_result_from_validated(validated_parent)
    if copied != expected:
        raise ValueError("V2.45.03 result replay drifted")
    return copied


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one external child result without exponential ancestor replay."""

    with ExecutionValidationMemo():
        return _validate_result_in_scope(value)


def _validate_cross_artifacts_in_scope(
    parent_result: Mapping[str, Any],
    record_bound_result: Mapping[str, Any],
    *,
    model_before: Mapping[str, Any],
    transport_before: Mapping[str, Any],
    search_before: Mapping[str, Any],
    model_after: Mapping[str, Any],
    transport_after: Mapping[str, Any],
    search_after: Mapping[str, Any],
    effect_equivalence_receipt: Mapping[str, Any],
    expected_model_cap: int,
) -> None:
    validated_parent = parent.validate_result(parent_result)
    recovered = _validate_result_in_scope(record_bound_result)
    if recovered["parent_result"] != validated_parent:
        raise ValueError("V2.45.03 recovery parent drifted")
    expected_effect = compare_effect_snapshots(
        model_before=model_before,
        model_after=model_after,
        transport_before=transport_before,
        transport_after=transport_after,
        search_before=search_before,
        search_after=search_after,
        expected_model_cap=expected_model_cap,
    )
    if validate_effect_equivalence_receipt(effect_equivalence_receipt) != expected_effect:
        raise ValueError("V2.45.03 effect-equivalence receipt drifted")


def validate_cross_artifacts(
    parent_result: Mapping[str, Any],
    record_bound_result: Mapping[str, Any],
    *,
    model_before: Mapping[str, Any],
    transport_before: Mapping[str, Any],
    search_before: Mapping[str, Any],
    model_after: Mapping[str, Any],
    transport_after: Mapping[str, Any],
    search_after: Mapping[str, Any],
    effect_equivalence_receipt: Mapping[str, Any],
    expected_model_cap: int,
) -> None:
    """Validate external cross-artifacts in one fail-closed memo scope."""

    with ExecutionValidationMemo():
        _validate_cross_artifacts_in_scope(
            parent_result,
            record_bound_result,
            model_before=model_before,
            transport_before=transport_before,
            search_before=search_before,
            model_after=model_after,
            transport_after=transport_after,
            search_after=search_after,
            effect_equivalence_receipt=effect_equivalence_receipt,
            expected_model_cap=expected_model_cap,
        )


def run_v24503_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
) -> IntegratedRecordBoundReserveOutcome:
    first = parent.run_v24496_task(
        task,
        model=model,
        search=search,
        partition_seed_sha256=partition_seed_sha256,
        limits=limits,
        monotonic=monotonic,
    )
    before_model = copy.deepcopy(first.model_slot_receipt)
    before_transport = copy.deepcopy(first.transport_health)
    before_search = copy.deepcopy(first.search_single_shot_receipt)
    with ExecutionValidationMemo():
        result = _recover_record_bound_reserve_in_scope(first.reserve_result)
        after_model = model.receipt()
        after_transport = search.transport_health()
        after_search = search.single_shot_receipt()
        effect = compare_effect_snapshots(
            model_before=before_model,
            model_after=after_model,
            transport_before=before_transport,
            transport_after=after_transport,
            search_before=before_search,
            search_after=after_search,
            expected_model_cap=int(after_model["slot_cap"]),
        )
        outcome = IntegratedRecordBoundReserveOutcome(
            parent=first,
            record_bound_result=result,
            model_slot_receipt_before_record_projection=before_model,
            transport_health_before_record_projection=before_transport,
            search_single_shot_receipt_before_record_projection=before_search,
            model_slot_receipt=after_model,
            transport_health=after_transport,
            search_single_shot_receipt=after_search,
            effect_equivalence_receipt=effect,
        )
        _validate_cross_artifacts_in_scope(
            first.reserve_result,
            result,
            model_before=before_model,
            transport_before=before_transport,
            search_before=before_search,
            model_after=after_model,
            transport_after=after_transport,
            search_after=after_search,
            effect_equivalence_receipt=effect,
            expected_model_cap=int(after_model["slot_cap"]),
        )
    return outcome


__all__ = [
    "IntegratedRecordBoundReserveOutcome",
    "POLICY_ID",
    "RESULT_ROLE",
    "recover_record_bound_reserve",
    "run_v24503_task",
    "validate_cross_artifacts",
    "validate_record_bound_receipt",
    "validate_result",
]
