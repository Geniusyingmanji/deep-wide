"""Zero-effect integration of conservative alias-title observations.

The frozen V2.45.03 result remains the immutable parent.  This successor
replays the same already-fetched page vector through V2.45.23, combines only
its canonical alias observations with the parent's already-filtered active
observations, and recomputes the unchanged posterior, leave-one-out epistemic
credit, decision credit, and candidate merge.

Source ambiguity is re-evaluated across both exact and alias title anchors.
If one source has more than one title-anchored page for a row, protected
parent narrative/record observations and new alias observations from that
source-row are removed and explicitly counted.  No model, query, search
batch, provider request, or fetch is added.
"""

from __future__ import annotations

import copy
import math
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import v24390_uncertainty_active_evidence_runtime as runtime
from . import v24503_record_bound_reserve_integration as parent
from . import v24523_conservative_alias_title_projection as alias
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24333_programmatic_support_catalog import _source_key
from .v24388_uncertainty_credit import (
    KNOWN_ALTERNATIVE_MINIMUM_SOURCES,
    MINIMUM_ALTERNATIVE_POSTERIOR,
    UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES,
    apply_active_evidence,
    validate_active_evidence_result,
)
from .v24405_structured_label_projection import (
    _canonical_observations,
    _observation_key,
)
from .v24413_effect_equivalence import (
    compare_effect_snapshots,
    validate_effect_equivalence_receipt,
)
from .v24428_unique_title_anchor_projection import _unique_title_row
from .v24447_third_source_entropy_to_decision import threshold_failure_partition
from .v24485_execution_scoped_validation_memo import ExecutionValidationMemo


POLICY_ID = "v24524_zero_effect_conservative_alias_title_integration_v1"
RESULT_ROLE = "v24524_alias_title_integration_result"
RECEIPT_ROLE = "v24524_alias_title_integration_receipt"
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "candidate_prediction",
        "alias_title_projection",
        "alias_active_evidence_result",
        "alias_title_receipt",
        "result_sha256",
    }
)
COUNT_FIELDS = (
    "selected_target_count",
    "parent_active_observation_count",
    "alias_active_observation_count",
    "added_observation_count",
    "removed_observation_count",
    "ambiguous_source_observation_rejection_count",
    "alias_ambiguous_source_observation_rejection_count",
    "exact_parent_ambiguous_source_observation_removal_count",
    "unique_alias_anchor_page_count",
    "alias_projection_count",
    "alias_observation_count",
    "parent_safe_change_count",
    "alias_safe_change_count",
    "safe_change_improvement_count",
    "safe_change_regression_count",
    "parent_candidate_changed_cell_count",
    "alias_candidate_changed_cell_count",
    "candidate_change_improvement_count",
    "candidate_change_regression_count",
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
    "alias_positive_information_gain_total_nats",
    "positive_information_gain_gain_nats",
    "positive_information_gain_regression_nats",
    "parent_epistemic_credit_total_nats",
    "alias_epistemic_credit_total_nats",
    "epistemic_credit_gain_nats",
    "epistemic_credit_regression_nats",
    "parent_decision_credit_total_nats",
    "alias_decision_credit_total_nats",
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
        "exact_and_alias_title_source_ambiguity_fail_closed",
        "observation_additions_and_removals_accounted",
        "posterior_thresholds_and_credit_rules_preserved",
        "source_credit_uses_normalized_leave_one_out_information_gain",
        "decision_credit_requires_safe_output_change",
        "alias_pages_used_for_model_prompt_or_candidate_generation",
        "allocated_credit_used_for_same_run_training_or_policy_update",
        "parent_record_bound_result_preserved",
        "task_query_url_page_prediction_candidate_value_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)


@dataclass(frozen=True)
class IntegratedAliasTitleOutcome:
    parent: parent.IntegratedRecordBoundReserveOutcome
    alias_title_result: dict[str, Any]
    model_slot_receipt_before_alias_projection: dict[str, Any]
    transport_health_before_alias_projection: dict[str, Any]
    search_single_shot_receipt_before_alias_projection: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]
    effect_equivalence_receipt: dict[str, Any]


def _finite(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"V2.45.24 {label} is invalid")
    return float(value)


def _validated_context(validated_parent: Mapping[str, Any]) -> dict[str, Any]:
    context = parent._validated_context(validated_parent["parent_result"])
    active = validate_active_evidence_result(
        validated_parent["record_bound_active_evidence_result"]
    )
    return {**context, "parent_active": active}


