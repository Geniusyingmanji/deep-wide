#!/usr/bin/env python3
"""Design-only contract for a fresh World Bank monotone-fill causal gate."""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24857_pacing_aware_exact220_contract as parent_contract  # noqa: E402
from deepwide_agent import v25267_production_only_exact220_contract as seal  # noqa: E402
from scripts import audit_v25140_targeted_revision_build as base  # noqa: E402
from scripts import diagnose_v25293_external_binder_reachability as diagnosis  # noqa: E402


DATE = "20260813"
ROLE = "v25294_worldbank_monotone_fill_gate_design"
OUTPUT = Path(f"results/v25294_worldbank_monotone_fill_gate_design_v1_{DATE}.json")
SOURCE = Path("scripts/design_v25294_worldbank_monotone_fill_gate.py")
TEST = Path("tests/test_design_v25294_worldbank_monotone_fill_gate.py")
PARENT_DIAGNOSIS = diagnosis.OUTPUT
EXPECTED_PARENT_SHA256 = (
    "acf96d5d19ca4bf5cd38478a8aef96ead7738ea64a67c36242cc5455b891d111"
)

TASK_COUNT = 12
ROWS_PER_TASK = 12
ENTITY_ROW_COUNT = TASK_COUNT * ROWS_PER_TASK
TARGET_COUNT = 4
VALUE_CELL_COUNT = ENTITY_ROW_COUNT * TARGET_COUNT
MINIMUM_OVERSAMPLE_TARGETS = 24
MINIMUM_COMMON_COMPLETE_ENTITIES = ENTITY_ROW_COUNT
MODEL_CALL_CAP = 3
QUERY_CAP = 4
FETCH_CAP = 10
WALL_SECONDS = 240
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
SEARCH_KEY_SLOT_CAP = 12
MAXIMUM_PAGE_CHARS = 5_000
PAGES_PER_TARGET = 2
PAGE_COUNT = TARGET_COUNT * PAGES_PER_TARGET
WORLD_BANK_PER_PAGE = 120
MAXIMUM_EVIDENCE_CHARS = 40_000
MAXIMUM_REVISION_PROMPT_CHARS = 60_000
TARGET_YEAR = "2022"
SELECTION_SEED = "v25294-fresh-worldbank-monotone-fill-v1"
payload_sha256 = seal.payload_sha256


def _parent_barrier() -> dict[str, Any]:
    if base.sha256(PARENT_DIAGNOSIS) != EXPECTED_PARENT_SHA256:
        raise RuntimeError("V2.52.94 parent diagnosis hash drifted")
    value = diagnosis.validate_diagnosis(
        json.loads(base._ordinary(PARENT_DIAGNOSIS).read_text(encoding="utf-8"))
    )
    authorization = value["authorization"]
    decision = value["decision"]
    if (
        value["diagnosis_valid"] is not True
        or value["findings"] != []
        or decision["next_design_domain"]
        != "world_bank_official_json_to_frozen_markdown"
        or decision["worldbank_fresh_disjoint_population_required"] is not True
        or decision["worldbank_consumed_population_reusable"] is not False
        or authorization["fresh_disjoint_worldbank_shared_prefix_protocol_design"]
        is not True
        or authorization["population_selection_or_freeze"] is not False
        or authorization["external_activation_or_launch"] is not False
    ):
        raise RuntimeError("V2.52.94 parent diagnosis barrier failed")
    return value


def deterministic_rank(namespace: str, value: str) -> str:
    normalized = " ".join(str(value).casefold().split())
    if not normalized or len(normalized) > 160:
        raise ValueError("V2.52.94 rank value drifted")
    if namespace not in {"target", "entity"}:
        raise ValueError("V2.52.94 rank namespace drifted")
    return hashlib.sha256(
        f"{SELECTION_SEED}\0{namespace}\0{normalized}".encode()
    ).hexdigest()


