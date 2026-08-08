#!/usr/bin/env python3
"""Network-free production-shaped child for the V2.48.76 parent gate."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24874_keyless_coverage_bundle import BUNDLE_NAME  # noqa: E402
from deepwide_agent.v24875_keyless_coverage_child_runtime import (  # noqa: E402
    run_child_bundle,
)
import test_v24860_coverage_revision_integration as core_test  # noqa: E402
from test_v24875_keyless_coverage_child_runtime import (  # noqa: E402
    MeteredLowSearch,
    MeteredPreProviderFailureSearch,
    MeteredRetrySearch,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=("low", "pre_provider", "retry", "nonzero", "timeout", "delete_bundle"),
        required=True,
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()
    output = Path(args.output_root).resolve()
    directory = Path(args.directory).resolve()
    if args.mode == "timeout":
        time.sleep(5)
        return 0
    clock = core_test.Clock(100.0)
    inner = core_test.SyntheticModel(
        [core_test.PLAN, core_test.BASELINE, core_test.SUPPORTED]
    )
    model = build_deadline_model(
        url="http://unused.invalid/responses", model_name="synthetic",
        reasoning_effort="low", service_tier="", static_timeout_seconds=180,
        max_retries=2, slot_directory=core_test.make_slots(directory),
        output_root=output, slot_cap=2, pool_id=POOL_ID,
        absolute_deadline=220.0, cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.01, monotonic=clock, sleeper=clock.sleep,
        inner=inner,
    )
    search_cls = {
        "low": MeteredLowSearch,
        "pre_provider": MeteredPreProviderFailureSearch,
        "retry": MeteredRetrySearch,
        "delete_bundle": MeteredLowSearch,
        "nonzero": MeteredLowSearch,
    }[args.mode]
    search = search_cls(clock, deadline=220.0)
    task = core_test.task()
    if args.mode == "nonzero":
        task = {**task, "question_type": "forbidden"}
    run_child_bundle(
        output_root=output, directory=directory, task=task, model=model,
        search=search, limits=core_test.limits(), expected_model_slot_cap=2,
        monotonic=clock,
    )
    if args.mode == "delete_bundle":
        (directory / BUNDLE_NAME).unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
