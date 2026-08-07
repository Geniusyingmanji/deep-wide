from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24836_information_bottleneck_projector import (  # noqa: E402
    build_projection as build_round_robin,
)
from deepwide_agent.v24839_structure_preserving_projector import (  # noqa: E402
    ProjectionPolicy,
    build_projection,
    payload_sha256,
    validate_projection,
    visible_requirement_groups,
)


QUESTION = """Use public web sources to return one Markdown table about these countries:
<COUNTRIES>
1. Alpha Republic [ALP]
2. Beta State [BET]
</COUNTRIES>
Please output one Markdown table with the columns, in this exact order:
Country | Population total [SP.POP.TOTL] @2024 | GDP current US$ [NY.GDP.MKTP.CD] @2024
Return one table only."""


def page(index: int, content: str, host: str | None = None) -> dict[str, str]:
    return {
        "title": f"Page {index}",
        "url": f"https://{host or f'h{index}.example'}/p{index}",
        "content": content,
    }


class V24839StructurePreservingProjectorTests(unittest.TestCase):
    def test_visible_groups_come_only_from_explicit_visible_syntax(self) -> None:
        groups = visible_requirement_groups(QUESTION)
        for expected in (
            "alpha republic",
            "alp",
            "beta state",
            "bet",
            "population total",
            "sp.pop.totl",
            "gdp current us$",
            "ny.gdp.mktp.cd",
        ):
            self.assertIn(expected, groups)
        self.assertNotIn("return one table only", groups)

    def test_late_relevant_structure_survives_when_round_robin_prefix_loses_it(self) -> None:
        relevant = (
            "# Official indicator records\n"
            "| Country | SP.POP.TOTL | NY.GDP.MKTP.CD |\n"
            "|---|---:|---:|\n"
            "| Alpha Republic | 101 | 202 |\n"
            "| Beta State | 303 | 404 |"
        )
        pages = [page(1, "irrelevant boilerplate " * 400 + "\n\n" + relevant)]
        old = build_round_robin(pages)["projection"]
        new = build_projection(QUESTION, pages)["projection"]
        self.assertNotIn("| Alpha Republic | 101 | 202 |", old)
        self.assertIn("| Alpha Republic | 101 | 202 |", new)
        self.assertIn("| Beta State | 303 | 404 |", new)

    def test_supported_visible_groups_are_all_retained(self) -> None:
        pages = [
            page(1, "Alpha Republic [ALP]\nPopulation total SP.POP.TOTL: 101"),
            page(2, "Beta State [BET]\nGDP current US$ NY.GDP.MKTP.CD: 404"),
        ]
        result = build_projection(QUESTION, pages)
        self.assertGreater(result["supported_visible_requirement_group_count"], 0)
        self.assertEqual(result["missed_supported_visible_requirement_group_count"], 0)
        self.assertEqual(
            result["retained_supported_visible_requirement_group_count"],
            result["supported_visible_requirement_group_count"],
        )

    def test_total_and_per_page_caps_are_hard(self) -> None:
        pages = [page(index, (f"section {index}\nvalue: {index}\n" * 1000)) for index in range(1, 9)]
        result = build_projection(QUESTION, pages)
        self.assertLessEqual(result["allocated_content_characters"], 16_000)
        self.assertTrue(
            all(value <= 5_000 for value in result["per_page_allocated_characters"])
        )

    def test_table_rows_below_block_cap_are_not_cut(self) -> None:
        row = "| Alpha Republic | 101 | 202 |"
        result = build_projection(
            QUESTION,
            [page(1, "| Country | Population | GDP |\n|---|---|---|\n" + row)],
        )
        self.assertIn(row, result["projection"])
        self.assertNotIn("| Alpha Republic | 101\n", result["projection"])

    def test_selected_blocks_render_in_original_order(self) -> None:
        pages = [
            page(1, "Beta State appears first.\n\nAlpha Republic appears second."),
            page(2, "NY.GDP.MKTP.CD appears on the later page."),
        ]
        projection = build_projection(QUESTION, pages)["projection"]
        self.assertLess(projection.index("Beta State"), projection.index("Alpha Republic"))
        self.assertLess(projection.index("Alpha Republic"), projection.index("NY.GDP.MKTP.CD"))

    def test_duplicate_url_is_stably_removed(self) -> None:
        pages = [
            page(1, "Alpha Republic first"),
            {**page(1, "Alpha Republic duplicate"), "title": "duplicate"},
        ]
        result = build_projection(QUESTION, pages)
        self.assertEqual(result["input_page_count"], 1)
        self.assertIn("first", result["projection"])
        self.assertNotIn("duplicate", result["projection"])

    def test_question_changes_selection_only_through_visible_terms(self) -> None:
        policy = ProjectionPolicy(
            total_character_cap=1_200,
            maximum_page_chars=1_200,
            block_character_cap=600,
        )
        pages = [page(1, "Alpha evidence " * 50 + "\n\n" + "Beta evidence " * 50)]
        alpha = build_projection(
            "Column names: Alpha.", pages, explicit_groups=["Alpha"], policy=policy
        )
        beta = build_projection(
            "Column names: Beta.", pages, explicit_groups=["Beta"], policy=policy
        )
        self.assertNotEqual(alpha["projection_sha256"], beta["projection_sha256"])

    def test_entropy_is_shadow_only_and_no_privileged_signal_exists(self) -> None:
        result = build_projection(QUESTION, [page(1, "Alpha Republic")])
        self.assertTrue(result["entropy_information_gain_shadow_only"])
        self.assertFalse(result["entropy_or_information_gain_assigns_credit"])
        self.assertFalse(
            result[
                "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
            ]
        )

    def test_replay_and_resealed_tamper_fail_closed(self) -> None:
        pages = [page(1, "Alpha Republic\nPopulation total: 101")]
        result = build_projection(QUESTION, pages)
        self.assertEqual(result, validate_projection(result, question=QUESTION, pages=pages))
        altered = copy.deepcopy(result)
        altered["per_page_allocated_characters"][0] -= 1
        altered.pop("receipt_sha256")
        altered["receipt_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_projection(altered, question=QUESTION, pages=pages)

    def test_bad_policy_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ProjectionPolicy(total_character_cap=0).validate()
        with self.assertRaises(ValueError):
            ProjectionPolicy(total_character_cap=1000, maximum_page_chars=2000).validate()

    def test_runtime_ast_has_no_io_network_process_or_dynamic_execution(self) -> None:
        path = ROOT / "src/deepwide_agent/v24839_structure_preserving_projector.py"
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
        self.assertTrue(imports.isdisjoint({"os", "pathlib", "socket", "subprocess", "requests"}))
        calls = {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(calls.isdisjoint({"open", "eval", "exec", "compile", "__import__"}))


if __name__ == "__main__":
    unittest.main()
