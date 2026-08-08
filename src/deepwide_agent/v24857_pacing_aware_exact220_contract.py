"""Fresh exact-220 rollout of the V2.48.56 pacing-aware admission.

The visible 220-vector, prompts, model, hard task budget, provider-wide Tavily
transport, and concurrency are inherited from V2.48.54.  The only algorithmic
change is that same-pass provider-gate wait may extend the first-wave
*admission* ceiling via V2.48.56; raw elapsed time and every absolute cap stay
unchanged.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24854_rate_aware_exact220_contract as parent
from . import v24856_pacing_aware_admission as admission


DATE = "20260808"
ROLE = "v24857_pacing_aware_exact220_preregistration"
PROTOCOL_ID = "v24857_same_pass_pacing_aware_fixed_full_budget_exact220_v1"
PROTOCOL = Path(f"results/v24857_pacing_aware_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24857_pacing_aware_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24857_pacing_aware_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24857_pacing_aware_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24857_pacing_aware_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24857_pacing_aware_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
KEY_SLOT_DIRECTORY = OUTPUT_ROOT / "tavily_key_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24857_pacing_aware_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_same_pass_pacing_aware_exact220"
RUNNER_MARKER = "scripts/run_v24857_pacing_aware_exact220.py"
CHILD_MARKER = "scripts/run_v24857_pacing_aware_exact220_task.py"
DIRECT_RECEIPT_NAME = parent.DIRECT_RECEIPT_NAME
RATE_RECEIPT_NAME = parent.RATE_RECEIPT_NAME
PACING_RECEIPT_NAME = "pacing_aware_admission_receipt.json"

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
TRANSPORT_SOURCE = parent.TRANSPORT_SOURCE
TRANSPORT_TEST = parent.TRANSPORT_TEST
ADMISSION_SOURCE = Path("src/deepwide_agent/v24856_pacing_aware_admission.py")
ADMISSION_TEST = Path("tests/test_v24856_pacing_aware_admission.py")
SOURCE = Path("src/deepwide_agent/v24857_pacing_aware_exact220_contract.py")
CONTROL = Path("scripts/control_v24857_pacing_aware_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24857_pacing_aware_exact220.py")
TEST = Path("tests/test_v24857_pacing_aware_exact220.py")
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked
protected_watcher_snapshot = parent.protected_watcher_snapshot
validate_transport_gate = parent.validate_transport_gate
rate_policy = parent.rate_policy


def parent_contract(root: Path) -> dict[str, Any]:
    return parent.validate_protocol(root, parent._read(root / PARENT_PROTOCOL))


def task_vector(
    root: Path, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    tasks = parent.task_vector(root, parent_contract(root))
    if len(tasks) != SELECTED_COUNT or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.48.57 visible exact-220 vector drifted")
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
            raise RuntimeError("V2.48.57 visible task binding drifted")
    return tasks


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update((PARENT_PROTOCOL, ADMISSION_SOURCE, ADMISSION_TEST))
    relatives.update(LOCAL_SOURCES)
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def pacing_policy() -> dict[str, Any]:
    return {
        "policy_id": admission.POLICY_ID,
        "provider_wait_metric": "same_task_max_provider_gate_wait_delta",
        "maximum_provider_wait_credit_seconds": (
            admission.MAX_PROVIDER_WAIT_CREDIT_SECONDS
        ),
        "raw_first_wave_elapsed_rewritten": False,
        "absolute_task_deadline_changed": False,
        "cleanup_reserve_changed": False,
        "query_fetch_model_token_or_context_cap_changed": False,
        "search_pacing_cooldown_or_attempt_cap_changed": False,
    }


def _parent_equalities() -> dict[str, bool]:
    values = {
        "selected_count_equal_v24854": SELECTED_COUNT == parent.SELECTED_COUNT,
        "executor_concurrency_equal_v24854": (
            EXECUTOR_CONCURRENCY == parent.EXECUTOR_CONCURRENCY
        ),
        "model_slot_cap_equal_v24854": MODEL_SLOT_CAP == parent.MODEL_SLOT_CAP,
        "tavily_key_slot_cap_equal_v24854": (
            TAVILY_KEY_SLOT_CAP == parent.TAVILY_KEY_SLOT_CAP
        ),
        "limits_equal_v24854": LIMITS == parent.LIMITS,
        "model_equal_v24854": MODEL == parent.MODEL,
        "search_equal_v24854": SEARCH == parent.SEARCH,
        "two_wave_policy_equal_v24854": TWO_WAVE_POLICY == parent.TWO_WAVE_POLICY,
        "rate_policy_equal_v24854": rate_policy() == parent.rate_policy(),
    }
    if not all(values.values()):
        raise RuntimeError("V2.48.57 parent equality drifted")
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
        or _git(root, "rev-parse", "HEAD")
        != _git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.48.57 protocol requires clean pushed HEAD")
    future = (
        PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT,
        OUTPUT_ROOT,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink() for path in future
    ):
        raise FileExistsError("V2.48.57 future surface exists")
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
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
        "neutral_transport_gate": copy.deepcopy(base["neutral_transport_gate"]),
        "fixed_full_budget_control_gate": copy.deepcopy(
            base["fixed_full_budget_control_gate"]
        ),
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
        "single_change": {
            "old_admission": "raw_wave1_elapsed_ceiling",
            "new_admission": "same_pass_max_provider_wait_pacing_aware_ceiling",
            "pacing_policy": pacing_policy(),
            "parent_equalities": _parent_equalities(),
            "fresh_execution_and_artifact_surfaces": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward": False,
            "prior_output_prediction_result_score_or_evaluator_opened_or_hashed": False,
            "credential_values_stdin_memory_only_not_persisted_hashed_or_emitted": True,
            "same_pass_content_free_transport_telemetry_only": True,
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
    return validate_protocol(root, value)


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    execution = copied.get("execution") or {}
    expected_task = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256(
            [task["opaque_id"] for task in tasks]
        ),
        "visible_question_vector_sha256": payload_sha256(
            [task["question"] for task in tasks]
        ),
    }
    expected_change = {
        "old_admission": "raw_wave1_elapsed_ceiling",
        "new_admission": "same_pass_max_provider_wait_pacing_aware_ceiling",
        "pacing_policy": pacing_policy(),
        "parent_equalities": _parent_equalities(),
        "fresh_execution_and_artifact_surfaces": True,
    }
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
        or copied.get("neutral_transport_gate") != base["neutral_transport_gate"]
        or copied.get("fixed_full_budget_control_gate")
        != base["fixed_full_budget_control_gate"]
        or copied.get("task_contract") != expected_task
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("tavily_key_slot_cap") != TAVILY_KEY_SLOT_CAP
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
        or copied.get("single_change") != expected_change
        or copied.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward"
        ) is not False
        or copied.get("authorization") != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
    ):
        raise RuntimeError("V2.48.57 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol", "dependency_manifest", "pacing_policy",
    "parent_contract", "payload_sha256", "protected_watcher_snapshot",
    "rate_policy", "sha256", "task_vector", "validate_protocol",
    "validate_transport_gate",
]
