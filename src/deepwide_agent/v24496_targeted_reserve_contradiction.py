"""Contradiction-aware reserve over frozen targeted discovery leads.

V2.44.90 discovers a task-local union of sources but fetches exactly the
current support deficit.  When an early selected source has no usable page or
does not produce a target-bound observation, already-discovered sources are
discarded even though the frozen targeted cap is three.  This append-only
successor runs only when the V2.44.90 stage did not improve safe-change count.
It reuses the same frozen discovery union, performs no new query/search/model
effect, and fetches at most the remaining slots under the original cap.

Allocation is deliberately two-sided.  The first reserve prefers a title/URL
that visibly contains the leading alternative; when a second slot exists it
prefers a target-relevant lead that does not visibly contain that alternative.
All fetched observations, including conflicts, enter the same unchanged
source-count/posterior/margin/leave-one-out decision gate.  No task, query,
URL, page, source, value, candidate, prediction, or digest is exposed by the
public receipt.
"""

from __future__ import annotations

import copy
import math
import unicodedata
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import v24388_uncertainty_credit as credit
from . import v24390_uncertainty_active_evidence_runtime as runtime
from . import v24490_entropy_targeted_support_search as parent
from .v24280_task_union_single_shot import validate_receipt as validate_search_receipt
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24325_shared_prefix_revision_runtime import _page_vector
from .v24333_programmatic_support_catalog import _source_key
from .v24355_explicit_partition_runtime import _source_from_lead
from .v24371_batch_stratified_verifier_runtime import _coverage
from .v24378_adaptive_heldout_verifier_runtime import _lead_projection, _target_score
from .v24447_third_source_entropy_to_decision import (
    THRESHOLD_PARTITION_FIELDS,
    threshold_failure_partition,
)
from .v24485_execution_scoped_validation_memo import ExecutionValidationMemo


POLICY_ID = "v24496_contradiction_aware_targeted_reserve_v1"
RESULT_ROLE = "v24496_targeted_reserve_result"
RECEIPT_ROLE = "v24496_targeted_reserve_support_receipt"
EFFECT_ROLE = "v24496_targeted_reserve_effect_delta"
MAXIMUM_TOTAL_TARGETED_FETCHES = parent.MAXIMUM_TARGETED_SOURCES
PAGE_CHARACTER_CAP = parent.PAGE_CHARACTER_CAP
PRIVATE_KEYS = frozenset(
    {
        "selected_reserve_leads",
        "reserve_fetch_batches",
        "reserve_pages",
    }
)
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "candidate_prediction",
        "reserve_projection",
        "reserve_active_evidence_result",
        "reserve_private_state",
        "reserve_support_receipt",
        "result_sha256",
    }
)
RECEIPT_COUNT_FIELDS = (
    "targeted_plan_present",
    "selected_target_count",
    "targeted_discovered_source_count",
    "targeted_selected_source_count_before_reserve",
    "targeted_usable_page_count_before_reserve",
    "targeted_new_observation_count_before_reserve",
    "reserve_candidate_source_count",
    "reserve_selected_source_count",
    "reserve_alternative_visible_source_count",
    "reserve_alternative_blind_source_count",
    "reserve_usable_page_count",
    "reserve_new_observation_count",
    "reserve_supporting_target_observation_count",
    "reserve_conflicting_target_observation_count",
    "reserve_other_observation_count",
    "total_targeted_selected_source_count",
    "total_targeted_usable_page_count",
    "total_targeted_new_observation_count",
    "support_deficit_before_targeted_search",
    "safe_change_count_before_targeted_search",
    "safe_change_count_before_reserve",
    "safe_change_count_after_reserve",
    "safe_change_improvement_count",
    "safe_change_regression_count",
    "candidate_changed_cell_count_after_reserve",
)
RECEIPT_NUMERIC_FIELDS = (
    "positive_information_gain_total_nats_before_reserve",
    "positive_information_gain_total_nats_after_reserve",
    "epistemic_credit_total_nats_before_reserve",
    "epistemic_credit_total_nats_after_reserve",
    "decision_credit_total_nats_before_reserve",
    "decision_credit_total_nats_after_reserve",
    "decision_credit_gain_nats",
    "decision_credit_regression_nats",
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        *RECEIPT_COUNT_FIELDS,
        *RECEIPT_NUMERIC_FIELDS,
        "threshold_failure_partition_after_reserve",
        "known_baseline_minimum_support_sources",
        "unknown_baseline_minimum_support_sources",
        "minimum_alternative_posterior",
        "required_support_margin",
        "maximum_total_targeted_fetches",
        "additional_logical_queries",
        "additional_search_batches",
        "additional_model_requests",
        "reserve_uses_only_frozen_targeted_discovery_union",
        "reserve_sources_disjoint_from_all_prior_selected_sources",
        "alternative_blind_reserve_is_a_contradiction_audit_not_negative_evidence",
        "all_reserve_observations_enter_unchanged_posterior",
        "targeted_pages_used_for_model_prompt_or_candidate_generation",
        "posterior_thresholds_and_credit_rules_preserved",
        "decision_credit_requires_safe_output_change",
        "allocated_credit_used_for_same_run_training_or_policy_update",
        "task_query_url_page_prediction_candidate_value_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
EFFECT_COUNT_FIELDS = (
    "additional_logical_queries",
    "additional_search_batches",
    "additional_provider_search_attempts",
    "additional_provider_deadline_failures",
    "additional_fetch_attempts",
    "additional_hard_fetch_helper_calls",
    "additional_fetch_deadline_rejections",
    "additional_hard_fetch_deadline_failures",
    "additional_fetch_helper_failures",
    "additional_fetch_effects",
    "additional_multi_query_chunks",
    "additional_recursive_split_requests",
    "additional_model_acquisitions",
)
EFFECT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        *EFFECT_COUNT_FIELDS,
        "model_effect_and_static_fields_equal",
        "model_remaining_seconds_nonincreasing",
        "model_deadline_state_monotonic",
        "transport_deadline_state_monotonic",
        "search_shape_fields_equal",
        "only_frozen_discovery_reserve_fetch_effects_allowed",
        "question_prompt_response_query_url_page_prediction_candidate_value_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "reserve_support_receipt_sha256",
        "receipt_sha256",
    }
)


