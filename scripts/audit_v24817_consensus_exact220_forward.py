#!/usr/bin/env python3
"""Audit the frozen V2.48.17 consensus predictions before evaluation."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24817_consensus_exact220_contract as contract  # noqa: E402


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise RuntimeError("V2.48.17 expected object")
    return value


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value); seal = unsigned.pop(field, None)
    return seal == contract.payload_sha256(unsigned)


def build(*, now: int | None = None) -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT, _read(ROOT / contract.PROTOCOL))
    forward = _read(ROOT / contract.FORWARD_RESULT); freeze = _read(ROOT / contract.PREDICTION_FREEZE); summary = _read(ROOT / contract.RUN_SUMMARY); rows = _jsonl(ROOT / contract.RUNTIME_PREDICTIONS); tasks = contract.task_vector(ROOT)
    checks = {
        "forward_sealed": forward.get("role") == "v24817_consensus_exact220_forward_result" and _sealed(forward, "result_payload_sha256"),
        "freeze_sealed": freeze.get("role") == "v24817_consensus_exact220_prediction_freeze" and _sealed(freeze, "freeze_payload_sha256"),
        "summary_sealed": summary.get("role") == "v24817_consensus_exact220_run_summary" and _sealed(summary, "summary_payload_sha256"),
        "exact_220_rows": len(rows) == 220 and [row.get("opaque_id") for row in rows] == [task["opaque_id"] for task in tasks],
        "all_rows_terminal_label_blind": all(row.get("status") == "completed" and row.get("label_blind") is True and row.get("mapping_gold_category_question_type_split_evaluator_score_read") is False and isinstance(row.get("prediction"), str) and row.get("prediction_sha256") == hashlib.sha256(row["prediction"].encode()).hexdigest() for row in rows),
        "runtime_hash_bound": freeze.get("runtime_predictions_sha256") == contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS) and forward.get("runtime_predictions_sha256") == contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS),
        "no_incremental_effects": forward.get("incremental_model_search_or_fetch_effects") == 0 and summary.get("incremental_model_requests") == summary.get("incremental_search_calls") == summary.get("incremental_fetch_calls") == 0,
        "source_evaluator_closed": forward.get("source_evaluator_result_or_score_file_opened_or_hashed") is False and freeze.get("source_evaluator_result_or_score_file_opened_or_hashed") is False and summary.get("source_evaluator_result_or_score_file_opened_or_hashed") is False,
        "mapping_and_evaluator_closed": forward.get("all_220_predictions_terminal_before_mapping_or_evaluator_open") is True and freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is False,
        "protected_watchers_stable": contract.protected_watcher_snapshot() == protocol["protected_watchers"],
    }
    value = {"artifact_version": 1, "role": "v24817_consensus_exact220_forward_audit", "protocol_id": contract.PROTOCOL_ID, "created_at_unix": int(time.time()) if now is None else int(now), "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL), "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT), "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE), "runtime_predictions_sha256": contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS), "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY), "generation_counts": summary.get("generation_counts"), "consensus_totals": summary.get("consensus_totals"), "checks": checks, "findings": sorted(name for name, okay in checks.items() if not okay), "audit_valid": all(checks.values()), "mapping_gold_source_evaluator_result_or_score_opened_or_hashed": False, "network_model_search_fetch_or_evaluator_called_by_audit": False, "authorization": {"postfreeze_exact220_evaluator_protocol": all(checks.values()), "selective_evaluation_or_revaluation": False, "leaderboard_or_sota_claim": False}}
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    if value["findings"]: raise RuntimeError(f"V2.48.17 forward audit failed: {value['findings']}")
    return value


def publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink(): raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True); handle.write("\n"); handle.flush(); os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build(); publish(ROOT / contract.FORWARD_AUDIT, value); print(json.dumps({"path": str(contract.FORWARD_AUDIT), "audit_valid": value["audit_valid"], "generation_counts": value["generation_counts"]}, sort_keys=True))
