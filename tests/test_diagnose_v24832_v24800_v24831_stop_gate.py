from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24832_v24800_v24831_stop_gate as target  # noqa: E402


class V24832StopGateDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build(now=1)

    def test_exact220_partitions_reconcile(self) -> None:
        self.assertEqual(self.value["overall"]["old"]["n"], 220)
        self.assertEqual(self.value["overall"]["new"]["n"], 220)
        self.assertEqual(
            sum(self.value["new_controller"]["decision_counts"].values()), 220
        )

    def test_stop_regresses_while_expand_improves(self) -> None:
        strata = self.value["paired_strata"]
        self.assertLess(
            strata["new_stop"]["delta"]["metrics"]["quality_composite"], 0
        )
        self.assertGreater(
            strata["new_expand"]["delta"]["metrics"]["quality_composite"], 0
        )
        self.assertLess(
            strata["new_stop"]["delta"]["retrieval"]["usable_pages"], 0
        )

    def test_mapping_failure_is_not_promoted_to_credit(self) -> None:
        conclusions = self.value["conclusions"]
        self.assertTrue(
            conclusions["mapping_failure_presence_is_not_a_monotone_quality_harm_signal"]
        )
        self.assertTrue(
            self.value["next_work"][
                "mapping_failure_alone_must_not_receive_credit_or_force_a_tuned_route"
            ]
        )

    def test_future_runtime_cannot_read_historical_scores(self) -> None:
        self.assertFalse(
            self.value["boundary"][
                "historical_score_or_stratum_authorized_as_future_runtime_input"
            ]
        )
        self.assertFalse(
            self.value["conclusions"][
                "historical_benchmark_metric_may_route_future_forward"
            ]
        )

    def test_only_external_design_is_authorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["transport_aware_controller_build"])
        self.assertTrue(authorization["fresh_benchmark_external_gate_design"])
        self.assertFalse(authorization["public_dev64"])
        self.assertFalse(authorization["public_exact220"])
        self.assertFalse(authorization["sota_claim"])

    def test_output_is_aggregate_only(self) -> None:
        encoded = json.dumps(self.value, sort_keys=True)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertNotIn('"question":', encoded.casefold())
        self.assertNotIn('"prediction":', encoded.casefold())
        self.assertNotIn("prediction_sha256", encoded)

    def test_rebuild_validation_is_exact(self) -> None:
        self.assertEqual(target.validate(self.value), self.value)


if __name__ == "__main__":
    unittest.main()
