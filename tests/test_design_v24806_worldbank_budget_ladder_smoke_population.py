from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    design_v24806_worldbank_budget_ladder_smoke_population as target,
)


class V24806PopulationRepairTests(unittest.TestCase):
    def test_clean_gate_allows_only_exact_research_tmp(self) -> None:
        with patch.object(
            target.base, "_git", return_value="?? .research/tmp/"
        ):
            self.assertTrue(target._clean_except_local_research_tmp())
        for status in (" M plan.md", "?? other/", "?? .research/tmp/\n M plan.md"):
            with self.subTest(status=status), patch.object(
                target.base, "_git", return_value=status
            ):
                self.assertFalse(target._clean_except_local_research_tmp())

    def test_repaired_artifact_changes_only_identity_and_audit_binding(self) -> None:
        selected = []
        for index in range(4):
            selected.append({
                "iso3": f"X{index:02d}", "name": f"Country {index}",
                "region_id": f"R{index}", "region_name": f"Region {index}",
                "records": [
                    {
                        "indicator": item["indicator"], "year": item["year"],
                        "value": str(index), "source_url": "https://example",
                        "response_sha256": str(index) * 64,
                    }
                    for item in target.base.TARGETS
                ],
            })
        with patch.object(target.base, "_sha256", return_value="f" * 64):
            private, public = target.build_artifacts(
                selected,
                catalog_metadata={"response_sha256": "c" * 64},
                snapshot_metadata=[],
                historical_manifest={"h": "a" * 64},
                metrics={"selected_country_count": 4},
                created_at=0,
                git_head="b" * 40,
            )
        self.assertEqual(
            private["append_only_clean_gate_successor"]["only_change"],
            "permit_exact_untracked_research_tmp_directory",
        )
        self.assertFalse(
            private["append_only_clean_gate_successor"]["predecessor_population_consumed"]
        )
        self.assertEqual(
            public["append_only_clean_gate_successor"][
                "population_selection_targets_ranks_strata_and_policy_unchanged"
            ],
            True,
        )
        self.assertNotIn("Country 0", json.dumps(public))

    def test_successor_surface_is_fresh_and_predecessor_is_not_reused(self) -> None:
        self.assertNotEqual(target.PRIVATE, target.base.PRIVATE)
        self.assertNotEqual(target.OUTPUT, target.base.OUTPUT)
        self.assertNotEqual(target.AUTHORIZATION, target.base.AUTHORIZATION)
        self.assertEqual(target.base.TARGETS[0]["year"], "2023")

    def test_missing_successor_authority_precedes_network(self) -> None:
        with (
            patch.object(target, "_clean_except_local_research_tmp", return_value=True),
            patch.object(target.base, "_git", side_effect=["a" * 40, "a" * 40]),
            patch.object(target, "_authorized", return_value=False),
            patch.object(target.base, "_fetch_bytes") as fetch,
        ):
            with self.assertRaisesRegex(RuntimeError, "not authorized"):
                target.main()
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
