"""Fresh exact-220 successor changing only the Tavily rate transport.

The public 220-vector, prompts, GPT-5.6 model, hard budgets, fixed full-budget
controller, projection, and concurrency are inherited from V2.48.50/V2.48.00.
The only algorithmic change is the append-only V2.48.52 provider-wide pacing
and cooldown layer, admitted by the neutral V2.48.53 transport gate.
"""

from __future__ import annotations

import copy
import functools
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import v24850_v24800_replication_exact220_contract as parent
from . import v24852_rate_aware_tavily_search as rate_transport


DATE = "20260808"
ROLE = "v24854_rate_aware_exact220_preregistration"
PROTOCOL_ID = "v24854_rate_aware_fixed_full_budget_exact220_v1"
PROTOCOL = Path(
    f"results/v24854_rate_aware_exact220_preregistration_v1_{DATE}.json"
)
PREAUDIT = Path(
    f"results/v24854_rate_aware_exact220_preactivation_audit_v1_{DATE}.json"
)
EXECUTION_START = Path(
    f"results/v24854_rate_aware_exact220_execution_start_v1_{DATE}.json"
)
FORWARD_RESULT = Path(
    f"results/v24854_rate_aware_exact220_forward_result_v1_{DATE}.json"
)
FORWARD_AUDIT = Path(
    f"results/v24854_rate_aware_exact220_forward_audit_v1_{DATE}.json"
)
OUTPUT_ROOT = Path(f"outputs/v24854_rate_aware_exact220_v1_{DATE}")
MODEL_SLOT_DIRECTORY = OUTPUT_ROOT / "model_slots"
KEY_SLOT_DIRECTORY = OUTPUT_ROOT / "tavily_key_slots"
TASK_ROOT = OUTPUT_ROOT / "tasks"
RUNTIME_PREDICTIONS = OUTPUT_ROOT / "runtime_predictions.jsonl"
RUN_SUMMARY = OUTPUT_ROOT / "run_summary.json"
PREDICTION_FREEZE = OUTPUT_ROOT / "prediction_freeze.json"
SAFE_PROGRESS = OUTPUT_ROOT / "safe_forward_progress.json"
LEASE_PATH = parent.LEASE_PATH
LEASE_OWNER = "v24854_rate_aware_exact220_forward_v1"
LEASE_PURPOSE = "fresh_label_blind_rate_aware_fixed_full_budget_exact220"
RUNNER_MARKER = "scripts/run_v24854_rate_aware_exact220.py"
CHILD_MARKER = "scripts/run_v24854_rate_aware_exact220_task.py"
DIRECT_RECEIPT_NAME = parent.DIRECT_RECEIPT_NAME
RATE_RECEIPT_NAME = "rate_aware_search_receipt.json"

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
TRANSPORT_GATE_PROTOCOL = Path(
    "results/v24853_rate_aware_transport_smoke_preregistration_v1_20260808.json"
)
TRANSPORT_GATE_RESULT = Path(
    "results/v24853_rate_aware_transport_smoke_result_v1_20260808.json"
)
TRANSPORT_SOURCE = Path(
    "src/deepwide_agent/v24852_rate_aware_tavily_search.py"
)
TRANSPORT_TEST = Path("tests/test_v24852_rate_aware_tavily_search.py")
SOURCE = Path(
    "src/deepwide_agent/v24854_rate_aware_exact220_contract.py"
)
CONTROL = Path("scripts/control_v24854_rate_aware_exact220.py")
RUNNER = Path(RUNNER_MARKER)
CHILD = Path(CHILD_MARKER)
FINALIZER = Path("scripts/finalize_v24854_rate_aware_exact220.py")
TEST = Path("tests/test_v24854_rate_aware_exact220.py")
LOCAL_SOURCES = (SOURCE, CONTROL, RUNNER, CHILD, FINALIZER, TEST)

payload_sha256 = parent.payload_sha256
sha256 = parent.sha256
_git = parent._git
_ordinary_tracked = parent._ordinary_tracked


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.48.54 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.54 expected JSON object")
    return value


def _sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


@functools.lru_cache(maxsize=2)
def _parent_contract_cached(
    root_text: str, protocol_sha256: str
) -> dict[str, Any]:
    root = Path(root_text)
    if sha256(root / PARENT_PROTOCOL) != protocol_sha256:
        raise RuntimeError("V2.48.54 parent protocol changed during validation")
    return parent.validate_protocol(root, _read(root / PARENT_PROTOCOL))


def parent_contract(root: Path) -> dict[str, Any]:
    resolved = root.resolve()
    value = _parent_contract_cached(
        str(resolved), sha256(resolved / PARENT_PROTOCOL)
    )
    return copy.deepcopy(value)


