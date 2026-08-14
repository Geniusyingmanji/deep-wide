from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25401_grounded_record_membership_runtime as parent  # noqa: E402
from deepwide_agent import v25545_deterministic_visible_constraint_runtime as target  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from test_v25123_visible_legacy_query_compatible_runtime import QUESTION  # noqa: E402
from test_v25395_visible_membership_synthesis_runtime import MEMBERSHIP_QUESTION  # noqa: E402
from test_v25401_grounded_record_membership_runtime import (  # noqa: E402
    GroundedMembershipModel,
    run_runtime,
)


ORDER_QUESTION = MEMBERSHIP_QUESTION.replace(
    "Preserve row order.", "Sort by TLD Manager in ascending order."
)


class V25545DeterministicVisibleConstraintRuntimeTests(unittest.TestCase):
    def test_one_parent_forward_and_deterministic_sort_changes_candidate(self) -> None:
        model = GroundedMembershipModel()
        result, stage, budget = run_runtime(target, model, question=ORDER_QUESTION)
        checked = target.validate_result(result)
        target.validate_stage_receipt(stage)
        receipt = checked["deterministic_visible_constraint_receipt"]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertTrue(receipt["constraint_active"])
        self.assertEqual(receipt["sort_applied_count"], 1)
        self.assertTrue(checked["candidate_prediction_changed"])
        self.assertLess(
            checked["prediction"].find("| .uk |"),
            checked["prediction"].find("| .in |"),
        )
        self.assertEqual(receipt["positive_signed_credit_count"], 0)
        self.assertFalse(stage["failure_present"])

    def test_no_constraint_is_parent_prediction_byte_exact(self) -> None:
        candidate_model = GroundedMembershipModel()
        parent_model = GroundedMembershipModel()
        result, _stage, budget = run_runtime(target, candidate_model, question=QUESTION)
        parent_result, _parent_stage, _ = run_runtime(parent, parent_model, question=QUESTION)
        checked = target.validate_result(result)
        receipt = checked["deterministic_visible_constraint_receipt"]
        self.assertFalse(receipt["constraint_active"])
        self.assertFalse(checked["candidate_prediction_changed"])
        self.assertEqual(checked["prediction"], parent_result["prediction"])
        self.assertEqual(candidate_model.systems, parent_model.systems)
        self.assertEqual(candidate_model.users, parent_model.users)
        self.assertEqual(budget["model_admitted_count"], 3)

    def test_resealed_contract_receipt_parent_or_prediction_tamper_fails(self) -> None:
        result, _stage, _budget = run_runtime(
            target, GroundedMembershipModel(), question=ORDER_QUESTION
        )
        for kind in ("contract", "receipt", "parent", "prediction"):
            changed = copy.deepcopy(result)
            receipt = changed["deterministic_visible_constraint_receipt"]
            if kind == "contract":
                changed["private_visible_constraint_contract"]["active_family_count"] = 0
                changed["private_visible_constraint_contract"].pop("contract_payload_sha256")
                changed["private_visible_constraint_contract"]["contract_payload_sha256"] = payload_sha256(
                    changed["private_visible_constraint_contract"]
                )
            elif kind == "receipt":
                receipt["sort_applied_count"] = 0
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            elif kind == "parent":
                receipt["parent_result_payload_sha256"] = "a" * 64
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            else:
                changed["prediction"] = changed["predictions"][target.CONTROL_ARM]
                changed["prediction_sha256"] = changed["prediction_sha256_by_arm"][target.CONTROL_ARM]
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_runtime_is_label_blind_and_has_no_direct_external_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25545_deterministic_visible_constraint_runtime.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        privileged: list[str] = []
        forbidden_fields = {"category", "question_type", "task_category", "split", "ground_truth", "gold", "answer_key", "score", "reward"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant) and node.slice.value in forbidden_fields:
                privileged.append(str(node.slice.value))
        self.assertEqual(privileged, [])
        for forbidden in ("os", "pathlib", "subprocess", "requests", "httpx", "socket", "urllib"):
            self.assertFalse(any(name == forbidden or name.startswith(forbidden + ".") for name in imports))
        for forbidden_call in ("open(", "getenv(", "run_official_eval_local("):
            self.assertNotIn(forbidden_call, source)


if __name__ == "__main__":
    unittest.main()
