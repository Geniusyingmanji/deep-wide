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

from scripts import design_v24688_worldbank_population as design  # noqa: E402


def encoded(value: object) -> bytes:
    return json.dumps(value, separators=(",", ":")).encode()


def catalogue(rows: list[dict]) -> bytes:
    return encoded(
        [
            {"page": 1, "pages": 1, "per_page": "400", "total": len(rows)},
            rows,
        ]
    )


def country(iso3: str, name: str, region: str = "R1") -> dict:
    return {
        "id": iso3,
        "name": name,
        "region": {"id": region, "value": f"Region {region}"},
    }


def snapshot(indicator: str, year: str, rows: list[tuple[str, object]]) -> bytes:
    return encoded(
        [
            {
                "page": 1,
                "pages": 1,
                "per_page": 400,
                "total": len(rows),
                "lastupdated": "2026-08-01",
            },
            [
                {
                    "indicator": {"id": indicator, "value": "Metric"},
                    "countryiso3code": iso3,
                    "date": year,
                    "value": value,
                }
                for iso3, value in rows
            ],
        ]
    )


class V24688WorldBankPopulationDesignTests(unittest.TestCase):
    def test_country_catalogue_excludes_aggregates_and_unsafe_names(self) -> None:
        rows = [
            country("AAA", "Alpha", "R1"),
            country("BBB", "Aggregate", "NA"),
            country("CCC", "Unsafe | name", "R2"),
        ] + [
            country(
                f"{chr(65 + index // 26)}{chr(65 + index % 26)}Z",
                f"Country {index}",
                "R3",
            )
            for index in range(49)
        ]
        countries, metadata = design.parse_country_catalog(catalogue(rows))
        self.assertIn("AAA", countries)
        self.assertNotIn("BBB", countries)
        self.assertNotIn("CCC", countries)
        self.assertEqual(metadata["eligible_country_count"], 50)

    def test_indicator_snapshot_preserves_decimal_lexeme_and_null(self) -> None:
        target = design.TARGETS[0]
        url = design.indicator_url(target["indicator"], target["year"])
        raw = snapshot(
            target["indicator"],
            target["year"],
            [("AAA", 84.0), ("BBB", None)],
        )
        values, metadata = design.parse_indicator_snapshot(
            raw,
            indicator=target["indicator"],
            year=target["year"],
            source_url=url,
        )
        self.assertEqual(values["AAA"]["value"], "84.0")
        self.assertNotIn("BBB", values)
        self.assertEqual(metadata["non_null_country_count"], 1)
        self.assertEqual(metadata["null_record_count"], 1)

    def test_selection_is_complete_disjoint_capped_and_balanced(self) -> None:
        countries = {}
        first = {}
        second = {}
        for index in range(40):
            iso3 = f"X{index:02d}"
            region = f"R{index % 5}"
            countries[iso3] = {
                "iso3": iso3,
                "name": f"Country {index}",
                "region_id": region,
                "region_name": f"Region {region}",
            }
            record_a = {
                "indicator": design.TARGETS[0]["indicator"],
                "year": design.TARGETS[0]["year"],
                "value": str(index + 1),
                "source_url": "https://example/a",
                "response_sha256": "a" * 64,
            }
            record_b = {
                "indicator": design.TARGETS[1]["indicator"],
                "year": design.TARGETS[1]["year"],
                "value": str(index + 2),
                "source_url": "https://example/b",
                "response_sha256": "b" * 64,
            }
            first[iso3] = record_a
            second[iso3] = record_b
        second.pop("X00")
        selected, metrics = design.select_records(
            countries,
            [first, second],
            selected_count=20,
            region_cap=4,
        )
        self.assertEqual(len(selected), 20)
        self.assertNotIn("X00", {item["iso3"] for item in selected})
        self.assertEqual(metrics["selected_region_max"], 4)
        self.assertGreaterEqual(metrics["minimum_distinct_regions_per_task"], 3)
        again, _ = design.select_records(
            countries,
            [first, second],
            selected_count=20,
            region_cap=4,
        )
        self.assertEqual(
            [item["iso3"] for item in selected],
            [item["iso3"] for item in again],
        )

    def test_public_artifact_contains_hashes_not_private_values(self) -> None:
        selected = []
        for index in range(4):
            selected.append(
                {
                    "iso3": f"X{index:02d}",
                    "name": f"Private Country {index}",
                    "region_id": f"R{index}",
                    "region_name": f"Region {index}",
                    "values": [
                        {
                            "indicator": target["indicator"],
                            "year": target["year"],
                            "value": f"{index}.0",
                            "source_url": "https://example",
                            "response_sha256": str(index) * 64,
                        }
                        for target in design.TARGETS
                    ],
                }
            )
        with (
            patch.object(design, "_sha256", return_value="f" * 64),
            patch.object(design, "AUTHORIZATION", Path("authorization.json")),
        ):
            private, public = design.build_artifacts(
                selected,
                catalog_metadata={"response_sha256": "c" * 64},
                snapshot_metadata=[],
                metrics={"candidate_count": 4},
                created_at=0,
                git_head="a" * 40,
            )
        public_text = json.dumps(public, sort_keys=True)
        self.assertIn("Private Country 0", json.dumps(private))
        self.assertNotIn("Private Country", public_text)
        self.assertNotIn('"0.0"', public_text)
        self.assertFalse(
            private["gold_provenance_or_evaluator_read_before_prediction_freeze_authorized"]
        )

    def test_parent_authorizes_design_but_not_population_publication(self) -> None:
        self.assertTrue(design._parent_valid())
        parent = design._read(ROOT / design.PARENT)
        self.assertTrue(
            parent["authorization"][
                "fresh_disjoint_worldbank_population_and_protocol_design"
            ]
        )
        self.assertFalse(
            parent["authorization"]["population_gold_or_provenance_publication"]
        )

    def test_missing_publication_authority_precedes_network(self) -> None:
        with (
            patch.object(design, "_git", side_effect=["", "a" * 40, "a" * 40]),
            patch.object(design, "_parent_valid", return_value=True),
            patch.object(design, "_authorization_valid", return_value=False),
            patch.object(design, "_fetch_bytes") as fetch,
        ):
            with self.assertRaisesRegex(RuntimeError, "not authorized"):
                design.main()
        fetch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
