#!/usr/bin/env python3
"""Zero-network recovery for the V2.50.27 post-freeze quality evaluation."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25027_clue_resolved_external_contract as parent  # noqa: E402
from deepwide_agent import v25028_clue_evaluation_recovery_contract as contract  # noqa: E402
from scripts import evaluate_v25027_clue_resolved_external as evaluator  # noqa: E402


def _publish(relative: Path, value: Mapping[str, Any]) -> None:
    path = ROOT / relative
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _clean_pushed() -> None:
    if contract.git(ROOT, "status", "--porcelain") or contract.git(
        ROOT, "rev-parse", "HEAD"
    ) != contract.git(ROOT, "rev-parse", "target/main"):
        raise RuntimeError("V2.50.28 requires clean pushed HEAD")


def _read_jsonl(relative: Path) -> list[dict[str, Any]]:
    path = ROOT / relative
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
        raise RuntimeError("V2.50.28 expected ordinary frozen JSONL")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if len(rows) != parent.TASK_COUNT or any(not isinstance(row, dict) for row in rows):
        raise RuntimeError("V2.50.28 frozen row denominator drifted")
    return rows


def _parents() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    failure = contract.read_json(ROOT / contract.FAILURE)
    unsigned = dict(failure)
    seal = unsigned.pop("failure_payload_sha256", None)
    audit = contract.read_json(ROOT / contract.PARENT_AUDIT)
    gold = contract.read_json(ROOT / contract.FROZEN_GOLD)
    if (
        seal != contract.payload_sha256(unsigned)
        or failure.get("prediction_metric_rows_evaluated") != 0
        or failure.get("gold_refetch_allowed") is not False
        or failure.get("quality_result_created") is not False
        or audit.get("audit_valid") is not True
        or audit.get("mechanism_gate", {}).get("passed") is not True
        or not parent.sealed(audit, "audit_payload_sha256")
        or gold.get("prediction_freeze_preexisted") is not True
        or gold.get("single_fetch_no_retry_or_refetch") is not True
        or not parent.sealed(gold, "gold_payload_sha256")
        or len(gold.get("records") or {}) != parent.TASK_COUNT
    ):
        raise RuntimeError("V2.50.28 frozen recovery parent drifted")
    return failure, audit, gold


def preregister() -> dict[str, Any]:
    _clean_pushed()
    _parents()
    if any((ROOT / path).exists() or (ROOT / path).is_symlink() for path in (contract.PROTOCOL, contract.RESULT, contract.POSTAUDIT)):
        raise RuntimeError("V2.50.28 recovery surface is not pristine")
    return contract.build_protocol(ROOT, now=int(time.time()), tracked=True)


def evaluate() -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, contract.read_json(ROOT / contract.PROTOCOL), tracked=True)
    _failure, audit, gold = _parents()
    if (ROOT / contract.RESULT).exists() or (ROOT / contract.RESULT).is_symlink():
        raise FileExistsError(ROOT / contract.RESULT)
    rows = _read_jsonl(contract.FROZEN_ROWS)
    metrics = evaluator.evaluate_rows(rows, gold["records"])
    delta = metrics[f"{parent.CANDIDATE_ARM}_minus_{parent.CONTROL_ARM}"]
    passed = (
        audit["mechanism_gate"]["passed"] is True
        and delta["exact_table_successes"] > 0
        and delta["composite"] > 0
        and all(delta[key] >= 0 for key in ("entity_recall", "row_f1", "item_f1", "column_f1"))
    )
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25028_clue_quality_recovery_result",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "status": "clue_quality_recovery_go" if passed else "clue_quality_recovery_no_go",
            "passed": passed,
            "metrics": metrics,
            "mechanism": audit["mechanism_gate"],
            "fixed_denominator_failure_as_zero": True,
            "evaluated_task_count": parent.TASK_COUNT,
            "evaluated_prediction_count": parent.TASK_COUNT * len(parent.ARMS),
            "network_model_search_fetch_or_forward_effect": False,
            "gold_refetched": False,
            "retry_resume_skip_or_selective_revaluation": False,
            "frozen_input_manifest_sha256": protocol["frozen_input_manifest_sha256"],
            "claim_scope": {
                "benchmark_external_quality_measured": True,
                "deepwidebench_quality_measured": False,
                "entropy_or_signed_credit_validated": False,
                "leaderboard_or_sota_supported": False,
            },
            "authorization": {
                "production_candidate_design": passed,
                "public_exact220_launch": False,
                "leaderboard_or_sota": False,
            },
        },
        "result_payload_sha256",
    )


def postaudit() -> dict[str, Any]:
    _clean_pushed()
    protocol = contract.validate_protocol(ROOT, contract.read_json(ROOT / contract.PROTOCOL), tracked=True)
    result = contract.read_json(ROOT / contract.RESULT)
    findings: list[str] = []
    if not contract.sealed(result, "result_payload_sha256"):
        findings.append("result_seal_invalid")
    if result.get("evaluated_task_count") != parent.TASK_COUNT or result.get("evaluated_prediction_count") != 40:
        findings.append("fixed_denominator_drifted")
    if result.get("network_model_search_fetch_or_forward_effect") is not False or result.get("gold_refetched") is not False:
        findings.append("zero_effect_contract_drifted")
    if result.get("frozen_input_manifest_sha256") != protocol["frozen_input_manifest_sha256"]:
        findings.append("frozen_input_binding_drifted")
    return contract.seal(
        {
            "artifact_version": 1,
            "role": "v25028_clue_quality_recovery_postresult_audit",
            "protocol_id": contract.PROTOCOL_ID,
            "created_at_unix": int(time.time()),
            "result_sha256": contract.sha256(ROOT / contract.RESULT),
            "findings": findings,
            "audit_valid": not findings,
            "network_model_search_fetch_evaluator_or_gold_refetch_called_by_audit": False,
            "authorization": {
                "production_candidate_design": not findings and result.get("passed") is True,
                "public_exact220_launch": False,
                "leaderboard_or_sota": False,
            },
        },
        "audit_payload_sha256",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preregister", "evaluate", "postaudit"))
    args = parser.parse_args()
    if args.command == "preregister":
        value, path = preregister(), contract.PROTOCOL
    elif args.command == "evaluate":
        value, path = evaluate(), contract.RESULT
    else:
        value, path = postaudit(), contract.POSTAUDIT
    _publish(path, value)
    print(json.dumps({
        "path": str(path), "status": value.get("status"), "passed": value.get("passed"),
        "metrics": value.get("metrics"), "findings": value.get("findings"),
        "authorization": value.get("authorization"),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
