from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import (  # noqa: E402
    ScoreFirstLimits,
    _evidence_projection,
)
from deepwide_agent.v24911_long_page_evidence_packer import (  # noqa: E402
    PackingPolicy,
    build_packing,
    payload_sha256,
    validate_packing,
)


QUESTION = (
    "Return one Markdown table with columns: Country | Target Metric.\n"
    "<COUNTRIES>\nOmega Republic [OMG]\n</COUNTRIES>"
)


def page(index: int, content: str, *, url: str | None = None) -> dict[str, str]:
    return {
        "title": f"Official page {index}",
        "url": url or f"https://official{index}.example/data",
        "content": content,
    }


def legacy(pages: list[dict[str, str]]) -> str:
    batches = [
        {
            "query": "visible",
            "results": [
                {
                    "title": value["title"],
                    "url": value["url"],
                    "raw_content": value["content"],
                }
                for value in pages
            ],
        }
    ]
    return _evidence_projection([], batches, ScoreFirstLimits(page_chars=5_000))


def long_table() -> str:
    rows = ["| Country | Target Metric |", "|---|---:|"]
    rows.extend(f"| filler-{index:04d} | {index} |" for index in range(360))
    rows.append("| Omega Republic [OMG] | 999 |")
    return "\n".join(rows)


class V24911LongPageEvidencePackerTests(unittest.TestCase):
    def test_short_pages_are_exact_legacy_identity(self) -> None:
        pages = [page(1, "Omega Republic [OMG]: 999"), page(2, "supporting note")]
        self.assertEqual(build_packing(QUESTION, pages)["projection"], legacy(pages))

    def test_late_visible_row_is_recovered_beyond_legacy_prefix(self) -> None:
        pages = [page(1, "boilerplate " * 600 + "\n\nOmega Republic [OMG]: 999")]
        old = legacy(pages)
        result = build_packing(QUESTION, pages)
        self.assertNotIn("Omega Republic [OMG]: 999", old)
        self.assertIn("Omega Republic [OMG]: 999", result["projection"])
        self.assertGreaterEqual(result["candidate_visible_requirement_gain_count"], 1)

    def test_late_table_row_keeps_atomic_header(self) -> None:
        result = build_packing(QUESTION, [page(1, long_table())])
        if "| Omega Republic [OMG] | 999 |" in result["projection"]:
            self.assertIn("| Country | Target Metric |", result["projection"])
        self.assertEqual(result["orphan_selected_table_continuation_block_count"], 0)

    def test_active_per_page_and_total_caps_are_hard(self) -> None:
        pages = [page(index, (f"record-{index} value\n" * 2_000)) for index in range(1, 11)]
        result = build_packing(QUESTION, pages)
        self.assertTrue(all(value <= 5_000 for value in result["per_page_output_content_characters"]))
        self.assertLessEqual(result["projected_rendered_characters"], 120_000)
        self.assertTrue(all(value <= 12_000 for value in result["per_page_effective_content_characters"]))

    def test_more_than_frozen_fetch_cap_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            build_packing(QUESTION, [page(index, "x") for index in range(1, 12)])

    def test_duplicate_url_is_stably_removed(self) -> None:
        pages = [
            page(1, "first Omega Republic", url="https://official.example/data"),
            page(2, "duplicate", url="https://official.example/data"),
        ]
        result = build_packing(QUESTION, pages)
        self.assertEqual(result["input_page_count"], 1)
        self.assertNotIn("duplicate", result["projection"])

    def test_question_changes_only_long_page_selection(self) -> None:
        content = (
            "Alpha target 101\n" * 180
            + "neutral filler\n" * 180
            + "Beta target 202\n" * 180
        )
        policy = PackingPolicy(
            output_page_character_cap=1_200,
            block_character_cap=600,
            total_rendered_character_cap=22_000,
        )
        alpha = build_packing(
            "Return Alpha target", [page(1, content)], policy=policy
        )
        beta = build_packing(
            "Return Beta target", [page(1, content)], policy=policy
        )
        self.assertNotEqual(alpha["projection_sha256"], beta["projection_sha256"])

    def test_prefix_visible_coverage_never_regresses(self) -> None:
        content = "Omega Republic [OMG] prefix\n" + "x " * 5_000 + "\nTarget Metric: 999"
        result = build_packing(QUESTION, [page(1, content)])
        self.assertGreaterEqual(
            result["candidate_retained_supported_visible_requirement_group_count"],
            result["prefix_retained_supported_visible_requirement_group_count"],
        )
        self.assertTrue(result["candidate_requirement_coverage_not_less_than_prefix_baseline"])

    def test_entropy_is_shadow_only_and_credit_is_zero(self) -> None:
        result = build_packing(QUESTION, [page(1, long_table())])
        self.assertTrue(result["entropy_information_gain_shadow_only"])
        self.assertFalse(result["entropy_or_information_gain_assigns_credit"])
        self.assertFalse(
            result[
                "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
            ]
        )

    def test_replay_and_resealed_tamper_fail_closed(self) -> None:
        pages = [page(1, long_table())]
        result = build_packing(QUESTION, pages)
        self.assertEqual(result, validate_packing(result, question=QUESTION, pages=pages))
        altered = copy.deepcopy(result)
        altered["per_page_output_content_characters"][0] -= 1
        altered.pop("receipt_sha256")
        altered["receipt_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_packing(altered, question=QUESTION, pages=pages)

    def test_policy_drift_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            PackingPolicy(input_page_character_cap=5_000).validate()
        with self.assertRaises(ValueError):
            PackingPolicy(block_character_cap=5_001).validate()

    def test_runtime_ast_has_no_io_network_process_or_dynamic_execution(self) -> None:
        path = ROOT / "src/deepwide_agent/v24911_long_page_evidence_packer.py"
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
