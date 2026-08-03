#!/usr/bin/env python3
"""Freeze the V2.43.15 exact-220 forward and post-freeze evaluator contracts."""

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

from deepwide_agent.v24315_forward_contract import (  # noqa: E402
    ACTIVATION,
    ARM,
    CHILD_MARKER,
    CHILD_TERMINAL_NAME,
    CLEANUP_RESERVE_SECONDS,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FETCH_HELPER_MARKER,
    FORWARD_CONTRACT,
    FORWARD_RESULT,
    ID_SOURCES,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    LIMITS,
    MODEL,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    MODEL_SLOT_POOL_ID,
    MINIMUM_MODEL_ATTEMPT_SECONDS,
    OUTPUT_ROOT,
    PARENT_DEADLINE_GRACE_SECONDS,
    PARENT_EXIT_NAME,
    PREDICTION_FREEZE,
    PREAUDIT,
    PROTOCOL_ID,
    ROLE,
    RUNTIME_PREDICTIONS,
    RUNNER_MARKER,
    RUN_SUMMARY,
    SAFE_PROGRESS,
    SEARCH,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    TASK_ROOT,
    TWO_WAVE_POLICY,
    RESERVE_POLICY,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    sha256,
    source_selected_ids,
    source_selected_shards,
    validate_forward_contract,
)


PROTOCOL = Path("results/v24315_exact220_preregistration_v1_20260803.json")
FINAL_RESULT = Path("results/v24315_exact220_result_v1_20260803.json")
POSTAUDIT = Path("results/v24315_exact220_postresult_audit_v1_20260803.json")
EVALUATOR_ROOT = OUTPUT_ROOT / "evaluator"
EVALUATOR_WORKERS = 8
V24314_PROTOCOL = Path("results/v24314_paired_dev64_preregistration_v1_20260803.json")
V24314_RESULT = Path("results/v24314_paired_dev64_result_v1_20260803.json")
V24314_AUDIT = Path("results/v24314_paired_dev64_postresult_audit_v1_20260803.json")
V24313_DECISION = Path("results/v24313_runner_integration_decision_v1_20260803.json")
V24313_AUDIT = Path("results/v24313_runner_integration_postresult_audit_v1_20260803.json")
RUNNER_SMOKE = Path("results/v24315_exact220_runner_smoke_v1_20260803.json")
SECRET = re.compile(r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}")
OPAQUE = re.compile(r"task_[0-9a-f]{24}")

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
    "src/deepwide_agent/v24272_two_wave_entropy_voc.py",
    "src/deepwide_agent/v24272_two_wave_retrieval.py",
    "src/deepwide_agent/v24273_two_wave_task_runtime.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24289_low_coverage_rescue.py",
    "src/deepwide_agent/v24290_low_coverage_task_runtime.py",
    "src/deepwide_agent/v24294_staged_reserve.py",
    "src/deepwide_agent/v24296_staged_reserve_task_runtime.py",
    "src/deepwide_agent/v24299_synthesis_recovery.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24310_paired_dev_runtime.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24313_runner_integration.py",
    "src/deepwide_agent/v24315_forward_contract.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/run_v24315_exact220_task.py",
    "scripts/run_v24315_exact220.py",
    "scripts/deepwide_api_lease.py",
)
CONTROL_FILES = (
    "scripts/preregister_v24315_exact220.py",
    "scripts/probe_v24315_exact220_runner.py",
    "scripts/audit_v24315_exact220.py",
    "scripts/activate_v24315_exact220.py",
    "scripts/finalize_v24315_exact220.py",
    "scripts/run_official_eval_local.py",
    "scripts/finalize_fullset_rollout.py",
    "scripts/audit_v24187_phase_liveness.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "scripts/preregister_v24259_deterministic_normalizer_smoke.py",
    "tests/test_v24310_paired_dev_runtime.py",
    "tests/test_v24312_deadline_reliability.py",
    "tests/test_v24313_runner_integration.py",
    "tests/test_v24315_exact220.py",
    "tests/fixtures/v24315_synthetic_child.py",
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


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    if raw.is_absolute() or ".." in raw.parts:
        raise RuntimeError("V2.43.15 preregistration path is noncanonical")
    path = root / raw
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise RuntimeError(f"V2.43.15 expected ordinary file: {relative}")
    return path


def _manifest(root: Path, files: tuple[str, ...]) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source) or (not relative.startswith("tests/") and OPAQUE.search(source)):
            raise RuntimeError(f"V2.43.15 unsafe frozen source: {relative}")
        output[relative] = sha256(path)
    return output


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _parent_evaluator_contract(root: Path) -> dict[str, Any]:
    protocol = read_object(_ordinary(root, V24314_PROTOCOL))
    result = read_object(_ordinary(root, V24314_RESULT))
    audit = read_object(_ordinary(root, V24314_AUDIT))
    if (
        protocol.get("role") != "v24314_paired_dev64_preregistration"
        or not _sealed(protocol, "protocol_payload_sha256")
        or result.get("status") != "development_gate_go"
        or not _sealed(result, "result_payload_sha256")
        or result.get("decision", {}).get("status") != "go"
        or result.get("decision", {}).get("passed") is not True
        or result.get("decision", {}).get("go_scope")
        != "fresh_exact220_design_only_not_launch"
        or result.get("authorization", {}).get("fresh_exact220_design") is not True
        or result.get("authorization", {}).get("fresh_exact220_launch") is not False
        or audit.get("audit_valid") is not True
        or not _sealed(audit, "audit_payload_sha256")
        or audit.get("findings") != []
        or audit.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward"
        )
        is not False
    ):
        raise RuntimeError("V2.43.15 exact-220 parent drifted")
    evaluator = protocol.get("evaluator_contract")
    if not isinstance(evaluator, dict):
        raise RuntimeError("V2.43.15 parent evaluator contract is absent")
    return dict(evaluator)


