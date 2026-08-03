#!/usr/bin/env python3
"""Network-free real-subprocess smoke for the V2.43.15 exact-220 runner."""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
import sys

for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_parent_receipt,
)
from deepwide_agent.v24310_paired_dev_runtime import (  # noqa: E402
    RECEIPT_FIELD,
    validate_v24310_result,
)
from deepwide_agent.v24315_forward_contract import (  # noqa: E402
    LIMITS,
    payload_sha256,
)
from scripts.preregister_v24315_exact220 import publish_new  # noqa: E402
from scripts import run_v24315_exact220 as runner  # noqa: E402


RESULT = Path("results/v24315_exact220_runner_smoke_v1_20260803.json")
FIXTURE = Path("tests/fixtures/v24315_synthetic_child.py")


def _visible() -> dict[str, str]:
    return {
        "opaque_id": f"task_{1:024x}",
        "question": "Return one table. The column names are: Name, Value, and Date.",
    }


def _command(mode: str, target: Path) -> list[str]:
    return [
        str(ROOT / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(ROOT / FIXTURE),
        "--mode",
        mode,
        "--task",
        str(target / "visible_task.json"),
        "--result",
        str(target / "result.json"),
        "--model-receipt",
        str(target / runner.RECEIPT_NAME),
        "--transport",
        str(target / runner.TRANSPORT_NAME),
        "--terminal",
        str(target / "child_terminal_receipt.json"),
    ]


def build_report(*, now: int | None = None) -> dict[str, Any]:
    outcomes: list[dict[str, Any]] = []
    original_output = runner.OUTPUT_ROOT
    original_tasks = runner.TASK_ROOT
    original_command = runner.task_command
    try:
        for mode in ("success", "nonzero"):
            with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
                base = Path(temporary)
                relative = base.relative_to(ROOT)
                task_root = base / "tasks"
                task_root.mkdir(parents=True)
                directory = task_root / "task_0001"
                runner.OUTPUT_ROOT = relative
                runner.TASK_ROOT = relative / "tasks"
                runner.task_command = lambda _root, target, selected=mode: _command(
                    selected, target
                )
                outcome = runner.run_one_task(ROOT, {}, _visible(), directory)
                parent = validate_parent_receipt(outcome.parent_exit or {})
                validate_v24310_result(outcome.result, "candidate")
                recovery = outcome.result[RECEIPT_FIELD]
                outcomes.append(
                    {
                        "mode": mode,
                        "failure_taxonomy": parent["failure_taxonomy"],
                        "parent_receipt_valid": True,
                        "child_terminal_receipt_present": parent[
                            "child_terminal_receipt_present"
                        ],
                        "child_terminal_receipt_valid": parent[
                            "child_terminal_receipt_valid"
                        ],
                        "model_receipt_present": parent["model_receipt_present"],
                        "model_receipt_valid": parent["model_receipt_valid"],
                        "transport_receipt_present": parent[
                            "transport_receipt_present"
                        ],
                        "transport_receipt_valid": parent[
                            "transport_receipt_valid"
                        ],
                        "result_envelope_present": parent[
                            "result_envelope_present"
                        ],
                        "result_envelope_valid": parent["result_envelope_valid"],
                        "effect_count_complete": recovery["effect_count_complete"],
                        "admitted_model_effects_upper_bound": recovery[
                            "admitted_model_effects_upper_bound"
                        ],
                    }
                )
    finally:
        runner.OUTPUT_ROOT = original_output
        runner.TASK_ROOT = original_tasks
        runner.task_command = original_command
    expected = {
        "success": "success",
        "nonzero": "child_nonzero_with_terminal_receipt",
    }
    findings: list[str] = []
    if {item["mode"]: item["failure_taxonomy"] for item in outcomes} != expected:
        findings.append("parent_taxonomy_mismatch")
    success = next(item for item in outcomes if item["mode"] == "success")
    nonzero = next(item for item in outcomes if item["mode"] == "nonzero")
    if not all(
        success[name]
        for name in (
            "parent_receipt_valid",
            "child_terminal_receipt_present",
            "child_terminal_receipt_valid",
            "model_receipt_present",
            "model_receipt_valid",
            "transport_receipt_present",
            "transport_receipt_valid",
            "result_envelope_present",
            "result_envelope_valid",
            "effect_count_complete",
        )
    ):
        findings.append("success_receipt_chain_incomplete")
    if (
        nonzero["effect_count_complete"] is not False
        or nonzero["admitted_model_effects_upper_bound"] != LIMITS["model_calls"]
    ):
        findings.append("nonzero_unknown_effect_envelope_drifted")
    value = {
        "artifact_version": 1,
        "role": "v24315_exact220_runner_benchmark_external_smoke",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "modes": outcomes,
        "external_effect_ledger": {
            "network": 0,
            "model": 0,
            "search": 0,
            "fetch": 0,
            "evaluator": 0,
        },
        "benchmark_manifest_mapping_gold_category_question_type_split_evaluator_score_read": False,
        "credential_value_read_persisted_hashed_or_emitted": False,
        "temporary_probe_directories_remaining": False,
        "findings": findings,
        "passed": not findings,
        "authorization": {
            "freeze_exact220_protocol": not findings,
            "benchmark_launch": False,
            "evaluator": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["report_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    report = build_report()
    publish_new(ROOT / RESULT, report)
    print(json.dumps({"path": str(RESULT), "passed": report["passed"]}, sort_keys=True))
