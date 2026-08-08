"""Control-binding-only successor of the V2.48.94 exact-220 contract."""

from __future__ import annotations

import copy
from pathlib import Path

from . import v24894_revision_envelope_exact220_contract as parent


DATE = "20260808"
ROLE = "v24895_control_binding_exact220_preregistration"
PROTOCOL_ID = "v24895_revision_envelope_control_binding_exact220_v1"
PROTOCOL = Path(f"results/v24895_control_binding_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24895_control_binding_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24895_control_binding_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24895_control_binding_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24895_control_binding_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24895_control_binding_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24895_control_binding_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_revision_envelope_control_binding_exact220"
RUNNER_MARKER = "scripts/run_v24895_control_binding_exact220.py"
CHILD_MARKER = "scripts/run_v24895_control_binding_exact220_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
SOURCE = Path("src/deepwide_agent/v24895_control_binding_exact220_contract.py")
CONTROL = Path("scripts/control_v24895_control_binding_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24895_control_binding_exact220.py")
TEST = Path("tests/test_v24895_control_binding_exact220.py")
V24894_INVALID_AUDIT = Path(
    "results/v24894_revision_envelope_exact220_preactivation_audit_v1_20260808.json"
)
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)
SEAM_SOURCES = parent.SEAM_SOURCES
SEAM_TESTS = parent.SEAM_TESTS
CORRECTED_SOURCES = parent.CORRECTED_SOURCES
CORRECTED_TESTS = parent.CORRECTED_TESTS

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked
protected_watcher_snapshot = parent.protected_watcher_snapshot
coverage_policy = parent.coverage_policy
task_vector = parent.task_vector
validate_reliability_gate = parent.validate_reliability_gate


def parent_contract(root: Path, *, frozen: bool = False) -> dict:
    value = parent._read(root / PARENT_PROTOCOL)
    return (
        parent.validate_frozen_protocol(root, value)
        if frozen
        else parent.validate_protocol(root, value)
    )


def _relatives(root: Path, *, frozen: bool) -> set[Path]:
    base = parent_contract(root, frozen=frozen)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update((PARENT_PROTOCOL, V24894_INVALID_AUDIT))
    relatives.update(LOCAL_SOURCES)
    relatives.update(
        (
            Path("scripts/run_v24877_keyless_coverage_exact220.py"),
            Path("scripts/run_v24877_keyless_coverage_exact220_task.py"),
            Path("scripts/control_v24877_keyless_coverage_exact220.py"),
            Path("scripts/finalize_v24877_keyless_coverage_exact220.py"),
        )
    )
    return relatives


def dependency_manifest(root: Path) -> dict[str, str]:
    return {
        str(path): sha256(_ordinary_tracked(root, path))
        for path in sorted(_relatives(root, frozen=False), key=str)
    }


def frozen_dependency_manifest(root: Path) -> dict[str, str]:
    return {
        str(path): sha256(_ordinary_tracked(root, path))
        for path in sorted(_relatives(root, frozen=True), key=str)
    }


def _patch(root: Path, value: dict) -> dict:
    copied = copy.deepcopy(value)
    copied["role"] = ROLE
    copied["protocol_id"] = PROTOCOL_ID
    copied["parent_algorithm"] = {
        "path": str(PARENT_PROTOCOL),
        "sha256": sha256(root / PARENT_PROTOCOL),
        "protocol_id": parent.PROTOCOL_ID,
        "dependency_manifest_sha256": value["dependency_manifest_sha256"],
        "prior_prediction_result_score_or_evaluator_reused_by_forward": False,
    }
    copied["execution"]["output_root"] = str(OUTPUT_ROOT)
    copied["execution"]["control_binding_corrected"] = True
    copied["single_change"] = {
        "parent": parent.PROTOCOL_ID,
        "change": "control_role_namespace_binding_only",
        "invalid_parent_audit_path": str(V24894_INVALID_AUDIT),
        "invalid_parent_audit_sha256": sha256(root / V24894_INVALID_AUDIT),
        "all_runtime_algorithm_task_vector_model_search_budget_controller_and_concurrency_values_unchanged": True,
        "retry_resume_skip_or_selective_rerun": False,
    }
    manifest = dependency_manifest(root)
    copied["dependency_manifest"] = manifest
    copied["dependency_manifest_sha256"] = payload_sha256(manifest)
    copied["authorization"] = {
        "preactivation_audit_generation": True,
        "execution_start_generation": False,
        "single_fresh_exact220_forward": False,
        "evaluator_call": False,
        "retry_resume_skip_or_selective_rerun": False,
    }
    copied.pop("protocol_payload_sha256", None)
    copied["protocol_payload_sha256"] = payload_sha256(copied)
    return copied


def build_protocol(root: Path, *, now: int, require_clean: bool = True, require_pristine: bool = True) -> dict:
    if require_clean and (
        _git(root, "status", "--porcelain")
        or _git(root, "rev-parse", "HEAD") != _git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.48.95 protocol requires clean pushed HEAD")
    future = (PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT, OUTPUT_ROOT)
    if require_pristine and any((root / p).exists() or (root / p).is_symlink() for p in future):
        raise FileExistsError("V2.48.95 future surface exists")
    value = _patch(
        root,
        parent.build_protocol(
            root, now=now, require_clean=False, require_pristine=False
        ),
    )
    value["created_at_unix"] = int(now)
    value["git_head"] = _git(root, "rev-parse", "HEAD")
    value.pop("protocol_payload_sha256", None)
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value)


def _validate(root: Path, value: dict, *, frozen: bool) -> dict:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    manifest = frozen_dependency_manifest(root) if frozen else dependency_manifest(root)
    execution = copied.get("execution") or {}
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("parent_algorithm", {}).get("path") != str(PARENT_PROTOCOL)
        or copied.get("parent_algorithm", {}).get("sha256") != sha256(root / PARENT_PROTOCOL)
        or copied.get("task_contract", {}).get("runtime_input_keys") != ["opaque_id", "question"]
        or copied.get("task_contract", {}).get("selected_count") != 220
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or execution.get("executor_concurrency") != 20
        or execution.get("model_slot_cap") != 8
        or execution.get("task_wall_seconds") != 240
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("two_wave_policy") != TWO_WAVE_POLICY
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("control_binding_corrected") is not True
        or copied.get("single_change", {}).get("change")
        != "control_role_namespace_binding_only"
        or copied.get("authorization") != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
    ):
        raise RuntimeError("V2.48.95 protocol drifted")
    if not frozen:
        task_vector(root, copied)
    return copied


def validate_protocol(root: Path, value: dict) -> dict:
    return _validate(root, value, frozen=False)


def validate_frozen_protocol(root: Path, value: dict) -> dict:
    return _validate(root, value, frozen=True)


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol", "coverage_policy", "dependency_manifest",
    "frozen_dependency_manifest", "parent_contract", "payload_sha256",
    "protected_watcher_snapshot", "sha256", "task_vector",
    "validate_frozen_protocol", "validate_protocol", "validate_reliability_gate",
]
