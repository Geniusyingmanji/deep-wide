from __future__ import annotations

import ast
import copy
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25401_grounded_record_membership_runtime as parent  # noqa: E402
from deepwide_agent import v25542_visible_constraint_synthesis_runtime as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import QUESTION  # noqa: E402
from test_v25395_visible_membership_synthesis_runtime import MEMBERSHIP_QUESTION  # noqa: E402
from test_v25401_grounded_record_membership_runtime import (  # noqa: E402
    GroundedMembershipModel,
    run_runtime,
)


SCALE_QUESTION = MEMBERSHIP_QUESTION + " Express TLD Manager in millions."


class V25542VisibleConstraintSynthesisRuntimeTests(unittest.TestCase):
    def test_active_constraint_reaches_existing_third_call_without_new_effect(self) -> None:
        model = GroundedMembershipModel()
        result, stage, budget = run_runtime(
            target, model, question=SCALE_QUESTION
        )
        checked = target.validate_result(result)
        target.validate_stage_receipt(stage)
        receipt = checked["visible_constraint_synthesis_receipt"]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertIn("VISIBLE OUTPUT CONSTRAINT CONTRACT:", model.users[2])
        self.assertTrue(receipt["constraint_prompt_applied"])
        self.assertTrue(receipt["numeric_scale_active"])
        self.assertEqual(receipt["active_family_count"], 1)
        self.assertGreater(receipt["constraint_suffix_characters"], 0)
        self.assertFalse(receipt["parent_third_user_forwarded_byte_exact"])
        self.assertEqual(receipt["positive_signed_credit_count"], 0)
        self.assertFalse(stage["failure_present"])

    def test_no_constraint_is_parent_system_user_and_prediction_byte_exact(self) -> None:
        candidate_model = GroundedMembershipModel()
        parent_model = GroundedMembershipModel()
        result, _stage, budget = run_runtime(
            target, candidate_model, question=QUESTION
        )
        parent_result, _parent_stage, _ = run_runtime(
            parent, parent_model, question=QUESTION
        )
        checked = target.validate_result(result)
        receipt = checked["visible_constraint_synthesis_receipt"]
        self.assertFalse(receipt["constraint_prompt_applied"])
        self.assertEqual(receipt["constraint_suffix_characters"], 0)
        self.assertTrue(receipt["parent_third_user_forwarded_byte_exact"])
        self.assertEqual(candidate_model.systems, parent_model.systems)
        self.assertEqual(candidate_model.users, parent_model.users)
        self.assertEqual(checked["prediction"], parent_result["prediction"])
        self.assertEqual(budget["model_admitted_count"], 3)

    def test_observer_is_content_free_non_mutating_and_parent_bound(self) -> None:
        result, _stage, _budget = run_runtime(
            target, GroundedMembershipModel(), question=SCALE_QUESTION
        )
        checked = target.validate_result(result)
        receipt = checked["visible_constraint_synthesis_receipt"]
        observation = receipt["constraint_observation"]
        self.assertFalse(observation["observation_changes_prediction"])
        self.assertFalse(observation["observation_judges_factual_correctness"])
        self.assertFalse(
            observation[
                "contains_question_column_value_prediction_opaque_id_or_credential"
            ]
        )
        self.assertEqual(
            checked["prediction"], checked["private_parent_result"]["prediction"]
        )

    def test_mixed_concurrency_keeps_constraint_state_task_local(self) -> None:
        with ThreadPoolExecutor(max_workers=2) as pool:
            active_future = pool.submit(
                run_runtime,
                target,
                GroundedMembershipModel(),
                question=SCALE_QUESTION,
            )
            inactive_future = pool.submit(
                run_runtime,
                target,
                GroundedMembershipModel(),
                question=QUESTION,
            )
            active, _active_stage, _active_budget = active_future.result()
            inactive, _inactive_stage, _inactive_budget = inactive_future.result()
        active_receipt = target.validate_result(active)[
            "visible_constraint_synthesis_receipt"
        ]
        inactive_receipt = target.validate_result(inactive)[
            "visible_constraint_synthesis_receipt"
        ]
        self.assertTrue(active_receipt["constraint_prompt_applied"])
        self.assertTrue(active_receipt["numeric_scale_active"])
        self.assertFalse(inactive_receipt["constraint_prompt_applied"])
        self.assertFalse(inactive_receipt["numeric_scale_active"])

    def test_resealed_contract_receipt_parent_or_credit_tamper_fails(self) -> None:
        result, _stage, _budget = run_runtime(
            target, GroundedMembershipModel(), question=SCALE_QUESTION
        )
        for kind in ("contract", "receipt", "parent", "credit"):
            changed = copy.deepcopy(result)
            receipt = changed["visible_constraint_synthesis_receipt"]
            if kind == "contract":
                changed["private_visible_constraint_contract"]["active_family_count"] = 0
                changed["private_visible_constraint_contract"].pop(
                    "contract_payload_sha256"
                )
                changed["private_visible_constraint_contract"][
                    "contract_payload_sha256"
                ] = payload_sha256(changed["private_visible_constraint_contract"])
            elif kind == "receipt":
                receipt["constraint_suffix_characters"] += 1
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            elif kind == "parent":
                receipt["parent_result_payload_sha256"] = "a" * 64
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            else:
                receipt["positive_signed_credit_count"] = 1
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_runtime_is_label_blind_and_has_no_direct_external_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25542_visible_constraint_synthesis_runtime.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden_fields = {
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
                and node.slice.value in forbidden_fields
            ):
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
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
        for forbidden_call in ("open(", "getenv(", "run_official_eval_local("):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
