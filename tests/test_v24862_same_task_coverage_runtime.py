from __future__ import annotations

import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24273_two_wave_task_runtime as parent_retrieval  # noqa: E402
from deepwide_agent import v24862_same_task_coverage_runtime as runtime  # noqa: E402
from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24630_thin_backfill_search import (  # noqa: E402
    ThinSameResponseCitationTitleBackfillSearchClient,
)
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    empty_rate_aware_receipt,
)
import test_v24860_coverage_revision_integration as core_test  # noqa: E402


class SyntheticThinSearch(ThinSameResponseCitationTitleBackfillSearchClient):
    def __init__(self, clock: core_test.Clock, *, deadline: float) -> None:
        super().__init__(
            "http://unused.invalid/responses",
            "synthetic",
            reasoning_effort="low",
            service_tier="",
            timeout=30,
            max_retries=1,
            fetch_pages=False,
            max_workers=1,
            fetch_workers=1,
            hard_fetch_deadline_seconds=25,
            absolute_deadline=deadline,
            cleanup_reserve_seconds=5,
            minimum_attempt_seconds=0.01,
            monotonic=clock,
            sleeper=clock.sleep,
        )
        self.search_invocations = 0

    def rate_aware_search_receipt(self):
        return empty_rate_aware_receipt()

    def search_many(self, queries, **_kwargs):
        self.search_invocations += 1
        values = list(queries)
        self._increment("calls", len(values))
        self._increment("tool_calls", len(values))
        return [
            {
                "query": query,
                "answer": "",
                "results": [
                    {
                        "url": (
                            f"https://source-{self.search_invocations}-{index}.example/record"
                        ),
                        "title": "synthetic",
                        "content": "discarded discovery snippet",
                    }
                    for index in range(1, 4)
                ],
                "error": None,
                "provider": "synthetic",
            }
            for query in values
        ]

    def fetch_urls(self, requests_):
        values = list(requests_)
        self._increment("fetch_calls", len(values))
        return [
            {
                "query": str(item.get("query", "")),
                "answer": "",
                "results": [
                    {
                        "url": str(item["url"]),
                        "requested_url": str(item["url"]),
                        "fetch_url": str(item["url"]),
                        "title": "synthetic",
                        "raw_content": "Alpha record. Date: 2026.",
                    }
                ],
                "error": None,
                "provider": "synthetic-fetch",
            }
            for item in values
        ]


class V24862SameTaskCoverageRuntimeTests(unittest.TestCase):
    def test_parent_modules_are_not_monkey_patched(self) -> None:
        runtime.validate_isolation()
        self.assertIsNot(
            parent_retrieval.TwoWaveCachingSearchClient.search_many,
            runtime._PACING_SEARCH_MANY,
        )

    def test_capture_uses_only_cache_entries_selected_as_fetched_leads(self) -> None:
        proxy = object.__new__(runtime.SameTaskCoverageCachingSearchClient)
        proxy.inner = SimpleNamespace()
        proxy._page_cache = {
            "https://a.example/page": {
                "url": "https://a.example/page",
                "raw_content": "Alpha record. Date: 2026.",
            },
            "https://unused.example/page": {
                "url": "https://unused.example/page",
                "raw_content": "must not be captured",
            },
        }
        output = [
            {
                "query": "fetched-page cache",
                "results": [{"url": "https://a.example/page"}],
            }
        ]
        with mock.patch.object(runtime, "_PACING_SEARCH_MANY", return_value=output):
            returned = proxy.search_many(["visible query"], max_results=3)
        self.assertEqual(returned, output)
        pages = getattr(proxy.inner, runtime.PAGE_ATTRIBUTE)
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0].url, "https://a.example/page")
        self.assertNotIn("unused", pages[0].content)

    def test_capture_failure_degrades_to_empty_private_prefix(self) -> None:
        proxy = object.__new__(runtime.SameTaskCoverageCachingSearchClient)
        proxy.inner = SimpleNamespace()
        proxy._page_cache = {
            "https://a.example/page": {
                "url": "https://a.example/page",
                "raw_content": "Alpha record. Date: 2026.",
            }
        }
        output = [{"query": "q", "results": [{"url": "https://a.example/page"}]}]
        with (
            mock.patch.object(runtime, "_PACING_SEARCH_MANY", return_value=output),
            mock.patch.object(
                runtime, "prepare_evidence_pages", side_effect=ValueError("synthetic")
            ),
        ):
            proxy.search_many(["visible query"], max_results=3)
        self.assertEqual(getattr(proxy.inner, runtime.PAGE_ATTRIBUTE), ())

    def test_full_same_task_chain_captures_pages_and_spends_third_slot(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock = core_test.Clock(100.0)
            inner = core_test.SyntheticModel(
                [core_test.PLAN, core_test.BASELINE, core_test.SUPPORTED]
            )
            model = build_deadline_model(
                url="http://unused.invalid/responses",
                model_name="synthetic",
                reasoning_effort="low",
                service_tier="",
                static_timeout_seconds=180,
                max_retries=2,
                slot_directory=core_test.make_slots(output),
                output_root=output,
                slot_cap=2,
                pool_id=POOL_ID,
                absolute_deadline=220.0,
                cleanup_reserve_seconds=5,
                minimum_attempt_seconds=0.01,
                monotonic=clock,
                sleeper=clock.sleep,
                inner=inner,
            )
            search = SyntheticThinSearch(clock, deadline=220.0)
            outcome = runtime.run_v24862_task(
                core_test.task(),
                arm="baseline",
                model=model,
                search=search,
                limits=core_test.limits(),
                two_wave_policy=TwoWavePolicy(),
                monotonic=clock,
            )
            receipt = outcome.coverage_revision_receipt
            self.assertEqual(receipt["disposition"], "admitted_supported_revision")
            self.assertEqual(receipt["logical_parent_model_calls"], 2)
            self.assertEqual(receipt["logical_final_model_calls"], 3)
            self.assertEqual(receipt["same_forward_page_count"], 6)
            self.assertTrue(receipt["complete_same_forward_page_prefix"])
            self.assertIn("| Alpha | 2026 |", outcome.result["prediction"])
            self.assertEqual(outcome.parent_model_slot_receipt["acquisitions"], 2)
            self.assertEqual(outcome.model_slot_receipt["acquisitions"], 3)
            pages = getattr(search, runtime.PAGE_ATTRIBUTE)
            self.assertEqual(len(pages), 6)
            self.assertTrue(all(page.fetch_integrity for page in pages))
            self.assertEqual(search.fetch_calls, 6)

    def test_runtime_surface_has_no_evaluator_capability_or_global_task_store(self) -> None:
        path = ROOT / "src/deepwide_agent/v24862_same_task_coverage_runtime.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = []
        assignments = []
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                assignments.append(node)
        self.assertFalse(
            any("evaluator" in name or "finalize" in name for name in imports)
        )
        self.assertNotIn("contextvars", source)
        self.assertNotIn("threading.local", source)
        self.assertIn("setattr(self.inner, PAGE_ATTRIBUTE", source)
        self.assertTrue(assignments)


if __name__ == "__main__":
    unittest.main()
