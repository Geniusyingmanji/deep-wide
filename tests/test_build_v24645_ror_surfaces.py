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

from scripts import build_v24645_ror_surfaces as builder


class SurfaceBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private, self.population = builder._validate_parents()
        self.surfaces = builder.build_surfaces()

    def test_visible_contract_has_only_visible_entity_surface(self) -> None:
        source = self.surfaces[builder.CONTRACT]
        tree = ast.parse(source)
        assignments = {
            target.id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance((target := node.targets[0]), ast.Name)
            and target.id in {"ENTITY_GROUPS", "QUESTIONS"}
        }
        visible_labels = [
            entity for group in assignments["ENTITY_GROUPS"] for entity in group
        ]
        self.assertEqual(
            visible_labels, [record["label"] for record in self.private["records"]]
        )
        for record in self.private["records"]:
            self.assertNotIn(record["record_id"], source)
            self.assertNotIn(record["git_blob_sha1"], source)
            self.assertNotIn(record["record_bytes_sha256"], source)
        self.assertNotIn(str(builder.PRIVATE), source)
        self.assertNotIn("evaluation/", source)
        self.assertNotIn("external_evaluator", source)

    def test_gold_is_fixed_48_row_denominator(self) -> None:
        rows = list(csv.DictReader(io.StringIO(self.surfaces[builder.GOLD])))
        self.assertEqual(len(rows), 48)
        self.assertEqual(
            set(rows[0]), {"opaque_id", "Organization", "ROR ID", "Country code"}
        )
        self.assertEqual(len({row["opaque_id"] for row in rows}), 12)
        self.assertEqual(len({row["Organization"] for row in rows}), 48)
        self.assertEqual(len({row["ROR ID"] for row in rows}), 48)

    def test_provenance_binds_population_and_forbids_forward(self) -> None:
        value = json.loads(self.surfaces[builder.PROVENANCE])
        seal = value.pop("provenance_payload_sha256")
        self.assertEqual(builder.payload_sha256(value), seal)
        self.assertEqual(len(value["records"]), 48)
        self.assertFalse(value["forward_import_or_runtime_read_authorized"])
        self.assertFalse(value["gold_open_before_prediction_freeze_authorized"])

    def test_parent_only_authorizes_design(self) -> None:
        self.assertEqual(self.population["selected_count"], 48)
        self.assertTrue(
            self.population["authorization"][
                "visible_contract_and_evaluator_gold_design"
            ]
        )
        self.assertFalse(self.population["authorization"]["activation_or_launch"])


if __name__ == "__main__":
    unittest.main()
