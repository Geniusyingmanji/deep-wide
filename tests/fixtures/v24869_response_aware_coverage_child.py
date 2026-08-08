#!/usr/bin/env python3
"""Network-free child for the V2.48.69 subprocess parent gate."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24868_response_aware_coverage_runtime import (  # noqa: E402
    run_child_bundle,
)
import test_v24860_coverage_revision_integration as core_test  # noqa: E402
from test_v24867_response_aware_coverage_bundle import (  # noqa: E402
    ScenarioSearch,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenario", choices=("pre_provider_failure", "retry"), required=True
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--directory", required=True)
    args = parser.parse_args()
    output = Path(args.output_root).resolve()
    directory = Path(args.directory).resolve()
    clock = core_test.Clock(100.0)
    inner = core_test.SyntheticModel(
        [core_test.PLAN, core_test.BASELINE, core_test.SUPPORTED]
    )
    model = build_deadline_model(
        url="http://unused.invalid/responses",
        model_name="synthetic",
        reasoning_effort="low",
        service_tier="",
        static_timeout_seconds=180,
        max_retries=2,
        slot_directory=core_test.make_slots(directory),
        output_root=output,
        slot_cap=2,
        pool_id="v24263_score_first_global_model_slots_v1",
        absolute_deadline=220.0,
        cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.01,
        monotonic=clock,
        sleeper=clock.sleep,
        inner=inner,
    )
    search = ScenarioSearch(
        clock, deadline=220.0, scenario=args.scenario
    )
    run_child_bundle(
        output_root=output,
        directory=directory,
        task=core_test.task(),
        model=model,
        search=search,
        limits=core_test.limits(),
        two_wave_policy=TwoWavePolicy(),
        expected_model_slot_cap=2,
        expected_tavily_key_slot_cap=2,
        monotonic=clock,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
