"""Frozen contract for one production-only DeepWideBench exact-220 run."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v25130_causal_salience_exact220_contract as task_parent
from . import v25253_outer_physical_cap_observed_runtime as cap
from . import v25265_production_only_totality_runtime as runtime


DATE = "20260812"
PROTOCOL_ID = "v25267_production_only_totality_exact220_v1"
BUILD_AUDIT = Path(f"results/v25266_production_only_exact220_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25267_production_only_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25268_production_only_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25268_production_only_exact220_execution_start_v1_{DATE}.json")
ATTEMPT_CLAIM = Path(f"results/v25267_production_only_exact220_attempt_claim_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25267_production_only_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25269_production_only_exact220_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v25267_production_only_exact220_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25267_production_only_exact220_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25267_production_only_exact220_postresult_audit_v1_{DATE}.json")

OUTPUT_ROOT = Path(f"outputs/v25267_production_only_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
RUNTIME_RESULTS = TASK_ROWS
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"

CONTRACT = Path("src/deepwide_agent/v25267_production_only_exact220_contract.py")
RUNTIME = Path("src/deepwide_agent/v25265_production_only_totality_runtime.py")
CAP_RUNTIME = Path("src/deepwide_agent/v25253_outer_physical_cap_observed_runtime.py")
RUNNER = Path("scripts/run_v25267_production_only_exact220.py")
RUNNER_MARKER = str(RUNNER)
CHILD_MARKER = "v25267_no_child_process"
CONTROL = Path("scripts/control_v25267_production_only_exact220.py")
FINALIZER = Path("scripts/finalize_v25267_production_only_exact220.py")
TEST = Path("tests/test_v25267_production_only_exact220.py")
RUNTIME_TEST = Path("tests/test_v25265_production_only_totality_runtime.py")
SOURCE_MANIFEST = task_parent.VISIBLE_MANIFEST

DIAGNOSIS = Path(f"results/v25264_v25260_observed_reliability_diagnosis_v1_{DATE}.json")
DIAGNOSIS_SHA256 = "1ce83802ab76007201a4ea1593fbea3071ea83f424e3464f3068cbe902452350"
CAP_BUILD_AUDIT = Path(f"results/v25254_outer_physical_cap_observed_build_audit_v1_{DATE}.json")
CAP_BUILD_AUDIT_SHA256 = "84ac0911eb900980657e11016a4adc32b8f3fd61e7732df92eee0651dc3cff87"
LATEST_RESULT = Path(f"results/v25208_quote_aware_exact220_result_r2_{DATE}.json")
REPLICATION_RESULT = Path("results/v24969_pacing_aware_replication_result_v1_20260809.json")
PEAK_RESULT = Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json")

TASK_COUNT = 220
SELECTED_COUNT = TASK_COUNT
EXECUTOR_CONCURRENCY = 40
MODEL_SLOT_CAP = 16
LEASE_PATH = task_parent.LEASE_PATH
LEASE_OWNER = "v25267_production_only_totality_exact220_forward_v1"
LEASE_PURPOSE = "single_label_blind_production_only_totality_exact220"
EVALUATOR_OWNER = "v25267_production_only_totality_exact220_evaluator_v1"
EVALUATOR_PURPOSE = "postfreeze_fixed_partition_parallel_v25267_exact220"
MODEL = copy.deepcopy(task_parent.MODEL)
SEARCH = copy.deepcopy(task_parent.SEARCH)
LIMITS = copy.deepcopy(task_parent.LIMITS)
CLEANUP_RESERVE_SECONDS = task_parent.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = task_parent.MINIMUM_MODEL_ATTEMPT_SECONDS
PROTECTED_WATCHERS = task_parent.PROTECTED_WATCHERS
COLUMNS = ("Unknown",)
PHYSICAL_CAPS = {
    "queries_per_task": cap.QUERY_CAP,
    "fetches_per_task": cap.FETCH_CAP,
    "model_forwards_per_task": cap.MODEL_CAP,
}

FORWARD_ROLE = "v25267_production_only_exact220_forward_result"
SUMMARY_ROLE = "v25267_production_only_exact220_run_summary"
FREEZE_ROLE = "v25267_production_only_exact220_prediction_freeze"

payload_sha256 = task_parent.payload_sha256
sha256 = task_parent.sha256
git = task_parent.git
seal = task_parent.seal
sealed = task_parent.sealed
watcher_snapshot = task_parent.protected_watcher_snapshot
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
        raise RuntimeError(f"V2.52.67 expected ordinary repository file: {relative}")
    if tracked and subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(relative)],
        cwd=repository,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode != 0:
        raise RuntimeError(f"V2.52.67 expected tracked file: {relative}")
    return path


def task_vector(
    root: Path | None = None, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    repository = Path(__file__).resolve().parents[2] if root is None else Path(root).resolve()
    rows = [
        {"opaque_id": row["opaque_id"], "question": row["question"]}
        for row in task_parent.task_vector(repository)
    ]
    if (
        len(rows) != TASK_COUNT
        or len({row["opaque_id"] for row in rows}) != TASK_COUNT
        or any(set(row) != {"opaque_id", "question"} for row in rows)
        or payload_sha256([row["opaque_id"] for row in rows])
        != "3c4b3eeb6cadbc9ce8b22552f294a0322e820dbb4be29c3e7fb2f99a4f83665a"
        or payload_sha256([row["question"] for row in rows])
        != "d009f9f13b51e48e249f6698b3b1417d3a62c7100c8551b1cb025e726bcd82b7"
    ):
        raise RuntimeError("V2.52.67 public exact-220 vector drifted")
    expected = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": TASK_COUNT,
        "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in rows]),
        "visible_question_vector_sha256": payload_sha256([row["question"] for row in rows]),
    }
    if protocol is not None and protocol.get("task_contract") != expected:
        raise RuntimeError("V2.52.67 task binding drifted")
    return rows


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "first_validated_sparse_production_is_only_scored_prediction": True,
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
    return {
        "fixed_task_denominator": TASK_COUNT,
        "required_terminal_predictions": TASK_COUNT,
        "required_budget_receipts": TASK_COUNT,
        "maximum_physical_queries_total": TASK_COUNT * cap.QUERY_CAP,
        "maximum_physical_fetches_total": TASK_COUNT * cap.FETCH_CAP,
        "maximum_model_forwards_total": TASK_COUNT * cap.MODEL_CAP,
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
        *forward_dependency_closure(root), CONTROL, FINALIZER, TEST, RUNTIME_TEST,
        task_parent.PARENT_TASK_PROTOCOL, DIAGNOSIS, CAP_BUILD_AUDIT,
    }
    return {
        str(relative): sha256(ordinary(root, relative, tracked=tracked))
        for relative in sorted(relatives, key=str)
    }


def parent_receipts(root: Path, *, tracked: bool) -> dict[str, Any]:
    diagnosis_path = ordinary(root, DIAGNOSIS, tracked=tracked)
    cap_path = ordinary(root, CAP_BUILD_AUDIT, tracked=tracked)
    diagnosis = json.loads(diagnosis_path.read_text(encoding="utf-8"))
    cap_audit = json.loads(cap_path.read_text(encoding="utf-8"))
    if (
        sha256(diagnosis_path) != DIAGNOSIS_SHA256
        or diagnosis.get("role") != "v25264_v25260_observed_reliability_content_free_diagnosis"
        or diagnosis.get("conclusions", {}).get("truthful_4_query_14_fetch_4_model_totality_gate_strict_go") is not True
        or diagnosis.get("authorization", {}).get("build_exact220_totality_successor_from_verified_shell") is not True
        or diagnosis.get("authorization", {}).get("external_forward") is not False
        or sha256(cap_path) != CAP_BUILD_AUDIT_SHA256
        or cap_audit.get("audit_valid") is not True
        or cap_audit.get("findings") != []
        or cap_audit.get("physical_caps") != {"queries": 4, "fetches": 14, "model_forwards": 4}
    ):
        raise RuntimeError("V2.52.67 parent reliability authority drifted")
    return {
        "v25264_reliability_diagnosis": {"path": str(DIAGNOSIS), "sha256": DIAGNOSIS_SHA256},
        "v25254_cap_build_audit": {"path": str(CAP_BUILD_AUDIT), "sha256": CAP_BUILD_AUDIT_SHA256},
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
        PROTOCOL, PREAUDIT, EXECUTION_START, ATTEMPT_CLAIM, FORWARD_RESULT,
        FORWARD_AUDIT, EVALUATOR_PROTOCOL, RESULT, POSTAUDIT, OUTPUT_ROOT,
    )
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise RuntimeError("V2.52.67 future surface is not pristine")
    tasks = task_vector(root)
    manifest = dependency_manifest(root, tracked=tracked)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25267_production_only_exact220_preregistration",
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
            "scored_prediction": "first_validated_sparse_production",
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
        raise RuntimeError("V2.52.67 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol", "dependency_manifest", "forward_dependency_closure", "git",
    "ordinary", "parent_receipts", "payload_sha256", "protected_watcher_snapshot",
    "seal", "sealed", "sha256", "source_policy", "task_vector", "totality_gate",
    "validate_protocol", "watcher_snapshot",
]
