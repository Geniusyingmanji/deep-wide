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
from deepwide_agent import v25530_iana_layout_runtime as target  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v25119_grounded_target_record_paired_runtime import limits  # noqa: E402
from test_v25518_evidence_coverage_external import (  # noqa: E402
    FIRST,
    SECOND,
    GenericIanaSearch,
    MultirowIanaModel,
    contract,
)


DETAIL_LAYOUT = (
    f"{SECOND} Domain Delegation Data\n\n"
    f"Delegation Record for {SECOND.upper()}\n\n"
    "(Generic top-level domain)\n\n"
    "Sponsoring Organisation\n\n"
    "Layout Verified Registry, Inc.\n\n"
    "Administrative Contact\n\nPerson"
)


class LayoutIanaSearch(GenericIanaSearch):
    def fetch_urls(self, requests_):
        values = list(requests_)
        output = super().fetch_urls(values)
        if (
            len(values) == 1
            and str(values[0].get("query"))
            == target.parent.selection.REQUEST_QUERY
        ):
            requested = str(values[0]["url"])
            self._prefixes[requested] = DETAIL_LAYOUT
            for batch in output:
                for page in batch.get("results") or []:
                    page["title"] = f"{SECOND} Domain Delegation Data"
                    page["raw_content"] = DETAIL_LAYOUT
                    page["content"] = ""
        return output


def run_runtime(task: dict[str, str] | None = None):
    visible = contract.task_vector()[0] if task is None else task
    model = MultirowIanaModel()
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
                LayoutIanaSearch(visible["question"], phase),
                budget,
                phase=phase,
            )
            for phase in target.PHASES
        }
        result, stage = target.run_task(
            visible,
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


class V25530IanaLayoutRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.model, cls.result, cls.stage, cls.budget = run_runtime()

    def test_one_parent_forward_and_shared_detail_page_apply_layout(self) -> None:
        receipt = self.result["iana_layout_receipt"]
        parser = receipt["iana_layout_parser_receipt"]
        self.assertEqual(self.model.logical_calls, 3)
        self.assertEqual(self.budget["query_admitted_count"], 4)
        self.assertEqual(self.budget["model_admitted_count"], 3)
        self.assertLessEqual(self.budget["fetch_admitted_count"], 14)
        self.assertEqual(receipt["detail_logical_request_count"], 1)
        self.assertEqual(receipt["detail_exact_nonredirected_page_count"], 1)
        self.assertEqual(parser["exact_iana_url_page_count"], 1)
        self.assertEqual(parser["url_row_key_bound_page_count"], 1)
        self.assertEqual(parser["identity_surface_bound_page_count"], 1)
        self.assertEqual(parser["iana_layout_complete_page_count"], 1)
        self.assertEqual(parser["evidence_closed_observation_count"], 2)
        self.assertEqual(parser["applied_coordinate_count"], 2)
        self.assertEqual(receipt["treatment_changed_coordinate_count"], 2)
        self.assertTrue(self.result["prediction_changed"])
        self.assertIn(
            f"| {SECOND} | Generic | Layout Verified Registry, Inc. |",
            self.result["prediction"],
        )

    def test_base_is_exact_parent_control_and_provider_effects_are_unchanged(self) -> None:
        parent = target.parent.validate_result(self.result["private_parent_result"])
        receipt = self.result["iana_layout_receipt"]
        self.assertEqual(
            self.result["predictions"][target.BASE_ARM],
            parent["predictions"][target.parent.BASE_ARM],
        )
        self.assertEqual(
            receipt["final_query_count"], self.budget["query_admitted_count"]
        )
        self.assertEqual(
            receipt["final_fetch_count"], self.budget["fetch_admitted_count"]
        )
        self.assertEqual(
            receipt["final_model_count"], self.budget["model_admitted_count"]
        )
        self.assertTrue(
            receipt["iana_layout_parser_adds_zero_query_fetch_or_model_effect"]
        )

    def test_runtime_replay_and_stage_receipts_are_closed(self) -> None:
        self.assertEqual(target.validate_result(self.result), self.result)
        self.assertEqual(target.validate_stage_receipt(self.stage), self.stage)
        self.assertEqual(
            self.stage["outer_physical_budget_receipt"], self.budget
        )

    def test_resealed_application_parser_stage_or_credit_tamper_fails(self) -> None:
        for kind in ("application", "parser", "stage", "credit"):
            if kind == "stage":
                changed_stage = copy.deepcopy(self.stage)
                changed_stage["iana_layout_parser_adds_zero_provider_effect"] = False
                changed_stage.pop("receipt_payload_sha256")
                changed_stage["receipt_payload_sha256"] = target.payload_sha256(
                    changed_stage
                )
                with self.subTest(kind=kind), self.assertRaises(ValueError):
                    target.validate_stage_receipt(changed_stage)
                continue
            changed = copy.deepcopy(self.result)
            if kind == "application":
                changed["private_iana_layout_application"][
                    "candidate_prediction"
                ] = changed["predictions"][target.BASE_ARM]
            elif kind == "parser":
                changed["iana_layout_receipt"]["iana_layout_parser_receipt"][
                    "iana_layout_complete_page_count"
                ] = 0
            else:
                changed["iana_layout_receipt"]["positive_signed_credit_count"] = 1
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_privileged_input_is_rejected_before_effect(self) -> None:
        budget = cap.PhysicalEffectBudget()
        with self.assertRaises(ValueError):
            target.run_task(
                {**contract.task_vector()[0], "category": "forbidden"},
                model=object(),
                searches={},
                limits=limits(),
                budget=budget,
                monotonic=time.monotonic,
            )
        self.assertEqual(budget.receipt()["fetch_admitted_count"], 0)

    def test_contract_preserves_parent_caps_and_zero_signed_credit(self) -> None:
        value = target.integration_contract()
        self.assertEqual(
            value["maximum_candidate_additional_fetches_beyond_parent"], 0
        )
        self.assertEqual(value["candidate_additional_queries_beyond_parent"], 0)
        self.assertEqual(value["candidate_additional_model_calls_beyond_parent"], 0)
        self.assertEqual(value["outer_query_cap"], 4)
        self.assertEqual(value["outer_fetch_cap"], 14)
        self.assertEqual(value["outer_normal_path_model_cap"], 3)
        self.assertFalse(
            value["entropy_or_information_gain_assigns_signed_credit"]
        )

    def test_runtime_is_label_blind_and_has_no_direct_effect_import(self) -> None:
        source_text = Path(target.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source_text)
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
                name == blocked or name.startswith(blocked + ".")
                for blocked in (
                    "requests",
                    "httpx",
                    "socket",
                    "subprocess",
                    "os",
                )
                for name in imports
            )
        )


if __name__ == "__main__":
    unittest.main()
