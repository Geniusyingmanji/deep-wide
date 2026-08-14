from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25494_fresh_visible_row_key_population as target  # noqa: E402


class V25494FreshVisibleRowKeyPopulationTests(unittest.TestCase):
    def test_identity_and_task_vectors_are_exact_and_unique(self) -> None:
        identities = target.identity_vector()
        tasks = target.task_vector()
        self.assertEqual(len(identities), 20)
        self.assertEqual(len(set(identities)), 20)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 20)
        self.assertEqual(
            target.payload_sha256(identities),
            target.EXPECTED_IDENTITY_VECTOR_SHA256,
        )
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )

    def test_questions_expose_only_runtime_allowed_public_inputs(self) -> None:
        for identity, task in zip(
            target.identity_vector(), target.task_vector(), strict=True
        ):
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertIn(f"<DOMAIN>{identity}</DOMAIN>", task["question"])
            self.assertIn(target.INDEX_URL, task["question"])
            self.assertIn("Domain | Type | TLD Manager", task["question"])

    def test_mechanism_gate_requires_full_fixed_denominator_and_zero_credit(self) -> None:
        gate = target.mechanism_gate()
        self.assertEqual(gate["fixed_task_denominator"], 20)
        self.assertEqual(gate["required_terminal_tasks"], 20)
        self.assertEqual(gate["maximum_candidate_additional_fetches"], 1)
        self.assertEqual(gate["candidate_additional_queries"], 0)
        self.assertEqual(gate["candidate_additional_model_calls"], 0)
        self.assertEqual(gate["positive_signed_credit_count"], 0)

    def test_task_vector_tamper_fails(self) -> None:
        values = target.task_vector()
        for kind in ("identity", "extra"):
            changed = copy.deepcopy(values)
            if kind == "identity":
                changed[0]["question"] = changed[0]["question"].replace(".ae", ".zz")
            else:
                changed[0]["category"] = "forbidden"
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_task_vector(changed)

    def test_source_policy_is_outcome_blind_and_grants_no_launch(self) -> None:
        policy = target.source_policy()
        self.assertEqual(
            policy["runtime_boundary"],
            ["opaque_id", "question", "same_forward_public_pages"],
        )
        self.assertFalse(
            policy[
                "detail_page_field_value_prediction_evaluator_score_or_quality_opened_for_selection"
            ]
        )
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )
        self.assertFalse(policy["network_model_search_fetch_evaluator_or_benchmark_authorized"])

    def test_pure_population_has_no_external_or_privileged_capability(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden = {
            "category",
            "question_type",
            "task_category",
            "split",
            "ground_truth",
            "gold",
            "answer_key",
            "score",
            "reward",
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif (
                isinstance(node, ast.Subscript)
                and isinstance(node.slice, ast.Constant)
                and node.slice.value in forbidden
            ):
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
        self.assertFalse(
            any(
                name == bad or name.startswith(bad + ".")
                for bad in ("os", "pathlib", "subprocess", "socket", "requests", "httpx")
                for name in imports
            )
        )


if __name__ == "__main__":
    unittest.main()
