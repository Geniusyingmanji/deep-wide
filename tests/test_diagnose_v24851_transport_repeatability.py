from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v24850_v24800_replication_exact220_contract as contract,
)
from scripts import (  # noqa: E402
    diagnose_v24851_v24800_v24807_v24850_transport_repeatability as target,
)


class V24851TransportRepeatabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build(now=1786164000)

    def test_three_complete_rollouts_reconcile(self) -> None:
        runs = self.value["overall"]["runs"]
        self.assertEqual(
            {name: runs[name]["whole_table_successes"] for name in runs},
            {"v24800": 8, "v24807": 8, "v24850": 7},
        )
        self.assertAlmostEqual(
            runs["v24850"]["metrics"]["quality_composite"],
            0.44218659855854536,
        )
        self.assertEqual(sum(runs[name]["n"] for name in runs), 660)

    def test_prediction_and_exact_stability_are_low(self) -> None:
        overall = self.value["overall"]
        self.assertEqual(
            overall["distinct_prediction_hash_count_distribution"],
            {"1": 7, "2": 11, "3": 202},
        )
        self.assertEqual(
            overall["whole_table_success_run_frequency"],
            {"0": 209, "1": 4, "2": 2, "3": 5},
        )
        self.assertFalse(
            self.value["conclusions"]["same_policy_predictions_are_byte_stable"]
        )

    def test_v24850_429_storm_is_full_key_rotation(self) -> None:
        storm = self.value["transport"]["v24850_provider_429_storm"]
        self.assertEqual(storm["rate_limited_task_count"], 15)
        self.assertEqual(storm["non_rate_limited_task_count"], 205)
        self.assertEqual(storm["status_429_total"], 624)
        self.assertEqual(storm["rate_limited_failed_query_count"], 52)
        self.assertEqual(
            storm["status_429_count_per_rate_limited_task"],
            {"24": 4, "48": 11},
        )
        self.assertEqual(storm["status_429_per_failed_query"], 12)
        self.assertTrue(
            storm["every_rate_limited_failed_query_rotated_across_full_key_cap"]
        )

    def test_429_cohort_is_descriptive_and_not_a_route(self) -> None:
        cohort = self.value["transport"][
            "v24850_429_cohort_postfreeze_aggregate"
        ]
        self.assertEqual(cohort["n"], 15)
        self.assertEqual(
            {
                name: cohort["metrics_by_run"][name]["whole_table_successes"]
                for name in target.RUNS
            },
            {"v24800": 2, "v24807": 1, "v24850": 0},
        )
        self.assertAlmostEqual(
            cohort["mechanism_by_run"]["v24850"]["usable_pages"], 1.0
        )
        self.assertFalse(cohort["historical_cohort_membership_for_runtime_routing"])
        self.assertFalse(cohort["causal_effect_of_429_claimed"])

    def test_non429_tasks_retain_all_v24850_exact_successes(self) -> None:
        cohort = self.value["transport"][
            "v24850_non429_cohort_postfreeze_aggregate"
        ]
        self.assertEqual(cohort["n"], 205)
        self.assertEqual(
            cohort["metrics_by_run"]["v24850"]["whole_table_successes"], 7
        )
        self.assertGreater(
            cohort["mechanism_by_run"]["v24850"]["projected_chars"], 30_000
        )

    def test_pairwise_bootstraps_keep_independent_runs_noncausal(self) -> None:
        pairs = self.value["overall"]["pairwise"]
        self.assertEqual(
            pairs["v24850_minus_v24800"]["delta"]["whole_table_successes"], -1
        )
        self.assertEqual(
            pairs["v24850_minus_v24807"]["delta"]["whole_table_successes"], -1
        )
        self.assertFalse(
            self.value["conclusions"]["fixed_budget_or_entropy_causal_effect_established"]
        )

    def test_output_is_aggregate_only_and_label_blind(self) -> None:
        boundary = self.value["boundary"]
        self.assertFalse(boundary["task_identifier_or_per_task_metric_emitted"])
        self.assertFalse(
            boundary[
                "historical_metric_correctness_or_429_cohort_authorized_as_future_runtime_route"
            ]
        )
        self.assertFalse(boundary["network_model_search_fetch_or_evaluator_called"])
        encoded = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.INSTANCE.search(encoded))
        self.assertIsNone(target.SECRET.search(encoded))

    def test_tamper_fails_even_when_resealed(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["authorization"]["new_public_exact220"] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate(changed, rebuild=False)

    def test_published_artifact_replays_when_present(self) -> None:
        path = ROOT / target.OUTPUT
        if not path.is_file():
            self.skipTest("V2.48.51 publication has not been created")
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(value, target.validate(value))


if __name__ == "__main__":
    unittest.main()
