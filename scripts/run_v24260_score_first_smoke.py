#!/usr/bin/env python3
"""V2.42.60 executor: V2.42.59 plus isolated child import bootstrap only."""

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

from scripts import run_v24259_score_first_smoke as parent  # noqa: E402
from scripts.deepwide_api_lease import acquire_deepwide_api_lease  # noqa: E402
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


DEFAULT_PROTOCOL = Path(
    "results/v24260_import_bootstrap_smoke_preregistration_v1_20260802.json"
)
ROLE = "v24260_import_bootstrap_smoke_result"
RUNNER_MARKER = "scripts/run_v24260_score_first_smoke.py"
CHILD = "scripts/v24260_successor/run_v24259_score_first_task.py"


def validate_protocol(root: Path, value: dict[str, Any]) -> dict[str, Any]:
    if (
        value.get("role") != "v24260_import_bootstrap_smoke_preregistration"
        or value.get("protocol_id") != "v24260_import_bootstrap_smoke16_v1"
        or value.get("label_blind") is not True
        or not parent.parent._sealed(value, "decision_contract_sha256")
        or value.get("source_policy", {}).get(
            "mapping_gold_category_question_type_evaluator_score_read"
        )
        is not False
    ):
        raise RuntimeError("V2.42.60 protocol identity drifted")
    manifest = value.get("control_surface", {}).get("manifest") or {}
    live: dict[str, str] = {}
    for name, expected in manifest.items():
        relative = parent.parent._relative(name)
        path = root / relative
        if path.is_symlink() or not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"V2.42.60 control source drifted: {relative}")
        live[str(relative)] = expected
    if payload_sha256(live) != value["control_surface"].get("manifest_sha256"):
        raise RuntimeError("V2.42.60 control manifest drifted")
    return value


def validate_activation(root: Path, protocol: dict[str, Any]) -> dict[str, Any]:
    path = root / parent.parent._relative(protocol["execution"]["activation_path"])
    value = parent.parent.read_object(path)
    if (
        value.get("role") != "v24260_import_bootstrap_smoke_activation"
        or value.get("status") != "active"
        or value.get("protocol_sha256") != sha256(root / DEFAULT_PROTOCOL)
        or value.get("control_manifest_sha256")
        != protocol["control_surface"]["manifest_sha256"]
        or value.get(
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read"
        )
        is not False
        or not parent.parent._sealed(value, "activation_payload_sha256")
    ):
        raise RuntimeError("V2.42.60 activation drifted")
    return value


def _task_command(root, protocol, task_path, result_path, progress_path):
    command = parent._task_command(
        root, protocol, task_path, result_path, progress_path
    )
    command[3] = str(root / CHILD)
    return command


def run_one_task(root, protocol, task, task_root, *, popen=parent.parent.subprocess.Popen):
    original = parent._task_command
    parent._task_command = _task_command
    try:
        return parent.run_one_task(root, protocol, task, task_root, popen=popen)
    finally:
        parent._task_command = original


def aggregate_results(protocol, results):
    value = parent.aggregate_results(protocol, results)
    value["role"] = ROLE
    value["protocol_id"] = protocol["protocol_id"]
    value["result_payload_sha256"] = payload_sha256(
        {k: v for k, v in value.items() if k != "result_payload_sha256"}
    )
    return value


def main() -> None:
    parser = parent.parent.argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--protocol", default=str(DEFAULT_PROTOCOL))
    args = parser.parse_args()
    root = Path(args.root).resolve()
    protocol_path = Path(args.protocol)
    if not protocol_path.is_absolute():
        protocol_path = root / protocol_path
    if root != ROOT or protocol_path.resolve() != (root / DEFAULT_PROTOCOL).resolve():
        raise RuntimeError("V2.42.60 executor path drifted")
    protocol = validate_protocol(root, parent.parent.read_object(protocol_path))
    activation = validate_activation(root, protocol)
    tasks = parent.parent._selected_tasks(root, protocol)
    execution = protocol["execution"]
    output_root = root / parent.parent._relative(execution["output_root"])
    start_path = root / parent.parent._relative(execution["execution_start_path"])
    result_path = root / parent.parent._relative(execution["result_path"])
    predictions_path = output_root / "runtime_predictions.jsonl"
    if any(path.exists() or path.is_symlink() for path in (output_root, start_path, result_path)):
        raise RuntimeError("V2.42.60 execution surface is not pristine")
    start: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24260_import_bootstrap_smoke_execution_start",
        "created_at_unix": int(parent.parent.time.time()),
        "protocol_sha256": sha256(protocol_path),
        "activation_sha256": sha256(
            root / parent.parent._relative(execution["activation_path"])
        ),
        "selected_opaque_ids_sha256": protocol["task_contract"][
            "selected_opaque_ids_sha256"
        ],
        "runner": {
            "pid": parent.parent.os.getpid(),
            "start_ticks": parent.parent._start_ticks(parent.parent.os.getpid()),
            "marker": RUNNER_MARKER,
        },
        "label_blind": True,
        "mapping_gold_category_question_type_evaluator_score_read": False,
        "api_called_before_execution_start": False,
    }
    start["execution_start_payload_sha256"] = payload_sha256(start)
    parent.parent._new_json(start_path, start)
    output_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    task_parent = output_root / "tasks"
    task_parent.mkdir(mode=0o700)
    results: list[dict[str, Any]] = []
    lease = protocol["lease_contract"]
    with acquire_deepwide_api_lease(
        root,
        owner=lease["owner"],
        purpose=lease["purpose"],
        path=root / parent.parent._relative(lease["path"]),
    ):
        for index, task in enumerate(tasks, start=1):
            result = run_one_task(
                root, protocol, task, task_parent / f"task_{index:04d}"
            )
            results.append(result)
            parent.parent._append_jsonl(predictions_path, result)
    aggregate = aggregate_results(protocol, results)
    aggregate["execution_start_sha256"] = sha256(start_path)
    aggregate["activation_payload_sha256"] = activation[
        "activation_payload_sha256"
    ]
    aggregate["result_payload_sha256"] = payload_sha256(
        {k: v for k, v in aggregate.items() if k != "result_payload_sha256"}
    )
    parent.parent._new_json(result_path, aggregate)
    print(json.dumps({"result": str(result_path), "engineering_gate": aggregate["engineering_gate"]}))


if __name__ == "__main__":
    main()
