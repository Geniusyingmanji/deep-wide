from __future__ import annotations

import concurrent.futures
import copy
import sys
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24799_fixed_full_budget_control import fixed_full_budget_policy  # noqa: E402
from deepwide_agent.v24852_rate_aware_tavily_search import empty_rate_aware_receipt  # noqa: E402
from deepwide_agent.v24856_pacing_aware_admission import run_pacing_aware_two_wave_retrieval  # noqa: E402
from deepwide_agent.v25020_pacing_distinct_coverage_retrieval import (  # noqa: E402
    run_pacing_distinct_coverage_retrieval,
    validate_isolation,
)


QUESTION = """Use the official Acme Package Index public page.
<PACKAGES>
1. AlphaKit
2. BetaCore
3. GammaTools
</PACKAGES>
Column names: Package, Version, Published, License. Return one table only."""
QUERIES = ["neutral one", "neutral two", "neutral three", "neutral four"]


class Clock:
    def __init__(self) -> None:
        self.value = 0.0
        self.lock = threading.Lock()

    def __call__(self) -> float:
        with self.lock:
            self.value += 1.0
            return self.value


class FakeRateSearch:
    def __init__(self) -> None:
        self.search_invocations = 0
        self.fetch_history: list[list[str]] = []
        self.calls = self.failures = self.tool_calls = 0
        self.fetch_calls = self.fetch_failures = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def search_many(self, queries, **_kwargs):
        values = list(queries)
        self.search_invocations += 1
        self.calls += len(values)
        self.tool_calls += len(values)
        host = "packages.acme.example" if self.search_invocations == 1 else "search.example"
        return [
            {
                "query": query,
                "answer": "",
                "results": [
                    {
                        "url": f"https://{host}/wave-{self.search_invocations}/q-{q}/source-{i}",
                        "title": "neutral source",
                        "content": "",
                    }
                    for i in range(3)
                ],
            }
            for q, query in enumerate(values)
        ]

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_history.append([str(item["url"]) for item in values])
        self.fetch_calls += len(values)
        first = len(self.fetch_history) == 1
        output = []
        for index, item in enumerate(values):
            links = []
            url = str(item["url"])
            if first and index == 0:
                # The source URL has an authority token and a collection path;
                # links are strict descendants with exact identity path tokens.
                url = "https://packages.acme.example/web/packages/"
                links = [
                    {"url": "AlphaKit/index.html", "text": "alpha"},
                    {"url": "BetaCore/index.html", "text": "beta"},
                    {"url": "GammaTools/index.html", "text": "gamma"},
                ]
            output.append(
                {
                    "query": item.get("query", ""),
                    "results": [
                        {
                            "url": url,
                            "requested_url": url,
                            "fetch_url": url,
                            "title": "neutral page",
                            "raw_content": f"neutral evidence {index} " + "x" * 2000,
                            "page_links": links,
                        }
                    ],
                }
            )
        return output

    def rate_aware_search_receipt(self):
        value = empty_rate_aware_receipt()
        value["provider_start_reservations"] = self.calls
        value.pop("receipt_payload_sha256")
        value["receipt_payload_sha256"] = payload_sha256(value)
        return value


class PacingDistinctCoverageRetrievalTests(unittest.TestCase):
    def _run(self, question: str = QUESTION):
        search = FakeRateSearch()
        value = run_pacing_distinct_coverage_retrieval(
            QUERIES,
            search=search,
            visible_question=question,
            required_column_count=4,
            policy=fixed_full_budget_policy(),
            monotonic=Clock(),
        )
        return search, value

    def test_candidate_changes_actual_second_wave_fetch_at_matched_cost(self) -> None:
        search, value = self._run()
        receipt = value["distinct_coverage_selection_receipt"]
        self.assertTrue(value["receipt"]["wave2"]["executed"])
        self.assertEqual([len(row) for row in search.fetch_history], [6, 4])
        self.assertEqual(receipt["control_new_distinct_identity_count"], 0)
        self.assertEqual(receipt["candidate_new_distinct_identity_count"], 3)
        self.assertEqual(receipt["new_distinct_identity_gain"], 3)
        self.assertTrue(receipt["selection_changed"])
        self.assertTrue(any("/AlphaKit/" in url for url in search.fetch_history[1]))
        self.assertTrue(any("/BetaCore/" in url for url in search.fetch_history[1]))
        self.assertTrue(any("/GammaTools/" in url for url in search.fetch_history[1]))
        self.assertEqual(value["receipt"]["total"]["fetches_attempted"], 10)

    def test_non_multi_identity_is_parent_identical(self) -> None:
        question = "Find one package from the official Acme Package Index."
        candidate_search, candidate = self._run(question)
        parent_search = FakeRateSearch()
        parent = run_pacing_aware_two_wave_retrieval(
            QUERIES,
            search=parent_search,
            required_column_count=4,
            policy=fixed_full_budget_policy(),
            monotonic=Clock(),
        )
        receipt = candidate.pop("distinct_coverage_selection_receipt")
        self.assertEqual(candidate, parent)
        self.assertEqual(candidate_search.fetch_history, parent_search.fetch_history)
        self.assertFalse(receipt["strategy_eligible"])
        self.assertFalse(receipt["selection_changed"])

    def test_parent_bindings_are_not_mutated(self) -> None:
        validate_isolation()
        self._run()
        validate_isolation()

    def test_context_isolated_across_concurrent_questions(self) -> None:
        questions = (QUESTION, "Find one package from the official Acme Index.")
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(self._run, questions))
        receipts = [value[1]["distinct_coverage_selection_receipt"] for value in values]
        self.assertEqual([row["new_distinct_identity_gain"] for row in receipts], [3, 0])

    def test_result_copy_does_not_mutate_parent_payload(self) -> None:
        _search, value = self._run()
        copied = copy.deepcopy(value)
        copied["distinct_coverage_selection_receipt"]["selection_changed"] = 0
        self.assertTrue(value["distinct_coverage_selection_receipt"]["selection_changed"])


if __name__ == "__main__":
    unittest.main()
