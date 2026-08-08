#!/usr/bin/env python3
"""Post-freeze audit and evaluator for V2.48.48 atomic-table-header 30k exact-220."""

from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24848_atomic_table_header_30k_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24791_exact220 as base  # noqa: E402


def configure() -> None:
    assignments = {
        "contract": contract,
        "FORWARD_AUDIT": contract.FORWARD_AUDIT,
        "EVALUATOR_PROTOCOL": Path(
            f"results/v24848_atomic_table_header_30k_exact220_evaluator_preregistration_v1_{contract.DATE}.json"
        ),
        "FINAL_RESULT": Path(
            f"results/v24848_atomic_table_header_30k_exact220_result_v1_{contract.DATE}.json"
        ),
        "POSTAUDIT": Path(
            f"results/v24848_atomic_table_header_30k_exact220_postresult_audit_v1_{contract.DATE}.json"
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
        "EVALUATOR_OWNER": "v24848_atomic_table_header_30k_exact220_evaluator_v1",
        "EVALUATOR_PURPOSE": "postfreeze_fixed_partition_parallel_v24848_atomic_table_header_30k_exact220_official_evaluator",
    }
    for name, value in assignments.items():
        setattr(base, name, value)
    base.CONTROL_FILES = (
        "scripts/finalize_v24848_atomic_table_header_30k_exact220.py",
        "scripts/finalize_v24791_exact220.py",
        "scripts/run_official_eval_local.py",
        "scripts/finalize_v24287_exact220.py",
        "scripts/finalize_fullset_rollout.py",
        "scripts/deepwide_api_lease.py",
        "tests/test_v24848_atomic_table_header_30k_exact220.py",
    )
    base.REFERENCES = {
        **base.REFERENCES,
        "v24800": Path("results/v24800_exact220_result_v1_20260807.json"),
        "v24834": Path("results/v24834_coverage_margin_exact220_result_v1_20260807.json"),
        "v24837": Path("results/v24837_information_bottleneck_exact220_result_v1_20260807.json"),
        "v24840": Path("results/v24840_structure_preserving_exact220_result_v1_20260807.json"),
        "v24844": Path("results/v24844_atomic_table_header_exact220_result_v1_20260808.json"),
    }

    inherited_read = base._read
    projections = {
        "v24848_atomic_table_header_30k_exact220_forward_result": (
            "v24791_exact220_forward_result",
            "result_payload_sha256",
        ),
        "v24848_atomic_table_header_30k_exact220_run_summary": (
            "v24791_exact220_run_summary",
            "summary_payload_sha256",
        ),
        "v24848_atomic_table_header_30k_exact220_prediction_freeze": (
            "v24791_exact220_prediction_freeze",
            "freeze_payload_sha256",
        ),
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
            raise RuntimeError("V2.48.48 forward seal drifted before projection")
        value = copy.deepcopy(raw)
        value["role"] = role
        value.pop(seal_field, None)
        value[seal_field] = contract.payload_sha256(value)
        return value

    base._read = compatible_read
    inherited_barrier = base._forward_barrier

    def receipt_bound_forward_barrier() -> dict:
        barrier = inherited_barrier()
        observed = contract.projection_receipt_summary(ROOT)
        if (
            barrier["summary"].get("projection_receipts") != observed
            or barrier["forward"].get("projection_receipts") != observed
            or barrier["freeze"].get("projection_receipts") != observed
        ):
            raise RuntimeError("V2.48.48 projection receipt aggregate drifted")
        return barrier

    base._forward_barrier = receipt_bound_forward_barrier


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
