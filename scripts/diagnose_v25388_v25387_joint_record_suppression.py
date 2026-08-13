#!/usr/bin/env python3
"""Content-free diagnosis of the V2.53.87 joint-record suppression funnel."""

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

from deepwide_agent import v25387_rfc_joint_synthesis_external_contract as contract  # noqa: E402
from scripts import run_v25387_rfc_joint_synthesis_external as runner  # noqa: E402


DATE = "20260813"
ROLE = "v25388_v25387_content_free_joint_record_suppression_diagnosis"
SOURCE = Path("scripts/diagnose_v25388_v25387_joint_record_suppression.py")
TEST = Path("tests/test_diagnose_v25388_v25387_joint_record_suppression.py")
OUTPUT = Path(
    f"results/v25388_v25387_joint_record_suppression_diagnosis_v1_{DATE}.json"
)
FORWARD_RESULT = contract.FORWARD_RESULT
FORWARD_AUDIT = contract.FORWARD_AUDIT
TASK_ROWS = contract.TASK_ROWS
PREDICTION_FREEZE = contract.PREDICTION_FREEZE
FIXED_HASHES = {
    FORWARD_RESULT: "0ec26a06bf2cd47f72d54117359b0aa6128ff3d2704c74d05a2afee19d8702e9",
    FORWARD_AUDIT: "6239d65203328762884fd40216a63854d727809b3e58a72412fe475482a90e6e",
    TASK_ROWS: "e970300d00f466a186246a7e5bf8d73480695446bee293b6b7642db3ca90ab75",
    PREDICTION_FREEZE: "a1fa9ee4f0865c6d9caa04e75c466e9e1c592eae3161c353f7f63523354f2a50",
}


