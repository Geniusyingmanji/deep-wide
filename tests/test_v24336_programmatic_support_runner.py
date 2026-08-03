from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
)
from deepwide_agent.v24335_programmatic_support_runtime import (  # noqa: E402
    payload_sha256,
)
from deepwide_agent.v24336_programmatic_support_runner import (  # noqa: E402
    build_envelope,
    run_v24336_task,
    validate_envelope,
    validate_observed_bundle,
)
from test_v24335_programmatic_support_runtime import (  # noqa: E402
    AdaptiveModel,
    TASK,
    limits,
)


class Clock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += float(seconds)


class SyntheticDeadlineSearch(DeadlineAwareNativeSearchClient):
    def __init__(self, clock: Clock, *, deadline: float, eligible: bool = True):
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
        self.eligible = eligible

    def search_many(self, queries, **_kwargs):
        self._increment("hosted_search_attempts")
        self._increment("calls")
        self._increment("tool_calls")
        return [
            {
                "query": "synthetic",
                "answer": "",
                "results": [
                    {
                        "url": f"https://host{index}.example/item",
                        "fetch_url": f"https://host{index}.example/item",
                        "title": f"synthetic-{index}",
                        "content": "",
                    }
                    for index in range(1, 11)
                ],
            }
        ]

    def fetch_urls(self, requests_):
        self.fetch_invocations += 1
        values = list(requests_)
        self._increment("fetch_calls", len(values))
        self._increment("hard_fetch_helper_calls", len(values))
        reserve = self.fetch_invocations == 2
        return [
            {
                "query": "synthetic",
                "results": [
                    {
                        "url": item["url"],
                        "requested_url": item["url"],
                        "title": item["title"],
                        "raw_content": (
                            "Independent official record. Alpha Year is 2025."
                            if reserve and self.eligible
                            else "Independent core record about Alpha without the year."
                        ),
                    }
                ],
            }
            for item in values
        ]


def slots(root: Path) -> Path:
    value = root / "slots"
    value.mkdir()
    for index in range(1, 3):
        (value / f"slot_{index:02d}.lock").write_text(
            json.dumps({"slot": index}) + "\n", encoding="utf-8"
        )
    return value


def clients(output: Path, clock: Clock, *, deadline: float, eligible: bool = True):
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
        inner=AdaptiveModel(),
    )
    search = SyntheticDeadlineSearch(clock, deadline=deadline, eligible=eligible)
    return model, search


class V24336ProgrammaticSupportRunnerTests(unittest.TestCase):
    def run_case(self, *, eligible: bool = True):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = Clock()
        model, search = clients(
            output, clock, deadline=300, eligible=eligible
        )
        outcome = run_v24336_task(
            TASK,
            model=model,
            search=search,
            limits=limits(),
            monotonic=clock,
        )
        return outcome

    def test_natural_admission_closes_model_fetch_and_envelope_equations(self) -> None:
        outcome = self.run_case()
        envelope = build_envelope(outcome)
        validate_envelope(envelope)
        validate_observed_bundle(
            envelope,
            model_slot_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            expected_cap=2,
        )
        core = outcome.result["core_result"]
        support = outcome.result["support_runtime_receipt"]
        self.assertEqual(outcome.model_slot_receipt["acquisitions"], 3)
        self.assertEqual(core["cost"]["search"]["fetch_calls"], 10)
        self.assertEqual(outcome.transport_health["hard_fetch_helper_calls"], 10)
        self.assertEqual(support["admitted_cell_changes"], 1)
        self.assertFalse(support["candidate_identity_handoff"])

    def test_no_eligible_support_saves_third_model_acquisition(self) -> None:
        outcome = self.run_case(eligible=False)
        support = outcome.result["support_runtime_receipt"]
        self.assertEqual(outcome.model_slot_receipt["acquisitions"], 2)
        self.assertEqual(support["catalog_status"], "built_empty")
        self.assertTrue(support["third_model_call_skipped_no_eligible_support"])
        self.assertTrue(support["candidate_identity_handoff"])

    def test_resealed_private_catalog_tamper_fails_through_envelope(self) -> None:
        outcome = self.run_case()
        envelope = build_envelope(outcome)
        altered = copy.deepcopy(envelope)
        altered["result"]["support_runtime_private_state"]["catalog_pages"][0][
            "content"
        ] += " tamper"
        result = altered["result"]
        result.pop("result_sha256")
        result["result_sha256"] = payload_sha256(result)
        altered.pop("envelope_payload_sha256")
        altered["envelope_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_envelope(altered)

    def test_independent_receipt_drift_is_rejected(self) -> None:
        outcome = self.run_case()
        envelope = build_envelope(outcome)
        drifted = copy.deepcopy(outcome.transport_health)
        drifted["hard_fetch_helper_calls"] += 1
        with self.assertRaises(ValueError):
            validate_observed_bundle(
                envelope,
                model_slot_receipt=outcome.model_slot_receipt,
                transport_health=drifted,
                expected_cap=2,
            )


if __name__ == "__main__":
    unittest.main()
