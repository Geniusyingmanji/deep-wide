from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v24846_atomic_table_header_30k_profile as control  # noqa: E402
from deepwide_agent.v24921_target_value_coverage_projector import (  # noqa: E402
    build_projection,
    payload_sha256,
    validate_projection,
    validate_receipt,
    visible_row_targets,
    visible_target_columns,
)


QUESTION = """Return exactly one Markdown table. Column names: Country | Target Metric [TM] @2024.
<COUNTRIES>
1. Omega Republic [OMG]
2. Beta Islands [BET]
</COUNTRIES>"""


def page(index: int, content: str) -> dict[str, str]:
    return {
        "title": f"Official page {index}",
        "url": f"https://official-{index}.example/data",
        "content": content,
    }


class V24921TargetValueCoverageProjectorTests(unittest.TestCase):
    def test_visible_rows_and_value_columns_are_separated(self) -> None:
        self.assertEqual(visible_row_targets(QUESTION), ["omega republic", "beta islands"])
        self.assertEqual(
            visible_target_columns(QUESTION), ["target metric", "tm"]
        )

    def test_joint_binding_beats_independent_phrase_distractors(self) -> None:
        distractors = [
            page(index, ("Target Metric [TM] @2024 glossary and methodology.\n" * 80))
            for index in range(1, 7)
        ]
        records = page(
            7,
            "| Country | Target Metric [TM] @2024 |\n|---|---:|\n"
            "| Omega Republic | 999 |\n| Beta Islands | 777 |",
        )
        result = build_projection(QUESTION, [*distractors, records])
        self.assertIn("| Omega Republic | 999 |", result["projection"])
        self.assertIn("| Beta Islands | 777 |", result["projection"])
        self.assertGreaterEqual(result["supported_target_value_pair_count"], 2)
        self.assertEqual(result["missed_target_value_pair_count"], 0)

    def test_candidate_pair_coverage_is_not_less_than_fixed_30k_control(self) -> None:
        pages = [
            page(1, "Omega Republic background only.\n" * 300),
            page(2, "Target Metric [TM] @2024 definitions only.\n" * 300),
            page(
                3,
                "| Country | Target Metric [TM] @2024 |\n|---|---:|\n"
                + "\n".join(f"| filler-{i} | {i} |" for i in range(120))
                + "\n| Omega Republic | 999 |",
            ),
        ]
        fixed = control.build_projection(QUESTION, pages)
        candidate = build_projection(QUESTION, pages)
        self.assertLessEqual(candidate["projected_rendered_characters"], 30_000)
        self.assertGreaterEqual(
            candidate["retained_target_value_pair_count"],
            int("Omega Republic" in fixed["projection"] and "999" in fixed["projection"]),
        )

    def test_table_header_closure_and_caps_hold(self) -> None:
        table = "| Country | Target Metric [TM] @2024 |\n|---|---:|\n" + "\n".join(
            f"| filler-{i:03d} | {i} |" for i in range(400)
        ) + "\n| Omega Republic | 999 |"
        result = build_projection(QUESTION, [page(1, table)])
        if "| Omega Republic | 999 |" in result["projection"]:
            self.assertIn("| Country | Target Metric [TM] @2024 |", result["projection"])
        self.assertEqual(result["orphan_selected_table_continuation_block_count"], 0)
        self.assertLessEqual(result["projected_rendered_characters"], 30_000)
        self.assertTrue(all(value <= 5_000 for value in result["per_page_allocated_characters"]))

    def test_no_visible_rows_degrades_to_safe_parent_style_selection(self) -> None:
        question = "Column names: Country | Target Metric. Return a table."
        result = build_projection(question, [page(1, "Country Target Metric: 999")])
        self.assertEqual(result["visible_row_target_count"], 0)
        self.assertEqual(result["supported_target_value_pair_count"], 0)
        self.assertTrue(result["projection"])

    def test_duplicate_url_is_stably_removed(self) -> None:
        original = page(1, "Omega Republic Target Metric [TM] @2024: 999")
        duplicate = {**original, "title": "duplicate", "content": "bad duplicate"}
        result = build_projection(QUESTION, [original, duplicate])
        self.assertEqual(result["input_page_count"], 1)
        self.assertNotIn("bad duplicate", result["projection"])

    def test_replay_and_resealed_tamper_fail_closed(self) -> None:
        pages = [page(1, "Omega Republic Target Metric [TM] @2024: 999")]
        result = build_projection(QUESTION, pages)
        self.assertEqual(
            validate_projection(result, question=QUESTION, pages=pages), result
        )
        altered = copy.deepcopy(result["content_free_receipt"])
        altered["retained_target_value_pair_count"] += 1
        altered.pop("receipt_payload_sha256")
        altered["receipt_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_receipt(altered)

    def test_entropy_is_shadow_and_credit_zero(self) -> None:
        receipt = build_projection(
            QUESTION, [page(1, "Omega Republic Target Metric [TM] @2024: 999")]
        )["content_free_receipt"]
        self.assertTrue(receipt["entropy_information_gain_shadow_only"])
        self.assertFalse(receipt["entropy_or_information_gain_assigns_credit"])
        self.assertFalse(
            receipt[
                "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
            ]
        )

    def test_runtime_ast_has_no_io_network_process_or_dynamic_execution(self) -> None:
        path = ROOT / "src/deepwide_agent/v24921_target_value_coverage_projector.py"
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
                {"os", "pathlib", "socket", "subprocess", "requests", "httpx"}
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
