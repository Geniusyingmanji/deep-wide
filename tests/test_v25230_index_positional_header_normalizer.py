from __future__ import annotations

import ast
import copy
import json
import random
import string
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import (  # noqa: E402
    v24257_score_first_runtime as score,
    v25230_index_positional_header_normalizer as target,
)
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


COLUMNS = ("名称", "年份")


def table(header: str, separator: str, *rows: str) -> str:
    return "\n".join((header, separator, *rows))


def active(receipt: dict) -> str:
    return next(
        name for name, count in receipt["disposition_counts"].items() if count
    )


class V25230IndexPositionalHeaderNormalizerTests(unittest.TestCase):
    def test_composes_generic_index_drop_and_positional_header(self) -> None:
        raw = table(
            "| No. | Name | Year |",
            "| --- | --- | --- |",
            "| 1 | Alpha | 2024 |",
            "| 2 | Beta | 2025 |",
        )
        normalized, receipt = target.normalize_index_positional_header_table(
            raw, COLUMNS, unknown_marker="Unknown"
        )
        self.assertIsNotNone(normalized)
        self.assertEqual(active(receipt), "accepted")
        self.assertEqual(receipt["accepted_data_row_count"], 2)
        self.assertIn("| Alpha | 2024 |", normalized or "")
        self.assertNotIn("| 1 |", normalized or "")
        checked, _errors = score.extract_valid_markdown_table(
            normalized or "", COLUMNS
        )
        self.assertEqual(checked, normalized)

    def test_empty_remaining_cell_uses_only_existing_unknown_marker(self) -> None:
        raw = table(
            "| # | Alias A | Alias B |",
            "| --- | --- | --- |",
            "| 7 | Alpha |  |",
        )
        normalized, receipt = target.normalize_index_positional_header_table(
            raw, COLUMNS, unknown_marker="未知"
        )
        self.assertEqual(receipt["filled_empty_cell_count"], 1)
        self.assertIn("| Alpha | 未知 |", normalized or "")

    def test_parent_already_supported_drop_index_state_is_not_claimed(self) -> None:
        raw = table(
            "| # | 名称 | 年份 |",
            "| --- | --- | --- |",
            "| 1 | Alpha | 2024 |",
        )
        normalized, receipt = target.normalize_index_positional_header_table(
            raw, COLUMNS, unknown_marker="Unknown"
        )
        self.assertIsNone(normalized)
        self.assertEqual(active(receipt), "no_positional_after_index_header_reject")

    def test_non_generic_or_nonleading_index_and_two_extras_fail_closed(self) -> None:
        cases = {
            "nongeneric": table(
                "| Rank | Alias A | Alias B |",
                "| --- | --- | --- |",
                "| 1 | Alpha | 2024 |",
            ),
            "nonleading": table(
                "| Alias A | No. | Alias B |",
                "| --- | --- | --- |",
                "| Alpha | 1 | 2024 |",
            ),
            "two_extra": table(
                "| # | Extra | Alias A | Alias B |",
                "| --- | --- | --- | --- |",
                "| 1 | X | Alpha | 2024 |",
            ),
        }
        for name, raw in cases.items():
            with self.subTest(name=name):
                normalized, receipt = target.normalize_index_positional_header_table(
                    raw, COLUMNS, unknown_marker="Unknown"
                )
                self.assertIsNone(normalized)
                self.assertFalse(receipt["accepted"])

    def test_invalid_required_schema_or_unknown_marker_fails_closed(self) -> None:
        raw = table(
            "| # | A | B |", "| --- | --- | --- |", "| 1 | x | y |"
        )
        cases = (
            (("Name", " Name "), "Unknown"),
            (tuple(f"c{i}" for i in range(21)), "Unknown"),
            (COLUMNS, "bad|marker"),
            ("not-a-sequence", "Unknown"),
        )
        for columns, marker in cases:
            with self.subTest(columns=columns, marker=marker):
                normalized, receipt = target.normalize_index_positional_header_table(
                    raw, columns, unknown_marker=marker
                )
                self.assertIsNone(normalized)
                self.assertEqual(active(receipt), "invalid_required_columns_reject")

    def test_missing_data_and_malformed_width_fail_closed(self) -> None:
        missing = table("| # | A | B |", "| --- | --- | --- |")
        malformed = table(
            "| # | A | B |",
            "| --- | --- | --- |",
            "| 1 | Alpha | 2024 |",
            "| 2 | Beta |",
        )
        for raw, disposition in (
            (missing, "missing_data_rows_reject"),
            (malformed, "malformed_data_width_reject"),
        ):
            normalized, receipt = target.normalize_index_positional_header_table(
                raw, COLUMNS, unknown_marker="Unknown"
            )
            self.assertIsNone(normalized)
            self.assertEqual(active(receipt), disposition)

    def test_early_structural_funnel_dispositions_are_exact(self) -> None:
        cases = (
            ("plain prose", "no_pipe_group_reject"),
            ("| # | A | B |\n| 1 | x | y |", "no_separator_row_reject"),
            (
                table(
                    "| # | A | B |",
                    "| --- | --- |",
                    "| 1 | x | y |",
                ),
                "separator_width_mismatch_reject",
            ),
        )
        for raw, disposition in cases:
            with self.subTest(disposition=disposition):
                normalized, receipt = target.normalize_index_positional_header_table(
                    raw, COLUMNS, unknown_marker="Unknown"
                )
                self.assertIsNone(normalized)
                self.assertEqual(active(receipt), disposition)

    def test_escaped_pipe_and_internal_entity_collision_fail_closed(self) -> None:
        escaped = table(
            "| # | A | B |",
            "| --- | --- | --- |",
            r"| 1 | Alpha \| Beta | 2024 |",
        )
        collision = table(
            "| # | A | B |",
            "| --- | --- | --- |",
            "| 1 | Alpha&#124;Beta | 2024 |",
        )
        for raw, disposition in (
            (escaped, "escaped_pipe_reject"),
            (collision, "internal_entity_collision_reject"),
        ):
            normalized, receipt = target.normalize_index_positional_header_table(
                raw, COLUMNS, unknown_marker="Unknown"
            )
            self.assertIsNone(normalized)
            self.assertEqual(active(receipt), disposition)

    def test_multiple_safe_candidates_are_rejected_even_if_identical(self) -> None:
        one = table(
            "| # | A | B |",
            "| --- | --- | --- |",
            "| 1 | Alpha | 2024 |",
        )
        normalized, receipt = target.normalize_index_positional_header_table(
            one + "\nprose\n" + one, COLUMNS, unknown_marker="Unknown"
        )
        self.assertIsNone(normalized)
        self.assertEqual(active(receipt), "multiple_structural_candidates_reject")
        self.assertEqual(receipt["exact_parser_roundtrip_candidate_count"], 2)

    def test_receipt_is_content_free_and_tamper_fails_closed(self) -> None:
        raw = table(
            "| # | Secret Header A | Secret Header B |",
            "| --- | --- | --- |",
            "| 1 | Secret Alpha | Secret 2024 |",
        )
        _normalized, receipt = target.normalize_index_positional_header_table(
            raw, COLUMNS, unknown_marker="Unknown"
        )
        encoded = json.dumps(receipt, ensure_ascii=False, sort_keys=True)
        for forbidden in (
            "Secret",
            "Alpha",
            "2024",
            "名称",
            "年份",
            "task_",
            "https://",
        ):
            self.assertNotIn(forbidden, encoded)
        for kind in ("count", "disposition", "credit", "launch", "content"):
            changed = copy.deepcopy(receipt)
            if kind == "count":
                changed["accepted_data_row_count"] += 1
            elif kind == "disposition":
                changed["disposition_counts"]["accepted"] = 0
                changed["disposition_counts"]["missing_data_rows_reject"] = 1
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            elif kind == "launch":
                changed[
                    "runtime_integration_prediction_change_or_external_launch_authorized"
                ] = True
            else:
                changed["raw_header"] = "leak"
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_receipt(changed)

    def test_arbitrary_string_surface_is_total_and_receipts_validate(self) -> None:
        generator = random.Random(25230)
        alphabet = string.printable + "中文|\\\r\n"
        for _ in range(300):
            text = "".join(generator.choice(alphabet) for _ in range(generator.randrange(160)))
            normalized, receipt = target.normalize_index_positional_header_table(
                text, COLUMNS, unknown_marker="Unknown"
            )
            self.assertEqual(target.validate_receipt(receipt), receipt)
            if normalized is not None:
                checked, _errors = score.extract_valid_markdown_table(
                    normalized, COLUMNS
                )
                self.assertEqual(checked, normalized)

    def test_module_is_label_blind_and_has_no_direct_effect_imports(self) -> None:
        path = ROOT / "src/deepwide_agent/v25230_index_positional_header_normalizer.py"
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
            calls.isdisjoint(
                {"complete", "search_many", "fetch_urls", "create_connection", "open"}
            )
        )


if __name__ == "__main__":
    unittest.main()
