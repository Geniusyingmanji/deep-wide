from __future__ import annotations

import copy
import hashlib
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24829_target_cell_disjoint_population as target  # noqa: E402


class Response:
    def __init__(self, raw: bytes, status: int = 200) -> None:
        self.raw = raw
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, limit: int) -> bytes:
        return self.raw[:limit]


class Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 0.01
        return self.value


def fixture(count: int = 170):
    countries: dict[str, dict[str, str]] = {}
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
        for position, spec in enumerate(target.TARGETS):
            snapshots[position][iso3] = {
                "indicator": spec["indicator"],
                "year": spec["year"],
                "value": str(index + position / 10),
                "source_url": "https://api.worldbank.org/example",
                "response_sha256": f"{position + 1:064x}",
            }
    return countries, snapshots


def receipt(index: int) -> dict:
    raw = f"payload-{index}".encode()
    _body, value = target.fetch_bytes_bounded(
        "https://api.worldbank.org/example",
        opener=lambda *_args, **_kwargs: Response(raw),
        monotonic=Clock(),
    )
    return value


class V24829TargetCellDisjointPopulationTests(unittest.TestCase):
    def test_selection_is_unrequested_preoutcome_remainder(self) -> None:
        value = target.target_selection_contract(ROOT)
        self.assertFalse(value["network_or_transport_outcome_field_read_for_selection"])
        self.assertEqual(
            value["selected_unrequested_target_key_vector"],
            ["SH.STA.BASS.ZS@2022", "SL.UEM.TOTL.ZS@2023"],
        )
        self.assertEqual(
            value["already_requested_target_key_vector"],
            ["EG.ELC.ACCS.ZS@2022", "SH.H2O.BASW.ZS@2022"],
        )

    def test_cumulative_historical_boundary_is_exact(self) -> None:
        entities, cells, targets, manifest = target.historical_boundary(ROOT)
        self.assertEqual(len(manifest), 5)
        self.assertEqual(len(entities), 217)
        self.assertEqual(len(cells), 672)
        self.assertEqual(len(targets), 8)
        self.assertTrue(
            {(item["indicator"], item["year"]) for item in target.TARGETS}.isdisjoint(
                targets
            )
        )

    def test_selects_fixed_128_and_prioritizes_novel_entities(self) -> None:
        countries, snapshots = fixture()
        historical_entities = set(sorted(countries)[:150])
        old_targets = {("OLD.A", "2022"), ("OLD.B", "2022")}
        old_cells = {
            (iso3, indicator, year)
            for iso3 in historical_entities
            for indicator, year in old_targets
        }
        selected, metrics = target.select_population(
            countries, snapshots, historical_entities, old_cells, old_targets
        )
        self.assertEqual(len(selected), 128)
        self.assertEqual(metrics["selected_entity_novel_count"], 20)
        self.assertEqual(metrics["selected_entity_overlap_count"], 108)
        self.assertEqual(metrics["selected_gold_cell_overlap_count"], 0)

    def test_target_or_cell_overlap_fails_closed(self) -> None:
        countries, snapshots = fixture()
        first = target.TARGETS[0]
        with self.assertRaisesRegex(RuntimeError, "target/year"):
            target.select_population(
                countries,
                snapshots,
                set(),
                set(),
                {(first["indicator"], first["year"])},
            )
        iso3 = next(iter(countries))
        with self.assertRaisesRegex(RuntimeError, "gold cell"):
            target.select_population(
                countries,
                snapshots,
                set(),
                {(iso3, first["indicator"], first["year"])},
                set(),
            )

    def test_incomplete_values_are_excluded_before_selection(self) -> None:
        countries, snapshots = fixture()
        for iso3 in list(countries)[:10]:
            snapshots[1][iso3] = {**snapshots[1][iso3], "value": None}
        selected, metrics = target.select_population(
            countries, snapshots, set(), set(), set()
        )
        self.assertEqual(len(selected), 128)
        self.assertEqual(metrics["complete_candidate_count"], 160)

    def test_bounded_snapshot_timeout_then_success_is_receipted(self) -> None:
        outcomes = [TimeoutError("slow"), Response(b"payload")]
        sleeps = []

        def opener(_request, *, timeout):
            self.assertEqual(timeout, 90)
            value = outcomes.pop(0)
            if isinstance(value, BaseException):
                raise value
            return value

        raw, value = target.fetch_bytes_bounded(
            "https://api.worldbank.org/example",
            opener=opener,
            sleeper=sleeps.append,
            monotonic=Clock(),
        )
        self.assertEqual(raw, b"payload")
        self.assertEqual(value["attempt_count"], 2)
        self.assertEqual(sleeps, [0.5])
        self.assertFalse(value["url_or_response_content_emitted"])

    def test_bounded_snapshot_exhaustion_and_host_guard(self) -> None:
        with self.assertRaisesRegex(ValueError, "URL"):
            target.fetch_bytes_bounded("https://example.org/not-worldbank")
        calls = []
        with self.assertRaisesRegex(RuntimeError, "exhausted"):
            target.fetch_bytes_bounded(
                "https://api.worldbank.org/example",
                opener=lambda *_args, **kwargs: (
                    calls.append(kwargs["timeout"]),
                    (_ for _ in ()).throw(TimeoutError("slow")),
                )[1],
                sleeper=lambda _value: None,
                monotonic=Clock(),
            )
        self.assertEqual(calls, [90, 90, 90])

    def test_artifacts_are_private_public_split_and_deterministic(self) -> None:
        countries, snapshots = fixture(128)
        selected, metrics = target.select_population(
            countries, snapshots, set(countries), set(), set()
        )
        selection = {
            "rule": "fixture",
            "network_or_transport_outcome_field_read_for_selection": False,
        }
        private, public = target.build_artifacts(
            selected,
            transport_receipts=[receipt(index) for index in range(3)],
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
            selection_contract=selection,
            metrics=metrics,
            created_at=1,
            git_head="5" * 40,
            authorization_audit_sha256="6" * 64,
        )
        self.assertEqual(len(private["groups"]), 32)
        self.assertTrue(
            private["disjointness_scope"][
                "targets_never_previously_requested_or_evaluated"
            ]
        )
        self.assertFalse(public["scope"]["entity_disjoint_claim"])
        self.assertEqual(public["transport"]["url_count"], 3)
        self.assertNotIn("Country 0", target.json.dumps(public))
        reselection, remetrics = target.select_population(
            copy.deepcopy(countries), copy.deepcopy(snapshots), set(countries), set(), set()
        )
        self.assertEqual(selected, reselection)
        self.assertEqual(metrics, remetrics)


if __name__ == "__main__":
    unittest.main()
