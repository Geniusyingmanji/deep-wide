from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v24790_full_catalog_selected_target as target  # noqa: E402
from deepwide_agent.v24365_entity_segment_projection import build_target_segment_catalog  # noqa: E402
from deepwide_agent.v24743_generic_record_binding import _render_table  # noqa: E402


def page(host: str, content: str) -> dict[str, object]:
    return {"host": host, "content": content, "fetch_integrity": True}


def tables(first: str = "Unknown", second: str = "Unknown") -> str:
    return _render_table(["Organization", "Founded"], [["Alpha Institute", first], ["Beta Labs", second]])


def cells(first: str = "Unknown", second: str = "Unknown") -> list[dict]:
    return [
        {"row_key": "Alpha Institute", "column": "Founded", "old_value": first},
        {"row_key": "Beta Labs", "column": "Founded", "old_value": second},
    ]


class V24790FullCatalogSelectedTargetTests(unittest.TestCase):
    def test_row_major_selects_first_unknown_after_known_cells(self) -> None:
        selected = target.select_first_unknown_target(tables("1990", "Unknown"))
        self.assertIsNotNone(selected)
        self.assertEqual(selected.row_key, "Beta Labs")
        self.assertIsNone(target.select_first_unknown_target(tables("1990", "2000")))

    def test_two_source_selected_target_closes_same_group_joint(self) -> None:
        catalog = build_target_segment_catalog(
            cells(),
            [page("one.example", "Alpha Institute was founded in 1999."), page("two.example.net", "Alpha Institute was established in 1999.")],
            [],
        )
        frozen = copy.deepcopy(catalog)
        receipt = target.build_selected_target_cross_tab(catalog, tables(), tables("1999", "Unknown"))
        self.assertEqual(catalog, frozen)
        self.assertIsNotNone(receipt)
        cross = receipt["cross_tab_receipt"]
        self.assertEqual(cross["target_count"], 1)
        self.assertEqual(cross["unknown_two_or_more_source_projection_group_count"], 1)
        self.assertEqual(cross["strict_joint_safe_change_group_count"], 1)
        self.assertFalse(receipt["single_target_catalog_rebuilt"])

    def test_adjacent_entity_relation_is_not_rebound_to_selected_target(self) -> None:
        content = "Alpha Institute and Beta Labs was founded in 2001."
        catalog = build_target_segment_catalog(cells(), [page("one.example", content)], [])
        receipt = target.build_selected_target_cross_tab(catalog, tables(), tables())
        self.assertIsNotNone(receipt)
        cross = receipt["cross_tab_receipt"]
        # Alpha is selected first.  Beta remains a delimiter in the validated
        # full catalog, so its 2001 relation cannot become an Alpha projection.
        self.assertEqual(cross["projection_group_count"], 0)
        self.assertEqual(cross["zero_projection_target_count"], 1)
        self.assertTrue(receipt["other_visible_entities_retained_as_segment_boundaries"])

    def test_no_unknown_returns_none_without_catalog_mutation(self) -> None:
        baseline = tables("1990", "2000")
        catalog = build_target_segment_catalog(cells("1990", "2000"), [], [])
        frozen = copy.deepcopy(catalog)
        self.assertIsNone(target.build_selected_target_cross_tab(catalog, baseline, baseline))
        self.assertEqual(catalog, frozen)

    def test_public_receipt_excludes_private_literals(self) -> None:
        catalog = build_target_segment_catalog(
            cells(), [page("private.example", "Alpha Institute was founded in 1987.")], []
        )
        receipt = target.build_selected_target_cross_tab(catalog, tables(), tables())
        encoded = json.dumps(receipt, ensure_ascii=False).casefold()
        for literal in ("alpha institute", "beta labs", "private.example", "1987"):
            self.assertNotIn(literal, encoded)

    def test_resealed_rebuild_or_authority_tamper_fails(self) -> None:
        catalog = build_target_segment_catalog(cells(), [], [])
        receipt = target.build_selected_target_cross_tab(catalog, tables(), tables())
        for mutate in (
            lambda value: value.__setitem__("single_target_catalog_rebuilt", True),
            lambda value: value.__setitem__("benchmark_launch_or_evaluator_authorized", True),
        ):
            altered = copy.deepcopy(receipt)
            mutate(altered)
            altered.pop("receipt_sha256")
            altered["receipt_sha256"] = target.payload_sha256(altered)
            with self.assertRaises(ValueError):
                target.validate_receipt(altered)

    def test_module_has_no_external_or_privileged_capability(self) -> None:
        tree = ast.parse(Path(target.__file__).read_text(encoding="utf-8"))
        forbidden = {"os", "pathlib", "requests", "socket", "subprocess", "httpx"}
        imported = {
            alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
        } | {
            (node.module or "").split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        }
        self.assertTrue(imported.isdisjoint(forbidden))


if __name__ == "__main__":
    unittest.main()
