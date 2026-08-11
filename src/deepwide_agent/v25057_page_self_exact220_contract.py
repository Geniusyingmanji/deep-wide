"""Fresh r2 contract after V2.50.56's preactivation-only test failure.

V2.50.56 never created a preactivation audit, execution start, output root, or
any network/model/search/fetch/evaluator effect.  This successor uses distinct
immutable paths and roles while preserving its exact task vector, treatment,
resource caps, concurrency, and unconditional fixed-220 evaluation contract.
"""

from __future__ import annotations

import copy
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from . import v25056_page_self_exact220_contract as base


DATE = "20260811"
PROTOCOL_ID = "v25057_page_self_evidence_conditioned_keyless_exact220_r2"
BUILD_AUDIT = Path(f"results/v25057_page_self_exact220_build_audit_r2_{DATE}.json")
PROTOCOL = Path(f"results/v25057_page_self_exact220_preregistration_r2_{DATE}.json")
PREAUDIT = Path(f"results/v25057_page_self_exact220_preactivation_audit_r2_{DATE}.json")
EXECUTION_START = Path(f"results/v25057_page_self_exact220_execution_start_r2_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25057_page_self_exact220_forward_result_r2_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25057_page_self_exact220_forward_audit_r2_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v25057_page_self_exact220_evaluator_preregistration_r2_{DATE}.json")
RESULT = Path(f"results/v25057_page_self_exact220_result_r2_{DATE}.json")
POSTAUDIT = Path(f"results/v25057_page_self_exact220_postresult_audit_r2_{DATE}.json")

