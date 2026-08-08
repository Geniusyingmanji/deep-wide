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

from deepwide_agent import v24842_atomic_table_header_closure as control  # noqa: E402
from deepwide_agent import v24846_atomic_table_header_30k_profile as candidate  # noqa: E402


QUESTION = "Column names: Country | Target Metric. Return rows for Omega Republic and Sigma State."


def pages() -> list[dict[str, str]]:
    output = []
    for page_index in range(1, 9):
        lines = ["| Country | Target Metric |", "|---|---:|"]
        lines.extend(
            f"| filler-{page_index}-{row:03d} | {page_index * 1000 + row} |"
            for row in range(180)
        )
        if page_index == 6:
            lines.append("| Omega Republic | 999 |")
        if page_index == 8:
            lines.append("| Sigma State | 777 |")
        output.append(
            {
                "title": f"Official page {page_index}",
                "url": f"https://official{page_index}.example/table",
                "content": "\n".join(lines),
            }
        )
    return output


class V24846AtomicTableHeader30kProfileTests(unittest.TestCase):
    def test_only_total_cap_changes_from_v24842_profile(self) -> None:
        policy = candidate.profile_policy()
        self.assertEqual(policy.total_character_cap, 30_000)
        self.assertEqual(policy.maximum_page_chars, control.DEFAULT_MAXIMUM_PAGE_CHARS)
        self.assertEqual(policy.block_character_cap, control.DEFAULT_BLOCK_CHARACTER_CAP)
        self.assertEqual(policy.maximum_visible_groups, control.DEFAULT_MAXIMUM_VISIBLE_GROUPS)
        self.assertEqual(policy.maximum_query_terms, control.DEFAULT_MAXIMUM_QUERY_TERMS)

    def test_candidate_uses_more_context_under_same_raw_pages(self) -> None:
        raw = pages()
        parent = control.build_projection(QUESTION, raw)
        value = candidate.build_projection(QUESTION, raw)
        receipt = value["content_free_receipt"]
        self.assertLessEqual(parent["projected_rendered_characters"], 16_000)
        self.assertLessEqual(receipt["projected_rendered_characters"], 30_000)
        self.assertGreater(
            receipt["projected_rendered_characters"],
            parent["projected_rendered_characters"],
        )
        self.assertEqual(
            receipt["orphan_selected_table_continuation_block_count"], 0
        )

    def test_content_free_receipt_exposes_closure_trigger_counts(self) -> None:
        lines = ["| Country | Target Metric |", "|---|---:|"]
        lines.extend(f"| filler-{row:03d} | {row} |" for row in range(60))
        lines.append("| Omega Republic | 999 |")
        raw = [
            {
                "title": "Official long table",
                "url": "https://official.example/table",
                "content": "\n".join(lines),
            }
        ]
        value = candidate.build_projection(
            "Return the row for Omega Republic.", raw
        )
        receipt = value["content_free_receipt"]
        self.assertIn("selected_table_continuation_block_count", receipt)
        self.assertIn("table_header_dependency_addition_count", receipt)
        self.assertGreater(receipt["selected_table_continuation_block_count"], 0)
        self.assertGreaterEqual(receipt["table_header_dependency_addition_count"], 1)

    def test_receipt_contains_no_visible_or_fetched_content_or_hashes(self) -> None:
        value = candidate.build_projection(QUESTION, pages())
        encoded = json.dumps(value["content_free_receipt"], sort_keys=True)
        for prohibited in (
            "Omega Republic",
            "Sigma State",
            "official1.example",
            "filler-1-001",
            "projection_sha256",
            "content_sha256",
            "visible_question_sha256",
        ):
            self.assertNotIn(prohibited, encoded)

    def test_non_table_projection_is_control_identical_when_below_16k(self) -> None:
        raw = [
            {
                "title": "Official record",
                "url": "https://official.example/record",
                "content": "Omega Republic Target Metric: 999\nSigma State Target Metric: 777",
            }
        ]
        parent = control.build_projection(QUESTION, raw)["projection"]
        value = candidate.build_projection(QUESTION, raw)["projection"]
        self.assertEqual(value, parent)

    def test_projection_and_receipt_replay(self) -> None:
        raw = pages()
        value = candidate.build_projection(QUESTION, raw)
        self.assertEqual(
            value,
            candidate.validate_projection(value, question=QUESTION, pages=raw),
        )
        self.assertEqual(
            value["content_free_receipt"],
            candidate.validate_receipt(value["content_free_receipt"]),
        )

    def test_resealed_orphan_tamper_fails_closed(self) -> None:
        raw = pages()
        value = candidate.build_projection(QUESTION, raw)
        altered = copy.deepcopy(value)
        receipt = altered["content_free_receipt"]
        receipt["orphan_selected_table_continuation_block_count"] = 1
        receipt.pop("receipt_payload_sha256")
        receipt["receipt_payload_sha256"] = candidate.payload_sha256(receipt)
        altered.pop("artifact_payload_sha256")
        altered["artifact_payload_sha256"] = candidate.payload_sha256(altered)
        with self.assertRaises(ValueError):
            candidate.validate_projection(altered, question=QUESTION, pages=raw)

    def test_entropy_credit_remains_zero(self) -> None:
        value = candidate.build_projection(QUESTION, pages())
        self.assertTrue(value["entropy_information_gain_shadow_only"])
        self.assertFalse(value["entropy_or_information_gain_assigns_credit"])

    def test_runtime_ast_has_no_io_network_process_or_dynamic_execution(self) -> None:
        source = ROOT / "src/deepwide_agent/v24846_atomic_table_header_30k_profile.py"
        tree = ast.parse(source.read_text(encoding="utf-8"))
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
                {"os", "pathlib", "socket", "subprocess", "requests", "httpx"}
            )
        )
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(
            calls.isdisjoint({"open", "eval", "exec", "compile", "__import__"})
        )


if __name__ == "__main__":
    unittest.main()
