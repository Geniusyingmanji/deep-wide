#!/usr/bin/env python3
"""Content-free diagnosis of V2.46.71's information-gain NO-GO.

The diagnosis reads only sealed forward artifacts and content-free task
receipts after all predictions are frozen.  It does not read visible-task
files, questions, queries, URLs, page text, predictions, mapping, gold,
provenance, category, split, score, reward, or evaluator surfaces, and it
performs no model, search, fetch, benchmark, or evaluator effect.
"""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24668_visible_surface_information_gain_runtime import (  # noqa: E402
    validate_result,
)
from deepwide_agent.v24671_ror_external_contract import (  # noqa: E402
    DATE,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    PROTOCOL_ID,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    sha256,
)
from deepwide_agent.v24671_runner_integration import validate_envelope  # noqa: E402


OUTPUT = Path(f"results/v24674_v24671_information_gain_no_go_diagnosis_v1_{DATE}.json")
COUNT_FIELDS = (
    "selected_unknown_target_count",
    "generic_fetch_targets",
    "generic_usable_page_count",
    "targeted_logical_query_count",
    "targeted_search_batch_count",
    "targeted_discovered_independent_source_count",
    "targeted_selected_independent_source_count",
    "targeted_fetch_targets",
    "targeted_usable_page_count",
    "visible_surface_selection_invocation_count",
    "visible_surface_input_lead_count",
    "visible_surface_eligible_source_count",
    "visible_surface_aligned_source_count",
    "visible_surface_selected_lead_count",
    "visible_surface_selected_aligned_lead_count",
    "visible_surface_source_representative_replacement_count",
    "visible_surface_title_aligned_source_count",
    "visible_surface_url_only_aligned_source_count",
    "logical_model_admission_count",
    "pre_provider_model_rejection_count",
    "proposed_cell_change_count",
    "forbidden_mutation_count",
    "support_closure_invocation_count",
    "support_closure_added_evidence_id_count",
    "support_closure_eligible_change_count",
    "counterfactual_parent_admitted_cell_change_count",
    "strict_closure_admitted_cell_change_count",
    "incremental_strict_closure_admitted_cell_change_count",
    "recoverable_failure_count",
)
FLOAT_FIELDS = (
    "visible_surface_prior_source_entropy_nats",
    "visible_surface_aligned_subset_entropy_nats",
    "visible_surface_localization_information_gain_nats",
    "epistemic_action_credit_nats",
)
HISTOGRAM_FIELDS = (
    "selected_unknown_target_count",
    "targeted_usable_page_count",
    "visible_surface_selected_aligned_lead_count",
    "proposed_cell_change_count",
    "support_closure_eligible_change_count",
)
EXPECTED_TOTALS = {
    "selected_unknown_target_count": 11,
    "generic_fetch_targets": 69,
    "generic_usable_page_count": 69,
    "targeted_logical_query_count": 11,
    "targeted_search_batch_count": 11,
    "targeted_discovered_independent_source_count": 281,
    "targeted_selected_independent_source_count": 44,
    "targeted_fetch_targets": 44,
    "targeted_usable_page_count": 33,
    "visible_surface_selection_invocation_count": 11,
    "visible_surface_input_lead_count": 495,
    "visible_surface_eligible_source_count": 281,
    "visible_surface_aligned_source_count": 82,
    "visible_surface_selected_lead_count": 44,
    "visible_surface_selected_aligned_lead_count": 35,
    "visible_surface_source_representative_replacement_count": 42,
    "visible_surface_title_aligned_source_count": 0,
    "visible_surface_url_only_aligned_source_count": 82,
    "logical_model_admission_count": 35,
    "pre_provider_model_rejection_count": 0,
    "proposed_cell_change_count": 0,
    "forbidden_mutation_count": 0,
    "support_closure_invocation_count": 11,
    "support_closure_added_evidence_id_count": 0,
    "support_closure_eligible_change_count": 0,
    "counterfactual_parent_admitted_cell_change_count": 0,
    "strict_closure_admitted_cell_change_count": 0,
    "incremental_strict_closure_admitted_cell_change_count": 0,
    "recoverable_failure_count": 0,
}
EXPECTED_FLOATS = {
    "visible_surface_prior_source_entropy_nats": 34.548666276885,
    "visible_surface_aligned_subset_entropy_nats": 17.65831209435,
    "visible_surface_localization_information_gain_nats": 16.890354182535,
    "epistemic_action_credit_nats": 16.890354182535,
}
EXPECTED_HISTOGRAMS = {
    "selected_unknown_target_count": {"0": 1, "1": 11},
    "targeted_usable_page_count": {"0": 1, "1": 1, "2": 2, "3": 4, "4": 4},
    "visible_surface_selected_aligned_lead_count": {
        "0": 1,
        "1": 2,
        "2": 1,
        "3": 1,
        "4": 7,
    },
    "proposed_cell_change_count": {"0": 12},
    "support_closure_eligible_change_count": {"0": 12},
}
EXPECTED_STAGE_HISTOGRAM = {
    "shared_plan|baseline_synthesis": 1,
    "shared_plan|baseline_synthesis|candidate_revision": 11,
}


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.74 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.74 expected object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward = read(ROOT / FORWARD_RESULT)
    audit = read(ROOT / FORWARD_AUDIT)
    if (
        forward.get("protocol_id") != PROTOCOL_ID
        or audit.get("protocol_id") != PROTOCOL_ID
        or not sealed(forward, "result_sha256")
        or not sealed(audit, "audit_sha256")
        or forward.get("terminal_arm_predictions") != 24
        or forward.get("all_predictions_terminal_before_gold_or_evaluator_open")
        is not True
        or forward.get("official_benchmark_evaluator_called") is not False
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("checks", {}).get("mechanism_triggered") is not False
        or audit.get("authorization", {}).get("mechanism_no_go_without_evaluator")
        is not True
        or audit.get("authorization", {}).get(
            "postfreeze_outer_utility_protocol_design"
        )
        is not False
    ):
        raise RuntimeError("V2.46.74 frozen parent drifted")

    totals: Counter[str] = Counter()
    float_totals: Counter[str] = Counter()
    histograms = {field: Counter() for field in HISTOGRAM_FIELDS}
    stages: Counter[str] = Counter()
    terminal = 0
    for index in range(1, SELECTED_COUNT + 1):
        envelope = validate_envelope(
            read(ROOT / TASK_ROOT / f"task_{index:04d}" / "result.json")
        )
        result = validate_result(envelope["result"])
        receipt = result["receipt"]
        if (
            envelope.get(
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            )
            is not False
            or envelope.get("benchmark_launch_or_evaluator_authorized") is not False
            or receipt.get(
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            )
            is not False
            or receipt.get("positive_decision_credit_assigned") is not False
            or receipt.get("postfreeze_outer_utility_observed") is not False
        ):
            raise RuntimeError("V2.46.74 privileged or decision-credit drifted")
        terminal += 1
        for field in COUNT_FIELDS:
            totals[field] += int(receipt[field])
        for field in FLOAT_FIELDS:
            float_totals[field] += float(receipt[field])
        for field in HISTOGRAM_FIELDS:
            histograms[field][int(receipt[field])] += 1
        stages["|".join(str(item) for item in receipt["provider_model_stage_vector"])] += 1

    aggregate = {field: totals[field] for field in COUNT_FIELDS}
    float_aggregate = {
        field: round(float_totals[field], 12) for field in FLOAT_FIELDS
    }
    histogram_aggregate = {
        field: {str(key): values[key] for key in sorted(values)}
        for field, values in histograms.items()
    }
    stage_histogram = {key: stages[key] for key in sorted(stages)}
    checks = audit["checks"]
    if (
        terminal != SELECTED_COUNT
        or aggregate != EXPECTED_TOTALS
        or float_aggregate != EXPECTED_FLOATS
        or histogram_aggregate != EXPECTED_HISTOGRAMS
        or stage_histogram != EXPECTED_STAGE_HISTOGRAM
        or checks.get("terminal_tasks") != SELECTED_COUNT
        or checks.get("terminal_arm_predictions") != 24
        or checks.get("model_slot_acquisitions") != 35
        or checks.get("model_slot_timeouts") != 0
        or any(checks.get(field) != aggregate[field] for field in (
            "selected_unknown_target_count",
            "generic_fetch_targets",
            "targeted_discovered_independent_source_count",
            "targeted_fetch_targets",
            "targeted_usable_page_count",
            "visible_surface_aligned_source_count",
            "visible_surface_selected_aligned_lead_count",
            "proposed_cell_change_count",
            "strict_closure_admitted_cell_change_count",
        ))
        or checks.get("epistemic_action_credit_nats")
        != float_aggregate["epistemic_action_credit_nats"]
    ):
        raise RuntimeError("V2.46.74 aggregate diagnosis drifted")

    value = {
        "artifact_version": 1,
        "role": "v24674_v24671_information_gain_no_go_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "entity_localization_information_gain_not_value_support_gain",
        "parents": {
            "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
            "forward_audit_sha256": sha256(ROOT / FORWARD_AUDIT),
        },
        "aggregate": aggregate,
        "information_aggregate": float_aggregate,
        "histograms": histogram_aggregate,
        "provider_model_stage_histogram": stage_histogram,
        "diagnosis": {
            "execution_transport_or_model_stage_failure_is_primary_bottleneck": False,
            "candidate_revision_executed_for_every_selected_target_task": True,
            "all_visible_surface_alignment_was_url_only": True,
            "any_title_aligned_source_observed": False,
            "entity_surface_localization_reduced_prefetch_source_set_entropy": True,
            "any_target_value_proposal_or_support_eligible_change_observed": False,
            "prefetch_entity_localization_gain_is_target_value_posterior_gain": False,
            "current_epistemic_action_credit_is_calibrated_to_value_support": False,
            "positive_task_or_decision_credit_supported": False,
            "subcause_between_page_value_absence_truncation_model_abstention_and_unchanged_revision_identified": False,
        },
        "credit_revision": {
            "url_or_title_entity_alignment_alone_earns_positive_credit": False,
            "discovery_volume_or_usable_page_count_alone_earns_positive_credit": False,
            "future_epistemic_credit_requires_addressable_target_value_belief_change": True,
            "future_decision_credit_requires_strict_safe_admission_and_postfreeze_outer_utility": True,
            "minimum_independent_local_exact_support_sources": 2,
            "support_threshold_relaxed": False,
        },
        "next_strategy": {
            "consume_another_ror_population_for_url_localization_replication": False,
            "reuse_completed_official_structured_lookup_as_positive_control": True,
            "measure_label_blind_visible_question_coverage_on_all_deepwidebench_tasks_before_new_dev64": True,
            "runtime_router_may_use_only_visible_question_and_schema_signatures": True,
            "benchmark_category_split_question_type_gold_mapping_score_or_evaluator_may_route_runtime": False,
            "new_dev64_or_exact220_authorized_by_this_diagnosis": False,
        },
        "source_policy": {
            "diagnosis_program_opened_only_forward_result_audit_and_content_free_task_result_envelopes": True,
            "visible_task_files_questions_queries_urls_page_text_or_prediction_text_opened_by_diagnosis_program": False,
            "mapping_gold_provenance_category_split_score_reward_or_evaluator_read": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "question_query_url_page_prediction_answer_value_or_credential_emitted": False,
        },
        "claim_scope": {
            "current_credit_proxy_falsified_as_value_support_information_gain": True,
            "page_level_failure_subcause_identified": False,
            "deepwidebench_quality_measured_by_v24671": False,
            "entropy_credit_assignment_validated": False,
            "sota_supported": False,
        },
        "authorization": {
            "label_blind_full_visible_question_coverage_audit": True,
            "new_runtime_implementation": False,
            "fresh_external_protocol_or_launch": False,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = payload_sha256(value)
    return value


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    diagnosis = copied.get("diagnosis", {})
    authorization = copied.get("authorization", {})
    if (
        copied.get("role")
        != "v24674_v24671_information_gain_no_go_diagnosis"
        or copied.get("status")
        != "entity_localization_information_gain_not_value_support_gain"
        or diagnosis.get(
            "prefetch_entity_localization_gain_is_target_value_posterior_gain"
        )
        is not False
        or diagnosis.get("positive_task_or_decision_credit_supported") is not False
        or authorization
        != {
            "label_blind_full_visible_question_coverage_audit": True,
            "new_runtime_implementation": False,
            "fresh_external_protocol_or_launch": False,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.74 diagnosis drifted")
    return copied


def publish_new(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    diagnosis = validate_diagnosis(build_diagnosis())
    publish_new(ROOT / OUTPUT, diagnosis)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "status": diagnosis["status"],
                "coverage_audit_authorized": diagnosis["authorization"][
                    "label_blind_full_visible_question_coverage_audit"
                ],
            },
            sort_keys=True,
        )
    )
