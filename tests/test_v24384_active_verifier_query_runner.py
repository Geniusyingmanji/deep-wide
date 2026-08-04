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
from deepwide_agent.v24384_active_verifier_query_runner import (  # noqa: E402
    ActiveVerifierDeadlineAwareNativeSearchClient,
    build_envelope,
    run_v24384_task,
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


class DeadlineSearch(ActiveVerifierDeadlineAwareNativeSearchClient):
    def __init__(
        self, clock: Clock, *, deadline: float, retry_first: bool = False
    ):
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
        self.retry_first = retry_first

    def _request(self, queries):  # type: ignore[override]
        self.request_invocations += 1
        if self.retry_first and self.request_invocations == 1:
            self._increment("hosted_search_attempts")
            self._increment("calls")
        self._increment("hosted_search_attempts")
        self._increment("calls")
        self._increment("tool_calls")
        if self.request_invocations <= 2:
            prefix = "wavea" if self.request_invocations == 1 else "waveb"
            sources = [
                {
                    "type": "web_source",
                    "url": f"https://{prefix}{index}.example/item/{index}",
                    "title": f"proposal {queries[(index - 1) % len(queries)]}",
                }
                for index in range(1, 9)
            ]
        else:
            sources = [
                {
                    "type": "web_source",
                    "url": "https://active-alpha.example/record",
                    "title": "Alpha official Founding year 2025",
                },
                {
                    "type": "web_source",
                    "url": "https://active-beta.example/record",
                    "title": "Beta official Founding year 2024",
                },
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
        active = self.fetch_invocations == 3
        content = (
            f"Alpha was founded in 2025, while Beta was founded in 2024. {HIDDEN_MARKER}"
            if active
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


def clients(
    output: Path, clock: Clock, *, deadline: float, retry_first: bool = False
):
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
    return model, DeadlineSearch(
        clock, deadline=deadline, retry_first=retry_first
    )


class V24384ActiveVerifierQueryRunnerTests(unittest.TestCase):
    def run_case(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = Clock()
        model, search = clients(output, clock, deadline=300)
        outcome = run_v24384_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        return outcome, model, search

    def test_transport_model_and_active_effect_equations_close(self) -> None:
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
        receipt = outcome.result["active_verifier_receipt"]
        self.assertEqual(receipt["total_search_batch_count"], 3)
        self.assertEqual(receipt["total_logical_query_count"], 6)
        self.assertEqual(receipt["total_fetch_calls"], 10)
        self.assertEqual(outcome.transport_health["hosted_search_attempts"], 3)
        self.assertEqual(outcome.transport_health["hard_fetch_helper_calls"], 10)
        self.assertEqual(outcome.search_single_shot_receipt["multi_query_chunks"], 3)
        self.assertEqual(outcome.search_single_shot_receipt["recursive_split_requests"], 0)
        self.assertEqual(outcome.model_slot_receipt["acquisitions"], 3)
        self.assertEqual(model.acquisitions, 3)
        self.assertEqual(search.fetch_invocations, 3)

    def test_independent_receipt_and_private_replay_drift_rejected(self) -> None:
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

        altered = copy.deepcopy(envelope)
        altered["result"]["private_replay_state"]["active_target_state"][
            "active_queries"
        ][0] += " tamper"
        result = altered["result"]
        result.pop("result_sha256")
        result["result_sha256"] = payload_sha256(result)
        altered.pop("envelope_payload_sha256")
        altered["envelope_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_envelope(altered)

    def test_budgeted_provider_retry_is_not_a_new_logical_batch(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = Clock()
        model, search = clients(
            output, clock, deadline=300, retry_first=True
        )
        outcome = run_v24384_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        envelope = build_envelope(outcome)
        validate_envelope(envelope)
        receipt = outcome.result["active_verifier_receipt"]
        self.assertEqual(receipt["total_search_batch_count"], 3)
        self.assertEqual(receipt["total_provider_search_calls"], 4)
        self.assertEqual(outcome.transport_health["hosted_search_attempts"], 4)
        self.assertEqual(outcome.search_single_shot_receipt["multi_query_chunks"], 3)

    def test_privileged_input_rejected_before_effect(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = Clock()
        model, search = clients(output, clock, deadline=300)
        with self.assertRaises(ValueError):
            run_v24384_task(
                {**TASK, "split": "forbidden"},
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
