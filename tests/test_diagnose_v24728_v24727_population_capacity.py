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

from scripts import diagnose_v24728_v24727_population_capacity as target  # noqa: E402


class V24728PopulationCapacityDiagnosisTests(unittest.TestCase):
    def test_capacity_curve_selects_minimum_feasible_cap(self) -> None:
        curve = target.capacity_curve(
            {"R1": 35, "R2": 30, "R3": 25, "R4": 15, "R5": 10, "R6": 1}
        )
        self.assertEqual(curve["9"], 46)
        self.assertEqual(curve["10"], 51)
        self.assertEqual(target.minimum_feasible_cap(curve), 10)

    def test_invalid_capacity_vector_fails_closed(self) -> None:
        for value in ({}, {"": 2}, {"R": 0}, {"R": True}):
            with self.assertRaises(ValueError):
                target.capacity_curve(value)

    def test_resealed_authorization_tamper_fails_closed(self) -> None:
        countries = {}
        index = 0
        for region, amount in {
            "R1": 35,
            "R2": 30,
            "R3": 25,
            "R4": 15,
            "R5": 10,
            "R6": 1,
        }.items():
            for _ in range(amount):
                countries[f"C{index:03d}"] = {
                    "region_id": region,
                    "name": f"Country {index}",
                }
                index += 1
        snapshots = [
            {key: index + offset for index, key in enumerate(countries)}
            for offset in (0, 100)
        ]
        with (
            patch.object(target.design, "prior_worldbank_iso3", return_value=set()),
            patch.object(target, "sha256", return_value="a" * 64),
        ):
            value = target.build_diagnosis(
                countries=countries,
                snapshots=snapshots,
                catalog_sha256="b" * 64,
                snapshot_metadata=[],
                now=0,
                git_head="c" * 40,
            )
            tampered = copy.deepcopy(value)
            tampered["authorization"]["forward_launch"] = True
            tampered.pop("diagnosis_payload_sha256")
            tampered["diagnosis_payload_sha256"] = target.payload_sha256(tampered)
            with self.assertRaises(RuntimeError):
                target.validate_diagnosis(tampered)


if __name__ == "__main__":
    unittest.main()
