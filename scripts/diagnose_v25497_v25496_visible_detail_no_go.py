#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.54.96 mechanism NO-GO.

Only the already-published forward result and forward-audit JSON objects are
opened.  Their content-free aggregates are hash-bound and validated without
opening task rows, questions, opaque ids, URLs, pages, predictions, truth,
evaluator material, scores, rewards, or historical per-task outcomes.  The
diagnosis authorizes successor design and a separate question-only transfer
audit, never a forward.  Entropy/information gain remains shadow-only and
assigns zero signed credit.
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

from deepwide_agent import v25496_visible_row_key_detail_external_contract as contract  # noqa: E402
from scripts import run_v25496_visible_row_key_detail_external as runner  # noqa: E402


DATE = "20260814"
ROLE = "v25497_v25496_visible_detail_no_go_aggregate_diagnosis"
OUTPUT = Path(
    f"results/v25497_v25496_visible_detail_no_go_diagnosis_v1_{DATE}.json"
)
FORWARD_RESULT_SHA256 = (
    "6ec33be3c58bac0f7f4bea7ba66c0ae378a7d87aed516a15810b63a9ec0b020c"
)
FORWARD_AUDIT_SHA256 = (
    "9253f99f72709c0b4cd9514b3c4dcb23c4f649fd69803ca506471a342ac0c606"
)
FROZEN_INPUTS = {
    str(contract.FORWARD_RESULT): FORWARD_RESULT_SHA256,
    str(contract.FORWARD_AUDIT): FORWARD_AUDIT_SHA256,
}
EXPECTED_FUNNEL = {
    "terminal_tasks": 20,
    "raw_page_visible_link_tasks": 20,
    "joint_bound_link_tasks": 5,
    "eligible_unique_link_tasks": 4,
    "logical_detail_request_tasks": 4,
    "exact_nonredirected_detail_page_tasks": 4,
    "identity_surface_bound_detail_page_tasks": 4,
    "field_surface_tasks": 0,
    "evidence_closed_observation_tasks": 0,
    "available_candidate_tasks": 0,
    "applied_candidate_tasks": 0,
    "prediction_changed_tasks": 0,
}


