#!/usr/bin/env python3
"""Freeze and activate the V2.43.30 shared-prefix paired exact-220 run."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24330_forward_contract import (  # noqa: E402
    ACTIVATION,
    ARMS,
    CHILD_MARKER,
    CHILD_TERMINAL_NAME,
    EVALUATOR_LEASE_OWNER,
    EVALUATOR_LEASE_PURPOSE,
    EVALUATOR_GATE,
    EVALUATOR_ROOT,
    EVALUATOR_START,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FETCH_HELPER_MARKER,
    FINAL_RESULT,
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
    OUTPUT_ROOT,
    PAIR_SUMMARY,
    PARENT_EXIT_NAME,
    PARENT_TIMEOUT_SECONDS,
    POSTAUDIT,
    PREAUDIT,
    PREDICTION_FREEZE,
    PROTOCOL,
    PROTOCOL_ID,
    ROLE,
    RUNNER_MARKER,
    RUNTIME_PREDICTIONS,
    RUN_SUMMARY,
    SAFE_PROGRESS,
    SEARCH,
    SELECTED_COUNT,
    SOURCE_MANIFEST,
    TASK_ROOT,
    payload_sha256,
    protected_watcher_snapshot,
    read_object,
    selected_tasks,
    sha256,
    source_selected_ids,
    source_selected_shards,
    validate_forward_contract,
)
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.deepwide_api_lease import DEFAULT_RELATIVE_PATH  # noqa: E402


CAPACITY_DECISION = Path(
    "results/v24329_capacity_continuation_decision_v1_20260803.json"
)
CAPACITY_AUDIT = Path(
    "results/v24329_capacity_continuation_postresult_audit_v1_20260803.json"
)
TRANSPORT_DECISION = Path(
    "results/v24327_neutral_transport_decision_v1_20260803.json"
)
TRANSPORT_AUDIT = Path(
    "results/v24327_neutral_transport_postresult_audit_v1_20260803.json"
)
RUNTIME_AUDIT = Path(
    "results/v24326_runner_integration_build_audit_v1_20260803.json"
)
EVALUATOR_IDENTITY_PARENT = Path(
    "results/v24287_exact220_preregistration_v1_20260803.json"
)
BEST_FULL220 = Path("results/v24267_exact220_result_v1_20260802.json")

EVALUATOR_WORKERS_PER_ARM = 8
TOTAL_EVALUATOR_WORKERS = 16
MAPPING_PATH = Path("outputs/runtime_manifest_v1_repro/evaluator_mapping.jsonl")
BOOTSTRAP_SEED = 24330
BOOTSTRAP_RESAMPLES = 10_000
DECISION_CONTRACT = {
    "primary_report_group": "test_156",
    "secondary_complete_group": "all_220",
    "minimum_test156_quality_composite_delta": 0.0,
    "minimum_test156_entity_acc_delta": -0.01,
    "minimum_test156_f1_by_row_delta": 0.0,
    "minimum_test156_f1_by_item_delta": 0.0,
    "minimum_test156_column_f1_delta": 0.0,
    "minimum_all220_quality_composite_delta": 0.0,
    "minimum_all220_whole_table_success_delta": 0,
    "minimum_candidate_all220_whole_table_successes": 8,
    "minimum_candidate_all220_quality_composite": 0.4135414180682089,
    "maximum_candidate_evaluator_invalid_or_not_run": 14,
    "maximum_candidate_minus_baseline_evaluator_invalid": 2,
    "maximum_failed_pair_tasks": 5,
    "minimum_candidate_nonidentity_tasks": 1,
    "minimum_admitted_cell_changes": 1,
    "minimum_credited_conditional_entropy_reduction_nats": 0.000001,
    "required_repeated_upstream_effects": 0,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 4,
    "maximum_fetch_helper_failures": 4,
    "maximum_hosted_search_deadline_failures": 4,
    "maximum_fetch_deadline_rejections": 4,
    "maximum_deadline_exhausted_tasks": 4,
    "minimum_test156_paired_bootstrap_95_lower_bound": -0.03,
    "maximum_test156_paired_bootstrap_95_interval_width": 0.10,
    "minimum_test156_paired_median_delta": 0.0,
    "paired_bootstrap_seed": BOOTSTRAP_SEED,
    "paired_bootstrap_resamples": BOOTSTRAP_RESAMPLES,
}

SECRET = re.compile(
    r"(?<![A-Za-z0-9])(?:ghp_|github_pat_|tvly-dev-|sk-)[A-Za-z0-9_-]{16,}"
)
OPAQUE_LITERAL = re.compile(r"task_[0-9a-f]{24}")
PRIVILEGED = frozenset(
    {
        "benchmark_question_type",
        "question_type",
        "task_category",
        "category",
        "split",
        "ground_truth",
        "gold",
        "answer_key",
        "mapping",
        "evaluator",
        "score",
        "reward",
        "results.csv",
    }
)

FORWARD_FILES = (
    "src/deepwide_agent/__init__.py",
    "src/deepwide_agent/clients.py",
    "src/deepwide_agent/native_search.py",
    "src/deepwide_agent/v24257_score_first_runtime.py",
    "src/deepwide_agent/v24259_deterministic_table_normalizer.py",
    "src/deepwide_agent/v24263_global_model_limiter.py",
    "src/deepwide_agent/v24269_task_union_discovery.py",
    "src/deepwide_agent/v24286_visible_schema_runtime.py",
    "src/deepwide_agent/v24287_hard_deadline_fetch.py",
    "src/deepwide_agent/v24308_child_exit_observability.py",
    "src/deepwide_agent/v24309_runner_exit_integration.py",
    "src/deepwide_agent/v24312_deadline_reliability.py",
    "src/deepwide_agent/v24313_runner_integration.py",
    "src/deepwide_agent/v24315_forward_contract.py",
    "src/deepwide_agent/v24316_deadline_search.py",
    "src/deepwide_agent/v24320_forward_contract.py",
    "src/deepwide_agent/v24323_shared_prefix_cell_entropy.py",
    "src/deepwide_agent/v24324_shared_prefix_runner.py",
    "src/deepwide_agent/v24325_shared_prefix_revision_runtime.py",
    "src/deepwide_agent/v24326_runner_integration.py",
    "src/deepwide_agent/v24330_forward_contract.py",
    "scripts/run_v24287_fetch_helper.py",
    "scripts/run_v24330_shared_prefix_exact220_task.py",
    "scripts/run_v24330_shared_prefix_exact220.py",
    "scripts/deepwide_api_lease.py",
)
CONTROL_FILES = (
    "scripts/v24330_shared_prefix_exact220_control.py",
    "scripts/finalize_v24330_shared_prefix_exact220.py",
    "scripts/run_official_eval_local.py",
    "scripts/finalize_fullset_rollout.py",
    "scripts/audit_v24187_phase_liveness.py",
    "scripts/audit_v24195_lease_owner_compatibility.py",
    "tests/test_v24330_shared_prefix_exact220.py",
    "tests/test_finalize_v24330_shared_prefix_exact220.py",
)
FOCUSED_TESTS = (
    "test_v24330_shared_prefix_exact220.py",
    "test_finalize_v24330_shared_prefix_exact220.py",
    "test_v24326_runner_integration.py",
    "test_v24326_subprocess_integration.py",
    "test_v24325_shared_prefix_revision_runtime.py",
    "test_v24316_deadline_search.py",
    "test_v24312_deadline_reliability.py",
    "test_v24309_runner_exit_integration.py",
    "test_v24308_child_exit_observability.py",
)
FUTURE_PATHS = (
    PREAUDIT,
    ACTIVATION,
    EXECUTION_START,
    FORWARD_RESULT,
    EVALUATOR_GATE,
    EVALUATOR_START,
    FINAL_RESULT,
    POSTAUDIT,
    OUTPUT_ROOT,
)


def _ordinary(root: Path, relative: str | Path) -> Path:
    raw = Path(relative)
    path = root / raw
    if (
        raw.is_absolute()
        or ".." in raw.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.43.30 expected ordinary file: {relative}")
    return path


def _read(root: Path, relative: str | Path) -> dict[str, Any]:
    return read_object(_ordinary(root, relative))


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _manifest(
    root: Path, files: tuple[str, ...], *, reject_opaque_literals: bool
) -> dict[str, str]:
    output: dict[str, str] = {}
    for relative in files:
        path = _ordinary(root, relative)
        source = path.read_text(encoding="utf-8")
        if SECRET.search(source):
            raise RuntimeError(f"V2.43.30 credential literal in {relative}")
        if reject_opaque_literals and OPAQUE_LITERAL.search(source):
            raise RuntimeError(f"V2.43.30 opaque task literal in {relative}")
        output[relative] = sha256(path)
    return output


def _field_accesses(root: Path) -> list[str]:
    hits: list[str] = []
    for relative in FORWARD_FILES:
        path = _ordinary(root, relative)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            key: str | None = None
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "get"
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                key = node.args[0].value
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and isinstance(node.slice.value, str)
            ):
                key = node.slice.value
            if key is not None and key.casefold() in PRIVILEGED:
                if relative == "src/deepwide_agent/clients.py" and key.casefold() == "score":
                    continue
                hits.append(f"{relative}:{node.lineno}:{key}")
    return sorted(hits)


def _import_hits(root: Path) -> list[str]:
    hits: list[str] = []
    forbidden = ("finalize", "official_eval", "evaluator", "mapping")
    for relative in FORWARD_FILES:
        path = _ordinary(root, relative)
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                names.append(node.module or "")
        for name in names:
            if any(token in name.casefold() for token in forbidden):
                hits.append(f"{relative}:{name}")
    return sorted(hits)


def _run_tests() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for filename in FOCUSED_TESTS:
        completed = subprocess.run(
            [
                str(ROOT / ".venv-eval/bin/python"),
                "-I",
                "-B",
                "-m",
                "unittest",
                "discover",
                "-s",
                "tests",
                "-p",
                filename,
            ],
            cwd=ROOT,
            env={
                "HOME": str(Path.home()),
                "USER": os.environ.get("USER", "azureuser"),
                "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
            },
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=300,
            check=False,
            text=True,
        )
        count = 0
        match = re.search(r"Ran (\d+) tests?", completed.stdout)
        if match:
            count = int(match.group(1))
        output.append(
            {
                "file": filename,
                "passed": completed.returncode == 0,
                "test_count": count,
            }
        )
    return output


def _port_listening() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 9878), timeout=0.5):
            return True
    except OSError:
        return False


def _git_output(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _parent_evidence(root: Path) -> dict[str, Any]:
    capacity = _read(root, CAPACITY_DECISION)
    capacity_audit = _read(root, CAPACITY_AUDIT)
    transport = _read(root, TRANSPORT_DECISION)
    transport_audit = _read(root, TRANSPORT_AUDIT)
    runtime = _read(root, RUNTIME_AUDIT)
    best = _read(root, BEST_FULL220)
    if (
        capacity.get("status") != "capacity_continuation_go"
        or capacity.get("passed") is not True
        or capacity.get("recommended_executor_count") != EXECUTOR_CONCURRENCY
        or capacity.get("authorization", {}).get(
            "fresh_shared_prefix_paired_benchmark_protocol_design"
        )
        is not True
        or not _sealed(capacity, "decision_payload_sha256")
        or capacity_audit.get("audit_valid") is not True
        or capacity_audit.get("findings") != []
        or not _sealed(capacity_audit, "audit_payload_sha256")
        or transport.get("status") != "neutral_transport_go"
        or transport.get("passed") is not True
        or not _sealed(transport, "decision_payload_sha256")
        or transport_audit.get("audit_valid") is not True
        or transport_audit.get("findings") != []
        or not _sealed(transport_audit, "audit_payload_sha256")
        or runtime.get("role") != "v24326_runner_integration_build_audit"
        or runtime.get("audit_valid") is not True
        or runtime.get("findings") != []
        or not _sealed(runtime, "audit_payload_sha256")
        or best.get("metrics", {}).get("whole_table_successes") != 7
        or best.get("claims", {}).get("sota") is not False
    ):
        raise RuntimeError("V2.43.30 parent evidence drifted")
    return {
        "capacity": capacity,
        "capacity_audit": capacity_audit,
        "transport": transport,
        "transport_audit": transport_audit,
        "runtime": runtime,
        "best": best,
    }


def _evaluator_contract(root: Path) -> dict[str, Any]:
    parent = _read(root, EVALUATOR_IDENTITY_PARENT)
    evaluator = parent.get("evaluator_contract")
    if (
        parent.get("role") != "v24287_exact220_preregistration"
        or not isinstance(evaluator, Mapping)
        or evaluator.get("mapping_query_answer_or_gold_bytes_opened_or_hashed")
        is not False
    ):
        raise RuntimeError("V2.43.30 evaluator identity parent drifted")
    return dict(evaluator)


def build_forward_contract(
    root: Path = ROOT,
    *,
    now: int | None = None,
    require_pristine: bool = True,
) -> dict[str, Any]:
    root = root.resolve()
    _parent_evidence(root)
    present = [
        str(path)
        for path in FUTURE_PATHS
        if (root / path).exists() or (root / path).is_symlink()
    ]
    if require_pristine and present:
        raise RuntimeError(f"V2.43.30 future surface is not pristine: {present}")
    ids = source_selected_ids(root)
    shards = source_selected_shards(root)
    forward = _manifest(root, FORWARD_FILES, reject_opaque_literals=True)
    value = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "label_blind": True,
        "parents": {
            str(path): sha256(root / path)
            for path in (
                CAPACITY_DECISION,
                CAPACITY_AUDIT,
                TRANSPORT_DECISION,
                TRANSPORT_AUDIT,
                RUNTIME_AUDIT,
            )
        },
        "task_contract": {
            "manifest_path": str(SOURCE_MANIFEST),
            "manifest_sha256": sha256(_ordinary(root, SOURCE_MANIFEST)),
            "runtime_boundary": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "selected_opaque_ids": ids,
            "selected_opaque_ids_sha256": payload_sha256(ids),
            "partitions": [
                {
                    "tag": tag,
                    "path": str(relative),
                    "sha256": sha256(_ordinary(root, relative)),
                    "count": expected,
                }
                for tag, relative, expected in ID_SOURCES
            ],
            "partition_vector_sha256": payload_sha256(
                [{"tag": tag, "ids": values} for tag, values in shards]
            ),
            "selection_rule": "exact frozen test_s01,test_s02,test_s03,devval opaque-ID order",
            "public_reused_tasks_not_unseen_or_strict_held_out": True,
            "mapping_split_category_gold_score_used_for_selection": False,
        },
        "execution": {
            "runner_marker": RUNNER_MARKER,
            "child_marker": CHILD_MARKER,
            "fetch_helper_marker": FETCH_HELPER_MARKER,
            "output_root": str(OUTPUT_ROOT),
            "model_slot_directory": str(MODEL_SLOT_DIRECTORY),
            "task_root": str(TASK_ROOT),
            "runtime_predictions": {
                arm: str(RUNTIME_PREDICTIONS[arm]) for arm in ARMS
            },
            "run_summary": {arm: str(RUN_SUMMARY[arm]) for arm in ARMS},
            "prediction_freeze": {
                arm: str(PREDICTION_FREEZE[arm]) for arm in ARMS
            },
            "pair_summary": str(PAIR_SUMMARY),
            "safe_progress": str(SAFE_PROGRESS),
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model_slot_pool_id": MODEL_SLOT_POOL_ID,
            "one_shared_prefix_forward_per_visible_task": True,
            "two_predictions_from_each_single_task_forward": True,
            "resume_skip_rerun_or_selective_retry": False,
            "protected_watchers": protected_watcher_snapshot(),
        },
        "limits": dict(LIMITS),
        "model": dict(MODEL),
        "search": dict(SEARCH),
        "parent_timeout_seconds": PARENT_TIMEOUT_SECONDS,
        "lease": {
            "path": str(LEASE_PATH),
            "owner": LEASE_OWNER,
            "purpose": LEASE_PURPOSE,
            "nonblocking_single_owner": True,
        },
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "evaluator_surface_absent_from_forward_dependency_manifest": True,
            "both_arm_220_prediction_freezes_before_evaluator_resources_open": True,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "forward_terminal_contract": {
            "required_terminal_pair_tasks": SELECTED_COUNT,
            "required_prediction_rows_per_arm": SELECTED_COUNT,
            "required_valid_parent_exit_receipts": SELECTED_COUNT,
            "forward_failure_policy": "both_arms_failure_as_zero_no_task_rerun",
            "maximum_model_effects_per_pair": 3,
            "maximum_logical_queries_per_pair": 4,
            "maximum_fetch_targets_per_pair": 10,
            "required_repeated_upstream_effects": 0,
            "mapping_or_evaluator_open_before_both_freezes": False,
        },
        "authorization": {
            "single_fresh_shared_prefix_paired_exact220_forward": True,
            "additional_rollout_resume_or_rerun": False,
        },
        "dependency_manifest": forward,
        "dependency_manifest_sha256": payload_sha256(forward),
    }
    value["forward_contract_payload_sha256"] = payload_sha256(value)
    return value


def build_protocol(
    root: Path = ROOT,
    *,
    forward: Mapping[str, Any] | None = None,
    now: int | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    frozen = dict(forward) if forward is not None else validate_forward_contract(root)
    controls = _manifest(root, CONTROL_FILES, reject_opaque_literals=False)
    evaluator = _evaluator_contract(root)
    value = {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_contract_sha256": (
            None if forward is not None else sha256(root / FORWARD_CONTRACT)
        ),
        "selected_pair_tasks": SELECTED_COUNT,
        "prediction_rows_per_arm": SELECTED_COUNT,
        "forward_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "evaluator_workers_per_arm": EVALUATOR_WORKERS_PER_ARM,
        "total_evaluator_workers": TOTAL_EVALUATOR_WORKERS,
        "comparison_contract": {
            "single_shared_prefix_forward_per_task": True,
            "baseline_core_only_candidate_entropy_gated_reserve": True,
            "baseline_rows_never_deleted": True,
            "unsupported_candidate_changes_revert_to_baseline": True,
            "both_arms_frozen_before_mapping_or_evaluator_open": True,
            "same_task_forward_failure_counts_zero_for_both_arms": True,
            "no_single_arm_retry_or_revaluation": True,
            "public_reused_tasks_not_unseen_or_strict_held_out": True,
            "test156_primary_mechanism_report_not_future_population_claim": True,
            "all220_complete_secondary_report": True,
        },
        "evaluation_contract": {
            "fixed_eight_contiguous_workers_per_arm": True,
            "all_frozen_completed_predictions_evaluated_once": True,
            "forward_and_evaluator_failure_as_zero": True,
            "catastrophic_worker_failure_becomes_terminal_error_rows_no_retry": True,
            "selective_retry_error_revaluation_or_prediction_selection": False,
            "report_groups": ["test_156", "all_220"],
            "conservative_denominators": {"test_156": 156, "all_220": 220},
        },
        "decision_contract": dict(DECISION_CONTRACT),
        "evaluator_contract": evaluator,
        "lease_contract": {
            "path": str(LEASE_PATH),
            "forward_owner": LEASE_OWNER,
            "forward_purpose": LEASE_PURPOSE,
            "evaluator_owner": EVALUATOR_LEASE_OWNER,
            "evaluator_purpose": EVALUATOR_LEASE_PURPOSE,
        },
        "outputs": {
            "forward_contract": str(FORWARD_CONTRACT),
            "preactivation_audit": str(PREAUDIT),
            "activation": str(ACTIVATION),
            "execution_start": str(EXECUTION_START),
            "forward_result": str(FORWARD_RESULT),
            "evaluator_gate": str(EVALUATOR_GATE),
            "evaluator_start": str(EVALUATOR_START),
            "evaluator_root": str(EVALUATOR_ROOT),
            "final_result": str(FINAL_RESULT),
            "postresult_audit": str(POSTAUDIT),
        },
        "control_manifest": controls,
        "control_manifest_sha256": payload_sha256(controls),
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "forward_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "mapping_query_answer_evaluator_open_only_after_both_220_freezes": True,
            "same_run_evaluator_feedback_used_for_forward_or_prediction_selection": False,
        },
        "claims": {
            "fresh_execution": True,
            "public_task_set_reused": True,
            "historically_unseen_or_strict_held_out": False,
            "future_population_inference": False,
            "avg_at_4": False,
            "leaderboard_submission": False,
            "sota_claim_before_result": False,
        },
        "authorization": {
            "single_shared_prefix_paired_exact220_forward": True,
            "postfreeze_both_arm_exact220_evaluation": True,
            "additional_rollout_resume_skip_selective_retry": False,
            "avg_at_4": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return value


def validate_protocol(
    root: Path = ROOT,
    *,
    value: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    protocol = dict(value) if value is not None else _read(root, PROTOCOL)
    controls = protocol.get("control_manifest")
    if (
        protocol.get("role") != "v24330_shared_prefix_exact220_preregistration"
        or protocol.get("protocol_id") != PROTOCOL_ID
        or protocol.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or protocol.get("selected_pair_tasks") != SELECTED_COUNT
        or protocol.get("prediction_rows_per_arm") != SELECTED_COUNT
        or protocol.get("forward_concurrency") != EXECUTOR_CONCURRENCY
        or protocol.get("model_slot_cap") != MODEL_SLOT_CAP
        or protocol.get("evaluator_workers_per_arm") != EVALUATOR_WORKERS_PER_ARM
        or protocol.get("total_evaluator_workers") != TOTAL_EVALUATOR_WORKERS
        or protocol.get("comparison_contract", {}).get(
            "single_shared_prefix_forward_per_task"
        )
        is not True
        or protocol.get("comparison_contract", {}).get(
            "both_arms_frozen_before_mapping_or_evaluator_open"
        )
        is not True
        or protocol.get("comparison_contract", {}).get(
            "public_reused_tasks_not_unseen_or_strict_held_out"
        )
        is not True
        or protocol.get("decision_contract") != DECISION_CONTRACT
        or protocol.get("evaluator_contract") != _evaluator_contract(root)
        or protocol.get("source_policy", {}).get(
            "forward_mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or protocol.get("claims", {}).get("historically_unseen_or_strict_held_out")
        is not False
        or protocol.get("authorization", {}).get("sota_claim") is not False
        or not isinstance(controls, Mapping)
        or protocol.get("control_manifest_sha256") != payload_sha256(controls)
        or not _sealed(protocol, "protocol_payload_sha256")
    ):
        raise RuntimeError("V2.43.30 protocol identity drifted")
    for relative, digest in controls.items():
        if sha256(_ordinary(root, relative)) != digest:
            raise RuntimeError(f"V2.43.30 control dependency drifted: {relative}")
    validate_forward_contract(root)
    return protocol


def build_preaudit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    protocol = validate_protocol(root)
    future = (ACTIVATION, EXECUTION_START, FORWARD_RESULT, FINAL_RESULT, POSTAUDIT, OUTPUT_ROOT)
    pristine = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in future
    )
    tests = _run_tests()
    accesses = _field_accesses(root)
    imports = _import_hits(root)
    lease = lease_observation(root, Path("/proc"))
    port = _port_listening()
    watchers = protected_watcher_snapshot()
    findings: list[str] = []
    if not pristine:
        findings.append("future_surface_not_pristine")
    if not all(item["passed"] for item in tests):
        findings.append("focused_or_dependency_tests_failed")
    if accesses:
        findings.append("privileged_field_access_in_forward_surface")
    if imports:
        findings.append("evaluator_or_mapping_import_in_forward_surface")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if not port:
        findings.append("keyless_proxy_not_listening")
    if len(selected_tasks(root, contract)) != SELECTED_COUNT:
        findings.append("visible_exact220_task_boundary_invalid")
    value = {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_preactivation_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "protocol_sha256": sha256(root / PROTOCOL),
        "dependency_manifest_sha256": contract["dependency_manifest_sha256"],
        "control_manifest_sha256": protocol["control_manifest_sha256"],
        "focused_tests": tests,
        "privileged_field_accesses": accesses,
        "forbidden_forward_imports": imports,
        "checks": {
            "forward_contract_valid_and_sealed": True,
            "protocol_valid_and_sealed": True,
            "exact220_visible_only_tasks_validated": True,
            "one_shared_prefix_pair_per_task": True,
            "both_arm_failure_as_zero_outer_totality_tested": True,
            "evaluator_import_absent_from_forward_surface": not imports,
            "privileged_field_access_absent_from_forward_surface": not accesses,
            "focused_tests_passed": all(item["passed"] for item in tests),
            "keyless_proxy_listening_without_api_request": port,
            "shared_api_lease_inactive": lease.get("active") is False,
            "future_surface_pristine": pristine,
        },
        "protected_watchers": watchers,
        "findings": findings,
        "audit_valid": not findings,
        "launch_authorized": not findings,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "authorization": {
            "single_shared_prefix_paired_exact220_launch": not findings,
            "postfreeze_evaluator": False,
            "additional_rollout_or_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def validate_preaudit(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, PREAUDIT)
    if (
        value.get("role") != "v24330_shared_prefix_exact220_preactivation_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("launch_authorized") is not True
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("protected_watchers") != protected_watcher_snapshot()
        or value.get("privileged_field_accesses") != []
        or value.get("forbidden_forward_imports") != []
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or value.get("authorization", {}).get(
            "single_shared_prefix_paired_exact220_launch"
        )
        is not True
        or any(
            enabled
            for key, enabled in value.get("authorization", {}).items()
            if key != "single_shared_prefix_paired_exact220_launch"
        )
        or not _sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.43.30 preactivation audit drifted")
    validate_protocol(root)
    return value


def build_activation(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    validate_protocol(root)
    preaudit = validate_preaudit(root)
    lease = lease_observation(root, Path("/proc"))
    future = (ACTIVATION, EXECUTION_START, FORWARD_RESULT, FINAL_RESULT, POSTAUDIT, OUTPUT_ROOT)
    findings: list[str] = []
    if any((root / path).exists() or (root / path).is_symlink() for path in future):
        findings.append("activation_or_execution_surface_not_pristine")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_activation",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "active" if not findings else "rejected",
        "findings": findings,
        "launch_authorized": not findings,
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "dependency_manifest_sha256": contract["dependency_manifest_sha256"],
        "control_manifest_sha256": preaudit["control_manifest_sha256"],
        "selected_pair_tasks": SELECTED_COUNT,
        "prediction_rows_per_arm": SELECTED_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": contract["execution"]["protected_watchers"],
        "shared_api_lease_active_before_activation": lease.get("active") is True,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "runtime_input_exactly_opaque_id_and_question": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "authorization": {
            "single_shared_prefix_paired_exact220_launch": not findings,
            "postfreeze_evaluator": False,
            "additional_rollout_or_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["activation_payload_sha256"] = payload_sha256(value)
    return value


def validate_activation(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, ACTIVATION)
    contract = validate_forward_contract(root)
    if (
        value.get("role") != "v24330_shared_prefix_exact220_activation"
        or value.get("status") != "active"
        or value.get("findings") != []
        or value.get("launch_authorized") is not True
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or value.get("selected_pair_tasks") != SELECTED_COUNT
        or value.get("prediction_rows_per_arm") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("protected_watchers")
        != contract["execution"]["protected_watchers"]
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or value.get("authorization", {}).get(
            "single_shared_prefix_paired_exact220_launch"
        )
        is not True
        or any(
            enabled
            for key, enabled in value.get("authorization", {}).items()
            if key != "single_shared_prefix_paired_exact220_launch"
        )
        or not _sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.43.30 activation drifted")
    validate_preaudit(root)
    return value


def build_execution_start(
    root: Path = ROOT, *, now: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    activation = validate_activation(root)
    future = (EXECUTION_START, FORWARD_RESULT, FINAL_RESULT, POSTAUDIT, OUTPUT_ROOT)
    if any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise RuntimeError("V2.43.30 execution surface is not pristine")
    head = _git_output(root, "rev-parse", "HEAD")
    remote = _git_output(root, "rev-parse", "target/main")
    lease = lease_observation(root, Path("/proc"))
    findings: list[str] = []
    if head != remote:
        findings.append("activation_commit_not_pushed")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active")
    if not _port_listening():
        findings.append("keyless_proxy_not_listening")
    value = {
        "artifact_version": 1,
        "role": "v24330_shared_prefix_exact220_execution_start",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "ready" if not findings else "rejected",
        "findings": findings,
        "execution_authorized": not findings,
        "activation_base_commit": head,
        "target_main_at_start": remote,
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "protocol_sha256": sha256(root / PROTOCOL),
        "activation_sha256": sha256(root / ACTIVATION),
        "selected": SELECTED_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "protected_watchers": contract["execution"]["protected_watchers"],
        "shared_api_lease_active_before_execution_start": lease.get("active")
        is True,
        "api_called_before_execution_start": False,
        "runtime_input_exactly_opaque_id_and_question": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "benchmark_evaluator_or_additional_rollout_authorized": False,
    }
    value["execution_start_payload_sha256"] = payload_sha256(value)
    return value


def validate_execution_start(root: Path = ROOT) -> dict[str, Any]:
    root = root.resolve()
    value = _read(root, EXECUTION_START)
    contract = validate_forward_contract(root)
    if (
        value.get("role") != "v24330_shared_prefix_exact220_execution_start"
        or value.get("status") != "ready"
        or value.get("findings") != []
        or value.get("execution_authorized") is not True
        or value.get("forward_contract_sha256") != sha256(root / FORWARD_CONTRACT)
        or value.get("protocol_sha256") != sha256(root / PROTOCOL)
        or value.get("activation_sha256") != sha256(root / ACTIVATION)
        or value.get("selected") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("model_slot_cap") != MODEL_SLOT_CAP
        or value.get("protected_watchers")
        != contract["execution"]["protected_watchers"]
        or value.get("api_called_before_execution_start") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read")
        is not False
        or value.get("benchmark_evaluator_or_additional_rollout_authorized")
        is not False
        or not _sealed(value, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.43.30 execution-start drifted")
    validate_activation(root)
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "activation", "start"))
    args = parser.parse_args()
    if args.command == "protocol":
        forward = build_forward_contract()
        publish(ROOT / FORWARD_CONTRACT, forward)
        protocol = build_protocol()
        publish(ROOT / PROTOCOL, protocol)
        publish(ROOT / PREAUDIT, build_preaudit())
    elif args.command == "activation":
        publish(ROOT / ACTIVATION, build_activation())
    else:
        publish(ROOT / EXECUTION_START, build_execution_start())
    print(json.dumps({"command": args.command, "status": "ok"}, sort_keys=True))


if __name__ == "__main__":
    main()
