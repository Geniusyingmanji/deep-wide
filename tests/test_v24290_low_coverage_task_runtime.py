from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24290_low_coverage_task_runtime import (  # noqa: E402
    run_v24290_task,
    validate_v24290_result,
)
from test_v24272_two_wave_retrieval import Clock  # noqa: E402
from test_v24289_low_coverage_rescue import TailSearch  # noqa: E402


class FakeModel:
    def __init__(self, values):
        self.values = list(values)
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens, json_mode
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return SimpleNamespace(text=value)


def limits() -> ScoreFirstLimits:
    return ScoreFirstLimits(
        wall_seconds=120,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


def task() -> dict[str, str]:
    return {
        "opaque_id": "task_" + "9" * 24,
        "question": "Return one table. The column names are: Name, Version, and Date.",
    }


def plan() -> str:
    return json.dumps(
        {
            "columns": ["wrong"],
            "queries": ["visible one", "visible two", "visible three", "visible four"],
        }
    )


TABLE = "| Name | Version | Date |\n| --- | --- | --- |\n| A | 1 | 2026 |"


class V24290LowCoverageTaskRuntimeTests(unittest.TestCase):
    def test_end_to_end_stop_path_keeps_schema_timing_and_zero_rescue(self) -> None:
        search = TailSearch(sparse=False)
        result = run_v24290_task(
            task(),
            model=FakeModel([plan(), TABLE]),
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_v24290_result(result)
        self.assertEqual(result["visible_schema"]["status"], "applied")
        self.assertEqual(result["columns"], ["Name", "Version", "Date"])
        receipt = result["two_wave_retrieval"]["receipt"]
        self.assertEqual(receipt["controller"]["decision"], "stop")
        self.assertFalse(receipt["rescue"]["triggered"])
        self.assertEqual(receipt["hosted_search_requests_added_by_rescue"], 0)
        self.assertEqual(result["two_wave_retrieval"]["cache_miss_count"], 0)
        self.assertEqual(result["two_wave_retrieval"]["network_fetches_during_cache_serve"], 0)

    def test_expand_low_coverage_rescue_reaches_synthesis_without_extra_search(self) -> None:
        search = TailSearch(sparse=True, failed_fetches=3, empty_first=True)
        result = run_v24290_task(
            task(),
            model=FakeModel([plan(), TABLE]),
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_v24290_result(result)
        receipt = result["two_wave_retrieval"]["receipt"]
        self.assertTrue(receipt["rescue"]["triggered"])
        self.assertEqual(search.search_invocations, 2)
        self.assertEqual(receipt["hosted_search_requests_added_by_rescue"], 0)
        self.assertLessEqual(receipt["total"]["fetches_attempted"], 10)
        self.assertEqual(
            result["budget"]["admitted_fetch_targets"],
            receipt["total"]["usable_pages"],
        )
        self.assertEqual(result["completion_kind"], "primary")

    def test_receipts_contain_no_visible_content_or_identifier(self) -> None:
        visible = task()
        result = run_v24290_task(
            visible,
            model=FakeModel([plan(), TABLE]),
            search=TailSearch(sparse=True, failed_fetches=3, empty_first=True),
            limits=limits(),
            monotonic=Clock(),
        )
        encoded = json.dumps(
            {
                "retrieval": result["two_wave_retrieval"],
                "schema": result["visible_schema"],
                "timing": result["attributed_timing"],
            }
        )
        for forbidden in (visible["opaque_id"], "visible one", "Name", "tail-", "| A |"):
            self.assertNotIn(forbidden, encoded)

    def test_tamper_and_privileged_input_fail_closed(self) -> None:
        result = run_v24290_task(
            task(),
            model=FakeModel([plan(), TABLE]),
            search=TailSearch(sparse=False),
            limits=limits(),
            monotonic=Clock(),
        )
        altered = copy.deepcopy(result)
        altered["two_wave_retrieval"]["receipt"]["total"]["fetches_attempted"] += 1
        with self.assertRaises(ValueError):
            validate_v24290_result(altered)
        model = FakeModel([plan(), TABLE])
        search = TailSearch(sparse=False)
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24290_task(
                {**task(), "question_type": "forbidden"},
                model=model,
                search=search,
                limits=limits(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.search_invocations, 0)


if __name__ == "__main__":
    unittest.main()
