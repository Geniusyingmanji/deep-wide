from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24289_low_coverage_rescue import (  # noqa: E402
    RescuePolicy,
    payload_sha256,
    run_low_coverage_rescue,
    validate_receipt,
)
from test_v24272_two_wave_retrieval import Clock, FakeSearch, QUERIES  # noqa: E402


class TailSearch(FakeSearch):
    def __init__(self, *, sparse: bool, failed_fetches: int = 0, empty_first: bool = False):
        super().__init__(sparse=sparse)
        self.failed_fetches = failed_fetches
        self.empty_first = empty_first

    def search_many(self, queries, **kwargs):
        batches = super().search_many(queries, **kwargs)
        if self.empty_first and self.search_invocations == 1:
            for batch in batches:
                batch["results"] = []
            return batches
        # The provider can expose a larger task-local source union than top-k.
        # These deterministic tail URLs came from the same hosted-search call.
        for batch_index, batch in enumerate(batches):
            for index in range(3, 7):
                batch["results"].append(
                    {
                        "url": f"https://tail-{self.search_invocations}-{batch_index}-{index}.example/page",
                        "title": "tail",
                        "content": "discarded provider snippet",
                    }
                )
        return batches

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_invocations.append(values)
        self.fetch_calls += len(values)
        batches = []
        for index, item in enumerate(values):
            if self.failed_fetches > 0:
                self.failed_fetches -= 1
                self.fetch_failures += 1
                self.failures += 1
                batches.append({"query": item["query"], "results": [], "error": "synthetic"})
            else:
                batches.append(
                    {
                        "query": item["query"],
                        "results": [
                            {
                                "url": item["url"],
                                "title": "page",
                                "raw_content": f"usable {len(self.fetch_invocations)} {index} " + "x" * 2_000,
                            }
                        ],
                    }
                )
        return batches


class V24289LowCoverageRescueTests(unittest.TestCase):
    def test_sufficient_stop_path_has_zero_rescue_effects(self) -> None:
        search = TailSearch(sparse=False)
        value = run_low_coverage_rescue(
            QUERIES,
            search=search,
            required_column_count=3,
            monotonic=Clock(),
        )
        receipt = value["receipt"]
        validate_receipt(receipt)
        self.assertEqual(receipt["controller"]["decision"], "stop")
        self.assertFalse(receipt["rescue"]["triggered"])
        self.assertEqual(receipt["rescue"]["reason"], "controller_stop")
        self.assertEqual(receipt["hosted_search_requests_added_by_rescue"], 0)
        self.assertEqual(len(search.fetch_invocations), 1)

    def test_expand_low_coverage_fetches_same_response_tail_within_cap(self) -> None:
        search = TailSearch(sparse=True, failed_fetches=3, empty_first=True)
        value = run_low_coverage_rescue(
            QUERIES,
            search=search,
            required_column_count=6,
            monotonic=Clock(),
        )
        receipt = value["receipt"]
        self.assertEqual(receipt["controller"]["decision"], "expand")
        self.assertTrue(receipt["rescue"]["triggered"])
        self.assertGreater(receipt["rescue"]["tail_candidates"], 0)
        self.assertLessEqual(receipt["rescue"]["fetches_attempted"], 4)
        self.assertLessEqual(receipt["total"]["fetches_attempted"], 10)
        self.assertEqual(search.search_invocations, 2)
        self.assertEqual(receipt["hosted_search_requests_added_by_rescue"], 0)
        encoded = json.dumps(receipt)
        for forbidden in ("visible one", "tail-", "discarded provider", "usable 3 0"):
            self.assertNotIn(forbidden, encoded)

    def test_latency_ceiling_and_no_tail_fail_closed_without_rescue(self) -> None:
        search = TailSearch(sparse=True, failed_fetches=20)
        value = run_low_coverage_rescue(
            QUERIES,
            search=search,
            required_column_count=6,
            rescue_policy=RescuePolicy(maximum_pre_rescue_retrieval_seconds=1),
            monotonic=Clock(increment=2),
        )
        self.assertFalse(value["receipt"]["rescue"]["triggered"])
        self.assertEqual(value["receipt"]["rescue"]["reason"], "latency_ceiling")

    def test_resealed_metadata_and_accounting_tamper_are_rejected(self) -> None:
        value = run_low_coverage_rescue(
            QUERIES,
            search=TailSearch(sparse=False),
            required_column_count=3,
            monotonic=Clock(),
        )["receipt"]
        for mutation in ("metadata", "accounting"):
            altered = copy.deepcopy(value)
            if mutation == "metadata":
                altered["question_type"] = "forbidden"
            else:
                altered["total"]["fetches_attempted"] += 1
            unsigned = dict(altered)
            unsigned.pop("receipt_sha256", None)
            altered["receipt_sha256"] = payload_sha256(unsigned)
            with self.assertRaises(ValueError):
                validate_receipt(altered)

    def test_invalid_visible_contract_has_no_search_effect(self) -> None:
        search = TailSearch(sparse=True)
        with self.assertRaises(ValueError):
            run_low_coverage_rescue(
                QUERIES,
                search=search,
                required_column_count=0,
            )
        self.assertEqual(search.search_invocations, 0)


if __name__ == "__main__":
    unittest.main()
