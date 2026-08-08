from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24839_structure_preserving_projector import (  # noqa: E402
    ProjectionPolicy,
    build_projection as build_control,
)
from deepwide_agent.v24842_atomic_table_header_closure import (  # noqa: E402
    build_projection,
    payload_sha256,
    validate_projection,
)


QUESTION = "Column names: Country | Target Metric. Return the row for Omega Republic."
TARGET_ONLY_QUESTION = "Return the row for Omega Republic."


def page(index: int, content: str) -> dict[str, str]:
    return {
        "title": "long official table" if index == 1 else f"Page {index}",
        "url": (
            "https://official.example/table"
            if index == 1
            else f"https://h{index}.example/table"
        ),
        "content": content,
    }


def long_table() -> str:
    lines = ["| Country | Target Metric |", "|---|---:|"]
    lines.extend(f"| filler-{index:03d} | {index} |" for index in range(60))
    lines.append("| Omega Republic | 999 |")
    return "\n".join(lines)


class V24842AtomicTableHeaderClosureTests(unittest.TestCase):
    def test_control_orphan_is_reproduced_at_tight_budget(self) -> None:
        policy = ProjectionPolicy(
            total_character_cap=260,
            maximum_page_chars=260,
            block_character_cap=180,
        )
        projection = build_control(QUESTION, [page(1, long_table())], policy=policy)[
            "projection"
        ]
        self.assertIn("| Omega Republic | 999 |", projection)
        self.assertNotIn("| Country | Target Metric |", projection)

    def test_candidate_never_emits_orphan_at_tight_budget(self) -> None:
        policy = ProjectionPolicy(
            total_character_cap=260,
            maximum_page_chars=260,
            block_character_cap=180,
        )
        result = build_projection(QUESTION, [page(1, long_table())], policy=policy)
        self.assertFalse(
            "| Omega Republic | 999 |" in result["projection"]
            and "| Country | Target Metric |" not in result["projection"]
        )
        self.assertEqual(result["orphan_selected_table_continuation_block_count"], 0)
        self.assertLessEqual(result["projected_rendered_characters"], 260)

    def test_candidate_atomically_retains_header_and_tail_when_bundle_fits(self) -> None:
        policy = ProjectionPolicy(
            total_character_cap=320,
            maximum_page_chars=320,
            block_character_cap=180,
        )
        result = build_projection(
            TARGET_ONLY_QUESTION, [page(1, long_table())], policy=policy
        )
        self.assertIn("| Country | Target Metric |", result["projection"])
        self.assertIn("| Omega Republic | 999 |", result["projection"])
        self.assertGreaterEqual(result["table_header_dependency_addition_count"], 1)
        self.assertGreaterEqual(result["selected_table_continuation_block_count"], 1)
        self.assertEqual(result["orphan_selected_table_continuation_block_count"], 0)

    def test_separate_tables_do_not_borrow_each_others_headers(self) -> None:
        first = "| A | B |\n|---|---|\n" + "\n".join(
            f"| first-{index} | {index} |" for index in range(30)
        )
        second = "| Country | Target Metric |\n|---|---:|\n" + "\n".join(
            f"| second-{index} | {index} |" for index in range(30)
        ) + "\n| Omega Republic | 999 |"
        result = build_projection(
            QUESTION,
            [page(1, first + "\n\n" + second)],
            policy=ProjectionPolicy(
                total_character_cap=500,
                maximum_page_chars=500,
                block_character_cap=180,
            ),
        )
        if "| Omega Republic | 999 |" in result["projection"]:
            self.assertIn("| Country | Target Metric |", result["projection"])
        self.assertEqual(result["orphan_selected_table_continuation_block_count"], 0)

    def test_non_table_selection_matches_control_on_simple_pages(self) -> None:
        pages = [
            page(1, "Omega Republic Target Metric: 999\n\nOther evidence."),
            page(2, "Independent Omega Republic record: 999"),
        ]
        control = build_control(QUESTION, pages)["projection"]
        candidate = build_projection(QUESTION, pages)["projection"]
        self.assertEqual(candidate, control)

    def test_default_rendered_and_per_page_caps_are_hard(self) -> None:
        pages = [page(index, long_table() * 5) for index in range(1, 9)]
        result = build_projection(QUESTION, pages)
        self.assertLessEqual(result["projected_rendered_characters"], 16_000)
        self.assertTrue(
            all(value <= 5_000 for value in result["per_page_allocated_characters"])
        )

    def test_supported_visible_groups_remain_retained_when_feasible(self) -> None:
        result = build_projection(
            QUESTION,
            [page(1, long_table())],
            policy=ProjectionPolicy(
                total_character_cap=1000,
                maximum_page_chars=1000,
                block_character_cap=180,
            ),
        )
        self.assertGreater(result["supported_visible_requirement_group_count"], 0)
        self.assertEqual(result["missed_supported_visible_requirement_group_count"], 0)

    def test_duplicate_url_is_stably_removed(self) -> None:
        pages = [
            page(1, "Omega Republic Target Metric: 999"),
            {**page(1, "duplicate"), "title": "duplicate"},
        ]
        result = build_projection(QUESTION, pages)
        self.assertEqual(result["input_page_count"], 1)
        self.assertNotIn("duplicate", result["projection"])

    def test_entropy_is_shadow_only_and_credit_is_zero(self) -> None:
        result = build_projection(QUESTION, [page(1, long_table())])
        self.assertTrue(result["entropy_information_gain_shadow_only"])
        self.assertFalse(result["entropy_or_information_gain_assigns_credit"])
        self.assertFalse(
            result[
                "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
            ]
        )

    def test_replay_and_resealed_tamper_fail_closed(self) -> None:
        pages = [page(1, long_table())]
        result = build_projection(QUESTION, pages)
        self.assertEqual(result, validate_projection(result, question=QUESTION, pages=pages))
        altered = copy.deepcopy(result)
        altered["orphan_selected_table_continuation_block_count"] = 1
        altered.pop("receipt_sha256")
        altered["receipt_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_projection(altered, question=QUESTION, pages=pages)

    def test_runtime_ast_has_no_io_network_process_or_dynamic_execution(self) -> None:
        path = ROOT / "src/deepwide_agent/v24842_atomic_table_header_closure.py"
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
        self.assertTrue(
            calls.isdisjoint({"open", "eval", "exec", "compile", "__import__"})
        )


if __name__ == "__main__":
    unittest.main()
