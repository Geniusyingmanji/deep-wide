#!/usr/bin/env python3
"""Run one fresh label-blind V2.48.37 information-bottleneck exact-220."""

from __future__ import annotations

import copy
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24837_information_bottleneck_exact220_contract as contract  # noqa: E402
from scripts import run_v24831_keyless_exact220 as base  # noqa: E402


PREAUDIT_ROLE = "v24837_information_bottleneck_exact220_preactivation_audit"
START_ROLE = "v24837_information_bottleneck_exact220_execution_start"


def configure() -> None:
    base.contract = contract
    inherited_progress = base._progress

    def progress(completed: int) -> dict:
        value = inherited_progress(completed)
        value["role"] = "v24837_information_bottleneck_exact220_safe_forward_progress"
        value.pop("progress_payload_sha256", None)
        value["progress_payload_sha256"] = contract.payload_sha256(value)
        return value

    base._progress = progress
    inherited_validate = base.validate_execution_start

    def validate_execution_start(root: Path, protocol: dict) -> dict:
        audit = base._read(root / contract.PREAUDIT)
        start = base._read(root / contract.EXECUTION_START)
        if audit.get("role") != PREAUDIT_ROLE or start.get("role") != START_ROLE:
            raise RuntimeError("V2.48.37 execution authorization drifted")
        projected_audit = copy.deepcopy(audit)
        projected_audit["role"] = "v24831_keyless_exact220_preactivation_audit"
        projected_audit.pop("audit_payload_sha256", None)
        projected_audit["audit_payload_sha256"] = contract.payload_sha256(
            projected_audit
        )
        projected_start = copy.deepcopy(start)
        projected_start["role"] = "v24831_keyless_exact220_execution_start"
        projected_start.pop("execution_start_payload_sha256", None)
        projected_start["execution_start_payload_sha256"] = contract.payload_sha256(
            projected_start
        )
        inherited_read = base._read

        def compatible_read(path: Path) -> dict:
            if path == root / contract.PREAUDIT:
                return projected_audit
            if path == root / contract.EXECUTION_START:
                return projected_start
            return inherited_read(path)

        base._read = compatible_read
        try:
            inherited_validate(root, protocol)
        finally:
            base._read = inherited_read
        return start

    base.validate_execution_start = validate_execution_start


def main() -> None:
    configure()
    base.configure_algorithm()
    algorithm = base.algorithm
    root = ROOT
    protocol = contract.validate_protocol(root, base._read(root / contract.PROTOCOL))
    start = base.validate_execution_start(root, protocol)
    tasks = contract.task_vector(root, protocol)
    head = base.subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True,
        stdout=base.subprocess.PIPE, stderr=base.subprocess.DEVNULL, check=True,
    ).stdout.strip()
    remote = base.subprocess.run(
        ["git", "rev-parse", "target/main"], cwd=root, text=True,
        stdout=base.subprocess.PIPE, stderr=base.subprocess.DEVNULL, check=True,
    ).stdout.strip()
    dirty = base.subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, text=True,
        stdout=base.subprocess.PIPE, stderr=base.subprocess.DEVNULL, check=True,
    ).stdout.strip()
    if head != remote or dirty:
        raise RuntimeError("V2.48.37 launch requires clean pushed HEAD")
    required = (
        contract.PROTOCOL,
        contract.PREAUDIT,
        contract.EXECUTION_START,
        *map(Path, protocol["dependency_manifest"]),
    )
    if any(
        base.subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)], cwd=root,
            stdout=base.subprocess.DEVNULL, stderr=base.subprocess.DEVNULL,
            check=False,
        ).returncode != 0
        for path in required
    ):
        raise RuntimeError("V2.48.37 launch dependency is not tracked")
    conflicts = base._active_conflicts()
    if conflicts:
        raise RuntimeError(f"V2.48.37 conflicting benchmark/evaluator active: {conflicts}")
    with base.socket.create_connection(("127.0.0.1", 9878), timeout=2.0):
        pass
    for path in (root / contract.FORWARD_RESULT, root / contract.OUTPUT_ROOT):
        if path.exists() or path.is_symlink():
            raise RuntimeError("V2.48.37 forward surface is not pristine")
    with base.acquire_deepwide_api_lease(
        root, owner=contract.LEASE_OWNER, purpose=contract.LEASE_PURPOSE,
        path=root / contract.LEASE_PATH,
    ):
        if contract.protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]:
            raise RuntimeError("V2.48.37 protected watcher drifted before effect")
        (root / contract.OUTPUT_ROOT).mkdir(mode=0o700, parents=True, exist_ok=False)
        algorithm._prepare_slots(root)
        (root / contract.TASK_ROOT).mkdir(mode=0o700)
        started = time.monotonic()
        outcomes = algorithm.execute_forward(
            root, protocol, tasks,
            progress_writer=lambda value: algorithm._atomic_json(
                root / contract.SAFE_PROGRESS,
                base._progress(int(value["completed"])),
            ),
        )
        wall = max(0.0, time.monotonic() - started)
    rows = [algorithm._runtime_row(item.result) for item in outcomes]
    algorithm._write_jsonl_new(root / contract.RUNTIME_PREDICTIONS, rows)
    summary = algorithm._summary(outcomes, wall)
    summary["role"] = "v24837_information_bottleneck_exact220_run_summary"
    summary["protocol_id"] = contract.PROTOCOL_ID
    summary.pop("summary_payload_sha256", None)
    summary["summary_payload_sha256"] = contract.payload_sha256(summary)
    algorithm._new_json(root / contract.RUN_SUMMARY, summary)
    freeze = {
        "artifact_version": 1,
        "role": "v24837_information_bottleneck_exact220_prediction_freeze",
        "protocol_id": contract.PROTOCOL_ID,
        "selected": contract.SELECTED_COUNT,
        "terminal": contract.SELECTED_COUNT,
        "runtime_predictions_sha256": contract.sha256(root / contract.RUNTIME_PREDICTIONS),
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
        "role": "v24837_information_bottleneck_exact220_forward_result",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()),
        "selected": contract.SELECTED_COUNT,
        "terminal_predictions": contract.SELECTED_COUNT,
        "model_generated_tables": summary["model_generated_tables"],
        "fallback_tables": summary["fallback_tables"],
        "system_total_tokens": summary["system_total_tokens"],
        "forward_wall_seconds": summary["forward_wall_seconds"],
        "prediction_freeze_sha256": contract.sha256(root / contract.PREDICTION_FREEZE),
        "run_summary_sha256": contract.sha256(root / contract.RUN_SUMMARY),
        "execution_start_sha256": contract.sha256(root / contract.EXECUTION_START),
        "execution_start_payload_sha256": start["execution_start_payload_sha256"],
        "all_220_predictions_terminal_before_mapping_or_evaluator_open": True,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "official_evaluator_called": False,
        "retry_resume_skip_or_selective_rerun_launched": False,
    }
    forward["result_payload_sha256"] = contract.payload_sha256(forward)
    algorithm._new_json(root / contract.FORWARD_RESULT, forward)
    algorithm._atomic_json(root / contract.SAFE_PROGRESS, base._progress(220))
    print(base.json.dumps({
        "terminal": 220,
        "wall_seconds": wall,
        "fallback_tables": summary["fallback_tables"],
        "forward_result": str(contract.FORWARD_RESULT),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
