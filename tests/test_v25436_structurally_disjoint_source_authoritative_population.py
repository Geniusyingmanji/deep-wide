from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent import v25004_identity_bound_detail_fields as authority  # noqa: E402
from deepwide_agent import v25395_visible_membership_synthesis_runtime as membership  # noqa: E402
from deepwide_agent import v25436_structurally_disjoint_source_authoritative_population as target  # noqa: E402


class V25436StructurallyDisjointPopulationTests(unittest.TestCase):
    def test_vectors_are_complete_unique_and_hash_bound(self) -> None:
        identities = target.identity_vector()
        groups = target.group_vector()
        tasks = target.task_vector()
        self.assertEqual(len(identities), 80)
        self.assertEqual(len(set(identities)), 80)
        self.assertEqual(len(groups), 20)
        self.assertEqual(len(tasks), 20)
        self.assertEqual(
            target.payload_sha256(identities),
            target.EXPECTED_IDENTITY_VECTOR_SHA256,
        )
        self.assertEqual(
            target.payload_sha256(groups), target.EXPECTED_GROUP_VECTOR_SHA256
        )
        self.assertEqual(
            target.payload_sha256(tasks), target.EXPECTED_TASK_VECTOR_SHA256
        )

    def test_visible_membership_schema_and_authority_are_exact(self) -> None:
        for task_index, task in enumerate(target.task_vector()):
            expected = tuple(
                f"RFC {number}"
                for number in range(9160 + 4 * task_index, 9164 + 4 * task_index)
            )
            members, source = membership.visible_membership(task["question"])
            self.assertEqual(members, expected)
            self.assertEqual(source, "plural_inline_tag_vector")
            production_prompt = (
                "VISIBLE QUESTION:\n"
                + task["question"]
                + "\n\nREQUIRED COLUMNS:\n"
                + target.json.dumps(list(target.COLUMNS))
                + "\n\nBOUNDED WEB MATERIAL:\n\n"
                + "Produce the best-supported answer possible within the "
                "supplied material."
            )
            self.assertEqual(
                membership.parent.joint_parent.sparse._prompt_columns(
                    production_prompt,
                    ("Result", "Value"),
                ),
                target.COLUMNS,
            )
            self.assertTrue(authority._authorities(task["question"]))
            self.assertTrue(
                {"rfc", "editor"}.issubset(
                    set(authority._authority_tokens(task["question"]))
                )
            )

    def test_group_validation_and_tamper_fail_closed(self) -> None:
        value = target.group_vector()
        self.assertEqual(target.validate_group_vector(value), value)
        for kind in ("question", "identity_count", "opaque"):
            changed = copy.deepcopy(value)
            if kind == "question":
                changed[0]["task"]["question"] += " RFC 9239"
            elif kind == "identity_count":
                changed[0]["identity_count"] = 3
            else:
                changed[0]["task"]["opaque_id"] = changed[1]["task"]["opaque_id"]
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_group_vector(changed)

    def test_policy_and_gate_forbid_launch_and_signed_credit(self) -> None:
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
        self.assertEqual(gate["positive_signed_credit_count"], 0)
        self.assertEqual(gate["exact_normal_path_model_forwards_per_completed_task"], 3)


if __name__ == "__main__":
    unittest.main()
