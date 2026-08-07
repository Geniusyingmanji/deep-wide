#!/usr/bin/env python3
"""One-shot 32-task V2.48.24 quality-first external forward."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24824_quality_first_external_contract as contract  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    validate_receipt as validate_model,
)
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    validate_transport_health,
)
from deepwide_agent.v24686_worldbank_target_value_runtime import (  # noqa: E402
    _unknown_table,
    _visible_contract,
)
from deepwide_agent.v24819_quality_first_controller import ARMS  # noqa: E402
from deepwide_agent.v24823_quality_first_accounting import (  # noqa: E402
    validate_envelope,
)
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


def read(path: Path) -> dict[str, Any]:
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(ROOT.resolve())
    ):
        raise RuntimeError("V2.48.24 expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.24 expected object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


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


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def progress_value(completed: int) -> dict[str, Any]:
    if (
        isinstance(completed, bool)
        or not isinstance(completed, int)
        or not 0 <= completed <= contract.SELECTED_COUNT
    ):
        raise ValueError("V2.48.24 progress count drifted")
    return {
        "artifact_version": 1,
        "role": "v24824_content_free_safe_forward_progress",
        "selected": contract.SELECTED_COUNT,
        "completed": completed,
        "unfinished": contract.SELECTED_COUNT - completed,
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "question_query_url_page_prediction_answer_value_country_indicator_opaque_id_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }


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


def _terminate_group(process: Any) -> None:
    try:
        os.killpg(process.pid, 15)
        process.wait(timeout=2)
    except ProcessLookupError:
        return
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, 9)
        except ProcessLookupError:
            return
        process.wait(timeout=2)


def run_task(position: int, task: dict[str, str]) -> dict[str, Any]:
    directory = ROOT / contract.TASK_ROOT / f"task_{position:04d}"
    directory.mkdir(mode=0o700)
    new(directory / "visible_task.json", task)
    command = [
        str(ROOT / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(ROOT / contract.CHILD_MARKER),
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
        return_code = process.wait(timeout=contract.PARENT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_group(process)
        return_code = process.returncode
    result = None
    valid = False
    try:
        envelope = validate_envelope(read(directory / "result.json"))
        validate_model(
            read(directory / "model_slot_receipt.json"),
            expected_cap=contract.MODEL_SLOT_CAP,
        )
        validate_transport_health(read(directory / "transport_health.json"))
        result = envelope["result"]
        valid = return_code == 0 and not timed_out
    except (
        KeyError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        result = None
    parent = {
        "artifact_version": 1,
        "role": "v24824_content_free_parent_exit_receipt",
        "return_code": return_code,
        "timed_out": timed_out,
        "elapsed_seconds": round(max(0.0, time.monotonic() - started), 6),
        "task_result_valid": valid,
        "question_query_url_page_prediction_answer_value_or_credential_emitted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    parent["receipt_sha256"] = contract.payload_sha256(parent)
    new(directory / "parent_exit_receipt.json", parent)
    return {"position": position, "task": task, "result": result, "valid": valid}


def fallback(task: Mapping[str, str]) -> dict[str, str]:
    prediction = _unknown_table(_visible_contract(task["question"]))
    return {arm: prediction for arm in ARMS}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
        check=True,
    ).stdout.strip()


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
    markers = (
        contract.RUNNER_MARKER,
        contract.CHILD_MARKER,
        "scripts/run_official_eval_local.py",
    )
    output = []
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


def main() -> None:
    protocol, preaudit, activation, start = (
        read(ROOT / path)
        for path in (
            contract.PROTOCOL,
            contract.PREAUDIT,
            contract.ACTIVATION,
            contract.EXECUTION_START,
        )
    )
    protocol = contract.validate_protocol(ROOT, protocol)
    if (
        _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
        or _git("status", "--porcelain")
    ):
        raise RuntimeError("V2.48.24 launch requires clean pushed HEAD")
    if (
        not sealed(preaudit, "audit_payload_sha256")
        or not sealed(activation, "activation_payload_sha256")
        or not sealed(start, "execution_start_payload_sha256")
        or preaudit.get("audit_valid") is not True
        or activation.get("status") != "activated_not_started"
        or start.get("status") != "authorized_not_started"
        or start.get("authorization")
        != {
            "single_external_forward": True,
            "evaluator": False,
            "public_dev64_or_exact220": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
        or any(
            contract.sha256(ROOT / path) != digest
            for path, digest in protocol["dependency_manifest"].items()
        )
        or _active_conflicts()
    ):
        raise RuntimeError("V2.48.24 launch authorization drifted")
    tasks = contract.validate_task_vector(protocol["visible_tasks"])
    if contract.protected_watcher_snapshot() != protocol["execution"][
        "protected_watchers"
    ]:
        raise RuntimeError("V2.48.24 protected watcher drifted")
    for path in (ROOT / contract.OUTPUT_ROOT, ROOT / contract.FORWARD_RESULT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.48.24 forward surface not pristine")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2):
        pass
    with acquire_deepwide_api_lease(
        ROOT,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=ROOT / contract.LEASE_PATH,
    ):
        (ROOT / contract.OUTPUT_ROOT).mkdir(mode=0o700, parents=True)
        (ROOT / contract.MODEL_SLOT_DIRECTORY).mkdir(mode=0o700)
        for index in range(1, contract.MODEL_SLOT_CAP + 1):
            (ROOT / contract.MODEL_SLOT_DIRECTORY / f"slot_{index:02d}.lock").touch(
                mode=0o600
            )
        (ROOT / contract.TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=contract.EXECUTOR_CONCURRENCY
        ) as executor:
            futures = [
                executor.submit(run_task, index, task)
                for index, task in enumerate(tasks, 1)
            ]
            outcomes = []
            for future in concurrent.futures.as_completed(futures):
                outcomes.append(future.result())
                atomic_json(
                    ROOT / contract.SAFE_PROGRESS,
                    progress_value(len(outcomes)),
                )
        wall = max(0.0, time.monotonic() - started)
    outcomes.sort(key=lambda item: item["position"])
    rows = []
    decision_counts: dict[str, int] = {}
    adaptive_equals_fixed = 0
    for item in outcomes:
        predictions = (
            item["result"]["predictions"] if item["valid"] else fallback(item["task"])
        )
        if item["valid"]:
            decision = item["result"]["adaptive_decision"]["decision"]
            decision_counts[decision] = decision_counts.get(decision, 0) + 1
        if predictions["coverage_risk_adaptive"] == predictions["fixed_full_budget"]:
            adaptive_equals_fixed += 1
        rows.append(
            {
                "opaque_id": item["task"]["opaque_id"],
                "predictions": predictions,
                "prediction_sha256": {
                    arm: hashlib.sha256(predictions[arm].encode()).hexdigest()
                    for arm in ARMS
                },
                "runtime_result_valid": item["valid"],
                "shared_prefix_sha256": (
                    item["result"]["shared_prefix"]["prefix_sha256"]
                    if item["valid"]
                    else None
                ),
            }
        )
    jsonl_new(ROOT / contract.PREDICTIONS, rows)
    summary = {
        "artifact_version": 1,
        "role": "v24824_forward_run_summary",
        "protocol_id": contract.PROTOCOL_ID,
        "selected_tasks": contract.SELECTED_COUNT,
        "selected_arm_predictions": contract.SELECTED_COUNT * contract.ARM_COUNT,
        "valid_task_results": sum(item["valid"] for item in outcomes),
        "projected_failure_tasks": sum(not item["valid"] for item in outcomes),
        "adaptive_decision_counts": dict(sorted(decision_counts.items())),
        "adaptive_prediction_equals_fixed_full_count": adaptive_equals_fixed,
        "forward_wall_seconds": round(wall, 6),
        "resume_retry_skip_or_selective_rerun": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }
    summary["summary_payload_sha256"] = contract.payload_sha256(summary)
    new(ROOT / contract.RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24824_prediction_freeze",
        "protocol_id": contract.PROTOCOL_ID,
        "selected_tasks": contract.SELECTED_COUNT,
        "selected_arm_predictions": contract.SELECTED_COUNT * contract.ARM_COUNT,
        "predictions_sha256": contract.sha256(ROOT / contract.PREDICTIONS),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "all_predictions_terminal_before_private_population_or_evaluator_open": True,
        "private_population_gold_or_evaluator_opened_or_hashed": False,
    }
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    new(ROOT / contract.PREDICTION_FREEZE, freeze)
    forward = {
        "artifact_version": 1,
        "role": "v24824_forward_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected_tasks": contract.SELECTED_COUNT,
        "terminal_arm_predictions": contract.SELECTED_COUNT * contract.ARM_COUNT,
        "prediction_freeze_sha256": contract.sha256(
            ROOT / contract.PREDICTION_FREEZE
        ),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "all_predictions_terminal_before_private_population_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "evaluator_called": False,
        "resume_retry_skip_or_selective_rerun": False,
    }
    forward["result_payload_sha256"] = contract.payload_sha256(forward)
    new(ROOT / contract.FORWARD_RESULT, forward)


if __name__ == "__main__":
    main()
