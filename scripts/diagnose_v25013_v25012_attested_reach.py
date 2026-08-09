#!/usr/bin/env python3
"""Counts-only reach diagnosis of the frozen V2.50.12 external gate.

Only attested-selection receipts, detail-stage observer receipts, the parent
content-free runtime receipt, and the parent ``prediction_changed`` boolean are
JSON-decoded.  Every task identifier, question, query, URL, page, anchor,
record value, prediction text, answer, gold/evaluator row, and credential is
skipped as an opaque character range and is never emitted.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
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

from deepwide_agent import v25002_page_visible_link_paired_runtime as parent  # noqa: E402
from deepwide_agent import v25009_detail_stage_observer_fetch as observer  # noqa: E402
from deepwide_agent import v25010_attested_child_detail_selection as selector  # noqa: E402
from deepwide_agent import v25012_attested_detail_external_contract as contract  # noqa: E402
from scripts import diagnose_v25008_v25007_detail_field_link_phase as scanner  # noqa: E402


DATE = "20260809"
ROLE = "v25013_v25012_counts_only_attested_reach_diagnosis"
OUTPUT = Path(f"results/v25013_v25012_attested_reach_diagnosis_v1_{DATE}.json")
SOURCE = Path("scripts/diagnose_v25013_v25012_attested_reach.py")
TEST = Path("tests/test_diagnose_v25013_v25012_attested_reach.py")
TOP_EXPECTED = frozenset(
    {
        "additional_search_fetch_model_token_context_byte_process_retry_wall_or_network_cap",
        "artifact_version",
        "attested_selection_receipt",
        "benchmark_launch_or_evaluator_authorized",
        "detail_stage_observer_receipts",
        "entropy_information_gain_shadow_only",
        "entropy_or_information_gain_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "parent_result",
        "parent_result_and_parent_projection_receipts_unmodified",
        "parent_runner_code_object_reused_without_parent_global_mutation",
        "policy_id",
        "result_payload_sha256",
        "role",
        "same_planning_search_fetch_evidence_synthesis_normalizer_budget_deadline_and_failure_path_as_parent",
        "selection_receipts_context_local_for_concurrent_tasks",
    }
)
PARENT_EXPECTED = frozenset(
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
        raise RuntimeError(f"V2.50.13 expected ordinary repository file: {relative}")
    return path


def _read(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.13 expected JSON object")
    return value


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
        raise ValueError("V2.50.13 expected JSON object")
    index += 1
    names: set[str] = set()
    decoded: dict[str, Any] = {}
    raw_values: dict[str, str] = {}
    decoder = json.JSONDecoder()
    while True:
        index = scanner._skip_ws(text, index)
        if index < len(text) and text[index] == "}":
            index += 1
            break
        name, name_end = decoder.raw_decode(text, index)
        if not isinstance(name, str) or name in names:
            raise ValueError("V2.50.13 duplicate or invalid member")
        names.add(name)
        index = scanner._skip_ws(text, name_end)
        if index >= len(text) or text[index] != ":":
            raise ValueError("V2.50.13 member separator drifted")
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
        raise ValueError("V2.50.13 member delimiter drifted")
    if (
        scanner._skip_ws(text, index) != len(text)
        or names != expected
        or set(decoded) != set(decode)
        or set(raw_values) != set(raw)
    ):
        raise ValueError("V2.50.13 object schema drifted")
    return decoded, raw_values


def safe_row(line: str) -> dict[str, Any]:
    top, raw = _members(
        line,
        expected=TOP_EXPECTED,
        decode=frozenset(
            {"attested_selection_receipt", "detail_stage_observer_receipts"}
        ),
        raw=frozenset({"parent_result"}),
    )
    parent_values, _ = _members(
        raw["parent_result"],
        expected=PARENT_EXPECTED,
        decode=frozenset({"content_free_receipt", "prediction_changed"}),
    )
    attested = selector.validate_receipt(top["attested_selection_receipt"])
    observations = top["detail_stage_observer_receipts"]
    if not isinstance(observations, Mapping) or set(observations) != set(contract.PHASES):
        raise RuntimeError("V2.50.13 observer phase schema drifted")
    checked_observers = {
        phase: observer.validate_observer_receipt(observations[phase])
        for phase in contract.PHASES
    }
    content = parent.validate_receipt(parent_values["content_free_receipt"])
    prediction_changed = parent_values["prediction_changed"]
    if (
        not isinstance(prediction_changed, bool)
        or content["selection_changed"] is not bool(attested["selection_changed"])
        or content["bound_visible_link_gain"]
        != attested["attested_child_detail_link_gain"]
        or content["prediction_changed"] is not prediction_changed
    ):
        raise RuntimeError("V2.50.13 content-free cross-binding drifted")
    return {
        "attested": attested,
        "observers": checked_observers,
        "content": content,
        "prediction_changed": prediction_changed,
    }


def _safe_rows() -> list[dict[str, Any]]:
    rows = [
        safe_row(line)
        for line in _ordinary(contract.TASK_RESULTS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.50.13 frozen task denominator drifted")
    return rows


def _sum(rows: Sequence[Mapping[str, Any]], *path: str) -> int:
    total = 0
    for row in rows:
        value: Any = row
        for name in path:
            value = value[name]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise RuntimeError("V2.50.13 expected nonnegative count")
        total += value
    return total


def _selection(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    fields = (
        "raw_first_wave_page_count",
        "raw_page_visible_link_count",
        "resolved_public_http_link_count",
        "unique_visible_link_count_before_exclusion",
        "excluded_original_or_selected_link_count",
        "available_visible_link_count",
        "authority_bound_attesting_page_count",
        "same_origin_strict_child_link_count",
        "exact_identity_child_link_count",
        "attested_child_detail_link_count",
        "available_attested_child_detail_link_count",
        "control_attested_child_detail_link_count",
        "candidate_attested_child_detail_link_count",
        "attested_child_detail_link_gain",
    )
    distribution = Counter(
        (
            row["attested"]["available_attested_child_detail_link_count"],
            row["attested"]["visible_link_prefix_cap"],
            row["attested"]["selection_changed"],
        )
        for row in rows
    )
    return {
        **{name: _sum(rows, "attested", name) for name in fields},
        "tasks_with_any_attested_child": sum(
            row["attested"]["attested_child_detail_link_count"] > 0 for row in rows
        ),
        "tasks_with_available_attested_child": sum(
            row["attested"]["available_attested_child_detail_link_count"] > 0
            for row in rows
        ),
        "strategy_eligible_tasks": sum(row["attested"]["strategy_eligible"] for row in rows),
        "selection_changed_tasks": sum(
            bool(row["attested"]["selection_changed"]) for row in rows
        ),
        "availability_slot_change_distribution": {
            f"available={available},slots={slots},changed={changed}": count
            for (available, slots, changed), count in sorted(distribution.items())
        },
    }


def _stage(rows: Sequence[Mapping[str, Any]], phase: str) -> dict[str, Any]:
    fields = (
        "parent_fetch_calls_snapshot",
        "parent_helper_result_count",
        "observed_detail_receipt_count",
        "invalid_observer_envelope_count",
        "visible_contract_ready_page_count",
        "identity_url_path_bound_page_count",
        "authority_url_token_bound_page_count",
        "identity_page_surface_bound_page_count",
        "all_target_fields_unique_page_count",
        "discovered_record_page_count",
        "retained_record_page_count",
        "raw_detail_candidate_line_count",
        "target_detail_candidate_count",
        "duplicate_or_conflicting_target_count",
    )
    signatures: Counter[str] = Counter()
    for row in rows:
        signatures.update(row["observers"][phase]["stage_signature_counts"])
    return {
        **{name: _sum(rows, "observers", phase, name) for name in fields},
        "stage_signature_counts": dict(sorted(signatures.items())),
    }


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    forward = _read(contract.FORWARD_RESULT)
    audit = _read(contract.FORWARD_AUDIT)
    checks = audit.get("checks")
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
        or audit.get("mechanism_gate", {}).get("passed") is not False
        or not isinstance(checks, Mapping)
        or not checks
        or not all(value is True for value in checks.values())
        or audit.get("authorization")
        != {
            "postfreeze_external_evaluator_protocol": False,
            "public_exact220_launch": False,
            "leaderboard_or_sota": False,
        }
        or not all(_absent(path) for path in FUTURE_SURFACES)
    ):
        raise RuntimeError("V2.50.13 frozen parent or closed surface drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, audit = _validate_parents()
    rows = _safe_rows()
    changed = [row for row in rows if row["attested"]["selection_changed"]]
    unchanged = [row for row in rows if not row["attested"]["selection_changed"]]
    selection = _selection(rows)
    changed_selection = _selection(changed)
    stages = {phase: _stage(rows, phase) for phase in contract.PHASES}
    changed_second = _stage(changed, contract.PHASES[1])
    unchanged_second = _stage(unchanged, contract.PHASES[1])
    parent_counts = {
        "prediction_changed_tasks": sum(row["prediction_changed"] for row in rows),
        "selection_and_prediction_changed_tasks": sum(
            bool(row["attested"]["selection_changed"]) and row["prediction_changed"]
            for row in rows
        ),
        "prediction_changed_without_selection_change_tasks": sum(
            not row["attested"]["selection_changed"] and row["prediction_changed"]
            for row in rows
        ),
        "tasks_with_positive_projected_page_gain": sum(
            row["content"]["candidate_target_bound_projected_page_gain"] > 0
            for row in rows
        ),
        "tasks_with_positive_record_gain": sum(
            row["content"]["candidate_target_bound_record_gain"] > 0
            for row in rows
        ),
        "record_mechanism_engaged_tasks": sum(
            row["content"]["target_bound_record_mechanism_engaged"] for row in rows
        ),
    }
    mechanism = audit["mechanism_gate"]
    expected_selection = {
        "attested_child_detail_link_count": 15,
        "available_attested_child_detail_link_count": 3,
        "attested_child_detail_link_gain": 2,
        "tasks_with_any_attested_child": 15,
        "tasks_with_available_attested_child": 3,
        "strategy_eligible_tasks": 2,
        "selection_changed_tasks": 2,
    }
    if (
        len(rows) != 20
        or any(selection[name] != value for name, value in expected_selection.items())
        or selection["availability_slot_change_distribution"]
        != {
            "available=0,slots=0,changed=0": 7,
            "available=0,slots=2,changed=0": 1,
            "available=0,slots=3,changed=0": 1,
            "available=0,slots=4,changed=0": 8,
            "available=1,slots=0,changed=0": 1,
            "available=1,slots=4,changed=1": 2,
        }
        or changed_second["stage_signature_counts"]
        != {"c1p0a1s0f0d0r0": 8, "c1p1a1s1f1d1r1": 2}
        or changed_second["discovered_record_page_count"] != 2
        or changed_second["retained_record_page_count"] != 2
        or unchanged_second["discovered_record_page_count"] != 2
        or unchanged_second["retained_record_page_count"] != 2
        or parent_counts
        != {
            "prediction_changed_tasks": 3,
            "selection_and_prediction_changed_tasks": 2,
            "prediction_changed_without_selection_change_tasks": 1,
            "tasks_with_positive_projected_page_gain": 2,
            "tasks_with_positive_record_gain": 2,
            "record_mechanism_engaged_tasks": 2,
        }
        or mechanism.get("selection_changed_tasks") != 2
        or mechanism.get("total_attested_child_detail_link_gain") != 2
    ):
        raise RuntimeError("V2.50.13 content-free aggregate drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "parents": {
            "forward_result_sha256": contract.sha256(_ordinary(contract.FORWARD_RESULT)),
            "forward_audit_sha256": contract.sha256(_ordinary(contract.FORWARD_AUDIT)),
            "prediction_freeze_sha256": contract.sha256(_ordinary(contract.PREDICTION_FREEZE)),
            "task_results_sha256": contract.sha256(_ordinary(contract.TASK_RESULTS)),
            "forward_wall_seconds": forward["wall_seconds"],
            "forward_audit_valid": True,
            "mechanism_gate_passed": False,
        },
        "selection_funnel": selection,
        "detail_stage_funnel": stages,
        "changed_subset": {
            "selection": changed_selection,
            "second_wave_detail_stage": changed_second,
            "tasks": len(changed),
        },
        "unchanged_subset": {
            "second_wave_detail_stage": unchanged_second,
            "tasks": len(unchanged),
        },
        "parent_outcome_counts": parent_counts,
        "causal_diagnosis": {
            "attested_child_reach_exists": True,
            "available_attested_child_reach_is_below_preregistered_gate": True,
            "changed_subset_detail_record_conversion_successes": 2,
            "changed_subset_detail_record_conversion_denominator": 2,
            "changed_subset_record_and_joint_prediction_conversion_complete": True,
            "projector_or_compact_admission_is_current_primary_bottleneck": False,
            "single_identity_direct_search_and_prior_fetch_redundancy_is_primary_observed_ceiling": True,
            "attested_children_removed_by_combined_prior_self_search_prefix_exclusion": 12,
            "available_attested_child_blocked_by_zero_link_slots": 1,
            "prediction_change_without_selection_change_is_treatment_credit": False,
            "excluded_attested_children_uniquely_partitionable_by_exclusion_reason": False,
        },
        "next_experiment": {
            "repeat_resume_or_loosen_v25012": False,
            "open_v25012_evaluator_or_gold": False,
            "public_exact220_authorized": False,
            "continue_single_identity_attested_link_ranking": False,
            "required_new_population": (
                "fresh multi-identity, multi-row directory tasks where one authority-bound "
                "index page visibly attests several distinct child details and direct search "
                "cannot make every child redundant within the unchanged fetch cap"
            ),
            "required_new_projector": (
                "visible multi-identity extraction with per-page exact identity/path/surface, "
                "same-page all-field binding, and atomic per-record compact admission"
            ),
            "required_mechanism_gate": (
                "candidate-only distinct identity coverage, discovered and retained records, "
                "row coverage, prediction change, and unchanged matched budgets"
            ),
        },
        "source_policy": {
            "decoded_surfaces": [
                "attested_selection_receipt",
                "detail_stage_observer_receipts",
                "parent_content_free_receipt",
                "parent_prediction_changed_boolean",
            ],
            "opaque_id_question_query_url_anchor_page_record_value_prediction_text_answer_gold_evaluator_row_or_credential_decoded": False,
            "disallowed_members_scanned_only_to_find_json_boundary": True,
            "benchmark_category_question_type_split_or_ground_truth_used": False,
            "network_model_search_fetch_process_or_evaluator_effect": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
        },
        "authorization": {
            "design_multi_identity_external_candidate": True,
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
    selection = copied.get("selection_funnel") or {}
    changed = copied.get("changed_subset") or {}
    outcomes = copied.get("parent_outcome_counts") or {}
    diagnosis = copied.get("causal_diagnosis") or {}
    source = copied.get("source_policy") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("parents", {}).get("forward_audit_valid") is not True
        or copied.get("parents", {}).get("mechanism_gate_passed") is not False
        or selection.get("attested_child_detail_link_count") != 15
        or selection.get("available_attested_child_detail_link_count") != 3
        or selection.get("selection_changed_tasks") != 2
        or changed.get("tasks") != 2
        or changed.get("second_wave_detail_stage", {}).get("discovered_record_page_count") != 2
        or changed.get("second_wave_detail_stage", {}).get("retained_record_page_count") != 2
        or outcomes.get("selection_and_prediction_changed_tasks") != 2
        or outcomes.get("prediction_changed_without_selection_change_tasks") != 1
        or diagnosis.get("changed_subset_record_and_joint_prediction_conversion_complete")
        is not True
        or diagnosis.get("projector_or_compact_admission_is_current_primary_bottleneck")
        is not False
        or diagnosis.get("single_identity_direct_search_and_prior_fetch_redundancy_is_primary_observed_ceiling")
        is not True
        or diagnosis.get("excluded_attested_children_uniquely_partitionable_by_exclusion_reason")
        is not False
        or source.get(
            "opaque_id_question_query_url_anchor_page_record_value_prediction_text_answer_gold_evaluator_row_or_credential_decoded"
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
            "design_multi_identity_external_candidate": True,
            "retry_resume_selective_rerun": False,
            "postfreeze_evaluator": False,
            "public_exact220": False,
            "leaderboard_or_sota": False,
        }
        or copied.get("findings") != []
        or copied.get("diagnosis_valid") is not True
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.50.13 counts-only reach diagnosis drifted")
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
        raise RuntimeError("V2.50.13 publication requires clean pushed tracked code")


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
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
                "attested_available_changed": [
                    value["selection_funnel"][name]
                    for name in (
                        "attested_child_detail_link_count",
                        "available_attested_child_detail_link_count",
                        "selection_changed_tasks",
                    )
                ],
                "record_and_joint_prediction_change": [
                    value["parent_outcome_counts"]["tasks_with_positive_record_gain"],
                    value["parent_outcome_counts"]["selection_and_prediction_changed_tasks"],
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
