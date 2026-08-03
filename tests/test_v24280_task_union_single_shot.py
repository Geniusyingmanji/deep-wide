from __future__ import annotations

import copy
import unittest

from deepwide_agent.clients import SearchRequestError
from deepwide_agent.v24269_task_union_discovery import (
    TaskUnionDiscoverySearchClient,
)
from deepwide_agent.v24280_task_union_single_shot import (
    TaskUnionSingleShotNativeSearchClient,
    validate_receipt,
)


def payload(*, marker_count: int = 1) -> dict:
    sources = [
        {"type": "web_source", "url": "https://a.example/page", "title": "A"},
        {"type": "web_source", "url": "https://b.example/page", "title": "B"},
    ]
    text = "".join(
        f"[[QUERY Q{index:04d}]]\nsummary\n[[END Q{index:04d}]]\n"
        for index in range(1, marker_count + 1)
    )
    return {
        "id": "response",
        "output": [
            {
                "type": "web_search_call",
                "id": "call",
                "status": "completed",
                "action": {
                    "type": "search",
                    "queries": ["one", "two"],
                    "sources": sources,
                },
            },
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": text, "annotations": []}
                ],
            },
        ],
    }


class FakeSingleShot(TaskUnionSingleShotNativeSearchClient):
    def __init__(self, response: dict | None = None, failure: str | None = None) -> None:
        super().__init__(
            "http://unused/responses",
            "model",
            fetch_pages=False,
            max_workers=1,
            batch_size=8,
        )
        self.response = copy.deepcopy(response)
        self.failure = failure
        self.requests: list[list[str]] = []

    def _request(self, queries):  # type: ignore[override]
        self.requests.append(list(queries))
        if self.failure is not None:
            raise SearchRequestError(self.failure)
        return copy.deepcopy(self.response)


class V24280TaskUnionSingleShotTests(unittest.TestCase):
    def test_incomplete_mapping_uses_one_request_and_recovers_action_union(self) -> None:
        inner = FakeSingleShot(payload(marker_count=1))
        client = TaskUnionDiscoverySearchClient(inner)
        batches = client.search_many(["one", "two"], max_results=3)

        self.assertEqual(inner.requests, [["one", "two"]])
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(batches[0]["results"]), 2)
        self.assertEqual(client.failures, 0)
        discovery = client.receipt()
        self.assertEqual(discovery["raw_action_source_count"], 2)
        self.assertEqual(discovery["raw_query_local_mapping_failure_count"], 2)
        self.assertEqual(discovery["union_source_count"], 2)
        receipt = inner.single_shot_receipt()
        validate_receipt(receipt)
        self.assertEqual(receipt["multi_query_chunks"], 1)
        self.assertEqual(receipt["incomplete_mapping_chunks"], 1)
        self.assertEqual(receipt["mapping_failure_rows_normalized"], 1)
        self.assertEqual(receipt["action_trace_attachments"], 1)
        self.assertEqual(receipt["recursive_split_requests"], 0)

    def test_complete_mapping_still_attaches_action_trace_once(self) -> None:
        inner = FakeSingleShot(payload(marker_count=2))
        rows = inner.search_many(["one", "two"], max_results=3)
        self.assertEqual(sum("hosted_search_trace" in row for row in rows), 1)
        self.assertEqual(inner.requests, [["one", "two"]])
        receipt = inner.single_shot_receipt()
        self.assertEqual(receipt["incomplete_mapping_chunks"], 0)
        self.assertEqual(receipt["action_trace_attachments"], 1)

    def test_transport_failure_is_not_reclassified_or_split(self) -> None:
        inner = FakeSingleShot(failure="transport failed")
        client = TaskUnionDiscoverySearchClient(inner)
        self.assertEqual(client.search_many(["one", "two"], max_results=3), [])
        self.assertEqual(inner.requests, [["one", "two"]])
        self.assertEqual(client.failures, 2)
        self.assertEqual(
            client.receipt()["raw_unrecoverable_failure_count"], 2
        )
        self.assertEqual(inner.single_shot_receipt()["recursive_split_requests"], 0)

    def test_receipt_tamper_fails_closed(self) -> None:
        inner = FakeSingleShot(payload(marker_count=1))
        inner.search_many(["one", "two"], max_results=3)
        receipt = inner.single_shot_receipt()
        receipt["recursive_split_requests"] = 1
        with self.assertRaisesRegex(ValueError, "accounting"):
            validate_receipt(receipt)


if __name__ == "__main__":
    unittest.main()
