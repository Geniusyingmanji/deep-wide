#!/usr/bin/env python3
"""Post-freeze audit and evaluator for V2.49.71 exact-220."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24971_readiness_armed_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24857_pacing_aware_exact220 as parent  # noqa: E402


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.49.71 finalizer expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.49.71 finalizer expected JSON object")
    return value


def configure() -> None:
    parent.contract = contract
    parent.configure()
    engine = parent.base
    date = contract.DATE
    evaluator_root = contract.OUTPUT_ROOT / "evaluator"
    assignments = {
        "contract": contract,
        "FORWARD_AUDIT": contract.FORWARD_AUDIT,
        "EVALUATOR_PROTOCOL": Path(
            f"results/v24971_readiness_armed_exact220_evaluator_preregistration_v1_{date}.json"
        ),
        "FINAL_RESULT": Path(
            f"results/v24971_readiness_armed_exact220_result_v1_{date}.json"
        ),
        "POSTAUDIT": Path(
            f"results/v24971_readiness_armed_exact220_postresult_audit_v1_{date}.json"
        ),
        "EVALUATOR_ROOT": evaluator_root,
        "PREPARE_ATTESTATION": evaluator_root / "prepare_attestation.json",
        "JOINED_OUTCOMES": evaluator_root / "terminal_outcomes_evaluator_joined.jsonl",
        "OFFICIAL_PREDICTIONS": evaluator_root / "official_predictions.jsonl",
        "EVALUATOR_RUNS": evaluator_root / "official_eval_workers",
        "EVALUATOR_LOGS": evaluator_root / "logs",
        "MERGED_RESULTS": evaluator_root / "official_eval_results.jsonl",
        "MERGE_ATTESTATION": evaluator_root / "merge_attestation.json",
        "SUMMARY": evaluator_root / "conservative_summary.json",
        "EVALUATOR_OWNER": "v24971_readiness_armed_exact220_evaluator_v1",
        "EVALUATOR_PURPOSE": (
            "postfreeze_fixed_partition_parallel_v24971_exact220_evaluator"
        ),
    }
    for name, value in assignments.items():
        setattr(engine, name, value)
    inherited_forward_barrier = engine._forward_barrier

    def readiness_bound_forward_barrier() -> dict[str, Any]:
        barrier = inherited_forward_barrier()
        armed = contract.validate_armed_receipt(
            ROOT, _read(ROOT / contract.ARMED_RECEIPT)
        )
        start_value = _read(ROOT / contract.EXECUTION_START)
        start = contract.validate_execution_start(
            ROOT,
            barrier["protocol"],
            now=int(start_value["created_at_unix"]),
            require_current_runner=False,
        )
        forward = barrier["forward"]
        if (
            armed["readiness"]["passed"] is not True
            or forward.get("execution_start_sha256")
            != contract.sha256(ROOT / contract.EXECUTION_START)
            or forward.get("execution_start_payload_sha256")
            != start["execution_start_payload_sha256"]
            or start["armed_receipt_sha256"]
            != contract.sha256(ROOT / contract.ARMED_RECEIPT)
        ):
            raise RuntimeError("V2.49.71 readiness authorization chain drifted")
        barrier["armed_receipt"] = armed
        barrier["execution_start"] = start
        return barrier

    engine._forward_barrier = readiness_bound_forward_barrier
    engine.CONTROL_FILES = tuple(
        dict.fromkeys(
            (
                str(contract.FINALIZER),
                str(contract.RUNNER),
                str(contract.CHILD),
                str(contract.CONTROL),
                str(contract.SOURCE),
                str(contract.TEST),
                str(contract.READINESS_SOURCE),
                str(contract.READINESS_TEST),
                str(contract.ARMED_RECEIPT),
                str(contract.EXECUTION_START),
                *engine.CONTROL_FILES,
            )
        )
    )
    engine.REFERENCES = {
        **engine.REFERENCES,
        "v24857": Path(
            "results/v24857_pacing_aware_exact220_result_v1_20260808.json"
        ),
        "v24969": Path(
            "results/v24969_pacing_aware_replication_result_v1_20260809.json"
        ),
    }


def main() -> None:
    configure()
    parent.base.main()


if __name__ == "__main__":
    main()
