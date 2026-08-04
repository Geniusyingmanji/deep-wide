"""Content-free projection for V2.44.09 structured uncertainty probes.

The projection validates the complete private V2.44.09 envelope and emits only
counts, nonnegative entropy/credit scalars, effect receipts, and Boolean
conservation claims.  It never emits a task identifier, question, query, URL,
page, observation value, prediction, candidate value, or source.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from deepwide_agent.v24308_child_exit_observability import validate_parent_receipt
from deepwide_agent.v24409_structured_uncertainty_runner import validate_envelope
from scripts import v24393_uncertainty_external_projection as base


SELECTED = 16
MODEL_SLOT_CAP = 2
COMPLETION_KINDS = base.COMPLETION_KINDS
_integer = base._integer
_number = base._number
TASK_CHECK_NAMES = (
    "parent_success",
    "all_parent_artifacts_valid",
    "legacy_effect_accounting_complete",
    "legacy_structural_normalization",
    "legacy_proposal_two_batch_complete",
    "legacy_candidate_independent_active_query_contract",
    "legacy_recursive_split_absent",
    "legacy_source_budget_and_disjointness",
    "legacy_active_pages_prompt_excluded",
    "structured_projection_private_replay",
    "structured_observation_conservation",
    "structured_posterior_resolution_conservation",
    "structured_entropy_credit_conservation",
    "zero_additional_effects",
    "parent_effect_counts_reused",
    "fetch_budget_transport_conserved",
    "model_slot_conserved",
    "deadline_not_exhausted",
)
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
    "selected_uncertainty_target_count",
    "active_discovered_source_count",
    "active_selected_source_count",
    "active_page_count",
    "legacy_active_observation_count",
    "structured_projection_count",
    "novel_structured_observation_count",
    "combined_active_observation_count",
    "legacy_safe_change_count",
    "recovered_safe_change_count",
    "recovered_baseline_confirmed_count",
    "recovered_unresolved_count",
    "recovered_positive_epistemic_target_count",
    "recovered_source_credit_record_count",
    "legacy_candidate_changed_cell_count",
    "recovered_candidate_changed_cell_count",
    "parent_model_requests",
    "parent_total_logical_queries",
    "parent_total_search_batches",
    "parent_total_fetch_calls",
    "additional_model_requests",
    "additional_logical_queries",
    "additional_search_batches",
    "additional_fetch_calls",
    "model_requests",
    "model_attempts",
    "model_total_tokens",
    "slot_acquisitions",
    "slot_timeouts",
    "provider_deadline_failures",
    "hosted_search_attempts",
    "fetch_failures",
    "hosted_search_deadline_failures",
    "hard_fetch_helper_calls",
    "hard_fetch_deadline_failures",
    "fetch_deadline_rejections",
    "fetch_helper_failures",
)
NUMERIC_FIELDS = (
    "wall_seconds",
    "legacy_epistemic_credit_total_nats",
    "recovered_pre_active_entropy_total_nats",
    "recovered_combined_entropy_total_nats",
    "recovered_positive_information_gain_total_nats",
    "recovered_bayesian_surprise_total_nats",
    "recovered_epistemic_credit_total_nats",
    "recovered_decision_credit_total_nats",
    "slot_total_wait_seconds",
    "slot_max_wait_seconds",
)
BOOLEAN_FIELDS = (
    "all_parent_artifacts_valid",
    "legacy_effect_accounting_complete",
    "legacy_structural_normalization",
    "legacy_active_sources_disjoint_from_proposal_sources",
    "legacy_active_pages_prompt_excluded",
    "structured_recovery_changed_output",
    "parent_target_query_source_and_effects_reused_without_reexecution",
    "structured_projection_private_replay_valid",
    "frozen_uncertainty_catalog_reused_without_target_reselection",
    "posterior_and_credit_recomputed_from_combined_observations",
    "decision_credit_requires_safe_output_change",
    "private_replay_valid",
    "deadline_exhausted",
    "passed",
)
VECTOR_FIELDS = ("proposal_batch_logical_query_counts", "proposal_batch_host_counts")
TASK_KEYS = frozenset(
    {
        "ordinal",
        "parent_taxonomy",
        "completion_kind",
        "slot_acquisition_counts",
        "checks",
        *COUNT_FIELDS,
        *NUMERIC_FIELDS,
        *BOOLEAN_FIELDS,
        *VECTOR_FIELDS,
    }
)


def task_checks(value: Mapping[str, Any]) -> dict[str, bool]:
    selected = int(value.get("selected_uncertainty_target_count", -1))
    safe = int(value.get("recovered_safe_change_count", -1))
    confirmed = int(value.get("recovered_baseline_confirmed_count", -1))
    unresolved = int(value.get("recovered_unresolved_count", -1))
    total_queries = int(value.get("total_logical_query_count", -1))
    total_batches = int(value.get("total_search_batch_count", -1))
    return {
        "parent_success": value.get("parent_taxonomy") == "success",
        "all_parent_artifacts_valid": value.get("all_parent_artifacts_valid")
        is True,
        "legacy_effect_accounting_complete": value.get(
            "legacy_effect_accounting_complete"
        )
        is True,
        "legacy_structural_normalization": value.get(
            "legacy_structural_normalization"
        )
        is True,
        "legacy_proposal_two_batch_complete": (
            value.get("proposal_logical_query_count") == 4
            and value.get("proposal_search_batch_count") == 2
            and value.get("proposal_batch_logical_query_counts") == [2, 2]
        ),
        "legacy_candidate_independent_active_query_contract": (
            value.get("active_logical_query_count") == 1
            and value.get("active_search_batch_count") == 1
            and selected == 1
            and total_queries == 5
            and total_batches == 3
        ),
        "legacy_recursive_split_absent": value.get("recursive_split_requests")
        == 0,
        "legacy_source_budget_and_disjointness": (
            0 <= int(value.get("proposal_source_count", -1)) <= 8
            and 0 <= int(value.get("active_selected_source_count", -1)) <= 2
            and value.get("active_selected_source_count", -1)
            <= value.get("active_discovered_source_count", -1)
            and value.get("legacy_active_sources_disjoint_from_proposal_sources")
            is True
        ),
        "legacy_active_pages_prompt_excluded": value.get(
            "legacy_active_pages_prompt_excluded"
        )
        is True,
        "structured_projection_private_replay": (
            value.get("structured_projection_private_replay_valid") is True
            and value.get("frozen_uncertainty_catalog_reused_without_target_reselection")
            is True
            and value.get("posterior_and_credit_recomputed_from_combined_observations")
            is True
            and value.get("private_replay_valid") is True
        ),
        "structured_observation_conservation": (
            value.get("combined_active_observation_count", -1)
            == value.get("legacy_active_observation_count", -1)
            + value.get("novel_structured_observation_count", -1)
            and value.get("novel_structured_observation_count", -1)
            <= value.get("combined_active_observation_count", -1)
            and value.get("recovered_source_credit_record_count", -1)
            <= value.get("combined_active_observation_count", -1)
        ),
        "structured_posterior_resolution_conservation": (
            safe + confirmed + unresolved == selected
            and value.get("recovered_positive_epistemic_target_count", -1)
            <= selected
        ),
        "structured_entropy_credit_conservation": (
            0.0
            <= float(value.get("recovered_decision_credit_total_nats", -1.0))
            <= float(value.get("recovered_epistemic_credit_total_nats", -1.0))
            + 1e-12
            <= float(
                value.get("recovered_positive_information_gain_total_nats", -1.0)
            )
            + 1e-12
            and value.get("decision_credit_requires_safe_output_change") is True
            and (
                float(value.get("recovered_decision_credit_total_nats", 0.0))
                == 0
                or safe > 0
            )
        ),
        "zero_additional_effects": all(
            value.get(name) == 0
            for name in (
                "additional_model_requests",
                "additional_logical_queries",
                "additional_search_batches",
                "additional_fetch_calls",
            )
        ),
        "parent_effect_counts_reused": (
            value.get("parent_target_query_source_and_effects_reused_without_reexecution")
            is True
            and value.get("parent_model_requests") == value.get("model_requests")
            and value.get("parent_total_logical_queries") == total_queries
            and value.get("parent_total_search_batches") == total_batches
            and value.get("parent_total_fetch_calls")
            == value.get("hard_fetch_helper_calls")
            + value.get("fetch_deadline_rejections")
        ),
        "fetch_budget_transport_conserved": (
            value.get("parent_total_fetch_calls")
            == value.get("hard_fetch_helper_calls")
            + value.get("fetch_deadline_rejections")
            and 0 <= int(value.get("parent_total_fetch_calls", -1)) <= 10
        ),
        "model_slot_conserved": value.get("parent_model_requests")
        == value.get("model_requests")
        == value.get("slot_acquisitions"),
        "deadline_not_exhausted": value.get("deadline_exhausted") is False,
    }


def task_projection(
    ordinal: int,
    parent: Mapping[str, Any],
    envelope: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(envelope, Mapping):
        raise ValueError("V2.44.11 successful parent is missing its envelope")
    parent_exit = validate_parent_receipt(dict(parent))
    wrapped = validate_envelope(envelope)
    recovery = wrapped["result"]
    legacy = recovery["parent_result"]
    legacy_receipt = legacy["uncertainty_active_receipt"]
    structured = recovery["structured_recovery_receipt"]
    structural_parent = legacy["parent_result"]
    semantic = structural_parent["semantic_result"]
    core = semantic["core_result"]
    core_receipt = core["shared_prefix_revision_receipt"]
    structural_receipt = structural_parent["structural_receipt"]
    private = legacy["private_replay_state"]
    proposal_state = private["proposal_selection_state"]
    slot = wrapped["model_slot_receipt"]
    transport = wrapped["transport_health"]
    single_shot = wrapped["search_single_shot_receipt"]
    model_cost = core["cost"]["model"]
    search_cost = core["cost"]["search"]
    projection = recovery["structured_active_projection"]
    active_result = recovery["structured_active_evidence_result"]
    value = {
        "ordinal": ordinal,
        "wall_seconds": round(float(parent_exit["elapsed_seconds"]), 6),
        "parent_taxonomy": parent_exit["failure_taxonomy"],
        "all_parent_artifacts_valid": all(
            parent_exit[name] is True
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
        "legacy_effect_accounting_complete": core_receipt[
            "effect_accounting_complete"
        ],
        "legacy_structural_normalization": structural_receipt[
            "same_normalized_baseline_for_baseline_and_candidate"
        ],
        "proposal_logical_query_count": _integer(
            legacy_receipt, "proposal_logical_query_count"
        ),
        "proposal_search_batch_count": _integer(
            legacy_receipt, "proposal_search_batch_count"
        ),
        "active_logical_query_count": _integer(
            legacy_receipt, "active_logical_query_count"
        ),
        "active_search_batch_count": _integer(
            legacy_receipt, "active_search_batch_count"
        ),
        "total_logical_query_count": _integer(
            legacy_receipt, "total_logical_query_count"
        ),
        "total_search_batch_count": _integer(
            legacy_receipt, "total_search_batch_count"
        ),
        "proposal_batch_logical_query_counts": [
            len(batch) for batch in proposal_state["query_batches"]
        ],
        "proposal_batch_host_counts": list(
            legacy_receipt["proposal_batch_host_counts"]
        ),
        "parent_provider_search_calls": _integer(
            legacy_receipt, "parent_provider_search_calls"
        ),
        "active_provider_search_calls": _integer(
            legacy_receipt, "active_provider_search_calls"
        ),
        "total_provider_search_calls": _integer(
            legacy_receipt, "total_provider_search_calls"
        ),
        "single_shot_multi_query_chunks": _integer(
            single_shot, "multi_query_chunks"
        ),
        "recursive_split_requests": _integer(
            single_shot, "recursive_split_requests"
        ),
        "proposal_discovered_source_count": sum(
            len(batch) for batch in proposal_state["raw_batch_leads"]
        ),
        "proposal_unselected_source_count": sum(
            len(batch) for batch in proposal_state["heldout_batch_leads"]
        ),
        "proposal_source_count": _integer(legacy_receipt, "proposal_source_count"),
        "parent_proposal_page_count": _integer(
            legacy_receipt, "parent_proposal_page_count"
        ),
        "proposal_observation_count": _integer(
            legacy_receipt, "proposal_observation_count"
        ),
        "selected_uncertainty_target_count": _integer(
            structured, "selected_target_count"
        ),
        "active_discovered_source_count": _integer(
            legacy_receipt, "active_discovered_source_count"
        ),
        "active_selected_source_count": _integer(
            legacy_receipt, "active_selected_source_count"
        ),
        "active_page_count": _integer(structured, "active_page_count"),
        "legacy_active_observation_count": _integer(
            structured, "legacy_active_observation_count"
        ),
        "structured_projection_count": _integer(
            structured, "structured_projection_count"
        ),
        "novel_structured_observation_count": _integer(
            structured, "novel_structured_observation_count"
        ),
        "combined_active_observation_count": _integer(
            structured, "combined_active_observation_count"
        ),
        "legacy_safe_change_count": _integer(
            structured, "legacy_safe_change_count"
        ),
        "recovered_safe_change_count": _integer(
            structured, "recovered_safe_change_count"
        ),
        "recovered_baseline_confirmed_count": _integer(
            structured, "recovered_baseline_confirmed_count"
        ),
        "recovered_unresolved_count": _integer(
            structured, "recovered_unresolved_count"
        ),
        "recovered_positive_epistemic_target_count": _integer(
            structured, "recovered_positive_epistemic_target_count"
        ),
        "recovered_source_credit_record_count": _integer(
            structured, "recovered_source_credit_record_count"
        ),
        "legacy_epistemic_credit_total_nats": _number(
            structured, "legacy_epistemic_credit_total_nats"
        ),
        "recovered_pre_active_entropy_total_nats": _number(
            structured, "recovered_pre_active_entropy_total_nats"
        ),
        "recovered_combined_entropy_total_nats": _number(
            structured, "recovered_combined_entropy_total_nats"
        ),
        "recovered_positive_information_gain_total_nats": _number(
            structured, "recovered_positive_information_gain_total_nats"
        ),
        "recovered_bayesian_surprise_total_nats": _number(
            structured, "recovered_bayesian_surprise_total_nats"
        ),
        "recovered_epistemic_credit_total_nats": _number(
            structured, "recovered_epistemic_credit_total_nats"
        ),
        "recovered_decision_credit_total_nats": _number(
            structured, "recovered_decision_credit_total_nats"
        ),
        "legacy_candidate_changed_cell_count": _integer(
            structured, "legacy_candidate_changed_cell_count"
        ),
        "recovered_candidate_changed_cell_count": _integer(
            structured, "recovered_candidate_changed_cell_count"
        ),
        "structured_recovery_changed_output": structured[
            "structured_recovery_changed_output"
        ],
        "parent_model_requests": _integer(structured, "parent_model_requests"),
        "parent_total_logical_queries": _integer(
            structured, "parent_total_logical_queries"
        ),
        "parent_total_search_batches": _integer(
            structured, "parent_total_search_batches"
        ),
        "parent_total_fetch_calls": _integer(
            structured, "parent_total_fetch_calls"
        ),
        "additional_model_requests": _integer(
            structured, "additional_model_requests"
        ),
        "additional_logical_queries": _integer(
            structured, "additional_logical_queries"
        ),
        "additional_search_batches": _integer(
            structured, "additional_search_batches"
        ),
        "additional_fetch_calls": _integer(structured, "additional_fetch_calls"),
        "parent_target_query_source_and_effects_reused_without_reexecution": structured[
            "parent_target_query_source_and_effects_reused_without_reexecution"
        ],
        "structured_projection_private_replay_valid": structured[
            "structured_projection_private_replay_valid"
        ],
        "frozen_uncertainty_catalog_reused_without_target_reselection": structured[
            "frozen_uncertainty_catalog_reused_without_target_reselection"
        ],
        "posterior_and_credit_recomputed_from_combined_observations": structured[
            "posterior_and_credit_recomputed_from_combined_observations"
        ],
        "decision_credit_requires_safe_output_change": structured[
            "decision_credit_requires_safe_output_change"
        ],
        "legacy_active_sources_disjoint_from_proposal_sources": legacy_receipt[
            "active_sources_disjoint_from_proposal_sources"
        ],
        "legacy_active_pages_prompt_excluded": not legacy_receipt[
            "active_pages_used_for_model_prompt_or_candidate_generation"
        ],
        "model_requests": _integer(model_cost, "requests"),
        "model_attempts": _integer(model_cost, "attempts"),
        "model_total_tokens": _integer(model_cost, "total_tokens"),
        "slot_acquisitions": _integer(slot, "acquisitions"),
        "slot_timeouts": _integer(slot, "slot_timeouts"),
        "provider_deadline_failures": _integer(slot, "provider_deadline_failures"),
        "slot_total_wait_seconds": _number(slot, "total_wait_seconds"),
        "slot_max_wait_seconds": _number(slot, "max_wait_seconds"),
        "slot_acquisition_counts": list(slot["slot_acquisition_counts"]),
        "hosted_search_attempts": _integer(transport, "hosted_search_attempts"),
        "fetch_failures": _integer(search_cost, "fetch_failures"),
        "hosted_search_deadline_failures": _integer(
            transport, "hosted_search_deadline_failures"
        ),
        "hard_fetch_helper_calls": _integer(
            transport, "hard_fetch_helper_calls"
        ),
        "hard_fetch_deadline_failures": _integer(
            transport, "hard_fetch_deadline_failures"
        ),
        "fetch_deadline_rejections": _integer(
            transport, "fetch_deadline_rejections"
        ),
        "fetch_helper_failures": _integer(transport, "fetch_helper_failures"),
        "private_replay_valid": (
            projection["observations"] == active_result["active_observations"]
            and structured["combined_active_observation_count"]
            == len(projection["observations"])
            and structured["recovered_epistemic_credit_total_nats"]
            == active_result["receipt"]["epistemic_credit_total_nats"]
        ),
        "deadline_exhausted": transport["deadline_exhausted"] is True,
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
        or value.get("completion_kind") not in {
            "paired",
            "identity_no_reserve",
            "identity_fallback",
            None,
        }
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or value[name] < 0
            for name in COUNT_FIELDS
        )
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in NUMERIC_FIELDS
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
        != value["proposal_source_count"]
        + value["proposal_unselected_source_count"]
        or not isinstance(checks, Mapping)
        or tuple(checks) != TASK_CHECK_NAMES
        or dict(checks) != task_checks(value)
        or value["passed"] is not all(checks.values())
    ):
        raise RuntimeError("V2.44.11 task projection drifted")
    return dict(value)


def local_failure(ordinal: int) -> dict[str, Any]:
    value: dict[str, Any] = {
        "ordinal": ordinal,
        "parent_taxonomy": "local_projection_failure",
        "completion_kind": None,
        "slot_acquisition_counts": [0] * MODEL_SLOT_CAP,
        "wall_seconds": 0.0,
        "slot_total_wait_seconds": 0.0,
        "slot_max_wait_seconds": 0.0,
    }
    for name in COUNT_FIELDS:
        value[name] = 0
    for name in NUMERIC_FIELDS:
        value[name] = 0.0
    for name in BOOLEAN_FIELDS:
        value[name] = False
    for name in VECTOR_FIELDS:
        value[name] = [0, 0]
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
    "full_proposal_partition_tasks",
    "two_active_source_tasks",
    "active_page_tasks",
    "combined_observation_tasks",
    "novel_structured_observation_tasks",
    "positive_epistemic_tasks",
    "safe_change_tasks",
    "positive_epistemic_credit",
    "decision_credit_consistency",
    "all_private_replay_valid",
    "all_zero_additional_effects",
    "all_fetch_budgets_conserved",
    "all_model_budgets_conserved",
    "search_effect_conservation",
)
AGGREGATE_COUNT_FIELDS = (
    "selected",
    "terminal_success_tasks",
    "structurally_passed_tasks",
    "full_proposal_partition_tasks",
    "two_active_source_tasks",
    "active_page_tasks",
    "combined_observation_tasks",
    "novel_structured_observation_tasks",
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
    "legacy_active_observations",
    "structured_projections",
    "novel_structured_observations",
    "combined_active_observations",
    "safe_change_count",
    "baseline_confirmed_count",
    "unresolved_count",
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
    "additional_model_requests",
    "additional_logical_queries",
    "additional_search_batches",
    "additional_fetch_calls",
)
AGGREGATE_NUMERIC_FIELDS = (
    "batch_wall_seconds",
    "throughput_tasks_per_minute",
    "legacy_epistemic_credit_total_nats",
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
    "all_zero_additional_effects",
    "all_fetch_budgets_conserved",
    "all_model_budgets_conserved",
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
        "full_proposal_partition_tasks": summary["full_proposal_partition_tasks"]
        >= gates["minimum_full_proposal_partition_tasks"],
        "two_active_source_tasks": summary["two_active_source_tasks"]
        >= gates["minimum_two_active_source_tasks"],
        "active_page_tasks": summary["active_page_tasks"]
        >= gates["minimum_active_page_tasks"],
        "combined_observation_tasks": summary["combined_observation_tasks"]
        >= gates["minimum_combined_observation_tasks"],
        "novel_structured_observation_tasks": summary[
            "novel_structured_observation_tasks"
        ]
        >= gates["minimum_novel_structured_observation_tasks"],
        "positive_epistemic_tasks": summary["positive_epistemic_tasks"]
        >= gates["minimum_positive_epistemic_tasks"],
        "safe_change_tasks": summary["safe_change_tasks"]
        >= gates["minimum_safe_change_tasks"],
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
        "all_zero_additional_effects": summary["all_zero_additional_effects"]
        is True,
        "all_fetch_budgets_conserved": summary["all_fetch_budgets_conserved"]
        is True,
        "all_model_budgets_conserved": summary["all_model_budgets_conserved"]
        is True,
        "search_effect_conservation": (
            summary["proposal_logical_queries"] == 4 * summary["selected"]
            and summary["active_logical_queries"] == summary["selected"]
            and summary["total_logical_queries"] == 5 * summary["selected"]
            and summary["proposal_search_batches"] == 2 * summary["selected"]
            and summary["active_search_batches"] == summary["selected"]
            and summary["total_search_batches"] == 3 * summary["selected"]
            and summary["total_provider_search_calls"]
            == summary["parent_provider_search_calls"]
            + summary["active_provider_search_calls"]
            and summary["total_provider_search_calls"]
            <= summary["hosted_search_attempts"]
            <= 2 * summary["total_search_batches"]
        ),
    }
    if tuple(value) != AGGREGATE_CHECK_NAMES:
        raise RuntimeError("V2.44.11 aggregate check order drifted")
    return value


def aggregate_tasks(
    tasks: Sequence[Mapping[str, Any]],
    batch_wall_seconds: float,
    gates: Mapping[str, Any],
) -> dict[str, Any]:
    values = sorted(
        (validate_task_projection(item) for item in tasks),
        key=lambda item: item["ordinal"],
    )
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
        "completion_kinds": dict(
            sorted(Counter(str(item["completion_kind"]) for item in values).items())
        ),
        "full_proposal_partition_tasks": sum(
            item["proposal_source_count"] == 8 for item in values
        ),
        "two_active_source_tasks": sum(
            item["active_selected_source_count"] == 2 for item in values
        ),
        "active_page_tasks": sum(item["active_page_count"] > 0 for item in values),
        "combined_observation_tasks": sum(
            item["combined_active_observation_count"] > 0 for item in values
        ),
        "novel_structured_observation_tasks": sum(
            item["novel_structured_observation_count"] > 0 for item in values
        ),
        "positive_epistemic_tasks": sum(
            item["recovered_epistemic_credit_total_nats"] > 0 for item in values
        ),
        "safe_change_tasks": sum(
            item["recovered_safe_change_count"] > 0 for item in values
        ),
        "baseline_confirmation_tasks": sum(
            item["recovered_baseline_confirmed_count"] > 0 for item in values
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
        "legacy_active_observations": sum(
            item["legacy_active_observation_count"] for item in values
        ),
        "structured_projections": sum(
            item["structured_projection_count"] for item in values
        ),
        "novel_structured_observations": sum(
            item["novel_structured_observation_count"] for item in values
        ),
        "combined_active_observations": sum(
            item["combined_active_observation_count"] for item in values
        ),
        "safe_change_count": sum(
            item["recovered_safe_change_count"] for item in values
        ),
        "baseline_confirmed_count": sum(
            item["recovered_baseline_confirmed_count"] for item in values
        ),
        "unresolved_count": sum(item["recovered_unresolved_count"] for item in values),
        "positive_epistemic_target_count": sum(
            item["recovered_positive_epistemic_target_count"] for item in values
        ),
        "source_credit_record_count": sum(
            item["recovered_source_credit_record_count"] for item in values
        ),
        "slot_total_wait_seconds": round(
            sum(item["slot_total_wait_seconds"] for item in values), 6
        ),
        "slot_max_wait_seconds": round(
            max((item["slot_max_wait_seconds"] for item in values), default=0.0), 6
        ),
        "all_private_replay_valid": all(
            item["private_replay_valid"] for item in values
        ),
        "all_zero_additional_effects": all(
            item["checks"]["zero_additional_effects"] for item in values
        ),
        "all_fetch_budgets_conserved": all(
            item["checks"]["fetch_budget_transport_conserved"] for item in values
        ),
        "all_model_budgets_conserved": all(
            item["checks"]["model_slot_conserved"] for item in values
        ),
        "task_identifier_question_query_url_page_prediction_response_candidate_value_or_source_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    direct = {
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
        "fetch_calls": "parent_total_fetch_calls",
        "fetch_failures": "fetch_failures",
        "hosted_search_deadline_failures": "hosted_search_deadline_failures",
        "hard_fetch_helper_calls": "hard_fetch_helper_calls",
        "hard_fetch_deadline_failures": "hard_fetch_deadline_failures",
        "fetch_deadline_rejections": "fetch_deadline_rejections",
        "fetch_helper_failures": "fetch_helper_failures",
        "additional_model_requests": "additional_model_requests",
        "additional_logical_queries": "additional_logical_queries",
        "additional_search_batches": "additional_search_batches",
        "additional_fetch_calls": "additional_fetch_calls",
    }
    for output, source in direct.items():
        summary[output] = sum(item[source] for item in values)
    numeric = {
        "legacy_epistemic_credit_total_nats": "legacy_epistemic_credit_total_nats",
        "pre_active_entropy_total_nats": "recovered_pre_active_entropy_total_nats",
        "combined_entropy_total_nats": "recovered_combined_entropy_total_nats",
        "positive_information_gain_total_nats": "recovered_positive_information_gain_total_nats",
        "bayesian_surprise_total_nats": "recovered_bayesian_surprise_total_nats",
        "epistemic_credit_total_nats": "recovered_epistemic_credit_total_nats",
        "decision_credit_total_nats": "recovered_decision_credit_total_nats",
    }
    for output, source in numeric.items():
        summary[output] = round(sum(item[source] for item in values), 12)
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
        or not isinstance(completion, Mapping)
        or any(
            name not in COMPLETION_KINDS
            or isinstance(count, bool)
            or not isinstance(count, int)
            or count < 0
            for name, count in completion.items()
        )
        or sum(completion.values()) != value["selected"]
        or value["proposal_sources"] > 8 * value["selected"]
        or value["active_selected_sources"] > 2 * value["selected"]
        or value["active_pages"] > value["active_selected_sources"]
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
        raise RuntimeError("V2.44.11 aggregate drifted")
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
