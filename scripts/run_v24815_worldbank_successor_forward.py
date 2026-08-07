#!/usr/bin/env python3
"""One-shot 12-task V2.48.15 fresh external forward."""

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
from deepwide_agent.v24686_worldbank_target_value_runtime import _unknown_table, _visible_contract  # noqa: E402
from deepwide_agent.v24804_shared_prefix_budget_ladder import ARMS  # noqa: E402
from deepwide_agent.v24812_batched_search_accounting import validate_envelope  # noqa: E402
from deepwide_agent.v24815_worldbank_successor_contract import *  # noqa: F403,E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


CHILD = CHILD_MARKER  # noqa: F405


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
        raise RuntimeError("V2.48.15 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise RuntimeError("V2.48.15 expected object")
    return value


def sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value); seal = unsigned.pop(field, None)
    return seal == payload_sha256(unsigned)  # noqa: F405


def new(path: Path, value: Any) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    except BaseException:
        temporary.unlink(missing_ok=True); raise


def progress_value(completed: int) -> dict[str, Any]:
    if isinstance(completed, bool) or not isinstance(completed, int) or not 0 <= completed <= SELECTED_COUNT:  # noqa: F405
        raise ValueError("V2.48.15 progress count drifted")
    return {
        "artifact_version": 1, "role": "v24815_content_free_safe_forward_progress",
        "selected": SELECTED_COUNT, "completed": completed,  # noqa: F405
        "unfinished": SELECTED_COUNT - completed,  # noqa: F405
        "executor_concurrency": EXECUTOR_CONCURRENCY,  # noqa: F405
        "question_query_url_page_prediction_answer_value_country_indicator_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }


def jsonl_new(path: Path, rows: list[dict[str, Any]]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        for row in rows: handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        handle.flush(); os.fsync(handle.fileno())


def environment() -> dict[str, str]:
    return {
        "HOME": os.environ.get("HOME", str(Path.home())), "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1", "PYTHONSAFEPATH": "1",
    }


def _terminate_group(process: Any) -> None:
    try: os.killpg(process.pid, 15); process.wait(timeout=2)
    except ProcessLookupError: return
    except subprocess.TimeoutExpired:
        try: os.killpg(process.pid, 9)
        except ProcessLookupError: return
        process.wait(timeout=2)


def run_task(position: int, task: dict[str, str]) -> dict[str, Any]:
    directory = ROOT / TASK_ROOT / f"task_{position:04d}"  # noqa: F405
    directory.mkdir(mode=0o700)
    new(directory / "visible_task.json", task)
    command = [
        str(ROOT / ".venv-eval/bin/python"), "-I", "-B", str(ROOT / CHILD),
        "--task", str(directory / "visible_task.json"), "--result", str(directory / "result.json"),
        "--model-slot-receipt", str(directory / "model_slot_receipt.json"),
        "--transport-health", str(directory / "transport_health.json"),
        "--terminal", str(directory / "child_terminal_receipt.json"),
    ]
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=ROOT, env=environment(), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    timed_out = False
    try: return_code = process.wait(timeout=PARENT_TIMEOUT_SECONDS)  # noqa: F405
    except subprocess.TimeoutExpired:
        timed_out = True; _terminate_group(process); return_code = process.returncode
    result = None; valid = False
    try:
        envelope = validate_envelope(read(directory / "result.json"))
        validate_model(read(directory / "model_slot_receipt.json"), expected_cap=MODEL_SLOT_CAP)  # noqa: F405
        validate_transport_health(read(directory / "transport_health.json"))
        result = envelope["result"]
        valid = return_code == 0 and not timed_out
    except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
        result = None
    parent = {
        "artifact_version": 1, "role": "v24815_content_free_parent_exit_receipt",
        "return_code": return_code, "timed_out": timed_out,
        "elapsed_seconds": round(max(0.0, time.monotonic() - started), 6),
        "task_result_valid": valid,
        "question_query_url_page_prediction_answer_value_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    parent["receipt_sha256"] = payload_sha256(parent)  # noqa: F405
    new(directory / "parent_exit_receipt.json", parent)
    return {"position": position, "task": task, "result": result, "valid": valid}


def fallback(task: dict[str, str]) -> dict[str, str]:
    prediction = _unknown_table(_visible_contract(task["question"]))
    return {arm: prediction for arm in ARMS}


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20, check=True).stdout.strip()


def _active_conflicts() -> list[int]:
    completed = subprocess.run(["ps", "-eo", "pid=,comm=,args="], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20, check=False)
    markers = (RUNNER_MARKER, CHILD_MARKER, "scripts/run_official_eval_local.py")  # noqa: F405
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) >= 3 and int(parts[0]) != os.getpid() and "python" in parts[1].casefold() and any(marker in parts[2] for marker in markers):
            output.append(int(parts[0]))
    return sorted(output)


def main() -> None:
    protocol, preaudit, activation, start = (read(ROOT / path) for path in (PROTOCOL, PREAUDIT, ACTIVATION, EXECUTION_START))  # noqa: F405
    protocol = validate_protocol(ROOT, protocol)  # noqa: F405
    if _git("rev-parse", "HEAD") != _git("rev-parse", "target/main") or _git("status", "--porcelain"):
        raise RuntimeError("V2.48.15 launch requires clean pushed HEAD")
    if (
        not sealed(preaudit, "audit_payload_sha256") or not sealed(activation, "activation_payload_sha256")
        or not sealed(start, "execution_start_payload_sha256") or preaudit.get("audit_valid") is not True
        or activation.get("status") != "activated_not_started" or start.get("status") != "authorized_not_started"
        or start.get("authorization") != {"single_smoke_forward": True, "evaluator": False, "public_dev64_or_exact220": False, "retry_resume_skip_or_selective_rerun": False}
        or any(sha256(ROOT / path) != digest for path, digest in protocol["dependency_manifest"].items())  # noqa: F405
        or _active_conflicts()
    ):
        raise RuntimeError("V2.48.15 launch authorization drifted")
    tasks = validate_task_vector(protocol["visible_tasks"])  # noqa: F405
    if protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]:  # noqa: F405
        raise RuntimeError("V2.48.15 protected watcher drifted")
    for path in (ROOT / OUTPUT_ROOT, ROOT / FORWARD_RESULT):  # noqa: F405
        if path.exists() or path.is_symlink(): raise RuntimeError("V2.48.15 forward surface not pristine")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2): pass
    with acquire_deepwide_api_lease(ROOT, owner=LEASE_OWNER, purpose=LEASE_PURPOSE, path=ROOT / LEASE_PATH):  # noqa: F405
        (ROOT / OUTPUT_ROOT).mkdir(mode=0o700, parents=True)  # noqa: F405
        (ROOT / MODEL_SLOT_DIRECTORY).mkdir(mode=0o700)  # noqa: F405
        for index in range(1, MODEL_SLOT_CAP + 1): (ROOT / MODEL_SLOT_DIRECTORY / f"slot_{index:02d}.lock").touch(mode=0o600)  # noqa: F405
        (ROOT / TASK_ROOT).mkdir(mode=0o700)  # noqa: F405
        started = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as executor:  # noqa: F405
            futures = [executor.submit(run_task, index, task) for index, task in enumerate(tasks, 1)]
            outcomes = []
            for future in concurrent.futures.as_completed(futures):
                outcomes.append(future.result()); atomic_json(ROOT / SAFE_PROGRESS, progress_value(len(outcomes)))  # noqa: F405
        wall = max(0.0, time.monotonic() - started)
    outcomes.sort(key=lambda item: item["position"])
    rows = []; decision_counts: dict[str, int] = {}
    for item in outcomes:
        predictions = item["result"]["predictions"] if item["valid"] else fallback(item["task"])
        if item["valid"]:
            decision = item["result"]["adaptive_decision"]["decision"]
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
        rows.append({
            "opaque_id": item["task"]["opaque_id"], "predictions": predictions,
            "prediction_sha256": {arm: hashlib.sha256(predictions[arm].encode()).hexdigest() for arm in ARMS},
            "runtime_result_valid": item["valid"],
            "shared_prefix_sha256": item["result"]["shared_prefix"]["prefix_sha256"] if item["valid"] else None,
        })
    jsonl_new(ROOT / PREDICTIONS, rows)  # noqa: F405
    summary = {
        "artifact_version": 1, "role": "v24815_forward_run_summary", "protocol_id": PROTOCOL_ID,  # noqa: F405
        "selected_tasks": SELECTED_COUNT, "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT,  # noqa: F405
        "valid_task_results": sum(item["valid"] for item in outcomes),
        "projected_failure_tasks": sum(not item["valid"] for item in outcomes),
        "adaptive_decision_counts": dict(sorted(decision_counts.items())),
        "forward_wall_seconds": round(wall, 6), "resume_retry_skip_or_selective_rerun": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    summary["summary_payload_sha256"] = payload_sha256(summary); new(ROOT / RUN_SUMMARY, summary)  # noqa: F405
    freeze = {
        "artifact_version": 1, "role": "v24815_prediction_freeze", "protocol_id": PROTOCOL_ID,  # noqa: F405
        "selected_tasks": SELECTED_COUNT, "selected_arm_predictions": SELECTED_COUNT * ARM_COUNT,  # noqa: F405
        "predictions_sha256": sha256(ROOT / PREDICTIONS), "run_summary_sha256": sha256(ROOT / RUN_SUMMARY),  # noqa: F405
        "all_predictions_terminal_before_private_population_or_evaluator_open": True,
        "private_population_gold_or_evaluator_opened_or_hashed": False,
    }
    freeze["freeze_payload_sha256"] = payload_sha256(freeze); new(ROOT / PREDICTION_FREEZE, freeze)  # noqa: F405
    forward = {
        "artifact_version": 1, "role": "v24815_forward_result", "protocol_id": PROTOCOL_ID,  # noqa: F405
        "created_at_unix": int(time.time()), "selected_tasks": SELECTED_COUNT,  # noqa: F405
        "terminal_arm_predictions": SELECTED_COUNT * ARM_COUNT,  # noqa: F405
        "prediction_freeze_sha256": sha256(ROOT / PREDICTION_FREEZE), "run_summary_sha256": sha256(ROOT / RUN_SUMMARY),  # noqa: F405
        "all_predictions_terminal_before_private_population_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "evaluator_called": False, "resume_retry_skip_or_selective_rerun": False,
    }
    forward["result_payload_sha256"] = payload_sha256(forward); new(ROOT / FORWARD_RESULT, forward)  # noqa: F405


if __name__ == "__main__": main()
