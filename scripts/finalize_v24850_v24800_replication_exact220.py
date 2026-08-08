#!/usr/bin/env python3
"""Post-freeze audit and evaluation for the V2.48.50 replication."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v24850_v24800_replication_exact220_contract as contract,
)
from scripts import finalize_v24800_exact220 as base  # noqa: E402


def configure() -> None:
    date = contract.DATE
    root = contract.OUTPUT_ROOT / "evaluator"
    assignments = {
        "contract": contract,
        "FORWARD_AUDIT": contract.FORWARD_AUDIT,
        "EVALUATOR_PROTOCOL": Path(
            f"results/v24850_v24800_replication_exact220_evaluator_preregistration_v1_{date}.json"
        ),
        "FINAL_RESULT": Path(
            f"results/v24850_v24800_replication_exact220_result_v1_{date}.json"
        ),
        "POSTAUDIT": Path(
            f"results/v24850_v24800_replication_exact220_postresult_audit_v1_{date}.json"
        ),
        "EVALUATOR_ROOT": root,
        "PREPARE_ATTESTATION": root / "prepare_attestation.json",
        "JOINED_OUTCOMES": root / "terminal_outcomes_evaluator_joined.jsonl",
        "OFFICIAL_PREDICTIONS": root / "official_predictions.jsonl",
        "EVALUATOR_RUNS": root / "official_eval_workers",
        "EVALUATOR_LOGS": root / "logs",
        "MERGED_RESULTS": root / "official_eval_results.jsonl",
        "MERGE_ATTESTATION": root / "merge_attestation.json",
        "SUMMARY": root / "conservative_summary.json",
        "EVALUATOR_OWNER": "v24850_v24800_replication_exact220_evaluator_v1",
        "EVALUATOR_PURPOSE": (
            "postfreeze_fixed_partition_parallel_v24800_replication_exact220_evaluator"
        ),
        "CONTROL_FILES": (
            "scripts/finalize_v24850_v24800_replication_exact220.py",
            "scripts/run_v24850_v24800_replication_exact220.py",
            "scripts/run_v24850_v24800_replication_exact220_task.py",
            "scripts/control_v24850_v24800_replication_exact220.py",
            "src/deepwide_agent/v24850_v24800_replication_exact220_contract.py",
            "tests/test_v24850_v24800_replication_exact220.py",
            "scripts/finalize_v24800_exact220.py",
            "scripts/run_v24800_exact220.py",
            "scripts/run_v24800_exact220_task.py",
            "scripts/run_official_eval_local.py",
            "scripts/finalize_v24287_exact220.py",
            "scripts/finalize_fullset_rollout.py",
            "scripts/deepwide_api_lease.py",
        ),
        "REFERENCES": {
            **base.REFERENCES,
            "v24800": Path("results/v24800_exact220_result_v1_20260807.json"),
            "v24848": Path(
                "results/v24848_atomic_table_header_30k_exact220_result_v1_20260808.json"
            ),
        },
    }
    for name, value in assignments.items():
        setattr(base, name, value)


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