@dataclass(frozen=True)
class IntegratedTargetedReserveOutcome:
    parent: parent.IntegratedEntropyTargetedSupportOutcome
    reserve_result: dict[str, Any]
    model_slot_receipt_before_reserve: dict[str, Any]
    transport_health_before_reserve: dict[str, Any]
    search_single_shot_receipt_before_reserve: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]
    effect_delta_receipt: dict[str, Any]


def _count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.44.96 {label} is invalid")
    return value


def _finite(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise ValueError(f"V2.44.96 {label} is invalid")
    return float(value)


def _counter_delta(before: Mapping[str, Any], after: Mapping[str, Any], name: str) -> int:
    left = _count(before.get(name), f"before {name}")
    right = _count(after.get(name), f"after {name}")
    if right < left:
        raise ValueError(f"V2.44.96 {name} decreased")
    return right - left


def _normalize(value: object) -> str:
    return " ".join(unicodedata.normalize("NFKC", str(value)).casefold().split())


def _alternative_visible(lead: Mapping[str, Any], plan: Mapping[str, Any]) -> bool:
    alternative = _normalize(plan.get("leading_alternative"))
    haystack = _normalize(
        str(lead.get("title") or "") + " " + str(lead.get("url") or "")
    )
    return bool(alternative and alternative in haystack)


def _lead_order(
    lead: Mapping[str, Any], plan: Mapping[str, Any]
) -> tuple[int | str, ...]:
    target = {
        "row_key": str(plan["row_key"]),
        "column": str(plan["column"]),
        "new_value": str(plan["leading_alternative"]),
    }
    target_score = _target_score(lead, [target])
    coverage = _coverage(lead, plan["query_vector"])[1]
    return (
        *(-int(number) for number in target_score),
        *(-int(number) for number in coverage),
        _source_from_lead(lead),
    )


def _reserve_candidates_from_validated(
    validated: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, str]], int]:
    private = validated["targeted_private_state"]
    plan = private["target_plan"]
    support = parent.validate_recovery_receipt(validated["targeted_support_receipt"])
    selected = [_lead_projection(item) for item in private["selected_targeted_leads"]]
    if (
        plan is None
        or support["safe_change_count_after_targeted_search"]
        > support["safe_change_count_before_targeted_search"]
    ):
        return copy.deepcopy(plan), [], 0
    capacity = max(0, MAXIMUM_TOTAL_TARGETED_FETCHES - len(selected))
    used = {_source_from_lead(item) for item in selected}
    candidates: list[dict[str, str]] = []
    seen = set(used)
    for raw in private["targeted_union_leads"]:
        lead = _lead_projection(raw)
        source = _source_from_lead(lead)
        if source in seen:
            continue
        seen.add(source)
        candidates.append(lead)
    return copy.deepcopy(plan), candidates, capacity


