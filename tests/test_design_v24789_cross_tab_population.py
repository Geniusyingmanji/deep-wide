from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24789_cross_tab_population as target  # noqa: E402


def record(record_id: str, label: str, country_code: str, established: int):
    value = {
        "id": f"https://ror.org/{record_id}",
        "status": "active",
        "types": ["company"],
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


def selected_rows() -> list[dict]:
    rows = []
    for country_index, count in enumerate([2, 10, 10, 10]):
        code = f"{chr(65 + country_index)}Z"
        for _index in range(count):
            ordinal = len(rows) + 1
            rows.append(
                {
                    "label": f"Fresh Successor Organization {ordinal}",
                    "canonical": f"fresh successor organization {ordinal}",
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


def metrics() -> dict:
    return {
        "eligible_record_count": 1_186,
        "canonical_unique_candidate_count": 1_184,
        "candidate_country_count": 4,
        "selected_country_count": 4,
        "selected_country_max": 10,
        "selected_country_count_vector_sorted": [2, 10, 10, 10],
    }


class V24789CrossTabPopulationTests(unittest.TestCase):
    def test_parent_freezes_minimum_cap_and_no_same_seed_retry(self) -> None:
        self.assertTrue(target._parent_valid())
        value = target._read(ROOT / target.PARENT)
        self.assertEqual(value["authorization"]["repaired_country_cap"], 10)
        self.assertFalse(
            value["authorization"]["same_seed_retry_resume_or_supplement"]
        )
        self.assertFalse(value["authorization"]["activation_or_external_launch"])

    def test_history_remains_4816_after_failed_v24787(self) -> None:
        visible, canonical = target.historical_entities()
        self.assertEqual(len(visible), 4_816)
        self.assertEqual(len(canonical), 4_816)

    def test_new_seed_replaces_failed_seed(self) -> None:
        row = record("01abc0001", "Fresh Successor Company", "US", 1900)
        candidate = target.record_candidate(
            *row,
            historical_canonical=set(),
            canonical=lambda value: value.casefold(),
        )
        self.assertIsNotNone(candidate)
        expected = hashlib.sha256(
            f"{target.failed.base.source.ROR_COMMIT}:v24789:01abc0001".encode()
        ).hexdigest()
        failed_rank = hashlib.sha256(
            f"{target.failed.base.source.ROR_COMMIT}:v24787:01abc0001".encode()
        ).hexdigest()
        self.assertEqual(candidate["rank"], expected)
        self.assertNotEqual(candidate["rank"], failed_rank)

    def test_selection_requires_exact_production_capacity_metrics(self) -> None:
        rows = [
            record(
                f"{country_index}{index:08d}",
                f"Organization {country_index}-{index}",
                f"{chr(65 + country_index)}Z",
                1700 + (index % 300),
            )
            for country_index, count in enumerate([4, 28, 68, 1_084])
            for index in range(count)
        ]
        rows.extend(
            [
                record("dup000001", "Duplicate Canonical Pair", "AZ", 1900),
                record("dup000002", "Duplicate Canonical Pair", "BZ", 1901),
            ]
        )
        # The synthetic vector has the same 1,184 unique candidates and four
        # countries as production.  Rank ordering plus cap10 must select 32.
        selected, observed = target.select_records(
            rows,
            historical_canonical=set(),
            canonical=lambda value: value.casefold(),
        )
        self.assertEqual(len(selected), 32)
        self.assertEqual(observed, metrics())
        with self.assertRaises(ValueError):
            target.select_records(
                rows,
                historical_canonical=set(),
                canonical=lambda value: value.casefold(),
                country_cap=8,
            )

    def test_visible_contract_excludes_private_values(self) -> None:
        rows = selected_rows()
        raw = target.contract_source(rows)
        text = raw.decode()
        ast.parse(text)
        self.assertIn("v24789", text)
        self.assertNotIn(rows[0]["record_id"], text)
        self.assertNotIn(rows[0]["founded"], text)
        self.assertNotIn(rows[0]["country"], text)

    def test_surfaces_freeze_cumulative_reads_and_target_contract(self) -> None:
        rows = selected_rows()
        entries = [(f"{index:09d}.json", "a" * 40) for index in range(3_482)]
        history = {f"Historical Organization {index}" for index in range(4_816)}
        public, private_raw, visible_raw = target.build_surfaces(
            tree_raw=b"immutable-tree",
            entries=entries,
            records=[("", "", b"", {})] * 3_482,
            selected=rows,
            metrics=metrics(),
            historical_visible=history,
            historical_canonical={value.casefold() for value in history},
            now=0,
            git_head="b" * 40,
        )
        target.validate_public(public)
        self.assertEqual(public["source"]["cumulative_preselection_tree_reads"], 6)
        self.assertEqual(
            public["source"]["cumulative_preselection_record_reads"], 20_892
        )
        self.assertFalse(
            public["failed_predecessor"]["same_seed_retry_resume_or_supplement"]
        )
        self.assertEqual(
            public["future_target_selection_contract"][
                "maximum_selected_baseline_unknown_target_per_task"
            ],
            1,
        )
        private = json.loads(private_raw)
        self.assertEqual(private["records"][0]["founded"], rows[0]["founded"])
        self.assertNotIn(rows[0]["founded"], visible_raw.decode())

    def test_resealed_seed_target_or_launch_tamper_fails_closed(self) -> None:
        rows = selected_rows()
        entries = [(f"{index:09d}.json", "a" * 40) for index in range(3_482)]
        history = {f"Historical Organization {index}" for index in range(4_816)}
        public, _private, _visible = target.build_surfaces(
            tree_raw=b"immutable-tree",
            entries=entries,
            records=[("", "", b"", {})] * 3_482,
            selected=rows,
            metrics=metrics(),
            historical_visible=history,
            historical_canonical={value.casefold() for value in history},
            now=0,
            git_head="b" * 40,
        )
        for mutate in (
            lambda value: value["source"].__setitem__("fixed_rank_seed", "v24787"),
            lambda value: value["future_target_selection_contract"].__setitem__(
                "maximum_selected_baseline_unknown_target_per_task", 2
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
