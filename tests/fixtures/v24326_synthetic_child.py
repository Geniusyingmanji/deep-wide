#!/usr/bin/env python3
"""Network-free real subprocess child for V2.43.26."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24309_runner_exit_integration import (  # noqa: E402
    run_child_with_terminal_receipt,
)
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24325_shared_prefix_revision_runtime import validate_result  # noqa: E402
from deepwide_agent.v24326_runner_integration import (  # noqa: E402
    build_envelope,
    run_v24326_task,
)
from test_v24325_shared_prefix_revision_runtime import limits  # noqa: E402
from test_v24326_runner_integration import (  # noqa: E402
    Clock,
    InnerModel,
    SyntheticDeadlineSearch,
)
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402


def write_new(path: Path, value: dict) -> None:
    descriptor = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=(
            "success",
            "slot_reject",
            "reserve_failure",
            "nonzero",
            "timeout",
            "missing_result",
            "missing_model",
            "missing_transport",
            "invalid_result",
            "drift_model",
            "drift_transport",
        ),
        required=True,
    )
    parser.add_argument("--task", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--model-receipt", required=True)
    parser.add_argument("--transport", required=True)
    parser.add_argument("--terminal", required=True)
    parser.add_argument("--slots", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    task = json.loads(Path(args.task).read_text(encoding="utf-8"))

    def action() -> None:
        if args.mode == "timeout":
            time.sleep(5)
            return
        if args.mode == "nonzero":
            raise RuntimeError("content-free synthetic nonzero")
        clock = Clock()
        deadline = 100.10 if args.mode == "slot_reject" else 300.0
        model = build_deadline_model(
            url="http://unused.invalid/responses",
            model_name="synthetic",
            reasoning_effort="low",
            service_tier="",
            static_timeout_seconds=180,
            max_retries=2,
            slot_directory=Path(args.slots),
            output_root=Path(args.output_root),
            slot_cap=2,
            pool_id=POOL_ID,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
            inner=InnerModel(),
        )
        search = SyntheticDeadlineSearch(
            clock,
            deadline=deadline,
            fail_reserve=args.mode == "reserve_failure",
        )
        outcome = run_v24326_task(
            task,
            model=model,
            search=search,
            limits=limits(),
            monotonic=clock,
        )
        validate_result(outcome.result)
        external_model = dict(outcome.model_slot_receipt)
        external_transport = dict(outcome.transport_health)
        if args.mode == "drift_model":
            external_model["remaining_seconds_at_receipt"] += 0.125
            external_model.pop("receipt_payload_sha256")
            from deepwide_agent.v24263_global_model_limiter import payload_sha256

            external_model["receipt_payload_sha256"] = payload_sha256(external_model)
        if args.mode == "drift_transport":
            external_transport["hosted_search_attempts"] += 1
        if args.mode != "missing_model":
            write_new(Path(args.model_receipt), external_model)
        if args.mode != "missing_transport":
            write_new(Path(args.transport), external_transport)
        if args.mode == "invalid_result":
            write_new(Path(args.result), {"invalid": True})
        elif args.mode != "missing_result":
            write_new(Path(args.result), build_envelope(outcome))

    run_child_with_terminal_receipt(
        output_root=Path(args.output_root),
        directory=Path(args.terminal).parent,
        action=action,
        result_name=Path(args.result).name,
        model_receipt_name=Path(args.model_receipt).name,
        transport_receipt_name=Path(args.transport).name,
        terminal_name=Path(args.terminal).name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
