"""Readiness-armed exact-220 contract for the frozen V2.48.57 policy.

The algorithm is unchanged.  Before an exact-220 execution start may exist,
one live runner must test all twelve ephemeral Tavily credentials through the
production rate-aware transport.  A successful aggregate receipt is bound to
that runner's PID/start ticks and to a non-serializable same-process capability.
The control plane can then authorize that exact process; the process consumes
the capability once and starts the frozen label-blind forward.
"""

from __future__ import annotations

import copy
import json
import os
import time
from collections.abc import Mapping
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import v24857_pacing_aware_exact220_contract as algorithm
from . import v24970_same_process_search_readiness as readiness


DATE = "20260809"
ROLE = "v24971_readiness_armed_exact220_preregistration"
PROTOCOL_ID = "v24971_readiness_armed_v24857_exact220_v1"
PROTOCOL = Path(f"results/v24971_readiness_armed_exact220_preregistration_v1_{DATE}.json")
PREAUDIT = Path(f"results/v24971_readiness_armed_exact220_preactivation_audit_v1_{DATE}.json")
ARMED_RECEIPT = Path(f"results/v24971_readiness_armed_exact220_armed_receipt_v1_{DATE}.json")
EXECUTION_START = Path(f"results/v24971_readiness_armed_exact220_execution_start_v1_{DATE}.json")
FORWARD_RESULT = Path(f"results/v24971_readiness_armed_exact220_forward_result_v1_{DATE}.json")
FORWARD_AUDIT = Path(f"results/v24971_readiness_armed_exact220_forward_audit_v1_{DATE}.json")
OUTPUT_ROOT = Path(f"outputs/v24971_readiness_armed_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
KEY_SLOT_DIRECTORY = OUTPUT_ROOT / "tavily_key_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = algorithm.LEASE_PATH
LEASE_OWNER = "v24971_readiness_armed_exact220_forward_v1"
LEASE_PURPOSE = "same_process_readiness_then_label_blind_exact220"
RUNNER_MARKER = "scripts/run_v24971_readiness_armed_exact220.py"
CHILD_MARKER = "scripts/run_v24971_readiness_armed_exact220_task.py"
DIRECT_RECEIPT_NAME = algorithm.DIRECT_RECEIPT_NAME
RATE_RECEIPT_NAME = algorithm.RATE_RECEIPT_NAME
PACING_RECEIPT_NAME = algorithm.PACING_RECEIPT_NAME
AUTHORIZATION_WAIT_SECONDS = 1800

PREAUDIT_AUTHORIZATION = {
    "same_process_readiness_arming": True,
    "execution_start_generation": False,
    "single_fresh_exact220_forward": False,
    "evaluator_call": False,
    "retry_resume_skip_or_selective_rerun": False,
}
ARMED_AUTHORIZATION = {
    "execution_start_generation": True,
    "single_fresh_exact220_forward": False,
    "evaluator": False,
    "retry_resume_skip_or_selective_rerun": False,
}
START_AUTHORIZATION = {
    "single_fresh_exact220_forward": True,
    "evaluator_call": False,
    "retry_resume_skip_or_selective_rerun": False,
}
START_CHECK_KEYS = {
    "armed_receipt_commit_pushed",
    "arming_git_head_is_ancestor_of_armed_commit",
    "authorization_deadline_open",
    "conflicting_process_pids_empty_except_bound_runner",
    "execution_surface_pristine",
    "gpt56_endpoint_reachable_without_provider_request",
    "protected_watchers_unchanged",
    "runner_command_marker_matches",
    "runner_pid_start_ticks_live",
    "shared_api_lease_held_by_bound_runner",
}

SELECTED_COUNT = algorithm.SELECTED_COUNT
EXECUTOR_CONCURRENCY = algorithm.EXECUTOR_CONCURRENCY
MODEL_SLOT_CAP = algorithm.MODEL_SLOT_CAP
TAVILY_KEY_SLOT_CAP = algorithm.TAVILY_KEY_SLOT_CAP
LIMITS = copy.deepcopy(algorithm.LIMITS)
MODEL = copy.deepcopy(algorithm.MODEL)
SEARCH = copy.deepcopy(algorithm.SEARCH)
TWO_WAVE_POLICY = copy.deepcopy(algorithm.TWO_WAVE_POLICY)
PROTECTED_WATCHERS = algorithm.PROTECTED_WATCHERS
PARENT_PROTOCOL = algorithm.PROTOCOL
TRANSPORT_SOURCE = algorithm.TRANSPORT_SOURCE
TRANSPORT_TEST = algorithm.TRANSPORT_TEST
ADMISSION_SOURCE = algorithm.ADMISSION_SOURCE
ADMISSION_TEST = algorithm.ADMISSION_TEST
READINESS_SOURCE = Path("src/deepwide_agent/v24970_same_process_search_readiness.py")
READINESS_TEST = Path("tests/test_v24970_same_process_search_readiness.py")
SOURCE = Path("src/deepwide_agent/v24971_readiness_armed_exact220_contract.py")
CONTROL = Path("scripts/control_v24971_readiness_armed_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24971_readiness_armed_exact220.py")
TEST = Path("tests/test_v24971_readiness_armed_exact220.py")
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)

