from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import finalize_v24630_exact220 as finalizer  # noqa: E402
from scripts import preregister_v24630_exact220_evaluator as prereg  # noqa: E402


class V24630Exact220EvaluatorTests(unittest.TestCase):
    def test_fixed_32_way_partitions_cover_220_once(self) -> None:
        partitions = finalizer.fixed_partitions()
        self.assertEqual(len(partitions), 32)
        self.assertEqual(partitions[0][0], 0)
        self.assertEqual(partitions[-1][1], 220)
        values = [index for start, end in partitions for index in range(start, end)]
        self.assertEqual(values, list(range(220)))
        self.assertEqual(sorted({end - start for start, end in partitions}), [6, 7])

    def test_protocol_opens_evaluator_only_after_exact220_barrier(self) -> None:
        value = prereg.build_protocol(ROOT, now=1)
        self.assertEqual(value["selected"], 220)
        self.assertEqual(value["evaluator_workers"], 32)
        self.assertEqual(value["forward_barrier"]["terminal_predictions"], 220)
        self.assertFalse(value["forward_barrier"]["mapping_or_evaluator_opened_during_forward"])
        self.assertTrue(
            value["evaluation_contract"][
                "all_220_predictions_frozen_before_mapping_query_answer_or_evaluator_open"
            ]
        )
        self.assertTrue(
            value["evaluation_contract"][
                "official_evaluator_on_every_frozen_prediction_exactly_once"
            ]
        )
        self.assertFalse(value["authorization"]["selective_retry_or_revaluation"])
        self.assertFalse(value["authorization"]["additional_rollout_avg4_leaderboard_or_sota"])

    def test_comparison_delta_is_exact(self) -> None:
        current = {
            "whole_table_successes": 8,
            "score": 8 / 220,
            "quality_composite": 0.45,
            "entity_acc": 0.7,
            "f1_by_row": 0.2,
            "f1_by_item": 0.4,
            "column_f1": 0.5,
        }
        value = finalizer._comparison(
            current,
            ROOT / "results/v24267_exact220_result_v1_20260802.json",
            "V2.42.67",
        )
        self.assertEqual(value["whole_table_success_delta"], 1)
        self.assertAlmostEqual(value["score_delta"], 1 / 220)


if __name__ == "__main__":
    unittest.main()
