#!/usr/bin/env python3
"""Content-free value-shape proposal and attribution diagnosis for V2.50.98."""

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

from deepwide_agent import v25098_value_shape_external_contract as contract  # noqa: E402
from scripts import run_v25098_value_shape_external as runner  # noqa: E402


OUTPUT = Path("results/v25099_v25098_value_shape_external_diagnosis_v1_20260811.json")


def _read_json(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.99 expected JSON object")
    return value


def _read_rows() -> list[dict[str, Any]]:
    return [runner.validate_task_row(row) for row in runner._read_jsonl(contract.TASK_ROWS, tracked=True)]


def _hist(values: Sequence[object]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _sum(values: Sequence[Mapping[str, Any]], name: str) -> int:
    return sum(int(value[name]) for value in values)


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
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
        or forward.get("mechanism_decision", {}).get("mechanism_gate_passed") is not False
        or len(rows) != contract.TASK_COUNT
    ):
        raise RuntimeError("V2.50.99 parent barrier drifted")

    completed = [row for row in rows if row["runtime_completed"]]
    failures = [row for row in rows if not row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    bindings = [receipt["record_binding_receipt"] for receipt in receipts if receipt["record_binding_receipt"] is not None]
    selections = [binding["authority_selection_receipt"] for binding in bindings]
    terminal_names = tuple(
        name for name in rows[0]["effect_health"] if name != "query_local_mapping_failure_rows"
    )
    terminal_hard = sum(
        int(row["effect_health"][name]) for row in rows for name in terminal_names
    )
    mapping_failures = sum(
        int(row["effect_health"]["query_local_mapping_failure_rows"]) for row in rows
    )
    selected_tasks = sum(selection["selected_page_count"] == 1 for selection in selections)
    parsed_fields = _sum(bindings, "parsed_field_count")
    accepted_fields = _sum(bindings, "field_accepted_count")
    lexical_fields = _sum(bindings, "field_lexical_accepted_count")
    shape_fields = _sum(bindings, "field_value_shape_accepted_count")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25099_v25098_value_shape_external_content_free_funnel_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        },
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_funnel": {
            "runtime_completed_histogram": _hist([row["runtime_completed"] for row in rows]),
            "failure_as_zero_histogram": _hist([row["failure_as_zero"] for row in rows]),
            "outer_failure_type_histogram": _hist([row["outer_failure_type"] for row in failures]),
            "terminal_hard_failure_total": terminal_hard,
            "query_local_mapping_failure_rows": mapping_failures,
            "representation_validation_failure_tasks": sum(
                receipt["representation_validation_failed"] for receipt in receipts
            ),
            "strict_identity_page_tasks": sum(
                selection["strict_identity_page_count"] > 0 for selection in selections
            ),
            "selected_page_tasks": selected_tasks,
            "unique_identity_page_selected_tasks": sum(
                selection["unique_identity_page_selected"] for selection in selections
            ),
            "authority_tiebreak_eligible_tasks": sum(
                selection["authority_tiebreak_eligible"] for selection in selections
            ),
            "authority_tiebreak_selected_tasks": sum(
                selection["authority_tiebreak_selected"] for selection in selections
            ),
            "proposal_empty_tasks": sum(binding["parsed_record_count"] == 0 for binding in bindings),
            "proposal_nonempty_tasks": sum(binding["parsed_record_count"] > 0 for binding in bindings),
            "parsed_records": _sum(bindings, "parsed_record_count"),
            "parsed_fields": parsed_fields,
            "field_accepted_count": accepted_fields,
            "field_lexical_accepted_count": lexical_fields,
            "field_value_shape_accepted_count": shape_fields,
            "field_target_column_rejections": _sum(bindings, "field_target_column_rejection_count"),
            "field_source_label_conflict_rejections": _sum(
                bindings, "field_source_label_conflict_rejection_count"
            ),
            "field_value_shape_rejections": _sum(bindings, "field_value_shape_rejection_count"),
            "field_coordinate_rejections": _sum(bindings, "field_coordinate_rejection_count"),
            "verified_partial_records": _sum(bindings, "verified_partial_record_count"),
            "rendered_fields": _sum(bindings, "rendered_field_count"),
            "verifier_exposure_tasks": sum(row["candidate_evidence_changed"] for row in completed),
            "prediction_changed_tasks": sum(row["prediction_changed"] for row in completed),
            "exposed_and_prediction_changed_tasks": sum(
                row["candidate_evidence_changed"] and row["prediction_changed"] for row in completed
            ),
            "unexposed_and_prediction_changed_tasks": sum(
                not row["candidate_evidence_changed"] and row["prediction_changed"] for row in completed
            ),
            "prediction_identity_handoff_tasks": sum(
                receipt["prediction_identity_handoff_applied"] for receipt in receipts
            ),
        },
        "diagnosis": {
            "mechanism_gate_passed": False,
            "evaluator_and_quality_conclusion_remain_forbidden": True,
            "nineteen_completed_one_failure_as_zero": len(completed) == 19 and len(failures) == 1,
            "outer_value_error_has_no_transport_model_or_timeout_receipt": (
                len(failures) == 1
                and failures[0]["outer_failure_type"] == "ValueError"
                and terminal_hard == 0
            ),
            "outer_value_error_is_outside_the_contained_representation_stage": (
                sum(receipt["representation_validation_failed"] for receipt in receipts) == 0
            ),
            "outer_value_error_stage_is_not_attributable_from_frozen_content_free_row": True,
            "value_shape_created_all_seven_accepted_fields": (
                accepted_fields == 7 and lexical_fields == 0 and shape_fields == 7
            ),
            "value_shape_increased_exposure_to_seven_tasks": (
                forward["aggregate"]["verifier_exposure_tasks"] == 7
            ),
            "two_exposures_created_two_attributable_prediction_changes": (
                forward["aggregate"]["exposed_and_prediction_changed_tasks"] == 2
            ),
            "unexposed_prediction_noise_remains_zero": (
                forward["aggregate"]["unexposed_and_prediction_changed_tasks"] == 0
            ),
            "proposal_reach_is_current_bottleneck_after_fourteen_selected_pages": (
                selected_tasks == 14
                and sum(binding["parsed_record_count"] > 0 for binding in bindings) == 8
            ),
            "ten_parsed_fields_have_complete_dispositions": parsed_fields == 10,
            "remaining_field_rejections_are_one_shape_and_two_coordinate": (
                _sum(bindings, "field_value_shape_rejection_count") == 1
                and _sum(bindings, "field_coordinate_rejection_count") == 2
            ),
            "next_candidate_must_not_retry_resume_or_reuse_v25098_population": True,
            "next_build_only_candidate_should_prompt_each_non_key_column_independently": True,
            "next_build_only_candidate_should_request_all_visible_fields_without_atomic_omission": True,
            "next_runtime_should_contain_post_synthesis_accounting_and_receipt_validation_errors": True,
            "value_shape_authority_coordinate_conflict_and_attribution_checks_must_remain_strict": True,
            "query_fetch_model_context_token_wall_or_network_byte_caps_must_not_expand": True,
            "entropy_or_information_gain_signed_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "question_query_url_title_page_quote_identity_field_value_prediction_answer_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "only_content_free_receipt_counts_failure_types_and_parent_hashes_aggregated": True,
        },
        "authorization": {
            "v25098_evaluator_or_quality_result": False,
            "v25098_retry_resume_skip_or_selective_rerun": False,
            "new_disjoint_build_only_successor_design": True,
            "new_external_launch": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    funnel = copied.get("content_free_funnel") or {}
    diagnosis = copied.get("diagnosis") or {}
    authorization = copied.get("authorization") or {}
    required_true = (
        "nineteen_completed_one_failure_as_zero",
        "outer_value_error_has_no_transport_model_or_timeout_receipt",
        "outer_value_error_is_outside_the_contained_representation_stage",
        "outer_value_error_stage_is_not_attributable_from_frozen_content_free_row",
        "value_shape_created_all_seven_accepted_fields",
        "value_shape_increased_exposure_to_seven_tasks",
        "two_exposures_created_two_attributable_prediction_changes",
        "unexposed_prediction_noise_remains_zero",
        "proposal_reach_is_current_bottleneck_after_fourteen_selected_pages",
        "ten_parsed_fields_have_complete_dispositions",
        "remaining_field_rejections_are_one_shape_and_two_coordinate",
        "next_build_only_candidate_should_prompt_each_non_key_column_independently",
        "next_build_only_candidate_should_request_all_visible_fields_without_atomic_omission",
        "next_runtime_should_contain_post_synthesis_accounting_and_receipt_validation_errors",
    )
    if (
        copied.get("role") != "v25099_v25098_value_shape_external_content_free_funnel_diagnosis"
        or seal != contract.payload_sha256(unsigned)
        or diagnosis.get("mechanism_gate_passed") is not False
        or diagnosis.get("evaluator_and_quality_conclusion_remain_forbidden") is not True
        or any(diagnosis.get(name) is not True for name in required_true)
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or funnel.get("selected_page_tasks") != 14
        or funnel.get("proposal_nonempty_tasks") != 8
        or funnel.get("parsed_fields") != 10
        or funnel.get("field_accepted_count") != 7
        or funnel.get("field_value_shape_accepted_count") != 7
        or funnel.get("verifier_exposure_tasks") != 7
        or funnel.get("exposed_and_prediction_changed_tasks") != 2
        or funnel.get("unexposed_and_prediction_changed_tasks") != 0
        or funnel.get("representation_validation_failure_tasks") != 0
        or authorization.get("new_disjoint_build_only_successor_design") is not True
        or any(
            authorization.get(name) is not False
            for name in authorization
            if name != "new_disjoint_build_only_successor_design"
        )
        or copied.get("content_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        )
        is not False
    ):
        raise RuntimeError("V2.50.99 diagnosis drifted")
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