def _reserve_candidates(
    parent_result: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, str]], int]:
    return _reserve_candidates_from_validated(parent.validate_result(parent_result))


def _select_reserve_leads_from_validated(
    validated: Mapping[str, Any],
) -> list[dict[str, str]]:
    plan, candidates, capacity = _reserve_candidates_from_validated(validated)
    if plan is None or capacity <= 0 or not candidates:
        return []
    support = sorted(
        (item for item in candidates if _alternative_visible(item, plan)),
        key=lambda item: _lead_order(item, plan),
    )
    audit = sorted(
        (item for item in candidates if not _alternative_visible(item, plan)),
        key=lambda item: _lead_order(item, plan),
    )
    output: list[dict[str, str]] = []
    if support:
        output.append(copy.deepcopy(support[0]))
    if len(output) < capacity and audit:
        output.append(copy.deepcopy(audit[0]))
    selected_sources = {_source_from_lead(item) for item in output}
    for item in sorted(candidates, key=lambda lead: _lead_order(lead, plan)):
        source = _source_from_lead(item)
        if len(output) >= capacity:
            break
        if source in selected_sources:
            continue
        output.append(copy.deepcopy(item))
        selected_sources.add(source)
    return output


def select_reserve_leads(parent_result: Mapping[str, Any]) -> list[dict[str, str]]:
    """Select support-first plus alternative-blind audit reserve leads."""

    return _select_reserve_leads_from_validated(
        parent.validate_result(parent_result)
    )


def _canonical_reserve_pages(
    batches: Sequence[Mapping[str, Any]], selected: Sequence[Mapping[str, Any]]
) -> list[dict[str, str]]:
    allowed = {_source_from_lead(item) for item in selected}
    pages = _page_vector(batches, prefix="R", page_chars=PAGE_CHARACTER_CAP)
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for page in pages:
        source = _source_key(str(page["host"]))
        if source not in allowed or source in seen:
            continue
        seen.add(source)
        output.append(copy.deepcopy(page))
    if len(output) > len(selected):
        raise ValueError("V2.44.96 reserve page cap drifted")
    return output


def _observation_key(value: Mapping[str, Any]) -> tuple[str, str, str, str]:
    row, column = runtime._target_identity(value["row_key"], value["column"])
    return (
        row,
        column,
        _source_key(str(value["source_host"])),
        credit._normalized_value(value["value"]),
    )


