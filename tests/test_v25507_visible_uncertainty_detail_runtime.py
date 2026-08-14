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
from deepwide_agent import v25507_visible_uncertainty_detail_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v25119_grounded_target_record_paired_runtime import limits  # noqa: E402
from test_v25492_visible_row_key_detail_runtime import (  # noqa: E402
    DETAIL_PAGE,
    DETAIL_URL,
    QUESTION,
    TASK,
    VisibleDetailModel,
    VisibleDetailSearch,
)


BETA_DETAIL_URL = "https://registry.example/packages/beta/metadata"
BETA_DETAIL_PAGE = (
    "beta package metadata\n"
    "Version: 3.0\n"
    "Authors: Carol; Dan\n"
    "Status: Stable"
)


class TwoRowVisibleDetailModel(VisibleDetailModel):
    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        if self.logical_calls < 2:
            return super().complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        del system, user, max_output_tokens, json_mode
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        text = (
            "| Package | Version | Authors | Status |\n"
            "|---|---|---|---|\n"
            "| alpha | 1.0 | Alice; Bob | Unknown |\n"
            "| beta | Unknown | Carol; Dan | Unknown |"
        )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class UncertaintyDetailSearch(VisibleDetailSearch):
    def fetch_urls(self, requests_):
        values = list(requests_)
        if (
            len(values) == 1
            and str(values[0].get("query")) == target.selection.REQUEST_QUERY
        ):
            requested = str(values[0]["url"])
            self._prefixes[requested] = DETAIL_PAGE
            final = requested + "?redirected=1" if self.mode == "redirect" else requested
            return [
                {
                    "query": values[0]["query"],
                    "answer": "",
                    "results": [
                        {
                            "title": "alpha package metadata",
                            "url": final,
                            "fetch_url": requested,
                            "requested_url": requested,
                            "raw_content": DETAIL_PAGE,
                            "content": "",
                            "page_links": [],
                        }
                    ],
                    "error": None,
                    "provider": "synthetic-uncertainty-detail",
                }
            ]
        return super().fetch_urls(values)


class TwoRowUncertaintyDetailSearch(UncertaintyDetailSearch):
    def fetch_urls(self, requests_):
        values = list(requests_)
        if (
            len(values) == 1
            and str(values[0].get("query")) == target.selection.REQUEST_QUERY
            and str(values[0].get("url")) == BETA_DETAIL_URL
        ):
            self._prefixes[BETA_DETAIL_URL] = BETA_DETAIL_PAGE
            return [
                {
                    "query": values[0]["query"],
                    "answer": "",
                    "results": [
                        {
                            "title": "beta package metadata",
                            "url": BETA_DETAIL_URL,
                            "fetch_url": BETA_DETAIL_URL,
                            "requested_url": BETA_DETAIL_URL,
                            "raw_content": BETA_DETAIL_PAGE,
                            "content": "",
                            "page_links": [],
                        }
                    ],
                    "error": None,
                    "provider": "synthetic-two-row-detail",
                }
            ]
        output = super().fetch_urls(values)
        if self._phase != target.PHASES[1]:
            return output
        for batch in output:
            if not isinstance(batch, dict):
                continue
            for page in batch.get("results") or []:
                if isinstance(page, dict) and page.get("page_links"):
                    page["page_links"].append(
                        {"url": BETA_DETAIL_URL, "text": "beta package metadata"}
                    )
        return output


def run_runtime(
    *,
    mode: str = "valid",
    task: dict[str, str] | None = None,
    two_rows: bool = False,
):
    model = TwoRowVisibleDetailModel() if two_rows else VisibleDetailModel()
    search_type = TwoRowUncertaintyDetailSearch if two_rows else UncertaintyDetailSearch
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
                search_type(QUESTION, phase, mode=mode),
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


