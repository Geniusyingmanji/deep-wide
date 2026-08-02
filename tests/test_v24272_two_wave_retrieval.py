from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24272_two_wave_entropy_voc import (  # noqa: E402
    TwoWavePolicy,
    object_sha256,
)
from deepwide_agent.v24272_two_wave_retrieval import (  # noqa: E402
    run_two_wave_retrieval,
    validate_retrieval_receipt,
)


class Clock:
    def __init__(self, increment=0.25):
        self.value = 0.0
        self.increment = increment

    def __call__(self):
        self.value += self.increment
        return self.value


class FakeSearch:
    batch_size = 8
    max_workers = 1
    fetch_workers = 8
    fetch_timeout = 20
    fetch_pages = False

    def __init__(self, *, sparse=False, duplicate_second=False, failed_fetch=False):
        self.sparse = sparse
        self.duplicate_second = duplicate_second
        self.failed_fetch = failed_fetch
        self.search_invocations = 0
        self.search_query_batches = []
        self.fetch_invocations = []
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.search_invocations += 1
        self.search_query_batches.append(values)
        self.calls += 1
        self.tool_calls += 1
        batches = []
        for query_index, query in enumerate(values):
            results = []
            count = 1 if self.sparse and self.search_invocations == 1 else 3
            for source_index in range(count):
                if self.duplicate_second and self.search_invocations == 2 and source_index == 0:
                    url = "https://source-0-0.example/page"
                else:
                    url = f"https://source-{self.search_invocations - 1}-{query_index * 3 + source_index}.example/page"
                results.append({"url": url, "title": "source", "content": "snippet"})
            batches.append({"query": query, "answer": "PRIVATE", "results": results})
        return batches

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_invocations.append(values)
        self.fetch_calls += len(values)
        batches = []
        for index, item in enumerate(values):
            if self.failed_fetch:
                self.fetch_failures += 1
                self.failures += 1
                batches.append({"query": item["query"], "results": [], "error": "transport_error"})
                continue
            content = (
                "same duplicate page"
                if self.duplicate_second and len(self.fetch_invocations) == 2 and index == 0
                else f"usable evidence {len(self.fetch_invocations)} {index} " + "x" * 2_000
            )
            batches.append(
                {
                    "query": item["query"],
                    "results": [{"url": item["url"], "title": "page", "raw_content": content}],
                }
            )
        return batches


QUERIES = ["visible one", "visible two", "visible three", "visible four"]


class V24272TwoWaveRetrievalTests(unittest.TestCase):
    def test_sufficient_first_wave_executes_only_two_queries_and_six_fetches(self):
        search = FakeSearch()
        value = run_two_wave_retrieval(
            QUERIES,
            search=search,
            required_column_count=3,
            monotonic=Clock(),
        )
        receipt = value["receipt"]
        validate_retrieval_receipt(receipt)
        self.assertEqual(receipt["controller"]["decision"], "stop")
        self.assertEqual(receipt["total"]["queries_executed"], 2)
        self.assertEqual(receipt["total"]["fetches_attempted"], 6)
        self.assertEqual(search.search_invocations, 1)
        self.assertEqual(len(search.fetch_invocations), 1)
        encoded = json.dumps(receipt)
        for forbidden in ("visible one", "source-0", "usable evidence", "PRIVATE"):
            self.assertNotIn(forbidden, encoded)

    def test_sparse_first_wave_expands_delta_only_without_refetching_urls(self):
        search = FakeSearch(sparse=True, duplicate_second=True)
        value = run_two_wave_retrieval(
            QUERIES,
            search=search,
            required_column_count=6,
            monotonic=Clock(),
        )
        receipt = value["receipt"]
        self.assertEqual(receipt["controller"]["decision"], "expand")
        self.assertTrue(receipt["wave2"]["executed"])
        self.assertEqual(receipt["total"]["queries_executed"], 4)
        first_urls = {item["url"] for item in search.fetch_invocations[0]}
        second_urls = {item["url"] for item in search.fetch_invocations[1]}
        self.assertTrue(first_urls.isdisjoint(second_urls))
        self.assertLessEqual(receipt["total"]["fetches_attempted"], 10)
        self.assertEqual(receipt["budget_equivalence"]["logical_query_count"], 4)

    def test_failed_slow_first_wave_stops_at_latency_ceiling(self):
        search = FakeSearch(failed_fetch=True)
        value = run_two_wave_retrieval(
            QUERIES,
            search=search,
            required_column_count=5,
            monotonic=Clock(increment=16.0),
        )
        receipt = value["receipt"]
        self.assertEqual(receipt["controller"]["reason"], "latency_ceiling")
        self.assertFalse(receipt["wave2"]["executed"])
        self.assertEqual(search.search_invocations, 1)

    def test_one_planned_query_has_no_second_wave_and_stays_within_capacity(self):
        search = FakeSearch()
        value = run_two_wave_retrieval(
            ["only visible query"],
            search=search,
            required_column_count=2,
            monotonic=Clock(),
        )
        receipt = value["receipt"]
        self.assertEqual(receipt["controller"]["reason"], "no_delta_budget")
        self.assertEqual(receipt["total"]["queries_executed"], 1)
        self.assertLessEqual(receipt["total"]["fetches_attempted"], 3)

    def test_receipt_rejects_resealed_nested_and_accounting_tamper(self):
        value = run_two_wave_retrieval(
            QUERIES,
            search=FakeSearch(),
            required_column_count=3,
            monotonic=Clock(),
        )["receipt"]
        for mutation in ("nested", "accounting", "metadata"):
            altered = copy.deepcopy(value)
            if mutation == "nested":
                altered["controller"]["reason"] = "positive_entropy_voc"
            elif mutation == "accounting":
                altered["total"]["fetches_attempted"] += 1
            else:
                altered["question_type"] = "forbidden"
            unsigned = dict(altered)
            unsigned.pop("receipt_sha256", None)
            altered["receipt_sha256"] = object_sha256(unsigned)
            with self.assertRaises(ValueError):
                validate_retrieval_receipt(altered)

    def test_invalid_visible_plan_shape_is_rejected_before_search(self):
        search = FakeSearch()
        with self.assertRaises(ValueError):
            run_two_wave_retrieval(
                [], search=search, required_column_count=3, monotonic=Clock()
            )
        with self.assertRaises(ValueError):
            run_two_wave_retrieval(
                QUERIES,
                search=search,
                required_column_count=0,
                monotonic=Clock(),
            )
        self.assertEqual(search.search_invocations, 0)


if __name__ == "__main__":
    unittest.main()