def _anchor_row(page: Mapping[str, Any], cells: Sequence[Any]) -> str | None:
    exact = _unique_title_row(str(page["title"]), cells)
    if exact is not None:
        return exact[0]
    current = alias.unique_alias_title_row(str(page["title"]), cells)
    return None if current is None else current.row_key


def _title_source_counts(
    projection: Mapping[str, Any], baseline: str
) -> Counter[tuple[str, str]]:
    cells = runtime._baseline_cells(baseline)
    counts: Counter[tuple[str, str]] = Counter()
    for page in projection["pages"]:
        row = _anchor_row(page, cells)
        if row is None:
            continue
        counts[
            (
                _source_key(str(page["host"])),
                runtime._target_identity(row, "")[0],
            )
        ] += 1
    return counts


def _ambiguity_filtered_observations(
    projection: Mapping[str, Any],
    baseline: str,
    parent_observations: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], int, int]:
    counts = _title_source_counts(projection, baseline)
    frozen_parent_projection = projection["parent_projection"]
    parent_protected = {
        _observation_key(item)
        for item in [
            *frozen_parent_projection["admitted_parent_narrative_projections"],
            *frozen_parent_projection["record_bound_projections"],
        ]
    }
    alias_protected = {
        _observation_key(item)
        for item in projection["alias_title_projections"]
    }
    combined = _canonical_observations(
        [*parent_observations, *projection["alias_observations"]]
    )
    output: list[dict[str, Any]] = []
    removed_alias = 0
    removed_parent = 0
    for raw in combined:
        item = copy.deepcopy(dict(raw))
        key = _observation_key(item)
        identity = runtime._target_identity(item["row_key"], item["column"])[0]
        source_identity = (_source_key(str(item["source_host"])), identity)
        if key in (parent_protected | alias_protected) and counts[source_identity] != 1:
            if key in alias_protected:
                removed_alias += 1
            else:
                removed_parent += 1
            continue
        output.append(item)
    return output, removed_alias, removed_parent


def _snapshot(validated_parent: Mapping[str, Any]) -> dict[str, Any]:
    context = _validated_context(validated_parent)
    projection = alias.build_conservative_alias_title_projection(
        context["baseline"],
        context["pages"],
        selected_identities=context["selected_identities"],
    )
    observations, removed_alias, removed_parent = _ambiguity_filtered_observations(
        projection,
        context["baseline"],
        context["parent_active"]["active_observations"],
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
        "removed_alias": removed_alias,
        "removed_parent": removed_parent,
        "active": active,
        "candidate": candidate,
        "threshold_failure_partition": threshold_failure_partition(active),
    }


def _delta(after: float, before: float) -> tuple[float, float]:
    return max(0.0, after - before), max(0.0, before - after)


