from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24773_v24772_population_capacity as target  # noqa: E402


class V24773PopulationCapacityDiagnosisTests(unittest.TestCase):
    def test_capacity_curve_and_minimum(self) -> None:
        curve = target.capacity_curve({"AA": 20, "BB": 10, "CC": 2})
        self.assertEqual(curve["1"], 3)
        self.assertEqual(curve["10"], 22)
        self.assertEqual(curve["20"], 32)
        self.assertEqual(target.minimum_feasible_cap(curve), 20)

    def test_invalid_capacity_vector_is_rejected(self) -> None:
        for value in ({}, {"AA": 0}, {"": 2}, {"AA": True}):
            with self.assertRaises(ValueError):
                target.capacity_curve(value)

    def test_build_and_validate_content_free_diagnosis(self) -> None:
        countries = {"AA": 20, "BB": 10, "CC": 2}
        value = target.build_diagnosis(
            eligible_count=32,
            canonical_unique_count=32,
            country_counts=countries,
            tree_bytes_sha256="a" * 64,
            tree_record_count=3_482,
            now=1,
            git_head="b" * 40,
        )
        self.assertEqual(
            value["denominator_correction"]["correct_history_count"], 4_720
        )
        self.assertTrue(
            value["content_free_capacity"]["exact_v24772_failure_reproduced"]
        )
        self.assertEqual(
            value["authorization"]["repaired_country_cap"], 20
        )
        self.assertFalse(value["authorization"]["activation_or_external_launch"])
        self.assertNotIn("AA", str(value["content_free_capacity"]))

    def test_surface_paths_are_pristine(self) -> None:
        self.assertTrue(
            all(
                not (ROOT / path).exists() and not (ROOT / path).is_symlink()
                for path in target.FAILED_SURFACES
            )
        )


if __name__ == "__main__":
    unittest.main()
