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

from scripts import design_v24760_zero_effect_population as prior  # noqa: E402
from scripts import design_v24772_visible_entity_fair_population as target  # noqa: E402


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


class V24772VisibleEntityFairPopulationTests(unittest.TestCase):
    def test_parent_authority_is_valid_and_launch_is_forbidden(self) -> None:
        self.assertTrue(target._parent_valid())
        self.assertEqual(target.COUNTRY_CAP, 11)
        self.assertEqual(target.SELECTED_COUNT, 32)

    def test_history_adds_v24750_and_v24760_and_is_unique(self) -> None:
        visible, canonical = target.historical_entities()
        self.assertEqual(len(visible), target.EXPECTED_HISTORY)
        self.assertEqual(len(canonical), target.EXPECTED_HISTORY)
        v24750 = {
            entity
            for group in target.v24750_contract.ROR_GROUPS
            for entity in group
        }
        v24760 = {
            entity
            for group in target.v24760_contract.ENTITY_GROUPS
            for entity in group
        }
        self.assertEqual(len(v24750), target.EXPECTED_V24750)
        self.assertEqual(len(v24760), target.EXPECTED_V24760)
        self.assertFalse(v24750 & v24760)
        self.assertTrue((v24750 | v24760).issubset(visible))

    def test_new_seed_changes_rank_without_changing_eligibility(self) -> None:
        row = record("01abc0001", "Fresh Fair Institute", "US", 1900)
        canonical = lambda value: value.casefold()
        old = prior.record_candidate(
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

    def test_country_cap11_selects_fixed_32(self) -> None:
        rows = [
            record(f"0{index:08d}", f"Institute {index}", "US", 1800 + index)
            for index in range(1, 23)
        ] + [
            record(f"1{index:08d}", f"College {index}", "CA", 1850 + index)
            for index in range(1, 23)
        ] + [
            record(f"2{index:08d}", f"Academy {index}", "GB", 1900 + index)
            for index in range(1, 23)
        ]
        selected, metrics = target.select_records(
            rows,
            historical_canonical=set(),
            canonical=lambda value: value.casefold(),
        )
        self.assertEqual(len(selected), 32)
        self.assertLessEqual(metrics["selected_country_max"], 11)
        with self.assertRaises(ValueError):
            target.select_records(
                rows,
                historical_canonical=set(),
                canonical=lambda value: value.casefold(),
                country_cap=10,
            )

    def test_visible_contract_has_only_visible_values(self) -> None:
        rows = [
            {
                "label": f"Visible Fair Institute {index}",
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
        self.assertIn("v24772", text)
        self.assertNotIn(rows[0]["record_id"], text)
        self.assertNotIn(rows[0]["founded"], text)
        self.assertNotIn(rows[0]["country"], text)
        namespace: dict[str, object] = {}
        exec(compile(text, "<v24772-contract>", "exec"), namespace)
        tasks = namespace["task_vector"]()
        self.assertEqual(len(tasks), 8)
        self.assertTrue(
            all(set(item) == {"opaque_id", "question"} for item in tasks)
        )


if __name__ == "__main__":
    unittest.main()