def _new_observation_partition(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> dict[str, int]:
    validated_before = credit.validate_active_evidence_result(before)
    validated_after = credit.validate_active_evidence_result(after)
    before_keys = {
        _observation_key(item) for item in validated_before["active_observations"]
    }
    new = [
        item
        for item in validated_after["active_observations"]
        if _observation_key(item) not in before_keys
    ]
    target = runtime._target_identity(plan["row_key"], plan["column"])
    alternative = credit._normalized_value(plan["leading_alternative"])
    supporting = 0
    conflicting = 0
    other = 0
    for item in new:
        identity = runtime._target_identity(item["row_key"], item["column"])
        if identity != target:
            other += 1
        elif credit._normalized_value(item["value"]) == alternative:
            supporting += 1
        else:
            conflicting += 1
    return {
        "new": len(new),
        "supporting": supporting,
        "conflicting": conflicting,
        "other": other,
    }


def _snapshot(
    validated_parent: Mapping[str, Any], reserve_pages: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    adaptive = parent.parent.validate_result(validated_parent["parent_result"])
    original = parent.parent._original_parent_result(adaptive["parent_result"])
    targeted_pages = validated_parent["targeted_private_state"]["targeted_pages"]
    return parent.parent._snapshot(
        original,
        [
            *parent._parent_adaptive_pages(adaptive),
            *copy.deepcopy(list(targeted_pages)),
            *copy.deepcopy(list(reserve_pages)),
        ],
    )


def _build_receipt(
    validated_parent: Mapping[str, Any],
    selected: Sequence[Mapping[str, Any]],
    pages: Sequence[Mapping[str, Any]],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    support = parent.validate_recovery_receipt(
        validated_parent["targeted_support_receipt"]
    )
    plan = validated_parent["targeted_private_state"]["target_plan"]
    partition = threshold_failure_partition(snapshot["active"])
    if not isinstance(plan, Mapping):
        if selected or pages:
            raise ValueError("V2.44.96 reserve effects exist without target plan")
        observation = {"new": 0, "supporting": 0, "conflicting": 0, "other": 0}
        plan_present = 0
        alternative_visible = 0
    else:
        observation = _new_observation_partition(
            validated_parent["targeted_active_evidence_result"],
            snapshot["active"],
            plan,
        )
        plan_present = 1
        alternative_visible = sum(
            _alternative_visible(item, plan) for item in selected
        )
    candidate_changes = runtime._changed_cells(
        snapshot["baseline_prediction"], snapshot["candidate_prediction"]
    )
    total_selected = support["targeted_selected_source_count"] + len(selected)
    total_pages = support["targeted_usable_page_count"] + len(pages)
    total_observations = support["targeted_new_observation_count"] + observation["new"]
    before_safe = int(support["safe_change_count_after_targeted_search"])
    after_safe = int(snapshot["active"]["receipt"]["safe_change_count"])
    before_information = float(
        support["positive_information_gain_total_nats_after_targeted_search"]
    )
    after_information = float(
        snapshot["active"]["receipt"]["positive_information_gain_total_nats"]
    )
    before_epistemic = float(
        support["epistemic_credit_total_nats_after_targeted_search"]
    )
    after_epistemic = float(
        snapshot["active"]["receipt"]["epistemic_credit_total_nats"]
    )
    before_decision = float(
        support["decision_credit_total_nats_after_targeted_search"]
    )
    after_decision = float(
        snapshot["active"]["receipt"]["decision_credit_total_nats"]
    )
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "targeted_plan_present": plan_present,
        "selected_target_count": int(support["selected_target_count"]),
        "targeted_discovered_source_count": int(
            support["targeted_discovered_source_count"]
        ),
        "targeted_selected_source_count_before_reserve": int(
            support["targeted_selected_source_count"]
        ),
        "targeted_usable_page_count_before_reserve": int(
            support["targeted_usable_page_count"]
        ),
        "targeted_new_observation_count_before_reserve": int(
            support["targeted_new_observation_count"]
        ),
        "reserve_candidate_source_count": len(
            _reserve_candidates_from_validated(validated_parent)[1]
        ),
        "reserve_selected_source_count": len(selected),
        "reserve_alternative_visible_source_count": alternative_visible,
        "reserve_alternative_blind_source_count": len(selected) - alternative_visible,
        "reserve_usable_page_count": len(pages),
        "reserve_new_observation_count": observation["new"],
        "reserve_supporting_target_observation_count": observation["supporting"],
        "reserve_conflicting_target_observation_count": observation["conflicting"],
        "reserve_other_observation_count": observation["other"],
        "total_targeted_selected_source_count": total_selected,
        "total_targeted_usable_page_count": total_pages,
        "total_targeted_new_observation_count": total_observations,
        "support_deficit_before_targeted_search": int(
            support["support_deficit_before_targeted_search"]
        ),
        "safe_change_count_before_targeted_search": int(
            support["safe_change_count_before_targeted_search"]
        ),
        "safe_change_count_before_reserve": before_safe,
        "safe_change_count_after_reserve": after_safe,
        "safe_change_improvement_count": max(0, after_safe - before_safe),
        "safe_change_regression_count": max(0, before_safe - after_safe),
        "candidate_changed_cell_count_after_reserve": len(candidate_changes),
        "positive_information_gain_total_nats_before_reserve": before_information,
        "positive_information_gain_total_nats_after_reserve": after_information,
        "epistemic_credit_total_nats_before_reserve": before_epistemic,
        "epistemic_credit_total_nats_after_reserve": after_epistemic,
        "decision_credit_total_nats_before_reserve": before_decision,
        "decision_credit_total_nats_after_reserve": after_decision,
        "decision_credit_gain_nats": max(0.0, after_decision - before_decision),
        "decision_credit_regression_nats": max(0.0, before_decision - after_decision),
        "threshold_failure_partition_after_reserve": partition,
        "known_baseline_minimum_support_sources": credit.KNOWN_ALTERNATIVE_MINIMUM_SOURCES,
        "unknown_baseline_minimum_support_sources": credit.UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES,
        "minimum_alternative_posterior": credit.MINIMUM_ALTERNATIVE_POSTERIOR,
        "required_support_margin": 1,
        "maximum_total_targeted_fetches": MAXIMUM_TOTAL_TARGETED_FETCHES,
        "additional_logical_queries": 0,
        "additional_search_batches": 0,
        "additional_model_requests": 0,
        "reserve_uses_only_frozen_targeted_discovery_union": True,
        "reserve_sources_disjoint_from_all_prior_selected_sources": True,
        "alternative_blind_reserve_is_a_contradiction_audit_not_negative_evidence": True,
        "all_reserve_observations_enter_unchanged_posterior": True,
        "targeted_pages_used_for_model_prompt_or_candidate_generation": False,
        "posterior_thresholds_and_credit_rules_preserved": True,
        "decision_credit_requires_safe_output_change": True,
        "allocated_credit_used_for_same_run_training_or_policy_update": False,
        "task_query_url_page_prediction_candidate_value_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_reserve_receipt(value)


def validate_reserve_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    partition = copied.get("threshold_failure_partition_after_reserve")
    true_fields = (
        "reserve_uses_only_frozen_targeted_discovery_union",
        "reserve_sources_disjoint_from_all_prior_selected_sources",
        "alternative_blind_reserve_is_a_contradiction_audit_not_negative_evidence",
        "all_reserve_observations_enter_unchanged_posterior",
        "posterior_thresholds_and_credit_rules_preserved",
        "decision_credit_requires_safe_output_change",
    )
    false_fields = (
        "targeted_pages_used_for_model_prompt_or_candidate_generation",
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
        or any(_count(copied.get(name), name) < 0 for name in RECEIPT_COUNT_FIELDS)
        or any(_finite(copied.get(name), name) < 0 for name in RECEIPT_NUMERIC_FIELDS)
        or copied.get("targeted_plan_present") not in {0, 1}
        or copied.get("reserve_alternative_visible_source_count")
        + copied.get("reserve_alternative_blind_source_count")
        != copied.get("reserve_selected_source_count")
        or copied.get("reserve_usable_page_count")
        > copied.get("reserve_selected_source_count")
        or copied.get("reserve_new_observation_count")
        != copied.get("reserve_supporting_target_observation_count")
        + copied.get("reserve_conflicting_target_observation_count")
        + copied.get("reserve_other_observation_count")
        or copied.get("total_targeted_selected_source_count")
        != copied.get("targeted_selected_source_count_before_reserve")
        + copied.get("reserve_selected_source_count")
        or copied.get("total_targeted_usable_page_count")
        != copied.get("targeted_usable_page_count_before_reserve")
        + copied.get("reserve_usable_page_count")
        or copied.get("total_targeted_usable_page_count")
        > copied.get("total_targeted_selected_source_count")
        or copied.get("total_targeted_new_observation_count")
        != copied.get("targeted_new_observation_count_before_reserve")
        + copied.get("reserve_new_observation_count")
        or copied.get("total_targeted_selected_source_count")
        > MAXIMUM_TOTAL_TARGETED_FETCHES
        or copied.get("reserve_selected_source_count")
        > copied.get("reserve_candidate_source_count")
        or copied.get("safe_change_count_after_reserve")
        > copied.get("selected_target_count")
        or copied.get("safe_change_count_before_reserve")
        > copied.get("selected_target_count")
        or copied.get("safe_change_improvement_count")
        != max(
            0,
            copied.get("safe_change_count_after_reserve")
            - copied.get("safe_change_count_before_reserve"),
        )
        or copied.get("safe_change_regression_count")
        != max(
            0,
            copied.get("safe_change_count_before_reserve")
            - copied.get("safe_change_count_after_reserve"),
        )
        or not math.isclose(
            copied.get("decision_credit_gain_nats", -1),
            max(
                0.0,
                copied.get("decision_credit_total_nats_after_reserve", 0.0)
                - copied.get("decision_credit_total_nats_before_reserve", 0.0),
            ),
            abs_tol=1e-12,
        )
        or not math.isclose(
            copied.get("decision_credit_regression_nats", -1),
            max(
                0.0,
                copied.get("decision_credit_total_nats_before_reserve", 0.0)
                - copied.get("decision_credit_total_nats_after_reserve", 0.0),
            ),
            abs_tol=1e-12,
        )
        or copied.get("decision_credit_gain_nats", 0) > 0
        and (
            copied.get("safe_change_improvement_count") == 0
            or copied.get("candidate_changed_cell_count_after_reserve") == 0
        )
        or copied.get("positive_information_gain_total_nats_before_reserve", 0)
        < copied.get("epistemic_credit_total_nats_before_reserve", 0) - 1e-12
        or copied.get("epistemic_credit_total_nats_before_reserve", 0)
        < copied.get("decision_credit_total_nats_before_reserve", 0) - 1e-12
        or copied.get("decision_credit_total_nats_after_reserve", 0)
        > copied.get("epistemic_credit_total_nats_after_reserve", 0) + 1e-12
        or copied.get("epistemic_credit_total_nats_after_reserve", 0)
        > copied.get("positive_information_gain_total_nats_after_reserve", 0)
        + 1e-12
        or copied.get("known_baseline_minimum_support_sources")
        != credit.KNOWN_ALTERNATIVE_MINIMUM_SOURCES
        or copied.get("unknown_baseline_minimum_support_sources")
        != credit.UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
        or copied.get("minimum_alternative_posterior")
        != credit.MINIMUM_ALTERNATIVE_POSTERIOR
        or copied.get("required_support_margin") != 1
        or copied.get("maximum_total_targeted_fetches")
        != MAXIMUM_TOTAL_TARGETED_FETCHES
        or any(copied.get(name) != 0 for name in (
            "additional_logical_queries", "additional_search_batches", "additional_model_requests"
        ))
        or not isinstance(partition, Mapping)
        or tuple(partition) != THRESHOLD_PARTITION_FIELDS
        or any(
            isinstance(partition[name], bool)
            or not isinstance(partition[name], int)
            or partition[name] < 0
            for name in THRESHOLD_PARTITION_FIELDS
        )
        or sum(partition.values()) != copied.get("selected_target_count")
        or partition["safe_change_count"]
        != copied.get("safe_change_count_after_reserve")
        or any(copied.get(name) is not True for name in true_fields)
        or any(copied.get(name) is not False for name in false_fields)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.96 reserve receipt drifted")
    return copied


def _derive_from_validated(
    validated: Mapping[str, Any], private_state: Mapping[str, Any]
) -> dict[str, Any]:
    if set(private_state) != PRIVATE_KEYS:
        raise ValueError("V2.44.96 private state drifted")
    raw_selected = private_state.get("selected_reserve_leads")
    batches = private_state.get("reserve_fetch_batches")
    raw_pages = private_state.get("reserve_pages")
    if not isinstance(raw_selected, list) or not isinstance(batches, list) or not isinstance(raw_pages, list):
        raise ValueError("V2.44.96 private vectors drifted")
    selected = [_lead_projection(item) for item in raw_selected]
    expected = _select_reserve_leads_from_validated(validated)
    if selected != expected:
        raise ValueError("V2.44.96 reserve source selection drifted")
    existing = {
        _source_from_lead(item)
        for item in validated["targeted_private_state"]["selected_targeted_leads"]
    }
    if existing & {_source_from_lead(item) for item in selected}:
        raise ValueError("V2.44.96 reserve source overlaps prior selection")
    pages = _canonical_reserve_pages(batches, selected)
    if raw_pages != pages:
        raise ValueError("V2.44.96 reserve page replay drifted")
    snapshot = _snapshot(validated, pages)
    receipt = _build_receipt(validated, selected, pages, snapshot)
    return {
        "private": {
            "selected_reserve_leads": selected,
            "reserve_fetch_batches": copy.deepcopy(batches),
            "reserve_pages": pages,
        },
        "snapshot": snapshot,
        "receipt": receipt,
    }


def _derive(
    parent_result: Mapping[str, Any], private_state: Mapping[str, Any]
) -> dict[str, Any]:
    return _derive_from_validated(
        parent.validate_result(parent_result), private_state
    )


def _compute_result_from_validated(
    validated: Mapping[str, Any], private_state: Mapping[str, Any]
) -> dict[str, Any]:
    derived = _derive_from_validated(validated, private_state)
    snapshot = derived["snapshot"]
    value = {
        "artifact_version": 1,
        "role": RESULT_ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(validated),
        "candidate_prediction": snapshot["candidate_prediction"],
        "reserve_projection": snapshot["projection"],
        "reserve_active_evidence_result": snapshot["active"],
        "reserve_private_state": derived["private"],
        "reserve_support_receipt": derived["receipt"],
    }
    value["result_sha256"] = payload_sha256(value)
    return value


def _compute_result(
    parent_result: Mapping[str, Any], private_state: Mapping[str, Any]
) -> dict[str, Any]:
    return _compute_result_from_validated(
        parent.validate_result(parent_result), private_state
    )


def validate_result(value: Mapping[str, Any]) -> dict[str, Any]:
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
        or not isinstance(copied.get("reserve_projection"), Mapping)
        or not isinstance(copied.get("reserve_active_evidence_result"), Mapping)
        or not isinstance(copied.get("reserve_private_state"), Mapping)
        or not isinstance(copied.get("reserve_support_receipt"), Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.96 result identity drifted")
    validated_parent = parent.validate_result(copied["parent_result"])
    credit.validate_active_evidence_result(copied["reserve_active_evidence_result"])
    validate_reserve_receipt(copied["reserve_support_receipt"])
    expected = _compute_result_from_validated(
        validated_parent, copied["reserve_private_state"]
    )
    if copied != expected:
        raise ValueError("V2.44.96 result replay drifted")
    return copied


def build_effect_delta_receipt(
    *,
    model_before: Mapping[str, Any],
    model_after: Mapping[str, Any],
    transport_before: Mapping[str, Any],
    transport_after: Mapping[str, Any],
    search_before: Mapping[str, Any],
    search_after: Mapping[str, Any],
    reserve_receipt: Mapping[str, Any],
    expected_model_cap: int,
) -> dict[str, Any]:
    before_model = validate_model_receipt(dict(model_before), expected_cap=expected_model_cap)
    after_model = validate_model_receipt(dict(model_after), expected_cap=expected_model_cap)
    before_transport = validate_transport_health(transport_before)
    after_transport = validate_transport_health(transport_after)
    before_search = dict(search_before)
    after_search = dict(search_after)
    validate_search_receipt(before_search)
    validate_search_receipt(after_search)
    reserve = validate_reserve_receipt(reserve_receipt)
    transport_deltas = {
        name: _counter_delta(before_transport, after_transport, name)
        for name in (
            "hosted_search_attempts",
            "hosted_search_deadline_failures",
            "hard_fetch_helper_calls",
            "fetch_deadline_rejections",
            "hard_fetch_deadline_failures",
            "fetch_helper_failures",
        )
    }
    search_deltas = {
        name: _counter_delta(before_search, after_search, name)
        for name in ("multi_query_chunks", "recursive_split_requests")
    }
    model_observation = {
        "remaining_seconds_at_receipt", "deadline_exhausted", "receipt_payload_sha256"
    }
    model_equal = {
        key: item for key, item in before_model.items() if key not in model_observation
    } == {
        key: item for key, item in after_model.items() if key not in model_observation
    }
    search_shape = {
        key: item
        for key, item in before_search.items()
        if key not in {"multi_query_chunks", "recursive_split_requests", "receipt_payload_sha256"}
    } == {
        key: item
        for key, item in after_search.items()
        if key not in {"multi_query_chunks", "recursive_split_requests", "receipt_payload_sha256"}
    }
    fetch_effects = (
        transport_deltas["hard_fetch_helper_calls"]
        + transport_deltas["fetch_deadline_rejections"]
    )
    value = {
        "artifact_version": 1,
        "role": EFFECT_ROLE,
        "policy_id": POLICY_ID,
        "additional_logical_queries": 0,
        "additional_search_batches": 0,
        "additional_provider_search_attempts": transport_deltas["hosted_search_attempts"],
        "additional_provider_deadline_failures": transport_deltas["hosted_search_deadline_failures"],
        "additional_fetch_attempts": int(reserve["reserve_selected_source_count"]),
        "additional_hard_fetch_helper_calls": transport_deltas["hard_fetch_helper_calls"],
        "additional_fetch_deadline_rejections": transport_deltas["fetch_deadline_rejections"],
        "additional_hard_fetch_deadline_failures": transport_deltas["hard_fetch_deadline_failures"],
        "additional_fetch_helper_failures": transport_deltas["fetch_helper_failures"],
        "additional_fetch_effects": fetch_effects,
        "additional_multi_query_chunks": search_deltas["multi_query_chunks"],
        "additional_recursive_split_requests": search_deltas["recursive_split_requests"],
        "additional_model_acquisitions": int(after_model["acquisitions"])
        - int(before_model["acquisitions"]),
        "model_effect_and_static_fields_equal": model_equal,
        "model_remaining_seconds_nonincreasing": 0.0
        <= float(after_model["remaining_seconds_at_receipt"])
        <= float(before_model["remaining_seconds_at_receipt"]) + 1e-6,
        "model_deadline_state_monotonic": not (
            before_model["deadline_exhausted"] is True
            and after_model["deadline_exhausted"] is False
        ),
        "transport_deadline_state_monotonic": not (
            before_transport["deadline_exhausted"] is True
            and after_transport["deadline_exhausted"] is False
        ),
        "search_shape_fields_equal": search_shape,
        "only_frozen_discovery_reserve_fetch_effects_allowed": True,
        "question_prompt_response_query_url_page_prediction_candidate_value_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
        "reserve_support_receipt_sha256": payload_sha256(reserve),
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_effect_delta_receipt(value)


def validate_effect_delta_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    if (
        set(copied) != EFFECT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != EFFECT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or any(_count(copied.get(name), name) < 0 for name in EFFECT_COUNT_FIELDS)
        or copied.get("additional_logical_queries") != 0
        or copied.get("additional_search_batches") != 0
        or copied.get("additional_provider_search_attempts") != 0
        or copied.get("additional_provider_deadline_failures") != 0
        or copied.get("additional_fetch_effects")
        != copied.get("additional_fetch_attempts")
        or copied.get("additional_fetch_effects")
        != copied.get("additional_hard_fetch_helper_calls")
        + copied.get("additional_fetch_deadline_rejections")
        or copied.get("additional_hard_fetch_deadline_failures")
        + copied.get("additional_fetch_helper_failures")
        > copied.get("additional_hard_fetch_helper_calls")
        or copied.get("additional_multi_query_chunks") != 0
        or copied.get("additional_recursive_split_requests") != 0
        or copied.get("additional_model_acquisitions") != 0
        or any(
            copied.get(name) is not True
            for name in (
                "model_effect_and_static_fields_equal",
                "model_remaining_seconds_nonincreasing",
                "model_deadline_state_monotonic",
                "transport_deadline_state_monotonic",
                "search_shape_fields_equal",
                "only_frozen_discovery_reserve_fetch_effects_allowed",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "question_prompt_response_query_url_page_prediction_candidate_value_or_source_emitted",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or not isinstance(copied.get("reserve_support_receipt_sha256"), str)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.96 effect receipt drifted")
    return copied


def run_v24496_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
) -> IntegratedTargetedReserveOutcome:
    with ExecutionValidationMemo():
        first = parent.run_v24490_task(
            task,
            model=model,
            search=search,
            partition_seed_sha256=partition_seed_sha256,
            limits=limits,
            monotonic=monotonic,
        )
        outcome = _run_reserve_stage_from_v24490_outcome(
            first, model=model, search=search
        )
        result = outcome.reserve_result
        validate_result(result)
    return outcome


def _run_reserve_stage_from_v24490_outcome(
    first: parent.IntegratedEntropyTargetedSupportOutcome,
    *,
    model: Any,
    search: Any,
) -> IntegratedTargetedReserveOutcome:
    """Continue reserve from one typed and already validated V2.44.90 outcome."""

    if not isinstance(first, parent.IntegratedEntropyTargetedSupportOutcome):
        raise TypeError("V2.44.96 reserve continuation requires V2.44.90 outcome")
    before_model = copy.deepcopy(first.model_slot_receipt)
    before_transport = copy.deepcopy(first.transport_health)
    before_search = copy.deepcopy(first.search_single_shot_receipt)
    selected = _select_reserve_leads_from_validated(first.targeted_result)
    batches = list(search.fetch_urls(selected)) if selected else []
    pages = _canonical_reserve_pages(batches, selected)
    private = {
        "selected_reserve_leads": copy.deepcopy(selected),
        "reserve_fetch_batches": copy.deepcopy(batches),
        "reserve_pages": copy.deepcopy(pages),
    }
    result = _compute_result_from_validated(first.targeted_result, private)
    after_model = model.receipt()
    after_transport = search.transport_health()
    after_search = search.single_shot_receipt()
    effect = build_effect_delta_receipt(
        model_before=before_model,
        model_after=after_model,
        transport_before=before_transport,
        transport_after=after_transport,
        search_before=before_search,
        search_after=after_search,
        reserve_receipt=result["reserve_support_receipt"],
        expected_model_cap=int(after_model["slot_cap"]),
    )
    return IntegratedTargetedReserveOutcome(
        parent=first,
        reserve_result=result,
        model_slot_receipt_before_reserve=before_model,
        transport_health_before_reserve=before_transport,
        search_single_shot_receipt_before_reserve=before_search,
        model_slot_receipt=after_model,
        transport_health=after_transport,
        search_single_shot_receipt=after_search,
        effect_delta_receipt=effect,
    )


__all__ = [
    "EFFECT_ROLE",
    "IntegratedTargetedReserveOutcome",
    "MAXIMUM_TOTAL_TARGETED_FETCHES",
    "POLICY_ID",
    "RESULT_ROLE",
    "build_effect_delta_receipt",
    "run_v24496_task",
    "select_reserve_leads",
    "validate_effect_delta_receipt",
    "validate_reserve_receipt",
    "validate_result",
]
