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

from scripts import build_v24671_ror_surfaces as builder  # noqa: E402


class V24671SurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.surfaces = builder.build_surfaces()

    def test_builds_visible_contract_and_separate_evaluator_files(self) -> None:
        self.assertEqual(
            set(self.surfaces), {builder.CONTRACT, builder.GOLD, builder.PROVENANCE}
        )
        rows = list(csv.DictReader(io.StringIO(self.surfaces[builder.GOLD])))
        self.assertEqual(len(rows), 48)

    def test_visible_contract_contains_no_gold_ids_hashes_or_private_path(self) -> None:
        source = self.surfaces[builder.CONTRACT]
        private, _population = builder._validate_parents()
        for record in private["records"]:
            self.assertNotIn(record["record_id"], source)
            self.assertNotIn(record["git_blob_sha1"], source)
            self.assertNotIn(record["record_bytes_sha256"], source)
        self.assertNotIn("evaluation/", source)
        self.assertNotIn("external_evaluator", source)
        self.assertNotIn(str(builder.PRIVATE), source)

    def test_contract_is_exactly_twelve_visible_tasks(self) -> None:
        tree = ast.parse(self.surfaces[builder.CONTRACT])
        values = {
            target.id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance((target := node.targets[0]), ast.Name)
            and target.id in {"ENTITY_GROUPS", "QUESTIONS"}
        }
        self.assertEqual(len(values["ENTITY_GROUPS"]), 12)
        self.assertTrue(all(len(group) == 4 for group in values["ENTITY_GROUPS"]))
        self.assertEqual(len(values["QUESTIONS"]), 12)

    def test_treatment_freezes_information_gain_and_strict_support(self) -> None:
        source = self.surfaces[builder.CONTRACT]
        self.assertIn('"unknown_target_cell_cap": 1', source)
        self.assertIn(
            '"targeted_fetch_capacity_concentrated_on_one_target": True', source
        )
        self.assertIn(
            '"visible_title_and_normalized_url_path_information_gain_priority": True',
            source,
        )
        self.assertIn(
            '"minimum_independent_local_exact_support_sources": 2', source
        )
        self.assertIn(
            '"decision_credit_before_safe_change_and_postfreeze_outer_utility": False',
            source,
        )

    def test_provenance_forbids_forward_access(self) -> None:
        value = json.loads(self.surfaces[builder.PROVENANCE])
        self.assertEqual(value["role"], "v24671_ror_gold_provenance")
        self.assertFalse(value["forward_import_or_runtime_read_authorized"])
        self.assertFalse(value["gold_open_before_prediction_freeze_authorized"])
        self.assertEqual(len(value["records"]), 48)


if __name__ == "__main__":
    unittest.main()
