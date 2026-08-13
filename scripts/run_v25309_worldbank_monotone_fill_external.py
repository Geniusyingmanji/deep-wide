#!/usr/bin/env python3
"""Run the single authorized fresh12 World Bank monotone-fill mechanism gate."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
import re
import socket
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25309_worldbank_monotone_fill_external_contract as contract  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import coarse_exception_type  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
    validate_receipt as validate_model_slot_receipt,
)
from deepwide_agent.v24468_total_wall_transport import HardTotalWallResponsesClient  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


runtime = contract.runtime
TASK_ROLE = "v25309_worldbank_monotone_fill_task_result"
FORWARD_ROLE = "v25309_worldbank_monotone_fill_forward_result"
FREEZE_ROLE = "v25309_worldbank_monotone_fill_prediction_freeze"
CLAIM_ROLE = "v25309_worldbank_monotone_fill_attempt_claim"


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.53.09 expected a JSON object")
    return value


def _publish_json(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _publish_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_progress(completed: int) -> None:
    value = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25309_worldbank_monotone_fill_safe_progress",
            "created_at_unix": int(time.time()),
            "selected": contract.TASK_COUNT,
            "completed": int(completed),
            "unfinished": contract.TASK_COUNT - int(completed),
            "contains_question_query_url_page_value_prediction_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "progress_payload_sha256",
    )
    path = ROOT / contract.SAFE_PROGRESS
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _clean_pushed() -> None:
    if (
        contract.git(ROOT, "status", "--porcelain")
        or contract.git(ROOT, "rev-parse", "HEAD")
        != contract.git(ROOT, "rev-parse", "target/main")
    ):
        raise RuntimeError("V2.53.09 forward requires clean pushed HEAD")


def _lease_inactive() -> bool:
    path = ROOT / contract.LEASE_PATH
    if path.is_symlink():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return True
    except (BlockingIOError, OSError):
        return False


def _active_conflicts() -> list[int]:
    completed = subprocess.run(
        ["ps", "-eo", "pid=,comm=,args="],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=False,
    )
    markers = (str(contract.RUNNER), "scripts/run_official_eval_local.py")
    output: list[int] = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if (
            len(parts) >= 3
            and int(parts[0]) != os.getpid()
            and "python" in parts[1].casefold()
            and any(marker in parts[2] for marker in markers)
        ):
            output.append(int(parts[0]))
    return sorted(output)


def execution_start_commit_boundary(
    start: Mapping[str, Any], *, current_head: str, current_target: str
) -> bool:
    try:
        parent_row = contract.git(
            ROOT, "rev-list", "--parents", "-n", "1", current_head
        ).split()
        changed = sorted(
            line.strip()
            for line in contract.git(
                ROOT, "diff-tree", "--no-commit-id", "--name-only", "-r", current_head
            ).splitlines()
            if line.strip()
        )
    except BaseException:
        return False
    return bool(
        current_head == current_target
        and len(parent_row) == 2
        and parent_row[0] == current_head
        and parent_row[1] == start.get("git_head")
        and changed == [str(contract.EXECUTION_START)]
    )


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    current_head = contract.git(ROOT, "rev-parse", "HEAD")
    current_target = contract.git(ROOT, "rev-parse", "target/main")
    if (
        set(start)
        != {
            "artifact_version", "role", "protocol_id", "status", "created_at_unix",
            "git_head", "protocol_sha256", "preactivation_audit_sha256",
            "source_manifest", "task_vector_sha256", "page_vector_sha256",
            "selected", "executor_concurrency", "model_slot_cap", "runtime_input_contract",
            "physical_caps", "mechanism_gate", "protected_watchers", "findings",
            "authorization", "execution_start_payload_sha256",
        }
        or start.get("artifact_version") != 1
        or start.get("role") != "v25310_worldbank_monotone_fill_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("status") != "authorized_not_started"
        or re.fullmatch(r"[0-9a-f]{40}", str(start.get("git_head"))) is None
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256") != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("source_manifest") != protocol["source_manifest"]
        or {
            path: contract.sha256(contract.ordinary(ROOT, Path(path), tracked=True))
            for path in protocol["source_manifest"]
        }
        != dict(protocol["source_manifest"])
        or start.get("task_vector_sha256") != contract.TASK_VECTOR_SHA256
        or start.get("page_vector_sha256") != contract.RENDERED_PAGES_SHA256
        or start.get("selected") != contract.TASK_COUNT
        or start.get("executor_concurrency") != contract.EXECUTOR_CONCURRENCY
        or start.get("model_slot_cap") != contract.MODEL_SLOT_CAP
        or start.get("runtime_input_contract") != ["opaque_id", "question"]
        or start.get("physical_caps") != contract.PHYSICAL_CAPS
        or start.get("mechanism_gate") != contract.mechanism_gate()
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("findings") != []
        or start.get("authorization")
        != {
            "single_fresh12_worldbank_monotone_fill_forward": True,
            "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        }
        or not execution_start_commit_boundary(
            start, current_head=current_head, current_target=current_target
        )
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.53.09 execution start drifted")
    return protocol, start


def _prepare_output() -> None:
    root = ROOT / contract.OUTPUT_ROOT
    root.mkdir(parents=True, mode=0o700, exist_ok=False)
    slots = ROOT / contract.MODEL_SLOT_DIRECTORY
    slots.mkdir(mode=0o700)
    for index in range(1, contract.MODEL_SLOT_CAP + 1):
        _publish_json(
            slots / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
                "role": "v25309_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_task_content": False,
            },
        )


def build_attempt_claim(
    protocol: Mapping[str, Any], start: Mapping[str, Any], *, now: int | None = None
) -> dict[str, Any]:
    checked = contract.validate_protocol(ROOT, protocol)
    if (
        start.get("role") != "v25310_worldbank_monotone_fill_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise ValueError("V2.53.09 attempt claim start drifted")
    return contract.seal(
        {
            "artifact_version": 1,
            "role": CLAIM_ROLE,
            "created_at_unix": int(time.time()) if now is None else int(now),
            "protocol_id": contract.PROTOCOL_ID,
            "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "execution_start_payload_sha256": start["execution_start_payload_sha256"],
            "source_manifest": copy.deepcopy(checked["source_manifest"]),
            "task_vector_sha256": contract.TASK_VECTOR_SHA256,
            "page_vector_sha256": contract.RENDERED_PAGES_SHA256,
            "selected": contract.TASK_COUNT,
            "attempt_authority_consumed_before_endpoint_model_or_output_effect": True,
            "retry_resume_skip_backfill_replacement_selective_rerun_or_second_attempt": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "postfreeze_evaluator": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        },
        "claim_payload_sha256",
    )


def validate_attempt_claim(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        set(copied)
        != {
            "artifact_version", "role", "created_at_unix", "protocol_id",
            "protocol_sha256", "execution_start_sha256", "execution_start_payload_sha256",
            "source_manifest", "task_vector_sha256", "page_vector_sha256", "selected",
            "attempt_authority_consumed_before_endpoint_model_or_output_effect",
            "retry_resume_skip_backfill_replacement_selective_rerun_or_second_attempt",
            "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit", "postfreeze_evaluator",
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota", "claim_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != CLAIM_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("task_vector_sha256") != contract.TASK_VECTOR_SHA256
        or copied.get("page_vector_sha256") != contract.RENDERED_PAGES_SHA256
        or copied.get("selected") != contract.TASK_COUNT
        or copied.get("attempt_authority_consumed_before_endpoint_model_or_output_effect") is not True
        or any(
            copied.get(name) is not False
            for name in (
                "retry_resume_skip_backfill_replacement_selective_rerun_or_second_attempt",
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit", "postfreeze_evaluator",
                "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota",
            )
        )
        or not contract.sealed(copied, "claim_payload_sha256")
    ):
        raise ValueError("V2.53.09 attempt claim drifted")
    return copied


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _model_cost(result: Mapping[str, Any]) -> dict[str, int]:
    cost = (result.get("candidate_result") or {}).get("cost") or {}
    model = cost.get("model") or {}
    return {
        "requests": int(model.get("requests", 0) or 0),
        "attempts": int(model.get("attempts", 0) or 0),
        "input_tokens": int(model.get("input_tokens", 0) or 0),
        "output_tokens": int(model.get("output_tokens", 0) or 0),
        "total_tokens": int(model.get("total_tokens", 0) or 0),
        "system_total_tokens": int(cost.get("system_total_tokens", 0) or 0),
    }


def _from_runtime(task: Mapping[str, str], result: Mapping[str, Any], elapsed: float) -> dict[str, Any]:
    checked = runtime.validate_result(result)
    paired = checked["content_free_paired_receipt"]
    integration = checked["candidate_result"]["monotone_unknown_fill_receipt"]
    core = integration["monotone_unknown_fill_receipt"]
    parent_prediction = checked["parent_envelope"]["result"]["prediction"]
    candidate_prediction = checked["candidate_result"]["prediction"]
    row: dict[str, Any] = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "opaque_id": str(task["opaque_id"]),
        "status": "terminal",
        "runtime_completed": True,
        "failure_as_zero": False,
        "outer_failure_type": None,
        "prediction_kind": str(checked["candidate_result"]["completion_kind"]),
        "parent_prediction": parent_prediction,
        "candidate_prediction": candidate_prediction,
        "parent_prediction_sha256": _sha256(parent_prediction),
        "candidate_prediction_sha256": _sha256(candidate_prediction),
        "paired_runtime_result": copy.deepcopy(checked),
        "paired_runtime_result_payload_sha256": str(checked["result_payload_sha256"]),
        "content_free_paired_receipt": copy.deepcopy(paired),
        "content_free_integration_receipt": copy.deepcopy(integration),
        "content_free_core_receipt": copy.deepcopy(core),
        "candidate_model_slot_receipt": copy.deepcopy(
            checked["candidate_final_model_slot_receipt"]
        ),
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "cost": _model_cost(checked),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "evaluator_or_quality_metric_called": False,
    }
    row["task_payload_sha256"] = contract.payload_sha256(row)
    return validate_task_row(row)


def _terminal_outer_failure(
    task: Mapping[str, str], error: BaseException, elapsed: float, model: Any
) -> dict[str, Any]:
    receipt = None
    if isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        try:
            receipt = model.receipt()
        except BaseException:
            receipt = None
    row: dict[str, Any] = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "opaque_id": str(task["opaque_id"]),
        "status": "terminal",
        "runtime_completed": False,
        "failure_as_zero": True,
        "outer_failure_type": coarse_exception_type(error),
        "prediction_kind": "failure_as_zero",
        "parent_prediction": None,
        "candidate_prediction": None,
        "parent_prediction_sha256": None,
        "candidate_prediction_sha256": None,
        "paired_runtime_result": None,
        "paired_runtime_result_payload_sha256": None,
        "content_free_paired_receipt": None,
        "content_free_integration_receipt": None,
        "content_free_core_receipt": None,
        "candidate_model_slot_receipt": receipt,
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "cost": None,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "evaluator_or_quality_metric_called": False,
    }
    row["task_payload_sha256"] = contract.payload_sha256(row)
    return validate_task_row(row)


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    signature = unsigned.pop("task_payload_sha256", None)
    completed = copied.get("runtime_completed") is True
    paired = copied.get("content_free_paired_receipt")
    integration = copied.get("content_free_integration_receipt")
    core = copied.get("content_free_core_receipt")
    slot = copied.get("candidate_model_slot_receipt")
    if (
        set(copied)
        != {
            "artifact_version", "role", "opaque_id", "status", "runtime_completed",
            "failure_as_zero", "outer_failure_type", "prediction_kind", "parent_prediction",
            "candidate_prediction", "parent_prediction_sha256", "candidate_prediction_sha256",
            "paired_runtime_result", "paired_runtime_result_payload_sha256",
            "content_free_paired_receipt", "content_free_integration_receipt",
            "content_free_core_receipt", "candidate_model_slot_receipt", "elapsed_seconds",
            "cost", "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
            "entropy_or_information_gain_assigns_signed_credit", "evaluator_or_quality_metric_called",
            "task_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != TASK_ROLE
        or re.fullmatch(r"task_[0-9a-f]{24}", str(copied.get("opaque_id"))) is None
        or copied.get("status") != "terminal"
        or not isinstance(copied.get("runtime_completed"), bool)
        or not isinstance(copied.get("failure_as_zero"), bool)
        or copied.get("failure_as_zero") is completed
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or not math.isfinite(float(copied["elapsed_seconds"]))
        or copied["elapsed_seconds"] < 0
        or any(
            copied.get(name) is not False
            for name in (
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
                "entropy_or_information_gain_assigns_signed_credit",
                "evaluator_or_quality_metric_called",
            )
        )
        or signature != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.53.09 task row drifted")
    if completed:
        if (
            copied.get("outer_failure_type") is not None
            or not isinstance(copied.get("paired_runtime_result"), Mapping)
            or runtime.validate_result(copied["paired_runtime_result"])
            != dict(copied["paired_runtime_result"])
            or copied.get("paired_runtime_result_payload_sha256")
            != copied["paired_runtime_result"]["result_payload_sha256"]
            or not isinstance(paired, Mapping)
            or runtime.validate_paired_receipt(paired) != dict(paired)
            or not isinstance(integration, Mapping)
            or runtime.candidate.validate_integration_receipt(integration)
            != dict(integration)
            or not isinstance(core, Mapping)
            or runtime.candidate.core.validate_receipt(core) != dict(core)
            or integration["monotone_unknown_fill_receipt"] != core
            or copied["paired_runtime_result"]["content_free_paired_receipt"] != paired
            or copied["paired_runtime_result"]["candidate_result"]["monotone_unknown_fill_receipt"]
            != integration
            or not isinstance(slot, Mapping)
            or validate_model_slot_receipt(slot, expected_cap=contract.MODEL_SLOT_CAP)
            != dict(slot)
            or copied.get("parent_prediction")
            != copied["paired_runtime_result"]["parent_envelope"]["result"]["prediction"]
            or copied.get("candidate_prediction")
            != copied["paired_runtime_result"]["candidate_result"]["prediction"]
            or copied.get("parent_prediction_sha256") != _sha256(copied["parent_prediction"])
            or copied.get("candidate_prediction_sha256") != _sha256(copied["candidate_prediction"])
            or copied.get("prediction_kind")
            != copied["paired_runtime_result"]["candidate_result"]["completion_kind"]
            or not isinstance(copied.get("cost"), Mapping)
        ):
            raise ValueError("V2.53.09 completed task row drifted")
    elif (
        not isinstance(copied.get("outer_failure_type"), str)
        or not copied["outer_failure_type"]
        or copied.get("prediction_kind") != "failure_as_zero"
        or any(
            copied.get(name) is not None
            for name in (
                "parent_prediction", "candidate_prediction", "parent_prediction_sha256",
                "candidate_prediction_sha256", "paired_runtime_result",
                "paired_runtime_result_payload_sha256", "content_free_paired_receipt",
                "content_free_integration_receipt", "content_free_core_receipt", "cost",
            )
        )
        or slot is not None
        and validate_model_slot_receipt(slot, expected_cap=contract.MODEL_SLOT_CAP)
        != dict(slot)
    ):
        raise ValueError("V2.53.09 failure-as-zero task row drifted")
    return copied


def run_one_task(task: Mapping[str, str], pages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.53.09 runtime input must be opaque_id and question")
    started = time.monotonic()
    model: Any = None
    try:
        deadline = started + float(contract.LIMITS["wall_seconds"])
        inner = HardTotalWallResponsesClient(
            contract.MODEL["proxy_url"],
            contract.MODEL["name"],
            reasoning_effort=contract.MODEL["reasoning_effort"],
            service_tier=contract.MODEL["service_tier"],
            timeout=contract.MODEL["timeout_seconds"],
            max_retries=contract.MODEL["max_retries"],
            absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
            stage_callback=lambda _event: None,
        )
        model = DeadlineAwareGlobalModelSlotLimiter(
            inner,
            slot_directory=ROOT / contract.MODEL_SLOT_DIRECTORY,
            output_root=ROOT / contract.OUTPUT_ROOT,
            slot_cap=contract.MODEL_SLOT_CAP,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
        search = runtime.FrozenWorldBankSnapshotSearchClient(
            pages, absolute_deadline=deadline, monotonic=time.monotonic
        )
        result = runtime.run_paired_task(
            task,
            model=model,
            search=search,
            limits=ScoreFirstLimits(**contract.LIMITS),
            two_wave_policy=TwoWavePolicy(**contract.TWO_WAVE_POLICY),
            monotonic=time.monotonic,
        )
        return _from_runtime(task, result, time.monotonic() - started)
    except BaseException as exc:
        return _terminal_outer_failure(task, exc, time.monotonic() - started, model)


_AGGREGATE_INTS = (
    "task_count", "terminal_tasks", "completed_runtime_tasks", "failure_as_zero_tasks",
    "model_generated_tasks", "fallback_tasks", "parent_two_call_baseline_unknown_tasks",
    "complete_eight_page_prefix_tasks", "revision_prompt_within_cap_tasks",
    "third_slot_proposal_tasks", "supported_unknown_fill_tasks",
    "supported_unknown_fill_cells", "attributable_prediction_change_tasks",
    "query_effect_equal_tasks", "fetch_effect_equal_tasks",
    "total_model_calls_at_most_three_tasks", "known_cell_schema_row_key_order_or_count_violation_tasks",
    "unsupported_or_conflicting_admitted_fill_cells", "physical_queries", "physical_fetches",
    "physical_model_forwards", "maximum_queries_on_one_task", "maximum_fetches_on_one_task",
    "maximum_model_forwards_on_one_task", "model_requests", "model_attempts",
    "input_tokens", "output_tokens", "system_total_tokens", "positive_signed_credit_count",
)


def validate_aggregate(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    false_names = {
        "contains_question_query_url_page_value_answer_prediction_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit", "evaluator_or_quality_metric_called",
    }
    if (
        set(copied) != {*_AGGREGATE_INTS, "batch_wall_seconds", *false_names}
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in _AGGREGATE_INTS
        )
        or isinstance(copied.get("batch_wall_seconds"), bool)
        or not isinstance(copied.get("batch_wall_seconds"), (int, float))
        or not math.isfinite(float(copied["batch_wall_seconds"]))
        or copied["batch_wall_seconds"] < 0
        or any(copied.get(name) is not False for name in false_names)
        or copied["task_count"] != contract.TASK_COUNT
        or copied["terminal_tasks"] != contract.TASK_COUNT
        or copied["completed_runtime_tasks"] + copied["failure_as_zero_tasks"]
        != copied["terminal_tasks"]
        or copied["model_generated_tasks"] + copied["fallback_tasks"]
        != copied["terminal_tasks"]
        or any(copied[name] > copied["completed_runtime_tasks"] for name in (
            "parent_two_call_baseline_unknown_tasks", "complete_eight_page_prefix_tasks",
            "revision_prompt_within_cap_tasks", "third_slot_proposal_tasks",
            "supported_unknown_fill_tasks", "attributable_prediction_change_tasks",
            "query_effect_equal_tasks", "fetch_effect_equal_tasks",
            "total_model_calls_at_most_three_tasks",
        ))
        or copied["supported_unknown_fill_tasks"] > copied["supported_unknown_fill_cells"]
        or copied["attributable_prediction_change_tasks"] != copied["supported_unknown_fill_tasks"]
        or copied["physical_queries"] > contract.TASK_COUNT * contract.PHYSICAL_CAPS["queries_per_task"]
        or copied["physical_fetches"] > contract.TASK_COUNT * contract.PHYSICAL_CAPS["fetches_per_task"]
        or copied["physical_model_forwards"] > contract.TASK_COUNT * contract.PHYSICAL_CAPS["model_forwards_per_task"]
        or copied["maximum_queries_on_one_task"] > contract.PHYSICAL_CAPS["queries_per_task"]
        or copied["maximum_fetches_on_one_task"] > contract.PHYSICAL_CAPS["fetches_per_task"]
        or copied["maximum_model_forwards_on_one_task"] > contract.PHYSICAL_CAPS["model_forwards_per_task"]
        or copied["positive_signed_credit_count"] != 0
    ):
        raise ValueError("V2.53.09 aggregate drifted")
    return copied


def aggregate_rows(rows: Sequence[Mapping[str, Any]], *, wall_seconds: float) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    tasks = contract.task_vector(ROOT)
    if (
        len(checked) != contract.TASK_COUNT
        or [row["opaque_id"] for row in checked] != [task["opaque_id"] for task in tasks]
    ):
        raise RuntimeError("V2.53.09 fixed task vector drifted")
    completed = [row for row in checked if row["runtime_completed"]]
    paired = [row["content_free_paired_receipt"] for row in completed]
    integrations = [row["content_free_integration_receipt"] for row in completed]
    cores = [row["content_free_core_receipt"] for row in completed]
    value = {
        "task_count": contract.TASK_COUNT,
        "terminal_tasks": len(checked),
        "completed_runtime_tasks": len(completed),
        "failure_as_zero_tasks": sum(row["failure_as_zero"] for row in checked),
        "model_generated_tasks": sum(
            row["runtime_completed"]
            and row["prediction_kind"]
            in {"primary", "repaired", "normalized_primary", "normalized_repaired"}
            for row in checked
        ),
        "fallback_tasks": sum(
            not row["runtime_completed"]
            or row["prediction_kind"]
            not in {"primary", "repaired", "normalized_primary", "normalized_repaired"}
            for row in checked
        ),
        "parent_two_call_baseline_unknown_tasks": sum(
            receipt["logical_parent_model_calls"] == 2
            and receipt["baseline_unknown_cell_count"] > 0
            for receipt in integrations
        ),
        "complete_eight_page_prefix_tasks": sum(
            receipt["complete_same_forward_page_prefix"] is True
            and receipt["same_forward_page_count"] == runtime.PAGE_COUNT
            for receipt in integrations
        ),
        "revision_prompt_within_cap_tasks": sum(
            receipt["revision_prompt_within_parent_cap"] for receipt in integrations
        ),
        "third_slot_proposal_tasks": sum(
            receipt["logical_revision_call_admitted"]
            and receipt["proposal_returned"]
            and not receipt["proposal_truncated"]
            for receipt in integrations
        ),
        "supported_unknown_fill_tasks": sum(
            receipt["admitted_unknown_fill_count"] > 0 for receipt in cores
        ),
        "supported_unknown_fill_cells": sum(
            receipt["admitted_unknown_fill_count"] for receipt in cores
        ),
        "attributable_prediction_change_tasks": sum(
            receipt["candidate_prediction_changed"]
            and receipt["supported_unknown_fill_count"] > 0
            for receipt in paired
        ),
        "query_effect_equal_tasks": sum(
            receipt["query_effect_shared_and_candidate_additional_query_count"] == 0
            for receipt in paired
        ),
        "fetch_effect_equal_tasks": sum(
            receipt["fetch_effect_shared_and_candidate_additional_fetch_count"] == 0
            for receipt in paired
        ),
        "total_model_calls_at_most_three_tasks": sum(
            receipt["final_logical_model_calls"] <= 3 for receipt in paired
        ),
        "known_cell_schema_row_key_order_or_count_violation_tasks": sum(
            receipt["known_cells_schema_row_keys_order_and_count_immutable"] is not True
            or core["baseline_known_cells_preserved"] is not True
            or core["baseline_row_keys_order_count_and_schema_preserved"] is not True
            for receipt, core in zip(paired, cores, strict=True)
        ),
        "unsupported_or_conflicting_admitted_fill_cells": sum(
            count
            for receipt in cores
            for support, count in receipt[
                "admitted_supporting_page_count_distribution"
            ].items()
            if int(support) < receipt["minimum_supporting_pages"]
        ),
        "physical_queries": sum(receipt["physical_query_count"] for receipt in paired),
        "physical_fetches": sum(receipt["physical_fetch_count"] for receipt in paired),
        "physical_model_forwards": sum(receipt["final_logical_model_calls"] for receipt in paired),
        "maximum_queries_on_one_task": max((receipt["physical_query_count"] for receipt in paired), default=0),
        "maximum_fetches_on_one_task": max((receipt["physical_fetch_count"] for receipt in paired), default=0),
        "maximum_model_forwards_on_one_task": max((receipt["final_logical_model_calls"] for receipt in paired), default=0),
        "model_requests": sum(int(row["cost"]["requests"]) for row in completed),
        "model_attempts": sum(int(row["cost"]["attempts"]) for row in completed),
        "input_tokens": sum(int(row["cost"]["input_tokens"]) for row in completed),
        "output_tokens": sum(int(row["cost"]["output_tokens"]) for row in completed),
        "system_total_tokens": sum(int(row["cost"]["system_total_tokens"]) for row in completed),
        "positive_signed_credit_count": 0,
        "batch_wall_seconds": round(max(0.0, float(wall_seconds)), 6),
        "contains_question_query_url_page_value_answer_prediction_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "evaluator_or_quality_metric_called": False,
    }
    return validate_aggregate(value)


def mechanism_decision(aggregate: Mapping[str, Any]) -> dict[str, Any]:
    checked = validate_aggregate(aggregate)
    gate = contract.mechanism_gate()
    checks = {
        "fixed_terminal_denominator": checked["task_count"] == checked["terminal_tasks"] == gate["fixed_task_denominator"],
        "minimum_parent_two_call_baseline_unknown_tasks": checked["parent_two_call_baseline_unknown_tasks"] >= gate["minimum_parent_two_call_baseline_unknown_tasks"],
        "minimum_complete_eight_page_prefix_tasks": checked["complete_eight_page_prefix_tasks"] >= gate["minimum_complete_eight_page_prefix_tasks"],
        "minimum_revision_prompt_within_cap_tasks": checked["revision_prompt_within_cap_tasks"] >= gate["minimum_revision_prompt_within_cap_tasks"],
        "minimum_third_slot_proposal_tasks": checked["third_slot_proposal_tasks"] >= gate["minimum_third_slot_proposal_tasks"],
        "minimum_supported_unknown_fill_tasks": checked["supported_unknown_fill_tasks"] >= gate["minimum_supported_unknown_fill_tasks"],
        "minimum_supported_unknown_fill_cells": checked["supported_unknown_fill_cells"] >= gate["minimum_supported_unknown_fill_cells"],
        "minimum_attributable_prediction_change_tasks": checked["attributable_prediction_change_tasks"] >= gate["minimum_attributable_prediction_change_tasks"],
        "all_query_effects_equal": checked["query_effect_equal_tasks"] == gate["required_query_effect_equal_tasks"],
        "all_fetch_effects_equal": checked["fetch_effect_equal_tasks"] == gate["required_fetch_effect_equal_tasks"],
        "all_model_calls_within_cap": checked["total_model_calls_at_most_three_tasks"] == gate["required_total_model_calls_at_most_three_tasks"],
        "known_cell_schema_row_key_order_or_count_violation_zero": checked["known_cell_schema_row_key_order_or_count_violation_tasks"] <= gate["maximum_known_cell_schema_row_key_order_or_count_violation_tasks"],
        "unsupported_or_conflicting_admitted_fill_zero": checked["unsupported_or_conflicting_admitted_fill_cells"] <= gate["maximum_unsupported_or_conflicting_admitted_fill_cells"],
        "physical_caps_preserved": checked["physical_queries"] <= gate["maximum_queries_total"] and checked["physical_fetches"] <= gate["maximum_fetches_total"] and checked["physical_model_forwards"] <= gate["maximum_model_forwards_total"],
        "positive_signed_credit_zero": checked["positive_signed_credit_count"] == gate["positive_signed_credit_count"],
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    return {
        "checks": checks,
        "failed_checks": failed,
        "mechanism_gate_passed": not failed,
        "postfreeze_evaluator_after_pushed_forward_audit": not failed,
        "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
        "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
    }


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    decision = copied.get("mechanism_decision")
    if (
        set(copied)
        != {
            "artifact_version", "role", "protocol_id", "created_at_unix",
            "execution_start_sha256", "attempt_claim_sha256", "task_rows_sha256",
            "prediction_freeze_sha256", "aggregate", "mechanism_decision",
            "authorization", "result_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != FORWARD_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or any(re.fullmatch(r"[0-9a-f]{64}", str(copied.get(name))) is None for name in (
            "execution_start_sha256", "attempt_claim_sha256", "task_rows_sha256", "prediction_freeze_sha256"
        ))
        or not isinstance(aggregate, Mapping)
        or validate_aggregate(aggregate) != dict(aggregate)
        or decision != mechanism_decision(aggregate)
        or copied.get("authorization")
        != {
            "forward_audit": True,
            "postfreeze_evaluator_after_pushed_forward_audit": bool(decision and decision["mechanism_gate_passed"]),
            "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
            "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
        }
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise ValueError("V2.53.09 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if not _lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.53.09 shared runtime is not ready")
    future = (
        contract.ATTEMPT_CLAIM, contract.FORWARD_RESULT, contract.FORWARD_AUDIT,
        contract.OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.53.09 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        raise RuntimeError("V2.53.09 protected watcher identity drifted")
    population = contract.frozen_population(ROOT)
    claim = build_attempt_claim(protocol, start)
    _publish_json(ROOT / contract.ATTEMPT_CLAIM, claim)
    validate_attempt_claim(_read(contract.ATTEMPT_CLAIM, tracked=False))
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    _prepare_output()
    started = time.monotonic()
    values: list[dict[str, Any] | None] = [None] * contract.TASK_COUNT
    with acquire_deepwide_api_lease(
        ROOT, owner=contract.LEASE_OWNER, purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = {
                pool.submit(run_one_task, task, population["pages"]): index
                for index, task in enumerate(population["tasks"])
            }
            completed = 0
            for future in as_completed(futures):
                index = futures[future]
                values[index] = validate_task_row(future.result())
                completed += 1
                _atomic_progress(completed)
    rows = [validate_task_row(row) for row in values if row is not None]
    if len(rows) != contract.TASK_COUNT:
        raise RuntimeError("V2.53.09 terminal denominator drifted")
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    aggregate = aggregate_rows(rows, wall_seconds=time.monotonic() - started)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": FREEZE_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected": contract.TASK_COUNT,
            "terminal": contract.TASK_COUNT,
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "parent_prediction_hash_vector_sha256": contract.payload_sha256(
                [row["parent_prediction_sha256"] for row in rows]
            ),
            "candidate_prediction_hash_vector_sha256": contract.payload_sha256(
                [row["candidate_prediction_sha256"] for row in rows]
            ),
            "paired_runtime_result_hash_vector_sha256": contract.payload_sha256(
                [row["paired_runtime_result_payload_sha256"] for row in rows]
            ),
            "all_predictions_and_results_terminal_before_evaluator": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        },
        "freeze_payload_sha256",
    )
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    decision = mechanism_decision(aggregate)
    forward = contract.seal(
        {
            "artifact_version": 1,
            "role": FORWARD_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "execution_start_sha256": contract.sha256(ROOT / contract.EXECUTION_START),
            "attempt_claim_sha256": contract.sha256(ROOT / contract.ATTEMPT_CLAIM),
            "task_rows_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
            "aggregate": aggregate,
            "mechanism_decision": decision,
            "authorization": {
                "forward_audit": True,
                "postfreeze_evaluator_after_pushed_forward_audit": decision["mechanism_gate_passed"],
                "retry_resume_skip_backfill_replacement_or_selective_rerun": False,
                "deepwidebench_dev64_exact220_avg4_leaderboard_or_sota": False,
            },
        },
        "result_payload_sha256",
    )
    _publish_json(ROOT / contract.FORWARD_RESULT, forward)
    return validate_forward_result(forward)


def main() -> None:
    value = run_forward()
    print(json.dumps({
        "path": str(contract.FORWARD_RESULT),
        "aggregate": value["aggregate"],
        "mechanism_decision": value["mechanism_decision"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
