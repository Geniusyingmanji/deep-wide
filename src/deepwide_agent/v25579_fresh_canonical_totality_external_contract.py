"""One-shot external contract for the fresh canonical-column totality gate.

The fixed V2.55.77 population is split before any provider effect by visible
column bytes alone.  Every task executes exactly one V2.55.75 successor
forward.  After that forward is complete, a pure local invocation of the
frozen V2.53.95 verifier reconstructs whether the predecessor would have
raised on the same raw columns.  No second model, search, fetch, or sampling
effect is permitted.

For a verified canonical-column predecessor failure, the outer control is a
pre-registered visible-schema failure-as-zero fallback and the outer
candidate is the V2.55.75 parent prediction preserved by its narrow handoff.
For an ordinary ASCII task, the two outer predictions are byte-identical.
Truth, evaluator output, benchmark labels, and historical outcomes are absent
from the forward dependency closure.  Entropy/information gain assigns zero
signed credit.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import re
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v25068_quote_verified_external_contract as base
from . import v25558_model_pool_contract as model_pool
from . import v25575_canonical_column_totality_runtime as runtime
from . import v25577_fresh_canonical_totality_population as population


DATE = "20260818"
PROTOCOL_ID = "v25579_fresh_canonical_column_totality_external_v1"
BUILD_AUDIT = Path(
    f"results/v25579_fresh_canonical_totality_build_audit_v1_{DATE}.json"
)
PROTOCOL = Path(
    f"results/v25579_fresh_canonical_totality_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v25579_fresh_canonical_totality_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v25579_fresh_canonical_totality_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v25579_fresh_canonical_totality_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v25579_fresh_canonical_totality_forward_audit_v1_{DATE}.json"
)
POSTFREEZE_QUALITY_PROTOCOL = Path(
    f"results/v25580_fresh_canonical_totality_quality_preregistration_v1_{DATE}.json"
)
QUALITY_RESULT = Path(
    f"results/v25580_fresh_canonical_totality_quality_result_v1_{DATE}.json"
)
QUALITY_AUDIT = Path(
    f"results/v25580_fresh_canonical_totality_quality_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v25579_fresh_canonical_totality_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
TASK_ROWS = OUTPUT_ROOT / "frozen_task_results.jsonl"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"

CONTRACT = Path(
    "src/deepwide_agent/v25579_fresh_canonical_totality_external_contract.py"
)
RUNTIME = Path(
    "src/deepwide_agent/v25575_canonical_column_totality_runtime.py"
)
POPULATION = Path(
    "src/deepwide_agent/v25577_fresh_canonical_totality_population.py"
)
RUNNER = Path("scripts/run_v25579_fresh_canonical_totality_external.py")
CONTROL = Path("scripts/control_v25579_fresh_canonical_totality_external.py")
TEST = Path("tests/test_v25579_fresh_canonical_totality_external.py")
CONTROL_TEST = Path(
    "tests/test_control_v25579_fresh_canonical_totality_external.py"
)
RUNTIME_TEST = Path(
    "tests/test_v25575_canonical_column_totality_runtime.py"
)
POPULATION_TEST = Path(
    "tests/test_v25577_fresh_canonical_totality_population.py"
)
POPULATION_AUDIT_TEST = Path(
    "tests/test_audit_v25578_fresh_canonical_totality_population.py"
)
MODEL_POOL_TEST = Path("tests/test_v25558_model_pool_contract.py")
CLONE_HELPER = Path("scripts/v25478_clone_safe_runner_namespace.py")
CLONE_HELPER_TEST = Path("tests/test_v25478_clone_safe_runner_namespace.py")
HELPER = base.HELPER
LEASE = Path("scripts/deepwide_api_lease.py")

RUNTIME_IMPLEMENTATION_COMMIT = "9357ef7a49859b4e6ae4f96f4937be5dfcf313e3"
RUNTIME_SHA256 = (
    "37c10b847bb9b340e78b78f5d0af5d0b34388247e57407e3cc239166ce943bef"
)
RUNTIME_BUILD_AUDIT = Path(
    "results/v25576_canonical_column_totality_build_audit_v1_20260818.json"
)
RUNTIME_BUILD_AUDIT_SHA256 = (
    "04cfc97fd957394929b7fcf68991027a707a2122198fec5ec7f0c0daa659014f"
)
POPULATION_IMPLEMENTATION_COMMIT = "9054ab8485ff88ff1666830beeda94b69a3454f9"
POPULATION_AUDIT = Path(
    "results/v25578_fresh_canonical_totality_population_build_audit_v1_20260818.json"
)
POPULATION_AUDIT_SHA256 = (
    "542bfaaa9f86270dde820a443b8a5d8009305afd25c2d742dbfdb829eea3c654"
)

CONTROL_ARM = "predecessor_failure_as_zero_control"
CANDIDATE_ARM = "v25575_successor_candidate"
ARMS = (CONTROL_ARM, CANDIDATE_ARM)
EXPECTED_FAILURE_FALLBACK_VECTOR_SHA256 = (
    "dedbac50dd0e76d053a3ce832e4a1b8e1455808d737855792dc54dd49457735e"
)

FORWARD_SOURCES = (
    CONTRACT,
    RUNTIME,
    POPULATION,
    RUNNER,
    CLONE_HELPER,
    HELPER,
    LEASE,
)
TASK_COUNT = population.TASK_COUNT
EXECUTOR_CONCURRENCY = 20
MODEL_SLOT_CAP = 16
PHASES = runtime.PHASES
LEASE_PATH = base.LEASE_PATH
LEASE_OWNER = "v25579_fresh_canonical_column_totality_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_canonical_column_totality_gate_v1"

# Three formerly protected watchers were already absent in the pushed
# V2.55.76 audit.  They remain required absent; this contract neither restarts
# nor replaces them.  The sole healthy watcher must preserve its exact PID,
# start ticks, and command marker.
EXPECTED_WATCHERS = (
    (2808901, 746680268, "scripts/watch_v24215_joint_package_recovery.py"),
)
EXPECTED_ABSENT_WATCHERS = (
    (795336, 713986317, "scripts/watch_v2415_r1_checkpoint_liveness.py"),
    (3061652, 747569004, "scripts/watch_v24218_exact220_executor.py"),
    (2889939, 746969965, "scripts/watch_v24216_package_gate.py"),
)

MODEL = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "name": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
}
SEARCH = {
    "proxy_url": "http://127.0.0.1:9878/responses",
    "model": "gpt-5.6-sol",
    "reasoning_effort": "low",
    "service_tier": "priority",
    "timeout_seconds": 65,
    "max_retries": 2,
    "workers": 1,
    "batch_size": 8,
    "context_size": "medium",
    "max_output_tokens": 7_000,
    "fetch_workers": 8,
    "fetch_timeout_seconds": 20,
    "hard_fetch_deadline_seconds": 25,
}
LIMITS = {
    "wall_seconds": 240,
    "model_calls": 3,
    "search_queries": 4,
    "fetch_targets": 10,
    "search_results_per_query": 3,
    "evidence_chars": 60_000,
    "page_chars": 5_000,
    "plan_output_tokens": 4_000,
    "synthesis_output_tokens": 30_000,
    "repair_output_tokens": 12_000,
}
CLEANUP_RESERVE_SECONDS = 5.0
MINIMUM_MODEL_ATTEMPT_SECONDS = 0.05
SECRET = base.SECRET
payload_sha256 = base.payload_sha256
sha256 = base.sha256
seal = base.seal
sealed = base.sealed
git = base.git
ordinary = base.ordinary


def task_vector() -> list[dict[str, str]]:
    return population.task_vector()


def validate_task_vector(
    values: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    copied = [dict(value) for value in values]
    if copied != population.task_vector():
        raise ValueError("V2.55.79 task vector drifted")
    return copied


def failure_fallback(index: int) -> str:
    columns = population.columns_for_index(index)
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n| "
        + " | ".join("Unknown" for _ in columns)
        + " |\n| "
        + " | ".join("Unknown" for _ in columns)
        + " |\n```"
    )


def failure_fallback_vector() -> list[str]:
    values = [failure_fallback(index) for index in range(TASK_COUNT)]
    if (
        EXPECTED_FAILURE_FALLBACK_VECTOR_SHA256 != "TO_BE_FROZEN"
        and payload_sha256(values) != EXPECTED_FAILURE_FALLBACK_VECTOR_SHA256
    ):
        raise RuntimeError("V2.55.79 failure fallback vector drifted")
    return values


def watcher_snapshot(proc_root: Path = Path("/proc")) -> dict[str, Any]:
    present: list[dict[str, Any]] = []
    for pid, ticks, marker in EXPECTED_WATCHERS:
        stat = proc_root / str(pid) / "stat"
        cmdline = proc_root / str(pid) / "cmdline"
        if not stat.is_file() or not cmdline.is_file():
            raise RuntimeError("V2.55.79 protected watcher absent")
        raw = stat.read_text(encoding="utf-8")
        suffix = raw[raw.rfind(")") + 2 :].split()
        command = cmdline.read_bytes().replace(b"\0", b" ").decode(
            errors="replace"
        )
        if len(suffix) <= 19 or int(suffix[19]) != ticks or marker not in command:
            raise RuntimeError("V2.55.79 protected watcher identity drifted")
        present.append({"pid": pid, "start_ticks": ticks, "marker": marker})
    absent: list[dict[str, Any]] = []
    for pid, ticks, marker in EXPECTED_ABSENT_WATCHERS:
        if (proc_root / str(pid)).exists():
            raise RuntimeError("V2.55.79 absent watcher PID was replaced")
        absent.append(
            {
                "pid": pid,
                "start_ticks": ticks,
                "marker": marker,
                "present": False,
            }
        )
    return {
        "healthy_frozen_watchers": present,
        "historically_exited_watchers": absent,
        "replacement_process_count": 0,
        "agent_signal_stop_restart_or_replacement_performed": False,
    }


def source_policy() -> dict[str, Any]:
    return {
        **population.source_policy(),
        "one_v25575_successor_forward_per_task": True,
        "outer_control_is_predecessor_failure_fallback_only_after_exact_local_failure": True,
        "outer_candidate_is_successor_parent_prediction_byte_exact": True,
        "ordinary_outer_control_and_candidate_are_byte_exact": True,
        "predecessor_counterfactual_invokes_frozen_v25395_verifier_locally": True,
        "counterfactual_runs_only_after_successor_provider_effects_complete": True,
        "counterfactual_additional_model_search_fetch_sampling_or_network_effects": 0,
        "preassigned_exposure_never_routes_search_model_fetch_or_prompt": True,
        "independent_sampling_between_outer_arms": False,
        "candidate_additional_queries_fetches_model_calls_tokens_context_wall_or_network": 0,
        "historical_parent_replay_routes_or_filters_fresh_forward": False,
        "evaluator_truth_quality_absent_from_forward_dependency_closure": True,
        "fixed_failure_as_zero_denominator_no_retry_resume_or_replacement": True,
        "clone_namespace_assembled_from_actual_source_function_globals": True,
        "model_pool_policy_id": model_pool.POLICY_ID,
        "model_pool_id": model_pool.MODEL_POOL_ID,
        "prediction_freeze_precedes_truth_evaluator_or_quality_decision": True,
    }


def mechanism_gate() -> dict[str, Any]:
    return copy.deepcopy(population.mechanism_gate())


def quality_gate() -> dict[str, Any]:
    return copy.deepcopy(population.quality_gate())


def _module_candidates(relative: Path, node: ast.AST) -> list[Path]:
    return base._module_candidates(relative, node)


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
        TEST,
        CONTROL_TEST,
        RUNTIME_TEST,
        POPULATION_TEST,
        POPULATION_AUDIT_TEST,
        MODEL_POOL_TEST,
        CLONE_HELPER_TEST,
        RUNTIME_BUILD_AUDIT,
        POPULATION_AUDIT,
    }
    output: dict[str, str] = {}
    for relative in sorted(relatives, key=str):
        path = ordinary(root, relative, tracked=tracked)
        if path.suffix == ".py" and SECRET.search(path.read_text(encoding="utf-8")):
            raise RuntimeError("V2.55.79 credential literal in dependency manifest")
        output[str(relative)] = sha256(path)
    return output


def future_surfaces() -> tuple[Path, ...]:
    return (
        PROTOCOL,
        PREAUDIT,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        POSTFREEZE_QUALITY_PROTOCOL,
        QUALITY_RESULT,
        QUALITY_AUDIT,
        OUTPUT_ROOT,
    )


def population_contract() -> dict[str, Any]:
    return {
        "task_count": TASK_COUNT,
        "identity_count": 40,
        "canonical_drift_task_count": population.DRIFT_TASK_COUNT,
        "ordinary_ascii_task_count": population.ORDINARY_TASK_COUNT,
        "identity_vector_sha256": population.EXPECTED_IDENTITY_VECTOR_SHA256,
        "task_vector_sha256": population.EXPECTED_TASK_VECTOR_SHA256,
        "failure_fallback_vector_sha256": (
            EXPECTED_FAILURE_FALLBACK_VECTOR_SHA256
        ),
        "selection_parent_commit": population.SELECTION_PARENT_COMMIT,
        "question_overlap_with_fixed220": 0,
        "opaque_id_overlap_with_fixed220": 0,
        "all_historical_population_identity_and_question_overlap": 0,
        "prior_population_or_execution_reused": False,
    }


def build_protocol(
    root: Path,
    *,
    now: int,
    tracked: bool,
    require_pristine: bool,
    build_audit_sha256: str,
) -> dict[str, Any]:
    head = git(root, "rev-parse", "HEAD")
    target = git(root, "rev-parse", "target/main")
    if require_pristine and (
        git(root, "status", "--porcelain")
        or head != target
        or any(
            (root / path).exists() or (root / path).is_symlink()
            for path in future_surfaces()
        )
    ):
        raise RuntimeError("V2.55.79 protocol surface is not pristine")
    manifest = dependency_manifest(root, tracked=tracked)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25579_fresh_canonical_totality_preregistration",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": head,
        "target_main": target,
        "build_audit_sha256": str(build_audit_sha256),
        "runtime_implementation": {
            "commit": RUNTIME_IMPLEMENTATION_COMMIT,
            "path": str(RUNTIME),
            "sha256": RUNTIME_SHA256,
            "build_audit_path": str(RUNTIME_BUILD_AUDIT),
            "build_audit_sha256": RUNTIME_BUILD_AUDIT_SHA256,
        },
        "population_audit": {
            "implementation_commit": POPULATION_IMPLEMENTATION_COMMIT,
            "path": str(POPULATION_AUDIT),
            "sha256": POPULATION_AUDIT_SHA256,
        },
        "source_manifest": manifest,
        "source_manifest_sha256": payload_sha256(manifest),
        "population": population_contract(),
        "execution": {
            "executor_concurrency": EXECUTOR_CONCURRENCY,
            "model_slot_cap": MODEL_SLOT_CAP,
            "model": copy.deepcopy(MODEL),
            "search": copy.deepcopy(SEARCH),
            "limits": copy.deepcopy(LIMITS),
            "physical_caps": {
                "queries": 4,
                "fetches": 14,
                "normal_path_model_forwards": 3,
            },
            "single_task_attempt": True,
            "retry_resume_skip_backfill_replacement": False,
            "runtime_policy_id": runtime.POLICY_ID,
            "ordinary_surface_policy_id": runtime.totality.POLICY_ID,
            "predecessor_verifier_policy_id": runtime.visible_parent.POLICY_ID,
            "outer_arms": list(ARMS),
            "clone_namespace_policy_id": "v25478_clone_safe_runner_namespace_v1",
            "model_pool_policy_id": model_pool.POLICY_ID,
            "model_pool_id": model_pool.MODEL_POOL_ID,
            "one_successor_forward_per_task": True,
            "control_and_candidate_share_all_provider_retrieval_and_sampling_effects": True,
            "counterfactual_additional_queries_fetches_model_calls_or_sampling_effects": 0,
            "persist_both_outer_prediction_texts_for_postfreeze_quality": True,
        },
        "failure_gate_semantics": {
            "fixed_terminal_denominator": TASK_COUNT,
            "successor_outer_failure_allowed": 0,
            "budget_rejection_allowed": 0,
            "unsafe_handoff_allowed": 0,
            "drift_control_is_pre_registered_failure_as_zero_fallback": True,
            "ordinary_control_is_candidate_byte_exact": True,
            "failure_rows_retain_partial_effects_and_per_task_hard_caps": True,
        },
        "source_policy": source_policy(),
        "mechanism_gate": mechanism_gate(),
        "postfreeze_quality_gate": quality_gate(),
        "protected_watchers": watcher_snapshot(),
        "authorization": {
            "preactivation_audit_generation": True,
            "execution_start_generation": False,
            "one_external_forward": False,
            "postfreeze_quality": False,
            "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
            "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
        },
    }
    return validate_protocol(root, seal(value, "protocol_payload_sha256"), tracked=tracked)


def validate_protocol(
    root: Path, value: Mapping[str, Any], *, tracked: bool = True
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    manifest = copied.get("source_manifest")
    execution = copied.get("execution") or {}
    expected_authorization = {
        "preactivation_audit_generation": True,
        "execution_start_generation": False,
        "one_external_forward": False,
        "postfreeze_quality": False,
        "deepwidebench_forward_evaluator_leaderboard_or_sota": False,
        "retry_resume_replay_backfill_replacement_or_selective_revaluation": False,
    }
    if (
        copied.get("artifact_version") != 1
        or copied.get("role")
        != "v25579_fresh_canonical_totality_preregistration"
        or copied.get("protocol_id") != PROTOCOL_ID
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied.get("git_head") != copied.get("target_main")
        or re.fullmatch(
            r"[0-9a-f]{64}", str(copied.get("build_audit_sha256"))
        )
        is None
        or copied.get("runtime_implementation")
        != {
            "commit": RUNTIME_IMPLEMENTATION_COMMIT,
            "path": str(RUNTIME),
            "sha256": RUNTIME_SHA256,
            "build_audit_path": str(RUNTIME_BUILD_AUDIT),
            "build_audit_sha256": RUNTIME_BUILD_AUDIT_SHA256,
        }
        or copied.get("population_audit")
        != {
            "implementation_commit": POPULATION_IMPLEMENTATION_COMMIT,
            "path": str(POPULATION_AUDIT),
            "sha256": POPULATION_AUDIT_SHA256,
        }
        or not isinstance(manifest, Mapping)
        or dict(manifest) != dependency_manifest(root, tracked=tracked)
        or copied.get("source_manifest_sha256") != payload_sha256(manifest)
        or copied.get("population") != population_contract()
        or execution.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or execution.get("model_slot_cap") != MODEL_SLOT_CAP
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("limits") != LIMITS
        or execution.get("physical_caps")
        != {"queries": 4, "fetches": 14, "normal_path_model_forwards": 3}
        or execution.get("single_task_attempt") is not True
        or execution.get("retry_resume_skip_backfill_replacement") is not False
        or execution.get("runtime_policy_id") != runtime.POLICY_ID
        or execution.get("ordinary_surface_policy_id") != runtime.totality.POLICY_ID
        or execution.get("predecessor_verifier_policy_id")
        != runtime.visible_parent.POLICY_ID
        or execution.get("outer_arms") != list(ARMS)
        or execution.get("clone_namespace_policy_id")
        != "v25478_clone_safe_runner_namespace_v1"
        or execution.get("model_pool_policy_id") != model_pool.POLICY_ID
        or execution.get("model_pool_id") != model_pool.MODEL_POOL_ID
        or execution.get("one_successor_forward_per_task") is not True
        or execution.get(
            "control_and_candidate_share_all_provider_retrieval_and_sampling_effects"
        )
        is not True
        or execution.get(
            "counterfactual_additional_queries_fetches_model_calls_or_sampling_effects"
        )
        != 0
        or execution.get(
            "persist_both_outer_prediction_texts_for_postfreeze_quality"
        )
        is not True
        or copied.get("failure_gate_semantics")
        != {
            "fixed_terminal_denominator": 20,
            "successor_outer_failure_allowed": 0,
            "budget_rejection_allowed": 0,
            "unsafe_handoff_allowed": 0,
            "drift_control_is_pre_registered_failure_as_zero_fallback": True,
            "ordinary_control_is_candidate_byte_exact": True,
            "failure_rows_retain_partial_effects_and_per_task_hard_caps": True,
        }
        or copied.get("source_policy") != source_policy()
        or copied.get("mechanism_gate") != mechanism_gate()
        or copied.get("postfreeze_quality_gate") != quality_gate()
        or copied.get("protected_watchers") != watcher_snapshot()
        or copied.get("authorization") != expected_authorization
        or not sealed(copied, "protocol_payload_sha256")
    ):
        raise ValueError("V2.55.79 external protocol drifted")
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "failure_fallback",
    "failure_fallback_vector",
    "forward_dependency_closure",
    "future_surfaces",
    "mechanism_gate",
    "model_pool",
    "population",
    "population_contract",
    "quality_gate",
    "runtime",
    "source_policy",
    "task_vector",
    "validate_protocol",
    "validate_task_vector",
    "watcher_snapshot",
]
