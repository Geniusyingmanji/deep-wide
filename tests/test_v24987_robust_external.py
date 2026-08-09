from __future__ import annotations

import ast
import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v24983_late_page_external_contract as prior  # noqa: E402
from deepwide_agent import v24987_robust_external_contract as target  # noqa: E402


class RobustExternalContractTests(unittest.TestCase):
    def test_population_is_fresh_fixed_unique_and_label_blind(self) -> None:
        tasks = target.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({row["opaque_id"] for row in tasks}), 20)
        self.assertFalse(set(target.TLD_COHORT).intersection(prior.TLD_COHORT))
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in tasks))
        self.assertTrue(all(target.IANA_URL not in row["question"] for row in tasks))

    def test_arm_order_is_exactly_balanced_and_bound(self) -> None:
        orders = target.arm_order_vector()
        self.assertEqual(len(orders), 20)
        self.assertEqual(sum(order[0] == target.CANDIDATE_ARM for order in orders), 10)
        self.assertTrue(all(set(order) == set(target.ARMS) for order in orders))

    def test_hard_budgets_match_production(self) -> None:
        self.assertEqual(
            target.LIMITS,
            {
                "wall_seconds": 240,
                "model_calls": 3,
                "search_queries": 4,
                "fetch_targets": 10,
                "search_results_per_query": 3,
                "evidence_chars": 60000,
                "page_chars": 5000,
                "plan_output_tokens": 4000,
                "synthesis_output_tokens": 30000,
                "repair_output_tokens": 12000,
            },
        )

    def test_entropy_is_shadow_only_and_exact220_closed(self) -> None:
        source = target.source_policy()
        self.assertFalse(source["entropy_or_information_gain_assigns_credit_or_routes"])
        self.assertFalse(source["public_deepwidebench_exact220_launch_authorized"])
        self.assertTrue(source["robust_visible_schema_parsed_from_question_only"])
        self.assertTrue(source["query_completion_uses_question_and_same_pass_plan_only"])

    def test_forward_sources_do_not_import_benchmark_or_evaluator(self) -> None:
        for relative in (target.PROJECTOR, target.FETCH, target.RUNTIME, target.HELPER, target.RUNNER):
            tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name.casefold() for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append((node.module or "").casefold())
            self.assertFalse(any("deepwidebench" in name or "evaluate_v24987" in name for name in imports))

    def test_future_surfaces_are_distinct_and_create_only(self) -> None:
        paths = {
            target.PREAUDIT,
            target.EXECUTION_START,
            target.FORWARD_RESULT,
            target.FORWARD_AUDIT,
            target.EVALUATOR_PROTOCOL,
            target.RESULT,
            target.POSTAUDIT,
            target.OUTPUT_ROOT,
        }
        self.assertEqual(len(paths), 8)
        source = (ROOT / target.RUNNER).read_text(encoding="utf-8")
        self.assertIn("os.O_EXCL", source)
        self.assertNotIn('"--resume"', source.casefold())
        self.assertNotIn("def resume", source.casefold())

    def test_protocol_roundtrip_before_files_are_tracked(self) -> None:
        protocol = target._protocol(ROOT, now=123, tracked=False)
        checked = target.validate_protocol(ROOT, protocol, tracked=False)
        self.assertEqual(checked, protocol)
        self.assertEqual(checked["population"]["selected_tasks"], 20)
        self.assertFalse(checked["authorization"]["one_external_forward"])

    def test_protocol_tamper_is_rejected(self) -> None:
        protocol = target._protocol(ROOT, now=123, tracked=False)
        tampered = copy.deepcopy(protocol)
        tampered["mechanism_gate_before_evaluator"]["minimum_prediction_changed_tasks"] = 1
        with self.assertRaises(ValueError):
            target.validate_protocol(ROOT, tampered, tracked=False)


if __name__ == "__main__":
    unittest.main()
