from __future__ import annotations

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
from deepwide_agent import v25521_source_bound_detail_runtime as runtime  # noqa: E402
from deepwide_agent import v25525_source_bound_external_contract as contract  # noqa: E402
from deepwide_agent.clients import ModelResult  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter  # noqa: E402
from scripts import run_v25525_source_bound_external as runner  # noqa: E402
from test_v25119_grounded_target_record_paired_runtime import (  # noqa: E402
    build_projection,
    limits,
)
from test_v25496_visible_row_key_detail_external import (  # noqa: E402
    VisibleIanaModel,
    VisibleIanaSearch,
)


FIRST, SECOND = contract.population.PAIRS[0]
FIRST_DETAIL_URL = (
    f"https://www.iana.org/domains/root/db/{FIRST.removeprefix('.')}.html"
)
SECOND_DETAIL_URL = (
    f"https://www.iana.org/domains/root/db/{SECOND.removeprefix('.')}.html"
)
FIRST_PARENT_URL = (
    f"https://registry.example/tld/{FIRST.removeprefix('.')}/summary"
)
FIRST_PARENT_PAGE = (
    f"{FIRST} Domain Delegation Data\n"
    "tldType | generic top-level domain\n"
    f"TLD Manager\n\n{FIRST.removeprefix('.').upper()}"
)
GENERIC_DETAIL_PAGE = (
    f"{SECOND} Domain Delegation Data\n"
    "tldType | generic top-level domain\n"
    f"TLD Manager\n\n{SECOND.removeprefix('.').upper()}"
)


class MultirowIanaModel(VisibleIanaModel):
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
            "| Domain | Type | TLD Manager |\n"
            "|---|---|---|\n"
            f"| {FIRST} | legacy sponsored domain | Former Registry One |\n"
            f"| {SECOND} | retired country-code domain | Former Registry Two |"
        )
        return ModelResult(text=text, usage={}, response_id=None, attempts=1)


class GenericIanaSearch(VisibleIanaSearch):
    def fetch_urls(self, requests_):
        values = list(requests_)
        if (
            len(values) == 1
            and str(values[0].get("query"))
            == runtime.parent.selection.REQUEST_QUERY
        ):
            requested = str(values[0]["url"])
            self._prefixes[requested] = GENERIC_DETAIL_PAGE
            return [
                {
                    "query": values[0]["query"],
                    "answer": "",
                    "results": [
                        {
                            "title": f"{SECOND} Domain Delegation Data",
                            "url": requested,
                            "fetch_url": requested,
                            "requested_url": requested,
                            "raw_content": GENERIC_DETAIL_PAGE,
                            "content": "",
                            "page_links": [],
                        }
                    ],
                    "error": None,
                    "provider": "synthetic-multirow-detail",
                }
            ]
        output = super().fetch_urls(values)
        if self._phase == runtime.PHASES[0] and output:
            projected = build_projection(
                self._question,
                {
                    "title": f"{FIRST} Domain Delegation Data",
                    "url": FIRST_PARENT_URL,
                    "text": FIRST_PARENT_PAGE,
                },
            )
            first = output[0]["results"][0]
            first.update(
                {
                    "title": f"{FIRST} Domain Delegation Data",
                    "url": FIRST_PARENT_URL,
                    "fetch_url": FIRST_PARENT_URL,
                    "requested_url": FIRST_PARENT_URL,
                    "raw_content": projected["projection"],
                    "content": "",
                    "page_links": [],
                }
            )
            self._prefixes[FIRST_PARENT_URL] = FIRST_PARENT_PAGE
        if self._phase == runtime.PHASES[1]:
            for batch in output:
                for page in batch.get("results") or []:
                    page["page_links"] = [
                        {"url": FIRST_DETAIL_URL, "text": FIRST},
                        {"url": SECOND_DETAIL_URL, "text": SECOND},
                    ]
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
                GenericIanaSearch(visible["question"], phase), budget, phase=phase
            )
            for phase in runtime.PHASES
        }
        result, stage = runtime.run_task(
            visible,
            model=cap.HardCappedModelLimiter(bounded, budget),
            searches=searches,
            limits=limits(),
            budget=budget,
            monotonic=time.monotonic,
        )
    return model, result, stage, budget


class _BudgetReplay:
    def __init__(self, value: dict) -> None:
        self._value = copy.deepcopy(value)

    def receipt(self) -> dict:
        return copy.deepcopy(self._value)


def completed_row() -> tuple[dict, dict, dict]:
    task = contract.task_vector()[0]
    _model, result, stage, budget = run_runtime(task)
    row = runner._from_runtime(
        task,
        result,
        stage,
        elapsed=1.0,
        budget=_BudgetReplay(budget.receipt()),
        health=runner._health(),
    )
    return runner.validate_task_row(row), result, stage


