#!/usr/bin/env python3
"""Audit V2.42.13 at its healthy dual-preterminal recovery boundary."""

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
from scripts.activate_v24213_entropy_recovery import validate_activation  # noqa: E402
from scripts.preregister_v24212_entropy_component import (  # noqa: E402
    protected_processes,
    publish_new,
    sha256,
)
from scripts.preregister_v24213_entropy_recovery import (  # noqa: E402
    ACTIVATION,
    OUTPUT,
    PUBLICATION,
    STATE,
    V24212_ACTIVATION,
    V24212_CANDIDATE,
    V24212_PUBLICATION,
    V24212_STATE,
    WAIT_AUDIT,
    validate_protocol,
)
from scripts.publish_v24213_entropy_recovery import CANDIDATE_ROOT  # noqa: E402


def _read_object(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.42.13 expected an ordinary wait-state file")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("V2.42.13 expected one wait-state object")
    return value


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
    state = _read_object(state_path)
    unsigned = {
        key: item for key, item in state.items() if key != "state_payload_sha256"
    }
    frozen = protocol["value"]["safe_wait_boundary"]["protected_processes"]
    live = protected_processes(proc_root)
    false_fields = (
        "selected_work_order_opened",
        "search_publication_opened",
        "gate2a_report_opened",
        "action_model_opened",
        "failed_v24212_activation_state_candidate_or_publication_reused_overwritten_or_resumed",
        "numeric_metrics_predictions_or_aggregates_read_before_both_terminal",
        "component_publication_created",
        "entropy_component_published",
        "entropy_component_absent_noop",
        "candidate_materialized",
        "real_state_transition_adapters_included",
        "historical_module_containing_revoked_projection_arm_present_as_adapter_dependency",
        "projection_only_action_arm_selected_instantiated_or_called",
        "joint_package_quality_gate_evaluated_or_launched",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_question_answer_evidence_prediction_or_url_parsed_or_emitted",
        "mapping_gold_category_question_type_evaluator_score_or_reward_read_for_forward_routing",
        "credential_value_read_persisted_hashed_or_emitted",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
        "terminal",
    )
    if (
        state.get("role") != "v24213_selected_entropy_component_recovery_state"
        or state.get("protocol", {}).get("sha256") != protocol["sha256"]
        or state.get("execution_activation", {}).get("sha256")
        != activation["sha256"]
        or state.get("status")
        != "waiting_for_search_parent_and_gate2a_terminal"
        or state.get("reason") != "search_parent_and_gate2a_preterminal"
        or state.get("search_parent_safe_state_envelope_opened") is not True
        or state.get("gate2a_safe_state_envelope_opened") is not True
        or any(state.get(field) is not False for field in false_fields)
        or state.get("state_payload_sha256") != payload_sha256(unsigned)
        or (root / PUBLICATION).exists()
        or (root / PUBLICATION).is_symlink()
        or CANDIDATE_ROOT.exists()
        or CANDIDATE_ROOT.is_symlink()
        or not (root / V24212_ACTIVATION).is_file()
        or not (root / V24212_STATE).is_file()
        or (root / V24212_PUBLICATION).exists()
        or (root / V24212_PUBLICATION).is_symlink()
        or V24212_CANDIDATE.exists()
        or V24212_CANDIDATE.is_symlink()
        or live != frozen
    ):
        raise RuntimeError("V2.42.13 recovery wait boundary is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24213_selected_entropy_component_recovery_wait_audit",
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
            "recovery_delta_exactly_upstream_false_field_name": True,
            "search_parent_safe_state_envelope_opened": True,
            "gate2a_safe_state_envelope_opened": True,
            "search_parent_terminal": False,
            "gate2a_terminal": False,
            "selected_parent_report_and_model_unopened": True,
            "failed_v24212_activation_and_state_preserved": True,
            "failed_v24212_candidate_and_publication_absent": True,
            "recovery_component_publication_absent": True,
            "recovery_candidate_root_absent": True,
            "all_protocol_protected_process_identities_preserved": True,
            "protected_processes": live,
            "projection_only_action_arm_selected_instantiated_or_called": False,
            "shared_api_lease_acquired": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "mapping_gold_category_question_type_evaluator_score_or_reward_read_for_forward_routing": False,
            "benchmark_forward_or_full220_launch_allowed": False,
        },
        "authorization": {
            "versioned_recovery_watcher_active": True,
            "future_selected_content_read_requires_both_terminal_states": True,
            "future_entropy_materialization_requires_replicate_aware_go": True,
            "future_all220_requires_package_gate_and_separate_executor": True,
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
        raise RuntimeError("V2.42.13 wait-audit path drifted")
    value = build_audit()
    publish_new(target, value)
    print({"path": str(target), "sha256": sha256(target)})


if __name__ == "__main__":
    main()
