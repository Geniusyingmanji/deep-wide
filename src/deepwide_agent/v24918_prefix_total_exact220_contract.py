"""Frozen label-blind exact-220 contract for the V2.49.16 totality repair."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24914_cap_bound_long_page_exact220_contract as parent
from . import v24916_prefix_total_runtime_binding as binding


DATE = "20260808"
ROLE = "v24918_prefix_total_exact220_preregistration"
PROTOCOL_ID = "v24918_keyless_fixed_budget_prefix_total_exact220_v2"
PROTOCOL = Path(f"results/v24918_prefix_total_exact220_preregistration_v2_{DATE}.json")
PREAUDIT = Path(f"results/v24918_prefix_total_exact220_preactivation_audit_v2_{DATE}.json")
EXECUTION_START = Path(f"results/v24918_prefix_total_exact220_execution_start_v2_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24918_prefix_total_exact220_forward_result_v2_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24918_prefix_total_exact220_forward_audit_v2_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24918_prefix_total_exact220_v2_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24918_prefix_total_exact220_forward_v2"
LEASE_PURPOSE = "fresh_label_blind_fixed_budget_prefix_total_exact220"
RUNNER_MARKER = "scripts/run_v24918_prefix_total_exact220.py"
CHILD_MARKER = "scripts/run_v24918_prefix_total_exact220_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
BUILD_AUDIT = Path("results/v24916_prefix_total_long_page_build_audit_v1_20260808.json")
SOURCE = Path("src/deepwide_agent/v24918_prefix_total_exact220_contract.py")
FETCH_SOURCE = parent.FETCH_SOURCE
FETCH_HELPER = parent.FETCH_HELPER
PACKER_SOURCE = Path("src/deepwide_agent/v24916_prefix_total_long_page_packer.py")
BINDING_SOURCE = Path("src/deepwide_agent/v24916_prefix_total_runtime_binding.py")
GENERIC_CHILD = Path("scripts/run_v24916_prefix_total_long_page_task.py")
CONTROL = Path("scripts/control_v24918_prefix_total_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24918_prefix_total_exact220.py")
TEST = Path("tests/test_v24918_prefix_total_exact220.py")
RECEIPT_TEST = Path("tests/test_v24918_prefix_total_receipt_integration.py")
LOCAL_SOURCES = (
    SOURCE,
    PACKER_SOURCE,
    BINDING_SOURCE,
    GENERIC_CHILD,
    CONTROL,
    RUNNER,
    CHILD,
    FINALIZER,
    TEST,
    RECEIPT_TEST,
)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git


def _ordinary_tracked(root: Path, relative: Path) -> Path:
    path = root / relative
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise RuntimeError(f"V2.49.18 expected ordinary public source: {relative}")
    return path


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.49.18 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.18 expected JSON object")
    return value


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    return parent.protected_watcher_snapshot(proc_root)


def parent_contract(root: Path) -> dict[str, Any]:
    return parent.validate_protocol(root, _read(root / PARENT_PROTOCOL))


def task_vector(
    root: Path, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    tasks = parent.task_vector(root)
    if len(tasks) != SELECTED_COUNT or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.49.18 visible exact-220 vector drifted")
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
            raise RuntimeError("V2.49.18 visible task binding drifted")
    return tasks


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.add(PARENT_PROTOCOL)
    relatives.add(BUILD_AUDIT)
    relatives.update(LOCAL_SOURCES)
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def _single_change() -> dict[str, Any]:
    equalities = {
        "selected_count_equal_v24914": SELECTED_COUNT == parent.SELECTED_COUNT,
        "executor_concurrency_equal_v24914": EXECUTOR_CONCURRENCY == 20,
        "model_slot_cap_equal_v24914": MODEL_SLOT_CAP == 8,
        "limits_equal_v24914": LIMITS == parent.LIMITS,
        "model_equal_v24914": MODEL == parent.MODEL,
        "search_equal_v24914": SEARCH == parent.SEARCH,
        "two_wave_policy_equal_v24914": TWO_WAVE_POLICY == parent.TWO_WAVE_POLICY,
    }
    if not all(equalities.values()):
        raise RuntimeError("V2.49.18 single-change contract drifted")
    return {
        "field": "structural_projection_cap_totality",
        "from": parent.binding.POLICY_ID,
        "to": binding.POLICY_ID,
        "only_exact_diagnosed_overflow_falls_back_to_same_page_prefix": True,
        "unrelated_exception_swallowed": False,
        "additional_search_fetch_model_call_or_wall_cap": False,
        "entropy_or_information_gain_used_for_credit_or_routing": False,
        "equalities": equalities,
    }


def _validate_build_audit(root: Path) -> dict[str, Any]:
    value = _read(root / BUILD_AUDIT)
    if (
        value.get("role") != "v24916_prefix_total_long_page_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("checks", {}).get("diagnosed_overflow_is_totalized") is not True
        or value.get("checks", {}).get("fallback_is_exact_stable_5k_prefix") is not True
        or value.get("checks", {}).get("nonoverflow_query_aware_mechanism_preserved") is not True
        or value.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_historical_result_read"
        )
        is not False
        or value.get("source_policy", {}).get(
            "entropy_or_information_gain_assigns_credit"
        )
        is not False
    ):
        raise RuntimeError("V2.49.18 V2.49.16 build audit drifted")
    return value


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
        raise RuntimeError("V2.49.18 protocol requires clean pushed HEAD")
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
        raise FileExistsError("V2.49.18 future surface exists")
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    _validate_build_audit(root)
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
        "mechanism": {
            "build_audit": str(BUILD_AUDIT),
            "build_audit_sha256": sha256(root / BUILD_AUDIT),
            "binding_policy_id": binding.POLICY_ID,
            "fetch_input_page_character_cap": 12_000,
            "active_output_page_character_cap": 5_000,
            "diagnosed_overflow_totalized": True,
            "content_free_per_task_receipt": True,
            "same_forward_visible_question_and_fetched_pages_only": True,
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
    mechanism = copied.get("mechanism") or {}
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
    _validate_build_audit(root)
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
        or mechanism.get("build_audit_sha256") != sha256(root / BUILD_AUDIT)
        or mechanism.get("binding_policy_id") != binding.POLICY_ID
        or mechanism.get("fetch_input_page_character_cap") != 12_000
        or mechanism.get("active_output_page_character_cap") != 5_000
        or mechanism.get("diagnosed_overflow_totalized") is not True
        or mechanism.get("content_free_per_task_receipt") is not True
        or mechanism.get("entropy_or_information_gain_assigns_credit") is not False
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
        or copied.get("single_change") != _single_change()
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
        raise RuntimeError("V2.49.18 protocol drifted")
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
