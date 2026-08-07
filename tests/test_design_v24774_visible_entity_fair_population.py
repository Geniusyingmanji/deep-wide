from __future__ import annotations

import ast
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24774_visible_entity_fair_population as target  # noqa: E402


def record(record_id: str, label: str, country_code: str, established: int):
    value = {
        "id": f"https://ror.org/{record_id}",
        "status": "active",
        "types": ["education"],
        "names": [{"value": label, "types": ["ror_display"]}],
        "locations": [
            {
                "geonames_details": {
                    "country_name": f"Country {country_code}",
                    "country_code": country_code,
                }
            }
        ],
        "established": established,
    }
    raw = json.dumps(value, sort_keys=True).encode()
    blob = hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw,
        usedforsecurity=False,
    ).hexdigest()
    return f"{record_id}.json", blob, raw, value


class V24774VisibleEntityFairPopulationTests(unittest.TestCase):
    def test_capacity_parent_and_failed_surfaces_are_bound(self) -> None:
        self.assertTrue(target._parent_valid())
        self.assertEqual(target.COUNTRY_CAP, 16)
        self.assertEqual(target.EXPECTED_HISTORY, 4_720)
        self.assertTrue(
            all(
                not (ROOT / path).exists() and not (ROOT / path).is_symlink()
                for path in target.FAILED_V24772_SURFACES
            )
        )

    def test_new_seed_changes_rank_without_changing_eligibility(self) -> None:
        row = record("01abc0001", "Fresh Successor Institute", "US", 1900)
        canonical = lambda value: value.casefold()
        old = target.base.record_candidate(
            *row, historical_canonical=set(), canonical=canonical
        )
        new = target.record_candidate(
            *row, historical_canonical=set(), canonical=canonical
        )
        self.assertIsNotNone(old)
        self.assertIsNotNone(new)
        self.assertEqual(
            {key: value for key, value in old.items() if key != "rank"},
            {key: value for key, value in new.items() if key != "rank"},
        )
        self.assertNotEqual(old["rank"], new["rank"])

    def test_country_cap16_selects_fixed_32(self) -> None:
        rows = [
            record(f"0{index:08d}", f"Institute {index}", "US", 1800 + index)
            for index in range(1, 23)
        ] + [
            record(f"1{index:08d}", f"College {index}", "CA", 1850 + index)
            for index in range(1, 23)
        ]
        selected, metrics = target.select_records(
            rows,
            historical_canonical=set(),
            canonical=lambda value: value.casefold(),
        )
        self.assertEqual(len(selected), 32)
        self.assertEqual(metrics["selected_country_count"], 2)
        self.assertEqual(metrics["selected_country_max"], 16)
        with self.assertRaises(ValueError):
            target.select_records(
                rows,
                historical_canonical=set(),
                canonical=lambda value: value.casefold(),
                country_cap=15,
            )

    def test_visible_contract_has_successor_identity_and_no_private_values(self) -> None:
        rows = [
            {
                "label": f"Visible Successor Institute {index}",
                "record_id": f"0{index:08d}",
                "founded": str(1700 + index),
                "country": f"Private Country {index}",
                "country_code": "ZZ",
            }
            for index in range(1, target.SELECTED_COUNT + 1)
        ]
        raw = target.contract_source(rows)
        text = raw.decode()
        ast.parse(text)
        self.assertIn("v24774", text)
        self.assertNotIn("v24772", text.casefold())
        self.assertNotIn(rows[0]["record_id"], text)
        self.assertNotIn(rows[0]["founded"], text)
        self.assertNotIn(rows[0]["country"], text)


if __name__ == "__main__":
    unittest.main()
