from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24645_ror_population as design


def record(record_id: str, label: str, country: str, *, status: str = "active"):
    raw = json.dumps({"id": f"https://ror.org/{record_id}"}).encode()
    entry = {"path": f"{record_id}.json", "sha": "b" * 40}
    value = {
        "id": f"https://ror.org/{record_id}",
        "status": status,
        "names": [{"value": label, "types": ["ror_display"]}],
        "locations": [{"geonames_details": {"country_code": country}}],
    }
    return entry, raw, value


class PopulationTests(unittest.TestCase):
    def test_historical_vector_includes_v24642(self) -> None:
        visible, canonical = design.historical_entities()
        self.assertEqual(len(visible), 4_432)
        self.assertEqual(len(canonical), 4_432)
        self.assertTrue(
            all(entity in visible for group in design.ROR42 for entity in group)
        )

    def test_filters_historical_duplicate_and_unsafe_identity(self) -> None:
        canonical = lambda value: "".join(character for character in value.casefold() if character.isalnum())
        historical = {canonical("Old Institute")}
        values = [
            record("01aaa0001", "Old Institute", "US"),
            record("01aaa0002", "Duplicate Name", "CA"),
            record("01aaa0003", "Duplicate-Name", "GB"),
            record("01aaa0004", "Unsafe | Table", "FR"),
            record("01aaa0005", "Valid Institute", "DE"),
        ]
        eligible = [
            design._record_candidate(
                entry,
                raw,
                value,
                historical_canonical=historical,
                canonical=canonical,
            )
            for entry, raw, value in values
        ]
        self.assertIsNone(eligible[0])
        self.assertIsNone(eligible[3])
        self.assertEqual(eligible[4]["label"], "Valid Institute")
        duplicate_counts = {
            item["canonical"]
            for item in eligible
            if item is not None
            and sum(
                other is not None and other["canonical"] == item["canonical"]
                for other in eligible
            )
            > 1
        }
        self.assertEqual(duplicate_counts, {canonical("Duplicate Name")})

    def test_country_cap_and_quartile_interleave(self) -> None:
        old_selected = design.SELECTED_COUNT
        old_cap = design.COUNTRY_CAP
        try:
            design.SELECTED_COUNT = 8
            design.COUNTRY_CAP = 2
            rows = []
            countries = ("US", "US", "US", "CA", "CA", "GB", "DE", "FR", "AU")
            for index, country in enumerate(countries, 1):
                rows.append(record(f"0{index:08d}", f"Institute {index}", country))
            selected, metrics = design.select_records(
                rows,
                historical_canonical=set(),
                canonical=lambda value: value.casefold(),
            )
        finally:
            design.SELECTED_COUNT = old_selected
            design.COUNTRY_CAP = old_cap
        counts = {}
        for item in selected:
            counts[item["country"]] = counts.get(item["country"], 0) + 1
        self.assertEqual(len(selected), 8)
        self.assertLessEqual(max(counts.values()), 2)
        self.assertEqual(metrics["selected_country_max"], 2)
        self.assertEqual(len({item["canonical"] for item in selected}), 8)

    def test_parent_authorizes_design_but_not_launch(self) -> None:
        self.assertTrue(design._parent_valid())
        parent = design._read(ROOT / design.PARENT)
        self.assertTrue(
            parent["authorization"]["fresh_external_population_and_protocol_design"]
        )
        self.assertFalse(parent["authorization"]["fresh_external_activation_or_launch"])


if __name__ == "__main__":
    unittest.main()
