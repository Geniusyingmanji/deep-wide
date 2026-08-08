from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24855_v24854_rate_aware_quality as diagnosis  # noqa: E402


class V24855RateAwareQualityDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = diagnosis.build(now=1)

    def test_all_three_complete_rollouts_reconcile(self) -> None:
        self.assertTrue(self.value["diagnosis_valid"])
        self.assertEqual(self.value["findings"], [])
        self.assertTrue(all(self.value["checks"].values()))
        self.assertTrue(
            all(run["n"] == 220 for run in self.value["overall"]["runs"].values())
        )

    def test_transport_storm_is_eliminated(self) -> None:
        transport = self.value["transport"]
        self.assertEqual(transport["v24850_status_429_total"], 624)
        self.assertEqual(transport["v24854_status_429_total"], 0)
        self.assertEqual(transport["v24854_slot_timeout_total"], 0)
        self.assertEqual(transport["v24854_transport_failure_total"], 0)

    def test_provider_wait_is_mixed_into_legacy_latency_ceiling(self) -> None:
        mixture = self.value["pacing_latency_mixture"]
        self.assertEqual(mixture["v24800_latency_stop_count"], 2)
        self.assertEqual(mixture["v24850_latency_stop_count"], 2)
        self.assertEqual(mixture["v24854_latency_stop_count"], 27)
        self.assertEqual(mixture["pacing_mixed_stop_count"], 21)
        self.assertEqual(mixture["residual_slow_stop_count"], 6)
        self.assertTrue(mixture["all_v24854_stops_have_positive_provider_gate_wait"])

    def test_quality_gain_is_not_established(self) -> None:
        conclusions = self.value["conclusions"]
        self.assertTrue(conclusions["v24854_improved_composite_over_v24850"])
        self.assertFalse(conclusions["v24854_improved_exact_over_v24850"])
        self.assertFalse(conclusions["v24854_improved_composite_or_exact_over_v24800"])
        self.assertFalse(
            conclusions["v24854_pairwise_composite_interval_excludes_zero"]
        )
        for pair in self.value["overall"]["pairwise"].values():
            self.assertFalse(
                pair["paired_composite_bootstrap"]["interval_excludes_zero"]
            )

    def test_historical_cohorts_are_not_runtime_routes(self) -> None:
        self.assertFalse(
            self.value["boundary"][
                "historical_correctness_429_or_latency_cohort_authorized_as_runtime_route"
            ]
        )
        self.assertFalse(
            self.value["transport"]["v24850_old_429_cohort"][
                "historical_cohort_membership_for_runtime_routing"
            ]
        )
        self.assertFalse(
            self.value["pacing_latency_mixture"]["stop_cohort"][
                "historical_cohort_membership_for_runtime_routing"
            ]
        )

    def test_output_is_aggregate_only_and_content_safe(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(diagnosis.OPAQUE.search(encoded))
        self.assertIsNone(diagnosis.INSTANCE.search(encoded))
        self.assertIsNone(diagnosis.SECRET.search(encoded))
        self.assertNotIn("| Result |", encoded)

    def test_authorization_forbids_public_benchmark_and_sota(self) -> None:
        auth = self.value["authorization"]
        self.assertTrue(auth["pacing_aware_admission_adapter_build"])
        self.assertTrue(auth["fresh_shared_prefix_external_protocol_design"])
        self.assertFalse(auth["fresh_external_launch"])
        self.assertFalse(auth["new_public_dev64_or_exact220"])
        self.assertFalse(auth["sota_claim"])

    def test_published_artifact_replays_when_present(self) -> None:
        path = ROOT / diagnosis.OUTPUT
        if path.is_file():
            published = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(diagnosis.validate(published), published)


if __name__ == "__main__":
    unittest.main()
