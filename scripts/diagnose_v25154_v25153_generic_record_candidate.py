#!/usr/bin/env python3
"""Counts-only diagnosis of the frozen V2.51.53 generic-record NO-GO.

Only terminal booleans and the sealed V2.51.51/V2.51.35 content-free
receipts are decoded. Task identity, question, queries, URLs, pages, values,
parent payloads, predictions, mapping/gold/evaluator rows, scores, and
credentials remain opaque JSON ranges and are never emitted.
"""

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

from deepwide_agent import v25135_sparse_production_runtime as sparse  # noqa: E402
from deepwide_agent import v25151_generic_record_quote_candidate_runtime as generic  # noqa: E402
from deepwide_agent import v25153_generic_record_candidate_external_contract as contract  # noqa: E402
from scripts import diagnose_v25146_v25145_quote_attested as scanner  # noqa: E402
from scripts import run_v25153_generic_record_candidate_external as runner  # noqa: E402


DATE = "20260812"
ROLE = "v25154_v25153_generic_record_candidate_counts_only_diagnosis"
OUTPUT = Path(
    f"results/v25154_v25153_generic_record_candidate_diagnosis_v1_{DATE}.json"
)
FUTURE_SURFACES = (
    contract.EVALUATOR,
    contract.EVALUATOR_TEST,
    contract.EVALUATOR_PROTOCOL,
    contract.RESULT,
    contract.POSTAUDIT,
    contract.POSTFREEZE_GOLD,
)
GRAMMAR_COUNTS = (
    "bound_json_record_observation_count",
    "pipe_table_observation_count",
    "flat_json_object_observation_count",
    "inline_labelled_record_observation_count",
    "multiline_labelled_record_observation_count",
    "heading_labelled_record_observation_count",
)
FAILED_CHECKS = [
    "minimum_attributable_prediction_changed",
    "minimum_candidate_availability_selection_and_reverified_application",
    "verified_gain_range",
]


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.51.54 expected ordinary repository file")
    return path


def _absent(relative: Path) -> bool:
    path = ROOT / relative
    return not path.exists() and not path.is_symlink()


def safe_row(line: str) -> dict[str, Any]:
    """Decode only the two sealed content-free receipts and safe booleans."""

    top, raw = scanner._members(
        line,
        expected=scanner.EXPECTED_TOP,
        decode=scanner.SAFE_TOP - {"parent_result"},
        raw=frozenset({"parent_result"}),
    )
    parent, _ = scanner._members(
        raw["parent_result"],
        expected=scanner.PARENT_EXPECTED,
        decode=frozenset({"content_free_receipt"}),
    )
    outer = generic.validate_receipt(top["content_free_receipt"])
    inner = sparse.validate_receipt(parent["content_free_receipt"])
    if (
        top["runtime_completed"] is not True
        or top["failure_as_zero"] is not False
        or top["entropy_or_information_gain_assigns_signed_credit"] is not False
        or top[
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        ]
        is not False
        or outer["parent_revision_eligible"] is not inner["revision_eligible"]
        or outer["parent_revision_failure_present"]
        is not inner["revision_failure_present"]
    ):
        raise RuntimeError("V2.51.54 content-free cross-binding drifted")
    return {"outer": outer, "inner": inner}


