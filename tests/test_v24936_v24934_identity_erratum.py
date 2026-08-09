from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24934_contextual_record_external_contract as contract  # noqa: E402
from scripts import evaluate_v24923_target_value_external as old  # noqa: E402
from scripts import evaluate_v24936_v24934_identity_erratum as erratum  # noqa: E402


ENTITIES = [("Alpha Republic", "ALP"), ("Beta Islands", "BET")]
COLUMNS = contract.visible_columns()


def table(first: str = "Alpha Republic [ALP]", second: str = "Beta Islands [BET]") -> str:
    return (
        "| " + " | ".join(COLUMNS) + " |\n"
        "|---|---:|---:|\n"
        f"| {first} | 101 | 201 |\n"
        f"| {second} | 102 | 202 |"
    )


GOLD = [
    {"Country": "Alpha Republic", COLUMNS[1]: "101", COLUMNS[2]: "201"},
    {"Country": "Beta Islands", COLUMNS[1]: "102", COLUMNS[2]: "202"},
]


class V24936IdentityErratumTests(unittest.TestCase):
    def test_accepts_exact_visible_name(self) -> None:
        self.assertEqual(
            erratum.canonical_visible_identity("Alpha Republic", ENTITIES),
            erratum._norm("Alpha Republic"),
        )

    def test_accepts_matching_visible_name_iso3(self) -> None:
        self.assertEqual(
            erratum.canonical_visible_identity("Alpha Republic [ALP]", ENTITIES),
            erratum._norm("Alpha Republic"),
        )

    def test_rejects_wrong_iso3(self) -> None:
        self.assertIsNone(
            erratum.canonical_visible_identity("Alpha Republic [BET]", ENTITIES)
        )

    def test_rejects_nonvisible_identity(self) -> None:
        self.assertIsNone(erratum.canonical_visible_identity("Gamma", ENTITIES))

    def test_old_evaluator_reproduces_tagged_identity_zero(self) -> None:
        metrics = old.evaluate_prediction(table(), GOLD)
        self.assertEqual(metrics["entity_recall"], 0.0)
        self.assertEqual(metrics["exact_table_success"], 0)

    def test_corrected_evaluator_recovers_complete_table(self) -> None:
        metrics = erratum.evaluate_prediction(table(), GOLD, ENTITIES)
        self.assertEqual(metrics["entity_recall"], 1.0)
        self.assertEqual(metrics["row_f1"], 1.0)
        self.assertEqual(metrics["item_f1"], 1.0)
        self.assertEqual(metrics["exact_table_success"], 1)

    def test_wrong_iso3_cannot_receive_entity_or_item_credit(self) -> None:
        metrics = erratum.evaluate_prediction(
            table(first="Alpha Republic [BET]"), GOLD, ENTITIES
        )
        self.assertEqual(metrics["entity_recall"], 0.5)
        self.assertLess(metrics["item_f1"], 1.0)
        self.assertEqual(metrics["exact_table_success"], 0)

    def test_duplicate_canonical_identity_is_not_exact(self) -> None:
        metrics = erratum.evaluate_prediction(
            table(second="Alpha Republic"), GOLD, ENTITIES
        )
        self.assertEqual(metrics["exact_table_success"], 0)


if __name__ == "__main__":
    unittest.main()
