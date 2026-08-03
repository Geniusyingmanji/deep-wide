#!/usr/bin/env python3
"""Publish the content-free V2.43.21 decision after V2.43.20 forward closure."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24320_forward_contract import (
    EVALUATOR_ROOT,
    FINAL_RESULT,
    protected_watcher_snapshot,
)
from deepwide_agent.v24321_v24320_evaluator_guard import DECISION, build_decision
from scripts.audit_v24187_phase_liveness import process_snapshot
from scripts.audit_v24195_lease_owner_compatibility import lease_observation
from scripts.preregister_v24259_deterministic_normalizer_smoke import _matching
from scripts.preregister_v24321_v24320_evaluator_guard import publish


RUNNER = "scripts/run_v24320_paired_dev64.py"
CHILD = "scripts/run_v24320_paired_dev64_task.py"
EXPECTED_WATCHERS = [
    {
        "pid": 795336,
        "marker": "scripts/watch_v2415_r1_checkpoint_liveness.py",
        "start_ticks": 713986317,
    },
    {
        "pid": 3061652,
        "marker": "scripts/watch_v24218_exact220_executor.py",
        "start_ticks": 747569004,
    },
]


if __name__ == "__main__":
    rows = process_snapshot()
    value = build_decision(
        ROOT,
        evaluator_surface_absent=not any(
            (ROOT / path).exists() or (ROOT / path).is_symlink()
            for path in (EVALUATOR_ROOT, FINAL_RESULT)
        ),
        runner_and_children_absent=not _matching(rows, RUNNER)
        and not _matching(rows, CHILD),
        shared_lease_inactive=lease_observation(ROOT, Path("/proc")).get("active")
        is False,
        protected_watchers_unchanged=protected_watcher_snapshot()
        == EXPECTED_WATCHERS,
    )
    publish(ROOT / DECISION, value)
    print(
        json.dumps(
            {
                "path": str(DECISION),
                "passed": value["passed"],
                "failed_checks": value["failed_checks"],
            },
            sort_keys=True,
        )
    )
