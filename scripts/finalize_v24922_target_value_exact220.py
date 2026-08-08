#!/usr/bin/env python3
"""Post-freeze audit and evaluator for V2.49.22 exact-220."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24922_target_value_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24800_exact220 as base  # noqa: E402


def configure() -> None:
    date = contract.DATE
    evaluator_root = contract.OUTPUT_ROOT / "evaluator"
    assignments = {
        "contract": contract,
        "FORWARD_AUDIT": contract.FORWARD_AUDIT,
        "EVALUATOR_PROTOCOL": Path(
            f"results/v24922_target_value_exact220_evaluator_preregistration_v1_{date}.json"
        ),
        "FINAL_RESULT": Path(
            f"results/v24922_target_value_exact220_result_v1_{date}.json"
        ),
        "POSTAUDIT": Path(
            f"results/v24922_target_value_exact220_postresult_audit_v1_{date}.json"
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
        "EVALUATOR_OWNER": "v24922_target_value_exact220_evaluator_v1",
        "EVALUATOR_PURPOSE": "postfreeze_fixed_partition_parallel_v24922_target_value_exact220_evaluator",
        "CONTROL_FILES": (
            "scripts/finalize_v24922_target_value_exact220.py",
            "scripts/run_v24922_target_value_exact220.py",
            "scripts/run_v24922_target_value_exact220_task.py",
            "scripts/control_v24922_target_value_exact220.py",
            "src/deepwide_agent/v24922_target_value_exact220_contract.py",
            "src/deepwide_agent/v24921_target_value_coverage_projector.py",
            "tests/test_v24922_target_value_exact220.py",
            "scripts/finalize_v24800_exact220.py",
            "scripts/run_official_eval_local.py",
            "scripts/finalize_v24287_exact220.py",
            "scripts/finalize_fullset_rollout.py",
            "scripts/deepwide_api_lease.py",
        ),
        "REFERENCES": {
            **base.REFERENCES,
            "v24800": Path("results/v24800_exact220_result_v1_20260807.json"),
            "v24848": Path("results/v24848_atomic_table_header_30k_exact220_result_v1_20260808.json"),
            "v24857": Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json"),
            "v24918": Path("results/v24918_prefix_total_exact220_result_v2_20260808.json"),
        },
    }
    for name, value in assignments.items():
        setattr(base, name, value)

    role_projection = {
        "v24922_target_value_exact220_forward_result": (
            "v24800_exact220_forward_result",
            "result_payload_sha256",
        ),
        "v24922_target_value_exact220_run_summary": (
            "v24800_exact220_run_summary",
            "summary_payload_sha256",
        ),
        "v24922_target_value_exact220_prediction_freeze": (
            "v24800_exact220_prediction_freeze",
            "freeze_payload_sha256",
        ),
    }
    inherited_read = base._read

    def compatible_read(path: Path) -> dict:
        raw = inherited_read(path)
        projected = role_projection.get(raw.get("role"))
        if projected is None:
            return raw
        role, field = projected
        unsigned = dict(raw)
        seal = unsigned.pop(field, None)
        if seal != contract.payload_sha256(unsigned):
            raise RuntimeError("V2.49.22 forward seal drifted before projection")
        value = dict(raw)
        value["role"] = role
        value.pop(field, None)
        value[field] = contract.payload_sha256(value)
        return value

    base._read = compatible_read

    inherited_barrier = base._forward_barrier

    def receipt_bound_forward_barrier() -> dict:
        barrier = inherited_barrier()
        observed = contract.projection_receipt_summary(ROOT)
        if barrier["summary"].get("direct_search_totals", {}).get(
            "target_value_projection"
        ) != observed:
            raise RuntimeError("V2.49.22 projection receipt aggregate drifted")
        return barrier

    base._forward_barrier = receipt_bound_forward_barrier


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
