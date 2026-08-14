"""One-shot contract for the fresh row-key IANA-detail mechanism gate."""

from __future__ import annotations

import ast
import copy
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25068_quote_verified_external_contract as base
from . import v25484_row_key_iana_detail_runtime as runtime
from . import v25486_outcome_blind_iana_detail_population as population


DATE = "20260814"
PROTOCOL_ID = "v25488_fresh_row_key_iana_detail_external_v1"
BUILD_AUDIT = Path(f"results/v25488_iana_detail_external_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25488_iana_detail_external_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25488_iana_detail_external_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25488_iana_detail_external_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25488_iana_detail_external_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25488_iana_detail_external_forward_audit_v1_{DATE}.json")
POSTFREEZE_QUALITY_PROTOCOL = Path(
    f"results/v25488_iana_detail_quality_preregistration_v1_{DATE}.json"
)
QUALITY_RESULT = Path(f"results/v25488_iana_detail_quality_result_v1_{DATE}.json")
QUALITY_AUDIT = Path(f"results/v25488_iana_detail_quality_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v25488_iana_detail_external_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"

CONTRACT = Path("src/deepwide_agent/v25488_iana_detail_external_contract.py")
RUNTIME = Path("src/deepwide_agent/v25484_row_key_iana_detail_runtime.py")
POPULATION = Path(
    "src/deepwide_agent/v25486_outcome_blind_iana_detail_population.py"
)
RUNNER = Path("scripts/run_v25488_iana_detail_external.py")
CONTROL = Path("scripts/control_v25488_iana_detail_external.py")
TEST = Path("tests/test_v25488_iana_detail_external.py")
CONTROL_TEST = Path("tests/test_control_v25488_iana_detail_external.py")
PRIMITIVE_TEST = Path("tests/test_v25483_row_key_iana_detail_candidate.py")
RUNTIME_TEST = Path("tests/test_v25484_row_key_iana_detail_runtime.py")
POPULATION_TEST = Path(
    "tests/test_v25486_outcome_blind_iana_detail_population.py"
)
RUNTIME_AUDIT_TEST = Path("tests/test_audit_v25485_row_key_iana_detail_build.py")
POPULATION_AUDIT_TEST = Path(
    "tests/test_audit_v25487_outcome_blind_iana_detail_population.py"
)
CLONE_HELPER = Path("scripts/v25478_clone_safe_runner_namespace.py")
CLONE_HELPER_TEST = Path("tests/test_v25478_clone_safe_runner_namespace.py")
HELPER = base.HELPER
LEASE = Path("scripts/deepwide_api_lease.py")
RUNTIME_BUILD_AUDIT = Path(
    "results/v25485_row_key_iana_detail_build_audit_v1_20260814.json"
)
RUNTIME_BUILD_AUDIT_SHA256 = (
    "b531db35b7b862a19517db6dd9a67caab45ed9de0694974ea70d8925b0e95c13"
)
POPULATION_AUDIT = Path(
    "results/v25487_outcome_blind_iana_detail_population_audit_v1_20260814.json"
)
POPULATION_AUDIT_SHA256 = (
    "c7abdeb21942008ccea06ca97324753eb0cb6569041bc3c2a4274cfb7da134c7"
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
COLUMNS = population.COLUMNS
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25488_iana_detail_external_forward_v1"
LEASE_PURPOSE = "fresh_outcome_blind_row_key_iana_detail_gate_v1"
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
    copied = [dict(value) for value in values]
    if copied != population.task_vector():
        raise ValueError("V2.54.88 task vector drifted")
    return copied


def source_policy() -> dict[str, Any]:
    return {
        **population.source_policy(),
        "one_v25472_parent_forward_exposes_shared_control_and_iana_detail_candidate": True,
        "qualified_source_label_parent_prediction_is_exact_control": True,
        "independent_sampling_between_quality_arms": False,
        "candidate_additional_queries": 0,
        "candidate_additional_model_calls": 0,
        "maximum_candidate_additional_fetches": 1,
        "fixed_failure_as_zero_denominator_no_retry_resume_or_replacement": True,
        "historical_population_forward_or_output_reused": False,
        "v25481_execution_authority_consumed_but_not_reused": True,
        "clone_namespace_assembled_from_actual_source_function_globals": True,
        "recursive_load_global_resolution_required_before_effect": True,
    }


def mechanism_gate() -> dict[str, Any]:
    return {
        **population.mechanism_gate(),
        "maximum_naked_outer_failure_tasks": 0,
        "required_synthesis_capture_valid_tasks": TASK_COUNT,
    }


def quality_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "country_tld_and_iana_truth_opened_only_after_prediction_freeze_and_forward_audit": True,
        "each_base_and_candidate_prediction_evaluated_exactly_once": True,
        "invalid_or_unavailable_truth_is_failure_as_zero_without_retry": True,
        "candidate_whole_table_exact_strictly_greater_than_base": True,
        "candidate_entity_coverage_not_lower_than_base": True,
        "candidate_row_exact_not_lower_than_base": True,
        "candidate_cell_accuracy_not_lower_than_base": True,
        "candidate_column_accuracy_not_lower_than_base": True,
        "candidate_quality_composite_not_lower_than_base": True,
        "candidate_fallback_count_not_greater_than_base": True,
        "candidate_invalid_count_not_greater_than_base": True,
        "base_and_candidate_share_one_v25472_parent_forward": True,
        "positive_signed_credit_count": 0,
    }


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
        PRIMITIVE_TEST,
        RUNTIME_TEST,
        POPULATION_TEST,
        RUNTIME_AUDIT_TEST,
        POPULATION_AUDIT_TEST,
        CLONE_HELPER_TEST,
        RUNTIME_BUILD_AUDIT,
        POPULATION_AUDIT,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if path.suffix == ".py" and SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.54.88 credential literal in dependency manifest")
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
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in future_surfaces()
        )
    ):
        raise RuntimeError("V2.54.88 protocol surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    tasks = task_vector()
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25488_iana_detail_external_preregistration",
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
            "task_vector_sha256": payload_sha256(tasks),
            "clue_vector_sha256": population.EXPECTED_CLUE_VECTOR_SHA256,
            "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
            "selected_block_index": population.SELECTED_BLOCK_INDEX,
            "consumed_public_clue_count": 80,
            "selected_union_consumed_overlap_count": 0,
            "v25481_population_or_execution_reused": False,
            "no_visible_membership_country_or_tld_identity": True,
        },
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
                "outer_hard_model_cap": 4,
            },
            "single_task_attempt": True,
            "retry_resume_skip_backfill_replacement": False,
            "runtime_policy_id": runtime.POLICY_ID,
            "parent_policy_id": runtime.parent.POLICY_ID,
            "candidate_policy_id": runtime.candidates.POLICY_ID,
            "clone_namespace_policy_id": "v25478_clone_safe_runner_namespace_v1",
            "recursive_load_global_resolution_before_effect": True,
            "one_parent_forward_per_task": True,
            "base_and_candidate_share_parent_sampling": True,
            "candidate_additional_queries": 0,
            "maximum_candidate_additional_fetches": 1,
            "candidate_additional_model_calls": 0,
            "persist_both_prediction_texts_for_postfreeze_quality": True,
        },
        "failure_gate_semantics": {
            "fixed_terminal_denominator": TASK_COUNT,
            "outer_failure_allowed": 0,
            "naked_outer_failure_allowed": 0,
            "budget_rejection_allowed": 0,
            "physical_budget_is_upper_bound_per_completed_row": True,
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


def validate_protocol(
    root: Path, value: Mapping[str, Any], *, tracked: bool = True
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("protocol_payload_sha256", None)
    manifest = copied.get("source_manifest")
    expected_population = {
        "task_count": TASK_COUNT,
        "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
        "clue_vector_sha256": population.EXPECTED_CLUE_VECTOR_SHA256,
        "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
        "selected_block_index": population.SELECTED_BLOCK_INDEX,
        "consumed_public_clue_count": 80,
        "selected_union_consumed_overlap_count": 0,
        "v25481_population_or_execution_reused": False,
        "no_visible_membership_country_or_tld_identity": True,
    }
    expected_execution = {
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "model_slot_cap": MODEL_SLOT_CAP,
        "model": MODEL,
        "search": SEARCH,
        "limits": LIMITS,
        "physical_caps": {
            "queries": 4,
            "fetches": 14,
            "maximum_normal_path_model_forwards": 3,
            "outer_hard_model_cap": 4,
        },
        "single_task_attempt": True,
        "retry_resume_skip_backfill_replacement": False,
        "runtime_policy_id": runtime.POLICY_ID,
        "parent_policy_id": runtime.parent.POLICY_ID,
        "candidate_policy_id": runtime.candidates.POLICY_ID,
        "clone_namespace_policy_id": "v25478_clone_safe_runner_namespace_v1",
        "recursive_load_global_resolution_before_effect": True,
        "one_parent_forward_per_task": True,
        "base_and_candidate_share_parent_sampling": True,
        "candidate_additional_queries": 0,
        "maximum_candidate_additional_fetches": 1,
        "candidate_additional_model_calls": 0,
        "persist_both_prediction_texts_for_postfreeze_quality": True,
    }
    expected_failure = {
        "fixed_terminal_denominator": TASK_COUNT,
        "outer_failure_allowed": 0,
        "naked_outer_failure_allowed": 0,
        "budget_rejection_allowed": 0,
        "physical_budget_is_upper_bound_per_completed_row": True,
        "failure_rows_retain_partial_effects_and_per_task_hard_caps": True,
    }
    expected_auth = {
        "preactivation_audit_generation": True,
        "execution_start_generation": False,
        "one_external_forward": False,
        "postfreeze_quality": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
    }
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v25488_iana_detail_external_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("git_head") != copied.get("target_main")
        or re.fullmatch(r"[0-9a-f]{64}", str(copied.get("build_audit_sha256")))
        is None
        or copied.get("runtime_build_audit")
        != {
            "path": str(RUNTIME_BUILD_AUDIT),
            "sha256": RUNTIME_BUILD_AUDIT_SHA256,
        }
        or copied.get("population_audit")
        != {"path": str(POPULATION_AUDIT), "sha256": POPULATION_AUDIT_SHA256}
        or not isinstance(manifest, Mapping)
        or dict(manifest) != dependency_manifest(root, tracked=tracked)
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("population") != expected_population
        or copied.get("execution") != expected_execution
        or copied.get("failure_gate_semantics") != expected_failure
        or copied.get("source_policy") != source_policy()
        or copied.get("mechanism_gate") != mechanism_gate()
        or copied.get("postfreeze_quality_gate") != quality_gate()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("authorization") != expected_auth
        or signature != payload_sha256(unsigned)
    ):
        raise ValueError("V2.54.88 external protocol drifted")
    return copied


__all__ = [
    "BUILD_AUDIT",
    "CLONE_HELPER",
    "CLONE_HELPER_TEST",
    "COLUMNS",
    "CONTROL",
    "CONTROL_TEST",
    "EXECUTION_START",
    "EXECUTOR_CONCURRENCY",
    "EXPECTED_WATCHERS",
    "FORWARD_AUDIT",
    "FORWARD_RESULT",
    "LEASE_OWNER",
    "LEASE_PATH",
    "LEASE_PURPOSE",
    "LIMITS",
    "MODEL",
    "MODEL_SLOT_CAP",
    "MODEL_SLOT_DIRECTORY",
    "OUTPUT_ROOT",
    "PHASES",
    "POPULATION_AUDIT",
    "POSTFREEZE_QUALITY_PROTOCOL",
    "PREDICTION_FREEZE",
    "PREAUDIT",
    "PROTOCOL",
    "PROTOCOL_ID",
    "QUALITY_AUDIT",
    "QUALITY_RESULT",
    "RUNNER",
    "SEARCH",
    "TASK_COUNT",
    "TASK_ROWS",
    "TEST",
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
