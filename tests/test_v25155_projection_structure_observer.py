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

from deepwide_agent import v25155_projection_structure_observer as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402


class V25155ProjectionStructureObserverTests(unittest.TestCase):
    def test_table_to_key_value_pipe_is_retained_across_layers(self) -> None:
        value = target.observe_structure(
            "<table><tr><td>Version:</td><td>1.2.3</td></tr>"
            "<tr><td>License:</td><td>MIT</td></tr></table>",
            "Version: | 1.2.3\nLicense: | MIT",
            "Version: | 1.2.3\nLicense: | MIT",
        )
        self.assertEqual(value["raw_markup_counts"]["table_count"], 1)
        self.assertEqual(
            value["raw_markup_counts"][
                "table_row_with_at_least_two_cells_count"
            ],
            2,
        )
        self.assertEqual(
            value["extracted_text_counts"]["key_value_pipe_line_count"], 2
        )
        self.assertTrue(
            value["transitions"][
                "extracted_key_value_pipe_surface_retained_after_projection"
            ]
        )

    def test_preprojection_receipt_can_be_finalized_without_semantic_content(self) -> None:
        pre = target.observe_preprojection(
            "<table><tr><td>Field:</td><td>Value</td></tr></table>",
            "Field: | Value",
        )
        encoded = json.dumps(pre, ensure_ascii=False)
        self.assertNotIn("Field", encoded)
        self.assertNotIn("Value", encoded)
        value = target.finalize_observation(pre, "Field: | Value")
        self.assertTrue(
            value["transitions"][
                "extracted_key_value_pipe_surface_retained_after_projection"
            ]
        )

    def test_raw_to_extracted_and_extracted_to_projected_loss_are_distinct(self) -> None:
        raw_loss = target.observe_structure(
            "<dl><dt>Field</dt><dd>Value</dd></dl>", "plain text", "plain text"
        )
        self.assertTrue(
            raw_loss["transitions"]["raw_to_extracted_total_structure_loss"]
        )
        projected_loss = target.observe_structure(
            "<p>plain</p>",
            "Field: Value\nOther: Value",
            "plain text",
        )
        self.assertFalse(
            projected_loss["transitions"]["raw_to_extracted_total_structure_loss"]
        )
        self.assertTrue(
            projected_loss["transitions"][
                "extracted_to_projected_total_structure_loss"
            ]
        )

    def test_json_ld_and_json_object_lines_are_counted_without_content(self) -> None:
        value = target.observe_structure(
            '<script type="application/ld+json">{"name":"alpha"}</script>',
            '{"name":"alpha","version":"1"}',
            '{"name":"alpha","version":"1"}',
        )
        self.assertEqual(value["raw_markup_counts"]["json_ld_script_count"], 1)
        self.assertEqual(value["extracted_text_counts"]["json_object_line_count"], 1)
        encoded = json.dumps(value, ensure_ascii=False)
        self.assertNotIn("alpha", encoded)

    def test_semantically_different_pages_with_same_shape_have_same_receipt(self) -> None:
        first = target.observe_structure(
            "<table><tr><td>A:</td><td>B</td></tr></table>",
            "A: | B",
            "A: | B",
        )
        second = target.observe_structure(
            "<table><tr><td>X:</td><td>Y</td></tr></table>",
            "X: | Y",
            "X: | Y",
        )
        self.assertEqual(first, second)

    def test_aggregate_is_content_free_and_count_closed(self) -> None:
        values = [
            target.observe_structure(
                "<table><tr><td>A:</td><td>B</td></tr></table>",
                "A: | B",
                "A: | B",
            ),
            target.observe_structure("<p>narrative</p>", "narrative", "narrative"),
        ]
        aggregate = target.aggregate_observations(values)
        self.assertEqual(aggregate["counts"]["observed_page_count"], 2)
        self.assertEqual(aggregate["counts"]["raw_structured_page_count"], 1)
        self.assertEqual(
            aggregate["counts"]["projected_structured_page_count"], 1
        )
        changed = copy.deepcopy(aggregate)
        changed["counts"]["raw_structured_page_count"] = 3
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_aggregate(changed)

    def test_tamper_or_oversized_layer_fails_closed(self) -> None:
        value = target.observe_structure("", "A: B\nC: D", "A: B\nC: D")
        for kind in ("count", "transition", "credit", "launch"):
            changed = copy.deepcopy(value)
            if kind == "count":
                changed["projected_text_counts"]["key_value_pipe_line_count"] = (
                    changed["projected_text_counts"]["pipe_line_count"] + 1
                )
            elif kind == "transition":
                changed["transitions"][
                    "projected_structured_surface_present"
                ] = False
            elif kind == "credit":
                changed["entropy_or_information_gain_assigns_signed_credit"] = True
            else:
                changed["benchmark_launch_or_evaluator_authorized"] = True
            changed.pop("receipt_payload_sha256")
            changed["receipt_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_observation(changed)
        with self.assertRaises(ValueError):
            target.observe_structure(
                "x" * (target.MAXIMUM_LAYER_CHARACTERS + 1), "", ""
            )

    def test_module_is_pure_label_blind_and_build_only(self) -> None:
        path = ROOT / "src/deepwide_agent/v25155_projection_structure_observer.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports: list[str] = []
        privileged: list[str] = []
        calls: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(
                node.slice, ast.Constant
            ) and node.slice.value in {
                "category",
                "question_type",
                "task_category",
                "split",
                "ground_truth",
                "gold",
                "answer_key",
                "score",
                "reward",
            }:
                privileged.append(str(node.slice.value))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
        self.assertTrue(
            {name.split(".")[0] for name in imports}.isdisjoint(
                {
                    "os",
                    "pathlib",
                    "socket",
                    "subprocess",
                    "requests",
                    "httpx",
                    "openai",
                }
            )
        )
        self.assertEqual(privileged, [])
        self.assertTrue(
            calls.isdisjoint(
                {"complete", "search_many", "fetch_urls", "create_connection"}
            )
        )


if __name__ == "__main__":
    unittest.main()
