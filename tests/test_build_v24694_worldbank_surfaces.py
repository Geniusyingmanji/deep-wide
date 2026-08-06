from __future__ import annotations

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

from scripts import build_v24694_worldbank_surfaces as builder  # noqa: E402


class V24694WorldBankSurfaceRepairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.surfaces = builder.build_surfaces()

    def test_append_only_paths_and_namespaces(self) -> None:
        self.assertNotEqual(builder.CONTRACT, builder.predecessor.CONTRACT)
        self.assertNotEqual(builder.EVALUATOR, builder.predecessor.EVALUATOR)
        self.assertIn("v24694", self.surfaces[builder.CONTRACT])
        self.assertNotIn("v24691", self.surfaces[builder.CONTRACT])

    def test_evaluator_braces_are_repaired_and_executable(self) -> None:
        source = self.surfaces[builder.EVALUATOR]
        self.assertNotIn("{{", source)
        self.assertNotIn("}}", source)
        compile(source, str(builder.EVALUATOR), "exec")

    def test_gold_uses_new_fixed_opaque_namespace(self) -> None:
        rows = list(csv.DictReader(io.StringIO(self.surfaces[builder.GOLD])))
        self.assertEqual(len(rows), 48)
        identifiers = list(dict.fromkeys(row["opaque_id"] for row in rows))
        self.assertEqual(
            identifiers,
            [builder._new_id(index) for index in range(1, 13)],
        )

    def test_provenance_is_resealed_and_marks_exact_repair(self) -> None:
        value = json.loads(self.surfaces[builder.PROVENANCE])
        seal = value.pop("provenance_payload_sha256")
        self.assertEqual(builder.payload_sha256(value), seal)
        self.assertEqual(len(value["records"]), 96)
        self.assertTrue(
            value["append_only_repair"][
                "population_gold_values_and_provenance_unchanged"
            ]
        )

    def test_quarantine_is_required(self) -> None:
        self.assertTrue(builder._quarantine_valid())

    def test_missing_repair_authority_precedes_build(self) -> None:
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