payload_sha256 = algorithm.payload_sha256
sha256 = algorithm.sha256


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.49.71 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.71 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def protected_watcher_snapshot(proc_root: Path = Path("/proc")) -> list[dict[str, Any]]:
    return algorithm.protected_watcher_snapshot(proc_root)


@lru_cache(maxsize=2)
def _cached_parent_contract(
    root_string: str, parent_protocol_sha256: str
) -> dict[str, Any]:
    del parent_protocol_sha256
    root = Path(root_string)
    return algorithm.validate_protocol(root, _read(root / PARENT_PROTOCOL))


def parent_contract(root: Path) -> dict[str, Any]:
    resolved = root.resolve()
    return copy.deepcopy(
        _cached_parent_contract(
            str(resolved), sha256(resolved / PARENT_PROTOCOL)
        )
    )


def _task_contract(tasks: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "runtime_input_keys": ["opaque_id", "question"],
        "selected_count": SELECTED_COUNT,
        "opaque_id_vector_sha256": payload_sha256([task["opaque_id"] for task in tasks]),
        "visible_question_vector_sha256": payload_sha256([task["question"] for task in tasks]),
    }


@lru_cache(maxsize=2)
def _cached_task_vector(
    root_string: str, parent_protocol_sha256: str
) -> tuple[tuple[str, str], ...]:
    del parent_protocol_sha256
    tasks = algorithm.task_vector(Path(root_string))
    if len(tasks) != 220 or any(set(task) != {"opaque_id", "question"} for task in tasks):
        raise RuntimeError("V2.49.71 visible exact-220 vector drifted")
    return tuple((task["opaque_id"], task["question"]) for task in tasks)


def task_vector(root: Path, protocol: Mapping[str, Any] | None = None) -> list[dict[str, str]]:
    tasks = [
        {"opaque_id": opaque_id, "question": question}
        for opaque_id, question in _cached_task_vector(
            str(root.resolve()), sha256(root.resolve() / PARENT_PROTOCOL)
        )
    ]
    if protocol is not None and protocol.get("task_contract") != _task_contract(tasks):
        raise RuntimeError("V2.49.71 visible task binding drifted")
    return tasks


def dependency_manifest(root: Path, *, require_tracked: bool = True) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update((PARENT_PROTOCOL, READINESS_SOURCE, READINESS_TEST))
    relatives.update(LOCAL_SOURCES)
    return {
        str(relative): sha256(
            algorithm._ordinary_tracked(root, relative)
            if require_tracked
            else (root / relative)
        )
        for relative in sorted(relatives, key=str)
    }


def rate_policy() -> dict[str, Any]:
    return copy.deepcopy(algorithm.rate_policy())


def pacing_policy() -> dict[str, Any]:
    return copy.deepcopy(algorithm.pacing_policy())


