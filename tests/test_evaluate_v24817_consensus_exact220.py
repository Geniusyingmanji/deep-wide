from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import evaluate_v24817_consensus_exact220 as target  # noqa: E402


class V24817EvaluatorTests(unittest.TestCase):
    def test_fixed_partitions_cover_220_once(self):
        parts = target.fixed_partitions()
        self.assertEqual(len(parts), 32)
        self.assertEqual(parts[0][0], 0)
        self.assertEqual(parts[-1][1], 220)
        self.assertEqual(sum(end - start for start, end in parts), 220)

    def test_claims_are_explicitly_posthoc(self):
        self.assertTrue(target.RESULT_CLAIMS["public_exact220_posthoc_three_rollout_ensemble"])
        self.assertTrue(target.RESULT_CLAIMS["source_rollouts_previously_evaluated"])
        self.assertFalse(target.RESULT_CLAIMS["unseen_or_held_out"])
        self.assertFalse(target.RESULT_CLAIMS["sota"])

    def test_forward_barrier_is_complete_before_evaluator(self):
        barrier = target._barrier()
        self.assertEqual(len(barrier["runtime_rows"]), 220)
        self.assertFalse(barrier["freeze"]["mapping_gold_or_evaluator_opened_or_hashed"])


if __name__ == "__main__": unittest.main()
