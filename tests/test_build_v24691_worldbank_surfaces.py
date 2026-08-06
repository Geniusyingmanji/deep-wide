from __future__ import annotations

import ast
import csv
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import build_v24691_worldbank_surfaces as builder  # noqa: E402


class V24691WorldBankSurfaceBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private, self.population = builder._validate_parents()
        self.surfaces = builder.build_surfaces()

    def test_visible_contract_contains_identity_not_private_value_or_hash(self) -> None:
        source = self.surfaces[builder.CONTRACT]
        tree = ast.parse(source)
        assignments = {
            target.id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance((target := node.targets[0]), ast.Name)
            and target.id in {"COUNTRY_GROUPS", "QUESTIONS", "TARGETS"}
        }
        visible = [item for group in assignments["COUNTRY_GROUPS"] for item in group]
        expected = [
            (record["name"], record["iso3"])
            for group in self.private["groups"]
            for record in group
        ]
        self.assertEqual(visible, expected)
        for group in self.private["groups"]:
            for record in group:
                for value in record["values"]:
                    self.assertNotIn(value["value"], source)
                    self.assertNotIn(value["response_sha256"], source)
        self.assertNotIn("evaluation/", source)
        self.assertNotIn("external_evaluator", source)

    def test_gold_has_fixed_48_rows_and_96_values(self) -> None:
        rows = list(csv.DictReader(io.StringIO(self.surfaces[builder.GOLD])))
        self.assertEqual(len(rows), 48)
        self.assertEqual(len({row["opaque_id"] for row in rows}), 12)
        self.assertEqual(len({row["Country"] for row in rows}), 48)
        self.assertTrue(all(all(row[column] for column in list(row)[2:]) for row in rows))

    def test_provenance_binds_96_exact_official_targets(self) -> None:
        value = json.loads(self.surfaces[builder.PROVENANCE])
        seal = value.pop("provenance_payload_sha256")
        self.assertEqual(builder.payload_sha256(value), seal)
        self.assertEqual(len(value["records"]), 96)
        self.assertFalse(value["forward_import_or_runtime_read_authorized"])
        self.assertFalse(value["gold_open_before_prediction_freeze_authorized"])

    def test_generated_evaluator_has_three_arm_gate(self) -> None:
        source = self.surfaces[builder.EVALUATOR]
        tree = ast.parse(source)
        self.assertIn("target_value_minus_expanded", source)
        self.assertIn("expanded_minus_frozen", source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("v24686" in name for name in imports))

    def test_parent_authorizes_design_not_launch_or_evaluation(self) -> None:
        self.assertTrue(
            self.population["authorization"][
                "isolated_forward_contract_gold_provenance_and_evaluator_design"
            ]
        )
        self.assertFalse(self.population["authorization"]["activation_or_launch"])
        self.assertFalse(self.population["authorization"]["evaluator_access"])

    def test_missing_surface_authority_precedes_publication(self) -> None:
        with (
            patch.object(builder, "_git", side_effect=["", "a" * 40, "a" * 40]),
            patch.object(builder, "_authorization_valid", return_value=False),
            patch.object(builder, "build_surfaces") as build,
        ):
            with self.assertRaisesRegex(RuntimeError, "not authorized"):
                builder.main()
        build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