def readiness_policy() -> dict[str, Any]:
    return {
        "policy_id": readiness.POLICY_ID,
        "ephemeral_key_count": readiness.EXPECTED_KEY_COUNT,
        "executor_concurrency": readiness.EXECUTOR_CONCURRENCY,
        "attempts_per_key": readiness.ATTEMPTS_PER_KEY,
        "results_per_query": readiness.RESULTS_PER_QUERY,
        "per_key_deadline_seconds": readiness.DEADLINE_SECONDS,
        "neutral_query_sha256": payload_sha256(readiness.NEUTRAL_QUERY),
        "all_keys_require_2xx_and_nonempty_url_lead": True,
        "same_process_same_memory_pool_handoff": True,
        "receipt_alone_authorizes_benchmark_forward": False,
        "credential_value_or_hash_persisted": False,
        "authorization_wait_seconds": AUTHORIZATION_WAIT_SECONDS,
    }


def _algorithm_equality() -> dict[str, bool]:
    values = {
        "selected_count_equal_v24857": SELECTED_COUNT == algorithm.SELECTED_COUNT == 220,
        "executor_concurrency_equal_v24857": EXECUTOR_CONCURRENCY == algorithm.EXECUTOR_CONCURRENCY == 20,
        "model_slot_cap_equal_v24857": MODEL_SLOT_CAP == algorithm.MODEL_SLOT_CAP == 8,
        "tavily_key_slot_cap_equal_v24857": TAVILY_KEY_SLOT_CAP == algorithm.TAVILY_KEY_SLOT_CAP == 12,
        "limits_equal_v24857": LIMITS == algorithm.LIMITS,
        "model_equal_v24857": MODEL == algorithm.MODEL,
        "search_equal_v24857": SEARCH == algorithm.SEARCH,
        "two_wave_policy_equal_v24857": TWO_WAVE_POLICY == algorithm.TWO_WAVE_POLICY,
        "rate_policy_equal_v24857": rate_policy() == algorithm.rate_policy(),
        "pacing_policy_equal_v24857": pacing_policy() == algorithm.pacing_policy(),
    }
    if not all(values.values()):
        raise RuntimeError("V2.49.71 frozen algorithm equality drifted")
    return values


