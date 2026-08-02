#!/usr/bin/env python3
"""Seal the invalid V2.42.66 partial run without opening task content."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import lease_observation  # noqa: E402
from scripts.preregister_v24259_deterministic_normalizer_smoke import _matching  # noqa: E402
from scripts.preregister_v24266_exact220 import (  # noqa: E402
    ACTIVATION,
    CHILD_MARKER,
    OUTPUT,
    RUNNER_MARKER,
    validate_protocol,
)
from scripts.run_v24257_score_first_smoke import payload_sha256, sha256  # noqa: E402


QUARANTINE_RESULTS = Path(
    "results/DO_NOT_USE_invalid_v24266_exact220_fallback_header_20260802"
)
QUARANTINE_OUTPUTS = Path(
    "outputs/DO_NOT_USE_invalid_v24266_exact220_fallback_header_20260802"
)
EXECUTION_START = QUARANTINE_RESULTS / "v24266_exact220_execution_start_v1_20260802.json"
PARTIAL_ROOT = QUARANTINE_OUTPUTS / "v24266_exact220_v1_20260802"
PARTIAL_PROGRESS = PARTIAL_ROOT / "safe_forward_progress.json"
OUTPUT = QUARANTINE_RESULTS / "invalid_run_audit.json"


def _ordinary(path: Path) -> Path:
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(ROOT):
        raise RuntimeError(f"V2.42.66 invalid audit expected ordinary file: {path}")
    return path


def _count(root: Path, name: str) -> int:
    # Bound traversal to the exact quarantined task root.
    tasks = root / "tasks"
    if tasks.is_symlink() or not tasks.is_dir():
        raise RuntimeError("V2.42.66 quarantined task root is invalid")
    return sum(path.is_file() and not path.is_symlink() for path in tasks.glob(f"task_*/{name}"))


def build_audit(root: Path = ROOT, *, now: int | None = None) -> dict:
    root = root.resolve()
    protocol = validate_protocol(root, Path("results/v24266_exact220_preregistration_v1_20260802.json"))
    progress = json.loads(_ordinary(root / PARTIAL_PROGRESS).read_text(encoding="utf-8"))
    execution = json.loads(_ordinary(root / EXECUTION_START).read_text(encoding="utf-8"))
    rows = process_snapshot()
    lease = lease_observation(root, Path("/proc"))
    runner_present = bool(_matching(rows, RUNNER_MARKER))
    child_present = bool(_matching(rows, f"outputs/v24266_exact220_v1_20260802/tasks/"))
    if (
        progress.get("role") != "v24266_exact220_safe_forward_progress"
        or progress.get("completed_predictions") != 65
        or progress.get("unfinished_predictions") != 155
        or progress.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False
        or execution.get("role") != "v24266_exact220_execution_start"
        or execution.get("api_called_before_execution_start") is not False
    ):
        raise RuntimeError("V2.42.66 invalid-run evidence drifted")
    value = {
        "artifact_version": 1,
        "role": "v24266_exact220_invalid_run_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "protocol_sha256": sha256(root / Path("results/v24266_exact220_preregistration_v1_20260802.json")),
        "activation_sha256": sha256(root / ACTIVATION),
        "invalid_reason": "parent fallback construction rejected an unrepresentable visible pipe header after task 66 child exited without result",
        "exception_type": "ValueError",
        "exception_message": "score-first prediction is not canonical Markdown",
        "mechanism": {
            "visible_column_count": 1,
            "visible_column_contains_pipe": True,
            "fallback_validator_self_inconsistent": True,
            "label_or_evaluator_metadata_involved": False,
        },
        "partial_execution": {
            "safe_completed_predictions_before_parent_exception": 65,
            "safe_unfinished_predictions": 155,
            "task_directories_created_before_shutdown": _count(root / PARTIAL_ROOT, "visible_task.json"),
            "child_results_present_before_shutdown": _count(root / PARTIAL_ROOT, "result.json"),
            "child_receipts_present_before_shutdown": _count(root / PARTIAL_ROOT, "model_slot_receipt.json"),
            "forward_result_created": False,
            "prediction_freeze_created": False,
            "evaluator_opened_or_called": False,
            "result_or_score_released": False,
        },
        "quarantine": {
            "results_path": str(QUARANTINE_RESULTS),
            "outputs_path": str(QUARANTINE_OUTPUTS),
            "partial_predictions_or_scores_valid_for_reporting": False,
            "partial_outputs_may_feed_successor": False,
        },
        "execution_closure": {
            "v24266_runner_present": runner_present,
            "v24266_child_present": child_present,
            "shared_api_lease_active": lease.get("active") is True,
            "v24266_runner_and_children_explicitly_stopped_after_invalidity_confirmed": True,
            "other_benchmark_or_watcher_signaled_restarted_or_stopped": False,
        },
        "source_policy": {
            "runtime_boundary": ["opaque_id", "question"],
            "mapping_gold_category_question_type_split_evaluator_score_read_by_forward": False,
            "same_run_evaluator_feedback_used": False,
            "credential_value_persisted_hashed_or_emitted": False,
        },
        "authorization": {
            "append_only_fresh_exact220_successor_design": True,
            "resume_rerun_skip_or_selective_retry_v24266": False,
            "additional_rollout_avg4_leaderboard_or_sota_claim": False,
        },
        "audit_valid": not runner_present and not child_present and lease.get("active") is False,
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def publish(path: Path, value: dict) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    publish(ROOT / OUTPUT, build_audit())
    print(json.dumps({"path": str(OUTPUT), "sha256": sha256(ROOT / OUTPUT)}))
