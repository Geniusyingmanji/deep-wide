from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24268_keyless_batched_runtime import (  # noqa: E402
    run_v24268_task,
    validate_v24268_result,
)


TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": "表格中的列名依次为：名称、省份、年份。只输出Markdown表格。",
}
PLAN = json.dumps(
    {
        "language": "中文",
        "columns": ["名称", "省份", "年份"],
        "row_target_hint": "one",
        "queries": ["visible one", "visible two", "visible three", "visible four"],
    },
    ensure_ascii=False,
)
TABLE = """```markdown
| 名称 | 省份 | 年份 |
| --- | --- | --- |
| 示例 | 未知 | 2024 |
```"""


class Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 0.25
        return self.value


class FakeModel:
    def __init__(self, values):
        self.values = list(values)
        self.requests = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        value = self.values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return SimpleNamespace(text=value)


class FakeKeylessSearch:
    def __init__(self) -> None:
        self.batch_size = 4
        self.max_workers = 1
        self.fetch_workers = 8
        self.fetch_timeout = 20
        self.fetch_pages = False
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def search_many(self, queries, **kwargs):
        self.calls += 1
        self.tool_calls += 1
        self.input_tokens += 40
        self.output_tokens += 10
        self.total_tokens += 50
        return [
            {
                "query": query,
                "answer": "lead",
                "results": [
                    {
                        "title": "source",
                        "url": f"https://example.org/{index}",
                        "fetch_url": f"https://example.org/{index}",
                        "content": "citation",
                    }
                ],
            }
            for index, query in enumerate(queries)
        ]

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_calls += len(values)
        return [
            {
                "query": item["query"],
                "results": [
                    {
                        "title": item["title"],
                        "url": item["url"],
                        "raw_content": "page text",
                    }
                ],
            }
            for item in values
        ]


class V24268KeylessBatchedRuntimeTests(unittest.TestCase):
    def result(self):
        return run_v24268_task(
            TASK,
            model=FakeModel([PLAN, TABLE]),
            search=FakeKeylessSearch(),
            limits=ScoreFirstLimits(
                wall_seconds=120,
                search_queries=4,
                fetch_targets=4,
                search_results_per_query=1,
            ),
            monotonic=Clock(),
        )

    def test_result_downcasts_to_parent_and_records_only_counts(self) -> None:
        result = self.result()
        validate_v24268_result(result)
        telemetry = result["telemetry"]
        self.assertEqual([row["stage"] for row in telemetry["model_events"]], ["plan", "synthesis"])
        self.assertEqual([row["stage"] for row in telemetry["search_events"]], ["search", "fetch"])
        self.assertEqual(telemetry["search_events"][0]["logical_request_count"], 4)
        self.assertEqual(telemetry["search_events"][0]["calls_delta"], 1)
        self.assertEqual(telemetry["table"]["row_count"], 1)
        self.assertEqual(telemetry["table"]["unknown_cell_count"], 1)
        encoded = json.dumps(telemetry, ensure_ascii=False)
        for forbidden in ("visible one", "example.org", "page text", "示例", TASK["opaque_id"]):
            self.assertNotIn(forbidden, encoded)

    def test_model_failure_is_timed_without_exception_text(self) -> None:
        result = run_v24268_task(
            TASK,
            model=FakeModel([RuntimeError("private provider response")]),
            search=FakeKeylessSearch(),
            limits=ScoreFirstLimits(wall_seconds=120, model_calls=1, search_queries=1, fetch_targets=1),
            monotonic=Clock(),
        )
        validate_v24268_result(result)
        self.assertFalse(result["telemetry"]["model_events"][0]["success"])
        self.assertNotIn("private provider response", json.dumps(result, ensure_ascii=False))

    def test_telemetry_tamper_and_privileged_input_fail_closed(self) -> None:
        result = self.result()
        tampered = copy.deepcopy(result)
        tampered["telemetry"]["search_events"][0]["url"] = "https://forbidden.example"
        with self.assertRaisesRegex(ValueError, "telemetry event"):
            validate_v24268_result(tampered)
        model = FakeModel([PLAN, TABLE])
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24268_task(
                {**TASK, "question_type": "forbidden"},
                model=model,
                search=FakeKeylessSearch(),
            )
        self.assertEqual(model.requests, 0)


if __name__ == "__main__":
    unittest.main()