def select_vector(
    complete_entities_by_target: Mapping[str, Sequence[str]],
    rendered_page_chars_by_target: Mapping[str, Sequence[int]],
    *,
    historical_target_keys: Sequence[str],
) -> dict[str, list[str]]:
    normalized_entities: dict[str, set[str]] = {}
    normalized_chars: dict[str, tuple[int, ...]] = {}
    for raw_target, raw_entities in complete_entities_by_target.items():
        target = " ".join(str(raw_target).casefold().split())
        entities = [" ".join(str(value).casefold().split()) for value in raw_entities]
        raw_chars = rendered_page_chars_by_target.get(raw_target)
        if (
            not target
            or len(target) > 160
            or target in normalized_entities
            or len(entities) != len(set(entities))
            or any(not value or len(value) > 160 for value in entities)
            or isinstance(raw_chars, (str, bytes))
            or not isinstance(raw_chars, Sequence)
            or len(raw_chars) != PAGES_PER_TARGET
            or any(
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
                or value > MAXIMUM_PAGE_CHARS
                for value in raw_chars
            )
        ):
            raise RuntimeError("V2.52.94 candidate response aggregate drifted")
        normalized_entities[target] = set(entities)
        normalized_chars[target] = tuple(int(value) for value in raw_chars)
    if len(rendered_page_chars_by_target) != len(normalized_entities):
        raise RuntimeError("V2.52.94 page aggregate target vector drifted")
    targets = list(normalized_entities)
    old_targets = {" ".join(str(value).casefold().split()) for value in historical_target_keys}
    if (
        len(targets) < MINIMUM_OVERSAMPLE_TARGETS
        or len(set(targets)) != len(targets)
    ):
        raise RuntimeError("V2.52.94 candidate capacity drifted")
    eligible_targets = [value for value in targets if value not in old_targets]
    if len(eligible_targets) < TARGET_COUNT:
        raise RuntimeError("V2.52.94 fresh/disjoint capacity is insufficient")
    ranked_targets = sorted(
        eligible_targets, key=lambda value: (deterministic_rank("target", value), value)
    )
    selected_targets: list[str] | None = None
    complete_entities: set[str] | None = None
    for combination in itertools.combinations(ranked_targets, TARGET_COUNT):
        common = set.intersection(
            *(normalized_entities[target] for target in combination)
        )
        page_chars = [
            value
            for target in combination
            for value in normalized_chars[target]
        ]
        if (
            len(common) >= MINIMUM_COMMON_COMPLETE_ENTITIES
            and len(page_chars) == PAGE_COUNT
            and sum(page_chars) <= MAXIMUM_EVIDENCE_CHARS
        ):
            selected_targets = list(combination)
            complete_entities = common
            break
    if selected_targets is None or complete_entities is None:
        raise RuntimeError("V2.52.94 no eligible four-target combination")
    selected_entities = sorted(
        complete_entities,
        key=lambda value: (deterministic_rank("entity", value), value),
    )[:ENTITY_ROW_COUNT]
    return {"target_keys": selected_targets, "entity_keys": selected_entities}


def _caps() -> dict[str, Any]:
    if (
        parent_contract.LIMITS["model_calls"] != MODEL_CALL_CAP
        or parent_contract.LIMITS["search_queries"] != QUERY_CAP
        or parent_contract.LIMITS["fetch_targets"] != FETCH_CAP
        or parent_contract.LIMITS["wall_seconds"] != WALL_SECONDS
        or parent_contract.EXECUTOR_CONCURRENCY != EXECUTOR_CONCURRENCY
        or parent_contract.MODEL_SLOT_CAP != MODEL_SLOT_CAP
        or parent_contract.TAVILY_KEY_SLOT_CAP != SEARCH_KEY_SLOT_CAP
    ):
        raise RuntimeError("V2.52.94 inherited physical cap drifted")
    return {
        "task_count": TASK_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "search_key_slot_cap": SEARCH_KEY_SLOT_CAP,
        "query_cap_per_task": QUERY_CAP,
        "fetch_cap_per_task": FETCH_CAP,
        "model_call_cap_per_task": MODEL_CALL_CAP,
        "wall_seconds_per_task": WALL_SECONDS,
        "maximum_page_characters": MAXIMUM_PAGE_CHARS,
        "page_count_per_task": PAGE_COUNT,
        "maximum_eight_page_evidence_characters": MAXIMUM_EVIDENCE_CHARS,
        "maximum_revision_prompt_characters": MAXIMUM_REVISION_PROMPT_CHARS,
        "new_query_fetch_model_context_token_or_wall_budget": False,
    }


