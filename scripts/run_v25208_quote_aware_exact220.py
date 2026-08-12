#!/usr/bin/env python3
"""Run one atomic label-blind V2.52.08 DeepWideBench exact-220 forward."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v25110_exact_visible_schema as visible_schema,
)
from deepwide_agent import (  # noqa: E402
    v25192_content_free_outer_failure_observer as failure_observer,
)
from deepwide_agent import (  # noqa: E402
    v25193_failure_observable_execution as staged_execution,
)
from deepwide_agent import (  # noqa: E402
    v25197_vertical_receipt_failure_probe as failure_probe,
)
from deepwide_agent import (  # noqa: E402
    v25200_post_effect_tolerant_vertical_receipt as compatibility,
)
from deepwide_agent import (  # noqa: E402
    v25208_quote_aware_exact220_contract as contract,
)
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24468_total_wall_transport import (  # noqa: E402
    HardTotalWallResponsesClient,
)
from deepwide_agent.v24985_robust_late_page_fetch import (  # noqa: E402
    validate_search_class,
)
from scripts import run_v25206_cran_dcf_quality as parent  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


TASK_ROLE = "v25208_quote_aware_exact220_task_result"
_APPLICATIONS: dict[str, bool] = {}
_APPLICATION_LOCK = threading.Lock()


def _bind_parent() -> None:
    parent.contract = contract
    parent.TASK_ROLE = TASK_ROLE
    parent._bind_parent()


_bind_parent()
runtime = contract.runtime
accounting = parent.accounting
failure_parent = parent.parent.parent


def _read(relative: Path, *, tracked: bool = True) -> dict[str, Any]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.52.08 expected JSON object")
    return value


def _read_jsonl(relative: Path, *, tracked: bool = False) -> list[dict[str, Any]]:
    path = contract.ordinary(ROOT, relative, tracked=tracked)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.52.08 expected JSONL objects")
    return rows


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
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _atomic_progress(completed: int) -> None:
    value = contract.seal(
        {
            "artifact_version": 1,
            "role": "v25208_quote_aware_exact220_safe_progress",
            "created_at_unix": int(time.time()),
            "selected": contract.TASK_COUNT,
            "completed": int(completed),
            "unfinished": contract.TASK_COUNT - int(completed),
            "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
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
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.52.08 forward requires clean pushed HEAD")


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
    markers = (contract.RUNNER_MARKER, "scripts/run_official_eval_local.py")
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


def _validate_start() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = contract.validate_protocol(ROOT, _read(contract.PROTOCOL))
    start = _read(contract.EXECUTION_START)
    expected_authorization = {
        "single_exact220_forward": True,
        "postfreeze_official_evaluator": False,
        "retry_resume_skip_or_selective_rerun": False,
        "leaderboard_or_sota": False,
    }
    if (
        start.get("role") != "v25208_quote_aware_exact220_execution_start"
        or start.get("protocol_id") != contract.PROTOCOL_ID
        or start.get("status") != "authorized_not_started"
        or start.get("protocol_sha256") != contract.sha256(ROOT / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(ROOT / contract.PREAUDIT)
        or start.get("selected") != contract.TASK_COUNT
        or start.get("executor_concurrency") != contract.EXECUTOR_CONCURRENCY
        or start.get("model_slot_cap") != contract.MODEL_SLOT_CAP
        or start.get("runtime_input_contract") != ["opaque_id", "question"]
        or start.get("protected_watchers") != contract.watcher_snapshot()
        or start.get("findings") != []
        or start.get("authorization") != expected_authorization
        or not contract.sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.52.08 execution start drifted")
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
                "role": "v25208_model_slot",
                "slot": index,
                "slot_cap": contract.MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def _visible_fallback(question: str) -> str:
    columns = visible_schema.extract_exact_visible_columns(question)
    if not columns:
        columns = ["Unknown"]
    return (
        "```markdown\n| "
        + " | ".join(columns)
        + " |\n| "
        + " | ".join("---" for _ in columns)
        + " |\n| "
        + " | ".join("Unknown" for _ in columns)
        + " |\n```"
    )


def _terminal_outer_failure(
    task: Mapping[str, str],
    observation: Mapping[str, Any],
    elapsed: float,
    health: Mapping[str, int] | None = None,
    actual_effect_snapshot: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    observed = failure_observer.validate_observation(observation)
    fallback = _visible_fallback(str(task["question"]))
    value = {
        "artifact_version": 1,
        "role": TASK_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "opaque_id": str(task["opaque_id"]),
        "runtime_input_keys": ["opaque_id", "question", "same_forward_public_pages"],
        "terminal": True,
        "runtime_completed": False,
        "failure_as_zero": True,
        "failure_observation": copy.deepcopy(observed),
        "predictions": {arm: fallback for arm in contract.ARMS},
        "prediction_sha256": {
            arm: hashlib.sha256(fallback.encode()).hexdigest()
            for arm in contract.ARMS
        },
        "prediction_kind": "fallback",
        "failure_types": None,
        "parent_result": None,
        "parent_result_payload_sha256": None,
        "cost": None,
        "content_free_receipt": None,
        "runtime_result_payload_sha256": None,
        "elapsed_seconds": round(max(0.0, float(elapsed)), 6),
        "effect_health": accounting._health(health),
        "actual_effect_snapshot": accounting._validate_actual_effect_snapshot(
            actual_effect_snapshot or accounting._actual_effect_snapshot(None, {})
        ),
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "retry_resume_skip_population_replacement_or_selective_rerun": False,
        "contains_question_query_url_title_page_target_authority_column_or_credential_outside_frozen_predictions": False,
    }
    return contract.seal(value, "result_payload_sha256")


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    _bind_parent()
    parent._ensure_compatibility_validation()
    return parent.validate_task_row(value)


def run_one_task(task: Mapping[str, str]) -> dict[str, Any]:
    if set(task) != {"opaque_id", "question"}:
        raise ValueError("V2.52.08 runtime input must be opaque_id and question")
    _bind_parent()
    compatibility_token = compatibility.begin_task()
    probe_token = failure_probe.begin_task()
    started = time.monotonic()
    model: Any = None
    searches: dict[str, Any] = {}

    def runtime_stage() -> dict[str, Any]:
        nonlocal model, searches
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
        model = accounting._EffectAccountingModelSlotLimiter(
            inner,
            slot_directory=ROOT / contract.MODEL_SLOT_DIRECTORY,
            output_root=ROOT / contract.OUTPUT_ROOT,
            slot_cap=contract.MODEL_SLOT_CAP,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=contract.CLEANUP_RESERVE_SECONDS,
            minimum_attempt_seconds=contract.MINIMUM_MODEL_ATTEMPT_SECONDS,
        )
        searches = {
            phase: failure_parent._search(str(task["question"]), deadline)
            for phase in runtime.PHASES
        }
        return runtime.run_task(
            task,
            model=model,
            searches=searches,
            limits=ScoreFirstLimits(**contract.LIMITS),
            monotonic=time.monotonic,
        )

    def conversion_stage(result: Mapping[str, Any]) -> dict[str, Any]:
        return parent._from_runtime(
            task,
            result,
            time.monotonic() - started,
            accounting._health_snapshot(model, searches),
            accounting._actual_effect_snapshot(model, searches),
        )

    def terminal_factory(observation: Mapping[str, Any]) -> dict[str, Any]:
        return _terminal_outer_failure(
            task,
            observation,
            time.monotonic() - started,
            accounting._health_snapshot(model, searches),
            accounting._actual_effect_snapshot(model, searches),
        )

    try:
        row = staged_execution.execute_staged_once(
            runtime_stage=runtime_stage,
            conversion_stage=conversion_stage,
            row_validation_stage=validate_task_row,
            terminal_failure_factory=terminal_factory,
        )
        observation = failure_probe.failure_observation()
        with parent.parent._OBSERVATION_LOCK:
            parent.parent._OBSERVATIONS[str(task["opaque_id"])] = copy.deepcopy(
                observation
            )
        applied = compatibility.compatibility_applied()
        with _APPLICATION_LOCK:
            _APPLICATIONS[str(task["opaque_id"])] = applied
        return validate_task_row(row)
    finally:
        failure_probe.end_task(probe_token)
        compatibility.end_task(compatibility_token)


def _summary(
    rows: Sequence[Mapping[str, Any]], aggregate: Mapping[str, Any]
) -> dict[str, Any]:
    checked = [validate_task_row(row) for row in rows]
    value = {
        "artifact_version": 1,
        "role": contract.SUMMARY_ROLE,
        "protocol_id": contract.PROTOCOL_ID,
        "selected": contract.TASK_COUNT,
        "completed": contract.TASK_COUNT,
        "failed": 0,
        "runtime_completed": int(aggregate["completed_runtime_tasks"]),
        "failure_as_zero_tasks": int(aggregate["failure_as_zero_tasks"]),
        "model_generated_tables": int(aggregate["model_generated_tasks"]),
        "fallback_tables": contract.TASK_COUNT
        - int(aggregate["model_generated_tasks"]),
        "same_raw_counterfactual_active_tasks": int(
            aggregate["same_raw_counterfactual_active_tasks"]
        ),
        "prediction_changed_tasks": int(aggregate["prediction_changed_tasks"]),
        "system_total_tokens": int(aggregate["system_total_tokens"]),
        "forward_wall_seconds": float(aggregate["batch_wall_seconds"]),
        "official_evaluator_called": False,
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "positive_signed_credit_count": 0,
    }
    return contract.seal(value, "summary_payload_sha256")


def validate_summary(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    if (
        copied.get("role") != contract.SUMMARY_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("selected") != contract.TASK_COUNT
        or copied.get("completed") != contract.TASK_COUNT
        or copied.get("failed") != 0
        or copied.get("model_generated_tables", -1)
        + copied.get("fallback_tables", -1)
        != contract.TASK_COUNT
        or copied.get("positive_signed_credit_count") != 0
        or copied.get("official_evaluator_called") is not False
        or not contract.sealed(copied, "summary_payload_sha256")
    ):
        raise RuntimeError("V2.52.08 run summary drifted")
    return copied


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    aggregate = copied.get("aggregate")
    if (
        copied.get("role") != contract.FORWARD_ROLE
        or copied.get("protocol_id") != contract.PROTOCOL_ID
        or copied.get("selected") != contract.TASK_COUNT
        or copied.get("terminal_predictions") != contract.TASK_COUNT
        or copied.get("model_generated_tables", -1)
        + copied.get("fallback_tables", -1)
        != contract.TASK_COUNT
        or not isinstance(aggregate, Mapping)
        or parent.validate_aggregate(aggregate) != dict(aggregate)
        or copied.get("mechanism_decision") != parent.mechanism_decision(aggregate)
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_read")
        is not False
        or copied.get("official_evaluator_called") is not False
        or copied.get("retry_resume_skip_or_selective_rerun_launched") is not False
        or copied.get("positive_signed_credit_count") != 0
        or not contract.sealed(copied, "result_payload_sha256")
    ):
        raise RuntimeError("V2.52.08 forward result drifted")
    return copied


def run_forward() -> dict[str, Any]:
    _clean_pushed()
    protocol, start = _validate_start()
    if not parent._lease_inactive() or _active_conflicts():
        raise RuntimeError("V2.52.08 shared runtime is not ready")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    future = (
        contract.FORWARD_RESULT,
        contract.FORWARD_AUDIT,
        contract.EVALUATOR_PROTOCOL,
        contract.RESULT,
        contract.POSTAUDIT,
        contract.OUTPUT_ROOT,
    )
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in future):
        raise RuntimeError("V2.52.08 forward surface is not pristine")
    if contract.watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        raise RuntimeError("V2.52.08 protected watcher identity drifted")
    validate_search_class()
    parent.install_runtime_observers()
    tasks = contract.task_vector(ROOT, protocol)
    _prepare_output()
    with parent.parent._OBSERVATION_LOCK:
        parent.parent._OBSERVATIONS.clear()
    with _APPLICATION_LOCK:
        _APPLICATIONS.clear()
    started = time.monotonic()
    values: list[dict[str, Any] | None] = [None] * contract.TASK_COUNT
    with acquire_deepwide_api_lease(
        ROOT,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        with ThreadPoolExecutor(max_workers=contract.EXECUTOR_CONCURRENCY) as pool:
            futures = {
                pool.submit(run_one_task, task): index
                for index, task in enumerate(tasks)
            }
            completed = 0
            for future in as_completed(futures):
                index = futures[future]
                values[index] = validate_task_row(future.result())
                completed += 1
                _atomic_progress(completed)
    rows = [validate_task_row(row) for row in values if row is not None]
    if (
        len(rows) != contract.TASK_COUNT
        or [row["opaque_id"] for row in rows]
        != [task["opaque_id"] for task in tasks]
    ):
        raise RuntimeError("V2.52.08 exact-220 terminal denominator drifted")
    with parent.parent._OBSERVATION_LOCK:
        observations = [
            copy.deepcopy(parent.parent._OBSERVATIONS.get(task["opaque_id"]))
            for task in tasks
        ]
    with _APPLICATION_LOCK:
        applications = [
            bool(_APPLICATIONS.get(task["opaque_id"], False)) for task in tasks
        ]
        if set(_APPLICATIONS) != {task["opaque_id"] for task in tasks}:
            raise RuntimeError("V2.52.08 compatibility observation incomplete")
    sidecar = parent.build_compatibility_aggregate(
        rows, observations, applications
    )
    _publish_json(ROOT / contract.COMPATIBILITY_AGGREGATE, sidecar)
    _publish_jsonl(ROOT / contract.TASK_ROWS, rows)
    aggregate = parent.aggregate_rows(
        rows,
        wall_seconds=time.monotonic() - started,
        compatibility_aggregate=sidecar,
    )
    decision = parent.mechanism_decision(aggregate)
    predictions = [
        {
            "opaque_id": row["opaque_id"],
            "status": "completed",
            "prediction": row["predictions"][contract.CANDIDATE_ARM],
            "prediction_sha256": row["prediction_sha256"][contract.CANDIDATE_ARM],
            "completion_kind": (
                "model_generated"
                if row["runtime_completed"]
                and row["prediction_kind"] == "model_generated"
                else "best_effort_fallback"
            ),
            "elapsed_seconds": row["elapsed_seconds"],
            "cost": copy.deepcopy(row["cost"]),
            "label_blind": True,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        }
        for row in rows
    ]
    _publish_jsonl(ROOT / contract.RUNTIME_PREDICTIONS, predictions)
    summary = _summary(rows, aggregate)
    _publish_json(ROOT / contract.RUN_SUMMARY, summary)
    freeze = contract.seal(
        {
            "artifact_version": 1,
            "role": contract.FREEZE_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected": contract.TASK_COUNT,
            "terminal": contract.TASK_COUNT,
            "runtime_results_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "compatibility_aggregate_sha256": contract.sha256(
                ROOT / contract.COMPATIBILITY_AGGREGATE
            ),
            "runtime_predictions_sha256": contract.sha256(
                ROOT / contract.RUNTIME_PREDICTIONS
            ),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "prediction_hashes_sha256": contract.payload_sha256(
                [row["prediction_sha256"] for row in predictions]
            ),
            "all_predictions_terminal_before_mapping_query_answer_or_official_evaluator_open": True,
            "mapping_gold_or_evaluator_opened_or_hashed": False,
        },
        "freeze_payload_sha256",
    )
    _publish_json(ROOT / contract.PREDICTION_FREEZE, freeze)
    forward = contract.seal(
        {
            "artifact_version": 1,
            "role": contract.FORWARD_ROLE,
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "selected": contract.TASK_COUNT,
            "terminal_predictions": contract.TASK_COUNT,
            "model_generated_tables": summary["model_generated_tables"],
            "fallback_tables": summary["fallback_tables"],
            "system_total_tokens": summary["system_total_tokens"],
            "forward_wall_seconds": summary["forward_wall_seconds"],
            "execution_start_sha256": contract.sha256(
                ROOT / contract.EXECUTION_START
            ),
            "runtime_results_sha256": contract.sha256(ROOT / contract.TASK_ROWS),
            "compatibility_aggregate_sha256": contract.sha256(
                ROOT / contract.COMPATIBILITY_AGGREGATE
            ),
            "runtime_predictions_sha256": contract.sha256(
                ROOT / contract.RUNTIME_PREDICTIONS
            ),
            "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
            "prediction_freeze_sha256": contract.sha256(
                ROOT / contract.PREDICTION_FREEZE
            ),
            "aggregate": aggregate,
            "mechanism_decision": decision,
            "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "entropy_or_information_gain_assigns_signed_credit": False,
            "positive_signed_credit_count": 0,
            "official_evaluator_called": False,
            "retry_resume_skip_or_selective_rerun_launched": False,
            "authorization": {
                "forward_audit": True,
                "postfreeze_exact220_evaluator_only_after_pushed_forward_audit": True,
                "retry_resume_skip_or_selective_rerun": False,
                "leaderboard_or_sota": False,
            },
        },
        "result_payload_sha256",
    )
    _publish_json(ROOT / contract.FORWARD_RESULT, forward)
    return validate_forward_result(forward)


def main() -> None:
    value = run_forward()
    print(
        json.dumps(
            {
                "path": str(contract.FORWARD_RESULT),
                "selected": value["selected"],
                "terminal_predictions": value["terminal_predictions"],
                "model_generated_tables": value["model_generated_tables"],
                "fallback_tables": value["fallback_tables"],
                "forward_wall_seconds": value["forward_wall_seconds"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
