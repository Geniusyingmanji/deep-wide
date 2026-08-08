from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v24924_visible_row_table_compactor as compact  # noqa: E402


QUESTION = """Return one table. Column names: Country | Metric A | Metric B.
<COUNTRIES>
1. Alpha Republic [ALP]
2. Beta Islands [BET]
</COUNTRIES>"""


class V24924VisibleRowTableCompactorTests(unittest.TestCase):
    def test_compacts_table_to_visible_rows_with_header(self) -> None:
        content = (
            "Context paragraph.\n"
            "| Country | Metric A |\n|---|---:|\n"
            "| filler one | 1 |\n| Alpha Republic | 9 |\n"
            "| filler two | 2 |\n| Beta Islands | 8 |"
        )
        result, counts = compact.compact_page_content(
            content, ["Alpha Republic", "Beta Islands"]
        )
        self.assertIn("| Country | Metric A |", result)
        self.assertIn("| Alpha Republic | 9 |", result)
        self.assertIn("| Beta Islands | 8 |", result)
        self.assertNotIn("filler one", result)
        self.assertEqual(counts["retained_table_row_count"], 2)
        self.assertEqual(counts["dropped_table_row_count"], 2)

    def test_nonmatching_table_and_non_table_text_are_preserved(self) -> None:
        content = "Intro text\n| Key | Value |\n|---|---|\n| unrelated | 5 |"
        result, counts = compact.compact_page_content(content, ["Alpha Republic"])
        self.assertEqual(result, content)
        self.assertEqual(counts["eligible_table_count"], 0)

    def test_multiple_tables_do_not_cross_bind_headers(self) -> None:
        content = (
            "| Country | A |\n|---|---:|\n| Alpha Republic | 1 |\n\n"
            "| Country | B |\n|---|---:|\n| Beta Islands | 2 |"
        )
        result, counts = compact.compact_page_content(
            content, ["Alpha Republic", "Beta Islands"]
        )
        self.assertEqual(result.count("| Country |"), 2)
        self.assertEqual(counts["eligible_table_count"], 2)

    def test_duplicate_visible_entity_does_not_duplicate_rows(self) -> None:
        content = "| Country | A |\n|---|---:|\n| Alpha Republic | 1 |"
        result, counts = compact.compact_page_content(
            content, ["Alpha Republic", "Alpha Republic"]
        )
        self.assertEqual(result.count("| Alpha Republic |"), 1)
        self.assertEqual(counts["retained_table_row_count"], 1)

    def test_visible_name_does_not_substring_match_another_entity(self) -> None:
        content = (
            "| Country | A |\n|---|---:|\n"
            "| Congo | 1 |\n| Democratic Republic of the Congo | 2 |"
        )
        result, counts = compact.compact_page_content(content, ["Congo"])
        self.assertIn("| Congo | 1 |", result)
        self.assertNotIn("Democratic Republic", result)
        self.assertEqual(counts["retained_table_row_count"], 1)

    def test_projection_exposes_all_requested_sparse_values(self) -> None:
        fillers = "\n".join(f"| filler-{index:03d} | {index} |" for index in range(300))
        pages = [
            {
                "title": "Official A",
                "url": "https://a.example/data",
                "content": (
                    "| Country | Metric A |\n|---|---:|\n"
                    + fillers
                    + "\n| Alpha Republic | 900 |\n| Beta Islands | 800 |"
                ),
            },
            {
                "title": "Official B",
                "url": "https://b.example/data",
                "content": (
                    "| Country | Metric B |\n|---|---:|\n"
                    + fillers
                    + "\n| Alpha Republic | 700 |\n| Beta Islands | 600 |"
                ),
            },
        ]
        value = compact.build_projection(QUESTION, pages)
        for expected in ("900", "800", "700", "600"):
            self.assertIn(expected, value["projection"])
        self.assertGreater(
            value["compaction_receipt"]["dropped_table_row_count"], 0
        )

    def test_projection_keeps_fixed_caps_and_zero_effect_delta(self) -> None:
        pages = [
            {
                "title": "Official",
                "url": "https://official.example/data",
                "content": "| Country | Metric A |\n|---|---:|\n| Alpha Republic | 9 |",
            }
        ]
        value = compact.build_projection(QUESTION, pages)
        receipt = value["projection_receipt"]
        self.assertEqual(receipt["policy"]["total_character_cap"], 30_000)
        self.assertEqual(receipt["policy"]["maximum_page_chars"], 5_000)
        self.assertFalse(
            value["additional_search_fetch_model_token_context_or_wall_cap"]
        )

    def test_replay_and_resealed_receipt_tamper_fail(self) -> None:
        pages = [
            {
                "title": "Official",
                "url": "https://official.example/data",
                "content": "| Country | Metric A |\n|---|---:|\n| Alpha Republic | 9 |",
            }
        ]
        value = compact.build_projection(QUESTION, pages)
        self.assertEqual(
            compact.validate_projection(value, question=QUESTION, pages=pages), value
        )
        tampered = copy.deepcopy(value["compaction_receipt"])
        tampered["dropped_table_row_count"] += 1
        tampered.pop("receipt_payload_sha256")
        tampered["receipt_payload_sha256"] = compact.payload_sha256(tampered)
        with self.assertRaises(ValueError):
            compact.validate_receipt(tampered)

    def test_entropy_and_privileged_inputs_assign_no_credit(self) -> None:
        pages = [
            {
                "title": "Official",
                "url": "https://official.example/data",
                "content": "| Country | Metric A |\n|---|---:|\n| Alpha Republic | 9 |",
            }
        ]
        value = compact.build_projection(QUESTION, pages)
        self.assertFalse(value["entropy_or_information_gain_assigns_credit"])
        self.assertFalse(
            value[
                "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
            ]
        )

    def test_runtime_ast_has_no_io_network_model_or_dynamic_execution(self) -> None:
        path = ROOT / "src/deepwide_agent/v24924_visible_row_table_compactor.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imports.update(
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        )
        self.assertTrue(
            imports.isdisjoint(
                {"os", "pathlib", "socket", "subprocess", "requests", "httpx", "openai"}
            )
        )
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(calls.isdisjoint({"open", "eval", "exec", "compile", "__import__"}))


if __name__ == "__main__":
    unittest.main()