OUTPUT_ROOT = Path(f"outputs/v25057_page_self_exact220_r2_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
RUNTIME_RESULTS = OUTPUT_ROOT / "runtime_results.jsonl"
TASK_RECEIPTS = OUTPUT_ROOT / "content_free_task_receipts.jsonl"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25057_page_self_exact220_forward_r2"
LEASE_PURPOSE = "single_label_blind_page_self_representation_exact220_r2"

PARENT_TASK_PROTOCOL = base.PARENT_TASK_PROTOCOL
VISIBLE_MANIFEST = base.VISIBLE_MANIFEST
ID_SOURCES = base.ID_SOURCES
ID_COUNTS = base.ID_COUNTS
OPAQUE = base.OPAQUE
SELECTED_COUNT = base.SELECTED_COUNT
EXECUTOR_CONCURRENCY = base.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = base.MODEL_SLOT_CAP
CLEANUP_RESERVE_SECONDS = base.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = base.MINIMUM_MODEL_ATTEMPT_SECONDS
LIMITS = copy.deepcopy(base.LIMITS)
MODEL = copy.deepcopy(base.MODEL)
SEARCH = copy.deepcopy(base.SEARCH)
PROTECTED_WATCHERS = base.PROTECTED_WATCHERS

SOURCE = Path("src/deepwide_agent/v25057_page_self_exact220_contract.py")
RUNTIME = base.RUNTIME
REFINEMENT = base.REFINEMENT
PARENT_SHARED_WAVE = base.PARENT_SHARED_WAVE
PARENT_COMPACT = base.PARENT_COMPACT
PARENT_ROBUST = base.PARENT_ROBUST
PARENT_COUNTERS = base.PARENT_COUNTERS
FETCH = base.FETCH
FETCH_HELPER = base.FETCH_HELPER
REPRESENTATION = base.REPRESENTATION
LEASE = base.LEASE
CONTROL = Path("scripts/control_v25057_page_self_exact220.py")
RUNNER = Path("scripts/run_v25057_page_self_exact220.py")
FINALIZER = Path("scripts/finalize_v25057_page_self_exact220.py")
TEST = Path("tests/test_v25057_page_self_exact220.py")
PARENT_TESTS = (Path("tests/test_v25056_page_self_exact220.py"), *base.PARENT_TESTS)
RUNNER_MARKER = str(RUNNER)
CHILD_MARKER = "v25057_no_child_process"
BUILD_ROLE = "v25057_page_self_exact220_build_audit"
PROTOCOL_ROLE = "v25057_page_self_exact220_preregistration"
PREAUDIT_ROLE = "v25057_page_self_exact220_preactivation_audit"
START_ROLE = "v25057_page_self_exact220_execution_start"
PROGRESS_ROLE = "v25057_page_self_exact220_safe_progress"
SLOT_ROLE = "v25057_model_slot"
SUMMARY_ROLE = "v25057_page_self_exact220_run_summary"
FREEZE_ROLE = "v25057_page_self_exact220_prediction_freeze"
FORWARD_ROLE = "v25057_page_self_exact220_forward_result"
FORWARD_AUDIT_NATIVE_ROLE = "v25057_page_self_exact220_forward_audit"
EVALUATOR_OWNER = "v25057_page_self_exact220_evaluator_r2"
EVALUATOR_PURPOSE = "postfreeze_fixed_partition_parallel_v25057_exact220_evaluator"
EVALUATOR_FREEZE_BINDING_FIELD = (
    "native_v25057_prediction_freeze_bound_by_role_projection"
)
V25056_BUILD_AUDIT = Path(
    "results/v25056_page_self_exact220_build_audit_v1_20260811.json"
)
V25056_PROTOCOL = Path(
    "results/v25056_page_self_exact220_preregistration_v1_20260811.json"
)
V25056_PREAUDIT = Path(
    "results/v25056_page_self_exact220_preactivation_audit_v1_20260811.json"
)
V25056_START = Path(
    "results/v25056_page_self_exact220_execution_start_v1_20260811.json"
)
V25056_OUTPUT_ROOT = Path("outputs/v25056_page_self_exact220_v1_20260811")
FORWARD_SOURCES = (
    SOURCE, RUNTIME, REFINEMENT, PARENT_SHARED_WAVE, PARENT_COMPACT,
    PARENT_ROBUST, PARENT_COUNTERS, FETCH, FETCH_HELPER, REPRESENTATION,
    LEASE, RUNNER,
)
LOCAL_SOURCES = (*FORWARD_SOURCES, CONTROL, FINALIZER, TEST, PARENT_TASK_PROTOCOL)
_LEGACY_RUNNER_ROLES = {
    "v25030_evidence_conditioned_exact220_build_audit": BUILD_ROLE,
    "v25030_evidence_conditioned_exact220_preactivation_audit": PREAUDIT_ROLE,
    "v25030_evidence_conditioned_exact220_execution_start": START_ROLE,
    "v25030_evidence_conditioned_exact220_safe_progress": PROGRESS_ROLE,
    "v25030_evidence_conditioned_exact220_prediction_freeze": FREEZE_ROLE,
    "v25030_evidence_conditioned_exact220_forward_result": FORWARD_ROLE,
}

_PATCH = {
    name: value
    for name, value in globals().copy().items()
    if (name == "_LEGACY_RUNNER_ROLES" or name.isupper())
    and hasattr(base, name)
}


@contextmanager
def _configured() -> Iterator[None]:
    previous = {name: getattr(base, name) for name in _PATCH}
    try:
        for name, value in _PATCH.items():
            setattr(base, name, value)
        yield
    finally:
        for name, value in previous.items():
            setattr(base, name, value)


payload_sha256 = base.payload_sha256
sha256 = base.sha256
git = base.git
protected_watcher_snapshot = base.protected_watcher_snapshot
_ordinary = base._ordinary
_parent_task_contract = base._parent_task_contract
_input_bindings = base._input_bindings


def seal(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    with _configured():
        return base.seal(value, field)


def sealed(value: Mapping[str, Any], field: str) -> bool:
    return base.sealed(value, field)


def task_vector(root: Path, protocol: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    with _configured():
        return base.task_vector(root, protocol)


def forward_dependency_closure(root: Path) -> tuple[Path, ...]:
    with _configured():
        return base.forward_dependency_closure(root)


def dependency_manifest(root: Path, *, tracked: bool = True) -> dict[str, str]:
    with _configured():
        return base.dependency_manifest(root, tracked=tracked)


def _build_audit_binding(root: Path) -> dict[str, str] | None:
    with _configured():
        return base._build_audit_binding(root)


def _predecessor_disposition(root: Path) -> dict[str, Any]:
    build = _ordinary(V25056_BUILD_AUDIT, root)
    protocol = _ordinary(V25056_PROTOCOL, root)
    effects_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in (V25056_PREAUDIT, V25056_START, V25056_OUTPUT_ROOT)
    )
    value = {
        "protocol_id": base.PROTOCOL_ID,
        "build_audit_sha256": sha256(build),
        "protocol_sha256": sha256(protocol),
        "failure_stage": "preactivation_focused_test_validation_before_publication",
        "observed_tests": 64,
        "stage_unstable_test_errors": 2,
        "preactivation_audit_published": False,
        "execution_start_published": False,
        "output_root_created": False,
        "network_model_search_fetch_evaluator_or_api_called": False,
        "old_protocol_or_output_reused_by_r2": False,
        "all_effect_surfaces_absent": effects_absent,
    }
    if not effects_absent:
        raise RuntimeError("V2.50.57 predecessor effect surface is not absent")
    return value


def build_protocol(
    root: Path, *, now: int, tracked: bool = True,
    require_clean: bool = True, require_pristine: bool = True,
) -> dict[str, Any]:
    with _configured():
        value = base.build_protocol(
            root, now=now, tracked=tracked, require_clean=require_clean,
            require_pristine=require_pristine,
        )
    value = copy.deepcopy(value)
    value["predecessor_disposition"] = _predecessor_disposition(root)
    value["treatment_scope"]["v25056_preactivation_failed_before_any_effect"] = True
    value["treatment_scope"]["v25056_protocol_or_outputs_reused"] = False
    value["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "protocol_payload_sha256"}
    )
    return validate_protocol(root, value, tracked=tracked)


def validate_protocol(
    root: Path, value: Mapping[str, Any], *, tracked: bool = True
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    treatment = copied.get("treatment_scope") or {}
    if (
        copied.get("predecessor_disposition") != _predecessor_disposition(root)
        or copied.get("predecessor_disposition", {}).get(
            "network_model_search_fetch_evaluator_or_api_called"
        )
        is not False
        or
        treatment.get("v25056_preactivation_failed_before_any_effect") is not True
        or treatment.get("v25056_protocol_or_outputs_reused") is not False
    ):
        raise RuntimeError("V2.50.57 predecessor disposition drifted")
    projected = copy.deepcopy(copied)
    projected.pop("predecessor_disposition", None)
    projected["treatment_scope"].pop(
        "v25056_preactivation_failed_before_any_effect", None
    )
    projected["treatment_scope"].pop("v25056_protocol_or_outputs_reused", None)
    projected["protocol_payload_sha256"] = payload_sha256(
        {key: item for key, item in projected.items() if key != "protocol_payload_sha256"}
    )
    with _configured():
        base.validate_protocol(root, projected, tracked=tracked)
    unsigned = copy.deepcopy(copied)
    observed = unsigned.pop("protocol_payload_sha256", None)
    if observed != payload_sha256(unsigned):
        raise RuntimeError("V2.50.57 protocol seal drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol", "dependency_manifest", "forward_dependency_closure",
    "git", "payload_sha256", "protected_watcher_snapshot", "seal", "sealed",
    "sha256", "task_vector", "validate_protocol",
]
