#!/usr/bin/env python3
"""Audit and evaluate the frozen V2.55.68 deterministic-constraint exact-220 run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25568_constraint_exact220_contract as contract  # noqa: E402
from scripts import finalize_v25267_production_only_exact220 as base  # noqa: E402
from scripts import run_v25568_constraint_exact220 as runner  # noqa: E402


EVALUATOR_ROOT = contract.OUTPUT_ROOT / "evaluator"


def configure() -> None:
    base.contract = contract
    base.runner = runner
    base.EVALUATOR_ROOT = EVALUATOR_ROOT
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
            "v25406_latest_complete": contract.LATEST_RESULT,
            "v24969_replication": contract.REPLICATION_RESULT,
            "v24857_single_rollout_peak": contract.PEAK_RESULT,
        },
        "SOURCE_MANIFEST": contract.SOURCE_MANIFEST,
    }
    for name, value in assignments.items():
        setattr(base.base, name, value)
    base.base.contract = contract
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
    copied["native_role"] = "v25568_constraint_exact220_forward_audit"
    aggregate = _forward_barrier()["forward"]["aggregate"]
    checks = dict(copied["checks"])
    checks["truthful_physical_caps_preserved"] = (
        aggregate["maximum_queries_on_one_task"] <= 4
        and aggregate["maximum_fetches_on_one_task"] <= 14
        and aggregate["maximum_model_forwards_on_one_task"] <= 3
    )
    findings = sorted(name for name, passed in checks.items() if not passed)
    authorization = dict(copied["authorization"])
    authorization["postfreeze_exact220_evaluator_protocol"] = not findings
    copied.update(
        {
            "checks": checks,
            "findings": findings,
            "audit_valid": not findings,
            "truthful_physical_caps": {
                "maximum_queries_on_one_task": aggregate[
                    "maximum_queries_on_one_task"
                ],
                "maximum_fetches_on_one_task": aggregate[
                    "maximum_fetches_on_one_task"
                ],
                "maximum_model_forwards_on_one_task": aggregate[
                    "maximum_model_forwards_on_one_task"
                ],
            },
            "authorization": authorization,
        }
    )
    return contract.seal(copied, "audit_payload_sha256")


def main() -> None:
    configure()
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit", "protocol", "evaluate", "postaudit"))
    args = parser.parse_args()
    if args.command == "audit":
        value = _build_native_forward_audit()
        if not value["audit_valid"]:
            raise RuntimeError(value["findings"])
        base._publish_new(ROOT / contract.FORWARD_AUDIT, value)
        print(
            json.dumps(
                {
                    "path": str(contract.FORWARD_AUDIT),
                    "audit_valid": True,
                    "findings": [],
                },
                sort_keys=True,
            )
        )
        return
    # Call the fixed evaluator directly after the V2.55.68 bindings above;
    # entering the intermediate V2.52.67 main would re-run its configure()
    # and overwrite the successor reference names.
    sys.argv = [sys.argv[0], args.command]
    base.base.main()


if __name__ == "__main__":
    main()
