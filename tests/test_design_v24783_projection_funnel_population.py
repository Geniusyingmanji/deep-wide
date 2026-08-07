from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24783_projection_funnel_population as target  # noqa: E402


def record(
    record_id: str,
    label: str,
    country_code: str,
    established: int,
    *,
    types: list[str] | None = None,
    display_count: int = 1,
):
    value = {
        "id": f"https://ror.org/{record_id}",
        "status": "active",
        "types": ["company"] if types is None else types,
        "names": [
            {"value": label if index == 0 else f"{label} Duplicate", "types": ["ror_display"]}
            for index in range(display_count)
        ],
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


def selected_rows() -> list[dict]:
    rows = []
    counts = [4, 7, 7, 7, 7]
    for country_index, count in enumerate(counts):
        code = f"{chr(65 + country_index)}Z"
        for index in range(count):
            ordinal = len(rows) + 1
            rows.append(
                {
                    "label": f"Visible Projection Organization {ordinal}",
                    "canonical": f"visible projection organization {ordinal}",
                    "record_id": f"{ordinal:09d}",
                    "founded": str(1700 + ordinal),
                    "country": f"Private Country {code}",
                    "country_code": code,
                    "ror_types": ["company"],
                    "git_blob_sha1": f"{ordinal:040x}",
                    "record_bytes_sha256": f"{ordinal:064x}",
                }
            )
    return rows


class V24783ProjectionFunnelPopulationTests(unittest.TestCase):
    def test_capacity_parent_authorizes_exact_design_without_launch(self) -> None:
        self.assertTrue(target._parent_valid())
        parent = target._read(ROOT / target.PARENT)
        self.assertTrue(
            parent["authorization"]["implement_exact_v24783_population_rule"]
        )
        self.assertFalse(parent["authorization"]["activation_or_external_launch"])
        self.assertEqual(
            parent["probe_results"]["all_types_capacity_curve"][
                "country_count_vector_at_minimum_cap_sorted"
            ],
            [4, 7, 7, 7, 7],
        )

    def test_history_adds_only_v24779_visible_contract(self) -> None:
        visible, canonical = target.historical_entities()
        self.assertEqual(len(visible), 4_784)
        self.assertEqual(len(canonical), 4_784)
        successor = {
            entity
            for group in target.v24779_contract.ENTITY_GROUPS
            for entity in group
        }
        self.assertEqual(len(successor), 32)
        self.assertTrue(successor.issubset(visible))

    def test_any_nonempty_type_is_eligible_and_bad_surfaces_fail_closed(self) -> None:
        row = record("01abc0001", "Fresh Projection Company", "US", 1900)
        candidate = target.record_candidate(
            *row,
            historical_canonical=set(),
            canonical=lambda value: value.casefold(),
        )
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["ror_types"], ["company"])
        for bad in (
            record("01abc0002", "No Type", "US", 1900, types=[]),
            record("01abc0003", "Unsafe (Parenthesis)", "US", 1900),
            record("01abc0004", "Two Displays", "US", 1900, display_count=2),
            record("01abc0005", "Bad Year", "US", 999),
        ):
            self.assertIsNone(
                target.record_candidate(
                    *bad,
                    historical_canonical=set(),
                    canonical=lambda value: value.casefold(),
                )
            )
        self.assertIsNone(
            target.record_candidate(
                *row,
                historical_canonical={"fresh projection company"},
                canonical=lambda value: value.casefold(),
            )
        )

    def test_country_cap7_selects_fixed_32_distribution(self) -> None:
        rows = [
            record(
                f"{country_index}{index:08d}",
                f"Organization {country_index}-{index}",
                f"{chr(65 + country_index)}Z",
                1700 + index,
            )
            for country_index, count in enumerate([4, 8, 8, 8, 8])
            for index in range(count)
        ]
        selected, metrics = target.select_records(
            rows,
            historical_canonical=set(),
            canonical=lambda value: value.casefold(),
        )
        self.assertEqual(len(selected), 32)
        counts = sorted(Counter(item["country_code"] for item in selected).values())
        self.assertEqual(counts, [4, 7, 7, 7, 7])
        self.assertEqual(metrics["selected_country_count_vector_sorted"], counts)
        with self.assertRaises(ValueError):
            target.select_records(
                rows,
                historical_canonical=set(),
                canonical=lambda value: value.casefold(),
                country_cap=6,
            )

    def test_visible_contract_returns_only_opaque_id_and_question(self) -> None:
        rows = selected_rows()
        raw = target.contract_source(rows)
        text = raw.decode()
        ast.parse(text)
        self.assertIn("v24783", text)
        self.assertNotIn("ENTITY_GROUPS", text)
        self.assertNotIn(rows[0]["record_id"], text)
        self.assertNotIn(rows[0]["founded"], text)
        self.assertNotIn(rows[0]["country"], text)

    def test_surfaces_freeze_exact_read_accounting_and_physical_separation(self) -> None:
        rows = selected_rows()
        metrics = {
            "eligible_record_count": 1_218,
            "canonical_unique_candidate_count": 1_216,
            "candidate_country_count": 5,
            "selected_country_count": 5,
            "selected_country_max": 7,
            "selected_country_count_vector_sorted": [4, 7, 7, 7, 7],
        }
        entries = [(f"{index:09d}.json", "a" * 40) for index in range(3_482)]
        records = [("", "", b"", {})] * 3_482
        historical_visible = {f"Historical Organization {index}" for index in range(4_784)}
        historical_canonical = {value.casefold() for value in historical_visible}
        public, private_raw, visible_raw = target.build_surfaces(
            tree_raw=b"immutable-tree",
            entries=entries,
            records=records,
            selected=rows,
            metrics=metrics,
            historical_visible=historical_visible,
            historical_canonical=historical_canonical,
            now=0,
            git_head="b" * 40,
        )
        target.validate_public(public)
        self.assertEqual(public["source"]["cumulative_preselection_tree_reads"], 3)
        self.assertEqual(
            public["source"]["cumulative_preselection_record_reads"], 10_446
        )
        private = json.loads(private_raw)
        self.assertEqual(private["records"][0]["founded"], rows[0]["founded"])
        self.assertNotIn(rows[0]["founded"], visible_raw.decode())
        self.assertFalse(
            public["surface_separation"][
                "public_selected_identity_field_value_url_page_emitted"
            ]
        )

    def test_resealed_read_or_launch_tamper_fails_closed(self) -> None:
        rows = selected_rows()
        metrics = {
            "eligible_record_count": 1_218,
            "canonical_unique_candidate_count": 1_216,
            "candidate_country_count": 5,
            "selected_country_count": 5,
            "selected_country_max": 7,
            "selected_country_count_vector_sorted": [4, 7, 7, 7, 7],
        }
        entries = [(f"{index:09d}.json", "a" * 40) for index in range(3_482)]
        historical_visible = {f"Historical Organization {index}" for index in range(4_784)}
        historical_canonical = {value.casefold() for value in historical_visible}
        public, _private, _visible = target.build_surfaces(
            tree_raw=b"immutable-tree",
            entries=entries,
            records=[("", "", b"", {})] * 3_482,
            selected=rows,
            metrics=metrics,
            historical_visible=historical_visible,
            historical_canonical=historical_canonical,
            now=0,
            git_head="b" * 40,
        )
        for mutate in (
            lambda value: value["source"].__setitem__(
                "cumulative_preselection_record_reads", 6_964
            ),
            lambda value: value["authorization"].__setitem__(
                "activation_or_external_launch", True
            ),
        ):
            altered = copy.deepcopy(public)
            mutate(altered)
            altered.pop("design_payload_sha256")
            altered["design_payload_sha256"] = target.payload_sha256(altered)
            with self.assertRaises(RuntimeError):
                target.validate_public(altered)

    def test_create_only_publication(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "surface.json"
            target._publish(path, b"{}\n")
            with self.assertRaises(FileExistsError):
                target._publish(path, b"{}\n")


if __name__ == "__main__":
    unittest.main()
