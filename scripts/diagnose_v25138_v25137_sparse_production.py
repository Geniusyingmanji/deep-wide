#!/usr/bin/env python3
"""Counts-only diagnosis of the frozen V2.51.37-r2 sparse gate.

The task rows contain opaque identifiers, full parent envelopes, and two
prediction strings.  This module deliberately does not JSON-decode those
members.  A boundary scanner decodes only terminal booleans and the sealed
V2.51.35 content-free receipt, then aggregates the already-frozen mechanism
funnel.  It never opens a question, query, URL, page, prediction, answer,
mapping, gold row, evaluator row, score, credential, or task identity.
"""

from __future__ import annotations

import ast
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

from deepwide_agent import v25135_sparse_production_runtime as runtime  # noqa: E402
from deepwide_agent import v25137_sparse_production_external_contract as contract  # noqa: E402
from scripts import diagnose_v25008_v25007_detail_field_link_phase as scanner  # noqa: E402
from scripts import run_v25137_sparse_production_external as runner  # noqa: E402


DATE = "20260812"
ROLE = "v25138_v25137_sparse_production_counts_only_diagnosis"
OUTPUT = Path(
    f"results/v25138_v25137_sparse_production_diagnosis_v1_{DATE}.json"
)
SOURCE = Path("scripts/diagnose_v25138_v25137_sparse_production.py")
TEST = Path("tests/test_diagnose_v25138_v25137_sparse_production.py")
RUNTIME_SOURCE = Path("src/deepwide_agent/v25135_sparse_production_runtime.py")
SAFE_MEMBERS = frozenset(
    {
        "runtime_completed",
        "failure_as_zero",
        "content_free_receipt",
        "entropy_or_information_gain_assigns_signed_credit",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
    }
)
EXPECTED_TOP_LEVEL_MEMBERS = frozenset(
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
        raise RuntimeError(f"V2.51.38 expected ordinary repository file: {relative}")
    return path


def _absent(relative: Path) -> bool:
    path = ROOT / relative
    return not path.exists() and not path.is_symlink()


def _read_json(relative: Path) -> dict[str, Any]:
    value = json.loads(_ordinary(relative).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.51.38 expected JSON object")
    return value


def safe_row(line: str) -> dict[str, Any]:
    """Decode only five explicitly content-free members of a frozen row."""

    index = scanner._skip_ws(line, 0)
    if index >= len(line) or line[index] != "{":
        raise ValueError("V2.51.38 expected top-level JSON object")
    index += 1
    decoder = json.JSONDecoder()
    names: set[str] = set()
    safe: dict[str, Any] = {}
    while True:
        index = scanner._skip_ws(line, index)
        if index < len(line) and line[index] == "}":
            index += 1
            break
        name, name_end = decoder.raw_decode(line, index)
        if not isinstance(name, str) or name in names:
            raise ValueError("V2.51.38 duplicate or invalid member")
        names.add(name)
        index = scanner._skip_ws(line, name_end)
        if index >= len(line) or line[index] != ":":
            raise ValueError("V2.51.38 member separator drifted")
        start = scanner._skip_ws(line, index + 1)
        end = scanner._scan_value(line, start)
        if name in SAFE_MEMBERS:
            safe[name] = json.loads(line[start:end])
        index = scanner._skip_ws(line, end)
        if index < len(line) and line[index] == ",":
            index += 1
            continue
        if index < len(line) and line[index] == "}":
            index += 1
            break
        raise ValueError("V2.51.38 member delimiter drifted")
    if (
        scanner._skip_ws(line, index) != len(line)
        or names != EXPECTED_TOP_LEVEL_MEMBERS
        or set(safe) != SAFE_MEMBERS
    ):
        raise ValueError("V2.51.38 frozen row schema drifted")
    if (
        safe["runtime_completed"] is not True
        or safe["failure_as_zero"] is not False
        or safe["entropy_or_information_gain_assigns_signed_credit"] is not False
        or safe[
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
        ]
        is not False
        or runtime.validate_receipt(safe["content_free_receipt"])
        != safe["content_free_receipt"]
    ):
        raise RuntimeError("V2.51.38 content-free row drifted")
    return safe


def _safe_rows() -> list[dict[str, Any]]:
    rows = [
        safe_row(line)
        for line in _ordinary(contract.TASK_ROWS)
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.51.38 fixed denominator drifted")
    return rows


def _hist(values: Sequence[int]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _revision_source_contract() -> dict[str, Any]:
    """Prove that V2.51.35 forwarded the inherited revision prompt verbatim."""

    tree = ast.parse(_ordinary(RUNTIME_SOURCE).read_text(encoding="utf-8"))
    method: ast.FunctionDef | None = None
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "SparseProductionModel":
            method = next(
                (
                    child
                    for child in node.body
                    if isinstance(child, ast.FunctionDef)
                    and child.name == "_revision"
                ),
                None,
            )
            break
    if method is None:
        raise RuntimeError("V2.51.38 revision method missing")
    forwards = []
    for node in ast.walk(method):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "complete"
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "_bounded"
        ):
            forwards.append(node)
    user_mutations = [
        node
        for node in ast.walk(method)
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign))
        and any(
            isinstance(target, ast.Name) and target.id == "user"
            for target in (
                node.targets
                if isinstance(node, ast.Assign)
                else [node.target]
            )
        )
    ]
    inherited_user_forwarded = bool(
        len(forwards) == 1
        and len(forwards[0].args) >= 2
        and isinstance(forwards[0].args[0], ast.Name)
        and forwards[0].args[0].id == "system"
        and isinstance(forwards[0].args[1], ast.Name)
        and forwards[0].args[1].id == "user"
        and not user_mutations
    )
    if not inherited_user_forwarded:
        raise RuntimeError("V2.51.38 revision source contract drifted")
    return {
        "single_revision_provider_forward_site": True,
        "inherited_candidate_synthesis_user_forwarded_verbatim": True,
        "production_prediction_inserted_into_revision_prompt": False,
        "revision_user_argument_mutated_before_provider_forward": False,
    }


def _validate_parents() -> tuple[dict[str, Any], dict[str, Any]]:
    forward = runner.validate_forward_result(_read_json(contract.FORWARD_RESULT))
    audit = _read_json(contract.FORWARD_AUDIT)
    decision = forward["mechanism_decision"]
    if (
        not contract.sealed(audit, "audit_payload_sha256")
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("forward_result_sha256")
        != contract.sha256(_ordinary(contract.FORWARD_RESULT))
        or audit.get("task_rows_sha256")
        != contract.sha256(_ordinary(contract.TASK_ROWS))
        or decision.get("mechanism_gate_passed") is not False
        or decision.get("failed_checks")
        != ["minimum_attributable_prediction_changed"]
        or audit.get("authorization", {}).get(
            "postfreeze_external_evaluator_implementation_and_protocol"
        )
        is not False
        or not all(_absent(path) for path in FUTURE_SURFACES)
    ):
        raise RuntimeError("V2.51.38 frozen parent barrier drifted")
    return forward, audit


def build_diagnosis(*, now: int | None = None) -> dict[str, Any]:
    forward, _audit = _validate_parents()
    rows = _safe_rows()
    receipts = [row["content_free_receipt"] for row in rows]
    revision_rows = [
        receipt
        for receipt in receipts
        if receipt["revision_synthesis_provider_forward_count"] == 1
    ]
    source_contract = _revision_source_contract()
    funnel = {
        "task_count": len(rows),
        "runtime_completed_tasks": sum(row["runtime_completed"] for row in rows),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in rows),
        "target_field_page_gain_histogram": _hist(
            [receipt["target_field_page_gain"] for receipt in receipts]
        ),
        "target_field_pair_gain_histogram": _hist(
            [receipt["target_field_pair_gain"] for receipt in receipts]
        ),
        "complete_target_field_page_gain_histogram": _hist(
            [receipt["complete_target_field_page_gain"] for receipt in receipts]
        ),
        "verified_gain_tasks": sum(
            receipt["verified_source_identity_field_gain"] for receipt in receipts
        ),
        "revision_provider_forward_tasks": len(revision_rows),
        "revision_provider_valid_tasks": sum(
            receipt["revision_provider_output_valid"] for receipt in revision_rows
        ),
        "revision_changed_prediction_tasks": sum(
            receipt["final_prediction_changed_from_production"]
            for receipt in revision_rows
        ),
        "revision_unchanged_prediction_tasks": sum(
            not receipt["final_prediction_changed_from_production"]
            for receipt in revision_rows
        ),
        "identity_replay_tasks": sum(
            receipt["identity_replay_used"] for receipt in receipts
        ),
        "gain_verification_failure_tasks": sum(
            receipt["gain_verification_failure_present"] for receipt in receipts
        ),
        "revision_failure_tasks": sum(
            receipt["revision_failure_present"] for receipt in receipts
        ),
        "post_effect_failure_tasks": sum(
            receipt["post_effect_failure_present"] for receipt in receipts
        ),
        "production_fallback_tasks": sum(
            receipt["production_fallback_used"] for receipt in receipts
        ),
        "revision_change_conversion_numerator": sum(
            receipt["final_prediction_changed_from_production"]
            for receipt in revision_rows
        ),
        "revision_change_conversion_denominator": len(revision_rows),
    }
    expected_funnel = {
        "task_count": 20,
        "runtime_completed_tasks": 20,
        "failure_as_zero_tasks": 0,
        "target_field_page_gain_histogram": {"-1": 1, "0": 13, "1": 6},
        "target_field_pair_gain_histogram": {
            "-1": 1,
            "0": 13,
            "1": 5,
            "2": 1,
        },
        "complete_target_field_page_gain_histogram": {"0": 20},
        "verified_gain_tasks": 6,
        "revision_provider_forward_tasks": 6,
        "revision_provider_valid_tasks": 6,
        "revision_changed_prediction_tasks": 1,
        "revision_unchanged_prediction_tasks": 5,
        "identity_replay_tasks": 14,
        "gain_verification_failure_tasks": 0,
        "revision_failure_tasks": 0,
        "post_effect_failure_tasks": 0,
        "production_fallback_tasks": 0,
        "revision_change_conversion_numerator": 1,
        "revision_change_conversion_denominator": 6,
    }
    if funnel != expected_funnel:
        raise RuntimeError("V2.51.38 content-free funnel drifted")
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
            "runtime_source_sha256": contract.sha256(_ordinary(RUNTIME_SOURCE)),
            "audit_valid": True,
            "mechanism_gate_passed": False,
            "failed_checks": ["minimum_attributable_prediction_changed"],
        },
        "aggregate": copy.deepcopy(forward["aggregate"]),
        "content_free_funnel": funnel,
        "revision_source_contract": source_contract,
        "diagnosis": {
            "retrieval_and_gain_verification_natural_reach_exists": True,
            "revision_provider_transport_or_normalization_is_not_the_observed_bottleneck": True,
            "five_of_six_valid_revisions_left_prediction_unchanged": True,
            "all_complete_target_field_page_gains_are_zero": True,
            "v25135_revision_is_an_independent_candidate_evidence_resynthesis": True,
            "v25135_revision_does_not_explicitly_condition_on_the_completed_production_table": True,
            "observed_primary_conversion_bottleneck_is_revision_actionability": True,
            "quality_effect_is_unknown_because_evaluator_was_correctly_not_authorized": True,
            "v25137_population_must_not_be_retried_resumed_or_reused": True,
            "next_build_only_candidate_must_supply_completed_production_table_to_revision": True,
            "next_build_only_candidate_must_supply_only_verified_incremental_evidence_as_delta": True,
            "next_build_only_candidate_must_preserve_unmentioned_rows_and_cells": True,
            "next_build_only_candidate_must_allow_only_evidence_supported_cell_changes": True,
            "next_build_only_candidate_must_preserve_production_on_revision_projection_or_posteffect_failure": True,
            "query_fetch_model_context_token_wall_and_network_caps_must_not_expand": True,
            "entropy_or_information_gain_signed_credit_validated": False,
            "entropy_or_information_gain_signed_credit": 0,
        },
        "content_policy": {
            "decoded_task_row_members": sorted(SAFE_MEMBERS),
            "opaque_id_question_query_url_title_page_prediction_answer_mapping_gold_category_split_evaluator_score_credential_decoded": False,
            "disallowed_members_scanned_only_to_find_json_boundaries": True,
            "network_model_search_fetch_process_or_evaluator_effect": False,
            "same_run_evaluator_feedback_used_for_runtime_routing": False,
        },
        "authorization": {
            "production_table_conditioned_targeted_revision_build_only": True,
            "new_fresh_disjoint_external_protocol_or_launch": False,
            "v25137_evaluator_or_quality_result": False,
            "v25137_retry_resume_or_population_reuse": False,
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
    source = copied.get("revision_source_contract") or {}
    diagnosis = copied.get("diagnosis") or {}
    authorization = copied.get("authorization") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("parents", {}).get("audit_valid") is not True
        or copied.get("parents", {}).get("mechanism_gate_passed") is not False
        or copied.get("parents", {}).get("failed_checks")
        != ["minimum_attributable_prediction_changed"]
        or funnel.get("verified_gain_tasks") != 6
        or funnel.get("revision_provider_valid_tasks") != 6
        or funnel.get("revision_changed_prediction_tasks") != 1
        or funnel.get("revision_unchanged_prediction_tasks") != 5
        or funnel.get("complete_target_field_page_gain_histogram") != {"0": 20}
        or source.get("inherited_candidate_synthesis_user_forwarded_verbatim")
        is not True
        or source.get("production_prediction_inserted_into_revision_prompt")
        is not False
        or diagnosis.get(
            "observed_primary_conversion_bottleneck_is_revision_actionability"
        )
        is not True
        or diagnosis.get("quality_effect_is_unknown_because_evaluator_was_correctly_not_authorized")
        is not True
        or diagnosis.get("entropy_or_information_gain_signed_credit") != 0
        or authorization
        != {
            "production_table_conditioned_targeted_revision_build_only": True,
            "new_fresh_disjoint_external_protocol_or_launch": False,
            "v25137_evaluator_or_quality_result": False,
            "v25137_retry_resume_or_population_reuse": False,
            "deepwidebench_dev64_exact220_leaderboard_or_sota": False,
        }
        or copied.get("findings") != []
        or copied.get("diagnosis_valid") is not True
        or seal != contract.payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.51.38 diagnosis drifted")
    return copied


def publish_exclusive(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        json.dumps(dict(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode()
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    value = build_diagnosis()
    publish_exclusive(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "role": ROLE}, sort_keys=True))


if __name__ == "__main__":
    main()
