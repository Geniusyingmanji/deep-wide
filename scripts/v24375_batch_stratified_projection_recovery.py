#!/usr/bin/env python3
"""Build-only recovery for the V2.43.74 public projection depth bug.

The V2.43.74 external tasks are permanently frozen and are never reopened,
resumed, or rerun.  This append-only component repairs only the pure mapping
from a validated V2.43.72 private envelope plus its content-free parent exit
receipt to the V2.43.74 task projection schema.  It exists to demonstrate the
root cause with synthetic envelopes and to support a future, genuinely fresh
external gate.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from deepwide_agent.v24308_child_exit_observability import validate_parent_receipt
from deepwide_agent.v24372_batch_stratified_verifier_runner import validate_envelope
from scripts import v24374_batch_stratified_external_gate as frozen


POLICY_ID = "v24375_batch_stratified_projection_recovery_v1"


def project_task(
    ordinal: int,
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any],
) -> dict[str, Any]:
    """Project one already-validated envelope without any external effect."""

    validated_parent = validate_parent_receipt(parent)
    validated_envelope = validate_envelope(envelope)
    wrapped = validated_envelope["result"]
    target = wrapped["parent_result"]
    legacy = target["parent_result"]
    semantic_parent = legacy["parent_result"]
    semantic = semantic_parent["semantic_result"]
    core = semantic["core_result"]
    core_receipt = core["shared_prefix_revision_receipt"]
    structural = semantic_parent["structural_receipt"]
    runtime = target["target_segment_verifier_receipt"]
    partition = runtime["partition_receipt"]
    private = target["private_replay_state"]
    utility = private["target_segment_utility_catalog"]
    proposal_catalog = semantic["semantic_active_private_state"][
        "semantic_active_catalog"
    ]
    discovery = legacy["two_batch_discovery_receipt"]
    stratification = wrapped["batch_stratification_receipt"]
    single_shot = validated_envelope["search_single_shot_receipt"]
    slot = validated_envelope["model_slot_receipt"]
    transport = validated_envelope["transport_health"]
    model_cost = core["cost"]["model"]
    search_cost = core["cost"]["search"]
    status_counts = runtime["verification_status_counts"]
    selected_statuses = runtime["selected_verification_status_counts"]
    parent_eligible = frozen._integer(
        proposal_catalog["active_catalog"]["base_catalog"],
        "eligible_support_set_count",
    )
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
        "logical_query_count": frozen._integer(discovery, "logical_query_count"),
        "discovery_batch_count": frozen._integer(discovery, "discovery_batch_count"),
        "batch_logical_query_counts": list(discovery["batch_logical_query_counts"]),
        "provider_search_call_count": frozen._integer(
            discovery, "provider_search_call_count"
        ),
        "single_shot_multi_query_chunks": frozen._integer(
            single_shot, "multi_query_chunks"
        ),
        "recursive_split_requests": frozen._integer(
            single_shot, "recursive_split_requests"
        ),
        "pre_host_dedup_url_lead_count": frozen._integer(
            discovery, "pre_host_dedup_url_lead_count"
        ),
        "registrable_host_union_count": frozen._integer(
            discovery, "registrable_host_union_count"
        ),
        "registrable_host_duplicate_url_count": frozen._integer(
            discovery, "registrable_host_duplicate_url_count"
        ),
        "selected_batch_host_counts": list(
            stratification["selected_batch_host_counts"]
        ),
        "proposal_batch_host_counts": list(
            stratification["proposal_batch_host_counts"]
        ),
        "verifier_batch_host_counts": list(
            stratification["verifier_batch_host_counts"]
        ),
        "full_capacity_batch_stratification_satisfied": stratification[
            "full_capacity_batch_stratification_satisfied"
        ],
        "selected_source_count": frozen._integer(partition, "selected_source_count"),
        "proposal_source_count": frozen._integer(partition, "proposal_source_count"),
        "verifier_source_count": frozen._integer(partition, "verifier_source_count"),
        "verifier_source_cap": frozen._integer(partition, "verifier_source_cap"),
        "host_union_precedes_partition_fetch_candidate": discovery[
            "registrable_host_union_precedes_partition_fetch_and_candidate"
        ],
        "source_partition_disjoint": partition[
            "proposal_and_verifier_sources_disjoint"
        ],
        "hidden_verifier_prompt_excluded": not runtime[
            "hidden_verifier_pages_used_for_candidate_generation_or_model_prompt"
        ],
        "hidden_verifier_no_new_candidate": not runtime[
            "new_candidate_value_generated_by_hidden_verifier"
        ],
        "parent_support_ids_reused": runtime[
            "parent_support_set_ids_reused_without_rebuild"
        ],
        "target_segment_entity_boundary_enforced": runtime[
            "target_segment_entity_boundary_enforced"
        ],
        "legacy_character_window_projector_used_for_final_decision": runtime[
            "legacy_character_window_projector_used_for_final_decision"
        ],
        "observed_pages_respect_frozen_partition": runtime[
            "observed_pages_respect_frozen_partition"
        ],
        "parent_semantic_catalog_present": runtime[
            "parent_semantic_catalog_present"
        ],
        "parent_proposal_page_count": frozen._integer(
            runtime, "parent_proposal_page_count"
        ),
        "hidden_verifier_page_count": frozen._integer(
            runtime, "hidden_verifier_page_count"
        ),
        "parent_fetch_calls": frozen._integer(runtime, "parent_fetch_calls"),
        "hidden_verifier_fetch_calls": frozen._integer(
            runtime, "hidden_verifier_fetch_calls"
        ),
        "total_fetch_calls": frozen._integer(runtime, "total_fetch_calls"),
        "parent_eligible_support_set_count": parent_eligible,
        "parent_candidate_changed_cells": frozen._integer(
            runtime, "candidate_changed_cells_before_hidden_verifier"
        ),
        "legacy_candidate_changed_cells": frozen._integer(
            runtime, "legacy_candidate_changed_cells_after_hidden_verifier"
        ),
        "target_segment_candidate_changed_cells": frozen._integer(
            runtime, "candidate_changed_cells_after_hidden_verifier"
        ),
        "target_segment_recovered_cells": frozen._integer(
            runtime, "target_segment_recovered_cells"
        ),
        "target_segment_reverted_legacy_cells": frozen._integer(
            runtime, "target_segment_reverted_legacy_cells"
        ),
        "hidden_verifier_admitted_cells": frozen._integer(
            runtime, "hidden_verifier_admitted_cells"
        ),
        "hidden_verifier_reverted_cells": frozen._integer(
            runtime, "hidden_verifier_reverted_cells"
        ),
        "selection_resolution_count": frozen._integer(
            runtime, "selection_resolution_count"
        ),
        "candidate_changes_without_declaration": frozen._integer(
            runtime, "candidate_changes_without_declaration"
        ),
        "selected_exactly_bound_candidate_changes": frozen._integer(
            runtime, "selected_exactly_bound_candidate_changes"
        ),
        "verification_record_count": frozen._integer(
            runtime, "verification_record_count"
        ),
        "verified_candidate_records": int(status_counts.get("verified_candidate", 0)),
        "no_independent_candidate_support_records": int(
            status_counts.get("no_independent_candidate_support", 0)
        ),
        "verifier_supports_baseline_records": int(
            status_counts.get("verifier_supports_baseline", 0)
        ),
        "independent_conflict_records": int(
            status_counts.get("independent_conflict", 0)
        ),
        "nonpositive_proposal_entropy_records": int(
            status_counts.get("nonpositive_proposal_entropy", 0)
        ),
        "selected_verified_candidate_changes": int(
            selected_statuses.get("verified_candidate", 0)
        ),
        "selected_no_independent_candidate_support_changes": int(
            selected_statuses.get("no_independent_candidate_support", 0)
        ),
        "selected_verifier_supports_baseline_changes": int(
            selected_statuses.get("verifier_supports_baseline", 0)
        ),
        "selected_independent_conflict_changes": int(
            selected_statuses.get("independent_conflict", 0)
        ),
        "selected_nonpositive_proposal_entropy_changes": int(
            selected_statuses.get("nonpositive_proposal_entropy", 0)
        ),
        "verifier_semantic_projection_count": frozen._integer(
            runtime, "verifier_semantic_projection_count"
        ),
        "proposal_support_entropy_total_nats": frozen._number(
            runtime, "proposal_support_entropy_total_nats"
        ),
        "selected_proposal_entropy_nats": frozen._number(
            runtime, "selected_proposal_conditional_entropy_reduction_nats"
        ),
        "utility_aligned_entropy_credit_nats": frozen._number(
            runtime, "utility_aligned_entropy_credit_nats"
        ),
        "model_requests": frozen._integer(model_cost, "requests"),
        "model_attempts": frozen._integer(model_cost, "attempts"),
        "model_total_tokens": frozen._integer(model_cost, "total_tokens"),
        "slot_acquisitions": frozen._integer(slot, "acquisitions"),
        "slot_timeouts": frozen._integer(slot, "slot_timeouts"),
        "provider_deadline_failures": frozen._integer(
            slot, "provider_deadline_failures"
        ),
        "slot_total_wait_seconds": frozen._number(slot, "total_wait_seconds"),
        "slot_max_wait_seconds": frozen._number(slot, "max_wait_seconds"),
        "slot_acquisition_counts": list(slot["slot_acquisition_counts"]),
        "search_calls": frozen._integer(search_cost, "calls"),
        "fetch_failures": frozen._integer(search_cost, "fetch_failures"),
        "search_total_tokens": frozen._integer(search_cost, "total_tokens"),
        "hosted_search_attempts": frozen._integer(
            transport, "hosted_search_attempts"
        ),
        "hosted_search_deadline_failures": frozen._integer(
            transport, "hosted_search_deadline_failures"
        ),
        "hard_fetch_helper_calls": frozen._integer(
            transport, "hard_fetch_helper_calls"
        ),
        "hard_fetch_deadline_failures": frozen._integer(
            transport, "hard_fetch_deadline_failures"
        ),
        "fetch_deadline_rejections": frozen._integer(
            transport, "fetch_deadline_rejections"
        ),
        "fetch_helper_failures": frozen._integer(
            transport, "fetch_helper_failures"
        ),
        "deadline_exhausted": transport["deadline_exhausted"] is True,
        "private_replay_valid": isinstance(utility, Mapping),
    }
    value["checks"] = frozen._task_checks(value)
    value["passed"] = all(value["checks"].values())
    frozen.validate_task_projection(value)
    return copy.deepcopy(value)


__all__ = ["POLICY_ID", "project_task"]
