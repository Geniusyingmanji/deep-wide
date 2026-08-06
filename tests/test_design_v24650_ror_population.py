from __future__ import annotations

import json
import sys
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24650_ror_population as design


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
    def test_historical_vector_includes_v24645(self) -> None:
        visible, canonical = design.historical_entities()
        self.assertEqual(len(visible), 4_480)
        self.assertEqual(len(canonical), 4_480)
        self.assertTrue(
            all(entity in visible for group in design.ROR45 for entity in group)
        )

    def test_filters_history_and_query_ambiguous_identity(self) -> None:
        canonical = lambda value: "".join(
            character for character in value.casefold() if character.isalnum()
        )
        historical = {canonical("Old Institute")}
        values = [
            record("01aaa0001", "Old Institute", "US"),
            record("01aaa0002", 'Quoted "Institute"', "CA"),
            record("01aaa0003", "Backslash \\ Institute", "GB"),
            record("01aaa0004", "Valid Institute", "DE"),
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
        self.assertIsNone(eligible[1])
        self.assertIsNone(eligible[2])
        self.assertEqual(eligible[3]["label"], "Valid Institute")

    def test_country_cap4_and_quartile_interleave(self) -> None:
        old_selected = design.SELECTED_COUNT
        old_cap = design.COUNTRY_CAP
        try:
            design.SELECTED_COUNT = 8
            design.COUNTRY_CAP = 4
            countries = ("US", "US", "US", "US", "US", "CA", "GB", "DE", "FR")
            rows = [
                record(f"0{index:08d}", f"Institute {index}", country)
                for index, country in enumerate(countries, 1)
            ]
            selected, metrics = design.select_records(
                rows,
                historical_canonical=set(),
                canonical=lambda value: value.casefold(),
            )
        finally:
            design.SELECTED_COUNT = old_selected
            design.COUNTRY_CAP = old_cap
        counts = Counter(item["country"] for item in selected)
        self.assertEqual(len(selected), 8)
        self.assertLessEqual(max(counts.values()), 4)
        self.assertEqual(metrics["selected_country_max"], 4)

    def test_parent_authorizes_design_but_not_launch(self) -> None:
        self.assertTrue(design._parent_valid())
        parent = design._read(ROOT / design.PARENT)
        self.assertTrue(
            parent["authorization"]["fresh_external_population_and_protocol_design"]
        )
        self.assertFalse(parent["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(parent["supersedes"]["v1_authorizes_successor_use"])


if __name__ == "__main__":
    unittest.main()
