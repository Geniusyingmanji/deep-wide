#!/usr/bin/env python3
"""Content-free identity/proposal funnel diagnosis for V2.50.83."""

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

from deepwide_agent import v25083_visible_identity_external_contract as contract  # noqa: E402
from scripts import run_v25083_visible_identity_external as runner  # noqa: E402


OUTPUT = Path("results/v25084_v25083_visible_identity_external_diagnosis_v1_20260811.json")


def _read_json(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.84 expected JSON object")
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
        raise RuntimeError("V2.50.84 parent barrier drifted")
    completed = [row for row in rows if row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    bindings = [receipt["record_binding_receipt"] for receipt in receipts]
    terminal_names = tuple(
        name
        for name in rows[0]["effect_health"]
        if name != "query_local_mapping_failure_rows"
    )
    terminal_hard = sum(
        int(row["effect_health"][name]) for row in rows for name in terminal_names
    )
    mapping_failures = sum(
        int(row["effect_health"]["query_local_mapping_failure_rows"]) for row in rows
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25084_v25083_visible_identity_external_content_free_funnel_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        },
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_identity_proposal_funnel": {
            "runtime_completed_histogram": _hist([row["runtime_completed"] for row in rows]),
            "failure_as_zero_histogram": _hist([row["failure_as_zero"] for row in rows]),
            "terminal_hard_failure_total": terminal_hard,
            "query_local_mapping_failure_rows": mapping_failures,
            "visible_identity_tasks": sum(binding["visible_identity_present"] for binding in bindings),
            "identity_url_match_pages": _sum(bindings, "identity_url_match_page_count"),
            "identity_surface_match_pages": _sum(bindings, "identity_surface_match_page_count"),
            "joint_identity_bound_pages": _sum(bindings, "joint_identity_bound_page_count"),
            "unique_identity_bound_page_tasks": sum(
                binding["bounded_page_count"] == 1 for binding in bindings
            ),
            "ambiguous_multi_joint_page_tasks": sum(
                binding["joint_identity_bound_page_count"] > 1 for binding in bindings
            ),
            "zero_joint_page_tasks": sum(
                binding["joint_identity_bound_page_count"] == 0 for binding in bindings
            ),
            "proposal_model_call_attempted_histogram": _hist(
                [binding["model_call_attempted"] for binding in bindings]
            ),
            "proposal_strict_json_histogram": _hist(
                [binding["model_output_strictly_valid"] for binding in bindings]
            ),
            "parsed_record_count_histogram": _hist(
                [binding["parsed_record_count"] for binding in bindings]
            ),
            "parsed_field_count_histogram": _hist(
                [binding["parsed_field_count"] for binding in bindings]
            ),
            "proposal_empty_tasks": sum(binding["parsed_record_count"] == 0 for binding in bindings),
            "proposal_nonempty_tasks": sum(binding["parsed_record_count"] > 0 for binding in bindings),
            "parsed_records": _sum(bindings, "parsed_record_count"),
            "parsed_fields": _sum(bindings, "parsed_field_count"),
            "verified_records": _sum(bindings, "verified_record_count"),
            "verified_fields": _sum(bindings, "verified_field_count"),
            "field_label_or_value_binding_rejections": _sum(
                bindings, "rejected_field_label_or_value_binding_count"
            ),
            "field_coordinate_rejections": _sum(
                bindings, "rejected_nonunique_field_coordinate_count"
            ),
            "rendered_records": _sum(bindings, "rendered_record_count"),
            "candidate_evidence_changed_tasks": sum(
                bool(row["candidate_evidence_changed"]) for row in rows
            ),
            "prediction_changed_tasks": sum(bool(row["prediction_changed"]) for row in rows),
        },
        "diagnosis": {
            "mechanism_gate_passed": False,
            "evaluator_and_quality_conclusion_remain_forbidden": True,
            "all_twenty_tasks_completed_without_terminal_hard_failure": (
                len(completed) == contract.TASK_COUNT
                and not any(row["failure_as_zero"] for row in rows)
                and terminal_hard == 0
            ),
            "query_local_mapping_failures_are_coverage_not_terminal_failures": (
                mapping_failures == 52 and terminal_hard == 0
            ),
            "identity_binding_created_nine_unique_page_tasks": sum(
                binding["bounded_page_count"] == 1 for binding in bindings
            )
            == 9,
            "proposal_reach_increased_to_eight_nonempty_tasks": sum(
                binding["parsed_record_count"] > 0 for binding in bindings
            )
            == 8,
            "all_eight_nonempty_records_failed_atomic_field_binding": (
                _sum(bindings, "parsed_record_count") == 8
                and _sum(bindings, "verified_record_count") == 0
                and _sum(bindings, "rejected_field_label_or_value_binding_count") == 8
            ),
            "identity_first_improved_proposal_reach_but_not_verifier_exposure": True,
            "prediction_change_is_unattributable_independent_synthesis_variation": (
                forward["aggregate"]["prediction_changed_tasks"] == 1
                and forward["aggregate"]["verifier_exposure_tasks"] == 0
            ),
            "observed_bottleneck_moved_to_atomic_field_disposition": True,
            "aggregate_rejection_does_not_prove_any_individual_field_was_valid": True,
            "next_candidate_must_not_retry_resume_or_reuse_v25083_population": True,
            "next_build_only_candidate_should_emit_per_field_disposition_counts": True,
            "verified_field_subset_may_be_rendered_only_after_each_field_independently_passes_label_value_and_coordinate_binding": True,
            "record_identity_and_page_binding_must_remain_atomic_and_unchanged": True,
            "query_fetch_model_context_token_wall_or_network_byte_caps_must_not_expand": True,
            "entropy_or_information_gain_signed_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "question_query_url_title_page_quote_identity_field_value_prediction_answer_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "only_content_free_receipt_counts_booleans_failure_types_and_parent_hashes_aggregated": True,
        },
        "authorization": {
            "v25083_evaluator_or_quality_result": False,
            "v25083_retry_resume_skip_or_selective_rerun": False,
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
    funnel = copied.get("content_free_identity_proposal_funnel") or {}
    diagnosis = copied.get("diagnosis") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role")
        != "v25084_v25083_visible_identity_external_content_free_funnel_diagnosis"
        or seal != contract.payload_sha256(unsigned)
        or diagnosis.get("mechanism_gate_passed") is not False
        or diagnosis.get("evaluator_and_quality_conclusion_remain_forbidden") is not True
        or diagnosis.get("all_twenty_tasks_completed_without_terminal_hard_failure") is not True
        or diagnosis.get("identity_binding_created_nine_unique_page_tasks") is not True
        or diagnosis.get("proposal_reach_increased_to_eight_nonempty_tasks") is not True
        or diagnosis.get("all_eight_nonempty_records_failed_atomic_field_binding") is not True
        or diagnosis.get("aggregate_rejection_does_not_prove_any_individual_field_was_valid") is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or funnel.get("visible_identity_tasks") != 20
        or funnel.get("unique_identity_bound_page_tasks") != 9
        or funnel.get("proposal_nonempty_tasks") != 8
        or funnel.get("verified_records") != 0
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
        raise RuntimeError("V2.50.84 diagnosis drifted")
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
