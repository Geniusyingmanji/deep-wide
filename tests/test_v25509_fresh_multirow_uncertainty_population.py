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

from deepwide_agent import v25494_fresh_visible_row_key_population as cc_visible  # noqa: E402
from deepwide_agent import v25502_fresh_generic_mechanical_population as prior  # noqa: E402
from deepwide_agent import v25509_fresh_multirow_uncertainty_population as target  # noqa: E402


class V25509FreshMultirowUncertaintyPopulationTests(unittest.TestCase):
    def test_pair_vector_is_fixed_unique_and_structurally_cctld_disjoint(self) -> None:
        pairs = target.pair_vector()
        flattened = [identity for pair in pairs for identity in pair]
        self.assertEqual(len(pairs), 20)
        self.assertEqual(len(flattened), 40)
        self.assertEqual(len(set(flattened)), 40)
        self.assertTrue(all(len(value.removeprefix(".")) >= 3 for value in flattened))
        self.assertTrue(
            all(len(value.removeprefix(".")) == 2 for value in cc_visible.IDENTITIES)
        )
        self.assertFalse(set(flattened) & set(cc_visible.IDENTITIES))
        self.assertEqual(
            target.payload_sha256(pairs), target.EXPECTED_PAIR_VECTOR_SHA256
        )

    def test_task_vector_is_exactly_twenty_visible_pair_inputs(self) -> None:
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
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )

    def test_questions_and_ids_do_not_overlap_latest_consumed_population(self) -> None:
        tasks = target.task_vector()
        prior_tasks = prior.task_vector()
        self.assertFalse(
            {row["opaque_id"] for row in tasks}
            & {row["opaque_id"] for row in prior_tasks}
        )
        self.assertFalse(
            {row["question"] for row in tasks}
            & {row["question"] for row in prior_tasks}
        )

    def test_source_policy_and_gate_are_label_blind_fixed_and_strict(self) -> None:
        policy = target.source_policy()
        gate = target.mechanism_gate()
        self.assertEqual(
            policy["runtime_boundary"],
            ["opaque_id", "question", "same_forward_public_pages"],
        )
        self.assertTrue(
            policy[
                "three_plus_character_identifiers_are_structurally_disjoint_from_prior_two_letter_cctlds"
            ]
        )
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )
        self.assertEqual(gate["fixed_task_denominator"], 20)
        self.assertEqual(gate["minimum_multirow_eligible_link_tasks"], 6)
        self.assertEqual(gate["minimum_treatment_changed_tasks"], 2)
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
