#!/usr/bin/env python3
"""Post-freeze, label-blind forward audit for V2.47.11."""

from __future__ import annotations

import hashlib
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
from deepwide_agent.v24711_sparse_full220_contract import (  # noqa: E402
    ACTIVATION,
    ACTIVATION_AUTHORIZATION,
    CONTROL_PREDICTIONS,
    DOWNLOAD_RECEIPT,
    EXECUTION_START,
    EXPECTED_APPLIED_TASKS,
    EXPECTED_ROUTE_ELIGIBLE,
    EXPECTED_TARGET_VALUES,
    EXPECTED_UNCHANGED_TASKS,
    FORWARD_AUDIT,
    FORWARD_RESULT,
    OUTPUT_ROOT,
    PREAUDIT,
    PREAUDIT_AUTHORIZATION,
    PREDICTION_FREEZE,
    PROTOCOL,
    PROTOCOL_ID,
    RUN_SUMMARY,
    RUNTIME_PREDICTIONS,
    SELECTED_COUNT,
    START_AUTHORIZATION,
    payload_sha256,
    protected_watcher_snapshot,
    read_jsonl,
    read_object,
    sealed,
    sha256,
    validate_control_rows,
    validate_protocol,
    validate_stage,
)
from scripts.control_v24711_sparse_full220 import _active_runner, _lease_inactive  # noqa: E402
from scripts.run_v24711_sparse_full220 import (  # noqa: E402
    validate_download_receipt,
    validate_run_summary,
    validate_runtime_row,
)


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
        ["git", *args],
        cwd=ROOT,
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        timeout=20,
    ).stdout.strip()


def _tracked(path: Path) -> bool:
    return subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(path)],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        check=False,
    ).returncode == 0


def _identity_columns_preserved(
    control_prediction: str, candidate_prediction: str
) -> bool:
    control = _matrix(control_prediction)
    candidate = _matrix(candidate_prediction)
    return bool(
        control is not None
        and candidate is not None
        and len(control) == len(candidate)
        and all(before[:2] == after[:2] for before, after in zip(control, candidate, strict=True))
    )


