#!/usr/bin/env python3
"""Audit V2.42.17 at its parent-preterminal wait boundary."""

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

from deepwide_agent.v24217_capacity_successor import payload_sha256  # noqa: E402
from scripts.activate_v24217_capacity_successor import validate_activation  # noqa: E402
from scripts.preregister_v24210_search_component import (  # noqa: E402
    publish_new,
    read_object,
    sha256,
)
from scripts.preregister_v24217_capacity_successor import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    FREEZE,
    OUTPUT,
    REPORT,
    STATE,
    V24194_EXECUTION_ACTIVATION,
    V24194_FREEZE,
    V24194_REPORT,
    V24196_FREEZE,
    V24196_REPORT,
    WAIT_AUDIT,
    validate_protocol,
)


def _present(root: Path, path: Path) -> bool:
    target = root / path
    return target.exists() or target.is_symlink()


def build_audit(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    activation = validate_activation(root, ACTIVATION, proc_root=proc_root)
    state = read_object(root / STATE)
    unsigned = dict(state)
    seal = unsigned.pop("state_payload_sha256", None)
    false_fields = (
        "parent_terminal_go_validated",
        "legacy_capacity_boundary_validated",
        "shared_api_lease_acquired",
        "lease_compatibility_valid",
        "execution_start_published",
        "neutral_capacity_model_api_called",
        "capacity_report_created",
        "capacity_freeze_created",
        "benchmark_question_prediction_mapping_gold_category_evaluator_score_read",
        "search_fetch_or_evaluator_api_called",
        "credential_value_read_persisted_hashed_or_emitted",
        "response_text_or_response_id_persisted",
        "legacy_watcher_signaled_restarted_modified_or_terminated",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
        "terminal",
    )
    future = (
        EXECUTION_START,
        REPORT,
        FREEZE,
        V24194_EXECUTION_ACTIVATION,
        V24194_REPORT,
        V24194_FREEZE,
        V24196_REPORT,
        V24196_FREEZE,
    )
    if (
        state.get("role") != "v24217_capacity_successor_watcher_state"
        or state.get("protocol", {}).get("sha256") != protocol["sha256"]
        or state.get("execution_activation", {}).get("sha256")
        != activation["sha256"]
        or state.get("status") != "waiting_for_v24216_package_gate_terminal"
        or state.get("reason") != "parent_preterminal"
        or state.get("parent_safe_state_envelope_opened") is not True
        or state.get("parent_state", {}).get("terminal") is not False
        or any(state.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
        or any(_present(root, path) for path in future)
    ):
        raise RuntimeError("V2.42.17 wait boundary is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24217_capacity_successor_wait_audit",
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "protocol": {
            "path": str(OUTPUT),
            "sha256": protocol["sha256"],
            "decision_contract_sha256": protocol["value"]["decision_contract_sha256"],
            "control_manifest_sha256": protocol["value"]["control_surface"]["manifest_sha256"],
        },
        "execution_activation": {
            "path": str(ACTIVATION),
            "sha256": activation["sha256"],
            "watcher_pid": activation["value"]["watcher"]["pid"],
            "watcher_start_ticks": activation["value"]["watcher"]["start_ticks"],
        },
        "initial_wait_state": {
            "path": str(STATE),
            "sha256": sha256(root / STATE),
            "status": state["status"],
        },
        "boundary": {
            "parent_safe_state_envelope_opened": True,
            "parent_terminal": False,
            "legacy_watchers_remain_running_and_unmodified": True,
            "legacy_execution_activation_reports_and_freezes_absent": True,
            "execution_start_report_and_freeze_absent": True,
            "shared_api_lease_acquired": False,
            "neutral_capacity_model_api_called": False,
            "benchmark_question_prediction_mapping_gold_category_evaluator_score_read": False,
            "search_fetch_or_evaluator_api_called": False,
            "benchmark_forward_or_full220_launch_allowed": False,
        },
        "authorization": {
            "watcher_active": True,
            "future_capacity_requires_parent_package_gate_go": True,
            "future_capacity_requires_two_quiet_observations_and_one_shared_lease": True,
            "future_execution_start_precedes_client_and_api": True,
            "future_incomplete_attempt_is_terminal_no_retry": True,
            "future_full220_requires_separate_single_owner_activation": True,
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
        raise RuntimeError("V2.42.17 wait-audit output drifted")
    value = build_audit()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
