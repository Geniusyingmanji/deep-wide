#!/usr/bin/env python3
"""Audit V2.42.15 at its healthy parent-preterminal boundary."""

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

from deepwide_agent.v24200_successor import payload_sha256  # noqa: E402
from scripts.activate_v24215_joint_package_recovery import (  # noqa: E402
    validate_activation,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    publish_new,
    read_object,
    sha256,
)
from scripts.preregister_v24215_joint_package_recovery import (  # noqa: E402
    ACTIVATION,
    FAILED_AUDIT_PATH,
    FAILED_AUDIT_SHA256,
    OUTPUT,
    PUBLICATION,
    STATE,
    V24214_ACTIVATION,
    V24214_CANDIDATE,
    V24214_PROTOCOL,
    V24214_PUBLICATION,
    V24214_STATE,
    WAIT_AUDIT,
    protected_processes,
    validate_protocol,
)
from scripts.publish_v24215_joint_package_recovery import (  # noqa: E402
    CANDIDATE_ROOT,
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
    unsigned = {
        key: item for key, item in state.items() if key != "state_payload_sha256"
    }
    frozen = protocol["value"]["safe_wait_boundary"]["protected_processes"]
    live = protected_processes(proc_root)
    false_fields = (
        "selected_work_order_opened",
        "markdown_publication_opened",
        "scope_publication_opened",
        "search_publication_opened",
        "entropy_publication_opened",
        "v24214_protocol_activation_state_candidate_or_publication_reused_overwritten_or_resumed",
        "joint_package_publication_created",
        "identity_handoff_only",
        "joint_package_materialized",
        "single_deepest_cumulative_graph_used",
        "component_directory_overlay_used",
        "complete_parent_and_component_regression_rerun",
        "strict_component_activation_validated",
        "silent_component_drop_or_baseline_fallback_used",
        "package_gate_evaluated_or_launched",
        "dev64_launch_allowed",
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
        state.get("role") != "v24215_selected_joint_package_recovery_state"
        or state.get("protocol", {}).get("sha256") != protocol["sha256"]
        or state.get("execution_activation", {}).get("sha256")
        != activation["sha256"]
        or state.get("recovery_parent")
        != {"path": FAILED_AUDIT_PATH, "sha256": FAILED_AUDIT_SHA256}
        or state.get("status")
        != "waiting_for_v24213_entropy_recovery_terminal"
        or state.get("reason") != "parent_preterminal"
        or state.get("parent_safe_state_envelope_opened") is not True
        or state.get("parent_state", {}).get("terminal") is not False
        or any(state.get(field) is not False for field in false_fields)
        or state.get("state_payload_sha256") != payload_sha256(unsigned)
        or (root / PUBLICATION).exists()
        or (root / PUBLICATION).is_symlink()
        or CANDIDATE_ROOT.exists()
        or CANDIDATE_ROOT.is_symlink()
        or not (root / V24214_PROTOCOL).is_file()
        or not (root / V24214_ACTIVATION).is_file()
        or not (root / V24214_STATE).is_file()
        or (root / V24214_PUBLICATION).exists()
        or (root / V24214_PUBLICATION).is_symlink()
        or V24214_CANDIDATE.exists()
        or V24214_CANDIDATE.is_symlink()
        or live != frozen
    ):
        raise RuntimeError("V2.42.15 recovery wait boundary is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24215_selected_joint_package_recovery_wait_audit",
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "protocol": {
            "path": str(OUTPUT),
            "sha256": protocol["sha256"],
            "decision_contract_sha256": protocol["value"][
                "decision_contract_sha256"
            ],
            "control_manifest_sha256": protocol["value"]["control_surface"][
                "manifest_sha256"
            ],
        },
        "execution_activation": {
            "path": str(ACTIVATION),
            "sha256": activation["sha256"],
            "watcher_pid": activation["value"]["watcher"]["pid"],
            "watcher_start_ticks": activation["value"]["watcher"][
                "start_ticks"
            ],
        },
        "initial_wait_state": {
            "path": str(STATE),
            "sha256": sha256(state_path),
            "status": state["status"],
        },
        "boundary": {
            "only_recovery_delta_is_actual_entropy_publication_path": True,
            "parent_safe_state_envelope_opened": True,
            "parent_terminal": False,
            "selected_work_order_and_component_publications_unopened": True,
            "failed_v24214_protocol_activation_and_state_preserved": True,
            "failed_v24214_candidate_and_publication_absent": True,
            "recovery_joint_publication_absent": True,
            "recovery_joint_candidate_absent": True,
            "component_directory_overlay_used": False,
            "all_protocol_protected_process_identities_preserved": True,
            "protected_processes": live,
            "package_gate_evaluated_or_launched": False,
            "dev64_launch_allowed": False,
            "shared_api_lease_acquired": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
            "benchmark_forward_or_full220_launch_allowed": False,
        },
        "authorization": {
            "versioned_recovery_watcher_active": True,
            "future_selected_content_read_requires_parent_terminal": True,
            "future_joint_publication_requires_complete_revalidation": True,
            "future_dev64_requires_separate_package_gate_protocol": True,
            "future_all220_requires_package_gate_capacity_and_single_owner": True,
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
        raise RuntimeError("V2.42.15 wait-audit output drifted")
    value = build_audit()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
