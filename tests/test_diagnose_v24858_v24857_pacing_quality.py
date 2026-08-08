from __future__ import annotations

import copy
import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24858_v24857_pacing_quality as diagnosis  # noqa: E402


class V24858PacingQualityDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = diagnosis.build(now=1_786_172_800)

    def test_all_complete_rollouts_reconcile(self) -> None:
        self.assertTrue(self.value["diagnosis_valid"])
        self.assertEqual(self.value["findings"], [])
        self.assertTrue(all(self.value["checks"].values()))
        self.assertTrue(
            all(
                run["n"] == 220
                for run in self.value["overall"]["runs"].values()
            )
        )

    def test_v24857_is_observed_best_but_overall_intervals_cross_zero(self) -> None:
        runs = self.value["overall"]["runs"]
        self.assertEqual(runs["v24857"]["whole_table_successes"], 9)
        self.assertGreater(
            runs["v24857"]["metrics"]["quality_composite"],
            runs["v24800"]["metrics"]["quality_composite"],
        )
        rank = self.value["overall"]["recorded_complete_rollout_rank"]
        self.assertGreaterEqual(rank["recorded_complete_rollouts"], 18)
        self.assertEqual(rank["candidate_exact_rank"], 1)
        self.assertEqual(rank["candidate_composite_rank"], 1)
        for pair in self.value["overall"]["v24857_pairwise"].values():
            self.assertFalse(
                pair["paired_composite_bootstrap"]["interval_excludes_zero"]
            )
            self.assertFalse(pair["paired_exact_test"]["significant_at_0_05"])

    def test_pacing_mechanism_changed_nineteen_tasks_cleanly(self) -> None:
        mechanism = self.value["pacing_mechanism"]
        self.assertEqual(mechanism["legacy_latency_stop_tasks"], 26)
        self.assertEqual(mechanism["pacing_aware_latency_stop_tasks"], 7)
        self.assertEqual(mechanism["decision_changed_tasks"], 19)
        self.assertEqual(mechanism["provider_attempts"], 867)
        self.assertEqual(mechanism["provider_attempts"], mechanism["provider_2xx"])
        self.assertEqual(mechanism["provider_429"], 0)
        self.assertEqual(mechanism["provider_transport_failures"], 0)

    def test_exact_gain_did_not_come_from_changed_admission_cohort(self) -> None:
        cohort = self.value["pacing_mechanism"]["decision_change_cohort"]
        self.assertEqual(cohort["n"], 19)
        self.assertEqual(
            cohort["whole_table_successes_by_run"],
            {"v24800": 0, "v24850": 0, "v24854": 0, "v24857": 0},
        )
        self.assertFalse(
            self.value["conclusions"]["observed_exact_gain_attributable_to_pacing"]
        )

    def test_changed_cohort_composite_signal_is_not_causal(self) -> None:
        conclusions = self.value["conclusions"]
        self.assertTrue(
            conclusions[
                "decision_change_cohort_composite_interval_excludes_zero_vs_v24854"
            ]
        )
        self.assertTrue(
            conclusions[
                "decision_change_cohort_posthoc_independent_rollout_cannot_establish_causality"
            ]
        )
        self.assertFalse(self.value["boundary"]["causal_effect_claimed"])

    def test_report_is_aggregate_only_and_content_safe(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))
        self.assertNotIn("deep2wide_result", encoded)
        self.assertNotIn("| Result |", encoded)
        self.assertFalse(
            self.value["boundary"]
            ["historical_score_transition_or_cohort_authorized_as_future_runtime_input"]
        )

    def test_successor_targets_conversion_not_more_budget(self) -> None:
        work = self.value["next_work"]
        self.assertEqual(
            work["primary_bottleneck"],
            "evidence_to_complete_table_conversion_not_raw_retrieval_admission",
        )
        self.assertIn(
            "same discovered lead vector and raw page byte prefix for both arms",
            work["required_external_gate_controls"],
        )
        self.assertFalse(work["public_exact220_authorized_after_this_diagnosis"])

    def test_authorization_forbids_benchmark_and_sota(self) -> None:
        auth = self.value["authorization"]
        self.assertTrue(auth["coverage_utility_selector_build"])
        self.assertTrue(auth["fresh_benchmark_external_shared_prefix_gate_design"])
        self.assertFalse(auth["fresh_external_activation_or_launch"])
        self.assertFalse(auth["public_dev64_or_exact220"])
        self.assertFalse(auth["historical_cohort_runtime_routing"])
        self.assertFalse(auth["sota_claim"])

    def test_resealed_tamper_fails(self) -> None:
        altered = copy.deepcopy(self.value)
        altered["pacing_mechanism"]["decision_changed_tasks"] += 1
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = diagnosis.contract.payload_sha256(
            altered
        )
        with self.assertRaises(RuntimeError):
            diagnosis.validate(altered)

    def test_published_artifact_replays_when_present(self) -> None:
        path = ROOT / diagnosis.OUTPUT
        if path.is_file():
            published = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(diagnosis.validate(published), published)


if __name__ == "__main__":
    unittest.main()
