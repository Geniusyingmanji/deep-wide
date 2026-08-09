"""Fresh label-blind replication of the frozen V2.49.32 policy.

Only execution and artifact namespaces change.  The visible 220-task vector,
prompt, keyless model/search transport, projector, budgets, and concurrency are
inherited unchanged.  Historical predictions, evaluator outputs, scores, and
per-task correctness are unavailable to the forward pass.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24932_unicode_total_exact220_contract as parent


DATE = "20260809"
ROLE = "v24935_unicode_total_replication_preregistration"
PROTOCOL_ID = "v24935_unicode_total_keyless_exact220_cold_replication_v1"
PROTOCOL = Path(f"results/v24935_unicode_total_replication_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24935_unicode_total_replication_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24935_unicode_total_replication_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24935_unicode_total_replication_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24935_unicode_total_replication_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24935_unicode_total_replication_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
PROJECTION_RECEIPT_NAME = parent.PROJECTION_RECEIPT_NAME
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24935_unicode_total_replication_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_unicode_total_keyless_exact220_replication"
RUNNER_MARKER = "scripts/run_v24935_unicode_total_replication.py"
CHILD_MARKER = "scripts/run_v24935_unicode_total_replication_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
PROJECTOR_SOURCE = parent.PROJECTOR_SOURCE
PROJECTOR_AUDIT = parent.PROJECTOR_AUDIT
LEGACY_PROJECTOR_SOURCE = parent.LEGACY_PROJECTOR_SOURCE
TARGET_VALUE_SOURCE = parent.TARGET_VALUE_SOURCE
BINDING = parent.BINDING
SOURCE = Path("src/deepwide_agent/v24935_unicode_total_replication_contract.py")
CONTROL = Path("scripts/control_v24935_unicode_total_replication.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24935_unicode_total_replication.py")
TEST = Path("tests/test_v24935_unicode_total_replication.py")
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.49.35 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.35 expected JSON object")
    return value


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    return parent.protected_watcher_snapshot(proc_root)


def parent_contract(root: Path) -> dict[str, Any]:
    return parent.validate_protocol(root, _read(root / PARENT_PROTOCOL))


def _task_contract(tasks: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
        "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
    }


def task_vector(root: Path, protocol: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    tasks = parent.task_vector(root, parent_contract(root))
    if len(tasks) != 220 or any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.49.35 visible exact-220 vector drifted")
    if protocol is not None and protocol.get("task_contract") != _task_contract(tasks):
        raise RuntimeError("V2.49.35 visible task binding drifted")
    return tasks


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.add(PARENT_PROTOCOL)
    relatives.update(LOCAL_SOURCES)
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def _algorithm_equality() -> dict[str, bool]:
    equalities = {
        "selected_count_equal_v24932": SELECTED_COUNT == parent.SELECTED_COUNT == 220,
        "executor_concurrency_equal_v24932": EXECUTOR_CONCURRENCY == parent.EXECUTOR_CONCURRENCY == 20,
        "model_slot_cap_equal_v24932": MODEL_SLOT_CAP == parent.MODEL_SLOT_CAP == 8,
        "limits_equal_v24932": LIMITS == parent.LIMITS,
        "model_equal_v24932": MODEL == parent.MODEL,
        "search_equal_v24932": SEARCH == parent.SEARCH,
        "two_wave_policy_equal_v24932": TWO_WAVE_POLICY == parent.TWO_WAVE_POLICY,
        "projector_equal_v24932": PROJECTOR_SOURCE == parent.PROJECTOR_SOURCE,
    }
    if not all(equalities.values()):
        raise RuntimeError("V2.49.35 frozen algorithm equality drifted")
    return equalities


def _single_change() -> dict[str, Any]:
    return {
        "fresh_execution_and_artifact_surfaces_only": True,
        "algorithm_equality": _algorithm_equality(),
        "independent_cold_single_rollout_replication": True,
        "frozen_unicode_total_v24932_policy_replicated": True,
        "additional_search_fetch_model_token_context_or_wall_cap": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
    }


def build_protocol(
    root: Path,
    *,
    now: int,
    require_clean: bool = True,
    require_pristine: bool = True,
) -> dict[str, Any]:
    if require_clean and (
        _git(root, "status", "--porcelain")
        or _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.49.35 protocol requires clean pushed HEAD")
    future = (PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise FileExistsError("V2.49.35 future surface exists")
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": _git(root, "rev-parse", "HEAD"),
        "parent_algorithm": {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": base["protocol_id"],
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
        },
        "task_contract": _task_contract(tasks),
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "task_wall_seconds": LIMITS["wall_seconds"],
            "model_calls_per_task": LIMITS["model_calls"],
            "search_queries_per_task": LIMITS["search_queries"],
            "fetch_targets_per_task": LIMITS["fetch_targets"],
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "two_wave_policy": copy.deepcopy(TWO_WAVE_POLICY),
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "single_fresh_forward_no_retry_resume_or_selective_rerun": True,
        },
        "single_change": _single_change(),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "prior_benchmark_prediction_result_score_or_evaluator_opened_or_hashed": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "fixed_public_exact220_task_set_reexecuted": True,
            "new_or_disjoint_task_population_claimed": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
            "explicit_user_request_authorizes_one_cold_exact220_replication": True,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value, manifest=manifest, tasks=tasks)


def validate_protocol(
    root: Path,
    value: Mapping[str, Any],
    *,
    manifest: Mapping[str, str] | None = None,
    tasks: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    base = parent_contract(root)
    tasks = task_vector(root) if tasks is None else tasks
    manifest = dependency_manifest(root) if manifest is None else dict(manifest)
    execution = copied.get("execution") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("parent_algorithm") != {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": base["protocol_id"],
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
        }
        or copied.get("task_contract") != _task_contract(tasks)
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or execution.get("executor_concurrency") != 20
        or execution.get("model_slot_cap") != 8
        or execution.get("task_wall_seconds") != 240
        or execution.get("model_calls_per_task") != 3
        or execution.get("search_queries_per_task") != 4
        or execution.get("fetch_targets_per_task") != 10
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("two_wave_policy") != TWO_WAVE_POLICY
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or copied.get("single_change") != _single_change()
        or copied.get("source_policy", {}).get("runtime_reads_only_opaque_id_and_question") is not True
        or copied.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward"
        ) is not False
        or copied.get("source_policy", {}).get(
            "explicit_user_request_authorizes_one_cold_exact220_replication"
        ) is not True
        or copied.get("authorization") != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
    ):
        raise RuntimeError("V2.49.35 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "parent_contract",
    "payload_sha256",
    "protected_watcher_snapshot",
    "sha256",
    "task_vector",
    "validate_protocol",
]
