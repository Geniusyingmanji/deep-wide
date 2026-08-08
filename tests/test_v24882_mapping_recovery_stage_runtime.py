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

from deepwide_agent import v24882_mapping_recovery_stage_runtime as target  # noqa: E402
from test_v24875_keyless_coverage_child_runtime import (  # noqa: E402
    MeteredFullSearch,
    V24875KeylessCoverageChildRuntimeTests,
)
import test_v24860_coverage_revision_integration as core_test  # noqa: E402


class V24882MappingRecoveryStageRuntimeTests(unittest.TestCase):
    def test_stage_receipts_are_content_free_and_ordered(self) -> None:
        for index, stage in enumerate(target.STAGES, start=1):
            value = target.build_stage_receipt(stage)
            self.assertEqual(value["stage_ordinal"], index)
            self.assertFalse(
                value[
                    "contains_question_query_url_host_page_prediction_candidate_value_answer_opaque_id_or_credential"
                ]
            )

    def test_real_synthetic_child_finishes_at_bundle_committed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory = output / "task"
            directory.mkdir()
            helper = V24875KeylessCoverageChildRuntimeTests()
            clock, _inner, model, search = helper.clients(output, MeteredFullSearch)
            target.run_child_bundle(
                output_root=output,
                directory=directory,
                task=core_test.task(),
                model=model,
                search=search,
                limits=core_test.limits(),
                expected_model_slot_cap=2,
                monotonic=clock,
            )
            stage = target.validate_stage_receipt(
                json.loads((directory / target.STAGE_NAME).read_text())
            )
            self.assertEqual(stage["stage"], "bundle_committed")

    def test_privileged_input_fails_before_effect_with_visible_stage_absent(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory = output / "task"
            directory.mkdir()
            helper = V24875KeylessCoverageChildRuntimeTests()
            clock, inner, model, search = helper.clients(output, MeteredFullSearch)
            with self.assertRaises(ValueError):
                target.run_child_bundle(
                    output_root=output,
                    directory=directory,
                    task={**core_test.task(), "question_type": "forbidden"},
                    model=model,
                    search=search,
                    limits=core_test.limits(),
                    expected_model_slot_cap=2,
                    monotonic=clock,
                )
            self.assertEqual(inner.requests, 0)
            self.assertEqual(search.calls, 0)
            self.assertFalse((directory / target.STAGE_NAME).exists())

    def test_stage_cannot_move_backwards(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            path = Path(temporary) / target.STAGE_NAME
            target._atomic_stage(
                path, target.build_stage_receipt("parent_runtime_entered")
            )
            with self.assertRaises(ValueError):
                target._atomic_stage(
                    path, target.build_stage_receipt("visible_input_validated")
                )


if __name__ == "__main__":
    unittest.main()
