#!/usr/bin/env python3
"""The only authorized local entrypoint for V2.43.20 evaluation."""

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
from deepwide_agent.v24321_v24320_evaluator_guard import (
    DECISION,
    validate_live_decision,
)
from scripts.audit_v24187_phase_liveness import process_snapshot
from scripts.audit_v24195_lease_owner_compatibility import lease_observation
from scripts.preregister_v24259_deterministic_normalizer_smoke import _matching


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


def main() -> None:
    if any(
        (ROOT / path).exists() or (ROOT / path).is_symlink()
        for path in (EVALUATOR_ROOT, FINAL_RESULT)
    ):
        raise RuntimeError("V2.43.21 evaluator surface is not pristine")
    rows = process_snapshot()
    if (
        _matching(rows, RUNNER)
        or _matching(rows, CHILD)
        or lease_observation(ROOT, Path("/proc")).get("active") is not False
        or protected_watcher_snapshot() != EXPECTED_WATCHERS
    ):
        raise RuntimeError("V2.43.21 live closure gate failed")
    decision = validate_live_decision(
        ROOT,
        json.loads((ROOT / DECISION).read_text(encoding="utf-8"))
    )
    if (
        decision.get("passed") is not True
        or decision.get("failed_checks") != []
        or decision.get("authorization", {}).get("v24320_evaluator") is not True
    ):
        raise RuntimeError("V2.43.21 evaluator guard is not positive")
    # Import only after the positive, sealed guard has been verified.  The
    # finalizer is the first component with mapping/evaluator capability.
    from scripts.finalize_v24320_paired_dev64 import finalize

    result = finalize(ROOT)
    print(
        json.dumps(
            {
                "result": str(FINAL_RESULT),
                "status": result["status"],
                "failed_checks": result["decision"]["failed_checks"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
