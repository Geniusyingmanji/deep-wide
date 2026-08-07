from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24814_fresh_worldbank_population as target  # noqa: E402
from tests.test_design_v24813_fresh_worldbank_population import (  # noqa: E402
    V24813FreshPopulationTests,
)


class V24814FreshPopulationTests(unittest.TestCase):
    def test_successor_reaches_48_without_reusing_excluded(self):
        countries, snapshots = V24813FreshPopulationTests().fixture()
        excluded = set(list(countries)[:2])
        selected, metrics = target.select_population(countries, snapshots, excluded)
        self.assertEqual(len(selected), 48)
        self.assertTrue(excluded.isdisjoint({item["iso3"] for item in selected}))
        self.assertEqual(metrics["complete_candidate_count"], 58)

    def test_v24813_surfaces_remain_absent(self):
        self.assertFalse((ROOT / target.base.PRIVATE).exists())
        self.assertFalse((ROOT / target.base.OUTPUT).exists())

    def test_only_selection_change_is_unreachable_region_cap(self):
        self.assertEqual(target.base.SELECTED_COUNT, 48)
        self.assertEqual(target.base.TASK_COUNT, 12)
        self.assertEqual(target.base.TARGETS, target.base.base.TARGETS)
        self.assertEqual(target.REGION_CAP, target.base.SELECTED_COUNT)


if __name__ == "__main__":
    unittest.main()
