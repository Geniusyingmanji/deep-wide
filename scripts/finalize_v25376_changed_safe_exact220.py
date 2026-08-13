#!/usr/bin/env python3
"""Audit and evaluate the frozen V2.53.76 changed-safe exact-220 run."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25376_changed_safe_exact220_contract as contract  # noqa: E402
from scripts import finalize_v25267_production_only_exact220 as base  # noqa: E402
from scripts import run_v25376_changed_safe_exact220 as runner  # noqa: E402


EVALUATOR_ROOT = contract.OUTPUT_ROOT / "evaluator"


def configure() -> None:
    base.contract = contract
    base.runner = runner
    assignments = {
        "FORWARD_AUDIT": contract.FORWARD_AUDIT,
        "EVALUATOR_PROTOCOL": contract.EVALUATOR_PROTOCOL,
        "FINAL_RESULT": contract.RESULT,
        "POSTAUDIT": contract.POSTAUDIT,
        "EVALUATOR_ROOT": EVALUATOR_ROOT,
        "PREPARE_ATTESTATION": EVALUATOR_ROOT / "prepare_attestation.json",
        "JOINED_OUTCOMES": EVALUATOR_ROOT / "terminal_outcomes_evaluator_joined.jsonl",
        "OFFICIAL_PREDICTIONS": EVALUATOR_ROOT / "official_predictions.jsonl",
        "EVALUATOR_RUNS": EVALUATOR_ROOT / "official_eval_workers",
        "EVALUATOR_LOGS": EVALUATOR_ROOT / "logs",
        "MERGED_RESULTS": EVALUATOR_ROOT / "official_eval_results.jsonl",
        "MERGE_ATTESTATION": EVALUATOR_ROOT / "merge_attestation.json",
        "SUMMARY": EVALUATOR_ROOT / "conservative_summary.json",
        "EVALUATOR_OWNER": contract.EVALUATOR_OWNER,
        "EVALUATOR_PURPOSE": contract.EVALUATOR_PURPOSE,
        "CONTROL_FILES": (
            str(contract.FINALIZER),
            str(contract.RUNNER),
            str(contract.CONTROL),
            str(contract.CONTRACT),
            str(contract.RUNTIME),
            str(contract.CAP_RUNTIME),
            str(contract.TEST),
            str(contract.RUNTIME_TEST),
            "scripts/finalize_v25267_production_only_exact220.py",
            "scripts/finalize_v24791_exact220.py",
            "scripts/run_official_eval_local.py",
            "scripts/finalize_v24287_exact220.py",
            "scripts/finalize_fullset_rollout.py",
            "scripts/deepwide_api_lease.py",
        ),
        "REFERENCES": {
            "v25342_latest_complete": contract.LATEST_RESULT,
            "v24969_replication": contract.REPLICATION_RESULT,
            "v24857_single_rollout_peak": contract.PEAK_RESULT,
        },
        "SOURCE_MANIFEST": contract.SOURCE_MANIFEST,
    }
    for name, value in assignments.items():
        setattr(base.base, name, value)
    base._forward_barrier = _forward_barrier
    base.base._forward_barrier = _forward_barrier


def _forward_barrier():
    original_contract, original_runner = base.contract, base.runner
    try:
        base.contract = contract
        base.runner = runner
        return base._forward_barrier_original()
    finally:
        base.contract, base.runner = original_contract, original_runner


base._forward_barrier_original = base._forward_barrier


def _build_native_forward_audit():
    configure()
    value = base._build_native_forward_audit()
    copied = dict(value)
    copied.pop("audit_payload_sha256", None)
    copied["native_role"] = "v25378_changed_safe_exact220_forward_audit"
    aggregate = copied.get("aggregate") or {}
    if aggregate and aggregate.get("maximum_model_forwards_on_one_task", 4) > 3:
        raise RuntimeError("V2.53.76 forward exceeded three model effects")
    return contract.seal(copied, "audit_payload_sha256")


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
