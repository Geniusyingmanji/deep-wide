from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24322_v24320_paired_dev64 as diagnosis  # noqa: E402


class V24322DiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = diagnosis.build(ROOT, now=1)

    def test_rebuild_is_content_free_and_sealed(self) -> None:
        diagnosis.validate(self.value)
        serialized = json.dumps(self.value, ensure_ascii=False)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", serialized))
        for forbidden in ("deep2wide_result_", '"prediction":', '"question":'):
            self.assertNotIn(forbidden, serialized)
        self.assertTrue(
            self.value["source_policy"][
                "offline_after_both_arm_prediction_and_evaluator_freeze"
            ]
        )

    def test_reserve_and_route_discordance_localize_loss(self) -> None:
        by_name = {row["name"]: row for row in self.value["paired_strata"]}
        self.assertEqual(by_name["candidate_reserved_stage_executed"]["task_count"], 13)
        self.assertLess(
            by_name["candidate_reserved_stage_executed"]["mean_composite_delta"],
            by_name["candidate_reserved_stage_not_executed"]["mean_composite_delta"],
        )
        self.assertAlmostEqual(
            by_name["controller_baseline_stop_candidate_stop"]["mean_composite_delta"],
            0.0012199007366752203,
        )
        self.assertEqual(
            self.value["mechanism_facts"]["controller_route_discordant_tasks"], 15
        )

    def test_successor_is_shared_prefix_design_only(self) -> None:
        requirements = self.value["successor_requirements"]
        self.assertTrue(requirements["shared_visible_only_plan_and_first_wave"])
        self.assertTrue(requirements["shared_first_six_page_evidence_prefix"])
        self.assertTrue(
            requirements["reliability_weighted_cell_conditional_information_gain"]
        )
        self.assertFalse(self.value["authorization"]["successor_launch"])
        self.assertFalse(self.value["authorization"]["additional_dev64_or_exact220"])


if __name__ == "__main__":
    unittest.main()
