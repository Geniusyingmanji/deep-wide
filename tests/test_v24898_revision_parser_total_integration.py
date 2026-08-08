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

from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24319_runner_integration import run_v24319_task  # noqa: E402
from deepwide_agent import v24898_revision_parser_total_integration as target  # noqa: E402
from test_v24319_runner_integration import Clock, SyntheticDeadlineSearch  # noqa: E402
from test_v24860_coverage_revision_integration import (  # noqa: E402
    SyntheticModel, limits, make_slots, pages_for,
)


class V24898RevisionParserTotalIntegrationTests(unittest.TestCase):
    def test_fullwidth_pipe_parent_returns_without_third_effect(self) -> None:
        task = {
            "opaque_id": "task_0123456789abcdef01234567",
            "question": "Return one table. The column names are: Name, Code, Note.",
        }
        plan = json.dumps(
            {"columns": ["Name", "Code", "Note"], "queries": ["one", "two", "three", "four"]}
        )
        table = "| Name | Code | Note |\n| --- | --- | --- |\n| Alpha | left｜right | Stable |"
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            clock = Clock(100.0)
            inner = SyntheticModel([plan, table, "must-not-be-consumed"])
            model = build_deadline_model(
                url="http://unused.invalid/responses", model_name="synthetic",
                reasoning_effort="low", service_tier="", static_timeout_seconds=180,
                max_retries=2, slot_directory=make_slots(output), output_root=output,
                slot_cap=2, pool_id=POOL_ID, absolute_deadline=220.0,
                cleanup_reserve_seconds=5, minimum_attempt_seconds=0.01,
                monotonic=clock, sleeper=clock.sleep, inner=inner,
            )
            search = SyntheticDeadlineSearch(clock, deadline=220.0)
            parent = run_v24319_task(
                task, arm="baseline", model=model, search=search, limits=limits(),
                two_wave_policy=TwoWavePolicy(), monotonic=clock,
            )
            before = model.receipt()["acquisitions"]
            value = target.run_coverage_revision(
                task, parent_result=parent.result,
                parent_model_slot_receipt=parent.model_slot_receipt,
                model=model, pages=pages_for(parent.result), limits=limits(),
                monotonic=clock,
            )
            receipt = target.validate_integration_receipt(value.integration_receipt)
            self.assertEqual(receipt["disposition"], "identity_parent_not_eligible")
            self.assertEqual(receipt["model_slot_acquisition_delta"], 0)
            self.assertEqual(model.receipt()["acquisitions"], before)
            self.assertEqual(inner.requests, 2)
            self.assertEqual(value.result["prediction"], parent.result["prediction"])

    def test_isolation(self) -> None:
        target.validate_isolation()


if __name__ == "__main__":
    unittest.main()
