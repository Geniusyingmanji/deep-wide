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
from deepwide_agent.v24355_explicit_partition_runtime import _partition_leads  # noqa: E402
from deepwide_agent.v24358_two_batch_discovery import (  # noqa: E402
    TwoBatchRegistrableHostUnionSearchClient,
    build_discovery_receipt,
    validate_discovery_receipt,
)


SEED = "b" * 64


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
        self.queries: list[list[str]] = []
        self.fetch_search_call_counts: list[int] = []

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.queries.append(values)
        self.calls += 1
        self.tool_calls += 1
        indices = range(1, 7) if len(self.queries) == 1 else range(4, 13)
        return [
            {
                "query": "private provider query",
                "answer": "private provider narrative",
                "results": [
                    {
                        "title": f"record-{index}",
                        "url": f"https://sub{index}.source{index}.example/item/{len(self.queries)}",
                        "fetch_url": f"https://sub{index}.source{index}.example/item/{len(self.queries)}",
                    }
                    for index in indices
                ],
            }
        ]

    def fetch_urls(self, requests):
        values = list(requests)
        self.fetch_search_call_counts.append(self.calls)
        self.fetch_calls += len(values)
        return []


class V24358TwoBatchDiscoveryTests(unittest.TestCase):
    def run_case(self):
        search = Search()
        client = TwoBatchRegistrableHostUnionSearchClient(search)
        batches = client.search_many(
            ["one", "two", "three", "four"], max_results=3
        )
        state = client.private_replay_state()
        leads = batches[0]["results"]
        proposal, verifier, partition = _partition_leads(
            leads[:10], partition_seed_sha256=SEED
        )
        self.assertEqual(len(proposal), 9)
        self.assertEqual(len(verifier), 1)
        receipt = build_discovery_receipt(state, partition)
        validate_discovery_receipt(
            receipt, private_state=state, partition_receipt=partition
        )
        return search, client, batches, state, partition, receipt

    def test_two_batches_union_duplicate_hosts_before_partition(self) -> None:
        search, _, batches, _, partition, receipt = self.run_case()
        self.assertEqual(search.queries, [["one", "two"], ["three", "four"]])
        self.assertEqual(receipt["discovery_batch_count"], 2)
        self.assertEqual(receipt["provider_search_call_count"], 2)
        self.assertEqual(receipt["batch_provider_search_call_counts"], [1, 1])
        self.assertEqual(receipt["pre_host_dedup_url_lead_count"], 15)
        self.assertEqual(receipt["registrable_host_union_count"], 12)
        self.assertEqual(receipt["registrable_host_duplicate_url_count"], 3)
        self.assertEqual(receipt["selected_host_count"], 10)
        self.assertEqual(len(batches[0]["results"]), 12)
        self.assertEqual(partition["proposal_source_count"], 9)
        self.assertEqual(partition["verifier_source_count"], 1)

    def test_partition_is_deterministic_and_fetch_cannot_precede_union(self) -> None:
        search = Search()
        fresh = TwoBatchRegistrableHostUnionSearchClient(search)
        with self.assertRaises(RuntimeError):
            fresh.fetch_urls([])
        first = self.run_case()
        second = self.run_case()
        self.assertEqual(first[4], second[4])
        self.assertEqual(first[5], second[5])
        self.assertEqual(first[5]["fetch_effects_before_partition"], 0)

    def test_replay_tamper_fails_closed(self) -> None:
        _, _, _, state, partition, receipt = self.run_case()
        altered_state = copy.deepcopy(state)
        altered_state["query_batches"][0].reverse()
        with self.assertRaises(ValueError):
            validate_discovery_receipt(
                receipt,
                private_state=altered_state,
                partition_receipt=partition,
            )
        altered_receipt = copy.deepcopy(receipt)
        altered_receipt["registrable_host_union_count"] += 1
        altered_receipt.pop("receipt_sha256")
        altered_receipt["receipt_sha256"] = payload_sha256(altered_receipt)
        with self.assertRaises(ValueError):
            validate_discovery_receipt(altered_receipt)

    def test_repeated_search_is_rejected(self) -> None:
        search = Search()
        client = TwoBatchRegistrableHostUnionSearchClient(search)
        client.search_many(["one", "two", "three", "four"], max_results=3)
        with self.assertRaises(RuntimeError):
            client.search_many(["one", "two", "three", "four"], max_results=3)
        self.assertEqual(search.calls, 2)


if __name__ == "__main__":
    unittest.main()
