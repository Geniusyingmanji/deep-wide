"""Entropy-conditioned targeted support after frozen adaptive acquisition.

V2.44.88 showed that the V2.44.57 frozen-lead policy can reduce entropy while
leaving the unchanged source-count gate unreachable.  This append-only layer
uses the already validated posterior to select at most one unresolved cell
that has a concrete leading alternative and a bounded support deficit.  It
then issues exactly one non-recursive batch of two label-blind queries derived
only from the frozen row, column, and leading alternative.  At most three new
sources, disjoint from every proposal, active, and adaptive source, are
fetched and projected programmatically.  Targeted pages never enter a model
prompt.

The known/unknown source-count thresholds, posterior threshold, support
margin, posterior update, leave-one-out epistemic credit, and decision-credit
gate are unchanged.  No benchmark label, mapping, gold answer, evaluator,
reward, score, or credential is available to this module.
"""

from __future__ import annotations

import copy
import math
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from . import v24388_uncertainty_credit as credit
from . import v24390_uncertainty_active_evidence_runtime as runtime
from . import v24457_adaptive_entropy_support as parent
from .v24269_task_union_discovery import (
    TaskUnionDiscoverySearchClient,
    validate_receipt as validate_union_receipt,
)
from .v24280_task_union_single_shot import validate_receipt as validate_search_receipt
from .v24312_deadline_reliability import validate_receipt as validate_model_receipt
from .v24316_deadline_search import validate_transport_health
from .v24323_shared_prefix_cell_entropy import payload_sha256
from .v24325_shared_prefix_revision_runtime import _page_vector
from .v24333_programmatic_support_catalog import _source_key
from .v24355_explicit_partition_runtime import _source_from_lead
from .v24371_batch_stratified_verifier_runtime import _coverage, _unique_host_leads
from .v24378_adaptive_heldout_verifier_runtime import _lead_projection, _target_score
from .v24447_third_source_entropy_to_decision import threshold_failure_partition


POLICY_ID = "v24490_entropy_conditioned_targeted_support_search_v1"
RESULT_ROLE = "v24490_entropy_targeted_support_result"
PLAN_ROLE = "v24490_entropy_target_plan"
RECEIPT_ROLE = "v24490_entropy_targeted_support_receipt"
EFFECT_ROLE = "v24490_entropy_targeted_effect_delta"
MAXIMUM_TARGETED_CELLS = 1
MAXIMUM_TARGETED_LOGICAL_QUERIES = 2
MAXIMUM_TARGETED_SEARCH_BATCHES = 1
MAXIMUM_TARGETED_SOURCES = 3
MAXIMUM_PROVIDER_ATTEMPTS_PER_BATCH = 2
PAGE_CHARACTER_CAP = 5_000

PLAN_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "target_binding_sha256",
        "row_key",
        "column",
        "leading_alternative",
        "leading_alternative_hypothesis",
        "combined_entropy_nats",
        "current_alternative_support_count",
        "current_alternative_active_support_count",
        "current_alternative_posterior_probability",
        "current_alternative_support_margin",
        "required_support_count",
        "support_deficit",
        "maximum_targeted_fetches",
        "query_vector",
        "selection_uses_only_validated_posterior_entropy_and_support_deficit",
        "queries_use_only_frozen_row_column_and_leading_alternative",
        "benchmark_label_mapping_gold_evaluator_score_or_reward_read",
        "plan_payload_sha256",
    }
)
PRIVATE_KEYS = frozenset(
    {
        "target_plan",
        "targeted_union_leads",
        "selected_targeted_leads",
        "targeted_fetch_batches",
        "targeted_pages",
        "targeted_union_receipt",
    }
)
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_policy_id",
        "targeted_cell_count",
        "selected_target_count",
        "targeted_logical_query_count",
        "targeted_search_batch_count",
        "targeted_discovered_source_count",
        "targeted_selected_source_count",
        "targeted_usable_page_count",
        "targeted_new_observation_count",
        "support_deficit_before_targeted_search",
        "safe_change_count_before_targeted_search",
        "safe_change_count_after_targeted_search",
        "candidate_changed_cell_count_after_targeted_search",
        "positive_information_gain_total_nats_after_targeted_search",
        "epistemic_credit_total_nats_after_targeted_search",
        "decision_credit_total_nats_after_targeted_search",
        "threshold_failure_partition_after_targeted_search",
        "known_baseline_minimum_support_sources",
        "unknown_baseline_minimum_support_sources",
        "minimum_alternative_posterior",
        "required_support_margin",
        "maximum_targeted_cells",
        "maximum_targeted_logical_queries",
        "maximum_targeted_search_batches",
        "maximum_targeted_sources",
        "additional_model_requests",
        "target_selection_uses_current_validated_entropy_and_support_deficit",
        "one_nonrecursive_targeted_search_batch",
        "new_sources_disjoint_from_all_proposal_active_and_adaptive_sources",
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
EFFECT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "target_plan_present",
        "additional_logical_queries",
        "additional_search_batches",
        "additional_union_search_invocations",
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
        "model_effect_and_static_fields_equal",
        "model_remaining_seconds_nonincreasing",
        "model_deadline_state_monotonic",
        "transport_deadline_state_monotonic",
        "union_receipt_sha256",
        "one_bounded_targeted_batch_only",
        "only_source_disjoint_targeted_page_effects_allowed",
        "question_prompt_response_query_url_page_prediction_candidate_value_or_source_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_sha256",
    }
)
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "parent_result",
        "candidate_prediction",
        "targeted_projection",
        "targeted_active_evidence_result",
        "targeted_private_state",
        "targeted_support_receipt",
        "result_sha256",
    }
)


