"""Frozen contract for one checkpoint-protected DeepWideBench exact-220 run."""

from __future__ import annotations

import ast
import copy
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v25267_production_only_exact220_contract as parent
from . import v25342_checkpoint_exact220_adapter as runtime
from . import v25253_outer_physical_cap_observed_runtime as cap


DATE = "20260813"
PROTOCOL_ID = "v25342_checkpoint_protected_production_exact220_v1"
BUILD_AUDIT = Path(f"results/v25342_checkpoint_exact220_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25342_checkpoint_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25343_checkpoint_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25343_checkpoint_exact220_execution_start_v1_{DATE}.json")
ATTEMPT_CLAIM = Path(f"results/v25342_checkpoint_exact220_attempt_claim_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25342_checkpoint_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25344_checkpoint_exact220_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v25342_checkpoint_exact220_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25342_checkpoint_exact220_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25344_checkpoint_exact220_postresult_audit_v1_{DATE}.json")

OUTPUT_ROOT = Path(f"outputs/v25342_checkpoint_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
RUNTIME_RESULTS = TASK_ROWS
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"

CONTRACT = Path("src/deepwide_agent/v25342_checkpoint_exact220_contract.py")
RUNTIME = Path("src/deepwide_agent/v25342_checkpoint_exact220_adapter.py")
CAP_RUNTIME = parent.CAP_RUNTIME
RUNNER = Path("scripts/run_v25342_checkpoint_exact220.py")
RUNNER_MARKER = str(RUNNER)
CHILD_MARKER = "v25342_no_child_process"
CONTROL = Path("scripts/control_v25342_checkpoint_exact220.py")
FINALIZER = Path("scripts/finalize_v25342_checkpoint_exact220.py")
TEST = Path("tests/test_v25342_checkpoint_exact220.py")
RUNTIME_TEST = TEST
SOURCE_MANIFEST = parent.SOURCE_MANIFEST

CHECKPOINT_BUILD_AUDIT = Path(
    "results/v25272_validated_production_checkpoint_build_audit_v1_20260812.json"
)
CHECKPOINT_BUILD_AUDIT_SHA256 = (
    "f7c7d16def15ff80ae76b3a506da345c38b3c28286bf4c3e05eec84480f5aace"
)
CHECKPOINT_RELIABILITY_AUDIT = Path(
    "results/v25283_paired_checkpoint_reliability_forward_audit_v1_20260813.json"
)
CHECKPOINT_RELIABILITY_AUDIT_SHA256 = (
    "8c1bd6cd12e32be50ae9e9dbb1706ebb145fda699c392b26ee0e656d8f13bc2a"
)
# Names retained for the inherited control's two-parent manifest interface.
DIAGNOSIS = CHECKPOINT_BUILD_AUDIT
CAP_BUILD_AUDIT = CHECKPOINT_RELIABILITY_AUDIT

LATEST_RESULT = parent.RESULT
REPLICATION_RESULT = parent.REPLICATION_RESULT
PEAK_RESULT = parent.PEAK_RESULT

TASK_COUNT = parent.TASK_COUNT
SELECTED_COUNT = TASK_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v25342_checkpoint_production_exact220_forward_v1"
LEASE_PURPOSE = "single_label_blind_checkpoint_production_exact220"
EVALUATOR_OWNER = "v25342_checkpoint_production_exact220_evaluator_v1"
EVALUATOR_PURPOSE = "postfreeze_fixed_partition_parallel_v25342_checkpoint_exact220"
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
LIMITS = copy.deepcopy(parent.LIMITS)
CLEANUP_RESERVE_SECONDS = parent.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = parent.MINIMUM_MODEL_ATTEMPT_SECONDS
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
COLUMNS = parent.COLUMNS
PHYSICAL_CAPS = copy.deepcopy(parent.PHYSICAL_CAPS)

FORWARD_ROLE = "v25342_checkpoint_exact220_forward_result"
SUMMARY_ROLE = "v25342_checkpoint_exact220_run_summary"
FREEZE_ROLE = "v25342_checkpoint_exact220_prediction_freeze"

task_parent = parent.task_parent
payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
git = parent.git
seal = parent.seal
sealed = parent.sealed
watcher_snapshot = parent.watcher_snapshot
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
        raise RuntimeError(f"V2.53.42 expected ordinary repository file: {relative}")
    if tracked and subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=repository,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode != 0:
        raise RuntimeError(f"V2.53.42 expected tracked file: {relative}")
    return path


def task_vector(
    root: Path | None = None, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    rows = parent.task_vector(root)
    expected = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": TASK_COUNT,
        "opaque_id_vector_sha256": payload_sha256(
            [row["opaque_id"] for row in rows]
        ),
        "visible_question_vector_sha256": payload_sha256(
            [row["question"] for row in rows]
        ),
    }
    if protocol is not None and protocol.get("task_contract") != expected:
        raise RuntimeError("V2.53.42 task binding drifted")
    return rows


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "first_validated_sparse_production_is_only_scored_prediction": True,
        "validated_production_checkpoint_precedes_auxiliary_envelope": True,
        "post_checkpoint_failure_preserves_same_prediction_without_extra_effect": True,
        "normal_path_provider_search_fetch_prompt_prediction_unchanged": True,
        "second_synthesis_entry_is_local_replay_without_provider_effect": True,
        "header_quote_vertical_candidate_or_revision_prediction_used": False,
        "truthful_pre_effect_query4_fetch14_model4_caps": True,
        "mapping_gold_category_question_type_split_answer_evaluator_score_reward_read_by_forward": False,
        "prior_prediction_result_score_reward_or_evaluator_read_by_forward": False,
        "prediction_freeze_before_mapping_query_answer_or_official_evaluator_open": True,
        "entropy_or_information_gain_assigns_signed_credit_or_routes": False,
        "positive_signed_credit_count": 0,
        "fixed_public_exact220_task_set_reexecuted": True,
        "new_or_disjoint_task_population_claimed": False,
        "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
        "leaderboard_or_sota_authorized": False,
    }


