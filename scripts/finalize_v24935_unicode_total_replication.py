#!/usr/bin/env python3
"""Post-freeze audit and evaluator for the V2.49.32 cold replication."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24935_unicode_total_replication_contract as contract  # noqa: E402
from scripts import finalize_v24932_unicode_total_exact220 as parent  # noqa: E402


def configure() -> None:
    parent.contract = contract
    parent.configure()
    engine = parent.parent.base
    date = contract.DATE
    evaluator_root = contract.OUTPUT_ROOT / "evaluator"
    engine.EVALUATOR_PROTOCOL = Path(
        f"results/v24935_unicode_total_replication_evaluator_preregistration_v1_{date}.json"
    )
    engine.FINAL_RESULT = Path(
        f"results/v24935_unicode_total_replication_result_v1_{date}.json"
    )
    engine.POSTAUDIT = Path(
        f"results/v24935_unicode_total_replication_postresult_audit_v1_{date}.json"
    )
    engine.EVALUATOR_ROOT = evaluator_root
    engine.PREPARE_ATTESTATION = evaluator_root / "prepare_attestation.json"
    engine.JOINED_OUTCOMES = evaluator_root / "terminal_outcomes_evaluator_joined.jsonl"
    engine.OFFICIAL_PREDICTIONS = evaluator_root / "official_predictions.jsonl"
    engine.EVALUATOR_RUNS = evaluator_root / "official_eval_workers"
    engine.EVALUATOR_LOGS = evaluator_root / "logs"
    engine.MERGED_RESULTS = evaluator_root / "official_eval_results.jsonl"
    engine.MERGE_ATTESTATION = evaluator_root / "merge_attestation.json"
    engine.SUMMARY = evaluator_root / "conservative_summary.json"
    engine.EVALUATOR_OWNER = "v24935_unicode_total_replication_evaluator_v1"
    engine.EVALUATOR_PURPOSE = "postfreeze_fixed_partition_parallel_v24935_exact220_evaluator"
    engine.CONTROL_FILES = tuple(
        dict.fromkeys(
            (
                str(contract.FINALIZER),
                str(contract.RUNNER),
                str(contract.CHILD),
                str(contract.CONTROL),
                str(contract.SOURCE),
                str(contract.TEST),
                *engine.CONTROL_FILES,
            )
        )
    )
    engine.REFERENCES = {
        **engine.REFERENCES,
        "v24857": Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json"),
        "v24932": Path("results/v24932_unicode_total_exact220_result_v1_20260809.json"),
    }


def main() -> None:
    configure()
    parent.parent.base.main()


if __name__ == "__main__":
    main()
