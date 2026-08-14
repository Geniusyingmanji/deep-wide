from __future__ import annotations

import ast
import copy
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25253_outer_physical_cap_observed_runtime as cap  # noqa: E402
from deepwide_agent import v25500_generic_mechanical_field_runtime as target  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v25119_grounded_target_record_paired_runtime import limits  # noqa: E402
from test_v25492_visible_row_key_detail_runtime import (  # noqa: E402
    DETAIL_URL,
    TASK,
    VisibleDetailModel,
    VisibleDetailSearch,
)


DETAIL_CONTENT = (
    "alpha package metadata\n"
    "pkgVersion | 2.0\n"
    "Package Authors: Alice; Bob\n"
    "Status\n\nStable"
)


class GenericDetailSearch(VisibleDetailSearch):
    def fetch_urls(self, requests_):
        output = super().fetch_urls(requests_)
        values = list(requests_)
        if len(values) == 1 and str(values[0].get("url") or "") == DETAIL_URL:
            self._prefixes[DETAIL_URL] = DETAIL_CONTENT
        return output


def run_runtime(*, task: dict[str, str] | None = None):
    model = VisibleDetailModel()
    with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as raw:
        output = Path(raw)
        slots = output / "slots"
        slots.mkdir()
        for index in range(1, 5):
            (slots / f"slot_{index:02d}.lock").write_text("{}\n")
        bounded = DeadlineAwareGlobalModelSlotLimiter(
            model,
            slot_directory=slots,
            output_root=output,
            slot_cap=4,
            absolute_deadline=time.monotonic() + 240,
        )
        budget = cap.PhysicalEffectBudget()
        searches = {
            phase: cap.HardCappedSearchClient(
                GenericDetailSearch(TASK["question"], phase),
                budget,
                phase=phase,
            )
            for phase in target.PHASES
        }
        result, stage = target.run_task(
            TASK if task is None else task,
            model=cap.HardCappedModelLimiter(bounded, budget),
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return (
        model,
        target.validate_result(result),
        target.validate_stage_receipt(stage),
        cap.validate_budget_receipt(budget.receipt()),
    )


class V25500GenericMechanicalFieldRuntimeTests(unittest.TestCase):
    def test_one_parent_one_detail_fetch_and_generic_grammar_apply(self) -> None:
        model, result, stage, budget = run_runtime()
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertEqual(budget["fetch_rejected_count"], 0)
        self.assertTrue(result["prediction_changed"])
        self.assertIn(
            "| alpha | 2.0 | Alice; Bob | Stable |", result["prediction"]
        )
        receipt = result["generic_mechanical_field_receipt"]
        self.assertEqual(receipt["exact_detail_page_count"], 1)
        self.assertGreaterEqual(receipt["generic_mechanical_observation_count"], 3)
        # Authors is already correct in the frozen control, so the third
        # evidence-closed observation is deliberately counted as unchanged.
        self.assertEqual(receipt["generic_mechanical_observation_count"], 3)
        self.assertEqual(receipt["applied_coordinate_count"], 2)
        self.assertFalse(stage["failure_present"])

    def test_parent_and_detail_pages_are_one_candidate_input(self) -> None:
        _model, result, _stage, _budget = run_runtime()
        parent_result = result["private_parent_result"]
        expected = len(
            parent_result["private_parent_result"]["private_same_forward_pages"]
        ) + len(parent_result["private_detail_pages"])
        self.assertEqual(
            result["generic_mechanical_field_receipt"][
                "combined_candidate_page_count"
            ],
            expected,
        )
        self.assertEqual(len(result["private_combined_candidate_pages"]), expected)

    def test_no_additional_effect_beyond_v25492(self) -> None:
        _model, result, stage, budget = run_runtime()
        parent_stage = result["private_parent_result"][
            "visible_row_key_detail_receipt"
        ]
        self.assertEqual(
            budget["query_admitted_count"], parent_stage["final_query_count"]
        )
        self.assertEqual(
            budget["fetch_admitted_count"], parent_stage["final_fetch_count"]
        )
        self.assertEqual(
            budget["model_admitted_count"], parent_stage["final_model_count"]
        )
        self.assertEqual(stage["outer_physical_budget_receipt"], budget)

    def test_privileged_input_rejected_before_any_effect(self) -> None:
        with self.assertRaises(ValueError):
            run_runtime(task={**TASK, "category": "forbidden"})

    def test_result_stage_application_and_credit_tamper_fail(self) -> None:
        _model, result, stage, _budget = run_runtime()
        for kind in ("application", "credit", "stage"):
            if kind == "stage":
                changed_stage = copy.deepcopy(stage)
                changed_stage["outer_query4_fetch14_model3_caps_preserved"] = False
                changed_stage.pop("receipt_payload_sha256")
                changed_stage["receipt_payload_sha256"] = target.payload_sha256(
                    changed_stage
                )
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    target.validate_stage_receipt(changed_stage)
                continue
            changed = copy.deepcopy(result)
            if kind == "application":
                changed["private_generic_mechanical_application"][
                    "candidate_prediction"
                ] += "x"
            else:
                changed["generic_mechanical_field_receipt"][
                    "positive_signed_credit_count"
                ] = 1
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_runtime_is_label_blind_and_has_no_direct_network_import(self) -> None:
        contract = target.integration_contract()
        self.assertEqual(contract["runtime_input_keys"], ["opaque_id", "question"])
        self.assertEqual(
            contract["maximum_total_additional_fetches_beyond_v25472"], 1
        )
        self.assertEqual(contract["candidate_additional_queries"], 0)
        self.assertEqual(contract["candidate_additional_model_calls"], 0)
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
