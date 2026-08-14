"""One-shot contract for the fresh deterministic visible-constraint gate."""

from __future__ import annotations

import ast
import copy
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25068_quote_verified_external_contract as base
from . import v25545_deterministic_visible_constraint_runtime as runtime
from . import v25547_fresh_visible_constraint_population as population


DATE = "20260814"
PROTOCOL_ID = "v25550_fresh_deterministic_visible_constraint_external_v1"
BUILD_AUDIT = Path(f"results/v25550_visible_constraint_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25550_visible_constraint_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25550_visible_constraint_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25550_visible_constraint_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25550_visible_constraint_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25550_visible_constraint_external_forward_audit_v1_{DATE}.json")
POSTFREEZE_QUALITY_PROTOCOL = Path(f"results/v25550_visible_constraint_quality_preregistration_v1_{DATE}.json")
QUALITY_RESULT = Path(f"results/v25550_visible_constraint_quality_result_v1_{DATE}.json")
QUALITY_AUDIT = Path(f"results/v25550_visible_constraint_quality_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25550_visible_constraint_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"

CONTRACT = Path("src/deepwide_agent/v25550_visible_constraint_external_contract.py")
RUNTIME = Path("src/deepwide_agent/v25545_deterministic_visible_constraint_runtime.py")
POPULATION = Path("src/deepwide_agent/v25547_fresh_visible_constraint_population.py")
RUNNER = Path("scripts/run_v25550_visible_constraint_external.py")
CONTROL = Path("scripts/control_v25550_visible_constraint_external.py")
TEST = Path("tests/test_v25550_visible_constraint_external.py")
CONTROL_TEST = Path("tests/test_control_v25550_visible_constraint_external.py")
RUNTIME_TEST = Path("tests/test_v25545_deterministic_visible_constraint_runtime.py")
PROJECTOR_TEST = Path("tests/test_v25544_deterministic_visible_constraint_projector.py")
POPULATION_TEST = Path("tests/test_v25547_fresh_visible_constraint_population.py")
BUILD_AUDIT_TEST = Path("tests/test_audit_v25549_scale_sort_guard_build.py")
POPULATION_AUDIT_TEST = Path("tests/test_audit_v25548_fresh_visible_constraint_population.py")
CLONE_HELPER = Path("scripts/v25478_clone_safe_runner_namespace.py")
CLONE_HELPER_TEST = Path("tests/test_v25478_clone_safe_runner_namespace.py")
HELPER = base.HELPER
LEASE = Path("scripts/deepwide_api_lease.py")
RUNTIME_BUILD_AUDIT = Path("results/v25549_scale_sort_guard_build_audit_v1_20260814.json")
RUNTIME_BUILD_AUDIT_SHA256 = "fe72a1db83b946fbae056851fd43679d41169fc4399c57617ab3fde12515b5cb"
POPULATION_AUDIT = Path("results/v25548_fresh_visible_constraint_population_audit_v1_20260814.json")
POPULATION_AUDIT_SHA256 = "a28395efad2f0772508a722752fb1a305fe64f58868664474798ebbf9b639d5f"

FORWARD_SOURCES = (CONTRACT, RUNTIME, POPULATION, RUNNER, CLONE_HELPER, HELPER, LEASE)
TASK_COUNT = population.TASK_COUNT
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 16
PHASES = runtime.PHASES
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25550_visible_constraint_external_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_deterministic_visible_constraint_gate_v1"
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
        raise ValueError("V2.55.50 task vector drifted")
    return copied


def source_policy() -> dict[str, Any]:
    return {
        **population.source_policy(),
        "one_v25401_parent_forward_shared_by_control_and_candidate": True,
        "control_is_parent_prediction_byte_exact": True,
        "candidate_is_only_v25544_pure_deterministic_projection": True,
        "independent_sampling_between_arms": False,
        "candidate_additional_queries_fetches_model_calls_tokens_context_wall_or_network": 0,
        "scale_converted_column_sorting_forbidden": True,
        "fixed_failure_as_zero_denominator_no_retry_resume_or_replacement": True,
        "historical_population_forward_prediction_or_output_reused": False,
        "clone_namespace_assembled_from_actual_source_function_globals": True,
        "recursive_load_global_resolution_required_before_effect": True,
        "prediction_freeze_precedes_truth_evaluator_or_quality_decision": True,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        **copy.deepcopy(population.mechanism_gate()),
        "required_model_generated_tasks": TASK_COUNT,
        "maximum_naked_outer_failure_tasks": 0,
    }


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
        PROJECTOR_TEST,
        POPULATION_TEST,
        BUILD_AUDIT_TEST,
        POPULATION_AUDIT_TEST,
        CLONE_HELPER_TEST,
        RUNTIME_BUILD_AUDIT,
        POPULATION_AUDIT,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if path.suffix == ".py" and SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.55.50 credential literal in dependency manifest")
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
        raise RuntimeError("V2.55.50 protocol surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25550_visible_constraint_external_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": head,
        "target_main": target,
        "build_audit_sha256": str(build_audit_sha256),
        "runtime_build_audit": {"path": str(RUNTIME_BUILD_AUDIT), "sha256": sha256(root / RUNTIME_BUILD_AUDIT)},
        "population_audit": {"path": str(POPULATION_AUDIT), "sha256": sha256(root / POPULATION_AUDIT)},
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "population": {
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
        },
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "physical_caps": {"queries": 4, "fetches": 14, "maximum_normal_path_model_forwards": 3},
            "single_task_attempt": True,
            "retry_resume_skip_backfill_replacement": False,
            "runtime_policy_id": runtime.POLICY_ID,
            "parent_policy_id": runtime.parent.POLICY_ID,
            "constraint_policy_id": runtime.contracts.POLICY_ID,
            "projector_policy_id": runtime.projector.POLICY_ID,
            "clone_namespace_policy_id": "v25478_clone_safe_runner_namespace_v1",
            "one_parent_forward_per_task": True,
            "control_and_candidate_share_all_provider_retrieval_and_sampling_effects": True,
            "candidate_additional_queries_fetches_model_calls_or_sampling_effects": 0,
            "persist_both_prediction_texts_for_postfreeze_quality": True,
        },
        "failure_gate_semantics": {
            "fixed_terminal_denominator": TASK_COUNT,
            "outer_failure_allowed": 0,
            "budget_rejection_allowed": 0,
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
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value, tracked=tracked)


def validate_protocol(root: Path, value: Mapping[str, Any], *, tracked: bool = True) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal_value = unsigned.pop("protocol_payload_sha256", None)
    manifest = copied.get("source_manifest")
    population_value = copied.get("population")
    execution = copied.get("execution")
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25550_visible_constraint_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("git_head") != copied.get("target_main")
        or re.fullmatch(r"[0-9a-f]{64}", str(copied.get("build_audit_sha256"))) is None
        or copied.get("runtime_build_audit") != {"path": str(RUNTIME_BUILD_AUDIT), "sha256": RUNTIME_BUILD_AUDIT_SHA256}
        or copied.get("population_audit") != {"path": str(POPULATION_AUDIT), "sha256": POPULATION_AUDIT_SHA256}
        or not isinstance(manifest, Mapping)
        or dict(manifest) != dependency_manifest(root, tracked=tracked)
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or population_value != {
            "task_count": 20,
            "identity_count": 40,
            "date_task_count": 10,
            "scale_task_count": 10,
            "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
            "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
            "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
            "question_overlap_with_fixed220": 0,
            "opaque_id_overlap_with_fixed220": 0,
            "prior_population_or_execution_reused": False,
        }
        or not isinstance(execution, Mapping)
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("limits") != LIMITS
        or execution.get("physical_caps") != {"queries": 4, "fetches": 14, "maximum_normal_path_model_forwards": 3}
        or execution.get("single_task_attempt") is not True
        or execution.get("retry_resume_skip_backfill_replacement") is not False
        or execution.get("runtime_policy_id") != runtime.POLICY_ID
        or execution.get("parent_policy_id") != runtime.parent.POLICY_ID
        or execution.get("constraint_policy_id") != runtime.contracts.POLICY_ID
        or execution.get("projector_policy_id") != runtime.projector.POLICY_ID
        or execution.get("clone_namespace_policy_id") != "v25478_clone_safe_runner_namespace_v1"
        or execution.get("one_parent_forward_per_task") is not True
        or execution.get("control_and_candidate_share_all_provider_retrieval_and_sampling_effects") is not True
        or execution.get("candidate_additional_queries_fetches_model_calls_or_sampling_effects") != 0
        or execution.get("persist_both_prediction_texts_for_postfreeze_quality") is not True
        or copied.get("failure_gate_semantics") != {
            "fixed_terminal_denominator": 20,
            "outer_failure_allowed": 0,
            "budget_rejection_allowed": 0,
            "failure_rows_retain_partial_effects_and_per_task_hard_caps": True,
        }
        or copied.get("source_policy") != source_policy()
        or copied.get("mechanism_gate") != mechanism_gate()
        or copied.get("postfreeze_quality_gate") != quality_gate()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("authorization") != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "one_external_forward": False,
            "postfreeze_quality": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        }
        or seal_value != payload_sha256(unsigned)
    ):
        raise ValueError("V2.55.50 external protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "forward_dependency_closure",
    "future_surfaces",
    "mechanism_gate",
    "population",
    "quality_gate",
    "runtime",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "validate_task_vector",
]
