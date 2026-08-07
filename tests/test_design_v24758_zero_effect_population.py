from __future__ import annotations

import ast
import hashlib
import json
import sys
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24758_zero_effect_population as target  # noqa: E402


def record(
    record_id: str,
    label: str,
    country: str,
    country_code: str,
    established: int | None,
    *,
    status: str = "active",
    types: list[str] | None = None,
):
    value = {
        "id": f"https://ror.org/{record_id}",
        "status": status,
        "names": [{"value": label, "types": ["ror_display"]}],
        "locations": [
            {
                "geonames_details": {
                    "country_name": country,
                    "country_code": country_code,
                }
            }
        ],
        "established": established,
        "types": ["education"] if types is None else types,
    }
    raw = json.dumps(value, sort_keys=True).encode()
    blob = hashlib.sha1(
        f"blob {len(raw)}\0".encode("ascii") + raw,
        usedforsecurity=False,
    ).hexdigest()
    return f"{record_id}.json", blob, raw, value


class V24758ZeroEffectPopulationTests(unittest.TestCase):
    def test_parent_and_historical_population_are_valid(self) -> None:
        self.assertTrue(target._parent_valid())
        visible, canonical = target.historical_entities()
        self.assertEqual(len(visible), target.EXPECTED_HISTORY)
        self.assertEqual(len(canonical), target.EXPECTED_HISTORY)

    def test_selection_filters_history_invalid_year_and_caps_country(self) -> None:
        canonical = lambda value: "".join(
            character for character in value.casefold() if character.isalnum()
        )
        rows = [
            record("01aaa0001", "Old Institute", "United States", "US", 1900),
            record("01aaa0002", "No Year Institute", "Canada", "CA", None),
            record("01aaa0003", "Future Institute", "France", "FR", 2026),
            record(
                "01aaa0007",
                "Company Institute",
                "Germany",
                "DE",
                1904,
                types=["company"],
            ),
            record("01aaa0004", "Alpha Institute", "United States", "US", 1901),
            record("01aaa0005", "Beta Institute", "United States", "US", 1902),
            record("01aaa0006", "Gamma Institute", "Canada", "CA", 1903),
        ]
        selected, metrics = target.select_records(
            rows,
            historical_canonical={canonical("Old Institute")},
            canonical=canonical,
            selected_count=2,
            task_size=1,
            country_cap=1,
        )
        self.assertEqual(len(selected), 2)
        self.assertNotIn("Old Institute", {item["label"] for item in selected})
        self.assertLessEqual(
            max(Counter(item["country_code"] for item in selected).values()), 1
        )
        self.assertGreaterEqual(metrics["canonical_unique_candidate_count"], 3)

    def test_contract_is_visible_only_and_round_trips_tasks(self) -> None:
        rows = [
            {
                "label": f"Visible Institute {index}",
                "record_id": f"0{index:08d}",
                "founded": str(1800 + index),
                "country": f"Private Country {index}",
                "country_code": "ZZ",
            }
            for index in range(1, target.SELECTED_COUNT + 1)
        ]
        raw = target.contract_source(rows)
        text = raw.decode("utf-8")
        ast.parse(text)
        self.assertIn("Organization, Founded, Country", text)
        self.assertNotIn(rows[0]["record_id"], text)
        self.assertNotIn(rows[0]["country"], text)
        self.assertNotIn(rows[0]["founded"], text)
        namespace: dict[str, object] = {"__name__": "v24758_test_contract"}
        exec(compile(raw, "v24758_test_contract.py", "exec"), namespace)
        tasks = namespace["task_vector"]()
        self.assertEqual(len(tasks), target.SELECTED_COUNT // target.TASK_SIZE)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))
        self.assertTrue(all(len(group) == target.TASK_SIZE for group in namespace["ENTITY_GROUPS"]))

    def test_rank_is_seeded_before_any_search_outcome(self) -> None:
        tree = json.dumps(
            {
                "truncated": False,
                "tree": [
                    {"path": f"0{index:08d}.json", "sha": f"{index:040x}", "type": "blob"}
                    for index in range(1, 3_483)
                ],
            },
            sort_keys=True,
        ).encode()
        old_hash = target.source.ROR_TREE_SHA256
        try:
            target.source.ROR_TREE_SHA256 = hashlib.sha256(tree).hexdigest()
            first = target.ranked_entries(tree)
            second = target.ranked_entries(tree)
        finally:
            target.source.ROR_TREE_SHA256 = old_hash
        self.assertEqual(first, second)
        self.assertEqual(len(first), 3_482)


if __name__ == "__main__":
    unittest.main()
