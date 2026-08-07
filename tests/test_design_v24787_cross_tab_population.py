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

from scripts import design_v24787_cross_tab_population as target  # noqa: E402


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
    for country_index in range(4):
        code = f"{chr(65 + country_index)}Z"
        for index in range(8):
            ordinal = len(rows) + 1
            rows.append(
                {
                    "label": f"Fresh Cross Tab Organization {ordinal}",
                    "canonical": f"fresh cross tab organization {ordinal}",
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


class V24787CrossTabPopulationTests(unittest.TestCase):
    def test_parent_authorizes_population_design_without_launch(self) -> None:
        self.assertTrue(target._parent_valid())
        value = target._read(ROOT / target.PARENT)
        self.assertTrue(value["authorization"]["fresh_disjoint_population_design"])
        self.assertFalse(value["authorization"]["activation_or_external_launch"])
        self.assertFalse(
            value["authorization"]["trusted_child_integration_or_runner_build"]
        )

    def test_history_adds_v24783_visible_contract_only(self) -> None:
        visible, canonical = target.historical_entities()
        self.assertEqual(len(visible), 4_816)
        self.assertEqual(len(canonical), 4_816)
        successor = target._v24783_entities()
        self.assertEqual(len(successor), 32)
        self.assertTrue(successor.issubset(visible))

    def test_candidate_uses_new_rank_seed_and_history_exclusion(self) -> None:
        row = record("01abc0001", "Fresh Cross Tab Company", "US", 1900)
        candidate = target.record_candidate(
            *row,
            historical_canonical=set(),
            canonical=lambda value: value.casefold(),
        )
        self.assertIsNotNone(candidate)
        expected = hashlib.sha256(
            f"{target.base.source.ROR_COMMIT}:v24787:01abc0001".encode()
        ).hexdigest()
        self.assertEqual(candidate["rank"], expected)
        self.assertIsNone(
            target.record_candidate(
                *row,
                historical_canonical={"fresh cross tab company"},
                canonical=lambda value: value.casefold(),
            )
        )

    def test_country_cap8_requires_four_country_fresh_vector(self) -> None:
        rows = [
            record(
                f"{country_index}{index:08d}",
                f"Organization {country_index}-{index}",
                f"{chr(65 + country_index)}Z",
                1700 + index,
            )
            for country_index in range(4)
            for index in range(9)
        ]
        selected, metrics = target.select_records(
            rows,
            historical_canonical=set(),
            canonical=lambda value: value.casefold(),
        )
        self.assertEqual(len(selected), 32)
        counts = sorted(Counter(item["country_code"] for item in selected).values())
        self.assertEqual(counts, [8, 8, 8, 8])
        self.assertEqual(metrics["selected_country_count_vector_sorted"], counts)
        with self.assertRaises(ValueError):
            target.select_records(
                rows,
                historical_canonical=set(),
                canonical=lambda value: value.casefold(),
                country_cap=9,
            )

    def test_visible_contract_has_only_opaque_id_and_question(self) -> None:
        rows = selected_rows()
        raw = target.contract_source(rows)
        text = raw.decode()
        ast.parse(text)
        self.assertIn("v24787", text)
        self.assertNotIn(rows[0]["record_id"], text)
        self.assertNotIn(rows[0]["founded"], text)
        self.assertNotIn(rows[0]["country"], text)

    def test_surfaces_freeze_one_unknown_target_and_read_accounting(self) -> None:
        rows = selected_rows()
        metrics = {
            "eligible_record_count": 1_100,
            "canonical_unique_candidate_count": 1_098,
            "candidate_country_count": 4,
            "selected_country_count": 4,
            "selected_country_max": 8,
            "selected_country_count_vector_sorted": [8, 8, 8, 8],
        }
        entries = [(f"{index:09d}.json", "a" * 40) for index in range(3_482)]
        historical_visible = {
            f"Historical Organization {index}" for index in range(4_816)
        }
        historical_canonical = {value.casefold() for value in historical_visible}
        public, private_raw, visible_raw = target.build_surfaces(
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
        target.validate_public(public)
        self.assertEqual(public["source"]["cumulative_preselection_tree_reads"], 4)
        self.assertEqual(
            public["source"]["cumulative_preselection_record_reads"], 13_928
        )
        target_rule = public["future_target_selection_contract"]
        self.assertTrue(
            target_rule["baseline_prediction_must_be_frozen_before_target_selection"]
        )
        self.assertEqual(
            target_rule["maximum_selected_baseline_unknown_target_per_task"], 1
        )
        self.assertFalse(
            target_rule[
                "private_truth_provenance_quality_or_evaluator_used_for_selection"
            ]
        )
        private = json.loads(private_raw)
        self.assertEqual(private["records"][0]["founded"], rows[0]["founded"])
        self.assertNotIn(rows[0]["founded"], visible_raw.decode())

    def test_resealed_target_or_launch_tamper_fails_closed(self) -> None:
        rows = selected_rows()
        metrics = {
            "eligible_record_count": 1_100,
            "canonical_unique_candidate_count": 1_098,
            "candidate_country_count": 4,
            "selected_country_count": 4,
            "selected_country_max": 8,
            "selected_country_count_vector_sorted": [8, 8, 8, 8],
        }
        entries = [(f"{index:09d}.json", "a" * 40) for index in range(3_482)]
        history = {f"Historical Organization {index}" for index in range(4_816)}
        public, _private, _visible = target.build_surfaces(
            tree_raw=b"immutable-tree",
            entries=entries,
            records=[("", "", b"", {})] * 3_482,
            selected=rows,
            metrics=metrics,
            historical_visible=history,
            historical_canonical={value.casefold() for value in history},
            now=0,
            git_head="b" * 40,
        )
        for mutate in (
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