def _read(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.88 expected JSON object")
    return value


def _barrier() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if any(contract.sha256(ROOT / path) != expected for path, expected in FIXED_HASHES.items()):
        raise RuntimeError("V2.53.88 fixed artifact hash drifted")
    forward = runner.validate_forward_result(_read(FORWARD_RESULT))
    audit = _read(FORWARD_AUDIT)
    rows = [
        runner.validate_task_row(row)
        for row in runner._read_jsonl(TASK_ROWS, tracked=True)
    ]
    if (
        audit.get("role") != "v25387_rfc_joint_synthesis_forward_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("deepwidebench_successor_build")
        is not False
        or audit.get("forward_result_sha256")
        != contract.sha256(ROOT / FORWARD_RESULT)
        or len(rows) != contract.TASK_COUNT
        or forward["aggregate"]
        != runner.aggregate_rows(
            rows, wall_seconds=float(forward["aggregate"]["batch_wall_seconds"])
        )
    ):
        raise RuntimeError("V2.53.88 forward audit barrier drifted")
    return forward, rows


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, rows = _barrier()
    joints = [
        row["content_free_stage_receipt"]["joint_synthesis_receipt"]
        for row in rows
    ]
    grounded_tasks = sum(
        receipt["grounded_records_stripped_count"] > 0 for receipt in joints
    )
    grounded_total = sum(
        receipt["grounded_records_stripped_count"] for receipt in joints
    )
    joint_tasks = sum(receipt["envelope_record_count"] > 0 for receipt in joints)
    joint_total = sum(receipt["envelope_record_count"] for receipt in joints)
    verifier_counts: dict[str, int] = {}
    prompt_counts: dict[str, int] = {}
    for receipt in joints:
        verifier = str(receipt["verifier_bounded_page_count"])
        prompt = str(receipt["synthesis_prompt_page_count"])
        verifier_counts[verifier] = verifier_counts.get(verifier, 0) + 1
        prompt_counts[prompt] = prompt_counts.get(prompt, 0) + 1
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "source_bindings": {
            str(path): contract.sha256(ROOT / path) for path in FIXED_HASHES
        },
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_funnel": {
            "task_count": len(joints),
            "joint_envelope_exact_tasks": sum(
                receipt["joint_envelope_exact"] for receipt in joints
            ),
            "joint_table_normalizable_tasks": sum(
                receipt["joint_table_normalizable"] for receipt in joints
            ),
            "joint_records_armed_tasks": sum(
                receipt["joint_records_armed"] for receipt in joints
            ),
            "grounded_record_member_nonempty_tasks": grounded_tasks,
            "grounded_record_count_total": grounded_total,
            "joint_record_member_nonempty_tasks": joint_tasks,
            "joint_record_count_total": joint_total,
            "verified_record_tasks": sum(
                receipt["verified_record_count"] > 0 for receipt in joints
            ),
            "changed_safe_coordinate_tasks": sum(
                receipt["changed_safe_coordinate_count"] > 0 for receipt in joints
            ),
            "attributable_prediction_changed_tasks": sum(
                row["attributable_prediction_change"] for row in rows
            ),
            "synthesis_prompt_page_count_histogram": prompt_counts,
            "verifier_bounded_page_count_histogram": verifier_counts,
            "verifier_bounded_page_characters_min": min(
                receipt["verifier_bounded_page_characters"] for receipt in joints
            ),
            "verifier_bounded_page_characters_max": max(
                receipt["verifier_bounded_page_characters"] for receipt in joints
            ),
        },
        "diagnosis": {
            "retrieval_plan_and_joint_envelope_are_not_current_bottlenecks": True,
            "joint_third_response_record_proposal_is_current_first_zero_conversion": True,
            "grounded_second_response_has_nonzero_record_proposals": grounded_tasks > 0,
            "same_forward_grounded_record_fallback_is_mechanically_available": grounded_tasks > 0,
            "grounded_and_joint_records_must_not_be_merged": True,
            "fixed_priority_joint_nonempty_else_grounded_preserves_one_record_source": True,
            "fallback_records_still_require_existing_page_quote_field_value_and_same_response_table_row_verification": True,
            "quality_or_deepwidebench_improvement_established": False,
            "entropy_information_gain_signed_credit_evidence_present": False,
        },
        "contains_question_query_url_page_quote_record_identity_field_value_prediction_answer_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read": False,
        "model_search_fetch_evaluator_benchmark_or_api_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "hybrid_joint_or_grounded_record_fallback_build_only": True,
            "new_external_forward": False,
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
    funnel = copied.get("content_free_funnel")
    diagnosis = copied.get("diagnosis")
    authorization = copied.get("authorization")
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("source_bindings")
        != {str(path): expected for path, expected in FIXED_HASHES.items()}
        or not isinstance(funnel, Mapping)
        or funnel.get("task_count") != 20
        or funnel.get("joint_envelope_exact_tasks") != 20
        or funnel.get("joint_table_normalizable_tasks") != 20
        or funnel.get("joint_records_armed_tasks") != 20
        or funnel.get("grounded_record_member_nonempty_tasks") != 8
        or funnel.get("grounded_record_count_total") != 11
        or funnel.get("joint_record_member_nonempty_tasks") != 0
        or funnel.get("joint_record_count_total") != 0
        or funnel.get("verified_record_tasks") != 0
        or funnel.get("changed_safe_coordinate_tasks") != 0
        or funnel.get("attributable_prediction_changed_tasks") != 0
        or funnel.get("synthesis_prompt_page_count_histogram")
        != {"9": 5, "10": 15}
        or funnel.get("verifier_bounded_page_count_histogram")
        != {"6": 12, "7": 8}
        or funnel.get("verifier_bounded_page_characters_min") != 12_000
        or funnel.get("verifier_bounded_page_characters_max") != 12_000
        or not isinstance(diagnosis, Mapping)
        or diagnosis
        != {
            "retrieval_plan_and_joint_envelope_are_not_current_bottlenecks": True,
            "joint_third_response_record_proposal_is_current_first_zero_conversion": True,
            "grounded_second_response_has_nonzero_record_proposals": True,
            "same_forward_grounded_record_fallback_is_mechanically_available": True,
            "grounded_and_joint_records_must_not_be_merged": True,
            "fixed_priority_joint_nonempty_else_grounded_preserves_one_record_source": True,
            "fallback_records_still_require_existing_page_quote_field_value_and_same_response_table_row_verification": True,
            "quality_or_deepwidebench_improvement_established": False,
            "entropy_information_gain_signed_credit_evidence_present": False,
        }
        or copied.get(
            "contains_question_query_url_page_quote_record_identity_field_value_prediction_answer_or_credential"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
        )
        is not False
        or copied.get("model_search_fetch_evaluator_benchmark_or_api_called")
        is not False
        or copied.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or copied.get("positive_signed_credit_count") != 0
        or authorization
        != {
            "hybrid_joint_or_grounded_record_fallback_build_only": True,
            "new_external_forward": False,
            "deepwidebench_forward_or_evaluator": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.88 joint record suppression diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
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


def main() -> None:
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "content_free_funnel": value["content_free_funnel"],
                "authorization": value["authorization"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