def totality_gate() -> dict[str, Any]:
    value = copy.deepcopy(parent.totality_gate())
    value.update(
        {
            "checkpoint_recovery_is_terminal_not_outer_failure": True,
            "checkpoint_recovery_additional_effect": 0,
            "microstage_receipt_required_for_every_runtime_result": True,
        }
    )
    return value


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
        task_parent.PARENT_TASK_PROTOCOL,
        DIAGNOSIS,
        CAP_BUILD_AUDIT,
    }
    return {
        str(relative): sha256(ordinary(root, relative, tracked=tracked))
        for relative in sorted(relatives, key=str)
    }


def parent_receipts(root: Path, *, tracked: bool) -> dict[str, Any]:
    build_path = ordinary(root, CHECKPOINT_BUILD_AUDIT, tracked=tracked)
    reliability_path = ordinary(
        root, CHECKPOINT_RELIABILITY_AUDIT, tracked=tracked
    )
    build = json.loads(build_path.read_text(encoding="utf-8"))
    reliability = json.loads(reliability_path.read_text(encoding="utf-8"))
    if (
        sha256(build_path) != CHECKPOINT_BUILD_AUDIT_SHA256
        or build.get("role")
        != "v25272_validated_production_checkpoint_clean_build_audit"
        or build.get("audit_valid") is not True
        or build.get("findings") != []
        or build.get("checks", {}).get(
            "normal_path_prediction_cost_and_effect_match_parent"
        )
        is not True
        or sha256(reliability_path) != CHECKPOINT_RELIABILITY_AUDIT_SHA256
        or reliability.get("role")
        != "v25283_paired_checkpoint_reliability_forward_audit"
        or reliability.get("audit_valid") is not True
        or reliability.get("findings") != []
        or reliability.get("checks", {}).get(
            "candidate_additional_effect_and_credit_zero"
        )
        is not True
        or reliability.get("checks", {}).get(
            "completed_rows_bind_control_and_candidate_projection"
        )
        is not True
    ):
        raise RuntimeError("V2.53.42 checkpoint parent authority drifted")
    return {
        "v25272_checkpoint_build_audit": {
            "path": str(CHECKPOINT_BUILD_AUDIT),
            "sha256": CHECKPOINT_BUILD_AUDIT_SHA256,
        },
        "v25283_checkpoint_reliability_audit": {
            "path": str(CHECKPOINT_RELIABILITY_AUDIT),
            "sha256": CHECKPOINT_RELIABILITY_AUDIT_SHA256,
        },
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
        raise RuntimeError("V2.53.42 future surface is not pristine")
    tasks = task_vector(root)
    manifest = dependency_manifest(root, tracked=tracked)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25342_checkpoint_exact220_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": TASK_COUNT,
            "opaque_id_vector_sha256": payload_sha256(
                [row["opaque_id"] for row in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [row["question"] for row in tasks]
            ),
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
            "checkpoint_policy_id": runtime.checkpoint.POLICY_ID,
            "scored_prediction": "validated_production_or_same_sealed_checkpoint",
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
        raise RuntimeError("V2.53.42 protocol drifted")
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
