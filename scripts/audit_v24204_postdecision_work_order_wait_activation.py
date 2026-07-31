#!/usr/bin/env python3
"""Audit V2.42.04 at its preterminal post-decision wait boundary."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from scripts.activate_v24204_postdecision_work_order import (  # noqa: E402
    validate_activation,
)
from scripts.preregister_v24204_postdecision_work_order import (  # noqa: E402
    ACTIVATION,
    OUTPUT,
    PARENT_DECISION,
    SELECTED_WORK_ORDER,
    STATE,
    WAIT_AUDIT,
    protected_processes,
    publish_new,
    read_object,
    sha256,
    validate_protocol,
)


def build_audit(
    root: Path = ROOT,
    *,
    created_at_unix: int | None = None,
    proc_root: Path = Path("/proc"),
) -> dict[str, Any]:
    root = root.resolve()
    protocol = validate_protocol(root, OUTPUT)
    activation = validate_activation(root, ACTIVATION, proc_root=proc_root)
    state_path = root / STATE
    state = read_object(state_path)
    unsigned = {key: item for key, item in state.items() if key != "state_payload_sha256"}
    frozen = protocol["value"]["safe_wait_boundary"]["protected_processes"]
    live = protected_processes(proc_root)
    false_fields = (
        "parent_content_free_decision_receipt_opened",
        "parent_numeric_metrics_reports_predictions_or_aggregates_read",
        "selected_work_order_published",
        "identity_handoff_selected",
        "nonempty_blocked_work_order_selected",
        "candidate_code_built_merged_or_materialized",
        "component_implementation_publisher_invoked",
        "package_gate_evaluated_or_launched",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read",
        "credential_value_read_persisted_hashed_or_emitted",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
        "terminal",
    )
    if (
        state.get("role") != "v24204_postdecision_work_order_watcher_state"
        or state.get("protocol", {}).get("sha256") != protocol["sha256"]
        or state.get("execution_activation", {}).get("sha256") != activation["sha256"]
        or state.get("status") != "waiting_for_v24200_terminal_decision"
        or state.get("reason") != "parent_quality_chain_preterminal"
        or state.get("parent_safe_state_envelope_opened") is not True
        or any(state.get(field) is not False for field in false_fields)
        or state.get("state_payload_sha256") != payload_sha256(unsigned)
        or (root / PARENT_DECISION).exists()
        or (root / PARENT_DECISION).is_symlink()
        or (root / SELECTED_WORK_ORDER).exists()
        or (root / SELECTED_WORK_ORDER).is_symlink()
        or live != frozen
    ):
        raise RuntimeError("V2.42.04 wait boundary is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24204_postdecision_work_order_wait_activation_audit",
        "created_at_unix": int(time.time()) if created_at_unix is None else int(created_at_unix),
        "protocol": {
            "path": str(OUTPUT),
            "sha256": protocol["sha256"],
            "decision_contract_sha256": protocol["value"]["decision_contract_sha256"],
            "control_manifest_sha256": protocol["value"]["control_surface"][
                "manifest_sha256"
            ],
        },
        "execution_activation": {
            "path": str(ACTIVATION),
            "sha256": activation["sha256"],
            "watcher_pid": activation["value"]["watcher"]["pid"],
            "watcher_start_ticks": activation["value"]["watcher"]["start_ticks"],
        },
        "initial_wait_state": {
            "path": str(STATE),
            "sha256": sha256(state_path),
            "status": state["status"],
        },
        "boundary": {
            "parent_safe_state_envelope_opened": True,
            "parent_quality_chain_terminal": False,
            "parent_content_free_decision_receipt_absent_and_unopened": True,
            "selected_work_order_absent": True,
            "candidate_code_built_merged_or_materialized": False,
            "component_implementation_publisher_invoked": False,
            "package_gate_evaluated_or_launched": False,
            "all_protocol_protected_process_identities_preserved": True,
            "protected_processes": live,
            "shared_api_lease_acquired": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
            "benchmark_forward_or_full220_launch_allowed": False,
        },
        "authorization": {
            "postdecision_work_order_watcher_active": True,
            "future_decision_read_requires_parent_terminal_state": True,
            "identity_handoff_or_blocked_work_order_only": True,
            "future_nonempty_publications_require_separate_authorized_publishers": True,
            "future_package_gate_requires_complete_selected_package": True,
            "future_all220_requires_package_gate_go_or_identity_handoff_and_separate_executor": True,
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
        raise RuntimeError("V2.42.04 wait-audit path drifted")
    value = build_audit()
    publish_new(target, value)
    print({"path": str(target), "sha256": sha256(target)})


if __name__ == "__main__":
    main()
