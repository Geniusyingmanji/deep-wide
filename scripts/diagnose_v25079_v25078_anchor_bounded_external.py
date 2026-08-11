#!/usr/bin/env python3
"""Content-free post-freeze funnel diagnosis for V2.50.78."""

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

from deepwide_agent import v25078_anchor_bounded_external_contract as contract  # noqa: E402
from scripts import run_v25078_anchor_bounded_external as runner  # noqa: E402


OUTPUT = Path("results/v25079_v25078_anchor_bounded_external_diagnosis_v1_20260811.json")


def _read_json(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.79 expected JSON object")
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
        raise RuntimeError("V2.50.79 parent barrier drifted")

    completed = [row for row in rows if row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    bindings = [receipt["record_binding_receipt"] for receipt in receipts]
    waves = [
        wave
        for receipt in receipts
        for wave in (receipt["first_wave_receipt"], receipt["second_wave_receipt"])
        if wave is not None
    ]
    fetch_receipts = [wave["fetch_receipt"] for wave in waves]
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
    parsed_records = _sum(bindings, "parsed_record_count")
    verified_records = _sum(bindings, "verified_region_record_count")
    empty_proposals = sum(binding["parsed_record_count"] == 0 for binding in bindings)
    nonempty_proposals = sum(binding["parsed_record_count"] > 0 for binding in bindings)
    upstream = {
        "wave_count": len(waves),
        "wave_discovered_records": _sum(waves, "discovered_records"),
        "wave_admissible_records": _sum(waves, "admissible_records"),
        "wave_retained_records": _sum(waves, "retained_records"),
        "fetch_projector_discovered_records": _sum(fetch_receipts, "discovered_record_count"),
        "fetch_projector_admissible_records": _sum(fetch_receipts, "admissible_record_count"),
        "fetch_projector_retained_records": _sum(fetch_receipts, "retained_record_count"),
        "fetch_projector_mechanism_engaged_pages": _sum(
            fetch_receipts, "mechanism_engaged_page_count"
        ),
        "fetch_projector_changed_pages": _sum(
            fetch_receipts, "candidate_evidence_changed_page_count"
        ),
        "fetch_projector_positive_signed_credit": _sum(
            fetch_receipts, "positive_signed_credit_count"
        ),
    }

    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25079_v25078_anchor_bounded_external_content_free_funnel_diagnosis",
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
            "proposal_empty_tasks": empty_proposals,
            "proposal_nonempty_tasks": nonempty_proposals,
            "parsed_records": parsed_records,
            "parsed_fields": _sum(bindings, "parsed_field_count"),
            "verified_records": verified_records,
            "verified_fields": _sum(bindings, "verified_field_count"),
            "rendered_records": _sum(bindings, "rendered_record_count"),
            "field_label_or_value_binding_rejections": _sum(
                bindings, "rejected_field_label_or_value_binding_count"
            ),
            "candidate_evidence_changed_tasks": sum(
                bool(row["candidate_evidence_changed"]) for row in rows
            ),
            "prediction_changed_tasks": sum(bool(row["prediction_changed"]) for row in rows),
            "upstream_record_projection": upstream,
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
                mapping_failures == 42 and terminal_hard == 0
            ),
            "all_proposal_calls_succeeded_with_strict_json": all(
                binding["model_call_attempted"] and binding["model_output_strictly_valid"]
                for binding in bindings
            ),
            "nineteen_empty_proposals_and_one_nonempty_binding_rejection": (
                empty_proposals == 19
                and nonempty_proposals == 1
                and parsed_records == 1
                and verified_records == 0
                and _sum(bindings, "rejected_field_label_or_value_binding_count") == 1
            ),
            "upstream_projector_also_had_zero_record_exposure": all(
                value == 0 for name, value in upstream.items() if name != "wave_count"
            ),
            "anchor_geometry_relaxation_did_not_create_natural_exposure": (
                forward["aggregate"]["verifier_exposure_tasks"] == 0
            ),
            "prediction_change_is_unattributable_independent_synthesis_variation": (
                forward["aggregate"]["prediction_changed_tasks"] == 5
                and forward["aggregate"]["verifier_exposure_tasks"] == 0
            ),
            "observed_bottleneck_is_page_identity_to_record_conversion_not_transport": True,
            "content_free_counts_do_not_prove_pages_lacked_relevant_facts": True,
            "next_candidate_must_not_retry_resume_or_reuse_v25078_population": True,
            "next_candidate_should_bind_visible_row_identity_to_unique_same_forward_page_title": True,
            "next_candidate_should_verify_fields_inside_identity_bound_page_region": True,
            "next_candidate_must_fail_closed_on_ambiguous_title_identity_field_coordinate_or_conflict": True,
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
            "v25078_evaluator_or_quality_result": False,
            "v25078_retry_resume_skip_or_selective_rerun": False,
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
    upstream = funnel.get("upstream_record_projection") or {}
    if (
        copied.get("role")
        != "v25079_v25078_anchor_bounded_external_content_free_funnel_diagnosis"
        or seal != contract.payload_sha256(unsigned)
        or diagnosis.get("mechanism_gate_passed") is not False
        or diagnosis.get("evaluator_and_quality_conclusion_remain_forbidden") is not True
        or diagnosis.get("all_twenty_tasks_completed_without_terminal_hard_failure") is not True
        or diagnosis.get("nineteen_empty_proposals_and_one_nonempty_binding_rejection") is not True
        or diagnosis.get("upstream_projector_also_had_zero_record_exposure") is not True
        or diagnosis.get("prediction_change_is_unattributable_independent_synthesis_variation") is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or funnel.get("proposal_empty_tasks") != 19
        or funnel.get("proposal_nonempty_tasks") != 1
        or funnel.get("verified_records") != 0
        or upstream.get("wave_count") != 40
        or any(
            upstream.get(name) != 0
            for name in upstream
            if name != "wave_count"
        )
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
        raise RuntimeError("V2.50.79 diagnosis drifted")
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
