"""Frozen one-shot contract for the repaired mechanism on fresh PEPs.

This successor combines the V2.53.54 pre-effect query-contract repair with
the V2.53.56 second disjoint visible-PEP population.  It preserves the paired
shared-page counterfactual, equal-length quote-verified fact-prefix treatment,
and physical 4-query/14-fetch/4-model envelope.  No evaluator, hidden mapping,
benchmark label, or signed entropy credit is part of this contract.
"""

from __future__ import annotations

import ast
import copy
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25068_quote_verified_external_contract as base
from . import v25354_pre_effect_query_compatible_grounded_fact_runtime as runtime
from . import v25356_second_fresh_pep_grounded_fact_population as population


DATE = "20260813"
PROTOCOL_ID = "v25358_repaired_second_fresh_pep_external_v1"
BUILD_AUDIT = Path(
    f"results/v25358_repaired_second_fresh_pep_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v25358_repaired_second_fresh_pep_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v25358_repaired_second_fresh_pep_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25358_repaired_second_fresh_pep_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v25358_repaired_second_fresh_pep_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v25358_repaired_second_fresh_pep_forward_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v25358_repaired_second_fresh_pep_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"

CONTRACT = Path(
    "src/deepwide_agent/v25358_repaired_second_fresh_pep_external_contract.py"
)
RUNTIME = Path(
    "src/deepwide_agent/v25354_pre_effect_query_compatible_grounded_fact_runtime.py"
)
POPULATION = Path(
    "src/deepwide_agent/v25356_second_fresh_pep_grounded_fact_population.py"
)
RUNNER = Path("scripts/run_v25358_repaired_second_fresh_pep_external.py")
CONTROL = Path("scripts/control_v25358_repaired_second_fresh_pep_external.py")
TEST = Path("tests/test_v25358_repaired_second_fresh_pep_external.py")
CONTROL_TEST = Path("tests/test_control_v25358_repaired_second_fresh_pep_external.py")
RUNTIME_TEST = Path(
    "tests/test_v25354_pre_effect_query_compatible_grounded_fact_runtime.py"
)
POPULATION_TEST = Path(
    "tests/test_v25356_second_fresh_pep_grounded_fact_population.py"
)
HELPER = base.HELPER
LEASE = Path("scripts/deepwide_api_lease.py")
PARENT_BUILD_AUDIT = Path(
    "results/v25350_shared_prefix_grounded_fact_paired_build_audit_v1_20260813.json"
)
PARENT_BUILD_AUDIT_SHA256 = (
    "72eea8f9712d02dc770784790404c6922e21893a996b5fe37b58d0ac3787cf2c"
)
DIAGNOSIS = Path(
    "results/v25355_v25353_pre_effect_query_contract_diagnosis_v1_20260813.json"
)
DIAGNOSIS_SHA256 = (
    "20c2b8e655c02186deee2418a84f177ca68a6603267cc6baadb610551638227b"
)
POPULATION_AUDIT = Path(
    "results/v25357_second_fresh_pep_population_selection_audit_v1_20260813.json"
)
POPULATION_AUDIT_SHA256 = (
    "98774f6b73bb00e513c5259b8c8fe14b8fa01150dde7b68962c34ac5707c0811"
)
FORWARD_SOURCES = (CONTRACT, RUNTIME, POPULATION, RUNNER, HELPER, LEASE)

TASK_COUNT = population.TASK_COUNT
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 16
ARMS = runtime.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
PHASES = runtime.PHASES
COLUMNS = population.COLUMNS
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25358_repaired_second_fresh_pep_forward_v1"
LEASE_PURPOSE = "repaired_second_fresh_pep_grounded_fact_gate_v1"
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


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    return population.validate_task_vector(values)


def arm_order_vector() -> list[list[str]]:
    return population.arm_order_vector()


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
        *forward_dependency_closure(root),
        CONTROL,
        TEST,
        CONTROL_TEST,
        RUNTIME_TEST,
        POPULATION_TEST,
        PARENT_BUILD_AUDIT,
        DIAGNOSIS,
        POPULATION_AUDIT,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if path.suffix == ".py" and SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.53.58 credential literal in dependency manifest")
        output[str(relative)] = sha256(path)
    return output


def _future_surfaces() -> tuple[Path, ...]:
    return (
        PROTOCOL,
        PREAUDIT,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        OUTPUT_ROOT,
    )


def build_protocol(
    root: Path,
    *,
    now: int,
    tracked: bool,
    require_pristine: bool,
    build_audit_sha256: str,
) -> dict[str, Any]:
    head = git(root, "rev-parse", "HEAD")
    target = git(root, "rev-parse", "target/main")
    if require_pristine and (
        git(root, "status", "--porcelain")
        or head != target
        or any((root / path).exists() or (root / path).is_symlink() for path in _future_surfaces())
    ):
        raise RuntimeError("V2.53.58 protocol surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    orders = arm_order_vector()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25358_repaired_second_fresh_pep_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": head,
        "target_main": target,
        "build_audit_sha256": str(build_audit_sha256),
        "parent_build_audit": {
            "path": str(PARENT_BUILD_AUDIT),
            "sha256": sha256(root / PARENT_BUILD_AUDIT),
        },
        "diagnosis": {
            "path": str(DIAGNOSIS),
            "sha256": sha256(root / DIAGNOSIS),
        },
        "population_audit": {
            "path": str(POPULATION_AUDIT),
            "sha256": sha256(root / POPULATION_AUDIT),
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "population": {
            "task_count": TASK_COUNT,
            "task_vector_sha256": payload_sha256(tasks),
            "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
            "arm_order_vector_sha256": payload_sha256(orders),
            "candidate_first_tasks": sum(
                order[0] == CANDIDATE_ARM for order in orders
            ),
            "freshness_parent_commit": population.FRESHNESS_PARENT_COMMIT,
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "physical_caps": {"queries": 4, "fetches": 14, "model_forwards": 4},
            "single_task_attempt": True,
            "retry_resume_skip_backfill_replacement": False,
            "pre_effect_query_projection_required": True,
        },
        "failure_gate_semantics": {
            "fixed_terminal_denominator": TASK_COUNT,
            "failure_as_zero_allowed": mechanism_gate()[
                "maximum_failure_as_zero_tasks"
            ],
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
    root: Path,
    value: Mapping[str, Any],
    *,
    tracked: bool = True,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("protocol_payload_sha256", None)
    manifest = copied.get("source_manifest")
    expected_population = {
        "task_count": TASK_COUNT,
        "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
        "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
        "arm_order_vector_sha256": population.EXPECTED_ARM_ORDER_VECTOR_SHA256,
        "candidate_first_tasks": TASK_COUNT // 2,
        "freshness_parent_commit": population.FRESHNESS_PARENT_COMMIT,
    }
    expected_execution = {
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "model": MODEL,
        "search": SEARCH,
        "limits": LIMITS,
        "physical_caps": {"queries": 4, "fetches": 14, "model_forwards": 4},
        "single_task_attempt": True,
        "retry_resume_skip_backfill_replacement": False,
        "pre_effect_query_projection_required": True,
    }
    expected_failure_semantics = {
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
        set(copied)
        != {
            "artifact_version",
            "role",
            "protocol_id",
            "created_at_unix",
            "git_head",
            "target_main",
            "build_audit_sha256",
            "parent_build_audit",
            "diagnosis",
            "population_audit",
            "source_manifest",
            "source_manifest_sha256",
            "population",
            "execution",
            "failure_gate_semantics",
            "source_policy",
            "mechanism_gate",
            "protected_watchers",
            "authorization",
            "protocol_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25358_repaired_second_fresh_pep_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("git_head") != copied.get("target_main")
        or not isinstance(copied.get("build_audit_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", copied["build_audit_sha256"]) is None
        or copied.get("parent_build_audit")
        != {"path": str(PARENT_BUILD_AUDIT), "sha256": PARENT_BUILD_AUDIT_SHA256}
        or copied.get("diagnosis")
        != {"path": str(DIAGNOSIS), "sha256": DIAGNOSIS_SHA256}
        or copied.get("population_audit")
        != {"path": str(POPULATION_AUDIT), "sha256": POPULATION_AUDIT_SHA256}
        or not isinstance(manifest, Mapping)
        or dict(manifest) != dependency_manifest(root, tracked=tracked)
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("population") != expected_population
        or copied.get("execution") != expected_execution
        or copied.get("failure_gate_semantics") != expected_failure_semantics
        or copied.get("source_policy") != source_policy()
        or copied.get("mechanism_gate") != mechanism_gate()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("authorization") != expected_authorization
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.58 external protocol drifted")
    return copied


__all__ = [
    "ARMS",
    "BUILD_AUDIT",
    "CANDIDATE_ARM",
    "COLUMNS",
    "CONTROL_ARM",
    "DIAGNOSIS",
    "EXECUTION_START",
    "FORWARD_AUDIT",
    "FORWARD_RESULT",
    "LIMITS",
    "MODEL",
    "MODEL_SLOT_CAP",
    "MODEL_SLOT_DIRECTORY",
    "OUTPUT_ROOT",
    "PHASES",
    "POPULATION_AUDIT",
    "PREAUDIT",
    "PROTOCOL",
    "PROTOCOL_ID",
    "RUNNER",
    "SEARCH",
    "TASK_COUNT",
    "TASK_ROWS",
    "PREDICTION_FREEZE",
    "arm_order_vector",
    "build_protocol",
    "dependency_manifest",
    "forward_dependency_closure",
    "mechanism_gate",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "validate_task_vector",
]
