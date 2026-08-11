#!/usr/bin/env python3
"""Content-free attribution and disposition diagnosis for V2.50.88."""

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

from deepwide_agent import v25088_partial_field_external_contract as contract  # noqa: E402
from scripts import run_v25088_partial_field_external as runner  # noqa: E402


OUTPUT = Path("results/v25089_v25088_partial_field_external_diagnosis_v1_20260811.json")


def _read_json(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.89 expected JSON object")
    return value


def _read_rows() -> list[dict[str, Any]]:
    return [
        runner.validate_task_row(row)
        for row in runner._read_jsonl(contract.TASK_ROWS, tracked=True)
    ]


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
        raise RuntimeError("V2.50.89 parent barrier drifted")

    completed = [row for row in rows if row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    bindings = [receipt["record_binding_receipt"] for receipt in receipts]
    terminal_names = tuple(
        name for name in rows[0]["effect_health"] if name != "query_local_mapping_failure_rows"
    )
    terminal_hard = sum(
        int(row["effect_health"][name]) for row in rows for name in terminal_names
    )
    mapping_failures = sum(
        int(row["effect_health"]["query_local_mapping_failure_rows"]) for row in rows
    )
    exposed_changed = sum(
        bool(row["candidate_evidence_changed"] and row["prediction_changed"]) for row in rows
    )
    exposed_unchanged = sum(
        bool(row["candidate_evidence_changed"] and not row["prediction_changed"])
        for row in rows
    )
    unexposed_changed = sum(
        bool(not row["candidate_evidence_changed"] and row["prediction_changed"])
        for row in rows
    )
    unexposed_unchanged = sum(
        bool(not row["candidate_evidence_changed"] and not row["prediction_changed"])
        for row in rows
    )
    parsed_fields = _sum(bindings, "parsed_field_count")
    accepted_fields = _sum(bindings, "field_accepted_count")
    label_rejections = _sum(bindings, "field_label_or_value_binding_rejection_count")
    unique_pages = sum(binding["bounded_page_count"] == 1 for binding in bindings)
    multi_pages = sum(binding["joint_identity_bound_page_count"] > 1 for binding in bindings)
    zero_pages = sum(binding["joint_identity_bound_page_count"] == 0 for binding in bindings)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25089_v25088_partial_field_external_content_free_attribution_diagnosis",
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
            "terminal_hard_failure_total": terminal_hard,
            "query_local_mapping_failure_rows": mapping_failures,
            "visible_identity_tasks": sum(binding["visible_identity_present"] for binding in bindings),
            "identity_url_match_pages": _sum(bindings, "identity_url_match_page_count"),
            "identity_surface_match_pages": _sum(bindings, "identity_surface_match_page_count"),
            "joint_identity_bound_pages": _sum(bindings, "joint_identity_bound_page_count"),
            "unique_identity_bound_page_tasks": unique_pages,
            "ambiguous_multi_joint_page_tasks": multi_pages,
            "zero_joint_page_tasks": zero_pages,
            "proposal_strict_json_histogram": _hist(
                [binding["model_output_strictly_valid"] for binding in bindings]
            ),
            "proposal_empty_tasks": sum(binding["parsed_record_count"] == 0 for binding in bindings),
            "proposal_nonempty_tasks": sum(binding["parsed_record_count"] > 0 for binding in bindings),
            "parsed_records": _sum(bindings, "parsed_record_count"),
            "parsed_fields": parsed_fields,
            "field_accepted_count": accepted_fields,
            "field_label_or_value_binding_rejections": label_rejections,
            "field_unknown_rejections": _sum(bindings, "field_unknown_rejection_count"),
            "field_coordinate_rejections": _sum(bindings, "field_coordinate_rejection_count"),
            "field_conflict_rejections": _sum(bindings, "field_conflict_rejection_count"),
            "record_conflicts": _sum(bindings, "record_conflict_count"),
            "verified_partial_records": _sum(bindings, "verified_partial_record_count"),
            "rendered_fields": _sum(bindings, "rendered_field_count"),
            "mixed_accepted_and_rejected_field_tasks": sum(
                binding["field_accepted_count"] > 0
                and binding["parsed_field_count"] > binding["field_accepted_count"]
                for binding in bindings
            ),
            "exposed_and_prediction_changed_tasks": exposed_changed,
            "exposed_and_prediction_unchanged_tasks": exposed_unchanged,
            "unexposed_and_prediction_changed_tasks": unexposed_changed,
            "unexposed_and_prediction_unchanged_tasks": unexposed_unchanged,
        },
        "diagnosis": {
            "mechanism_gate_passed": False,
            "evaluator_and_quality_conclusion_remain_forbidden": True,
            "all_twenty_tasks_completed_without_terminal_hard_failure": (
                len(completed) == contract.TASK_COUNT
                and not any(row["failure_as_zero"] for row in rows)
                and terminal_hard == 0
            ),
            "partial_field_retention_created_four_real_exposures": accepted_fields == 4
            and forward["aggregate"]["verifier_exposure_tasks"] == 4,
            "all_four_exposures_retained_a_good_field_beside_rejected_fields": (
                accepted_fields == 4
                and sum(
                    binding["field_accepted_count"] > 0
                    and binding["parsed_field_count"] > binding["field_accepted_count"]
                    for binding in bindings
                )
                == 4
            ),
            "ten_of_fourteen_fields_failed_label_or_value_binding": (
                parsed_fields == 14 and label_rejections == 10 and accepted_fields == 4
            ),
            "unique_identity_page_requirement_limited_proposal_surface_to_eight_tasks": (
                unique_pages == 8 and multi_pages == 9 and zero_pages == 3
            ),
            "no_exposed_task_changed_prediction": exposed_changed == 0
            and exposed_unchanged == 4,
            "all_prediction_changes_were_unexposed_independent_synthesis_variation": (
                unexposed_changed == 4
                and forward["aggregate"]["prediction_changed_tasks"] == 4
            ),
            "separate_exposure_and_prediction_change_thresholds_do_not_establish_attribution": True,
            "future_gate_must_require_exposure_prediction_change_intersection": True,
            "future_runtime_must_identity_handoff_when_candidate_evidence_is_unchanged": True,
            "next_candidate_must_not_retry_resume_or_reuse_v25088_population": True,
            "next_build_only_candidate_should_resolve_multiple_strict_identity_pages_by_one_visible_authority": True,
            "next_build_only_candidate_must_fail_closed_without_one_unique_visible_authority_winner": True,
            "identity_url_surface_field_coordinate_and_conflict_checks_must_remain_strict": True,
            "query_fetch_model_context_token_wall_or_network_byte_caps_must_not_expand": True,
            "entropy_or_information_gain_signed_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "question_query_url_title_page_quote_identity_field_value_prediction_answer_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "only_content_free_receipt_counts_booleans_and_parent_hashes_aggregated": True,
        },
        "authorization": {
            "v25088_evaluator_or_quality_result": False,
            "v25088_retry_resume_skip_or_selective_rerun": False,
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
    if (
        copied.get("role")
        != "v25089_v25088_partial_field_external_content_free_attribution_diagnosis"
        or seal != contract.payload_sha256(unsigned)
        or diagnosis.get("mechanism_gate_passed") is not False
        or diagnosis.get("evaluator_and_quality_conclusion_remain_forbidden") is not True
        or diagnosis.get("all_twenty_tasks_completed_without_terminal_hard_failure") is not True
        or diagnosis.get("partial_field_retention_created_four_real_exposures") is not True
        or diagnosis.get("all_four_exposures_retained_a_good_field_beside_rejected_fields") is not True
        or diagnosis.get("ten_of_fourteen_fields_failed_label_or_value_binding") is not True
        or diagnosis.get("unique_identity_page_requirement_limited_proposal_surface_to_eight_tasks") is not True
        or diagnosis.get("no_exposed_task_changed_prediction") is not True
        or diagnosis.get("all_prediction_changes_were_unexposed_independent_synthesis_variation") is not True
        or diagnosis.get("future_gate_must_require_exposure_prediction_change_intersection") is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or funnel.get("visible_identity_tasks") != 20
        or funnel.get("unique_identity_bound_page_tasks") != 8
        or funnel.get("ambiguous_multi_joint_page_tasks") != 9
        or funnel.get("zero_joint_page_tasks") != 3
        or funnel.get("parsed_fields") != 14
        or funnel.get("field_accepted_count") != 4
        or funnel.get("field_label_or_value_binding_rejections") != 10
        or funnel.get("exposed_and_prediction_changed_tasks") != 0
        or funnel.get("unexposed_and_prediction_changed_tasks") != 4
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
        raise RuntimeError("V2.50.89 diagnosis drifted")
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