def build_protocol(
    root: Path,
    *,
    now: int,
    require_clean: bool = True,
    require_pristine: bool = True,
) -> dict[str, Any]:
    git = algorithm._git
    if require_clean and (
        git(root, "status", "--porcelain")
        or git(root, "rev-parse", "HEAD") != git(root, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.49.71 protocol requires clean pushed HEAD")
    future = (
        PROTOCOL,
        PREAUDIT,
        ARMED_RECEIPT,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        OUTPUT_ROOT,
    )
    if require_pristine and any((root / path).exists() or (root / path).is_symlink() for path in future):
        raise FileExistsError("V2.49.71 future surface exists")
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root, require_tracked=require_clean)
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "git_head": git(root, "rev-parse", "HEAD") if require_clean else "build-only",
        "parent_algorithm": {
            "path": str(PARENT_PROTOCOL),
            "sha256": sha256(root / PARENT_PROTOCOL),
            "protocol_id": base["protocol_id"],
            "dependency_manifest_sha256": base["dependency_manifest_sha256"],
            "prior_output_prediction_result_score_or_evaluator_read_or_reused": False,
        },
        "neutral_transport_gate": copy.deepcopy(base["neutral_transport_gate"]),
        "fixed_full_budget_control_gate": copy.deepcopy(base["fixed_full_budget_control_gate"]),
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
            "readiness_policy": readiness_policy(),
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "key_slot_directory": str(KEY_SLOT_DIRECTORY),
            "single_fresh_forward_no_retry_resume_or_selective_rerun": True,
        },
        "single_change": {
            "fresh_execution_and_artifact_surfaces_only": True,
            "algorithm_equality": _algorithm_equality(),
            "same_process_pre_start_search_readiness_handoff_added": True,
            "additional_benchmark_search_fetch_model_token_context_or_wall_cap": False,
            "entropy_or_information_gain_assigns_credit_or_routes": False,
        },
        "dependency_manifest": manifest,
        "dependency_manifest_sha256": payload_sha256(manifest),
        "source_policy": {
            "runtime_reads_only_opaque_id_and_question_after_start": True,
            "readiness_uses_only_fixed_neutral_query": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward_or_readiness": False,
            "prior_benchmark_prediction_result_score_or_evaluator_opened_or_hashed": False,
            "credential_values_stdin_memory_only_not_persisted_hashed_or_emitted": True,
            "fixed_public_exact220_task_set_reexecuted": True,
            "new_or_disjoint_task_population_claimed": False,
            "cross_version_public_benchmark_feedback_overfitting_remains_a_limitation": True,
        },
        "authorization": {
            "preactivation_audit_generation": True,
            "same_process_readiness_arming": False,
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
    change = copied.get("single_change") or {}
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
        or copied.get("fixed_full_budget_control_gate") != base["fixed_full_budget_control_gate"]
        or copied.get("task_contract") != _task_contract(tasks)
        or copied.get("dependency_manifest") != manifest
        or copied.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or execution.get("executor_concurrency") != 20
        or execution.get("model_slot_cap") != 8
        or execution.get("tavily_key_slot_cap") != 12
        or execution.get("task_wall_seconds") != 240
        or execution.get("model_calls_per_task") != 3
        or execution.get("search_queries_per_task") != 4
        or execution.get("fetch_targets_per_task") != 10
        or execution.get("model") != MODEL
        or execution.get("search") != SEARCH
        or execution.get("two_wave_policy") != TWO_WAVE_POLICY
        or execution.get("rate_policy") != rate_policy()
        or execution.get("pacing_admission_policy") != pacing_policy()
        or execution.get("readiness_policy") != readiness_policy()
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("key_slot_directory") != str(KEY_SLOT_DIRECTORY)
        or change.get("algorithm_equality") != _algorithm_equality()
        or change.get("same_process_pre_start_search_readiness_handoff_added") is not True
        or change.get("additional_benchmark_search_fetch_model_token_context_or_wall_cap") is not False
        or copied.get("source_policy", {}).get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read_by_forward_or_readiness"
        )
        is not False
        or copied.get("authorization")
        != {
            "preactivation_audit_generation": True,
            "same_process_readiness_arming": False,
            "execution_start_generation": False,
            "single_fresh_exact220_forward": False,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
    ):
        raise RuntimeError("V2.49.71 protocol drifted")
    task_vector(root, copied)
    return copied