def build_forward_contract(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    present = [str(path) for path in FUTURE_PATHS if (root / path).exists() or (root / path).is_symlink()]
    if require_pristine and present:
        raise RuntimeError(f"V2.43.15 future surface is not pristine: {present}")
    paired = read_object(_ordinary(root, V24314_RESULT))
    paired_audit = read_object(_ordinary(root, V24314_AUDIT))
    integration = read_object(_ordinary(root, V24313_DECISION))
    integration_audit = read_object(_ordinary(root, V24313_AUDIT))
    smoke = read_object(_ordinary(root, RUNNER_SMOKE))
    if (
        paired.get("status") != "development_gate_go"
        or not _sealed(paired, "result_payload_sha256")
        or paired.get("decision", {}).get("status") != "go"
        or paired.get("decision", {}).get("passed") is not True
        or paired.get("authorization", {}).get("fresh_exact220_design") is not True
        or paired.get("authorization", {}).get("fresh_exact220_launch") is not False
        or paired_audit.get("audit_valid") is not True
        or paired_audit.get("findings") != []
        or not _sealed(paired_audit, "audit_payload_sha256")
        or integration.get("status") != "neutral_runner_integration_go"
        or not _sealed(integration, "decision_payload_sha256")
        or integration.get("passed") is not True
        or integration_audit.get("audit_valid") is not True
        or integration_audit.get("findings") != []
        or not _sealed(integration_audit, "audit_payload_sha256")
        or smoke.get("role")
        != "v24315_exact220_runner_benchmark_external_smoke"
        or smoke.get("passed") is not True
        or not _sealed(smoke, "report_payload_sha256")
        or smoke.get("findings") != []
        or smoke.get("external_effect_ledger")
        != {"network": 0, "model": 0, "search": 0, "fetch": 0, "evaluator": 0}
        or smoke.get("authorization", {}).get("benchmark_launch") is not False
    ):
        raise RuntimeError("V2.43.15 parent evidence drifted")
    ids = source_selected_ids(root)
    shards = source_selected_shards(root)
    forward = _manifest(root, FORWARD_FILES)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parents": {
            "v24314_paired_dev64_result": {"path": str(V24314_RESULT), "sha256": sha256(root / V24314_RESULT)},
            "v24314_postresult_audit": {"path": str(V24314_AUDIT), "sha256": sha256(root / V24314_AUDIT)},
            "v24313_runner_integration_decision": {"path": str(V24313_DECISION), "sha256": sha256(root / V24313_DECISION)},
            "v24313_runner_integration_postresult_audit": {"path": str(V24313_AUDIT), "sha256": sha256(root / V24313_AUDIT)},
            "v24315_benchmark_external_runner_smoke": {"path": str(RUNNER_SMOKE), "sha256": sha256(root / RUNNER_SMOKE)},
            "historical_dev64_result_and_audit_opened_for_successor_authorization": True,
            "same_run_exact220_prediction_mapping_gold_evaluator_or_score_opened_or_hashed": False,
        },
        "task_contract": {
            "manifest_path": str(SOURCE_MANIFEST),
            "manifest_sha256": sha256(_ordinary(root, SOURCE_MANIFEST)),
            "runtime_boundary": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "selected_opaque_ids": ids,
            "selected_opaque_ids_sha256": payload_sha256(ids),
            "partitions": [
                {"tag": tag, "path": str(relative), "sha256": sha256(_ordinary(root, relative)), "count": expected}
                for tag, relative, expected in ID_SOURCES
            ],
            "partition_vector_sha256": payload_sha256([{"tag": tag, "ids": values} for tag, values in shards]),
            "selection_rule": "exact frozen test_s01, test_s02, test_s03, then devval opaque-ID order",
            "mapping_split_category_gold_score_used_for_selection": False,
        },
        "execution": {
            "arm": ARM,
            "runner_marker": RUNNER_MARKER,
            "child_marker": CHILD_MARKER,
            "fetch_helper_marker": FETCH_HELPER_MARKER,
            "output_root": str(OUTPUT_ROOT),
            "model_slot_directory": str(MODEL_SLOT_DIRECTORY),
            "task_root": str(TASK_ROOT),
            "runtime_predictions": str(RUNTIME_PREDICTIONS),
            "run_summary": str(RUN_SUMMARY),
            "prediction_freeze": str(PREDICTION_FREEZE),
            "safe_progress": str(SAFE_PROGRESS),
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model_slot_pool_id": MODEL_SLOT_POOL_ID,
            "child_terminal_receipt_name": CHILD_TERMINAL_NAME,
            "parent_exit_receipt_name": PARENT_EXIT_NAME,
            "protected_watchers": protected_watcher_snapshot(),
            "one_cold_forward_per_visible_task": True,
            "resume_skip_rerun_or_selective_retry": False,
        },
        "limits": dict(LIMITS),
        "two_wave_policy": dict(TWO_WAVE_POLICY),
        "reserve_policy": dict(RESERVE_POLICY),
        "deadline_contract": {
            "cleanup_reserve_seconds": CLEANUP_RESERVE_SECONDS,
            "minimum_model_attempt_seconds": MINIMUM_MODEL_ATTEMPT_SECONDS,
            "parent_deadline_grace_seconds": PARENT_DEADLINE_GRACE_SECONDS,
        },
        "model": dict(MODEL),
        "search": dict(SEARCH),
        "lease": {"path": str(LEASE_PATH), "owner": LEASE_OWNER, "purpose": LEASE_PURPOSE, "nonblocking_single_owner": True},
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "evaluator_surface_absent_from_forward_dependency_manifest": True,
            "all_220_predictions_frozen_before_evaluator_resources_open": True,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "forward_acceptance_gate": {
            "required_terminal_predictions": SELECTED_COUNT,
            "required_parent_exit_receipts": SELECTED_COUNT,
            "required_valid_child_terminal_receipts": SELECTED_COUNT,
            "required_valid_model_slot_receipts": SELECTED_COUNT,
            "required_valid_transport_receipts": SELECTED_COUNT,
            "maximum_non_success_parent_exits": 0,
            "maximum_incomplete_effect_counts": 0,
            "maximum_fourth_model_effects": 0,
        },
        "authorization": {"single_fresh_exact220_forward": True, "additional_rollout_or_rerun": False},
        "dependency_manifest": forward,
        "dependency_manifest_sha256": payload_sha256(forward),
    }
    value["forward_contract_payload_sha256"] = payload_sha256(value)
    return value


