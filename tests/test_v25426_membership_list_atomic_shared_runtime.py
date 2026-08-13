from __future__ import annotations

import ast
import copy
import inspect
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25426_membership_list_atomic_shared_runtime as target  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
)
from test_v25123_visible_legacy_query_compatible_runtime import (  # noqa: E402
    TASK,
    limits,
)
from test_v25349_shared_prefix_grounded_fact_paired_runtime import FactSearch  # noqa: E402
from test_v25395_visible_membership_synthesis_runtime import MEMBERSHIP_QUESTION  # noqa: E402
from test_v25401_grounded_record_membership_runtime import (  # noqa: E402
    DualIdentitySearch,
    GroundedMembershipModel,
)


def run_runtime(model: GroundedMembershipModel, *, question: str = MEMBERSHIP_QUESTION):
    task = {"opaque_id": TASK["opaque_id"], "question": question}
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
        root = Path(raw)
        slots = root / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n")
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            model,
            slot_directory=slots,
            output_root=root,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )
        budget = cap.PhysicalEffectBudget()
        outer = cap.HardCappedModelLimiter(bounded, budget)
        searches = {
            phase: cap.HardCappedSearchClient(
                DualIdentitySearch(question, phase), budget, phase=phase
            )
            for phase in target.PHASES
        }
        result, stage = target.run_task(
            task,
            model=outer,
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return result, stage, cap.validate_budget_receipt(budget.receipt())


class V25426MembershipListAtomicSharedRuntimeTests(unittest.TestCase):
    def test_one_parent_forward_applies_membership_and_exposes_three_shared_arms(self) -> None:
        model = GroundedMembershipModel()
        result, stage, budget = run_runtime(model)
        checked = target.validate_result(result)
        target.validate_stage_receipt(stage)
        receipt = checked["combined_membership_list_atomic_receipt"]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertIn("VISIBLE RECORD MEMBERSHIP CONSTRAINT:", model.systems[1])
        self.assertEqual(receipt["grounded_raw_membership_match_count"], 1)
        self.assertEqual(receipt["grounded_raw_membership_violation_count"], 0)
        self.assertTrue(receipt["all_grounded_raw_records_membership_aligned"])
        self.assertEqual(set(checked["predictions"]), set(target.ARMS))
        self.assertNotEqual(
            checked["predictions"][target.BASE_ARM],
            checked["predictions"][target.RAW_ARM],
        )
        self.assertEqual(
            checked["predictions"][target.RAW_ARM],
            checked["predictions"][target.GUARDED_ARM],
        )

    def test_provider_membership_violation_is_observed_and_not_filtered(self) -> None:
        model = GroundedMembershipModel(ignore_grounded_constraint=True)
        result, _stage, _budget = run_runtime(model)
        receipt = target.validate_result(result)[
            "combined_membership_list_atomic_receipt"
        ]
        self.assertEqual(receipt["grounded_raw_membership_match_count"], 0)
        self.assertEqual(receipt["grounded_raw_membership_mismatch_count"], 1)
        self.assertEqual(receipt["grounded_raw_membership_violation_count"], 1)
        self.assertFalse(receipt["all_grounded_raw_records_membership_aligned"])

    def test_wrapper_calls_v25401_once_and_has_no_provider_call_surface(self) -> None:
        source = inspect.getsource(target.run_task)
        self.assertEqual(source.count("parent.run_task("), 1)
        self.assertNotIn("model.complete", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("search(", source)

    def test_result_and_receipts_fail_closed_under_resealed_tamper(self) -> None:
        result, stage, _budget = run_runtime(GroundedMembershipModel())
        for kind in ("prediction", "receipt", "credit", "stage"):
            if kind == "stage":
                changed = copy.deepcopy(stage)
                changed["one_parent_forward_and_pure_local_guard"] = False
                changed.pop("receipt_payload_sha256")
                changed["receipt_payload_sha256"] = target.payload_sha256(changed)
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    target.validate_stage_receipt(changed)
                continue
            changed = copy.deepcopy(result)
            receipt = changed["combined_membership_list_atomic_receipt"]
            if kind == "prediction":
                changed["prediction"] = changed["predictions"][target.BASE_ARM]
                changed["prediction_sha256"] = target.hashlib.sha256(
                    changed["prediction"].encode()
                ).hexdigest()
            elif kind == "receipt":
                receipt["rejected_list_cardinality_decrease_count"] += 1
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = target.payload_sha256(receipt)
            else:
                receipt["positive_signed_credit_count"] = 1
                receipt.pop("receipt_payload_sha256")
                receipt["receipt_payload_sha256"] = target.payload_sha256(receipt)
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_privileged_input_is_rejected_before_any_effect(self) -> None:
        model = GroundedMembershipModel()
        task = {
            "opaque_id": TASK["opaque_id"],
            "question": MEMBERSHIP_QUESTION,
            "category": "forbidden",
        }
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
            root = Path(raw)
            slots = root / "slots"
            slots.mkdir()
            for index in range(1, 5):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n")
            bounded = DeadlineAwareGlobalModelSlotLimiter(
                model,
                slot_directory=slots,
                output_root=root,
                slot_cap=4,
                absolute_deadline=time.monotonic() + 240,
            )
            budget = cap.PhysicalEffectBudget()
            outer = cap.HardCappedModelLimiter(bounded, budget)
            searches = {
                phase: cap.HardCappedSearchClient(
                    FactSearch(MEMBERSHIP_QUESTION, phase), budget, phase=phase
                )
                for phase in target.PHASES
            }
            with self.assertRaises(ValueError):
                target.run_task(
                    task,
                    model=outer,
                    searches=searches,
                    limits=limits(),
                    budget=budget,
                    monotonic=time.monotonic,
                )
        self.assertEqual(model.logical_calls, 0)
        self.assertEqual(budget.receipt()["model_admitted_count"], 0)

    def test_runtime_source_is_label_blind_and_has_no_external_capability(self) -> None:
        path = ROOT / "src/deepwide_agent/v25426_membership_list_atomic_shared_runtime.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
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


if __name__ == "__main__":
    unittest.main()
