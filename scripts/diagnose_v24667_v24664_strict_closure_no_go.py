#!/usr/bin/env python3
"""Post-freeze, label-blind diagnosis of V2.46.64's strict-closure NO-GO.

The diagnosis aggregates only sealed forward artifacts and content-free receipt
fields.  It does not open visible-task files, mapping, gold, provenance,
category, split, score, or evaluator surfaces, and performs no model, search,
fetch, benchmark, or evaluator effect.
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

from deepwide_agent.v24661_support_closure_task_runtime import (  # noqa: E402
    validate_result,
)
from deepwide_agent.v24664_ror_external_contract import (  # noqa: E402
    DATE,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    PROTOCOL_ID,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    sha256,
)
from deepwide_agent.v24664_runner_integration import validate_envelope  # noqa: E402


OUTPUT = Path(f"results/v24667_v24664_strict_closure_no_go_diagnosis_v1_{DATE}.json")
AGGREGATE_FIELDS = (
    "selected_unknown_target_count",
    "generic_fetch_targets",
    "generic_usable_page_count",
    "targeted_logical_query_count",
    "targeted_search_batch_count",
    "targeted_discovered_independent_source_count",
    "targeted_selected_independent_source_count",
    "targeted_fetch_targets",
    "targeted_usable_page_count",
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
EXPECTED_AGGREGATE = {
    "selected_unknown_target_count": 18,
    "generic_fetch_targets": 68,
    "generic_usable_page_count": 68,
    "targeted_logical_query_count": 18,
    "targeted_search_batch_count": 18,
    "targeted_discovered_independent_source_count": 399,
    "targeted_selected_independent_source_count": 40,
    "targeted_fetch_targets": 40,
    "targeted_usable_page_count": 38,
    "proposed_cell_change_count": 3,
    "forbidden_mutation_count": 0,
    "support_closure_invocation_count": 10,
    "support_closure_added_evidence_id_count": 0,
    "support_closure_eligible_change_count": 0,
    "counterfactual_parent_admitted_cell_change_count": 0,
    "strict_closure_admitted_cell_change_count": 0,
    "incremental_strict_closure_admitted_cell_change_count": 0,
    "recoverable_failure_count": 0,
}
EXPECTED_SUPPORT_TAXONOMY = {
    "proposal_count": 3,
    "all_declared_ids_resolved_count": 3,
    "registrably_independent_declared_set_count": 3,
    "every_declared_source_locally_supports_count": 1,
    "deterministic_support_gate_pass_count": 0,
    "declared_evidence_id_count_histogram": {"1": 2, "2": 1},
    "local_exact_support_source_count_histogram": {"0": 1, "1": 2},
    "proposal_with_two_or_more_declared_sources_count": 1,
    "proposal_with_two_or_more_local_exact_support_sources_count": 0,
}


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.67 diagnosis expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.67 diagnosis expected object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def _support_taxonomy(admissions: list[Mapping[str, Any]]) -> dict[str, Any]:
    declared: Counter[int] = Counter()
    local: Counter[int] = Counter()
    output = {
        "proposal_count": len(admissions),
        "all_declared_ids_resolved_count": 0,
        "registrably_independent_declared_set_count": 0,
        "every_declared_source_locally_supports_count": 0,
        "deterministic_support_gate_pass_count": 0,
        "proposal_with_two_or_more_declared_sources_count": 0,
        "proposal_with_two_or_more_local_exact_support_sources_count": 0,
    }
    for item in admissions:
        support = item.get("support_receipt")
        if not isinstance(support, Mapping):
            raise RuntimeError("V2.46.67 support receipt absent")
        declared_count = int(support["declared_evidence_id_count"])
        local_count = int(support["local_exact_row_value_support_source_count"])
        declared[declared_count] += 1
        local[local_count] += 1
        output["all_declared_ids_resolved_count"] += int(
            support["all_declared_evidence_ids_resolved"] is True
        )
        output["registrably_independent_declared_set_count"] += int(
            support["cited_sources_are_registrably_independent"] is True
        )
        output["every_declared_source_locally_supports_count"] += int(
            support["every_cited_source_has_local_exact_row_value_support"] is True
        )
        output["deterministic_support_gate_pass_count"] += int(
            support["deterministic_support_gate_passed"] is True
        )
        output["proposal_with_two_or_more_declared_sources_count"] += int(
            declared_count >= 2
        )
        output["proposal_with_two_or_more_local_exact_support_sources_count"] += int(
            local_count >= 2
        )
    output["declared_evidence_id_count_histogram"] = {
        str(key): declared[key] for key in sorted(declared)
    }
    output["local_exact_support_source_count_histogram"] = {
        str(key): local[key] for key in sorted(local)
    }
    return output


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
            "postfreeze_external_evaluator_protocol_design"
        )
        is not False
    ):
        raise RuntimeError("V2.46.67 frozen parent drifted")

    totals: Counter[str] = Counter()
    admissions: list[Mapping[str, Any]] = []
    terminal = 0
    for index in range(1, SELECTED_COUNT + 1):
        envelope = validate_envelope(
            read(ROOT / TASK_ROOT / f"task_{index:04d}" / "result.json")
        )
        result = validate_result(envelope["result"])
        receipt = result["receipt"]
        if (
            envelope.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read")
            is not False
            or envelope.get("benchmark_launch_or_evaluator_authorized") is not False
            or receipt.get(
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            )
            is not False
            or receipt.get("entropy_or_task_credit_used_by_closure") is not False
        ):
            raise RuntimeError("V2.46.67 privileged or entropy effect drifted")
        terminal += 1
        for field in AGGREGATE_FIELDS:
            totals[field] += int(receipt[field])
        raw_admissions = receipt.get("cell_admissions")
        if not isinstance(raw_admissions, list):
            raise RuntimeError("V2.46.67 cell admissions drifted")
        admissions.extend(
            item for item in raw_admissions if isinstance(item, Mapping)
        )

    aggregate = {field: totals[field] for field in AGGREGATE_FIELDS}
    taxonomy = _support_taxonomy(admissions)
    audit_checks = audit["checks"]
    audited_fields = (
        "selected_unknown_target_count",
        "generic_fetch_targets",
        "targeted_fetch_targets",
        "targeted_usable_page_count",
        "proposed_cell_change_count",
        "support_closure_invocation_count",
        "support_closure_added_evidence_id_count",
        "support_closure_eligible_change_count",
        "counterfactual_parent_admitted_cell_change_count",
        "strict_closure_admitted_cell_change_count",
        "incremental_strict_closure_admitted_cell_change_count",
    )
    if (
        terminal != SELECTED_COUNT
        or aggregate != EXPECTED_AGGREGATE
        or taxonomy != EXPECTED_SUPPORT_TAXONOMY
        or any(audit_checks.get(field) != aggregate[field] for field in audited_fields)
        or audit_checks.get("terminal_tasks") != SELECTED_COUNT
        or audit_checks.get("terminal_arm_predictions") != 24
        or audit_checks.get("model_slot_acquisitions") != 34
        or audit_checks.get("model_slot_timeouts") != 0
    ):
        raise RuntimeError("V2.46.67 aggregate diagnosis drifted")

    value = {
        "artifact_version": 1,
        "role": "v24667_v24664_strict_closure_no_go_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "citation_omission_hypothesis_falsified_on_frozen_population",
        "parents": {
            "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
            "forward_audit_sha256": sha256(ROOT / FORWARD_AUDIT),
        },
        "aggregate": aggregate,
        "support_failure_taxonomy": taxonomy,
        "diagnosis": {
            "transport_or_fetch_failure_is_primary_bottleneck": False,
            "discovery_source_volume_is_primary_bottleneck": False,
            "model_citation_omission_is_supported_as_current_primary_bottleneck": False,
            "closure_found_any_unwritten_exact_local_support_page": False,
            "any_proposal_had_two_independent_local_exact_support_sources": False,
            "current_bottleneck_is_failure_to_acquire_same_value_two_source_exact_support": True,
            "page_selection_value_format_alias_or_page_truncation_subcause_identified": False,
            "v24661_strict_fail_closed_gate_remains_valid": True,
        },
        "entropy_and_credit": {
            "entropy_or_task_credit_affected_v24664_forward": False,
            "positive_decision_credit_supported_by_v24664": False,
            "raw_discovery_volume_earns_positive_credit": False,
            "usable_page_count_without_same_value_support_earns_positive_credit": False,
            "future_epistemic_credit_requires_measured_support_uncertainty_reduction": True,
            "future_decision_credit_requires_safe_admission_and_postfreeze_outer_utility": True,
        },
        "next_falsification": {
            "treatment": "visible_row_aligned_single_target_fetch_concentration_before_unchanged_strict_support_gate",
            "one_unknown_target_per_task": True,
            "targeted_fetch_budget_concentrated_on_one_target": 4,
            "visible_title_and_url_alignment_is_retrieval_hint_only": True,
            "fetched_page_text_remains_only_active_evidence": True,
            "minimum_independent_local_exact_support_sources": 2,
            "proposal_value_or_support_threshold_changed": False,
            "same_total_model_query_fetch_caps": [3, 4, 10],
            "entropy_information_gain_recorded_at_action_level_before_any_credit": True,
            "positive_decision_credit_before_safe_change_and_outer_utility": False,
            "fresh_nonoverlapping_external_population_required": True,
            "same_population_resume_retry_or_selective_rerun": False,
            "mechanism_gate": "at_least_one_incremental_strictly_admitted_cell_change",
            "evaluator_before_mechanism_gate": False,
        },
        "source_policy": {
            "task_result_envelopes_opened_only_after_prediction_freeze": True,
            "only_content_free_receipt_fields_aggregated": True,
            "visible_task_question_file_opened": False,
            "prediction_text_used_for_diagnosis": False,
            "mapping_gold_provenance_category_split_score_or_evaluator_read": False,
            "network_model_search_fetch_benchmark_or_evaluator_called": False,
            "question_query_url_page_prediction_answer_value_or_credential_emitted": False,
        },
        "claim_scope": {
            "mechanism_failure_localized": True,
            "subcause_among_selection_format_alias_or_truncation_identified": False,
            "deepwidebench_quality_measured_by_v24664": False,
            "entropy_or_credit_assignment_validated": False,
            "sota_supported": False,
        },
        "authorization": {
            "visible_lead_alignment_successor_implementation": True,
            "fresh_external_protocol_design": False,
            "fresh_external_activation_or_launch": False,
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
        != "v24667_v24664_strict_closure_no_go_diagnosis"
        or copied.get("status")
        != "citation_omission_hypothesis_falsified_on_frozen_population"
        or diagnosis.get(
            "current_bottleneck_is_failure_to_acquire_same_value_two_source_exact_support"
        )
        is not True
        or diagnosis.get(
            "model_citation_omission_is_supported_as_current_primary_bottleneck"
        )
        is not False
        or authorization
        != {
            "visible_lead_alignment_successor_implementation": True,
            "fresh_external_protocol_design": False,
            "fresh_external_activation_or_launch": False,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
            "leaderboard_or_sota": False,
        }
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.46.67 diagnosis drifted")
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
                "successor_implementation_authorized": diagnosis["authorization"][
                    "visible_lead_alignment_successor_implementation"
                ],
            },
            sort_keys=True,
        )
    )
