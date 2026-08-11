#!/usr/bin/env python3
"""Content-free funnel diagnosis for the frozen V2.51.15 NO-GO."""

from __future__ import annotations

import copy
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24257_score_first_runtime as score  # noqa: E402
from deepwide_agent import v25115_schema_recovered_external_recovery_contract as contract  # noqa: E402
from scripts import run_v25115_schema_recovered_external_recovery as runner  # noqa: E402


OUTPUT = Path("results/v25116_v25115_verified_field_funnel_diagnosis_v1_20260811.json")
EXPECTED_PARENTS = {
    "forward_result_sha256": "2775fbbd1a07664a5b6c58f6950881b76185fcc13f72babc4db075194201ce3f",
    "forward_audit_sha256": "22f60a2c4694b9f42b7eea3cd3c1ad3dbb54fbaab9d028d2418e87b94b1b7f09",
    "task_rows_sha256": "20db022532aefe55d5eaf1d4b7fbfc080100345707e08308ca9f88277f1173d8",
}
UNKNOWN = frozenset({"", "unknown", "未知", "n/a", "na"})


def _read_json(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.16 expected JSON object")
    return value


def _read_rows() -> list[dict[str, Any]]:
    return [
        runner.validate_task_row(row)
        for row in runner._read_jsonl(contract.TASK_ROWS, tracked=True)
    ]


def _histogram(values: Sequence[object]) -> dict[str, int]:
    return dict(sorted(Counter("None" if value is None else str(value) for value in values).items()))


def _table(prediction: str) -> tuple[list[str], list[list[str]]] | None:
    canonical, _errors = score.extract_valid_markdown_table(prediction, contract.COLUMNS)
    if canonical is None:
        return None
    lines = [line.strip() for line in canonical.splitlines() if line.strip().startswith("|")]
    rows = [score._split_table_row(line) for line in lines]
    if len(rows) < 3 or any(len(row) != len(contract.COLUMNS) for row in rows):
        return None
    return rows[0], rows[2:]


def _prediction_diff_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts = {
        "changed_tasks": 0,
        "both_tables_valid_tasks": 0,
        "same_table_shape_tasks": 0,
        "row_count_changed_tasks": 0,
        "cell_changes": 0,
        "identity_cell_changes": 0,
        "target_cell_changes": 0,
        "unknown_to_fact_changes": 0,
        "fact_to_unknown_changes": 0,
        "fact_to_different_fact_changes": 0,
    }
    for row in rows:
        if not row["prediction_changed"]:
            continue
        counts["changed_tasks"] += 1
        control = _table(str(row["predictions"][contract.CONTROL_ARM]))
        candidate = _table(str(row["predictions"][contract.CANDIDATE_ARM]))
        if control is None or candidate is None:
            continue
        counts["both_tables_valid_tasks"] += 1
        control_header, control_rows = control
        candidate_header, candidate_rows = candidate
        same_shape = (
            len(control_header) == len(candidate_header)
            and len(control_rows) == len(candidate_rows)
            and all(
                len(control_row) == len(candidate_row) == len(control_header)
                for control_row, candidate_row in zip(
                    control_rows, candidate_rows, strict=True
                )
            )
        )
        counts["same_table_shape_tasks"] += int(same_shape)
        counts["row_count_changed_tasks"] += int(
            len(control_rows) != len(candidate_rows)
        )
        if not same_shape:
            continue
        for control_row, candidate_row in zip(
            control_rows, candidate_rows, strict=True
        ):
            for index, (before, after) in enumerate(
                zip(control_row, candidate_row, strict=True)
            ):
                if before == after:
                    continue
                counts["cell_changes"] += 1
                counts[
                    "identity_cell_changes" if index == 0 else "target_cell_changes"
                ] += 1
                before_unknown = before.strip().casefold() in UNKNOWN
                after_unknown = after.strip().casefold() in UNKNOWN
                if before_unknown and not after_unknown:
                    counts["unknown_to_fact_changes"] += 1
                elif not before_unknown and after_unknown:
                    counts["fact_to_unknown_changes"] += 1
                else:
                    counts["fact_to_different_fact_changes"] += 1
    return counts


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    parents = {
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
        "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
    }
    if parents != EXPECTED_PARENTS:
        raise RuntimeError("V2.51.16 frozen parent hash drifted")
    forward = runner.validate_forward_result(_read_json(contract.FORWARD_RESULT))
    audit = _read_json(contract.FORWARD_AUDIT)
    rows = _read_rows()
    if (
        audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_implementation_and_protocol"
        )
        is not False
        or forward["mechanism_decision"]["mechanism_gate_passed"] is not False
        or len(rows) != contract.TASK_COUNT
    ):
        raise RuntimeError("V2.51.16 parent barrier drifted")

    completed = [row for row in rows if row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    stages = [row["stage_failure_accounting"] for row in completed]
    bindings = [receipt["record_binding_receipt"] for receipt in receipts]
    parents_receipts = [binding["parent_value_shape_receipt"] for binding in bindings]
    selections = [parent["authority_selection_receipt"] for parent in parents_receipts]
    enforcement = [
        receipt["verified_field_enforcement_receipt"]
        for receipt in receipts
        if receipt["verified_field_enforcement_receipt"] is not None
    ]
    prediction = _prediction_diff_counts(completed)
    stage_failure_total = sum(
        int(stage[name])
        for stage in stages
        for name in (
            "plan_model_effect_failed",
            "plan_transport_failed",
            "plan_output_validation_failed",
            "proposal_model_effect_failed",
            "proposal_transport_failed",
            "representation_validation_failed",
        )
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25116_v25115_verified_field_funnel_content_free_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": parents,
        "frozen_parent": {
            "task_count": len(rows),
            "audit_valid": True,
            "mechanism_gate_passed": False,
            "failed_checks": list(forward["mechanism_decision"]["failed_checks"]),
            "evaluator_implemented_or_called": False,
            "stage_failure_total": stage_failure_total,
            "model_provider_requests": forward["aggregate"]["model_provider_requests"],
            "model_provider_attempts": forward["aggregate"]["model_provider_attempts"],
        },
        "content_free_funnel": {
            "runtime_completed_tasks": len(completed),
            "both_arms_model_success_tasks": sum(
                all(row["model_success"].values()) for row in completed
            ),
            "usable_page_tasks": sum(
                receipt["usable_page_count"] > 0 for receipt in receipts
            ),
            "selected_page_tasks": sum(
                selection["selected_page_count"] == 1 for selection in selections
            ),
            "complete_proposal_tasks": sum(
                binding["complete_column_proposal_strictly_valid"]
                for binding in bindings
            ),
            "requested_non_key_column_dispositions": sum(
                binding["requested_non_key_column_count"] for binding in bindings
            ),
            "submitted_column_dispositions": sum(
                binding["submitted_column_disposition_count"] for binding in bindings
            ),
            "found_column_dispositions": sum(
                binding["found_column_disposition_count"] for binding in bindings
            ),
            "unavailable_column_dispositions": sum(
                binding["unavailable_column_disposition_count"] for binding in bindings
            ),
            "parent_parsed_fields": sum(
                binding["parent_parsed_field_count"] for binding in bindings
            ),
            "parent_accepted_fields": sum(
                binding["parent_accepted_field_count"] for binding in bindings
            ),
            "field_lexical_accepted_count": sum(
                parent["field_lexical_accepted_count"] for parent in parents_receipts
            ),
            "field_value_shape_accepted_count": sum(
                parent["field_value_shape_accepted_count"]
                for parent in parents_receipts
            ),
            "field_value_shape_rejection_count": sum(
                parent["field_value_shape_rejection_count"]
                for parent in parents_receipts
            ),
            "field_coordinate_rejection_count": sum(
                parent["field_coordinate_rejection_count"]
                for parent in parents_receipts
            ),
            "field_identity_page_rejection_count": sum(
                parent["field_identity_page_rejection_count"]
                for parent in parents_receipts
            ),
            "field_conflict_rejection_count": sum(
                parent["field_conflict_rejection_count"]
                for parent in parents_receipts
            ),
            "verifier_exposure_tasks": sum(
                row["candidate_evidence_changed"] for row in completed
            ),
            "enforcement_receipt_tasks": len(enforcement),
            "enforcement_verified_fields": sum(
                receipt["verified_field_count"] for receipt in enforcement
            ),
            "enforcement_applied_fields": sum(
                receipt["applied_field_count"] for receipt in enforcement
            ),
            "enforcement_changed_cells": sum(
                receipt["changed_cell_count"] for receipt in enforcement
            ),
            "enforcement_output_changed_tasks": sum(
                receipt["output_changed"] for receipt in enforcement
            ),
            "prediction_changed_tasks": sum(
                row["prediction_changed"] for row in completed
            ),
            "exposed_and_prediction_changed_tasks": sum(
                row["candidate_evidence_changed"] and row["prediction_changed"]
                for row in completed
            ),
            "unexposed_and_prediction_changed_tasks": sum(
                not row["candidate_evidence_changed"] and row["prediction_changed"]
                for row in completed
            ),
            "found_disposition_histogram": _histogram(
                [binding["found_column_disposition_count"] for binding in bindings]
            ),
            "accepted_field_histogram": _histogram(
                [binding["parent_accepted_field_count"] for binding in bindings]
            ),
        },
        "prediction_structure": prediction,
        "diagnosis": {
            "parser_transport_and_representation_failures_are_resolved_in_this_population": True,
            "proposal_shape_is_total_but_target_field_discovery_is_sparse": True,
            "forty_three_of_fifty_four_submitted_dispositions_are_unavailable": True,
            "ten_of_eleven_found_fields_pass_unchanged_value_shape_verifier": True,
            "verification_rejection_is_not_the_primary_bottleneck": True,
            "all_ten_verified_fields_already_match_candidate_synthesis_cells": True,
            "deterministic_enforcement_directly_changed_no_cell": True,
            "two_prediction_changes_are_representation_induced_not_enforcement_induced": True,
            "two_changed_tasks_are_abstention_only": True,
            "unknown_to_fact_or_fact_correction_change_observed": False,
            "next_candidate_should_improve_target_field_source_acquisition_not_strengthen_enforcement": True,
            "next_candidate_must_use_fresh_population_and_matched_cost": True,
            "entropy_or_information_gain_signed_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "prediction_text_parsed_in_memory_after_freeze_for_structure_direction_counts_only": True,
            "question_query_url_title_page_quote_identity_field_value_prediction_answer_or_task_id_persisted_or_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "v25115_evaluator_retry_resume_or_selective_revaluation": False,
            "append_only_fresh_field_acquisition_successor_design": True,
            "new_external_forward": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    parent = copied.get("frozen_parent") or {}
    funnel = copied.get("content_free_funnel") or {}
    prediction = copied.get("prediction_structure") or {}
    diagnosis = copied.get("diagnosis") or {}
    authorization = copied.get("authorization") or {}
    required_true = (
        "parser_transport_and_representation_failures_are_resolved_in_this_population",
        "proposal_shape_is_total_but_target_field_discovery_is_sparse",
        "forty_three_of_fifty_four_submitted_dispositions_are_unavailable",
        "ten_of_eleven_found_fields_pass_unchanged_value_shape_verifier",
        "verification_rejection_is_not_the_primary_bottleneck",
        "all_ten_verified_fields_already_match_candidate_synthesis_cells",
        "deterministic_enforcement_directly_changed_no_cell",
        "two_prediction_changes_are_representation_induced_not_enforcement_induced",
        "two_changed_tasks_are_abstention_only",
        "next_candidate_should_improve_target_field_source_acquisition_not_strengthen_enforcement",
        "next_candidate_must_use_fresh_population_and_matched_cost",
    )
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25116_v25115_verified_field_funnel_content_free_diagnosis"
        or copied.get("parents") != EXPECTED_PARENTS
        or seal != contract.payload_sha256(unsigned)
        or parent.get("task_count") != 20
        or parent.get("audit_valid") is not True
        or parent.get("mechanism_gate_passed") is not False
        or parent.get("failed_checks")
        != ["minimum_attributable_prediction_change", "minimum_prediction_change"]
        or parent.get("evaluator_implemented_or_called") is not False
        or parent.get("stage_failure_total") != 0
        or parent.get("model_provider_requests") != 80
        or parent.get("model_provider_attempts") != 80
        or funnel.get("runtime_completed_tasks") != 20
        or funnel.get("both_arms_model_success_tasks") != 20
        or funnel.get("usable_page_tasks") != 20
        or funnel.get("selected_page_tasks") != 18
        or funnel.get("complete_proposal_tasks") != 20
        or funnel.get("requested_non_key_column_dispositions") != 60
        or funnel.get("submitted_column_dispositions") != 54
        or funnel.get("found_column_dispositions") != 11
        or funnel.get("unavailable_column_dispositions") != 43
        or funnel.get("parent_parsed_fields") != 11
        or funnel.get("parent_accepted_fields") != 10
        or funnel.get("field_lexical_accepted_count") != 0
        or funnel.get("field_value_shape_accepted_count") != 10
        or funnel.get("field_value_shape_rejection_count") != 1
        or funnel.get("field_coordinate_rejection_count") != 0
        or funnel.get("field_identity_page_rejection_count") != 0
        or funnel.get("field_conflict_rejection_count") != 0
        or funnel.get("verifier_exposure_tasks") != 10
        or funnel.get("enforcement_receipt_tasks") != 10
        or funnel.get("enforcement_verified_fields") != 10
        or funnel.get("enforcement_applied_fields") != 10
        or funnel.get("enforcement_changed_cells") != 0
        or funnel.get("enforcement_output_changed_tasks") != 0
        or funnel.get("prediction_changed_tasks") != 2
        or funnel.get("exposed_and_prediction_changed_tasks") != 2
        or funnel.get("unexposed_and_prediction_changed_tasks") != 0
        or prediction.get("changed_tasks") != 2
        or prediction.get("both_tables_valid_tasks") != 2
        or prediction.get("same_table_shape_tasks") != 2
        or prediction.get("row_count_changed_tasks") != 0
        or prediction.get("cell_changes") != 3
        or prediction.get("identity_cell_changes") != 0
        or prediction.get("target_cell_changes") != 3
        or prediction.get("unknown_to_fact_changes") != 0
        or prediction.get("fact_to_unknown_changes") != 3
        or prediction.get("fact_to_different_fact_changes") != 0
        or any(diagnosis.get(name) is not True for name in required_true)
        or diagnosis.get("unknown_to_fact_or_fact_correction_change_observed") is not False
        or diagnosis.get("entropy_or_information_gain_signed_credit_validated") is not False
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or authorization.get("append_only_fresh_field_acquisition_successor_design")
        is not True
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "append_only_fresh_field_acquisition_successor_design"
        )
        or copied.get("content_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
        or copied.get("content_policy", {}).get(
            "credential_value_read_persisted_hashed_or_emitted"
        )
        is not False
    ):
        raise RuntimeError("V2.51.16 diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    payload = (json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "role": value["role"]}, sort_keys=True))


if __name__ == "__main__":
    main()
