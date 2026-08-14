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
from deepwide_agent import v25484_row_key_iana_detail_runtime as target  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v25119_grounded_target_record_paired_runtime import limits  # noqa: E402
from test_v25472_qualified_source_label_runtime import (  # noqa: E402
    QUESTION,
    TASK,
    QualifiedModel,
    QualifiedSearch,
)


DETAIL_URL = "https://www.iana.org/domains/root/db/af.html"
DETAIL_PAGE = (
    ".af Domain Delegation Data\n"
    "TLD Type | country-code top-level domain\n"
    "ccTLD Manager\n\nAfghanistan Network Information Center"
)


class DirectIanaSearch(QualifiedSearch):
    def __init__(self, question: str, phase: str, *, redirect: bool = False) -> None:
        super().__init__(question, phase)
        self.redirect = redirect

    def fetch_urls(self, requests_):
        values = list(requests_)
        if (
            len(values) == 1
            and str(values[0].get("query") or "").startswith(
                "official IANA detail page"
            )
        ):
            requested = str(values[0]["url"])
            self._prefixes[requested] = DETAIL_PAGE
            final = requested + "?redirected=1" if self.redirect else requested
            return [
                {
                    "query": values[0].get("query", ""),
                    "answer": "",
                    "results": [
                        {
                            "title": ".af Domain Delegation Data",
                            "url": final,
                            "fetch_url": requested,
                            "requested_url": requested,
                            "raw_content": DETAIL_PAGE,
                            "content": "",
                        }
                    ],
                    "error": None,
                    "provider": "synthetic-direct-detail-fetch",
                }
            ]
        return super().fetch_urls(values)


def run_runtime(*, redirect: bool = False):
    model = QualifiedModel()
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
                DirectIanaSearch(QUESTION, phase, redirect=redirect),
                budget,
                phase=phase,
            )
            for phase in target.PHASES
        }
        result, stage = target.run_task(
            TASK,
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


class V25484RowKeyIanaDetailRuntimeTests(unittest.TestCase):
    def test_one_parent_then_capacity_safe_detail_candidate(self) -> None:
        model, result, stage, budget = run_runtime()
        receipt = result["row_key_iana_detail_receipt"]
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertEqual(budget["fetch_rejected_count"], 0)
        self.assertEqual(
            receipt["final_fetch_count"],
            receipt["parent_fetch_count"] + receipt["detail_admitted_fetch_count"],
        )
        self.assertEqual(receipt["detail_exact_nonredirected_page_count"], 1)
        self.assertGreaterEqual(receipt["applied_coordinate_count"], 1)
        self.assertTrue(result["prediction_changed"])
        self.assertIn("Afghanistan Network Information Center", result["prediction"])
        self.assertFalse(stage["failure_present"])

    def test_base_is_exact_v25472_parent_prediction(self) -> None:
        _model, result, _stage, _budget = run_runtime()
        parent = target.parent.validate_result(result["private_parent_result"])
        self.assertEqual(result["predictions"][target.BASE_ARM], parent["prediction"])
        self.assertTrue(
            result["row_key_iana_detail_receipt"][
                "qualified_source_label_parent_prediction_is_exact_control"
            ]
        )

    def test_redirected_page_is_not_admitted(self) -> None:
        _model, result, _stage, budget = run_runtime(redirect=True)
        receipt = result["row_key_iana_detail_receipt"]
        self.assertEqual(receipt["detail_exact_nonredirected_page_count"], 0)
        self.assertEqual(receipt["applied_coordinate_count"], 0)
        self.assertFalse(result["prediction_changed"])
        self.assertEqual(budget["fetch_rejected_count"], 0)

    def test_capacity_selection_never_attempts_overcap_fetch(self) -> None:
        budget = cap.PhysicalEffectBudget()
        budget.reserve("fetch", 14, stage="shared_first_wave_fetch")
        parent_budget = cap.validate_budget_receipt(budget.receipt())
        remaining = max(0, cap.FETCH_CAP - parent_budget["fetch_admitted_count"])
        self.assertEqual(remaining, 0)

    def test_resealed_application_receipt_stage_or_credit_tamper_fails(self) -> None:
        _model, result, stage, _budget = run_runtime()
        for kind in ("application", "receipt", "stage", "credit"):
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
                changed["private_row_key_iana_detail_application"][
                    "candidate_prediction"
                ] = changed["predictions"][target.BASE_ARM]
            elif kind == "receipt":
                changed["row_key_iana_detail_receipt"]["final_fetch_count"] += 1
            else:
                changed["row_key_iana_detail_receipt"][
                    "positive_signed_credit_count"
                ] = 1
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_privileged_input_is_rejected_before_effect(self) -> None:
        budget = cap.PhysicalEffectBudget()
        with self.assertRaises(ValueError):
            target.run_task(
                {**TASK, "category": "forbidden"},
                model=object(),
                searches={},
                limits=limits(),
                budget=budget,
                monotonic=time.monotonic,
            )
        self.assertEqual(budget.receipt()["fetch_admitted_count"], 0)

    def test_runtime_is_label_blind_and_has_no_direct_network_import(self) -> None:
        contract = target.integration_contract()
        self.assertEqual(contract["maximum_candidate_additional_fetches"], 1)
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
        for name in ("requests", "httpx", "socket", "subprocess", "os"):
            self.assertFalse(
                any(value == name or value.startswith(name + ".") for value in imports)
            )


if __name__ == "__main__":
    unittest.main()
