#!/usr/bin/env python3
"""Content-free identifiability diagnosis for the frozen V2.53.67 gate.

The task rows contain visible questions, predictions, and private same-forward
state.  This script never decodes those members.  It lexically selects only
predeclared terminal, arm-health, format, and treatment-effect booleans, then
joins them to the already-published content-free forward aggregate and audit.

The diagnosis is post-freeze and cannot authorize a retry, evaluator, or
DeepWideBench run.  Its only positive authorization is a build-only matched
intervention whose candidate deterministically edits a shared base table at a
verified, unique, changed row/column coordinate.
"""

from __future__ import annotations

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

from deepwide_agent import (  # noqa: E402
    v25367_partial_field_third_fresh_external_contract as contract,
)
from scripts import diagnose_v25063_three_run_output_structure as lexical  # noqa: E402


DATE = "20260813"
ROLE = "v25368_v25367_treatment_identifiability_content_free_diagnosis"
SOURCE = Path("scripts/diagnose_v25368_v25367_treatment_identifiability.py")
TEST = Path("tests/test_diagnose_v25368_v25367_treatment_identifiability.py")
OUTPUT = Path(
    f"results/v25368_v25367_treatment_identifiability_diagnosis_v1_{DATE}.json"
)
FORWARD = Path(
    f"results/v25367_partial_field_third_fresh_forward_result_v1_{DATE}.json"
)
AUDIT = Path(
    f"results/v25367_partial_field_third_fresh_forward_audit_v1_{DATE}.json"
)
ROWS = Path(
    f"outputs/v25367_partial_field_third_fresh_v1_{DATE}/frozen_task_results.jsonl"
)
EXPECTED_SHA256 = {
    "forward": "61b6353d8e9d3409b17e647944d2bcd72309d17a3208fb06a038842de46282b7",
    "audit": "03ec3ef59fe7f6a8f723f8215aa9ce1546e43691bf3b7d887049a4038e2e4aa5",
    "rows": "5698bc6827408691e6c5829836c6fe12b7c1d0e6b40fdec2e0e2db6cf88363dd",
}
TOP_LEVEL_FIELDS = frozenset(
    {
        "runtime_completed",
        "failure_as_zero",
        "model_success",
        "normalizer_status",
        "prediction_changed",
        "candidate_production_prompt_changed",
        "attributable_prediction_change",
        "unattributable_prediction_change",
    }
)


def _ordinary(relative: Path) -> Path:
    return contract.ordinary(ROOT, relative, tracked=True)


