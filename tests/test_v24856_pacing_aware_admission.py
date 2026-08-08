from __future__ import annotations

import concurrent.futures
import copy
import json
import sys
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24799_fixed_full_budget_control import (  # noqa: E402
    fixed_full_budget_policy,
)
from deepwide_agent.v24852_rate_aware_tavily_search import (  # noqa: E402
    empty_rate_aware_receipt,
)
from deepwide_agent.v24263_global_model_limiter import payload_sha256  # noqa: E402
from deepwide_agent.v24856_pacing_aware_admission import (  # noqa: E402
    MAX_PROVIDER_WAIT_CREDIT_SECONDS,
    run_pacing_aware_two_wave_retrieval,
    validate_isolation,
    validate_receipt,
)


class Clock:
    def __init__(self, increment: float = 16.0) -> None:
        self.value = 0.0
        self.increment = increment
        self.lock = threading.Lock()

    def __call__(self) -> float:
        with self.lock:
            self.value += self.increment
            return self.value


class FakeRateSearch:
    batch_size = 8
    max_workers = 1
    fetch_workers = 8
    fetch_timeout = 20
    fetch_pages = False

    def __init__(self, wait: float) -> None:
        self.wait = wait
        self.search_invocations = 0
        self.fetch_invocations = 0
        self.calls = 0
        self.failures = 0
        self.tool_calls = 0
        self.fetch_calls = 0
        self.fetch_failures = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0

    def search_many(self, queries, **_kwargs):
        values = list(queries)
        self.search_invocations += 1
        self.calls += len(values)
        self.tool_calls += len(values)
        output = []
        for query_index, query in enumerate(values):
            results = [
                {
                    "url": (
                        f"https://wave-{self.search_invocations}-"
                        f"q-{query_index}-source-{source}.example/page"
                    ),
                    "title": "neutral source",
                    "content": "",
                }
                for source in range(3)
            ]
            output.append({"query": query, "answer": "", "results": results})
        return output

    def fetch_urls(self, requests_):
        values = list(requests_)
        self.fetch_invocations += 1
        self.fetch_calls += len(values)
        return [
            {
                "query": item["query"],
                "results": [
                    {
                        "url": item["url"],
                        "title": "neutral page",
                        "raw_content": (
                            f"neutral evidence wave {self.fetch_invocations} "
                            f"item {index} " + "x" * 2_000
                        ),
                    }
                ],
            }
            for index, item in enumerate(values)
        ]

    def rate_aware_search_receipt(self):
        value = empty_rate_aware_receipt()
        value["provider_start_reservations"] = self.search_invocations * 2
        value["provider_pacing_wait_events"] = int(
            bool(self.search_invocations and self.wait)
        )
        value["total_provider_gate_wait_seconds"] = round(
            self.wait * self.search_invocations * 2, 6
        )
        value["max_provider_gate_wait_seconds"] = round(
            self.wait if self.search_invocations else 0.0, 6
        )
        value.pop("receipt_payload_sha256")
        value["receipt_payload_sha256"] = payload_sha256(value)
        return value


QUERIES = ["neutral one", "neutral two", "neutral three", "neutral four"]


class V24856PacingAwareAdmissionTests(unittest.TestCase):
    def run_value(self, wait: float):
        return run_pacing_aware_two_wave_retrieval(
            QUERIES,
            search=FakeRateSearch(wait),
            required_column_count=3,
            policy=fixed_full_budget_policy(),
            monotonic=Clock(),
        )

    def test_isolated_binding_does_not_patch_frozen_parent(self) -> None:
        validate_isolation()

    def test_max_wait_changes_only_latency_admission(self) -> None:
        value = self.run_value(5.0)
        pacing = validate_receipt(value["pacing_admission_receipt"])
        retrieval = value["receipt"]
        self.assertEqual(pacing["legacy_decision"], "stop")
        self.assertEqual(pacing["legacy_reason"], "latency_ceiling")
        self.assertEqual(pacing["pacing_aware_decision"], "expand")
        self.assertTrue(pacing["decision_changed"])
        self.assertEqual(pacing["raw_wave1_elapsed_seconds"], 32.0)
        self.assertEqual(pacing["credited_provider_wait_seconds"], 5.0)
        self.assertEqual(pacing["effective_wave1_ceiling_seconds"], 35.0)
        self.assertEqual(retrieval["controller"]["policy"]["maximum_wave1_seconds"], 35.0)
        self.assertTrue(retrieval["wave2"]["executed"])
        self.assertEqual(retrieval["total"]["queries_executed"], 4)

    def test_zero_wait_preserves_legacy_stop(self) -> None:
        value = self.run_value(0.0)
        pacing = value["pacing_admission_receipt"]
        self.assertEqual(pacing["legacy_decision"], "stop")
        self.assertEqual(pacing["pacing_aware_decision"], "stop")
        self.assertFalse(pacing["decision_changed"])
        self.assertFalse(value["receipt"]["wave2"]["executed"])
        self.assertEqual(value["receipt"]["total"]["queries_executed"], 2)

    def test_wait_credit_is_capped_at_thirty_seconds(self) -> None:
        value = self.run_value(50.0)
        receipt = value["pacing_admission_receipt"]
        self.assertEqual(
            receipt["maximum_provider_wait_credit_seconds"],
            MAX_PROVIDER_WAIT_CREDIT_SECONDS,
        )
        self.assertEqual(receipt["credited_provider_wait_seconds"], 30.0)
        self.assertEqual(receipt["effective_wave1_ceiling_seconds"], 60.0)

    def test_receipt_is_content_free_and_forbids_privileged_inputs(self) -> None:
        receipt = self.run_value(5.0)["pacing_admission_receipt"]
        encoded = json.dumps(receipt, ensure_ascii=False)
        for prohibited in QUERIES + ["https://"]:
            self.assertNotIn(prohibited, encoded)
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_reward_read"
            ]
        )
        self.assertFalse(receipt["historical_correctness_429_or_latency_cohort_read"])

    def test_resealed_tamper_fails(self) -> None:
        receipt = copy.deepcopy(self.run_value(5.0)["pacing_admission_receipt"])
        receipt["absolute_task_deadline_changed"] = True
        receipt.pop("receipt_payload_sha256")
        receipt["receipt_payload_sha256"] = __import__(
            "deepwide_agent.v24856_pacing_aware_admission",
            fromlist=["object_sha256"],
        ).object_sha256(receipt)
        with self.assertRaises(ValueError):
            validate_receipt(receipt)

    def test_context_is_isolated_across_threads(self) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            values = list(pool.map(self.run_value, (0.0, 5.0)))
        receipts = [value["pacing_admission_receipt"] for value in values]
        self.assertEqual(
            [receipt["credited_provider_wait_seconds"] for receipt in receipts],
            [0.0, 5.0],
        )
        self.assertEqual(
            [receipt["pacing_aware_decision"] for receipt in receipts],
            ["stop", "expand"],
        )


if __name__ == "__main__":
    unittest.main()
