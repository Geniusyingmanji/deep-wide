#!/usr/bin/env python3
"""Run the exact-64 shared-prefix paired forward without evaluator access."""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24259_deterministic_table_normalizer import (  # noqa: E402
    NORMALIZED_KINDS,
)
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    POOL_ID,
    validate_receipt,
)
from deepwide_agent.v24265_paired_normalizer_runtime import (  # noqa: E402
    build_paired_fallback_result,
    validate_paired_result,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.preregister_v24265_paired_dev64 import (  # noqa: E402
    ACTIVATION,
    CANDIDATE_FREEZE,
    CANDIDATE_RUNTIME,
    CANDIDATE_SUMMARY,
    CONTROL_FREEZE,
    CONTROL_RUNTIME,
    CONTROL_SUMMARY,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FORWARD_RESULT,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    OUTPUT,
    OUTPUT_ROOT,
    RUNNER_MARKER,
    SAFE_PROGRESS,
    SELECTED_COUNT,
    TASK_ROOT,
    validate_protocol,
    selected_tasks,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    _child_env,
    _new_json,
    _start_ticks,
    _terminate_group,
    payload_sha256,
    read_object,
    sha256,
)
from scripts.run_v24262_score_first_capacity import _atomic_json  # noqa: E402


ROLE = "v24265_shared_prefix_paired_dev64_forward_result"
CHILD = "scripts/run_v24265_paired_task.py"
RECEIPT_NAME = "model_slot_receipt.json"
MODEL_GENERATED_CONTROL = frozenset({"primary", "repaired"})
MODEL_GENERATED_CANDIDATE = frozenset(
    {"primary", "repaired", *NORMALIZED_KINDS}
)
RUNTIME_ROW_KEYS = frozenset(
    {
        "opaque_id",
        "status",
        "prediction",
        "prediction_sha256",
        "completion_kind",
        "elapsed_seconds",
        "cost",
        "label_blind",
        "mapping_gold_category_question_type_split_evaluator_score_read",
    }
)
SUMMARY_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "selected",
        "completed",
        "failed",
        "model_generated_tables",
        "fallback_tables",
        "completion_kinds",
        "system_total_tokens",
        "wall_seconds_sum",
        "label_blind",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "official_evaluator_called",
    }
)
FREEZE_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "selected",
        "terminal",
        "selected_opaque_ids_sha256",
        "runtime_predictions_sha256",
        "run_summary_sha256",
        "prediction_hashes_sha256",
        "exact_terminal_before_mapping_query_answer_gold_or_evaluator_open",
        "mapping_query_answer_gold_or_evaluator_opened_or_hashed",
        "label_blind",
        "freeze_payload_sha256",
    }
)
PROGRESS_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "selected",
        "completed_pairs",
        "unfinished_pairs",
        "executor_concurrency",
        "global_model_slot_cap",
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "progress_payload_sha256",
    }
)
FORWARD_RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "selected",
        "terminal_pairs",
        "control",
        "candidate",
        "shared_model_receipts",
        "both_arms_exact_terminal_before_evaluator_open",
        "mapping_query_answer_gold_or_evaluator_opened_or_hashed",
        "label_blind",
        "official_evaluator_called",
        "full220_or_leaderboard_launched",
        "execution_start_sha256",
        "activation_payload_sha256",
        "result_payload_sha256",
    }
)
FORWARD_ARM_KEYS = frozenset(
    {
        "model_generated_tables",
        "fallback_tables",
        "system_total_tokens",
        "prediction_freeze_sha256",
    }
)
RECEIPT_SUMMARY_KEYS = frozenset(
    {
        "children",
        "present",
        "valid",
        "invalid",
        "actual_shared_model_requests",
        "slot_acquisitions",
        "all_acquisitions_match_actual_requests",
    }
)
ACTIVATION_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "status",
        "protocol_sha256",
        "preactivation_audit_sha256",
        "decision_contract_sha256",
        "control_manifest_sha256",
        "forward_manifest_sha256",
        "selected_count",
        "executor_concurrency",
        "global_model_slot_cap",
        "shared_api_lease_active_before_activation",
        "network_model_search_fetch_evaluator_or_api_called",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "full220_or_leaderboard_authorized",
        "activation_payload_sha256",
    }
)
EXECUTION_START_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "protocol_sha256",
        "activation_sha256",
        "selected_opaque_ids_sha256",
        "runner",
        "selected",
        "executor_concurrency",
        "global_model_slot_cap",
        "label_blind",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "api_called_before_execution_start",
        "execution_start_payload_sha256",
    }
)


