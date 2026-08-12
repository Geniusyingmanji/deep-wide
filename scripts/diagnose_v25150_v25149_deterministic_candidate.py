#!/usr/bin/env python3
"""Counts-only diagnosis of the frozen V2.51.49 deterministic-candidate NO-GO.

Only terminal booleans and the sealed V2.51.47/V2.51.35 content-free receipts
are decoded.  Task identity, question, queries, URLs, pages, parent payloads,
predictions, mapping/gold/evaluator rows, scores, and credentials remain opaque
JSON ranges and are never emitted.
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
from deepwide_agent import v25147_deterministic_quote_candidate_runtime as candidate  # noqa: E402
from deepwide_agent import v25149_deterministic_candidate_external_contract as contract  # noqa: E402
from scripts import diagnose_v25146_v25145_quote_attested as scanner  # noqa: E402
from scripts import run_v25149_deterministic_candidate_external as runner  # noqa: E402


DATE = "20260812"
ROLE = "v25150_v25149_deterministic_candidate_counts_only_diagnosis"
OUTPUT = Path(
    f"results/v25150_v25149_deterministic_candidate_diagnosis_v1_{DATE}.json"
)
FUTURE_SURFACES = (
    contract.EVALUATOR,
    contract.EVALUATOR_TEST,
    contract.EVALUATOR_PROTOCOL,
    contract.RESULT,
    contract.POSTAUDIT,
    contract.POSTFREEZE_GOLD,
)


def _ordinary(relative: Path) -> Path:
    path = ROOT / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.51.50 expected ordinary repository file")
    return path


def _absent(relative: Path) -> bool:
    path = ROOT / relative
    return not path.exists() and not path.is_symlink()


def safe_row(line: str) -> dict[str, Any]:
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
    outer = candidate.validate_receipt(top["content_free_receipt"])
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
        raise RuntimeError("V2.51.50 content-free cross-binding drifted")
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
        raise RuntimeError("V2.51.50 fixed denominator drifted")
    return rows


def _hist(values: Sequence[int]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _read_json(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.50 expected JSON object")
    return value


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    forward = runner.validate_forward_result(_read_json(contract.FORWARD_RESULT))
    audit = _read_json(contract.FORWARD_AUDIT)
    failed = [
        "minimum_attributable_prediction_changed",
        "minimum_candidate_availability_selection_and_reverified_application",
    ]
    if (
        not contract.sealed(audit, "audit_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("forward_result_sha256")
        != contract.sha256(_ordinary(contract.FORWARD_RESULT))
        or audit.get("task_rows_sha256")
        != contract.sha256(_ordinary(contract.TASK_ROWS))
        or forward.get("mechanism_decision", {}).get("failed_checks") != failed
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_implementation_and_protocol"
        )
        is not False
        or not all(_absent(path) for path in FUTURE_SURFACES)
    ):
        raise RuntimeError("V2.51.50 frozen parent barrier drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, _audit = _validate_parents()
    rows = _safe_rows()
    outer = [row["outer"] for row in rows]
    inner = [row["inner"] for row in rows]
    revised = [value for value in outer if value["candidate_revision_entry_count"]]
    funnel = {
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
        "json_record_observation_count_histogram": _hist(
            [value["json_record_observation_count"] for value in revised]
        ),
        "pipe_span_observation_count_histogram": _hist(
            [value["pipe_span_observation_count"] for value in revised]
        ),
        "raw_candidate_observation_count_histogram": _hist(
            [value["raw_candidate_observation_count"] for value in revised]
        ),
        "verifier_admissible_candidate_count_histogram": _hist(
            [value["verifier_admissible_candidate_count"] for value in revised]
        ),
        "available_candidate_count_histogram": _hist(
            [value["available_candidate_count"] for value in revised]
        ),
        "supplied_candidate_count_histogram": _hist(
            [value["supplied_candidate_count"] for value in revised]
        ),
        "selected_candidate_count_histogram": _hist(
            [value["selected_candidate_count"] for value in revised]
        ),
        "applied_edit_count_histogram": _hist(
            [value["applied_edit_count"] for value in revised]
        ),
        "raw_candidate_observation_total": sum(
            value["raw_candidate_observation_count"] for value in revised
        ),
        "verifier_admissible_candidate_total": sum(
            value["verifier_admissible_candidate_count"] for value in revised
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
        "available_candidate_total": sum(
            value["available_candidate_count"] for value in revised
        ),
        "supplied_candidate_total": sum(
            value["supplied_candidate_count"] for value in revised
        ),
        "selected_candidate_total": sum(
            value["selected_candidate_count"] for value in revised
        ),
        "applied_edit_total": sum(value["applied_edit_count"] for value in revised),
        "rejected_selected_edit_total": sum(
            value["rejected_selected_edit_count"] for value in revised
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
        "original_candidate_prompt_character_total": sum(
            value["original_candidate_prompt_character_count"] for value in revised
        ),
        "candidate_prompt_character_total": sum(
            value["candidate_prompt_character_count"] for value in revised
        ),
        "candidate_quote_character_total": sum(
            value["candidate_quote_character_count"] for value in revised
        ),
    }
    expected = {
        "task_count": 20,
        "verified_gain_tasks": 5,
        "target_field_page_gain_histogram": {"-1": 1, "0": 14, "1": 3, "2": 2},
        "target_field_pair_gain_histogram": {"-1": 1, "-5": 1, "0": 13, "1": 3, "2": 2},
        "complete_target_field_page_gain_histogram": {"-2": 1, "0": 19},
        "candidate_revision_tasks": 5,
        "verified_incremental_page_count_histogram": {"1": 3, "2": 2},
        "verified_incremental_page_total": 7,
        "json_record_observation_count_histogram": {"0": 5},
        "pipe_span_observation_count_histogram": {"0": 5},
        "raw_candidate_observation_count_histogram": {"0": 5},
        "verifier_admissible_candidate_count_histogram": {"0": 5},
        "available_candidate_count_histogram": {"0": 5},
        "supplied_candidate_count_histogram": {"0": 5},
        "selected_candidate_count_histogram": {"0": 5},
        "applied_edit_count_histogram": {"0": 5},
        "raw_candidate_observation_total": 0,
        "verifier_admissible_candidate_total": 0,
        "conflicting_candidate_total": 0,
        "duplicate_candidate_total": 0,
        "truncated_candidate_total": 0,
        "available_candidate_total": 0,
        "supplied_candidate_total": 0,
        "selected_candidate_total": 0,
        "applied_edit_total": 0,
        "rejected_selected_edit_total": 0,
        "selector_prompt_built_tasks": 5,
        "strict_json_tasks": 5,
        "projection_valid_tasks": 5,
        "projection_failure_tasks": 0,
        "provider_failure_tasks": 0,
        "parent_post_effect_failure_tasks": 0,
        "final_prediction_changed_tasks": 0,
        "original_candidate_prompt_character_total": 188650,
        "candidate_prompt_character_total": 8520,
        "candidate_quote_character_total": 0,
    }
    if funnel != expected:
        raise RuntimeError("V2.51.50 content-free funnel drifted")
    failed = [
        "minimum_attributable_prediction_changed",
        "minimum_candidate_availability_selection_and_reverified_application",
    ]
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
            "failed_checks": failed,
        },
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_funnel": funnel,
        "diagnosis": {
            "verified_retrieval_gain_natural_reach_exists": True,
            "seven_verified_incremental_pages_reached_candidate_extractor": True,
            "atomic_json_and_pipe_span_observation_recall_is_zero": True,
            "zero_candidates_reached_preverification_conflict_deduplication_truncation_or_selection": True,
            "selector_transport_strict_json_and_empty_projection_are_reliable": True,
            "primary_bottleneck_is_representation_grammar_recall_before_verifier_or_selector": True,
            "current_receipts_do_not_identify_which_unmatched_page_representation_is_present": True,
            "next_build_only_candidate_may_add_generic_exact_quote_record_grammars_but_must_not_infer_from_frozen_content": True,
            "same_page_identity_field_value_binding_and_selected_edit_reverification_remain_mandatory": True,
            "query_fetch_model_context_token_wall_and_network_caps_must_not_expand": True,
            "quality_effect_is_unknown_because_evaluator_remains_forbidden": True,
            "v25149_population_must_not_be_retried_resumed_or_reused": True,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "decoded_surfaces": [
                "terminal_booleans",
                "v25147_content_free_deterministic_quote_candidate_receipt",
                "v25135_content_free_sparse_production_receipt",
            ],
            "opaque_id_question_query_url_title_page_value_prediction_answer_mapping_gold_category_split_evaluator_score_credential_decoded": False,
            "disallowed_members_scanned_only_to_find_json_boundaries": True,
            "network_model_search_fetch_process_or_evaluator_effect": False,
        },
        "authorization": {
            "generic_record_grammar_successor_build_only": True,
            "new_external_protocol_or_launch": False,
            "v25149_evaluator_or_quality_result": False,
            "v25149_retry_resume_or_population_reuse": False,
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
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("parents", {}).get("audit_valid") is not True
        or copied.get("parents", {}).get("mechanism_gate_passed") is not False
        or funnel.get("verified_gain_tasks") != 5
        or funnel.get("candidate_revision_tasks") != 5
        or funnel.get("verified_incremental_page_total") != 7
        or funnel.get("raw_candidate_observation_total") != 0
        or funnel.get("available_candidate_total") != 0
        or funnel.get("selected_candidate_total") != 0
        or funnel.get("applied_edit_total") != 0
        or diagnosis.get(
            "primary_bottleneck_is_representation_grammar_recall_before_verifier_or_selector"
        )
        is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or authorization
        != {
            "generic_record_grammar_successor_build_only": True,
            "new_external_protocol_or_launch": False,
            "v25149_evaluator_or_quality_result": False,
            "v25149_retry_resume_or_population_reuse": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        }
        or copied.get("findings") != []
        or copied.get("diagnosis_valid") is not True
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.50 diagnosis drifted")
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
