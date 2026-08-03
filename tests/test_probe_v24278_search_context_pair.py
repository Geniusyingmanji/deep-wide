from __future__ import annotations

import copy
import unittest

from scripts import preregister_v24278_search_context_pair as prereg
from scripts import probe_v24278_search_context_pair as target


def arm(pair: int, context: str) -> dict:
    low = context == "low"
    return {
        "pair": pair,
        "context": context,
        "terminal": True,
        "failure_type": None,
        "wall_seconds": 8.0 if low else 10.0,
        "search_seconds": 5.0 if low else 7.0,
        "fetch_seconds": 3.0,
        "provider_counters": {
            "calls": 1,
            "failures": 0,
            "tool_calls": 2,
            "fetch_calls": 6,
            "fetch_failures": 0,
            "input_tokens": 600 if low else 1000,
            "output_tokens": 100,
            "total_tokens": 700 if low else 1100,
        },
        "search_invocations": 1,
        "logical_queries": 2,
        "raw_unrecoverable_search_failures": 0,
        "admitted_sources": 6,
        "fetch_attempts": 6,
        "usable_pages": 5,
        "usable_chars": 20000,
        "unique_hosts": 4,
        "hard_fetch_helper_calls": 6,
        "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0,
        "benchmark_question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }


class V24278SearchContextPairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = prereg.build_protocol(require_pristine=False, now=1)
        self.rows = [
            arm(pair, context)
            for pair in range(1, prereg.PAIR_COUNT + 1)
            for context in prereg.CONTEXTS
        ]

    def test_protocol_freezes_exact_neutral_pair_without_authority(self) -> None:
        prereg.validate_protocol(value=self.protocol)
        self.assertEqual(len(prereg.schedule()), 2)
        self.assertEqual(
            self.protocol["pair_contract"]["query_set_sha256"],
            prereg.payload_sha256(prereg.NEUTRAL_QUERY_PAIRS),
        )
        self.assertFalse(any(self.protocol["authorization"].values()))

    def test_synthetic_low_context_pair_passes(self) -> None:
        summary = target.summarize(self.protocol, self.rows, 30.0)
        self.assertTrue(summary["passed"])
        self.assertLessEqual(summary["low_over_medium"]["search_input_tokens"], 0.7)
        self.assertEqual(
            summary["pair_directions"]["search_input_tokens"]["low_better"],
            prereg.PAIR_COUNT,
        )

    def test_token_yield_deadline_and_content_tamper_fail_closed(self) -> None:
        cases = []
        token = copy.deepcopy(self.rows)
        for row in token:
            if row["context"] == "low":
                row["provider_counters"]["input_tokens"] = 900
                row["provider_counters"]["total_tokens"] = 1000
        cases.append(token)
        yield_failure = copy.deepcopy(self.rows)
        for row in yield_failure:
            if row["context"] == "low":
                row["usable_pages"] = 1
                row["usable_chars"] = 1000
        cases.append(yield_failure)
        deadline = copy.deepcopy(self.rows)
        deadline[0]["hard_fetch_deadline_failures"] = 1
        cases.append(deadline)
        zero_yield = copy.deepcopy(self.rows)
        for row in zero_yield:
            row["admitted_sources"] = 0
            row["fetch_attempts"] = 0
            row["usable_pages"] = 0
            row["usable_chars"] = 0
            row["unique_hosts"] = 0
            row["provider_counters"]["fetch_calls"] = 0
            row["hard_fetch_helper_calls"] = 0
        cases.append(zero_yield)
        for rows in cases:
            self.assertFalse(target.summarize(self.protocol, rows, 30.0)["passed"])

        unsafe = arm(1, "low")
        unsafe["query"] = "forbidden"
        with self.assertRaisesRegex(RuntimeError, "schema"):
            target.validate_arm(unsafe)

    def test_neutral_queries_have_no_benchmark_ids_or_urls(self) -> None:
        encoded = "\n".join(
            query for pair in prereg.NEUTRAL_QUERY_PAIRS for query in pair
        )
        self.assertNotIn("DeepWide", encoded)
        self.assertNotIn("task_", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)


if __name__ == "__main__":
    unittest.main()
