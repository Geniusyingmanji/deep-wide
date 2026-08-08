from __future__ import annotations

import ast
import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24842_atomic_table_header_closure as control_projector  # noqa: E402
from deepwide_agent import v24846_atomic_table_header_30k_profile as candidate_projector  # noqa: E402
from deepwide_agent import v24847_projection_budget_external_contract as contract  # noqa: E402
from scripts import control_v24847_projection_budget_external as control  # noqa: E402
from scripts import evaluate_v24847_projection_budget_external as evaluator  # noqa: E402
from scripts import run_v24847_projection_budget_external_forward as runner  # noqa: E402
from scripts import run_v24847_projection_budget_external_task as child  # noqa: E402


class V24847ProjectionBudgetExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.private = json.loads((ROOT / control.POPULATION_PRIVATE).read_text())
        cls.tasks = control.project_tasks(cls.private)

    def test_population_is_target_cell_disjoint_32x4(self) -> None:
        public = json.loads((ROOT / control.POPULATION_DESIGN).read_text())
        self.assertEqual(len(self.private["groups"]), 32)
        self.assertTrue(all(len(group) == 4 for group in self.private["groups"]))
        self.assertEqual(public["selected_gold_cell_count"], 256)
        self.assertEqual(public["selected_gold_cell_overlap_count"], 0)
        self.assertEqual(public["selected_target_pair_overlap_count"], 0)
        self.assertEqual(public["selected_entity_overlap_count"], 128)

    def test_visible_forward_tasks_are_exactly_opaque_id_and_question(self) -> None:
        self.assertEqual(len(self.tasks), 32)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in self.tasks))
        with self.assertRaises(ValueError):
            contract.validate_task_vector([{**task, "question_type": "hidden"} for task in self.tasks])

    def test_protocol_uses_physically_separate_visible_task_artifact(self) -> None:
        self.assertTrue(str(contract.VISIBLE_TASK_ARTIFACT).startswith("results/"))
        self.assertNotIn("evaluation", str(contract.VISIBLE_TASK_ARTIFACT))

    def test_visible_tasks_do_not_project_private_values(self) -> None:
        encoded = json.dumps(self.tasks, ensure_ascii=False)
        for group in self.private["groups"]:
            for item in group:
                for record in item["records"]:
                    self.assertNotIn(str(record["value"]), encoded)

    def test_raw_page_builder_freezes_two_responses_into_eight_shared_pages(self) -> None:
        blobs = []
        for target_index in range(2):
            records = []
            for index in range(12):
                records.append(
                    {
                        "country": {"value": f"Country {index}"},
                        "countryiso3code": f"A{index:02d}",
                        "value": target_index * 100 + index,
                    }
                )
            blobs.append(json.dumps([{}, records]).encode())
        value = runner._raw_pages(blobs)
        self.assertEqual(value["source_count"], 2)
        self.assertEqual(value["structural_page_count"], 8)
        self.assertEqual(len(value["pages"]), 8)
        self.assertEqual(len({page["url"] for page in value["pages"]}), 8)
        self.assertTrue(value["fetched_once_before_arm_branch"])

    def test_same_pages_produce_distinct_16k_and_30k_projection_caps(self) -> None:
        pages = []
        for index in range(8):
            lines = ["| Country | Target Metric |", "|---|---:|"]
            lines.extend(f"| filler-{index}-{row} | {row} |" for row in range(180))
            pages.append({"title": str(index), "url": f"https://h{index}.example", "content": "\n".join(lines)})
        question = "Column names: Country | Target Metric. Return rows for China and Morocco."
        first = control_projector.build_projection(question, pages)
        second = candidate_projector.build_projection(question, pages)
        self.assertLessEqual(first["projected_rendered_characters"], 16_000)
        self.assertLessEqual(second["content_free_receipt"]["projected_rendered_characters"], 30_000)
        self.assertGreater(second["content_free_receipt"]["projected_rendered_characters"], first["projected_rendered_characters"])

    def test_prompt_and_country_parser_are_visible_only(self) -> None:
        countries = child._countries(self.tasks[0]["question"])
        self.assertEqual(len(countries), 4)
        prompt = child._prompt(self.tasks[0]["question"], "VISIBLE_EVIDENCE")
        self.assertIn("VISIBLE_EVIDENCE", prompt)
        self.assertNotIn("ground_truth", prompt)

    def test_evaluator_exact_and_partial_metrics(self) -> None:
        gold = evaluator._gold(self.private)
        opaque = self.tasks[0]["opaque_id"]
        columns = evaluator._columns()
        lines = ["| " + " | ".join(columns) + " |", "|---|---|---|"]
        for row in gold[opaque]:
            lines.append("| " + " | ".join(row[column] for column in columns) + " |")
        exact = evaluator.evaluate_prediction("\n".join(lines), gold[opaque])
        self.assertEqual(exact["exact_table_success"], 1)
        self.assertEqual(exact["composite"], 1.0)

    def test_go_rule_requires_strict_exact_gain(self) -> None:
        gold = evaluator._gold(self.private)
        rows = []
        columns = evaluator._columns()
        for task in self.tasks:
            lines = ["| " + " | ".join(columns) + " |", "|---|---|---|"]
            for row in gold[task["opaque_id"]]:
                lines.append("| " + " | ".join(row[column] for column in columns) + " |")
            exact = "\n".join(lines)
            rows.append({"opaque_id": task["opaque_id"], "predictions": {"atomic_16k": exact, "atomic_30k": exact}})
        metrics = evaluator.evaluate_rows(rows, gold)
        self.assertEqual(metrics["atomic_30k_minus_16k"]["exact_table_successes"], 0)

    def test_forward_ast_does_not_import_evaluator_or_private_population(self) -> None:
        for relative in (contract.RUNNER_MARKER, contract.CHILD_MARKER):
            source = (ROOT / relative).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any("evaluate_v24847" in name for name in imports))
            self.assertNotIn("POPULATION_PRIVATE", source)

    def test_entropy_credit_and_public_launch_are_disabled(self) -> None:
        self.assertEqual(contract.ARMS, ("atomic_16k", "atomic_30k"))
        self.assertEqual(candidate_projector.TOTAL_CHARACTER_CAP, 30_000)
        profile = json.loads((ROOT / control.PROFILE_AUDIT).read_text())
        self.assertFalse(profile["source_policy"]["entropy_or_information_gain_assigns_credit"])
        self.assertFalse(profile["authorization"]["public_dev64_or_exact220"])


if __name__ == "__main__":
    unittest.main()
