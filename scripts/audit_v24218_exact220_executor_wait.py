#!/usr/bin/env python3
"""Audit V2.42.18 at its activated parent-preterminal wait boundary."""

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

from deepwide_agent.v24218_exact220_executor import payload_sha256  # noqa: E402
from scripts.activate_v24218_exact220_executor import (  # noqa: E402
    validate_activation,
)
from scripts.preregister_v24210_search_component import (  # noqa: E402
    publish_new,
    read_object,
    sha256,
)
from scripts.preregister_v24218_exact220_executor import (  # noqa: E402
    ACTIVATION,
    EXECUTION_START,
    OUTPUT,
    STATE,
    WAIT_AUDIT,
    protected_processes,
    validate_protocol,
)
from scripts.run_v24218_exact220_executor import (  # noqa: E402
    EVALUATOR_ROOT,
    FORWARD_BARRIER,
    MATERIALIZATION,
    PREPARE_ROOT,
    RESULT,
    SHARD_ROOTS,
    SUMMARY,
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
        "package_parent_go_validated",
        "capacity_parent_safe_envelope_opened",
        "capacity_parent_go_validated",
        "shared_api_lease_acquired",
        "lease_compatibility_valid",
        "execution_start_published",
        "candidate_package_opened",
        "capacity_report_or_freeze_opened",
        "materialization_created",
        "fresh_candidate_roots_created",
        "preflight_model_search_api_called",
        "benchmark_forward_called",
        "all_four_shards_exact_terminal",
        "mapping_or_evaluator_opened",
        "official_evaluator_called",
        "result_created",
        "benchmark_category_question_type_split_mapping_gold_answer_evaluator_score_used_for_forward_routing",
        "credential_value_read_persisted_hashed_or_emitted",
        "process_signal_restart_resume_rerun_skip_or_selective_retry",
        "existing_benchmark_or_watcher_signaled_restarted_modified_or_terminated",
        "leaderboard_submission_or_sota_claim",
        "terminal",
    )
    future = (
        EXECUTION_START,
        MATERIALIZATION,
        FORWARD_BARRIER,
        PREPARE_ROOT,
        EVALUATOR_ROOT,
        SUMMARY,
        RESULT,
    )
    frozen_processes = protocol["value"]["safe_wait_boundary"][
        "protected_processes"
    ]
    live_processes = protected_processes(proc_root)
    if (
        state.get("role") != "v24218_exact220_executor_watcher_state"
        or state.get("protocol", {}).get("sha256") != protocol["sha256"]
        or state.get("execution_activation", {}).get("sha256")
        != activation["sha256"]
        or state.get("status") != "waiting_for_v24216_package_gate_terminal"
        or state.get("reason") != "package_parent_preterminal"
        or state.get("package_parent_safe_envelope_opened") is not True
        or state.get("package_parent", {}).get("terminal") is not False
        or state.get("runtime_forward_inputs_exactly_opaque_id_and_question") is not True
        or any(state.get(field) is not False for field in false_fields)
        or seal != payload_sha256(unsigned)
        or any(_present(root, path) for path in future)
        or any(path.exists() or path.is_symlink() for path in SHARD_ROOTS.values())
        or live_processes != frozen_processes
    ):
        raise RuntimeError("V2.42.18 activated wait boundary is invalid")
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": "v24218_exact220_executor_wait_audit",
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
            "package_parent_safe_envelope_opened": True,
            "package_parent_terminal": False,
            "capacity_parent_opened": False,
            "candidate_package_or_capacity_report_freeze_opened": False,
            "execution_start_absent": True,
            "all_four_future_candidate_roots_absent": True,
            "materialization_barrier_evaluator_and_result_absent": True,
            "shared_api_lease_acquired": False,
            "network_model_search_fetch_evaluator_or_api_called": False,
            "benchmark_forward_called": False,
            "mapping_or_evaluator_opened": False,
            "runtime_forward_inputs_exactly_opaque_id_and_question": True,
            "benchmark_category_question_type_split_mapping_gold_answer_evaluator_score_used_for_forward_routing": False,
            "existing_benchmark_and_watchers_preserved_without_signal_restart_or_modification": True,
            "protected_processes": live_processes,
        },
        "authorization": {
            "watcher_active": True,
            "future_execution_requires_both_parent_go": True,
            "future_execution_requires_two_quiet_observations_and_unique_lease": True,
            "future_execution_start_precedes_any_materialization_or_api": True,
            "future_four_fresh_roots_precede_per_shard_fresh_preflight": True,
            "future_mapping_and_evaluator_require_four_exact_terminal_shards": True,
            "future_incomplete_attempt_is_terminal_no_retry": True,
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
        raise RuntimeError("V2.42.18 wait-audit output drifted")
    value = build_audit()
    publish_new(target, value)
    print(json.dumps({"path": str(target), "sha256": sha256(target)}))


if __name__ == "__main__":
    main()
