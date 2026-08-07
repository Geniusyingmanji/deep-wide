from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    design_v24820_cell_disjoint_worldbank_population as target,
)


def fixture(count: int = 170):
    countries = {}
    snapshots = ({}, {})
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for index in range(count):
        iso3 = (
            alphabet[(index // (26 * 26)) % 26]
            + alphabet[(index // 26) % 26]
            + alphabet[index % 26]
        )
        countries[iso3] = {
            "iso3": iso3,
            "name": f"Country {index}",
            "region_id": f"R{index % 6}",
            "region_name": f"Region {index % 6}",
        }
        for position, target_value in enumerate(target.TARGETS):
            snapshots[position][iso3] = {
                "indicator": target_value["indicator"],
                "year": target_value["year"],
                "value": str(index + position / 10),
                "source_url": "https://api.worldbank.org/example",
                "response_sha256": f"{position + 1:064x}",
            }
    return countries, snapshots


class V24820PopulationTests(unittest.TestCase):
    def test_selects_fixed_128_and_prioritizes_novel_entities(self) -> None:
        countries, snapshots = fixture()
        ordered = sorted(countries)
        historical_entities = set(ordered[:150])
        historical_targets = {("OLD.A", "2022"), ("OLD.B", "2022")}
        historical_cells = {
            (iso3, indicator, year)
            for iso3 in historical_entities
            for indicator, year in historical_targets
        }
        selected, metrics = target.select_population(
            countries,
            snapshots,
            historical_entities,
            historical_cells,
            historical_targets,
        )
        self.assertEqual(len(selected), 128)
        selected_iso3 = {item["iso3"] for item in selected}
        self.assertEqual(len(selected_iso3), 128)
        self.assertEqual(metrics["selected_entity_novel_count"], 20)
        self.assertEqual(metrics["selected_entity_overlap_count"], 108)
        self.assertEqual(metrics["selected_target_pair_overlap_count"], 0)
        self.assertEqual(metrics["selected_gold_cell_overlap_count"], 0)

    def test_historical_target_pair_overlap_is_rejected(self) -> None:
        countries, snapshots = fixture()
        with self.assertRaisesRegex(RuntimeError, "target/year"):
            target.select_population(
                countries,
                snapshots,
                set(),
                set(),
                {
                    (
                        target.TARGETS[0]["indicator"],
                        target.TARGETS[0]["year"],
                    )
                },
            )

    def test_historical_cell_overlap_is_rejected(self) -> None:
        countries, snapshots = fixture()
        iso3 = next(iter(countries))
        with self.assertRaisesRegex(RuntimeError, "candidate cell"):
            target.select_population(
                countries,
                snapshots,
                set(),
                {
                    (
                        iso3,
                        target.TARGETS[0]["indicator"],
                        target.TARGETS[0]["year"],
                    )
                },
                set(),
            )

    def test_incomplete_values_are_excluded_before_selection(self) -> None:
        countries, snapshots = fixture()
        for iso3 in list(countries)[:10]:
            snapshots[1][iso3] = {
                **snapshots[1][iso3],
                "value": None,
            }
        selected, metrics = target.select_population(
            countries, snapshots, set(), set(), set()
        )
        self.assertEqual(len(selected), 128)
        self.assertEqual(metrics["complete_candidate_count"], 160)
        self.assertTrue(
            all(item["records"][1]["value"] is not None for item in selected)
        )

    def test_build_artifacts_discloses_entity_overlap_without_content(self) -> None:
        countries, snapshots = fixture(128)
        selected, metrics = target.select_population(
            countries,
            snapshots,
            set(list(countries)[:100]),
            set(),
            set(),
        )
        private, public = target.build_artifacts(
            selected,
            authorization_audit_sha256="6" * 64,
            catalog_metadata={
                "response_sha256": "1" * 64,
                "reported_total": 128,
                "eligible_country_count": 128,
            },
            snapshot_metadata=[
                {
                    "indicator": item["indicator"],
                    "year": item["year"],
                    "source_url": "https://api.worldbank.org/example",
                    "response_sha256": f"{index + 2:064x}",
                    "lastupdated": "2026-08-07",
                    "reported_total": 128,
                    "non_null_country_count": 128,
                    "null_country_count": 0,
                }
                for index, item in enumerate(target.TARGETS)
            ],
            historical_manifest={"historical": "4" * 64},
            metrics=metrics,
            created_at=1,
            git_head="5" * 40,
        )
        self.assertEqual(len(private["groups"]), 32)
        self.assertFalse(
            private["disjointness_scope"]["country_entities_disjoint"]
        )
        self.assertTrue(
            private["disjointness_scope"][
                "country_indicator_year_gold_cells_disjoint"
            ]
        )
        self.assertFalse(public["scope"]["entity_disjoint_claim"])
        self.assertTrue(public["scope"]["target_cell_disjoint_claim"])
        serialized = target.json.dumps(public)
        self.assertNotIn("Country 0", serialized)

    def test_reselection_is_deterministic(self) -> None:
        countries, snapshots = fixture()
        first, first_metrics = target.select_population(
            countries, snapshots, set(), set(), set()
        )
        second, second_metrics = target.select_population(
            copy.deepcopy(countries),
            copy.deepcopy(snapshots),
            set(),
            set(),
            set(),
        )
        self.assertEqual(first, second)
        self.assertEqual(first_metrics, second_metrics)

    def test_current_historical_boundary_has_new_target_pairs(self) -> None:
        entities, cells, target_pairs, manifest = target.historical_boundary()
        self.assertGreaterEqual(len(entities), 190)
        self.assertGreater(len(cells), 0)
        self.assertEqual(len(target_pairs), 6)
        self.assertEqual(len(manifest), 4)
        self.assertTrue(
            {
                (item["indicator"], item["year"])
                for item in target.TARGETS
            }.isdisjoint(target_pairs)
        )


if __name__ == "__main__":
    unittest.main()
