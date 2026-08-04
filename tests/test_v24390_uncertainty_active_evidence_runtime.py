from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24390_uncertainty_active_evidence_runtime import (  # noqa: E402
    run_v24390_task,
    validate_result,
)
from test_v24342_semantic_active_runtime import Clock, limits  # noqa: E402
from test_v24367_target_segment_verifier_runtime import Model as CandidateModel  # noqa: E402


TASK = {
    "opaque_id": "task_1123456789abcdef01234567",
    "question": (
        "Use public web sources to return one Markdown table about Alpha and "
        "Beta. The column names are: Name, Founding year. Return one table only."
    ),
}
PLAN = json.dumps(
    {
        "language": "English",
        "columns": ["wrong"],
        "row_target_hint": "",
        "queries": ["one", "two", "three", "four"],
    }
)
BASELINE = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha | Unknown |
| Beta | Unknown |
```"""
KNOWN_BASELINE = """```markdown
| Name | Founding year |
| --- | --- |
| Alpha | 2025 |
| Beta | 2024 |
```"""
ACTIVE_MARKER = "UNCERTAINTY_ACTIVE_PRIVATE_24390"
SEED = "d" * 64


class IdentityModel:
    def __init__(self, *, baseline: str = BASELINE) -> None:
        self.baseline = baseline
        self.requests = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.prompts: list[tuple[str, str, bool]] = []

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del max_output_tokens
        self.prompts.append((system, user, json_mode))
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        if self.requests == 1:
            return SimpleNamespace(text=PLAN)
        if self.requests == 2:
            return SimpleNamespace(text=self.baseline)
        raise AssertionError("identity parent must not issue candidate revision")


class Search:
    def __init__(
        self, *, active_mode: str = "support", proposal_support: bool = False
    ) -> None:
        self.active_mode = active_mode
        self.proposal_support = proposal_support
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
        self.query_vectors: list[list[str]] = []

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.query_vectors.append(values)
        self.search_invocations += 1
        self.calls += 1
        self.tool_calls += 1
        if self.search_invocations <= 2:
            prefix = "wavea" if self.search_invocations == 1 else "waveb"
            results = [
                {
                    "title": f"proposal {values[(index - 1) % len(values)]}",
                    "url": f"https://{prefix}{index}.example/item/{index}",
                    "fetch_url": f"https://{prefix}{index}.example/item/{index}",
                }
                for index in range(1, 9)
            ]
        else:
            results = [
                {
                    "title": "Alpha official Founding year",
                    "url": "https://active-alpha.example/record",
                    "fetch_url": "https://active-alpha.example/record",
                },
                {
                    "title": "Beta official Founding year",
                    "url": "https://active-beta.example/record",
                    "fetch_url": "https://active-beta.example/record",
                },
                {
                    "title": "generic archive",
                    "url": "https://active-generic.example/record",
                    "fetch_url": "https://active-generic.example/record",
                },
            ]
        return [{"query": "private", "answer": "", "results": results}]

    def fetch_urls(self, requests):
        self.fetch_invocations += 1
        values = list(requests)
        self.fetch_calls += len(values)
        active = self.fetch_invocations == 3
        if not active:
            content = (
                "Alpha was founded in 2025. Beta was established in 2024."
                if self.proposal_support
                else "Alpha publishes software. Beta publishes software."
            )
        elif self.active_mode == "support":
            content = (
                "Alpha was founded in 2025. Beta was established in 2024. "
                + ACTIVE_MARKER
            )
        else:
            content = "Alpha and Beta publish documentation. " + ACTIVE_MARKER
        return_values = []
        for index, item in enumerate(values):
            if active and self.active_mode == "disagreement":
                content = (
                    f"Alpha was founded in {2025 + index}. "
                    f"Beta was established in {2024 + index}. {ACTIVE_MARKER}"
                )
            elif active and self.active_mode == "missing":
                content = "Alpha and Beta publish documentation. " + ACTIVE_MARKER
            return_values.append(
                {
                    "query": "synthetic",
                    "results": [
                        {
                            "title": item["title"],
                            "url": item["url"],
                            "requested_url": item["url"],
                            "raw_content": content,
                        }
                    ],
                }
            )
        return return_values


class V24390UncertaintyActiveEvidenceRuntimeTests(unittest.TestCase):
    def run_case(self, *, active_mode: str = "support", baseline: str = BASELINE):
        model = IdentityModel(baseline=baseline)
        search = Search(active_mode=active_mode)
        result = run_v24390_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(result)
        return result, model, search

    def test_identity_parent_activates_one_target_with_two_sources(self) -> None:
        result, model, search = self.run_case()
        receipt = result["uncertainty_active_receipt"]
        self.assertEqual(model.requests, 2)
        self.assertEqual(receipt["selected_uncertainty_target_count"], 1)
        self.assertEqual(receipt["active_logical_query_count"], 1)
        self.assertEqual(receipt["active_search_batch_count"], 1)
        self.assertEqual(receipt["total_search_batch_count"], 3)
        self.assertEqual(receipt["total_logical_query_count"], 5)
        self.assertEqual(receipt["active_selected_source_count"], 2)
        self.assertEqual(receipt["total_fetch_calls"], 10)
        self.assertEqual(search.calls, 3)
        self.assertFalse(
            receipt["active_target_selection_requires_preexisting_candidate_change"]
        )
        self.assertFalse(receipt["parent_candidate_used_as_activation_prerequisite"])

    def test_active_queries_omit_frozen_values_and_pages_omit_model_prompt(self) -> None:
        result, model, search = self.run_case()
        catalog = result["private_replay_state"]["uncertainty_catalog"]
        queries = catalog["active_queries"]
        self.assertEqual(search.query_vectors[-1], queries)
        self.assertEqual(len(queries), 1)
        self.assertTrue(any(name in queries[0] for name in ("Alpha", "Beta")))
        self.assertTrue(all("Unknown" not in query for query in queries))
        prompt = "\n".join(user for _, user, _ in model.prompts)
        self.assertNotIn(ACTIVE_MARKER, prompt)
        self.assertTrue(
            result["uncertainty_active_receipt"]
            ["active_queries_use_only_frozen_row_and_column"]
        )

    def test_two_active_sources_fill_unknown_cell_and_receive_both_credits(self) -> None:
        result, _, _ = self.run_case()
        receipt = result["uncertainty_active_receipt"]
        self.assertEqual(receipt["safe_change_count"], 1)
        self.assertEqual(receipt["candidate_changed_cell_count"], 1)
        self.assertNotEqual(result["candidate_prediction"], BASELINE)
        self.assertGreater(receipt["epistemic_credit_total_nats"], 0)
        self.assertGreater(receipt["decision_credit_total_nats"], 0)

    def test_missing_active_relations_preserve_identity_with_zero_credit(self) -> None:
        result, _, _ = self.run_case(active_mode="missing")
        receipt = result["uncertainty_active_receipt"]
        self.assertEqual(result["candidate_prediction"], BASELINE)
        self.assertEqual(receipt["safe_change_count"], 0)
        self.assertEqual(receipt["epistemic_credit_total_nats"], 0)
        self.assertEqual(receipt["decision_credit_total_nats"], 0)

    def test_known_baseline_confirmation_gets_epistemic_only_credit(self) -> None:
        result, _, _ = self.run_case(baseline=KNOWN_BASELINE)
        receipt = result["uncertainty_active_receipt"]
        self.assertEqual(result["candidate_prediction"], KNOWN_BASELINE)
        self.assertEqual(receipt["safe_change_count"], 0)
        self.assertEqual(receipt["baseline_confirmed_count"], 1)
        self.assertGreater(receipt["epistemic_credit_total_nats"], 0)
        self.assertEqual(receipt["decision_credit_total_nats"], 0)

    def test_disagreeing_active_sources_do_not_change_output(self) -> None:
        result, _, _ = self.run_case(active_mode="disagreement")
        receipt = result["uncertainty_active_receipt"]
        self.assertEqual(result["candidate_prediction"], BASELINE)
        self.assertEqual(receipt["safe_change_count"], 0)
        self.assertEqual(receipt["decision_credit_total_nats"], 0)

    def test_untouched_safe_parent_candidate_changes_are_preserved(self) -> None:
        model = CandidateModel()
        search = Search(active_mode="missing", proposal_support=True)
        result = run_v24390_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(result)
        receipt = result["uncertainty_active_receipt"]
        self.assertEqual(receipt["parent_candidate_changed_cell_count"], 2)
        self.assertEqual(receipt["active_reverted_parent_candidate_count"], 0)
        self.assertEqual(receipt["candidate_changed_cell_count"], 2)
        self.assertIn("| Alpha | 2025 |", result["candidate_prediction"])
        self.assertIn("| Beta | 2024 |", result["candidate_prediction"])

    def test_private_replay_and_credit_tamper_fail_closed(self) -> None:
        result, _, _ = self.run_case()
        for field in ("query", "page", "observation", "credit", "prediction"):
            with self.subTest(field=field):
                altered = copy.deepcopy(result)
                private = altered["private_replay_state"]
                if field == "query":
                    private["uncertainty_catalog"]["active_queries"][0] += " tamper"
                elif field == "page":
                    private["active_fetch_batches"][0]["results"][0][
                        "raw_content"
                    ] += " tamper"
                elif field == "observation":
                    private["active_observations"][0]["value"] = "2030"
                elif field == "credit":
                    private["active_evidence_result"]["receipt"][
                        "epistemic_credit_total_nats"
                    ] += 0.1
                else:
                    altered["candidate_prediction"] = BASELINE
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_privileged_input_is_rejected_before_any_effect(self) -> None:
        model = IdentityModel()
        search = Search()
        with self.assertRaises(ValueError):
            run_v24390_task(
                {**TASK, "question_type": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=Clock(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)


if __name__ == "__main__":
    unittest.main()
