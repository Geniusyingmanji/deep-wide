from __future__ import annotations

import ast
import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24333_programmatic_support_catalog import CellTarget  # noqa: E402
from scripts import diagnose_v24777_v24775_fetch_fallback as target  # noqa: E402


ENTITIES = ("Alpha Institute", "Beta College", "Gamma School", "Delta Academy")


class V24777FetchFallbackDiagnosisTests(unittest.TestCase):
    def test_record_scopes_are_explicitly_separated(self) -> None:
        founded = CellTarget("Alpha Institute", "Founded", "Unknown")
        strict = "Alpha Institute\nFounded: 2017"
        near = "Heading\nFounded: 2017\nAlpha Institute"
        unique = "Alpha Institute\nProfile\nDescription\nFounded: 2017"
        self.assertEqual(
            target._strict_values(strict, entities=ENTITIES, target=founded),
            {"2017"},
        )
        self.assertEqual(
            target._strict_values(near, entities=ENTITIES, target=founded), set()
        )
        self.assertEqual(
            target._bounded_near_values(near, entities=ENTITIES, target=founded),
            {"2017"},
        )
        self.assertEqual(
            target._unique_target_page_values(
                unique, entities=ENTITIES, target=founded
            ),
            {"2017"},
        )

    def test_upper_bounds_do_not_cross_bind_another_visible_entity(self) -> None:
        founded = CellTarget("Alpha Institute", "Founded", "Unknown")
        text = "Alpha Institute\nBeta College\nFounded: 1999"
        self.assertEqual(
            target._bounded_near_values(text, entities=ENTITIES, target=founded),
            set(),
        )
        self.assertEqual(
            target._unique_target_page_values(text, entities=ENTITIES, target=founded),
            set(),
        )

    def test_scope_counts_partition_cells_and_require_two_sources(self) -> None:
        fields = {"a": "Founded", "b": "Country", "c": "Founded"}
        observations = {
            "a": {"v1": {"one.example"}},
            "b": {"v2": {"one.example", "two.example"}},
        }
        counts = target._scope_counts(observations, fields)
        self.assertEqual(counts["unreachable_cell_count"], 1)
        self.assertEqual(counts["one_source_same_value_cell_count"], 1)
        self.assertEqual(counts["two_source_same_value_cell_count"], 1)
        self.assertEqual(counts["safe_two_source_same_value_pair_count"], 1)

    def test_histogram_uses_closed_zero_one_two_plus_buckets(self) -> None:
        self.assertEqual(
            target._histogram([0, 1, 2, 3, 0]),
            {"0": 2, "1": 1, "2+": 2},
        )

    def test_publication_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "diagnosis.json"
            target.publish_new(path, {"count": 1})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {"count": 1})

    def test_runtime_source_is_label_blind_and_has_no_external_effect_import(self) -> None:
        tree = ast.parse(Path(target.__file__).read_text(encoding="utf-8"))
        privileged = {
            "answer_key",
            "benchmark_question_type",
            "category",
            "gold",
            "ground_truth",
            "mapping",
            "question_type",
            "reward",
            "score",
            "split",
            "task_category",
        }
        external = {"httpx", "requests", "socket", "subprocess"}
        findings = []
        for node in ast.walk(tree):
            key = None
            if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                key = node.slice.value
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in {"get", "pop", "setdefault"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
            ):
                key = node.args[0].value
            if isinstance(key, str) and key.casefold() in privileged:
                findings.append((node.lineno, key))
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [(node.module or "").split(".")[0]]
            findings.extend(
                (node.lineno, name) for name in names if name in external
            )
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
