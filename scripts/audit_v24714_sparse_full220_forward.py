#!/usr/bin/env python3
"""Post-freeze audit for V2.47.14 sparse full-220."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24709_sparse_worldbank_adapter import _matrix  # noqa: E402
from deepwide_agent import v24714_sparse_full220_order_join as contract  # noqa: E402
from scripts.control_v24714_sparse_full220 import _active_runner, _lease_inactive  # noqa: E402
from scripts.run_v24711_sparse_full220 import validate_runtime_row  # noqa: E402
from scripts.run_v24714_sparse_full220 import validate_download, validate_summary  # noqa: E402


AUTHORIZATION_GO = {
    "postfreeze_evaluator_protocol_publication": True,
    "evaluator_execution": False,
    "additional_forward_resume_retry_or_rerun": False,
    "leaderboard_or_sota": False,
}
AUTHORIZATION_NO_GO = {
    "postfreeze_evaluator_protocol_publication": False,
    "evaluator_execution": False,
    "additional_forward_resume_retry_or_rerun": False,
    "leaderboard_or_sota": False,
}


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, timeout=20,
    ).stdout.strip()


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)], cwd=ROOT,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, timeout=20, check=False,
    ).returncode == 0


def _identity_preserved(control_prediction: str, candidate_prediction: str) -> bool:
    before = _matrix(control_prediction)
    after = _matrix(candidate_prediction)
    return bool(
        before is not None and after is not None and len(before) == len(after)
        and all(a[:2] == b[:2] for a, b in zip(before, after, strict=True))
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    protocol = contract.validate_protocol(ROOT)
    contract.validate_stage(
        ROOT, contract.PREAUDIT, role="v24714_sparse_full220_preactivation_audit",
        seal_field="audit_payload_sha256", authorization=contract.PREAUDIT_AUTHORIZATION,
    )
    contract.validate_stage(
        ROOT, contract.ACTIVATION, role="v24714_sparse_full220_activation",
        seal_field="activation_payload_sha256", authorization=contract.ACTIVATION_AUTHORIZATION,
    )
    contract.validate_stage(
        ROOT, contract.EXECUTION_START, role="v24714_sparse_full220_execution_start",
        seal_field="execution_start_payload_sha256", authorization=contract.START_AUTHORIZATION,
    )
    forward = contract.read_object(ROOT / contract.FORWARD_RESULT)
    freeze = contract.read_object(ROOT / contract.PREDICTION_FREEZE)
    summary = validate_summary(contract.read_object(ROOT / contract.RUN_SUMMARY))
    download = validate_download(contract.read_object(ROOT / contract.DOWNLOAD_RECEIPT))
    rows = contract.read_jsonl(ROOT / contract.RUNTIME_PREDICTIONS)
    control_rows = contract.validate_control_rows(ROOT)
    control = {row["opaque_id"]: row for row in control_rows}
    findings: list[str] = []
    if (
        forward.get("role") != "v24714_sparse_full220_forward_result"
        or forward.get("protocol_id") != contract.PROTOCOL_ID
        or not contract.sealed(forward, "result_payload_sha256")
        or forward.get("terminal_predictions") != contract.SELECTED_COUNT
        or forward.get("prediction_freeze_sha256") != contract.sha256(ROOT / contract.PREDICTION_FREEZE)
        or forward.get("run_summary_sha256") != contract.sha256(ROOT / contract.RUN_SUMMARY)
        or forward.get("download_receipt_sha256") != contract.sha256(ROOT / contract.DOWNLOAD_RECEIPT)
        or forward.get("all_220_predictions_terminal_before_mapping_gold_evaluator_or_score_open") is not True
        or forward.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_read") is not False
        or forward.get("official_evaluator_called") is not False
        or forward.get("resume_retry_skip_or_selective_rerun") is not False
    ):
        findings.append("forward_result_drifted")
    if (
        freeze.get("role") != "v24714_sparse_full220_prediction_freeze"
        or freeze.get("protocol_id") != contract.PROTOCOL_ID
        or freeze.get("terminal") != contract.SELECTED_COUNT
        or freeze.get("runtime_predictions_sha256") != contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS)
        or freeze.get("run_summary_sha256") != contract.sha256(ROOT / contract.RUN_SUMMARY)
        or freeze.get("download_receipt_sha256") != contract.sha256(ROOT / contract.DOWNLOAD_RECEIPT)
        or freeze.get("all_220_predictions_terminal_before_mapping_gold_evaluator_or_score_open") is not True
        or freeze.get("mapping_gold_category_question_type_split_evaluator_score_or_reward_opened_or_hashed") is not False
        or freeze.get("official_evaluator_called") is not False
        or not contract.sealed(freeze, "freeze_payload_sha256")
    ):
        findings.append("prediction_freeze_drifted")
    row_valid = len(rows) == contract.SELECTED_COUNT
    try:
        if row_valid:
            for row in rows:
                validate_runtime_row(row)
    except (KeyError, TypeError, ValueError):
        row_valid = False
    if not row_valid or [row.get("opaque_id") for row in rows] != [row["opaque_id"] for row in control_rows]:
        findings.append("runtime_prediction_vector_drifted")
    changed = [row for row in rows if row.get("prediction_sha256") != row.get("control_prediction_sha256")]
    unchanged = [row for row in rows if row not in changed]
    if (
        len(unchanged) != contract.EXPECTED_UNCHANGED_TASKS
        or any(row.get("prediction") != control.get(row.get("opaque_id"), {}).get("prediction") for row in unchanged)
    ):
        findings.append("nontrigger_control_reuse_drifted")
    identity = bool(
        len(changed) == contract.EXPECTED_APPLIED_TASKS
        and _identity_preserved(control[changed[0]["opaque_id"]]["prediction"], changed[0]["prediction"])
    )
    if not identity:
        findings.append("changed_task_identity_columns_drifted")
    if (
        summary.get("route_eligible_tasks") != contract.EXPECTED_ROUTE_ELIGIBLE
        or summary.get("applied_tasks") != contract.EXPECTED_APPLIED_TASKS
        or summary.get("unchanged_prediction_hash_tasks") != contract.EXPECTED_UNCHANGED_TASKS
        or summary.get("changed_prediction_hash_tasks") != contract.EXPECTED_APPLIED_TASKS
        or summary.get("official_target_value_count") != contract.EXPECTED_TARGET_VALUES
        or not 1 <= summary.get("changed_numeric_cell_count", 0) <= contract.EXPECTED_TARGET_VALUES
        or summary.get("adapter_bulk_callback_invocations") != 1
        or summary.get("failure_reason_counts") != {"not_eligible": contract.EXPECTED_UNCHANGED_TASKS}
    ):
        findings.append("mechanism_gate_failed")
    if download.get("successful") != 4 or download.get("failed") != 0 or any(item.get("success") is not True for item in download["downloads"]):
        findings.append("bulk_download_gate_failed")
    if (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
        or any(not _tracked(path) for path in (
            contract.FORWARD_RESULT, contract.RUNTIME_PREDICTIONS,
            contract.RUN_SUMMARY, contract.DOWNLOAD_RECEIPT, contract.PREDICTION_FREEZE,
        ))
    ):
        findings.append("forward_artifacts_not_clean_pushed_and_tracked")
    if contract.protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    if not _lease_inactive():
        findings.append("shared_api_lease_active")
    if _active_runner():
        findings.append("forward_runner_active")
    value = {
        "artifact_version": 1,
        "role": "v24714_sparse_full220_forward_audit",
        "protocol_id": contract.PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": contract.sha256(ROOT / contract.PROTOCOL),
        "forward_result_sha256": contract.sha256(ROOT / contract.FORWARD_RESULT),
        "prediction_freeze_sha256": contract.sha256(ROOT / contract.PREDICTION_FREEZE),
        "runtime_predictions_sha256": contract.sha256(ROOT / contract.RUNTIME_PREDICTIONS),
        "run_summary_sha256": contract.sha256(ROOT / contract.RUN_SUMMARY),
        "download_receipt_sha256": contract.sha256(ROOT / contract.DOWNLOAD_RECEIPT),
        "observed": {
            "terminal_predictions": len(rows),
            "route_eligible_tasks": summary.get("route_eligible_tasks"),
            "applied_tasks": summary.get("applied_tasks"),
            "unchanged_prediction_hash_tasks": len(unchanged),
            "changed_prediction_hash_tasks": len(changed),
            "official_target_value_count": summary.get("official_target_value_count"),
            "changed_numeric_cell_count": summary.get("changed_numeric_cell_count"),
            "bulk_download_successes": download.get("successful"),
            "country_and_capital_cells_preserved_on_changed_task": identity,
            "canonical_output_order": "frozen_control_prediction_order",
        },
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "control_and_candidate_predictions_opened_postfreeze_for_hash_and_visible_identity_audit": True,
            "official_evaluator_called": False,
            "exploratory_due_to_v24707_incident": True,
        },
        "runtime_state": {
            "protected_watchers_unchanged": contract.protected_watcher_snapshot() == protocol["execution"]["protected_watchers"],
            "shared_api_lease_inactive": _lease_inactive(),
            "forward_runner_active": _active_runner(),
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": dict(AUTHORIZATION_GO if not findings else AUTHORIZATION_NO_GO),
    }
    value["audit_payload_sha256"] = contract.payload_sha256(value)
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_audit()
    publish(ROOT / contract.FORWARD_AUDIT, value)
    print(json.dumps({"path": str(contract.FORWARD_AUDIT), "audit_valid": value["audit_valid"], "findings": value["findings"], "authorization": value["authorization"]}, sort_keys=True))
