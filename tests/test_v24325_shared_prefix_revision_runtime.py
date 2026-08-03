from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24325_shared_prefix_revision_runtime import (  # noqa: E402
    run_v24325_task,
    run_v24325_total_task,
    validate_result,
)


TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": (
        "Use web evidence to complete the table. The column names are: Name, Year. "
        "Return one Markdown table only."
    ),
}
PLAN = json.dumps(
    {
        "language": "English",
        "columns": ["wrong"],
        "row_target_hint": "",
        "queries": ["query one", "query two", "query three", "query four"],
    }
)
BASELINE_UNKNOWN = """```markdown
| Name | Year |
| --- | --- |
| Alpha | Unknown |
```"""
BASELINE_KNOWN = """```markdown
| Name | Year |
| --- | --- |
| Alpha | 2024 |
```"""


def proposal(table: str, evidence_ids: list[str]) -> str:
    return json.dumps(
        {
            "candidate_table": table,
            "cell_evidence": [
                {
                    "row_key": "Alpha",
                    "column": "Year",
                    "evidence_ids": evidence_ids,
                }
            ],
        }
    )


def candidate(year: str) -> str:
    return f"""```markdown
| Name | Year |
| --- | --- |
| Alpha | {year} |
```"""


class Clock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        self.value += 0.001
        return self.value


class FakeModel:
    def __init__(
        self,
        outputs: list[str | BaseException],
        *,
        reject_index: int | None = None,
        reject_after_request_index: int | None = None,
    ) -> None:
        self.outputs = list(outputs)
        self.requests = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.prompts: list[tuple[str, str, bool]] = []
        self.reject_index = reject_index
        self.reject_after_request_index = reject_after_request_index

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        next_index = len(self.prompts) + 1
        self.prompts.append((system, user, json_mode))
        if next_index == self.reject_index:
            raise RuntimeError("synthetic pre-provider rejection")
        self.requests += 1
        if next_index == self.reject_after_request_index:
            raise RuntimeError("synthetic provider deadline rejection before attempt")
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        value = self.outputs.pop(0)
        if isinstance(value, BaseException):
            raise value
        return SimpleNamespace(text=value)


class FakeSearch:
    def __init__(
        self,
        *,
        reserve_value: str = "2025",
        fail_stage: str | None = None,
        reserve_mentions_entity: bool = True,
        one_reserve_host: bool = False,
    ) -> None:
        self.reserve_value = reserve_value
        self.fail_stage = fail_stage
        self.reserve_mentions_entity = reserve_mentions_entity
        self.one_reserve_host = one_reserve_host
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.search_invocations = 0
        self.fetch_invocations = 0

    def search_many(self, queries, **kwargs):
        self.search_invocations += 1
        self.calls += 1
        self.tool_calls += 1
        self.input_tokens += 10
        self.output_tokens += 2
        self.total_tokens += 12
        if self.fail_stage == f"search_{self.search_invocations}":
            self.failures += 1
            raise RuntimeError("private synthetic search detail")
        prefix = "shared" if self.search_invocations == 1 else "unexpected"
        count = 10
        return [
            {
                "query": "content-free synthetic query",
                "answer": "",
                "results": [
                    {
                        "title": f"{prefix}-{index}",
                        "url": (
                            f"https://one.example/{index}"
                            if prefix == "shared" and index > 7 and self.one_reserve_host
                            else f"https://{prefix}{index}.example/item"
                        ),
                        "fetch_url": (
                            f"https://one.example/{index}"
                            if prefix == "shared" and index > 7 and self.one_reserve_host
                            else f"https://{prefix}{index}.example/item"
                        ),
                        "content": "",
                    }
                    for index in range(1, count + 1)
                ],
                "error": None,
            }
        ]

    def fetch_urls(self, requests):
        self.fetch_invocations += 1
        values = list(requests)
        self.fetch_calls += len(values)
        if self.fail_stage == f"fetch_{self.fetch_invocations}":
            self.fetch_failures += len(values)
            raise RuntimeError("private synthetic fetch detail")
        reserve = self.fetch_invocations == 2
        return [
            {
                "query": "content-free synthetic query",
                "results": [
                    {
                        "title": item["title"],
                        "url": item["url"],
                        "requested_url": item["url"],
                        "raw_content": (
                            (
                                f"Independent official record: Alpha year is {self.reserve_value}."
                                if self.reserve_mentions_entity
                                else f"Independent official record: a different entity year is {self.reserve_value}."
                            )
                            if reserve
                            else "Independent core record about Alpha without the requested year."
                        ),
                    }
                ],
            }
            for item in values
        ]


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=120,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
        plan_output_tokens=4_000,
        synthesis_output_tokens=30_000,
        repair_output_tokens=12_000,
    )


