from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25391_fresh_rfc_hybrid_population as target  # noqa: E402


class V25391FreshRfcHybridPopulationTests(unittest.TestCase):
    def test_fixed_consecutive_identity_and_task_vectors(self) -> None:
        identities = target.identity_vector()
        tasks = target.task_vector()
        self.assertEqual(target.RFC_NUMBERS, tuple(range(9680, 9760)))
        self.assertEqual(len(identities), 80)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(
            target.payload_sha256(identities),
            target.EXPECTED_IDENTITY_VECTOR_SHA256,
        )
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )

    def test_each_visible_task_has_exactly_four_ordered_disjoint_rows(self) -> None:
        identities = target.identity_vector()
        seen: list[str] = []
        for index, task in enumerate(target.task_vector()):
            group = identities[index * 4 : (index + 1) * 4]
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertIn(f"<RFCS>{'; '.join(group)}</RFCS>", task["question"])
            self.assertIn(
                "Columns exactly: RFC | Title | Authors | Status | Stream | Published",
                task["question"],
            )
            seen.extend(group)
        self.assertEqual(seen, identities)
        self.assertEqual(len(set(seen)), 80)

    def test_mutation_reordering_or_privileged_member_fails(self) -> None:
        tasks = target.task_vector()
        changed = copy.deepcopy(tasks)
        changed[0]["question"] = changed[0]["question"].replace(
            "RFC 9680; RFC 9681", "RFC 9681; RFC 9680"
        )
        with self.assertRaises(ValueError):
            target.validate_task_vector(changed)
        changed = copy.deepcopy(tasks)
        changed[0]["question_type"] = "forbidden"
        with self.assertRaises(ValueError):
            target.validate_task_vector(changed)

    def test_module_is_pure_and_gate_requires_hybrid_funnel(self) -> None:
        path = ROOT / "src/deepwide_agent/v25391_fresh_rfc_hybrid_population.py"
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
            policy[
                "record_source_priority_is_joint_nonempty_then_grounded_nonempty_then_none"
            ]
        )
        self.assertTrue(
            policy["record_source_selected_before_quote_or_edit_verification"]
        )
        self.assertFalse(
            policy["deepwidebench_forward_evaluator_leaderboard_or_sota_authorized"]
        )
        gate = target.mechanism_gate()
        self.assertEqual(gate["minimum_selected_raw_record_tasks"], 8)
        self.assertEqual(gate["minimum_verified_record_tasks"], 4)
        self.assertEqual(gate["minimum_changed_safe_coordinate_tasks"], 4)
        self.assertEqual(gate["minimum_attributable_prediction_changed_tasks"], 4)
        self.assertEqual(gate["positive_signed_credit_count"], 0)


if __name__ == "__main__":
    unittest.main()
