from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24405_structured_label_projection import (  # noqa: E402
    build_structured_label_projection,
)
from deepwide_agent.v24421_structured_projection_observability import (  # noqa: E402
    REASONS,
    build_projection_observability,
    validate_projection_observability,
)


def baseline(column: str = "Founding year") -> str:
    return (
        "```markdown\n"
        f"| Company | {column} |\n"
        "| --- | --- |\n"
        "| Alpha | Unknown |\n"
        "```"
    )


def catalog(content: str, *, column: str = "Founding year") -> dict:
    return build_structured_label_projection(
        baseline(column),
        [{"host": "one.example", "content": content, "fetch_integrity": True}],
    )


def observed(content: str, *, column: str = "Founding year") -> dict:
    current = catalog(content, column=column)
    return build_projection_observability(current)


class V24421StructuredProjectionObservabilityTests(unittest.TestCase):
    def assert_reason(self, value: dict, expected: str) -> None:
        self.assertEqual(value["page_target_pair_count"], 1)
        self.assertEqual(sum(value["reason_counts"].values()), 1)
        self.assertEqual(value["reason_counts"][expected], 1)
        for name in REASONS:
            if name != expected:
                self.assertEqual(value["reason_counts"][name], 0)

    def test_five_reasons_are_mutually_exclusive(self) -> None:
        cases = (
            ("Alpha\nFounded | 2007", "Revenue", "unsupported_column_kind"),
            (
                "Alpha was founded in 2007.",
                "Founding year",
                "exact_structured_entity_anchor_absent",
            ),
            (
                "Alpha\nHeadquarters | Example City",
                "Founding year",
                "exact_label_absent_in_entity_scope",
            ),
            (
                "Alpha\nFounded | Unknown",
                "Founding year",
                "exact_label_value_year_absent",
            ),
            (
                "Alpha\nFounded | 2007",
                "Founding year",
                "structured_projection_emitted",
            ),
        )
        for content, column, expected in cases:
            with self.subTest(expected=expected):
                self.assert_reason(observed(content, column=column), expected)

    def test_table_projection_and_duplicate_legacy_are_counted(self) -> None:
        current = catalog(
            "Alpha was founded in 2007.\n\n"
            "Company | Founding year\n--- | ---\nAlpha | 2007"
        )
        value = build_projection_observability(current)
        self.assertEqual(value["structured_projection_pair_count"], 1)
        self.assertEqual(value["structured_projection_count"], 1)
        self.assertEqual(value["structured_observation_count"], 1)
        self.assertEqual(value["novel_structured_observation_count"], 0)
        self.assertEqual(value["structured_observation_duplicate_legacy_count"], 1)

    def test_multiple_pages_and_targets_conserve_pair_partition(self) -> None:
        base = (
            "```markdown\n| Company | Founding year |\n| --- | --- |\n"
            "| Alpha | Unknown |\n| Beta | Unknown |\n```"
        )
        current = build_structured_label_projection(
            base,
            [
                {
                    "host": "one.example",
                    "content": "Alpha\nFounded | 2007",
                    "fetch_integrity": True,
                },
                {
                    "host": "two.example",
                    "content": "Beta\nFounded | Unknown",
                    "fetch_integrity": True,
                },
            ],
        )
        value = build_projection_observability(current)
        self.assertEqual(value["page_count"], 2)
        self.assertEqual(value["selected_target_count"], 2)
        self.assertEqual(value["page_target_pair_count"], 4)
        self.assertEqual(sum(value["reason_counts"].values()), 4)
        self.assertEqual(value["reason_counts"]["structured_projection_emitted"], 1)
        self.assertEqual(value["reason_counts"]["exact_label_value_year_absent"], 1)
        self.assertEqual(
            value["reason_counts"]["exact_structured_entity_anchor_absent"], 2
        )

    def test_unselected_entity_still_delimits_selected_entity_scope(self) -> None:
        base = (
            "```markdown\n| Company | Founding year |\n| --- | --- |\n"
            "| Alpha | Unknown |\n| Beta | Unknown |\n```"
        )
        current = build_structured_label_projection(
            base,
            [
                {
                    "host": "one.example",
                    "content": "Alpha\nBeta\nFounded | 2007",
                    "fetch_integrity": True,
                }
            ],
            selected_identities={("alpha", "foundingyear")},
        )
        value = build_projection_observability(current)
        self.assertEqual(value["selected_target_count"], 1)
        self.assertEqual(
            value["reason_counts"]["exact_label_absent_in_entity_scope"], 1
        )
        self.assertEqual(value["structured_projection_count"], 0)

    def test_receipt_contains_counts_only_and_replay_rejects_tamper(self) -> None:
        current = catalog("Alpha\nFounded | 2007")
        value = build_projection_observability(current)
        encoded = json.dumps(value, sort_keys=True)
        for private in ("Alpha", "one.example", "2007", "http"):
            self.assertNotIn(private, encoded)
        self.assertEqual(
            [name for name in value if "sha256" in name], ["receipt_sha256"]
        )
        altered = copy.deepcopy(value)
        altered["reason_counts"]["structured_projection_emitted"] = 0
        altered["reason_counts"]["exact_label_value_year_absent"] = 1
        with self.assertRaises(ValueError):
            validate_projection_observability(altered, catalog=current)

    def test_privileged_claim_tamper_fails_closed(self) -> None:
        current = catalog("Alpha\nFounded | 2007")
        value = build_projection_observability(current)
        altered = copy.deepcopy(value)
        altered[
            "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
        ] = True
        with self.assertRaises(ValueError):
            validate_projection_observability(altered)

    def test_json_round_trip_does_not_depend_on_reason_key_order(self) -> None:
        current = catalog("Alpha\nFounded | 2007")
        value = build_projection_observability(current)
        decoded = json.loads(json.dumps(value, sort_keys=True))
        validate_projection_observability(decoded, catalog=current)


if __name__ == "__main__":
    unittest.main()
