#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.55.11 mechanism NO-GO.

Only the hash-bound forward result and forward audit are opened.  No task row,
question, opaque id, URL, page, prediction, truth, evaluator record, score,
reward, or per-task outcome is read.  The diagnosis authorizes a build-only
successor whose scheduling signal is observable evidence-coverage deficit,
not model-emitted literal ``Unknown``.  Entropy/IG remains shadow-only with
zero signed credit.
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

from deepwide_agent import v25511_multirow_uncertainty_external_contract as contract  # noqa: E402
from scripts import run_v25511_multirow_uncertainty_external as runner  # noqa: E402


DATE = "20260814"
ROLE = "v25512_v25511_literal_unknown_no_go_aggregate_diagnosis"
OUTPUT = Path(
    f"results/v25512_v25511_literal_unknown_no_go_diagnosis_v1_{DATE}.json"
)
FORWARD_RESULT_SHA256 = (
    "82eee3338128b01710db2cd1327159251bc6a1425608ee6439c4807b23a6cef4"
)
FORWARD_AUDIT_SHA256 = (
    "7ecf284e16f22ecdeffc0b8797c7317ed057dd70a7d1571d0c180de1e86c48d3"
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
        raise RuntimeError("V2.55.12 expected JSON object")
    return value


def _inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    for relative, digest in FROZEN_INPUTS.items():
        if contract.sha256(ROOT / relative) != digest:
            raise RuntimeError("V2.55.12 frozen input hash drifted")
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    audit = _read(contract.FORWARD_AUDIT)
    if (
        audit.get("role")
        != "v25511_multirow_uncertainty_external_forward_audit"
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
        raise RuntimeError("V2.55.12 forward-audit barrier drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, _audit = _inputs()
    aggregate = runner.validate_aggregate(forward["aggregate"])
    links = aggregate["multirow_eligible_link_tasks"]
    uncertainty = aggregate["positive_uncertainty_candidate_tasks"]
    requests = aggregate["logical_detail_request_tasks"]
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
        "multirow_eligible_link_tasks": links,
        "eligible_unique_link_count_total": aggregate[
            "eligible_unique_link_count_total"
        ],
        "positive_uncertainty_candidate_tasks": uncertainty,
        "positive_uncertainty_candidate_count_total": aggregate[
            "positive_uncertainty_candidate_count_total"
        ],
        "logical_detail_request_tasks": requests,
        "admitted_detail_fetch_tasks": aggregate["admitted_detail_fetch_tasks"],
        "exact_nonredirected_detail_page_tasks": aggregate[
            "exact_nonredirected_detail_page_tasks"
        ],
        "combined_generic_observation_tasks": aggregate[
            "combined_generic_observation_tasks"
        ],
        "combined_generic_observation_count_total": aggregate[
            "combined_generic_observation_count_total"
        ],
        "treatment_changed_tasks": aggregate["treatment_changed_tasks"],
        "treatment_changed_coordinate_count_total": aggregate[
            "treatment_changed_coordinate_count_total"
        ],
        "eligible_link_to_literal_unknown_task_retention_numerator": uncertainty,
        "eligible_link_to_literal_unknown_task_retention_denominator": links,
        "literal_unknown_to_request_task_retention_numerator": requests,
        "literal_unknown_to_request_task_retention_denominator": uncertainty,
        "runtime_failure_budget_capacity_or_parser_is_not_the_observed_cause": (
            aggregate["completed_runtime_tasks"] == aggregate["task_count"]
            and aggregate["failure_as_zero_tasks"] == 0
            and aggregate["control_application_failure_tasks"] == 0
            and aggregate["candidate_application_failure_tasks"] == 0
            and aggregate["budget_rejection_tasks"] == 0
            and aggregate["combined_generic_observation_tasks"] >= 5
        ),
        "multirow_visible_link_reach_is_established": links >= 6,
        "literal_unknown_is_not_a_reliable_epistemic_uncertainty_proxy": (
            links >= 6 and uncertainty == 0
        ),
        "primary_bottleneck": (
            "literal_Unknown_is_absent_from_all_eligible_control_rows_so_the_"
            "visible_uncertainty_gate_suppresses_every_otherwise_reachable_detail_action"
        ),
        "next_design_obligations": [
            "do_not_open_v25511_task_rows_pages_predictions_or_truth_for_tuning",
            "do_not_retry_resume_rerun_replace_or_reuse_the_v25511_population",
            "replace_literal_unknown_with_row_local_source_bound_evidence_coverage_deficit",
            "coverage_deficit_must_be_computed_only_from_control_application_receipts_and_visible_schema",
            "retain_public_same_origin_path_anchor_one_url_per_row_admissibility",
            "retain_one_parent_matched_control_one_fetch_and_query4_fetch14_model3_caps",
            "require_a_new_task_disjoint_mechanism_gate_before_quality_or_exact220",
            "retain_zero_signed_entropy_credit",
        ],
    }
    checks = {
        "frozen_forward_and_audit_hash_exact": True,
        "forward_result_and_content_free_aggregate_validate": True,
        "forward_audit_valid_and_quality_not_authorized": True,
        "all_tasks_terminal_without_runtime_application_or_budget_failure": diagnosis[
            "runtime_failure_budget_capacity_or_parser_is_not_the_observed_cause"
        ],
        "multirow_link_reach_meets_preregistered_floor": links == 6,
        "nineteen_unique_eligible_links_observed": aggregate[
            "eligible_unique_link_count_total"
        ]
        == 19,
        "literal_unknown_candidates_requests_fetches_and_changes_are_zero": (
            uncertainty == 0
            and aggregate["positive_uncertainty_candidate_count_total"] == 0
            and requests == 0
            and aggregate["admitted_detail_fetch_tasks"] == 0
            and aggregate["exact_nonredirected_detail_page_tasks"] == 0
            and aggregate["treatment_changed_tasks"] == 0
        ),
        "generic_observations_exist_without_detail_action": (
            aggregate["combined_generic_observation_tasks"] == 5
            and aggregate["combined_generic_observation_count_total"] == 5
        ),
        "literal_unknown_proxy_falsified": diagnosis[
            "literal_unknown_is_not_a_reliable_epistemic_uncertainty_proxy"
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
            "evidence_coverage_deficit_successor_build": not findings,
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
        or diagnosis.get("multirow_eligible_link_tasks") != 6
        or diagnosis.get("eligible_unique_link_count_total") != 19
        or diagnosis.get("positive_uncertainty_candidate_tasks") != 0
        or diagnosis.get("logical_detail_request_tasks") != 0
        or diagnosis.get("combined_generic_observation_tasks") != 5
        or diagnosis.get("treatment_changed_tasks") != 0
        or diagnosis.get(
            "literal_unknown_is_not_a_reliable_epistemic_uncertainty_proxy"
        )
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
            "evidence_coverage_deficit_successor_build": valid,
            "external_protocol_or_forward": False,
            "postfreeze_quality_or_truth": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.12 diagnosis drifted")
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
