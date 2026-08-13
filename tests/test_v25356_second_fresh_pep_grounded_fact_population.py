from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25356_second_fresh_pep_grounded_fact_population as target  # noqa: E402


class V25356SecondFreshPepGroundedFactPopulationTests(unittest.TestCase):
    def test_fixed_visible_identity_task_and_arm_vectors(self) -> None:
        identities = target.identity_vector()
        tasks = target.task_vector()
        orders = target.arm_order_vector()
        self.assertEqual(len(identities), target.TASK_COUNT)
        self.assertEqual(len(tasks), target.TASK_COUNT)
        self.assertEqual(
            target.payload_sha256(identities),
            target.EXPECTED_IDENTITY_VECTOR_SHA256,
        )
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )
        self.assertEqual(
            target.payload_sha256(orders),
            target.EXPECTED_ARM_ORDER_VECTOR_SHA256,
        )
        self.assertEqual(
            sum(order[0] == target.CANDIDATE_ARM for order in orders), 10
        )

    def test_tasks_expose_only_identity_question_and_exact_schema(self) -> None:
        for identity, task in zip(
            target.identity_vector(), target.task_vector(), strict=True
        ):
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertIn(f"<PEP>{identity}</PEP>", task["question"])
            self.assertIn("Columns exactly: PEP | Title | Status | Type | Created", task["question"])

    def test_mutation_or_privileged_member_fails(self) -> None:
        tasks = target.task_vector()
        changed = copy.deepcopy(tasks)
        changed[0]["question"] = changed[0]["question"].replace(
            "<PEP>PEP 701</PEP>", "<PEP>PEP 700</PEP>"
        )
        with self.assertRaises(ValueError):
            target.validate_task_vector(changed)
        changed = copy.deepcopy(tasks)
        changed[0]["category"] = "forbidden"
        with self.assertRaises(ValueError):
            target.validate_task_vector(changed)

    def test_module_is_pure_and_authorizes_no_effect(self) -> None:
        path = ROOT / "src/deepwide_agent/v25356_second_fresh_pep_grounded_fact_population.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "subprocess",
            "requests",
            "httpx",
            "socket",
            "urllib",
        ):
            self.assertFalse(
                any(
                    name == forbidden or name.startswith(forbidden + ".")
                    for name in imports
                )
            )
        policy = target.source_policy()
        self.assertTrue(
            policy["pre_effect_query_projection_required_before_first_search_or_fetch"]
        )
        self.assertFalse(
            policy["deepwidebench_forward_evaluator_leaderboard_or_sota_authorized"]
        )


if __name__ == "__main__":
    unittest.main()
