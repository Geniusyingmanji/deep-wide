from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24703_visible_authority_namespace_repair import (  # noqa: E402
    validate_signature,
    visible_authority_signature,
)


class V24703VisibleAuthorityRepairTests(unittest.TestCase):
    def test_lowercase_and_title_who_are_not_namespace_cues(self) -> None:
        for word in ("who", "Who"):
            value = visible_authority_signature(
                f"Show {word} appeared in 2023. The column names are: Name, Date."
            )
            self.assertEqual(value["namespace_count"], 0)
            self.assertFalse(value["adapter_route_eligible"])

    def test_uppercase_who_is_a_namespace_cue(self) -> None:
        value = visible_authority_signature(
            "Use WHO data for 2023. The column names are: Country, Mortality rate."
        )
        validate_signature(value)
        self.assertEqual(value["unique_namespace"], "who")
        self.assertTrue(value["adapter_route_eligible"])

    def test_full_name_is_case_insensitive(self) -> None:
        value = visible_authority_signature(
            "Use world health organization data for 2023. The column names are: Country, Cases."
        )
        self.assertEqual(value["unique_namespace"], "who")

    def test_other_namespace_behavior_is_preserved(self) -> None:
        value = visible_authority_signature(
            "Use World Bank data for 2023. The column names are: Country, Population."
        )
        self.assertEqual(value["unique_namespace"], "world_bank")
        self.assertTrue(value["adapter_route_eligible"])


if __name__ == "__main__":
    unittest.main()
