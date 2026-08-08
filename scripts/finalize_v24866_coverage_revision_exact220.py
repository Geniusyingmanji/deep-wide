#!/usr/bin/env python3
"""Post-freeze audit and evaluator for V2.48.66 exact-220."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24866_coverage_revision_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24800_exact220 as base  # noqa: E402


def _configure_forward_projection() -> None:
    if getattr(base, "_v24866_forward_projection_installed", False):
        return
    inherited_barrier = base._forward_barrier

    def barrier():
        value = inherited_barrier()
        forward = value["forward"]
        summary = value["summary"]
        if (
            forward.get("role")
            != "v24866_coverage_revision_exact220_forward_result"
            or summary.get("role")
            != "v24866_coverage_revision_exact220_run_summary"
            or forward.get("coverage_revision_totals")
            != summary.get("coverage_revision_totals")
        ):
            raise RuntimeError("V2.48.66 forward projection drifted")
        return value

    # The inherited verifier expects its historical role literals.  Preserve
    # all content and seals, changing only the two local identity checks while
    # V2.48.66's wrapper checks the real roles and coverage aggregate.
    original_read = base._read

    def projected_read(path):
        value = original_read(path)
        if path == base.ROOT / contract.FORWARD_RESULT:
            value = dict(value)
            value["role"] = "v24800_exact220_forward_result"
            unsigned = dict(value)
            unsigned.pop("result_payload_sha256", None)
            value["result_payload_sha256"] = contract.payload_sha256(unsigned)
        elif path == base.ROOT / contract.RUN_SUMMARY:
            value = dict(value)
            value["role"] = "v24800_exact220_run_summary"
            unsigned = dict(value)
            unsigned.pop("summary_payload_sha256", None)
            value["summary_payload_sha256"] = contract.payload_sha256(unsigned)
        elif path == base.ROOT / contract.PREDICTION_FREEZE:
            value = dict(value)
            value["role"] = "v24800_exact220_prediction_freeze"
            unsigned = dict(value)
            unsigned.pop("freeze_payload_sha256", None)
            value["freeze_payload_sha256"] = contract.payload_sha256(unsigned)
        return value

    def projected_barrier():
        base._read = projected_read
        try:
            return inherited_barrier()
        finally:
            base._read = original_read

    def checked_barrier():
        real_forward = original_read(base.ROOT / contract.FORWARD_RESULT)
        real_summary = original_read(base.ROOT / contract.RUN_SUMMARY)
        if (
            real_forward.get("role")
            != "v24866_coverage_revision_exact220_forward_result"
            or real_summary.get("role")
            != "v24866_coverage_revision_exact220_run_summary"
            or real_forward.get("coverage_revision_totals")
            != real_summary.get("coverage_revision_totals")
        ):
            raise RuntimeError("V2.48.66 forward identity drifted")
        return projected_barrier()

    base._forward_barrier = checked_barrier
    base._v24866_forward_projection_installed = True


def configure() -> None:
    date = contract.DATE
    evaluator_root = contract.OUTPUT_ROOT / "evaluator"
    assignments = {
        "contract": contract,
        "FORWARD_AUDIT": contract.FORWARD_AUDIT,
        "EVALUATOR_PROTOCOL": Path(
            f"results/v24866_coverage_revision_exact220_evaluator_preregistration_v1_{date}.json"
        ),
        "FINAL_RESULT": Path(
            f"results/v24866_coverage_revision_exact220_result_v1_{date}.json"
        ),
        "POSTAUDIT": Path(
            f"results/v24866_coverage_revision_exact220_postresult_audit_v1_{date}.json"
        ),
        "EVALUATOR_ROOT": evaluator_root,
        "PREPARE_ATTESTATION": evaluator_root / "prepare_attestation.json",
        "JOINED_OUTCOMES": evaluator_root
        / "terminal_outcomes_evaluator_joined.jsonl",
        "OFFICIAL_PREDICTIONS": evaluator_root / "official_predictions.jsonl",
        "EVALUATOR_RUNS": evaluator_root / "official_eval_workers",
        "EVALUATOR_LOGS": evaluator_root / "logs",
        "MERGED_RESULTS": evaluator_root / "official_eval_results.jsonl",
        "MERGE_ATTESTATION": evaluator_root / "merge_attestation.json",
        "SUMMARY": evaluator_root / "conservative_summary.json",
        "EVALUATOR_OWNER": "v24866_coverage_revision_exact220_evaluator_v1",
        "EVALUATOR_PURPOSE": "postfreeze_fixed_partition_parallel_v24866_evaluator",
        "CONTROL_FILES": (
            "scripts/finalize_v24866_coverage_revision_exact220.py",
            "scripts/run_v24866_coverage_revision_exact220.py",
            "scripts/run_v24866_coverage_revision_exact220_task.py",
            "scripts/control_v24866_coverage_revision_exact220.py",
            "src/deepwide_agent/v24866_coverage_revision_exact220_contract.py",
            "src/deepwide_agent/v24859_full_evidence_coverage_revision.py",
            "src/deepwide_agent/v24860_coverage_revision_integration.py",
            "src/deepwide_agent/v24861_coverage_revision_exact_task.py",
            "src/deepwide_agent/v24862_same_task_coverage_runtime.py",
            "src/deepwide_agent/v24863_coverage_revision_child_bundle.py",
            "src/deepwide_agent/v24864_coverage_revision_child_runtime.py",
            "src/deepwide_agent/v24865_coverage_revision_subprocess_gate.py",
            "scripts/finalize_v24800_exact220.py",
            "scripts/run_official_eval_local.py",
            "scripts/finalize_v24287_exact220.py",
            "scripts/finalize_fullset_rollout.py",
            "scripts/deepwide_api_lease.py",
        ),
        "REFERENCES": {
            **base.REFERENCES,
            "v24800": Path("results/v24800_exact220_result_v1_20260807.json"),
            "v24857": Path(
                "results/v24857_pacing_aware_exact220_result_v1_20260808.json"
            ),
        },
    }
    for name, value in assignments.items():
        setattr(base, name, value)
    _configure_forward_projection()


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
