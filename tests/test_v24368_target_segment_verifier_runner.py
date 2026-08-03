from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24368_target_segment_verifier_runner import (  # noqa: E402
    TargetSegmentDeadlineAwareNativeSearchClient,
    build_envelope,
    run_v24368_task,
    validate_envelope,
    validate_observed_bundle,
)
from test_v24343_semantic_active_runner import Clock, slots  # noqa: E402
from test_v24367_target_segment_verifier_runtime import (  # noqa: E402
    HIDDEN_MARKER,
    Model,
    SEED,
    TASK,
    limits,
)


class DeadlineSearch(TargetSegmentDeadlineAwareNativeSearchClient):
    def __init__(self, clock: Clock, *, deadline: float):
        super().__init__(
            "http://unused.invalid/responses",
            "synthetic",
            timeout=180,
            max_retries=2,
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
        self.fetch_invocations = 0
        self.request_invocations = 0

    def _request(self, queries):  # type: ignore[override]
        self.request_invocations += 1
        self._increment("hosted_search_attempts")
        self._increment("calls")
        self._increment("tool_calls")
        start = 1 if self.request_invocations == 1 else 4
        sources = [
            {
                "type": "web_source",
                "url": f"https://host{index}.example/item/{self.request_invocations}",
                "title": f"synthetic-{index}",
            }
            for index in range(start, start + 7)
        ]
        return {
            "id": f"response-{self.request_invocations}",
            "output": [
                {
                    "type": "web_search_call",
                    "id": f"call-{self.request_invocations}",
                    "status": "completed",
                    "action": {
                        "type": "search",
                        "queries": list(queries),
                        "sources": sources,
                    },
                },
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": "[[QUERY Q0001]]\nsummary\n[[END Q0001]]\n",
                            "annotations": [],
                        }
                    ],
                },
            ],
        }

    def fetch_urls(self, requests_):
        self.fetch_invocations += 1
        values = list(requests_)
        self._increment("fetch_calls", len(values))
        self._increment("hard_fetch_helper_calls", len(values))
        hidden = self.fetch_invocations == 3
        content = (
            f"Alpha was founded in 2025, while Beta was founded in 2024. {HIDDEN_MARKER}"
            if hidden
            else "Alpha was founded in 2025. Beta was established in 2024."
        )
        return [
            {
                "query": "synthetic",
                "results": [
                    {
                        "url": item["url"],
                        "requested_url": item["url"],
                        "title": item["title"],
                        "raw_content": content,
                    }
                ],
            }
            for item in values
        ]


def clients(output: Path, clock: Clock, *, deadline: float):
    model = build_deadline_model(
        url="http://unused.invalid/responses",
        model_name="synthetic",
        reasoning_effort="low",
        service_tier="",
        static_timeout_seconds=180,
        max_retries=2,
        slot_directory=slots(output),
        output_root=output,
        slot_cap=2,
        pool_id=POOL_ID,
        absolute_deadline=deadline,
        cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.01,
        monotonic=clock,
        sleeper=clock.sleep,
        inner=Model(),
    )
    return model, DeadlineSearch(clock, deadline=deadline)


class V24368TargetSegmentVerifierRunnerTests(unittest.TestCase):
    def run_case(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = Clock()
        model, search = clients(output, clock, deadline=300)
        outcome = run_v24368_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        return outcome, model, search

    def test_two_search_eight_plus_two_fetch_model_and_entropy_equations_close(self) -> None:
        outcome, model, search = self.run_case()
        envelope = build_envelope(outcome)
        validate_envelope(envelope)
        validate_observed_bundle(
            envelope,
            model_slot_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_single_shot_receipt=outcome.search_single_shot_receipt,
            expected_cap=2,
        )
        result = outcome.result
        legacy = result["parent_result"]
        runtime = result["target_segment_verifier_receipt"]
        discovery = legacy["two_batch_discovery_receipt"]
        self.assertEqual(discovery["discovery_batch_count"], 2)
        self.assertEqual(discovery["provider_search_call_count"], 2)
        self.assertEqual(outcome.transport_health["hosted_search_attempts"], 2)
        self.assertEqual(
            outcome.search_single_shot_receipt["recursive_split_requests"], 0
        )
        self.assertEqual(runtime["parent_fetch_calls"], 8)
        self.assertEqual(runtime["hidden_verifier_fetch_calls"], 2)
        self.assertEqual(runtime["total_fetch_calls"], 10)
        self.assertEqual(outcome.transport_health["hard_fetch_helper_calls"], 10)
        self.assertEqual(outcome.model_slot_receipt["acquisitions"], 3)
        self.assertEqual(runtime["parent_model_requests"], 3)
        self.assertEqual(model.acquisitions, 3)
        self.assertEqual(search.fetch_invocations, 3)
        self.assertGreater(
            runtime["selected_proposal_conditional_entropy_reduction_nats"], 0
        )
        self.assertGreater(runtime["utility_aligned_entropy_credit_nats"], 0)

    def test_independent_receipt_and_private_replay_drift_are_rejected(self) -> None:
        outcome, _, _ = self.run_case()
        envelope = build_envelope(outcome)
        drifted = copy.deepcopy(outcome.transport_health)
        drifted["hard_fetch_helper_calls"] += 1
        with self.assertRaises(ValueError):
            validate_observed_bundle(
                envelope,
                model_slot_receipt=outcome.model_slot_receipt,
                transport_health=drifted,
                search_single_shot_receipt=outcome.search_single_shot_receipt,
                expected_cap=2,
            )

        split = copy.deepcopy(outcome.search_single_shot_receipt)
        split["recursive_split_requests"] = 1
        with self.assertRaises(ValueError):
            validate_observed_bundle(
                envelope,
                model_slot_receipt=outcome.model_slot_receipt,
                transport_health=outcome.transport_health,
                search_single_shot_receipt=split,
                expected_cap=2,
            )

        altered = copy.deepcopy(envelope)
        catalog = altered["result"]["private_replay_state"][
            "target_segment_utility_catalog"
        ]
        catalog["verification_records"][0]["candidate_value"] += " tamper"
        catalog.pop("catalog_payload_sha256")
        catalog["catalog_payload_sha256"] = payload_sha256(catalog)
        result = altered["result"]
        result.pop("result_sha256")
        result["result_sha256"] = payload_sha256(result)
        altered.pop("envelope_payload_sha256")
        altered["envelope_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_envelope(altered)

    def test_privileged_input_is_rejected_before_effect(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = Clock()
        model, search = clients(output, clock, deadline=300)
        with self.assertRaises(ValueError):
            run_v24368_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
        self.assertEqual(model.acquisitions, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)


if __name__ == "__main__":
    unittest.main()
