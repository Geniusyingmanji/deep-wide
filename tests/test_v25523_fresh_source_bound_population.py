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

from deepwide_agent import v25018_multi_identity_external_contract as namespace  # noqa: E402
from deepwide_agent import v25509_fresh_multirow_uncertainty_population as prior9  # noqa: E402
from deepwide_agent import v25516_fresh_evidence_coverage_population as prior16  # noqa: E402
from deepwide_agent import v25523_fresh_source_bound_population as target  # noqa: E402


class V25523FreshSourceBoundPopulationTests(unittest.TestCase):
    def test_pair_vector_is_exact_next_forty_identity_block(self) -> None:
        cohort = list(namespace.TLD_COHORT)
        start = cohort.index(".bank") + 1
        expected = [
            tuple(cohort[index : index + 2])
            for index in range(start, start + 40, 2)
        ]
        pairs = target.pair_vector()
        flattened = [identity for pair in pairs for identity in pair]
        self.assertEqual(pairs, expected)
        self.assertEqual(len(pairs), 20)
        self.assertEqual(len(flattened), 40)
        self.assertEqual(len(set(flattened)), 40)
        self.assertEqual(flattened[0], ".bar")
        self.assertEqual(flattened[-1], ".bnpparibas")
        self.assertEqual(
            target.payload_sha256(pairs), target.EXPECTED_PAIR_VECTOR_SHA256
        )

    def test_rows_questions_and_opaque_ids_are_disjoint_from_consumed_blocks(self) -> None:
        tasks = target.task_vector()
        consumed_rows = {
            identity
            for pair in (*prior9.PAIRS, *prior16.PAIRS)
            for identity in pair
        }
        consumed_tasks = [*prior9.task_vector(), *prior16.task_vector()]
        self.assertFalse(
            {identity for pair in target.PAIRS for identity in pair}
            & consumed_rows
        )
        self.assertFalse(
            {task["question"] for task in tasks}
            & {task["question"] for task in consumed_tasks}
        )
        self.assertFalse(
            {task["opaque_id"] for task in tasks}
            & {task["opaque_id"] for task in consumed_tasks}
        )

    def test_task_vector_contains_only_visible_pair_inputs(self) -> None:
        tasks = target.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertEqual(len({row["opaque_id"] for row in tasks}), 20)
        for task, pair in zip(tasks, target.PAIRS, strict=True):
            self.assertEqual(set(task), {"opaque_id", "question"})
            self.assertEqual(task["question"].count("<DOMAIN>"), 2)
            self.assertEqual(task["question"].count("</DOMAIN>"), 2)
            self.assertIn(pair[0], task["question"])
            self.assertIn(pair[1], task["question"])
            self.assertNotIn("https://", task["question"])
            self.assertNotIn("iana", task["question"].casefold())
            self.assertNotIn("coverage", task["question"].casefold())
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )

    def test_source_policy_and_mechanism_gate_are_strict_and_label_blind(self) -> None:
        policy = target.source_policy()
        gate = target.mechanism_gate()
        self.assertEqual(
            policy["runtime_boundary"],
            ["opaque_id", "question", "same_forward_public_pages"],
        )
        self.assertTrue(
            policy[
                "next_lexical_block_is_row_identity_disjoint_from_v25509_and_v25516"
            ]
        )
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )
        self.assertEqual(gate["fixed_task_denominator"], 20)
        self.assertEqual(gate["minimum_exact_iana_url_page_tasks"], 3)
        self.assertEqual(gate["minimum_evidence_closed_observation_tasks"], 3)
        self.assertEqual(gate["minimum_material_candidate_tasks"], 2)
        self.assertEqual(gate["minimum_treatment_changed_tasks"], 2)
        self.assertEqual(gate["candidate_additional_fetches_beyond_parent"], 0)
        self.assertEqual(gate["positive_signed_credit_count"], 0)
        self.assertTrue(gate["postfreeze_shared_parent_quality_required"])

    def test_tamper_or_wrong_shape_fails(self) -> None:
        tasks = target.task_vector()
        for kind in ("drop", "question", "metadata"):
            changed = copy.deepcopy(tasks)
            if kind == "drop":
                changed.pop()
            elif kind == "question":
                changed[0]["question"] += " https://example.invalid"
            else:
                changed[0]["category"] = "forbidden"
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_task_vector(changed)

    def test_module_is_pure_and_has_no_outcome_or_effect_capability(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(
            any(
                name == bad or name.startswith(bad + ".")
                for bad in (
                    "os",
                    "pathlib",
                    "subprocess",
                    "socket",
                    "requests",
                    "httpx",
                )
                for name in imports
            )
        )
        self.assertNotIn("model.complete", source)
        self.assertNotIn("search_many", source)
        self.assertNotIn("fetch_urls", source)
        self.assertFalse(
            target.source_policy()[
                "network_model_search_fetch_evaluator_or_benchmark_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()
