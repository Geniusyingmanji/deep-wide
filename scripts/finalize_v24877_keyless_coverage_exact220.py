#!/usr/bin/env python3
"""Post-freeze audit and evaluator for V2.48.77 exact-220."""

from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24877_keyless_coverage_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24791_exact220 as base  # noqa: E402


FORWARD_ROLE = "v24877_keyless_coverage_exact220_forward_result"
SUMMARY_ROLE = "v24877_keyless_coverage_exact220_run_summary"
FREEZE_ROLE = "v24877_keyless_coverage_exact220_prediction_freeze"


def _reseal(value: dict, *, role: str, field: str) -> dict:
    copied = copy.deepcopy(value)
    copied["role"] = role
    copied.pop(field, None)
    copied[field] = contract.payload_sha256(copied)
    return copied


def configure() -> None:
    assignments = {
        "contract": contract,
        "FORWARD_AUDIT": contract.FORWARD_AUDIT,
        "EVALUATOR_PROTOCOL": Path(
            f"results/v24877_keyless_coverage_exact220_evaluator_preregistration_v1_{contract.DATE}.json"
        ),
        "FINAL_RESULT": Path(
            f"results/v24877_keyless_coverage_exact220_result_v1_{contract.DATE}.json"
        ),
        "POSTAUDIT": Path(
            f"results/v24877_keyless_coverage_exact220_postresult_audit_v1_{contract.DATE}.json"
        ),
        "EVALUATOR_ROOT": contract.OUTPUT_ROOT / "evaluator",
        "PREPARE_ATTESTATION": contract.OUTPUT_ROOT / "evaluator" / "prepare_attestation.json",
        "JOINED_OUTCOMES": contract.OUTPUT_ROOT / "evaluator" / "terminal_outcomes_evaluator_joined.jsonl",
        "OFFICIAL_PREDICTIONS": contract.OUTPUT_ROOT / "evaluator" / "official_predictions.jsonl",
        "EVALUATOR_RUNS": contract.OUTPUT_ROOT / "evaluator" / "official_eval_workers",
        "EVALUATOR_LOGS": contract.OUTPUT_ROOT / "evaluator" / "logs",
        "MERGED_RESULTS": contract.OUTPUT_ROOT / "evaluator" / "official_eval_results.jsonl",
        "MERGE_ATTESTATION": contract.OUTPUT_ROOT / "evaluator" / "merge_attestation.json",
        "SUMMARY": contract.OUTPUT_ROOT / "evaluator" / "conservative_summary.json",
        "EVALUATOR_OWNER": "v24877_keyless_coverage_exact220_evaluator_v1",
        "EVALUATOR_PURPOSE": "postfreeze_fixed_partition_parallel_v24877_keyless_coverage_exact220",
    }
    for name, value in assignments.items():
        setattr(base, name, value)
    base.CONTROL_FILES = (
        "scripts/finalize_v24877_keyless_coverage_exact220.py",
        "scripts/finalize_v24791_exact220.py",
        "scripts/run_official_eval_local.py",
        "scripts/finalize_v24287_exact220.py",
        "scripts/finalize_fullset_rollout.py",
        "scripts/deepwide_api_lease.py",
        "tests/test_v24877_keyless_coverage_exact220.py",
    )
    base.REFERENCES = {
        **base.REFERENCES,
        "v24831": Path("results/v24831_keyless_exact220_result_v1_20260807.json"),
        "v24857": Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json"),
        "v24866": Path("results/v24866_coverage_revision_exact220_result_v1_20260808r2.json"),
    }

    inherited_read = base._read
    projections = {
        FORWARD_ROLE: ("v24791_exact220_forward_result", "result_payload_sha256"),
        SUMMARY_ROLE: ("v24791_exact220_run_summary", "summary_payload_sha256"),
        FREEZE_ROLE: ("v24791_exact220_prediction_freeze", "freeze_payload_sha256"),
    }

    def compatible_read(path: Path) -> dict:
        raw = inherited_read(path)
        projection = projections.get(raw.get("role"))
        if projection is None:
            return raw
        role, seal_field = projection
        unsigned = dict(raw)
        seal = unsigned.pop(seal_field, None)
        if seal != contract.payload_sha256(unsigned):
            raise RuntimeError("V2.48.77 artifact seal drifted before projection")
        return _reseal(raw, role=role, field=seal_field)

    base._read = compatible_read



def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
