#!/usr/bin/env python3
"""Seal the failed V2.42.14 activation after a frozen path mismatch."""

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
from deepwide_agent.v24214_joint_package import PUBLICATION_PATHS  # noqa: E402
from scripts.preregister_v24210_search_component import (  # noqa: E402
    publish_new,
    read_object,
    sha256,
)
from scripts.preregister_v24214_joint_package import (  # noqa: E402
    ACTIVATION,
    OUTPUT as PROTOCOL,
    PUBLICATION,
    STATE,
    protected_processes,
)
from scripts.publish_v24213_entropy_recovery import (  # noqa: E402
    OUTPUT as ACTUAL_ENTROPY_PUBLICATION,
)
from scripts.publish_v24214_joint_package import CANDIDATE_ROOT  # noqa: E402


OUTPUT = Path("results/v24214_selected_joint_package_failed_activation_audit_v1_20260731.json")
PROTOCOL_SHA256 = "d565ed96245c3746b71615c2b8e8e5089d7373effbba686b8efb6da7b3242fff"
ACTIVATION_SHA256 = "7288f7f01391df2a15c9ed9cc31f0f9b19509ae4d2ed326cc67ccee1ca1541c5"
STATE_SHA256 = "1a4dd7703508d6a0c97cc5406b614903751000bdc41e3e0c666a7377170207a3"
FROZEN_WRONG_PATH = Path(
    "results/v24213_selected_entropy_component_recovery_publication_v1_20260731.json"
)


def _sealed(value: dict[str, Any], field: str) -> bool:
    unsigned = dict(value)
    seal = unsigned.pop(field, None)
    return isinstance(seal, str) and seal == payload_sha256(unsigned)


def _watcher_pids() -> list[int]:
    marker = "scripts/watch_v24214_joint_package.py"
    from scripts.audit_v24187_phase_liveness import (
        actual_python_script,
        process_snapshot,
    )

    pids: list[int] = []
    for row in process_snapshot(Path("/proc")):
        argv = [str(item) for item in row.get("argv") or []]
        script = actual_python_script(argv)
        if script is not None and (
            script == marker or script.endswith("/" + marker)
        ):
            pids.append(int(row["pid"]))
    return sorted(pids)


def build_audit(
    root: Path = ROOT, *, created_at_unix: int | None = None
) -> dict[str, Any]:
    root = root.resolve()
    protocol = read_object(root / PROTOCOL)
    activation = read_object(root / ACTIVATION)
    state = read_object(root / STATE)
    false_fields = (
        "selected_work_order_opened",
        "markdown_publication_opened",
        "scope_publication_opened",
        "search_publication_opened",
        "entropy_publication_opened",
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
        sha256(root / PROTOCOL) != PROTOCOL_SHA256
        or sha256(root / ACTIVATION) != ACTIVATION_SHA256
        or sha256(root / STATE) != STATE_SHA256
        or protocol.get("role") != "v24214_selected_joint_package_preregistration"
        or protocol.get("joint_package_contract", {}).get(
            "manifest_payload_sha256"
        )
        != "b839ca6a38178ff1bb9139c3c5b16506d3fa2aa1ed0c6fcee683528777e87113"
        or activation.get("role") != "v24214_selected_joint_package_activation"
        or not _sealed(activation, "activation_payload_sha256")
        or state.get("role") != "v24214_selected_joint_package_watcher_state"
        or state.get("status")
        != "waiting_for_v24213_entropy_recovery_terminal"
        or state.get("reason") != "parent_preterminal"
        or state.get("parent_safe_state_envelope_opened") is not True
        or any(state.get(field) is not False for field in false_fields)
        or not _sealed(state, "state_payload_sha256")
        or PUBLICATION_PATHS.get("entropy") != str(FROZEN_WRONG_PATH)
        or ACTUAL_ENTROPY_PUBLICATION == FROZEN_WRONG_PATH
        or _watcher_pids()
        or (root / PUBLICATION).exists()
        or (root / PUBLICATION).is_symlink()
        or CANDIDATE_ROOT.exists()
        or CANDIDATE_ROOT.is_symlink()
    ):
        raise RuntimeError("V2.42.14 failed-activation evidence drifted")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24214_selected_joint_package_failed_activation_audit",
        "created_at_unix": (
            int(time.time()) if created_at_unix is None else int(created_at_unix)
        ),
        "protocol": {"path": str(PROTOCOL), "sha256": PROTOCOL_SHA256},
        "activation": {"path": str(ACTIVATION), "sha256": ACTIVATION_SHA256},
        "last_state": {"path": str(STATE), "sha256": STATE_SHA256},
        "failure": {
            "classification": "entropy_publication_path_binding_mismatch_fail_closed",
            "frozen_joint_manifest_path": str(FROZEN_WRONG_PATH),
            "actual_v24213_publisher_output_path": str(ACTUAL_ENTROPY_PUBLICATION),
            "paths_equal": False,
            "detected_by_post_activation_cross_constant_audit": True,
            "detected_before_parent_terminal_or_selected_content_open": True,
        },
        "boundary": {
            "parent_safe_state_envelope_opened": True,
            "parent_terminal": False,
            "selected_work_order_opened": False,
            "component_publications_opened": False,
            "joint_candidate_or_publication_created": False,
            "component_directory_overlay_used": False,
            "package_gate_evaluated_or_launched": False,
            "dev64_launched": False,
            "shared_api_lease_acquired": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "mapping_gold_category_question_type_evaluator_score_or_reward_read": False,
            "benchmark_forward_or_full220_launched": False,
            "leaderboard_submission_or_sota_claim": False,
        },
        "disposition": {
            "v24214_watcher_terminated": True,
            "v24214_watcher_pids_remaining": [],
            "v24214_protocol_activation_and_state_preserved": True,
            "same_namespace_restart_retry_resume_or_overwrite_allowed": False,
            "new_versioned_recovery_protocol_required": True,
            "only_recovery_delta_allowed": "bind_entropy_deepest_publication_to_actual_v24213_output_path",
            "upstream_protected_processes_preserved": protected_processes(),
            "package_gate_dev64_capacity_or_full220_authorized": False,
        },
    }
    value["audit_payload_sha256"] = payload_sha256(value)
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(OUTPUT))
    args = parser.parse_args()
    target = Path(args.output)
    if target.resolve(strict=False) != (ROOT / OUTPUT).resolve(strict=False):
        raise RuntimeError("V2.42.14 failure-audit output drifted")
    publish_new(target, build_audit())
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
