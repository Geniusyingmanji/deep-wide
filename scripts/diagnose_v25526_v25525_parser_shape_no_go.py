#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.55.25 mechanism NO-GO.

Only the hash-bound forward result and forward audit are opened.  No task row,
question, opaque id, URL, page, source field/value, prediction, truth,
evaluator record, score, reward, or per-task outcome is read.

The aggregate now separates the full funnel.  Eight exact IANA pages bind an
exact visible row key and the page surface, but produce zero raw visible-field
surfaces.  Therefore loss is proven to occur before evidence observation and
before materiality filtering.  This diagnosis authorizes only independent
public-page-shape study and a pure parser build, never a retry or forward.
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

from deepwide_agent import v25525_source_bound_external_contract as contract  # noqa: E402
from scripts import run_v25525_source_bound_external as runner  # noqa: E402


DATE = "20260814"
ROLE = "v25526_v25525_parser_shape_no_go_aggregate_diagnosis"
OUTPUT = Path(
    f"results/v25526_v25525_parser_shape_no_go_diagnosis_v1_{DATE}.json"
)
FORWARD_RESULT_SHA256 = (
    "2a6532a76d6fc0639851fba9c3e143a0a1b6500e2a3eba26ae0d4f37b9c36178"
)
FORWARD_AUDIT_SHA256 = (
    "5d2a750cfab6e210f3e94972ca7dd12376e6ebdd9e243a5a66c4b9feb869b7ea"
)
FROZEN_INPUTS = {
    str(contract.FORWARD_RESULT): FORWARD_RESULT_SHA256,
    str(contract.FORWARD_AUDIT): FORWARD_AUDIT_SHA256,
}


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(
        contract.ordinary(ROOT, relative, tracked=True).read_text(encoding="utf-8")
    )
    if not isinstance(value, dict):
        raise RuntimeError("V2.55.26 expected JSON object")
    return value


