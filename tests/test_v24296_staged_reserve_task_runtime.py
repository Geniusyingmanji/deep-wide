from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits  # noqa: E402
from deepwide_agent.v24296_staged_reserve_task_runtime import (  # noqa: E402
    run_v24296_task,
    run_v24296_total_task,
    validate_v24296_result,
    validate_v24296_total_result,
)
from test_v24272_two_wave_retrieval import Clock  # noqa: E402
from test_v24289_low_coverage_rescue import TailSearch  # noqa: E402
from test_v24290_low_coverage_task_runtime import FakeModel, TABLE, plan, task  # noqa: E402


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


class V24296StagedReserveTaskRuntimeTests(unittest.TestCase):
    def test_stop_path_preserves_schema_and_cache_only_evidence(self) -> None:
        search = TailSearch(sparse=False)
        result = run_v24296_task(
            task(),
            model=FakeModel([plan(), TABLE]),
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_v24296_result(result)
        self.assertEqual(result["visible_schema"]["status"], "applied")
        self.assertEqual(result["columns"], ["Name", "Version", "Date"])
        runtime = result["staged_reserve_retrieval"]
        receipt = runtime["receipt"]
        self.assertEqual(receipt["controller"]["decision"], "stop")
        self.assertFalse(receipt["reserved_stage"]["executed"])
        self.assertEqual(runtime["cache_miss_count"], 0)
        self.assertEqual(runtime["network_fetches_during_cache_serve"], 0)
        self.assertEqual(runtime["observed_inner_fetch_calls"], 6)

    def test_expand_low_coverage_reserved_tail_reaches_synthesis(self) -> None:
        search = TailSearch(sparse=True, failed_fetches=8)
        result = run_v24296_task(
            task(),
            model=FakeModel([plan(), TABLE]),
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        validate_v24296_result(result)
        runtime = result["staged_reserve_retrieval"]
        receipt = runtime["receipt"]
        self.assertEqual(receipt["controller"]["decision"], "expand")
        self.assertEqual(receipt["total_before_reserved"]["fetches_attempted"], 8)
        self.assertEqual(receipt["reserved_stage"]["reason"], "low_coverage_diversity_tail")
        self.assertEqual(receipt["reserved_stage"]["selected_tail_count"], 2)
        self.assertEqual(receipt["total"]["fetches_attempted"], 10)
        self.assertEqual(receipt["hosted_search_requests_added_by_reserved"], 0)
        self.assertEqual(runtime["cache_requested_source_count"], 2)
        self.assertEqual(runtime["cache_returned_page_count"], 2)
        self.assertEqual(runtime["cache_miss_count"], 0)
        self.assertEqual(runtime["network_fetches_during_cache_serve"], 0)
        self.assertEqual(result["budget"]["admitted_fetch_targets"], 2)
        self.assertEqual(result["evidence"]["fetch_target_count"], 2)
        self.assertEqual(result["completion_kind"], "primary")

    def test_expand_sufficient_uses_ranked_reserved_continuation(self) -> None:
        result = run_v24296_task(
            task(),
            model=FakeModel([plan(), TABLE]),
            search=TailSearch(sparse=True, failed_fetches=4),
            limits=limits(),
            monotonic=Clock(),
        )
        receipt = result["staged_reserve_retrieval"]["receipt"]
        self.assertEqual(receipt["reserved_stage"]["reason"], "coverage_sufficient_ranked_continuation")
        self.assertEqual(receipt["reserved_stage"]["selected_ranked_count"], 2)
        self.assertEqual(receipt["reserved_stage"]["selected_tail_count"], 0)

    def test_total_boundary_returns_valid_fallback(self) -> None:
        result = run_v24296_total_task(
            task(),
            model=FakeModel([KeyboardInterrupt()]),
            search=TailSearch(sparse=False),
            limits=limits(),
            monotonic=Clock(),
        )
        self.assertEqual(validate_v24296_total_result(result), "fallback")
        self.assertEqual(result["completion_kind"], "worker_failure_fallback")
        self.assertEqual(
            result["failures"],
            [{"stage": "v24296_runtime_totality", "type": "ValueError"}],
        )
        self.assertEqual(result["budget"]["admitted_fetch_targets"], 0)

    def test_total_boundary_preserves_valid_candidate(self) -> None:
        result = run_v24296_total_task(
            task(),
            model=FakeModel([plan(), TABLE]),
            search=TailSearch(sparse=False),
            limits=limits(),
            monotonic=Clock(),
        )
        self.assertEqual(validate_v24296_total_result(result), "candidate")
        self.assertEqual(result["completion_kind"], "primary")

    def test_receipts_are_content_free_and_tamper_fails(self) -> None:
        visible = task()
        result = run_v24296_task(
            visible,
            model=FakeModel([plan(), TABLE]),
            search=TailSearch(sparse=True, failed_fetches=8),
            limits=limits(),
            monotonic=Clock(),
        )
        encoded = json.dumps(
            {
                "retrieval": result["staged_reserve_retrieval"],
                "schema": result["visible_schema"],
                "timing": result["attributed_timing"],
            }
        )
        for forbidden in (
            visible["opaque_id"], "visible one", "Name", "tail-", "| A |"
        ):
            self.assertNotIn(forbidden, encoded)
        altered = copy.deepcopy(result)
        altered["staged_reserve_retrieval"]["receipt"]["total"]["fetches_attempted"] += 1
        with self.assertRaises(ValueError):
            validate_v24296_result(altered)

    def test_privileged_input_is_rejected_before_effects(self) -> None:
        model = FakeModel([plan(), TABLE])
        search = TailSearch(sparse=False)
        with self.assertRaisesRegex(ValueError, "privileged"):
            run_v24296_total_task(
                {**task(), "question_type": "forbidden"},
                model=model,
                search=search,
                limits=limits(),
            )
        self.assertEqual(model.requests, 0)
        self.assertEqual(search.search_invocations, 0)


if __name__ == "__main__":
    unittest.main()
