#!/usr/bin/env python3
"""One-shot 12-task V2.46.71 external forward; no evaluator capability."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24312_deadline_reliability import validate_receipt as validate_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24637_objective_alignment_runtime import _fallback  # noqa: E402
from deepwide_agent.v24639_ror_objective_runtime import EXPECTED_COLUMNS, extract_visible_entities  # noqa: E402
from deepwide_agent.v24668_visible_surface_information_gain_runtime import ARMS  # noqa: E402
from deepwide_agent.v24671_runner_integration import validate_envelope  # noqa: E402
from deepwide_agent.v24671_ror_external_contract import (  # noqa: E402
    ACTIVATION,
    ARM_COUNT,
    EXECUTION_START,
    EXECUTOR_CONCURRENCY,
    FORWARD_RESULT,
    LEASE_OWNER,
    LEASE_PATH,
    LEASE_PURPOSE,
    MODEL_SLOT_CAP,
    MODEL_SLOT_DIRECTORY,
    OUTPUT_ROOT,
    PARENT_TIMEOUT_SECONDS,
    PREDICTION_FREEZE,
    PREDICTIONS,
    PREAUDIT,
    PROTOCOL,
    PROTOCOL_ID,
    RUN_SUMMARY,
    SELECTED_COUNT,
    TASK_ROOT,
    payload_sha256,
    protected_watcher_snapshot,
    sha256,
    task_vector,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


CHILD = "scripts/run_v24671_ror_task.py"


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.46.71 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.46.71 expected object")
    return value


def sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)


def new(path: Path, value: Any) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def jsonl_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def environment() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }


def run_task(position: int, task: dict[str, str]) -> dict[str, Any]:
    directory = ROOT / TASK_ROOT / f"task_{position:04d}"
    directory.mkdir(mode=0o700)
    new(directory / "visible_task.json", task)
    command = [
        str(ROOT / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(ROOT / CHILD),
        "--task",
        str(directory / "visible_task.json"),
        "--result",
        str(directory / "result.json"),
        "--model-slot-receipt",
        str(directory / "model_slot_receipt.json"),
        "--transport-health",
        str(directory / "transport_health.json"),
        "--terminal",
        str(directory / "child_terminal_receipt.json"),
    ]
    started = time.monotonic()
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=environment(),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    timed_out = False
    try:
        return_code = process.wait(timeout=PARENT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, 15)
            process.wait(timeout=2)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, 9)
            except ProcessLookupError:
                pass
            process.wait(timeout=2)
        return_code = process.returncode
    result = None
    valid = False
    try:
        envelope = validate_envelope(read(directory / "result.json"))
        validate_model(
            read(directory / "model_slot_receipt.json"),
            expected_cap=MODEL_SLOT_CAP,
        )
        validate_transport_health(read(directory / "transport_health.json"))
        result = envelope["result"]
        valid = return_code == 0 and not timed_out
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        result = None
    parent = {
        "artifact_version": 1,
        "role": "v24671_content_free_parent_exit_receipt",
        "return_code": return_code,
        "timed_out": timed_out,
        "elapsed_seconds": round(max(0.0, time.monotonic() - started), 6),
        "task_result_valid": valid,
        "question_query_url_page_prediction_answer_entity_gold_or_credential_emitted": False,
        "mapping_gold_ror_id_country_code_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    parent["receipt_sha256"] = payload_sha256(parent)
    new(directory / "parent_exit_receipt.json", parent)
    return {"position": position, "task": task, "result": result, "valid": valid}


def fallback(task: dict[str, str]) -> dict[str, str]:
    entities = extract_visible_entities(task["question"])
    prediction = _fallback(task["question"], EXPECTED_COLUMNS, entities)
    return {arm: prediction for arm in ARMS}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def main() -> None:
    protocol, preaudit, activation, start = (
        read(ROOT / path)
        for path in (PROTOCOL, PREAUDIT, ACTIVATION, EXECUTION_START)
    )
    if _git("rev-parse", "HEAD") != _git("rev-parse", "target/main") or _git(
        "status", "--porcelain"
    ):
        raise RuntimeError("V2.46.71 launch requires clean pushed HEAD")
    manifest = protocol.get("dependency_manifest")
    tasks = task_vector()
    ids = [task["opaque_id"] for task in tasks]
    questions = [task["question"] for task in tasks]
    if (
        protocol.get("protocol_id") != PROTOCOL_ID
        or any(
            not sealed(value, field)
            for value, field in (
                (protocol, "protocol_sha256"),
                (preaudit, "audit_sha256"),
                (activation, "activation_sha256"),
                (start, "execution_start_sha256"),
            )
        )
        or any(
            value.get("launch_authorized") is not True
            for value in (preaudit, activation, start)
        )
        or start.get("authorization")
        != {
            "one_external_forward_launch": True,
            "evaluator": False,
            "dev64": False,
            "exact220": False,
        }
        or not isinstance(manifest, dict)
        or protocol.get("dependency_manifest_sha256") != payload_sha256(manifest)
        or any(sha256(ROOT / path) != digest for path, digest in manifest.items())
        or protocol.get("task_contract", {}).get("selected_ids_sha256")
        != payload_sha256(ids)
        or protocol.get("task_contract", {}).get("visible_question_vector_sha256")
        != payload_sha256(questions)
    ):
        raise RuntimeError("V2.46.71 authorization drifted")
    if protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        raise RuntimeError("V2.46.71 watcher drifted")
    for path in (ROOT / OUTPUT_ROOT, ROOT / FORWARD_RESULT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.46.71 surface not pristine")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2):
        pass
    with acquire_deepwide_api_lease(
        ROOT,
        owner=LEASE_OWNER,
        purpose=LEASE_PURPOSE,
        path=ROOT / LEASE_PATH,
    ):
        (ROOT / OUTPUT_ROOT).mkdir(mode=0o700, parents=True)
        (ROOT / MODEL_SLOT_DIRECTORY).mkdir(mode=0o700)
        for index in range(1, MODEL_SLOT_CAP + 1):
            (ROOT / MODEL_SLOT_DIRECTORY / f"slot_{index:02d}.lock").touch(mode=0o600)
        (ROOT / TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=EXECUTOR_CONCURRENCY
        ) as executor:
            futures = [
                executor.submit(run_task, index, task)
                for index, task in enumerate(tasks, 1)
            ]
            outcomes = [future.result() for future in futures]
        wall = max(0.0, time.monotonic() - started)
    outcomes.sort(key=lambda item: item["position"])
    rows = []
    for item in outcomes:
        predictions = (
            item["result"]["predictions"] if item["valid"] else fallback(item["task"])
        )
        rows.append(
            {
                "opaque_id": item["task"]["opaque_id"],
                "predictions": predictions,
                "prediction_sha256": {
                    arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
                    for arm in ARMS
                },
                "runtime_result_valid": item["valid"],
            }
        )
    jsonl_new(ROOT / PREDICTIONS, rows)
    summary = {
        "artifact_version": 1,
        "role": "v24671_forward_run_summary",
        "selected_tasks": SELECTED_COUNT,
        "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT,
        "valid_task_results": sum(item["valid"] for item in outcomes),
        "projected_failure_tasks": sum(not item["valid"] for item in outcomes),
        "forward_wall_seconds": round(wall, 6),
        "resume_retry_skip_or_selective_rerun": False,
        "mapping_gold_ror_id_country_code_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    summary["summary_sha256"] = payload_sha256(summary)
    new(ROOT / RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24671_ror_prediction_freeze",
        "protocol_id": PROTOCOL_ID,
        "selected_tasks": SELECTED_COUNT,
        "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT,
        "predictions_sha256": sha256(ROOT / PREDICTIONS),
        "run_summary_sha256": sha256(ROOT / RUN_SUMMARY),
        "all_predictions_terminal_before_gold_or_evaluator_open": True,
        "gold_path_opened_or_hashed": False,
        "mapping_gold_ror_id_country_code_evaluator_score_or_reward_read": False,
    }
    freeze["freeze_sha256"] = payload_sha256(freeze)
    new(ROOT / PREDICTION_FREEZE, freeze)
    forward = {
        "artifact_version": 1,
        "role": "v24671_information_gain_forward_result",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected_tasks": SELECTED_COUNT,
        "terminal_arm_predictions": SELECTED_COUNT * ARM_COUNT,
        "prediction_freeze_sha256": sha256(ROOT / PREDICTION_FREEZE),
        "run_summary_sha256": sha256(ROOT / RUN_SUMMARY),
        "execution_start_sha256": sha256(ROOT / EXECUTION_START),
        "all_predictions_terminal_before_gold_or_evaluator_open": True,
        "mapping_gold_ror_id_country_code_category_question_type_split_evaluator_score_or_reward_read": False,
        "official_benchmark_evaluator_called": False,
        "resume_retry_skip_or_selective_rerun": False,
    }
    forward["result_sha256"] = payload_sha256(forward)
    new(ROOT / FORWARD_RESULT, forward)
    print(
        json.dumps(
            {"terminal": SELECTED_COUNT * ARM_COUNT, "wall_seconds": wall},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
