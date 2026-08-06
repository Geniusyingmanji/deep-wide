from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24690_worldbank_population_capacity_repair as design  # noqa: E402


class V24690WorldBankPopulationCapacityRepairTests(unittest.TestCase):
    def test_append_only_paths_and_cap(self) -> None:
        self.assertEqual(design.REGION_CAP, 9)
        self.assertEqual(design.base.REGION_CAP, 8)
        self.assertNotEqual(design.PRIVATE, design.base.PRIVATE)
        self.assertNotEqual(design.OUTPUT, design.base.OUTPUT)
        self.assertNotEqual(design.AUTHORIZATION, design.PREDECESSOR_AUTHORIZATION)

    def test_repaired_selector_has_required_capacity(self) -> None:
        countries = {}
        snapshots = ({}, {})
        region_sizes = {"EAS": 9, "ECS": 9, "LCN": 9, "MEA": 9, "SSF": 9, "SAS": 4}
        index = 0
        for region, count in region_sizes.items():
            for _ in range(count):
                iso3 = f"X{index:02d}"
                index += 1
                countries[iso3] = {
                    "name": f"Country {iso3}",
                    "region_id": region,
                    "region_name": region,
                }
                for target_index, snapshot in enumerate(snapshots):
                    target = design.base.TARGETS[target_index]
                    snapshot[iso3] = {
                        "indicator": target["indicator"],
                        "year": target["year"],
                        "value": str(index),
                        "source_url": "https://example",
                        "response_sha256": str(target_index) * 64,
                    }
        selected, metrics = design.select_records(countries, list(snapshots))
        self.assertEqual(len(selected), 48)
        self.assertEqual(metrics["selected_region_max"], 9)
        self.assertGreaterEqual(metrics["minimum_distinct_regions_per_task"], 3)

    def test_missing_repaired_authority_precedes_network(self) -> None:
        with (
            patch.object(design, "_git", side_effect=["", "a" * 40, "a" * 40]),
            patch.object(design.base, "_parent_valid", return_value=True),
            patch.object(design, "_authorization_valid", return_value=False),
            patch.object(design.base, "_fetch_bytes") as fetch,
        ):
            with self.assertRaisesRegex(RuntimeError, "not authorized"):
                design.main()
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
