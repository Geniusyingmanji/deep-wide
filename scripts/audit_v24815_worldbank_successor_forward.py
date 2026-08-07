#!/usr/bin/env python3
"""Content-free post-freeze audit for V2.48.15."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from collections import Counter
from collections.abc import Mapping
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24815_worldbank_successor_contract as contract  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import validate_child_receipt  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import validate_receipt as validate_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import validate_transport_health  # noqa: E402
from deepwide_agent.v24804_shared_prefix_budget_ladder import ARMS  # noqa: E402
from deepwide_agent.v24812_batched_search_accounting import validate_envelope  # noqa: E402


def read(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file(): raise RuntimeError("V2.48.15 audit expected ordinary object")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise RuntimeError("V2.48.15 audit expected object")
    return value


def sealed(value: Mapping[str, Any], field: str) -> bool:
    unsigned = dict(value); seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def build(*, now: int | None = None) -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT, read(ROOT / contract.PROTOCOL))
    forward, freeze, summary = read(ROOT / contract.FORWARD_RESULT), read(ROOT / contract.PREDICTION_FREEZE), read(ROOT / contract.RUN_SUMMARY)
    findings = []
    if (forward.get("role") != "v24815_forward_result" or not sealed(forward, "result_payload_sha256") or not sealed(freeze, "freeze_payload_sha256") or not sealed(summary, "summary_payload_sha256") or forward.get("prediction_freeze_sha256") != contract.sha256(ROOT / contract.PREDICTION_FREEZE) or freeze.get("predictions_sha256") != contract.sha256(ROOT / contract.PREDICTIONS) or freeze.get("private_population_gold_or_evaluator_opened_or_hashed") is not False): findings.append("forward_freeze_or_summary_invalid")
    rows = [json.loads(line) for line in (ROOT / contract.PREDICTIONS).read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != contract.SELECTED_COUNT: findings.append("prediction_denominator_drifted")
    totals: Counter[str] = Counter(); terminal: Counter[str] = Counter(); valid = 0
    for row in rows:
        if not isinstance(row, Mapping) or set(row.get("predictions") or {}) != set(ARMS): findings.append("prediction_arm_schema_drifted"); continue
        for arm in ARMS:
            if row.get("prediction_sha256", {}).get(arm) != hashlib.sha256(str(row["predictions"][arm]).encode()).hexdigest(): findings.append("prediction_hash_drifted")
    for position in range(1, contract.SELECTED_COUNT + 1):
        directory = ROOT / contract.TASK_ROOT / f"task_{position:04d}"
        try:
            child = validate_child_receipt(read(directory / "child_terminal_receipt.json")); model = validate_model(read(directory / "model_slot_receipt.json"), expected_cap=contract.MODEL_SLOT_CAP); health = validate_transport_health(read(directory / "transport_health.json"))
            terminal[str(child["exception_type"] or "none")] += 1; totals["terminal_receipts"] += 1; totals["model_slot_acquisitions"] += model["acquisitions"]; totals["model_slot_timeouts"] += model["slot_timeouts"]; totals["hosted_search_attempts"] += health["hosted_search_attempts"]; totals["hard_fetch_helper_calls"] += health["hard_fetch_helper_calls"]; totals["fetch_deadline_rejections"] += health["fetch_deadline_rejections"]
            if child["result_envelope_written"]:
                envelope = validate_envelope(read(directory / "result.json")); accounting = envelope["effect_accounting"]; totals["logical_search_queries"] += accounting["logical_search_queries"]; totals["provider_response_calls"] += accounting["provider_response_calls"]; totals["provider_attempts"] += accounting["provider_attempts"]; totals["fetch_calls"] += accounting["fetch_calls"]; valid += 1
        except (KeyError, OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError): totals["invalid_task_artifacts"] += 1
    checks = {"prediction_denominator_exact": len(rows) == contract.SELECTED_COUNT, "all_terminal_receipts_valid": totals["terminal_receipts"] == contract.SELECTED_COUNT and totals["invalid_task_artifacts"] == 0, "valid_results_reconcile_summary": valid == summary.get("valid_task_results") and contract.SELECTED_COUNT - valid == summary.get("projected_failure_tasks"), "all_results_valid": valid == contract.SELECTED_COUNT, "model_effects_complete": totals["model_slot_acquisitions"] == 2 * contract.SELECTED_COUNT and totals["model_slot_timeouts"] == 0, "logical_search_queries_complete": totals["logical_search_queries"] == 4 * contract.SELECTED_COUNT, "provider_batch_calls_not_forced_equal_logical_queries": totals["provider_response_calls"] >= contract.SELECTED_COUNT and totals["provider_response_calls"] <= totals["logical_search_queries"], "provider_attempts_cover_responses": totals["provider_attempts"] >= totals["provider_response_calls"], "fetch_effects_complete": totals["fetch_calls"] == 10 * contract.SELECTED_COUNT and totals["hard_fetch_helper_calls"] + totals["fetch_deadline_rejections"] == 10 * contract.SELECTED_COUNT}
    value = {"artifact_version": 1, "role": "v24815_worldbank_successor_forward_audit", "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now), "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT), "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE), "predictions_sha256": contract.sha256(ROOT / contract.PREDICTIONS), "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY), "counts": {key: int(value) for key, value in sorted(totals.items())}, "adaptive_decision_counts": summary.get("adaptive_decision_counts"), "terminal_exception_counts": dict(sorted(terminal.items())), "checks": checks, "findings": sorted(name for name, okay in checks.items() if not okay), "private_population_gold_provenance_or_evaluator_opened_or_hashed": False, "network_model_search_fetch_or_evaluator_called_by_audit": False, "protected_watchers": contract.protected_watcher_snapshot(), "authorization": {"postfreeze_external_evaluator_protocol": all(checks.values()), "same_population_retry_resume_or_rerun": False, "evaluator_execution": False, "public_dev64_or_exact220": False}}
    value["audit_valid"] = not value["findings"]; value["audit_payload_sha256"] = contract.payload_sha256(value)
    if value["findings"]: raise RuntimeError(f"V2.48.15 forward audit failed: {value['findings']}")
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build(); publish(ROOT / contract.FORWARD_AUDIT, value); print(json.dumps({"path": str(contract.FORWARD_AUDIT), "audit_valid": value["audit_valid"], "counts": value["counts"]}, sort_keys=True))
