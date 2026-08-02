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

from deepwide_agent.v24269_task_union_discovery import (  # noqa: E402
    TaskUnionDiscoverySearchClient,
    run_v24269_task,
    validate_receipt,
    validate_v24269_result,
)
from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402


TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": "表格中的列名依次为：名称、省份、年份。只输出Markdown表格。",
}
PLAN = json.dumps(
    {
        "language": "中文",
        "columns": ["名称", "省份", "年份"],
        "queries": ["visible one", "visible two"],
    },
    ensure_ascii=False,
)
TABLE = """```markdown
| 名称 | 省份 | 年份 |
| --- | --- | --- |
| 示例 | 北京 | 2024 |
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
    def __init__(self, batches):
        self.batches = batches
        self.batch_size = 8
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
        self.failures += sum(bool(row.get("error")) for row in self.batches)
        self.tool_calls += 1
        self.input_tokens += 100
        self.output_tokens += 20
        self.total_tokens += 120
        return copy.deepcopy(self.batches)

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_calls += len(values)
        return [
            {
                "query": row["query"],
                "results": [
                    {
                        "title": row["title"],
                        "url": row["url"],
                        "raw_content": "fetched page",
                    }
                ],
            }
            for row in values
        ]


def failed_batch(sources):
    return {
        "query": "private logical query",
        "answer": "PRIVATE PROVIDER NARRATIVE",
        "results": [],
        "error": "hosted search returned no query-local URL citation",
        "hosted_search_trace": {
            "actions": [
                {
                    "query": "provider query",
                    "sources": sources,
                }
            ]
        },
    }


class V24269TaskUnionDiscoveryTests(unittest.TestCase):
    def test_action_sources_form_one_deduplicated_lead_batch_without_narrative(self) -> None:
        inner = FakeInner(
            [
                failed_batch(
                    [
                        {"url": "https://a.example/page", "title": "A"},
                        {"url": "https://b.example/page", "title": "B"},
                    ]
                ),
                failed_batch(
                    [
                        {"url": "https://a.example/page#fragment", "title": "A2"},
                    ]
                ),
            ]
        )
        client = TaskUnionDiscoverySearchClient(inner)
        batches = client.search_many(["one", "two"], max_results=3)
        self.assertEqual(len(batches), 1)
        self.assertEqual(len(batches[0]["results"]), 2)
        self.assertEqual(batches[0]["query"], "task-local discovery union")
        encoded = json.dumps(batches, ensure_ascii=False)
        self.assertNotIn("PRIVATE PROVIDER NARRATIVE", encoded)
        self.assertNotIn("private logical query", encoded)
        self.assertTrue(all(not row["content"] for row in batches[0]["results"]))
        self.assertEqual(client.calls, 1)
        self.assertEqual(client.failures, 0)
        receipt = client.receipt()
        validate_receipt(receipt)
        self.assertEqual(receipt["logical_query_count"], 2)
        self.assertEqual(receipt["raw_query_local_mapping_failure_count"], 2)
        self.assertEqual(receipt["union_source_count"], 2)
        self.assertEqual(receipt["duplicate_source_count"], 1)
        self.assertEqual(receipt["union_recovery_invocation_count"], 1)
        self.assertNotIn("example", json.dumps(receipt))

    def test_fetch_is_the_only_path_that_returns_page_text(self) -> None:
        client = TaskUnionDiscoverySearchClient(
            FakeInner([failed_batch([{"url": "https://a.example/page", "title": "A"}])])
        )
        leads = client.search_many(["one"], max_results=3)
        requests_ = [
            {
                "url": row["fetch_url"],
                "query": leads[0]["query"],
                "title": row["title"],
                "member_label": "",
            }
            for row in leads[0]["results"]
        ]
        pages = client.fetch_urls(requests_)
        self.assertEqual(pages[0]["results"][0]["raw_content"], "fetched page")
        receipt = client.receipt()
        self.assertEqual(receipt["fetch_requested_source_count"], 1)
        self.assertEqual(receipt["fetch_usable_page_count"], 1)
        self.assertTrue(receipt["fetched_page_text_is_only_active_evidence"])

    def test_absent_sources_remain_failure_and_receipt_tamper_fails_closed(self) -> None:
        client = TaskUnionDiscoverySearchClient(FakeInner([failed_batch([])]))
        self.assertEqual(client.search_many(["one"], max_results=3), [])
        self.assertEqual(client.failures, 1)
        receipt = client.receipt()
        tampered = dict(receipt)
        tampered["url"] = "https://forbidden.example"
        with self.assertRaisesRegex(ValueError, "receipt drifted"):
            validate_receipt(tampered)

    def test_full_runtime_downcasts_through_v24268_and_rejects_privileged_input(self) -> None:
        batches = [
            failed_batch([{"url": "https://a.example/page", "title": "A"}]),
            failed_batch([{"url": "https://b.example/page", "title": "B"}]),
        ]
        model = FakeModel()
        result = run_v24269_task(
            TASK,
            model=model,
            search=FakeInner(batches),
            limits=ScoreFirstLimits(
                wall_seconds=120,
                search_queries=2,
                fetch_targets=2,
                search_results_per_query=1,
            ),
            monotonic=Clock(),
        )
        validate_v24269_result(result)
        self.assertIn(
            result["completion_kind"],
            {"primary", "repaired", "normalized_primary", "normalized_repaired"},
        )
        self.assertEqual(result["discovery_union"]["union_source_count"], 2)
        self.assertEqual(result["discovery_union"]["fetch_usable_page_count"], 2)
        self.assertEqual(result["cost"]["search"]["failures"], 0)
        encoded = json.dumps(result["discovery_union"], ensure_ascii=False)
        self.assertNotIn("example", encoded)

        untouched = FakeModel()
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24269_task(
                {**TASK, "category": "forbidden"},
                model=untouched,
                search=FakeInner(batches),
            )
        self.assertEqual(untouched.requests, 0)

    def test_non_mapping_failure_is_not_erased_by_a_sibling_source(self) -> None:
        transport_failure = {
            "query": "private second query",
            "answer": "",
            "results": [],
            "error": "native search request failed",
            "provider": "azure-responses-web-search",
        }
        inner = FakeInner(
            [
                failed_batch([{"url": "https://a.example/page", "title": "A"}]),
                transport_failure,
            ]
        )
        client = TaskUnionDiscoverySearchClient(inner)
        batches = client.search_many(["one", "two"], max_results=3)
        self.assertEqual(len(batches), 1)
        self.assertEqual(client.failures, 1)
        receipt = client.receipt()
        self.assertEqual(receipt["raw_query_local_mapping_failure_count"], 1)
        self.assertEqual(receipt["raw_unrecoverable_failure_count"], 1)


if __name__ == "__main__":
    unittest.main()
