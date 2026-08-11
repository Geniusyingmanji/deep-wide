"""Label-blind exact-220 successor for the validated causal-salience runtime.

The public DeepWideBench task vector is byte-identical to V2.48.57.  Runtime
input remains exactly ``opaque_id`` and ``question``.  The only algorithmic
successor is the V2.51.27 paired runtime that (1) prioritizes existing
second-wave evidence without changing prompt length and (2) deterministically
hands control's prediction to candidate when no real retrieval mechanism was
engaged.  The candidate arm is frozen for the post-forward official evaluator.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import re
import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v25030_evidence_conditioned_exact220_contract as base
from . import v25127_causally_coupled_target_record_runtime as runtime


DATE = "20260811"
PROTOCOL_ID = "v25130_causal_salience_keyless_exact220_v1"
BUILD_AUDIT = Path(f"results/v25130_causal_salience_exact220_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25130_causal_salience_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25130_causal_salience_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25130_causal_salience_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25130_causal_salience_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25130_causal_salience_exact220_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(f"results/v25130_causal_salience_exact220_evaluator_preregistration_v1_{DATE}.json")
RESULT = Path(f"results/v25130_causal_salience_exact220_result_v1_{DATE}.json")
POSTAUDIT = Path(f"results/v25130_causal_salience_exact220_postresult_audit_v1_{DATE}.json")

OUTPUT_ROOT = Path(f"outputs/v25130_causal_salience_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
RUNTIME_RESULTS = OUTPUT_ROOT / "runtime_results.jsonl"
TASK_RECEIPTS = OUTPUT_ROOT / "content_free_task_receipts.jsonl"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"

LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25130_causal_salience_exact220_forward_v1"
LEASE_PURPOSE = "single_label_blind_causal_salience_exact220"
PARENT_TASK_PROTOCOL = base.PARENT_TASK_PROTOCOL
VISIBLE_MANIFEST = base.VISIBLE_MANIFEST
ID_SOURCES = base.ID_SOURCES
ID_COUNTS = base.ID_COUNTS
OPAQUE = base.OPAQUE
SELECTED_COUNT = base.SELECTED_COUNT
EXECUTOR_CONCURRENCY = 40
MODEL_SLOT_CAP = 16
CLEANUP_RESERVE_SECONDS = base.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = base.MINIMUM_MODEL_ATTEMPT_SECONDS
LIMITS = copy.deepcopy(base.LIMITS)
MODEL = copy.deepcopy(base.MODEL)
SEARCH = copy.deepcopy(base.SEARCH)
PROTECTED_WATCHERS = base.PROTECTED_WATCHERS
ARMS = runtime.ARMS
CONTROL_ARM, CANDIDATE_ARM = ARMS
COLUMNS = ("Package", "Version", "Released", "Requires")

SOURCE = Path("src/deepwide_agent/v25130_causal_salience_exact220_contract.py")
RUNTIME = Path("src/deepwide_agent/v25127_causally_coupled_target_record_runtime.py")
PARENT_RUNTIME = Path("src/deepwide_agent/v25123_visible_legacy_query_compatible_runtime.py")
GROUNDING = Path("src/deepwide_agent/v25119_grounded_target_record_paired_runtime.py")
PLANNER = Path("src/deepwide_agent/v25117_grounded_target_record_plan.py")
SELECTOR = Path("src/deepwide_agent/v25118_target_record_frontier_selection.py")
FETCH = base.FETCH
FETCH_HELPER = base.FETCH_HELPER
LEASE = base.LEASE
CONTROL = Path("scripts/control_v25130_causal_salience_exact220.py")
RUNNER = Path("scripts/run_v25130_causal_salience_exact220.py")
FINALIZER = Path("scripts/finalize_v25130_causal_salience_exact220.py")
TEST = Path("tests/test_v25130_causal_salience_exact220.py")
PARENT_TESTS = (
    Path("tests/test_v25127_causally_coupled_target_record_runtime.py"),
    Path("tests/test_v25123_visible_legacy_query_compatible_runtime.py"),
    Path("tests/test_v25119_grounded_target_record_paired_runtime.py"),
    Path("tests/test_v25117_grounded_target_record_plan.py"),
    Path("tests/test_v25118_target_record_frontier_selection.py"),
    Path("tests/test_v24999_shared_response_selection_runtime.py"),
    Path("tests/test_v24990_query_vector_paired_runtime.py"),
    Path("tests/test_v24986_robust_paired_runtime.py"),
    Path("tests/test_v25110_exact_visible_schema.py"),
)
RUNNER_MARKER = str(RUNNER)
CHILD_MARKER = "v25130_no_child_process"

BUILD_ROLE = "v25130_causal_salience_exact220_build_audit"
PROTOCOL_ROLE = "v25130_causal_salience_exact220_preregistration"
PREAUDIT_ROLE = "v25130_causal_salience_exact220_preactivation_audit"
START_ROLE = "v25130_causal_salience_exact220_execution_start"
PROGRESS_ROLE = "v25130_causal_salience_exact220_safe_progress"
SLOT_ROLE = "v25130_model_slot"
SUMMARY_ROLE = "v25130_causal_salience_exact220_run_summary"
FREEZE_ROLE = "v25130_causal_salience_exact220_prediction_freeze"
FORWARD_ROLE = "v25130_causal_salience_exact220_forward_result"
FORWARD_AUDIT_NATIVE_ROLE = "v25130_causal_salience_exact220_forward_audit"
EVALUATOR_OWNER = "v25130_causal_salience_exact220_evaluator_v1"
EVALUATOR_PURPOSE = "postfreeze_fixed_partition_parallel_v25130_exact220_evaluator"
EVALUATOR_FREEZE_BINDING_FIELD = "native_v25130_prediction_freeze_bound_by_role_projection"

PARENT_QUALITY_AUDIT = Path(
    "results/v25129_causal_salience_external_postresult_audit_v1_20260811.json"
)
PARENT_QUALITY_AUDIT_SHA256 = (
    "d1c15ecc71196a158c7c7aad647d610ce47f60930ddd420fdb034a10ca04e0b1"
)
BASELINE_RESULT = Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json")
LATEST_COMPLETE_RESULT = Path(
    "results/v24969_pacing_aware_replication_result_v1_20260809.json"
)

FORWARD_SOURCES = (
    SOURCE,
    RUNTIME,
    PARENT_RUNTIME,
    GROUNDING,
    PLANNER,
    SELECTOR,
    FETCH,
    FETCH_HELPER,
    LEASE,
    RUNNER,
)
LOCAL_SOURCES = (
    *FORWARD_SOURCES,
    CONTROL,
    FINALIZER,
    TEST,
    *PARENT_TESTS,
    PARENT_TASK_PROTOCOL,
    PARENT_QUALITY_AUDIT,
)

_LEGACY_CONTROL_ROLES = {
    "v25030_evidence_conditioned_exact220_build_audit": BUILD_ROLE,
    "v25030_evidence_conditioned_exact220_preactivation_audit": PREAUDIT_ROLE,
    "v25030_evidence_conditioned_exact220_execution_start": START_ROLE,
}

payload_sha256 = base.payload_sha256
sha256 = base.sha256
git = base.git
sealed = base.sealed
protected_watcher_snapshot = base.protected_watcher_snapshot
_ordinary = base._ordinary
_parent_task_contract = base._parent_task_contract
_input_bindings = base._input_bindings


def seal(value: Mapping[str, Any], field: str) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if copied.get("role") in _LEGACY_CONTROL_ROLES:
        copied["role"] = _LEGACY_CONTROL_ROLES[str(copied["role"])]
    copied.pop(field, None)
    copied[field] = payload_sha256(copied)
    return copied


def task_vector(
    root: Path, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    tasks = base.task_vector(root)
    expected = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256(
            [row["opaque_id"] for row in tasks]
        ),
        "visible_question_vector_sha256": payload_sha256(
            [row["question"] for row in tasks]
        ),
    }
    if protocol is not None and protocol.get("task_contract") != expected:
        raise RuntimeError("V2.51.30 protocol task binding drifted")
    return tasks


def arm_order_vector() -> list[list[str]]:
    root = Path(__file__).resolve().parents[2]
    tasks = task_vector(root)
    ranked = sorted(
        range(SELECTED_COUNT),
        key=lambda index: hashlib.sha256(
            f"v25130-arm-order:{tasks[index]['opaque_id']}".encode()
        ).hexdigest(),
    )
    candidate_first = set(ranked[: SELECTED_COUNT // 2])
    return [
        [CANDIDATE_ARM, CONTROL_ARM]
        if index in candidate_first
        else [CONTROL_ARM, CANDIDATE_ARM]
        for index in range(SELECTED_COUNT)
    ]


def _module_candidates(relative: Path, node: ast.AST) -> list[Path]:
    candidates: list[Path] = []
    if isinstance(node, ast.Import):
        for item in node.names:
            if item.name.startswith("deepwide_agent."):
                candidates.append(
                    Path("src") / Path(*item.name.split(".")).with_suffix(".py")
                )
            elif item.name.startswith("scripts."):
                candidates.append(Path(*item.name.split(".")).with_suffix(".py"))
    elif isinstance(node, ast.ImportFrom):
        module = node.module or ""
        if node.level and relative.parts[:2] == ("src", "deepwide_agent"):
            if module:
                candidates.append(
                    Path("src/deepwide_agent")
                    / Path(*module.split(".")).with_suffix(".py")
                )
            else:
                candidates.extend(
                    Path("src/deepwide_agent") / f"{item.name}.py"
                    for item in node.names
                )
        elif module == "deepwide_agent":
            candidates.extend(
                Path("src/deepwide_agent") / f"{item.name}.py"
                for item in node.names
            )
        elif module.startswith("deepwide_agent."):
            candidates.append(
                Path("src") / Path(*module.split(".")).with_suffix(".py")
            )
        elif module == "scripts":
            candidates.extend(
                Path("scripts") / f"{item.name}.py" for item in node.names
            )
        elif module.startswith("scripts."):
            candidates.append(Path(*module.split(".")).with_suffix(".py"))
    return candidates


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
            for candidate in _module_candidates(relative, node):
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool = True) -> dict[str, str]:
    relatives = {
        *forward_dependency_closure(root),
        CONTROL,
        FINALIZER,
        TEST,
        *PARENT_TESTS,
        PARENT_TASK_PROTOCOL,
        PARENT_QUALITY_AUDIT,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = _ordinary(relative, root)
        if tracked and subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(relative)],
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        ).returncode != 0:
            raise RuntimeError(f"V2.51.30 source is not tracked: {relative}")
        output[str(relative)] = sha256(path)
    return output


def _build_audit_binding(root: Path) -> dict[str, str] | None:
    path = root / BUILD_AUDIT
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.51.30 build audit is nonordinary")
    return {"path": str(BUILD_AUDIT), "sha256": sha256(path)}


def _quality_parent(root: Path) -> dict[str, Any]:
    path = _ordinary(PARENT_QUALITY_AUDIT, root)
    import json

    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        sha256(path) != PARENT_QUALITY_AUDIT_SHA256
        or value.get("role")
        != "v25129_causal_salience_external_quality_postresult_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("causal_salience_external_quality_gate_go") is not True
        or value.get("authorization", {}).get("full220_successor_build") is not True
        or value.get("authorization", {}).get(
            "deepwidebench_dev64_exact220_launch"
        )
        is not False
        or not sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.51.30 parent quality gate drifted")
    return {
        "path": str(PARENT_QUALITY_AUDIT),
        "sha256": PARENT_QUALITY_AUDIT_SHA256,
        "quality_gate_go": True,
        "full220_successor_build_authorized": True,
        "direct_exact220_launch_authorized_by_parent": False,
    }


def build_protocol(
    root: Path,
    *,
    now: int,
    tracked: bool = True,
    require_clean: bool = True,
    require_pristine: bool = True,
) -> dict[str, Any]:
    if require_clean and (
        git(root, "status", "--porcelain")
        or git(root, "rev-parse", "HEAD") != git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.51.30 protocol requires clean pushed HEAD")
    future = (
        PROTOCOL,
        PREAUDIT,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        EVALUATOR_PROTOCOL,
        RESULT,
        POSTAUDIT,
        OUTPUT_ROOT,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink() for path in future
    ):
        raise FileExistsError("V2.51.30 future surface exists")
    tasks = task_vector(root)
    manifest = dependency_manifest(root, tracked=tracked)
    value = {
        "artifact_version": 1,
        "role": PROTOCOL_ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": git(root, "rev-parse", "HEAD"),
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256(
                [row["opaque_id"] for row in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [row["question"] for row in tasks]
            ),
        },
        "build_audit": _build_audit_binding(root),
        "input_bindings": _input_bindings(root),
        "parent_quality_gate": _quality_parent(root),
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "limits": copy.deepcopy(LIMITS),
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "runtime_policy_id": runtime.POLICY_ID,
            "runtime_phases": list(runtime.PHASES),
            "frozen_prediction_arm": runtime.CANDIDATE_ARM,
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "single_forward_no_retry_resume_skip_or_selective_rerun": True,
        },
        "treatment_scope": {
            "v24857_visible_task_vector_byte_equal": True,
            "v25129_validated_causal_salience_runtime_integrated": True,
            "candidate_prediction_identity_handoff_without_retrieval_gain": True,
            "second_wave_evidence_priority_is_prompt_length_preserving": True,
            "matched_pair_doubles_synthesis_cost_vs_single_arm_exact220": True,
            "cross_rollout_difference_is_not_a_paired_causal_effect": True,
        },
        "mechanism_gate": {
            "fixed_denominator": SELECTED_COUNT,
            "all_tasks_terminal": True,
            "all_causal_receipts_valid": True,
            "zero_unattributable_prediction_changes": True,
            "identity_handoff_exactly_complements_retrieval_mechanism": True,
            "all_tasks_within_frozen_paired_resource_caps": True,
            "postfreeze_evaluator_unconditional_on_observed_quality": True,
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
    return seal(value, "protocol_payload_sha256")


def validate_protocol(
    root: Path, value: Mapping[str, Any], *, tracked: bool = True
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = build_protocol(
        root,
        now=int(copied.get("created_at_unix", -1)),
        tracked=tracked,
        require_clean=False,
        require_pristine=False,
    )
    # The protocol records the clean pushed implementation HEAD that existed
    # before the protocol artifact itself was committed.  Preserve that
    # immutable value when validating from later commits.
    if not isinstance(copied.get("git_head"), str) or not re.fullmatch(
        r"[0-9a-f]{40}", copied["git_head"]
    ):
        raise RuntimeError("V2.51.30 protocol git binding drifted")
    expected["git_head"] = copied["git_head"]
    expected = seal(expected, "protocol_payload_sha256")
    if copied != expected or not sealed(copied, "protocol_payload_sha256"):
        raise RuntimeError("V2.51.30 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "arm_order_vector",
    "dependency_manifest",
    "forward_dependency_closure",
    "git",
    "payload_sha256",
    "protected_watcher_snapshot",
    "seal",
    "sealed",
    "sha256",
    "task_vector",
    "validate_protocol",
]
