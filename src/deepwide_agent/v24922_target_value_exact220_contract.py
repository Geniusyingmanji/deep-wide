"""Fresh label-blind exact-220 contract for the V2.49.21 projector.

This rollout keeps the V2.48.57 task vector, prompt, model, search/fetch,
controller, task-level hard budgets, and concurrency.  Its forward treatment
replaces the complete evidence projector: the legacy 60k stable-prefix view
becomes a 30k joint visible row--value-target projector.  Because both the
selection rule and total projection cap change, this full-set rollout measures
the component package and does not identify either sub-effect alone.  Entropy
and information gain remain shadow-only observations with zero signed credit.
"""

from __future__ import annotations

import copy
import functools
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24857_pacing_aware_exact220_contract as parent
from . import v24635_exact220_contract as task_source
from .v24921_target_value_coverage_projector import (
    BLOCK_CHARACTER_CAP,
    MAXIMUM_PAGE_CHARS,
    MAXIMUM_QUERY_TERMS,
    MAXIMUM_VISIBLE_GROUPS,
    POLICY_ID as PROJECTOR_POLICY_ID,
    TOTAL_CHARACTER_CAP,
    validate_receipt,
)


DATE = "20260808"
ROLE = "v24922_target_value_exact220_preregistration"
PROTOCOL_ID = "v24922_fresh_target_value_coverage_exact220_v1"
PROTOCOL = Path(f"results/v24922_target_value_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24922_target_value_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24922_target_value_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24922_target_value_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24922_target_value_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24922_target_value_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
KEY_SLOT_DIRECTORY = OUTPUT_ROOT / "tavily_key_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
PROJECTION_RECEIPT_NAME = "projection_receipt.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24922_target_value_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_target_value_coverage_exact220"
RUNNER_MARKER = "scripts/run_v24922_target_value_exact220.py"
CHILD_MARKER = "scripts/run_v24922_target_value_exact220_task.py"

SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
TAVILY_KEY_SLOT_CAP = parent.TAVILY_KEY_SLOT_CAP
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = copy.deepcopy(parent.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(parent.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS
PARENT_PROTOCOL = parent.PROTOCOL
DIRECT_RECEIPT_NAME = parent.DIRECT_RECEIPT_NAME
RATE_RECEIPT_NAME = parent.RATE_RECEIPT_NAME
PACING_RECEIPT_NAME = parent.PACING_RECEIPT_NAME
PROJECTOR_POLICY = {
    "policy_id": PROJECTOR_POLICY_ID,
    "total_character_cap": TOTAL_CHARACTER_CAP,
    "maximum_page_chars": MAXIMUM_PAGE_CHARS,
    "block_character_cap": BLOCK_CHARACTER_CAP,
    "maximum_visible_groups": MAXIMUM_VISIBLE_GROUPS,
    "maximum_query_terms": MAXIMUM_QUERY_TERMS,
}
PROJECTOR_AUDIT = Path(
    "results/v24921_target_value_coverage_projector_build_audit_v1_20260808.json"
)
SOURCE = Path("src/deepwide_agent/v24922_target_value_exact220_contract.py")
PROJECTOR_SOURCE = Path("src/deepwide_agent/v24921_target_value_coverage_projector.py")
CONTROL = Path("scripts/control_v24922_target_value_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24922_target_value_exact220.py")
TEST = Path("tests/test_v24922_target_value_exact220.py")
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked
protected_watcher_snapshot = parent.protected_watcher_snapshot
rate_policy = parent.rate_policy
pacing_policy = parent.pacing_policy


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.49.22 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.22 expected JSON object")
    return value


@functools.lru_cache(maxsize=1)
def parent_contract(root: Path) -> dict[str, Any]:
    value = _read(root / PARENT_PROTOCOL)
    unsigned = dict(value)
    seal = unsigned.pop("protocol_payload_sha256", None)
    task = value.get("task_contract") or {}
    execution = value.get("execution") or {}
    if (
        value.get("role") != parent.ROLE
        or value.get("protocol_id") != parent.PROTOCOL_ID
        or seal != payload_sha256(unsigned)
        or task.get("runtime_input_keys") != ["opaque_id", "question"]
        or task.get("selected_count") != SELECTED_COUNT
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("tavily_key_slot_cap") != TAVILY_KEY_SLOT_CAP
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("two_wave_policy") != TWO_WAVE_POLICY
        or value.get("dependency_manifest_sha256")
        != payload_sha256(value.get("dependency_manifest"))
    ):
        raise RuntimeError("V2.49.22 frozen parent protocol drifted")
    return value


def task_vector(
    root: Path, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    frozen = task_source.read_object(root / task_source.FORWARD_CONTRACT)
    tasks = task_source.selected_tasks(root, frozen)
    if len(tasks) != SELECTED_COUNT or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.49.22 visible exact-220 vector drifted")
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
            raise RuntimeError("V2.49.22 visible task binding drifted")
    return tasks


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update(
        (
            PARENT_PROTOCOL,
            PROJECTOR_AUDIT,
            PROJECTOR_SOURCE,
        )
    )
    relatives.update(LOCAL_SOURCES)
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def _validate_build_audit(root: Path) -> dict[str, Any]:
    projector = _read(root / PROJECTOR_AUDIT)
    if (
        projector.get("role")
        != "v24921_target_value_coverage_projector_build_audit"
        or projector.get("audit_valid") is not True
        or projector.get("findings") != []
        or projector.get("checks", {}).get("fixed_30k_total_and_5k_page_caps")
        is not True
        or projector.get("checks", {}).get(
            "target_value_pair_mechanism_naturally_engaged"
        )
        is not True
        or projector.get("source_policy", {}).get(
            "entropy_or_information_gain_assigns_signed_credit"
        )
        is not False
    ):
        raise RuntimeError("V2.49.22 build audit drifted")
    return projector


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
        "selected_count_equal_v24857": SELECTED_COUNT == parent.SELECTED_COUNT,
        "executor_concurrency_equal_v24857": (
            EXECUTOR_CONCURRENCY == parent.EXECUTOR_CONCURRENCY == 20
        ),
        "model_slot_cap_equal_v24857": MODEL_SLOT_CAP == parent.MODEL_SLOT_CAP == 8,
        "tavily_key_slot_cap_equal_v24857": (
            TAVILY_KEY_SLOT_CAP == parent.TAVILY_KEY_SLOT_CAP == 12
        ),
        "limits_equal_v24857": LIMITS == parent.LIMITS,
        "model_equal_v24857": MODEL == parent.MODEL,
        "search_equal_v24857": SEARCH == parent.SEARCH,
        "two_wave_policy_equal_v24857": TWO_WAVE_POLICY == parent.TWO_WAVE_POLICY,
    }
    if not all(equalities.values()):
        raise RuntimeError("V2.49.22 parent equality drifted")
    return {
        "field": "evidence_projector_component",
        "from": "v24857_legacy_prefix_evidence_projection",
        "to": PROJECTOR_POLICY_ID,
        "joint_visible_row_value_target_coverage_precedes_independent_phrase_coverage": True,
        "total_projection_character_cap_from_to": [60_000, 30_000],
        "per_page_character_cap_unchanged": True,
        "selection_rule_and_total_cap_sub_effects_not_separately_identified": True,
        "additional_search_fetch_model_token_context_or_wall_cap": False,
        "entropy_or_information_gain_assigns_credit_or_routes": False,
        "equalities": equalities,
    }


def projection_receipt_summary(root: Path) -> dict[str, Any]:
    total_fields = {
        "projected_rendered_characters": "rendered_characters",
        "visible_row_target_count": "visible_row_targets",
        "visible_value_target_count": "visible_value_targets",
        "supported_target_value_pair_count": "supported_target_value_pairs",
        "retained_target_value_pair_count": "retained_target_value_pairs",
        "missed_target_value_pair_count": "missed_target_value_pairs",
        "selected_table_continuation_block_count": "selected_table_continuations",
        "table_header_dependency_addition_count": "table_header_dependency_additions",
        "orphan_selected_table_continuation_block_count": "orphan_table_continuations",
        "retained_supported_visible_requirement_group_count": "retained_supported_visible_requirements",
    }
    totals = {target: 0 for target in total_fields.values()}
    seals: list[str] = []
    valid = 0
    missing = 0
    supported_tasks = 0
    retained_tasks = 0
    for position in range(1, SELECTED_COUNT + 1):
        path = root / TASK_ROOT / f"task_{position:04d}" / PROJECTION_RECEIPT_NAME
        if path.is_symlink():
            raise RuntimeError("V2.49.22 projection receipt is a symlink")
        if not path.exists():
            missing += 1
            continue
        if not path.is_file():
            raise RuntimeError("V2.49.22 projection receipt is nonordinary")
        try:
            receipt = validate_receipt(_read(path))
        except (OSError, RuntimeError, TypeError, ValueError) as error:
            raise RuntimeError(
                f"V2.49.22 invalid projection receipt at task {position:04d}"
            ) from error
        valid += 1
        supported_tasks += int(receipt["supported_target_value_pair_count"] > 0)
        retained_tasks += int(receipt["retained_target_value_pair_count"] > 0)
        seals.append(str(receipt["receipt_payload_sha256"]))
        for source, target in total_fields.items():
            totals[target] += int(receipt[source])
    if valid + missing != SELECTED_COUNT:
        raise RuntimeError("V2.49.22 projection receipt denominator drifted")
    value = {
        "expected_receipts": SELECTED_COUNT,
        "valid_receipts": valid,
        "missing_receipts": missing,
        **totals,
        "tasks_with_supported_target_value_pairs": supported_tasks,
        "tasks_with_retained_target_value_pairs": retained_tasks,
        "receipt_payload_seal_vector_sha256": payload_sha256(seals),
        "contains_question_query_url_host_page_projection_content_or_hash": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    if value["orphan_table_continuations"] != 0:
        raise RuntimeError("V2.49.22 orphan table continuation entered receipts")
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
        raise RuntimeError("V2.49.22 protocol requires clean pushed HEAD")
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
        raise FileExistsError("V2.49.22 future surface exists")
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
        "neutral_transport_gate": copy.deepcopy(base["neutral_transport_gate"]),
        "fixed_full_budget_control_gate": copy.deepcopy(
            base["fixed_full_budget_control_gate"]
        ),
        "projector": {
            "source": str(PROJECTOR_SOURCE),
            "source_sha256": sha256(root / PROJECTOR_SOURCE),
            "build_audit": str(PROJECTOR_AUDIT),
            "build_audit_sha256": sha256(root / PROJECTOR_AUDIT),
            "policy": copy.deepcopy(PROJECTOR_POLICY),
            "visible_question_and_same_forward_fetched_page_text_only": True,
            "joint_target_value_coverage_before_independent_phrase_coverage": True,
            "atomic_table_header_closure_enforced": True,
            "stable_first_seen_page_and_block_order": True,
            "content_free_projection_receipt_enabled": True,
            "entropy_information_gain_shadow_only": True,
            "entropy_or_information_gain_assigns_credit": False,
        },
        "task_contract": _task_contract(tasks),
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "tavily_key_slot_cap": TAVILY_KEY_SLOT_CAP,
            "task_wall_seconds": LIMITS["wall_seconds"],
            "model_calls_per_task": LIMITS["model_calls"],
            "search_queries_per_task": LIMITS["search_queries"],
            "fetch_targets_per_task": LIMITS["fetch_targets"],
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "two_wave_policy": copy.deepcopy(TWO_WAVE_POLICY),
            "rate_policy": rate_policy(),
            "pacing_admission_policy": pacing_policy(),
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "key_slot_directory": str(KEY_SLOT_DIRECTORY),
            "single_fresh_forward_no_retry_resume_or_selective_rerun": True,
        },
        "single_change": _single_change(),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "prior_benchmark_prediction_result_score_or_evaluator_opened_or_hashed": False,
            "credential_values_stdin_memory_only_not_persisted_hashed_or_emitted": True,
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
    projector = copied.get("projector") or {}
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
        or copied.get("neutral_transport_gate") != base["neutral_transport_gate"]
        or copied.get("fixed_full_budget_control_gate")
        != base["fixed_full_budget_control_gate"]
        or projector.get("source_sha256") != sha256(root / PROJECTOR_SOURCE)
        or projector.get("build_audit_sha256") != sha256(root / PROJECTOR_AUDIT)
        or projector.get("policy") != PROJECTOR_POLICY
        or projector.get("joint_target_value_coverage_before_independent_phrase_coverage")
        is not True
        or projector.get("entropy_or_information_gain_assigns_credit") is not False
        or copied.get("task_contract") != _task_contract(tasks)
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or execution.get("executor_concurrency") != 20
        or execution.get("model_slot_cap") != 8
        or execution.get("tavily_key_slot_cap") != 12
        or execution.get("task_wall_seconds") != LIMITS["wall_seconds"]
        or execution.get("model_calls_per_task") != LIMITS["model_calls"]
        or execution.get("search_queries_per_task") != LIMITS["search_queries"]
        or execution.get("fetch_targets_per_task") != LIMITS["fetch_targets"]
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("two_wave_policy") != TWO_WAVE_POLICY
        or execution.get("rate_policy") != rate_policy()
        or execution.get("pacing_admission_policy") != pacing_policy()
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("key_slot_directory") != str(KEY_SLOT_DIRECTORY)
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
        raise RuntimeError("V2.49.22 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "parent_contract",
    "payload_sha256",
    "projection_receipt_summary",
    "protected_watcher_snapshot",
    "sha256",
    "task_vector",
    "validate_protocol",
]
