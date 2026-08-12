#!/usr/bin/env python3
"""Freeze the V2.52.29 header-totality successor design.

The only proposed new acceptance state composes two already-frozen structural
operations: remove one explicitly generic leading index column, then replace
the remaining equal-arity header positionally with the visible required
schema.  No runtime implementation or external effect is authorized here.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25209_v25208_exact220 as base  # noqa: E402


DATE = "20260812"
ROLE = "v25229_header_totality_successor_design"
OUTPUT = Path(f"results/v25229_header_totality_successor_design_v1_{DATE}.json")
SOURCE = Path("scripts/design_v25229_header_totality_successor.py")
TEST = Path("tests/test_design_v25229_header_totality_successor.py")
DIAGNOSIS = Path(
    f"results/v25228_v25208_production_totality_diagnosis_v1_{DATE}.json"
)
PARENT_NORMALIZER = Path(
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py"
)
PARENT_OBSERVER = Path(
    "src/deepwide_agent/v25170_production_normalizer_disposition_observer.py"
)
QUOTE_NORMALIZER = Path(
    "src/deepwide_agent/v25177_quote_aware_pipe_normalizer.py"
)
EXPECTED_SHA256 = {
    str(DIAGNOSIS): "400cd12be3bd3825ce7aa27652efda1004a3f2c399005afe5d47a702fbf456f7",
    str(PARENT_NORMALIZER): "bc2ed6ae62cd68cf908ff2c50f59caa37cf6f57d9d12ab3db5294cf39b2c5f91",
    str(PARENT_OBSERVER): "4bb27873dcae0896db83dcf35b23e71f3890d51a10b8c8b4dc6aa12a7f9fa71a",
    str(QUOTE_NORMALIZER): "12cb76288b69b588d472ca8dcbbda169e676a73b48e61880c192902b0816e95d",
}


def _parents() -> dict[str, str]:
    observed = {
        str(path): base.sha256(path)
        for path in (DIAGNOSIS, PARENT_NORMALIZER, PARENT_OBSERVER, QUOTE_NORMALIZER)
    }
    if observed != EXPECTED_SHA256:
        raise RuntimeError("V2.52.29 fixed parent hash drifted")
    diagnosis = json.loads(base._ordinary(DIAGNOSIS).read_text(encoding="utf-8"))
    aggregate = diagnosis.get("aggregate") or {}
    disposition = aggregate.get("disposition_counts") or {}
    authorization = diagnosis.get("authorization") or {}
    if (
        diagnosis.get("role")
        != "v25228_v25208_production_totality_aggregate_diagnosis"
        or disposition.get("no_bindable_header_reject") != 4
        or disposition.get("missing_data_rows_reject") != 1
        or authorization.get("synthetic_header_totality_successor_design_only")
        is not True
        or authorization.get("runtime_integration_or_prediction_change") is not False
    ):
        raise RuntimeError("V2.52.29 diagnosis authority drifted")
    return observed


def build_design(*, now: int | None = None) -> dict[str, Any]:
    parents = _parents()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "fixed_artifact_hashes": parents,
        "problem_boundary": {
            "completed_production_value_error_tasks": 5,
            "no_bindable_header_reject_tasks": 4,
            "missing_data_rows_reject_tasks": 1,
            "historical_receipts_are_localization_not_treatment_coverage": True,
            "old_fullset_retry_resume_replay_or_selective_rerun": False,
        },
        "single_change": {
            "mode": "drop_explicit_generic_index_then_positional_header",
            "composes_parent_drop_index_and_positional_header_operations": True,
            "leading_source_header_must_be_in_frozen_generic_index_vocabulary": True,
            "source_width_must_equal_required_width_plus_one": True,
            "every_data_row_must_equal_source_width": True,
            "remaining_source_header_count_must_equal_required_count": True,
            "required_columns_must_be_nonempty_unique_and_at_most_twenty": True,
            "all_remaining_cells_preserved_byte_for_byte_after_outer_trim": True,
            "leading_index_cell_values_are_dropped_not_reinterpreted": True,
            "empty_remaining_cells_use_existing_unknown_marker_only": True,
            "exactly_one_structural_candidate_required": True,
            "accepted_output_must_roundtrip_through_frozen_exact_parser": True,
            "missing_data_rows_malformed_width_escaped_pipe_multiple_candidates_and_nonindex_extra_columns_fail_closed": True,
            "question_prompt_search_fetch_model_context_token_wall_network_or_concurrency_budget_change": False,
            "semantic_cell_edit_or_new_fact_invention": False,
        },
        "synthetic_positive_case": {
            "source_header_shape": ["generic_index", "alias_a", "alias_b"],
            "required_header_shape": ["visible_a", "visible_b"],
            "source_data_row_width": 3,
            "expected_output_row_width": 2,
            "expected_candidate_count": 1,
            "content_is_synthetic_and_not_from_benchmark": True,
        },
        "synthetic_negative_cases": [
            "leading_extra_header_is_not_generic_index",
            "generic_index_is_not_leading",
            "two_extra_columns",
            "required_header_duplicate_after_normalization",
            "missing_data_rows",
            "mixed_data_row_width",
            "backslash_escaped_pipe",
            "multiple_admissible_table_candidates",
            "preexisting_internal_entity_collision",
            "more_than_twenty_required_columns",
        ],
        "required_proof": {
            "pure_function_total_for_arbitrary_string_and_schema_sequence": True,
            "positive_output_exact_parser_parity": True,
            "negative_neighbor_states_rejected": True,
            "content_free_receipt_exact_schema_and_tamper_rejection": True,
            "no_filesystem_process_environment_network_model_search_fetch_or_evaluator_capability": True,
            "no_privileged_runtime_field_access": True,
            "parent_normalizer_and_observer_source_unchanged": True,
            "fresh_artifact_disjoint_reliability_gate_before_runtime_adoption": True,
        },
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "authorization": {
            "header_totality_pure_implementation_build_only": True,
            "runtime_integration_or_prediction_change": False,
            "fresh_external_protocol_or_launch": False,
            "old_fullset_retry_resume_replay_replacement_or_selective_rerun": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        },
    }
    value["design_payload_sha256"] = base.payload_sha256(value)
    return validate_design(value)


def validate_design(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("design_payload_sha256", None)
    problem = copied.get("problem_boundary") or {}
    change = copied.get("single_change") or {}
    positive = copied.get("synthetic_positive_case") or {}
    negatives = copied.get("synthetic_negative_cases") or []
    proof = copied.get("required_proof") or {}
    authorization = copied.get("authorization") or {}
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "created_at_unix",
            "fixed_artifact_hashes",
            "problem_boundary",
            "single_change",
            "synthetic_positive_case",
            "synthetic_negative_cases",
            "required_proof",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "network_model_search_fetch_evaluator_benchmark_or_api_called",
            "entropy_or_information_gain_assigns_signed_credit",
            "authorization",
            "design_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("fixed_artifact_hashes") != EXPECTED_SHA256
        or problem
        != {
            "completed_production_value_error_tasks": 5,
            "no_bindable_header_reject_tasks": 4,
            "missing_data_rows_reject_tasks": 1,
            "historical_receipts_are_localization_not_treatment_coverage": True,
            "old_fullset_retry_resume_replay_or_selective_rerun": False,
        }
        or change.get("mode")
        != "drop_explicit_generic_index_then_positional_header"
        or any(
            change.get(name) is not True
            for name in (
                "composes_parent_drop_index_and_positional_header_operations",
                "leading_source_header_must_be_in_frozen_generic_index_vocabulary",
                "source_width_must_equal_required_width_plus_one",
                "every_data_row_must_equal_source_width",
                "remaining_source_header_count_must_equal_required_count",
                "required_columns_must_be_nonempty_unique_and_at_most_twenty",
                "all_remaining_cells_preserved_byte_for_byte_after_outer_trim",
                "leading_index_cell_values_are_dropped_not_reinterpreted",
                "empty_remaining_cells_use_existing_unknown_marker_only",
                "exactly_one_structural_candidate_required",
                "accepted_output_must_roundtrip_through_frozen_exact_parser",
                "missing_data_rows_malformed_width_escaped_pipe_multiple_candidates_and_nonindex_extra_columns_fail_closed",
            )
        )
        or change.get(
            "question_prompt_search_fetch_model_context_token_wall_network_or_concurrency_budget_change"
        )
        is not False
        or change.get("semantic_cell_edit_or_new_fact_invention") is not False
        or positive.get("expected_candidate_count") != 1
        or positive.get("content_is_synthetic_and_not_from_benchmark") is not True
        or len(negatives) != 10
        or len(set(negatives)) != 10
        or not all(proof.values())
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit") is not False
        or authorization
        != {
            "header_totality_pure_implementation_build_only": True,
            "runtime_integration_or_prediction_change": False,
            "fresh_external_protocol_or_launch": False,
            "old_fullset_retry_resume_replay_replacement_or_selective_rerun": False,
            "evaluator_deepwidebench_exact220_avg4_leaderboard_or_sota": False,
        }
        or seal != base.payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.29 header-totality design drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("design",))
    args = parser.parse_args()
    if args.command == "design":
        value = build_design()
        publish_exclusive(ROOT / OUTPUT, value)
        print(
            json.dumps(
                {
                    "path": str(OUTPUT),
                    "mode": value["single_change"]["mode"],
                    "implementation_build_only": value["authorization"][
                        "header_totality_pure_implementation_build_only"
                    ],
                    "runtime_integration": value["authorization"][
                        "runtime_integration_or_prediction_change"
                    ],
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
