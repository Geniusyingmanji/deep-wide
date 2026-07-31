#!/usr/bin/env python3
"""Audit V2.41.98 at its activated pre-capacity wait boundary."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from deepwide_agent.v24197_parallel_all220 import payload_sha256  # noqa: E402
from deepwide_agent.v24198_candidate_bundle import (  # noqa: E402
    BUNDLE,
    GO_RECEIPT,
    HANDOFF,
    QUALITY_TERMINAL_RECEIPT,
    SELECTION_PROTOCOL,
)
from scripts.activate_v24198_candidate_bundle import validate_activation  # noqa: E402
from scripts.preregister_v24198_candidate_bundle import (  # noqa: E402
    ACTIVATION,
    CAPACITY_FREEZE,
    CAPACITY_REPORT,
    OUTPUT,
    PLAN,
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
    future_absent = all(
        not (root / path).exists() and not (root / path).is_symlink()
        for path in (
            CAPACITY_REPORT,
            CAPACITY_FREEZE,
            SELECTION_PROTOCOL,
            QUALITY_TERMINAL_RECEIPT,
            HANDOFF,
            GO_RECEIPT,
            BUNDLE,
            PLAN,
        )
    )
    frozen_processes = protocol["value"]["safe_wait_boundary"][
        "protected_processes"
    ]
    live_processes = protected_processes(proc_root)
    false_fields = (
        "capacity_pair_opened",
        "selector_protocol_opened",
        "quality_terminal_receipt_opened",
        "selected_candidate_handoff_opened",
        "candidate_publication_bytes_hashed",
        "candidate_freezes_opened",
        "candidate_manifest_bytes_hashed",
        "go_receipt_created",
        "candidate_bundle_created",
        "candidate_selection_or_gate_evaluated",
        "shared_api_lease_acquired",
        "network_model_search_fetch_evaluator_or_api_called",
        "benchmark_question_answer_evidence_prediction_or_url_values_parsed_or_emitted",
        "mapping_gold_category_question_type_evaluator_score_read",
        "credential_value_read_persisted_hashed_or_emitted",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "benchmark_forward_or_full220_launch_allowed",
        "leaderboard_submission_or_sota_claim",
        "terminal",
    )
    if (
        state.get("role") != "v24198_candidate_bundle_watcher_state"
        or state.get("protocol", {}).get("sha256") != protocol["sha256"]
        or state.get("execution_activation", {}).get("sha256")
        != activation["sha256"]
        or state.get("status") != "waiting_for_capacity_freeze"
        or state.get("reason") != "v24196_capacity_pair_absent"
        or any(state.get(field) is not False for field in false_fields)
        or state.get("state_payload_sha256") != payload_sha256(unsigned)
        or not future_absent
        or live_processes != frozen_processes
    ):
        raise RuntimeError("V2.41.98 wait boundary is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24198_candidate_bundle_wait_activation_audit",
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
            "compiler_pid": activation["value"]["compiler"]["pid"],
            "compiler_start_ticks": activation["value"]["compiler"]["start_ticks"],
        },
        "initial_wait_state": {
            "path": str(STATE),
            "sha256": sha256(state_path),
            "status": state["status"],
        },
        "boundary": {
            "capacity_selection_handoff_go_bundle_and_plan_absent": True,
            "selector_terminal_handoff_candidate_or_manifest_opened": False,
            "all_protocol_protected_process_identities_preserved": True,
            "protected_processes": live_processes,
            "candidate_selection_or_gate_evaluated": False,
            "shared_api_lease_acquired": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "benchmark_question_answer_evidence_prediction_or_url_values_parsed_or_emitted": False,
            "mapping_gold_category_question_type_evaluator_score_read": False,
            "process_signal_restart_resume_rerun_skip_or_selective_retry": False,
            "benchmark_forward_or_full220_launch_allowed": False,
        },
        "authorization": {
            "wait_only_bundle_compiler_active": True,
            "candidate_selection_active": False,
            "go_receipt_or_bundle_creation_active": False,
            "future_compilation_requires_capacity_and_independent_terminal_handoff": True,
            "future_executor_requires_separate_preregistration_and_activation": True,
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
        raise RuntimeError("V2.41.98 wait-audit path drifted")
    value = build_audit()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
