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

from deepwide_agent.v24265_paired_normalizer_runtime import (  # noqa: E402
    run_paired_task,
    validate_paired_result,
)


TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": "请输出Markdown表格，列名依次为：名称、省份、年份。",
}


class Clock:
    def __init__(self) -> None:
        self.value = 1.0

    def __call__(self) -> float:
        self.value += 0.1
        return self.value


class Model:
    def __init__(self, outputs: list[str | BaseException]) -> None:
        self.outputs = list(outputs)
        self.requests = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def complete(self, *_args, **_kwargs):
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        value = self.outputs.pop(0)
        if isinstance(value, BaseException):
            raise value
        return SimpleNamespace(text=value)


class Search:
    def __init__(self) -> None:
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def search_many(self, queries, *, max_results, **_kwargs):
        self.calls += len(queries)
        self.tool_calls += len(queries)
        self.input_tokens += 20 * len(queries)
        self.output_tokens += 4 * len(queries)
        self.total_tokens += 24 * len(queries)
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
                        "raw_content": "untrusted useful record",
                    }
                ],
            }
            for item in values
        ]


def plan() -> str:
    return json.dumps(
        {
            "language": "中文",
            "columns": ["wrong"],
            "row_target_hint": "one",
            "queries": ["visible query"],
        },
        ensure_ascii=False,
    )


RAW_RECOVERABLE = """```markdown
| 省份 | 名称 | 年份 |
|---|---|---|
| 北京 | 示例甲 | 2024年 |
```"""
VALID = """```markdown
| 名称 | 省份 | 年份 |
| --- | --- | --- |
| 示例甲 | 北京 | 2024年 |
```"""


class V24265PairedNormalizerRuntimeTests(unittest.TestCase):
    def test_shared_prefix_normalization_avoids_candidate_repair_cost(self) -> None:
        model = Model([plan(), RAW_RECOVERABLE, VALID])
        search = Search()
        value = run_paired_task(
            TASK, model=model, search=search, monotonic=Clock()
        )
        validate_paired_result(value)
        control = value["control"]
        candidate = value["candidate"]
        self.assertEqual(model.requests, 3)
        self.assertEqual(control["completion_kind"], "repaired")
        self.assertEqual(candidate["completion_kind"], "normalized_primary")
        self.assertEqual(control["cost"]["model"]["requests"], 3)
        self.assertEqual(candidate["cost"]["model"]["requests"], 2)
        self.assertEqual(control["plan"], candidate["plan"])
        self.assertEqual(control["evidence"], candidate["evidence"])
        self.assertTrue(value["shared_execution"]["control_needed_repair"])
        self.assertFalse(value["shared_execution"]["candidate_needed_repair"])

    def test_exact_primary_predictions_are_identical_and_use_two_requests(self) -> None:
        model = Model([plan(), VALID])
        value = run_paired_task(
            TASK, model=model, search=Search(), monotonic=Clock()
        )
        validate_paired_result(value)
        self.assertEqual(model.requests, 2)
        self.assertEqual(value["control"]["prediction"], value["candidate"]["prediction"])
        self.assertEqual(value["control"]["completion_kind"], "primary")
        self.assertEqual(value["candidate"]["completion_kind"], "primary")

    def test_unrecoverable_candidate_shares_one_repair_response(self) -> None:
        model = Model([plan(), "not a table", VALID])
        value = run_paired_task(
            TASK, model=model, search=Search(), monotonic=Clock()
        )
        validate_paired_result(value)
        self.assertEqual(model.requests, 3)
        self.assertEqual(value["control"]["completion_kind"], "repaired")
        self.assertEqual(value["candidate"]["completion_kind"], "repaired")
        self.assertEqual(value["control"]["prediction"], value["candidate"]["prediction"])

    def test_privileged_metadata_is_rejected_before_effect(self) -> None:
        model = Model([plan(), VALID])
        search = Search()
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_paired_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                monotonic=Clock(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.calls, 0)

    def test_provider_failure_is_content_free_in_both_arms(self) -> None:
        value = run_paired_task(
            TASK,
            model=Model([RuntimeError("private provider body")]),
            search=Search(),
            monotonic=Clock(),
        )
        validate_paired_result(value)
        rendered = json.dumps(value, ensure_ascii=False)
        self.assertNotIn("private provider body", rendered)
        self.assertEqual(value["control"]["completion_kind"], "best_effort_fallback")
        self.assertEqual(value["candidate"]["completion_kind"], "best_effort_fallback")

    def test_prediction_and_shared_receipt_tamper_fail_closed(self) -> None:
        value = run_paired_task(
            TASK, model=Model([plan(), VALID]), search=Search(), monotonic=Clock()
        )
        prediction = copy.deepcopy(value)
        prediction["candidate"]["prediction"] += "\n"
        with self.assertRaisesRegex(ValueError, "seal"):
            validate_paired_result(prediction)
        receipt = copy.deepcopy(value)
        receipt["shared_execution"]["question"] = "forbidden"
        with self.assertRaisesRegex(ValueError, "receipt"):
            validate_paired_result(receipt)


if __name__ == "__main__":
    unittest.main()
