#!/usr/bin/env python3
"""Content-free diagnosis for the frozen V2.51.03 mechanism NO-GO."""

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

from deepwide_agent import v25103_complete_column_external_contract as contract  # noqa: E402
from scripts import run_v25103_complete_column_external as runner  # noqa: E402


OUTPUT = Path("results/v25104_v25103_complete_column_external_diagnosis_v1_20260811.json")


def _read_json(relative: Path) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=True)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.04 expected JSON object")
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
        raise RuntimeError("V2.51.04 parent barrier drifted")

    completed = [row for row in rows if row["runtime_completed"]]
    failures = [row for row in rows if not row["runtime_completed"]]
    receipts = [row["content_free_receipt"] for row in completed]
    bindings = [receipt["record_binding_receipt"] for receipt in receipts]
    parents = [binding["parent_value_shape_receipt"] for binding in bindings]
    selections = [parent["authority_selection_receipt"] for parent in parents]
    accounting = [
        row
        for row in failures
        if row["post_synthesis_accounting_or_receipt_validation_failed"]
    ]
    exposed = [row for row in completed if row["candidate_evidence_changed"]]
    terminal_names = tuple(
        name for name in rows[0]["effect_health"] if name != "query_local_mapping_failure_rows"
    )
    terminal_hard = sum(
        int(row["effect_health"][name]) for row in rows for name in terminal_names
    )
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25104_v25103_complete_column_content_free_diagnosis",
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
            "accounting_failure_stage_histogram": _hist(
                [row["content_free_receipt"]["failure_stage"] for row in accounting]
            ),
            "accounting_failure_type_histogram": _hist(
                [row["content_free_receipt"]["failure_type"] for row in accounting]
            ),
            "terminal_hard_failure_total": terminal_hard,
            "query_local_mapping_failure_rows": sum(
                int(row["effect_health"]["query_local_mapping_failure_rows"])
                for row in rows
            ),
            "selected_page_tasks": sum(
                selection["selected_page_count"] == 1 for selection in selections
            ),
            "complete_proposal_tasks": sum(
                binding["complete_column_proposal_strictly_valid"] for binding in bindings
            ),
            "submitted_column_dispositions": _sum(
                bindings, "submitted_column_disposition_count"
            ),
            "found_column_dispositions": _sum(bindings, "found_column_disposition_count"),
            "unavailable_column_dispositions": _sum(
                bindings, "unavailable_column_disposition_count"
            ),
            "parent_parsed_fields": _sum(bindings, "parent_parsed_field_count"),
            "parent_accepted_fields": _sum(bindings, "parent_accepted_field_count"),
            "field_lexical_accepted_count": _sum(parents, "field_lexical_accepted_count"),
            "field_value_shape_accepted_count": _sum(
                parents, "field_value_shape_accepted_count"
            ),
            "field_value_shape_rejection_count": _sum(
                parents, "field_value_shape_rejection_count"
            ),
            "field_coordinate_rejection_count": _sum(
                parents, "field_coordinate_rejection_count"
            ),
            "verifier_exposure_tasks": len(exposed),
            "exposed_and_prediction_changed_tasks": sum(
                row["prediction_changed"] for row in exposed
            ),
            "exposed_and_prediction_unchanged_tasks": sum(
                not row["prediction_changed"] for row in exposed
            ),
            "unexposed_and_prediction_changed_tasks": sum(
                not row["candidate_evidence_changed"] and row["prediction_changed"]
                for row in completed
            ),
            "exposed_single_accepted_field_tasks": sum(
                row["content_free_receipt"]["record_binding_receipt"][
                    "parent_accepted_field_count"
                ]
                == 1
                for row in exposed
            ),
            "exposed_multiple_accepted_field_tasks": sum(
                row["content_free_receipt"]["record_binding_receipt"][
                    "parent_accepted_field_count"
                ]
                > 1
                for row in exposed
            ),
        },
        "synthetic_reproduction": {
            "network_model_search_fetch_or_evaluator_called": False,
            "single_whitespace_fetch_result_reproduces_terminal_accounting_failure": True,
            "reproduced_failure_stage": "receipt_construction",
            "reproduced_failure_type": "ValueError",
            "runtime_page_count_uses_nonempty_content_filter": True,
            "wave_usable_page_count_uses_strip_before_boolean": True,
            "root_cause_is_whitespace_only_page_count_mismatch": True,
        },
        "diagnosis": {
            "mechanism_gate_passed": False,
            "evaluator_and_quality_conclusion_remain_forbidden": True,
            "nineteen_completed_one_accounting_failure_as_zero": (
                len(completed) == 19 and len(accounting) == 1
            ),
            "accounting_failure_is_receipt_construction_value_error": (
                len(accounting) == 1
                and accounting[0]["content_free_receipt"]["failure_stage"]
                == "receipt_construction"
                and accounting[0]["content_free_receipt"]["failure_type"] == "ValueError"
            ),
            "accounting_failure_has_no_transport_model_timeout_or_outer_failure": (
                len(accounting) == 1
                and terminal_hard == 0
                and accounting[0]["outer_failure_type"] is None
            ),
            "complete_column_contract_raised_exposure_from_seven_to_ten": (
                forward["aggregate"]["verifier_exposure_tasks"] == 10
            ),
            "all_completed_proposals_have_complete_disposition_vectors": (
                len(bindings) == 19
                and all(
                    binding["complete_column_proposal_strictly_valid"]
                    for binding in bindings
                )
            ),
            "ten_exposures_created_only_two_attributable_prediction_changes": (
                len(exposed) == 10
                and sum(row["prediction_changed"] for row in exposed) == 2
            ),
            "unexposed_prediction_noise_remains_zero": (
                forward["aggregate"]["unexposed_and_prediction_changed_tasks"] == 0
            ),
            "next_runtime_must_use_one_canonical_usable_page_count": True,
            "next_candidate_should_deterministically_enforce_verified_fields_after_synthesis": True,
            "deterministic_enforcement_must_not_add_model_search_fetch_token_context_wall_or_network_budget": True,
            "next_candidate_must_not_retry_resume_or_reuse_v25103_population": True,
            "value_shape_authority_coordinate_conflict_and_attribution_checks_must_remain_strict": True,
            "entropy_or_information_gain_signed_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "question_query_url_title_page_quote_identity_field_value_prediction_answer_or_hash_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "only_content_free_receipt_counts_failure_types_parent_hashes_and_synthetic_boolean_result_aggregated": True,
        },
        "authorization": {
            "v25103_evaluator_or_quality_result": False,
            "v25103_retry_resume_skip_or_selective_rerun": False,
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
    reproduction = copied.get("synthetic_reproduction") or {}
    authorization = copied.get("authorization") or {}
    required_true = (
        "nineteen_completed_one_accounting_failure_as_zero",
        "accounting_failure_is_receipt_construction_value_error",
        "accounting_failure_has_no_transport_model_timeout_or_outer_failure",
        "complete_column_contract_raised_exposure_from_seven_to_ten",
        "all_completed_proposals_have_complete_disposition_vectors",
        "ten_exposures_created_only_two_attributable_prediction_changes",
        "unexposed_prediction_noise_remains_zero",
        "next_runtime_must_use_one_canonical_usable_page_count",
        "next_candidate_should_deterministically_enforce_verified_fields_after_synthesis",
        "deterministic_enforcement_must_not_add_model_search_fetch_token_context_wall_or_network_budget",
    )
    if (
        copied.get("role") != "v25104_v25103_complete_column_content_free_diagnosis"
        or seal != contract.payload_sha256(unsigned)
        or diagnosis.get("mechanism_gate_passed") is not False
        or diagnosis.get("evaluator_and_quality_conclusion_remain_forbidden") is not True
        or any(diagnosis.get(name) is not True for name in required_true)
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or funnel.get("selected_page_tasks") != 15
        or funnel.get("complete_proposal_tasks") != 19
        or funnel.get("submitted_column_dispositions") != 45
        or funnel.get("found_column_dispositions") != 12
        or funnel.get("unavailable_column_dispositions") != 33
        or funnel.get("parent_accepted_fields") != 11
        or funnel.get("verifier_exposure_tasks") != 10
        or funnel.get("exposed_and_prediction_changed_tasks") != 2
        or funnel.get("exposed_and_prediction_unchanged_tasks") != 8
        or funnel.get("unexposed_and_prediction_changed_tasks") != 0
        or reproduction.get("root_cause_is_whitespace_only_page_count_mismatch") is not True
        or reproduction.get("network_model_search_fetch_or_evaluator_called") is not False
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
        raise RuntimeError("V2.51.04 diagnosis drifted")
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
