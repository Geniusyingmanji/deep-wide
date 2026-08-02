#!/usr/bin/env python3
"""Run the V2.42.63 capacity ladder with two global GPT request slots."""

from __future__ import annotations

import argparse
import concurrent.futures
import dataclasses
import json
import os
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
    build_v24259_fallback_result,
    validate_v24259_result,
)
from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    POOL_ID,
    validate_receipt,
)
from scripts import run_v24262_score_first_capacity as parent  # noqa: E402
from scripts import run_v24261_score_first_smoke as executor61  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.preregister_v24263_model_limited_capacity import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    OUTPUT,
    OUTPUT_ROOT,
    PROGRESS,
    RESULT,
    RUNNER_MARKER,
    TASK_COUNT,
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
from scripts.run_v24261_score_first_smoke import task_command as parent_task_command  # noqa: E402


ROLE = "v24263_model_limited_capacity_result"
PROGRESS_ROLE = "v24263_model_limited_capacity_safe_progress"
CHILD = "scripts/run_v24263_score_first_task.py"
RECEIPT_NAME = "model_slot_receipt.json"
EXTRA_TASK_ROW_KEYS = frozenset(
    {
        "model_slot_receipt_present",
        "model_slot_receipt_valid",
        "model_slot_cap",
        "model_slot_acquisitions",
        "model_slot_total_wait_seconds",
        "model_slot_max_wait_seconds",
        "model_slot_acquisition_counts",
    }
)
TASK_ROW_KEYS = parent.TASK_ROW_KEYS | EXTRA_TASK_ROW_KEYS
EXTRA_LEVEL_KEYS = frozenset(
    {
        "model_slot_receipt_invalid_count",
        "model_slot_acquisitions",
        "model_slot_total_wait_seconds",
        "model_slot_max_wait_seconds",
        "model_slot_acquisition_counts",
    }
)
LEVEL_KEYS = parent.LEVEL_KEYS | EXTRA_LEVEL_KEYS
PROGRESS_LEVEL_KEYS = parent.PROGRESS_LEVEL_KEYS | frozenset(
    {"model_slot_receipt_invalid_count", "model_slot_max_wait_seconds"}
)
PROGRESS_KEYS = parent.PROGRESS_KEYS
RESULT_KEYS = parent.RESULT_KEYS | frozenset({"global_model_slot_cap", "model_slot_pool_id"})
RESULT_EXECUTION_KEYS = parent.RESULT_EXECUTION_KEYS


@dataclasses.dataclass(frozen=True)
class TaskOutcome:
    result: dict[str, Any]
    receipt: dict[str, Any] | None