def build_protocol(
    root: Path = ROOT, *, now: int | None = None, require_pristine: bool = True
) -> dict[str, Any]:
    root = root.resolve()
    del require_pristine
    forward = validate_forward_contract(root)
    controls = _manifest(root, CONTROL_FILES)
    evaluator = _parent_evaluator_contract(root)
    value = {
        "artifact_version": 1,
        "role": "v24315_exact220_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "selected_count": SELECTED_COUNT,
        "forward_concurrency": EXECUTOR_CONCURRENCY,
        "forward_acceptance_gate": dict(forward["forward_acceptance_gate"]),
        "evaluator_workers": EVALUATOR_WORKERS,
        "evaluator_contract": evaluator,
        "evaluation_contract": {
            "all_220_predictions_frozen_before_mapping_query_answer_or_evaluator_open": True,
            "fixed_contiguous_eight_way_partition_in_prediction_order": True,
            "official_evaluator_on_every_frozen_prediction_exactly_once": True,
            "worker_error_rows_are_terminal_failure_as_zero": True,
            "selective_retry_revaluation_or_prediction_selection": False,
            "report_groups": ["test_156", "dev_validation_64", "all_220"],
            "conservative_denominators": {"test_156": 156, "all_220": 220},
        },
        "outputs": {
            "forward_contract": str(FORWARD_CONTRACT),
            "preactivation_audit": str(PREAUDIT),
            "activation": str(ACTIVATION),
            "execution_start": str(EXECUTION_START),
            "forward_result": str(FORWARD_RESULT),
            "evaluator_root": str(EVALUATOR_ROOT),
            "final_result": str(FINAL_RESULT),
            "postresult_audit": str(POSTAUDIT),
        },
        "control_manifest": controls,
        "control_manifest_sha256": payload_sha256(controls),
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "forward_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "authorization": {
            "single_fresh_exact220_forward": True,
            "post_freeze_exact220_evaluation": True,
            "additional_rollout_avg4_leaderboard_submission_or_sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return value


def validate_protocol(root: Path = ROOT, path: Path = PROTOCOL) -> dict[str, Any]:
    root = root.resolve()
    value = read_object(_ordinary(root, path))
    forward = validate_forward_contract(root)
    unsigned = dict(value)
    seal = unsigned.pop("protocol_payload_sha256", None)
    if (
        value.get("role") != "v24315_exact220_preregistration"
        or value.get("protocol_id") != PROTOCOL_ID
        or value.get("selected_count") != SELECTED_COUNT
        or value.get("forward_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("forward_acceptance_gate")
        != forward["forward_acceptance_gate"]
        or value.get("evaluator_workers") != EVALUATOR_WORKERS
        or value.get("authorization", {}).get("additional_rollout_avg4_leaderboard_submission_or_sota_claim") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.43.15 preregistration identity drifted")
    if value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT):
        raise RuntimeError("V2.43.15 forward/preregistration binding drifted")
    if value.get("evaluator_contract") != _parent_evaluator_contract(root):
        raise RuntimeError("V2.43.15 evaluator contract drifted")
    manifest = value.get("control_manifest")
    if not isinstance(manifest, dict) or value.get("control_manifest_sha256") != payload_sha256(manifest):
        raise RuntimeError("V2.43.15 control manifest seal drifted")
    for relative, digest in manifest.items():
        if sha256(_ordinary(root, relative)) != digest:
            raise RuntimeError(f"V2.43.15 frozen control dependency drifted: {relative}")
    return value


def publish_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    forward = build_forward_contract()
    publish_new(ROOT / FORWARD_CONTRACT, forward)
    protocol = build_protocol()
    publish_new(ROOT / PROTOCOL, protocol)
    print(json.dumps({"forward_contract": str(FORWARD_CONTRACT), "protocol": str(PROTOCOL)}, sort_keys=True))