def _safe_rows() -> list[dict[str, Any]]:
    rows = [
        safe_row(line)
        for line in _ordinary(contract.TASK_ROWS)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.51.54 fixed denominator drifted")
    return rows


def _hist(values: Sequence[int]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _read_json(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.54 expected JSON object")
    return value


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    forward = runner.validate_forward_result(_read_json(contract.FORWARD_RESULT))
    audit = _read_json(contract.FORWARD_AUDIT)
    if (
        not contract.sealed(audit, "audit_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("forward_result_sha256")
        != contract.sha256(_ordinary(contract.FORWARD_RESULT))
        or audit.get("task_rows_sha256")
        != contract.sha256(_ordinary(contract.TASK_ROWS))
        or forward.get("mechanism_decision", {}).get("failed_checks")
        != FAILED_CHECKS
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_implementation_and_protocol"
        )
        is not False
        or not all(_absent(path) for path in FUTURE_SURFACES)
    ):
        raise RuntimeError("V2.51.54 frozen parent barrier drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, _audit = _validate_parents()
    rows = _safe_rows()
    outer = [row["outer"] for row in rows]
    inner = [row["inner"] for row in rows]
    revised = [value for value in outer if value["candidate_revision_entry_count"]]

    funnel: dict[str, Any] = {
        "task_count": len(rows),
        "verified_gain_tasks": sum(
            value["verified_source_identity_field_gain"] for value in inner
        ),
        "target_field_page_gain_histogram": _hist(
            [value["target_field_page_gain"] for value in inner]
        ),
        "target_field_pair_gain_histogram": _hist(
            [value["target_field_pair_gain"] for value in inner]
        ),
        "complete_target_field_page_gain_histogram": _hist(
            [value["complete_target_field_page_gain"] for value in inner]
        ),
        "candidate_revision_tasks": len(revised),
        "verified_incremental_page_count_histogram": _hist(
            [value["verified_incremental_page_count"] for value in revised]
        ),
        "verified_incremental_page_total": sum(
            value["verified_incremental_page_count"] for value in revised
        ),
        "candidate_source_page_count_histogram": _hist(
            [value["candidate_source_page_count"] for value in revised]
        ),
        "candidate_source_page_total": sum(
            value["candidate_source_page_count"] for value in revised
        ),
        "candidate_quote_character_total": sum(
            value["candidate_quote_character_count"] for value in revised
        ),
        "original_candidate_prompt_character_total": sum(
            value["original_candidate_prompt_character_count"] for value in revised
        ),
        "candidate_prompt_character_total": sum(
            value["candidate_prompt_character_count"] for value in revised
        ),
        "selector_prompt_built_tasks": sum(
            value["selector_prompt_built"] for value in revised
        ),
        "strict_json_tasks": sum(
            value["selection_response_strict_json"] for value in revised
        ),
        "projection_valid_tasks": sum(
            value["candidate_projection_valid"] for value in revised
        ),
        "projection_failure_tasks": sum(
            value["projection_failure_present"] for value in revised
        ),
        "provider_failure_tasks": sum(
            value["provider_failure_present"] for value in revised
        ),
        "parent_post_effect_failure_tasks": sum(
            value["parent_post_effect_failure_present"] for value in revised
        ),
        "final_prediction_changed_tasks": sum(
            value["final_prediction_changed_from_production"] for value in revised
        ),
        "conflicting_candidate_total": sum(
            value["conflicting_candidate_count"] for value in revised
        ),
        "duplicate_candidate_total": sum(
            value["duplicate_candidate_count"] for value in revised
        ),
        "truncated_candidate_total": sum(
            value["truncated_candidate_count"] for value in revised
        ),
        "rejected_selected_edit_total": sum(
            value["rejected_selected_edit_count"] for value in revised
        ),
    }
    for name in GRAMMAR_COUNTS + (
        "raw_candidate_observation_count",
        "verifier_admissible_candidate_count",
        "available_candidate_count",
        "supplied_candidate_count",
        "selected_candidate_count",
        "applied_edit_count",
    ):
        funnel[f"{name}_histogram"] = _hist([value[name] for value in revised])
        funnel[f"{name}_total"] = sum(value[name] for value in revised)

    expected = {
        "task_count": 20,
        "verified_gain_tasks": 2,
        "target_field_page_gain_histogram": {"-1": 2, "0": 16, "1": 2},
        "target_field_pair_gain_histogram": {
            "-1": 2,
            "-2": 1,
            "-3": 1,
            "-4": 1,
            "-5": 1,
            "0": 13,
            "1": 1,
        },
        "complete_target_field_page_gain_histogram": {"-1": 3, "-2": 2, "0": 15},
        "candidate_revision_tasks": 2,
        "verified_incremental_page_count_histogram": {"1": 1, "2": 1},
        "verified_incremental_page_total": 3,
        "candidate_source_page_count_histogram": {"0": 2},
        "candidate_source_page_total": 0,
        "candidate_quote_character_total": 0,
        "original_candidate_prompt_character_total": 46188,
        "candidate_prompt_character_total": 3423,
        "selector_prompt_built_tasks": 2,
        "strict_json_tasks": 2,
        "projection_valid_tasks": 2,
        "projection_failure_tasks": 0,
        "provider_failure_tasks": 0,
        "parent_post_effect_failure_tasks": 0,
        "final_prediction_changed_tasks": 0,
        "conflicting_candidate_total": 0,
        "duplicate_candidate_total": 0,
        "truncated_candidate_total": 0,
        "rejected_selected_edit_total": 0,
    }
    for name in GRAMMAR_COUNTS + (
        "raw_candidate_observation_count",
        "verifier_admissible_candidate_count",
        "available_candidate_count",
        "supplied_candidate_count",
        "selected_candidate_count",
        "applied_edit_count",
    ):
        expected[f"{name}_histogram"] = {"0": 2}
        expected[f"{name}_total"] = 0
    if funnel != expected:
        raise RuntimeError("V2.51.54 content-free funnel drifted")

    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": contract.sha256(
                _ordinary(contract.FORWARD_RESULT)
            ),
            "forward_audit_sha256": contract.sha256(
                _ordinary(contract.FORWARD_AUDIT)
            ),
            "prediction_freeze_sha256": contract.sha256(
                _ordinary(contract.PREDICTION_FREEZE)
            ),
            "task_rows_sha256": contract.sha256(_ordinary(contract.TASK_ROWS)),
            "audit_valid": True,
            "mechanism_gate_passed": False,
            "failed_checks": list(FAILED_CHECKS),
        },
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_funnel": funnel,
        "diagnosis": {
            "verified_retrieval_gain_natural_reach_exists_but_is_below_preregistered_range": True,
            "three_verified_incremental_pages_reached_candidate_extractor": True,
            "all_six_generic_record_grammar_observation_counts_are_zero": True,
            "zero_candidates_reached_preverification_conflict_deduplication_truncation_or_selection": True,
            "selector_transport_strict_json_and_empty_projection_are_reliable": True,
            "current_receipts_cannot_distinguish_raw_page_structure_absence_from_fetch_or_projection_structure_loss": True,
            "adding_more_record_grammar_without_a_layer_local_observer_is_not_authorized": True,
            "next_build_only_candidate_should_compare_content_free_preprojection_and_postprojection_structure_signals": True,
            "observer_must_not_decode_or_emit_identity_question_url_page_value_or_prediction": True,
            "same_page_source_identity_field_value_binding_and_selected_edit_reverification_remain_mandatory": True,
            "query_fetch_model_context_token_wall_and_network_caps_must_not_expand": True,
            "quality_effect_is_unknown_because_evaluator_remains_forbidden": True,
            "v25153_population_must_not_be_retried_resumed_or_reused": True,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "benchmark_status": {
            "latest_normal_complete_run": "v25057_page_self_exact220_r2",
            "latest_normal_complete_exact_over_220": 6,
            "latest_normal_complete_composite": 0.4499596032520462,
            "latest_complete_but_severely_degraded_run": "v25130_causal_salience_exact220",
            "latest_complete_but_severely_degraded_exact_over_220": 1,
            "latest_complete_but_severely_degraded_composite": 0.3778654237910814,
            "best_observed_single_rollout_run": "v24857_pacing_aware_exact220",
            "best_observed_single_rollout_exact_over_220": 9,
            "best_observed_single_rollout_composite": 0.45724897824812605,
            "avg_at_4": False,
            "leaderboard_submitted": False,
            "sota": False,
        },
        "content_policy": {
            "decoded_surfaces": [
                "terminal_booleans",
                "v25151_content_free_generic_record_quote_candidate_receipt",
                "v25135_content_free_sparse_production_receipt",
            ],
            "opaque_id_question_query_url_title_page_value_prediction_answer_mapping_gold_category_split_evaluator_score_credential_decoded": False,
            "disallowed_members_scanned_only_to_find_json_boundaries": True,
            "network_model_search_fetch_process_or_evaluator_effect": False,
        },
        "authorization": {
            "pre_post_projection_content_free_observer_build_only": True,
            "additional_record_grammar_build": False,
            "new_external_protocol_or_launch": False,
            "v25153_evaluator_or_quality_result": False,
            "v25153_retry_resume_or_population_reuse": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        },
        "findings": [],
        "diagnosis_valid": True,
    }
    value["diagnosis_payload_sha256"] = contract.payload_sha256(value)
    return validate_diagnosis(value)


def validate_diagnosis(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("diagnosis_payload_sha256", None)
    funnel = copied.get("content_free_funnel") or {}
    diagnosis = copied.get("diagnosis") or {}
    benchmark = copied.get("benchmark_status") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("parents", {}).get("audit_valid") is not True
        or copied.get("parents", {}).get("mechanism_gate_passed") is not False
        or copied.get("parents", {}).get("failed_checks") != FAILED_CHECKS
        or funnel.get("verified_gain_tasks") != 2
        or funnel.get("candidate_revision_tasks") != 2
        or funnel.get("verified_incremental_page_total") != 3
        or any(funnel.get(f"{name}_total") != 0 for name in GRAMMAR_COUNTS)
        or funnel.get("raw_candidate_observation_count_total") != 0
        or funnel.get("available_candidate_count_total") != 0
        or funnel.get("selected_candidate_count_total") != 0
        or funnel.get("applied_edit_count_total") != 0
        or diagnosis.get(
            "current_receipts_cannot_distinguish_raw_page_structure_absence_from_fetch_or_projection_structure_loss"
        )
        is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or benchmark
        != {
            "latest_normal_complete_run": "v25057_page_self_exact220_r2",
            "latest_normal_complete_exact_over_220": 6,
            "latest_normal_complete_composite": 0.4499596032520462,
            "latest_complete_but_severely_degraded_run": "v25130_causal_salience_exact220",
            "latest_complete_but_severely_degraded_exact_over_220": 1,
            "latest_complete_but_severely_degraded_composite": 0.3778654237910814,
            "best_observed_single_rollout_run": "v24857_pacing_aware_exact220",
            "best_observed_single_rollout_exact_over_220": 9,
            "best_observed_single_rollout_composite": 0.45724897824812605,
            "avg_at_4": False,
            "leaderboard_submitted": False,
            "sota": False,
        }
        or authorization
        != {
            "pre_post_projection_content_free_observer_build_only": True,
            "additional_record_grammar_build": False,
            "new_external_protocol_or_launch": False,
            "v25153_evaluator_or_quality_result": False,
            "v25153_retry_resume_or_population_reuse": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        }
        or copied.get("findings") != []
        or copied.get("diagnosis_valid") is not True
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.54 diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
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
    print(json.dumps({"path": str(OUTPUT), "role": ROLE}, sort_keys=True))


if __name__ == "__main__":
    main()
