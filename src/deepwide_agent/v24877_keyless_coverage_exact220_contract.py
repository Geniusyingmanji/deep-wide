"""Fresh label-blind exact-220 contract for the keyless coverage seam.

V2.48.77 binds the audited V2.48.73--76 production seam to the same public
220-task vector, model, keyless hosted-search transport, and hard budgets used
by V2.48.31.  The retrieval controller is the frozen V2.47.99 fixed-full-
budget no-entropy control.  Entropy and information gain remain shadow-only.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24831_keyless_exact220_contract as parent
from .v24799_fixed_full_budget_control import POLICY_VALUES
from .v24859_full_evidence_coverage_revision import (
    MINIMUM_NEW_ROW_SOURCES,
    MINIMUM_OVERRIDE_SOURCES,
    MINIMUM_UNKNOWN_SOURCES,
)
from .v24873_keyless_fixed_coverage_runtime import POLICY_ID as RUNTIME_POLICY_ID
from .v24874_keyless_coverage_bundle import POLICY_ID as BUNDLE_POLICY_ID
from .v24875_keyless_coverage_child_runtime import POLICY_ID as CHILD_POLICY_ID
from .v24876_keyless_coverage_subprocess_gate import POLICY_ID as GATE_POLICY_ID


DATE = "20260808"
ROLE = "v24877_keyless_coverage_exact220_preregistration"
PROTOCOL_ID = "v24877_keyless_fixed_budget_coverage_exact220_v1"
PROTOCOL = Path(
    f"results/v24877_keyless_coverage_exact220_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24877_keyless_coverage_exact220_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24877_keyless_coverage_exact220_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v24877_keyless_coverage_exact220_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v24877_keyless_coverage_exact220_forward_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24877_keyless_coverage_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24877_keyless_coverage_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_keyless_fixed_budget_coverage_exact220"
RUNNER_MARKER = "scripts/run_v24877_keyless_coverage_exact220.py"
CHILD_MARKER = "scripts/run_v24877_keyless_coverage_exact220_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(POLICY_VALUES)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
BUILD_AUDIT = Path("results/v24876_keyless_coverage_build_audit_v1_20260808.json")
SOURCE = Path("src/deepwide_agent/v24877_keyless_coverage_exact220_contract.py")
CONTROL = Path("scripts/control_v24877_keyless_coverage_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24877_keyless_coverage_exact220.py")
TEST = Path("tests/test_v24877_keyless_coverage_exact220.py")
SEAM_SOURCES = tuple(
    Path(f"src/deepwide_agent/v248{version}_{name}.py")
    for version, name in (
        (73, "keyless_fixed_coverage_runtime"),
        (74, "keyless_coverage_bundle"),
        (75, "keyless_coverage_child_runtime"),
        (76, "keyless_coverage_subprocess_gate"),
    )
)
SEAM_TESTS = tuple(
    Path(f"tests/test_v248{version}_{name}.py")
    for version, name in (
        (73, "keyless_fixed_coverage_runtime"),
        (74, "keyless_coverage_bundle"),
        (75, "keyless_coverage_child_runtime"),
        (76, "keyless_coverage_subprocess_gate"),
    )
)
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.48.77 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.77 expected object")
    return value


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    return parent.protected_watcher_snapshot(proc_root)


def parent_contract(root: Path) -> dict[str, Any]:
    return parent.validate_protocol(root, _read(root / PARENT_PROTOCOL))


def task_vector(
    root: Path, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    tasks = parent.task_vector(root, parent_contract(root))
    if len(tasks) != SELECTED_COUNT or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.48.77 visible exact-220 vector drifted")
    if protocol is not None:
        observed = {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
        }
        if protocol.get("task_contract") != observed:
            raise RuntimeError("V2.48.77 visible task binding drifted")
    return tasks


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update((PARENT_PROTOCOL, BUILD_AUDIT))
    relatives.update(SEAM_SOURCES)
    relatives.update(SEAM_TESTS)
    relatives.update(LOCAL_SOURCES)
    relatives.update(
        (
            Path("src/deepwide_agent/v24799_fixed_full_budget_control.py"),
            Path("src/deepwide_agent/v24859_full_evidence_coverage_revision.py"),
            Path("src/deepwide_agent/v24860_coverage_revision_integration.py"),
            Path("src/deepwide_agent/v24861_coverage_revision_exact_task.py"),
            Path("scripts/run_v24635_exact220.py"),
            Path("scripts/run_v24831_keyless_exact220.py"),
        )
    )
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def coverage_policy() -> dict[str, Any]:
    return {
        "runtime_policy_id": RUNTIME_POLICY_ID,
        "bundle_policy_id": BUNDLE_POLICY_ID,
        "child_policy_id": CHILD_POLICY_ID,
        "subprocess_gate_policy_id": GATE_POLICY_ID,
        "unknown_fill_minimum_independent_sources": MINIMUM_UNKNOWN_SOURCES,
        "known_override_minimum_independent_sources": MINIMUM_OVERRIDE_SOURCES,
        "new_row_minimum_independent_sources": MINIMUM_NEW_ROW_SOURCES,
        "baseline_row_deletion_allowed": False,
        "logical_query_count_equal_http_response_count_required": False,
        "actual_fetch_count_equal_fetch_cap_required": False,
        "low_source_or_pre_provider_failure_preserves_parent_prediction": True,
        "entropy_or_information_gain_used_for_admission_or_routing": False,
        "entropy_or_information_gain_shadow_measurement_only": True,
    }


def _parent_equalities() -> dict[str, bool]:
    values = {
        "selected_equal_v24831": SELECTED_COUNT == parent.SELECTED_COUNT,
        "concurrency_equal_v24831": EXECUTOR_CONCURRENCY == parent.EXECUTOR_CONCURRENCY,
        "model_slots_equal_v24831": MODEL_SLOT_CAP == parent.MODEL_SLOT_CAP,
        "limits_equal_v24831": LIMITS == parent.LIMITS,
        "model_equal_v24831": MODEL == parent.MODEL,
        "search_equal_v24831": SEARCH == parent.SEARCH,
    }
    if not all(values.values()):
        raise RuntimeError("V2.48.77 parent equality drifted")
    return values


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
        raise RuntimeError("V2.48.77 protocol requires clean pushed HEAD")
    future = (
        PROTOCOL,
        PREAUDIT,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        OUTPUT_ROOT,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink() for path in future
    ):
        raise FileExistsError("V2.48.77 future surface exists")
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    audit = _read(root / BUILD_AUDIT)
    if (
        audit.get("role") != "v24876_keyless_coverage_build_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("label_blind_audit", {}).get("passed") is not True
    ):
        raise RuntimeError("V2.48.77 build audit drifted")
    value = {
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
        "production_seam": {
            "build_audit": str(BUILD_AUDIT),
            "build_audit_sha256": sha256(root / BUILD_AUDIT),
            "coverage_policy": coverage_policy(),
        },
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
        },
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
        "single_change": {
            "parent": "v24831_keyless_exact220",
            "change": "fixed_full_budget_same_forward_coverage_revision",
            "parent_equalities": _parent_equalities(),
            "frozen_keyless_coverage_production_seam": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "prior_output_prediction_result_score_or_evaluator_opened_or_hashed": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "fixed_public_exact220_task_set_reexecuted": True,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
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
    return validate_protocol(root, value)


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    execution = copied.get("execution") or {}
    expected_tasks = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256(
            [task["opaque_id"] for task in tasks]
        ),
        "visible_question_vector_sha256": payload_sha256(
            [task["question"] for task in tasks]
        ),
    }
    if (
        copied.get("role") != ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or copied.get("parent_algorithm")
        != {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": base["protocol_id"],
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
        }
        or copied.get("production_seam")
        != {
            "build_audit": str(BUILD_AUDIT),
            "build_audit_sha256": sha256(root / BUILD_AUDIT),
            "coverage_policy": coverage_policy(),
        }
        or copied.get("task_contract") != expected_tasks
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
        or copied.get("single_change")
        != {
            "parent": "v24831_keyless_exact220",
            "change": "fixed_full_budget_same_forward_coverage_revision",
            "parent_equalities": _parent_equalities(),
            "frozen_keyless_coverage_production_seam": True,
        }
        or copied.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward"
        )
        is not False
        or copied.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
    ):
        raise RuntimeError("V2.48.77 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "coverage_policy",
    "dependency_manifest",
    "parent_contract",
    "payload_sha256",
    "protected_watcher_snapshot",
    "sha256",
    "task_vector",
    "validate_protocol",
]