def build_audit(*, now: int | None = None) -> dict[str, Any]:
    protocol = validate_protocol(ROOT)
    validate_stage(
        ROOT,
        PREAUDIT,
        role="v24711_sparse_full220_preactivation_audit",
        seal_field="audit_payload_sha256",
        authorization=PREAUDIT_AUTHORIZATION,
    )
    validate_stage(
        ROOT,
        ACTIVATION,
        role="v24711_sparse_full220_activation",
        seal_field="activation_payload_sha256",
        authorization=ACTIVATION_AUTHORIZATION,
    )
    validate_stage(
        ROOT,
        EXECUTION_START,
        role="v24711_sparse_full220_execution_start",
        seal_field="execution_start_payload_sha256",
        authorization=START_AUTHORIZATION,
    )
    forward = read_object(ROOT / FORWARD_RESULT)
    freeze = read_object(ROOT / PREDICTION_FREEZE)
    summary = validate_run_summary(read_object(ROOT / RUN_SUMMARY))
    download = validate_download_receipt(read_object(ROOT / DOWNLOAD_RECEIPT))
    rows = read_jsonl(ROOT / RUNTIME_PREDICTIONS)
    control_rows = validate_control_rows(ROOT)
    control = {row["opaque_id"]: row for row in control_rows}
    findings: list[str] = []
    if (
        forward.get("role") != "v24711_sparse_full220_forward_result"
        or forward.get("protocol_id") != PROTOCOL_ID
        or not sealed(forward, "result_payload_sha256")
        or forward.get("terminal_predictions") != SELECTED_COUNT
        or forward.get("prediction_freeze_sha256") != sha256(ROOT / PREDICTION_FREEZE)
        or forward.get("run_summary_sha256") != sha256(ROOT / RUN_SUMMARY)
        or forward.get("download_receipt_sha256") != sha256(ROOT / DOWNLOAD_RECEIPT)
        or forward.get(
            "all_220_predictions_terminal_before_mapping_gold_evaluator_or_score_open"
        )
        is not True
        or forward.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        )
        is not False
        or forward.get("official_evaluator_called") is not False
        or forward.get("resume_retry_skip_or_selective_rerun") is not False
    ):
        findings.append("forward_result_drifted")
    if (
        freeze.get("role") != "v24711_sparse_full220_prediction_freeze"
        or freeze.get("terminal") != SELECTED_COUNT
        or freeze.get("runtime_predictions_sha256") != sha256(ROOT / RUNTIME_PREDICTIONS)
        or freeze.get("run_summary_sha256") != sha256(ROOT / RUN_SUMMARY)
        or freeze.get("download_receipt_sha256") != sha256(ROOT / DOWNLOAD_RECEIPT)
        or freeze.get(
            "all_220_predictions_terminal_before_mapping_gold_evaluator_or_score_open"
        )
        is not True
        or freeze.get(
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_opened_or_hashed"
        )
        is not False
        or freeze.get("official_evaluator_called") is not False
        or not sealed(freeze, "freeze_payload_sha256")
    ):
        findings.append("prediction_freeze_drifted")
    row_valid = len(rows) == SELECTED_COUNT
    try:
        if row_valid:
            for row in rows:
                validate_runtime_row(row)
    except (KeyError, TypeError, ValueError):
        row_valid = False
    if (
        not row_valid
        or [row.get("opaque_id") for row in rows]
        != [row.get("opaque_id") for row in control_rows]
    ):
        findings.append("runtime_prediction_vector_drifted")
    changed = [
        row
        for row in rows
        if row.get("prediction_sha256") != row.get("control_prediction_sha256")
    ]
    unchanged = [row for row in rows if row not in changed]
    if (
        len(unchanged) != EXPECTED_UNCHANGED_TASKS
        or any(
            row.get("prediction") != control.get(row.get("opaque_id"), {}).get("prediction")
            for row in unchanged
        )
    ):
        findings.append("nontrigger_control_reuse_drifted")
    identity_preserved = bool(
        len(changed) == EXPECTED_APPLIED_TASKS
        and _identity_columns_preserved(
            control[changed[0]["opaque_id"]]["prediction"], changed[0]["prediction"]
        )
    )
    if not identity_preserved:
        findings.append("changed_task_identity_columns_drifted")
    if (
        summary.get("route_eligible_tasks") != EXPECTED_ROUTE_ELIGIBLE
        or summary.get("applied_tasks") != EXPECTED_APPLIED_TASKS
        or summary.get("unchanged_prediction_hash_tasks") != EXPECTED_UNCHANGED_TASKS
        or summary.get("changed_prediction_hash_tasks") != EXPECTED_APPLIED_TASKS
        or summary.get("official_target_value_count") != EXPECTED_TARGET_VALUES
        or not 1 <= summary.get("changed_numeric_cell_count", 0) <= EXPECTED_TARGET_VALUES
        or summary.get("adapter_bulk_callback_invocations") != 1
        or summary.get("failure_reason_counts") != {"not_eligible": EXPECTED_UNCHANGED_TASKS}
    ):
        findings.append("mechanism_gate_failed")
    if (
        download.get("successful") != 4
        or download.get("failed") != 0
        or any(item.get("success") is not True for item in download["downloads"])
    ):
        findings.append("bulk_download_gate_failed")
    if (
        _git("status", "--porcelain")
        or _git("rev-parse", "HEAD") != _git("rev-parse", "target/main")
        or any(
            not _tracked(path)
            for path in (
                FORWARD_RESULT,
                RUNTIME_PREDICTIONS,
                RUN_SUMMARY,
                DOWNLOAD_RECEIPT,
                PREDICTION_FREEZE,
            )
        )
    ):
        findings.append("forward_artifacts_not_clean_pushed_and_tracked")
    if protected_watcher_snapshot() != protocol["execution"]["protected_watchers"]:
        findings.append("protected_watcher_identity_drifted")
    if not _lease_inactive():
        findings.append("shared_api_lease_active")
    if _active_runner():
        findings.append("forward_runner_active")
    value = {
        "artifact_version": 1,
        "role": "v24711_sparse_full220_forward_audit",
        "protocol_id": PROTOCOL_ID,
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(ROOT / PROTOCOL),
        "forward_result_sha256": sha256(ROOT / FORWARD_RESULT),
        "prediction_freeze_sha256": sha256(ROOT / PREDICTION_FREEZE),
        "runtime_predictions_sha256": sha256(ROOT / RUNTIME_PREDICTIONS),
        "run_summary_sha256": sha256(ROOT / RUN_SUMMARY),
        "download_receipt_sha256": sha256(ROOT / DOWNLOAD_RECEIPT),
        "observed": {
            "terminal_predictions": len(rows),
            "route_eligible_tasks": summary.get("route_eligible_tasks"),
            "applied_tasks": summary.get("applied_tasks"),
            "unchanged_prediction_hash_tasks": len(unchanged),
            "changed_prediction_hash_tasks": len(changed),
            "official_target_value_count": summary.get("official_target_value_count"),
            "changed_numeric_cell_count": summary.get("changed_numeric_cell_count"),
            "bulk_download_successes": download.get("successful"),
            "country_and_capital_cells_preserved_on_changed_task": identity_preserved,
        },
        "source_policy": {
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
            "control_and_candidate_predictions_opened_postfreeze_for_hash_and_visible_identity_audit": True,
            "official_evaluator_called": False,
            "exploratory_due_to_v24707_incident": True,
        },
        "runtime_state": {
            "protected_watchers_unchanged": protected_watcher_snapshot()
            == protocol["execution"]["protected_watchers"],
            "shared_api_lease_inactive": _lease_inactive(),
            "forward_runner_active": _active_runner(),
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": dict(AUTHORIZATION_GO if not findings else AUTHORIZATION_NO_GO),
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish(path: Path, value: Mapping[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(dict(value), handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    audit = build_audit()
    publish(ROOT / FORWARD_AUDIT, audit)
    print(
        json.dumps(
            {
                "path": str(FORWARD_AUDIT),
                "audit_valid": audit["audit_valid"],
                "findings": audit["findings"],
                "authorization": audit["authorization"],
            },
            sort_keys=True,
        )
    )