def validate_transport_gate(root: Path) -> dict[str, Any]:
    protocol = _read(root / TRANSPORT_GATE_PROTOCOL)
    result = _read(root / TRANSPORT_GATE_RESULT)
    rate = rate_transport.validate_receipt(result.get("rate_aware_receipt") or {})
    direct = result.get("rate_aware_direct_search_receipt") or {}
    observed = result.get("rate_aware_transport_aggregate") or {}
    if (
        protocol.get("role")
        != "v24853_rate_aware_transport_smoke_preregistration"
        or protocol.get("authorization", {}).get(
            "one_neutral_old_vs_rate_aware_live_smoke"
        )
        is not True
        or protocol.get("authorization", {}).get("exact220_launch") is not False
        or not _sealed(protocol, "protocol_payload_sha256")
        or result.get("role") != "v24853_rate_aware_transport_smoke_result"
        or result.get("protocol_sha256") != sha256(root / TRANSPORT_GATE_PROTOCOL)
        or result.get("passed") is not True
        or result.get("authorization", {}).get("exact220_protocol_design")
        is not True
        or result.get("authorization", {}).get("exact220_launch") is not False
        or observed.get("search_query_rows") != 4
        or observed.get("successful_query_rows") != 4
        or observed.get("failed_query_rows") != 0
        or direct.get("slot_timeouts") != 0
        or direct.get("credential_echo_rejections") != 0
        or rate.get("provider_wide_429_rotates_all_keys_immediately") is not False
        or rate.get(
            "provider_non_key_local_attempt_cap_per_logical_query"
        )
        != rate_transport.DEFAULT_PROVIDER_ATTEMPT_CAP
        or not _sealed(result, "result_payload_sha256")
    ):
        raise RuntimeError("V2.48.54 neutral transport gate drifted")
    return {
        "protocol_path": str(TRANSPORT_GATE_PROTOCOL),
        "protocol_sha256": sha256(root / TRANSPORT_GATE_PROTOCOL),
        "result_path": str(TRANSPORT_GATE_RESULT),
        "result_sha256": sha256(root / TRANSPORT_GATE_RESULT),
        "result_payload_sha256": result["result_payload_sha256"],
        "successful_query_rows": observed["successful_query_rows"],
        "failed_query_rows": observed["failed_query_rows"],
        "provider_429_responses": rate["provider_429_responses"],
        "provider_wide_429_rotates_all_keys_immediately": False,
    }


def protected_watcher_snapshot(
    proc_root: Path = Path("/proc"),
) -> list[dict[str, Any]]:
    return parent.protected_watcher_snapshot(proc_root)


@functools.lru_cache(maxsize=2)
def _task_vector_cached(
    root_text: str, parent_protocol_sha256: str
) -> tuple[tuple[str, str], ...]:
    root = Path(root_text)
    tasks = parent.task_vector(root, parent_contract(root))
    if len(tasks) != SELECTED_COUNT or any(
        set(task) != {"opaque_id", "question"} for task in tasks
    ):
        raise RuntimeError("V2.48.54 visible exact-220 vector drifted")
    return tuple((task["opaque_id"], task["question"]) for task in tasks)


def task_vector(
    root: Path, protocol: Mapping[str, Any] | None = None
) -> list[dict[str, str]]:
    resolved = root.resolve()
    rows = _task_vector_cached(
        str(resolved), sha256(resolved / PARENT_PROTOCOL)
    )
    tasks = [
        {"opaque_id": opaque_id, "question": question}
        for opaque_id, question in rows
    ]
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
            raise RuntimeError("V2.48.54 visible task binding drifted")
    return tasks


def rate_policy() -> dict[str, Any]:
    return {
        "transport_class": "RateAwareDeadlineTavilyThinCompatibilityClient",
        "provider_non_key_local_attempt_cap_per_logical_query": (
            rate_transport.DEFAULT_PROVIDER_ATTEMPT_CAP
        ),
        "minimum_start_interval_seconds": (
            rate_transport.DEFAULT_MINIMUM_START_INTERVAL_SECONDS
        ),
        "default_provider_cooldown_seconds": (
            rate_transport.DEFAULT_PROVIDER_COOLDOWN_SECONDS
        ),
        "maximum_provider_cooldown_seconds": (
            rate_transport.DEFAULT_MAXIMUM_COOLDOWN_SECONDS
        ),
        "provider_wide_429_rotates_all_keys_immediately": False,
        "credential_local_statuses": [401, 403, 432],
        "provider_answer_snippet_raw_content_or_score_forwarded": False,
    }


