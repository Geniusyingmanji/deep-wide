#!/usr/bin/env python3
"""Exact-220 evaluator successor with a read-only terminal-summary projection.

The first V2.51.30 evaluator attempt stopped before creating any evaluator
surface because the mature evaluator expected a legacy ``failed`` field.  The
frozen summary already records 220 terminal predictions and 27 internal
failure-as-zero tasks.  This adapter projects only ``failed=0`` in memory,
meaning no prediction row is nonterminal; it preserves the 27 conservative
fallback rows and never changes a frozen file or launches a forward retry.
"""

from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25130_causal_salience_exact220_contract as contract  # noqa: E402
from scripts import finalize_v25131_v25130_failure_as_zero_exact220 as parent  # noqa: E402


DATE = "20260811"
SOURCE = Path("scripts/finalize_v25132_v25130_terminal_summary_exact220.py")
TEST = Path("tests/test_finalize_v25132_v25130_terminal_summary_exact220.py")
EVALUATOR_PROTOCOL = Path(
    f"results/v25132_v25130_terminal_summary_evaluator_preregistration_v1_{DATE}.json"
)
FINAL_RESULT = Path(
    f"results/v25132_v25130_terminal_summary_exact220_result_v1_{DATE}.json"
)
POSTAUDIT = Path(
    f"results/v25132_v25130_terminal_summary_exact220_postresult_audit_v1_{DATE}.json"
)
EVALUATOR_ROOT = Path(
    f"outputs/v25132_v25130_terminal_summary_evaluator_v1_{DATE}"
)
PRIOR_EVALUATOR_PROTOCOL = contract.EVALUATOR_PROTOCOL
PRIOR_EVALUATOR_ROOT = contract.OUTPUT_ROOT / "evaluator"

_ORIGINAL_PREPARE = parent.base.evaluator.prepare_evaluator_inputs