def _inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    for relative, digest in FROZEN_INPUTS.items():
        if contract.sha256(ROOT / relative) != digest:
            raise RuntimeError("V2.55.26 frozen input hash drifted")
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    audit = _read(contract.FORWARD_AUDIT)
    if (
        audit.get("role") != "v25525_source_bound_external_forward_audit"
        or audit.get("protocol_id") != contract.PROTOCOL_ID
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("forward_result_sha256") != FORWARD_RESULT_SHA256
        or audit.get("aggregate") != forward["aggregate"]
        or audit.get("mechanism_decision") != forward["mechanism_decision"]
        or audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is not False
        or audit.get("authorization", {}).get("deepwidebench_forward_or_evaluator")
        is not False
        or not contract.sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.55.26 forward-audit barrier drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, _audit = _inputs()
    aggregate = runner.validate_aggregate(forward["aggregate"])
    failure_free = (
        aggregate["completed_runtime_tasks"] == aggregate["task_count"]
        and aggregate["failure_as_zero_tasks"] == 0
        and aggregate["outer_failure_tasks"] == 0
        and aggregate["parent_control_application_failure_tasks"] == 0
        and aggregate["parent_detail_fetch_failure_tasks"] == 0
        and aggregate["parent_generic_candidate_application_failure_tasks"] == 0
        and aggregate["candidate_application_failure_tasks"] == 0
        and aggregate["budget_rejection_tasks"] == 0
        and aggregate["detail_capacity_shortfall_count_total"] == 0
    )
    binding_funnel = (
        aggregate["exact_nonredirected_detail_page_tasks"] == 16
        and aggregate["exact_iana_url_page_tasks"] == 8
        and aggregate["url_row_key_bound_page_tasks"] == 8
        and aggregate["identity_surface_bound_page_tasks"] == 8
    )
    parser_miss = (
        binding_funnel
        and aggregate["raw_field_surface_tasks"] == 0
        and aggregate["detail_raw_field_surface_count_total"] == 0
        and aggregate["evidence_closed_observation_tasks"] == 0
        and aggregate["detail_evidence_closed_observation_count_total"] == 0
    )
    no_materiality_stage = (
        aggregate["detail_coordinate_group_count_total"] == 0
        and aggregate["material_candidate_tasks"] == 0
        and aggregate["detail_available_candidate_count_total"] == 0
        and aggregate["detail_applied_coordinate_count_total"] == 0
        and aggregate["treatment_changed_tasks"] == 0
        and aggregate["treatment_changed_coordinate_count_total"] == 0
    )
    diagnosis = {
        "mechanism_gate_passed": forward["mechanism_decision"][
            "mechanism_gate_passed"
        ],
        "failed_checks": copy.deepcopy(
            forward["mechanism_decision"]["failed_checks"]
        ),
        "task_count": aggregate["task_count"],
        "terminal_tasks": aggregate["terminal_tasks"],
        "completed_runtime_tasks": aggregate["completed_runtime_tasks"],
        "multirow_eligible_link_tasks": aggregate[
            "multirow_eligible_link_tasks"
        ],
        "positive_evidence_deficit_candidate_tasks": aggregate[
            "positive_evidence_deficit_candidate_tasks"
        ],
        "logical_detail_request_tasks": aggregate["logical_detail_request_tasks"],
        "admitted_detail_fetch_tasks": aggregate["admitted_detail_fetch_tasks"],
        "exact_nonredirected_detail_page_tasks": aggregate[
            "exact_nonredirected_detail_page_tasks"
        ],
        "exact_iana_url_page_tasks": aggregate["exact_iana_url_page_tasks"],
        "url_row_key_bound_page_tasks": aggregate[
            "url_row_key_bound_page_tasks"
        ],
        "identity_surface_bound_page_tasks": aggregate[
            "identity_surface_bound_page_tasks"
        ],
        "raw_field_surface_tasks": aggregate["raw_field_surface_tasks"],
        "detail_raw_field_surface_count_total": aggregate[
            "detail_raw_field_surface_count_total"
        ],
        "evidence_closed_observation_tasks": aggregate[
            "evidence_closed_observation_tasks"
        ],
        "material_candidate_tasks": aggregate["material_candidate_tasks"],
        "treatment_changed_tasks": aggregate["treatment_changed_tasks"],
        "runtime_failure_budget_capacity_or_fetch_is_not_the_observed_cause": failure_free,
        "exact_iana_url_row_and_surface_binding_is_established": binding_funnel,
        "field_parser_shape_miss_is_proven": parser_miss,
        "materiality_filter_is_not_reached": no_materiality_stage,
        "primary_bottleneck": (
            "eight_exact_iana_pages_bind_the_visible_row_and_page_surface_but_"
            "produce_zero_raw_visible_field_surfaces"
        ),
        "next_design_obligations": [
            "do_not_open_v25525_task_rows_pages_predictions_or_truth_for_tuning",
            "do_not_retry_resume_rerun_replace_or_reuse_the_v25525_population",
            "study_current_public_iana_page_shapes_independently_of_frozen_v25525_outputs",
            "extend_only_pure_mechanical_visible_field_grammars_with_synthetic_and_independent_public_page_fixtures",
            "preserve_exact_url_row_key_page_surface_unique_coordinate_materiality_and_list_fail_closed_rules",
            "retain_content_free_parser_observation_rejection_and_materiality_counters",
            "require_a_new_task_disjoint_mechanism_gate_before_quality_or_exact220",
            "retain_query4_fetch14_model3_and_zero_signed_entropy_credit",
        ],
    }
    checks = {
        "frozen_forward_and_audit_hash_exact": True,
        "forward_result_and_content_free_aggregate_validate": True,
        "forward_audit_valid_and_quality_not_authorized": True,
        "all_tasks_terminal_without_runtime_application_budget_capacity_or_fetch_failure": failure_free,
        "reach_request_and_fetch_funnel_exceeds_gate": (
            aggregate["multirow_eligible_link_tasks"] == 9
            and aggregate["positive_evidence_deficit_candidate_tasks"] == 16
            and aggregate["logical_detail_request_tasks"] == 16
            and aggregate["admitted_detail_fetch_tasks"] == 16
        ),
        "exact_iana_url_row_and_surface_binding_exact_eight": binding_funnel,
        "zero_raw_field_surface_and_observation": parser_miss,
        "materiality_stage_not_reached_and_zero_edit": no_materiality_stage,
        "mechanism_no_go_only_downstream_of_binding": forward[
            "mechanism_decision"
        ]["failed_checks"]
        == [
            "minimum_applied_coordinate_count_total",
            "minimum_evidence_closed_observation_tasks",
            "minimum_material_candidate_tasks",
            "minimum_raw_field_surface_tasks",
            "minimum_treatment_changed_coordinate_count_total",
            "minimum_treatment_changed_tasks",
        ],
        "positive_signed_credit_zero": aggregate["positive_signed_credit_count"]
        == 0,
        "task_rows_question_opaque_id_url_page_prediction_truth_or_per_task_outcome_not_opened": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_absent": True,
        "network_model_search_fetch_evaluator_benchmark_or_api_not_called": True,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "frozen_inputs": copy.deepcopy(FROZEN_INPUTS),
        "content_free_aggregate_only": True,
        "diagnosis": diagnosis,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "task_rows_question_opaque_id_url_page_prediction_truth_evaluator_or_per_task_outcome_read": False,
        "mapping_gold_category_question_type_split_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "independent_public_iana_page_shape_study": not findings,
            "pure_mechanical_field_parser_successor_build": not findings,
            "open_v25525_task_rows_pages_predictions_or_truth_for_tuning": False,
            "relax_url_row_surface_unique_coordinate_or_materiality_rules": False,
            "external_protocol_or_forward": False,
            "postfreeze_quality_or_truth": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    valid = copied.get("audit_valid") is True
    diagnosis = copied.get("diagnosis") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("frozen_inputs") != FROZEN_INPUTS
        or copied.get("content_free_aggregate_only") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or diagnosis.get("mechanism_gate_passed") is not False
        or diagnosis.get("exact_nonredirected_detail_page_tasks") != 16
        or diagnosis.get("exact_iana_url_page_tasks") != 8
        or diagnosis.get("url_row_key_bound_page_tasks") != 8
        or diagnosis.get("identity_surface_bound_page_tasks") != 8
        or diagnosis.get("raw_field_surface_tasks") != 0
        or diagnosis.get("evidence_closed_observation_tasks") != 0
        or diagnosis.get("material_candidate_tasks") != 0
        or diagnosis.get("treatment_changed_tasks") != 0
        or diagnosis.get("field_parser_shape_miss_is_proven") is not True
        or diagnosis.get("materiality_filter_is_not_reached") is not True
        or copied.get(
            "task_rows_question_opaque_id_url_page_prediction_truth_evaluator_or_per_task_outcome_read"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("network_model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("authorization")
        != {
            "independent_public_iana_page_shape_study": valid,
            "pure_mechanical_field_parser_successor_build": valid,
            "open_v25525_task_rows_pages_predictions_or_truth_for_tuning": False,
            "relax_url_row_surface_unique_coordinate_or_materiality_rules": False,
            "external_protocol_or_forward": False,
            "postfreeze_quality_or_truth": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.26 diagnosis drifted")
    return copied


def _publish(value: Mapping[str, Any]) -> None:
    path = ROOT / OUTPUT
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
    value = build_diagnosis()
    if value["findings"]:
        raise RuntimeError(value["findings"])
    _publish(value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "audit_valid": value["audit_valid"],
                "diagnosis": value["diagnosis"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
