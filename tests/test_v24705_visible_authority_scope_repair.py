from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24705_visible_authority_scope_repair import (  # noqa: E402
    validate_signature,
    visible_authority_signature,
)


class V24705AuthorityScopeTests(unittest.TestCase):
    def test_worldbank_fact_scope_is_eligible(self) -> None:
        value = visible_authority_signature(
            "Return 2023 population according to the statistics of the World Bank. The column names are: Country, Population."
        )
        validate_signature(value)
        self.assertEqual(value["unique_namespace"], "world_bank")
        self.assertTrue(value["adapter_route_eligible"])

    def test_github_discovery_clue_is_not_authority(self) -> None:
        value = visible_authority_signature(
            "Find a project whose GitHub stars exceed 20000 and list the founder. The column names are: Name, Date."
        )
        self.assertEqual(value["namespace_count"], 0)
        self.assertFalse(value["adapter_route_eligible"])

    def test_camera_iso_field_is_not_authority(self) -> None:
        value = visible_authority_signature(
            "List cameras in 2025. The column names are: Camera, ISO Range, Weight."
        )
        self.assertEqual(value["namespace_count"], 0)

    def test_explicit_github_api_scope_can_route(self) -> None:
        value = visible_authority_signature(
            "Using GitHub API data for 2024, output a table with the columns: Repository | Star count"
        )
        self.assertEqual(value["unique_namespace"], "github")
        self.assertTrue(value["authority_scope_explicit"])


if __name__ == "__main__":
    unittest.main()
