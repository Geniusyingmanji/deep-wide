from __future__ import annotations

import ast
import copy
import json
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
from deepwide_agent import v25492_visible_row_key_detail_runtime as target  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from test_v25119_grounded_target_record_paired_runtime import (  # noqa: E402
    GroundedFrontierSearch,
    limits,
)


QUESTION = (
    "Use public sources to return exactly one Markdown table. "
    "Columns exactly: Package | Version | Authors | Status."
)
TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": QUESTION,
}
INDEX_URL = "https://registry.example/packages/"
DETAIL_URL = "https://registry.example/packages/alpha/metadata"
DETAIL_PAGE = "alpha package metadata\nVersion: 2.0\nAuthors: Alice; Bob\nStatus: Stable"


class VisibleDetailModel:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0
        self.logical_calls = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens, json_mode
        self.logical_calls += 1
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if self.logical_calls == 1:
            text = json.dumps(
                {
                    "language": "English",
                    "columns": ["ignored"],
                    "queries": [
                        "alpha package official",
                        "alpha registry index",
                        "alpha version",
                        "alpha status",
                    ],
                }
            )
        elif self.logical_calls == 2:
            text = json.dumps(
                {
                    "pivots": ["alpha"],
                    "row_targets": ["alpha"],
                    "authority_terms": ["registry example"],
                    "queries": ["alpha metadata", "alpha official record"],
                    "records": [],
                }
            )
        else:
            text = (
                "| Package | Version | Authors | Status |\n"
                "|---|---|---|---|\n"
                "| alpha | 1.0 | Alice; Bob | Unknown |"
            )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class VisibleDetailSearch(GroundedFrontierSearch):
    def __init__(
        self,
        question: str,
        phase: str,
        *,
        mode: str = "valid",
    ) -> None:
        super().__init__(question, phase)
        self.mode = mode

    def fetch_urls(self, requests_):
        values = list(requests_)
        if len(values) == 1 and str(values[0].get("query")) == target.selection.REQUEST_QUERY:
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
                    "provider": "synthetic-visible-detail",
                }
            ]
        output = super().fetch_urls(values)
        if self._phase != target.PHASES[1]:
            return output
        page = next(
            (
                item
                for batch in output
                if isinstance(batch, dict)
                for item in (batch.get("results") or [])
                if isinstance(item, dict)
            ),
            None,
        )
        if page is None:
            return output
        page.update(
            {
                "url": INDEX_URL,
                "fetch_url": INDEX_URL,
                "requested_url": INDEX_URL,
                "title": "Package index",
                "page_links": [
                    {
                        "url": DETAIL_URL,
                        "text": "beta package metadata"
                        if self.mode == "anchor_mismatch"
                        else "alpha package metadata",
                    }
                ],
            }
        )
        return output


def run_runtime(*, mode: str = "valid", task: dict[str, str] | None = None):
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
                VisibleDetailSearch(QUESTION, phase, mode=mode),
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


class V25492VisibleRowKeyDetailRuntimeTests(unittest.TestCase):
    def test_one_parent_then_one_visible_detail_fetch_applies_fields(self) -> None:
        model, result, stage, budget = run_runtime()
        self.assertEqual(model.logical_calls, 3)
        self.assertEqual(budget["query_admitted_count"], 4)
        self.assertEqual(budget["model_admitted_count"], 3)
        self.assertLessEqual(budget["fetch_admitted_count"], 14)
        self.assertEqual(budget["fetch_rejected_count"], 0)
        self.assertTrue(result["prediction_changed"])
        self.assertIn("| alpha | 2.0 | Alice; Bob | Stable |", result["prediction"])
        receipt = result["visible_row_key_detail_receipt"]
        self.assertEqual(receipt["detail_admitted_fetch_count"], 1)
        self.assertEqual(receipt["detail_exact_nonredirected_page_count"], 1)
        self.assertGreaterEqual(receipt["applied_coordinate_count"], 1)
        self.assertFalse(stage["failure_present"])

    def test_anchor_mismatch_or_redirect_preserves_parent_byte_exact(self) -> None:
        for mode in ("anchor_mismatch", "redirect"):
            with self.subTest(mode=mode):
                _model, result, _stage, _budget = run_runtime(mode=mode)
                self.assertFalse(result["prediction_changed"])
                self.assertEqual(
                    result["predictions"][target.BASE_ARM],
                    result["predictions"][target.CANDIDATE_ARM],
                )

    def test_selection_uses_only_parent_fetch_batches_not_synthesized_url(self) -> None:
        _model, result, _stage, _budget = run_runtime(mode="anchor_mismatch")
        selection = result["private_visible_link_selection"]
        self.assertEqual(selection["requests"], [])
        self.assertEqual(
            result["visible_row_key_detail_receipt"]["detail_logical_request_count"],
            0,
        )

    def test_capacity_selection_never_attempts_an_overcap_fetch(self) -> None:
        budget = cap.PhysicalEffectBudget()
        budget.reserve("fetch", 14, stage="shared_first_wave_fetch")
        receipt = cap.validate_budget_receipt(budget.receipt())
        self.assertEqual(cap.FETCH_CAP - receipt["fetch_admitted_count"], 0)

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
                changed["private_visible_link_selection"]["requests"][0]["url"] += "x"
            elif kind == "application":
                changed["private_detail_application"]["candidate_prediction"] += "x"
            else:
                changed["visible_row_key_detail_receipt"][
                    "positive_signed_credit_count"
                ] = 1
            changed.pop("result_payload_sha256")
            changed["result_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_result(changed)

    def test_runtime_is_label_blind_and_has_no_direct_network_import(self) -> None:
        contract = target.integration_contract()
        self.assertEqual(contract["runtime_input_keys"], ["opaque_id", "question"])
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
