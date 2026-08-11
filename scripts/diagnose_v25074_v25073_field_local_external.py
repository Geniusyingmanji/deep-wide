#!/usr/bin/env python3
"""Content-free post-freeze diagnosis for the V2.50.73 external gate."""

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

from deepwide_agent import v25073_field_local_external_contract as contract  # noqa: E402
from scripts import run_v25073_field_local_external as runner  # noqa: E402


OUTPUT = Path("results/v25074_v25073_field_local_external_diagnosis_v1_20260811.json")


def _read_json(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.74 expected JSON object")
    return value


def _read_rows() -> list[dict[str, Any]]:
    return [
        runner.validate_task_row(row)
        for row in runner._read_jsonl(contract.TASK_ROWS, tracked=True)
    ]


def _hist(values: Sequence[object]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _sum(records: Sequence[Mapping[str, Any]], name: str) -> int:
    return sum(int(record[name]) for record in records)


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
        raise RuntimeError("V2.50.74 parent barrier drifted")

    completed = [row for row in rows if row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    records = [receipt["record_binding_receipt"] for receipt in receipts]
    health_names = tuple(rows[0]["effect_health"])
    terminal_health_names = tuple(
        name for name in health_names if name != "query_local_mapping_failure_rows"
    )
    proposal_empty = sum(record["parsed_record_count"] == 0 for record in records)
    proposal_nonempty = sum(record["parsed_record_count"] > 0 for record in records)
    verified_tasks = sum(record["verified_anchor_record_count"] > 0 for record in records)
    binding_rejection_tasks = sum(
        record["parsed_record_count"] > 0
        and record["verified_anchor_record_count"] == 0
        and record["rejected_field_label_or_value_binding_count"] > 0
        for record in records
    )
    terminal_hard_failures = sum(
        int(row["effect_health"][name])
        for row in rows
        for name in terminal_health_names
    )
    query_local_mapping_failures = sum(
        int(row["effect_health"]["query_local_mapping_failure_rows"])
        for row in rows
    )

    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25074_v25073_field_local_external_content_free_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        },
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_runtime_diagnosis": {
            "runtime_completed_histogram": _hist([row["runtime_completed"] for row in rows]),
            "failure_as_zero_histogram": _hist([row["failure_as_zero"] for row in rows]),
            "outer_failure_type_histogram": _hist(
                [row["outer_failure_type"] for row in rows if row["outer_failure_type"] is not None]
            ),
            "effect_health_totals": {
                name: sum(int(row["effect_health"][name]) for row in rows)
                for name in health_names
            },
            "terminal_hard_failure_total": terminal_hard_failures,
            "query_local_mapping_failure_rows": query_local_mapping_failures,
            "proposal_model_call_attempted_histogram": _hist(
                [record["model_call_attempted"] for record in records]
            ),
            "proposal_strict_json_histogram": _hist(
                [record["model_output_strictly_valid"] for record in records]
            ),
            "parsed_record_count_histogram": _hist(
                [record["parsed_record_count"] for record in records]
            ),
            "parsed_field_count_histogram": _hist(
                [record["parsed_field_count"] for record in records]
            ),
            "verified_record_count_histogram": _hist(
                [record["verified_anchor_record_count"] for record in records]
            ),
            "verified_field_count_histogram": _hist(
                [record["verified_field_quote_count"] for record in records]
            ),
            "rendered_record_count_histogram": _hist(
                [record["rendered_record_count"] for record in records]
            ),
            "proposal_empty_tasks": proposal_empty,
            "proposal_nonempty_tasks": proposal_nonempty,
            "verified_record_tasks": verified_tasks,
            "field_label_or_value_binding_rejection_tasks": binding_rejection_tasks,
            "parsed_records": _sum(records, "parsed_record_count"),
            "parsed_fields": _sum(records, "parsed_field_count"),
            "verified_records": _sum(records, "verified_anchor_record_count"),
            "verified_fields": _sum(records, "verified_field_quote_count"),
            "rendered_records": _sum(records, "rendered_record_count"),
            "rendered_fields": _sum(records, "rendered_field_count"),
            "field_label_or_value_binding_rejections": _sum(
                records, "rejected_field_label_or_value_binding_count"
            ),
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
                and terminal_hard_failures == 0
            ),
            "query_local_mapping_failures_are_coverage_diagnostics_not_terminal_failures": (
                query_local_mapping_failures == 28 and terminal_hard_failures == 0
            ),
            "all_proposal_calls_succeeded_with_strict_json": all(
                record["model_call_attempted"] and record["model_output_strictly_valid"]
                for record in records
            ),
            "dominant_outcome_is_empty_proposal": proposal_empty == 18
            and proposal_nonempty == 2,
            "one_nonempty_proposal_verified_and_one_failed_field_binding": (
                verified_tasks == 1 and binding_rejection_tasks == 1
            ),
            "field_local_contract_improved_natural_exposure_but_remains_below_gate": (
                forward["aggregate"]["verifier_exposure_tasks"] == 1
                and contract.mechanism_gate()["minimum_verifier_exposure_tasks"] == 8
            ),
            "prediction_change_remains_below_gate": (
                forward["aggregate"]["prediction_changed_tasks"] == 3
                and contract.mechanism_gate()["minimum_prediction_changed_tasks"] == 4
            ),
            "proposal_reach_is_primary_observed_bottleneck": proposal_empty == 18,
            "prediction_change_cannot_be_fully_attributed_to_treatment": (
                forward["aggregate"]["prediction_changed_tasks"]
                > forward["aggregate"]["verifier_exposure_tasks"]
            ),
            "next_candidate_must_not_retry_resume_or_reuse_v25073_population": True,
            "next_candidate_should_use_unique_anchor_to_define_same_page_bounded_record_region": True,
            "next_candidate_should_require_each_field_quote_to_be_unique_inside_that_region": True,
            "next_candidate_should_not_require_each_field_quote_to_contain_the_anchor": True,
            "next_candidate_must_preserve_identity_source_label_value_verbatim_binding_and_conflict_fail_closed": True,
            "query_fetch_model_context_token_wall_or_network_byte_caps_must_not_expand": True,
            "entropy_or_information_gain_signed_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "question_query_url_title_page_quote_anchor_identity_field_value_prediction_answer_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "only_content_free_receipt_counts_booleans_failure_types_and_parent_hashes_aggregated": True,
        },
        "authorization": {
            "v25073_evaluator_or_quality_result": False,
            "v25073_retry_resume_skip_or_selective_rerun": False,
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
    diagnosis = copied.get("diagnosis") or {}
    runtime = copied.get("content_free_runtime_diagnosis") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != "v25074_v25073_field_local_external_content_free_diagnosis"
        or seal != contract.payload_sha256(unsigned)
        or diagnosis.get("mechanism_gate_passed") is not False
        or diagnosis.get("evaluator_and_quality_conclusion_remain_forbidden") is not True
        or diagnosis.get("all_twenty_tasks_completed_without_terminal_hard_failure") is not True
        or diagnosis.get("dominant_outcome_is_empty_proposal") is not True
        or diagnosis.get("one_nonempty_proposal_verified_and_one_failed_field_binding") is not True
        or diagnosis.get("proposal_reach_is_primary_observed_bottleneck") is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or runtime.get("query_local_mapping_failure_rows") != 28
        or runtime.get("proposal_empty_tasks") != 18
        or runtime.get("proposal_nonempty_tasks") != 2
        or runtime.get("verified_record_tasks") != 1
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
        raise RuntimeError("V2.50.74 diagnosis drifted")
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