class V25525SourceBoundExternalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.row, cls.result, cls.stage = completed_row()

    def test_contract_population_caps_and_quality_gate_are_frozen(self) -> None:
        self.assertEqual(len(contract.task_vector()), 20)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 16)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["model_calls"], 3)
        self.assertEqual(runner.ARMS, runtime.ARMS)
        gate = contract.mechanism_gate()
        self.assertEqual(gate["minimum_multirow_eligible_link_tasks"], 6)
        self.assertEqual(gate["minimum_treatment_changed_tasks"], 2)
        self.assertTrue(
            contract.quality_gate()[
                "candidate_whole_table_exact_strictly_greater_than_base"
            ]
        )

    def test_clone_namespace_resolves_effect_infrastructure_before_effect(self) -> None:
        receipt = runner.clone_namespace_receipt()
        self.assertEqual(receipt["unresolved_function_count"], 0)
        self.assertEqual(receipt["unresolved_global_name_count"], 0)
        for name in (
            "fcntl_resolved",
            "socket_resolved",
            "subprocess_resolved",
            "thread_pool_executor_resolved",
            "as_completed_resolved",
            "lease_helper_resolved",
        ):
            self.assertTrue(receipt[name])

    def test_positive_source_bound_chain_decodes_native_receipts(self) -> None:
        decoded = runner._decode_completed(self.result, self.stage)
        reach = decoded["coverage_receipt"]
        receipt = decoded["source_bound_receipt"]
        self.assertGreaterEqual(reach["eligible_unique_link_count"], 2)
        self.assertEqual(reach["coverage_probe_covered_row_count"], 1)
        self.assertEqual(reach["positive_evidence_deficit_candidate_count"], 1)
        self.assertEqual(reach["detail_admitted_fetch_count"], 1)
        self.assertEqual(reach["detail_exact_nonredirected_page_count"], 1)
        self.assertEqual(receipt["detail_exact_iana_url_page_count"], 1)
        self.assertEqual(receipt["detail_identity_surface_bound_page_count"], 1)
        self.assertGreaterEqual(
            receipt["detail_evidence_closed_observation_count"], 2
        )
        self.assertGreaterEqual(receipt["detail_applied_coordinate_count"], 1)
        self.assertTrue(receipt["candidate_prediction_changed"])

    def test_frozen_task_row_contains_both_shared_effect_predictions(self) -> None:
        self.assertEqual(set(self.row["predictions"]), set(runtime.ARMS))
        self.assertNotIn("Unknown", self.row["predictions"][runtime.BASE_ARM])
        self.assertTrue(self.row["runtime_completed"])
        self.assertTrue(self.row["candidate_prediction_changed"])
        self.assertGreaterEqual(self.row["eligible_unique_link_count"], 2)
        self.assertGreaterEqual(
            self.row["detail_evidence_closed_observation_count"], 2
        )
        self.assertGreaterEqual(self.row["treatment_changed_coordinate_count"], 1)
        self.assertIn(
            SECOND.removeprefix(".").upper(),
            self.row["predictions"][runtime.CANDIDATE_ARM],
        )
        self.assertNotEqual(
            self.row["predictions"][runtime.BASE_ARM],
            self.row["predictions"][runtime.CANDIDATE_ARM],
        )

    def test_twenty_row_aggregate_recomputes_source_bound_stage_funnel(self) -> None:
        rows = [self.row]
        for task in contract.task_vector()[1:]:
            rows.append(
                runner._terminal_outer_failure(
                    task,
                    RuntimeError("synthetic-fixed-denominator"),
                    1.0,
                    budget=None,
                    health=None,
                )
            )
        aggregate = runner.aggregate_rows(rows, wall_seconds=1.0)
        decision = runner.mechanism_decision(aggregate)
        self.assertEqual(aggregate["task_count"], 20)
        self.assertEqual(aggregate["completed_runtime_tasks"], 1)
        self.assertEqual(aggregate["failure_as_zero_tasks"], 19)
        self.assertEqual(aggregate["exact_iana_url_page_tasks"], 1)
        self.assertEqual(aggregate["identity_surface_bound_page_tasks"], 1)
        self.assertGreaterEqual(aggregate["evidence_closed_observation_tasks"], 1)
        self.assertGreaterEqual(aggregate["material_candidate_tasks"], 1)
        self.assertEqual(
            aggregate["detail_applied_coordinate_count_total"],
            aggregate["treatment_changed_coordinate_count_total"],
        )
        self.assertFalse(decision["mechanism_gate_passed"])

    def test_failure_as_zero_freezes_identical_fallback_arms(self) -> None:
        row = runner._terminal_outer_failure(
            contract.task_vector()[0],
            RuntimeError("synthetic"),
            1.0,
            budget=None,
            health=None,
        )
        self.assertTrue(row["failure_as_zero"])
        self.assertEqual(len(set(row["predictions"].values())), 1)
        self.assertEqual(row["eligible_unique_link_count"], 0)

    def test_resealed_prediction_receipt_or_credit_tamper_fails(self) -> None:
        for kind in ("prediction", "receipt", "credit"):
            changed = copy.deepcopy(self.row)
            if kind == "prediction":
                changed["predictions"][runtime.CANDIDATE_ARM] += "x"
            elif kind == "receipt":
                changed["runtime_result"]["source_bound_detail_receipt"][
                    "detail_admitted_fetch_count"
                ] += 1
            else:
                changed["positive_signed_credit_count"] = 1
            changed.pop("result_payload_sha256")
            changed = contract.seal(changed, "result_payload_sha256")
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runner.validate_task_row(changed)

    def test_forward_closure_excludes_truth_evaluator_and_result_artifacts(self) -> None:
        paths = {str(path) for path in contract.forward_dependency_closure(ROOT)}
        self.assertIn(str(contract.CLONE_HELPER), paths)
        self.assertFalse(any("evaluate_v25525" in path for path in paths))
        self.assertFalse(any(path.startswith("results/") for path in paths))
        self.assertFalse(any(path.startswith("outputs/") for path in paths))

    def test_runtime_boundary_rejects_privileged_input_before_effect(self) -> None:
        task = {**contract.task_vector()[0], "category": "forbidden"}
        with self.assertRaises(ValueError):
            runner.run_one_task(task)


if __name__ == "__main__":
    unittest.main()
