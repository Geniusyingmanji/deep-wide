"""Content-free projection and gate algebra for V2.43.90--91 probes."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from deepwide_agent.v24308_child_exit_observability import validate_parent_receipt
from deepwide_agent.v24391_uncertainty_active_evidence_runner import validate_envelope


SELECTED = 16
MODEL_SLOT_CAP = 2
COMPLETION_KINDS = frozenset(
    {"paired", "identity_no_reserve", "identity_fallback", "None"}
)


def _integer(value: Mapping[str, Any], name: str) -> int:
    item = value.get(name)
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        raise ValueError(f"V2.43.93 invalid content-free count: {name}")
    return item


def _number(value: Mapping[str, Any], name: str) -> float:
    item = value.get(name)
    if (
        isinstance(item, bool)
        or not isinstance(item, (int, float))
        or not math.isfinite(float(item))
        or float(item) < 0
    ):
        raise ValueError(f"V2.43.93 invalid content-free number: {name}")
    return float(item)


TASK_CHECK_NAMES = (
    "parent_success",
    "all_parent_artifacts_valid",
    "effect_accounting_complete",
    "structural_shared_normalization",
    "proposal_two_batch_complete",
    "candidate_independent_active_query_contract",
    "recursive_split_absent",
    "transport_retry_within_frozen_budget",
    "source_budgets_and_disjointness",
    "active_pages_prompt_excluded",
    "target_segment_projection_only",
    "union_effect_replay_complete",
    "posterior_resolution_conservation",
    "parent_active_merge_conservation",
    "entropy_credit_conservation",
    "fetch_budget_transport_conserved",
    "model_slot_conserved",
    "private_replay_valid",
    "deadline_not_exhausted",
)


def task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    active_queries = int(value.get("active_logical_query_count", -1))
    active_batches = int(value.get("active_search_batch_count", -1))
    total_batches = int(value.get("total_search_batch_count", -1))
    hosted_attempts = int(value.get("hosted_search_attempts", -1))
    selected = int(value.get("selected_uncertainty_target_count", -1))
    safe = int(value.get("safe_change_count", -1))
    confirmed = int(value.get("baseline_confirmed_count", -1))
    unresolved = int(value.get("unresolved_count", -1))
    parent_changes = int(value.get("parent_candidate_changed_cell_count", -1))
    reverted = int(value.get("active_reverted_parent_candidate_count", -1))
    overlap = int(
        value.get("active_safe_change_overlapping_parent_target_count", -1)
    )
    final_changes = int(value.get("candidate_changed_cell_count", -1))
    return {
        "parent_success": value.get("parent_taxonomy") == "success",
        "all_parent_artifacts_valid": value.get("all_parent_artifacts_valid")
        is True,
        "effect_accounting_complete": value.get("effect_accounting_complete")
        is True,
        "structural_shared_normalization": value.get(
            "structural_shared_normalization"
        )
        is True,
        "proposal_two_batch_complete": (
            value.get("proposal_logical_query_count") == 4
            and value.get("proposal_search_batch_count") == 2
            and value.get("proposal_batch_logical_query_counts") == [2, 2]
        ),
        "candidate_independent_active_query_contract": (
            0 <= active_queries <= 1
            and active_batches == int(active_queries > 0)
            and selected == active_queries
            and value.get("total_logical_query_count") == 4 + active_queries
            and total_batches == 2 + active_batches
            and value.get("baseline_freeze_precedes_uncertainty_catalog") is True
            and value.get(
                "active_target_selection_requires_preexisting_candidate_change"
            )
            is False
            and value.get("active_queries_use_only_frozen_row_and_column") is True
            and value.get("active_queries_execute_as_one_nonrecursive_batch")
            is True
            and value.get("parent_candidate_used_as_activation_prerequisite")
            is False
        ),
        "recursive_split_absent": value.get("recursive_split_requests") == 0,
        "transport_retry_within_frozen_budget": (
            value.get("parent_provider_search_calls", -1) >= 2
            and value.get("active_provider_search_calls", -1) >= active_batches
            and value.get("total_provider_search_calls")
            == value.get("parent_provider_search_calls")
            + value.get("active_provider_search_calls")
            and value.get("total_provider_search_calls", -1) <= hosted_attempts
            <= 2 * total_batches
        ),
        "source_budgets_and_disjointness": (
            0 <= int(value.get("proposal_source_count", -1)) <= 8
            and 0 <= int(value.get("active_selected_source_count", -1)) <= 2
            and value.get("active_selected_source_count", -1)
            <= value.get("active_discovered_source_count", -1)
            and value.get("active_independent_source_count", -1)
            <= value.get("active_selected_source_count", -1)
            and value.get("active_sources_disjoint_from_proposal_sources") is True
        ),
        "active_pages_prompt_excluded": value.get(
            "active_pages_prompt_excluded"
        )
        is True,
        "target_segment_projection_only": (
            value.get("observations_use_target_segment_programmatic_projection")
            is True
            and value.get("combined_proposal_and_active_evidence_replayed") is True
            and value.get("fixed_reliability_is_uncalibrated_shadow_only") is True
            and value.get("training_or_routing_update_authorized") is False
        ),
        "union_effect_replay_complete": (
            value.get("proposal_union_search_invocations") == 2
            and value.get("proposal_union_logical_query_count") == 4
            and value.get("proposal_union_fetch_requested_source_count")
            == value.get("parent_fetch_calls")
            and value.get("final_union_search_invocations") == total_batches
            and value.get("final_union_logical_query_count")
            == value.get("total_logical_query_count")
            and value.get("final_union_fetch_requested_source_count")
            == value.get("total_fetch_calls")
        ),
        "posterior_resolution_conservation": (
            safe + confirmed + unresolved == selected
            and value.get("candidate_changed_cell_count", -1) >= safe - overlap
            and value.get("positive_epistemic_target_count", -1) <= selected
            and value.get("source_credit_record_count", -1)
            <= value.get("active_observation_count", -1)
        ),
        "parent_active_merge_conservation": (
            0 <= reverted <= parent_changes
            and 0 <= overlap <= min(parent_changes, safe)
            and final_changes == parent_changes - reverted + safe - overlap
        ),
        "entropy_credit_conservation": (
            0.0
            <= float(value.get("decision_credit_total_nats", -1.0))
            <= float(value.get("epistemic_credit_total_nats", -1.0)) + 1e-12
            <= float(value.get("positive_information_gain_total_nats", -1.0))
            + 1e-12
            and (
                float(value.get("decision_credit_total_nats", 0.0)) == 0
                or safe > 0
            )
        ),
        "fetch_budget_transport_conserved": (
            value.get("active_fetch_calls")
            == value.get("active_selected_source_count")
            and value.get("total_fetch_calls")
            == value.get("parent_fetch_calls") + value.get("active_fetch_calls")
            == value.get("hard_fetch_helper_calls")
            + value.get("fetch_deadline_rejections")
            and 0 <= int(value.get("total_fetch_calls", -1)) <= 10
        ),
        "model_slot_conserved": (
            value.get("parent_model_requests") == value.get("model_requests")
            == value.get("slot_acquisitions")
        ),
        "private_replay_valid": value.get("private_replay_valid") is True,
        "deadline_not_exhausted": value.get("deadline_exhausted") is False,
    }


COUNT_FIELDS = (
    "proposal_logical_query_count",
    "proposal_search_batch_count",
    "active_logical_query_count",
    "active_search_batch_count",
    "total_logical_query_count",
    "total_search_batch_count",
    "parent_provider_search_calls",
    "active_provider_search_calls",
    "total_provider_search_calls",
    "single_shot_multi_query_chunks",
    "recursive_split_requests",
    "proposal_discovered_source_count",
    "proposal_unselected_source_count",
    "proposal_source_count",
    "parent_proposal_page_count",
    "proposal_observation_count",
    "proposal_observation_source_count",
    "proposal_ambiguous_source_count",
    "visible_cell_target_count",
    "selected_uncertainty_target_count",
    "active_discovered_source_count",
    "active_selected_source_count",
    "active_page_count",
    "active_observation_count",
    "active_independent_source_count",
    "active_ambiguous_source_count",
    "parent_fetch_calls",
    "active_fetch_calls",
    "total_fetch_calls",
    "proposal_union_search_invocations",
    "proposal_union_logical_query_count",
    "proposal_union_fetch_requested_source_count",
    "final_union_search_invocations",
    "final_union_logical_query_count",
    "final_union_fetch_requested_source_count",
    "safe_change_count",
    "baseline_confirmed_count",
    "unresolved_count",
    "parent_candidate_changed_cell_count",
    "active_reverted_parent_candidate_count",
    "active_safe_change_overlapping_parent_target_count",
    "candidate_changed_cell_count",
    "positive_epistemic_target_count",
    "source_credit_record_count",
    "parent_model_requests",
    "model_requests",
    "model_attempts",
    "model_total_tokens",
    "slot_acquisitions",
    "slot_timeouts",
    "provider_deadline_failures",
    "search_calls",
    "hosted_search_attempts",
    "fetch_failures",
    "hosted_search_deadline_failures",
    "hard_fetch_helper_calls",
    "hard_fetch_deadline_failures",
    "fetch_deadline_rejections",
    "fetch_helper_failures",
)
VECTOR_FIELDS = (
    "proposal_batch_logical_query_counts",
    "proposal_batch_host_counts",
)
BOOLEAN_FIELDS = (
    "all_parent_artifacts_valid",
    "effect_accounting_complete",
    "structural_shared_normalization",
    "baseline_freeze_precedes_uncertainty_catalog",
    "active_target_selection_requires_preexisting_candidate_change",
    "active_queries_use_only_frozen_row_and_column",
    "active_queries_execute_as_one_nonrecursive_batch",
    "active_sources_disjoint_from_proposal_sources",
    "active_pages_prompt_excluded",
    "observations_use_target_segment_programmatic_projection",
    "combined_proposal_and_active_evidence_replayed",
    "fixed_reliability_is_uncalibrated_shadow_only",
    "parent_candidate_used_as_activation_prerequisite",
    "training_or_routing_update_authorized",
    "deadline_exhausted",
    "private_replay_valid",
    "passed",
)
NUMERIC_FIELDS = (
    "wall_seconds",
    "pre_active_entropy_total_nats",
    "combined_entropy_total_nats",
    "positive_information_gain_total_nats",
    "bayesian_surprise_total_nats",
    "epistemic_credit_total_nats",
    "decision_credit_total_nats",
    "slot_total_wait_seconds",
    "slot_max_wait_seconds",
)
TASK_KEYS = frozenset(
    {
        "ordinal",
        "parent_taxonomy",
        "completion_kind",
        "slot_acquisition_counts",
        "checks",
        *COUNT_FIELDS,
        *VECTOR_FIELDS,
        *BOOLEAN_FIELDS,
        *NUMERIC_FIELDS,
    }
)


def task_projection(
    ordinal: int,
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        raise ValueError("V2.43.93 successful parent is missing its envelope")
    validated_parent = validate_parent_receipt(dict(parent))
    validated_envelope = validate_envelope(envelope)
    wrapped = validated_envelope["result"]
    receipt = wrapped["uncertainty_active_receipt"]
    structural_parent = wrapped["parent_result"]
    semantic = structural_parent["semantic_result"]
    core = semantic["core_result"]
    core_receipt = core["shared_prefix_revision_receipt"]
    structural = structural_parent["structural_receipt"]
    private = wrapped["private_replay_state"]
    proposal_state = private["proposal_selection_state"]
    proposal_union = proposal_state["union_receipt_after_proposal_parent"]
    final_union = private["active_union_receipt_after_active"]
    entropy = private["active_evidence_result"]["receipt"]
    slot = validated_envelope["model_slot_receipt"]
    transport = validated_envelope["transport_health"]
    single_shot = validated_envelope["search_single_shot_receipt"]
    model_cost = core["cost"]["model"]
    search_cost = core["cost"]["search"]
    value = {
        "ordinal": ordinal,
        "wall_seconds": round(float(validated_parent["elapsed_seconds"]), 6),
        "parent_taxonomy": validated_parent["failure_taxonomy"],
        "all_parent_artifacts_valid": all(
            validated_parent[name] is True
            for name in (
                "child_terminal_receipt_present",
                "child_terminal_receipt_valid",
                "result_envelope_present",
                "result_envelope_valid",
                "model_receipt_present",
                "model_receipt_valid",
                "transport_receipt_present",
                "transport_receipt_valid",
            )
        ),
        "completion_kind": core["completion_kind"],
        "effect_accounting_complete": core_receipt["effect_accounting_complete"],
        "structural_shared_normalization": structural[
            "same_normalized_baseline_for_baseline_and_candidate"
        ],
        "proposal_logical_query_count": _integer(
            receipt, "proposal_logical_query_count"
        ),
        "proposal_search_batch_count": _integer(
            receipt, "proposal_search_batch_count"
        ),
        "active_logical_query_count": _integer(receipt, "active_logical_query_count"),
        "active_search_batch_count": _integer(receipt, "active_search_batch_count"),
        "total_logical_query_count": _integer(receipt, "total_logical_query_count"),
        "total_search_batch_count": _integer(receipt, "total_search_batch_count"),
        "proposal_batch_logical_query_counts": [
            len(batch) for batch in proposal_state["query_batches"]
        ],
        "parent_provider_search_calls": _integer(
            receipt, "parent_provider_search_calls"
        ),
        "active_provider_search_calls": _integer(
            receipt, "active_provider_search_calls"
        ),
        "total_provider_search_calls": _integer(
            receipt, "total_provider_search_calls"
        ),
        "single_shot_multi_query_chunks": _integer(
            single_shot, "multi_query_chunks"
        ),
        "recursive_split_requests": _integer(single_shot, "recursive_split_requests"),
        "proposal_discovered_source_count": sum(
            len(batch) for batch in proposal_state["raw_batch_leads"]
        ),
        "proposal_unselected_source_count": sum(
            len(batch) for batch in proposal_state["heldout_batch_leads"]
        ),
        "proposal_batch_host_counts": list(receipt["proposal_batch_host_counts"]),
        "proposal_source_count": _integer(receipt, "proposal_source_count"),
        "parent_proposal_page_count": _integer(
            receipt, "parent_proposal_page_count"
        ),
        "proposal_observation_count": _integer(
            receipt, "proposal_observation_count"
        ),
        "proposal_observation_source_count": _integer(
            receipt, "proposal_observation_source_count"
        ),
        "proposal_ambiguous_source_count": _integer(
            receipt, "proposal_ambiguous_source_count"
        ),
        "visible_cell_target_count": _integer(
            receipt, "visible_cell_target_count"
        ),
        "selected_uncertainty_target_count": _integer(
            receipt, "selected_uncertainty_target_count"
        ),
        "active_discovered_source_count": _integer(
            receipt, "active_discovered_source_count"
        ),
        "active_selected_source_count": _integer(
            receipt, "active_selected_source_count"
        ),
        "active_page_count": _integer(receipt, "active_page_count"),
        "active_observation_count": _integer(
            receipt, "active_observation_count"
        ),
        "active_independent_source_count": _integer(
            receipt, "active_independent_source_count"
        ),
        "active_ambiguous_source_count": _integer(
            receipt, "active_ambiguous_source_count"
        ),
        "parent_fetch_calls": _integer(receipt, "parent_fetch_calls"),
        "active_fetch_calls": _integer(receipt, "active_fetch_calls"),
        "total_fetch_calls": _integer(receipt, "total_fetch_calls"),
        "proposal_union_search_invocations": _integer(
            proposal_union, "search_invocations"
        ),
        "proposal_union_logical_query_count": _integer(
            proposal_union, "logical_query_count"
        ),
        "proposal_union_fetch_requested_source_count": _integer(
            proposal_union, "fetch_requested_source_count"
        ),
        "final_union_search_invocations": _integer(
            final_union, "search_invocations"
        ),
        "final_union_logical_query_count": _integer(
            final_union, "logical_query_count"
        ),
        "final_union_fetch_requested_source_count": _integer(
            final_union, "fetch_requested_source_count"
        ),
        "safe_change_count": _integer(receipt, "safe_change_count"),
        "baseline_confirmed_count": _integer(receipt, "baseline_confirmed_count"),
        "unresolved_count": _integer(receipt, "unresolved_count"),
        "parent_candidate_changed_cell_count": _integer(
            receipt, "parent_candidate_changed_cell_count"
        ),
        "active_reverted_parent_candidate_count": _integer(
            receipt, "active_reverted_parent_candidate_count"
        ),
        "active_safe_change_overlapping_parent_target_count": _integer(
            receipt, "active_safe_change_overlapping_parent_target_count"
        ),
        "candidate_changed_cell_count": _integer(
            receipt, "candidate_changed_cell_count"
        ),
        "positive_epistemic_target_count": _integer(
            receipt, "positive_epistemic_target_count"
        ),
        "source_credit_record_count": _integer(
            receipt, "source_credit_record_count"
        ),
        "pre_active_entropy_total_nats": _number(
            receipt, "pre_active_entropy_total_nats"
        ),
        "combined_entropy_total_nats": _number(
            receipt, "combined_entropy_total_nats"
        ),
        "positive_information_gain_total_nats": _number(
            receipt, "positive_information_gain_total_nats"
        ),
        "bayesian_surprise_total_nats": _number(
            receipt, "bayesian_surprise_total_nats"
        ),
        "epistemic_credit_total_nats": _number(
            receipt, "epistemic_credit_total_nats"
        ),
        "decision_credit_total_nats": _number(
            receipt, "decision_credit_total_nats"
        ),
        "baseline_freeze_precedes_uncertainty_catalog": receipt[
            "baseline_freeze_precedes_uncertainty_catalog"
        ],
        "active_target_selection_requires_preexisting_candidate_change": receipt[
            "active_target_selection_requires_preexisting_candidate_change"
        ],
        "active_queries_use_only_frozen_row_and_column": receipt[
            "active_queries_use_only_frozen_row_and_column"
        ],
        "active_queries_execute_as_one_nonrecursive_batch": receipt[
            "active_queries_execute_as_one_nonrecursive_batch"
        ],
        "active_sources_disjoint_from_proposal_sources": receipt[
            "active_sources_disjoint_from_proposal_sources"
        ],
        "active_pages_prompt_excluded": not receipt[
            "active_pages_used_for_model_prompt_or_candidate_generation"
        ],
        "observations_use_target_segment_programmatic_projection": receipt[
            "observations_use_target_segment_programmatic_projection"
        ],
        "combined_proposal_and_active_evidence_replayed": receipt[
            "combined_proposal_and_active_evidence_replayed"
        ],
        "fixed_reliability_is_uncalibrated_shadow_only": receipt[
            "fixed_reliability_is_uncalibrated_shadow_only"
        ],
        "parent_candidate_used_as_activation_prerequisite": receipt[
            "parent_candidate_used_as_activation_prerequisite"
        ],
        "training_or_routing_update_authorized": receipt[
            "training_policy_or_runtime_routing_update_authorized"
        ],
        "parent_model_requests": _integer(receipt, "parent_model_requests"),
        "model_requests": _integer(model_cost, "requests"),
        "model_attempts": _integer(model_cost, "attempts"),
        "model_total_tokens": _integer(model_cost, "total_tokens"),
        "slot_acquisitions": _integer(slot, "acquisitions"),
        "slot_timeouts": _integer(slot, "slot_timeouts"),
        "provider_deadline_failures": _integer(slot, "provider_deadline_failures"),
        "slot_total_wait_seconds": _number(slot, "total_wait_seconds"),
        "slot_max_wait_seconds": _number(slot, "max_wait_seconds"),
        "slot_acquisition_counts": list(slot["slot_acquisition_counts"]),
        "search_calls": _integer(search_cost, "calls"),
        "hosted_search_attempts": _integer(transport, "hosted_search_attempts"),
        "fetch_failures": _integer(search_cost, "fetch_failures"),
        "hosted_search_deadline_failures": _integer(
            transport, "hosted_search_deadline_failures"
        ),
        "hard_fetch_helper_calls": _integer(transport, "hard_fetch_helper_calls"),
        "hard_fetch_deadline_failures": _integer(
            transport, "hard_fetch_deadline_failures"
        ),
        "fetch_deadline_rejections": _integer(
            transport, "fetch_deadline_rejections"
        ),
        "fetch_helper_failures": _integer(transport, "fetch_helper_failures"),
        "deadline_exhausted": transport["deadline_exhausted"] is True,
        "private_replay_valid": (
            entropy["selected_target_count"]
            == receipt["selected_uncertainty_target_count"]
            and entropy["active_observation_count"]
            == receipt["active_observation_count"]
            and entropy["active_independent_source_count"]
            == receipt["active_independent_source_count"]
            and entropy["safe_change_count"] == receipt["safe_change_count"]
            and entropy["baseline_confirmed_count"]
            == receipt["baseline_confirmed_count"]
            and entropy["unresolved_count"] == receipt["unresolved_count"]
            and entropy["positive_epistemic_target_count"]
            == receipt["positive_epistemic_target_count"]
            and entropy["source_credit_record_count"]
            == receipt["source_credit_record_count"]
            and entropy["epistemic_credit_total_nats"]
            == receipt["epistemic_credit_total_nats"]
            and entropy["decision_credit_total_nats"]
            == receipt["decision_credit_total_nats"]
            and len(private["uncertainty_catalog"]["active_queries"])
            == receipt["active_logical_query_count"]
            and isinstance(private["active_observations"], list)
            and isinstance(private["active_pages"], list)
        ),
    }
    value["checks"] = task_checks(value)
    value["passed"] = all(value["checks"].values())
    validate_task_projection(value)
    return value


def validate_task_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    checks = value.get("checks")
    if (
        set(value) != TASK_KEYS
        or isinstance(value.get("ordinal"), bool)
        or not isinstance(value.get("ordinal"), int)
        or not 1 <= value["ordinal"] <= SELECTED
        or not isinstance(value.get("parent_taxonomy"), str)
        or value.get("completion_kind")
        not in {"paired", "identity_no_reserve", "identity_fallback", None}
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in COUNT_FIELDS
        )
        or any(not isinstance(value.get(name), bool) for name in BOOLEAN_FIELDS)
        or any(
            not isinstance(value.get(name), list)
            or len(value[name]) != 2
            or any(
                isinstance(item, bool) or not isinstance(item, int) or item < 0
                for item in value[name]
            )
            for name in VECTOR_FIELDS
        )
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in NUMERIC_FIELDS
        )
        or not isinstance(value.get("slot_acquisition_counts"), list)
        or len(value["slot_acquisition_counts"]) != MODEL_SLOT_CAP
        or any(
            isinstance(item, bool) or not isinstance(item, int) or item < 0
            for item in value["slot_acquisition_counts"]
        )
        or sum(value["slot_acquisition_counts"]) != value["slot_acquisitions"]
        or value["proposal_source_count"]
        != sum(value["proposal_batch_host_counts"])
        or value["proposal_discovered_source_count"]
        != value["proposal_source_count"] + value["proposal_unselected_source_count"]
        or value["parent_provider_search_calls"] != value["search_calls"]
        or not isinstance(checks, Mapping)
        or tuple(checks) != TASK_CHECK_NAMES
        or any(not isinstance(item, bool) for item in checks.values())
        or dict(checks) != task_checks(value)
        or value["passed"] is not all(checks.values())
    ):
        raise RuntimeError("V2.43.93 task projection drifted")
    return dict(value)


def local_failure(ordinal: int) -> dict[str, Any]:
    value: dict[str, Any] = {
        "ordinal": ordinal,
        "wall_seconds": 0.0,
        "parent_taxonomy": "local_projection_failure",
        "completion_kind": None,
        "slot_acquisition_counts": [0] * MODEL_SLOT_CAP,
        "slot_total_wait_seconds": 0.0,
        "slot_max_wait_seconds": 0.0,
    }
    for name in COUNT_FIELDS:
        value[name] = 0
    for name in VECTOR_FIELDS:
        value[name] = [0, 0]
    for name in BOOLEAN_FIELDS:
        value[name] = False
    for name in NUMERIC_FIELDS:
        value[name] = 0.0
    value["deadline_exhausted"] = True
    value["checks"] = task_checks(value)
    value["passed"] = False
    validate_task_projection(value)
    return value


AGGREGATE_CHECK_NAMES = (
    "exact_selected",
    "exact_ordinal_vector",
    "all_tasks_structurally_passed",
    "batch_wall_within_ceiling",
    "slot_timeouts",
    "provider_deadline_failures",
    "hosted_search_deadline_failures",
    "hard_fetch_deadline_failures",
    "fetch_helper_failures",
    "deadline_exhausted_tasks",
    "exact_proposal_two_batch_tasks",
    "zero_recursive_split_tasks",
    "full_proposal_partition_tasks",
    "proposal_source_count_total",
    "candidate_independent_active_query_tasks",
    "two_active_source_tasks",
    "active_page_tasks",
    "active_observation_tasks",
    "positive_epistemic_tasks",
    "safe_change_tasks",
    "baseline_confirmation_tasks",
    "positive_epistemic_credit",
    "decision_credit_consistency",
    "all_private_replay_valid",
    "all_source_partitions_disjoint",
    "all_active_pages_excluded_from_prompt",
    "all_fetch_budgets_conserved",
    "all_model_budgets_conserved",
    "all_union_effects_replayed",
    "all_parent_active_merges_conserved",
    "search_effect_conservation",
)


def aggregate_checks(
    summary: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, bool]:
    value = {
        "exact_selected": summary.get("selected") == SELECTED,
        "exact_ordinal_vector": summary.get("exact_ordinal_vector") is True,
        "all_tasks_structurally_passed": summary["structurally_passed_tasks"]
        == SELECTED,
        "batch_wall_within_ceiling": summary["batch_wall_seconds"]
        <= gates["maximum_batch_wall_seconds"],
        "slot_timeouts": summary["slot_timeouts"]
        <= gates["maximum_slot_timeouts"],
        "provider_deadline_failures": summary["provider_deadline_failures"]
        <= gates["maximum_provider_deadline_failures"],
        "hosted_search_deadline_failures": summary[
            "hosted_search_deadline_failures"
        ]
        <= gates["maximum_hosted_search_deadline_failures"],
        "hard_fetch_deadline_failures": summary["hard_fetch_deadline_failures"]
        <= gates["maximum_hard_fetch_deadline_failures"],
        "fetch_helper_failures": summary["fetch_helper_failures"]
        <= gates["maximum_fetch_helper_failures"],
        "deadline_exhausted_tasks": summary["deadline_exhausted_tasks"]
        <= gates["maximum_deadline_exhausted_tasks"],
        "exact_proposal_two_batch_tasks": summary["exact_proposal_two_batch_tasks"]
        >= gates["minimum_exact_proposal_two_batch_tasks"],
        "zero_recursive_split_tasks": summary["zero_recursive_split_tasks"]
        >= gates["minimum_zero_recursive_split_tasks"],
        "full_proposal_partition_tasks": summary["full_proposal_partition_tasks"]
        >= gates["minimum_full_proposal_partition_tasks"],
        "proposal_source_count_total": summary["proposal_sources"]
        >= gates["minimum_proposal_source_count_total"],
        "candidate_independent_active_query_tasks": summary["active_query_tasks"]
        >= gates["minimum_active_query_tasks"],
        "two_active_source_tasks": summary["two_active_source_tasks"]
        >= gates["minimum_two_active_source_tasks"],
        "active_page_tasks": summary["active_page_tasks"]
        >= gates["minimum_active_page_tasks"],
        "active_observation_tasks": summary["active_observation_tasks"]
        >= gates["minimum_active_observation_tasks"],
        "positive_epistemic_tasks": summary["positive_epistemic_tasks"]
        >= gates["minimum_positive_epistemic_tasks"],
        "safe_change_tasks": summary["safe_change_tasks"]
        >= gates["minimum_safe_change_tasks"],
        "baseline_confirmation_tasks": summary["baseline_confirmation_tasks"]
        >= gates["minimum_baseline_confirmation_tasks"],
        "positive_epistemic_credit": summary["epistemic_credit_total_nats"]
        >= gates["minimum_epistemic_credit_nats"],
        "decision_credit_consistency": (
            0.0
            <= summary["decision_credit_total_nats"]
            <= summary["epistemic_credit_total_nats"] + 1e-12
            and (
                summary["decision_credit_total_nats"] == 0
                or summary["safe_change_count"] > 0
            )
        ),
        "all_private_replay_valid": summary["all_private_replay_valid"] is True,
        "all_source_partitions_disjoint": summary[
            "all_source_partitions_disjoint"
        ]
        is True,
        "all_active_pages_excluded_from_prompt": summary[
            "all_active_pages_excluded_from_prompt"
        ]
        is True,
        "all_fetch_budgets_conserved": summary["all_fetch_budgets_conserved"]
        is True,
        "all_model_budgets_conserved": summary["all_model_budgets_conserved"]
        is True,
        "all_union_effects_replayed": summary["all_union_effects_replayed"]
        is True,
        "all_parent_active_merges_conserved": summary[
            "all_parent_active_merges_conserved"
        ]
        is True,
        "search_effect_conservation": (
            summary["proposal_logical_queries"] == 4 * summary["selected"]
            and summary["active_logical_queries"] == summary["selected"]
            and summary["total_logical_queries"]
            == summary["proposal_logical_queries"]
            + summary["active_logical_queries"]
            and summary["proposal_search_batches"] == 2 * summary["selected"]
            and summary["active_search_batches"] == summary["active_query_tasks"]
            and summary["total_search_batches"]
            == summary["proposal_search_batches"]
            + summary["active_search_batches"]
            and summary["total_provider_search_calls"]
            == summary["parent_provider_search_calls"]
            + summary["active_provider_search_calls"]
            and summary["total_provider_search_calls"]
            <= summary["hosted_search_attempts"]
            <= 2 * summary["total_search_batches"]
        ),
    }
    if tuple(value) != AGGREGATE_CHECK_NAMES:
        raise RuntimeError("V2.43.93 aggregate check order drifted")
    return value


AGGREGATE_COUNT_FIELDS = (
    "selected",
    "terminal_success_tasks",
    "structurally_passed_tasks",
    "exact_proposal_two_batch_tasks",
    "zero_recursive_split_tasks",
    "full_proposal_partition_tasks",
    "active_query_tasks",
    "two_active_source_tasks",
    "active_page_tasks",
    "active_observation_tasks",
    "positive_epistemic_tasks",
    "safe_change_tasks",
    "baseline_confirmation_tasks",
    "proposal_sources",
    "proposal_unselected_sources",
    "active_discovered_sources",
    "active_selected_sources",
    "proposal_pages",
    "proposal_observations",
    "active_pages",
    "active_observations",
    "safe_change_count",
    "baseline_confirmed_count",
    "unresolved_count",
    "parent_candidate_changed_cells",
    "active_reverted_parent_candidate_cells",
    "candidate_changed_cells",
    "positive_epistemic_target_count",
    "source_credit_record_count",
    "proposal_logical_queries",
    "active_logical_queries",
    "total_logical_queries",
    "proposal_search_batches",
    "active_search_batches",
    "total_search_batches",
    "parent_provider_search_calls",
    "active_provider_search_calls",
    "total_provider_search_calls",
    "model_requests",
    "model_attempts",
    "model_total_tokens",
    "slot_acquisitions",
    "slot_timeouts",
    "provider_deadline_failures",
    "hosted_search_attempts",
    "fetch_calls",
    "fetch_failures",
    "hosted_search_deadline_failures",
    "hard_fetch_helper_calls",
    "hard_fetch_deadline_failures",
    "fetch_deadline_rejections",
    "fetch_helper_failures",
    "deadline_exhausted_tasks",
)
AGGREGATE_NUMERIC_FIELDS = (
    "batch_wall_seconds",
    "throughput_tasks_per_minute",
    "pre_active_entropy_total_nats",
    "combined_entropy_total_nats",
    "positive_information_gain_total_nats",
    "bayesian_surprise_total_nats",
    "epistemic_credit_total_nats",
    "decision_credit_total_nats",
    "slot_total_wait_seconds",
    "slot_max_wait_seconds",
)
AGGREGATE_BOOLEAN_FIELDS = (
    "exact_ordinal_vector",
    "all_private_replay_valid",
    "all_source_partitions_disjoint",
    "all_active_pages_excluded_from_prompt",
    "all_fetch_budgets_conserved",
    "all_model_budgets_conserved",
    "all_union_effects_replayed",
    "all_parent_active_merges_conserved",
    "task_identifier_question_query_url_page_prediction_response_candidate_value_or_source_emitted",
    "mapping_gold_category_question_type_split_evaluator_score_or_reward_read",
    "passed",
)
AGGREGATE_KEYS = frozenset(
    {
        *AGGREGATE_COUNT_FIELDS,
        *AGGREGATE_NUMERIC_FIELDS,
        *AGGREGATE_BOOLEAN_FIELDS,
        "completion_kinds",
        "checks",
    }
)


def aggregate_tasks(
    tasks: Sequence[Mapping[str, Any]],
    batch_wall_seconds: float,
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    values = [validate_task_projection(task) for task in tasks]
    values.sort(key=lambda item: item["ordinal"])
    completion = Counter(str(item["completion_kind"]) for item in values)
    summary: dict[str, Any] = {
        "selected": len(values),
        "exact_ordinal_vector": [item["ordinal"] for item in values]
        == list(range(1, SELECTED + 1)),
        "terminal_success_tasks": sum(
            item["parent_taxonomy"] == "success" for item in values
        ),
        "structurally_passed_tasks": sum(item["passed"] for item in values),
        "batch_wall_seconds": round(max(0.0, float(batch_wall_seconds)), 6),
        "throughput_tasks_per_minute": round(
            len(values) / max(float(batch_wall_seconds), 1e-9) * 60, 6
        ),
        "completion_kinds": dict(sorted(completion.items())),
        "exact_proposal_two_batch_tasks": sum(
            item["checks"]["proposal_two_batch_complete"] for item in values
        ),
        "zero_recursive_split_tasks": sum(
            item["checks"]["recursive_split_absent"] for item in values
        ),
        "full_proposal_partition_tasks": sum(
            item["proposal_source_count"] == 8 for item in values
        ),
        "active_query_tasks": sum(
            item["active_logical_query_count"] == 1 for item in values
        ),
        "two_active_source_tasks": sum(
            item["active_selected_source_count"] == 2 for item in values
        ),
        "active_page_tasks": sum(item["active_page_count"] > 0 for item in values),
        "active_observation_tasks": sum(
            item["active_observation_count"] > 0 for item in values
        ),
        "positive_epistemic_tasks": sum(
            item["epistemic_credit_total_nats"] > 0 for item in values
        ),
        "safe_change_tasks": sum(item["safe_change_count"] > 0 for item in values),
        "baseline_confirmation_tasks": sum(
            item["baseline_confirmed_count"] > 0 for item in values
        ),
        "proposal_sources": sum(item["proposal_source_count"] for item in values),
        "proposal_unselected_sources": sum(
            item["proposal_unselected_source_count"] for item in values
        ),
        "active_discovered_sources": sum(
            item["active_discovered_source_count"] for item in values
        ),
        "active_selected_sources": sum(
            item["active_selected_source_count"] for item in values
        ),
        "proposal_pages": sum(item["parent_proposal_page_count"] for item in values),
        "proposal_observations": sum(
            item["proposal_observation_count"] for item in values
        ),
        "active_pages": sum(item["active_page_count"] for item in values),
        "active_observations": sum(
            item["active_observation_count"] for item in values
        ),
        "safe_change_count": sum(item["safe_change_count"] for item in values),
        "baseline_confirmed_count": sum(
            item["baseline_confirmed_count"] for item in values
        ),
        "unresolved_count": sum(item["unresolved_count"] for item in values),
        "parent_candidate_changed_cells": sum(
            item["parent_candidate_changed_cell_count"] for item in values
        ),
        "active_reverted_parent_candidate_cells": sum(
            item["active_reverted_parent_candidate_count"] for item in values
        ),
        "candidate_changed_cells": sum(
            item["candidate_changed_cell_count"] for item in values
        ),
        "positive_epistemic_target_count": sum(
            item["positive_epistemic_target_count"] for item in values
        ),
        "source_credit_record_count": sum(
            item["source_credit_record_count"] for item in values
        ),
        "slot_total_wait_seconds": round(
            sum(item["slot_total_wait_seconds"] for item in values), 6
        ),
        "slot_max_wait_seconds": round(
            max((item["slot_max_wait_seconds"] for item in values), default=0.0), 6
        ),
        "all_private_replay_valid": all(item["private_replay_valid"] for item in values),
        "all_source_partitions_disjoint": all(
            item["active_sources_disjoint_from_proposal_sources"] for item in values
        ),
        "all_active_pages_excluded_from_prompt": all(
            item["active_pages_prompt_excluded"] for item in values
        ),
        "all_fetch_budgets_conserved": all(
            item["checks"]["fetch_budget_transport_conserved"] for item in values
        ),
        "all_model_budgets_conserved": all(
            item["checks"]["model_slot_conserved"] for item in values
        ),
        "all_union_effects_replayed": all(
            item["checks"]["union_effect_replay_complete"] for item in values
        ),
        "all_parent_active_merges_conserved": all(
            item["checks"]["parent_active_merge_conservation"] for item in values
        ),
        "task_identifier_question_query_url_page_prediction_response_candidate_value_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    direct_sum = {
        "proposal_logical_queries": "proposal_logical_query_count",
        "active_logical_queries": "active_logical_query_count",
        "total_logical_queries": "total_logical_query_count",
        "proposal_search_batches": "proposal_search_batch_count",
        "active_search_batches": "active_search_batch_count",
        "total_search_batches": "total_search_batch_count",
        "parent_provider_search_calls": "parent_provider_search_calls",
        "active_provider_search_calls": "active_provider_search_calls",
        "total_provider_search_calls": "total_provider_search_calls",
        "model_requests": "model_requests",
        "model_attempts": "model_attempts",
        "model_total_tokens": "model_total_tokens",
        "slot_acquisitions": "slot_acquisitions",
        "slot_timeouts": "slot_timeouts",
        "provider_deadline_failures": "provider_deadline_failures",
        "hosted_search_attempts": "hosted_search_attempts",
        "fetch_calls": "total_fetch_calls",
        "fetch_failures": "fetch_failures",
        "hosted_search_deadline_failures": "hosted_search_deadline_failures",
        "hard_fetch_helper_calls": "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures": "hard_fetch_deadline_failures",
        "fetch_deadline_rejections": "fetch_deadline_rejections",
        "fetch_helper_failures": "fetch_helper_failures",
    }
    for output, source in direct_sum.items():
        summary[output] = sum(item[source] for item in values)
    for name in (
        "pre_active_entropy_total_nats",
        "combined_entropy_total_nats",
        "positive_information_gain_total_nats",
        "bayesian_surprise_total_nats",
        "epistemic_credit_total_nats",
        "decision_credit_total_nats",
    ):
        summary[name] = round(sum(item[name] for item in values), 12)
    summary["deadline_exhausted_tasks"] = sum(
        item["deadline_exhausted"] for item in values
    )
    checks = aggregate_checks(summary, gates)
    result = {**summary, "checks": checks, "passed": all(checks.values())}
    validate_aggregate(result, gates)
    return result


def validate_aggregate(
    value: Mapping[str, Any], gates: Mapping[str, Any]
) -> dict[str, Any]:
    checks = value.get("checks")
    completion = value.get("completion_kinds")
    task_bounded = (
        "terminal_success_tasks",
        "structurally_passed_tasks",
        "exact_proposal_two_batch_tasks",
        "zero_recursive_split_tasks",
        "full_proposal_partition_tasks",
        "active_query_tasks",
        "two_active_source_tasks",
        "active_page_tasks",
        "active_observation_tasks",
        "positive_epistemic_tasks",
        "safe_change_tasks",
        "baseline_confirmation_tasks",
        "deadline_exhausted_tasks",
    )
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
            not isinstance(value.get(name), bool) for name in AGGREGATE_BOOLEAN_FIELDS
        )
        or not isinstance(completion, Mapping)
        or any(
            name not in COMPLETION_KINDS
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for name, count in completion.items()
        )
        or sum(completion.values()) != value["selected"]
        or any(value[name] > value["selected"] for name in task_bounded)
        or value["proposal_sources"] > 8 * value["selected"]
        or value["active_selected_sources"] > 2 * value["selected"]
        or value["active_selected_sources"] > value["active_discovered_sources"]
        or value["active_pages"] > value["active_selected_sources"]
        or value["total_logical_queries"]
        != value["proposal_logical_queries"] + value["active_logical_queries"]
        or value["total_search_batches"]
        != value["proposal_search_batches"] + value["active_search_batches"]
        or value["total_provider_search_calls"]
        != value["parent_provider_search_calls"]
        + value["active_provider_search_calls"]
        or value["slot_acquisitions"] != value["model_requests"]
        or value["fetch_calls"]
        != value["hard_fetch_helper_calls"] + value["fetch_deadline_rejections"]
        or value[
            "task_identifier_question_query_url_page_prediction_response_candidate_value_or_source_emitted"
        ]
        is not False
        or value[
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        ]
        is not False
        or not isinstance(checks, Mapping)
        or tuple(checks) != AGGREGATE_CHECK_NAMES
        or dict(checks) != aggregate_checks(value, gates)
        or value["passed"] is not all(checks.values())
    ):
        raise RuntimeError("V2.43.93 aggregate drifted")
    return dict(value)


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
