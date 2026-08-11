#!/usr/bin/env python3
"""Content-free post-freeze diagnosis for V2.50.68."""

from __future__ import annotations

import copy
import hashlib
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

from deepwide_agent import v25068_quote_verified_external_contract as contract  # noqa: E402
from scripts import run_v25068_quote_verified_external as runner  # noqa: E402


OUTPUT = Path("results/v25069_v25068_quote_verified_external_diagnosis_v1_20260811.json")


def _read_json(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.69 expected JSON object")
    return value


def _read_rows() -> list[dict[str, Any]]:
    return [runner.validate_task_row(row) for row in runner._read_jsonl(contract.TASK_ROWS, tracked=True)]


def _hist(values: Sequence[object]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


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
        or len(rows) != contract.TASK_COUNT
    ):
        raise RuntimeError("V2.50.69 parent barrier drifted")
    completed = [row for row in rows if row["runtime_completed"]]
    records = [row["content_free_receipt"]["record_binding_receipt"] for row in completed]
    health_names = tuple(rows[0]["hard_failure_health"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25069_v25068_quote_verified_external_content_free_diagnosis",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
            "forward_audit_sha256": contract.sha256(ROOT / contract.FORWARD_AUDIT),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
        },
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_runtime_diagnosis": {
            "runtime_completed_histogram": _hist([row["runtime_completed"] for row in rows]),
            "outer_failure_type_histogram": _hist(
                [row["outer_failure_type"] for row in rows if row["outer_failure_type"] is not None]
            ),
            "normalizer_pair_histogram": _hist(
                [
                    (
                        row["normalizer_status"][contract.CONTROL_ARM],
                        row["normalizer_status"][contract.CANDIDATE_ARM],
                    )
                    for row in rows
                ]
            ),
            "hard_failure_health_totals": {
                name: sum(int(row["hard_failure_health"][name]) for row in rows)
                for name in health_names
            },
            "record_proposal_attempted_histogram": _hist(
                [record["model_call_attempted"] for record in records]
            ),
            "record_proposal_strict_json_histogram": _hist(
                [record["model_output_strictly_valid"] for record in records]
            ),
            "parsed_record_count_histogram": _hist(
                [record["parsed_record_count"] for record in records]
            ),
            "verified_record_count_histogram": _hist(
                [record["verified_quote_record_count"] for record in records]
            ),
            "rendered_record_count_histogram": _hist(
                [record["rendered_record_count"] for record in records]
            ),
            "rejected_field_binding_count_histogram": _hist(
                [record["rejected_field_binding_count"] for record in records]
            ),
            "bounded_page_count_histogram": _hist(
                [record["bounded_page_count"] for record in records]
            ),
            "candidate_evidence_changed_tasks": sum(row["candidate_evidence_changed"] for row in rows),
            "prediction_changed_tasks": sum(row["prediction_changed"] for row in rows),
        },
        "diagnosis": {
            "mechanism_gate_passed": False,
            "evaluator_remains_forbidden": True,
            "verifier_zero_exposure_is_not_parser_or_transport_failure": all(
                record["model_call_attempted"] and record["model_output_strictly_valid"]
                for record in records
            ),
            "dominant_proposal_outcome_is_strict_empty_record_list": sum(
                record["parsed_record_count"] == 0 for record in records
            )
            == len(records) - 1,
            "only_nonempty_proposal_failed_field_binding": sum(
                record["parsed_record_count"] > 0
                and record["verified_quote_record_count"] == 0
                and record["rejected_field_binding_count"] > 0
                for record in records
            )
            == 1,
            "current_single_quote_all_fields_contract_has_no_natural_reach": all(
                record["verified_quote_record_count"] == 0 for record in records
            ),
            "search_failure_counter_is_not_equivalent_to_terminal_retrieval_failure": sum(
                row["hard_failure_health"]["search_request_failures"] for row in completed
            )
            > 0
            and all(
                row["content_free_receipt"]["first_wave_receipt"] is not None
                and row["content_free_receipt"]["second_wave_receipt"] is not None
                for row in completed
            ),
            "one_outer_value_error_type_is_insufficient_for_root_cause": sum(
                not row["runtime_completed"] for row in rows
            )
            == 1,
            "next_candidate_must_not_retry_resume_or_reuse_v25068_population": True,
            "next_candidate_should_verify_fields_independently_within_one_source_page_then_bind_one_record": True,
            "next_candidate_should_preserve_quote_coordinates_per_field_and_forbid_cross_page_or_cross_identity_merge": True,
            "next_gate_should_define_hard_transport_failure_from_terminal_effect_receipts_not_recoverable_mapping_rows": True,
            "query_fetch_model_context_token_wall_or_network_byte_caps_must_not_expand": True,
            "entropy_or_information_gain_signed_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "question_query_url_title_page_quote_identity_field_value_prediction_answer_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "only_content_free_counts_booleans_failure_type_and_parent_hashes_read": True,
        },
        "authorization": {
            "v25068_evaluator_or_quality_result": False,
            "v25068_retry_resume_skip_or_selective_rerun": False,
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
    authorization = copied.get("authorization") or {}
    diagnosis = copied.get("diagnosis") or {}
    if (
        copied.get("role") != "v25069_v25068_quote_verified_external_content_free_diagnosis"
        or seal != contract.payload_sha256(unsigned)
        or diagnosis.get("mechanism_gate_passed") is not False
        or diagnosis.get("evaluator_remains_forbidden") is not True
        or diagnosis.get("current_single_quote_all_fields_contract_has_no_natural_reach") is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
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
        raise RuntimeError("V2.50.69 diagnosis drifted")
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
