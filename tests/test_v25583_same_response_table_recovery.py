from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25583_same_response_table_recovery as target  # noqa: E402


COLUMNS = ("Name", "Value")
QUESTION = "Return a table with columns Name and Value."


class V25583SameResponseTableRecoveryTests(unittest.TestCase):
    def test_frozen_parent_output_is_byte_preserved(self) -> None:
        raw = "```markdown\n| Name | Value |\n| --- | --- |\n| Alpha | 1 |\n```"
        table, receipt = target.normalize_synthesis(raw, COLUMNS, QUESTION)
        self.assertEqual(table, raw)
        self.assertEqual(receipt["mode"], "parent_exact")
        self.assertEqual(receipt["candidate_parser_count"], 0)

    def test_missing_or_weak_pipe_separator_is_recovered(self) -> None:
        cases = (
            (
                "| Value | Name |\n| 1 | Alpha |\n| 2 | Beta |",
                "recovered_missing_pipe_separator",
            ),
            (
                "| Name | Value |\n| -- | :--: |\n| Alpha | 1 |",
                "recovered_weak_pipe_separator",
            ),
        )
        for raw, mode in cases:
            with self.subTest(mode=mode):
                table, receipt = target.normalize_synthesis(raw, COLUMNS, QUESTION)
                self.assertEqual(receipt["mode"], mode)
                self.assertEqual(receipt["input_row_count"], receipt["output_row_count"])
                self.assertIn("| Alpha | 1 |", table or "")

    def test_strict_csv_and_tsv_are_recovered(self) -> None:
        cases = (
            ('Value,Name\n"one, exact",Alpha\n,Empty', "recovered_csv", "Unknown"),
            ("Name\tValue\nAlpha\tone\nBeta\ttwo", "recovered_tsv", "two"),
        )
        for raw, mode, expected in cases:
            with self.subTest(mode=mode):
                table, receipt = target.normalize_synthesis(raw, COLUMNS, QUESTION)
                self.assertEqual(receipt["mode"], mode)
                self.assertIn(expected, table or "")
                self.assertEqual(receipt["input_row_count"], 2)

    def test_strict_json_records_and_matrix_are_recovered(self) -> None:
        cases = (
            (
                '[{"Value":"1","Name":"Alpha"},{"Value":null,"Name":"Beta"}]',
                "recovered_json_records",
                "Unknown",
            ),
            (
                '{"columns":["Name","Value"],"rows":[["Alpha","1"]]}',
                "recovered_json_matrix",
                "| Alpha | 1 |",
            ),
        )
        for raw, mode, expected in cases:
            with self.subTest(mode=mode):
                table, receipt = target.normalize_synthesis(raw, COLUMNS, QUESTION)
                self.assertEqual(receipt["mode"], mode)
                self.assertIn(expected, table or "")

    def test_malformed_ambiguous_or_semantic_rewrite_cases_fail_closed(self) -> None:
        cases = (
            "| Name | Value |\n| Alpha | 1 |\n| ragged | extra | more |",
            "| Name | Value |\n| Alpha | one | two |",
            '[{"Name":"Alpha","Value":1}]',
            '[{"Name":"Alpha","Value":"one","Extra":"x"}]',
            '{"columns":["Name","Value"],"rows":[["Alpha","one|two"]]}',
            "| Name | Value |\n| Alpha | 1 |\n\n| Name | Value |\n| Beta | 2 |",
            "```json\n[{\"Name\":\"Alpha\",\"Value\":\"1\"}]\n``` trailing",
        )
        for raw in cases:
            with self.subTest(raw=raw):
                table, receipt = target.normalize_synthesis(raw, COLUMNS, QUESTION)
                self.assertIsNone(table)
                self.assertEqual(receipt["mode"], "unrecoverable")
                self.assertEqual(receipt["output_row_count"], 0)

    def test_chinese_empty_cell_uses_visible_language_unknown_only(self) -> None:
        table, receipt = target.normalize_synthesis(
            "名称,数值\n甲,", ("名称", "数值"), "请返回名称和数值表格。"
        )
        self.assertEqual(receipt["mode"], "recovered_csv")
        self.assertIn("| 甲 | 未知 |", table or "")
        self.assertEqual(receipt["filled_empty_cell_count"], 1)

    def test_receipt_tamper_fails(self) -> None:
        _table, value = target.normalize_synthesis(
            "Name,Value\nAlpha,1", COLUMNS, QUESTION
        )
        for field, replacement in (
            ("output_row_count", 2),
            ("positive_signed_credit_count", 1),
            ("benchmark_launch_or_evaluator_authorized", True),
        ):
            changed = copy.deepcopy(value)
            changed[field] = replacement
            changed["receipt_payload_sha256"] = target.payload_sha256(
                {
                    key: item
                    for key, item in changed.items()
                    if key != "receipt_payload_sha256"
                }
            )
            with self.subTest(field=field), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_contract_is_label_blind_zero_effect_and_zero_credit(self) -> None:
        value = target.integration_contract()
        self.assertTrue(value["frozen_parent_always_runs_first"])
        self.assertTrue(value["same_response_bytes_only"])
        self.assertFalse(
            value[
                "additional_model_search_fetch_token_context_wall_or_network_budget"
            ]
        )
        self.assertFalse(
            value[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )
        self.assertEqual(value["positive_signed_credit_count"], 0)

    def test_source_has_no_privileged_or_external_capability(self) -> None:
        source = ROOT / "src/deepwide_agent/v25583_same_response_table_recovery.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imports: list[str] = []
        privileged = {
            "category",
            "question_type",
            "task_category",
            "ground_truth",
            "answer_key",
            "reward",
        }
        hits: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ):
                if node.slice.value in privileged:
                    hits.append(str(node.slice.value))
        self.assertEqual(hits, [])
        self.assertFalse(
            any(
                name in {
                    "os",
                    "socket",
                    "subprocess",
                    "urllib",
                    "requests",
                    "httpx",
                    "pathlib",
                }
                or "evaluator" in name
                for name in imports
            )
        )


if __name__ == "__main__":
    unittest.main()