def dependency_manifest(root: Path) -> dict[str, str]:
    base = parent_contract(root)
    relatives = {Path(name) for name in base["dependency_manifest"]}
    relatives.update(
        (
            PARENT_PROTOCOL,
            TRANSPORT_GATE_PROTOCOL,
            TRANSPORT_GATE_RESULT,
            TRANSPORT_SOURCE,
            TRANSPORT_TEST,
        )
    )
    relatives.update(LOCAL_SOURCES)
    return {
        str(relative): sha256(_ordinary_tracked(root, relative))
        for relative in sorted(relatives, key=str)
    }


def _parent_equalities() -> dict[str, bool]:
    values = {
        "selected_count_equal_v24850": SELECTED_COUNT == parent.SELECTED_COUNT,
        "executor_concurrency_equal_v24850": (
            EXECUTOR_CONCURRENCY == parent.EXECUTOR_CONCURRENCY
        ),
        "model_slot_cap_equal_v24850": MODEL_SLOT_CAP == parent.MODEL_SLOT_CAP,
        "tavily_key_slot_cap_equal_v24850": (
            TAVILY_KEY_SLOT_CAP == parent.TAVILY_KEY_SLOT_CAP
        ),
        "limits_equal_v24850": LIMITS == parent.LIMITS,
        "model_equal_v24850": MODEL == parent.MODEL,
        "search_budget_and_projection_equal_v24850": SEARCH == parent.SEARCH,
        "two_wave_policy_equal_v24850": TWO_WAVE_POLICY == parent.TWO_WAVE_POLICY,
    }
    if not all(values.values()):
        raise RuntimeError("V2.48.54 parent equality drifted")
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
        raise RuntimeError("V2.48.54 protocol requires clean pushed HEAD")
    future = (
        PROTOCOL,
        PREAUDIT,
        EXECUTION_START,
        FORWARD_RESULT,
        FORWARD_AUDIT,
        OUTPUT_ROOT,
    )
    if require_pristine and any(
        (root / path).exists() or (root / path).is_symlink()
        for path in future
    ):
        raise FileExistsError("V2.48.54 future surface exists")
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
        "neutral_transport_gate": validate_transport_gate(root),
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
            "protected_watchers": protected_watcher_snapshot(),
            "output_root": str(OUTPUT_ROOT),
            "key_slot_directory": str(KEY_SLOT_DIRECTORY),
            "single_fresh_forward_no_retry_resume_or_selective_rerun": True,
        },
        "single_change": {
            "old_transport": "DeadlineTavilyThinCompatibilityClient",
            "new_transport": "RateAwareDeadlineTavilyThinCompatibilityClient",
            "provider_wide_pacing_cooldown_and_attempt_cap_only": True,
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


def validate_protocol(
    root: Path, value: Mapping[str, Any]
) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("protocol_payload_sha256", None)
    base = parent_contract(root)
    tasks = task_vector(root)
    manifest = dependency_manifest(root)
    execution = copied.get("execution") or {}
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
        or copied.get("neutral_transport_gate") != validate_transport_gate(root)
        or copied.get("fixed_full_budget_control_gate")
        != base["fixed_full_budget_control_gate"]
        or copied.get("task_contract")
        != {
            "runtime_input_keys": ["opaque_id", "question"],
            "selected_count": SELECTED_COUNT,
            "opaque_id_vector_sha256": payload_sha256(
                [task["opaque_id"] for task in tasks]
            ),
            "visible_question_vector_sha256": payload_sha256(
                [task["question"] for task in tasks]
            ),
        }
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
        or execution.get("protected_watchers") != protected_watcher_snapshot()
        or execution.get("output_root") != str(OUTPUT_ROOT)
        or execution.get("key_slot_directory") != str(KEY_SLOT_DIRECTORY)
        or copied.get("single_change")
        != {
            "old_transport": "DeadlineTavilyThinCompatibilityClient",
            "new_transport": "RateAwareDeadlineTavilyThinCompatibilityClient",
            "provider_wide_pacing_cooldown_and_attempt_cap_only": True,
            "parent_equalities": _parent_equalities(),
            "fresh_execution_and_artifact_surfaces": True,
        }
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
        raise RuntimeError("V2.48.54 protocol drifted")
    task_vector(root, copied)
    return copied


__all__ = [name for name in globals() if name.isupper()] + [
    "build_protocol",
    "dependency_manifest",
    "parent_contract",
    "payload_sha256",
    "protected_watcher_snapshot",
    "rate_policy",
    "sha256",
    "task_vector",
    "validate_protocol",
    "validate_transport_gate",
]
