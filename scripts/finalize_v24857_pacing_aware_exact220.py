#!/usr/bin/env python3
"""Post-freeze audit and evaluator for V2.48.57 exact-220."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24857_pacing_aware_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24800_exact220 as base  # noqa: E402


def configure() -> None:
    date = contract.DATE
    evaluator_root = contract.OUTPUT_ROOT / "evaluator"
    assignments = {
        "contract": contract,
        "FORWARD_AUDIT": contract.FORWARD_AUDIT,
        "EVALUATOR_PROTOCOL": Path(f"results/v24857_pacing_aware_exact220_evaluator_preregistration_v1_{date}.json"),
        "FINAL_RESULT": Path(f"results/v24857_pacing_aware_exact220_result_v1_{date}.json"),
        "POSTAUDIT": Path(f"results/v24857_pacing_aware_exact220_postresult_audit_v1_{date}.json"),
        "EVALUATOR_ROOT": evaluator_root,
        "PREPARE_ATTESTATION": evaluator_root / "prepare_attestation.json",
        "JOINED_OUTCOMES": evaluator_root / "terminal_outcomes_evaluator_joined.jsonl",
        "OFFICIAL_PREDICTIONS": evaluator_root / "official_predictions.jsonl",
        "EVALUATOR_RUNS": evaluator_root / "official_eval_workers",
        "EVALUATOR_LOGS": evaluator_root / "logs",
        "MERGED_RESULTS": evaluator_root / "official_eval_results.jsonl",
        "MERGE_ATTESTATION": evaluator_root / "merge_attestation.json",
        "SUMMARY": evaluator_root / "conservative_summary.json",
        "EVALUATOR_OWNER": "v24857_pacing_aware_exact220_evaluator_v1",
        "EVALUATOR_PURPOSE": "postfreeze_fixed_partition_parallel_v24857_pacing_aware_exact220_evaluator",
        "CONTROL_FILES": (
            "scripts/finalize_v24857_pacing_aware_exact220.py",
            "scripts/run_v24857_pacing_aware_exact220.py",
            "scripts/run_v24857_pacing_aware_exact220_task.py",
            "scripts/control_v24857_pacing_aware_exact220.py",
            "src/deepwide_agent/v24857_pacing_aware_exact220_contract.py",
            "src/deepwide_agent/v24856_pacing_aware_admission.py",
            "src/deepwide_agent/v24852_rate_aware_tavily_search.py",
            "tests/test_v24857_pacing_aware_exact220.py",
            "scripts/finalize_v24800_exact220.py",
            "scripts/run_official_eval_local.py",
            "scripts/finalize_v24287_exact220.py",
            "scripts/finalize_fullset_rollout.py",
            "scripts/deepwide_api_lease.py",
        ),
        "REFERENCES": {
            **base.REFERENCES,
            "v24800": Path("results/v24800_exact220_result_v1_20260807.json"),
            "v24850": Path("results/v24850_v24800_replication_exact220_result_v1_20260808.json"),
            "v24854": Path("results/v24854_rate_aware_exact220_result_v1_20260808.json"),
        },
    }
    for name, value in assignments.items():
        setattr(base, name, value)


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
