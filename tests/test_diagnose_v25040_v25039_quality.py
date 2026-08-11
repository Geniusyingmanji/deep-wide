from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25040_v25039_quality as diagnosis  # noqa: E402


class V25040V25039DiagnosisTests(unittest.TestCase):
    def test_frozen_paired_diagnosis_recomputes_expected_counts(self) -> None:
        value = diagnosis.validate(
            diagnosis.build(now=1, require_clean=False)
        )
        self.assertEqual(value["counts"]["prediction_changed"], 4)
        self.assertEqual(value["counts"]["candidate_item_gain"], 1)
        self.assertEqual(value["counts"]["candidate_item_loss"], 3)
        self.assertEqual(
            value["candidate_minus_control_correct_field_counts"],
            {
                "latest_version": -1,
                "latest_release_date": -1,
                "requires_python": 0,
            },
        )
        self.assertEqual(
            value["network_model_search_fetch_or_evaluator_calls"], 0
        )


if __name__ == "__main__":
    unittest.main()
