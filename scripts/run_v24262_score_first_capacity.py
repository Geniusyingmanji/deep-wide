#!/usr/bin/env python3
"""Run the frozen V2.42.62 full-pipeline concurrency ladder."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24259_deterministic_table_normalizer import (  # noqa: E402
    ALL_KINDS,
    NORMALIZED_KINDS,
    validate_v24259_result,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.preregister_v24262_score_first_capacity import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    LEVELS,
    MODEL_GENERATED,
    OUTPUT,
    OUTPUT_ROOT,
    PROGRESS,
    RESULT,
    ROLE as PROTOCOL_ROLE,
    RUNNER_MARKER,
    TASK_COUNT,
    WAVES_PER_LEVEL,
    schedule_manifest,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import (  # noqa: E402
    _new_json,
    _selected_tasks,
    _start_ticks,
    payload_sha256,
    read_object,
    sha256,
)
from scripts.run_v24261_score_first_smoke import run_one_task  # noqa: E402


ROLE = "v24262_score_first_capacity_result"
PROGRESS_ROLE = "v24262_score_first_capacity_safe_progress"
TASK_ROW_KEYS = frozenset(
    {
        "slot",
        "task_position",
        "completion_kind",
        "model_generated",
        "infrastructure_fallback",
        "failure_types",
        "elapsed_seconds",
        "system_total_tokens",
        "fetch_calls",
        "model_requests",
        "model_attempts",
        "logical_search_calls",
        "logical_search_failures",
        "fetch_failures",
        "question_query_url_page_prediction_answer_or_opaque_id_emitted",
    }
)
WAVE_KEYS = frozenset({"wave", "request_count", "elapsed_seconds", "tasks"})
LEVEL_KEYS = frozenset(
    {
        "concurrency",
        "waves",
        "executions",
        "model_generated",
        "fallbacks",
        "matched_serial_fallbacks",
        "infrastructure_fallbacks",
        "stage_failures",
        "additional_model_attempts_vs_matched_serial",
        "additional_logical_search_failures_vs_matched_serial",
        "additional_fetch_failures_vs_matched_serial",
        "median_wall_seconds",
        "p95_wall_seconds",
        "median_matched_wall_ratio",
        "p95_matched_wall_ratio",
        "mean_matched_token_ratio",
        "mean_matched_fetch_ratio",
        "serial_reference_wall_seconds",
        "observed_wave_wall_seconds",
        "effective_speedup",
        "effective_speedup_fraction",
        "passed",
        "findings",
    }
)
PROGRESS_LEVEL_KEYS = frozenset(
    {
        "concurrency",
        "executions",
        "model_generated",
        "fallbacks",
        "infrastructure_fallbacks",
        "stage_failures",
        "median_wall_seconds",
        "p95_wall_seconds",
        "effective_speedup",
        "effective_speedup_fraction",
        "passed",
        "findings",
    }
)
PROGRESS_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "created_at_unix",
        "status",
        "active_level",
        "active_wave",
        "completed_levels",
        "completed_executions",
        "level_summaries",
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "progress_payload_sha256",
    }
)
RESULT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "protocol_id",
        "created_at_unix",
        "label_blind",
        "levels",
        "selected_executor_concurrency",
        "capacity_gate",
        "total_executions",
        "stopped_after_first_failed_level",
        "prediction_question_query_url_page_answer_opaque_id_or_credential_emitted",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "official_evaluator_called",
        "paired_dev64_or_full220_launched",
        "leaderboard_submission_or_sota_claim",
        "result_payload_sha256",
    }
)
RESULT_EXECUTION_KEYS = frozenset(
    {"execution_start_sha256", "activation_payload_sha256"}
)


def _p95(values: list[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def validate_activation(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    value = read_object(root / ACTIVATION)
    unsigned = dict(value)
    seal = unsigned.pop("activation_payload_sha256", None)
    if (
        value.get("role") != "v24262_score_first_capacity_activation"
        or value.get("status") != "active"
        or value.get("protocol_sha256") != sha256(root / OUTPUT)
        or value.get("decision_contract_sha256") != protocol["decision_contract_sha256"]
        or value.get("control_manifest_sha256") != protocol["control_surface"]["manifest_sha256"]
        or value.get("forward_manifest_sha256") != protocol["forward_surface"]["manifest_sha256"]
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.62 activation drifted")
    return value


def _baseline(protocol: dict[str, Any]) -> dict[int, dict[str, Any]]:
    rows = protocol["baseline_contract"]["rows"]
    values = {int(row["task_position"]): dict(row) for row in rows}
    if set(values) != set(range(1, TASK_COUNT + 1)):
        raise RuntimeError("V2.42.62 baseline task positions drifted")
    return values


def safe_task_row(position: int, result: dict[str, Any]) -> dict[str, Any]:
    validate_v24259_result(result)
    kind = str(result["completion_kind"])
    if kind not in ALL_KINDS:
        raise RuntimeError("V2.42.62 completion kind drifted")
    failures = result.get("failures") or []
    return {
        "task_position": int(position),
        "completion_kind": kind,
        "model_generated": kind in MODEL_GENERATED,
        "infrastructure_fallback": kind in {"hard_deadline_fallback", "worker_failure_fallback"},
        "failure_types": sorted(str(item["type"]) for item in failures),
        "elapsed_seconds": float(result["budget"]["elapsed_seconds"]),
        "system_total_tokens": int(result["cost"]["system_total_tokens"]),
        "fetch_calls": int(result["cost"]["search"]["fetch_calls"]),
        "model_requests": int(result["cost"]["model"]["requests"]),
        "model_attempts": int(result["cost"]["model"]["attempts"]),
        "logical_search_calls": int(result["cost"]["search"]["calls"]),
        "logical_search_failures": int(result["cost"]["search"]["failures"]),
        "fetch_failures": int(result["cost"]["search"]["fetch_failures"]),
        "question_query_url_page_prediction_answer_or_opaque_id_emitted": False,
    }


def evaluate_level(protocol: dict[str, Any], concurrency: int, waves: list[dict[str, Any]]) -> dict[str, Any]:
    baseline = _baseline(protocol)
    rows = [row for wave in waves for row in wave["tasks"]]
    expected = concurrency * WAVES_PER_LEVEL
    if len(rows) != expected:
        raise RuntimeError("V2.42.62 level row count drifted")
    matched_wall = [float(row["elapsed_seconds"]) / float(baseline[int(row["task_position"])]["elapsed_seconds"]) for row in rows]
    matched_tokens = [int(row["system_total_tokens"]) / max(1, int(baseline[int(row["task_position"])]["system_total_tokens"])) for row in rows]
    matched_fetch = [int(row["fetch_calls"]) / max(1, int(baseline[int(row["task_position"])]["fetch_calls"])) for row in rows]
    serial_reference = sum(float(baseline[int(row["task_position"])]["elapsed_seconds"]) for row in rows)
    observed_wave_wall = sum(float(wave["elapsed_seconds"]) for wave in waves)
    speedup = serial_reference / max(observed_wave_wall, 1e-9)
    model_generated = sum(bool(row["model_generated"]) for row in rows)
    current_fallbacks = expected - model_generated
    baseline_fallbacks = sum(
        baseline[int(row["task_position"])]["completion_kind"] not in MODEL_GENERATED
        for row in rows
    )
    infrastructure_fallbacks = sum(bool(row["infrastructure_fallback"]) for row in rows)
    stage_failures = sum(len(row["failure_types"]) for row in rows)
    additional_model_attempts = sum(
        max(
            0,
            int(row["model_attempts"])
            - int(baseline[int(row["task_position"])]["model_attempts"]),
        )
        for row in rows
    )
    additional_search_failures = sum(
        max(
            0,
            int(row["logical_search_failures"])
            - int(baseline[int(row["task_position"])]["logical_search_failures"]),
        )
        for row in rows
    )
    additional_fetch_failures = sum(
        max(
            0,
            int(row["fetch_failures"])
            - int(baseline[int(row["task_position"])]["fetch_failures"]),
        )
        for row in rows
    )
    gates = protocol["capacity_contract"]["gates"]
    findings: list[str] = []
    if infrastructure_fallbacks > int(gates["maximum_infrastructure_fallbacks_per_level"]):
        findings.append("infrastructure_fallbacks_above_gate")
    if stage_failures > int(gates["maximum_stage_failures_per_level"]):
        findings.append("stage_failures_above_gate")
    if model_generated / expected < float(gates["minimum_model_generated_fraction"]):
        findings.append("model_generated_fraction_below_gate")
    if current_fallbacks - baseline_fallbacks > int(gates["maximum_additional_model_fallbacks_vs_matched_serial"]):
        findings.append("additional_model_fallbacks_above_gate")
    if additional_model_attempts > int(gates["maximum_additional_model_attempts_vs_matched_serial"]):
        findings.append("additional_model_attempts_above_gate")
    if additional_search_failures > int(gates["maximum_additional_logical_search_failures_vs_matched_serial"]):
        findings.append("additional_logical_search_failures_above_gate")
    if additional_fetch_failures > int(gates["maximum_additional_fetch_failures_vs_matched_serial"]):
        findings.append("additional_fetch_failures_above_gate")
    if statistics.median(matched_wall) > float(gates["maximum_median_matched_wall_ratio"]):
        findings.append("median_matched_wall_ratio_above_gate")
    if _p95(matched_wall) > float(gates["maximum_p95_matched_wall_ratio"]):
        findings.append("p95_matched_wall_ratio_above_gate")
    if _p95([float(row["elapsed_seconds"]) for row in rows]) > float(gates["maximum_absolute_p95_wall_seconds"]):
        findings.append("absolute_p95_wall_seconds_above_gate")
    if speedup / concurrency < float(gates["minimum_median_effective_speedup_fraction"]):
        findings.append("effective_speedup_fraction_below_gate")
    if sum(matched_tokens) / expected > float(gates["maximum_mean_matched_token_ratio"]):
        findings.append("mean_matched_token_ratio_above_gate")
    if sum(matched_fetch) / expected > float(gates["maximum_mean_matched_fetch_ratio"]):
        findings.append("mean_matched_fetch_ratio_above_gate")
    return {
        "concurrency": concurrency,
        "waves": waves,
        "executions": expected,
        "model_generated": model_generated,
        "fallbacks": current_fallbacks,
        "matched_serial_fallbacks": baseline_fallbacks,
        "infrastructure_fallbacks": infrastructure_fallbacks,
        "stage_failures": stage_failures,
        "additional_model_attempts_vs_matched_serial": additional_model_attempts,
        "additional_logical_search_failures_vs_matched_serial": additional_search_failures,
        "additional_fetch_failures_vs_matched_serial": additional_fetch_failures,
        "median_wall_seconds": round(statistics.median(float(row["elapsed_seconds"]) for row in rows), 6),
        "p95_wall_seconds": round(_p95([float(row["elapsed_seconds"]) for row in rows]), 6),
        "median_matched_wall_ratio": round(statistics.median(matched_wall), 6),
        "p95_matched_wall_ratio": round(_p95(matched_wall), 6),
        "mean_matched_token_ratio": round(sum(matched_tokens) / expected, 6),
        "mean_matched_fetch_ratio": round(sum(matched_fetch) / expected, 6),
        "serial_reference_wall_seconds": round(serial_reference, 6),
        "observed_wave_wall_seconds": round(observed_wave_wall, 6),
        "effective_speedup": round(speedup, 6),
        "effective_speedup_fraction": round(speedup / concurrency, 6),
        "passed": not findings,
        "findings": findings,
    }


def safe_progress(levels: list[dict[str, Any]], *, active_level: int | None, active_wave: int | None, status: str) -> dict[str, Any]:
    value = {
        "artifact_version": 1,
        "role": PROGRESS_ROLE,
        "created_at_unix": int(time.time()),
        "status": status,
        "active_level": active_level,
        "active_wave": active_wave,
        "completed_levels": len(levels),
        "completed_executions": sum(int(level["executions"]) for level in levels),
        "level_summaries": [
            {
                key: level[key]
                for key in (
                    "concurrency",
                    "executions",
                    "model_generated",
                    "fallbacks",
                    "infrastructure_fallbacks",
                    "stage_failures",
                    "median_wall_seconds",
                    "p95_wall_seconds",
                    "effective_speedup",
                    "effective_speedup_fraction",
                    "passed",
                    "findings",
                )
            }
            for level in levels
        ],
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
    }
    value["progress_payload_sha256"] = payload_sha256(value)
    return value


def validate_progress(value: dict[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("progress_payload_sha256", None)
    summaries = value.get("level_summaries")
    if (
        set(value) != PROGRESS_KEYS
        or value.get("role") != PROGRESS_ROLE
        or value.get("contains_question_query_url_page_prediction_answer_opaque_id_or_credential") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or not isinstance(summaries, list)
        or any(
            not isinstance(row, dict) or set(row) != PROGRESS_LEVEL_KEYS
            for row in summaries
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.62 safe progress schema drifted")


def execute_ladder(
    root: Path,
    protocol: dict[str, Any],
    tasks: list[dict[str, str]],
    task_parent: Path,
    *,
    task_runner: Callable[[Path, dict[str, Any], dict[str, str], Path], dict[str, Any]] = run_one_task,
    monotonic: Callable[[], float] = time.monotonic,
    progress_writer: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    if len(tasks) != TASK_COUNT:
        raise RuntimeError("V2.42.62 task count drifted")
    levels: list[dict[str, Any]] = []
    for level in protocol["capacity_contract"]["schedule"]:
        concurrency = int(level["concurrency"])
        waves: list[dict[str, Any]] = []
        for wave_spec in level["waves"]:
            wave_number = int(wave_spec["wave"])
            if progress_writer:
                progress_value = safe_progress(
                    levels,
                    active_level=concurrency,
                    active_wave=wave_number,
                    status="running",
                )
                validate_progress(progress_value)
                progress_writer(progress_value)
            wave_root = task_parent / f"level_{concurrency:02d}" / f"wave_{wave_number:02d}"
            wave_root.mkdir(mode=0o700, parents=True, exist_ok=False)
            started = monotonic()
            futures: dict[concurrent.futures.Future[dict[str, Any]], tuple[int, int]] = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix=f"v24262-capacity-{concurrency}") as executor:
                for slot, position in enumerate(wave_spec["task_positions"], start=1):
                    future = executor.submit(
                        task_runner,
                        root,
                        protocol,
                        tasks[int(position) - 1],
                        wave_root / f"slot_{slot:02d}",
                    )
                    futures[future] = (slot, int(position))
                rows: list[dict[str, Any]] = []
                for future in concurrent.futures.as_completed(futures):
                    slot, position = futures[future]
                    rows.append({"slot": slot, **safe_task_row(position, future.result())})
            rows.sort(key=lambda row: int(row["slot"]))
            waves.append(
                {
                    "wave": wave_number,
                    "request_count": concurrency,
                    "elapsed_seconds": round(max(0.0, monotonic() - started), 6),
                    "tasks": rows,
                }
            )
        summary = evaluate_level(protocol, concurrency, waves)
        levels.append(summary)
        if progress_writer:
            progress_value = safe_progress(
                levels,
                active_level=None,
                active_wave=None,
                status="level_terminal",
            )
            validate_progress(progress_value)
            progress_writer(progress_value)
        if protocol["capacity_contract"]["stop_after_first_failed_level"] and not summary["passed"]:
            break
    return levels


def aggregate(protocol: dict[str, Any], levels: list[dict[str, Any]]) -> dict[str, Any]:
    selected = 0
    for level in levels:
        if not level["passed"]:
            break
        selected = int(level["concurrency"])
    minimum = int(protocol["capacity_contract"]["gates"]["minimum_selected_concurrency_for_capacity_go"])
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "protocol_id": protocol["protocol_id"],
        "created_at_unix": int(time.time()),
        "label_blind": True,
        "levels": levels,
        "selected_executor_concurrency": selected,
        "capacity_gate": "go" if selected >= minimum else "no_go",
        "total_executions": sum(int(level["executions"]) for level in levels),
        "stopped_after_first_failed_level": bool(levels and not levels[-1]["passed"]),
        "prediction_question_query_url_page_answer_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "official_evaluator_called": False,
        "paired_dev64_or_full220_launched": False,
        "leaderboard_submission_or_sota_claim": False,
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return value


def validate_result(protocol: dict[str, Any], value: dict[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    keys = set(value)
    if (
        keys not in (RESULT_KEYS, RESULT_KEYS | RESULT_EXECUTION_KEYS)
        or value.get("role") != ROLE
        or value.get("protocol_id") != protocol["protocol_id"]
        or value.get("label_blind") is not True
        or value.get("prediction_question_query_url_page_answer_opaque_id_or_credential_emitted") is not False
        or value.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or value.get("official_evaluator_called") is not False
        or value.get("paired_dev64_or_full220_launched") is not False
        or value.get("leaderboard_submission_or_sota_claim") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.62 result identity drifted")
    levels = value.get("levels")
    if not isinstance(levels, list) or not levels:
        raise RuntimeError("V2.42.62 result has no capacity levels")
    expected_levels = list(protocol["capacity_contract"]["levels"])
    observed_levels = [level.get("concurrency") for level in levels if isinstance(level, dict)]
    if observed_levels != expected_levels[: len(observed_levels)]:
        raise RuntimeError("V2.42.62 result level order drifted")
    for level in levels:
        if set(level) != LEVEL_KEYS:
            raise RuntimeError("V2.42.62 result level schema drifted")
        waves = level.get("waves")
        if not isinstance(waves, list) or any(
            not isinstance(wave, dict)
            or set(wave) != WAVE_KEYS
            or not isinstance(wave.get("tasks"), list)
            or any(
                not isinstance(row, dict) or set(row) != TASK_ROW_KEYS
                for row in wave["tasks"]
            )
            for wave in waves
        ):
            raise RuntimeError("V2.42.62 result wave schema drifted")
        recomputed = evaluate_level(protocol, int(level["concurrency"]), level["waves"])
        if recomputed != level:
            raise RuntimeError("V2.42.62 result level summary drifted")
    if any(not level["passed"] for level in levels[:-1]):
        raise RuntimeError("V2.42.62 result continued past a failed level")
    selected = 0
    for level in levels:
        if not level["passed"]:
            break
        selected = int(level["concurrency"])
    minimum = int(protocol["capacity_contract"]["gates"]["minimum_selected_concurrency_for_capacity_go"])
    expected_gate = "go" if selected >= minimum else "no_go"
    expected_total = sum(int(level["executions"]) for level in levels)
    expected_stopped = bool(levels and not levels[-1]["passed"])
    if (
        value.get("selected_executor_concurrency") != selected
        or value.get("capacity_gate") != expected_gate
        or value.get("total_executions") != expected_total
        or value.get("stopped_after_first_failed_level") is not expected_stopped
    ):
        raise RuntimeError("V2.42.62 result aggregate summary drifted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(OUTPUT))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if root != ROOT:
        raise RuntimeError("V2.42.62 executor root drifted")
    protocol_path = Path(args.protocol)
    if not protocol_path.is_absolute():
        protocol_path = root / protocol_path
    if protocol_path.resolve() != (root / OUTPUT).resolve():
        raise RuntimeError("V2.42.62 protocol path drifted")
    protocol = validate_protocol(root, OUTPUT)
    activation = validate_activation(root, protocol)
    tasks = _selected_tasks(root, protocol)
    for task in tasks:
        if set(task) != {"opaque_id", "question"}:
            raise RuntimeError("V2.42.62 runtime task boundary drifted")
    for path in (root / EXECUTION_START, root / RESULT, root / OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.42.62 execution surface is not pristine")
    start: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24262_score_first_capacity_execution_start",
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(protocol_path),
        "activation_sha256": sha256(root / ACTIVATION),
        "selected_opaque_ids_sha256": protocol["task_contract"]["selected_opaque_ids_sha256"],
        "runner": {"pid": os.getpid(), "start_ticks": _start_ticks(os.getpid()), "marker": RUNNER_MARKER},
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "api_called_before_execution_start": False,
    }
    start["execution_start_payload_sha256"] = payload_sha256(start)
    _new_json(root / EXECUTION_START, start)
    (root / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
    task_parent = root / OUTPUT_ROOT / "tasks"
    task_parent.mkdir(mode=0o700)
    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["owner"],
        purpose=lease["purpose"],
        path=root / lease["path"],
    ):
        levels = execute_ladder(
            root,
            protocol,
            tasks,
            task_parent,
            progress_writer=lambda value: _atomic_json(root / PROGRESS, value),
        )
    result = aggregate(protocol, levels)
    result["execution_start_sha256"] = sha256(root / EXECUTION_START)
    result["activation_payload_sha256"] = activation["activation_payload_sha256"]
    unsigned = dict(result)
    unsigned.pop("result_payload_sha256", None)
    result["result_payload_sha256"] = payload_sha256(unsigned)
    validate_result(protocol, result)
    _new_json(root / RESULT, result)
    progress_value = safe_progress(
        levels, active_level=None, active_wave=None, status="complete"
    )
    validate_progress(progress_value)
    _atomic_json(root / PROGRESS, progress_value)
    print(json.dumps({"result": str(RESULT), "capacity_gate": result["capacity_gate"], "selected_executor_concurrency": result["selected_executor_concurrency"]}, sort_keys=True))


if __name__ == "__main__":
    main()
