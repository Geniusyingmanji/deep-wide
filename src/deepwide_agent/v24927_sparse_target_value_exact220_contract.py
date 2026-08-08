"""Label-blind exact-220 contract for sparse target--value projection.

The parent is the frozen keyless GPT-5.6 fixed-full-budget rollout.  This
successor changes only the evidence projector: table rows not bound to a row
entity visible in the question are compacted before the 30k target--value
projection.  Search, fetch, model, token, context, wall and concurrency caps
are unchanged.  Entropy/information gain remains shadow-only.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24909_keyless_fixed_budget_exact220_contract as parent
from . import v24924_visible_row_table_compactor as projector


DATE = "20260808"
ROLE = "v24927_sparse_target_value_exact220_preregistration"
PROTOCOL_ID = "v24927_keyless_sparse_target_value_exact220_v1"
PROTOCOL = Path(f"results/v24927_sparse_target_value_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24927_sparse_target_value_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24927_sparse_target_value_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24927_sparse_target_value_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24927_sparse_target_value_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24927_sparse_target_value_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
PROJECTION_RECEIPT_NAME = "sparse_projection_receipt.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24927_sparse_target_value_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_keyless_sparse_target_value_exact220"
RUNNER_MARKER = "scripts/run_v24927_sparse_target_value_exact220.py"
CHILD_MARKER = "scripts/run_v24927_sparse_target_value_exact220_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
PROJECTOR_SOURCE = Path("src/deepwide_agent/v24924_visible_row_table_compactor.py")
PROJECTOR_AUDIT = Path("results/v24924_visible_row_table_compactor_build_audit_v1_20260808.json")
TARGET_VALUE_SOURCE = Path("src/deepwide_agent/v24921_target_value_coverage_projector.py")
SOURCE = Path("src/deepwide_agent/v24927_sparse_target_value_exact220_contract.py")
BINDING = parent.BINDING
CONTROL = Path("scripts/control_v24927_sparse_target_value_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24927_sparse_target_value_exact220.py")
TEST = Path("tests/test_v24927_sparse_target_value_exact220.py")
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.49.27 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.27 expected JSON object")
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
        raise RuntimeError("V2.49.27 visible exact-220 vector drifted")
    if protocol is not None:
        expected = {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
        }
        if protocol.get("task_contract") != expected:
            raise RuntimeError("V2.49.27 visible task binding drifted")
    return tasks


def _validate_projector_audit(root: Path) -> dict[str, Any]:
    value = _read(root / PROJECTOR_AUDIT)
    checks = value.get("checks") or {}
    source_policy = value.get("source_policy") or {}
    if (
        value.get("role") != "v24924_visible_row_table_compactor_build_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or checks.get("candidate_reachability_full_576") is not True
        or checks.get("strict_exact_visible_cell_binding") is not True
        or checks.get("additional_effect_or_cap_zero") is not True
        or checks.get("entropy_assigns_no_credit") is not True
        or source_policy.get("visible_question_and_same_forward_pages_only") is not True
        or source_policy.get("entropy_or_information_gain_assigns_credit") is not False
    ):
        raise RuntimeError("V2.49.27 projector audit drifted")
    return value


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update(
        (PARENT_PROTOCOL, PROJECTOR_SOURCE, PROJECTOR_AUDIT, TARGET_VALUE_SOURCE)
    )
    relatives.update(LOCAL_SOURCES)
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def _task_contract(tasks: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256(
            [task["opaque_id"] for task in tasks]
        ),
        "visible_question_vector_sha256": payload_sha256(
            [task["question"] for task in tasks]
        ),
    }


def _single_change() -> dict[str, Any]:
    equalities = {
        "selected_count_equal_parent": SELECTED_COUNT == parent.SELECTED_COUNT == 220,
        "executor_concurrency_equal_parent": EXECUTOR_CONCURRENCY == parent.EXECUTOR_CONCURRENCY == 20,
        "model_slot_cap_equal_parent": MODEL_SLOT_CAP == parent.MODEL_SLOT_CAP == 8,
        "limits_equal_parent": LIMITS == parent.LIMITS,
        "model_equal_parent": MODEL == parent.MODEL,
        "search_equal_parent": SEARCH == parent.SEARCH,
        "two_wave_policy_equal_parent": TWO_WAVE_POLICY == parent.TWO_WAVE_POLICY,
    }
    if not all(equalities.values()):
        raise RuntimeError("V2.49.27 parent equality drifted")
    return {
        "field": "evidence_projector",
        "from": "legacy_keyless_evidence_projection",
        "to": projector.POLICY_ID,
        "visible_row_sparse_compaction_before_target_value_projection": True,
        "same_forward_page_bytes_only": True,
        "additional_search_fetch_model_token_context_or_wall_cap": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "equalities": equalities,
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
        raise RuntimeError("V2.49.27 protocol requires clean pushed HEAD")
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
        raise FileExistsError("V2.49.27 future surface exists")
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    _validate_projector_audit(root)
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
        "projector": {
            "policy_id": projector.POLICY_ID,
            "source": str(PROJECTOR_SOURCE),
            "source_sha256": sha256(root / PROJECTOR_SOURCE),
            "build_audit": str(PROJECTOR_AUDIT),
            "build_audit_sha256": sha256(root / PROJECTOR_AUDIT),
            "total_character_cap": 30_000,
            "per_page_character_cap": 5_000,
            "visible_question_and_same_forward_pages_only": True,
            "content_free_per_task_receipt": True,
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_credit": False,
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
    projection = copied.get("projector") or {}
    _validate_projector_audit(root)
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
        or copied.get("task_contract") != _task_contract(tasks)
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or projection.get("policy_id") != projector.POLICY_ID
        or projection.get("source_sha256") != sha256(root / PROJECTOR_SOURCE)
        or projection.get("build_audit_sha256") != sha256(root / PROJECTOR_AUDIT)
        or projection.get("total_character_cap") != 30_000
        or projection.get("per_page_character_cap") != 5_000
        or projection.get("entropy_or_information_gain_assigns_credit") is not False
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
        raise RuntimeError("V2.49.27 protocol drifted")
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
