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

from scripts import build_v24730_dual_namespace_surfaces as target  # noqa: E402


class V24730DualNamespaceSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.surfaces = target.build_surfaces()

    def test_builds_exact_physically_separated_surface_set(self) -> None:
        self.assertEqual(set(self.surfaces), set(target.SURFACES))
        self.assertEqual(len(self.surfaces), 5)
        for value in self.surfaces.values():
            self.assertTrue(value)

    def test_contract_contains_only_visible_tasks(self) -> None:
        source = self.surfaces[target.CONTRACT]
        tree = ast.parse(source)
        assignments = {
            name.id: ast.literal_eval(node.value)
            for node in tree.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance((name := node.targets[0]), ast.Name)
            and name.id in {"ROR_ENTITY_GROUPS", "WORLD_BANK_COUNTRY_GROUPS", "QUESTIONS"}
        }
        self.assertEqual(len(assignments["ROR_ENTITY_GROUPS"]), 12)
        self.assertEqual(len(assignments["WORLD_BANK_COUNTRY_GROUPS"]), 12)
        self.assertEqual(len(assignments["QUESTIONS"]), 24)
        self.assertNotIn("evaluation/", source)
        self.assertNotIn("record_bytes_sha256", source)
        self.assertNotIn("git_blob_sha1", source)

    def test_gold_denominators_and_namespaces_are_disjoint(self) -> None:
        ror = list(csv.DictReader(io.StringIO(self.surfaces[target.ROR_GOLD])))
        wb = list(csv.DictReader(io.StringIO(self.surfaces[target.WB_GOLD])))
        self.assertEqual(len(ror), 48)
        self.assertEqual(len(wb), 48)
        self.assertTrue({row["opaque_id"] for row in ror}.isdisjoint(row["opaque_id"] for row in wb))
        self.assertEqual(len({row["opaque_id"] for row in ror}), 12)
        self.assertEqual(len({row["opaque_id"] for row in wb}), 12)

    def test_provenance_is_evaluator_only_and_sealed(self) -> None:
        value = json.loads(self.surfaces[target.PROVENANCE])
        unsigned = dict(value)
        seal = unsigned.pop("provenance_payload_sha256")
        self.assertEqual(seal, target.payload_sha256(unsigned))
        self.assertFalse(value["forward_import_or_runtime_read_authorized"])
        self.assertFalse(value["gold_open_before_prediction_freeze_authorized"])
        self.assertEqual(len(value["ror_source"]["records"]), 48)
        self.assertEqual(len(value["worldbank_source"]["records"]), 96)

    def test_main_is_inert_without_separate_authorization(self) -> None:
        if not (ROOT / target.AUTHORIZATION).exists():
            self.assertFalse(target._authorization_valid())


if __name__ == "__main__":
    unittest.main()
