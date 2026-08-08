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

from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    validate_child_receipt,
)
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24796_deadline_tavily_search import empty_receipt  # noqa: E402
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    empty_rate_aware_receipt,
)
from deepwide_agent.v24863_coverage_revision_child_bundle import (  # noqa: E402
    BUNDLE_NAME,
    validate_bundle,
)
from deepwide_agent.v24864_coverage_revision_child_runtime import (  # noqa: E402
    TERMINAL_NAME,
    run_child_bundle,
)
import test_v24860_coverage_revision_integration as core_test  # noqa: E402
from test_v24862_same_task_coverage_runtime import SyntheticThinSearch  # noqa: E402


class ReceiptSyntheticThinSearch(SyntheticThinSearch):
    def direct_search_receipt(self):
        logical = int(self.calls)
        value = empty_receipt(2)
        value.update(
            {
                "provider_attempts": logical,
                "successful_queries": logical,
                "slot_acquisitions": logical,
                "status_2xx": logical,
            }
        )
        value["receipt_payload_sha256"] = payload_sha256(
            {key: item for key, item in value.items() if key != "receipt_payload_sha256"}
        )
        return value

    def rate_aware_search_receipt(self):
        value = empty_rate_aware_receipt()
        value["provider_start_reservations"] = int(self.calls)
        value["receipt_payload_sha256"] = payload_sha256(
            {key: item for key, item in value.items() if key != "receipt_payload_sha256"}
        )
        return value


class V24864CoverageRevisionChildRuntimeTests(unittest.TestCase):
    def clients(self, output: Path):
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
        search = ReceiptSyntheticThinSearch(clock, deadline=220.0)
        return clock, inner, model, search

    def test_success_writes_committed_bundle_then_terminal_receipt(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            task_directory = output / "task"
            task_directory.mkdir()
            clock, _inner, model, search = self.clients(output)
            value = run_child_bundle(
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
            self.assertEqual(value["role"], "v24863_coverage_revision_child_bundle_receipt")
            self.assertTrue((task_directory / BUNDLE_NAME).is_file())
            terminal = validate_child_receipt(
                json.loads((task_directory / TERMINAL_NAME).read_text(encoding="utf-8"))
            )
            self.assertEqual(terminal["stage"], "result_envelope_written")
            self.assertTrue(terminal["result_envelope_written"])
            self.assertTrue(terminal["model_receipt_written"])
            self.assertTrue(terminal["transport_receipt_written"])
            validate_bundle(
                output_root=output,
                directory=task_directory,
                expected_model_slot_cap=2,
                expected_tavily_key_slot_cap=2,
            )

    def test_privileged_task_fails_before_effect_and_without_bundle_marker(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            task_directory = output / "task"
            task_directory.mkdir()
            clock, inner, model, search = self.clients(output)
            before = model.receipt()
            with self.assertRaises(ValueError):
                run_child_bundle(
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
            after = model.receipt()
            self.assertEqual(inner.requests, 0)
            self.assertEqual(search.calls, 0)
            self.assertEqual(before["acquisitions"], after["acquisitions"])
            self.assertFalse((task_directory / BUNDLE_NAME).exists())
            terminal = validate_child_receipt(
                json.loads((task_directory / TERMINAL_NAME).read_text(encoding="utf-8"))
            )
            self.assertEqual(terminal["stage"], "child_exception")
            self.assertEqual(terminal["exception_type"], "ValidationError")

    def test_nonpristine_bundle_surface_fails_before_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            task_directory = output / "task"
            task_directory.mkdir()
            (task_directory / "result.json").write_text("{}\n", encoding="utf-8")
            clock, inner, model, search = self.clients(output)
            with self.assertRaises(FileExistsError):
                run_child_bundle(
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
            self.assertEqual(inner.requests, 0)
            self.assertEqual(search.calls, 0)
            self.assertFalse((task_directory / BUNDLE_NAME).exists())


if __name__ == "__main__":
    unittest.main()
