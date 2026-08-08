"""Fresh label-blind V2.48.42 atomic-table-header exact-220 contract."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24840_structure_preserving_exact220_contract as parent
from .v24842_atomic_table_header_closure import (
    DEFAULT_BLOCK_CHARACTER_CAP,
    DEFAULT_MAXIMUM_PAGE_CHARS,
    DEFAULT_MAXIMUM_QUERY_TERMS,
    DEFAULT_MAXIMUM_VISIBLE_GROUPS,
    DEFAULT_TOTAL_CHARACTER_CAP,
    POLICY_ID as PROJECTOR_POLICY_ID,
)


DATE = "20260808"
ROLE = "v24844_atomic_table_header_exact220_preregistration"
PROTOCOL_ID = "v24844_fresh_v24842_atomic_table_header_exact220_v1"
PROTOCOL = Path(f"results/v24844_atomic_table_header_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24844_atomic_table_header_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24844_atomic_table_header_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24844_atomic_table_header_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24844_atomic_table_header_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24844_atomic_table_header_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24844_atomic_table_header_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_v24842_atomic_table_header_exact220"
RUNNER_MARKER = "scripts/run_v24844_atomic_table_header_exact220.py"
CHILD_MARKER = "scripts/run_v24844_atomic_table_header_exact220_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
PROJECTOR_POLICY = {
    "policy_id": PROJECTOR_POLICY_ID,
    "total_character_cap": DEFAULT_TOTAL_CHARACTER_CAP,
    "maximum_page_chars": DEFAULT_MAXIMUM_PAGE_CHARS,
    "block_character_cap": DEFAULT_BLOCK_CHARACTER_CAP,
    "maximum_visible_groups": DEFAULT_MAXIMUM_VISIBLE_GROUPS,
    "maximum_query_terms": DEFAULT_MAXIMUM_QUERY_TERMS,
}
PROJECTOR_AUDIT = Path(
    "results/v24842_atomic_table_header_closure_build_audit_v1_20260808.json"
)
SOURCE = Path("src/deepwide_agent/v24844_atomic_table_header_exact220_contract.py")
PROJECTOR_SOURCE = Path("src/deepwide_agent/v24842_atomic_table_header_closure.py")
CONTROL = Path("scripts/control_v24844_atomic_table_header_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24844_atomic_table_header_exact220.py")
TEST = Path("tests/test_v24844_atomic_table_header_exact220.py")
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.48.44 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.44 expected JSON object")
    return value


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    return parent.protected_watcher_snapshot(proc_root)


def parent_contract(root: Path) -> dict[str, Any]:
    value = _read(root / PARENT_PROTOCOL)
    unsigned = dict(value)
    seal = unsigned.pop("protocol_payload_sha256", None)
    if (
        value.get("role") != parent.ROLE
        or value.get("protocol_id") != parent.PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or value.get("git_head") is None
        or not isinstance(value.get("dependency_manifest"), dict)
        or value.get("dependency_manifest_sha256")
        != payload_sha256(value["dependency_manifest"])
        or value.get("task_contract", {}).get("selected_count") != SELECTED_COUNT
        or value.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward"
        )
        is not False
    ):
        raise RuntimeError("V2.48.44 frozen parent protocol drifted")
    return value


def _parent_tasks(root: Path) -> list[dict[str, str]]:
    """Load the frozen public vector without recursively revalidating its manifest."""

    base = parent.parent.parent.parent.parent.parent
    frozen = base.read_object(root / base.FORWARD_CONTRACT)
    return base.selected_tasks(root, frozen)


def task_vector(
    root: Path, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    tasks = _parent_tasks(root)
    if len(tasks) != SELECTED_COUNT or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.48.44 visible exact-220 vector drifted")
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
            raise RuntimeError("V2.48.44 visible task binding drifted")
    return tasks


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update((PARENT_PROTOCOL, PROJECTOR_AUDIT, PROJECTOR_SOURCE))
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
        raise RuntimeError("V2.48.44 protocol requires clean pushed HEAD")
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
        raise FileExistsError("V2.48.44 future surface exists")
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    projector_audit = _read(root / PROJECTOR_AUDIT)
    if (
        projector_audit.get("role")
        != "v24842_atomic_table_header_closure_build_audit"
        or projector_audit.get("audit_valid") is not True
        or projector_audit.get("findings") != []
        or projector_audit.get("checks", {}).get(
            "candidate_rendered_caps_hard"
        )
        is not True
        or projector_audit.get("source_policy", {}).get(
            "entropy_or_information_gain_assigns_credit"
        )
        is not False
    ):
        raise RuntimeError("V2.48.44 projector audit drifted")
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
        "projector": {
            "source": str(PROJECTOR_SOURCE),
            "source_sha256": sha256(root / PROJECTOR_SOURCE),
            "build_audit": str(PROJECTOR_AUDIT),
            "build_audit_sha256": sha256(root / PROJECTOR_AUDIT),
            "policy": copy.deepcopy(PROJECTOR_POLICY),
            "visible_question_and_same_forward_fetched_page_text_only": True,
            "structure_and_record_boundaries_preserved": True,
            "atomic_table_header_closure_enforced": True,
            "stable_first_seen_page_and_block_order": True,
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
            "task_vector_prompt_model_search_fetch_controller_budgets_and_concurrency_equal_v24840": True,
            "v24839_projector_replaced_by_frozen_v24842_atomic_table_header_closure": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "prior_v24840_output_prediction_result_score_or_evaluator_opened_or_hashed": False,
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
    projector = copied.get("projector", {})
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
        or projector.get("source_sha256") != sha256(root / PROJECTOR_SOURCE)
        or projector.get("build_audit_sha256") != sha256(root / PROJECTOR_AUDIT)
        or projector.get("policy") != PROJECTOR_POLICY
        or projector.get("visible_question_and_same_forward_fetched_page_text_only")
        is not True
        or projector.get("structure_and_record_boundaries_preserved") is not True
        or projector.get("atomic_table_header_closure_enforced") is not True
        or projector.get("entropy_or_information_gain_assigns_credit") is not False
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
            "v24839_projector_replaced_by_frozen_v24842_atomic_table_header_closure"
        )
        is not True
        or copied.get("single_change", {}).get(
            "task_vector_prompt_model_search_fetch_controller_budgets_and_concurrency_equal_v24840"
        )
        is not True
        or copied.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward"
        )
        is not False
        or copied.get("source_policy", {}).get(
            "prior_v24840_output_prediction_result_score_or_evaluator_opened_or_hashed"
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
        raise RuntimeError("V2.48.44 protocol drifted")
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
