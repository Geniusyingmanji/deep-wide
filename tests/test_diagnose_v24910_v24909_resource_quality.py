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

from scripts import diagnose_v24910_v24909_resource_quality as diagnosis  # noqa: E402


class V24910ResourceQualityDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = diagnosis.build(now=1_786_207_600)

    def test_complete_frozen_chains_reconcile(self) -> None:
        self.assertTrue(self.value["diagnosis_valid"])
        self.assertEqual(self.value["findings"], [])
        self.assertTrue(all(self.value["checks"].values()))
        self.assertTrue(
            self.value["boundary"]
            ["all_three_prediction_and_evaluator_chains_terminal_before_diagnosis"]
        )

    def test_quality_ranking_is_exact(self) -> None:
        runs = self.value["runs"]
        self.assertEqual(runs["v24906"]["quality"]["whole_table_successes"], 4)
        self.assertEqual(runs["v24909"]["quality"]["whole_table_successes"], 7)
        self.assertEqual(runs["v24857"]["quality"]["whole_table_successes"], 9)
        self.assertTrue(
            self.value["conclusions"]
            ["v24909_below_v24857_exact_and_composite"]
        )

    def test_fixed_budget_keyless_mechanism_engaged(self) -> None:
        before = self.value["runs"]["v24906"]["mechanism"]
        after = self.value["runs"]["v24909"]["mechanism"]
        self.assertGreater(after["decision_counts"]["expand"], before["decision_counts"]["expand"])
        self.assertGreater(
            after["totals_and_means"]["fetches_attempted"],
            before["totals_and_means"]["fetches_attempted"],
        )

    def test_keyless_cost_is_search_token_dominated(self) -> None:
        values = self.value["runs"]["v24909"]["mechanism"]["totals_and_means"]
        self.assertEqual(values["search_total_tokens"], 8_547_691.0)
        self.assertGreater(values["search_token_share"], 0.75)
        self.assertTrue(
            self.value["conclusions"]
            ["v24909_search_tokens_are_majority_of_system_tokens"]
        )

    def test_tavily_frontier_has_more_usable_pages_and_hosts(self) -> None:
        keyless = self.value["runs"]["v24909"]["mechanism"]["totals_and_means"]
        tavily = self.value["runs"]["v24857"]["mechanism"]["totals_and_means"]
        self.assertLess(keyless["usable_pages"], tavily["usable_pages"])
        self.assertLess(keyless["unique_hosts"], tavily["unique_hosts"])

    def test_report_is_aggregate_only_and_content_safe(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))
        self.assertNotIn("| Result |", encoded)
        self.assertFalse(
            self.value["boundary"]
            ["historical_correctness_or_score_authorized_as_future_runtime_input"]
        )

    def test_successor_requires_external_shared_prefix_gate(self) -> None:
        gate = self.value["next_gate"]
        self.assertTrue(gate["same_retrieved_page_byte_prefix_for_baseline_and_candidate"])
        self.assertTrue(gate["benchmark_external_shared_prefix_quality_gate_required"])
        self.assertFalse(self.value["authorization"]["public_dev64_or_exact220"])

    def test_resealed_tamper_fails(self) -> None:
        altered = copy.deepcopy(self.value)
        altered["runs"]["v24909"]["quality"]["whole_table_successes"] = 8
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = diagnosis.contract.payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            diagnosis.validate(altered)

    def test_published_artifact_replays_when_present(self) -> None:
        path = ROOT / diagnosis.OUTPUT
        if path.is_file():
            published = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(diagnosis.validate(published), published)


if __name__ == "__main__":
    unittest.main()
