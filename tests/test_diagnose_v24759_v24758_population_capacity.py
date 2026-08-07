from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24759_v24758_population_capacity as target  # noqa: E402


COUNTRIES = {"A": 1_099, "B": 71, "C": 5, "D": 3, "E": 1, "F": 1}


class V24759V24758PopulationCapacityTests(unittest.TestCase):
    def test_exact_curve_reproduces_failed_cap_and_minimum_repair(self) -> None:
        curve = target.capacity_curve(COUNTRIES)
        self.assertEqual(curve["4"], 17)
        self.assertEqual(curve["10"], 30)
        self.assertEqual(curve["11"], 32)
        self.assertEqual(target.minimum_feasible_cap(curve), 11)

    def test_invalid_capacity_vectors_fail_closed(self) -> None:
        for value in ({}, {"": 1}, {"A": 0}, {"A": True}):
            with self.assertRaises(ValueError):
                target.capacity_curve(value)

    def test_resealed_launch_tamper_fails(self) -> None:
        with patch.object(target, "sha256", return_value="a" * 64):
            value = target.build_diagnosis(
                eligible_count=1_180,
                canonical_unique_count=1_180,
                country_counts=COUNTRIES,
                tree_bytes_sha256="b" * 64,
                tree_record_count=3_482,
                now=0,
                git_head="c" * 40,
            )
        altered = copy.deepcopy(value)
        altered["authorization"]["activation_or_external_launch"] = True
        altered.pop("diagnosis_payload_sha256")
        altered["diagnosis_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_diagnosis(altered)


if __name__ == "__main__":
    unittest.main()