@dataclass(frozen=True)
class IntegratedEntropyTargetedSupportOutcome:
    parent: parent.IntegratedAdaptiveEntropySupportOutcome
    targeted_result: dict[str, Any]
    model_slot_receipt_before_targeted_support: dict[str, Any]
    transport_health_before_targeted_support: dict[str, Any]
    search_single_shot_receipt_before_targeted_support: dict[str, Any]
    model_slot_receipt: dict[str, Any]
    transport_health: dict[str, Any]
    search_single_shot_receipt: dict[str, Any]
    effect_delta_receipt: dict[str, Any]


def _finite(value: object, label: str, *, nonnegative: bool = True) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or nonnegative
        and float(value) < 0
    ):
        raise ValueError(f"V2.44.90 {label} is invalid")
    return float(value)


def _count(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"V2.44.90 {label} is invalid")
    return value


def _counter_delta(before: Mapping[str, Any], after: Mapping[str, Any], name: str) -> int:
    left = _count(before.get(name), f"before {name}")
    right = _count(after.get(name), f"after {name}")
    if right < left:
        raise ValueError(f"V2.44.90 {name} decreased")
    return right - left


def _query_vector(row: str, column: str, alternative: str) -> list[str]:
    visible = row + column + alternative
    suffixes = (
        ("官方 记录 独立 来源", "历史 档案 独立 来源")
        if any("\u4e00" <= character <= "\u9fff" for character in visible)
        else ("official record independent source", "historical archive independent source")
    )
    queries = [
        f'"{row}" "{column}" "{alternative}" {suffix}'[:1_200]
        for suffix in suffixes
    ]
    if any(not query for query in queries) or len(set(item.casefold() for item in queries)) != 2:
        raise ValueError("V2.44.90 targeted query vector drifted")
    return queries


def _target_and_resolution(
    active_result: Mapping[str, Any], binding: str
) -> tuple[dict[str, Any], dict[str, Any]]:
    validated = credit.validate_active_evidence_result(active_result)
    targets = {
        str(item["target_binding_sha256"]): item
        for item in validated["catalog"]["targets"]
    }
    resolutions = {
        str(item["target_binding_sha256"]): item
        for item in validated["resolutions"]
    }
    target = targets.get(binding)
    resolution = resolutions.get(binding)
    if target is None or resolution is None:
        raise ValueError("V2.44.90 target binding is absent")
    return target, resolution


def _target_candidate(
    active_result: Mapping[str, Any], binding: str
) -> dict[str, Any] | None:
    validated = credit.validate_active_evidence_result(active_result)
    target, resolution = _target_and_resolution(validated, binding)
    if resolution["status"] == "safe_change":
        return None
    active_votes, _ambiguous = credit._bound_votes(
        target, validated["active_observations"]
    )
    hypotheses, _prior, proposal_posterior = credit._expanded_frozen_belief(
        target, active_votes
    )
    combined = credit._posterior_from_base(
        proposal_posterior, hypotheses, active_votes
    )
    combined_votes = [*target["proposal_votes"], *active_votes]
    counts = Counter(str(item["hypothesis"]) for item in combined_votes)
    active_counts = Counter(str(item["hypothesis"]) for item in active_votes)
    alternatives = [
        item for item in hypotheses if item not in {credit.CURRENT, credit.OTHER}
    ]
    alternative = max(
        alternatives,
        key=lambda item: (
            counts[item],
            combined[hypotheses.index(item)],
            item,
        ),
        default=None,
    )
    if alternative is None or counts[alternative] <= 0 or active_counts[alternative] <= 0:
        return None
    displays = sorted(
        {
            str(item["value"])
            for item in combined_votes
            if item["hypothesis"] == alternative
        },
        key=lambda item: (credit._normalized_value(item), len(item), item),
    )
    if not displays:
        return None
    support = counts[alternative]
    active_support = active_counts[alternative]
    probability = combined[hypotheses.index(alternative)]
    competitor = max(
        [
            counts[credit.CURRENT],
            *(counts[item] for item in alternatives if item != alternative),
        ],
        default=0,
    )
    margin = support - competitor
    required = (
        credit.UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
        if target["baseline_unknown"]
        else credit.KNOWN_ALTERNATIVE_MINIMUM_SOURCES
    )
    deficit = max(0, required - support)
    if (
        deficit <= 0
        or deficit > MAXIMUM_TARGETED_SOURCES
        or support != int(resolution["selected_alternative_support_count"])
        or active_support
        != int(resolution["selected_alternative_active_support_count"])
        or not math.isclose(
            probability,
            float(resolution["selected_alternative_posterior_probability"]),
            abs_tol=2e-12,
        )
        or margin != int(resolution["selected_alternative_support_margin"])
    ):
        return None
    return {
        "binding": binding,
        "target": target,
        "resolution": resolution,
        "alternative_hypothesis": alternative,
        "alternative_display": displays[0],
        "support": support,
        "active_support": active_support,
        "probability": probability,
        "margin": margin,
        "required": required,
        "deficit": deficit,
    }


