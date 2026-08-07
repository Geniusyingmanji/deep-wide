"""Fresh label-blind V2.48.33 coverage-margin exact-220 contract."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24831_keyless_exact220_contract as parent
from .v24833_coverage_margin_controller import POLICY_VALUES


DATE = "20260807"
ROLE = "v24834_coverage_margin_exact220_preregistration"
PROTOCOL_ID = "v24834_fresh_v24833_coverage_margin_exact220_v1"
PROTOCOL = Path(f"results/v24834_coverage_margin_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24834_coverage_margin_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24834_coverage_margin_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24834_coverage_margin_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24834_coverage_margin_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24834_coverage_margin_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24834_coverage_margin_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_v24833_coverage_margin_exact220"
RUNNER_MARKER = "scripts/run_v24834_coverage_margin_exact220.py"
CHILD_MARKER = "scripts/run_v24834_coverage_margin_exact220_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(POLICY_VALUES)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
CONTROLLER_AUDIT = Path(
    "results/v24833_coverage_margin_controller_build_audit_v1_20260807.json"
)
SOURCE = Path("src/deepwide_agent/v24834_coverage_margin_exact220_contract.py")
CONTROLLER_SOURCE = Path("src/deepwide_agent/v24833_coverage_margin_controller.py")
CONTROL = Path("scripts/control_v24834_coverage_margin_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24834_coverage_margin_exact220.py")
TEST = Path("tests/test_v24834_coverage_margin_exact220.py")
LOCAL_SOURCES = (
    SOURCE,
    CONTROLLER_SOURCE,
    CONTROL,
    RUNNER,
    CHILD,
    FINALIZER,
    TEST,
)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.48.34 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.34 expected JSON object")
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
        raise RuntimeError("V2.48.34 visible exact-220 vector drifted")
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
            raise RuntimeError("V2.48.34 visible task binding drifted")
    return tasks


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.add(PARENT_PROTOCOL)
    relatives.add(CONTROLLER_AUDIT)
    relatives.update(LOCAL_SOURCES)
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
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
        raise RuntimeError("V2.48.34 protocol requires clean pushed HEAD")
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
        raise FileExistsError("V2.48.34 future surface exists")
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    controller_audit = _read(root / CONTROLLER_AUDIT)
    if (
        controller_audit.get("role")
        != "v24833_coverage_margin_controller_build_audit"
        or controller_audit.get("audit_valid") is not True
        or controller_audit.get("findings") != []
        or controller_audit.get("policy") != TWO_WAVE_POLICY
    ):
        raise RuntimeError("V2.48.34 controller audit drifted")
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
        "controller": {
            "policy_id": "v24833_label_blind_coverage_margin_controller_v1",
            "source": str(CONTROLLER_SOURCE),
            "build_audit": str(CONTROLLER_AUDIT),
            "build_audit_sha256": sha256(root / CONTROLLER_AUDIT),
            "policy": copy.deepcopy(TWO_WAVE_POLICY),
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_credit": False,
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
            "model": MODEL,
            "search": SEARCH,
            "two_wave_policy": TWO_WAVE_POLICY,
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "single_fresh_forward_no_retry_resume_or_selective_rerun": True,
        },
        "single_change": {
            "fresh_execution_surfaces_only": True,
            "task_vector_prompt_model_search_maxima_and_concurrency_equal_v24831": True,
            "v24831_two_wave_policy_replaced_by_frozen_v24833_coverage_margin_policy": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "controller_reads_only_same_pass_content_free_first_wave_observation": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "prior_v24831_output_prediction_result_score_or_evaluator_opened_or_hashed": False,
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
    execution = copied.get("execution", {})
    controller = copied.get("controller", {})
    expected_tasks = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
        "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
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
        or controller.get("policy_id")
        != "v24833_label_blind_coverage_margin_controller_v1"
        or controller.get("build_audit_sha256") != sha256(root / CONTROLLER_AUDIT)
        or controller.get("policy") != TWO_WAVE_POLICY
        or controller.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get("task_contract") != expected_tasks
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
        or copied.get("single_change", {}).get(
            "v24831_two_wave_policy_replaced_by_frozen_v24833_coverage_margin_policy"
        )
        is not True
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
        raise RuntimeError("V2.48.34 protocol drifted")
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
