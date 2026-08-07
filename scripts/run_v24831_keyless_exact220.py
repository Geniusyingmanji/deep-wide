#!/usr/bin/env python3
"""Run one fresh label-blind V2.48.31 keyless exact-220 forward."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24831_keyless_exact220_contract as contract  # noqa: E402
from scripts import run_v24635_exact220 as algorithm  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402


def configure_algorithm() -> None:
    bindings = {
        "PROTOCOL_ID": contract.PROTOCOL_ID,
        "CHILD_MARKER": contract.CHILD_MARKER,
        "OUTPUT_ROOT": contract.OUTPUT_ROOT,
        "MODEL_SLOT_DIRECTORY": contract.MODEL_SLOT_DIRECTORY,
        "TASK_ROOT": contract.TASK_ROOT,
        "RUNTIME_PREDICTIONS": contract.RUNTIME_PREDICTIONS,
        "RUN_SUMMARY": contract.RUN_SUMMARY,
        "PREDICTION_FREEZE": contract.PREDICTION_FREEZE,
        "SAFE_PROGRESS": contract.SAFE_PROGRESS,
    }
    for name, value in bindings.items():
        setattr(algorithm, name, value)


def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.48.31 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.48.31 expected JSON object")
    return value


def _sealed(value: dict, field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def validate_execution_start(root: Path, protocol: dict) -> dict:
    audit = _read(root / contract.PREAUDIT)
    start = _read(root / contract.EXECUTION_START)
    if (
        audit.get("role") != "v24831_keyless_exact220_preactivation_audit"
        or audit.get("audit_valid") is not True
        or audit.get("findings") != []
        or audit.get("authorization", {}).get("execution_start_generation") is not True
        or not _sealed(audit, "audit_payload_sha256")
        or start.get("role") != "v24831_keyless_exact220_execution_start"
        or start.get("status") != "authorized_not_started"
        or start.get("protocol_sha256") != contract.sha256(root / contract.PROTOCOL)
        or start.get("preactivation_audit_sha256")
        != contract.sha256(root / contract.PREAUDIT)
        or start.get("dependency_manifest_sha256")
        != protocol["dependency_manifest_sha256"]
        or start.get("runtime_input_contract") != ["opaque_id", "question"]
        or start.get("protected_watchers")
        != protocol["execution"]["protected_watchers"]
        or start.get("authorization")
        != {
            "single_fresh_exact220_forward": True,
            "evaluator_call": False,
            "retry_resume_skip_or_selective_rerun": False,
        }
        or start.get("first_network_model_search_or_fetch_effect_started") is not False
        or not _sealed(start, "execution_start_payload_sha256")
    ):
        raise RuntimeError("V2.48.31 execution authorization drifted")
    return start


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
        "scripts/run_v24791_exact220.py",
        "scripts/run_v24791_exact220_task.py",
        "scripts/run_v24635_exact220.py",
        "scripts/run_v24635_exact220_task.py",
        "scripts/run_official_eval_local.py",
    )
    output = []
    for line in completed.stdout.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or "python" not in parts[1].casefold():
            continue
        pid = int(parts[0])
        if pid != os.getpid() and any(marker in parts[2] for marker in markers):
            output.append(pid)
    return sorted(output)


def _progress(completed: int) -> dict:
    value = {
        "artifact_version": 1,
        "role": "v24831_keyless_exact220_safe_forward_progress",
        "created_at_unix": int(time.time()),
        "selected": contract.SELECTED_COUNT,
        "completed": completed,
        "unfinished": contract.SELECTED_COUNT - completed,
        "executor_concurrency": contract.EXECUTOR_CONCURRENCY,
        "model_slot_cap": contract.MODEL_SLOT_CAP,
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    value["progress_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    configure_algorithm()
    root = ROOT
    protocol = contract.validate_protocol(root, _read(root / contract.PROTOCOL))
    start = validate_execution_start(root, protocol)
    tasks = contract.task_vector(root, protocol)
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=True,
    ).stdout.strip()
    remote = subprocess.run(
        ["git", "rev-parse", "target/main"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=True,
    ).stdout.strip()
    if head != remote or dirty:
        raise RuntimeError("V2.48.31 launch requires clean pushed HEAD")
    required = (
        contract.PROTOCOL,
        contract.PREAUDIT,
        contract.EXECUTION_START,
        *map(Path, protocol["dependency_manifest"]),
    )
    if any(
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode
        != 0
        for path in required
    ):
        raise RuntimeError("V2.48.31 launch dependency is not tracked")
    conflicts = _active_conflicts()
    if conflicts:
        raise RuntimeError(f"V2.48.31 conflicting benchmark/evaluator active: {conflicts}")
    with socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    for path in (root / contract.FORWARD_RESULT, root / contract.OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.48.31 forward surface is not pristine")
    with acquire_deepwide_api_lease(
        root,
        owner=contract.LEASE_OWNER,
        purpose=contract.LEASE_PURPOSE,
        path=root / contract.LEASE_PATH,
    ):
        if (
            contract.protected_watcher_snapshot()
            != protocol["execution"]["protected_watchers"]
        ):
            raise RuntimeError("V2.48.31 protected watcher drifted before effect")
        (root / contract.OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        algorithm._prepare_slots(root)
        (root / contract.TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        outcomes = algorithm.execute_forward(
            root,
            protocol,
            tasks,
            progress_writer=lambda value: algorithm._atomic_json(
                root / contract.SAFE_PROGRESS,
                _progress(int(value["completed"])),
            ),
        )
        wall = max(0.0, time.monotonic() - started)
    rows = [algorithm._runtime_row(item.result) for item in outcomes]
    algorithm._write_jsonl_new(root / contract.RUNTIME_PREDICTIONS, rows)
    summary = algorithm._summary(outcomes, wall)
    summary["role"] = "v24831_keyless_exact220_run_summary"
    summary["protocol_id"] = contract.PROTOCOL_ID
    summary.pop("summary_payload_sha256", None)
    summary["summary_payload_sha256"] = contract.payload_sha256(summary)
    algorithm._new_json(root / contract.RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24831_keyless_exact220_prediction_freeze",
        "protocol_id": contract.PROTOCOL_ID,
        "selected": contract.SELECTED_COUNT,
        "terminal": contract.SELECTED_COUNT,
        "runtime_predictions_sha256": contract.sha256(
            root / contract.RUNTIME_PREDICTIONS
        ),
        "run_summary_sha256": contract.sha256(root / contract.RUN_SUMMARY),
        "prediction_hashes_sha256": contract.payload_sha256(
            [row["prediction_sha256"] for row in rows]
        ),
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_or_evaluator_opened_or_hashed": False,
        "label_blind": True,
    }
    freeze["freeze_payload_sha256"] = contract.payload_sha256(freeze)
    algorithm._new_json(root / contract.PREDICTION_FREEZE, freeze)
    forward = {
        "artifact_version": 1,
        "role": "v24831_keyless_exact220_forward_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected": contract.SELECTED_COUNT,
        "terminal_predictions": contract.SELECTED_COUNT,
        "model_generated_tables": summary["model_generated_tables"],
        "fallback_tables": summary["fallback_tables"],
        "system_total_tokens": summary["system_total_tokens"],
        "forward_wall_seconds": summary["forward_wall_seconds"],
        "prediction_freeze_sha256": contract.sha256(
            root / contract.PREDICTION_FREEZE
        ),
        "run_summary_sha256": contract.sha256(root / contract.RUN_SUMMARY),
        "execution_start_sha256": contract.sha256(root / contract.EXECUTION_START),
        "execution_start_payload_sha256": start[
            "execution_start_payload_sha256"
        ],
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "official_evaluator_called": False,
        "retry_resume_skip_or_selective_rerun_launched": False,
    }
    forward["result_payload_sha256"] = contract.payload_sha256(forward)
    algorithm._new_json(root / contract.FORWARD_RESULT, forward)
    algorithm._atomic_json(
        root / contract.SAFE_PROGRESS, _progress(contract.SELECTED_COUNT)
    )
    print(
        json.dumps(
            {
                "terminal": contract.SELECTED_COUNT,
                "wall_seconds": wall,
                "fallback_tables": summary["fallback_tables"],
                "forward_result": str(contract.FORWARD_RESULT),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
