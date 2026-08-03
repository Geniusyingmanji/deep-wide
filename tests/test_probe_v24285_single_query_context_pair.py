from __future__ import annotations

import copy
import unittest

from scripts import preregister_v24285_single_query_context_pair as prereg
from scripts import probe_v24285_single_query_context_pair as target


def arm(pair: int, context: str) -> dict:
    low = context == "low"
    return {
        "pair": pair,
        "context": context,
        "query_count": 1,
        "results_per_query": 6,
        "terminal": True,
        "failure_type": None,
        "wall_seconds": 8.0 if low else 10.0,
        "search_seconds": 6.0 if low else 8.0,
        "fetch_seconds": 2.0,
        "provider_counters": {
            "calls": 1,
            "failures": 0,
            "tool_calls": 2,
            "fetch_calls": 6,
            "fetch_failures": 0,
            "input_tokens": 700 if low else 1000,
            "output_tokens": 100,
            "total_tokens": 800 if low else 1100,
        },
        "effective_search_failures": 0,
        "raw_mapping_failures": 0,
        "raw_unrecoverable_search_failures": 0,
        "recursive_split_requests": 0,
        "admitted_sources": 6,
        "fetch_attempts": 6,
        "usable_pages": 5,
        "usable_chars": 10000,
        "unique_hosts": 4,
        "hard_fetch_helper_calls": 6,
        "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0,
        "benchmark_question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }


class V24285SingleQueryContextPairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = prereg.build_protocol(require_pristine=False, now=1)
        self.rows = [
            arm(pair, context)
            for pair in range(1, prereg.PAIR_COUNT + 1)
            for context in prereg.CONTEXTS
        ]

    def test_protocol_freezes_single_query_context_pair_without_authority(self) -> None:
        prereg.validate_protocol(value=self.protocol)
        contract = self.protocol["pair_contract"]
        self.assertEqual(contract["queries_per_arm"], 1)
        self.assertEqual(contract["results_per_query"], 6)
        self.assertEqual(contract["fetch_cap"], 6)
        self.assertTrue(contract["same_single_shot_task_union_transport"])
        self.assertFalse(any(self.protocol["authorization"].values()))

    def test_synthetic_low_context_candidate_passes(self) -> None:
        summary = target.summarize(self.protocol, self.rows, 50.0)
        self.assertTrue(summary["passed"])
        self.assertLessEqual(summary["low_over_medium"]["search_input_tokens"], 0.7)
        self.assertEqual(
            summary["pair_directions"]["search_input_tokens"]["low_better"],
            prereg.PAIR_COUNT,
        )

    def test_token_yield_failure_and_deadline_cases_fail_closed(self) -> None:
        cases = []
        costly = copy.deepcopy(self.rows)
        for row in costly:
            if row["context"] == "low":
                row["provider_counters"]["input_tokens"] = 950
                row["provider_counters"]["total_tokens"] = 1050
        cases.append(costly)

        low_yield = copy.deepcopy(self.rows)
        for row in low_yield:
            if row["context"] == "low":
                row["usable_pages"] = 3
                row["usable_chars"] = 3000
                row["unique_hosts"] = 2
        cases.append(low_yield)

        failed = copy.deepcopy(self.rows)
        failed[0]["effective_search_failures"] = 1
        cases.append(failed)

        deadline = copy.deepcopy(self.rows)
        deadline[0]["hard_fetch_deadline_failures"] = 1
        deadline[0]["provider_counters"]["fetch_failures"] = 1
        cases.append(deadline)

        for rows in cases:
            self.assertFalse(target.summarize(self.protocol, rows, 50.0)["passed"])

    def test_content_surface_tamper_is_rejected(self) -> None:
        unsafe = arm(1, "low")
        unsafe["query"] = "forbidden"
        with self.assertRaisesRegex(RuntimeError, "schema"):
            target.validate_arm(unsafe)


if __name__ == "__main__":
    unittest.main()
