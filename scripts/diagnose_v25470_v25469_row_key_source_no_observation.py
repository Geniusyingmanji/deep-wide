#!/usr/bin/env python3
"""Aggregate-only diagnosis of the frozen V2.54.69 zero-observation gate."""

from __future__ import annotations

import copy
import json
import os
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in __import__("sys").path:
        __import__("sys").path.insert(0, str(path))

from deepwide_agent import v25432_source_authoritative_field_candidate as structured_parent  # noqa: E402
from deepwide_agent import v25464_row_key_bound_structured_source_candidate as candidate  # noqa: E402
from deepwide_agent import v25469_row_key_source_external_contract as contract  # noqa: E402
from scripts import run_v25469_row_key_source_external as runner  # noqa: E402


ROLE = "v25470_v25469_row_key_source_no_observation_diagnosis"
OUTPUT = Path("results/v25470_v25469_row_key_source_no_observation_diagnosis_v1_20260814.json")
EXPECTED = {
    str(contract.FORWARD_RESULT): "56f8afa00886374473c6f6673d47e0e37bfaeb10e49f66af04f56c6cb1492532",
    str(contract.FORWARD_AUDIT): "0d6c531ffdcb17f6987f1b5500436086f8b680652f7ff70c1eda24bfe906be21",
    str(contract.TASK_ROWS): "dee6e3ef4c5df11d01698bd62c1330c43ab7cf4baadf0230011e14962324f848",
    str(contract.PREDICTION_FREEZE): "a4e6fc988836cb0e2ba12b61a9c79e5f98cf8b72149090c67c364dcbdb3d46cf",
}


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(contract.ordinary(ROOT, relative, tracked=True).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.54.70 expected a JSON object")
    return value


def _rows() -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, contract.TASK_ROWS, tracked=True)
    values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [runner.validate_task_row(value) for value in values]


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    if any(contract.sha256(ROOT / path) != digest for path, digest in EXPECTED.items()):
        raise RuntimeError("V2.54.70 frozen input hash drifted")
    forward = runner.validate_forward_result(_read(contract.FORWARD_RESULT))
    audit = _read(contract.FORWARD_AUDIT)
    if (
        audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("postfreeze_quality_protocol") is not False
    ):
        raise RuntimeError("V2.54.70 forward audit barrier drifted")
    rows = _rows()
    registry = Counter()
    shape = Counter()
    for row in rows:
        decoded = runner._decode_completed(row["runtime_result"], row["content_free_stage_receipt"])
        result = decoded["result"]
        application = candidate.validate_application(result["private_source_application"])
        receipt = candidate.validate_registry_receipt(
            application["private_candidate_registry"]["content_free_receipt"]
        )
        for name, amount in receipt.items():
            if isinstance(amount, int) and not isinstance(amount, bool):
                registry[name] += amount
        columns, table_rows = structured_parent._canonical_table(
            result["predictions"][runner.runtime.BASE_ARM], result["private_source_columns"]
        )
        bound, _counts = candidate._bound_pages(table_rows, result["private_same_forward_pages"])
        for page in bound:
            for line in str(page["content"]).splitlines():
                requested = [
                    field for field in columns[1:]
                    if structured_parent._key(field)
                    and structured_parent._key(field) in structured_parent._key(line)
                ]
                if not requested:
                    continue
                shape["requested_field_token_lines"] += 1
                cells = structured_parent._pipe_cells(line)
                if cells is not None and len(cells) == 2:
                    shape["requested_field_token_two_cell_pipe_lines"] += 1
                    if any(structured_parent._key(field) in structured_parent._key(cells[0]) for field in requested):
                        shape["requested_field_token_in_left_pipe_cell"] += 1
                        if all(structured_parent._key(cells[0]) != structured_parent._key(field) for field in requested):
                            shape["left_pipe_label_has_extra_tokens"] += 1
                elif any(
                    structured_parent._key(line).endswith(structured_parent._key(field))
                    for field in requested
                ):
                    shape["standalone_or_prose_line_ending_in_requested_field"] += 1
    aggregate = forward["aggregate"]
    diagnosis = {
        "terminal_tasks": aggregate["terminal_tasks"],
        "completed_runtime_tasks": aggregate["completed_runtime_tasks"],
        "synthesis_capture_valid_tasks": aggregate["synthesis_capture_valid_tasks"],
        "captured_same_forward_page_count_total": aggregate["captured_same_forward_page_count_total"],
        "accepted_unique_identity_page_tasks": aggregate["accepted_unique_identity_page_tasks"],
        "accepted_unique_identity_page_count_total": aggregate["accepted_unique_identity_page_count_total"],
        "structured_surface_counts": {
            name: registry[name]
            for name in (
                "explicit_parent_candidate_count",
                "page_bound_horizontal_surface_count",
                "page_bound_vertical_surface_count",
                "page_bound_labelled_surface_count",
                "page_bound_json_surface_count",
                "raw_observation_count",
                "evidence_closed_observation_count",
                "coordinate_group_count",
                "available_candidate_count",
                "applied_coordinate_count",
            )
        },
        "surface_shape_counts": dict(sorted(shape.items())),
        "physical_model_forwards": aggregate["all_physical_model_forwards"],
        "grounded_plan_provider_success_tasks": aggregate["grounded_plan_provider_success_tasks"],
        "prediction_changed_tasks": aggregate["prediction_changed_tasks"],
        "mechanism_gate_passed": forward["mechanism_decision"]["mechanism_gate_passed"],
        "failed_checks": forward["mechanism_decision"]["failed_checks"],
        "next_bottleneck": "row_key_bound_page_to_visible_column_field_alignment",
        "more_row_key_binding_or_more_search_is_not_supported_by_this_result": True,
        "next_candidate_requires_predeclared_generic_source_label_to_visible_column_alignment": True,
        "historical_joint_synthesis_or_exact_label_parser_should_not_be_repeated": True,
    }
    checks = {
        "frozen_inputs_hash_exact": True,
        "forward_and_rows_validate": len(rows) == contract.TASK_COUNT,
        "forward_audit_valid_and_quality_unauthorized": True,
        "all_tasks_terminal_and_runtime_completed": aggregate["terminal_tasks"] == 20
        and aggregate["completed_runtime_tasks"] == 20,
        "row_key_page_binding_nonzero": aggregate["accepted_unique_identity_page_tasks"] >= 3
        and aggregate["accepted_unique_identity_page_count_total"] > 0,
        "all_four_structured_surfaces_zero": all(
            registry[name] == 0
            for name in (
                "page_bound_horizontal_surface_count",
                "page_bound_vertical_surface_count",
                "page_bound_labelled_surface_count",
                "page_bound_json_surface_count",
            )
        ),
        "raw_observation_candidate_edit_and_prediction_change_zero": all(
            amount == 0
            for amount in (
                registry["raw_observation_count"],
                registry["available_candidate_count"],
                registry["applied_coordinate_count"],
                aggregate["prediction_changed_tasks"],
            )
        ),
        "requested_field_tokens_exist_but_exact_structured_labels_do_not": shape[
            "requested_field_token_lines"
        ]
        > 0
        and shape["left_pipe_label_has_extra_tokens"] > 0,
        "mechanism_no_go_and_quality_not_opened": forward["mechanism_decision"][
            "mechanism_gate_passed"
        ]
        is False,
        "positive_signed_credit_zero": aggregate["positive_signed_credit_count"] == 0,
        "mapping_gold_truth_score_reward_evaluator_or_historical_correctness_absent": True,
        "network_model_search_fetch_or_evaluator_call_absent": True,
        "question_opaque_id_query_url_page_quote_value_prediction_or_per_task_outcome_not_persisted": True,
        "protected_watchers_unchanged": contract.watcher_snapshot()
        == [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in contract.EXPECTED_WATCHERS
        ],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "frozen_inputs": copy.deepcopy(EXPECTED),
        "content_free_aggregate_only": True,
        "diagnosis": diagnosis,
        "checks": checks,
        "findings": findings,
        "audit_valid": not findings,
        "mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_correctness_read": False,
        "network_model_search_fetch_or_evaluator_called": False,
        "positive_signed_credit_count": 0,
        "authorization": {
            "generic_source_label_alignment_build_design": not findings,
            "external_protocol_or_forward": False,
            "postfreeze_quality_or_truth": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        },
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    valid = copied.get("audit_valid") is True
    if (
        copied.get("role") != ROLE
        or copied.get("frozen_inputs") != EXPECTED
        or copied.get("content_free_aggregate_only") is not True
        or copied.get("findings") != []
        or not all((copied.get("checks") or {}).values())
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("mapping_gold_category_question_type_split_truth_evaluator_score_reward_or_historical_correctness_read") is not False
        or copied.get("network_model_search_fetch_or_evaluator_called") is not False
        or copied.get("authorization")
        != {
            "generic_source_label_alignment_build_design": valid,
            "external_protocol_or_forward": False,
            "postfreeze_quality_or_truth": False,
            "deepwidebench_forward_or_evaluator": False,
            "leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_rerun": False,
        }
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.70 diagnosis drifted")
    return copied


def _publish(value: Mapping[str, Any]) -> None:
    path = ROOT / OUTPUT
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_diagnosis()
    if value["findings"]:
        raise RuntimeError(value["findings"])
    _publish(value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": value["audit_valid"], "diagnosis": value["diagnosis"], "authorization": value["authorization"]}, sort_keys=True))


if __name__ == "__main__":
    main()
