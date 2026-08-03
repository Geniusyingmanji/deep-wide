from __future__ import annotations

import copy
import unittest

from scripts import preregister_v24284_query_width_pair as prereg
from scripts import probe_v24284_query_width_pair as target


def arm(pair: int, name: str) -> dict:
    candidate = name == "one_top6"
    config = prereg.ARM_CONFIG[name]
    return {
        "pair": pair,
        "arm": name,
        "query_count": config["query_count"],
        "results_per_query": config["results_per_query"],
        "terminal": True,
        "failure_type": None,
        "wall_seconds": 7.0 if candidate else 10.0,
        "search_seconds": 5.0 if candidate else 8.0,
        "fetch_seconds": 2.0,
        "provider_counters": {
            "calls": 1,
            "failures": 0,
            "tool_calls": 2,
            "fetch_calls": 6,
            "fetch_failures": 0,
            "input_tokens": 600 if candidate else 1000,
            "output_tokens": 100,
            "total_tokens": 700 if candidate else 1100,
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


class V24284QueryWidthPairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = prereg.build_protocol(require_pristine=False, now=1)
        self.rows = [
            arm(pair, name)
            for pair in range(1, prereg.PAIR_COUNT + 1)
            for name in prereg.ARMS
        ]

    def test_protocol_freezes_equal_fetch_capacity_without_authority(self) -> None:
        prereg.validate_protocol(value=self.protocol)
        contract = self.protocol["pair_contract"]
        self.assertEqual(contract["same_fetch_cap_per_arm"], 6)
        self.assertEqual(
            contract["arm_config"]["two_top3"]["query_count"]
            * contract["arm_config"]["two_top3"]["results_per_query"],
            6,
        )
        self.assertEqual(
            contract["arm_config"]["one_top6"]["query_count"]
            * contract["arm_config"]["one_top6"]["results_per_query"],
            6,
        )
        self.assertFalse(any(self.protocol["authorization"].values()))

    def test_synthetic_one_top6_candidate_passes(self) -> None:
        summary = target.summarize(self.protocol, self.rows, 50.0)
        self.assertTrue(summary["passed"])
        self.assertLessEqual(
            summary["one_top6_over_two_top3"]["search_input_tokens"], 0.6
        )
        self.assertEqual(
            summary["pair_directions"]["search_input_tokens"]["one_top6_better"],
            prereg.PAIR_COUNT,
        )

    def test_token_yield_failure_deadline_and_recursive_cases_fail_closed(self) -> None:
        cases = []
        costly = copy.deepcopy(self.rows)
        for row in costly:
            if row["arm"] == "one_top6":
                row["provider_counters"]["input_tokens"] = 900
                row["provider_counters"]["total_tokens"] = 1000
        cases.append(costly)

        low_yield = copy.deepcopy(self.rows)
        for row in low_yield:
            if row["arm"] == "one_top6":
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

        recursive = copy.deepcopy(self.rows)
        recursive[0]["recursive_split_requests"] = 1
        with self.assertRaisesRegex(RuntimeError, "accounting"):
            target.summarize(self.protocol, recursive, 50.0)

    def test_content_surface_tamper_is_rejected(self) -> None:
        unsafe = arm(1, "one_top6")
        unsafe["query"] = "forbidden"
        with self.assertRaisesRegex(RuntimeError, "schema"):
            target.validate_arm(unsafe)


if __name__ == "__main__":
    unittest.main()