def validate_preaudit(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    protocol = validate_protocol(root, _read(root / PROTOCOL))
    if (
        copied.get("role") != "v24971_readiness_armed_exact220_preactivation_audit"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(root / PROTOCOL)
        or copied.get("dependency_manifest_sha256") != protocol["dependency_manifest_sha256"]
        or copied.get("audit_valid") is not True
        or copied.get("findings") != []
        or copied.get("tests", {}).get("passed") is not True
        or copied.get("label_blind_audit", {}).get("passed") is not True
        or copied.get("runtime_state", {}).get(
            "gpt56_endpoint_reachable_without_provider_request"
        )
        is not True
        or copied.get("runtime_state", {}).get("shared_api_lease_inactive") is not True
        or copied.get("runtime_state", {}).get("conflicting_process_pids") != []
        or copied.get("runtime_state", {}).get("protected_watchers")
        != protocol["execution"]["protected_watchers"]
        or copied.get("runtime_state", {}).get("future_surface_pristine") is not True
        or copied.get("runtime_state", {}).get("armed_surface_pristine") is not True
        or copied.get("readiness_policy") != readiness_policy()
        or copied.get("authorization") != PREAUDIT_AUTHORIZATION
        or not _sealed(copied, "audit_payload_sha256")
    ):
        raise RuntimeError("V2.49.71 preactivation audit drifted")
    return copied


def proc_start_ticks(pid: int, proc_root: Path = Path("/proc")) -> int:
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("V2.49.71 process id is invalid")
    text = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
    close = text.rfind(")")
    if close < 0:
        raise RuntimeError("V2.49.71 process stat is invalid")
    fields = text[close + 2 :].split()
    if len(fields) < 20:
        raise RuntimeError("V2.49.71 process stat is truncated")
    return int(fields[19])


def process_matches(pid: int, start_ticks: int, proc_root: Path = Path("/proc")) -> bool:
    try:
        return proc_start_ticks(pid, proc_root) == start_ticks
    except (OSError, RuntimeError, TypeError, ValueError):
        return False


def build_armed_receipt(
    root: Path,
    readiness_receipt: Mapping[str, Any],
    *,
    pid: int,
    start_ticks: int,
    arming_git_head: str,
    now: int,
) -> dict[str, Any]:
    protocol = validate_protocol(root, _read(root / PROTOCOL))
    validate_preaudit(root, _read(root / PREAUDIT))
    checked = readiness.validate_receipt(readiness_receipt)
    if checked["passed"] is not True:
        raise RuntimeError("V2.49.71 unhealthy readiness cannot arm a benchmark")
    if pid != os.getpid() or not process_matches(pid, start_ticks):
        raise RuntimeError("V2.49.71 armed receipt must bind its creating process")
    git = algorithm._git
    head = git(root, "rev-parse", "HEAD")
    if (
        arming_git_head != head
        or head != git(root, "rev-parse", "target/main")
        or git(root, "status", "--porcelain")
    ):
        raise RuntimeError("V2.49.71 arming requires a clean pushed HEAD")
    if (root / ARMED_RECEIPT).exists() or (root / ARMED_RECEIPT).is_symlink():
        raise FileExistsError("V2.49.71 armed receipt surface exists")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24971_readiness_armed_exact220_armed_receipt",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(now),
        "authorization_deadline_unix": int(now) + AUTHORIZATION_WAIT_SECONDS,
        "protocol_sha256": sha256(root / PROTOCOL),
        "preactivation_audit_sha256": sha256(root / PREAUDIT),
        "dependency_manifest_sha256": protocol["dependency_manifest_sha256"],
        "arming_git_head": str(arming_git_head),
        "runner": {
            "pid": int(pid),
            "start_ticks": int(start_ticks),
            "marker": RUNNER_MARKER,
        },
        "readiness": checked,
        "readiness_receipt_payload_sha256": checked["receipt_payload_sha256"],
        "status": "armed_waiting_execution_start",
        "protected_watchers": protected_watcher_snapshot(),
        "benchmark_output_root_created": False,
        "benchmark_question_prediction_mapping_gold_evaluator_score_reward_read": False,
        "credential_value_or_hash_persisted_emitted_or_logged": False,
        "authorization": copy.deepcopy(ARMED_AUTHORIZATION),
    }
    value["armed_receipt_payload_sha256"] = payload_sha256(value)
    return validate_armed_receipt(root, value)


