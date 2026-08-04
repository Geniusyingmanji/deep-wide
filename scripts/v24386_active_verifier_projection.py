"""Content-free projection and gate algebra for the V2.43.86 probe."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from deepwide_agent.v24308_child_exit_observability import validate_parent_receipt
from deepwide_agent.v24384_active_verifier_query_runner import validate_envelope


SELECTED = 16
MODEL_SLOT_CAP = 2
COMPLETION_KINDS = frozenset(
    {"paired", "identity_no_reserve", "identity_fallback", "None"}
)
STATUS_NAMES = (
    "verified_candidate",
    "no_independent_candidate_support",
    "verifier_supports_baseline",
    "independent_conflict",
    "nonpositive_proposal_entropy",
)


def _integer(value: Mapping[str, Any], name: str) -> int:
    item = value.get(name)
    if isinstance(item, bool) or not isinstance(item, int) or item < 0:
        raise ValueError(f"V2.43.86 invalid content-free count: {name}")
    return item


def _number(value: Mapping[str, Any], name: str) -> float:
    item = value.get(name)
    if (
        isinstance(item, bool)
        or not isinstance(item, (int, float))
        or not math.isfinite(float(item))
        or float(item) < 0
    ):
        raise ValueError(f"V2.43.86 invalid content-free number: {name}")
    return float(item)


TASK_CHECK_NAMES = (
    "parent_success",
    "all_parent_artifacts_valid",
    "effect_accounting_complete",
    "structural_shared_normalization",
    "proposal_two_batch_complete",
    "active_query_contract_complete",
    "recursive_split_absent",
    "transport_retry_within_frozen_budget",
    "source_budgets_and_disjointness",
    "active_verifier_prompt_excluded",
    "active_verifier_no_new_candidate",
    "parent_support_ids_reused",
    "union_effect_replay_complete",
    "active_retention_conservation",
    "verification_record_conservation",
    "selected_verification_conservation",
    "entropy_credit_conservation",
    "fetch_budget_transport_conserved",
    "model_slot_conserved",
    "private_replay_valid",
    "deadline_not_exhausted",
)


def task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    verification_total = sum(
        int(value.get(f"{name}_records", -1)) for name in STATUS_NAMES
    )
    selected_total = sum(
        int(value.get(f"selected_{name}_changes", -1)) for name in STATUS_NAMES
    )
    active_queries = int(value.get("active_verifier_logical_query_count", -1))
    active_batches = int(value.get("active_verifier_search_batch_count", -1))
    total_batches = int(value.get("total_search_batch_count", -1))
    hosted_attempts = int(value.get("hosted_search_attempts", -1))
    before = int(value.get("candidate_changed_cells_before_active_verifier", -1))
    after = int(value.get("candidate_changed_cells_after_active_verifier", -1))
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
        "active_query_contract_complete": (
            0 <= active_queries <= 2
            and active_batches == int(active_queries > 0)
            and value.get("entropy_ranked_target_count") == active_queries
            and value.get("total_logical_query_count") == 4 + active_queries
            and total_batches == 2 + active_batches
            and value.get(
                "candidate_and_support_freeze_precedes_active_query_generation"
            )
            is True
            and value.get("proposal_entropy_ranks_active_query_targets") is True
            and value.get("active_queries_use_only_frozen_row_column_value") is True
            and value.get("active_queries_execute_as_one_nonrecursive_batch")
            is True
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
            and value.get("active_verifier_sources_disjoint_from_proposal_sources")
            is True
        ),
        "active_verifier_prompt_excluded": value.get(
            "active_verifier_prompt_excluded"
        )
        is True,
        "active_verifier_no_new_candidate": value.get(
            "active_verifier_no_new_candidate"
        )
        is True,
        "parent_support_ids_reused": value.get("parent_support_ids_reused")
        is True,
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
        "active_retention_conservation": (
            0 <= after <= before
            and value.get("active_verifier_reverted_cells") == before - after
            and value.get("active_verifier_admitted_cells") == after
            and value.get("selected_verified_candidate_changes") == after
        ),
        "verification_record_conservation": (
            verification_total == value.get("verification_record_count")
            and value.get("verification_record_count")
            == value.get("parent_eligible_support_set_count")
        ),
        "selected_verification_conservation": (
            selected_total == value.get("selected_exactly_bound_candidate_changes")
            and value.get("selection_resolution_count")
            + value.get("candidate_changes_without_declaration")
            == before
            and value.get("selected_exactly_bound_candidate_changes", -1)
            <= value.get("selection_resolution_count", -1)
        ),
        "entropy_credit_conservation": (
            0.0
            <= float(value.get("utility_aligned_entropy_credit_nats", -1.0))
            <= float(value.get("selected_proposal_entropy_nats", -1.0)) + 1e-12
            <= float(value.get("proposal_support_entropy_total_nats", -1.0))
            + 1e-12
        ),
        "fetch_budget_transport_conserved": (
            value.get("active_verifier_fetch_calls")
            == value.get("active_selected_source_count")
            and value.get("total_fetch_calls")
            == value.get("parent_fetch_calls")
            + value.get("active_verifier_fetch_calls")
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
    "active_verifier_logical_query_count",
    "active_verifier_search_batch_count",
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
    "active_discovered_source_count",
    "active_selected_source_count",
    "candidate_change_count",
    "entropy_ranked_target_count",
    "parent_proposal_page_count",
    "active_verifier_page_count",
    "parent_fetch_calls",
    "active_verifier_fetch_calls",
    "total_fetch_calls",
    "proposal_union_search_invocations",
    "proposal_union_logical_query_count",
    "proposal_union_fetch_requested_source_count",
    "final_union_search_invocations",
    "final_union_logical_query_count",
    "final_union_fetch_requested_source_count",
    "parent_eligible_support_set_count",
    "candidate_changed_cells_before_active_verifier",
    "candidate_changed_cells_after_active_verifier",
    "selection_resolution_count",
    "candidate_changes_without_declaration",
    "selected_exactly_bound_candidate_changes",
    "active_verifier_admitted_cells",
    "active_verifier_reverted_cells",
    "verification_record_count",
    *(f"{name}_records" for name in STATUS_NAMES),
    *(f"selected_{name}_changes" for name in STATUS_NAMES),
    "verifier_semantic_projection_count",
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
VECTOR_FIELDS = ("proposal_batch_logical_query_counts", "proposal_batch_host_counts")
BOOLEAN_FIELDS = (
    "all_parent_artifacts_valid",
    "effect_accounting_complete",
    "structural_shared_normalization",
    "candidate_and_support_freeze_precedes_active_query_generation",
    "proposal_entropy_ranks_active_query_targets",
    "active_queries_use_only_frozen_row_column_value",
    "active_queries_execute_as_one_nonrecursive_batch",
    "active_verifier_sources_disjoint_from_proposal_sources",
    "active_verifier_prompt_excluded",
    "active_verifier_no_new_candidate",
    "parent_support_ids_reused",
    "target_segment_entity_boundary_enforced",
    "parent_semantic_catalog_present",
    "deadline_exhausted",
    "private_replay_valid",
    "passed",
)
NUMERIC_FIELDS = (
    "wall_seconds",
    "proposal_support_entropy_total_nats",
    "selected_proposal_entropy_nats",
    "utility_aligned_entropy_credit_nats",
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
        raise ValueError("V2.43.86 successful parent is missing its envelope")
    validated_parent = validate_parent_receipt(dict(parent))
    validated_envelope = validate_envelope(envelope)
    wrapped = validated_envelope["result"]
    receipt = wrapped["active_verifier_receipt"]
    structural_parent = wrapped["parent_result"]
    semantic = structural_parent["semantic_result"]
    core = semantic["core_result"]
    core_receipt = core["shared_prefix_revision_receipt"]
    structural = structural_parent["structural_receipt"]
    private = wrapped["private_replay_state"]
    proposal_state = private["proposal_selection_state"]
    target_state = private["active_target_state"]
    proposal_union = proposal_state["union_receipt_after_proposal_parent"]
    final_union = private["active_union_receipt_after_active"]
    proposal_catalog = semantic["semantic_active_private_state"][
        "semantic_active_catalog"
    ]
    base_catalog = proposal_catalog["active_catalog"]["base_catalog"]
    slot = validated_envelope["model_slot_receipt"]
    transport = validated_envelope["transport_health"]
    single_shot = validated_envelope["search_single_shot_receipt"]
    model_cost = core["cost"]["model"]
    search_cost = core["cost"]["search"]
    statuses = receipt["verification_status_counts"]
    selected = receipt["selected_verification_status_counts"]
    before = _integer(receipt, "candidate_changed_cells_before_active_verifier")
    after = _integer(receipt, "candidate_changed_cells_after_active_verifier")
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
        "active_verifier_logical_query_count": _integer(
            receipt, "active_verifier_logical_query_count"
        ),
        "active_verifier_search_batch_count": _integer(
            receipt, "active_verifier_search_batch_count"
        ),
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
        "active_discovered_source_count": _integer(
            receipt, "active_discovered_source_count"
        ),
        "active_selected_source_count": _integer(
            receipt, "active_selected_source_count"
        ),
        "candidate_change_count": _integer(receipt, "candidate_change_count"),
        "entropy_ranked_target_count": _integer(
            receipt, "entropy_ranked_target_count"
        ),
        "parent_proposal_page_count": _integer(
            receipt, "parent_proposal_page_count"
        ),
        "active_verifier_page_count": _integer(
            receipt, "active_verifier_page_count"
        ),
        "parent_fetch_calls": _integer(receipt, "parent_fetch_calls"),
        "active_verifier_fetch_calls": _integer(
            receipt, "active_verifier_fetch_calls"
        ),
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
        "parent_semantic_catalog_present": isinstance(proposal_catalog, Mapping),
        "parent_eligible_support_set_count": _integer(
            base_catalog, "eligible_support_set_count"
        ),
        "candidate_changed_cells_before_active_verifier": before,
        "candidate_changed_cells_after_active_verifier": after,
        "selection_resolution_count": _integer(receipt, "selection_resolution_count"),
        "candidate_changes_without_declaration": _integer(
            receipt, "candidate_changes_without_declaration"
        ),
        "selected_exactly_bound_candidate_changes": _integer(
            receipt, "selected_exactly_bound_candidate_changes"
        ),
        "active_verifier_admitted_cells": _integer(
            receipt, "active_verifier_admitted_cells"
        ),
        "active_verifier_reverted_cells": _integer(
            receipt, "active_verifier_reverted_cells"
        ),
        "verification_record_count": _integer(receipt, "verification_record_count"),
        **{
            f"{name}_records": int(statuses.get(name, 0))
            for name in STATUS_NAMES
        },
        **{
            f"selected_{name}_changes": int(selected.get(name, 0))
            for name in STATUS_NAMES
        },
        "verifier_semantic_projection_count": _integer(
            receipt, "verifier_semantic_projection_count"
        ),
        "proposal_support_entropy_total_nats": _number(
            receipt, "proposal_support_entropy_total_nats"
        ),
        "selected_proposal_entropy_nats": _number(
            receipt, "selected_proposal_conditional_entropy_reduction_nats"
        ),
        "utility_aligned_entropy_credit_nats": _number(
            receipt, "utility_aligned_entropy_credit_nats"
        ),
        "candidate_and_support_freeze_precedes_active_query_generation": receipt[
            "candidate_and_support_freeze_precedes_active_query_generation"
        ],
        "proposal_entropy_ranks_active_query_targets": receipt[
            "proposal_entropy_ranks_active_query_targets"
        ],
        "active_queries_use_only_frozen_row_column_value": receipt[
            "active_queries_use_only_frozen_row_column_value"
        ],
        "active_queries_execute_as_one_nonrecursive_batch": receipt[
            "active_queries_execute_as_one_nonrecursive_batch"
        ],
        "active_verifier_sources_disjoint_from_proposal_sources": receipt[
            "active_verifier_sources_disjoint_from_proposal_sources"
        ],
        "active_verifier_prompt_excluded": not receipt[
            "active_verifier_pages_used_for_candidate_generation_or_model_prompt"
        ],
        "active_verifier_no_new_candidate": not receipt[
            "new_candidate_value_generated_by_active_verifier"
        ],
        "parent_support_ids_reused": receipt[
            "parent_support_set_ids_reused_without_rebuild"
        ],
        "target_segment_entity_boundary_enforced": receipt[
            "target_segment_entity_boundary_enforced"
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
            len(target_state["entropy_ranked_targets"])
            == len(target_state["active_queries"])
            and isinstance(private["target_segment_utility_catalog"], Mapping)
            and isinstance(private["cell_utility_resolutions"], list)
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
        or value["candidate_change_count"]
        != value["candidate_changed_cells_before_active_verifier"]
        or value["parent_provider_search_calls"] != value["search_calls"]
        or not isinstance(checks, Mapping)
        or tuple(checks) != TASK_CHECK_NAMES
        or any(not isinstance(item, bool) for item in checks.values())
        or dict(checks) != task_checks(value)
        or value["passed"] is not all(checks.values())
    ):
        raise RuntimeError("V2.43.86 task projection drifted")
    return dict(value)


def local_failure(ordinal: int) -> dict[str, Any]:
    value: dict[str, Any] = {
        "ordinal": ordinal,
        "wall_seconds": 0.0,
        "parent_taxonomy": "local_projection_failure",
        "completion_kind": None,
        "slot_acquisition_counts": [0] * MODEL_SLOT_CAP,
        "proposal_support_entropy_total_nats": 0.0,
        "selected_proposal_entropy_nats": 0.0,
        "utility_aligned_entropy_credit_nats": 0.0,
        "slot_total_wait_seconds": 0.0,
        "slot_max_wait_seconds": 0.0,
    }
    for name in COUNT_FIELDS:
        value[name] = 0
    for name in VECTOR_FIELDS:
        value[name] = [0, 0]
    for name in BOOLEAN_FIELDS:
        value[name] = False
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
    "parent_semantic_catalog_tasks",
    "active_query_tasks",
    "active_selected_sources",
    "active_verifier_pages",
    "parent_candidate_tasks",
    "selected_bound_candidate_tasks",
    "utility_aligned_tasks",
    "final_nonidentity_tasks",
    "selected_verified_candidate_changes",
    "active_retained_candidate_changed_cells",
    "selected_proposal_entropy",
    "utility_aligned_entropy",
    "selected_verified_final_alignment",
    "active_retention_conservation",
    "verification_record_conservation",
    "selected_verification_conservation",
    "entropy_credit_conservation",
    "all_private_replay_valid",
    "all_source_partitions_disjoint",
    "all_active_pages_excluded_from_parent_prompt",
    "all_active_verifier_final_decisions",
    "all_fetch_budgets_conserved",
    "all_model_budgets_conserved",
    "all_union_effects_replayed",
    "search_effect_conservation",
)


def aggregate_checks(summary: Mapping[str, Any], gates: Mapping[str, Any]) -> dict[str, bool]:
    value = {
        "exact_selected": summary.get("selected") == SELECTED,
        "exact_ordinal_vector": summary.get("exact_ordinal_vector") is True,
        "all_tasks_structurally_passed": summary["structurally_passed_tasks"]
        == SELECTED,
        "batch_wall_within_ceiling": summary["batch_wall_seconds"]
        <= gates["maximum_batch_wall_seconds"],
        "slot_timeouts": summary["slot_timeouts"] <= gates["maximum_slot_timeouts"],
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
        "parent_semantic_catalog_tasks": summary["parent_semantic_catalog_tasks"]
        >= gates["minimum_parent_semantic_catalog_tasks"],
        "active_query_tasks": summary["active_query_tasks"]
        >= gates["minimum_active_query_tasks"],
        "active_selected_sources": summary["active_selected_sources"]
        >= gates["minimum_active_selected_sources"],
        "active_verifier_pages": summary["active_verifier_pages"]
        >= gates["minimum_active_verifier_pages"],
        "parent_candidate_tasks": summary["parent_candidate_tasks"]
        >= gates["minimum_parent_candidate_tasks"],
        "selected_bound_candidate_tasks": summary["selected_bound_candidate_tasks"]
        >= gates["minimum_selected_bound_candidate_tasks"],
        "utility_aligned_tasks": summary["utility_aligned_tasks"]
        >= gates["minimum_utility_aligned_tasks"],
        "final_nonidentity_tasks": summary["final_nonidentity_tasks"]
        >= gates["minimum_final_nonidentity_tasks"],
        "selected_verified_candidate_changes": summary[
            "selected_verified_candidate_changes"
        ]
        >= gates["minimum_selected_verified_candidate_changes"],
        "active_retained_candidate_changed_cells": summary[
            "candidate_changed_cells_after_active_verifier"
        ]
        >= gates["minimum_active_retained_candidate_changed_cells"],
        "selected_proposal_entropy": summary["selected_proposal_entropy_nats"]
        >= gates["minimum_selected_proposal_entropy_nats"],
        "utility_aligned_entropy": summary["utility_aligned_entropy_credit_nats"]
        >= gates["minimum_utility_aligned_entropy_nats"],
        "selected_verified_final_alignment": summary[
            "selected_verified_candidate_changes"
        ]
        == summary["candidate_changed_cells_after_active_verifier"],
        "active_retention_conservation": summary[
            "candidate_changed_cells_after_active_verifier"
        ]
        == summary["candidate_changed_cells_before_active_verifier"]
        - summary["active_verifier_reverted_cells"],
        "verification_record_conservation": summary["verification_record_count"]
        == summary["parent_eligible_support_set_count"]
        == sum(summary[f"{name}_records"] for name in STATUS_NAMES),
        "selected_verification_conservation": summary[
            "selected_exactly_bound_candidate_changes"
        ]
        == sum(summary[f"selected_{name}_changes"] for name in STATUS_NAMES),
        "entropy_credit_conservation": 0.0
        <= summary["utility_aligned_entropy_credit_nats"]
        <= summary["selected_proposal_entropy_nats"] + 1e-12
        <= summary["proposal_support_entropy_total_nats"] + 1e-12,
        "all_private_replay_valid": summary["all_private_replay_valid"] is True,
        "all_source_partitions_disjoint": summary[
            "all_source_partitions_disjoint"
        ]
        is True,
        "all_active_pages_excluded_from_parent_prompt": summary[
            "all_active_pages_excluded_from_parent_prompt"
        ]
        is True,
        "all_active_verifier_final_decisions": summary[
            "all_active_verifier_final_decisions"
        ]
        is True,
        "all_fetch_budgets_conserved": summary["all_fetch_budgets_conserved"]
        is True,
        "all_model_budgets_conserved": summary["all_model_budgets_conserved"]
        is True,
        "all_union_effects_replayed": summary["all_union_effects_replayed"]
        is True,
        "search_effect_conservation": (
            summary["proposal_logical_queries"] == 4 * summary["selected"]
            and summary["total_logical_queries"]
            == summary["proposal_logical_queries"]
            + summary["active_verifier_logical_queries"]
            and summary["active_verifier_logical_queries"]
            <= 2 * summary["selected"]
            and summary["proposal_search_batches"] == 2 * summary["selected"]
            and summary["active_verifier_search_batches"]
            == summary["active_search_tasks"]
            and summary["total_search_batches"]
            == summary["proposal_search_batches"]
            + summary["active_verifier_search_batches"]
            and summary["total_provider_search_calls"]
            == summary["parent_provider_search_calls"]
            + summary["active_provider_search_calls"]
            and summary["total_provider_search_calls"]
            <= summary["hosted_search_attempts"]
            <= 2 * summary["total_search_batches"]
        ),
    }
    if tuple(value) != AGGREGATE_CHECK_NAMES:
        raise RuntimeError("V2.43.86 aggregate check order drifted")
    return value


AGGREGATE_COUNT_FIELDS = (
    "selected",
    "terminal_success_tasks",
    "structurally_passed_tasks",
    "exact_proposal_two_batch_tasks",
    "zero_recursive_split_tasks",
    "full_proposal_partition_tasks",
    "active_query_tasks",
    "active_search_tasks",
    "proposal_logical_queries",
    "active_verifier_logical_queries",
    "total_logical_queries",
    "proposal_search_batches",
    "active_verifier_search_batches",
    "total_search_batches",
    "parent_provider_search_calls",
    "active_provider_search_calls",
    "total_provider_search_calls",
    "proposal_sources",
    "proposal_unselected_sources",
    "active_discovered_sources",
    "active_selected_sources",
    "parent_semantic_catalog_tasks",
    "parent_eligible_support_tasks",
    "parent_eligible_support_set_count",
    "parent_candidate_tasks",
    "entropy_ranked_target_tasks",
    "selected_bound_candidate_tasks",
    "utility_aligned_tasks",
    "final_nonidentity_tasks",
    "candidate_changed_cells_before_active_verifier",
    "candidate_changed_cells_after_active_verifier",
    "selection_resolution_count",
    "candidate_changes_without_declaration",
    "selected_exactly_bound_candidate_changes",
    "active_verifier_admitted_cells",
    "active_verifier_reverted_cells",
    "verification_record_count",
    *(f"{name}_records" for name in STATUS_NAMES),
    *(f"selected_{name}_changes" for name in STATUS_NAMES),
    "verifier_semantic_projection_count",
    "proposal_pages",
    "active_verifier_pages",
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
    "proposal_support_entropy_total_nats",
    "selected_proposal_entropy_nats",
    "utility_aligned_entropy_credit_nats",
    "slot_total_wait_seconds",
    "slot_max_wait_seconds",
)
AGGREGATE_BOOLEAN_FIELDS = (
    "exact_ordinal_vector",
    "all_private_replay_valid",
    "all_source_partitions_disjoint",
    "all_active_pages_excluded_from_parent_prompt",
    "all_active_verifier_final_decisions",
    "all_fetch_budgets_conserved",
    "all_model_budgets_conserved",
    "all_union_effects_replayed",
    "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted",
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
            item["active_verifier_logical_query_count"] > 0 for item in values
        ),
        "active_search_tasks": sum(
            item["active_verifier_search_batch_count"] > 0 for item in values
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
        "parent_semantic_catalog_tasks": sum(
            item["parent_semantic_catalog_present"] for item in values
        ),
        "parent_eligible_support_tasks": sum(
            item["parent_eligible_support_set_count"] > 0 for item in values
        ),
        "parent_candidate_tasks": sum(
            item["candidate_changed_cells_before_active_verifier"] > 0
            for item in values
        ),
        "entropy_ranked_target_tasks": sum(
            item["entropy_ranked_target_count"] > 0 for item in values
        ),
        "selected_bound_candidate_tasks": sum(
            item["selected_exactly_bound_candidate_changes"] > 0
            for item in values
        ),
        "utility_aligned_tasks": sum(
            item["utility_aligned_entropy_credit_nats"] > 0 for item in values
        ),
        "final_nonidentity_tasks": sum(
            item["candidate_changed_cells_after_active_verifier"] > 0
            for item in values
        ),
        "proposal_support_entropy_total_nats": round(
            sum(item["proposal_support_entropy_total_nats"] for item in values), 12
        ),
        "selected_proposal_entropy_nats": round(
            sum(item["selected_proposal_entropy_nats"] for item in values), 12
        ),
        "utility_aligned_entropy_credit_nats": round(
            sum(item["utility_aligned_entropy_credit_nats"] for item in values), 12
        ),
        "slot_total_wait_seconds": round(
            sum(item["slot_total_wait_seconds"] for item in values), 6
        ),
        "slot_max_wait_seconds": round(
            max((item["slot_max_wait_seconds"] for item in values), default=0.0), 6
        ),
        "all_private_replay_valid": all(item["private_replay_valid"] for item in values),
        "all_source_partitions_disjoint": all(
            item["active_verifier_sources_disjoint_from_proposal_sources"]
            for item in values
        ),
        "all_active_pages_excluded_from_parent_prompt": all(
            item["active_verifier_prompt_excluded"] for item in values
        ),
        "all_active_verifier_final_decisions": all(
            item["checks"]["active_retention_conservation"] for item in values
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
        "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    direct_sum = {
        "parent_eligible_support_set_count": "parent_eligible_support_set_count",
        "candidate_changed_cells_before_active_verifier": "candidate_changed_cells_before_active_verifier",
        "candidate_changed_cells_after_active_verifier": "candidate_changed_cells_after_active_verifier",
        "selection_resolution_count": "selection_resolution_count",
        "candidate_changes_without_declaration": "candidate_changes_without_declaration",
        "selected_exactly_bound_candidate_changes": "selected_exactly_bound_candidate_changes",
        "active_verifier_admitted_cells": "active_verifier_admitted_cells",
        "active_verifier_reverted_cells": "active_verifier_reverted_cells",
        "verification_record_count": "verification_record_count",
        "verifier_semantic_projection_count": "verifier_semantic_projection_count",
        "proposal_pages": "parent_proposal_page_count",
        "active_verifier_pages": "active_verifier_page_count",
        "model_requests": "model_requests",
        "model_attempts": "model_attempts",
        "model_total_tokens": "model_total_tokens",
        "slot_acquisitions": "slot_acquisitions",
        "slot_timeouts": "slot_timeouts",
        "provider_deadline_failures": "provider_deadline_failures",
        "proposal_logical_queries": "proposal_logical_query_count",
        "active_verifier_logical_queries": "active_verifier_logical_query_count",
        "total_logical_queries": "total_logical_query_count",
        "proposal_search_batches": "proposal_search_batch_count",
        "active_verifier_search_batches": "active_verifier_search_batch_count",
        "total_search_batches": "total_search_batch_count",
        "parent_provider_search_calls": "parent_provider_search_calls",
        "active_provider_search_calls": "active_provider_search_calls",
        "total_provider_search_calls": "total_provider_search_calls",
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
    for name in STATUS_NAMES:
        summary[f"{name}_records"] = sum(
            item[f"{name}_records"] for item in values
        )
        summary[f"selected_{name}_changes"] = sum(
            item[f"selected_{name}_changes"] for item in values
        )
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
        "active_search_tasks",
        "parent_semantic_catalog_tasks",
        "parent_eligible_support_tasks",
        "parent_candidate_tasks",
        "entropy_ranked_target_tasks",
        "selected_bound_candidate_tasks",
        "utility_aligned_tasks",
        "final_nonidentity_tasks",
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
        or value["active_verifier_pages"] > value["active_selected_sources"]
        or value["total_logical_queries"]
        != value["proposal_logical_queries"]
        + value["active_verifier_logical_queries"]
        or value["total_search_batches"]
        != value["proposal_search_batches"]
        + value["active_verifier_search_batches"]
        or value["total_provider_search_calls"]
        != value["parent_provider_search_calls"]
        + value["active_provider_search_calls"]
        or value["slot_acquisitions"] != value["model_requests"]
        or value["fetch_calls"]
        != value["hard_fetch_helper_calls"] + value["fetch_deadline_rejections"]
        or value[
            "task_identifier_question_query_url_page_prediction_response_candidate_value_evidence_id_or_hash_persisted"
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
        raise RuntimeError("V2.43.86 aggregate drifted")
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