def validate_activation(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    value = read_object(root / ACTIVATION)
    unsigned = dict(value)
    seal = unsigned.pop("activation_payload_sha256", None)
    if (
        value.get("role") != "v24263_model_limited_capacity_activation"
        or value.get("status") != "active"
        or value.get("protocol_sha256") != sha256(root / OUTPUT)
        or value.get("decision_contract_sha256")
        != protocol["decision_contract_sha256"]
        or value.get("control_manifest_sha256")
        != protocol["control_surface"]["manifest_sha256"]
        or value.get("forward_manifest_sha256")
        != protocol["forward_surface"]["manifest_sha256"]
        or value.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.63 activation drifted")
    return value


def task_command(
    root: Path,
    protocol: dict[str, Any],
    task_path: Path,
    result_path: Path,
    progress_path: Path,
    receipt_path: Path,
) -> list[str]:
    command = parent_task_command(
        root, protocol, task_path, result_path, progress_path
    )
    command[3] = str(root / CHILD)
    command.extend(
        [
            "--model-slot-directory",
            str(root / MODEL_SLOT_DIRECTORY),
            "--model-slot-receipt",
            str(receipt_path),
            "--model-slot-cap",
            str(MODEL_SLOT_CAP),
            "--model-slot-pool-id",
            POOL_ID,
        ]
    )
    return command


def run_one_task(
    root: Path,
    protocol: dict[str, Any],
    task: dict[str, str],
    task_root: Path,
    *,
    popen: Any = executor61.scientific.parent.subprocess.Popen,
) -> TaskOutcome:
    task_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    task_path = task_root / "visible_task.json"
    result_path = task_root / "result.json"
    progress_path = task_root / "safe_progress.json"
    receipt_path = task_root / RECEIPT_NAME
    executor61.scientific.parent._new_json(task_path, task)
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
        env=executor61.scientific.parent._child_env(),
        stdin=executor61.scientific.parent.subprocess.DEVNULL,
        stdout=executor61.scientific.parent.subprocess.DEVNULL,
        stderr=executor61.scientific.parent.subprocess.DEVNULL,
        start_new_session=True,
    )
    started = executor61.scientific.parent.time.monotonic()
    timed_out = False
    try:
        return_code = process.wait(
            timeout=float(protocol["limits"]["wall_seconds"])
            + float(protocol["execution"]["parent_deadline_grace_seconds"])
        )
    except executor61.scientific.parent.subprocess.TimeoutExpired:
        timed_out = True
        executor61.scientific.parent._terminate_group(process)
        return_code = process.returncode
    elapsed = executor61.scientific.parent.time.monotonic() - started
    receipt: dict[str, Any] | None = None
    if receipt_path.is_file() and not receipt_path.is_symlink():
        candidate = read_object(receipt_path)
        try:
            receipt = validate_receipt(candidate, expected_cap=MODEL_SLOT_CAP)
        except ValueError:
            receipt = None
    if not timed_out and return_code == 0 and result_path.is_file():
        result = read_object(result_path)
        validate_v24259_result(result)
        expected = int(result["cost"]["model"]["requests"])
        try:
            if receipt is None:
                raise ValueError("model slot receipt absent")
            validate_receipt(
                receipt,
                expected_cap=MODEL_SLOT_CAP,
                expected_acquisitions=expected,
            )
        except ValueError:
            progress = executor61.scientific.parent._safe_progress(progress_path)
            result = build_v24259_fallback_result(
                task,
                limits=ScoreFirstLimits(**dict(protocol["limits"])),
                completion_kind="worker_failure_fallback",
                failure_stage="model_slot_receipt",
                failure_type="ModelSlotReceiptInvalid",
                elapsed_seconds=elapsed,
                last_progress=progress,
            )
            validate_v24259_result(result)
            # The valid child result already owns result_path.  Preserve it as
            # raw execution evidence but return the fail-closed parent outcome.
        return TaskOutcome(result=result, receipt=receipt)
    progress = executor61.scientific.parent._safe_progress(progress_path)
    result = build_v24259_fallback_result(
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
    validate_v24259_result(result)
    if not result_path.exists():
        executor61.scientific.parent._new_json(result_path, result)
    return TaskOutcome(result=result, receipt=receipt)


def safe_task_row(position: int, outcome: TaskOutcome) -> dict[str, Any]:
    row = parent.safe_task_row(position, outcome.result)
    receipt = outcome.receipt
    valid = False
    if receipt is not None:
        try:
            validate_receipt(
                receipt,
                expected_cap=MODEL_SLOT_CAP,
                expected_acquisitions=int(
                    outcome.result["cost"]["model"]["requests"]
                ),
            )
            valid = True
        except ValueError:
            valid = False
    row.update(
        {
            "model_slot_receipt_present": receipt is not None,
            "model_slot_receipt_valid": valid,
            "model_slot_cap": (
                int(receipt["slot_cap"]) if receipt is not None else MODEL_SLOT_CAP
            ),
            "model_slot_acquisitions": (
                int(receipt["acquisitions"]) if receipt is not None else 0
            ),
            "model_slot_total_wait_seconds": (
                float(receipt["total_wait_seconds"]) if receipt is not None else 0.0
            ),
            "model_slot_max_wait_seconds": (
                float(receipt["max_wait_seconds"]) if receipt is not None else 0.0
            ),
            "model_slot_acquisition_counts": (
                list(receipt["slot_acquisition_counts"])
                if receipt is not None
                else [0] * MODEL_SLOT_CAP
            ),
        }
    )
    if not valid:
        row["infrastructure_fallback"] = True
        row["model_generated"] = False
        row["failure_types"] = sorted(
            [*row["failure_types"], "ModelSlotReceiptInvalid"]
        )
    return row


def evaluate_level(
    protocol: dict[str, Any],
    concurrency: int,
    waves: list[dict[str, Any]],
) -> dict[str, Any]:
    value = parent.evaluate_level(protocol, concurrency, waves)
    rows = [row for wave in waves for row in wave["tasks"]]
    invalid = sum(not bool(row["model_slot_receipt_valid"]) for row in rows)
    acquisitions = sum(int(row["model_slot_acquisitions"]) for row in rows)
    counts = [
        sum(int(row["model_slot_acquisition_counts"][index]) for row in rows)
        for index in range(MODEL_SLOT_CAP)
    ]
    value.update(
        {
            "model_slot_receipt_invalid_count": invalid,
            "model_slot_acquisitions": acquisitions,
            "model_slot_total_wait_seconds": round(
                sum(float(row["model_slot_total_wait_seconds"]) for row in rows),
                6,
            ),
            "model_slot_max_wait_seconds": round(
                max(
                    (float(row["model_slot_max_wait_seconds"]) for row in rows),
                    default=0.0,
                ),
                6,
            ),
            "model_slot_acquisition_counts": counts,
        }
    )
    if invalid:
        value["findings"] = sorted(
            set([*value["findings"], "model_slot_receipt_invalid"])
        )
        value["passed"] = False
    return value


def safe_progress(
    levels: list[dict[str, Any]],
    *,
    active_level: int | None,
    active_wave: int | None,
    status: str,
) -> dict[str, Any]:
    value = parent.safe_progress(
        levels,
        active_level=active_level,
        active_wave=active_wave,
        status=status,
    )
    value["role"] = PROGRESS_ROLE
    for index, level in enumerate(levels):
        value["level_summaries"][index].update(
            {
                "model_slot_receipt_invalid_count": level[
                    "model_slot_receipt_invalid_count"
                ],
                "model_slot_max_wait_seconds": level[
                    "model_slot_max_wait_seconds"
                ],
            }
        )
    value["progress_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "progress_payload_sha256"}
    )
    return value


def validate_progress(value: dict[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("progress_payload_sha256", None)
    summaries = value.get("level_summaries")
    if (
        set(value) != PROGRESS_KEYS
        or value.get("role") != PROGRESS_ROLE
        or value.get(
            "contains_question_query_url_page_prediction_answer_opaque_id_or_credential"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or not isinstance(summaries, list)
        or any(
            not isinstance(row, dict) or set(row) != PROGRESS_LEVEL_KEYS
            for row in summaries
        )
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.63 safe progress schema drifted")


def execute_ladder(
    root: Path,
    protocol: dict[str, Any],
    tasks: list[dict[str, str]],
    task_parent: Path,
    *,
    task_runner: Callable[
        [Path, dict[str, Any], dict[str, str], Path], TaskOutcome
    ] = run_one_task,
    monotonic: Callable[[], float] = time.monotonic,
    progress_writer: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    if len(tasks) != TASK_COUNT:
        raise RuntimeError("V2.42.63 task count drifted")
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
            wave_root = (
                task_parent
                / f"level_{concurrency:02d}"
                / f"wave_{wave_number:02d}"
            )
            wave_root.mkdir(mode=0o700, parents=True, exist_ok=False)
            started = monotonic()
            futures: dict[
                concurrent.futures.Future[TaskOutcome], tuple[int, int]
            ] = {}
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=concurrency,
                thread_name_prefix=f"v24263-capacity-{concurrency}",
            ) as executor:
                for slot, position in enumerate(
                    wave_spec["task_positions"], start=1
                ):
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
                    rows.append(
                        {"slot": slot, **safe_task_row(position, future.result())}
                    )
            rows.sort(key=lambda row: int(row["slot"]))
            waves.append(
                {
                    "wave": wave_number,
                    "request_count": concurrency,
                    "elapsed_seconds": round(
                        max(0.0, monotonic() - started), 6
                    ),
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
        if (
            protocol["capacity_contract"]["stop_after_first_failed_level"]
            and not summary["passed"]
        ):
            break
    return levels


def aggregate(protocol: dict[str, Any], levels: list[dict[str, Any]]) -> dict[str, Any]:
    value = parent.aggregate(protocol, levels)
    value["role"] = ROLE
    value["protocol_id"] = protocol["protocol_id"]
    value["global_model_slot_cap"] = MODEL_SLOT_CAP
    value["model_slot_pool_id"] = POOL_ID
    value["result_payload_sha256"] = payload_sha256(
        {key: item for key, item in value.items() if key != "result_payload_sha256"}
    )
    return value


def validate_result(protocol: dict[str, Any], value: dict[str, Any]) -> None:
    unsigned = dict(value)
    seal = unsigned.pop("result_payload_sha256", None)
    keys = set(value)
    if (
        keys not in (RESULT_KEYS, RESULT_KEYS | RESULT_EXECUTION_KEYS)
        or value.get("role") != ROLE
        or value.get("protocol_id") != protocol["protocol_id"]
        or value.get("global_model_slot_cap") != MODEL_SLOT_CAP
        or value.get("model_slot_pool_id") != POOL_ID
        or value.get("label_blind") is not True
        or value.get(
            "prediction_question_query_url_page_answer_opaque_id_or_credential_emitted"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("official_evaluator_called") is not False
        or value.get("paired_dev64_or_full220_launched") is not False
        or value.get("leaderboard_submission_or_sota_claim") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise RuntimeError("V2.42.63 result identity drifted")
    levels = value.get("levels")
    if not isinstance(levels, list) or not levels:
        raise RuntimeError("V2.42.63 result has no levels")
    expected_levels = list(protocol["capacity_contract"]["levels"])
    if [level.get("concurrency") for level in levels] != expected_levels[: len(levels)]:
        raise RuntimeError("V2.42.63 result level order drifted")
    for level in levels:
        if set(level) != LEVEL_KEYS:
            raise RuntimeError("V2.42.63 result level schema drifted")
        waves = level.get("waves")
        if not isinstance(waves, list) or any(
            not isinstance(wave, dict)
            or set(wave) != parent.WAVE_KEYS
            or not isinstance(wave.get("tasks"), list)
            or any(
                not isinstance(row, dict) or set(row) != TASK_ROW_KEYS
                for row in wave["tasks"]
            )
            for wave in waves
        ):
            raise RuntimeError("V2.42.63 result wave schema drifted")
        if evaluate_level(protocol, int(level["concurrency"]), waves) != level:
            raise RuntimeError("V2.42.63 result level summary drifted")
    if any(not level["passed"] for level in levels[:-1]):
        raise RuntimeError("V2.42.63 result continued past failed level")
    selected = 0
    for level in levels:
        if not level["passed"]:
            break
        selected = int(level["concurrency"])
    minimum = int(
        protocol["capacity_contract"]["gates"][
            "minimum_selected_concurrency_for_capacity_go"
        ]
    )
    if (
        value.get("selected_executor_concurrency") != selected
        or value.get("capacity_gate")
        != ("go" if selected >= minimum else "no_go")
        or value.get("total_executions")
        != sum(int(level["executions"]) for level in levels)
        or value.get("stopped_after_first_failed_level")
        is not bool(levels and not levels[-1]["passed"])
    ):
        raise RuntimeError("V2.42.63 result aggregate drifted")


def _prepare_slot_pool(root: Path) -> None:
    directory = root / MODEL_SLOT_DIRECTORY
    directory.mkdir(mode=0o700, parents=False, exist_ok=False)
    for index in range(1, MODEL_SLOT_CAP + 1):
        _new_json(
            directory / f"slot_{index:02d}.lock",
            {
                "artifact_version": 1,
                "role": "v24263_model_slot",
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
    if root != ROOT:
        raise RuntimeError("V2.42.63 executor root drifted")
    protocol_path = Path(args.protocol)
    if not protocol_path.is_absolute():
        protocol_path = root / protocol_path
    if protocol_path.resolve() != (root / OUTPUT).resolve():
        raise RuntimeError("V2.42.63 protocol path drifted")
    protocol = validate_protocol(root, OUTPUT)
    activation = validate_activation(root, protocol)
    tasks = _selected_tasks(root, protocol)
    for task in tasks:
        if set(task) != {"opaque_id", "question"}:
            raise RuntimeError("V2.42.63 runtime task boundary drifted")
    for path in (root / EXECUTION_START, root / RESULT, root / OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.42.63 execution surface is not pristine")
    start: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24263_model_limited_capacity_execution_start",
        "created_at_unix": int(time.time()),
        "protocol_sha256": sha256(protocol_path),
        "activation_sha256": sha256(root / ACTIVATION),
        "selected_opaque_ids_sha256": protocol["task_contract"][
            "selected_opaque_ids_sha256"
        ],
        "runner": {
            "pid": os.getpid(),
            "start_ticks": _start_ticks(os.getpid()),
            "marker": RUNNER_MARKER,
        },
        "global_model_slot_cap": MODEL_SLOT_CAP,
        "label_blind": True,
        "mapping_gold_category_question_type_split_evaluator_score_read": False,
        "api_called_before_execution_start": False,
    }
    start["execution_start_payload_sha256"] = payload_sha256(start)
    _new_json(root / EXECUTION_START, start)
    (root / OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
    _prepare_slot_pool(root)
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
            progress_writer=lambda value: parent._atomic_json(
                root / PROGRESS, value
            ),
        )
    result = aggregate(protocol, levels)
    result["execution_start_sha256"] = sha256(root / EXECUTION_START)
    result["activation_payload_sha256"] = activation[
        "activation_payload_sha256"
    ]
    result["result_payload_sha256"] = payload_sha256(
        {key: item for key, item in result.items() if key != "result_payload_sha256"}
    )
    validate_result(protocol, result)
    _new_json(root / RESULT, result)
    progress_value = safe_progress(
        levels, active_level=None, active_wave=None, status="complete"
    )
    validate_progress(progress_value)
    parent._atomic_json(root / PROGRESS, progress_value)
    print(
        json.dumps(
            {
                "result": str(RESULT),
                "capacity_gate": result["capacity_gate"],
                "selected_executor_concurrency": result[
                    "selected_executor_concurrency"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
