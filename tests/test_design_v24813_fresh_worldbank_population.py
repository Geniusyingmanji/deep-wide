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

from scripts import design_v24813_fresh_worldbank_population as design  # noqa: E402
from tests.test_design_v24805_worldbank_budget_ladder_smoke_population import (  # noqa: E402
    country,
    iso3,
)


class V24813FreshPopulationTests(unittest.TestCase):
    def fixture(self):
        countries = {
            iso3(index): {
                "iso3": iso3(index), "name": f"Fresh Country {index}",
                "region_id": f"R{index % 8}", "region_name": f"Region {index % 8}",
            }
            for index in range(60)
        }
        snapshots = []
        for target_index, target in enumerate(design.TARGETS):
            snapshots.append(
                {
                    code: {
                        "indicator": target["indicator"], "year": target["year"],
                        "value": f"{index + target_index}.5",
                        "source_url": "https://example.invalid/snapshot",
                        "response_sha256": str(target_index + 1) * 64,
                    }
                    for index, code in enumerate(countries)
                }
            )
        return countries, snapshots

    def test_historical_exclusion_includes_consumed_smoke(self):
        excluded, manifest = design.historical_iso3(ROOT)
        self.assertEqual(len(excluded), 160)
        self.assertEqual(len(manifest), 5)
        consumed = json.loads((ROOT / design.CONSUMED_POPULATION).read_text())
        consumed_iso3 = {item["iso3"] for group in consumed["groups"] for item in group}
        self.assertEqual(len(consumed_iso3), 64)
        self.assertTrue(consumed_iso3.issubset(excluded))

    def test_selection_is_deterministic_disjoint_and_12_by_4(self):
        countries, snapshots = self.fixture()
        excluded = {iso3(0), iso3(1)}
        selected, metrics = design.select_population(countries, snapshots, excluded)
        self.assertEqual(len(selected), 48)
        self.assertTrue(excluded.isdisjoint({item["iso3"] for item in selected}))
        self.assertEqual(metrics["task_stratum_counts"], {"complete": 12})
        again, again_metrics = design.select_population(countries, snapshots, excluded)
        self.assertEqual([item["iso3"] for item in selected], [item["iso3"] for item in again])
        self.assertEqual(metrics, again_metrics)

    def test_public_artifact_contains_hashes_not_identity_or_values(self):
        countries, snapshots = self.fixture()
        selected, metrics = design.select_population(countries, snapshots, set())
        with patch.object(design, "_sha256", return_value="f" * 64):
            private, public = design.build_artifacts(
                selected, catalog_metadata={"response_sha256": "c" * 64},
                snapshot_metadata=[], historical_manifest={"history": "h" * 64},
                metrics=metrics, created_at=0, git_head="a" * 40,
            )
        self.assertIn("Fresh Country 0", json.dumps(private))
        public_text = json.dumps(public, sort_keys=True)
        self.assertNotIn("Fresh Country", public_text)
        self.assertNotIn('"0.5"', public_text)
        self.assertFalse(public["authorization"]["external_launch"])

    def test_authority_check_precedes_network(self):
        with (
            patch.object(design, "_git", side_effect=["", "a" * 40, "a" * 40]),
            patch.object(design, "_authorized", return_value=False),
            patch.object(design.base, "_fetch_bytes") as fetch,
        ):
            with self.assertRaisesRegex(RuntimeError, "not authorized"):
                design.main()
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