def _project_terminal_summary(value: dict[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(value)
    if (
        copied.get("selected") != 220
        or copied.get("completed") != 220
        or copied.get("runtime_completed", -1)
        + copied.get("failure_as_zero_tasks", -1)
        != 220
        or copied.get("model_generated_tables", -1)
        + copied.get("fallback_tables", -1)
        != 220
        or copied.get("unattributable_prediction_changed_tasks") != 0
        or copied.get("official_evaluator_called") is not False
        or not contract.sealed(copied, "summary_payload_sha256")
    ):
        raise RuntimeError("V2.51.32 frozen summary projection barrier failed")
    copied["failed"] = 0
    copied["terminal_summary_compatibility_projection"] = {
        "completed_means_terminal_prediction_rows": 220,
        "failed_means_nonterminal_prediction_rows": 0,
        "internal_runtime_failure_as_zero_tasks_preserved": int(
            copied["failure_as_zero_tasks"]
        ),
        "frozen_summary_file_modified": False,
        "forward_retry_resume_or_selective_rerun": False,
    }
    return copied


def _prepare_with_terminal_projection(
    root: Path, protocol: dict[str, Any], barrier: dict[str, Any]
) -> dict[str, Any]:
    original_read = parent.base.evaluator.read_object
    target = (root / contract.RUN_SUMMARY).resolve()

    def projected_read(path: Path) -> dict[str, Any]:
        value = original_read(path)
        if Path(path).resolve() == target:
            return _project_terminal_summary(value)
        return value

    parent.base.evaluator.read_object = projected_read
    try:
        return _ORIGINAL_PREPARE(root, protocol, barrier)
    finally:
        parent.base.evaluator.read_object = original_read


def _predecessor_disposition() -> dict[str, Any]:
    protocol = ROOT / PRIOR_EVALUATOR_PROTOCOL
    if protocol.is_symlink() or not protocol.is_file():
        raise RuntimeError("V2.51.32 prior evaluator protocol is absent")
    effect_absent = not (ROOT / PRIOR_EVALUATOR_ROOT).exists() and not (
        ROOT / PRIOR_EVALUATOR_ROOT
    ).is_symlink()
    if not effect_absent:
        raise RuntimeError("V2.51.32 prior evaluator effect surface exists")
    return {
        "prior_evaluator_protocol_path": str(PRIOR_EVALUATOR_PROTOCOL),
        "prior_evaluator_protocol_sha256": contract.sha256(protocol),
        "failure_stage": "pre_worker_terminal_summary_compatibility_check",
        "evaluator_root_created": False,
        "official_worker_started": False,
        "prediction_or_forward_artifact_modified": False,
        "retry_resume_or_selective_revaluation": False,
        "effect_surface_absent": True,
    }


def configure() -> None:
    parent.configure()
    assignments = {
        "EVALUATOR_PROTOCOL": EVALUATOR_PROTOCOL,
        "FINAL_RESULT": FINAL_RESULT,
        "POSTAUDIT": POSTAUDIT,
        "EVALUATOR_ROOT": EVALUATOR_ROOT,
        "PREPARE_ATTESTATION": EVALUATOR_ROOT / "prepare_attestation.json",
        "JOINED_OUTCOMES": EVALUATOR_ROOT
        / "terminal_outcomes_evaluator_joined.jsonl",
        "OFFICIAL_PREDICTIONS": EVALUATOR_ROOT / "official_predictions.jsonl",
        "EVALUATOR_RUNS": EVALUATOR_ROOT / "official_eval_workers",
        "EVALUATOR_LOGS": EVALUATOR_ROOT / "logs",
        "MERGED_RESULTS": EVALUATOR_ROOT / "official_eval_results.jsonl",
        "MERGE_ATTESTATION": EVALUATOR_ROOT / "merge_attestation.json",
        "SUMMARY": EVALUATOR_ROOT / "conservative_summary.json",
        "CONTROL_FILES": (
            str(SOURCE),
            str(TEST),
            str(parent.SOURCE),
            str(parent.TEST),
            str(contract.RUNNER),
            str(contract.CONTROL),
            str(contract.SOURCE),
            str(contract.RUNTIME),
            str(contract.TEST),
            "scripts/finalize_v24791_exact220.py",
            "scripts/run_official_eval_local.py",
            "scripts/finalize_v24287_exact220.py",
            "scripts/finalize_fullset_rollout.py",
            "scripts/deepwide_api_lease.py",
        ),
    }
    for name, value in assignments.items():
        setattr(parent.base, name, value)
    parent.base.evaluator.prepare_evaluator_inputs = _prepare_with_terminal_projection


def build_evaluator_protocol(*, now: int | None = None) -> dict[str, Any]:
    configure()
    value = parent.base.build_evaluator_protocol(now=now)
    value["predecessor_disposition"] = _predecessor_disposition()
    value["terminal_summary_compatibility_projection"] = {
        "source_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "disk_summary_modified": False,
        "projected_failed_nonterminal_rows": 0,
        "internal_failure_as_zero_rows_preserved": 27,
        "projection_applies_only_to_evaluator_input_join": True,
        "forward_retry_resume_or_selective_rerun": False,
    }
    value["protocol_payload_sha256"] = contract.payload_sha256(
        {
            key: item
            for key, item in value.items()
            if key != "protocol_payload_sha256"
        }
    )
    parent.base.validate_evaluator_protocol(value)
    return value


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("protocol", "evaluate", "postaudit"))
    args = parser.parse_args()
    configure()
    if args.command == "protocol":
        value = build_evaluator_protocol()
        parent._publish_new(ROOT / EVALUATOR_PROTOCOL, value)
        print(
            json.dumps(
                {
                    "path": str(EVALUATOR_PROTOCOL),
                    "authorization": value["authorization"],
                    "predecessor_disposition": value["predecessor_disposition"],
                },
                sort_keys=True,
            )
        )
        return
    sys.argv = [sys.argv[0], args.command]
    parent.base.main()


if __name__ == "__main__":
    main()
