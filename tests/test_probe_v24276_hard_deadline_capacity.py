from __future__ import annotations

import copy
import unittest

from scripts import probe_v24276_hard_deadline_capacity as target


def task(ordinal: int) -> dict:
    return {
        "ordinal": ordinal,
        "terminal": True,
        "failure_type": None,
        "completion_kind": "primary",
        "wall_seconds": 20.0,
        "model_counters": {
            "requests": 2,
            "attempts": 2,
            "input_tokens": 10,
            "output_tokens": 10,
            "total_tokens": 20,
        },
        "search_counters": {
            "calls": 1,
            "failures": 0,
            "tool_calls": 1,
            "fetch_calls": 6,
            "fetch_failures": 0,
            "input_tokens": 10,
            "output_tokens": 10,
            "total_tokens": 20,
        },
        "stage_seconds": {"search": 10.0, "fetch": 3.0},
        "failure_types": [],
        "retrieval_status": "completed",
        "controller_decision": "stop",
        "controller_reason": "first_wave_sufficient",
        "queries_executed": 2,
        "fetches_attempted": 6,
        "usable_pages": 4,
        "unrecoverable_search_failures": 0,
        "cache_miss_count": 0,
        "cache_serve_network_fetches": 0,
        "hard_fetch_helper_calls": 6,
        "hard_fetch_deadline_failures": 0,
        "fetch_helper_failures": 0,
        "question_query_url_host_page_prediction_answer_task_id_or_hash_persisted": False,
        "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
    }


class ProbeV24276HardDeadlineCapacityTests(unittest.TestCase):
    def test_synthetic_eight_way_result_passes(self) -> None:
        tasks = [task(index + 1) for index in range(8)]
        summary = target.summarize(tasks, 30.0)
        self.assertTrue(summary["passed"])

    def test_deadline_helper_or_retrieval_failure_fails_gate(self) -> None:
        for field in (
            "hard_fetch_deadline_failures",
            "fetch_helper_failures",
            "unrecoverable_search_failures",
            "cache_miss_count",
            "cache_serve_network_fetches",
        ):
            tasks = [task(index + 1) for index in range(8)]
            tasks[0][field] = 1
            self.assertFalse(target.summarize(tasks, 30.0)["passed"])
        tasks = [task(index + 1) for index in range(8)]
        tasks[0]["retrieval_status"] = "failed"
        self.assertFalse(target.summarize(tasks, 30.0)["passed"])

    def test_task_and_result_tamper_fail_closed(self) -> None:
        value = task(1)
        value["prediction"] = "forbidden"
        with self.assertRaisesRegex(RuntimeError, "schema"):
            target.validate_task(value)
        tasks = [task(index + 1) for index in range(8)]
        summary = target.summarize(tasks, 30.0)
        self.assertTrue(summary["passed"])
        altered = copy.deepcopy(summary)
        altered["hard_fetch_deadline_failures"] = 1
        self.assertNotEqual(altered, target.summarize(tasks, 30.0))

    def test_neutral_questions_have_no_benchmark_ids_or_urls(self) -> None:
        self.assertEqual(len(target.NEUTRAL_QUESTIONS), 8)
        encoded = "\n".join(target.NEUTRAL_QUESTIONS)
        self.assertNotIn("task_", encoded)
        self.assertNotIn("DeepWide", encoded)
        self.assertNotIn("http://", encoded)
        self.assertNotIn("https://", encoded)


if __name__ == "__main__":
    unittest.main()
