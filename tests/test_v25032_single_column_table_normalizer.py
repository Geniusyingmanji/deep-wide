from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    extract_valid_markdown_table,
)
from deepwide_agent.v25032_single_column_table_normalizer import (  # noqa: E402
    normalize_candidate_table,
)


class SingleColumnTableNormalizerTests(unittest.TestCase):
    def test_canonical_one_column_table_remains_exact(self) -> None:
        raw = """```markdown
| Name |
| --- |
| Alice |
```"""
        table, receipt = normalize_candidate_table(
            raw, ["Name"], unknown_marker="Unknown"
        )
        self.assertEqual(table, raw)
        self.assertEqual(receipt["status"], "exact")
        self.assertEqual(receipt["nonempty_factual_cell_rewrite_count"], 0)
        parsed, errors = extract_valid_markdown_table(table, ["Name"])
        self.assertEqual(parsed, raw)
        self.assertEqual(errors, [])

    def test_wrong_header_is_recovered_without_rewriting_factual_cells(self) -> None:
        raw = """| Person |
| :---: |
| Alice [A-1] |
| 张三（甲） |
"""
        table, receipt = normalize_candidate_table(
            raw, ["Name"], unknown_marker="Unknown"
        )
        self.assertEqual(receipt["mode"], "single_column_positional_header")
        self.assertEqual(receipt["additional_model_search_or_fetch_call_count"], 0)
        self.assertIn("| Alice [A-1] |", table)
        self.assertIn("| 张三（甲） |", table)
        self.assertNotIn("| Person |", table)
        parsed, errors = extract_valid_markdown_table(table, ["Name"])
        self.assertEqual(parsed, table)
        self.assertEqual(errors, [])

    def test_empty_cell_only_uses_explicit_unknown_marker(self) -> None:
        raw = "| Name |\n| --- |\n|  |"
        table, receipt = normalize_candidate_table(
            raw, ["Name"], unknown_marker="Unknown"
        )
        self.assertEqual(receipt["filled_empty_cell_count"], 1)
        self.assertIn("| Unknown |", table)

    def test_bare_rows_and_malformed_rows_fail_closed(self) -> None:
        for raw in (
            "Name\n---\nAlice",
            "| Name |\n| --- |\nAlice",
            "| Name |\n| --- |\n| Alice | extra",
            "| Name |\n| --- |",
        ):
            with self.subTest(raw=raw):
                table, receipt = normalize_candidate_table(
                    raw, ["Name"], unknown_marker="Unknown"
                )
                self.assertIsNone(table)
                self.assertEqual(receipt["status"], "unrecoverable")

    def test_multiple_candidate_tables_are_ambiguous(self) -> None:
        raw = """| Name |
| --- |
| Alice |

| Name |
| --- |
| Bob |
"""
        table, receipt = normalize_candidate_table(
            raw, ["Name"], unknown_marker="Unknown"
        )
        self.assertIsNone(table)
        self.assertEqual(receipt["mode"], "ambiguous_single_column_tables")
        self.assertEqual(receipt["single_column_candidate_table_count"], 2)

    def test_escaped_or_extra_pipe_fails_closed(self) -> None:
        for raw in (
            "| Name |\n| --- |\n| Alice\\|Bob |",
            "| Name | Other |\n| --- | --- |\n| Alice | Bob |",
        ):
            with self.subTest(raw=raw):
                table, receipt = normalize_candidate_table(
                    raw, ["Name"], unknown_marker="Unknown"
                )
                self.assertIsNone(table)
                self.assertEqual(receipt["status"], "unrecoverable")

    def test_multi_column_behavior_is_identical_to_frozen_parent(self) -> None:
        from deepwide_agent.v24259_deterministic_table_normalizer import (
            normalize_candidate_table as parent,
        )

        raw = "Name | Value\n--- | ---\nAlice | 7"
        expected = parent(raw, ["Entity", "Value"], unknown_marker="Unknown")
        actual = normalize_candidate_table(
            raw, ["Entity", "Value"], unknown_marker="Unknown"
        )
        self.assertEqual(actual, expected)

    def test_module_has_no_effect_or_evaluator_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25032_single_column_table_normalizer.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "socket",
            "deepwidebench",
            "eval",
        ):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        for forbidden in (
            "ground_truth",
            "answer_key",
            "question_type",
            "benchmark_category",
            "results.csv",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
