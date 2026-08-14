#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.55.04 mechanism NO-GO.

Only the hash-bound forward result and forward audit are opened.  No task row,
question, opaque id, URL, page, source field/value, prediction, truth,
evaluator record, score, reward, or per-task outcome is read.  The diagnosis
authorizes successor design only; entropy/IG remains shadow-only with zero
signed credit.
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

from deepwide_agent import v25504_generic_mechanical_external_contract as contract  # noqa: E402
from scripts import run_v25504_generic_mechanical_external as runner  # noqa: E402


DATE = "20260814"
ROLE = "v25505_v25504_generic_materiality_no_go_aggregate_diagnosis"
OUTPUT = Path(
    f"results/v25505_v25504_generic_materiality_no_go_diagnosis_v1_{DATE}.json"
)
FORWARD_RESULT_SHA256 = (
    "4032d63f87854e8895102798c65f1ce5968f358b64bc122199d3fe0fd3b89dc4"
)
FORWARD_AUDIT_SHA256 = (
    "090de4e8bdc33fe329577d82fcca36e2a537709dac928729073877164d19bc10"
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
        raise RuntimeError("V2.55.05 expected JSON object")
    return value


def _inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    for relative, digest in FROZEN_INPUTS.items():
        if contract.sha256(ROOT / relative) != digest:
            raise RuntimeError("V2.55.05 frozen input hash drifted")
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    audit = _read(contract.FORWARD_AUDIT)
    if (
        audit.get("role") != "v25504_generic_mechanical_external_forward_audit"
        or audit.get("protocol_id") != contract.PROTOCOL_ID
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("forward_result_sha256") != FORWARD_RESULT_SHA256
        or audit.get("aggregate") != forward["aggregate"]
        or audit.get("mechanism_decision") != forward["mechanism_decision"]
        or audit.get("authorization", {}).get("postfreeze_quality_protocol")
        is not False
        or not contract.sealed(audit, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.55.05 forward-audit barrier drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, _audit = _inputs()
    aggregate = runner.validate_aggregate(forward["aggregate"])
    field_tasks = aggregate["generic_mechanical_field_surface_tasks"]
    observation_tasks = aggregate["generic_mechanical_observation_tasks"]
    candidate_tasks = aggregate["available_candidate_tasks"]
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
        "combined_candidate_page_tasks": aggregate[
            "combined_candidate_page_tasks"
        ],
        "combined_candidate_page_count_total": aggregate[
            "combined_candidate_page_count_total"
        ],
        "generic_mechanical_field_surface_tasks": field_tasks,
        "generic_mechanical_field_surface_count_total": aggregate[
            "generic_mechanical_field_surface_count_total"
        ],
        "generic_mechanical_observation_tasks": observation_tasks,
        "generic_mechanical_observation_count_total": aggregate[
            "generic_mechanical_observation_count_total"
        ],
        "available_candidate_tasks": candidate_tasks,
        "available_candidate_count_total": aggregate[
            "available_candidate_count_total"
        ],
        "prediction_changed_tasks": aggregate["prediction_changed_tasks"],
        "surface_to_observation_task_retention_numerator": observation_tasks,
        "surface_to_observation_task_retention_denominator": field_tasks,
        "observation_to_material_candidate_task_retention_numerator": candidate_tasks,
        "observation_to_material_candidate_task_retention_denominator": observation_tasks,
        "observations_rejected_as_unchanged_or_surface_equivalent_task_lower_bound": max(
            0, observation_tasks - candidate_tasks
        ),
        "runtime_failure_budget_or_capacity_is_not_the_observed_cause": (
            aggregate["completed_runtime_tasks"] == aggregate["task_count"]
            and aggregate["failure_as_zero_tasks"] == 0
            and aggregate["application_failure_tasks"] == 0
            and aggregate["budget_rejection_tasks"] == 0
        ),
        "parser_engagement_is_no_longer_the_primary_bottleneck": (
            field_tasks >= 10 and observation_tasks >= 10
        ),
        "primary_bottleneck": (
            "evidence_is_often_already_equal_or_surface_equivalent_to_the_shared_control_so_only_one_of_ten_observation_tasks_yields_a_material_edit"
        ),
        "next_design_obligations": [
            "do_not_relax_materiality_or_unique_coordinate_fail_closed_rules",
            "do_not_open_v25504_task_rows_pages_predictions_or_truth_for_tuning",
            "prefer_upstream_evidence_selection_or_synthesis_coverage_that_can_change_missing_or_wrong_cells",
            "require_a_new_task_disjoint_mechanism_gate_before_quality_or_exact220",
            "retain_query4_fetch14_model3_and_zero_signed_entropy_credit",
        ],
    }
    checks = {
        "frozen_forward_and_audit_hash_exact": True,
        "forward_result_and_content_free_aggregate_validate": True,
        "forward_audit_valid_and_quality_not_authorized": True,
        "all_tasks_terminal_without_runtime_application_or_budget_failure": diagnosis[
            "runtime_failure_budget_or_capacity_is_not_the_observed_cause"
        ],
        "combined_pages_exist_for_all_tasks": aggregate[
            "combined_candidate_page_tasks"
        ]
        == 20,
        "generic_parser_engages_on_ten_tasks": field_tasks == 10,
        "evidence_closed_observations_engage_on_ten_tasks": observation_tasks == 10,
        "only_one_material_candidate_and_prediction_change": (
            candidate_tasks == 1
            and aggregate["available_candidate_count_total"] == 1
            and aggregate["applied_candidate_tasks"] == 1
            and aggregate["prediction_changed_tasks"] == 1
        ),
        "parser_engagement_not_primary_bottleneck": diagnosis[
            "parser_engagement_is_no_longer_the_primary_bottleneck"
        ],
        "mechanism_no_go_and_truth_quality_unopened": forward[
            "mechanism_decision"
        ]["mechanism_gate_passed"]
        is False,
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
            "upstream_evidence_selection_or_synthesis_coverage_successor_design": not findings,
            "relax_materiality_or_unique_coordinate_rules": False,
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
        or diagnosis.get("generic_mechanical_field_surface_tasks") != 10
        or diagnosis.get("generic_mechanical_observation_tasks") != 10
        or diagnosis.get("available_candidate_tasks") != 1
        or diagnosis.get("prediction_changed_tasks") != 1
        or diagnosis.get("parser_engagement_is_no_longer_the_primary_bottleneck")
        is not True
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
            "upstream_evidence_selection_or_synthesis_coverage_successor_design": valid,
            "relax_materiality_or_unique_coordinate_rules": False,
            "external_protocol_or_forward": False,
            "postfreeze_quality_or_truth": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.05 diagnosis drifted")
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
