#!/usr/bin/env python3
"""Closure and label-blind audit for the V2.43.15 forward NO-GO."""

from __future__ import annotations

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

from deepwide_agent.v24315_forward_contract import (  # noqa: E402
    FORWARD_RESULT,
    OUTPUT_ROOT,
    protected_watcher_snapshot,
    sha256,
    payload_sha256,
)
from scripts.audit_v24187_phase_liveness import process_snapshot  # noqa: E402
from scripts.audit_v24195_lease_owner_compatibility import (  # noqa: E402
    lease_observation,
)
from scripts.preregister_v24259_deterministic_normalizer_smoke import (  # noqa: E402
    _matching,
)
from scripts.preregister_v24315_exact220 import (  # noqa: E402
    EVALUATOR_ROOT,
    FINAL_RESULT,
    POSTAUDIT,
    publish_new,
)
from scripts.publish_v24315_exact220_forward_nogo import (  # noqa: E402
    AUDIT,
    RESULT,
    validate_result,
)
from deepwide_agent.v24315_forward_contract import (  # noqa: E402
    CHILD_MARKER,
    RUNNER_MARKER,
    read_object,
)


def build_audit(root: Path = ROOT, *, now: int | None = None) -> dict[str, Any]:
    root = root.resolve()
    result = read_object(root / RESULT)
    validate_result(root, result)
    rows = process_snapshot()
    runner_present = bool(_matching(rows, RUNNER_MARKER))
    child_present = bool(_matching(rows, CHILD_MARKER))
    lease = lease_observation(root, Path("/proc"))
    watchers = protected_watcher_snapshot()
    evaluator_paths = (root / EVALUATOR_ROOT, root / FINAL_RESULT, root / POSTAUDIT)
    evaluator_surface_absent = all(
        not path.exists() and not path.is_symlink() for path in evaluator_paths
    )
    success_forward_absent = not (root / FORWARD_RESULT).exists() and not (
        root / FORWARD_RESULT
    ).is_symlink()
    findings: list[str] = []
    if runner_present:
        findings.append("forward_runner_present_after_terminal_nogo")
    if child_present:
        findings.append("forward_child_present_after_terminal_nogo")
    if lease.get("active") is not False:
        findings.append("shared_api_lease_active_after_terminal_nogo")
    if not evaluator_surface_absent:
        findings.append("evaluator_side_surface_exists_after_forward_nogo")
    if not success_forward_absent:
        findings.append("success_forward_result_exists_after_forward_nogo")
    if result.get("official_evaluator_called") is not False:
        findings.append("evaluator_called_by_nogo_publication")
    if result.get("mapping_gold_category_question_type_split_evaluator_score_read") is not False:
        findings.append("privileged_evaluator_side_data_read_by_nogo_publication")
    value = {
        "artifact_version": 1,
        "role": "v24315_exact220_forward_nogo_audit",
        "created_at_unix": int(time.time()) if now is None else int(now),
        "forward_nogo": {"path": str(RESULT), "sha256": sha256(root / RESULT)},
        "closure": {
            "runner_process_present": runner_present,
            "child_process_present": child_present,
            "shared_api_lease_active": lease.get("active") is True,
            "success_forward_result_absent": success_forward_absent,
            "evaluator_side_surface_absent": evaluator_surface_absent,
            "protected_watchers": watchers,
            "active_run_killed_or_quarantined": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
        },
        "source_policy": {
            "all_220_predictions_frozen_before_publication": True,
            "question_opaque_id_prediction_url_page_or_credential_emitted": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "same_run_evaluator_feedback_used_for_forward_or_selection": False,
        },
        "findings": findings,
        "audit_valid": not findings,
        "authorization": {
            "v24316_runner_integration_design": not findings,
            "same_run_evaluator": False,
            "same_run_retry_resume_or_selective_rerun": False,
            "additional_rollout": False,
            "leaderboard_submission": False,
            "sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def _publish(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


if __name__ == "__main__":
    value = build_audit()
    _publish(ROOT / AUDIT, value)
    print(json.dumps({"path": str(AUDIT), "audit_valid": value["audit_valid"]}, sort_keys=True))