class V25507VisibleUncertaintyDetailRuntimeTests(unittest.TestCase):
    def test_two_safe_rows_schedule_the_row_with_more_unknown_cells(self) -> None:
        _model, result, _stage, _budget = run_runtime(two_rows=True)
        selected = result["private_uncertainty_selection"]
        self.assertEqual(len(selected["private_candidates"]), 2)
        self.assertEqual(selected["requests"][0]["title"], "beta")
        self.assertIn(
            "| beta | 3.0 | Carol; Dan | Stable |", result["prediction"]
        )
        self.assertIn(
            "| alpha | 1.0 | Alice; Bob | Unknown |", result["prediction"]
        )

    def test_one_parent_matched_control_and_one_detail_treatment(self) -> None:
        model, result, stage, budget = run_runtime()
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertEqual(budget["fetch_rejected_count"], 0)
        self.assertTrue(result["prediction_changed"])
        self.assertIn("| alpha | 2.0 | Alice; Bob | Stable |", result["prediction"])
        receipt = result["visible_uncertainty_detail_receipt"]
        self.assertEqual(receipt["detail_logical_request_count"], 1)
        self.assertEqual(receipt["detail_admitted_fetch_count"], 1)
        self.assertEqual(receipt["detail_exact_nonredirected_page_count"], 1)
        self.assertGreaterEqual(receipt["treatment_changed_coordinate_count"], 1)
        self.assertEqual(receipt["positive_signed_credit_count"], 0)
        self.assertFalse(stage["failure_present"])

    def test_control_uses_parent_pages_and_candidate_adds_only_detail(self) -> None:
        _model, result, _stage, _budget = run_runtime()
        receipt = result["visible_uncertainty_detail_receipt"]
        parent_pages = result["private_parent_result"]["private_same_forward_pages"]
        self.assertEqual(receipt["parent_candidate_page_count"], len(parent_pages))
        self.assertEqual(
            receipt["combined_candidate_page_count"],
            len(parent_pages) + len(result["private_detail_pages"]),
        )
        self.assertEqual(
            result["private_combined_candidate_pages"],
            [*parent_pages, *result["private_detail_pages"]],
        )

    def test_redirect_preserves_matched_control_byte_exact(self) -> None:
        _model, result, _stage, _budget = run_runtime(mode="redirect")
        self.assertFalse(result["prediction_changed"])
        self.assertEqual(
            result["predictions"][target.BASE_ARM],
            result["predictions"][target.CANDIDATE_ARM],
        )
        self.assertEqual(
            result["visible_uncertainty_detail_receipt"][
                "detail_exact_nonredirected_page_count"
            ],
            0,
        )

    def test_parent_and_detail_share_existing_outer_caps(self) -> None:
        _model, result, stage, budget = run_runtime()
        receipt = result["visible_uncertainty_detail_receipt"]
        self.assertEqual(receipt["final_query_count"], budget["query_admitted_count"])
        self.assertEqual(receipt["final_fetch_count"], budget["fetch_admitted_count"])
        self.assertEqual(receipt["final_model_count"], budget["model_admitted_count"])
        self.assertEqual(stage["outer_physical_budget_receipt"], budget)

    def test_privileged_input_rejected_before_any_effect(self) -> None:
        with self.assertRaises(ValueError):
            run_runtime(task={**TASK, "category": "forbidden"})

    def test_result_stage_selection_application_and_credit_tamper_fail(self) -> None:
        _model, result, stage, _budget = run_runtime()
        for kind in ("selection", "application", "credit", "stage"):
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
            if kind == "selection":
                changed["private_uncertainty_selection"]["requests"][0]["url"] += "x"
            elif kind == "application":
                changed["private_candidate_application"]["candidate_prediction"] += "x"
            else:
                changed["visible_uncertainty_detail_receipt"][
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
            contract["scheduling_signal"],
            "remaining_visible_unknown_nonkey_cell_count",
        )
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
        self.assertFalse(
            any(
                name == bad or name.startswith(bad + ".")
                for bad in ("os", "pathlib", "subprocess", "socket", "requests", "httpx")
                for name in imports
            )
        )


if __name__ == "__main__":
    unittest.main()
