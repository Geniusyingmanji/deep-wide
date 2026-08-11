"""Label-blind exact-220 contract for the page-self representation successor.

The visible 220-task vector, V2.50.29 runtime, GPT-5.6 transport, concurrency,
and every per-task resource cap are byte/effect compatible with V2.50.30.
The sole forward treatment is the V2.50.55 isolated fetch helper, which applies
V2.50.49 to the same decoded page and otherwise returns the inherited raw 5k
prefix byte-for-byte.
"""

from __future__ import annotations

import ast
import copy
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v25029_evidence_conditioned_runtime as runtime
from . import v25030_evidence_conditioned_exact220_contract as parent


DATE = "20260811"
PROTOCOL_ID = "v25056_page_self_evidence_conditioned_keyless_exact220_v1"
BUILD_AUDIT = Path(f"results/v25056_page_self_exact220_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25056_page_self_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25056_page_self_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25056_page_self_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25056_page_self_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25056_page_self_exact220_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v25056_page_self_exact220_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25056_page_self_exact220_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25056_page_self_exact220_postresult_audit_v1_{DATE}.json")

OUTPUT_ROOT = Path(f"outputs/v25056_page_self_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
RUNTIME_RESULTS = OUTPUT_ROOT / "runtime_results.jsonl"
TASK_RECEIPTS = OUTPUT_ROOT / "content_free_task_receipts.jsonl"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v25056_page_self_exact220_forward_v1"
LEASE_PURPOSE = "single_label_blind_page_self_representation_exact220"

PARENT_TASK_PROTOCOL = parent.PARENT_TASK_PROTOCOL
VISIBLE_MANIFEST = parent.VISIBLE_MANIFEST
ID_SOURCES = parent.ID_SOURCES
ID_COUNTS = parent.ID_COUNTS
OPAQUE = parent.OPAQUE
SELECTED_COUNT = parent.SELECTED_COUNT
EXECUTOR_CONCURRENCY = parent.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = parent.MODEL_SLOT_CAP
CLEANUP_RESERVE_SECONDS = parent.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = parent.MINIMUM_MODEL_ATTEMPT_SECONDS
LIMITS = copy.deepcopy(parent.LIMITS)
MODEL = copy.deepcopy(parent.MODEL)
SEARCH = {
    **copy.deepcopy(parent.SEARCH),
    "provider": "azure-native-keyless-bounded-page-self-production-fetch",
}
PROTECTED_WATCHERS = parent.PROTECTED_WATCHERS

SOURCE = Path("src/deepwide_agent/v25056_page_self_exact220_contract.py")
RUNTIME = parent.RUNTIME
REFINEMENT = parent.REFINEMENT
PARENT_SHARED_WAVE = parent.PARENT_SHARED_WAVE
PARENT_COMPACT = parent.PARENT_COMPACT
PARENT_ROBUST = parent.PARENT_ROBUST
PARENT_COUNTERS = parent.PARENT_COUNTERS
FETCH = Path("src/deepwide_agent/v25055_page_self_production_fetch.py")
FETCH_HELPER = Path("scripts/run_v25055_page_self_production_fetch_helper.py")
REPRESENTATION = Path("src/deepwide_agent/v25049_page_self_identified_record.py")
LEASE = parent.LEASE
CONTROL = Path("scripts/control_v25056_page_self_exact220.py")
RUNNER = Path("scripts/run_v25056_page_self_exact220.py")
FINALIZER = Path("scripts/finalize_v25056_page_self_exact220.py")
TEST = Path("tests/test_v25056_page_self_exact220.py")
PARENT_TESTS = (
    Path("tests/test_v25055_page_self_production_fetch.py"),
    Path("tests/test_v25049_page_self_identified_record.py"),
    *parent.PARENT_TESTS,
)
RUNNER_MARKER = str(RUNNER)
CHILD_MARKER = "v25056_no_child_process"
BUILD_ROLE = "v25056_page_self_exact220_build_audit"
PROTOCOL_ROLE = "v25056_page_self_exact220_preregistration"
PREAUDIT_ROLE = "v25056_page_self_exact220_preactivation_audit"
START_ROLE = "v25056_page_self_exact220_execution_start"
PROGRESS_ROLE = "v25056_page_self_exact220_safe_progress"
SLOT_ROLE = "v25056_model_slot"
SUMMARY_ROLE = "v25056_page_self_exact220_run_summary"
FREEZE_ROLE = "v25056_page_self_exact220_prediction_freeze"
FORWARD_ROLE = "v25056_page_self_exact220_forward_result"
FORWARD_AUDIT_NATIVE_ROLE = "v25056_page_self_exact220_forward_audit"
EVALUATOR_OWNER = "v25056_page_self_exact220_evaluator_v1"
EVALUATOR_PURPOSE = "postfreeze_fixed_partition_parallel_v25056_exact220_evaluator"
EVALUATOR_FREEZE_BINDING_FIELD = (
    "native_v25056_prediction_freeze_bound_by_role_projection"
)
FORWARD_SOURCES = (
    SOURCE,
    RUNTIME,
    REFINEMENT,
    PARENT_SHARED_WAVE,
    PARENT_COMPACT,
    PARENT_ROBUST,
    PARENT_COUNTERS,
    FETCH,
    FETCH_HELPER,
    REPRESENTATION,
    LEASE,
    RUNNER,
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


payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
git = parent.git
sealed = parent.sealed
protected_watcher_snapshot = parent.protected_watcher_snapshot
_ordinary = parent._ordinary
_parent_task_contract = parent._parent_task_contract
_input_bindings = parent._input_bindings


def seal(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    """Seal native artifacts and map only audited frozen-runner role literals."""

    copied = copy.deepcopy(dict(value))
    role = copied.get("role")
    if role in _LEGACY_RUNNER_ROLES:
        copied["role"] = _LEGACY_RUNNER_ROLES[str(role)]
    copied.pop(field, None)
    copied[field] = payload_sha256(copied)
    return copied


def task_vector(root: Path, protocol: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    tasks = parent.task_vector(root)
    if protocol is not None and protocol.get("task_contract") != {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
        "visible_question_vector_sha256": payload_sha256([row["question"] for row in tasks]),
    }:
        raise RuntimeError("V2.50.56 protocol task binding drifted")
    return tasks


def forward_dependency_closure(root: Path) -> tuple[Path, ...]:
    pending = list(FORWARD_SOURCES)
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = _ordinary(relative, root)
        observed.add(relative)
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            candidates: list[Path] = []
            if isinstance(node, ast.Import):
                for item in node.names:
                    if item.name.startswith("deepwide_agent."):
                        candidates.append(Path("src") / Path(*item.name.split(".")).with_suffix(".py"))
                    elif item.name.startswith("scripts."):
                        candidates.append(Path(*item.name.split(".")).with_suffix(".py"))
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level and relative.parts[:2] == ("src", "deepwide_agent"):
                    if module:
                        candidates.append(Path("src/deepwide_agent") / Path(*module.split(".")).with_suffix(".py"))
                    else:
                        candidates.extend(Path("src/deepwide_agent") / f"{item.name}.py" for item in node.names)
                elif module == "deepwide_agent":
                    candidates.extend(Path("src/deepwide_agent") / f"{item.name}.py" for item in node.names)
                elif module.startswith("deepwide_agent."):
                    candidates.append(Path("src") / Path(*module.split(".")).with_suffix(".py"))
                elif module == "scripts":
                    candidates.extend(Path("scripts") / f"{item.name}.py" for item in node.names)
                elif module.startswith("scripts."):
                    candidates.append(Path(*module.split(".")).with_suffix(".py"))
            for candidate in candidates:
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool = True) -> dict[str, str]:
    relatives = {
        *forward_dependency_closure(root), CONTROL, FINALIZER, TEST,
        *PARENT_TESTS, PARENT_TASK_PROTOCOL,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = _ordinary(relative, root)
        if tracked and subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)], cwd=root,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, timeout=20, check=False,
        ).returncode != 0:
            raise RuntimeError(f"V2.50.56 source is not tracked: {relative}")
        output[str(relative)] = sha256(path)
    return output


def _build_audit_binding(root: Path) -> dict[str, str] | None:
    path = root / BUILD_AUDIT
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.50.56 build audit is nonordinary")
    return {"path": str(BUILD_AUDIT), "sha256": sha256(path)}


def build_protocol(
    root: Path, *, now: int, tracked: bool = True,
    require_clean: bool = True, require_pristine: bool = True,
) -> dict[str, Any]:
    if require_clean and (
        git(root, "status", "--porcelain")
        or git(root, "rev-parse", "HEAD") != git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.50.56 protocol requires clean pushed HEAD")
    future = (
        PROTOCOL, PREAUDIT, EXECUTION_START, FORWARD_RESULT, FORWARD_AUDIT,
        EVALUATOR_PROTOCOL, RESULT, POSTAUDIT, OUTPUT_ROOT,
    )
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise FileExistsError("V2.50.56 future surface exists")
    tasks = task_vector(root)
    manifest = dependency_manifest(root, tracked=tracked)
    task_contract = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
        "visible_question_vector_sha256": payload_sha256([row["question"] for row in tasks]),
    }
    value = {
        "artifact_version": 1,
        "role": PROTOCOL_ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": git(root, "rev-parse", "HEAD"),
        "task_contract": task_contract,
        "build_audit": _build_audit_binding(root),
        "input_bindings": _input_bindings(root),
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "limits": copy.deepcopy(LIMITS),
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "runtime_policy_id": runtime.POLICY_ID,
            "runtime_phases": list(runtime.PHASES),
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "single_forward_no_retry_resume_skip_or_selective_rerun": True,
        },
        "treatment_scope": {
            "v25030_visible_task_runtime_model_query_fetch_and_budget_preserved": True,
            "sole_forward_treatment_is_v25055_page_self_fetch_projection": True,
            "strict_binding_failure_is_exact_raw_5k_prefix_handoff": True,
            "v25054_production_late_page_opportunity_supports_design_not_score": True,
            "cross_rollout_difference_is_not_a_paired_causal_effect": True,
        },
        "mechanism_gate": {
            "fixed_denominator": SELECTED_COUNT,
            "minimum_natural_page_self_exposed_pages": 1,
            "all_tasks_within_frozen_resource_caps": True,
            "postfreeze_evaluator_unconditional_on_mechanism_gate": True,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
            "mapping_gold_category_question_type_split_answer_evaluator_score_reward_read_by_forward": False,
            "prior_prediction_result_score_reward_or_evaluator_read_by_forward": False,
            "prediction_freeze_before_mapping_query_answer_or_official_evaluator_open": True,
            "entropy_or_information_gain_assigns_signed_credit_or_routes": False,
            "credential_value_read_persisted_hashed_or_emitted": False,
            "fixed_public_exact220_task_set_reexecuted": True,
            "new_or_disjoint_task_population_claimed": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_exact220_forward": False,
            "postfreeze_official_evaluator": False,
            "retry_resume_skip_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        },
    }
    value["protocol_payload_sha256"] = payload_sha256(value)
    return validate_protocol(root, value, tracked=tracked)


def validate_protocol(root: Path, value: Mapping[str, Any], *, tracked: bool = True) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    observed = unsigned.pop("protocol_payload_sha256", None)
    tasks = task_vector(root)
    manifest = dependency_manifest(root, tracked=tracked)
    execution = copied.get("execution") or {}
    expected_task = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256([row["opaque_id"] for row in tasks]),
        "visible_question_vector_sha256": payload_sha256([row["question"] for row in tasks]),
    }
    if (
        copied.get("role") != PROTOCOL_ROLE
        or copied.get("protocol_id") != PROTOCOL_ID
        or observed != payload_sha256(unsigned)
        or copied.get("task_contract") != expected_task
        or copied.get("build_audit") != _build_audit_binding(root)
        or copied.get("input_bindings") != _input_bindings(root)
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or execution.get("executor_concurrency") != 20
        or execution.get("model_slot_cap") != 8
        or execution.get("limits") != LIMITS
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("runtime_policy_id") != runtime.POLICY_ID
        or execution.get("runtime_phases") != list(runtime.PHASES)
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or copied.get("treatment_scope", {}).get("sole_forward_treatment_is_v25055_page_self_fetch_projection") is not True
        or copied.get("mechanism_gate", {}).get("minimum_natural_page_self_exposed_pages") != 1
        or copied.get("mechanism_gate", {}).get("postfreeze_evaluator_unconditional_on_mechanism_gate") is not True
        or copied.get("source_policy", {}).get("mapping_gold_category_question_type_split_answer_evaluator_score_reward_read_by_forward") is not False
        or copied.get("source_policy", {}).get("entropy_or_information_gain_assigns_signed_credit_or_routes") is not False
        or copied.get("authorization") != {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "single_exact220_forward": False,
            "postfreeze_official_evaluator": False,
            "retry_resume_skip_or_selective_rerun": False,
            "leaderboard_or_sota": False,
        }
    ):
        raise RuntimeError("V2.50.56 protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol", "dependency_manifest", "forward_dependency_closure",
    "git", "payload_sha256", "protected_watcher_snapshot", "seal", "sealed",
    "sha256", "task_vector", "validate_protocol",
]