def validate_armed_receipt(root: Path, value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    protocol = validate_protocol(root, _read(root / PROTOCOL))
    validate_preaudit(root, _read(root / PREAUDIT))
    inner = readiness.validate_receipt(copied.get("readiness") or {})
    runner = copied.get("runner") or {}
    if (
        copied.get("role") != "v24971_readiness_armed_exact220_armed_receipt"
        or copied.get("protocol_id") != PROTOCOL_ID
        or copied.get("protocol_sha256") != sha256(root / PROTOCOL)
        or copied.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or copied.get("dependency_manifest_sha256") != protocol["dependency_manifest_sha256"]
        or copied.get("authorization_deadline_unix")
        != copied.get("created_at_unix", -AUTHORIZATION_WAIT_SECONDS) + AUTHORIZATION_WAIT_SECONDS
        or not isinstance(copied.get("arming_git_head"), str)
        or len(copied["arming_git_head"]) != 40
        or isinstance(runner.get("pid"), bool)
        or not isinstance(runner.get("pid"), int)
        or runner["pid"] <= 0
        or isinstance(runner.get("start_ticks"), bool)
        or not isinstance(runner.get("start_ticks"), int)
        or runner["start_ticks"] <= 0
        or runner.get("marker") != RUNNER_MARKER
        or copied.get("readiness_receipt_payload_sha256") != inner["receipt_payload_sha256"]
        or inner["passed"] is not True
        or copied.get("status") != "armed_waiting_execution_start"
        or copied.get("protected_watchers") != protocol["execution"]["protected_watchers"]
        or copied.get("benchmark_output_root_created") is not False
        or copied.get("benchmark_question_prediction_mapping_gold_evaluator_score_reward_read") is not False
        or copied.get("credential_value_or_hash_persisted_emitted_or_logged") is not False
        or copied.get("authorization") != ARMED_AUTHORIZATION
        or not _sealed(copied, "armed_receipt_payload_sha256")
    ):
        raise RuntimeError("V2.49.71 armed receipt drifted")
    return copied


def validate_execution_start(
    root: Path,
    protocol: Mapping[str, Any],
    *,
    now: int | None = None,
    require_current_runner: bool = True,
) -> dict[str, Any]:
    checked_protocol = validate_protocol(root, protocol)
    armed = validate_armed_receipt(root, _read(root / ARMED_RECEIPT))
    start = _read(root / EXECUTION_START)
    runner = armed["runner"]
    observed_now = int(time.time()) if now is None else int(now)
    checks = start.get("checks") or {}
    if (
        start.get("role") != "v24971_readiness_armed_exact220_execution_start"
        or start.get("protocol_id") != PROTOCOL_ID
        or start.get("status") != "authorized_not_started"
        or start.get("protocol_sha256") != sha256(root / PROTOCOL)
        or start.get("preactivation_audit_sha256") != sha256(root / PREAUDIT)
        or start.get("armed_receipt_sha256") != sha256(root / ARMED_RECEIPT)
        or start.get("armed_receipt_payload_sha256") != armed["armed_receipt_payload_sha256"]
        or start.get("readiness_receipt_payload_sha256") != armed["readiness_receipt_payload_sha256"]
        or start.get("dependency_manifest_sha256") != checked_protocol["dependency_manifest_sha256"]
        or start.get("runner") != runner
        or start.get("session_nonce") != armed["readiness"]["session_nonce"]
        or not isinstance(start.get("authorization_parent_git_head"), str)
        or len(start["authorization_parent_git_head"]) != 40
        or start.get("created_at_unix", -1) < armed.get("created_at_unix", 0)
        or start.get("created_at_unix", 0) > armed.get("authorization_deadline_unix", -1)
        or observed_now > armed.get("authorization_deadline_unix", -1)
        or start.get("selected") != 220
        or start.get("executor_concurrency") != 20
        or start.get("model_slot_cap") != 8
        or start.get("tavily_key_slot_cap") != 12
        or start.get("protected_watchers") != checked_protocol["execution"]["protected_watchers"]
        or start.get("findings") != []
        or set(checks) != START_CHECK_KEYS
        or not all(value is True for value in checks.values())
        or start.get("first_benchmark_model_search_fetch_effect_started") is not False
        or start.get("credential_value_or_hash_persisted_emitted_or_logged") is not False
        or start.get("authorization") != START_AUTHORIZATION
        or not _sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.49.71 execution start drifted")
    if require_current_runner and (
        os.getpid() != runner["pid"]
        or not process_matches(runner["pid"], runner["start_ticks"])
    ):
        raise RuntimeError("V2.49.71 execution start is not bound to this live runner")
    return start


__all__ = [name for name in globals() if name.isupper()] + [
    "build_armed_receipt",
    "build_protocol",
    "dependency_manifest",
    "pacing_policy",
    "parent_contract",
    "payload_sha256",
    "proc_start_ticks",
    "process_matches",
    "protected_watcher_snapshot",
    "rate_policy",
    "readiness_policy",
    "sha256",
    "task_vector",
    "validate_armed_receipt",
    "validate_execution_start",
    "validate_preaudit",
    "validate_protocol",
]
