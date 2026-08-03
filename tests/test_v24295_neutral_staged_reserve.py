from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24294_staged_reserve import run_staged_reserve  # noqa: E402
from scripts import v24295_neutral_staged_reserve as target  # noqa: E402
from test_v24272_two_wave_retrieval import Clock, QUERIES  # noqa: E402
from test_v24289_low_coverage_rescue import TailSearch  # noqa: E402


class V24295NeutralStagedReserveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw = TailSearch(sparse=False)
        injection = target.FirstEightFetchOutcomeMask(raw)
        retrieval = run_staged_reserve(
            QUERIES,
            search=injection,
            required_column_count=14,
            monotonic=Clock(),
        )
        cls.value = target.project(
            retrieval,
            search_counters=target._counters(injection),
            injection=injection,
            wall_seconds=1.0,
            now=1,
        )

    def test_protocol_is_neutral_and_does_not_authorize_benchmark(self) -> None:
        protocol = target.build_protocol(ROOT, now=1, require_pristine=False)
        self.assertEqual(protocol["retrieval_contract"]["schedule"], "6_first_plus_2_observation_plus_2_reserved")
        self.assertEqual(protocol["retrieval_contract"]["maximum_fetches"], 10)
        self.assertFalse(protocol["authorization"]["benchmark_dev64_launch"])
        self.assertFalse(protocol["authorization"]["exact220_launch"])

    def test_real_fetch_wrapper_masks_eight_then_preserves_reserved_two(self) -> None:
        class Inner:
            fetch_calls = 0

            def fetch_urls(self, requests_):
                values = list(requests_)
                self.fetch_calls += len(values)
                return [{"results": [{"raw_content": "real"}]} for _ in values]

        inner = Inner()
        wrapper = target.FirstEightFetchOutcomeMask(inner)
        self.assertEqual(wrapper.fetch_urls([{}] * 6), [])
        self.assertEqual(wrapper.fetch_urls([{}] * 2), [])
        self.assertEqual(len(wrapper.fetch_urls([{}] * 2)), 2)
        self.assertEqual(inner.fetch_calls, 10)
        self.assertEqual(wrapper.real_fetch_requests_masked, 8)
        self.assertEqual(wrapper.real_reserved_fetch_requests_unmasked, 2)

    def test_projection_proves_reserved_effect_and_is_unauthorized(self) -> None:
        target.validate_projection(self.value)
        coverage = self.value["coverage"]
        self.assertEqual(coverage["fetches_before_reserved"], 8)
        self.assertEqual(coverage["reserved_fetches"], 2)
        self.assertEqual(coverage["selected_tail_count"], 2)
        self.assertGreater(coverage["usable_pages_after_reserved"], coverage["usable_pages_before_reserved"])
        self.assertFalse(any(self.value["authorization"].values()))

    def test_decision_gate_requires_every_predeclared_effect(self) -> None:
        checks = target._checks(self.value, target.GATES)
        self.assertTrue(all(checks.values()))
        decision = {
            "artifact_version": 1,
            "role": "v24295_neutral_staged_reserve_decision",
            "protocol_id": target.PROTOCOL_ID,
            "created_at_unix": 1,
            "status": "neutral_mechanism_go",
            "passed": True,
            "checks": checks,
            "failed_checks": [],
            "observed": {},
            "provenance": {},
            "claim_scope": {
                "fault_injected_mechanism_robustness": True,
                "natural_trigger_frequency_measured": False,
                "benchmark_quality_measured": False,
                "causal_quality_improvement_proven": False,
                "sota_supported": False,
            },
            "authorization": {
                "successor_dev64_design": True,
                "successor_dev64_launch": False,
                "exact220_launch": False,
                "evaluator_call": False,
                "training_credit_assignment": False,
                "leaderboard_submission_or_sota_claim": False,
            },
        }
        decision["decision_payload_sha256"] = target.payload_sha256(decision)
        target.validate_decision(decision)

    def test_resealed_effect_tamper_is_rejected(self) -> None:
        altered = copy.deepcopy(self.value)
        altered["coverage"]["fetches_after_reserved"] = 9
        unsigned = dict(altered)
        unsigned.pop("result_payload_sha256", None)
        altered["result_payload_sha256"] = target.payload_sha256(unsigned)
        with self.assertRaisesRegex(RuntimeError, "effect accounting drifted"):
            target.validate_projection(altered)


if __name__ == "__main__":
    unittest.main()
