from __future__ import annotations

import ast
import csv
import io
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import build_v24651_ror_surfaces as builder


class SurfaceBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private, cls.population = builder._validate_parents()
        cls.surfaces = builder.build_surfaces()

    def test_parent_only_authorizes_design(self) -> None:
        self.assertEqual(self.population["selected_count"], 48)
        self.assertEqual(self.population["historical_entity_count"], 4_480)
        self.assertTrue(
            self.population["authorization"][
                "visible_contract_and_evaluator_gold_design"
            ]
        )
        self.assertFalse(self.population["authorization"]["activation_or_launch"])

    def test_visible_contract_contains_only_visible_identity_surface(self) -> None:
        source = self.surfaces[builder.CONTRACT]
        tree = ast.parse(source)
        assignments = {
            node.targets[0].id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in {"ENTITY_GROUPS", "QUESTIONS", "TREATMENT"}
        }
        self.assertEqual(len(assignments["ENTITY_GROUPS"]), 12)
        self.assertTrue(all(len(group) == 4 for group in assignments["ENTITY_GROUPS"]))
        self.assertEqual(len(assignments["QUESTIONS"]), 12)
        self.assertEqual(assignments["TREATMENT"]["generic_fetch_cap"], 6)
        self.assertEqual(assignments["TREATMENT"]["unknown_target_lookup_cap"], 4)
        self.assertEqual(
            assignments["TREATMENT"]["targeted_lookup_max_page_chars"], 60_000
        )
        for record in self.private["records"]:
            self.assertNotIn(record["record_id"], source)
            self.assertNotIn(record["git_blob_sha1"], source)
            self.assertNotIn(record["record_bytes_sha256"], source)
        self.assertNotIn("evaluation/", source)
        self.assertNotIn("external_evaluator", source)

    def test_gold_is_fixed_48_row_denominator(self) -> None:
        rows = list(csv.DictReader(io.StringIO(self.surfaces[builder.GOLD])))
        self.assertEqual(len(rows), 48)
        self.assertEqual(len({row["opaque_id"] for row in rows}), 12)
        self.assertEqual(
            [row["Organization"] for row in rows],
            [record["label"] for record in self.private["records"]],
        )

    def test_provenance_binds_final_slice_and_forbids_forward(self) -> None:
        value = json.loads(self.surfaces[builder.PROVENANCE])
        self.assertEqual(value["slice_start_inclusive"], 3_000)
        self.assertEqual(value["slice_stop_exclusive"], 3_482)
        self.assertEqual(len(value["records"]), 48)
        self.assertFalse(value["forward_import_or_runtime_read_authorized"])
        self.assertFalse(value["gold_open_before_prediction_freeze_authorized"])


if __name__ == "__main__":
    unittest.main()