@dataclasses.dataclass(frozen=True)
class TaskOutcome:
    result: dict[str, Any]
    receipt_present: bool
    receipt_valid: bool
    receipt_acquisitions: int


def validate_activation(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    value = read_object(root / ACTIVATION)
    unsigned = dict(value)
    seal = unsigned.pop("activation_payload_sha256", None)
    if (
        set(value) != ACTIVATION_KEYS
        or value.get("artifact_version") != 1
        or
        value.get("role") != "v24265_paired_dev64_activation"
        or value.get("status") != "active"
        or value.get("protocol_sha256") != sha256(root / OUTPUT)
        or value.get("decision_contract_sha256")
        != protocol["decision_contract_sha256"]
        or value.get("control_manifest_sha256")
        != protocol["control_surface"]["manifest_sha256"]
        or value.get("forward_manifest_sha256")
        != protocol["forward_surface"]["manifest_sha256"]
        or value.get("selected_count") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or value.get("shared_api_lease_active_before_activation") is not False
        or value.get("network_model_search_fetch_evaluator_or_api_called") is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("full220_or_leaderboard_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.65 activation drifted")
    return value


def validate_execution_start(
    root: Path, protocol: dict[str, Any], activation: dict[str, Any]
) -> dict[str, Any]:
    value = read_object(root / EXECUTION_START)
    unsigned = dict(value)
    seal = unsigned.pop("execution_start_payload_sha256", None)
    runner = value.get("runner")
    if (
        set(value) != EXECUTION_START_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != "v24265_paired_dev64_execution_start"
        or value.get("protocol_sha256") != sha256(root / OUTPUT)
        or value.get("activation_sha256") != sha256(root / ACTIVATION)
        or value.get("selected_opaque_ids_sha256")
        != protocol["task_contract"]["selected_opaque_ids_sha256"]
        or not isinstance(runner, dict)
        or set(runner) != {"pid", "start_ticks", "marker"}
        or isinstance(runner.get("pid"), bool)
        or not isinstance(runner.get("pid"), int)
        or runner.get("pid") <= 0
        or isinstance(runner.get("start_ticks"), bool)
        or not isinstance(runner.get("start_ticks"), int)
        or runner.get("start_ticks") < 0
        or runner.get("marker") != RUNNER_MARKER
        or value.get("selected") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or value.get("label_blind") is not True
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("api_called_before_execution_start") is not False
        or seal != payload_sha256(unsigned)
        or activation.get("activation_payload_sha256")
        != read_object(root / ACTIVATION).get("activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.65 execution start drifted")
    return value


def task_command(
    root: Path,
    protocol: dict[str, Any],
    task_path: Path,
    result_path: Path,
    progress_path: Path,
    receipt_path: Path,
) -> list[str]:
    provider = protocol["provider_contract"]
    limits = protocol["limits"]
    return [
        str(root / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(root / CHILD),
        "--task",
        str(task_path),
        "--result",
        str(result_path),
        "--progress",
        str(progress_path),
        "--model-slot-directory",
        str(root / MODEL_SLOT_DIRECTORY),
        "--model-slot-receipt",
        str(receipt_path),
        "--model-slot-cap",
        str(MODEL_SLOT_CAP),
        "--model-slot-pool-id",
        POOL_ID,
        "--proxy-url",
        provider["model"]["proxy_url"],
        "--model",
        provider["model"]["name"],
        "--reasoning-effort",
        provider["model"]["reasoning_effort"],
        "--service-tier",
        provider["model"]["service_tier"],
        "--model-timeout",
        str(provider["model"]["timeout_seconds"]),
        "--model-max-retries",
        str(provider["model"]["max_retries"]),
        "--search-model",
        provider["search"]["model"],
        "--search-timeout",
        str(provider["search"]["timeout_seconds"]),
        "--search-max-retries",
        str(provider["search"]["max_retries"]),
        "--search-workers",
        str(provider["search"]["workers"]),
        "--fetch-workers",
        str(provider["search"]["fetch_workers"]),
        "--fetch-timeout",
        str(provider["search"]["fetch_timeout_seconds"]),
        "--wall-seconds",
        str(limits["wall_seconds"]),
        "--model-calls",
        str(limits["model_calls"]),
        "--search-queries",
        str(limits["search_queries"]),
        "--fetch-targets",
        str(limits["fetch_targets"]),
        "--search-results-per-query",
        str(limits["search_results_per_query"]),
        "--evidence-chars",
        str(limits["evidence_chars"]),
        "--page-chars",
        str(limits["page_chars"]),
    ]


def _safe_progress(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        return {}
    value = read_object(path)
    allowed = {
        "artifact_version",
        "role",
        "stage",
        "elapsed_seconds",
        "admitted_shared_model_calls",
        "admitted_search_queries",
        "admitted_fetch_targets",
        "search_batch_count",
        "projected_chars",
        "model_cost",
        "search_cost",
        "contains_question_query_url_page_prediction_answer_or_opaque_id",
        "mapping_gold_category_question_type_split_evaluator_score_read",
    }
    if (
        set(value) != allowed
        or value.get("role") != "v24265_paired_safe_progress"
        or value.get(
            "contains_question_query_url_page_prediction_answer_or_opaque_id"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
    ):
        raise RuntimeError("V2.42.65 safe progress drifted")
    return value


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return _is_sha256(seal) and seal == payload_sha256(unsigned)


def _nonnegative_integer(value: object, *, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"V2.42.65 {label} is not a nonnegative integer")
    return value


def validate_runtime_row(value: dict[str, Any]) -> None:
    elapsed = value.get("elapsed_seconds")
    prediction = value.get("prediction")
    cost = value.get("cost")
    if (
        set(value) != RUNTIME_ROW_KEYS
        or value.get("status") != "completed"
        or not isinstance(value.get("opaque_id"), str)
        or not isinstance(prediction, str)
        or not prediction
        or hashlib.sha256(prediction.encode("utf-8")).hexdigest()
        != value.get("prediction_sha256")
        or not isinstance(value.get("completion_kind"), str)
        or isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or float(elapsed) < 0
        or not isinstance(cost, dict)
        or set(cost) != {"system_total_tokens"}
        or value.get("label_blind") is not True
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
    ):
        raise RuntimeError("V2.42.65 runtime row schema drifted")
    _nonnegative_integer(cost["system_total_tokens"], label="runtime row token cost")


def validate_summary(value: dict[str, Any], arm: str) -> None:
    if (
        set(value) != SUMMARY_KEYS
        or value.get("role") != f"v24265_{arm}_run_summary"
        or value.get("artifact_version") != 1
        or value.get("selected") != SELECTED_COUNT
        or value.get("completed") != SELECTED_COUNT
        or value.get("failed") != 0
        or value.get("label_blind") is not True
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("official_evaluator_called") is not False
        or not isinstance(value.get("completion_kinds"), dict)
    ):
        raise RuntimeError("V2.42.65 run summary schema drifted")
    numeric = (
        "model_generated_tables",
        "fallback_tables",
        "system_total_tokens",
    )
    for key in numeric:
        _nonnegative_integer(value.get(key), label=f"summary.{key}")
    for key, count in value["completion_kinds"].items():
        if not isinstance(key, str):
            raise RuntimeError("V2.42.65 completion-kind key drifted")
        _nonnegative_integer(count, label="summary completion-kind count")
    wall = value.get("wall_seconds_sum")
    if (
        isinstance(wall, bool)
        or not isinstance(wall, (int, float))
        or not math.isfinite(float(wall))
        or float(wall) < 0
        or value["model_generated_tables"] + value["fallback_tables"]
        != SELECTED_COUNT
        or sum(value["completion_kinds"].values()) != SELECTED_COUNT
    ):
        raise RuntimeError("V2.42.65 run summary accounting drifted")


def validate_freeze(
    value: dict[str, Any],
    *,
    protocol: dict[str, Any],
    arm: str,
    runtime_path: Path,
    summary_path: Path,
) -> None:
    if (
        set(value) != FREEZE_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != f"v24265_{arm}_prediction_freeze"
        or value.get("protocol_id") != protocol["protocol_id"]
        or value.get("selected") != SELECTED_COUNT
        or value.get("terminal") != SELECTED_COUNT
        or value.get("selected_opaque_ids_sha256")
        != protocol["task_contract"]["selected_opaque_ids_sha256"]
        or value.get("runtime_predictions_sha256") != sha256(runtime_path)
        or value.get("run_summary_sha256") != sha256(summary_path)
        or value.get(
            "exact_terminal_before_mapping_query_answer_gold_or_evaluator_open"
        )
        is not True
        or value.get("mapping_query_answer_gold_or_evaluator_opened_or_hashed")
        is not False
        or value.get("label_blind") is not True
        or not _sealed(value, "freeze_payload_sha256")
    ):
        raise RuntimeError("V2.42.65 prediction freeze drifted")
    rows = [
        json.loads(line)
        for line in runtime_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(rows) != SELECTED_COUNT:
        raise RuntimeError("V2.42.65 prediction freeze row count drifted")
    for row in rows:
        validate_runtime_row(row)
    if payload_sha256([row["opaque_id"] for row in rows]) != protocol[
        "task_contract"
    ]["selected_opaque_ids_sha256"]:
        raise RuntimeError("V2.42.65 prediction freeze opaque-ID order drifted")
    if value.get("prediction_hashes_sha256") != payload_sha256(
        [row["prediction_sha256"] for row in rows]
    ):
        raise RuntimeError("V2.42.65 prediction hash vector drifted")
    validate_summary(read_object(summary_path), arm)


def validate_progress(value: dict[str, Any]) -> None:
    if (
        set(value) != PROGRESS_KEYS
        or value.get("role") != "v24265_paired_dev64_safe_forward_progress"
        or value.get("selected") != SELECTED_COUNT
        or value.get("executor_concurrency") != EXECUTOR_CONCURRENCY
        or value.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or value.get(
            "contains_question_query_url_page_prediction_answer_opaque_id_or_credential"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or not _sealed(value, "progress_payload_sha256")
    ):
        raise RuntimeError("V2.42.65 forward progress schema drifted")
    completed = _nonnegative_integer(
        value.get("completed_pairs"), label="completed pairs"
    )
    unfinished = _nonnegative_integer(
        value.get("unfinished_pairs"), label="unfinished pairs"
    )
    if completed + unfinished != SELECTED_COUNT:
        raise RuntimeError("V2.42.65 forward progress accounting drifted")


def run_one_task(
    root: Path,
    protocol: dict[str, Any],
    task: dict[str, str],
    task_root: Path,
    *,
    popen: Any = subprocess.Popen,
) -> TaskOutcome:
    task_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    task_path = task_root / "visible_task.json"
    result_path = task_root / "paired_result.json"
    progress_path = task_root / "safe_progress.json"
    receipt_path = task_root / RECEIPT_NAME
    _new_json(task_path, task)
    process = popen(
        task_command(
            root,
            protocol,
            task_path,
            result_path,
            progress_path,
            receipt_path,
        ),
        cwd=root,
        env=_child_env(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    started = time.monotonic()
    timed_out = False
    try:
        return_code = process.wait(
            timeout=float(protocol["limits"]["wall_seconds"])
            + float(protocol["execution"]["parent_deadline_grace_seconds"])
        )
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_group(process)
        return_code = process.returncode
    elapsed = time.monotonic() - started
    progress = _safe_progress(progress_path)
    receipt = None
    if receipt_path.is_file() and not receipt_path.is_symlink():
        candidate = read_object(receipt_path)
        try:
            receipt = validate_receipt(candidate, expected_cap=MODEL_SLOT_CAP)
        except ValueError:
            receipt = None
    if not timed_out and return_code == 0 and result_path.is_file():
        result = read_object(result_path)
        validate_paired_result(result)
        expected = int(
            result["shared_execution"]["actual_model_cost"]["requests"]
        )
        try:
            if receipt is None:
                raise ValueError("model slot receipt absent")
            validate_receipt(
                receipt,
                expected_cap=MODEL_SLOT_CAP,
                expected_acquisitions=expected,
            )
            return TaskOutcome(result, True, True, expected)
        except ValueError:
            return TaskOutcome(
                build_paired_fallback_result(
                    task,
                    limits=ScoreFirstLimits(**dict(protocol["limits"])),
                    completion_kind="worker_failure_fallback",
                    failure_stage="model_slot_receipt",
                    failure_type="ModelSlotReceiptInvalid",
                    elapsed_seconds=elapsed,
                    last_progress=progress,
                ),
                receipt is not None,
                False,
                int(receipt.get("acquisitions", 0)) if receipt is not None else 0,
            )
    fallback = build_paired_fallback_result(
        task,
        limits=ScoreFirstLimits(**dict(protocol["limits"])),
        completion_kind=(
            "hard_deadline_fallback" if timed_out else "worker_failure_fallback"
        ),
        failure_stage="parent_executor",
        failure_type=("HardDeadlineExceeded" if timed_out else "WorkerNonzeroExit"),
        elapsed_seconds=elapsed,
        last_progress=progress,
    )
    return TaskOutcome(
        fallback,
        receipt is not None,
        False,
        int(receipt.get("acquisitions", 0)) if receipt is not None else 0,
    )


def _runtime_row(result: dict[str, Any], arm: str) -> dict[str, Any]:
    value = result[arm]
    row = {
        "opaque_id": value["opaque_id"],
        "status": "completed",
        "prediction": value["prediction"],
        "prediction_sha256": value["prediction_sha256"],
        "completion_kind": value["completion_kind"],
        "elapsed_seconds": value["budget"]["elapsed_seconds"],
        "cost": {"system_total_tokens": value["cost"]["system_total_tokens"]},
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    validate_runtime_row(row)
    return row


def _summary(results: list[dict[str, Any]], arm: str) -> dict[str, Any]:
    kinds: dict[str, int] = {}
    values = [result[arm] for result in results]
    generated = MODEL_GENERATED_CONTROL if arm == "control" else MODEL_GENERATED_CANDIDATE
    for value in values:
        kind = str(value["completion_kind"])
        kinds[kind] = kinds.get(kind, 0) + 1
    result = {
        "artifact_version": 1,
        "role": f"v24265_{arm}_run_summary",
        "selected": SELECTED_COUNT,
        "completed": len(values),
        "failed": 0,
        "model_generated_tables": sum(
            kind in generated for kind in (value["completion_kind"] for value in values)
        ),
        "fallback_tables": sum(
            value["completion_kind"] not in generated for value in values
        ),
        "completion_kinds": kinds,
        "system_total_tokens": sum(
            int(value["cost"]["system_total_tokens"]) for value in values
        ),
        "wall_seconds_sum": round(
            sum(float(value["budget"]["elapsed_seconds"]) for value in values), 6
        ),
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
    }
    validate_summary(result, arm)
    return result


def _write_jsonl_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _freeze(
    protocol: dict[str, Any], arm: str, runtime_path: Path, summary_path: Path
) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": f"v24265_{arm}_prediction_freeze",
        "protocol_id": protocol["protocol_id"],
        "selected": SELECTED_COUNT,
        "terminal": SELECTED_COUNT,
        "selected_opaque_ids_sha256": protocol["task_contract"][
            "selected_opaque_ids_sha256"
        ],
        "runtime_predictions_sha256": sha256(runtime_path),
        "run_summary_sha256": sha256(summary_path),
        "prediction_hashes_sha256": payload_sha256(
            [
                json.loads(line)["prediction_sha256"]
                for line in runtime_path.read_text(encoding="utf-8").splitlines()
                if line
            ]
        ),
        "exact_terminal_before_mapping_query_answer_gold_or_evaluator_open": True,
        "mapping_query_answer_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
    }
    value["freeze_payload_sha256"] = payload_sha256(value)
    validate_freeze(
        value,
        protocol=protocol,
        arm=arm,
        runtime_path=runtime_path,
        summary_path=summary_path,
    )
    return value


def _safe_forward_progress(completed: int, unfinished: int) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": "v24265_paired_dev64_safe_forward_progress",
        "created_at_unix": int(time.time()),
        "selected": SELECTED_COUNT,
        "completed_pairs": completed,
        "unfinished_pairs": unfinished,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "global_model_slot_cap": MODEL_SLOT_CAP,
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    value["progress_payload_sha256"] = payload_sha256(value)
    validate_progress(value)
    return value


def execute_forward(
    root: Path,
    protocol: dict[str, Any],
    tasks: list[dict[str, str]],
    *,
    task_runner: Callable[
        [Path, dict[str, Any], dict[str, str], Path], TaskOutcome
    ] = run_one_task,
    progress_writer: Callable[[dict[str, Any]], None] | None = None,
) -> list[TaskOutcome]:
    if len(tasks) != SELECTED_COUNT:
        raise RuntimeError("V2.42.65 exact64 task count drifted")
    outcomes: dict[int, TaskOutcome] = {}
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=EXECUTOR_CONCURRENCY,
        thread_name_prefix="v24265-paired-dev64",
    ) as executor:
        futures = {
            executor.submit(
                task_runner,
                root,
                protocol,
                task,
                root / TASK_ROOT / f"task_{position:04d}",
            ): position
            for position, task in enumerate(tasks, start=1)
        }
        for future in concurrent.futures.as_completed(futures):
            position = futures[future]
            outcome = future.result()
            if not isinstance(outcome, TaskOutcome):
                raise RuntimeError("V2.42.65 task runner returned no receipt outcome")
            validate_paired_result(outcome.result)
            outcomes[position] = outcome
            if progress_writer:
                progress_writer(
                    _safe_forward_progress(
                        len(outcomes), len(futures) - len(outcomes)
                    )
                )
    ordered = [outcomes[position] for position in range(1, SELECTED_COUNT + 1)]
    if [value.result["opaque_id"] for value in ordered] != [
        task["opaque_id"] for task in tasks
    ]:
        raise RuntimeError("V2.42.65 paired result order drifted")
    return ordered


def _receipt_summary(outcomes: list[TaskOutcome]) -> dict[str, Any]:
    requests = sum(
        int(outcome.result["shared_execution"]["actual_model_cost"]["requests"])
        for outcome in outcomes
    )
    acquisitions = sum(outcome.receipt_acquisitions for outcome in outcomes)
    present = sum(outcome.receipt_present for outcome in outcomes)
    valid = sum(outcome.receipt_valid for outcome in outcomes)
    value = {
        "children": len(outcomes),
        "present": present,
        "valid": valid,
        "invalid": len(outcomes) - valid,
        "actual_shared_model_requests": requests,
        "slot_acquisitions": acquisitions,
        "all_acquisitions_match_actual_requests": (
            len(outcomes) == SELECTED_COUNT
            and present == SELECTED_COUNT
            and valid == SELECTED_COUNT
            and acquisitions == requests
        ),
    }
    if set(value) != RECEIPT_SUMMARY_KEYS:
        raise RuntimeError("V2.42.65 receipt summary schema drifted")
    return value


def validate_forward_result(
    protocol: dict[str, Any],
    value: dict[str, Any],
    *,
    root: Path = ROOT,
) -> None:
    activation = validate_activation(root, protocol)
    execution_start = validate_execution_start(root, protocol, activation)
    if (
        set(value) != FORWARD_RESULT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("protocol_id") != protocol["protocol_id"]
        or value.get("selected") != SELECTED_COUNT
        or value.get("terminal_pairs") != SELECTED_COUNT
        or value.get("both_arms_exact_terminal_before_evaluator_open") is not True
        or value.get("mapping_query_answer_gold_or_evaluator_opened_or_hashed")
        is not False
        or value.get("label_blind") is not True
        or value.get("official_evaluator_called") is not False
        or value.get("full220_or_leaderboard_launched") is not False
        or value.get("execution_start_sha256") != sha256(root / EXECUTION_START)
        or value.get("activation_payload_sha256")
        != activation["activation_payload_sha256"]
        or execution_start.get("activation_sha256") != sha256(root / ACTIVATION)
        or not _sealed(value, "result_payload_sha256")
    ):
        raise RuntimeError("V2.42.65 forward result identity drifted")
    for arm, runtime_path, summary_path, freeze_path in (
        ("control", root / CONTROL_RUNTIME, root / CONTROL_SUMMARY, root / CONTROL_FREEZE),
        (
            "candidate",
            root / CANDIDATE_RUNTIME,
            root / CANDIDATE_SUMMARY,
            root / CANDIDATE_FREEZE,
        ),
    ):
        arm_value = value.get(arm)
        if not isinstance(arm_value, dict) or set(arm_value) != FORWARD_ARM_KEYS:
            raise RuntimeError("V2.42.65 forward arm schema drifted")
        summary = read_object(summary_path)
        validate_summary(summary, arm)
        freeze = read_object(freeze_path)
        validate_freeze(
            freeze,
            protocol=protocol,
            arm=arm,
            runtime_path=runtime_path,
            summary_path=summary_path,
        )
        if arm_value != {
            "model_generated_tables": summary["model_generated_tables"],
            "fallback_tables": summary["fallback_tables"],
            "system_total_tokens": summary["system_total_tokens"],
            "prediction_freeze_sha256": sha256(freeze_path),
        }:
            raise RuntimeError("V2.42.65 forward arm binding drifted")
    receipts = value.get("shared_model_receipts")
    if (
        not isinstance(receipts, dict)
        or set(receipts) != RECEIPT_SUMMARY_KEYS
        or receipts.get("children") != SELECTED_COUNT
    ):
        raise RuntimeError("V2.42.65 forward receipt summary drifted")
    for key in RECEIPT_SUMMARY_KEYS - {"all_acquisitions_match_actual_requests"}:
        _nonnegative_integer(receipts.get(key), label=f"receipts.{key}")
    expected_health = (
        receipts["present"] == SELECTED_COUNT
        and receipts["valid"] == SELECTED_COUNT
        and receipts["invalid"] == 0
        and receipts["slot_acquisitions"]
        == receipts["actual_shared_model_requests"]
    )
    if (
        receipts["present"] > SELECTED_COUNT
        or receipts["valid"] > receipts["present"]
        or receipts["invalid"] != SELECTED_COUNT - receipts["valid"]
        or receipts.get("all_acquisitions_match_actual_requests")
        is not expected_health
    ):
        raise RuntimeError("V2.42.65 forward receipt accounting drifted")


def _prepare_slots(root: Path) -> None:
    directory = root / MODEL_SLOT_DIRECTORY
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    for index in range(1, MODEL_SLOT_CAP + 1):
        _new_json(
            directory / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
                "role": "v24265_model_slot",
                "pool_id": POOL_ID,
                "slot": index,
                "slot_cap": MODEL_SLOT_CAP,
                "contains_credential_or_benchmark_content": False,
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(OUTPUT))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    protocol_path = Path(args.protocol)
    if not protocol_path.is_absolute():
        protocol_path = root / protocol_path
    if root != ROOT or protocol_path.resolve() != (root / OUTPUT).resolve():
        raise RuntimeError("V2.42.65 executor path drifted")
    protocol = validate_protocol(root, OUTPUT)
    activation = validate_activation(root, protocol)
    tasks = selected_tasks(root, protocol)
    for path in (root / EXECUTION_START, root / FORWARD_RESULT, root / OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.42.65 forward surface is not pristine")
    start = {
        "artifact_version": 1,
        "role": "v24265_paired_dev64_execution_start",
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(protocol_path),
        "activation_sha256": sha256(root / ACTIVATION),
        "selected_opaque_ids_sha256": protocol["task_contract"]["selected_opaque_ids_sha256"],
        "runner": {"pid": os.getpid(), "start_ticks": _start_ticks(os.getpid()), "marker": RUNNER_MARKER},
        "selected": SELECTED_COUNT,
        "executor_concurrency": EXECUTOR_CONCURRENCY,
        "global_model_slot_cap": MODEL_SLOT_CAP,
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "api_called_before_execution_start": False,
    }
    start["execution_start_payload_sha256"] = payload_sha256(start)
    _new_json(root / EXECUTION_START, start)
    (root / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
    _prepare_slots(root)
    (root / TASK_ROOT).mkdir(mode=0o700)
    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["forward_owner"],
        purpose=lease["forward_purpose"],
        path=root / lease["path"],
    ):
        outcomes = execute_forward(
            root,
            protocol,
            tasks,
            progress_writer=lambda value: _atomic_json(root / SAFE_PROGRESS, value),
        )
    results = [outcome.result for outcome in outcomes]
    control_rows = [_runtime_row(value, "control") for value in results]
    candidate_rows = [_runtime_row(value, "candidate") for value in results]
    _write_jsonl_new(root / CONTROL_RUNTIME, control_rows)
    _write_jsonl_new(root / CANDIDATE_RUNTIME, candidate_rows)
    control_summary = _summary(results, "control")
    candidate_summary = _summary(results, "candidate")
    _new_json(root / CONTROL_SUMMARY, control_summary)
    _new_json(root / CANDIDATE_SUMMARY, candidate_summary)
    control_freeze = _freeze(
        protocol, "control", root / CONTROL_RUNTIME, root / CONTROL_SUMMARY
    )
    candidate_freeze = _freeze(
        protocol,
        "candidate",
        root / CANDIDATE_RUNTIME,
        root / CANDIDATE_SUMMARY,
    )
    _new_json(root / CONTROL_FREEZE, control_freeze)
    _new_json(root / CANDIDATE_FREEZE, candidate_freeze)
    result = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": protocol["protocol_id"],
        "created_at_unix": int(time.time()),
        "selected": SELECTED_COUNT,
        "terminal_pairs": len(results),
        "control": {
            "model_generated_tables": control_summary["model_generated_tables"],
            "fallback_tables": control_summary["fallback_tables"],
            "system_total_tokens": control_summary["system_total_tokens"],
            "prediction_freeze_sha256": sha256(root / CONTROL_FREEZE),
        },
        "candidate": {
            "model_generated_tables": candidate_summary["model_generated_tables"],
            "fallback_tables": candidate_summary["fallback_tables"],
            "system_total_tokens": candidate_summary["system_total_tokens"],
            "prediction_freeze_sha256": sha256(root / CANDIDATE_FREEZE),
        },
        "shared_model_receipts": _receipt_summary(outcomes),
        "both_arms_exact_terminal_before_evaluator_open": True,
        "mapping_query_answer_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
        "official_evaluator_called": False,
        "full220_or_leaderboard_launched": False,
        "execution_start_sha256": sha256(root / EXECUTION_START),
        "activation_payload_sha256": activation["activation_payload_sha256"],
    }
    result["result_payload_sha256"] = payload_sha256(result)
    validate_forward_result(protocol, result, root=root)
    _new_json(root / FORWARD_RESULT, result)
    _atomic_json(root / SAFE_PROGRESS, _safe_forward_progress(SELECTED_COUNT, 0))
    print(json.dumps({"forward_result": str(FORWARD_RESULT), "terminal_pairs": len(results)}, sort_keys=True))


if __name__ == "__main__":
    main()
