#!/usr/bin/env python3
"""One neutral real-chain smoke for the corrected keyless coverage runner."""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import run_v24877_keyless_coverage_exact220 as runner  # noqa: E402


OUTPUT = Path("outputs/v24878_keyless_coverage_runner_smoke_v1_20260808")
RESULT = Path("results/v24878_keyless_coverage_runner_smoke_v1_20260808.json")
TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": (
        "Using official documentation, list the stable release channels for "
        "Python package installation tools. Return a Markdown table with "
        "columns: Tool, Official documentation URL."
    ),
}


def main() -> None:
    if (ROOT / OUTPUT).exists() or (ROOT / RESULT).exists():
        raise FileExistsError("V2.48.78 smoke surface is not pristine")
    (ROOT / OUTPUT).mkdir(mode=0o700)
    runner.algorithm.OUTPUT_ROOT = OUTPUT
    runner.algorithm.MODEL_SLOT_DIRECTORY = OUTPUT / "model_slots"
    runner.algorithm.TASK_ROOT = OUTPUT / "tasks"
    (ROOT / OUTPUT / "model_slots").mkdir(mode=0o700)
    (ROOT / OUTPUT / "tasks").mkdir(mode=0o700)
    original_output = runner.contract.OUTPUT_ROOT
    original_slots = runner.contract.MODEL_SLOT_DIRECTORY
    original_tasks = runner.contract.TASK_ROOT
    try:
        runner.contract.OUTPUT_ROOT = OUTPUT
        runner.contract.MODEL_SLOT_DIRECTORY = OUTPUT / "model_slots"
        runner.contract.TASK_ROOT = OUTPUT / "tasks"
        started = time.monotonic()
        outcome = runner._run_one_task(
            ROOT,
            {},
            1,
            TASK,
            ROOT / OUTPUT / "tasks" / "task_0001",
        )
        wall = max(0.0, time.monotonic() - started)
    finally:
        runner.contract.OUTPUT_ROOT = original_output
        runner.contract.MODEL_SLOT_DIRECTORY = original_slots
        runner.contract.TASK_ROOT = original_tasks
    value = {
        "artifact_version": 1,
        "role": "v24878_keyless_coverage_runner_smoke",
        "created_at_unix": int(time.time()),
        "wall_seconds": round(wall, 6),
        "accepted_parent_success": bool(outcome.accepted_parent_success),
        "parent_failure_taxonomy": (
            outcome.parent_exit or {}
        ).get("failure_taxonomy", "parent_unobserved"),
        "model_receipt_present": bool(outcome.model_receipt_present),
        "transport_receipt_valid": bool(outcome.transport_receipt_valid),
        "single_receipt_valid": bool(outcome.single_receipt_valid),
        "backfill_receipt_valid": bool(outcome.backfill_receipt_valid),
        "completion_kind": str(outcome.result["completion_kind"]),
        "private_task_query_url_page_prediction_answer_or_credential_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
    }
    value["result_payload_sha256"] = runner.contract.payload_sha256(value)
    runner.algorithm._new_json(ROOT / RESULT, value)
    shutil.rmtree(ROOT / OUTPUT)
    print(json.dumps(value, sort_keys=True))


if __name__ == "__main__":
    main()
