#!/usr/bin/env python3
"""Counts-only phase diagnosis of the frozen V2.50.07 external gate.

The diagnosis consumes only already-audited, content-free receipts. The
task-results file also contains opaque identifiers and predictions, so this
module uses a small top-level JSON scanner: disallowed member values are
skipped as opaque character ranges and are never JSON-decoded, hashed, compared, or
emitted. No question, query, URL, page, anchor, record value, prediction,
answer, gold, evaluator row, credential, or task identity enters the report.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24999_shared_response_selection_runtime as prior99  # noqa: E402
from deepwide_agent import v25001_page_visible_link_selection as selector  # noqa: E402
from deepwide_agent import v25002_page_visible_link_paired_runtime as paired  # noqa: E402
from deepwide_agent import v25007_detail_field_link_external_contract as contract  # noqa: E402


DATE = "20260809"
ROLE = "v25008_v25007_counts_only_detail_field_link_phase_diagnosis"
OUTPUT = Path(
    f"results/v25008_v25007_detail_field_link_phase_diagnosis_v1_{DATE}.json"
)
SOURCE = Path("scripts/diagnose_v25008_v25007_detail_field_link_phase.py")
TEST = Path("tests/test_diagnose_v25008_v25007_detail_field_link_phase.py")
SAFE_MEMBERS = frozenset(
    {"content_free_receipt", "selection_receipt", "physical_wave_receipts"}
)
EXPECTED_TOP_LEVEL_MEMBERS = frozenset(
    {
        "artifact_version",
        "benchmark_launch_or_evaluator_authorized",
        "content_free_receipt",
        "cost",
        "evidence_characters",
        "failure_types",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "model_success",
        "opaque_id",
        "physical_effects",
        "physical_wave_receipts",
        "policy_id",
        "prediction_changed",
        "predictions",
        "result_payload_sha256",
        "role",
        "selection_receipt",
        "status",
    }
)
FUTURE_SURFACES = (
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
        raise RuntimeError(f"V2.50.08 expected ordinary repository file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.08 expected JSON object")
    return value


def _absent(relative: Path) -> bool:
    path = ROOT / relative
    return not path.exists() and not path.is_symlink()


def _skip_ws(text: str, index: int) -> int:
    while index < len(text) and text[index] in " \t\r\n":
        index += 1
    return index


def _scan_string(text: str, index: int) -> int:
    if index >= len(text) or text[index] != '"':
        raise ValueError("V2.50.08 JSON string boundary drifted")
    index += 1
    escaped = False
    while index < len(text):
        character = text[index]
        if escaped:
            escaped = False
        elif character == "\\":
            escaped = True
        elif character == '"':
            return index + 1
        index += 1
    raise ValueError("V2.50.08 unterminated JSON string")


def _scan_value(text: str, index: int) -> int:
    index = _skip_ws(text, index)
    if index >= len(text):
        raise ValueError("V2.50.08 missing JSON value")
    if text[index] == '"':
        return _scan_string(text, index)
    if text[index] in "[{":
        stack = [text[index]]
        index += 1
        while index < len(text) and stack:
            character = text[index]
            if character == '"':
                index = _scan_string(text, index)
                continue
            if character in "[{":
                stack.append(character)
            elif character in "]}":
                opening = stack.pop()
                if (opening, character) not in {("[", "]"), ("{", "}")}:
                    raise ValueError("V2.50.08 mismatched JSON container")
            index += 1
        if stack:
            raise ValueError("V2.50.08 unterminated JSON container")
        return index
    end = index
    while end < len(text) and text[end] not in ",} \t\r\n":
        end += 1
    if end == index:
        raise ValueError("V2.50.08 invalid JSON primitive")
    return end


def safe_top_level_members(line: str) -> dict[str, Any]:
    """Decode only the three content-free receipt members of one JSON row."""

    index = _skip_ws(line, 0)
    if index >= len(line) or line[index] != "{":
        raise ValueError("V2.50.08 expected top-level JSON object")
    index += 1
    names: set[str] = set()
    safe: dict[str, Any] = {}
    decoder = json.JSONDecoder()
    while True:
        index = _skip_ws(line, index)
        if index < len(line) and line[index] == "}":
            index += 1
            break
        if index >= len(line) or line[index] != '"':
            raise ValueError("V2.50.08 expected top-level member name")
        name, name_end = decoder.raw_decode(line, index)
        if not isinstance(name, str) or name in names:
            raise ValueError("V2.50.08 duplicate or invalid top-level member")
        names.add(name)
        index = _skip_ws(line, name_end)
        if index >= len(line) or line[index] != ":":
            raise ValueError("V2.50.08 expected top-level member separator")
        value_start = _skip_ws(line, index + 1)
        value_end = _scan_value(line, value_start)
        if name in SAFE_MEMBERS:
            safe[name] = json.loads(line[value_start:value_end])
        index = _skip_ws(line, value_end)
        if index < len(line) and line[index] == ",":
            index += 1
            continue
        if index < len(line) and line[index] == "}":
            index += 1
            break
        raise ValueError("V2.50.08 expected top-level delimiter")
    if _skip_ws(line, index) != len(line):
        raise ValueError("V2.50.08 trailing JSON data")
    if names != EXPECTED_TOP_LEVEL_MEMBERS or set(safe) != SAFE_MEMBERS:
        raise ValueError("V2.50.08 frozen task-result schema drifted")
    return safe


def _safe_rows() -> list[dict[str, Any]]:
    path = _ordinary(contract.TASK_RESULTS)
    rows = [
        safe_top_level_members(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.08 frozen task denominator drifted")
    for row in rows:
        content = paired.validate_receipt(row["content_free_receipt"])
        selection = selector.validate_receipt(row["selection_receipt"])
        phases = row["physical_wave_receipts"]
        if not isinstance(phases, Mapping) or set(phases) != set(contract.PHASES):
            raise RuntimeError("V2.50.08 phase receipt schema drifted")
        first = prior99.validate_first_receipt(phases[paired.FIRST_PHASE])
        second = paired.validate_second_receipt(phases[paired.SECOND_PHASE])
        if (
            second["selection_receipt"] != selection
            or content["selection_changed"] is not bool(selection["selection_changed"])
            or content["bound_visible_link_gain"] != selection["bound_visible_link_gain"]
            or first["logical_query_count"] != 2
            or second["logical_query_count"] != 2
        ):
            raise RuntimeError("V2.50.08 content-free cross-binding drifted")
    return rows


def _sum(rows: Sequence[Mapping[str, Any]], path: Sequence[str]) -> int:
    total = 0
    for row in rows:
        value: Any = row
        for name in path:
            value = value[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise RuntimeError("V2.50.08 expected nonnegative count")
        total += value
    return total


def _phase_counts(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    first_path = ("physical_wave_receipts", paired.FIRST_PHASE)
    second_path = ("physical_wave_receipts", paired.SECOND_PHASE)
    fetch_path = (*second_path, "fetch_receipt")
    return {
        "first_wave": {
            "physical_fetches": _sum(rows, (*first_path, "physical_fetch_count")),
            "usable_pages": _sum(rows, (*first_path, "usable_page_count")),
            "projected_pages": _sum(rows, (*first_path, "projected_page_count")),
            "retained_records": _sum(rows, (*first_path, "retained_record_count")),
        },
        "second_wave_union": {
            "shared_search_prefix_urls": _sum(
                rows, (*second_path, "shared_search_prefix_url_count")
            ),
            "physical_fetches": _sum(rows, (*second_path, "physical_union_fetch_count")),
            "usable_pages": _sum(
                rows, (*second_path, "physical_union_usable_page_count")
            ),
            "fetch_failures": _sum(rows, (*fetch_path, "fetch_failures_snapshot")),
            "helper_results": _sum(rows, (*fetch_path, "helper_result_count")),
            "projected_pages": _sum(rows, (*fetch_path, "projected_page_count")),
            "projection_failures": _sum(
                rows, (*fetch_path, "projection_failure_count")
            ),
            "discovered_records": _sum(rows, (*fetch_path, "discovered_record_count")),
            "admissible_records": _sum(rows, (*fetch_path, "admissible_record_count")),
            "retained_records": _sum(rows, (*fetch_path, "retained_record_count")),
            "mechanism_pages": _sum(rows, (*fetch_path, "mechanism_engaged_page_count")),
            "exact_parent_prefix_handoffs": _sum(
                rows, (*fetch_path, "exact_parent_prefix_handoff_page_count")
            ),
            "input_content_characters": _sum(
                rows, (*fetch_path, "input_content_characters")
            ),
            "compact_prefix_characters": _sum(
                rows, (*fetch_path, "compact_prefix_characters")
            ),
        },
    }


def _arm_count(rows: Sequence[Mapping[str, Any]], arm: str, name: str) -> int:
    return _sum(rows, ("content_free_receipt", "arm_metrics", arm, name))


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    forward = _read(contract.FORWARD_RESULT)
    audit = _read(contract.FORWARD_AUDIT)
    checks = audit.get("checks")
    mechanism = audit.get("mechanism_gate")
    if (
        not contract.sealed(forward, "result_payload_sha256")
        or not contract.sealed(audit, "audit_payload_sha256")
        or forward.get("task_results_sha256") != contract.sha256(_ordinary(contract.TASK_RESULTS))
        or forward.get("prediction_freeze_sha256")
        != contract.sha256(_ordinary(contract.PREDICTION_FREEZE))
        or audit.get("forward_result_sha256")
        != contract.sha256(_ordinary(contract.FORWARD_RESULT))
        or audit.get("prediction_freeze_sha256")
        != contract.sha256(_ordinary(contract.PREDICTION_FREEZE))
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or not isinstance(checks, Mapping)
        or not checks
        or not all(value is True for value in checks.values())
        or not isinstance(mechanism, Mapping)
        or mechanism.get("passed") is not False
        or audit.get("authorization")
        != {
            "postfreeze_external_evaluator_protocol": False,
            "public_exact220_launch": False,
            "leaderboard_or_sota": False,
        }
        or not all(_absent(path) for path in FUTURE_SURFACES)
    ):
        raise RuntimeError("V2.50.08 frozen parent or closed surface drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, audit = _validate_parents()
    rows = _safe_rows()
    changed = [
        row for row in rows if row["content_free_receipt"]["selection_changed"]
    ]
    all_counts = _phase_counts(rows)
    changed_counts = _phase_counts(changed)
    control = contract.CONTROL_ARM
    candidate = contract.CANDIDATE_ARM
    changed_selection = {
        "tasks": len(changed),
        "bound_visible_link_gain": _sum(
            changed, ("selection_receipt", "bound_visible_link_gain")
        ),
        "shared_search_prefix_urls": _sum(
            changed, ("selection_receipt", "original_response_selected_url_count")
        ),
        "selected_visible_links_per_arm": {
            control: _sum(
                changed, ("selection_receipt", "control_selected_visible_link_count")
            ),
            candidate: _sum(
                changed, ("selection_receipt", "candidate_selected_visible_link_count")
            ),
        },
        "bound_visible_links": {
            control: _sum(
                changed, ("selection_receipt", "control_bound_visible_link_count")
            ),
            candidate: _sum(
                changed, ("selection_receipt", "candidate_bound_visible_link_count")
            ),
        },
        "union_visible_link_fetches": sum(
            int(row["physical_wave_receipts"][paired.SECOND_PHASE]["physical_union_fetch_count"])
            - int(row["selection_receipt"]["original_response_selected_url_count"])
            for row in changed
        ),
        "arm_usable_pages": {
            control: _arm_count(changed, control, "usable_pages"),
            candidate: _arm_count(changed, candidate, "usable_pages"),
        },
        "target_bound_projected_pages": {
            control: _arm_count(
                changed, control, "second_wave_target_bound_projected_pages"
            ),
            candidate: _arm_count(
                changed, candidate, "second_wave_target_bound_projected_pages"
            ),
        },
        "target_bound_records": {
            control: _arm_count(changed, control, "second_wave_target_bound_records"),
            candidate: _arm_count(
                changed, candidate, "second_wave_target_bound_records"
            ),
        },
        "prediction_changed_tasks": sum(
            bool(row["content_free_receipt"]["prediction_changed"])
            for row in changed
        ),
        "phase_counts": changed_counts,
    }
    mechanism = audit["mechanism_gate"]
    if (
        len(rows) != mechanism["terminal_tasks"]
        or len(changed) != mechanism["selection_changed_tasks"]
        or changed_selection["bound_visible_link_gain"]
        != mechanism["total_bound_visible_link_gain"]
        or changed_selection["prediction_changed_tasks"] != 0
        or changed_selection["target_bound_projected_pages"]
        != {control: 0, candidate: 0}
        or changed_selection["target_bound_records"]
        != {control: 0, candidate: 0}
        or all_counts["first_wave"]
        != {
            "physical_fetches": 73,
            "usable_pages": 67,
            "projected_pages": 67,
            "retained_records": 15,
        }
        or all_counts["second_wave_union"]
        != {
            "shared_search_prefix_urls": 46,
            "physical_fetches": 83,
            "usable_pages": 81,
            "fetch_failures": 2,
            "helper_results": 83,
            "projected_pages": 81,
            "projection_failures": 0,
            "discovered_records": 4,
            "admissible_records": 4,
            "retained_records": 4,
            "mechanism_pages": 4,
            "exact_parent_prefix_handoffs": 77,
            "input_content_characters": 3321583,
            "compact_prefix_characters": 1943,
        }
    ):
        raise RuntimeError("V2.50.08 content-free aggregate drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": contract.sha256(_ordinary(contract.FORWARD_RESULT)),
            "forward_audit_sha256": contract.sha256(_ordinary(contract.FORWARD_AUDIT)),
            "prediction_freeze_sha256": contract.sha256(
                _ordinary(contract.PREDICTION_FREEZE)
            ),
            "task_results_sha256": contract.sha256(_ordinary(contract.TASK_RESULTS)),
            "forward_wall_seconds": forward["wall_seconds"],
            "forward_audit_valid": True,
            "mechanism_gate_passed": False,
        },
        "all_twenty_phase_counts": all_counts,
        "selection_changed_subset": changed_selection,
        "causal_elimination": {
            "selected_union_fetch_failure_explains_zero_increment": False,
            "projector_process_exception_explains_zero_increment": False,
            "compact_record_capacity_explains_zero_increment": False,
            "record_conversion_before_compact_admission_failed": True,
            "evidence": {
                "changed_subset_second_wave_fetches": changed_counts[
                    "second_wave_union"
                ]["physical_fetches"],
                "changed_subset_second_wave_usable_pages": changed_counts[
                    "second_wave_union"
                ]["usable_pages"],
                "changed_subset_projection_failures": changed_counts[
                    "second_wave_union"
                ]["projection_failures"],
                "changed_subset_discovered_records": changed_counts[
                    "second_wave_union"
                ]["discovered_records"],
                "changed_subset_exact_parent_prefix_handoffs": changed_counts[
                    "second_wave_union"
                ]["exact_parent_prefix_handoffs"],
            },
            "remaining_not_identifiable_from_frozen_counts": [
                "final URL exact identity-path binding failure",
                "distinctive authority URL-token binding failure",
                "title or leading-text identity binding failure",
                "missing duplicate conflicting or grammar-incompatible target fields",
                "redirect or canonical alias leading to an already represented page",
            ],
            "unique_attribution_available": False,
            "reason_unique_attribution_unavailable": (
                "V2.50.05 persisted the parent aggregate receipt but not the "
                "V2.50.04 detail-stage identity, authority, surface, and field counts"
            ),
        },
        "next_experiment": {
            "repeat_or_resume_v25007": False,
            "open_v25007_evaluator_or_gold": False,
            "loosen_identity_authority_or_all_fields_gate": False,
            "public_exact220_authorized": False,
            "required_observer": (
                "append-only content-free aggregation of V2.50.04 detail-stage counts "
                "for identity-path, authority-token, page-surface, field completeness, "
                "duplicate/conflict, discovered record, and compact admission"
            ),
            "candidate_treatment": (
                "admit only a search-prefix-nonoverlapping exact child-detail link "
                "attested by a same-origin authority-bound index page; compare against "
                "stable-first-seen under unchanged query, fetch, model, token, byte, "
                "context, and wall caps"
            ),
            "minimum_external_mechanism_evidence": [
                "candidate-only discovered detail record",
                "candidate-only retained compact record",
                "positive target-bound projected-page and record gain",
                "prediction change",
            ],
        },
        "source_policy": {
            "decoded_top_level_members": sorted(SAFE_MEMBERS),
            "opaque_id_question_query_url_anchor_page_record_value_prediction_answer_gold_evaluator_row_or_credential_decoded": False,
            "disallowed_task_result_members_scanned_only_to_find_json_boundary": True,
            "benchmark_category_question_type_split_or_ground_truth_used": False,
            "diagnosis_fed_back_into_same_forward": False,
            "network_model_search_fetch_process_or_evaluator_effect": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
        "authorization": {
            "implement_counts_only_observer_and_new_external_candidate": True,
            "retry_resume_selective_rerun": False,
            "postfreeze_evaluator": False,
            "public_exact220": False,
            "leaderboard_or_sota": False,
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
    changed = copied.get("selection_changed_subset") or {}
    phase = changed.get("phase_counts", {}).get("second_wave_union", {})
    elimination = copied.get("causal_elimination") or {}
    source = copied.get("source_policy") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("parents", {}).get("forward_audit_valid") is not True
        or copied.get("parents", {}).get("mechanism_gate_passed") is not False
        or changed.get("tasks") != 6
        or changed.get("bound_visible_link_gain") != 7
        or changed.get("shared_search_prefix_urls") != 1
        or changed.get("union_visible_link_fetches") != 30
        or changed.get("prediction_changed_tasks") != 0
        or phase.get("physical_fetches") != 31
        or phase.get("usable_pages") != 31
        or phase.get("fetch_failures") != 0
        or phase.get("helper_results") != 31
        or phase.get("projected_pages") != 31
        or phase.get("projection_failures") != 0
        or phase.get("discovered_records") != 0
        or phase.get("retained_records") != 0
        or phase.get("exact_parent_prefix_handoffs") != 31
        or elimination.get(
            "selected_union_fetch_failure_explains_zero_increment"
        )
        is not False
        or elimination.get(
            "projector_process_exception_explains_zero_increment"
        )
        is not False
        or elimination.get("compact_record_capacity_explains_zero_increment")
        is not False
        or elimination.get("record_conversion_before_compact_admission_failed")
        is not True
        or elimination.get("unique_attribution_available") is not False
        or source.get(
            "opaque_id_question_query_url_anchor_page_record_value_prediction_answer_gold_evaluator_row_or_credential_decoded"
        )
        is not False
        or source.get("benchmark_category_question_type_split_or_ground_truth_used")
        is not False
        or source.get("network_model_search_fetch_process_or_evaluator_effect")
        is not False
        or source.get("entropy_or_information_gain_assigns_signed_credit")
        is not False
        or authorization
        != {
            "implement_counts_only_observer_and_new_external_candidate": True,
            "retry_resume_selective_rerun": False,
            "postfreeze_evaluator": False,
            "public_exact220": False,
            "leaderboard_or_sota": False,
        }
        or copied.get("findings") != []
        or copied.get("diagnosis_valid") is not True
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.50.08 counts-only phase diagnosis drifted")
    return copied


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


def _clean_pushed() -> None:
    if (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
        or any(
            subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(path)],
                cwd=ROOT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=20,
                check=False,
            ).returncode
            != 0
            for path in (SOURCE, TEST)
        )
    ):
        raise RuntimeError("V2.50.08 publication requires clean pushed tracked code")


def publish(path: Path, value: Mapping[str, Any]) -> None:
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
    _clean_pushed()
    value = build_diagnosis()
    publish(ROOT / OUTPUT, value)
    print(
        json.dumps(
            {
                "path": str(OUTPUT),
                "diagnosis_valid": value["diagnosis_valid"],
                "selection_changed_tasks": value["selection_changed_subset"]["tasks"],
                "usable_projected_discovered_records": [
                    value["selection_changed_subset"]["phase_counts"][
                        "second_wave_union"
                    ][name]
                    for name in ("usable_pages", "projected_pages", "discovered_records")
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
