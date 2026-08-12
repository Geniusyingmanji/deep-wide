"""Label-blind exact-220 successor for the validated quote-aware repair.

The public DeepWideBench vector is byte-identical to the frozen V2.48.57
vector.  Runtime input is exactly ``opaque_id`` and ``question``.  Search,
model, prompt, retrieval, token, context, and wall limits are inherited from
the V2.52.06 quality experiment; only its deterministic same-response
quote-aware production/export treatment is carried into this full rollout.
"""

from __future__ import annotations

import ast
import copy
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v25130_causal_salience_exact220_contract as task_parent
from . import v25206_cran_dcf_quality_contract as quality_parent


DATE = "20260812"
PROTOCOL_ID = "v25208_quote_aware_keyless_exact220_v1"
BUILD_AUDIT = Path(f"results/v25208_quote_aware_exact220_build_audit_v1_{DATE}.json")
PROTOCOL = Path(f"results/v25208_quote_aware_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v25208_quote_aware_exact220_preactivation_audit_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v25208_quote_aware_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v25208_quote_aware_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v25208_quote_aware_exact220_forward_audit_v1_{DATE}.json")
EVALUATOR_PROTOCOL = Path(
    f"results/v25208_quote_aware_exact220_evaluator_preregistration_v1_{DATE}.json"
)
RESULT = Path(f"results/v25208_quote_aware_exact220_result_v1_{DATE}.json")
POSTAUDIT = Path(
    f"results/v25208_quote_aware_exact220_postresult_audit_v1_{DATE}.json"
)

