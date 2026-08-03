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
from deepwide_agent.v24359_two_batch_partition_runtime import (  # noqa: E402
    run_v24359_task,
    validate_result,
)
from test_v24342_semantic_active_runtime import (  # noqa: E402
    BASELINE_UNKNOWN,
    Clock,
    Model,
    TASK,
    limits,
)


SEED = "b" * 64
HIDDEN_MARKER = "HIDDEN_VERIFIER_ONLY_24359"


class Search:
    def __init__(self) -> None:
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
        content = (
            f"Alpha was founded in 2025. {HIDDEN_MARKER}"
            if hidden
            else "Alpha was founded in 2025 according to this public record."
        )
        return [
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
            for item in values
        ]


class V24359TwoBatchPartitionRuntimeTests(unittest.TestCase):
    def run_case(self):
        model = Model(baseline=BASELINE_UNKNOWN)
        search = Search()
        value = run_v24359_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_result(value)
        return value, model, search

    def test_two_search_effects_and_at_most_ten_fetch_effects(self) -> None:
        value, model, search = self.run_case()
        receipt = value["two_batch_discovery_receipt"]
        runtime = value["explicit_partition_result"]["hidden_verifier_receipt"]
        self.assertEqual(receipt["provider_search_call_count"], 2)
        self.assertEqual(receipt["registrable_host_union_count"], 12)
        self.assertEqual(receipt["selected_host_count"], 10)
        self.assertEqual(runtime["parent_fetch_calls"], 9)
        self.assertEqual(runtime["hidden_verifier_fetch_calls"], 1)
        self.assertEqual(runtime["total_fetch_calls"], 10)
        self.assertEqual(search.fetch_calls, 10)
        self.assertTrue(all(count == 2 for count in search.fetch_search_call_counts))
        self.assertEqual(model.requests, 3)

    def test_hidden_page_is_excluded_from_every_parent_prompt(self) -> None:
        value, model, _ = self.run_case()
        parent = value["explicit_partition_result"]
        prompt_text = "\n".join(user for _, user, _ in model.prompts)
        hidden_pages = parent["private_replay_state"]["verifier_pages"]
        self.assertTrue(hidden_pages)
        self.assertIn(HIDDEN_MARKER, hidden_pages[0]["content"])
        self.assertNotIn(HIDDEN_MARKER, prompt_text)

    def test_private_discovery_and_parent_tamper_fail_replay(self) -> None:
        value, _, _ = self.run_case()
        for field in ("query", "lead", "partition"):
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                if field == "query":
                    altered["two_batch_discovery_private_state"]["query_batches"][0][0] += " tamper"
                elif field == "lead":
                    altered["two_batch_discovery_private_state"][
                        "registrable_host_union_leads"
                    ][0]["url"] = "https://tampered.example/item"
                else:
                    altered["two_batch_discovery_receipt"][
                        "partition_receipt_sha256"
                    ] = "f" * 64
                altered.pop("result_sha256")
                altered["result_sha256"] = payload_sha256(altered)
                with self.assertRaises(ValueError):
                    validate_result(altered)

    def test_privileged_input_is_rejected_before_any_effect(self) -> None:
        model = Model(baseline=BASELINE_UNKNOWN)
        search = Search()
        with self.assertRaises(ValueError):
            run_v24359_task(
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
