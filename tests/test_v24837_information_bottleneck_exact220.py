from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24257_score_first_runtime as runtime  # noqa: E402
from deepwide_agent import v24834_coverage_margin_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24837_information_bottleneck_exact220_contract as contract  # noqa: E402
from scripts import run_v24837_information_bottleneck_exact220_task as child  # noqa: E402


class Limits:
    evidence_chars = 120_000


def batch(*results: dict[str, str]) -> dict[str, object]:
    return {"results": list(results)}


class V24837InformationBottleneckExact220Tests(unittest.TestCase):
    def test_task_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_only_projection_and_fresh_namespace_change_from_v24834(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, parent.EXECUTOR_CONCURRENCY)
        self.assertEqual(contract.MODEL_SLOT_CAP, parent.MODEL_SLOT_CAP)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)

    def test_projection_uses_fetched_pages_only(self) -> None:
        search = [batch({
            "title": "provider narrative",
            "url": "https://search.example/result",
            "content": "SHOULD_NOT_BE_ACTIVE",
        })]
        pages = [batch({
            "title": "page",
            "url": "https://page.example/a",
            "raw_content": "ACTIVE_PAGE_TEXT",
        })]
        evidence = child.information_bottleneck_evidence_projection(search, pages, Limits())
        self.assertIn("ACTIVE_PAGE_TEXT", evidence)
        self.assertNotIn("SHOULD_NOT_BE_ACTIVE", evidence)

    def test_projection_has_strict_16k_content_budget(self) -> None:
        pages = [batch(*(
            {
                "title": f"page {index}",
                "url": f"https://h{index}.example/a",
                "content": str(index) * 10_000,
            }
            for index in range(1, 8)
        ))]
        evidence = child.information_bottleneck_evidence_projection([], pages, Limits())
        self.assertLess(len(evidence), 20_000)
        self.assertGreater(len(evidence), 16_000)

    def test_projection_preserves_multiple_pages(self) -> None:
        pages = [batch(
            {"title": "one", "url": "https://one.example/a", "content": "A" * 5000},
            {"title": "two", "url": "https://two.example/a", "content": "B" * 5000},
            {"title": "three", "url": "https://three.example/a", "content": "C" * 5000},
        )]
        evidence = child.information_bottleneck_evidence_projection([], pages, Limits())
        self.assertIn("A" * 800, evidence)
        self.assertIn("B" * 800, evidence)
        self.assertIn("C" * 800, evidence)

    def test_duplicate_url_is_not_repeated(self) -> None:
        pages = [batch(
            {"title": "first", "url": "https://same.example/a", "content": "FIRST"},
            {"title": "second", "url": "https://same.example/a", "content": "SECOND"},
        )]
        evidence = child.information_bottleneck_evidence_projection([], pages, Limits())
        self.assertIn("FIRST", evidence)
        self.assertNotIn("SECOND", evidence)

    def test_parent_cap_below_projector_fails_closed(self) -> None:
        class TooSmall:
            evidence_chars = 15_999

        with self.assertRaises(RuntimeError):
            child.information_bottleneck_evidence_projection([], [], TooSmall())

    def test_entropy_credit_is_zero(self) -> None:
        self.assertEqual(contract.PROJECTOR_POLICY["total_character_cap"], 16_000)
        self.assertEqual(contract.TWO_WAVE_POLICY["information_gain_weight"], 0.0)

    def test_all_four_watchers_are_protected(self) -> None:
        self.assertEqual(
            [item["pid"] for item in contract.protected_watcher_snapshot()],
            [795336, 3061652, 2808901, 2889939],
        )

    def test_child_source_has_no_evaluator_import(self) -> None:
        tree = ast.parse(contract.CHILD.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))

    def test_configure_binds_runtime_projection(self) -> None:
        original = runtime._evidence_projection
        try:
            child.configure()
            self.assertIs(runtime._evidence_projection, child.information_bottleneck_evidence_projection)
        finally:
            runtime._evidence_projection = original


if __name__ == "__main__":
    unittest.main()
