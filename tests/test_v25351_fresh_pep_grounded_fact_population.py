from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25351_fresh_pep_grounded_fact_population as target  # noqa: E402


class V25351FreshPepGroundedFactPopulationTests(unittest.TestCase):
    def test_fixed_visible_identity_task_vector_and_hashes(self) -> None:
        identities = target.identity_vector()
        tasks = target.task_vector()
        self.assertEqual(len(identities), 20)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(
            target.payload_sha256(identities),
            target.EXPECTED_IDENTITY_VECTOR_SHA256,
        )
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )
        for identity, task in zip(identities, tasks, strict=True):
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertIn(f"<PEP>{identity}</PEP>", task["question"])

    def test_arm_order_is_fixed_balanced_and_complete(self) -> None:
        orders = target.arm_order_vector()
        self.assertEqual(len(orders), target.TASK_COUNT)
        self.assertTrue(all(set(order) == set(target.ARMS) for order in orders))
        self.assertEqual(
            sum(order[0] == target.CANDIDATE_ARM for order in orders), 10
        )

    def test_mutated_identity_or_privileged_member_fails(self) -> None:
        tasks = target.task_vector()
        changed = copy.deepcopy(tasks)
        changed[0]["question"] = changed[0]["question"].replace(
            "<PEP>PEP 621</PEP>", "<PEP>PEP 620</PEP>"
        )
        with self.assertRaises(ValueError):
            target.validate_task_vector(changed)
        changed = copy.deepcopy(tasks)
        changed[0]["category"] = "forbidden"
        with self.assertRaises(ValueError):
            target.validate_task_vector(changed)

    def test_module_is_pure_and_has_no_hidden_mapping_or_effect_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25351_fresh_pep_grounded_fact_population.py"
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
        for forbidden in (
            "ground_truth",
            "answer_key",
            "official_eval",
            "api_key",
            "target/main",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
