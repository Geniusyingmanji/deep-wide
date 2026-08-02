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
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24273_two_wave_task_runtime import (  # noqa: E402
    run_v24273_task,
    validate_v24273_result,
)
from test_v24272_two_wave_retrieval import Clock, FakeSearch  # noqa: E402


TASK = {
    "opaque_id": "task_" + "0" * 24,
    "question": "Table column names: Name, Version, Date. Return only a Markdown table.",
}
PLAN = json.dumps(
    {
        "language": "English",
        "columns": ["Name", "Version", "Date"],
        "row_target_hint": "one",
        "queries": ["visible one", "visible two", "visible three", "visible four"],
    }
)
TABLE = """```markdown
| Name | Version | Date |
| --- | --- | --- |
| Example | 1 | 2026-01-01 |
```"""


class FakeModel:
    def __init__(self, values=None):
        self.values = list(values or [PLAN, TABLE])
        self.requests = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def complete(self, system, user, *, max_output_tokens, json_mode=False):
        del system, user, max_output_tokens, json_mode
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return SimpleNamespace(text=self.values.pop(0))


class RedirectSearch(FakeSearch):
    def fetch_urls(self, requests_):
        values = list(requests_)
        batches = super().fetch_urls(values)
        for index, (item, batch) in enumerate(zip(values, batches, strict=True)):
            if batch.get("results"):
                batch["results"][0]["requested_url"] = item["url"]
                batch["results"][0]["url"] = (
                    f"https://redirected-{len(self.fetch_invocations)}-{index}.example/final"
                )
        return batches


class ExplodingSearch(FakeSearch):
    def __init__(self, *, stage):
        super().__init__()
        self.stage = stage

    def search_many(self, queries, **kwargs):
        if self.stage == "search":
            raise RuntimeError("private search response")
        return super().search_many(queries, **kwargs)

    def fetch_urls(self, requests_):
        if self.stage == "fetch":
            values = list(requests_)
            self.fetch_calls += len(values)
            raise RuntimeError("private fetch response")
        return super().fetch_urls(requests_)


def limits():
    return ScoreFirstLimits(
        wall_seconds=120,
        model_calls=3,
        search_queries=4,
        fetch_targets=10,
        search_results_per_query=3,
        evidence_chars=60_000,
        page_chars=5_000,
    )


class V24273TwoWaveTaskRuntimeTests(unittest.TestCase):
    def test_end_to_end_early_stop_reuses_cached_pages_without_refetch(self):
        search = FakeSearch()
        result = run_v24273_task(
            TASK,
            model=FakeModel(),
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_v24273_result(result)
        retrieval = result["two_wave_retrieval"]
        self.assertEqual(retrieval["receipt"]["controller"]["decision"], "stop")
        self.assertEqual(retrieval["receipt"]["total"]["queries_executed"], 2)
        self.assertEqual(retrieval["receipt"]["total"]["fetches_attempted"], 6)
        self.assertEqual(retrieval["network_fetches_during_cache_serve"], 0)
        self.assertEqual(len(search.fetch_invocations), 1)
        self.assertIn(result["completion_kind"], {"primary", "normalized_primary"})

    def test_sparse_first_wave_expands_and_still_fetches_each_url_once(self):
        search = FakeSearch(sparse=True, duplicate_second=True)
        result = run_v24273_task(
            TASK,
            model=FakeModel(),
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        retrieval = result["two_wave_retrieval"]
        self.assertEqual(retrieval["receipt"]["controller"]["decision"], "expand")
        self.assertEqual(retrieval["receipt"]["total"]["queries_executed"], 4)
        fetched = [item["url"] for wave in search.fetch_invocations for item in wave]
        self.assertEqual(len(fetched), len(set(fetched)))
        self.assertEqual(retrieval["network_fetches_during_cache_serve"], 0)

    def test_result_rejects_resealed_nested_receipt_and_parent_budget_tamper(self):
        result = run_v24273_task(
            TASK,
            model=FakeModel(),
            search=FakeSearch(),
            limits=limits(),
            monotonic=Clock(),
        )
        altered = copy.deepcopy(result)
        altered["two_wave_retrieval"]["cache_miss_count"] += 1
        with self.assertRaises(ValueError):
            validate_v24273_result(altered)
        altered = copy.deepcopy(result)
        altered["budget"]["admitted_fetch_targets"] -= 1
        with self.assertRaises(ValueError):
            validate_v24273_result(altered)

    def test_redirected_pages_are_served_by_requested_url_alias(self):
        search = RedirectSearch()
        result = run_v24273_task(
            TASK,
            model=FakeModel(),
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        retrieval = result["two_wave_retrieval"]
        self.assertEqual(retrieval["status"], "completed")
        self.assertEqual(retrieval["cache_miss_count"], 0)
        self.assertEqual(
            retrieval["cache_returned_page_count"],
            retrieval["receipt"]["total"]["usable_pages"],
        )

    def test_search_and_fetch_exceptions_return_content_free_failed_receipt(self):
        for stage in ("search", "fetch"):
            with self.subTest(stage=stage):
                result = run_v24273_task(
                    TASK,
                    model=FakeModel(),
                    search=ExplodingSearch(stage=stage),
                    limits=limits(),
                    monotonic=Clock(),
                )
                validate_v24273_result(result)
                retrieval = result["two_wave_retrieval"]
                self.assertEqual(retrieval["status"], "failed")
                self.assertEqual(retrieval["failure_type"], "RuntimeError")
                self.assertIsNone(retrieval["receipt"])
                self.assertNotIn("private", json.dumps(retrieval))

    def test_control_flow_exceptions_are_not_converted_to_predictions(self):
        class InterruptedSearch(FakeSearch):
            def search_many(self, queries, **kwargs):
                raise KeyboardInterrupt

        with self.assertRaises(KeyboardInterrupt):
            run_v24273_task(
                TASK,
                model=FakeModel(),
                search=InterruptedSearch(),
                limits=limits(),
                monotonic=Clock(),
            )

    def test_privileged_input_and_oversized_budget_fail_before_effects(self):
        model = FakeModel()
        search = FakeSearch()
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24273_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                limits=limits(),
                monotonic=Clock(),
            )
        with self.assertRaisesRegex(ValueError, "envelope"):
            run_v24273_task(
                TASK,
                model=model,
                search=search,
                limits=ScoreFirstLimits(
                    wall_seconds=120, search_queries=8, fetch_targets=16
                ),
                monotonic=Clock(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.search_invocations, 0)

    def test_content_free_retrieval_receipt_has_no_task_or_evidence_values(self):
        result = run_v24273_task(
            TASK,
            model=FakeModel(),
            search=FakeSearch(),
            limits=limits(),
            monotonic=Clock(),
        )
        encoded = json.dumps(result["two_wave_retrieval"])
        for forbidden in (
            TASK["opaque_id"],
            "visible one",
            "source-0",
            "usable evidence",
            "Example",
        ):
            self.assertNotIn(forbidden, encoded)


if __name__ == "__main__":
    unittest.main()
