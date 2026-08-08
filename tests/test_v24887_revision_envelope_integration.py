from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24860_coverage_revision_integration as frozen  # noqa: E402
from deepwide_agent import v24887_revision_envelope_integration as target  # noqa: E402
import test_v24860_coverage_revision_integration as core  # noqa: E402


def table(rows: int) -> str:
    return (
        "| Name | Date |\n| --- | --- |\n"
        + "\n".join(f"| R{index:04d} | {2000 + index} |" for index in range(rows))
    )


class V24887RevisionEnvelopeIntegrationTests(
    core.V24860CoverageRevisionIntegrationTests
):
    def test_513_parent_preserved_without_third_slot_effect(self) -> None:
        temporary, clock, inner, model, parent = self.build_parent(
            [core.PLAN, table(513), "must-not-be-consumed"]
        )
        self.addCleanup(temporary.cleanup)
        before_requests = inner.requests
        before_acquisitions = model.receipt()["acquisitions"]
        value = target.run_coverage_revision(
            core.task(),
            parent_result=parent.result,
            parent_model_slot_receipt=parent.model_slot_receipt,
            model=model,
            pages=core.pages_for(parent.result),
            limits=core.limits(),
            monotonic=clock,
        )
        receipt = target.validate_integration_receipt(value.integration_receipt)
        self.assertEqual(receipt["disposition"], "identity_parent_not_eligible")
        self.assertFalse(receipt["parent_eligible"])
        self.assertFalse(receipt["logical_revision_call_admitted"])
        self.assertEqual(receipt["provider_request_delta"], 0)
        self.assertEqual(receipt["model_slot_acquisition_delta"], 0)
        self.assertEqual(inner.requests, before_requests)
        self.assertEqual(model.receipt()["acquisitions"], before_acquisitions)
        self.assertEqual(value.result["prediction"], parent.result["prediction"])
        self.assertEqual(
            receipt["coverage_receipt"]["baseline_row_count"], 513
        )

    def test_isolation_keeps_frozen_bindings(self) -> None:
        target.validate_isolation()
        self.assertIsNot(target.run_coverage_revision, frozen.run_coverage_revision)


if __name__ == "__main__":
    unittest.main()
