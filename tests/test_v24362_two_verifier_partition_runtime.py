from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24362_two_verifier_partition_runtime import (  # noqa: E402
    _partition_leads,
    run_v24362_task,
    validate_result,
)
from test_v24342_semantic_active_runtime import (  # noqa: E402
    BASELINE_UNKNOWN,
    Clock,
    Model,
    TASK,
    limits,
)


SEED = "c" * 64
HIDDEN_MARKER = "HIDDEN_TWO_VERIFIER_24362"


class Search:
    def __init__(
        self,
        *,
        first_hidden_missing: bool = False,
        second_hidden_conflict: bool = False,
        both_hidden_missing: bool = False,
    ) -> None:
        self.first_hidden_missing = first_hidden_missing
        self.second_hidden_conflict = second_hidden_conflict
        self.both_hidden_missing = both_hidden_missing
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
        self.fetch_search_call_counts: list[int] = []

    def search_many(self, queries, **kwargs):
        del queries, kwargs
        self.search_invocations += 1
        self.calls += 1
        self.tool_calls += 1
        indices = range(1, 7) if self.search_invocations == 1 else range(4, 13)
        return [
            {
                "query": "synthetic",
                "results": [
                    {
                        "title": f"record-{index}",
                        "url": f"https://host{index}.example/item/{self.search_invocations}",
                        "fetch_url": f"https://host{index}.example/item/{self.search_invocations}",
                    }
                    for index in indices
                ],
            }
        ]

    def fetch_urls(self, requests):
        self.fetch_invocations += 1
        values = list(requests)
        self.fetch_search_call_counts.append(self.calls)
        self.fetch_calls += len(values)
        hidden = self.fetch_invocations == 3
        output = []
        for index, item in enumerate(values):
            if hidden and (
                self.both_hidden_missing
                or (self.first_hidden_missing and index == 0)
            ):
                content = ""
                self.fetch_failures += 1
            elif hidden and self.second_hidden_conflict and index == 1:
                content = f"Alpha was founded in 2024. {HIDDEN_MARKER} conflict."
            elif hidden:
                content = f"Alpha was founded in 2025. {HIDDEN_MARKER} support."
            else:
                content = "Alpha was founded in 2025 according to this public record."
            output.append(
                {
                    "query": "synthetic",
                    "results": [
                        {
                            "title": item["title"],
                            "url": item["url"],
                            "requested_url": item["url"],
                            "raw_content": content,
                        }
                    ]
                    if content
                    else [],
                }
            )
        return output


class V24362TwoVerifierPartitionRuntimeTests(unittest.TestCase):
    def run_case(self, *, search: Search | None = None):
        model = Model(baseline=BASELINE_UNKNOWN)
        search = search or Search()
        value = run_v24362_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        return value, model, search

    def test_full_capacity_is_eight_plus_two_and_retains_supported_change(self) -> None:
        value, model, search = self.run_case()
        receipt = value["hidden_verifier_receipt"]
        partition = receipt["partition_receipt"]
        discovery = value["two_batch_discovery_receipt"]
        self.assertEqual(partition["proposal_source_count"], 8)
        self.assertEqual(partition["verifier_source_count"], 2)
        self.assertEqual(partition["verifier_source_cap"], 2)
        self.assertEqual(discovery["discovery_batch_count"], 2)
        self.assertEqual(discovery["registrable_host_union_count"], 12)
        self.assertEqual(receipt["parent_fetch_calls"], 8)
        self.assertEqual(receipt["hidden_verifier_fetch_calls"], 2)
        self.assertEqual(receipt["total_fetch_calls"], 10)
        self.assertEqual(search.calls, 2)
        self.assertEqual(search.fetch_calls, 10)
        self.assertEqual(model.requests, 3)
        self.assertIn("| Alpha | 2025 |", value["candidate_prediction"])
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 1)
        self.assertGreater(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_low_coverage_partition_preserves_two_proposal_hosts(self) -> None:
        leads = [
            {
                "url": f"https://small{index}.example/item",
                "title": f"small-{index}",
                "query": "visible",
            }
            for index in range(1, 5)
        ]
        expected = {1: (1, 0), 2: (2, 0), 3: (2, 1), 4: (2, 2)}
        for count, (proposal_count, verifier_count) in expected.items():
            with self.subTest(count=count):
                proposal, verifier, receipt = _partition_leads(
                    leads[:count], partition_seed_sha256=SEED
                )
                self.assertEqual(len(proposal), proposal_count)
                self.assertEqual(len(verifier), verifier_count)
                self.assertEqual(receipt["selected_source_count"], count)

    def test_one_missing_verifier_can_be_rescued_by_second_support(self) -> None:
        value, _, _ = self.run_case(search=Search(first_hidden_missing=True))
        receipt = value["hidden_verifier_receipt"]
        self.assertEqual(receipt["hidden_verifier_page_count"], 1)
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 1)
        self.assertGreater(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_any_independent_conflict_still_reverts(self) -> None:
        value, _, _ = self.run_case(search=Search(second_hidden_conflict=True))
        receipt = value["hidden_verifier_receipt"]
        self.assertEqual(value["candidate_prediction"], value["baseline_prediction"])
        self.assertEqual(receipt["hidden_verifier_reverted_cells"], 1)
        self.assertEqual(receipt["utility_aligned_entropy_credit_nats"], 0)

    def test_no_hidden_support_fails_closed(self) -> None:
        value, _, _ = self.run_case(search=Search(both_hidden_missing=True))
        receipt = value["hidden_verifier_receipt"]
        self.assertEqual(value["candidate_prediction"], value["baseline_prediction"])
        self.assertEqual(receipt["hidden_verifier_page_count"], 0)
        self.assertEqual(receipt["candidate_changed_cells_after_hidden_verifier"], 0)

    def test_both_hidden_pages_are_excluded_from_parent_prompts(self) -> None:
        value, model, _ = self.run_case()
        hidden = value["private_replay_state"]["verifier_pages"]
        prompt_text = "\n".join(user for _, user, _ in model.prompts)
        self.assertEqual(len(hidden), 2)
        for page in hidden:
            self.assertIn(HIDDEN_MARKER, page["content"])
            self.assertNotIn(page["content"], prompt_text)
        self.assertNotIn(HIDDEN_MARKER, prompt_text)

    def test_discovery_partition_and_hidden_tamper_fail_replay(self) -> None:
        value, _, _ = self.run_case()
        for field in ("query", "lead", "partition", "hidden"):
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                private = altered["private_replay_state"]
                if field == "query":
                    private["two_batch_discovery_state"]["query_batches"][0][0] += " tamper"
                elif field == "lead":
                    private["partition"]["verifier_leads"][0]["url"] = (
                        "https://tampered.example/item"
                    )
                elif field == "partition":
                    altered["hidden_verifier_receipt"]["partition_receipt"][
                        "verifier_source_count"
                    ] = 1
                else:
                    private["verifier_fetch_batches"][0]["results"][0][
                        "raw_content"
                    ] += " tamper"
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_privileged_input_is_rejected_before_any_effect(self) -> None:
        model = Model(baseline=BASELINE_UNKNOWN)
        search = Search()
        with self.assertRaises(ValueError):
            run_v24362_task(
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
