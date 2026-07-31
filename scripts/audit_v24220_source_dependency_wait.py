#!/usr/bin/env python3
"""Seal the V2.42.20 preterminal wait boundary."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24220_source_dependency import payload_sha256  # noqa: E402
from scripts.activate_v24220_source_dependency import validate_activation  # noqa: E402
from scripts.preregister_v24220_source_dependency import (  # noqa: E402
    ACTIVATION,
    DETAIL,
    PROTOCOL,
    REPORT,
    STATE,
    WAIT_AUDIT,
    _publish_new,
    validate_protocol,
)
from scripts.run_v24220_source_dependency import file_sha256  # noqa: E402


def _present(root: Path, relative: Path) -> bool:
    target = root / relative
    return target.exists() or target.is_symlink()


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    protocol = validate_protocol(root, PROTOCOL)
    activation = validate_activation(root, ACTIVATION, protocol_path=PROTOCOL)
    path = root / STATE
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.20 wait state is not ordinary")
    state = json.loads(path.read_text(encoding="utf-8"))
    unsigned = dict(state)
    seal = unsigned.pop("state_payload_sha256", None)
    false_fields = (
        "parent_terminal_report_validated",
        "task_evidence_opened",
        "audit_started",
        "report_created",
        "question_query_prediction_mapping_gold_category_question_type_split_evaluator_score_read",
        "network_model_search_fetch_evaluator_or_api_called",
        "shared_api_lease_acquired",
        "forward_result_evaluator_or_watcher_modified",
        "official_score_or_prediction_recomputed",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
    )
    if (
        state.get("role") != "v24220_source_dependency_watcher_state"
        or state.get("protocol", {}).get("sha256") != protocol["sha256"]
        or state.get("execution_activation", {}).get("sha256") != activation["sha256"]
        or state.get("status") != "waiting_for_v24219_contamination_terminal"
        or state.get("reason") != "parent_preterminal"
        or state.get("parent_safe_state_envelope_opened") is not True
        or state.get("parent_state", {}).get("terminal") is not False
        or state.get("terminal") is not False
        or any(state.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
        or _present(root, DETAIL)
        or _present(root, REPORT)
    ):
        raise RuntimeError("V2.42.20 wait boundary is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24220_source_dependency_wait_audit",
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "protocol": {"path": str(PROTOCOL), "sha256": protocol["sha256"]},
        "activation": {"path": str(ACTIVATION), "sha256": activation["sha256"]},
        "initial_wait_state": {
            "path": str(STATE),
            "sha256": file_sha256(path),
            "status": state["status"],
        },
        "boundary": {
            "parent_safe_state_envelope_opened": True,
            "parent_terminal": False,
            "task_evidence_opened": False,
            "detail_or_report_created": False,
            "question_query_prediction_mapping_gold_category_question_type_split_evaluator_score_read": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "shared_api_lease_acquired": False,
            "benchmark_forward_or_full220_launch_allowed": False,
        },
        "authorization": {
            "watcher_active": True,
            "future_audit_requires_sealed_v24219_report": True,
            "future_audit_is_offline_post_terminal_and_create_exclusive": True,
            "official_primary_denominator_remains_220": True,
            "leaderboard_submission_or_sota_claim": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(WAIT_AUDIT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / WAIT_AUDIT).resolve(strict=False):
        raise RuntimeError("V2.42.20 wait-audit output drifted")
    value = build_audit()
    _publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": file_sha256(target)}))


if __name__ == "__main__":
    main()
