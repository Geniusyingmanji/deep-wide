#!/usr/bin/env python3
"""Direct, non-monkeypatch V2.42.61 executor for the normalizer smoke16."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


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
from scripts import run_v24259_score_first_smoke as scientific  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


DEFAULT_PROTOCOL = Path(
    "results/v24261_direct_executor_smoke_preregistration_v1_20260802.json"
)
ROLE = "v24261_direct_executor_smoke_result"
RUNNER_MARKER = "scripts/run_v24261_score_first_smoke.py"
CHILD = "scripts/v24260_successor/run_v24259_score_first_task.py"


def validate_protocol(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    if (
        value.get("role") != "v24261_direct_executor_smoke_preregistration"
        or value.get("protocol_id") != "v24261_direct_executor_smoke16_v1"
        or value.get("label_blind") is not True
        or not scientific.parent._sealed(value, "decision_contract_sha256")
    ):
        raise RuntimeError("V2.42.61 protocol identity drifted")
    manifest = value.get("control_surface", {}).get("manifest") or {}
    live: dict[str, str] = {}
    for name, expected in manifest.items():
        relative = scientific.parent._relative(name)
        path = root / relative
        if path.is_symlink() or not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"V2.42.61 control source drifted: {relative}")
        live[str(relative)] = expected
    if payload_sha256(live) != value["control_surface"].get("manifest_sha256"):
        raise RuntimeError("V2.42.61 control manifest drifted")
    return value


def validate_activation(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    value = scientific.parent.read_object(
        root / scientific.parent._relative(protocol["execution"]["activation_path"])
    )
    if (
        value.get("role") != "v24261_direct_executor_smoke_activation"
        or value.get("status") != "active"
        or value.get("protocol_sha256") != sha256(root / DEFAULT_PROTOCOL)
        or value.get("control_manifest_sha256")
        != protocol["control_surface"]["manifest_sha256"]
        or not scientific.parent._sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.61 activation drifted")
    return value


def task_command(root, protocol, task_path, result_path, progress_path):
    command = scientific._task_command(
        root, protocol, task_path, result_path, progress_path
    )
    command[3] = str(root / CHILD)
    return command


def run_one_task(
    root: Path,
    protocol: dict[str, Any],
    task: dict[str, str],
    task_root: Path,
    *,
    popen: Any = scientific.parent.subprocess.Popen,
) -> dict[str, Any]:
    task_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    task_path = task_root / "visible_task.json"
    result_path = task_root / "result.json"
    progress_path = task_root / "safe_progress.json"
    scientific.parent._new_json(task_path, task)
    process = popen(
        task_command(root, protocol, task_path, result_path, progress_path),
        cwd=root,
        env=scientific.parent._child_env(),
        stdin=scientific.parent.subprocess.DEVNULL,
        stdout=scientific.parent.subprocess.DEVNULL,
        stderr=scientific.parent.subprocess.DEVNULL,
        start_new_session=True,
    )
    started = scientific.parent.time.monotonic()
    timed_out = False
    try:
        return_code = process.wait(
            timeout=float(protocol["limits"]["wall_seconds"])
            + float(protocol["execution"]["parent_deadline_grace_seconds"])
        )
    except scientific.parent.subprocess.TimeoutExpired:
        timed_out = True
        scientific.parent._terminate_group(process)
        return_code = process.returncode
    elapsed = scientific.parent.time.monotonic() - started
    if not timed_out and return_code == 0 and result_path.is_file():
        result = scientific.parent.read_object(result_path)
        validate_v24259_result(result)
        return result
    progress = scientific.parent._safe_progress(progress_path)
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
    scientific.parent._new_json(result_path, result)
    return result


def aggregate_results(protocol, results):
    value = scientific.aggregate_results(protocol, results)
    value["role"] = ROLE
    value["protocol_id"] = protocol["protocol_id"]
    value["result_payload_sha256"] = payload_sha256(
        {k: v for k, v in value.items() if k != "result_payload_sha256"}
    )
    return value


def main() -> None:
    parser = scientific.parent.argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    protocol_path = Path(args.protocol)
    if not protocol_path.is_absolute():
        protocol_path = root / protocol_path
    if root != ROOT or protocol_path.resolve() != (root / DEFAULT_PROTOCOL).resolve():
        raise RuntimeError("V2.42.61 executor path drifted")
    protocol = validate_protocol(root, scientific.parent.read_object(protocol_path))
    activation = validate_activation(root, protocol)
    tasks = scientific.parent._selected_tasks(root, protocol)
    execution = protocol["execution"]
    output_root = root / scientific.parent._relative(execution["output_root"])
    start_path = root / scientific.parent._relative(execution["execution_start_path"])
    result_path = root / scientific.parent._relative(execution["result_path"])
    predictions_path = output_root / "runtime_predictions.jsonl"
    if any(path.exists() or path.is_symlink() for path in (output_root, start_path, result_path)):
        raise RuntimeError("V2.42.61 execution surface is not pristine")
    start: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24261_direct_executor_smoke_execution_start",
        "created_at_unix": int(scientific.parent.time.time()),
        "protocol_sha256": sha256(protocol_path),
        "activation_sha256": sha256(
            root / scientific.parent._relative(execution["activation_path"])
        ),
        "selected_opaque_ids_sha256": protocol["task_contract"][
            "selected_opaque_ids_sha256"
        ],
        "runner": {
            "pid": scientific.parent.os.getpid(),
            "start_ticks": scientific.parent._start_ticks(scientific.parent.os.getpid()),
            "marker": RUNNER_MARKER,
        },
        "label_blind": True,
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "api_called_before_execution_start": False,
    }
    start["execution_start_payload_sha256"] = payload_sha256(start)
    scientific.parent._new_json(start_path, start)
    output_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    task_parent = output_root / "tasks"
    task_parent.mkdir(mode=0o700)
    results: list[dict[str, Any]] = []
    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["owner"],
        purpose=lease["purpose"],
        path=root / scientific.parent._relative(lease["path"]),
    ):
        for index, task in enumerate(tasks, start=1):
            result = run_one_task(
                root, protocol, task, task_parent / f"task_{index:04d}"
            )
            results.append(result)
            scientific.parent._append_jsonl(predictions_path, result)
    aggregate = aggregate_results(protocol, results)
    aggregate["execution_start_sha256"] = sha256(start_path)
    aggregate["activation_payload_sha256"] = activation[
        "activation_payload_sha256"
    ]
    aggregate["result_payload_sha256"] = payload_sha256(
        {k: v for k, v in aggregate.items() if k != "result_payload_sha256"}
    )
    scientific.parent._new_json(result_path, aggregate)
    print(json.dumps({"result": str(result_path), "engineering_gate": aggregate["engineering_gate"]}))


if __name__ == "__main__":
    main()
