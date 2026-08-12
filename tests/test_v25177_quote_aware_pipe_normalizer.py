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

from deepwide_agent import v24257_score_first_runtime as score  # noqa: E402
from deepwide_agent import v25177_quote_aware_pipe_normalizer as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


COLUMNS = ("Package", "Version", "License", "NeedsCompilation")


def table(row: str) -> str:
    return (
        "```markdown\n"
        "| Package | Version | License | NeedsCompilation |\n"
        "| --- | --- | --- | --- |\n"
        f"{row}\n"
        "```"
    )


class V25177QuoteAwarePipeNormalizerTests(unittest.TestCase):
    def test_escaped_pipe_repairs_to_internal_and_final_representations(self) -> None:
        value = target.normalize_quote_aware_table(
            table(r"| alpha | 1.0 | MIT \| Apache-2.0 | no |"), COLUMNS
        )
        self.assertIsNotNone(value)
        internal, final, receipt = value or ("", "", {})
        checked, _errors = score.extract_valid_markdown_table(internal, COLUMNS)
        self.assertEqual(checked, internal)
        self.assertIn(target.INTERNAL_PIPE_ENTITY, internal)
        self.assertIn('"MIT | Apache-2.0"', final)
        self.assertEqual(receipt["escaped_pipe_cell_count"], 1)
        self.assertEqual(receipt["escaped_pipe_occurrence_count"], 1)
        self.assertGreater(receipt["adjacent_pipe_whitespace_count"], 0)

    def test_multiple_pipes_and_quotes_roundtrip_before_public_loader(self) -> None:
        value = target.normalize_quote_aware_table(
            table(r'| alpha | 1.0 | MIT "special" \| Apache \| BSD | no |'),
            COLUMNS,
        )
        self.assertIsNotNone(value)
        internal, final, receipt = value or ("", "", {})
        self.assertEqual(internal.count(target.INTERNAL_PIPE_ENTITY), 2)
        self.assertIn('"MIT ""special"" | Apache | BSD"', final)
        self.assertEqual(receipt["escaped_pipe_cell_count"], 1)
        self.assertEqual(receipt["escaped_pipe_occurrence_count"], 2)
        self.assertEqual(receipt["csv_quoted_cell_count"], 1)

    def test_no_escaped_pipe_or_row_width_only_does_not_trigger(self) -> None:
        valid = table("| alpha | 1.0 | MIT | no |")
        width = table("| alpha | 1.0 | MIT | Apache-2.0 | no |")
        self.assertIsNone(target.normalize_quote_aware_table(valid, COLUMNS))
        self.assertIsNone(target.normalize_quote_aware_table(width, COLUMNS))

    def test_partial_mixed_or_entity_collision_fails_closed(self) -> None:
        partial = (
            "```markdown\n"
            "| Package | Version | License | NeedsCompilation |\n"
            "| --- | --- | --- | --- |\n"
            r"| alpha | 1.0 | MIT \| Apache | no |"
            "\n| beta | 2.0 |\n```"
        )
        cases = (
            partial,
            table(r"| alpha | 1.0 | MIT \| Apache &#124; BSD | no |"),
            table(r"| alpha | 1.0 |  | no |"),
        )
        for value in cases:
            with self.subTest(value=value):
                self.assertIsNone(
                    target.normalize_quote_aware_table(value, COLUMNS)
                )

    def test_ambiguous_backslash_run_fails_closed(self) -> None:
        value = table(r"| alpha | 1.0 | MIT \\| Apache | no |")
        self.assertIsNone(target.normalize_quote_aware_table(value, COLUMNS))

    def test_multiple_candidate_tables_fail_closed(self) -> None:
        first = table(r"| alpha | 1.0 | MIT \| Apache | no |")
        second = table(r"| beta | 2.0 | BSD \| GPL | yes |")
        self.assertIsNone(
            target.normalize_quote_aware_table(first + "\n" + second, COLUMNS)
        )

    def test_header_reorder_or_separator_drift_is_not_repaired(self) -> None:
        reordered = (
            "| Version | Package | License | NeedsCompilation |\n"
            "| --- | --- | --- | --- |\n"
            r"| 1.0 | alpha | MIT \| Apache | no |"
        )
        bad_separator = (
            "| Package | Version | License | NeedsCompilation |\n"
            "| --- | --- | --- |\n"
            r"| alpha | 1.0 | MIT \| Apache | no |"
        )
        self.assertIsNone(target.normalize_quote_aware_table(reordered, COLUMNS))
        self.assertIsNone(
            target.normalize_quote_aware_table(bad_separator, COLUMNS)
        )

    def test_receipt_is_content_free_and_tamper_fails_closed(self) -> None:
        value = target.normalize_quote_aware_table(
            table(r"| alpha | 1.0 | MIT \| Apache | no |"), COLUMNS
        )
        self.assertIsNotNone(value)
        _internal, _final, receipt = value or ("", "", {})
        encoded = json.dumps(receipt, ensure_ascii=False)
        for forbidden in ("alpha", "MIT", "Apache", "Package", "https://"):
            self.assertNotIn(forbidden, encoded)
        for kind in ("count", "collision", "credit", "launch"):
            changed = copy.deepcopy(receipt)
            if kind == "count":
                changed["escaped_pipe_occurrence_count"] = 0
            elif kind == "collision":
                changed["internal_entity_collision_absent"] = False
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["benchmark_launch_or_external_protocol_authorized"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_module_is_pure_label_blind_and_effect_free(self) -> None:
        path = ROOT / "src/deepwide_agent/v25177_quote_aware_pipe_normalizer.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        imports: set[str] = set()
        privileged: set[str] = set()
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add((node.module or "").split(".")[0])
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value
                in {
                    "category",
                    "question_type",
                    "task_category",
                    "split",
                    "ground_truth",
                    "gold",
                    "answer_key",
                    "score",
                    "reward",
                }
            ):
                privileged.add(str(node.slice.value))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        self.assertTrue(
            imports.isdisjoint(
                {"os", "pathlib", "socket", "subprocess", "requests", "httpx", "openai"}
            )
        )
        self.assertEqual(privileged, set())
        self.assertTrue(
            calls.isdisjoint({"complete", "search_many", "fetch_urls", "create_connection"})
        )


if __name__ == "__main__":
    unittest.main()
