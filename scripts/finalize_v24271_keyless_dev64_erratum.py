#!/usr/bin/env python3
"""Run the frozen V2.42.71 finalizer with the narrow forward erratum barrier."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import finalize_v24271_keyless_dev64 as frozen  # noqa: E402
from scripts.validate_v24271_forward_erratum import (  # noqa: E402
    validate_committed_erratum,
    validate_forward_barrier as validate_erratum_forward_barrier,
)


def validate_candidate_barrier(root: Path) -> dict[str, Any]:
    barrier = validate_erratum_forward_barrier(root)
    forward = barrier["forward"]
    freeze = barrier["freeze"]
    rows = barrier["rows"]
    if (
        forward.get("shared_model_receipts", {}).get(
            "all_acquisitions_match_actual_requests"
        )
        is not True
        or forward.get("candidate_exact64_before_control_or_evaluator_open")
        is not True
        or freeze.get(
            "exact_terminal_before_control_prediction_mapping_gold_or_evaluator_open"
        )
        is not True
    ):
        raise RuntimeError("V2.42.71 erratum candidate freeze barrier is incomplete")
    return {
        "forward": forward,
        "freeze": freeze,
        "rows": rows,
        "summary": barrier["summary"],
        "forward_protocol": barrier["protocol"],
    }


def finalize(root: Path = ROOT, *, resume_evaluator: bool = False) -> dict[str, Any]:
    validate_committed_erratum(root)
    original = frozen.validate_candidate_barrier
    frozen.validate_candidate_barrier = validate_candidate_barrier
    try:
        return frozen.finalize(root, resume_evaluator=resume_evaluator)
    finally:
        frozen.validate_candidate_barrier = original


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(ROOT))
    parser.add_argument("--resume-evaluator", action="store_true")
    args = parser.parse_args()
    value = finalize(Path(args.root), resume_evaluator=args.resume_evaluator)
    print(
        json.dumps(
            {"result": str(frozen.FINAL_RESULT), "status": value["status"]},
            sort_keys=True,
        )
    )
