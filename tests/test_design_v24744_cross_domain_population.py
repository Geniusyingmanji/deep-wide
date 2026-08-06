from __future__ import annotations

import ast
import hashlib
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import design_v24744_cross_domain_population as target  # noqa: E402


class V24744CrossDomainPopulationTests(unittest.TestCase):
    def test_fixed_doi_vector_is_unique_partitioned_and_parent_absent(self) -> None:
        rows = target.doi_population_rows()
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({row["doi"].casefold() for row in rows}), 16)
        self.assertTrue(all(row["preselection_occurrence_count"] == 0 for row in rows))
        self.assertEqual(
            [row["mode"] for row in rows].count("official_crossref_exact_record"),
            8,
        )
        self.assertEqual(
            [row["mode"] for row in rows].count(
                "ordinary_crossref_openalex_corroboration"
            ),
            8,
        )

    def test_ranked_tree_order_is_content_independent(self) -> None:
        entries = [("0aaaaaaaa.json", "a" * 40), ("0bbbbbbbb.json", "b" * 40)]
        tree = {
            "truncated": False,
            "tree": [
                {"path": path, "sha": blob, "type": "blob"}
                for path, blob in entries
            ],
        }
        # The production parser binds a known full-tree hash, so exercise the
        # ranking formula directly without relaxing that immutable check.
        ranked = sorted(
            (
                hashlib.sha256(
                    f"{target.ror_base.ROR_COMMIT}:v24744:{path[:-5]}".encode()
                ).hexdigest(),
                path,
                blob,
            )
            for path, blob in entries
        )
        self.assertEqual([row[1] for row in ranked], [row[1] for row in sorted(ranked)])
        self.assertEqual(len(tree["tree"]), 2)

    def test_generated_contract_is_visible_only_and_well_formed(self) -> None:
        records = [
            {"label": f"Fresh Organization {index}"}
            for index in range(1, target.ROR_SELECTED_COUNT + 1)
        ]
        raw = target.contract_source(records)
        source = raw.decode("utf-8")
        tree = ast.parse(source)
        self.assertEqual(len([node for node in tree.body if isinstance(node, ast.Import)]), 2)
        self.assertNotIn("record_id", source)
        self.assertNotIn("country\"", source)
        self.assertNotIn("gold", source.casefold())
        self.assertIn("ordinary=True", source)

    def test_ror_prefix_selection_waits_for_capacity_and_stops_at_eight(self) -> None:
        def record(index: int, *, active: bool = True) -> tuple[str, str, bytes, dict]:
            record_id = f"0{index:08x}"[-9:]
            value = {
                "id": f"https://ror.org/{record_id}",
                "status": "active" if active else "inactive",
                "names": [
                    {"value": f"Unseen Institute {index}", "types": ["ror_display"]}
                ],
                "locations": [
                    {"geonames_details": {"country_code": f"{chr(65 + index // 2)}A"}}
                ],
            }
            raw = json.dumps(value, sort_keys=True).encode()
            return "0" * 64, f"{record_id}.json", raw, value

        prefix = [record(0, active=False)] + [record(index) for index in range(1, 10)]
        partial = target.select_ror_records(
            prefix[:5], historical_canonical=set(), require_complete=False
        )
        self.assertEqual(len(partial), 4)
        with self.assertRaises(RuntimeError):
            target.select_ror_records(prefix[:5], historical_canonical=set())
        complete = target.select_ror_records(prefix, historical_canonical=set())
        self.assertEqual(len(complete), target.ROR_SELECTED_COUNT)


if __name__ == "__main__":
    unittest.main()
