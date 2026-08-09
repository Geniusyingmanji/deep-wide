#!/usr/bin/env python3
"""Post-freeze evaluator and strict project-best decision for V2.50.23."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25023_distinct_coverage_exact220_contract as contract  # noqa: E402
from scripts import finalize_v24857_pacing_aware_exact220 as parent  # noqa: E402


REFERENCE = Path("results/v24857_pacing_aware_exact220_result_v1_20260808.json")


def configure() -> None:
    parent.contract = contract
    parent.configure()
    engine = parent.base
    evaluator_root = contract.OUTPUT_ROOT / "evaluator"
    assignments = {
        "contract": contract,
        "FORWARD_AUDIT": contract.FORWARD_AUDIT,
        "EVALUATOR_PROTOCOL": contract.EVALUATOR_PROTOCOL,
        "FINAL_RESULT": contract.RESULT,
        "POSTAUDIT": contract.POSTAUDIT,
        "EVALUATOR_ROOT": evaluator_root,
        "PREPARE_ATTESTATION": evaluator_root / "prepare_attestation.json",
        "JOINED_OUTCOMES": evaluator_root / "terminal_outcomes_evaluator_joined.jsonl",
        "OFFICIAL_PREDICTIONS": evaluator_root / "official_predictions.jsonl",
        "EVALUATOR_RUNS": evaluator_root / "official_eval_workers",
        "EVALUATOR_LOGS": evaluator_root / "logs",
        "MERGED_RESULTS": evaluator_root / "official_eval_results.jsonl",
        "MERGE_ATTESTATION": evaluator_root / "merge_attestation.json",
        "SUMMARY": evaluator_root / "conservative_summary.json",
        "EVALUATOR_OWNER": "v25023_distinct_coverage_exact220_evaluator_v1",
        "EVALUATOR_PURPOSE": "postfreeze_fixed_partition_v25023_exact220_evaluator",
    }
    for name, value in assignments.items():
        setattr(engine, name, value)
    engine.CONTROL_FILES = tuple(
        dict.fromkeys(
            (
                str(contract.FINALIZER),
                str(contract.RUNNER),
                str(contract.CHILD),
                str(contract.CONTROL),
                str(contract.SOURCE),
                str(contract.TEST),
                str(contract.SELECTION_SOURCE),
                str(contract.RETRIEVAL_SOURCE),
                str(contract.SEARCH_SOURCE),
                str(contract.TASK_INTEGRATION_SOURCE),
                str(contract.PROJECTOR_SOURCE),
                str(contract.FETCH_SOURCE),
                str(contract.FETCH_HELPER),
                *engine.CONTROL_FILES,
            )
        )
    )
    engine.REFERENCES = {
        **engine.REFERENCES,
        "v24857": REFERENCE,
        "v24969": Path("results/v24969_pacing_aware_replication_result_v1_20260809.json"),
    }


def _read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(f"V2.50.23 expected ordinary object: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.50.23 expected JSON object")
    return value


def quality_checks(
    current: dict[str, Any],
    prior: dict[str, Any],
    direct: dict[str, Any],
    *,
    postresult_audit_valid: bool,
) -> dict[str, bool]:
    rate = direct["rate_aware"]
    return {
        "postresult_audit_valid": bool(postresult_audit_valid),
        "whole_table_exact_strict_gain_over_v24857": current["whole_table_successes"] > prior["whole_table_successes"],
        "composite_strict_gain_over_v24857": current["quality_composite"] > prior["quality_composite"],
        "entity_nonregression": current["entity_acc"] >= prior["entity_acc"],
        "row_f1_nonregression": current["f1_by_row"] >= prior["f1_by_row"],
        "item_f1_nonregression": current["f1_by_item"] >= prior["f1_by_item"],
        "column_f1_nonregression": current["column_f1"] >= prior["column_f1"],
        "evaluator_invalid_nonincrease": current["evaluator_invalid_or_not_run"] <= prior["evaluator_invalid_or_not_run"],
        "fallback_nonincrease": current["fallback_tables"] <= prior["fallback_tables"],
        "provider_429_nonincrease": direct["status_429"] <= 0,
        "transport_failure_nonincrease": direct["transport_failures"] <= 0,
        "slot_timeout_nonincrease": direct["slot_timeouts"] <= 0,
        "provider_gate_timeout_nonincrease": rate["provider_gate_timeouts"] <= 0,
    }


def build_quality_decision(*, now: int | None = None) -> dict[str, Any]:
    configure()
    engine = parent.base
    post = engine.validate_postresult_audit(_read(ROOT / contract.POSTAUDIT))
    result = _read(ROOT / contract.RESULT)
    reference = _read(ROOT / REFERENCE)
    current = result["metrics"]["all_220"]
    prior = reference["metrics"]["all_220"]
    forward = _read(ROOT / contract.FORWARD_RESULT)
    direct = forward["direct_search_totals"]
    checks = quality_checks(
        current,
        prior,
        direct,
        postresult_audit_valid=(
            post["audit_valid"] is True and post["findings"] == []
        ),
    )
    passed = all(checks.values())
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v25023_distinct_coverage_exact220_quality_decision",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "status": "strict_project_best_go" if passed else "strict_project_best_no_go",
        "passed": passed,
        "checks": checks,
        "candidate_metrics": current,
        "reference_v24857_metrics": prior,
        "deltas": {
            "whole_table_successes": current["whole_table_successes"] - prior["whole_table_successes"],
            "quality_composite": current["quality_composite"] - prior["quality_composite"],
            "entity_acc": current["entity_acc"] - prior["entity_acc"],
            "f1_by_row": current["f1_by_row"] - prior["f1_by_row"],
            "f1_by_item": current["f1_by_item"] - prior["f1_by_item"],
            "column_f1": current["column_f1"] - prior["column_f1"],
        },
        "provenance": {
            "result_sha256": contract.sha256(ROOT / contract.RESULT),
            "postresult_audit_sha256": contract.sha256(ROOT / contract.POSTAUDIT),
            "reference_v24857_sha256": contract.sha256(ROOT / REFERENCE),
            "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        },
        "claim_scope": {
            "repository_single_rollout_project_best": passed,
            "leaderboard_submitted": False,
            "sota_supported": False,
            "avg_at_4_measured": False,
            "entropy_or_signed_credit_validated": False,
        },
        "authorization": {
            "future_candidate_design": passed,
            "leaderboard_or_sota_claim": False,
            "retry_rerun_selective_revaluation": False,
        },
    }
    value["decision_payload_sha256"] = contract.payload_sha256(value)
    return value


def main() -> None:
    if len(sys.argv) == 2 and sys.argv[1] == "decision":
        value = build_quality_decision()
        parent.base.publish_new(ROOT / contract.QUALITY_DECISION, value)
        print(json.dumps({"path": str(contract.QUALITY_DECISION), "status": value["status"], "passed": value["passed"], "deltas": value["deltas"]}, sort_keys=True))
        return
    configure()
    parent.base.main()


if __name__ == "__main__":
    main()
