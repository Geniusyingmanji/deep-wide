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

from deepwide_agent.v24294_staged_reserve import (  # noqa: E402
    StagedReservePolicy,
    payload_sha256,
    run_staged_reserve,
    validate_receipt,
)
from test_v24272_two_wave_retrieval import Clock, QUERIES  # noqa: E402
from test_v24289_low_coverage_rescue import TailSearch  # noqa: E402


class V24294StagedReserveTests(unittest.TestCase):
    def test_stop_path_is_unchanged_and_has_no_reserved_effect(self) -> None:
        search = TailSearch(sparse=False)
        value = run_staged_reserve(QUERIES, search=search, required_column_count=3, monotonic=Clock())
        receipt = value["receipt"]
        validate_receipt(receipt)
        self.assertEqual(receipt["controller"]["decision"], "stop")
        self.assertEqual(receipt["reserved_stage"]["reason"], "controller_stop")
        self.assertFalse(receipt["reserved_stage"]["executed"])
        self.assertEqual(receipt["total"]["fetches_attempted"], 6)
        self.assertEqual(search.search_invocations, 1)

    def test_expand_sufficient_spends_reserve_on_ranked_continuation(self) -> None:
        search = TailSearch(sparse=True, failed_fetches=4)
        value = run_staged_reserve(QUERIES, search=search, required_column_count=3, monotonic=Clock())
        receipt = value["receipt"]
        self.assertEqual(receipt["controller"]["decision"], "expand")
        self.assertFalse(receipt["reserved_stage"]["low_coverage_before"])
        self.assertEqual(receipt["reserved_stage"]["reason"], "coverage_sufficient_ranked_continuation")
        self.assertEqual(receipt["reserved_stage"]["selected_ranked_count"], 2)
        self.assertEqual(receipt["reserved_stage"]["selected_tail_count"], 0)
        self.assertEqual(receipt["total"]["fetches_attempted"], 10)
        self.assertEqual(receipt["hosted_search_requests_added_by_reserved"], 0)

    def test_expand_low_coverage_uses_two_diverse_tail_slots_inside_cap(self) -> None:
        search = TailSearch(sparse=True, failed_fetches=8)
        value = run_staged_reserve(QUERIES, search=search, required_column_count=14, monotonic=Clock())
        receipt = value["receipt"]
        self.assertEqual(receipt["controller"]["decision"], "expand")
        self.assertTrue(receipt["reserved_stage"]["low_coverage_before"])
        self.assertEqual(receipt["reserved_stage"]["reason"], "low_coverage_diversity_tail")
        self.assertEqual(receipt["reserved_stage"]["selected_tail_count"], 2)
        self.assertEqual(receipt["reserved_stage"]["fetches_attempted"], 2)
        self.assertEqual(receipt["total_before_reserved"]["fetches_attempted"], 8)
        self.assertEqual(receipt["total"]["fetches_attempted"], 10)
        self.assertEqual(receipt["reserved_stage"]["usable_pages"], 2)
        self.assertEqual(receipt["total"]["queries_executed"], 4)
        self.assertEqual(search.search_invocations, 2)
        self.assertEqual(receipt["hosted_search_requests_added_by_reserved"], 0)
        encoded = json.dumps(receipt)
        for forbidden in ("visible one", "tail-", "discarded provider", "usable 3 0"):
            self.assertNotIn(forbidden, encoded)

    def test_latency_path_preserves_ranked_continuation_without_tail_claim(self) -> None:
        search = TailSearch(sparse=True, failed_fetches=8)
        value = run_staged_reserve(
            QUERIES,
            search=search,
            required_column_count=14,
            reserve_policy=StagedReservePolicy(maximum_pre_reserved_retrieval_seconds=1),
            monotonic=Clock(increment=2),
        )
        receipt = value["receipt"]
        self.assertTrue(receipt["reserved_stage"]["low_coverage_before"])
        self.assertEqual(receipt["reserved_stage"]["reason"], "latency_ceiling_ranked_continuation")
        self.assertEqual(receipt["reserved_stage"]["selected_ranked_count"], 2)
        self.assertEqual(receipt["reserved_stage"]["selected_tail_count"], 0)

    def test_resealed_metadata_and_accounting_tamper_are_rejected(self) -> None:
        value = run_staged_reserve(QUERIES, search=TailSearch(sparse=False), required_column_count=3, monotonic=Clock())["receipt"]
        for mutation in ("metadata", "accounting", "decision"):
            altered = copy.deepcopy(value)
            if mutation == "metadata":
                altered["question_type"] = "forbidden"
            elif mutation == "accounting":
                altered["total"]["fetches_attempted"] += 1
            else:
                altered["reserved_stage"]["reason"] = "low_coverage_diversity_tail"
            unsigned = dict(altered)
            unsigned.pop("receipt_sha256", None)
            altered["receipt_sha256"] = payload_sha256(unsigned)
            with self.assertRaises(ValueError):
                validate_receipt(altered)

    def test_invalid_contract_has_no_search_effect(self) -> None:
        search = TailSearch(sparse=True)
        with self.assertRaises(ValueError):
            run_staged_reserve(QUERIES, search=search, required_column_count=0)
        self.assertEqual(search.search_invocations, 0)


if __name__ == "__main__":
    unittest.main()
