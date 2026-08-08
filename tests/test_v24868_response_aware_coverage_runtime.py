from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
)
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent import v24864_coverage_revision_child_runtime as frozen  # noqa: E402
from deepwide_agent.v24867_response_aware_coverage_bundle import (  # noqa: E402
    BUNDLE_NAME,
    validate_bundle,
)
from deepwide_agent import v24868_response_aware_coverage_runtime as repaired  # noqa: E402
import test_v24860_coverage_revision_integration as core_test  # noqa: E402
from test_v24867_response_aware_coverage_bundle import ScenarioSearch  # noqa: E402


class V24868ResponseAwareCoverageRuntimeTests(unittest.TestCase):
    def clients(self, output: Path, scenario: str):
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
            slot_directory=core_test.make_slots(output),
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
        search = ScenarioSearch(clock, deadline=220.0, scenario=scenario)
        return clock, inner, model, search

    def run_scenario(self, scenario: str):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        output = Path(temporary.name)
        task_directory = output / "task"
        task_directory.mkdir()
        clock, inner, model, search = self.clients(output, scenario)
        value = repaired.run_child_bundle(
            output_root=output,
            directory=task_directory,
            task=core_test.task(),
            model=model,
            search=search,
            limits=core_test.limits(),
            two_wave_policy=TwoWavePolicy(),
            expected_model_slot_cap=2,
            expected_tavily_key_slot_cap=2,
            monotonic=clock,
        )
        return temporary, output, task_directory, inner, search, value

    def test_pre_provider_failure_commits_parent_prediction_bundle(self) -> None:
        temporary, output, task_directory, _inner, _search, value = (
            self.run_scenario("pre_provider_failure")
        )
        self.addCleanup(temporary.cleanup)
        self.assertEqual(value["role"], "v24863_coverage_revision_child_bundle_receipt")
        self.assertTrue((task_directory / BUNDLE_NAME).is_file())
        validate_bundle(
            output_root=output,
            directory=task_directory,
            expected_model_slot_cap=2,
            expected_tavily_key_slot_cap=2,
        )
        terminal = validate_child_receipt(
            json.loads(
                (task_directory / repaired.TERMINAL_NAME).read_text(encoding="utf-8")
            )
        )
        self.assertEqual(terminal["stage"], "result_envelope_written")

    def test_retry_commits_parent_prediction_bundle(self) -> None:
        temporary, output, task_directory, _inner, _search, _value = (
            self.run_scenario("retry")
        )
        self.addCleanup(temporary.cleanup)
        validate_bundle(
            output_root=output,
            directory=task_directory,
            expected_model_slot_cap=2,
            expected_tavily_key_slot_cap=2,
        )

    def test_privileged_input_still_fails_before_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            task_directory = output / "task"
            task_directory.mkdir()
            clock, inner, model, search = self.clients(
                output, "pre_provider_failure"
            )
            with self.assertRaises(ValueError):
                repaired.run_child_bundle(
                    output_root=output,
                    directory=task_directory,
                    task={**core_test.task(), "question_type": "forbidden"},
                    model=model,
                    search=search,
                    limits=core_test.limits(),
                    two_wave_policy=TwoWavePolicy(),
                    expected_model_slot_cap=2,
                    expected_tavily_key_slot_cap=2,
                    monotonic=clock,
                )
            self.assertEqual(inner.requests, 0)
            self.assertEqual(search.calls, 0)
            self.assertFalse((task_directory / BUNDLE_NAME).exists())

    def test_isolated_successor_does_not_patch_frozen_runtime(self) -> None:
        repaired.validate_isolation()
        self.assertIs(
            frozen.run_child_bundle.__globals__["write_bundle"],
            frozen.write_bundle,
        )


if __name__ == "__main__":
    unittest.main()