def _mechanism_gate() -> dict[str, Any]:
    return {
        "fixed_denominator_tasks": TASK_COUNT,
        "all_tasks_terminal": TASK_COUNT,
        "failure_as_zero": True,
        "parent_exactly_two_model_calls_and_baseline_unknown_tasks_minimum": 2,
        "complete_eight_page_prefix_tasks_minimum": 2,
        "revision_prompt_within_cap_tasks_minimum": 2,
        "third_slot_proposal_returned_tasks_minimum": 2,
        "supported_unknown_fill_tasks_minimum": 2,
        "supported_unknown_fill_cells_minimum": 2,
        "attributable_prediction_change_tasks_minimum": 2,
        "query_effect_equal_tasks": TASK_COUNT,
        "fetch_effect_equal_tasks": TASK_COUNT,
        "total_model_calls_at_most_three_tasks": TASK_COUNT,
        "known_cell_schema_row_key_order_or_count_violation_tasks": 0,
        "unsupported_or_conflicting_admitted_fill_cells": 0,
        "budget_rejection_tasks": 0,
        "positive_signed_credit_count": 0,
        "zero_supported_fill_or_prediction_change": "strict_no_go_without_evaluator",
    }


def _quality_gate() -> dict[str, Any]:
    return {
        "exists_only_after_predictions_forward_result_and_audit_are_pushed": True,
        "gold_source": "exact_forward_frozen_official_world_bank_response_bytes",
        "gold_renderer_is_same_pure_frozen_json_to_markdown_function": True,
        "gold_renderer_code_hash_fixed_before_forward": True,
        "postfreeze_network_or_refetch_count": 0,
        "fixed_denominator_tasks": TASK_COUNT,
        "candidate_exact_successes_minimum_delta": 2,
        "control_exact_to_candidate_inexact_regressions": 0,
        "entity_row_item_column_and_composite_nonregression": True,
        "candidate_invalid_fallback_and_outer_failure_nonincrease": True,
        "evaluator_retry_refetch_replacement_or_selective_revaluation": False,
        "quality_result_cannot_change_same_run_runtime_policy": True,
    }


