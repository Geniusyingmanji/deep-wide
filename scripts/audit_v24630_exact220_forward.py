#!/usr/bin/env python3
"""Post-forward, pre-evaluator audit for the frozen V2.46.30 exact-220."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24630_exact220_contract import (  # noqa: E402
    FORWARD_CONTRACT, FORWARD_RESULT, OUTPUT_ROOT, PREDICTION_FREEZE,
    PROTOCOL_ID, RUNTIME_PREDICTIONS, RUN_SUMMARY, SELECTED_COUNT,
    payload_sha256, protected_watcher_snapshot, read_object, selected_ids,
    sha256, validate_forward_contract,
)
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24630_exact220 import publish_new  # noqa: E402


OUTPUT = Path("results/v24630_exact220_forward_audit_v1_20260806.json")


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _active(marker: str) -> bool:
    rows = subprocess.run(
        ["ps", "-eo", "cmd="], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, check=False,
    ).stdout.splitlines()
    return any(marker in row for row in rows if "ps -eo" not in row)


def build_report(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    contract = validate_forward_contract(root)
    forward = read_object(root / FORWARD_RESULT)
    summary = read_object(root / RUN_SUMMARY)
    freeze = read_object(root / PREDICTION_FREEZE)
    rows = [
        json.loads(line)
        for line in (root / RUNTIME_PREDICTIONS).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    lease = lease_observation(root, Path("/proc"))
    checks = {
        "forward_sealed": _sealed(forward, "result_payload_sha256"),
        "summary_sealed": _sealed(summary, "summary_payload_sha256"),
        "freeze_sealed": _sealed(freeze, "freeze_payload_sha256"),
        "runtime_rows_exact220": len(rows) == SELECTED_COUNT,
        "runtime_id_order_exact": [row.get("opaque_id") for row in rows] == selected_ids(contract),
        "runtime_predictions_hash_bound": freeze.get("runtime_predictions_sha256") == sha256(root / RUNTIME_PREDICTIONS),
        "run_summary_hash_bound": freeze.get("run_summary_sha256") == sha256(root / RUN_SUMMARY),
        "terminal_fixed_denominator": forward.get("terminal_predictions") == SELECTED_COUNT and freeze.get("terminal") == SELECTED_COUNT,
        "mapping_evaluator_closed_during_forward": freeze.get("mapping_gold_or_evaluator_opened_or_hashed") is False and forward.get("official_evaluator_called") is False,
        "shared_lease_released": lease.get("active") is False,
        "runner_absent": not _active("scripts/run_v24630_exact220.py"),
        "child_absent": not _active("scripts/run_v24630_exact220_task.py"),
        "protected_watchers_unchanged": protected_watcher_snapshot() == contract["execution"]["protected_watchers"],
    }
    findings = sorted(name for name, passed in checks.items() if not passed)
    value = {
        "artifact_version": 1,
        "role": "v24630_exact220_forward_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_contract_sha256": sha256(root / FORWARD_CONTRACT),
        "forward_result_sha256": sha256(root / FORWARD_RESULT),
        "prediction_freeze_sha256": sha256(root / PREDICTION_FREEZE),
        "runtime_predictions_sha256": sha256(root / RUNTIME_PREDICTIONS),
        "run_summary_sha256": sha256(root / RUN_SUMMARY),
        "checks": checks,
        "selected": SELECTED_COUNT,
        "terminal_predictions": forward.get("terminal_predictions"),
        "model_generated_tables": forward.get("model_generated_tables"),
        "fallback_tables": forward.get("fallback_tables"),
        "forward_wall_seconds": forward.get("forward_wall_seconds"),
        "system_total_tokens": forward.get("system_total_tokens"),
        "parent_exit_taxonomy": summary.get("parent_exit_taxonomy"),
        "backfill_totals": summary.get("backfill_totals"),
        "transport_totals": summary.get("transport_totals"),
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "postfreeze_exact220_evaluator": not findings,
            "forward_resume_retry_skip_or_rerun": False,
            "selective_evaluation_or_revaluation": False,
            "leaderboard_or_sota": False,
        },
        "mapping_gold_category_question_type_split_evaluator_score_read_by_audit": False,
        "network_model_search_fetch_or_evaluator_called_by_audit": False,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


if __name__ == "__main__":
    value = build_report()
    publish_new(ROOT / OUTPUT, value)
    print(json.dumps({"path": str(OUTPUT), "audit_valid": value["audit_valid"], "findings": value["findings"]}, sort_keys=True))
