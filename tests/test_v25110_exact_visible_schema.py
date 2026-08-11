from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25110_exact_visible_schema as target  # noqa: E402
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402


QUESTION = (
    "Return one table. Columns exactly: Package | Latest version | "
    "Latest release date (YYYY-MM-DD) | Requires-Python. Use Unknown when absent."
)
COLUMNS = [
    "Package",
    "Latest version",
    "Latest release date (YYYY-MM-DD)",
    "Requires-Python",
]


class ExactVisibleSchemaTests(unittest.TestCase):
    def test_columns_exactly_pipe_declaration_is_reachable(self) -> None:
        self.assertEqual(target.extract_exact_visible_columns(QUESTION), COLUMNS)
        plan = target.validated_exact_plan({}, QUESTION, ScoreFirstLimits(search_queries=4))
        self.assertEqual(plan["columns"], COLUMNS)
        self.assertEqual(plan["robust_visible_schema_column_count"], 4)
        self.assertEqual(len(plan["queries"]), 4)

    def test_inherited_comma_and_following_line_forms_are_unchanged(self) -> None:
        self.assertEqual(
            target.extract_exact_visible_columns(
                "The column names are: Entity, Value. Return no prose."
            ),
            ["Entity", "Value"],
        )
        self.assertEqual(
            target.extract_exact_visible_columns(
                "Provide the following columns:\nProject | State | Start Year\nNotes: use NA."
            ),
            ["Project", "State", "Start Year"],
        )

    def test_ambiguous_duplicate_or_instruction_only_declaration_fails_closed(self) -> None:
        for question in (
            "Columns exactly: Name | Name. Return a table.",
            "Columns exactly: Please return a table.",
            "Mention columns exactly but do not provide a declaration.",
        ):
            with self.subTest(question=question):
                self.assertEqual(target.extract_exact_visible_columns(question), [])

    def test_source_has_no_effect_or_privileged_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25110_exact_visible_schema.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports: list[str] = []
        privileged: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                if node.slice.value in {
                    "category",
                    "question_type",
                    "split",
                    "ground_truth",
                    "answer_key",
                    "score",
                    "reward",
                }:
                    privileged.append(str(node.slice.value))
        for forbidden in ("os", "pathlib", "subprocess", "requests", "socket"):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        self.assertEqual(privileged, [])


if __name__ == "__main__":
    unittest.main()
