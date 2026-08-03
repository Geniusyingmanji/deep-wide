from __future__ import annotations

import copy
import json
import unittest

from deepwide_agent.v24282_direct_search_page_projection import (
    DirectSearchPageProjectionClient,
    validate_receipt,
)


class FakeSearch:
    batch_size = 1
    max_workers = 2

    def __init__(self) -> None:
        self.calls = 0
        self.failures = 0

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.calls += len(values)
        return [
            {
                "query": query,
                "answer": "PRIVATE PROVIDER ANSWER",
                "results": [
                    {
                        "title": "A",
                        "url": "https://a.example/page?utm_source=x",
                        "content": "PRIVATE SNIPPET",
                        "raw_content": "PRIVATE PROVIDER RAW CONTENT",
                        "score": 0.99,
                    },
                    {
                        "title": "A duplicate",
                        "url": "https://a.example/page",
                        "content": "duplicate",
                    },
                    {"title": "invalid", "url": "file:///private"},
                ],
            }
            for query in values
        ]


class FakeFetcher:
    fetch_workers = 8
    fetch_timeout = 20

    def __init__(self) -> None:
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.hard_fetch_helper_calls = 0
        self.hard_fetch_deadline_failures = 0
        self.fetch_helper_failures = 0

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_calls += len(values)
        self.hard_fetch_helper_calls += len(values)
        return [
            {
                "query": item["query"],
                "results": [
                    {
                        "title": item["title"],
                        "url": item["url"],
                        "raw_content": "DETERMINISTIC FETCHED PAGE",
                    }
                ],
            }
            for item in values
        ]


class V24282DirectSearchPageProjectionTests(unittest.TestCase):
    def test_only_url_leads_survive_until_deterministic_fetch(self) -> None:
        client = DirectSearchPageProjectionClient(FakeSearch(), FakeFetcher())
        batches = client.search_many(
            ["one", "two"],
            max_results=3,
            search_depth="advanced",
            include_raw_content=False,
        )
        self.assertEqual(len(batches), 2)
        self.assertTrue(all(len(batch["results"]) == 1 for batch in batches))
        encoded = json.dumps(batches)
        self.assertNotIn("PRIVATE PROVIDER ANSWER", encoded)
        self.assertNotIn("PRIVATE SNIPPET", encoded)
        self.assertNotIn("PRIVATE PROVIDER RAW CONTENT", encoded)
        self.assertNotIn("0.99", encoded)
        self.assertTrue(
            all(result["content"] == "" for batch in batches for result in batch["results"])
        )

        requests_ = [
            {
                "query": batch["query"],
                "url": batch["results"][0]["fetch_url"],
                "title": batch["results"][0]["title"],
                "member_label": "",
            }
            for batch in batches
        ]
        pages = client.fetch_urls(requests_)
        self.assertEqual(len(pages), 2)
        self.assertTrue(
            all(
                page["results"][0]["raw_content"] == "DETERMINISTIC FETCHED PAGE"
                for page in pages
            )
        )
        receipt = client.receipt()
        validate_receipt(receipt)
        self.assertEqual(receipt["raw_result_count"], 6)
        self.assertEqual(receipt["projected_lead_count"], 2)
        self.assertEqual(receipt["invalid_or_duplicate_lead_count"], 4)
        self.assertEqual(receipt["fetch_usable_page_count"], 2)
        self.assertNotIn("example", json.dumps(receipt))

    def test_provider_failure_remains_visible_when_no_lead_exists(self) -> None:
        search = FakeSearch()
        search.search_many = lambda queries, **kwargs: [  # type: ignore[method-assign]
            {"query": "private", "answer": "", "results": [], "error": "safe failure"}
        ]
        client = DirectSearchPageProjectionClient(search, FakeFetcher())
        batches = client.search_many(["one"], max_results=3)
        self.assertEqual(batches[0]["error"], "safe failure")
        self.assertEqual(client.receipt()["provider_error_batch_count"], 1)

    def test_receipt_tamper_fails_closed(self) -> None:
        client = DirectSearchPageProjectionClient(FakeSearch(), FakeFetcher())
        client.search_many(["one"], max_results=3)
        receipt = copy.deepcopy(client.receipt())
        receipt["credential_environment_file_keyring_value_or_hash_read_or_emitted"] = True
        with self.assertRaisesRegex(ValueError, "drifted"):
            validate_receipt(receipt)


if __name__ == "__main__":
    unittest.main()
