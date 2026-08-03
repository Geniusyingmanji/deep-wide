from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import probe_v24290_neutral_low_coverage as target  # noqa: E402
from test_v24272_two_wave_retrieval import Clock  # noqa: E402
from test_v24289_low_coverage_rescue import TailSearch  # noqa: E402
from test_v24290_low_coverage_task_runtime import FakeModel, TABLE, limits, plan, task  # noqa: E402
from deepwide_agent.v24290_low_coverage_task_runtime import run_v24290_task  # noqa: E402


class V24290NeutralProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        search = TailSearch(sparse=True, failed_fetches=3, empty_first=True)
        result = run_v24290_task(
            task(),
            model=FakeModel([plan(), TABLE]),
            search=search,
            limits=limits(),
            monotonic=Clock(),
        )
        cls.value = target.project(
            result,
            model_counters=target._counters(result_model := FakeModel([]), target.MODEL_COUNTERS),
            search_counters=target._counters(search, target.SEARCH_COUNTERS),
            wall_seconds=1.0,
            now=1,
        )
        # Projection validation binds counts, not the disposable fake-model
        # object used above; replace its request counters with the task budget.
        cls.value["model_counters"]["requests"] = result["budget"]["admitted_model_calls"]
        cls.value["model_counters"]["attempts"] = result["budget"]["admitted_model_calls"]
        cls.value["model_counters"]["input_tokens"] = 20
        cls.value["model_counters"]["output_tokens"] = 10
        cls.value["model_counters"]["total_tokens"] = 30
        unsigned = dict(cls.value)
        unsigned.pop("result_payload_sha256", None)
        cls.value["result_payload_sha256"] = target.object_sha256(unsigned)
        target.validate_projection(cls.value)

    def test_projection_is_content_free_effect_accounted_and_unauthorized(self) -> None:
        target.validate_projection(self.value)
        self.assertTrue(self.value["coverage"]["rescue_triggered"])
        self.assertEqual(self.value["controller"]["hosted_search_requests_added_by_rescue"], 0)
        self.assertGreater(self.value["coverage"]["usable_pages_after_rescue"], self.value["coverage"]["usable_pages_before_rescue"])
        self.assertFalse(any(self.value["authorization"].values()))
        self.assertEqual(
            self.value["fault_injection"]["claim_scope"],
            "mechanism_robustness_not_natural_frequency_or_benchmark_quality",
        )

    def test_fault_injection_executes_real_search_then_masks_only_first_output(self) -> None:
        class Inner:
            calls = 0

            def search_many(self, queries, **kwargs):
                del queries, kwargs
                self.calls += 1
                return [{"results": [{"url": "https://example.com"}]}]

            def fetch_urls(self, requests_):
                return list(requests_)

        inner = Inner()
        wrapper = target.FirstWaveSourceMissInjection(inner)
        self.assertEqual(wrapper.search_many(["one"]), [])
        self.assertEqual(inner.calls, 1)
        second = wrapper.search_many(["two"])
        self.assertEqual(len(second), 1)
        self.assertEqual(inner.calls, 2)
        self.assertTrue(wrapper.first_wave_real_provider_call_executed)

    def test_resealed_search_or_cache_tamper_is_rejected(self) -> None:
        for mutation in ("search", "cache"):
            altered = copy.deepcopy(self.value)
            if mutation == "search":
                altered["controller"]["provider_search_calls_after_rescue"] += 1
            else:
                altered["runtime_health"]["cache_miss_count"] = 1
            unsigned = dict(altered)
            unsigned.pop("result_payload_sha256", None)
            altered["result_payload_sha256"] = target.object_sha256(unsigned)
            with self.assertRaisesRegex(RuntimeError, "effect accounting drifted"):
                target.validate_projection(altered)


if __name__ == "__main__":
    unittest.main()