OUTPUT_ROOT = Path(f"outputs/v25208_quote_aware_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
RUNTIME_RESULTS = TASK_ROWS
COMPATIBILITY_AGGREGATE = OUTPUT_ROOT / "compatibility_aggregate.json"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"

CONTRACT = Path("src/deepwide_agent/v25208_quote_aware_exact220_contract.py")
SOURCE = CONTRACT
RUNTIME = Path(
    "src/deepwide_agent/v25188_export_failure_tolerant_same_response_runtime.py"
)
RUNNER = Path("scripts/run_v25208_quote_aware_exact220.py")
RUNNER_MARKER = str(RUNNER)
CHILD_MARKER = "v25208_no_child_process"
CONTROL = Path("scripts/control_v25208_quote_aware_exact220.py")
FINALIZER = Path("scripts/finalize_v25208_quote_aware_exact220.py")
TEST = Path("tests/test_v25208_quote_aware_exact220.py")
SOURCE_MANIFEST = task_parent.VISIBLE_MANIFEST

PARENT_QUALITY_AUDIT = quality_parent.POSTAUDIT
PARENT_QUALITY_AUDIT_SHA256 = (
    "893e808090e1f25dd867087419252f98d9fe2c68eb7acf480493ff4acc7d4813"
)
PARENT_BUILD_AUDIT = quality_parent.BUILD_AUDIT
PARENT_BUILD_AUDIT_SHA256 = (
    "797e006564d991d3399101327a34d86766521c05a5a18f63d952fe7d2615034c"
)
PARENT_RECOVERY_AUDIT = Path(
    "results/v25207_v25206_hash_bound_preactivation_recovery_audit_v1_20260812.json"
)
PARENT_RECOVERY_AUDIT_SHA256 = (
    "fe71ec6417a9ce9cf7bb6a6eee3a1f995c771ebb2130f34a63c3419f33d99b67"
)
BASELINE_RESULT = Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json")
LATEST_COMPLETE_RESULT = Path(
    "results/v25132_v25130_terminal_summary_exact220_result_v1_20260811.json"
)

TASK_COUNT = 220
SELECTED_COUNT = TASK_COUNT
EXECUTOR_CONCURRENCY = 40
MODEL_SLOT_CAP = 16
LEASE_PATH = quality_parent.LEASE_PATH
LEASE_OWNER = "v25208_quote_aware_exact220_forward_v1"
LEASE_PURPOSE = "single_label_blind_quote_aware_exact220"
EVALUATOR_OWNER = "v25208_quote_aware_exact220_evaluator_v1"
EVALUATOR_PURPOSE = "postfreeze_fixed_partition_parallel_v25208_exact220"
MODEL = copy.deepcopy(quality_parent.MODEL)
SEARCH = copy.deepcopy(quality_parent.SEARCH)
LIMITS = copy.deepcopy(quality_parent.LIMITS)
CLEANUP_RESERVE_SECONDS = quality_parent.CLEANUP_RESERVE_SECONDS
MINIMUM_MODEL_ATTEMPT_SECONDS = quality_parent.MINIMUM_MODEL_ATTEMPT_SECONDS
runtime = quality_parent.runtime
ARMS = runtime.ARMS
CONTROL_ARM = runtime.CONTROL_ARM
CANDIDATE_ARM = runtime.CANDIDATE_ARM
# Used only if an outer failure happens before a visible schema can be read.
COLUMNS = ("Unknown",)
EXPECTED_WATCHERS = quality_parent.EXPECTED_WATCHERS
PROTECTED_WATCHERS = task_parent.PROTECTED_WATCHERS

FORWARD_ROLE = "v25208_quote_aware_exact220_forward_result"
SUMMARY_ROLE = "v25208_quote_aware_exact220_run_summary"
FREEZE_ROLE = "v25208_quote_aware_exact220_prediction_freeze"
FORWARD_AUDIT_NATIVE_ROLE = "v25208_quote_aware_exact220_forward_audit"

SECRET = quality_parent.SECRET
payload_sha256 = quality_parent.payload_sha256
sha256 = quality_parent.sha256
seal = quality_parent.seal
sealed = quality_parent.sealed
git = quality_parent.git
ordinary = quality_parent.ordinary
watcher_snapshot = quality_parent.watcher_snapshot
protected_watcher_snapshot = watcher_snapshot

FORWARD_SOURCES = (
    CONTRACT,
    RUNNER,
    quality_parent.COMPATIBILITY,
    *quality_parent.FORWARD_SOURCES,
)


def task_vector(
    root: Path | None = None, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    repository = (
        Path(__file__).resolve().parents[2] if root is None else Path(root).resolve()
    )
    rows = [
        {"opaque_id": row["opaque_id"], "question": row["question"]}
        for row in task_parent.task_vector(repository)
    ]
    if (
        len(rows) != TASK_COUNT
        or len({row["opaque_id"] for row in rows}) != TASK_COUNT
        or any(set(row) != {"opaque_id", "question"} for row in rows)
    ):
        raise RuntimeError("V2.52.08 public exact-220 vector drifted")
    expected = {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": TASK_COUNT,
        "opaque_id_vector_sha256": payload_sha256(
            [row["opaque_id"] for row in rows]
        ),
        "visible_question_vector_sha256": payload_sha256(
            [row["question"] for row in rows]
        ),
    }
    if protocol is not None and protocol.get("task_contract") != expected:
        raise RuntimeError("V2.52.08 protocol task binding drifted")
    return rows


def source_policy() -> dict[str, Any]:
    return {
        "runtime_boundary": ["opaque_id", "question", "same_forward_public_pages"],
        "mapping_gold_category_question_type_split_answer_evaluator_score_reward_read_by_forward": False,
        "prior_prediction_result_score_reward_or_evaluator_read_by_forward": False,
        "prediction_freeze_before_mapping_query_answer_or_official_evaluator_open": True,
        "only_treatment_is_v25206_validated_same_response_quote_aware_repair": True,
        "search_model_prompt_retrieval_budget_or_task_vector_changed_by_treatment": False,
        "control_and_candidate_share_the_same_raw_forward_response": True,
        "entropy_or_information_gain_assigns_signed_credit_or_routes": False,
        "positive_signed_credit_count": 0,
        "fixed_public_exact220_task_set_reexecuted": True,
        "new_or_disjoint_task_population_claimed": False,
        "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        "retry_resume_skip_or_selective_rerun": False,
        "leaderboard_or_sota_authorized": False,
    }


def mechanism_gate() -> dict[str, Any]:
    """Integrity gate; activation is reported but never required for scoring."""

    return {
        "fixed_task_denominator": TASK_COUNT,
        "terminal_tasks": TASK_COUNT,
        # These inherited fields keep the content-free mechanism decision
        # total.  The decision is diagnostic only for this unconditional
        # exact-220 evaluation; it never selects predictions or tasks.
        "completed_runtime_tasks": TASK_COUNT,
        "maximum_failure_as_zero_tasks": TASK_COUNT,
        "minimum_model_generated_tasks": 0,
        "maximum_fallback_tasks": TASK_COUNT,
        "minimum_same_raw_counterfactual_active_tasks": 0,
        "minimum_prediction_changed_tasks": 0,
        "active_equals_prediction_changed": True,
        "maximum_unsafe_public_export_failure_tasks": 0,
        "safe_public_export_failure_must_equal_safe_production_fallback": True,
        "maximum_outer_or_accounting_failure_tasks": TASK_COUNT,
        "maximum_terminal_effect_hard_failures": TASK_COUNT * 64,
        "exact_physical_queries_total": TASK_COUNT * 4,
        "maximum_physical_fetches_total": TASK_COUNT * 14,
        "maximum_model_forwards_total": TASK_COUNT * 4,
        "maximum_physical_queries_total": TASK_COUNT * 4,
        "maximum_additional_effect_tasks": 0,
        "positive_signed_credit_count": 0,
        "quote_aware_activation_is_shadow_not_a_scoring_gate": True,
        "official_evaluator_runs_on_all_frozen_predictions_after_audit": True,
    }


def quality_parent_receipt(root: Path, *, tracked: bool) -> dict[str, Any]:
    path = ordinary(root, PARENT_QUALITY_AUDIT, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if (
        sha256(path) != PARENT_QUALITY_AUDIT_SHA256
        or value.get("role") != "v25206_cran_dcf_quality_postresult_audit"
        or value.get("audit_valid") is not True
        or value.get("findings") != []
        or value.get("post_effect_tolerant_quality_gate_go") is not True
        or value.get("authorization", {}).get("deepwidebench_exact220_build")
        is not True
        or value.get("authorization", {}).get(
            "deepwidebench_exact220_launch_after_this_audit_is_pushed"
        )
        is not True
        or value.get("authorization", {}).get("leaderboard_or_sota") is not False
        or not sealed(value, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.52.08 quality parent drifted")
    return {
        "path": str(PARENT_QUALITY_AUDIT),
        "sha256": PARENT_QUALITY_AUDIT_SHA256,
        "quality_gate_go": True,
        "candidate_exact_successes": value["metrics"]["arms"][
            quality_parent.CANDIDATE_ARM
        ]["exact_table_successes"],
        "control_exact_successes": value["metrics"]["arms"][
            quality_parent.CONTROL_ARM
        ]["exact_table_successes"],
        "exact220_build_and_launch_authorized": True,
    }


def _module_candidates(relative: Path, node: ast.AST) -> list[Path]:
    return task_parent._module_candidates(relative, node)


def forward_dependency_closure(root: Path) -> tuple[Path, ...]:
    pending = list(FORWARD_SOURCES)
    observed: set[Path] = set()
    while pending:
        relative = pending.pop()
        if relative in observed:
            continue
        path = ordinary(root, relative, tracked=False)
        observed.add(relative)
        if path.suffix != ".py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            for candidate in _module_candidates(relative, node):
                if (root / candidate).is_file() and not (root / candidate).is_symlink():
                    pending.append(candidate)
    return tuple(sorted(observed, key=str))


def dependency_manifest(root: Path, *, tracked: bool) -> dict[str, str]:
    relatives = {
        *forward_dependency_closure(root),
        CONTROL,
        FINALIZER,
        TEST,
        task_parent.PARENT_TASK_PROTOCOL,
        PARENT_QUALITY_AUDIT,
        PARENT_BUILD_AUDIT,
        PARENT_RECOVERY_AUDIT,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if path.suffix in {".py", ".json", ".md"} and SECRET.search(
            path.read_text(encoding="utf-8")
        ):
            raise RuntimeError("V2.52.08 credential literal in manifest")
        output[str(relative)] = sha256(path)
    return output


def build_protocol(
    root: Path,
    *,
    now: int,
    tracked: bool,
    require_pristine: bool,
    build_audit_sha256: str,
) -> dict[str, Any]:
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
        raise RuntimeError("V2.52.08 future surface is not pristine")
    tasks = task_vector(root)
    manifest = dependency_manifest(root, tracked=tracked)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25208_quote_aware_exact220_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "build_audit_sha256": build_audit_sha256,
        "task_contract": {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": TASK_COUNT,
            "opaque_id_vector_sha256": payload_sha256(
                [row["opaque_id"] for row in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [row["question"] for row in tasks]
            ),
        },
        "input_bindings": task_parent._input_bindings(root),
        "parent_quality_gate": quality_parent_receipt(root, tracked=tracked),
        "execution": {
            "arms": list(ARMS),
            "only_treatment": "same_raw_v25206_validated_quote_aware_production_export",
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "runtime_policy_id": runtime.POLICY_ID,
            "frozen_prediction_arm": CANDIDATE_ARM,
            "protected_watchers": watcher_snapshot(),
            "single_atomic_forward_no_retry_resume_skip_or_selective_rerun": True,
        },
        "mechanism_gate": mechanism_gate(),
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": source_policy(),
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


def validate_protocol(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = build_protocol(
        root,
        now=int(copied.get("created_at_unix", -1)),
        tracked=True,
        require_pristine=False,
        build_audit_sha256=sha256(root / BUILD_AUDIT),
    )
    if copied != expected or not sealed(copied, "protocol_payload_sha256"):
        raise RuntimeError("V2.52.08 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "forward_dependency_closure",
    "git",
    "mechanism_gate",
    "payload_sha256",
    "protected_watcher_snapshot",
    "quality_parent_receipt",
    "seal",
    "sealed",
    "sha256",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "watcher_snapshot",
]
