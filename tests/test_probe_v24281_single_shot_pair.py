from __future__ import annotations

import copy
import unittest

from scripts import preregister_v24281_single_shot_pair as prereg
from scripts import probe_v24281_single_shot_pair as target


def arm(pair: int, name: str) -> dict:
    single = name == "single_shot"
    calls = 1 if single else 3
    tokens = 1000 if single else 3000
    return {
        "pair": pair,
        "arm": name,
        "terminal": True,
        "failure_type": None,
        "root_complete_mapping": False,
        "wall_seconds": 7.0 if single else 10.0,
        "search_seconds": 5.0 if single else 8.0,
        "fetch_seconds": 2.0,
        "provider_counters": {
            "calls": calls,
            "failures": 0,
            "tool_calls": calls,
            "fetch_calls": 4,
            "fetch_failures": 0,
            "input_tokens": tokens,
            "output_tokens": 100 * calls,
            "total_tokens": tokens + 100 * calls,
        },
        "recursive_suffix_chunk_requests": 0 if single else 2,
        "single_shot_action_trace_attachments": 1 if single else 0,
        "effective_search_failures": 0,
        "raw_mapping_failures": 2 if single else 0,
        "raw_unrecoverable_search_failures": 0,
        "admitted_sources": 4,
        "fetch_attempts": 4,
        "usable_pages": 4,
        "usable_chars": 6000,
        "unique_hosts": 4,
        "hard_fetch_helper_calls": 4,
        "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0,
        "benchmark_question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }


class V24281SingleShotPairTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = prereg.build_protocol(require_pristine=False, now=1)
        self.rows = [
            arm(pair, name)
            for pair in range(1, prereg.PAIR_COUNT + 1)
            for name in prereg.ARMS
        ]

    def test_protocol_freezes_shared_root_neutral_pair_without_authority(self) -> None:
        prereg.validate_protocol(value=self.protocol)
        contract = self.protocol["pair_contract"]
        self.assertTrue(contract["shared_root_response_within_pair"])
        self.assertTrue(contract["only_recursive_control_executes_suffix_requests"])
        self.assertEqual(len(contract["schedule"]), prereg.WAVES)
        self.assertEqual(
            contract["query_set_sha256"],
            prereg.payload_sha256(prereg.NEUTRAL_QUERY_PAIRS),
        )
        self.assertFalse(any(self.protocol["authorization"].values()))

    def test_synthetic_single_shot_pair_passes(self) -> None:
        summary = target.summarize(self.protocol, self.rows, 40.0)
        self.assertTrue(summary["passed"])
        self.assertEqual(
            summary["recursive"]["recursive_suffix_chunk_requests"],
            prereg.PAIR_COUNT * 2,
        )
        self.assertEqual(
            summary["single_shot"]["recursive_suffix_chunk_requests"], 0
        )
        self.assertLessEqual(
            summary["single_shot_over_recursive"]["http_search_calls"], 0.34
        )

    def test_no_exercised_split_cost_yield_and_failure_cases_fail_closed(self) -> None:
        cases = []
        no_split = copy.deepcopy(self.rows)
        for row in no_split:
            row["root_complete_mapping"] = True
            if row["arm"] == "recursive":
                row["recursive_suffix_chunk_requests"] = 0
        cases.append(no_split)

        costly = copy.deepcopy(self.rows)
        for row in costly:
            if row["arm"] == "single_shot":
                row["provider_counters"]["input_tokens"] = 2900
                row["provider_counters"]["total_tokens"] = 3000
        cases.append(costly)

        low_yield = copy.deepcopy(self.rows)
        for row in low_yield:
            if row["arm"] == "single_shot":
                row["usable_pages"] = 2
                row["usable_chars"] = 2000
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
            self.assertFalse(target.summarize(self.protocol, rows, 40.0)["passed"])

    def test_content_or_credential_surface_tamper_is_rejected(self) -> None:
        unsafe = arm(1, "single_shot")
        unsafe["query"] = "forbidden"
        with self.assertRaisesRegex(RuntimeError, "schema"):
            target.validate_arm(unsafe)

        encoded = "\n".join(
            query for pair in prereg.NEUTRAL_QUERY_PAIRS for query in pair
        )
        self.assertNotIn("DeepWide", encoded)
        self.assertNotIn("task_", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)


if __name__ == "__main__":
    unittest.main()