def build_target_plan(
    active_result: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Select one replayable support-deficit target from validated state."""

    validated = credit.validate_active_evidence_result(active_result)
    candidates = [
        candidate
        for resolution in validated["resolutions"]
        if (
            candidate := _target_candidate(
                validated, str(resolution["target_binding_sha256"])
            )
        )
        is not None
    ]
    if not candidates:
        return None
    chosen = min(
        candidates,
        key=lambda item: (
            -float(item["resolution"]["combined_entropy_nats"]),
            -int(item["deficit"]),
            -int(item["support"]),
            str(item["binding"]),
        ),
    )
    target = chosen["target"]
    row = " ".join(str(target["row_key"]).split()).strip()
    column = " ".join(str(target["column"]).split()).strip()
    alternative = " ".join(str(chosen["alternative_display"]).split()).strip()
    value = {
        "artifact_version": 1,
        "role": PLAN_ROLE,
        "policy_id": POLICY_ID,
        "target_binding_sha256": str(chosen["binding"]),
        "row_key": row,
        "column": column,
        "leading_alternative": alternative,
        "leading_alternative_hypothesis": str(chosen["alternative_hypothesis"]),
        "combined_entropy_nats": float(chosen["resolution"]["combined_entropy_nats"]),
        "current_alternative_support_count": int(chosen["support"]),
        "current_alternative_active_support_count": int(chosen["active_support"]),
        "current_alternative_posterior_probability": round(
            float(chosen["probability"]), 12
        ),
        "current_alternative_support_margin": int(chosen["margin"]),
        "required_support_count": int(chosen["required"]),
        "support_deficit": int(chosen["deficit"]),
        "maximum_targeted_fetches": int(chosen["deficit"]),
        "query_vector": _query_vector(row, column, alternative),
        "selection_uses_only_validated_posterior_entropy_and_support_deficit": True,
        "queries_use_only_frozen_row_column_and_leading_alternative": True,
        "benchmark_label_mapping_gold_evaluator_score_or_reward_read": False,
    }
    value["plan_payload_sha256"] = payload_sha256(value)
    return validate_target_plan(value, active_result=validated)


def validate_target_plan(
    value: Mapping[str, Any], *, active_result: Mapping[str, Any]
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("plan_payload_sha256", None)
    if (
        set(copied) != PLAN_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != PLAN_ROLE
        or copied.get("policy_id") != POLICY_ID
        or not isinstance(copied.get("row_key"), str)
        or not copied.get("row_key")
        or not isinstance(copied.get("column"), str)
        or not copied.get("column")
        or not isinstance(copied.get("leading_alternative"), str)
        or not copied.get("leading_alternative")
        or _finite(copied.get("combined_entropy_nats"), "combined entropy") < 0
        or _count(copied.get("support_deficit"), "support deficit") < 1
        or copied.get("support_deficit") > MAXIMUM_TARGETED_SOURCES
        or copied.get("maximum_targeted_fetches") != copied.get("support_deficit")
        or not isinstance(copied.get("query_vector"), list)
        or len(copied["query_vector"]) != MAXIMUM_TARGETED_LOGICAL_QUERIES
        or copied["query_vector"]
        != _query_vector(
            copied["row_key"], copied["column"], copied["leading_alternative"]
        )
        or copied.get(
            "selection_uses_only_validated_posterior_entropy_and_support_deficit"
        )
        is not True
        or copied.get(
            "queries_use_only_frozen_row_column_and_leading_alternative"
        )
        is not True
        or copied.get("benchmark_label_mapping_gold_evaluator_score_or_reward_read")
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.90 target plan drifted")
    expected = build_target_plan_without_validation(active_result)
    if expected is None or copied != expected:
        raise ValueError("V2.44.90 target plan replay drifted")
    return copied


def build_target_plan_without_validation(
    active_result: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Internal replay helper avoiding validation recursion."""

    validated = credit.validate_active_evidence_result(active_result)
    candidates = []
    for resolution in validated["resolutions"]:
        candidate = _target_candidate(
            validated, str(resolution["target_binding_sha256"])
        )
        if candidate is not None:
            candidates.append(candidate)
    if not candidates:
        return None
    chosen = min(
        candidates,
        key=lambda item: (
            -float(item["resolution"]["combined_entropy_nats"]),
            -int(item["deficit"]),
            -int(item["support"]),
            str(item["binding"]),
        ),
    )
    target = chosen["target"]
    row = " ".join(str(target["row_key"]).split()).strip()
    column = " ".join(str(target["column"]).split()).strip()
    alternative = " ".join(str(chosen["alternative_display"]).split()).strip()
    value = {
        "artifact_version": 1,
        "role": PLAN_ROLE,
        "policy_id": POLICY_ID,
        "target_binding_sha256": str(chosen["binding"]),
        "row_key": row,
        "column": column,
        "leading_alternative": alternative,
        "leading_alternative_hypothesis": str(chosen["alternative_hypothesis"]),
        "combined_entropy_nats": float(chosen["resolution"]["combined_entropy_nats"]),
        "current_alternative_support_count": int(chosen["support"]),
        "current_alternative_active_support_count": int(chosen["active_support"]),
        "current_alternative_posterior_probability": round(
            float(chosen["probability"]), 12
        ),
        "current_alternative_support_margin": int(chosen["margin"]),
        "required_support_count": int(chosen["required"]),
        "support_deficit": int(chosen["deficit"]),
        "maximum_targeted_fetches": int(chosen["deficit"]),
        "query_vector": _query_vector(row, column, alternative),
        "selection_uses_only_validated_posterior_entropy_and_support_deficit": True,
        "queries_use_only_frozen_row_column_and_leading_alternative": True,
        "benchmark_label_mapping_gold_evaluator_score_or_reward_read": False,
    }
    value["plan_payload_sha256"] = payload_sha256(value)
    return value


def _legacy_private(parent_result: Mapping[str, Any]) -> Mapping[str, Any]:
    validated = parent.validate_result(parent_result)
    original = parent._original_parent_result(validated["parent_result"])
    anchored = original["parent_result"]
    structured = anchored["parent_result"]
    legacy = structured["parent_result"]
    private = legacy["private_replay_state"]
    if not isinstance(private, Mapping):
        raise ValueError("V2.44.90 legacy private state is absent")
    return private


def _used_sources(parent_result: Mapping[str, Any]) -> set[str]:
    validated = parent.validate_result(parent_result)
    private = _legacy_private(validated)
    sources: set[str] = set()
    proposal_state = private["proposal_selection_state"]
    for name in (
        "raw_batch_leads",
        "proposal_batch_leads",
        "heldout_batch_leads",
    ):
        for batch in proposal_state[name]:
            sources.update(_source_from_lead(lead) for lead in batch)
    sources.update(
        _source_from_lead(lead) for lead in private["active_union_leads"]
    )
    sources.update(
        _source_from_lead(lead)
        for lead in validated["adaptive_private_state"]["selected_adaptive_leads"]
    )
    for observation in validated["adaptive_active_evidence_result"][
        "active_observations"
    ]:
        sources.add(_source_key(str(observation["source_host"])))
    return sources


def _select_targeted_leads(
    leads: Sequence[Mapping[str, Any]],
    plan: Mapping[str, Any],
    *,
    excluded_sources: set[str],
) -> list[dict[str, str]]:
    available: dict[str, dict[str, str]] = {}
    for raw in leads:
        lead = _lead_projection(raw)
        source = _source_from_lead(lead)
        if source in excluded_sources or source in available:
            continue
        available[source] = lead
    target = {
        "row_key": str(plan["row_key"]),
        "column": str(plan["column"]),
        "new_value": str(plan["leading_alternative"]),
    }
    ranked = sorted(
        available.values(),
        key=lambda lead: (
            tuple(-number for number in _target_score(lead, [target])),
            tuple(-number for number in _coverage(lead, plan["query_vector"])[1]),
            _source_from_lead(lead),
        ),
    )
    return [
        copy.deepcopy(item)
        for item in ranked[: int(plan["maximum_targeted_fetches"])]
    ]


def _canonical_targeted_pages(
    batches: Sequence[Mapping[str, Any]],
    selected: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    allowed = {_source_from_lead(item) for item in selected}
    pages = _page_vector(batches, prefix="Z", page_chars=PAGE_CHARACTER_CAP)
    output: list[dict[str, str]] = []
    seen: set[str] = set()
    for page in pages:
        source = _source_key(str(page["host"]))
        if source not in allowed or source in seen:
            continue
        seen.add(source)
        output.append(copy.deepcopy(page))
    if len(output) > len(selected) or len(output) > MAXIMUM_TARGETED_SOURCES:
        raise ValueError("V2.44.90 targeted page cap drifted")
    return output


def _parent_adaptive_pages(parent_result: Mapping[str, Any]) -> list[dict[str, Any]]:
    validated = parent.validate_result(parent_result)
    return [
        copy.deepcopy(page)
        for vector in validated["adaptive_private_state"]["adaptive_step_pages"]
        for page in vector
    ]


def _observation_key(value: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        runtime._target_identity(value["row_key"], value["column"])[0],
        runtime._target_identity(value["row_key"], value["column"])[1],
        _source_key(str(value["source_host"])),
        credit._normalized_value(value["value"]),
    )


def _build_receipt(
    parent_result: Mapping[str, Any],
    plan: Mapping[str, Any] | None,
    union_leads: Sequence[Mapping[str, Any]],
    selected: Sequence[Mapping[str, Any]],
    pages: Sequence[Mapping[str, Any]],
    snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    validated = parent.validate_result(parent_result)
    before = validated["adaptive_active_evidence_result"]
    after = snapshot["active"]
    before_keys = {_observation_key(item) for item in before["active_observations"]}
    after_keys = {_observation_key(item) for item in after["active_observations"]}
    candidate_changes = runtime._changed_cells(
        snapshot["baseline_prediction"], snapshot["candidate_prediction"]
    )
    value = {
        "artifact_version": 1,
        "role": RECEIPT_ROLE,
        "policy_id": POLICY_ID,
        "parent_policy_id": parent.POLICY_ID,
        "targeted_cell_count": int(plan is not None),
        "selected_target_count": int(after["receipt"]["selected_target_count"]),
        "targeted_logical_query_count": len(plan["query_vector"]) if plan else 0,
        "targeted_search_batch_count": int(plan is not None),
        "targeted_discovered_source_count": len(union_leads),
        "targeted_selected_source_count": len(selected),
        "targeted_usable_page_count": len(pages),
        "targeted_new_observation_count": len(after_keys - before_keys),
        "support_deficit_before_targeted_search": int(plan["support_deficit"])
        if plan
        else 0,
        "safe_change_count_before_targeted_search": int(
            before["receipt"]["safe_change_count"]
        ),
        "safe_change_count_after_targeted_search": int(
            after["receipt"]["safe_change_count"]
        ),
        "candidate_changed_cell_count_after_targeted_search": len(candidate_changes),
        "positive_information_gain_total_nats_after_targeted_search": float(
            after["receipt"]["positive_information_gain_total_nats"]
        ),
        "epistemic_credit_total_nats_after_targeted_search": float(
            after["receipt"]["epistemic_credit_total_nats"]
        ),
        "decision_credit_total_nats_after_targeted_search": float(
            after["receipt"]["decision_credit_total_nats"]
        ),
        "threshold_failure_partition_after_targeted_search": threshold_failure_partition(
            after
        ),
        "known_baseline_minimum_support_sources": credit.KNOWN_ALTERNATIVE_MINIMUM_SOURCES,
        "unknown_baseline_minimum_support_sources": credit.UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES,
        "minimum_alternative_posterior": credit.MINIMUM_ALTERNATIVE_POSTERIOR,
        "required_support_margin": 1,
        "maximum_targeted_cells": MAXIMUM_TARGETED_CELLS,
        "maximum_targeted_logical_queries": MAXIMUM_TARGETED_LOGICAL_QUERIES,
        "maximum_targeted_search_batches": MAXIMUM_TARGETED_SEARCH_BATCHES,
        "maximum_targeted_sources": MAXIMUM_TARGETED_SOURCES,
        "additional_model_requests": 0,
        "target_selection_uses_current_validated_entropy_and_support_deficit": True,
        "one_nonrecursive_targeted_search_batch": True,
        "new_sources_disjoint_from_all_proposal_active_and_adaptive_sources": True,
        "targeted_pages_used_for_model_prompt_or_candidate_generation": False,
        "posterior_thresholds_and_credit_rules_preserved": True,
        "decision_credit_requires_safe_output_change": True,
        "allocated_credit_used_for_same_run_training_or_policy_update": False,
        "task_query_url_page_prediction_candidate_value_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    validate_recovery_receipt(value)
    return value


def validate_recovery_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    counts = (
        "targeted_cell_count",
        "selected_target_count",
        "targeted_logical_query_count",
        "targeted_search_batch_count",
        "targeted_discovered_source_count",
        "targeted_selected_source_count",
        "targeted_usable_page_count",
        "targeted_new_observation_count",
        "support_deficit_before_targeted_search",
        "safe_change_count_before_targeted_search",
        "safe_change_count_after_targeted_search",
        "candidate_changed_cell_count_after_targeted_search",
        "known_baseline_minimum_support_sources",
        "unknown_baseline_minimum_support_sources",
        "required_support_margin",
        "maximum_targeted_cells",
        "maximum_targeted_logical_queries",
        "maximum_targeted_search_batches",
        "maximum_targeted_sources",
        "additional_model_requests",
    )
    numeric = (
        "positive_information_gain_total_nats_after_targeted_search",
        "epistemic_credit_total_nats_after_targeted_search",
        "decision_credit_total_nats_after_targeted_search",
        "minimum_alternative_posterior",
    )
    partition = copied.get("threshold_failure_partition_after_targeted_search")
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != RECEIPT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("parent_policy_id") != parent.POLICY_ID
        or any(_count(copied.get(name), name) < 0 for name in counts)
        or any(_finite(copied.get(name), name) < 0 for name in numeric)
        or copied.get("targeted_cell_count") not in {0, 1}
        or copied.get("targeted_logical_query_count")
        != copied.get("targeted_cell_count") * MAXIMUM_TARGETED_LOGICAL_QUERIES
        or copied.get("targeted_search_batch_count")
        != copied.get("targeted_cell_count")
        or copied.get("targeted_selected_source_count")
        > copied.get("targeted_discovered_source_count")
        or copied.get("targeted_selected_source_count") > MAXIMUM_TARGETED_SOURCES
        or copied.get("targeted_usable_page_count")
        > copied.get("targeted_selected_source_count")
        or copied.get("support_deficit_before_targeted_search")
        > MAXIMUM_TARGETED_SOURCES
        or copied.get("known_baseline_minimum_support_sources")
        != credit.KNOWN_ALTERNATIVE_MINIMUM_SOURCES
        or copied.get("unknown_baseline_minimum_support_sources")
        != credit.UNKNOWN_ALTERNATIVE_MINIMUM_SOURCES
        or copied.get("minimum_alternative_posterior")
        != credit.MINIMUM_ALTERNATIVE_POSTERIOR
        or copied.get("required_support_margin") != 1
        or copied.get("maximum_targeted_cells") != MAXIMUM_TARGETED_CELLS
        or copied.get("maximum_targeted_logical_queries")
        != MAXIMUM_TARGETED_LOGICAL_QUERIES
        or copied.get("maximum_targeted_search_batches")
        != MAXIMUM_TARGETED_SEARCH_BATCHES
        or copied.get("maximum_targeted_sources") != MAXIMUM_TARGETED_SOURCES
        or copied.get("additional_model_requests") != 0
        or not isinstance(partition, Mapping)
        or tuple(partition) != (
            "insufficient_support_count",
            "no_active_support_count",
            "posterior_below_threshold_count",
            "support_margin_below_threshold_count",
            "safe_change_count",
        )
        or sum(int(item) for item in partition.values())
        != copied.get("selected_target_count")
        or copied.get("decision_credit_total_nats_after_targeted_search", 0)
        > copied.get("epistemic_credit_total_nats_after_targeted_search", 0) + 1e-12
        or copied.get("decision_credit_total_nats_after_targeted_search", 0) > 0
        and copied.get("safe_change_count_after_targeted_search") == 0
        or any(
            copied.get(name) is not True
            for name in (
                "target_selection_uses_current_validated_entropy_and_support_deficit",
                "one_nonrecursive_targeted_search_batch",
                "new_sources_disjoint_from_all_proposal_active_and_adaptive_sources",
                "posterior_thresholds_and_credit_rules_preserved",
                "decision_credit_requires_safe_output_change",
            )
        )
        or any(
            copied.get(name) is not False
            for name in (
                "targeted_pages_used_for_model_prompt_or_candidate_generation",
                "allocated_credit_used_for_same_run_training_or_policy_update",
                "task_query_url_page_prediction_candidate_value_or_source_emitted",
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
                "benchmark_launch_or_evaluator_authorized",
            )
        )
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.90 recovery receipt drifted")
    return copied


def _derive(
    parent_result: Mapping[str, Any], private_state: Mapping[str, Any]
) -> dict[str, Any]:
    validated = parent.validate_result(parent_result)
    if set(private_state) != PRIVATE_KEYS:
        raise ValueError("V2.44.90 private state identity drifted")
    expected_plan = build_target_plan_without_validation(
        validated["adaptive_active_evidence_result"]
    )
    raw_plan = private_state.get("target_plan")
    if expected_plan is None:
        if raw_plan is not None:
            raise ValueError("V2.44.90 unexpected target plan")
        plan = None
    else:
        if not isinstance(raw_plan, Mapping):
            raise ValueError("V2.44.90 target plan is absent")
        plan = validate_target_plan(
            raw_plan, active_result=validated["adaptive_active_evidence_result"]
        )
    raw_leads = private_state.get("targeted_union_leads")
    raw_selected = private_state.get("selected_targeted_leads")
    batches = private_state.get("targeted_fetch_batches")
    raw_pages = private_state.get("targeted_pages")
    union_receipt = private_state.get("targeted_union_receipt")
    if (
        not isinstance(raw_leads, list)
        or not isinstance(raw_selected, list)
        or not isinstance(batches, list)
        or not isinstance(raw_pages, list)
        or not isinstance(union_receipt, Mapping)
    ):
        raise ValueError("V2.44.90 private vector drifted")
    validate_union_receipt(union_receipt)
    leads = [_lead_projection(item) for item in raw_leads]
    excluded = _used_sources(validated)
    expected_selected = (
        _select_targeted_leads(leads, plan, excluded_sources=excluded)
        if plan is not None
        else []
    )
    if raw_selected != expected_selected:
        raise ValueError("V2.44.90 targeted source selection drifted")
    selected_sources = {_source_from_lead(item) for item in expected_selected}
    if selected_sources & excluded:
        raise ValueError("V2.44.90 targeted source overlaps frozen sources")
    rebuilt_pages = _canonical_targeted_pages(batches, expected_selected)
    if raw_pages != rebuilt_pages:
        raise ValueError("V2.44.90 targeted page replay drifted")
    expected_search = int(plan is not None)
    expected_queries = len(plan["query_vector"]) if plan else 0
    if (
        union_receipt.get("search_invocations") != expected_search
        or union_receipt.get("logical_query_count") != expected_queries
        or union_receipt.get("returned_union_batch_count") > expected_search
        or union_receipt.get("fetch_invocations") != int(bool(expected_selected))
        or union_receipt.get("fetch_requested_source_count") != len(expected_selected)
    ):
        raise ValueError("V2.44.90 targeted union accounting drifted")
    original = parent._original_parent_result(validated["parent_result"])
    snapshot = parent._snapshot(
        original, [*_parent_adaptive_pages(validated), *rebuilt_pages]
    )
    receipt = _build_receipt(
        validated, plan, leads, expected_selected, rebuilt_pages, snapshot
    )
    canonical_private = {
        "target_plan": copy.deepcopy(plan),
        "targeted_union_leads": leads,
        "selected_targeted_leads": expected_selected,
        "targeted_fetch_batches": copy.deepcopy(batches),
        "targeted_pages": rebuilt_pages,
        "targeted_union_receipt": copy.deepcopy(dict(union_receipt)),
    }
    return {
        "private": canonical_private,
        "snapshot": snapshot,
        "receipt": receipt,
    }


def _compute_result(
    parent_result: Mapping[str, Any], private_state: Mapping[str, Any]
) -> dict[str, Any]:
    validated = parent.validate_result(parent_result)
    derived = _derive(validated, private_state)
    snapshot = derived["snapshot"]
    value = {
        "artifact_version": 1,
        "role": RESULT_ROLE,
        "policy_id": POLICY_ID,
        "parent_result": copy.deepcopy(validated),
        "candidate_prediction": snapshot["candidate_prediction"],
        "targeted_projection": snapshot["projection"],
        "targeted_active_evidence_result": snapshot["active"],
        "targeted_private_state": derived["private"],
        "targeted_support_receipt": derived["receipt"],
    }
    value["result_sha256"] = payload_sha256(value)
    return value


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
        or not isinstance(copied.get("targeted_projection"), Mapping)
        or not isinstance(copied.get("targeted_active_evidence_result"), Mapping)
        or not isinstance(copied.get("targeted_private_state"), Mapping)
        or not isinstance(copied.get("targeted_support_receipt"), Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.90 result identity drifted")
    parent.validate_result(copied["parent_result"])
    credit.validate_active_evidence_result(copied["targeted_active_evidence_result"])
    validate_recovery_receipt(copied["targeted_support_receipt"])
    expected = _compute_result(
        copied["parent_result"], copied["targeted_private_state"]
    )
    if copied != expected:
        raise ValueError("V2.44.90 result replay drifted")
    return copied


def build_effect_delta_receipt(
    *,
    model_before: Mapping[str, Any],
    model_after: Mapping[str, Any],
    transport_before: Mapping[str, Any],
    transport_after: Mapping[str, Any],
    search_before: Mapping[str, Any],
    search_after: Mapping[str, Any],
    union_receipt: Mapping[str, Any],
    plan: Mapping[str, Any] | None,
    expected_model_cap: int,
) -> dict[str, Any]:
    before_model = validate_model_receipt(
        dict(model_before), expected_cap=expected_model_cap
    )
    after_model = validate_model_receipt(
        dict(model_after), expected_cap=expected_model_cap
    )
    before_transport = validate_transport_health(transport_before)
    after_transport = validate_transport_health(transport_after)
    before_search = dict(search_before)
    after_search = dict(search_after)
    validate_search_receipt(before_search)
    validate_search_receipt(after_search)
    union = dict(union_receipt)
    validate_union_receipt(union)
    model_observation = {
        "remaining_seconds_at_receipt",
        "deadline_exhausted",
        "receipt_payload_sha256",
    }
    model_equal = {
        key: item for key, item in before_model.items() if key not in model_observation
    } == {
        key: item for key, item in after_model.items() if key not in model_observation
    }
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
    fetch_effects = (
        transport_deltas["hard_fetch_helper_calls"]
        + transport_deltas["fetch_deadline_rejections"]
    )
    value = {
        "artifact_version": 1,
        "role": EFFECT_ROLE,
        "policy_id": POLICY_ID,
        "target_plan_present": plan is not None,
        "additional_logical_queries": len(plan["query_vector"]) if plan else 0,
        "additional_search_batches": int(plan is not None),
        "additional_union_search_invocations": int(union["search_invocations"]),
        "additional_provider_search_attempts": transport_deltas[
            "hosted_search_attempts"
        ],
        "additional_provider_deadline_failures": transport_deltas[
            "hosted_search_deadline_failures"
        ],
        "additional_fetch_attempts": int(union["fetch_requested_source_count"]),
        "additional_hard_fetch_helper_calls": transport_deltas[
            "hard_fetch_helper_calls"
        ],
        "additional_fetch_deadline_rejections": transport_deltas[
            "fetch_deadline_rejections"
        ],
        "additional_hard_fetch_deadline_failures": transport_deltas[
            "hard_fetch_deadline_failures"
        ],
        "additional_fetch_helper_failures": transport_deltas[
            "fetch_helper_failures"
        ],
        "additional_fetch_effects": fetch_effects,
        "additional_multi_query_chunks": search_deltas["multi_query_chunks"],
        "additional_recursive_split_requests": search_deltas[
            "recursive_split_requests"
        ],
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
        "union_receipt_sha256": payload_sha256(union),
        "one_bounded_targeted_batch_only": True,
        "only_source_disjoint_targeted_page_effects_allowed": True,
        "question_prompt_response_query_url_page_prediction_candidate_value_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
        "benchmark_launch_or_evaluator_authorized": False,
    }
    value["receipt_sha256"] = payload_sha256(value)
    return validate_effect_delta_receipt(value)


def validate_effect_delta_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_sha256", None)
    counts = (
        "additional_logical_queries",
        "additional_search_batches",
        "additional_union_search_invocations",
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
    present = copied.get("target_plan_present") is True
    if (
        set(copied) != EFFECT_KEYS
        or copied.get("artifact_version") != 1
        or copied.get("role") != EFFECT_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("target_plan_present") not in {True, False}
        or any(_count(copied.get(name), name) < 0 for name in counts)
        or copied.get("additional_logical_queries")
        != int(present) * MAXIMUM_TARGETED_LOGICAL_QUERIES
        or copied.get("additional_search_batches") != int(present)
        or copied.get("additional_union_search_invocations") != int(present)
        or copied.get("additional_provider_search_attempts")
        > int(present) * MAXIMUM_PROVIDER_ATTEMPTS_PER_BATCH
        or copied.get("additional_provider_deadline_failures")
        > copied.get("additional_provider_search_attempts")
        or copied.get("additional_fetch_attempts") > MAXIMUM_TARGETED_SOURCES
        or copied.get("additional_fetch_effects")
        != copied.get("additional_hard_fetch_helper_calls")
        + copied.get("additional_fetch_deadline_rejections")
        or copied.get("additional_fetch_effects")
        != copied.get("additional_fetch_attempts")
        or copied.get("additional_hard_fetch_deadline_failures")
        + copied.get("additional_fetch_helper_failures")
        > copied.get("additional_hard_fetch_helper_calls")
        or copied.get("additional_multi_query_chunks") > int(present)
        or copied.get("additional_recursive_split_requests") != 0
        or copied.get("additional_model_acquisitions") != 0
        or any(
            copied.get(name) is not True
            for name in (
                "model_effect_and_static_fields_equal",
                "model_remaining_seconds_nonincreasing",
                "model_deadline_state_monotonic",
                "transport_deadline_state_monotonic",
                "one_bounded_targeted_batch_only",
                "only_source_disjoint_targeted_page_effects_allowed",
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
        or not isinstance(copied.get("union_receipt_sha256"), str)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.44.90 effect delta receipt drifted")
    return copied


def run_v24490_task(
    task: Mapping[str, Any],
    *,
    model: Any,
    search: Any,
    partition_seed_sha256: str,
    limits: Any,
    monotonic: Callable[[], float],
) -> IntegratedEntropyTargetedSupportOutcome:
    first = parent.run_v24457_task(
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
    plan = build_target_plan(first.adaptive_result["adaptive_active_evidence_result"])
    union = TaskUnionDiscoverySearchClient(search)
    if plan is None:
        leads: list[dict[str, str]] = []
        selected: list[dict[str, str]] = []
        fetched: list[dict[str, Any]] = []
        pages: list[dict[str, str]] = []
    else:
        raw = union.search_many(
            plan["query_vector"],
            max_results=6,
            search_depth="advanced",
            include_raw_content=False,
        )
        leads = _unique_host_leads(raw, batch_ordinal=4)
        selected = _select_targeted_leads(
            leads, plan, excluded_sources=_used_sources(first.adaptive_result)
        )
        fetched = list(union.fetch_urls(selected)) if selected else []
        pages = _canonical_targeted_pages(fetched, selected)
    union_receipt = union.receipt()
    private = {
        "target_plan": copy.deepcopy(plan),
        "targeted_union_leads": copy.deepcopy(leads),
        "selected_targeted_leads": copy.deepcopy(selected),
        "targeted_fetch_batches": copy.deepcopy(fetched),
        "targeted_pages": copy.deepcopy(pages),
        "targeted_union_receipt": union_receipt,
    }
    result = _compute_result(first.adaptive_result, private)
    validate_result(result)
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
        union_receipt=union_receipt,
        plan=plan,
        expected_model_cap=int(after_model["slot_cap"]),
    )
    return IntegratedEntropyTargetedSupportOutcome(
        parent=first,
        targeted_result=result,
        model_slot_receipt_before_targeted_support=before_model,
        transport_health_before_targeted_support=before_transport,
        search_single_shot_receipt_before_targeted_support=before_search,
        model_slot_receipt=after_model,
        transport_health=after_transport,
        search_single_shot_receipt=after_search,
        effect_delta_receipt=effect,
    )


__all__ = [
    "EFFECT_ROLE",
    "IntegratedEntropyTargetedSupportOutcome",
    "MAXIMUM_TARGETED_CELLS",
    "MAXIMUM_TARGETED_LOGICAL_QUERIES",
    "MAXIMUM_TARGETED_SEARCH_BATCHES",
    "MAXIMUM_TARGETED_SOURCES",
    "POLICY_ID",
    "RESULT_ROLE",
    "build_effect_delta_receipt",
    "build_target_plan",
    "run_v24490_task",
    "validate_effect_delta_receipt",
    "validate_recovery_receipt",
    "validate_result",
    "validate_target_plan",
]
