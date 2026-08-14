"""One-shot external contract for the fresh constraint-totality gate.

The forward boundary is restricted to the frozen V2.55.70 visible tasks and
same-forward public pages.  V2.55.69 contributes only a deterministic local
projection or a byte-exact parent handoff; neither arm receives an independent
provider call.  Truth, evaluator output, benchmark labels, and historical
outcomes are outside the forward dependency closure.
"""

from __future__ import annotations

import ast
import copy
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25068_quote_verified_external_contract as base
from . import v25558_model_pool_contract as model_pool
from . import v25569_constraint_totality_safe_handoff_runtime as runtime
from . import v25570_fresh_totality_population as population


DATE = "20260814"
PROTOCOL_ID = "v25571_fresh_constraint_totality_external_v1"
BUILD_AUDIT = Path(f"results/v25571_fresh_totality_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25571_fresh_totality_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25571_fresh_totality_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25571_fresh_totality_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25571_fresh_totality_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25571_fresh_totality_forward_audit_v1_{DATE}.json")
POSTFREEZE_QUALITY_PROTOCOL = Path(
    f"results/v25572_fresh_totality_quality_preregistration_v1_{DATE}.json"
)
QUALITY_RESULT = Path(f"results/v25572_fresh_totality_quality_result_v1_{DATE}.json")
QUALITY_AUDIT = Path(f"results/v25572_fresh_totality_quality_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25571_fresh_totality_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"

CONTRACT = Path("src/deepwide_agent/v25571_fresh_totality_external_contract.py")
RUNTIME = Path("src/deepwide_agent/v25569_constraint_totality_safe_handoff_runtime.py")
POPULATION = Path("src/deepwide_agent/v25570_fresh_totality_population.py")
RUNNER = Path("scripts/run_v25571_fresh_totality_external.py")
CONTROL = Path("scripts/control_v25571_fresh_totality_external.py")
TEST = Path("tests/test_v25571_fresh_totality_external.py")
CONTROL_TEST = Path("tests/test_control_v25571_fresh_totality_external.py")
RUNTIME_TEST = Path("tests/test_v25569_constraint_totality_safe_handoff_runtime.py")
POPULATION_TEST = Path("tests/test_v25570_fresh_totality_population.py")
POPULATION_AUDIT_TEST = Path("tests/test_audit_v25570_fresh_totality_population.py")
MODEL_POOL_TEST = Path("tests/test_v25558_model_pool_contract.py")
CLONE_HELPER = Path("scripts/v25478_clone_safe_runner_namespace.py")
CLONE_HELPER_TEST = Path("tests/test_v25478_clone_safe_runner_namespace.py")
HELPER = base.HELPER
LEASE = Path("scripts/deepwide_api_lease.py")

RUNTIME_IMPLEMENTATION_COMMIT = "665322378a92d4d78b3f7fe55a9c397a679591ec"
RUNTIME_SHA256 = "3e87be159f9771e154cfc995ff782141e8ed7a2264c037c4b562e5aa1ec2127b"
POPULATION_AUDIT = Path(
    "results/v25570_fresh_totality_population_build_audit_v1_20260814.json"
)
POPULATION_AUDIT_SHA256 = (
    "9f82b5fc7ca39c8361f380354c5557ca91f0a2208d9a1f76a7c35b297bc181e2"
)

FORWARD_SOURCES = (
    CONTRACT,
    RUNTIME,
    POPULATION,
    RUNNER,
    CLONE_HELPER,
    HELPER,
    LEASE,
)
TASK_COUNT = population.TASK_COUNT
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 16
PHASES = runtime.PHASES
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25571_fresh_constraint_totality_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_constraint_totality_gate_v1"
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
    copied = [dict(value) for value in values]
    if copied != population.task_vector():
        raise ValueError("V2.55.71 task vector drifted")
    return copied


def source_policy() -> dict[str, Any]:
    return {
        **population.source_policy(),
        "one_v25401_parent_forward_shared_by_control_and_candidate": True,
        "control_is_parent_prediction_byte_exact": True,
        "candidate_is_strict_projection_or_byte_exact_parent_handoff": True,
        "projection_nonadmission_never_becomes_unknown_fallback": True,
        "internal_receipt_binding_or_projector_failure_contained": False,
        "independent_sampling_between_arms": False,
        "candidate_additional_queries_fetches_model_calls_tokens_context_wall_or_network": 0,
        "historical_parent_replay_routes_or_filters_fresh_forward": False,
        "evaluator_truth_totality_absent_from_forward_dependency_closure": True,
        "fixed_failure_as_zero_denominator_no_retry_resume_or_replacement": True,
        "clone_namespace_assembled_from_actual_source_function_globals": True,
        "model_pool_policy_id": model_pool.POLICY_ID,
        "model_pool_id": model_pool.MODEL_POOL_ID,
        "prediction_freeze_precedes_truth_evaluator_or_quality_decision": True,
    }


def mechanism_gate() -> dict[str, Any]:
    return copy.deepcopy(population.mechanism_gate())


def quality_gate() -> dict[str, Any]:
    return copy.deepcopy(population.quality_gate())


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
        POPULATION_AUDIT_TEST,
        MODEL_POOL_TEST,
        CLONE_HELPER_TEST,
        POPULATION_AUDIT,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if path.suffix == ".py" and SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.55.71 credential literal in dependency manifest")
        output[str(relative)] = sha256(path)
    return output


def future_surfaces() -> tuple[Path, ...]:
    return (
        PROTOCOL,
        PREAUDIT,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        POSTFREEZE_QUALITY_PROTOCOL,
        QUALITY_RESULT,
        QUALITY_AUDIT,
        OUTPUT_ROOT,
    )


def population_contract() -> dict[str, Any]:
    return {
        "task_count": TASK_COUNT,
        "identity_count": 40,
        "date_task_count": population.DATE_TASK_COUNT,
        "scale_task_count": population.SCALE_TASK_COUNT,
        "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
        "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
        "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
        "question_overlap_with_fixed220": 0,
        "opaque_id_overlap_with_fixed220": 0,
        "prior_population_or_execution_reused": False,
    }


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
        or any((root / path).exists() or (root / path).is_symlink() for path in future_surfaces())
    ):
        raise RuntimeError("V2.55.71 protocol surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25571_fresh_totality_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": head,
        "target_main": target,
        "build_audit_sha256": str(build_audit_sha256),
        "runtime_implementation": {
            "commit": RUNTIME_IMPLEMENTATION_COMMIT,
            "path": str(RUNTIME),
            "sha256": RUNTIME_SHA256,
        },
        "population_audit": {
            "path": str(POPULATION_AUDIT),
            "sha256": POPULATION_AUDIT_SHA256,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "population": population_contract(),
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "physical_caps": {
                "queries": 4,
                "fetches": 14,
                "maximum_normal_path_model_forwards": 3,
            },
            "single_task_attempt": True,
            "retry_resume_skip_backfill_replacement": False,
            "runtime_policy_id": runtime.POLICY_ID,
            "parent_policy_id": runtime.parent.POLICY_ID,
            "constraint_policy_id": runtime.contracts.POLICY_ID,
            "strict_projection_policy_id": runtime.constrained.POLICY_ID,
            "projector_policy_id": runtime.constrained.projector.POLICY_ID,
            "clone_namespace_policy_id": "v25478_clone_safe_runner_namespace_v1",
            "model_pool_policy_id": model_pool.POLICY_ID,
            "model_pool_id": model_pool.MODEL_POOL_ID,
            "one_parent_forward_per_task": True,
            "control_and_candidate_share_all_provider_retrieval_and_sampling_effects": True,
            "candidate_additional_queries_fetches_model_calls_or_sampling_effects": 0,
            "persist_both_prediction_texts_for_postfreeze_quality": True,
        },
        "failure_gate_semantics": {
            "fixed_terminal_denominator": TASK_COUNT,
            "outer_failure_allowed": 0,
            "budget_rejection_allowed": 0,
            "unsafe_handoff_allowed": 0,
            "failure_rows_retain_partial_effects_and_per_task_hard_caps": True,
        },
        "source_policy": source_policy(),
        "mechanism_gate": mechanism_gate(),
        "postfreeze_quality_gate": quality_gate(),
        "protected_watchers": watcher_snapshot(),
        "authorization": {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "one_external_forward": False,
            "postfreeze_quality": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    return validate_protocol(root, seal(value, "protocol_payload_sha256"), tracked=tracked)


def validate_protocol(
    root: Path, value: Mapping[str, Any], *, tracked: bool = True
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    manifest = copied.get("source_manifest")
    execution = copied.get("execution") or {}
    expected_authorization = {
        "preactivation_audit_generation": True,
        "execution_start_generation": False,
        "one_external_forward": False,
        "postfreeze_quality": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
    }
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25571_fresh_totality_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("git_head") != copied.get("target_main")
        or re.fullmatch(r"[0-9a-f]{64}", str(copied.get("build_audit_sha256"))) is None
        or copied.get("runtime_implementation")
        != {"commit": RUNTIME_IMPLEMENTATION_COMMIT, "path": str(RUNTIME), "sha256": RUNTIME_SHA256}
        or copied.get("population_audit")
        != {"path": str(POPULATION_AUDIT), "sha256": POPULATION_AUDIT_SHA256}
        or not isinstance(manifest, Mapping)
        or dict(manifest) != dependency_manifest(root, tracked=tracked)
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("population") != population_contract()
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("limits") != LIMITS
        or execution.get("physical_caps")
        != {"queries": 4, "fetches": 14, "maximum_normal_path_model_forwards": 3}
        or execution.get("single_task_attempt") is not True
        or execution.get("retry_resume_skip_backfill_replacement") is not False
        or execution.get("runtime_policy_id") != runtime.POLICY_ID
        or execution.get("parent_policy_id") != runtime.parent.POLICY_ID
        or execution.get("constraint_policy_id") != runtime.contracts.POLICY_ID
        or execution.get("strict_projection_policy_id") != runtime.constrained.POLICY_ID
        or execution.get("projector_policy_id") != runtime.constrained.projector.POLICY_ID
        or execution.get("clone_namespace_policy_id") != "v25478_clone_safe_runner_namespace_v1"
        or execution.get("model_pool_policy_id") != model_pool.POLICY_ID
        or execution.get("model_pool_id") != model_pool.MODEL_POOL_ID
        or execution.get("one_parent_forward_per_task") is not True
        or execution.get("control_and_candidate_share_all_provider_retrieval_and_sampling_effects") is not True
        or execution.get("candidate_additional_queries_fetches_model_calls_or_sampling_effects") != 0
        or execution.get("persist_both_prediction_texts_for_postfreeze_quality") is not True
        or copied.get("failure_gate_semantics")
        != {
            "fixed_terminal_denominator": 20,
            "outer_failure_allowed": 0,
            "budget_rejection_allowed": 0,
            "unsafe_handoff_allowed": 0,
            "failure_rows_retain_partial_effects_and_per_task_hard_caps": True,
        }
        or copied.get("source_policy") != source_policy()
        or copied.get("mechanism_gate") != mechanism_gate()
        or copied.get("postfreeze_quality_gate") != quality_gate()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("authorization") != expected_authorization
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise ValueError("V2.55.71 external protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "forward_dependency_closure",
    "future_surfaces",
    "mechanism_gate",
    "model_pool",
    "population",
    "population_contract",
    "quality_gate",
    "runtime",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "validate_task_vector",
]