def _build_receipt(
    validated_parent: Mapping[str, Any], snapshot: Mapping[str, Any]
) -> dict[str, Any]:
    before_active = validate_active_evidence_result(
        validated_parent["record_bound_active_evidence_result"]
    )
    after_active = validate_active_evidence_result(snapshot["active"])
    before_observations = list(before_active["active_observations"])
    after_observations = list(after_active["active_observations"])
    before_keys = {_observation_key(item) for item in before_observations}
    after_keys = {_observation_key(item) for item in after_observations}
    before_receipt = before_active["receipt"]
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
    removed_alias = int(snapshot["removed_alias"])
    removed_parent = int(snapshot["removed_parent"])
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "projection_policy_id": alias.POLICY_ID,
        "selected_target_count": int(after_receipt["selected_target_count"]),
        "parent_active_observation_count": len(before_observations),
        "alias_active_observation_count": len(after_observations),
        "added_observation_count": len(after_keys - before_keys),
        "removed_observation_count": len(before_keys - after_keys),
        "ambiguous_source_observation_rejection_count": removed_alias
        + removed_parent,
        "alias_ambiguous_source_observation_rejection_count": removed_alias,
        "exact_parent_ambiguous_source_observation_removal_count": removed_parent,
        "unique_alias_anchor_page_count": int(
            projection["unique_alias_anchor_page_count"]
        ),
        "alias_projection_count": int(projection["alias_projection_count"]),
        "alias_observation_count": len(projection["alias_observations"]),
        "parent_safe_change_count": before_safe,
        "alias_safe_change_count": after_safe,
        "safe_change_improvement_count": max(0, after_safe - before_safe),
        "safe_change_regression_count": max(0, before_safe - after_safe),
        "parent_candidate_changed_cell_count": before_change_count,
        "alias_candidate_changed_cell_count": after_change_count,
        "candidate_change_improvement_count": max(
            0, after_change_count - before_change_count
        ),
        "candidate_change_regression_count": max(
            0, before_change_count - after_change_count
        ),
        "parent_positive_information_gain_total_nats": float(
            before_receipt["positive_information_gain_total_nats"]
        ),
        "alias_positive_information_gain_total_nats": float(
            after_receipt["positive_information_gain_total_nats"]
        ),
        "positive_information_gain_gain_nats": information_gain,
        "positive_information_gain_regression_nats": information_regression,
        "parent_epistemic_credit_total_nats": float(
            before_receipt["epistemic_credit_total_nats"]
        ),
        "alias_epistemic_credit_total_nats": float(
            after_receipt["epistemic_credit_total_nats"]
        ),
        "epistemic_credit_gain_nats": epistemic_gain,
        "epistemic_credit_regression_nats": epistemic_regression,
        "parent_decision_credit_total_nats": float(
            before_receipt["decision_credit_total_nats"]
        ),
        "alias_decision_credit_total_nats": float(
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
        "exact_and_alias_title_source_ambiguity_fail_closed": True,
        "observation_additions_and_removals_accounted": True,
        "posterior_thresholds_and_credit_rules_preserved": True,
        "source_credit_uses_normalized_leave_one_out_information_gain": True,
        "decision_credit_requires_safe_output_change": True,
        "alias_pages_used_for_model_prompt_or_candidate_generation": False,
        "allocated_credit_used_for_same_run_training_or_policy_update": False,
        "parent_record_bound_result_preserved": True,
        "task_query_url_page_prediction_candidate_value_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_alias_title_receipt(value)


def validate_alias_title_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    partition = copied.get("threshold_failure_partition")
    true_fields = (
        "same_frozen_page_vector_replayed",
        "exact_and_alias_title_source_ambiguity_fail_closed",
        "observation_additions_and_removals_accounted",
        "posterior_thresholds_and_credit_rules_preserved",
        "source_credit_uses_normalized_leave_one_out_information_gain",
        "decision_credit_requires_safe_output_change",
        "parent_record_bound_result_preserved",
    )
    false_fields = (
        "alias_pages_used_for_model_prompt_or_candidate_generation",
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
        or copied.get("projection_policy_id") != alias.POLICY_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in COUNT_FIELDS
        )
        or any(_finite(copied.get(name), name) < 0 for name in NUMERIC_FIELDS)
        or copied["alias_active_observation_count"]
        != copied["parent_active_observation_count"]
        + copied["added_observation_count"]
        - copied["removed_observation_count"]
        or copied["ambiguous_source_observation_rejection_count"]
        != copied["alias_ambiguous_source_observation_rejection_count"]
        + copied["exact_parent_ambiguous_source_observation_removal_count"]
        or copied["exact_parent_ambiguous_source_observation_removal_count"]
        > copied["removed_observation_count"]
        or copied["alias_projection_count"] < copied["alias_observation_count"]
        or copied["safe_change_improvement_count"]
        != max(
            0,
            copied["alias_safe_change_count"]
            - copied["parent_safe_change_count"],
        )
        or copied["safe_change_regression_count"]
        != max(
            0,
            copied["parent_safe_change_count"]
            - copied["alias_safe_change_count"],
        )
        or copied["candidate_change_improvement_count"]
        != max(
            0,
            copied["alias_candidate_changed_cell_count"]
            - copied["parent_candidate_changed_cell_count"],
        )
        or copied["candidate_change_regression_count"]
        != max(
            0,
            copied["parent_candidate_changed_cell_count"]
            - copied["alias_candidate_changed_cell_count"],
        )
        or not math.isclose(
            copied["positive_information_gain_gain_nats"],
            max(
                0.0,
                copied["alias_positive_information_gain_total_nats"]
                - copied["parent_positive_information_gain_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["positive_information_gain_regression_nats"],
            max(
                0.0,
                copied["parent_positive_information_gain_total_nats"]
                - copied["alias_positive_information_gain_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["epistemic_credit_gain_nats"],
            max(
                0.0,
                copied["alias_epistemic_credit_total_nats"]
                - copied["parent_epistemic_credit_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["epistemic_credit_regression_nats"],
            max(
                0.0,
                copied["parent_epistemic_credit_total_nats"]
                - copied["alias_epistemic_credit_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["decision_credit_gain_nats"],
            max(
                0.0,
                copied["alias_decision_credit_total_nats"]
                - copied["parent_decision_credit_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied["decision_credit_regression_nats"],
            max(
                0.0,
                copied["parent_decision_credit_total_nats"]
                - copied["alias_decision_credit_total_nats"],
            ),
            abs_tol=1e-12,
        )
        or copied["alias_decision_credit_total_nats"]
        > copied["alias_epistemic_credit_total_nats"] + 1e-12
        or copied["decision_credit_gain_nats"] > 0
        and (
            copied["alias_safe_change_count"] == 0
            or copied["alias_candidate_changed_cell_count"] == 0
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
        != copied["alias_safe_change_count"]
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.24 alias title receipt drifted")
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
        "alias_title_projection": snapshot["projection"],
        "alias_active_evidence_result": snapshot["active"],
        "alias_title_receipt": _build_receipt(validated_parent, snapshot),
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def _recover_alias_title_in_scope(
    parent_result: Mapping[str, Any]
) -> dict[str, Any]:
    return _compute_result_from_validated(parent._validate_result_in_scope(parent_result))


def recover_alias_title(parent_result: Mapping[str, Any]) -> dict[str, Any]:
    """Validate one external V2.45.03 result and replay it in one memo scope."""

    with ExecutionValidationMemo():
        return _recover_alias_title_in_scope(parent_result)


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
        or not isinstance(copied.get("alias_title_projection"), Mapping)
        or not isinstance(copied.get("alias_active_evidence_result"), Mapping)
        or not isinstance(copied.get("alias_title_receipt"), Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.45.24 result identity drifted")
    validated_parent = parent._validate_result_in_scope(copied["parent_result"])
    alias.validate_conservative_alias_title_projection(
        copied["alias_title_projection"]
    )
    validate_active_evidence_result(copied["alias_active_evidence_result"])
    validate_alias_title_receipt(copied["alias_title_receipt"])
    expected = _compute_result_from_validated(validated_parent)
    if copied != expected:
        raise ValueError("V2.45.24 result replay drifted")
    return copied


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
    with ExecutionValidationMemo():
        return _validate_result_in_scope(value)


def _validate_cross_artifacts_in_scope(
    parent_result: Mapping[str, Any],
    alias_result: Mapping[str, Any],
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
    validated_parent = parent._validate_result_in_scope(parent_result)
    recovered = _validate_result_in_scope(alias_result)
    if recovered["parent_result"] != validated_parent:
        raise ValueError("V2.45.24 recovery parent drifted")
    expected_effect = compare_effect_snapshots(
        model_before=model_before,
        model_after=model_after,
        transport_before=transport_before,
        transport_after=transport_after,
        search_before=search_before,
        search_after=search_after,
        expected_model_cap=expected_model_cap,
    )
    if (
        validate_effect_equivalence_receipt(effect_equivalence_receipt)
        != expected_effect
    ):
        raise ValueError("V2.45.24 effect-equivalence receipt drifted")


def validate_cross_artifacts(
    parent_result: Mapping[str, Any],
    alias_result: Mapping[str, Any],
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
    with ExecutionValidationMemo():
        _validate_cross_artifacts_in_scope(
            parent_result,
            alias_result,
            model_before=model_before,
            transport_before=transport_before,
            search_before=search_before,
            model_after=model_after,
            transport_after=transport_after,
            search_after=search_after,
            effect_equivalence_receipt=effect_equivalence_receipt,
            expected_model_cap=expected_model_cap,
        )


def run_v24524_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
) -> IntegratedAliasTitleOutcome:
    first = parent.run_v24503_task(
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
        result = _recover_alias_title_in_scope(first.record_bound_result)
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
        outcome = IntegratedAliasTitleOutcome(
            parent=first,
            alias_title_result=result,
            model_slot_receipt_before_alias_projection=before_model,
            transport_health_before_alias_projection=before_transport,
            search_single_shot_receipt_before_alias_projection=before_search,
            model_slot_receipt=after_model,
            transport_health=after_transport,
            search_single_shot_receipt=after_search,
            effect_equivalence_receipt=effect,
        )
        _validate_cross_artifacts_in_scope(
            first.record_bound_result,
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
    "IntegratedAliasTitleOutcome",
    "POLICY_ID",
    "RESULT_ROLE",
    "recover_alias_title",
    "run_v24524_task",
    "validate_alias_title_receipt",
    "validate_cross_artifacts",
    "validate_result",
]