def _read_aggregate_artifact(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.54.97 expected a JSON object")
    return value


def _validated_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    for relative, digest in FROZEN_INPUTS.items():
        if contract.sha256(ROOT / relative) != digest:
            raise RuntimeError("V2.54.97 frozen aggregate input hash drifted")
    forward = runner.validate_forward_result(
        _read_aggregate_artifact(contract.FORWARD_RESULT)
    )
    audit = _read_aggregate_artifact(contract.FORWARD_AUDIT)
    if (
        audit.get("role")
        != "v25496_visible_row_key_detail_external_forward_audit"
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
        raise RuntimeError("V2.54.97 frozen forward-audit barrier drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, _audit = _validated_inputs()
    aggregate = runner.validate_aggregate(forward["aggregate"])
    funnel = {name: aggregate[name] for name in EXPECTED_FUNNEL}
    unused_fetch_capacity = (
        aggregate["completed_runtime_tasks"]
        * contract.mechanism_gate()["maximum_physical_fetches_per_completed_task"]
        - aggregate["completed_physical_fetches"]
    )
    diagnosis = {
        "mechanism_gate_passed": forward["mechanism_decision"][
            "mechanism_gate_passed"
        ],
        "failed_checks": copy.deepcopy(
            forward["mechanism_decision"]["failed_checks"]
        ),
        "funnel_task_counts": funnel,
        "raw_page_visible_link_count_total": aggregate[
            "raw_page_visible_link_count_total"
        ],
        "joint_bound_link_count_total": aggregate["joint_bound_link_count_total"],
        "eligible_unique_link_count_total": aggregate[
            "eligible_unique_link_count_total"
        ],
        "detail_exact_nonredirected_page_count_total": aggregate[
            "detail_exact_nonredirected_page_count_total"
        ],
        "detail_identity_surface_bound_page_count_total": aggregate[
            "detail_identity_surface_bound_page_count_total"
        ],
        "detail_raw_field_surface_count_total": aggregate[
            "detail_raw_field_surface_count_total"
        ],
        "tasks_without_unique_detail_request": aggregate["task_count"]
        - aggregate["logical_detail_request_tasks"],
        "identity_bound_detail_pages_without_field_surface": aggregate[
            "identity_surface_bound_detail_page_tasks"
        ]
        - aggregate["field_surface_tasks"],
        "unused_fetch_capacity_under_existing_hard_cap_aggregate": unused_fetch_capacity,
        "runtime_failure_budget_or_capacity_is_not_the_observed_cause": (
            aggregate["completed_runtime_tasks"] == aggregate["task_count"]
            and aggregate["failure_as_zero_tasks"] == 0
            and aggregate["application_failure_tasks"] == 0
            and aggregate["budget_rejection_tasks"] == 0
            and aggregate["detail_capacity_shortfall_count_total"] == 0
        ),
        "reach_bottleneck": (
            "visible_links_exist_for_all_tasks_but_unique_row_key_detail_requests_exist_for_four_of_twenty"
        ),
        "parsing_bottleneck": (
            "four_exact_identity_bound_detail_pages_produce_zero_visible_field_surfaces"
        ),
        "two_stage_bottleneck_frozen": True,
        "successor_design_obligations": [
            "measure_exact220_visible_index_or_directory_exposure_question_only_before_bootstrap_design",
            "generalize_mechanical_field_grammar_to_exact_one_token_fused_and_bounded_adjacent_visible_labels",
            "apply_the_same_grammar_to_parent_pages_and_any_admitted_detail_page",
            "preserve_existing_query4_fetch14_model3_hard_caps_and_fail_closed_on_ambiguity",
            "require_a_new_task_disjoint_mechanism_gate_before_any_quality_or_exact220_forward",
        ],
    }
    checks = {
        "frozen_forward_result_and_audit_hash_exact": True,
        "forward_result_and_content_free_aggregate_validate": True,
        "forward_audit_valid_and_quality_not_authorized": True,
        "expected_funnel_exact": funnel == EXPECTED_FUNNEL,
        "all_tasks_terminal_without_runtime_application_budget_or_capacity_failure": diagnosis[
            "runtime_failure_budget_or_capacity_is_not_the_observed_cause"
        ],
        "reach_bottleneck_independently_observed": (
            aggregate["raw_page_visible_link_tasks"] == 20
            and aggregate["logical_detail_request_tasks"] == 4
            and diagnosis["tasks_without_unique_detail_request"] == 16
        ),
        "parsing_bottleneck_independently_observed": (
            aggregate["identity_surface_bound_detail_page_tasks"] == 4
            and aggregate["field_surface_tasks"] == 0
            and diagnosis["identity_bound_detail_pages_without_field_surface"] == 4
        ),
        "aggregate_unused_fetch_capacity_positive": unused_fetch_capacity == 76,
        "mechanism_no_go_and_truth_quality_unopened": forward[
            "mechanism_decision"
        ]["mechanism_gate_passed"]
        is False,
        "positive_signed_credit_zero": aggregate["positive_signed_credit_count"]
        == 0,
        "mapping_gold_truth_evaluator_score_reward_or_historical_correctness_absent": True,
        "task_rows_question_opaque_id_url_page_prediction_or_per_task_outcome_not_opened": True,
        "network_model_search_fetch_evaluator_or_benchmark_not_called": True,
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
            "exact220_question_only_visible_signal_transfer_audit": not findings,
            "generic_visible_schema_successor_build_design": not findings,
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
        or diagnosis.get("funnel_task_counts") != EXPECTED_FUNNEL
        or diagnosis.get("tasks_without_unique_detail_request") != 16
        or diagnosis.get("identity_bound_detail_pages_without_field_surface") != 4
        or diagnosis.get(
            "unused_fetch_capacity_under_existing_hard_cap_aggregate"
        )
        != 76
        or diagnosis.get("two_stage_bottleneck_frozen") is not True
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
            "exact220_question_only_visible_signal_transfer_audit": valid,
            "generic_visible_schema_successor_build_design": valid,
            "external_protocol_or_forward": False,
            "postfreeze_quality_or_truth": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.97 diagnosis drifted")
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
