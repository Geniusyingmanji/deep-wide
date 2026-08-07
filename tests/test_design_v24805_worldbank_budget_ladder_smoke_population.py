from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    design_v24805_worldbank_budget_ladder_smoke_population as design,
)


def encoded(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode()


def catalogue(rows: list[dict]) -> bytes:
    return encoded(
        [{"page": 1, "pages": 1, "per_page": 400, "total": len(rows)}, rows]
    )


def country(iso3: str, name: str, region: str) -> dict:
    return {
        "id": iso3,
        "name": name,
        "region": {"id": region, "value": f"Region {region}"},
    }


def iso3(index: int) -> str:
    return (
        chr(65 + index // (26 * 26))
        + chr(65 + (index // 26) % 26)
        + chr(65 + index % 26)
    )


def snapshot(indicator: str, year: str, rows: list[tuple[str, object]]) -> bytes:
    return encoded(
        [
            {
                "page": 1,
                "pages": 1,
                "per_page": 400,
                "total": len(rows),
                "lastupdated": "2026-07-13",
            },
            [
                {
                    "indicator": {"id": indicator, "value": "Metric"},
                    "countryiso3code": code,
                    "date": year,
                    "value": value,
                }
                for code, value in rows
            ],
        ]
    )


class V24805PopulationDesignTests(unittest.TestCase):
    def fixture(self):
        rows = [
            country(iso3(index), f"Country {index}", f"R{index % 8}")
            for index in range(90)
        ]
        countries, _metadata = design.parse_country_catalog(catalogue(rows))
        first: dict[str, dict] = {}
        second: dict[str, dict] = {}
        for index, code in enumerate(countries):
            available = index < 65
            first[code] = {
                "indicator": design.TARGETS[0]["indicator"],
                "year": design.TARGETS[0]["year"],
                "value": str(index + 1) if available else None,
                "source_url": "https://example/first",
                "response_sha256": "a" * 64,
            }
            second[code] = {
                "indicator": design.TARGETS[1]["indicator"],
                "year": design.TARGETS[1]["year"],
                "value": str(index + 2) if available else None,
                "source_url": "https://example/second",
                "response_sha256": "b" * 64,
            }
        return countries, (first, second)

    def test_catalog_and_snapshot_preserve_null_and_decimal_spelling(self) -> None:
        rows = [
            country(iso3(index), f"Country {index}", f"R{index % 8}")
            for index in range(64)
        ]
        countries, metadata = design.parse_country_catalog(catalogue(rows))
        self.assertEqual(len(countries), 64)
        self.assertEqual(metadata["eligible_country_count"], 64)
        target = design.TARGETS[0]
        raw = snapshot(
            target["indicator"], target["year"],
            [(rows[0]["id"], 84.0), (rows[1]["id"], None)],
        )
        records, stats = design.parse_indicator_snapshot(
            raw,
            indicator=target["indicator"],
            year=target["year"],
            source_url=design.indicator_url(target["indicator"], target["year"]),
        )
        self.assertEqual(records[rows[0]["id"]]["value"], "84.0")
        self.assertIsNone(records[rows[1]["id"]]["value"])
        self.assertEqual(stats["non_null_country_count"], 1)
        self.assertEqual(stats["null_country_count"], 1)

    def test_selection_is_fresh_fixed_strata_and_deterministic(self) -> None:
        countries, snapshots = self.fixture()
        excluded = {iso3(0), iso3(70)}
        selected, metrics = design.select_population(
            countries, snapshots, excluded
        )
        self.assertEqual(len(selected), 64)
        self.assertTrue(excluded.isdisjoint({item["iso3"] for item in selected}))
        self.assertEqual(
            metrics["task_stratum_counts"],
            {"complete": 10, "missing": 4, "mixed": 2},
        )
        self.assertEqual(metrics["selected_complete_country_count"], 44)
        self.assertEqual(metrics["selected_missing_country_count"], 20)
        again, again_metrics = design.select_population(
            countries, snapshots, excluded
        )
        self.assertEqual(
            [item["iso3"] for item in selected],
            [item["iso3"] for item in again],
        )
        self.assertEqual(metrics, again_metrics)

    def test_real_historical_exclusion_is_bound_to_four_tracked_artifacts(self) -> None:
        excluded, manifest = design.historical_iso3(ROOT)
        self.assertEqual(len(excluded), 96)
        self.assertEqual(set(manifest), {str(path) for path in design.HISTORICAL_PRIVATE})
        self.assertTrue(all(len(value) == 64 for value in manifest.values()))

    def test_public_artifact_contains_hashes_not_private_identity_or_value(self) -> None:
        countries, snapshots = self.fixture()
        selected, metrics = design.select_population(countries, snapshots, set())
        with patch.object(design, "_sha256", return_value="f" * 64):
            private, public = design.build_artifacts(
                selected,
                catalog_metadata={"response_sha256": "c" * 64},
                snapshot_metadata=[],
                historical_manifest={"history": "h" * 64},
                metrics=metrics,
                created_at=0,
                git_head="a" * 40,
            )
        public_text = json.dumps(public, sort_keys=True)
        self.assertIn("Country", json.dumps(private))
        self.assertNotIn("Country 0", public_text)
        self.assertNotIn('"1"', public_text)
        self.assertFalse(
            private["gold_provenance_or_evaluator_read_before_prediction_freeze_authorized"]
        )
        self.assertFalse(public["scope"]["this_population_satisfies_main_sample_size"])
        self.assertFalse(public["authorization"]["smoke_launch"])

    def test_missing_authority_precedes_any_network_effect(self) -> None:
        with (
            patch.object(design, "_git", side_effect=["", "a" * 40, "a" * 40]),
            patch.object(design, "_authorized", return_value=False),
            patch.object(design, "_fetch_bytes") as fetch,
        ):
            with self.assertRaisesRegex(RuntimeError, "not authorized"):
                design.main()
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
