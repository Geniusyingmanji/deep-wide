#!/usr/bin/env python3
"""Audit V2.42.07 at its preterminal Markdown-parent wait boundary."""

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
from scripts.activate_v24207_scope_alias_component import (  # noqa: E402
    validate_activation,
)
from scripts.preregister_v24207_scope_alias_component import (  # noqa: E402
    ACTIVATION,
    OUTPUT,
    PUBLICATION,
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
        "parent_selected_work_order_opened",
        "parent_markdown_publication_opened",
        "parent_numeric_metrics_reports_predictions_or_aggregates_read",
        "component_publication_created",
        "branch_scope_component_published",
        "historical_p12_binding_selected",
        "mainline_zero_byte_namespace_alias_selected",
        "historical_scope_patch_reapplied",
        "candidate_bytes_modified_or_materialized",
        "search_yield_or_entropy_implemented",
        "joint_package_built_or_materialized",
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
        state.get("role") != "v24207_selected_scope_alias_component_watcher_state"
        or state.get("protocol", {}).get("sha256") != protocol["sha256"]
        or state.get("execution_activation", {}).get("sha256") != activation["sha256"]
        or state.get("status") != "waiting_for_v24206_terminal_markdown_publication"
        or state.get("reason") != "parent_markdown_component_preterminal"
        or state.get("parent_safe_state_envelope_opened") is not True
        or any(state.get(field) is not False for field in false_fields)
        or state.get("state_payload_sha256") != payload_sha256(unsigned)
        or (root / PUBLICATION).exists()
        or (root / PUBLICATION).is_symlink()
        or live != frozen
    ):
        raise RuntimeError("V2.42.07 wait boundary is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24207_selected_scope_alias_component_wait_activation_audit",
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
            "sha256": sha256(state_path),
            "status": state["status"],
        },
        "boundary": {
            "parent_safe_state_envelope_opened": True,
            "parent_markdown_component_terminal": False,
            "parent_selected_work_order_and_markdown_unopened": True,
            "component_publication_absent": True,
            "candidate_bytes_modified_or_materialized": False,
            "historical_scope_patch_reapplied": False,
            "search_and_entropy_remain_blocked": True,
            "joint_package_built_or_materialized": False,
            "package_gate_evaluated_or_launched": False,
            "all_protocol_protected_process_identities_preserved": True,
            "protected_processes": live,
            "shared_api_lease_acquired": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
            "benchmark_forward_or_full220_launch_allowed": False,
        },
        "authorization": {
            "selected_scope_alias_component_watcher_active": True,
            "future_parent_content_read_requires_parent_terminal_state": True,
            "future_mainline_scope_alias_is_zero_byte": True,
            "future_p12_scope_binding_is_historical_schema70": True,
            "future_unowned_components_require_separate_publishers": True,
            "future_joint_package_requires_complete_selected_components": True,
            "future_all220_requires_package_gate_or_identity_handoff_and_separate_executor": True,
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
        raise RuntimeError("V2.42.07 wait-audit path drifted")
    value = build_audit()
    publish_new(target, value)
    print({"path": str(target), "sha256": sha256(target)})


if __name__ == "__main__":
    main()
