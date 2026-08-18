"""Frozen contract for one totality-safe constraint DeepWideBench exact-220."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v25267_production_only_exact220_contract as shell
from . import v25569_constraint_totality_safe_handoff_runtime as runtime
from . import v25253_outer_physical_cap_observed_runtime as cap


DATE = "20260814"
PROTOCOL_ID = "v25573_totality_safe_visible_constraint_exact220_v1"
BUILD_AUDIT = Path(f"results/v25573_totality_exact220_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25573_totality_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25573_totality_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25573_totality_exact220_execution_start_v1_{DATE}.json")
ATTEMPT_CLAIM = Path(f"results/v25573_totality_exact220_attempt_claim_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25573_totality_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25573_totality_exact220_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v25573_totality_exact220_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25573_totality_exact220_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25573_totality_exact220_postresult_audit_v1_{DATE}.json")

OUTPUT_ROOT = Path(f"outputs/v25573_totality_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
RUNTIME_RESULTS = TASK_ROWS
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"

CONTRACT = Path("src/deepwide_agent/v25573_totality_exact220_contract.py")
RUNTIME = Path("src/deepwide_agent/v25569_constraint_totality_safe_handoff_runtime.py")
CAP_RUNTIME = shell.CAP_RUNTIME
RUNNER = Path("scripts/run_v25573_totality_exact220.py")
RUNNER_MARKER = str(RUNNER)
CHILD_MARKER = "v25573_no_child_process"
CONTROL = Path("scripts/control_v25573_totality_exact220.py")
FINALIZER = Path("scripts/finalize_v25573_totality_exact220.py")
TEST = Path("tests/test_v25573_totality_exact220.py")
RUNTIME_TEST = Path("tests/test_v25569_constraint_totality_safe_handoff_runtime.py")
SOURCE_MANIFEST = shell.SOURCE_MANIFEST

PARENT_QUALITY_AUDIT = Path(
    "results/v25572_fresh_totality_quality_audit_v1_20260814.json"
)
PARENT_QUALITY_AUDIT_SHA256 = (
    "adf6c8a8e9d80a28b37b9de64b28d55a0101f1f32c1b564b417737dfacd0a85a"
)
# Compatibility names used by the inherited fixed-denominator control shell.
DIAGNOSIS = PARENT_QUALITY_AUDIT
CAP_BUILD_AUDIT = PARENT_QUALITY_AUDIT
LATEST_RESULT = Path("results/v25568_constraint_exact220_result_v1_20260814.json")
REPLICATION_RESULT = shell.REPLICATION_RESULT
PEAK_RESULT = shell.PEAK_RESULT

TASK_COUNT = 220
SELECTED_COUNT = TASK_COUNT
EXECUTOR_CONCURRENCY = 40
MODEL_SLOT_CAP = 16
LEASE_PATH = shell.LEASE_PATH
LEASE_OWNER = "v25573_totality_exact220_forward_v1"
LEASE_PURPOSE = "single_label_blind_totality_constraint_exact220_v25573"
EVALUATOR_OWNER = "v25573_totality_exact220_evaluator_v1"
EVALUATOR_PURPOSE = "postfreeze_fixed_partition_parallel_v25573_exact220"
MODEL = copy.deepcopy(shell.MODEL)
SEARCH = copy.deepcopy(shell.SEARCH)
LIMITS = copy.deepcopy(shell.LIMITS)
CLEANUP_RESERVE_SECONDS = shell.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = shell.MINIMUM_MODEL_ATTEMPT_SECONDS
PROTECTED_WATCHERS = shell.PROTECTED_WATCHERS
COLUMNS = ("Result", "Value")
PHYSICAL_CAPS = {
    "queries_per_task": cap.QUERY_CAP,
    "fetches_per_task": cap.FETCH_CAP,
    "model_forwards_per_task": 3,
}

FORWARD_ROLE = "v25573_totality_exact220_forward_result"
SUMMARY_ROLE = "v25573_totality_exact220_run_summary"
FREEZE_ROLE = "v25573_totality_exact220_prediction_freeze"

task_parent = shell.task_parent
payload_sha256 = shell.payload_sha256
sha256 = shell.sha256
git = shell.git
seal = shell.seal
sealed = shell.sealed
watcher_snapshot = shell.watcher_snapshot
protected_watcher_snapshot = watcher_snapshot


def ordinary(root: Path, relative: Path, *, tracked: bool) -> Path:
    repository = Path(root).resolve()
    path = repository / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(repository)
    ):
        raise RuntimeError(f"V2.55.73 expected ordinary repository file: {relative}")
    if tracked and subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=repository,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode != 0:
        raise RuntimeError(f"V2.55.73 expected tracked file: {relative}")
    return path


def task_vector(
    root: Path | None = None, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    repository = Path(__file__).resolve().parents[2] if root is None else Path(root).resolve()
    rows = shell.task_vector(repository)
    expected = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": TASK_COUNT,
        "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in rows]),
        "visible_question_vector_sha256": payload_sha256([row["question"] for row in rows]),
    }
    if protocol is not None and protocol.get("task_contract") != expected:
        raise RuntimeError("V2.55.73 task binding drifted")
    return rows


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "one_v25401_parent_forward_and_one_pure_local_projection": True,
        "first_validated_sparse_production_is_only_scored_prediction": False,
        "header_quote_vertical_candidate_or_revision_prediction_used": True,
        "scored_prediction_is_totality_constraint_candidate_or_safe_parent_handoff": True,
        "constraint_contract_uses_only_visible_question_and_parent_table_columns": True,
        "date_scale_order_range_and_rank_constraints_are_visible_only": True,
        "canonical_projection_behavior_unchanged": True,
        "projection_nonadmission_is_byte_exact_parent_handoff": True,
        "internal_validation_failure_is_not_contained": True,
        "constraint_active_task_count_on_fixed220": 95,
        "date_format_task_count_on_fixed220": 46,
        "numeric_scale_task_count_on_fixed220": 19,
        "explicit_order_task_count_on_fixed220": 3,
        "temporal_year_range_task_count_on_fixed220": 43,
        "rank_slots_task_count_on_fixed220": 6,
        "control_retained_only_in_private_runtime_receipt": True,
        "candidate_has_no_independent_model_or_sampling_effect": True,
        "candidate_only_effect_is_v25544_projection_or_v25569_safe_parent_handoff": True,
        "schema_hierarchy": [
            "exact_visible",
            "expanded_explicit_visible",
            "same_effect_provider_plan",
            "generic_result_value",
        ],
        "task_local_function_namespace_without_global_mutation": True,
        "truthful_pre_effect_query4_fetch14_model3_caps": True,
        "mapping_gold_category_question_type_split_answer_evaluator_score_reward_read_by_forward": False,
        "prior_prediction_result_score_reward_or_evaluator_read_by_forward": False,
        "prediction_freeze_before_mapping_query_answer_or_official_evaluator_open": True,
        "entropy_or_information_gain_assigns_signed_credit_or_routes": False,
        "positive_signed_credit_count": 0,
        "fixed_public_exact220_task_set_reexecuted": True,
        "fresh20_totality_mechanism_and_arm_blind_quality_gates_strict_go_before_exact220_build": True,
        "new_or_disjoint_task_population_claimed": False,
        "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
        "leaderboard_or_sota_authorized": False,
    }


def totality_gate() -> dict[str, Any]:
    return {
        "fixed_task_denominator": TASK_COUNT,
        "required_terminal_predictions": TASK_COUNT,
        "required_budget_receipts": TASK_COUNT,
        "maximum_parent_prediction_loss_tasks": 0,
        "maximum_unsafe_handoff_tasks": 0,
        "maximum_physical_queries_total": TASK_COUNT * cap.QUERY_CAP,
        "maximum_physical_fetches_total": TASK_COUNT * cap.FETCH_CAP,
        "maximum_model_forwards_total": TASK_COUNT * 3,
        "prediction_freeze_and_pushed_forward_audit_before_evaluator": True,
        "quality_evaluator_unconditional_on_runtime_success_or_observed_quality": True,
        "invalid_evaluator_rows_are_failure_as_zero_without_selective_retry": True,
        "positive_signed_credit_count": 0,
    }


def _module_candidates(relative: Path, node: ast.AST) -> list[Path]:
    return task_parent._module_candidates(relative, node)


FORWARD_SOURCES = (CONTRACT, RUNNER, RUNTIME, CAP_RUNTIME)


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
        FINALIZER,
        TEST,
        RUNTIME_TEST,
        task_parent.PARENT_TASK_PROTOCOL,
        PARENT_QUALITY_AUDIT,
    }
    return {
        str(relative): sha256(ordinary(root, relative, tracked=tracked))
        for relative in sorted(relatives, key=str)
    }


def parent_receipts(root: Path, *, tracked: bool) -> dict[str, Any]:
    path = ordinary(root, PARENT_QUALITY_AUDIT, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    observed_sha256 = sha256(path)
    if (
        observed_sha256 != PARENT_QUALITY_AUDIT_SHA256
        or value.get("role") != "v25572_fresh_totality_quality_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("quality_gate_passed") is not True
        or value.get("authorization", {}).get("deepwidebench_successor_build") is not True
        or value.get("authorization", {}).get("new_exact220_protocol_design") is not True
        or value.get("authorization", {}).get("deepwidebench_forward_or_evaluator") is not False
    ):
        raise RuntimeError("V2.55.73 mechanism authority drifted")
    return {
        "v25572_fresh_totality_quality_audit": {
            "path": str(PARENT_QUALITY_AUDIT),
            "sha256": observed_sha256,
        }
    }


def build_protocol(
    root: Path,
    *,
    now: int,
    tracked: bool,
    require_pristine: bool,
    build_audit_sha256: str,
) -> dict[str, Any]:
    future = (
        PROTOCOL,
        PREAUDIT,
        EXECUTION_START,
        ATTEMPT_CLAIM,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        EVALUATOR_PROTOCOL,
        RESULT,
        POSTAUDIT,
        OUTPUT_ROOT,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink() for path in future
    ):
        raise RuntimeError("V2.55.73 future surface is not pristine")
    tasks = task_vector(root)
    manifest = dependency_manifest(root, tracked=tracked)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25573_totality_exact220_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": TASK_COUNT,
            "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
            "visible_question_vector_sha256": payload_sha256([row["question"] for row in tasks]),
        },
        "input_bindings": task_parent._input_bindings(root),
        "parent_receipts": parent_receipts(root, tracked=tracked),
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "logical_limits": copy.deepcopy(LIMITS),
            "truthful_physical_caps": copy.deepcopy(PHYSICAL_CAPS),
            "runtime_policy_id": runtime.POLICY_ID,
            "shared_parent_policy_id": runtime.parent.POLICY_ID,
            "constraint_policy_id": runtime.contracts.POLICY_ID,
            "strict_projection_policy_id": runtime.constrained.POLICY_ID,
            "projector_policy_id": runtime.constrained.projector.POLICY_ID,
            "scored_prediction": "totality_constraint_candidate_or_byte_exact_parent_handoff",
            "protected_watchers": watcher_snapshot(),
            "single_atomic_forward_no_retry_resume_skip_backfill_replacement_or_selective_rerun": True,
        },
        "totality_gate": totality_gate(),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
        "authorization": {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_exact220_forward": False,
            "postfreeze_official_evaluator": False,
            "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    return seal(value, "protocol_payload_sha256")


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = build_protocol(
        root,
        now=int(copied.get("created_at_unix", -1)),
        tracked=True,
        require_pristine=False,
        build_audit_sha256=sha256(root / BUILD_AUDIT),
    )
    if copied != expected or not sealed(copied, "protocol_payload_sha256"):
        raise RuntimeError("V2.55.73 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "forward_dependency_closure",
    "git",
    "ordinary",
    "parent_receipts",
    "payload_sha256",
    "protected_watcher_snapshot",
    "seal",
    "sealed",
    "sha256",
    "source_policy",
    "task_vector",
    "totality_gate",
    "validate_protocol",
    "watcher_snapshot",
]
