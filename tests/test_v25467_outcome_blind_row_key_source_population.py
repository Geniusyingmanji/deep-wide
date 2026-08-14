from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25395_visible_membership_synthesis_runtime as membership  # noqa: E402
from deepwide_agent import v25467_outcome_blind_row_key_source_population as target  # noqa: E402


class V25467OutcomeBlindRowKeySourcePopulationTests(unittest.TestCase):
    def test_selected_whole_block_is_complete_unique_and_hash_bound(self) -> None:
        clues = target.selected_clues()
        tasks = target.task_vector()
        self.assertEqual(len(clues), target.TASK_COUNT)
        self.assertEqual(len(set(clues)), target.TASK_COUNT)
        self.assertEqual(len(tasks), target.TASK_COUNT)
        self.assertEqual(
            target.payload_sha256(clues), target.EXPECTED_CLUE_VECTOR_SHA256
        )
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )

    def test_selection_is_first_zero_consumed_overlap_block(self) -> None:
        consumed = set(target.CONSUMED_PUBLIC_CLUES)
        overlaps = [
            len(set(block).intersection(consumed)) for block in target.CANDIDATE_BLOCKS
        ]
        self.assertEqual(overlaps[target.SELECTED_BLOCK_INDEX], 0)
        self.assertEqual(
            target.SELECTED_BLOCK_INDEX,
            next(index for index, overlap in enumerate(overlaps) if overlap == 0),
        )
        self.assertEqual(
            target.SELECTION_RULE,
            "first_whole_static_twenty_clue_block_with_zero_consumed_overlap",
        )

    def test_questions_have_schema_and_authority_but_no_visible_membership(self) -> None:
        for task in target.task_vector():
            question = task["question"]
            self.assertTrue(all(column in question for column in target.COLUMNS))
            self.assertIn("IANA Root Zone Database", question)
            members, source = membership.visible_membership(question)
            self.assertEqual(members, ())
            self.assertEqual(source, "none")
            self.assertNotIn("https://", question)
            self.assertNotIn("<ENTITIES>", question)

    def test_task_validation_and_tamper_fail_closed(self) -> None:
        values = target.task_vector()
        self.assertEqual(target.validate_task_vector(values), values)
        for kind in ("question", "opaque", "denominator"):
            changed = copy.deepcopy(values)
            if kind == "question":
                changed[0]["question"] += " .af"
            elif kind == "opaque":
                changed[0]["opaque_id"] = changed[1]["opaque_id"]
            else:
                changed.pop()
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_task_vector(changed)

    def test_policy_and_gate_are_label_blind_and_forbid_launch(self) -> None:
        policy = target.source_policy()
        gate = target.mechanism_gate()
        self.assertFalse(
            policy["network_model_search_fetch_evaluator_or_benchmark_authorized"]
        )
        self.assertFalse(
            policy[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read"
            ]
        )
        self.assertTrue(policy["no_visible_membership_or_row_key_tag"])
        self.assertFalse(
            policy["individual_clue_or_task_retention_replacement_or_ranking"]
        )
        self.assertEqual(gate["positive_signed_credit_count"], 0)
        self.assertEqual(gate["candidate_additional_queries"], 0)
        self.assertEqual(gate["candidate_additional_fetches"], 0)
        self.assertEqual(gate["candidate_additional_model_calls"], 0)

    def test_pure_population_module_has_no_effect_or_privileged_imports(self) -> None:
        source = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
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
        self.assertTrue(
            imports.isdisjoint(
                {"os", "pathlib", "subprocess", "socket", "requests", "urllib", "http"}
            )
        )
        for forbidden in (
            "ground_truth",
            "historical_correctness",
            "results.csv",
            "model.complete",
            "search_many",
            "fetch_urls",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
