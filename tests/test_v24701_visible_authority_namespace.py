from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24701_visible_authority_namespace import (  # noqa: E402
    validate_signature,
    visible_authority_signature,
)


class V24701VisibleAuthorityTests(unittest.TestCase):
    def test_unique_visible_namespace_and_year_are_eligible(self) -> None:
        value = visible_authority_signature(
            "Using World Bank data for 2023, output a Markdown table with the columns: Country | Population"
        )
        validate_signature(value)
        self.assertEqual(value["unique_namespace"], "world_bank")
        self.assertTrue(value["adapter_route_eligible"])

    def test_who_literal_is_not_a_substring_match(self) -> None:
        value = visible_authority_signature(
            "Show whoever appears in 2023. The column names are: Name, Date."
        )
        self.assertEqual(value["namespace_count"], 0)
        self.assertFalse(value["adapter_route_eligible"])

    def test_ambiguous_namespaces_fail_closed(self) -> None:
        value = visible_authority_signature(
            "Compare WHO and World Bank in 2023. The column names are: Source, Value."
        )
        self.assertEqual(value["namespace_count"], 2)
        self.assertIsNone(value["unique_namespace"])
        self.assertFalse(value["adapter_route_eligible"])

    def test_namespace_without_schema_is_not_eligible(self) -> None:
        value = visible_authority_signature("Read Wikipedia and answer about 2020.")
        self.assertEqual(value["unique_namespace"], "wikipedia")
        self.assertFalse(value["adapter_route_eligible"])

    def test_address_column_can_replace_visible_year(self) -> None:
        value = visible_authority_signature(
            "Use GitHub. Please output one Markdown table with the columns, in this exact order: Repository | ID"
        )
        self.assertTrue(value["address_column_present"])
        self.assertTrue(value["adapter_route_eligible"])

    def test_signature_contains_no_question_or_identifier(self) -> None:
        value = visible_authority_signature(
            "Use WHO for 2022. The column names are: Country, Mortality rate."
        )
        self.assertNotIn("question", value)
        self.assertNotIn("opaque_id", value)
        self.assertFalse(
            value[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )


if __name__ == "__main__":
    unittest.main()