def build_design(*, now: int | None = None) -> dict[str, Any]:
    _parent_barrier()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parent_diagnosis": {
            "path": str(PARENT_DIAGNOSIS),
            "sha256": base.sha256(PARENT_DIAGNOSIS),
        },
        "source_hashes": {
            str(path): base.sha256(path) for path in (SOURCE, TEST)
        },
        "research_question": (
            "does_one_budgeted_third_model_call_plus_mechanical_monotone_support_fill_unknown_cells_and_improve_outer_table_utility"
        ),
        "population_contract": {
            "domain": "official_world_bank_indicator_json",
            "target_year": TARGET_YEAR,
            "fresh_target_indicator_year_pairs": TARGET_COUNT,
            "minimum_unconsumed_target_oversample": MINIMUM_OVERSAMPLE_TARGETS,
            "tasks": TASK_COUNT,
            "rows_per_task": ROWS_PER_TASK,
            "entity_rows": ENTITY_ROW_COUNT,
            "value_cells": VALUE_CELL_COUNT,
            "target_indicator_year_pairs_disjoint_from_all_prior_worldbank_external_runs_and_development_probes": True,
            "all_entity_indicator_year_cells_disjoint_from_prior_runs_by_fresh_target_key": True,
            "entity_identity_reuse_across_different_historical_targets_permitted": True,
            "each_entity_appears_in_exactly_one_current_task": True,
            "entities_have_complete_values_for_all_four_targets_at_population_freeze": True,
            "selection_predicate_uses_official_public_record_completeness_only": True,
            "candidate_discovery_fetches_exactly_two_fixed_paginated_endpoints_for_each_of_24_ranked_fresh_targets_once": True,
            "all_48_candidate_response_bytes_are_frozen_before_target_quartet_selection": True,
            "selected_quartet_is_first_deterministically_ranked_combination_with_144_common_complete_entities_and_eight_pages_within_cap": True,
            "all_24_probed_target_keys_become_consumed_even_when_population_is_no_go": True,
            "selection_may_not_read_model_prediction_gold_evaluator_score_or_correctness": True,
            "deterministic_selection_order": "sha256_seed_namespace_normalized_key_then_key",
            "selection_seed_sha256": hashlib.sha256(SELECTION_SEED.encode()).hexdigest(),
            "no_retry_resume_replacement_backfill_or_manual_reordering": True,
        },
        "snapshot_and_representation_contract": {
            "one_catalog_get_and_two_paginated_gets_per_each_of_24_ranked_fresh_targets_before_selection": True,
            "world_bank_per_page": WORLD_BANK_PER_PAGE,
            "pages_per_target": PAGES_PER_TARGET,
            "redirect_retry_conditional_refetch_or_alternate_endpoint_count": 0,
            "exact_response_bytes_sha256_and_transport_receipt_frozen": True,
            "single_pure_json_to_markdown_renderer": True,
            "renderer_code_hash_fixed_before_population_freeze": True,
            "markdown_columns": [
                "visible_entity_code",
                "one_exact_target_label_indicator_and_year",
            ],
            "two_global_paginated_pages_per_target": True,
            "each_page_uses_entity_code_as_exact_row_key": True,
            "all_eight_global_pages_rendered_before_any_model_arm": True,
            "same_eight_global_rendered_pages_shared_by_all_tasks_control_candidate_and_binder": True,
            "renderer_output_fixed_before_parent_or_candidate_branch": True,
            "rendered_page_integrity_true_only_after_exact_snapshot_validation": True,
            "raw_json_not_claimed_as_v25289_natively_parseable": True,
            "renderer_is_protocol_infrastructure_not_candidate_only_information": True,
        },
        "runtime_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "visible_question_requests_exactly_twelve_entity_code_rows_and_four_value_columns": True,
            "control_prediction": "v24857_two_call_parent_prediction",
            "candidate_prediction": "v25290_monotone_unknown_fill_result",
            "control_and_candidate_share_parent_prediction": True,
            "control_and_candidate_share_queries_search_responses_fetch_bytes_and_rendered_pages": True,
            "snapshot_bound_search_transport_returns_only_the_eight_frozen_global_pages": True,
            "snapshot_transport_is_not_claimed_as_production_search_equivalence": True,
            "candidate_may_spend_only_parent_unused_third_model_slot": True,
            "candidate_mutable_cells": "baseline_unknown_non_key_value_cells_only",
            "known_cells_schema_row_keys_order_and_count_byte_immutable": True,
            "same_page_row_column_value_support_required": True,
            "conflicting_bound_values_reject_cell": True,
            "all_candidate_failures_return_exact_parent_prediction": True,
            "candidate_proposal_or_receipt_cannot_route_same_run_search": True,
            "entropy_or_information_gain_shadow_only": True,
            "positive_signed_credit_count": 0,
        },
        "physical_caps": _caps(),
        "mechanism_gate_before_evaluator": _mechanism_gate(),
        "postfreeze_quality_gate": _quality_gate(),
        "stop_rules": {
            "population_or_snapshot_capacity_failure": "no_population_freeze_or_external_forward",
            "renderer_or_integrity_failure": "no_model_call",
            "mechanism_gate_failure": "no_evaluator_and_population_permanently_sealed",
            "quality_gate_failure": "no_public_deepwidebench_220",
            "quality_gate_success": "authorizes_public220_protocol_design_only_not_launch",
            "privileged_runtime_signal_or_evaluator_open_before_freeze": "quarantine_as_invalid",
            "same_population_retry_resume_replacement_or_selective_rerun": "forbidden",
        },
        "claim_scope": {
            "prior_consumed_worldbank_population_effect_claimed": False,
            "actual_third_slot_supported_fill_or_prediction_change_claimed": False,
            "worldbank_representation_reachability_transfers_to_deepwidebench": False,
            "production_search_transport_or_retrieval_utility_claimed": False,
            "deepwidebench_improvement_avg_at_4_leaderboard_or_sota_claimed": False,
            "entropy_or_information_gain_signed_credit_claimed": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "authorization": {
            "population_selector_and_runtime_implementation_build_only": True,
            "network_population_selection_or_freeze": False,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "candidate_quality_avg_at_4_leaderboard_or_sota": False,
        },
    }
    value["design_payload_sha256"] = payload_sha256(value)
    return validate_design(value)


