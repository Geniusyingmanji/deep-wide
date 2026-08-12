#!/usr/bin/env python3
"""Counts-only diagnosis of the frozen V2.51.45 quote-attested NO-GO.

Only terminal booleans plus the sealed V2.51.43 and V2.51.35 content-free
receipts are decoded. Task identity, question, queries, URLs, pages, parent
payloads, predictions, mapping/gold/evaluator rows, scores, and credentials are
skipped as opaque JSON character ranges and never emitted.
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
from deepwide_agent import v25143_quote_attested_cell_edit_runtime as quote  # noqa: E402
from deepwide_agent import v25145_quote_attested_external_contract as contract  # noqa: E402
from scripts import diagnose_v25008_v25007_detail_field_link_phase as scanner  # noqa: E402
from scripts import run_v25145_quote_attested_external as runner  # noqa: E402


DATE = "20260812"
ROLE = "v25146_v25145_quote_attested_counts_only_diagnosis"
OUTPUT = Path(
    f"results/v25146_v25145_quote_attested_diagnosis_v1_{DATE}.json"
)
SAFE_TOP = frozenset(
    {
        "runtime_completed",
        "failure_as_zero",
        "content_free_receipt",
        "parent_result",
        "entropy_or_information_gain_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
    }
)
EXPECTED_TOP = frozenset(
    {
        "actual_effect_snapshot",
        "artifact_version",
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions",
        "content_free_receipt",
        "cost",
        "effect_health",
        "elapsed_seconds",
        "entropy_or_information_gain_assigns_signed_credit",
        "failure_as_zero",
        "failure_types",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "opaque_id",
        "outer_failure_type",
        "parent_result",
        "parent_result_payload_sha256",
        "prediction_kind",
        "prediction_sha256",
        "predictions",
        "protocol_id",
        "result_payload_sha256",
        "retry_resume_skip_population_replacement_or_selective_rerun",
        "role",
        "runtime_completed",
        "runtime_input_keys",
        "runtime_result_payload_sha256",
        "terminal",
    }
)
PARENT_EXPECTED = frozenset(
    {
        "artifact_version",
        "benchmark_launch_or_evaluator_authorized",
        "content_free_receipt",
        "cost",
        "entropy_or_information_gain_assigns_signed_credit",
        "failure_types",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "opaque_id",
        "parent_result",
        "parent_result_payload_sha256",
        "policy_id",
        "prediction",
        "prediction_kind",
        "prediction_sha256",
        "production_prediction",
        "production_prediction_sha256",
        "result_payload_sha256",
        "role",
        "status",
    }
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
        raise RuntimeError("V2.51.46 expected ordinary repository file")
    return path


def _absent(relative: Path) -> bool:
    path = ROOT / relative
    return not path.exists() and not path.is_symlink()


def _members(
    text: str,
    *,
    expected: frozenset[str],
    decode: frozenset[str],
    raw: frozenset[str] = frozenset(),
) -> tuple[dict[str, Any], dict[str, str]]:
    index = scanner._skip_ws(text, 0)
    if index >= len(text) or text[index] != "{":
        raise ValueError("V2.51.46 expected JSON object")
    index += 1
    decoder = json.JSONDecoder()
    names: set[str] = set()
    decoded: dict[str, Any] = {}
    raw_values: dict[str, str] = {}
    while True:
        index = scanner._skip_ws(text, index)
        if index < len(text) and text[index] == "}":
            index += 1
            break
        name, name_end = decoder.raw_decode(text, index)
        if not isinstance(name, str) or name in names:
            raise ValueError("V2.51.46 duplicate or invalid member")
        names.add(name)
        index = scanner._skip_ws(text, name_end)
        if index >= len(text) or text[index] != ":":
            raise ValueError("V2.51.46 member separator drifted")
        start = scanner._skip_ws(text, index + 1)
        end = scanner._scan_value(text, start)
        if name in decode:
            decoded[name] = json.loads(text[start:end])
        if name in raw:
            raw_values[name] = text[start:end]
        index = scanner._skip_ws(text, end)
        if index < len(text) and text[index] == ",":
            index += 1
            continue
        if index < len(text) and text[index] == "}":
            index += 1
            break
        raise ValueError("V2.51.46 member delimiter drifted")
    if (
        scanner._skip_ws(text, index) != len(text)
        or names != expected
        or set(decoded) != decode
        or set(raw_values) != raw
    ):
        raise ValueError("V2.51.46 object schema drifted")
    return decoded, raw_values


def safe_row(line: str) -> dict[str, Any]:
    top, raw = _members(
        line,
        expected=EXPECTED_TOP,
        decode=SAFE_TOP - {"parent_result"},
        raw=frozenset({"parent_result"}),
    )
    parent, _ = _members(
        raw["parent_result"],
        expected=PARENT_EXPECTED,
        decode=frozenset({"content_free_receipt"}),
    )
    outer = quote.validate_receipt(top["content_free_receipt"])
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
        raise RuntimeError("V2.51.46 content-free cross-binding drifted")
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
        raise RuntimeError("V2.51.46 fixed denominator drifted")
    return rows


def _hist(values: Sequence[int]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _read_json(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.46 expected JSON object")
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
        != [
            "minimum_attributable_prediction_changed",
            "minimum_quote_attested_projection_applied",
        ]
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_implementation_and_protocol"
        )
        is not False
        or not all(_absent(path) for path in FUTURE_SURFACES)
    ):
        raise RuntimeError("V2.51.46 frozen parent barrier drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, _audit = _validate_parents()
    rows = _safe_rows()
    outer = [row["outer"] for row in rows]
    inner = [row["inner"] for row in rows]
    revised = [value for value in outer if value["cell_edit_revision_entry_count"]]
    rejection_totals = {
        name: sum(value["rejection_counts"][name] for value in revised)
        for name in quote._REJECTION_NAMES
    }
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
        "cell_edit_revision_tasks": len(revised),
        "verified_incremental_page_count_histogram": _hist(
            [value["verified_incremental_page_count"] for value in revised]
        ),
        "supplied_incremental_page_count_histogram": _hist(
            [value["supplied_incremental_page_count"] for value in revised]
        ),
        "verified_incremental_page_total": sum(
            value["verified_incremental_page_count"] for value in revised
        ),
        "supplied_incremental_page_total": sum(
            value["supplied_incremental_page_count"] for value in revised
        ),
        "supplied_incremental_evidence_character_total": sum(
            value["supplied_incremental_evidence_character_count"]
            for value in revised
        ),
        "original_candidate_prompt_character_total": sum(
            value["original_candidate_prompt_character_count"] for value in revised
        ),
        "cell_edit_prompt_character_total": sum(
            value["cell_edit_prompt_character_count"] for value in revised
        ),
        "strict_json_tasks": sum(
            value["edit_response_strict_json"] for value in revised
        ),
        "projection_valid_tasks": sum(
            value["edit_projection_valid"] for value in revised
        ),
        "model_edit_count_histogram": _hist(
            [value["model_edit_count"] for value in revised]
        ),
        "parsed_edit_count_histogram": _hist(
            [value["parsed_edit_count"] for value in revised]
        ),
        "quote_attested_edit_count_histogram": _hist(
            [value["quote_attested_edit_count"] for value in revised]
        ),
        "applied_edit_count_histogram": _hist(
            [value["applied_edit_count"] for value in revised]
        ),
        "model_edit_total": sum(value["model_edit_count"] for value in revised),
        "quote_attested_edit_total": sum(
            value["quote_attested_edit_count"] for value in revised
        ),
        "applied_edit_total": sum(
            value["applied_edit_count"] for value in revised
        ),
        "rejected_edit_total": sum(
            value["rejected_edit_count"] for value in revised
        ),
        "rejection_totals": rejection_totals,
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
    }
    expected = {
        "task_count": 20,
        "verified_gain_tasks": 7,
        "target_field_page_gain_histogram": {"0": 13, "1": 4, "2": 1, "3": 2},
        "target_field_pair_gain_histogram": {"0": 13, "1": 4, "3": 1, "4": 1, "5": 1},
        "complete_target_field_page_gain_histogram": {"0": 19, "1": 1},
        "cell_edit_revision_tasks": 7,
        "verified_incremental_page_count_histogram": {"1": 4, "3": 3},
        "supplied_incremental_page_count_histogram": {"1": 4, "3": 3},
        "verified_incremental_page_total": 13,
        "supplied_incremental_page_total": 13,
        "supplied_incremental_evidence_character_total": 54035,
        "original_candidate_prompt_character_total": 309987,
        "cell_edit_prompt_character_total": 71147,
        "strict_json_tasks": 7,
        "projection_valid_tasks": 7,
        "model_edit_count_histogram": {"0": 7},
        "parsed_edit_count_histogram": {"0": 7},
        "quote_attested_edit_count_histogram": {"0": 7},
        "applied_edit_count_histogram": {"0": 7},
        "model_edit_total": 0,
        "quote_attested_edit_total": 0,
        "applied_edit_total": 0,
        "rejected_edit_total": 0,
        "rejection_totals": {name: 0 for name in quote._REJECTION_NAMES},
        "projection_failure_tasks": 0,
        "provider_failure_tasks": 0,
        "parent_post_effect_failure_tasks": 0,
        "final_prediction_changed_tasks": 0,
    }
    if funnel != expected:
        raise RuntimeError("V2.51.46 content-free funnel drifted")
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
            "failed_checks": [
                "minimum_attributable_prediction_changed",
                "minimum_quote_attested_projection_applied",
            ],
        },
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_funnel": funnel,
        "diagnosis": {
            "retrieval_field_gain_natural_reach_exists": True,
            "production_conditioning_prompt_transport_strict_json_and_projection_are_reliable": True,
            "all_seven_cell_edit_responses_explicitly_returned_empty_edits": True,
            "verifier_did_not_reject_any_proposed_edit": True,
            "primary_bottleneck_is_edit_proposal_recall_not_verifier_precision": True,
            "field_name_page_gain_does_not_guarantee_quoteable_row_field_value_sentence": True,
            "candidate_delta_projection_may_remove_the_raw_contiguous_quote_needed_by_the_edit_model": True,
            "next_build_only_candidate_should_supply_deterministically_extracted_quote_candidates_before_model_edit_selection": True,
            "deterministic_quote_candidates_must_be_same_page_source_row_field_value_bound_and_content_exact": True,
            "model_should_select_or_abstain_over_verified_quote_candidates_not_copy_arbitrary_page_text": True,
            "query_fetch_model_context_token_wall_and_network_caps_must_not_expand": True,
            "quality_effect_is_unknown_because_evaluator_remains_forbidden": True,
            "v25145_population_must_not_be_retried_resumed_or_reused": True,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "decoded_surfaces": [
                "terminal_booleans",
                "v25143_content_free_quote_attested_cell_edit_receipt",
                "v25135_content_free_sparse_production_receipt",
            ],
            "opaque_id_question_query_url_title_page_value_prediction_answer_mapping_gold_category_split_evaluator_score_credential_decoded": False,
            "disallowed_members_scanned_only_to_find_json_boundaries": True,
            "network_model_search_fetch_process_or_evaluator_effect": False,
        },
        "authorization": {
            "deterministic_quote_candidate_successor_build_only": True,
            "new_external_protocol_or_launch": False,
            "v25145_evaluator_or_quality_result": False,
            "v25145_retry_resume_or_population_reuse": False,
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
        or funnel.get("verified_gain_tasks") != 7
        or funnel.get("cell_edit_revision_tasks") != 7
        or funnel.get("strict_json_tasks") != 7
        or funnel.get("projection_valid_tasks") != 7
        or funnel.get("model_edit_total") != 0
        or funnel.get("rejected_edit_total") != 0
        or diagnosis.get(
            "primary_bottleneck_is_edit_proposal_recall_not_verifier_precision"
        )
        is not True
        or diagnosis.get(
            "all_seven_cell_edit_responses_explicitly_returned_empty_edits"
        )
        is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or authorization
        != {
            "deterministic_quote_candidate_successor_build_only": True,
            "new_external_protocol_or_launch": False,
            "v25145_evaluator_or_quality_result": False,
            "v25145_retry_resume_or_population_reuse": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        }
        or copied.get("findings") != []
        or copied.get("diagnosis_valid") is not True
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.46 diagnosis drifted")
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
