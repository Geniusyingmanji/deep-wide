"""Corrected append-only exact-220 contract after V2.48.77 launch failure."""

from __future__ import annotations

import copy
from pathlib import Path

from . import v24877_keyless_coverage_exact220_contract as parent


DATE = "20260808"
ROLE = "v24878_corrected_keyless_coverage_exact220_preregistration"
PROTOCOL_ID = "v24878_corrected_keyless_fixed_budget_coverage_exact220_v1"
PROTOCOL = Path(
    f"results/v24878_keyless_coverage_exact220_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24878_keyless_coverage_exact220_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24878_keyless_coverage_exact220_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v24878_keyless_coverage_exact220_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v24878_keyless_coverage_exact220_forward_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24878_keyless_coverage_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24878_keyless_coverage_exact220_forward_v1"
LEASE_PURPOSE = "fresh_corrected_label_blind_keyless_coverage_exact220"
RUNNER_MARKER = "scripts/run_v24878_keyless_coverage_exact220.py"
CHILD_MARKER = "scripts/run_v24878_keyless_coverage_exact220_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
BUILD_AUDIT = parent.BUILD_AUDIT
SOURCE = Path("src/deepwide_agent/v24878_keyless_coverage_exact220_contract.py")
CONTROL = Path("scripts/control_v24878_keyless_coverage_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24878_keyless_coverage_exact220.py")
TEST = Path("tests/test_v24878_keyless_coverage_exact220.py")
RUNNER_FIX_TEST = Path("tests/test_v24878_keyless_coverage_runner_fix.py")
LAUNCH_FAILURE = Path(
    "results/v24877_keyless_coverage_exact220_launch_failure_v1_20260808.json"
)
SEAM_SOURCES = parent.SEAM_SOURCES
SEAM_TESTS = parent.SEAM_TESTS
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST, RUNNER_FIX_TEST)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked
protected_watcher_snapshot = parent.protected_watcher_snapshot
coverage_policy = parent.coverage_policy
parent_contract = parent.parent_contract
task_vector = parent.task_vector


def dependency_manifest(root: Path) -> dict[str, str]:
    relatives = {Path(name) for name in parent.dependency_manifest(root)}
    relatives.update((PARENT_PROTOCOL, LAUNCH_FAILURE))
    relatives.update(LOCAL_SOURCES)
    relatives.update(
        (
            Path("scripts/run_v24877_keyless_coverage_exact220.py"),
            Path("scripts/run_v24877_keyless_coverage_exact220_task.py"),
        )
    )
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def frozen_dependency_manifest(root: Path) -> dict[str, str]:
    relatives = {Path(name) for name in parent.frozen_dependency_manifest(root)}
    relatives.update((PARENT_PROTOCOL, LAUNCH_FAILURE))
    relatives.update(LOCAL_SOURCES)
    relatives.update(
        (
            Path("scripts/run_v24877_keyless_coverage_exact220.py"),
            Path("scripts/run_v24877_keyless_coverage_exact220_task.py"),
        )
    )
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def _patch(value: dict) -> dict:
    copied = copy.deepcopy(value)
    copied["role"] = ROLE
    copied["protocol_id"] = PROTOCOL_ID
    copied["parent_algorithm"] = {
        "path": str(PARENT_PROTOCOL),
        "sha256": sha256(Path(__file__).resolve().parents[2] / PARENT_PROTOCOL),
        "protocol_id": parent.PROTOCOL_ID,
        "dependency_manifest_sha256": value["dependency_manifest_sha256"],
        "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
    }
    copied["execution"]["output_root"] = str(OUTPUT_ROOT)
    copied["execution"]["corrected_child_environment_binding"] = True
    copied["single_change"] = {
        "parent": "v24877_pre_subprocess_launch_failure",
        "change": "concrete_nonrecursive_child_environment_and_static_successor_paths",
        "all_algorithm_model_search_budget_concurrency_values_unchanged": True,
        "v24877_resume_retry_or_reuse": False,
    }
    copied["dependency_manifest"] = dependency_manifest(
        Path(__file__).resolve().parents[2]
    )
    copied["dependency_manifest_sha256"] = payload_sha256(
        copied["dependency_manifest"]
    )
    copied.pop("protocol_payload_sha256", None)
    copied["protocol_payload_sha256"] = payload_sha256(copied)
    return copied


def build_protocol(root: Path, *, now: int, require_clean: bool = True, require_pristine: bool = True) -> dict:
    if require_clean and (
        _git(root, "status", "--porcelain")
        or _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.48.78 protocol requires clean pushed HEAD")
    future = (PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise FileExistsError("V2.48.78 future surface exists")
    base = parent.build_protocol(root, now=now, require_clean=False, require_pristine=False)
    value = _patch(base)
    value["created_at_unix"] = int(now)
    value["git_head"] = _git(root, "rev-parse", "HEAD")
    value.pop("protocol_payload_sha256", None)
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value)


def validate_protocol(root: Path, value) -> dict:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    execution = copied.get("execution") or {}
    task = copied.get("task_contract") or {}
    manifest = dependency_manifest(root)
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("parent_algorithm", {}).get("path") != str(PARENT_PROTOCOL)
        or copied.get("parent_algorithm", {}).get("sha256") != sha256(root / PARENT_PROTOCOL)
        or task.get("runtime_input_keys") != ["opaque_id", "question"]
        or task.get("selected_count") != 220
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
        or execution.get("corrected_child_environment_binding") is not True
        or copied.get("single_change")
        != {
            "parent": "v24877_pre_subprocess_launch_failure",
            "change": "concrete_nonrecursive_child_environment_and_static_successor_paths",
            "all_algorithm_model_search_budget_concurrency_values_unchanged": True,
            "v24877_resume_retry_or_reuse": False,
        }
    ):
        raise RuntimeError("V2.48.78 protocol drifted")
    task_vector(root, copied)
    return copied


def validate_frozen_protocol(root: Path, value) -> dict:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    execution = copied.get("execution") or {}
    task = copied.get("task_contract") or {}
    manifest = frozen_dependency_manifest(root)
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or task.get("runtime_input_keys") != ["opaque_id", "question"]
        or task.get("selected_count") != 220
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("corrected_child_environment_binding") is not True
        or execution.get("protected_watchers") != protected_watcher_snapshot()
    ):
        raise RuntimeError("V2.48.78 frozen protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "coverage_policy",
    "dependency_manifest",
    "frozen_dependency_manifest",
    "parent_contract",
    "payload_sha256",
    "protected_watcher_snapshot",
    "sha256",
    "task_vector",
    "validate_frozen_protocol",
    "validate_protocol",
]