def validate_design(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("design_payload_sha256", None)
    parent_value = copied.get("parent_diagnosis") or {}
    population = copied.get("population_contract") or {}
    snapshot = copied.get("snapshot_and_representation_contract") or {}
    runtime = copied.get("runtime_contract") or {}
    caps = copied.get("physical_caps") or {}
    mechanism = copied.get("mechanism_gate_before_evaluator") or {}
    quality = copied.get("postfreeze_quality_gate") or {}
    claim = copied.get("claim_scope") or {}
    authorization = copied.get("authorization") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "parent_diagnosis",
            "source_hashes",
            "research_question",
            "population_contract",
            "snapshot_and_representation_contract",
            "runtime_contract",
            "physical_caps",
            "mechanism_gate_before_evaluator",
            "postfreeze_quality_gate",
            "stop_rules",
            "claim_scope",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "authorization",
            "design_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or parent_value
        != {"path": str(PARENT_DIAGNOSIS), "sha256": EXPECTED_PARENT_SHA256}
        or copied.get("source_hashes")
        != {str(path): base.sha256(path) for path in (SOURCE, TEST)}
        or population.get("fresh_target_indicator_year_pairs") != TARGET_COUNT
        or population.get("target_year") != TARGET_YEAR
        or population.get("minimum_unconsumed_target_oversample")
        != MINIMUM_OVERSAMPLE_TARGETS
        or population.get("tasks") != TASK_COUNT
        or population.get("rows_per_task") != ROWS_PER_TASK
        or population.get("entity_rows") != ENTITY_ROW_COUNT
        or population.get("value_cells") != VALUE_CELL_COUNT
        or population.get(
            "selection_may_not_read_model_prediction_gold_evaluator_score_or_correctness"
        )
        is not True
        or population.get("no_retry_resume_replacement_backfill_or_manual_reordering")
        is not True
        or snapshot.get("redirect_retry_conditional_refetch_or_alternate_endpoint_count")
        != 0
        or snapshot.get("same_eight_global_rendered_pages_shared_by_all_tasks_control_candidate_and_binder")
        is not True
        or snapshot.get("renderer_output_fixed_before_parent_or_candidate_branch")
        is not True
        or snapshot.get("renderer_is_protocol_infrastructure_not_candidate_only_information")
        is not True
        or runtime.get("runtime_input_keys") != ["opaque_id", "question"]
        or runtime.get("control_and_candidate_share_parent_prediction") is not True
        or runtime.get(
            "control_and_candidate_share_queries_search_responses_fetch_bytes_and_rendered_pages"
        )
        is not True
        or runtime.get("candidate_may_spend_only_parent_unused_third_model_slot")
        is not True
        or runtime.get("known_cells_schema_row_keys_order_and_count_byte_immutable")
        is not True
        or runtime.get("entropy_or_information_gain_shadow_only") is not True
        or runtime.get("positive_signed_credit_count") != 0
        or caps != _caps()
        or mechanism != _mechanism_gate()
        or quality != _quality_gate()
        or any(value is not False for value in claim.values())
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or authorization
        != {
            "population_selector_and_runtime_implementation_build_only": True,
            "network_population_selection_or_freeze": False,
            "external_activation_or_launch": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_forward_or_evaluator": False,
            "retry_resume_replacement_selective_rerun_or_revaluation": False,
            "candidate_quality_avg_at_4_leaderboard_or_sota": False,
        }
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.94 World Bank gate design drifted")
    return copied


def main() -> None:
    value = build_design()
    base.publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "tasks": value["population_contract"]["tasks"],
                "value_cells": value["population_contract"]["value_cells"],
                "implementation_build_only": value["authorization"]
                ["population_selector_and_runtime_implementation_build_only"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
