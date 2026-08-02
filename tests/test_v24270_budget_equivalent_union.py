from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from deepwide_agent.v24270_budget_equivalent_union import (  # noqa: E402
    BudgetEquivalentTaskUnionSearchClient,
    run_v24270_task,
    validate_receipt,
    validate_v24270_result,
)
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402


TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": "Table column names: Name, Value. Return only a Markdown table.",
}
PLAN = json.dumps(
    {
        "language": "English",
        "columns": ["Name", "Value"],
        "queries": ["visible query"],
    }
)
TABLE = """```markdown
| Name | Value |
| --- | --- |
| Example | Supported |
```"""


class Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 0.25
        return self.value


class FakeModel:
    def __init__(self) -> None:
        self.values = [PLAN, TABLE]
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
        return SimpleNamespace(text=self.values.pop(0))


class FakeInner:
    batch_size = 8
    max_workers = 1
    fetch_workers = 8
    fetch_timeout = 20
    fetch_pages = False

    def __init__(self, count: int) -> None:
        self.count = count
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
        self.failures += len(queries)
        self.tool_calls += 1
        sources = [
            {"url": f"https://source{index}.example/page", "title": str(index)}
            for index in range(self.count)
        ]
        return [
            {
                "query": "private",
                "answer": "PRIVATE NARRATIVE",
                "results": [],
                "error": "hosted search returned no query-local URL citation",
                "hosted_search_trace": {"actions": [{"sources": sources}]},
            }
            for _ in queries
        ]

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_calls += len(values)
        return [
            {
                "query": row["query"],
                "results": [
                    {"url": row["url"], "title": row["title"], "raw_content": "page"}
                ],
            }
            for row in values
        ]


class V24270BudgetEquivalentUnionTests(unittest.TestCase):
    def test_one_query_eleven_sources_is_stably_capped_to_three(self) -> None:
        client = BudgetEquivalentTaskUnionSearchClient(
            FakeInner(11), search_results_per_query=3, global_fetch_cap=16
        )
        batches = client.search_many(["one"], max_results=3)
        self.assertEqual(len(batches[0]["results"]), 3)
        self.assertEqual(
            [row["title"] for row in batches[0]["results"]], ["0", "1", "2"]
        )
        receipt = client.receipt()
        validate_receipt(receipt)
        self.assertEqual(receipt["pre_cap_source_count"], 11)
        self.assertEqual(receipt["post_cap_source_count"], 3)
        self.assertEqual(receipt["truncated_source_count"], 8)
        self.assertEqual(receipt["declared_query_result_capacity"], 3)
        self.assertNotIn("source0", json.dumps(receipt))

    def test_global_cap_applies_across_multiple_search_invocations(self) -> None:
        client = BudgetEquivalentTaskUnionSearchClient(
            FakeInner(20), search_results_per_query=3, global_fetch_cap=5
        )
        first = client.search_many(["one"], max_results=3)
        second = client.search_many(["two"], max_results=3)
        self.assertEqual(len(first[0]["results"]), 3)
        self.assertEqual(len(second[0]["results"]), 2)
        receipt = client.receipt()
        self.assertEqual(receipt["post_cap_source_count"], 5)
        self.assertEqual(receipt["remaining_global_fetch_capacity"], 0)

    def test_cap_drift_and_receipt_tamper_fail_closed(self) -> None:
        client = BudgetEquivalentTaskUnionSearchClient(
            FakeInner(4), search_results_per_query=3, global_fetch_cap=16
        )
        with self.assertRaisesRegex(ValueError, "per-query"):
            client.search_many(["one"], max_results=4)
        client.search_many(["one"], max_results=3)
        receipt = client.receipt()
        tampered = copy.deepcopy(receipt)
        tampered["post_cap_source_count"] = 4
        with self.assertRaisesRegex(ValueError, "accounting"):
            validate_receipt(tampered)

    def test_full_runtime_fetches_no_more_than_query_times_topk(self) -> None:
        result = run_v24270_task(
            TASK,
            model=FakeModel(),
            search=FakeInner(11),
            limits=ScoreFirstLimits(
                wall_seconds=120,
                search_queries=8,
                fetch_targets=16,
                search_results_per_query=3,
            ),
            monotonic=Clock(),
        )
        validate_v24270_result(result)
        cap = result["budget_equivalence"]
        discovery = result["discovery_union"]
        self.assertEqual(cap["logical_query_count"], 1)
        self.assertEqual(cap["pre_cap_source_count"], 11)
        self.assertEqual(cap["post_cap_source_count"], 3)
        self.assertEqual(discovery["fetch_requested_source_count"], 3)
        self.assertEqual(result["budget"]["admitted_fetch_targets"], 3)
        self.assertEqual(result["cost"]["search"]["failures"], 0)
        self.assertNotIn("example", json.dumps(cap))


if __name__ == "__main__":
    unittest.main()
