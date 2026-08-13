"""One-shot contract for the fresh RFC hybrid-record mechanism gate."""

from __future__ import annotations

import ast
import copy
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25068_quote_verified_external_contract as base
from . import v25389_hybrid_record_fallback_runtime as runtime
from . import v25391_fresh_rfc_hybrid_population as population


DATE = "20260813"
PROTOCOL_ID = "v25393_fresh_rfc_hybrid_record_fallback_external_v1"
BUILD_AUDIT = Path(f"results/v25393_rfc_hybrid_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25393_rfc_hybrid_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25393_rfc_hybrid_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25393_rfc_hybrid_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25393_rfc_hybrid_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25393_rfc_hybrid_external_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25393_rfc_hybrid_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "content_free_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_hash_freeze.json"

CONTRACT = Path("src/deepwide_agent/v25393_rfc_hybrid_external_contract.py")
RUNTIME = Path("src/deepwide_agent/v25389_hybrid_record_fallback_runtime.py")
POPULATION = Path("src/deepwide_agent/v25391_fresh_rfc_hybrid_population.py")
RUNNER = Path("scripts/run_v25393_rfc_hybrid_external.py")
CONTROL = Path("scripts/control_v25393_rfc_hybrid_external.py")
TEST = Path("tests/test_v25393_rfc_hybrid_external.py")
CONTROL_TEST = Path("tests/test_control_v25393_rfc_hybrid_external.py")
RUNTIME_TEST = Path("tests/test_v25389_hybrid_record_fallback_runtime.py")
POPULATION_TEST = Path("tests/test_v25391_fresh_rfc_hybrid_population.py")
RUNTIME_AUDIT_TEST = Path("tests/test_audit_v25390_hybrid_record_fallback_build.py")
POPULATION_AUDIT_TEST = Path("tests/test_audit_v25392_fresh_rfc_hybrid_population.py")
HELPER = base.HELPER
LEASE = Path("scripts/deepwide_api_lease.py")
RUNTIME_BUILD_AUDIT = Path(
    "results/v25390_hybrid_record_fallback_build_audit_v1_20260813.json"
)
RUNTIME_BUILD_AUDIT_SHA256 = (
    "272fe9c061bde164b68f6d95abb1900e81d985b8b37ede8d4c950276146a10df"
)
POPULATION_AUDIT = Path(
    "results/v25392_fresh_rfc_hybrid_population_audit_v1_20260813.json"
)
POPULATION_AUDIT_SHA256 = (
    "8d8f615d1674876c2774896eddda9de6c58d934b0c6590365abae289d819956b"
)
FORWARD_SOURCES = (CONTRACT, RUNTIME, POPULATION, RUNNER, HELPER, LEASE)

TASK_COUNT = population.TASK_COUNT
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 8
ARMS = (runtime.CONTROL_ARM, runtime.CANDIDATE_ARM)
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = runtime.PHASES
COLUMNS = population.COLUMNS
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25393_rfc_hybrid_external_forward_v1"
LEASE_PURPOSE = "fresh_outcome_blind_rfc_hybrid_record_mechanism_gate_v1"
EXPECTED_WATCHERS = base.EXPECTED_WATCHERS

MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}
SEARCH = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
    "workers": 1,
    "batch_size": 8,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
}
LIMITS = {
    "wall_seconds": 240,
    "model_calls": 3,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_MODEL_ATTEMPT_SECONDS = 0.05
SECRET = base.SECRET
payload_sha256 = base.payload_sha256
sha256 = base.sha256
seal = base.seal
sealed = base.sealed
git = base.git
ordinary = base.ordinary
watcher_snapshot = base.watcher_snapshot


def task_vector() -> list[dict[str, str]]:
    return population.task_vector()


def validate_task_vector(values: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    return population.validate_task_vector(values)


def source_policy() -> dict[str, Any]:
    return population.source_policy()


def mechanism_gate() -> dict[str, Any]:
    return population.mechanism_gate()


def _module_candidates(relative: Path, node: ast.AST) -> list[Path]:
    return base._module_candidates(relative, node)


def forward_dependency_closure(root: Path) -> tuple[Path, ...]:
    pending = list(FORWARD_SOURCES)
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = ordinary(root, relative, tracked=False)
        observed.add(relative)
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for candidate in _module_candidates(relative, node):
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {
        *forward_dependency_closure(root), CONTROL, TEST, CONTROL_TEST,
        RUNTIME_TEST, POPULATION_TEST, RUNTIME_AUDIT_TEST,
        POPULATION_AUDIT_TEST, RUNTIME_BUILD_AUDIT, POPULATION_AUDIT,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if path.suffix == ".py" and SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.53.93 credential literal in dependency manifest")
        output[str(relative)] = sha256(path)
    return output


def future_surfaces() -> tuple[Path, ...]:
    return (PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)


def build_protocol(
    root: Path, *, now: int, tracked: bool, require_pristine: bool,
    build_audit_sha256: str,
) -> dict[str, Any]:
    head = git(root, "rev-parse", "HEAD")
    target = git(root, "rev-parse", "target/main")
    if require_pristine and (
        git(root, "status", "--porcelain")
        or head != target
        or any((root / path).exists() or (root / path).is_symlink() for path in future_surfaces())
    ):
        raise RuntimeError("V2.53.93 protocol surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25393_rfc_hybrid_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": head,
        "target_main": target,
        "build_audit_sha256": str(build_audit_sha256),
        "runtime_build_audit": {
            "path": str(RUNTIME_BUILD_AUDIT),
            "sha256": sha256(root / RUNTIME_BUILD_AUDIT),
        },
        "population_audit": {
            "path": str(POPULATION_AUDIT),
            "sha256": sha256(root / POPULATION_AUDIT),
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "population": {
            "task_count": TASK_COUNT,
            "rows_per_task": population.ROWS_PER_TASK,
            "identity_count": len(population.identity_vector()),
            "task_vector_sha256": payload_sha256(tasks),
            "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
            "freshness_parent_commit": population.FRESHNESS_PARENT_COMMIT,
            "consecutive_indivisible_group": True,
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "physical_caps": {
                "queries": 4, "fetches": 14,
                "normal_path_model_forwards": 3, "outer_hard_model_cap": 4,
            },
            "single_task_attempt": True,
            "retry_resume_skip_backfill_replacement": False,
            "one_final_joint_table_record_synthesis": True,
            "record_source_priority": ["nonempty_joint", "nonempty_grounded", "none"],
            "record_source_selection_before_verification": True,
            "record_source_merge_or_union": False,
            "verification_outcome_fallthrough": False,
            "candidate_model_forward_count": 0,
            "persist_prediction_hashes_not_prediction_text": True,
        },
        "failure_gate_semantics": {
            "fixed_terminal_denominator": TASK_COUNT,
            "failure_as_zero_allowed": mechanism_gate()["maximum_failure_as_zero_tasks"],
            "budget_rejection_allowed": 0,
            "exact_physical_budget_applies_to_completed_rows": True,
            "failure_rows_retain_partial_effects_and_per_task_hard_caps": True,
        },
        "source_policy": source_policy(),
        "mechanism_gate": mechanism_gate(),
        "protected_watchers": watcher_snapshot(),
        "authorization": {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "one_external_forward": False,
            "evaluator": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value, tracked=tracked)


def validate_protocol(
    root: Path, value: Mapping[str, Any], *, tracked: bool = True
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("protocol_payload_sha256", None)
    manifest = copied.get("source_manifest")
    expected_population = {
        "task_count": TASK_COUNT,
        "rows_per_task": population.ROWS_PER_TASK,
        "identity_count": TASK_COUNT * population.ROWS_PER_TASK,
        "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
        "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
        "freshness_parent_commit": population.FRESHNESS_PARENT_COMMIT,
        "consecutive_indivisible_group": True,
    }
    expected_execution = {
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "model": MODEL,
        "search": SEARCH,
        "limits": LIMITS,
        "physical_caps": {
            "queries": 4, "fetches": 14,
            "normal_path_model_forwards": 3, "outer_hard_model_cap": 4,
        },
        "single_task_attempt": True,
        "retry_resume_skip_backfill_replacement": False,
        "one_final_joint_table_record_synthesis": True,
        "record_source_priority": ["nonempty_joint", "nonempty_grounded", "none"],
        "record_source_selection_before_verification": True,
        "record_source_merge_or_union": False,
        "verification_outcome_fallthrough": False,
        "candidate_model_forward_count": 0,
        "persist_prediction_hashes_not_prediction_text": True,
    }
    expected_failure = {
        "fixed_terminal_denominator": TASK_COUNT,
        "failure_as_zero_allowed": mechanism_gate()["maximum_failure_as_zero_tasks"],
        "budget_rejection_allowed": 0,
        "exact_physical_budget_applies_to_completed_rows": True,
        "failure_rows_retain_partial_effects_and_per_task_hard_caps": True,
    }
    expected_authorization = {
        "preactivation_audit_generation": True,
        "execution_start_generation": False,
        "one_external_forward": False,
        "evaluator": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
    }
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25393_rfc_hybrid_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("git_head") != copied.get("target_main")
        or re.fullmatch(r"[0-9a-f]{64}", str(copied.get("build_audit_sha256"))) is None
        or copied.get("runtime_build_audit") != {
            "path": str(RUNTIME_BUILD_AUDIT), "sha256": RUNTIME_BUILD_AUDIT_SHA256,
        }
        or copied.get("population_audit") != {
            "path": str(POPULATION_AUDIT), "sha256": POPULATION_AUDIT_SHA256,
        }
        or not isinstance(manifest, Mapping)
        or dict(manifest) != dependency_manifest(root, tracked=tracked)
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("population") != expected_population
        or copied.get("execution") != expected_execution
        or copied.get("failure_gate_semantics") != expected_failure
        or copied.get("source_policy") != source_policy()
        or copied.get("mechanism_gate") != mechanism_gate()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("authorization") != expected_authorization
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.93 external protocol drifted")
    return copied


__all__ = [
    "ARMS", "BUILD_AUDIT", "CANDIDATE_ARM", "COLUMNS", "CONTROL_ARM",
    "EXECUTION_START", "EXECUTOR_CONCURRENCY", "FORWARD_AUDIT", "FORWARD_RESULT",
    "LIMITS", "MODEL", "MODEL_SLOT_CAP", "MODEL_SLOT_DIRECTORY", "OUTPUT_ROOT",
    "PHASES", "POPULATION_AUDIT", "PREDICTION_FREEZE", "PREAUDIT", "PROTOCOL",
    "PROTOCOL_ID", "RUNNER", "SEARCH", "TASK_COUNT", "TASK_ROWS", "build_protocol",
    "dependency_manifest", "forward_dependency_closure", "future_surfaces",
    "mechanism_gate", "source_policy", "task_vector", "validate_protocol",
    "validate_task_vector",
]