def _read_json(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.68 expected JSON object")
    return value


def _parents() -> tuple[dict[str, str], dict[str, Any]]:
    observed = {
        "forward": contract.sha256(_ordinary(FORWARD)),
        "audit": contract.sha256(_ordinary(AUDIT)),
        "rows": contract.sha256(_ordinary(ROWS)),
    }
    if observed != EXPECTED_SHA256:
        raise RuntimeError("V2.53.68 frozen parent hash drifted")
    forward = _read_json(FORWARD)
    audit = _read_json(AUDIT)
    decision = forward.get("mechanism_decision") or {}
    audit_authorization = audit.get("authorization") or {}
    if (
        forward.get("role")
        != "v25367_partial_field_third_fresh_forward_result"
        or audit.get("role")
        != "v25367_partial_field_third_fresh_forward_audit"
        or forward.get("protocol_id") != contract.PROTOCOL_ID
        or audit.get("protocol_id") != contract.PROTOCOL_ID
        or not contract.sealed(forward, "result_payload_sha256")
        or not contract.sealed(audit, "audit_payload_sha256")
        or audit.get("forward_result_sha256") != observed["forward"]
        or audit.get("task_rows_sha256") != observed["rows"]
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or decision.get("mechanism_gate_passed") is not False
        or decision.get("failed_checks")
        != ["minimum_attributable_prediction_change"]
        or audit_authorization.get("deepwidebench_successor_build") is not False
        or audit_authorization.get("deepwidebench_forward_or_evaluator") is not False
    ):
        raise RuntimeError("V2.53.68 frozen parent barrier drifted")
    return observed, forward


def _row_aggregate() -> dict[str, int]:
    count = 0
    completed = 0
    failure_as_zero = 0
    both_model_success = 0
    both_normalizer_exact = 0
    prompt_changed = 0
    prompt_changed_prediction_equal = 0
    prompt_unchanged = 0
    prediction_changed = 0
    attributable = 0
    unattributable = 0
    for line in _ordinary(ROWS).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        count += 1
        row = lexical.selected_top_level_fields(line, TOP_LEVEL_FIELDS)
        model = row["model_success"]
        normalizer = row["normalizer_status"]
        if (
            not isinstance(model, Mapping)
            or set(model) != set(contract.ARMS)
            or any(not isinstance(value, bool) for value in model.values())
            or not isinstance(normalizer, Mapping)
            or set(normalizer) != set(contract.ARMS)
            or any(not isinstance(value, str) for value in normalizer.values())
            or any(
                not isinstance(row[name], bool)
                for name in TOP_LEVEL_FIELDS - {"model_success", "normalizer_status"}
            )
            or row["failure_as_zero"] is row["runtime_completed"]
            or row["attributable_prediction_change"]
            and not row["prediction_changed"]
            or row["unattributable_prediction_change"]
            is not bool(
                row["prediction_changed"]
                and not row["attributable_prediction_change"]
            )
        ):
            raise RuntimeError("V2.53.68 selected row state drifted")
        completed += int(row["runtime_completed"])
        failure_as_zero += int(row["failure_as_zero"])
        both_model_success += int(all(model.values()))
        both_normalizer_exact += int(
            all(value == "exact" for value in normalizer.values())
        )
        prompt_changed += int(row["candidate_production_prompt_changed"])
        prompt_changed_prediction_equal += int(
            row["candidate_production_prompt_changed"]
            and not row["prediction_changed"]
        )
        prompt_unchanged += int(not row["candidate_production_prompt_changed"])
        prediction_changed += int(row["prediction_changed"])
        attributable += int(row["attributable_prediction_change"])
        unattributable += int(row["unattributable_prediction_change"])
    output = {
        "task_rows": count,
        "runtime_completed_tasks": completed,
        "failure_as_zero_tasks": failure_as_zero,
        "both_arms_model_success_tasks": both_model_success,
        "both_arms_exact_normalizer_tasks": both_normalizer_exact,
        "candidate_prompt_changed_tasks": prompt_changed,
        "candidate_prompt_changed_prediction_equal_tasks": (
            prompt_changed_prediction_equal
        ),
        "candidate_prompt_unchanged_tasks": prompt_unchanged,
        "prediction_changed_tasks": prediction_changed,
        "attributable_prediction_changed_tasks": attributable,
        "unattributable_prediction_changed_tasks": unattributable,
    }
    expected = {
        "task_rows": 20,
        "runtime_completed_tasks": 20,
        "failure_as_zero_tasks": 0,
        "both_arms_model_success_tasks": 20,
        "both_arms_exact_normalizer_tasks": 20,
        "candidate_prompt_changed_tasks": 16,
        "candidate_prompt_changed_prediction_equal_tasks": 16,
        "candidate_prompt_unchanged_tasks": 4,
        "prediction_changed_tasks": 0,
        "attributable_prediction_changed_tasks": 0,
        "unattributable_prediction_changed_tasks": 0,
    }
    if output != expected:
        raise RuntimeError("V2.53.68 frozen row aggregate drifted")
    return output


def _aggregate(forward: Mapping[str, Any]) -> dict[str, Any]:
    parent = forward.get("aggregate") or {}
    parent_projection = {
        "terminal_tasks": parent.get("terminal_tasks"),
        "verified_record_tasks": parent.get("verified_record_tasks"),
        "verified_record_count_total": parent.get("verified_record_count_total"),
        "verified_field_count_total": parent.get("verified_field_count_total"),
        "partial_field_parsed_record_count_total": parent.get(
            "partial_field_parsed_record_count_total"
        ),
        "partial_field_parsed_field_count_total": parent.get(
            "partial_field_parsed_field_count_total"
        ),
        "partial_field_accepted_field_count_total": parent.get(
            "partial_field_accepted_field_count_total"
        ),
        "partial_field_rejected_field_count_total": parent.get(
            "partial_field_rejected_field_count_total"
        ),
        "physical_queries": parent.get("all_physical_queries"),
        "physical_fetches": parent.get("all_physical_fetches"),
        "physical_model_forwards": parent.get("all_physical_model_forwards"),
        "system_total_tokens": parent.get("system_total_tokens"),
        "batch_wall_seconds": parent.get("batch_wall_seconds"),
    }
    expected = {
        "terminal_tasks": 20,
        "verified_record_tasks": 16,
        "verified_record_count_total": 16,
        "verified_field_count_total": 49,
        "partial_field_parsed_record_count_total": 17,
        "partial_field_parsed_field_count_total": 68,
        "partial_field_accepted_field_count_total": 49,
        "partial_field_rejected_field_count_total": 19,
        "physical_queries": 80,
        "physical_fetches": 199,
        "physical_model_forwards": 80,
        "system_total_tokens": 1_034_407,
        "batch_wall_seconds": 54.75452,
    }
    if parent_projection != expected:
        raise RuntimeError("V2.53.68 parent aggregate drifted")
    return {
        "forward_content_free": parent_projection,
        "row_content_free": _row_aggregate(),
    }


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    parents, forward = _parents()
    aggregate = _aggregate(forward)
    row = aggregate["row_content_free"]
    parent = aggregate["forward_content_free"]
    diagnosis = {
        "mechanism_gate_passed": False,
        "verified_treatment_exposure_observed": (
            parent["verified_field_count_total"] == 49
            and row["candidate_prompt_changed_tasks"] == 16
        ),
        "paired_synthesis_and_format_viability_complete": (
            row["both_arms_model_success_tasks"] == 20
            and row["both_arms_exact_normalizer_tasks"] == 20
        ),
        "all_natural_treatment_outputs_equal_their_controls": (
            row["candidate_prompt_changed_prediction_equal_tasks"]
            == row["candidate_prompt_changed_tasks"]
            == 16
            and row["prediction_changed_tasks"] == 0
        ),
        "verified_prefix_has_identified_causal_effect": False,
        "raw_page_redundancy_and_model_insensitivity_are_distinguishable": False,
        "exact_normalizer_status_establishes_format_not_answer_correctness": True,
        "same_population_retry_replay_or_evaluator_can_resolve_identifiability": False,
        "next_candidate_uses_one_shared_production_synthesis": True,
        "control_is_shared_base_table_and_candidate_is_deterministic_edit": True,
        "edit_requires_unique_verified_row_column_coordinate": True,
        "edit_requires_verified_value_different_from_base_cell": True,
        "unknown_conflict_missing_or_ambiguous_coordinate_is_identity_noop": True,
        "table_shape_row_order_and_all_other_cells_must_be_preserved": True,
        "new_search_fetch_model_token_context_or_wall_budget_allowed": False,
        "fresh_disjoint_structurally_harder_outcome_blind_population_required": True,
        "quality_gate_requires_changed_safe_coordinate_to_edit_to_prediction_change": True,
        "entropy_or_information_gain_signed_credit": 0,
    }
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": parents,
        "aggregate": aggregate,
        "diagnosis": diagnosis,
        "content_policy": {
            "decoded_top_level_task_row_fields": sorted(TOP_LEVEL_FIELDS),
            "all_other_task_row_values_skipped_lexically": True,
            "task_identity_question_query_url_page_quote_prediction_answer_gold_evaluator_or_score_decoded_or_emitted": False,
            "historical_correctness_or_outcome_used_for_future_runtime_routing": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        },
        "authorization": {
            "changed_safe_matched_intervention_build_only": True,
            "same_population_retry_resume_replay_backfill_replacement_or_evaluator": False,
            "new_external_forward": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    diagnosis = copied.get("diagnosis") or {}
    row = (copied.get("aggregate") or {}).get("row_content_free") or {}
    required_true = (
        "verified_treatment_exposure_observed",
        "paired_synthesis_and_format_viability_complete",
        "all_natural_treatment_outputs_equal_their_controls",
        "exact_normalizer_status_establishes_format_not_answer_correctness",
        "next_candidate_uses_one_shared_production_synthesis",
        "control_is_shared_base_table_and_candidate_is_deterministic_edit",
        "edit_requires_unique_verified_row_column_coordinate",
        "edit_requires_verified_value_different_from_base_cell",
        "unknown_conflict_missing_or_ambiguous_coordinate_is_identity_noop",
        "table_shape_row_order_and_all_other_cells_must_be_preserved",
        "fresh_disjoint_structurally_harder_outcome_blind_population_required",
        "quality_gate_requires_changed_safe_coordinate_to_edit_to_prediction_change",
    )
    required_false = (
        "mechanism_gate_passed",
        "verified_prefix_has_identified_causal_effect",
        "raw_page_redundancy_and_model_insensitivity_are_distinguishable",
        "same_population_retry_replay_or_evaluator_can_resolve_identifiability",
        "new_search_fetch_model_token_context_or_wall_budget_allowed",
    )
    expected_authorization = {
        "changed_safe_matched_intervention_build_only": True,
        "same_population_retry_resume_replay_backfill_replacement_or_evaluator": False,
        "new_external_forward": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
    }
    if (
        copied.get("role") != ROLE
        or seal != contract.payload_sha256(unsigned)
        or any(diagnosis.get(name) is not True for name in required_true)
        or any(diagnosis.get(name) is not False for name in required_false)
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or row.get("task_rows") != 20
        or row.get("candidate_prompt_changed_tasks") != 16
        or row.get("candidate_prompt_changed_prediction_equal_tasks") != 16
        or row.get("prediction_changed_tasks") != 0
        or copied.get("authorization") != expected_authorization
        or copied.get("content_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
    ):
        raise RuntimeError("V2.53.68 diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    payload = (
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "role": value["role"],
                "aggregate": value["aggregate"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