class V24325SharedPrefixRevisionRuntimeTests(unittest.TestCase):
    def run_case(
        self,
        baseline: str,
        proposed: str,
        ids: list[str],
        *,
        search: FakeSearch | None = None,
    ):
        model = FakeModel([PLAN, baseline, proposal(proposed, ids)])
        client = search or FakeSearch()
        result = run_v24325_task(
            TASK,
            model=model,
            search=client,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(result)
        return result, model, client

    def test_two_independent_hosts_fill_unknown_and_receive_entropy_credit(self) -> None:
        result, model, search = self.run_case(
            BASELINE_UNKNOWN, candidate("2025"), ["R0001", "R0002"]
        )
        receipt = result["shared_prefix_revision_receipt"]
        self.assertIn("| Alpha | 2025 |", result["candidate_prediction"])
        self.assertEqual(receipt["admitted_cell_changes"], 1)
        self.assertGreater(receipt["credited_conditional_entropy_reduction_nats"], 0)
        self.assertEqual(
            receipt["cell_admissions"][0]["admission_receipt"]["context_action"],
            "append_reserve_support",
        )
        self.assertEqual(model.requests, 3)
        self.assertEqual(search.search_invocations, 1)
        self.assertEqual(search.fetch_calls, 10)
        self.assertEqual(receipt["core_logical_queries"], 4)
        self.assertEqual(receipt["reserve_logical_queries"], 0)
        self.assertEqual(receipt["core_fetch_targets"], 7)
        self.assertEqual(receipt["reserve_fetch_targets"], 3)
        self.assertEqual(receipt["prefix_bundle"]["producer_execution_count"], 1)

    def test_three_independent_hosts_can_override_known_value(self) -> None:
        result, _, _ = self.run_case(
            BASELINE_KNOWN,
            candidate("2025"),
            ["R0001", "R0002", "R0003"],
        )
        admission = result["shared_prefix_revision_receipt"]["cell_admissions"][0]
        self.assertTrue(admission["admitted"])
        self.assertEqual(
            admission["admission_receipt"]["context_action"],
            "replace_core_after_corroborated_override",
        )
        self.assertIn("| Alpha | 2025 |", result["candidate_prediction"])

    def test_single_source_and_nonexistent_citations_are_quarantined(self) -> None:
        for ids in (["R0001"], ["R9998", "R9999"]):
            with self.subTest(ids=ids):
                result, _, _ = self.run_case(
                    BASELINE_UNKNOWN, candidate("2025"), list(ids)
                )
                receipt = result["shared_prefix_revision_receipt"]
                self.assertEqual(
                    result["candidate_prediction"], result["baseline_prediction"]
                )
                self.assertTrue(receipt["candidate_identity_handoff"])
                self.assertEqual(receipt["admitted_cell_changes"], 0)
                self.assertEqual(receipt["credited_conditional_entropy_reduction_nats"], 0)

    def test_value_without_local_entity_or_same_host_repetition_is_quarantined(self) -> None:
        for search in (
            FakeSearch(reserve_mentions_entity=False),
            FakeSearch(one_reserve_host=True),
        ):
            with self.subTest(search=search.__dict__):
                result, _, _ = self.run_case(
                    BASELINE_UNKNOWN,
                    candidate("2025"),
                    ["R0001", "R0002", "R0003"],
                    search=search,
                )
                receipt = result["shared_prefix_revision_receipt"]
                self.assertTrue(receipt["candidate_identity_handoff"])
                self.assertEqual(receipt["admitted_cell_changes"], 0)

    def test_candidate_cannot_delete_baseline_rows(self) -> None:
        baseline = """```markdown
| Name | Year |
| --- | --- |
| Alpha | Unknown |
| Beta | 2023 |
```"""
        result, _, _ = self.run_case(
            baseline, candidate("Unknown"), ["R0001", "R0002"]
        )
        self.assertEqual(result["candidate_prediction"], baseline)
        self.assertIn("| Beta | 2023 |", result["candidate_prediction"])

    def test_recoverable_reserve_failure_is_byte_identical_not_total_failure(self) -> None:
        model = FakeModel([PLAN, BASELINE_UNKNOWN])
        search = FakeSearch(fail_stage="fetch_2")
        result = run_v24325_task(
            TASK, model=model, search=search, limits=limits(), monotonic=Clock()
        )
        validate_result(result)
        receipt = result["shared_prefix_revision_receipt"]
        self.assertEqual(result["candidate_prediction"], result["baseline_prediction"])
        self.assertEqual(
            receipt["recoverable_failures"],
            [{"stage": "reserve_fetch", "type": "RuntimeError"}],
        )
        self.assertEqual(model.requests, 2)

    def test_total_boundary_preserves_nonzero_effect_lower_bounds(self) -> None:
        model = FakeModel([KeyboardInterrupt()])
        search = FakeSearch()
        result = run_v24325_total_task(
            TASK, model=model, search=search, limits=limits(), monotonic=Clock()
        )
        validate_result(result)
        receipt = result["shared_prefix_revision_receipt"]
        self.assertFalse(receipt["effect_accounting_complete"])
        self.assertEqual(receipt["unattributed_model_effects_lower_bound"], 1)
        self.assertEqual(receipt["unattributed_model_attempts_lower_bound"], 1)
        self.assertEqual(result["cost"]["model"]["requests"], 1)
        self.assertEqual(result["candidate_prediction"], result["baseline_prediction"])

    def test_pre_provider_revision_rejection_closes_logical_effect_equation(self) -> None:
        model = FakeModel([PLAN, BASELINE_UNKNOWN], reject_index=3)
        result = run_v24325_task(
            TASK,
            model=model,
            search=FakeSearch(),
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(result)
        receipt = result["shared_prefix_revision_receipt"]
        self.assertEqual(receipt["logical_model_admissions"], 3)
        self.assertEqual(receipt["provider_model_requests"], 2)
        self.assertEqual(receipt["pre_provider_model_rejections"], 1)
        self.assertEqual(result["candidate_prediction"], result["baseline_prediction"])

    def test_provider_wrapper_can_reject_before_first_attempt(self) -> None:
        model = FakeModel(
            [PLAN, BASELINE_UNKNOWN], reject_after_request_index=3
        )
        result = run_v24325_task(
            TASK,
            model=model,
            search=FakeSearch(),
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(result)
        receipt = result["shared_prefix_revision_receipt"]
        self.assertEqual(receipt["logical_model_admissions"], 3)
        self.assertEqual(receipt["provider_model_requests"], 3)
        self.assertEqual(receipt["provider_model_attempts"], 2)
        self.assertEqual(receipt["pre_provider_model_rejections"], 0)

    def test_plan_pre_provider_rejection_cannot_claim_frozen_prefix(self) -> None:
        model = FakeModel([BASELINE_UNKNOWN], reject_index=1)
        search = FakeSearch()
        result = run_v24325_task(
            TASK,
            model=model,
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(result)
        receipt = result["shared_prefix_revision_receipt"]
        self.assertEqual(receipt["prefix_status"], "unavailable")
        self.assertIsNone(receipt["prefix_bundle"])
        self.assertEqual(receipt["reserve_fetch_targets"], 0)
        self.assertTrue(receipt["candidate_identity_handoff"])
        self.assertEqual(receipt["logical_model_admissions"], 2)
        self.assertEqual(receipt["provider_model_requests"], 1)
        self.assertEqual(receipt["pre_provider_model_rejections"], 1)

    def test_baseline_failure_uses_third_call_for_core_recovery_not_reserve(self) -> None:
        model = FakeModel([PLAN, RuntimeError("private"), BASELINE_KNOWN])
        search = FakeSearch()
        result = run_v24325_task(
            TASK,
            model=model,
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(result)
        receipt = result["shared_prefix_revision_receipt"]
        self.assertIn("| Alpha | 2024 |", result["baseline_prediction"])
        self.assertEqual(result["candidate_prediction"], result["baseline_prediction"])
        self.assertEqual(
            receipt["model_effect_stages"],
            ["plan", "baseline_synthesis", "baseline_recovery"],
        )
        self.assertEqual(receipt["reserve_fetch_targets"], 0)
        self.assertEqual(search.fetch_calls, 7)

    def test_privileged_input_fails_before_any_effect(self) -> None:
        model = FakeModel([PLAN])
        search = FakeSearch()
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24325_total_task(
                {**TASK, "question_type": "forbidden"},
                model=model,
                search=search,
                limits=limits(),
                monotonic=Clock(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)

    def test_resealed_result_or_entropy_credit_tamper_fails_closed(self) -> None:
        result, _, _ = self.run_case(
            BASELINE_UNKNOWN, candidate("2025"), ["R0001", "R0002"]
        )
        altered = copy.deepcopy(result)
        altered["shared_prefix_revision_receipt"][
            "credited_conditional_entropy_reduction_nats"
        ] += 1
        receipt = altered["shared_prefix_revision_receipt"]
        unsigned_receipt = dict(receipt)
        unsigned_receipt.pop("receipt_sha256", None)
        receipt["receipt_sha256"] = payload_sha256(unsigned_receipt)
        unsigned_result = dict(altered)
        unsigned_result.pop("result_sha256", None)
        altered["result_sha256"] = payload_sha256(unsigned_result)
        with self.assertRaises(ValueError):
            validate_result(altered)


if __name__ == "__main__":
    unittest.main()
