from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24750_host_local_population as target  # noqa: E402


class V24750HostLocalPopulationTests(unittest.TestCase):
    def test_fixed_doi_vector_is_unique_partitioned_and_parent_absent(self) -> None:
        rows = target.doi_population_rows()
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({row["doi"].casefold() for row in rows}), 16)
        self.assertTrue(
            all(row["preselection_occurrence_count"] == 0 for row in rows)
        )
        self.assertEqual(
            [row["mode"] for row in rows].count(
                "official_crossref_exact_record"
            ),
            8,
        )
        self.assertEqual(
            [row["mode"] for row in rows].count(
                "ordinary_crossref_openalex_corroboration"
            ),
            8,
        )

    def test_prior_history_adds_v24744_and_is_canonical_disjoint(self) -> None:
        visible, canonical = target.prior_ror_entities()
        self.assertEqual(len(visible), target.EXPECTED_PRIOR_ROR_COUNT)
        self.assertEqual(len(canonical), target.EXPECTED_PRIOR_ROR_COUNT)
        self.assertTrue(
            {
                entity
                for group in target.prior_contract.ROR_GROUPS
                for entity in group
            }.issubset(visible)
        )

    def test_generated_contract_uses_new_population_and_visible_only_surface(self) -> None:
        records = [
            {"label": f"Fresh Host Local Institute {index}"}
            for index in range(1, target.ROR_SELECTED_COUNT + 1)
        ]
        source = target.contract_source(records).decode("utf-8")
        ast.parse(source)
        self.assertIn("v24750", source)
        self.assertNotIn("v24744", source)
        self.assertIn(target.OFFICIAL_CROSSREF_DOIS[0], source)
        self.assertIn(target.ORDINARY_DUAL_SOURCE_DOIS[-1], source)
        self.assertNotIn("record_id", source)
        self.assertNotIn("gold", source.casefold())


if __name__ == "__main__":
    unittest.main()
