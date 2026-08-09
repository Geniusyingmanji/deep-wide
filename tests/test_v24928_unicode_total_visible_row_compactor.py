from __future__ import annotations

import ast
import copy
import random
import string
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v24924_visible_row_table_compactor as parent  # noqa: E402
from deepwide_agent import v24928_unicode_total_visible_row_compactor as total  # noqa: E402


QUESTION = """Return one table. Column names: Entity | Metric.
<ENTITIES>
1. Alpha [ALP]
2. Beta [BET]
</ENTITIES>"""


class V24928UnicodeTotalVisibleRowCompactorTests(unittest.TestCase):
    def test_reproduces_parent_nfkc_expansion_failure(self) -> None:
        for glyph in ("½", "Ⅷ", "㎏", "℡", "™", "℃", "ﬃ", "㍑"):
            with self.subTest(glyph=glyph), self.assertRaises(ValueError):
                parent.compact_pages(
                    QUESTION,
                    [{"title": "Neutral", "url": "https://example.test", "content": glyph}],
                )

    def test_unicode_expansions_are_total(self) -> None:
        glyphs = "½ Ⅷ ㎏ ℡ ™ ℃ ﬃ ㍑"
        pages, receipt = total.compact_pages(
            QUESTION,
            [{"title": "Neutral", "url": "https://example.test", "content": glyphs}],
        )
        self.assertEqual(len(pages), 1)
        self.assertGreater(receipt["nfkc_expansion_characters"], 0)
        self.assertEqual(receipt["nfkc_expansion_page_count"], 1)
        self.assertGreaterEqual(
            receipt["normalized_input_content_characters"],
            receipt["output_content_characters"],
        )

    def test_nfkc_contraction_is_accounted(self) -> None:
        _pages, receipt = total.compact_pages(
            QUESTION,
            [{"title": "Neutral", "url": "https://example.test", "content": "ＡＢＣ"}],
        )
        self.assertEqual(receipt["nfkc_expansion_characters"], 0)
        self.assertEqual(receipt["nfkc_contraction_characters"], 0)
        self.assertEqual(receipt["normalized_input_content_characters"], 3)

    def test_projection_keeps_unicode_and_late_visible_values(self) -> None:
        fillers = "\n".join(f"| filler-{index:03d} | {index} |" for index in range(300))
        pages = [{
            "title": "Neutral",
            "url": "https://example.test/data",
            "content": (
                "Compatibility: ½ ℃ ™\n"
                "| Entity | Metric |\n|---|---:|\n"
                + fillers
                + "\n| Alpha | 991 |\n| Beta | 881 |"
            ),
        }]
        value = total.build_projection(QUESTION, pages)
        self.assertIn("991", value["projection"])
        self.assertIn("881", value["projection"])
        self.assertGreater(
            value["compaction_receipt"]["nfkc_expansion_characters"], 0
        )

    def test_caps_and_effect_budget_are_unchanged(self) -> None:
        value = total.build_projection(
            QUESTION,
            [{"title": "Neutral", "url": "https://example.test", "content": "½"}],
        )
        policy = value["projection_receipt"]["policy"]
        self.assertEqual(policy["total_character_cap"], 30_000)
        self.assertEqual(policy["maximum_page_chars"], 5_000)
        self.assertFalse(value["additional_search_fetch_model_token_context_or_wall_cap"])

    def test_raw_normalized_delta_invariant(self) -> None:
        _pages, receipt = total.compact_pages(
            QUESTION,
            [{"title": "Neutral", "url": "https://example.test", "content": "½™"}],
        )
        self.assertEqual(
            receipt["normalized_input_content_characters"]
            - receipt["raw_input_content_characters"],
            receipt["nfkc_expansion_characters"]
            - receipt["nfkc_contraction_characters"],
        )

    def test_resealed_length_tamper_fails(self) -> None:
        _pages, receipt = total.compact_pages(
            QUESTION,
            [{"title": "Neutral", "url": "https://example.test", "content": "½"}],
        )
        tampered = copy.deepcopy(receipt)
        tampered["normalized_input_content_characters"] -= 1
        tampered.pop("receipt_payload_sha256")
        tampered["receipt_payload_sha256"] = total.payload_sha256(tampered)
        with self.assertRaises(ValueError):
            total.validate_receipt(tampered)

    def test_strict_visible_cell_binding_is_preserved(self) -> None:
        content = (
            "| Entity | Metric |\n|---|---:|\n"
            "| Alpha | 1 |\n| Alpha Extended | 2 |\n| Beta | 3 |"
        )
        pages, receipt = total.compact_pages(
            QUESTION,
            [{"title": "Neutral", "url": "https://example.test", "content": content}],
        )
        self.assertIn("| Alpha | 1 |", pages[0]["content"])
        self.assertNotIn("Alpha Extended", pages[0]["content"])
        self.assertEqual(receipt["retained_table_row_count"], 2)

    def test_empty_and_invalid_pages_are_total(self) -> None:
        for pages in ([], [{}], [{"url": "", "content": "½"}]):
            with self.subTest(pages=pages):
                value = total.build_projection(QUESTION, pages)
                self.assertIsInstance(value["projection"], str)

    def test_random_unicode_structures_are_total(self) -> None:
        rng = random.Random(24928)
        alphabet = string.ascii_letters + " ½Ⅷ㎏℡™℃ﬃ㍑"
        for index in range(300):
            lines = []
            for _ in range(rng.randrange(1, 25)):
                kind = rng.randrange(4)
                if kind == 0:
                    lines.append("| Entity | Metric |")
                elif kind == 1:
                    lines.append("|---|---:|")
                elif kind == 2:
                    lines.append(f"| Alpha | {rng.randrange(1000)} |")
                else:
                    lines.append(
                        "".join(rng.choice(alphabet) for _ in range(rng.randrange(1, 80)))
                    )
            pages = [{
                "title": f"Neutral {index}",
                "url": f"https://example.test/{index}",
                "content": "\n".join(lines),
            }]
            total.build_projection(QUESTION, pages)

    def test_entropy_and_privileged_inputs_assign_no_credit(self) -> None:
        value = total.build_projection(
            QUESTION,
            [{"title": "Neutral", "url": "https://example.test", "content": "½"}],
        )
        self.assertFalse(value["entropy_or_information_gain_assigns_credit"])
        self.assertFalse(
            value[
                "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
            ]
        )

    def test_runtime_ast_has_no_io_network_model_or_dynamic_execution(self) -> None:
        path = ROOT / "src/deepwide_agent/v24928_unicode_total_visible_row_compactor.py"
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
