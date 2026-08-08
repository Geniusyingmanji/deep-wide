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

from deepwide_agent import v24879_mapping_recovery_effect_bundle as frozen  # noqa: E402
from deepwide_agent import v24889_revision_envelope_runtime as runtime  # noqa: E402
from deepwide_agent import v24890_revision_envelope_mapping_bundle as target  # noqa: E402
import test_v24860_coverage_revision_integration as core  # noqa: E402
from test_v24879_mapping_recovery_effect_bundle import (  # noqa: E402
    MappingRecoveryThinSearch,
    V24879MappingRecoveryEffectBundleTests,
)
from test_v24875_keyless_coverage_child_runtime import (  # noqa: E402
    MeteredFullSearch,
    V24875KeylessCoverageChildRuntimeTests,
    _MeteredMixin,
)


class MeteredMappingRecoverySearch(_MeteredMixin, MappingRecoveryThinSearch):
    pass


def table(rows: int) -> str:
    return (
        "| Name | Date |\n| --- | --- |\n"
        + "\n".join(f"| R{index:04d} | {2000 + index} |" for index in range(rows))
    )


class V24890RevisionEnvelopeMappingBundleTests(unittest.TestCase):
    def _write(self, output: Path, search_cls, *, rows: int | None = None):
        helper = V24875KeylessCoverageChildRuntimeTests()
        clock, inner, model, search = helper.clients(output, search_cls)
        if rows is not None:
            inner.values = [core.PLAN, table(rows), "must-not-be-consumed"]
        outcome = runtime.run_v24889_task(
            core.task(),
            arm="baseline",
            model=model,
            search=search,
            limits=core.limits(),
            monotonic=clock,
        )
        directory = output / "task"
        directory.mkdir()
        target.write_bundle(
            output_root=output,
            directory=directory,
            outcome=outcome,
            status_counts=search.status_counts,
            transport_failures=search.transport_failures,
            hard_total_wall_timeouts=search.hard_total_wall_timeouts,
            expected_model_slot_cap=2,
        )
        return directory, inner, model, outcome

    def test_mapping_recovery_bundle_round_trip(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory, _inner, _model, _outcome = self._write(
                output, MeteredMappingRecoverySearch
            )
            target.validate_bundle(
                output_root=output,
                directory=directory,
                expected_model_slot_cap=2,
            )

    def test_513_row_parent_round_trips_without_third_slot_or_truncation(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory, inner, model, outcome = self._write(
                output, MeteredFullSearch, rows=513
            )
            envelope = json.loads(
                (directory / target.RESULT_NAME).read_text(encoding="utf-8")
            )
            receipt = envelope["coverage_revision_receipt"]
            self.assertEqual(receipt["disposition"], "identity_parent_not_eligible")
            self.assertEqual(receipt["model_slot_acquisition_delta"], 0)
            self.assertEqual(inner.requests, 2)
            self.assertEqual(model.receipt()["acquisitions"], 2)
            parent_prediction = outcome.result["parent_result"]["prediction"]
            self.assertEqual(outcome.result["prediction"], parent_prediction)
            self.assertEqual(envelope["result"]["prediction"], parent_prediction)
            self.assertEqual(parent_prediction.count("\n| R"), 513)
            self.assertEqual(
                receipt["coverage_receipt"]["baseline_row_count"], 513
            )

    def test_isolation(self) -> None:
        target.validate_isolation()
        self.assertIsNot(target.validate_bundle, frozen.validate_bundle)


if __name__ == "__main__":
    unittest.main()
