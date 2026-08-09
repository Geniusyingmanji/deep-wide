from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import evaluate_v25027_clue_resolved_external as target  # noqa: E402


class ClueResolvedEvaluatorTests(unittest.TestCase):
    def test_mapping_is_fixed_unique_and_evaluator_only(self) -> None:
        vector = target._mapping()
        self.assertEqual(len(vector), 20)
        self.assertEqual(len(set(vector)), 20)
        self.assertEqual(vector[0], ".in")
        self.assertEqual(vector[-1], ".la")

    def test_parse_iana_page_selects_only_frozen_vector(self) -> None:
        rows = "".join(
            f"<tr><td>{tld}</td><td>country-code</td><td>Manager {index}</td></tr>"
            for index, tld in enumerate(target._mapping())
        )
        # html_to_text produces a table-like pipe representation from a proper table.
        gold = target.parse_iana_page(f"<html><table>{rows}</table></html>")
        self.assertEqual(tuple(gold), target._mapping())

    def test_prediction_metrics_exact_and_wrong(self) -> None:
        gold = {"Domain": ".in", "Type": "country-code", "TLD Manager": "Registry"}
        exact = target.evaluate_prediction(
            "| Domain | Type | TLD Manager |\n|---|---|---|\n| .in | country-code | Registry |",
            gold,
        )
        wrong = target.evaluate_prediction(
            "| Domain | Type | TLD Manager |\n|---|---|---|\n| .in | country-code | Wrong |",
            gold,
        )
        self.assertEqual(exact["exact_table_success"], 1)
        self.assertEqual(wrong["exact_table_success"], 0)
        self.assertGreater(exact["composite"], wrong["composite"])


if __name__ == "__main__":
    unittest.main()
