#!/usr/bin/env python3
"""Freeze the V2.42.73 two-wave candidate versus V2.42.71 dev64 control."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24275_forward_contract import (  # noqa: E402
    ACTIVATION,
    CHILD_MARKER,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FETCH_HELPER_MARKER,
    FORWARD_PROTOCOL,
    FORWARD_RESULT,
    LIMITS,
    MODEL,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    MODEL_SLOT_POOL_ID,
    OUTPUT_ROOT,
    PREAUDIT,
    PREDICTION_FREEZE,
    PROTOCOL_ID,
    RUNTIME_PREDICTIONS,
    RUNNER_MARKER,
    RUN_SUMMARY,
    SAFE_PROGRESS,
    SEARCH,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    TASK_ROOT,
    TWO_WAVE_POLICY,
    payload_sha256,
    read_object,
    sha256,
)


ROLE = "v24275_two_wave_vs_v24271_frozen_candidate_dev64_preregistration"
OUTPUT = Path("results/v24275_two_wave_dev64_preregistration_v1_20260802.json")
FINAL_RESULT = Path("results/v24275_two_wave_dev64_result_v1_20260802.json")
POSTAUDIT = Path(
    "results/v24275_two_wave_dev64_postresult_audit_v1_20260802.json"
)
EVALUATOR_ROOT = OUTPUT_ROOT / "evaluator"
FINALIZER_MARKER = "scripts/finalize_v24275_two_wave_dev64.py"
MAPPING_PATH = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
LEASE = Path("outputs/deepwide_benchmark_api.lease.lock")

CONTROL_PROTOCOL = Path(
    "results/v24271_keyless_dev64_preregistration_v1_20260802.json"
)
CONTROL_RESULT = Path("results/v24271_keyless_dev64_result_v1_20260802.json")
CONTROL_POSTAUDIT = Path(
    "results/v24271_keyless_dev64_postresult_erratum_audit_v1_20260802.json"
)
CONTROL_FORWARD_ERRATUM = Path(
    "results/v24271_forward_validator_field_alias_erratum_v1_20260802.json"
)
CONTROL_OUTPUT_ROOT = Path("outputs/v24271_keyless_dev64_v1_20260802")
CONTROL_PREDICTION_FREEZE = CONTROL_OUTPUT_ROOT / "candidate_prediction_freeze.json"
CONTROL_RUNTIME = CONTROL_OUTPUT_ROOT / "candidate_runtime_predictions.jsonl"
CONTROL_RUN_SUMMARY = CONTROL_OUTPUT_ROOT / "candidate_run_summary.json"

BUILD_AUDIT = Path("results/v24273_two_wave_task_build_audit_v1_20260802.json")
NEUTRAL_FULL_PROBE = Path(
    "results/v24273_neutral_full_task_probe_v1_20260802.json"
)
CAPACITY_STAIRCASE = Path(
    "results/v24273_neutral_capacity_staircase_v1_20260802.json"
)
CAPACITY_EXTENSION = Path(
    "results/v24274_neutral_capacity_extension_v1_20260802.json"
)

FORWARD_FILES = (
    "src/deepwide_agent/__init__.py",
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24267_total_fallback.py",
    "src/deepwide_agent/v24268_keyless_batched_runtime.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24270_budget_equivalent_union.py",
    "src/deepwide_agent/v24272_two_wave_entropy_voc.py",
    "src/deepwide_agent/v24272_two_wave_retrieval.py",
    "src/deepwide_agent/v24273_two_wave_task_runtime.py",
    "src/deepwide_agent/v24275_hard_deadline_fetch.py",
    "scripts/deepwide_api_lease.py",
    "scripts/run_v24275_fetch_helper.py",
    "scripts/run_v24275_two_wave_task.py",
)
FORWARD_ENTRY_FILES = (
    "src/deepwide_agent/v24275_forward_contract.py",
    "scripts/run_v24275_two_wave_dev64.py",
)
CONTROL_FILES = (
    "scripts/preregister_v24275_two_wave_dev64.py",
    "scripts/audit_v24275_two_wave_dev64.py",
    "scripts/activate_v24275_two_wave_dev64.py",
    "scripts/finalize_v24275_two_wave_dev64.py",
    "scripts/run_official_eval_local.py",
    "scripts/finalize_fullset_rollout.py",
    "tests/test_v24275_two_wave_dev64.py",
)
FUTURE_PATHS = (
    PREAUDIT,
    ACTIVATION,
    EXECUTION_START,
    FORWARD_RESULT,
    FINAL_RESULT,
    POSTAUDIT,
    OUTPUT_ROOT,
)
SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE = re.compile(r"task_[0-9a-f]{24}")


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.42.75 path is noncanonical")
    path = root / raw
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise RuntimeError(f"V2.42.75 expected ordinary file: {relative}")
    return path


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _manifest(root: Path, files: tuple[str, ...]) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source) or (
            not relative.startswith("tests/") and OPAQUE.search(source)
        ):
            raise RuntimeError(f"V2.42.75 unsafe frozen source: {relative}")
        output[relative] = sha256(path)
    return output


def _parents(root: Path) -> dict[str, Any]:
    paths = (
        CONTROL_PROTOCOL,
        CONTROL_RESULT,
        CONTROL_POSTAUDIT,
        CONTROL_FORWARD_ERRATUM,
        BUILD_AUDIT,
        NEUTRAL_FULL_PROBE,
        CAPACITY_STAIRCASE,
        CAPACITY_EXTENSION,
    )
    for path in paths:
        _ordinary(root, path)
    control_protocol = read_object(root / CONTROL_PROTOCOL)
    control_result = read_object(root / CONTROL_RESULT)
    control_audit = read_object(root / CONTROL_POSTAUDIT)
    control_erratum = read_object(root / CONTROL_FORWARD_ERRATUM)
    build_audit = read_object(root / BUILD_AUDIT)
    neutral = read_object(root / NEUTRAL_FULL_PROBE)
    capacity = read_object(root / CAPACITY_STAIRCASE)
    extension = read_object(root / CAPACITY_EXTENSION)
    if (
        control_protocol.get("role")
        != "v24271_keyless_candidate_vs_frozen_control_dev64_preregistration"
        or not _sealed(control_protocol, "decision_contract_sha256")
        or control_result.get("role") != "v24271_keyless_dev64_result"
        or control_result.get("status") != "development_gate_no_go"
        or not _sealed(control_result, "result_payload_sha256")
        or control_result.get("claims", {}).get("sota") is not False
        or control_audit.get("role")
        != "v24271_keyless_dev64_postresult_erratum_audit"
        or control_audit.get("audit_valid") is not True
        or not _sealed(control_audit, "audit_payload_sha256")
        or control_erratum.get("role")
        != "v24271_forward_validator_field_alias_erratum"
        or control_erratum.get("valid") is not True
        or not _sealed(control_erratum, "erratum_payload_sha256")
        or build_audit.get("role") != "v24273_two_wave_task_build_audit"
        or build_audit.get("audit_valid") is not True
        or any(build_audit.get("authorization", {}).values())
        or neutral.get("role") != "v24273_neutral_full_task_probe"
        or neutral.get("completion_kind") not in {"primary", "normalized_primary"}
        or any(neutral.get("authorization", {}).values())
        or capacity.get("role") != "v24273_neutral_capacity_staircase"
        or capacity.get("highest_passing_concurrency") != 4
        or capacity.get("all_requested_levels_passed") is not True
        or extension.get("role") != "v24274_neutral_capacity_extension"
        or extension.get("highest_passing_concurrency") != 8
        or extension.get("all_requested_levels_passed") is not False
        or [level.get("passed") for level in extension.get("levels", [])]
        != [True, False]
    ):
        raise RuntimeError("V2.42.75 parent identity drifted")
    evaluator = control_protocol.get("evaluator_contract")
    task_contract = control_protocol.get("task_contract")
    if (
        not isinstance(evaluator, dict)
        or evaluator.get("mapping_query_answer_or_gold_bytes_opened_or_hashed")
        is not False
        or not isinstance(task_contract, dict)
        or task_contract.get("selected_count") != SELECTED_COUNT
        or task_contract.get("runtime_boundary") != ["opaque_id", "question"]
    ):
        raise RuntimeError("V2.42.75 parent task/evaluator identity drifted")
    ids = task_contract.get("selected_opaque_ids")
    if (
        not isinstance(ids, list)
        or len(ids) != SELECTED_COUNT
        or len(set(ids)) != SELECTED_COUNT
        or any(not isinstance(value, str) or OPAQUE.fullmatch(value) is None for value in ids)
        or payload_sha256(ids) != task_contract.get("selected_opaque_ids_sha256")
    ):
        raise RuntimeError("V2.42.75 parent opaque allowlist drifted")
    return {
        "control_protocol": control_protocol,
        "control_result": control_result,
        "control_audit": control_audit,
        "control_erratum": control_erratum,
        "build_audit": build_audit,
        "neutral": neutral,
        "capacity": capacity,
        "extension": extension,
        "evaluator": evaluator,
        "task_contract": task_contract,
        "ids": list(ids),
    }


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    parents = _parents(root)
    manifest_path = _ordinary(root, SOURCE_MANIFEST)
    present = [
        str(path)
        for path in (*FUTURE_PATHS, FORWARD_PROTOCOL)
        if (root / path).exists() or (root / path).is_symlink()
    ]
    if require_pristine and present:
        raise RuntimeError(f"V2.42.75 future surface is not pristine: {present}")
    dependencies = _manifest(root, FORWARD_FILES)
    entries = _manifest(root, FORWARD_ENTRY_FILES)
    controls = _manifest(root, CONTROL_FILES)
    task_parent = parents["task_contract"]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parents": {
            "frozen_control_protocol": {
                "path": str(CONTROL_PROTOCOL),
                "sha256": sha256(root / CONTROL_PROTOCOL),
            },
            "frozen_control_result": {
                "path": str(CONTROL_RESULT),
                "sha256": sha256(root / CONTROL_RESULT),
            },
            "frozen_control_postresult_audit": {
                "path": str(CONTROL_POSTAUDIT),
                "sha256": sha256(root / CONTROL_POSTAUDIT),
            },
            "frozen_control_forward_erratum": {
                "path": str(CONTROL_FORWARD_ERRATUM),
                "sha256": sha256(root / CONTROL_FORWARD_ERRATUM),
            },
            "two_wave_build_audit": {
                "path": str(BUILD_AUDIT),
                "sha256": sha256(root / BUILD_AUDIT),
            },
            "neutral_full_task_probe": {
                "path": str(NEUTRAL_FULL_PROBE),
                "sha256": sha256(root / NEUTRAL_FULL_PROBE),
            },
            "neutral_capacity_staircase": {
                "path": str(CAPACITY_STAIRCASE),
                "sha256": sha256(root / CAPACITY_STAIRCASE),
            },
            "neutral_capacity_extension": {
                "path": str(CAPACITY_EXTENSION),
                "sha256": sha256(root / CAPACITY_EXTENSION),
                "highest_passing_concurrency": 8,
                "concurrency_16_passed": False,
            },
            "historical_control_prediction_freeze_runtime_summary_mapping_gold_or_evaluator_rows_opened_or_hashed": False,
        },
        "comparison_contract": {
            "control": "frozen V2.42.71 candidate on consumed dev-validation64",
            "candidate": "one cold V2.42.73 two-wave rollout on the same 64 opaque IDs",
            "shared_random_prefix": False,
            "strict_causal_ablation": False,
            "development_gate_only": True,
            "control_prediction_bytes_open_only_after_candidate_exact64_freeze": True,
            "both_arms_fully_re_evaluated_with_the_same_current_judge": True,
            "old_evaluator_rows_reused": False,
            "selective_changed_prediction_evaluation": False,
        },
        "task_contract": {
            "manifest": {
                "path": str(SOURCE_MANIFEST),
                "sha256": sha256(manifest_path),
                "row_schema": ["opaque_id", "question"],
            },
            "selection_rule": "frozen opaque-ID allowlist; no category, question_type, or split metadata",
            "selected_count": SELECTED_COUNT,
            "selected_opaque_ids": parents["ids"],
            "selected_opaque_ids_sha256": payload_sha256(parents["ids"]),
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_split_category_gold_evaluator_or_score_used_for_selection": False,
            "development_resource_already_consumed_not_fresh_or_held_out": True,
            "same_opaque_order_as_frozen_control": parents["ids"]
            == task_parent["selected_opaque_ids"],
        },
        "forward_contract": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "global_model_slot_cap": MODEL_SLOT_CAP,
            "maximum_concurrent_loopback_provider_requests": MODEL_SLOT_CAP,
            "exact_terminal_predictions_required": SELECTED_COUNT,
            "one_candidate_forward_per_visible_task": True,
            "resume_rerun_skip_or_selective_retry_allowed": False,
            "worker_or_validator_failure_returns_total_fallback": True,
            "mapping_control_prediction_gold_or_evaluator_open_before_candidate_freeze": False,
        },
        "limits": dict(LIMITS),
        "two_wave_policy": dict(TWO_WAVE_POLICY),
        "provider_contract": {
            "model": dict(MODEL),
            "search": dict(SEARCH),
            "credential_required_or_persisted": False,
        },
        "model_slot_contract": {
            "pool_id": MODEL_SLOT_POOL_ID,
            "slot_cap": MODEL_SLOT_CAP,
            "directory": str(MODEL_SLOT_DIRECTORY),
            "receipt_required_per_child": True,
            "receipt_acquisitions_must_equal_actual_model_requests": True,
        },
        "freeze_contract": {
            "candidate_runtime_path": str(RUNTIME_PREDICTIONS),
            "candidate_summary_path": str(RUN_SUMMARY),
            "candidate_freeze_path": str(PREDICTION_FREEZE),
            "candidate_exact64_before_control_or_evaluator_side_open": True,
        },
        "evaluator_contract": dict(parents["evaluator"]),
        "evaluation_contract": {
            "control_and_candidate_full64_current_judge_evaluation": True,
            "conservative_denominator_per_arm": SELECTED_COUNT,
            "forward_or_evaluator_failure_as_zero": True,
            "selective_error_retry_allowed": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "decision_contract": {
            "maximum_search_token_ratio": 0.70,
            "maximum_task_wall_sum_ratio": 0.50,
            "minimum_quality_composite_delta": -0.01,
            "minimum_entity_acc_delta": -0.03125,
            "minimum_f1_by_row_delta": -0.02,
            "minimum_f1_by_item_delta": -0.02,
            "minimum_column_f1_delta": -0.02,
            "minimum_whole_table_success_delta": 0,
            "minimum_model_generated_table_delta": -1,
            "candidate_retrieval_failures_maximum": 0,
            "candidate_unrecoverable_search_failures_maximum": 0,
            "candidate_cache_misses_maximum": 0,
            "candidate_cache_serve_network_fetches_maximum": 0,
            "candidate_hard_fetch_deadline_failures_maximum": 0,
            "candidate_fetch_helper_failures_maximum": 0,
        },
        "lease_contract": {
            "path": str(LEASE),
            "forward_owner": "v24275_two_wave_dev64_forward_v1",
            "forward_purpose": "label_blind_two_wave_candidate_dev64_forward",
            "evaluator_owner": "v24275_two_wave_dev64_evaluator_v1",
            "evaluator_purpose": "post_candidate_freeze_full64_both_arms_evaluator",
            "forward_and_evaluator_may_not_overlap": True,
        },
        "execution": {
            "runner_marker": RUNNER_MARKER,
            "child_marker": CHILD_MARKER,
            "fetch_helper_marker": FETCH_HELPER_MARKER,
            "finalizer_marker": FINALIZER_MARKER,
            "preactivation_audit_path": str(PREAUDIT),
            "activation_path": str(ACTIVATION),
            "execution_start_path": str(EXECUTION_START),
            "forward_result_path": str(FORWARD_RESULT),
            "final_result_path": str(FINAL_RESULT),
            "postresult_audit_path": str(POSTAUDIT),
            "output_root": str(OUTPUT_ROOT),
            "parent_deadline_grace_seconds": 15,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_control_prediction_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "historical_control_and_evaluator_open_only_after_candidate_exact64_freeze": True,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "single_candidate_dev64_forward_after_activation": True,
            "post_freeze_full64_both_arms_evaluator": True,
            "exact220_design_if_go": True,
            "new_exact220_launch": False,
            "additional_rollout_or_avg4": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "forward_surface": {
            "dependency_manifest": dependencies,
            "dependency_manifest_sha256": payload_sha256(dependencies),
            "entry_manifest": entries,
            "entry_manifest_sha256": payload_sha256(entries),
            "manifest": {**dependencies, **entries},
            "manifest_sha256": payload_sha256({**dependencies, **entries}),
        },
        "control_surface": {
            "manifest": controls,
            "manifest_sha256": payload_sha256(controls),
        },
    }
    projection = build_forward_contract(value)
    value["forward_runtime_contract"] = {
        "path": str(FORWARD_PROTOCOL),
        "payload_sha256": projection["forward_contract_payload_sha256"],
        "contains_control_mapping_gold_evaluator_or_score_path": False,
    }
    value["decision_contract_sha256"] = payload_sha256(value)
    return value


def build_forward_contract(protocol: dict[str, Any]) -> dict[str, Any]:
    execution = protocol["execution"]
    lease = protocol["lease_contract"]
    value = {
        "artifact_version": 1,
        "role": "v24275_two_wave_dev64_forward_contract",
        "protocol_id": protocol["protocol_id"],
        "created_at_unix": protocol["created_at_unix"],
        "label_blind": True,
        "task_contract": {
            key: protocol["task_contract"][key]
            for key in (
                "manifest",
                "selection_rule",
                "selected_count",
                "selected_opaque_ids",
                "selected_opaque_ids_sha256",
                "runtime_boundary",
                "mapping_split_category_gold_evaluator_or_score_used_for_selection",
            )
        },
        "forward_contract": dict(protocol["forward_contract"]),
        "limits": dict(protocol["limits"]),
        "two_wave_policy": dict(protocol["two_wave_policy"]),
        "provider_contract": dict(protocol["provider_contract"]),
        "model_slot_contract": dict(protocol["model_slot_contract"]),
        "lease_contract": {
            key: lease[key]
            for key in ("path", "forward_owner", "forward_purpose")
        },
        "execution": {
            key: execution[key]
            for key in (
                "runner_marker",
                "child_marker",
                "fetch_helper_marker",
                "preactivation_audit_path",
                "activation_path",
                "execution_start_path",
                "forward_result_path",
                "output_root",
                "parent_deadline_grace_seconds",
            )
        },
        "source_policy": dict(protocol["source_policy"]),
        "authorization": {
            key: protocol["authorization"][key]
            for key in (
                "single_candidate_dev64_forward_after_activation",
                "new_exact220_launch",
                "additional_rollout_or_avg4",
                "leaderboard_submission_or_sota_claim",
            )
        },
        "forward_surface": {
            "dependency_manifest": dict(
                protocol["forward_surface"]["dependency_manifest"]
            ),
            "dependency_manifest_sha256": protocol["forward_surface"][
                "dependency_manifest_sha256"
            ],
            "runner_entry": {
                "path": RUNNER_MARKER,
                "sha256": protocol["forward_surface"]["entry_manifest"][
                    RUNNER_MARKER
                ],
            },
            "contract_source": {
                "path": "src/deepwide_agent/v24275_forward_contract.py",
                "sha256": protocol["forward_surface"]["entry_manifest"][
                    "src/deepwide_agent/v24275_forward_contract.py"
                ],
            },
        },
    }
    value["forward_contract_payload_sha256"] = payload_sha256(value)
    return value


def validate_protocol(
    root: Path = ROOT, path: Path = OUTPUT
) -> dict[str, Any]:
    root = root.resolve()
    value = read_object(_ordinary(root, path))
    if (
        value.get("role") != ROLE
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("label_blind") is not True
        or not _sealed(value, "decision_contract_sha256")
        or value.get("task_contract", {}).get("selected_count") != SELECTED_COUNT
        or value.get("task_contract", {}).get("runtime_boundary")
        != ["opaque_id", "question"]
        or value.get("task_contract", {}).get("same_opaque_order_as_frozen_control")
        is not True
        or value.get("forward_contract", {}).get("executor_concurrency")
        != EXECUTOR_CONCURRENCY
        or value.get("forward_contract", {}).get("global_model_slot_cap")
        != MODEL_SLOT_CAP
        or value.get("authorization", {}).get("new_exact220_launch") is not False
        or value.get("authorization", {}).get("leaderboard_submission_or_sota_claim")
        is not False
    ):
        raise RuntimeError("V2.42.75 protocol identity drifted")
    parents = _parents(root)
    for key, path_ in (
        ("frozen_control_protocol", CONTROL_PROTOCOL),
        ("frozen_control_result", CONTROL_RESULT),
        ("frozen_control_postresult_audit", CONTROL_POSTAUDIT),
        ("frozen_control_forward_erratum", CONTROL_FORWARD_ERRATUM),
        ("two_wave_build_audit", BUILD_AUDIT),
        ("neutral_full_task_probe", NEUTRAL_FULL_PROBE),
        ("neutral_capacity_staircase", CAPACITY_STAIRCASE),
        ("neutral_capacity_extension", CAPACITY_EXTENSION),
    ):
        if value["parents"][key]["sha256"] != sha256(root / path_):
            raise RuntimeError(f"V2.42.75 parent hash drifted: {key}")
    if value.get("evaluator_contract") != parents["evaluator"]:
        raise RuntimeError("V2.42.75 evaluator contract drifted")
    for surface in ("forward_surface", "control_surface"):
        manifest = value[surface]["manifest"]
        if payload_sha256(manifest) != value[surface]["manifest_sha256"]:
            raise RuntimeError(f"V2.42.75 {surface} manifest seal drifted")
        for relative, expected in manifest.items():
            if sha256(_ordinary(root, relative)) != expected:
                raise RuntimeError(f"V2.42.75 frozen source drifted: {relative}")
    projection = build_forward_contract(value)
    if (
        value.get("forward_runtime_contract", {}).get("path")
        != str(FORWARD_PROTOCOL)
        or value["forward_runtime_contract"].get("payload_sha256")
        != projection["forward_contract_payload_sha256"]
        or value["forward_runtime_contract"].get(
            "contains_control_mapping_gold_evaluator_or_score_path"
        )
        is not False
    ):
        raise RuntimeError("V2.42.75 forward projection binding drifted")
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    parent = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)


if __name__ == "__main__":
    protocol = build_protocol()
    projection = build_forward_contract(protocol)
    publish_new(ROOT / OUTPUT, protocol)
    publish_new(ROOT / FORWARD_PROTOCOL, projection)
    print(
        json.dumps(
            {
                "protocol": str(OUTPUT),
                "forward_contract": str(FORWARD_PROTOCOL),
                "protocol_sha256": sha256(ROOT / OUTPUT),
                "forward_contract_sha256": sha256(ROOT / FORWARD_PROTOCOL),
            },
            sort_keys=True,
        )
    )
