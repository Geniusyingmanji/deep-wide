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
from deepwide_agent.v24316_deadline_search import DeadlineAwareNativeSearchClient  # noqa: E402
from deepwide_agent.v24657_runner_integration import (  # noqa: E402
    build_envelope,
    run_v24657_task,
    validate_envelope,
    validate_observed_bundle,
)
from test_v24655_unknown_cell_targeted_runtime import (  # noqa: E402
    Model,
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


class DeadlineSearch(DeadlineAwareNativeSearchClient):
    def __init__(self, clock: Clock, *, deadline: float) -> None:
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
        self.search_invocations = 0

    def search_many(self, queries, **kwargs):
        del kwargs
        values = list(queries)
        self.search_invocations += 1
        self._increment("hosted_search_attempts")
        self._increment("calls")
        self._increment("tool_calls")
        targeted = self.search_invocations > 1
        count = 4 if targeted else 6
        prefix = "target" if targeted else "generic"
        return [
            {
                "query": values[0] if values else "",
                "answer": "",
                "results": [
                    {
                        "title": f"{prefix} source {index}",
                        "url": f"https://{prefix}-{index}.example/record",
                        "fetch_url": f"https://{prefix}-{index}.example/record",
                    }
                    for index in range(count)
                ],
                "error": None,
            }
        ]

    def fetch_urls(self, requests_):
        values = list(requests_)
        self._increment("fetch_calls", len(values))
        self._increment("hard_fetch_helper_calls", len(values))
        targeted = bool(values and "target-" in values[0]["url"])
        content = (
            "Alpha Phone official record: Release Date 2024-09-20."
            if targeted
            else "Generic product history without the requested release date."
        )
        return [
            {
                "query": request.get("query", ""),
                "answer": "",
                "results": [
                    {
                        "title": request.get("title", ""),
                        "url": request["url"],
                        "raw_content": content,
                    }
                ],
                "error": None,
            }
            for request in values
        ]


def _slots(root: Path, cap: int = 8) -> Path:
    value = root / "slots"
    value.mkdir()
    for index in range(1, cap + 1):
        (value / f"slot_{index:02d}.lock").write_text(
            json.dumps({"slot": index}) + "\n", encoding="utf-8"
        )
    return value


def synthetic_outcome():
    temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
    output = Path(temporary.name)
    clock = Clock()
    model = build_deadline_model(
        url="http://unused.invalid/responses",
        model_name="synthetic",
        reasoning_effort="low",
        service_tier="",
        static_timeout_seconds=180,
        max_retries=2,
        slot_directory=_slots(output),
        output_root=output,
        slot_cap=8,
        pool_id=POOL_ID,
        absolute_deadline=400,
        cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.01,
        monotonic=clock,
        sleeper=clock.sleep,
        inner=Model(),
    )
    search = DeadlineSearch(clock, deadline=400)
    outcome = run_v24657_task(
        TASK,
        model=model,
        search=search,
        limits=limits(),
        monotonic=clock,
    )
    return temporary, outcome


class V24657RunnerIntegrationTests(unittest.TestCase):
    def test_unknown_target_admission_closes_model_fetch_and_envelope_equations(
        self,
    ) -> None:
        temporary, outcome = synthetic_outcome()
        self.addCleanup(temporary.cleanup)
        envelope = build_envelope(outcome)
        validate_envelope(envelope)
        validate_observed_bundle(
            envelope,
            model_slot_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            expected_cap=8,
        )
        receipt = outcome.result["receipt"]
        self.assertEqual(outcome.model_slot_receipt["acquisitions"], 3)
        self.assertEqual(outcome.transport_health["hard_fetch_helper_calls"], 10)
        self.assertEqual(receipt["admitted_cell_change_count"], 1)
        self.assertFalse(receipt["positive_task_credit_assigned"])

    def test_independent_model_or_transport_receipt_drift_is_rejected(self) -> None:
        temporary, outcome = synthetic_outcome()
        self.addCleanup(temporary.cleanup)
        envelope = build_envelope(outcome)
        model = copy.deepcopy(outcome.model_slot_receipt)
        model["acquisitions"] += 1
        with self.assertRaises(ValueError):
            validate_observed_bundle(
                envelope,
                model_slot_receipt=model,
                transport_health=outcome.transport_health,
                expected_cap=8,
            )
        transport = copy.deepcopy(outcome.transport_health)
        transport["hard_fetch_helper_calls"] += 1
        with self.assertRaises(ValueError):
            validate_observed_bundle(
                envelope,
                model_slot_receipt=outcome.model_slot_receipt,
                transport_health=transport,
                expected_cap=8,
            )

    def test_envelope_has_no_evaluator_or_positive_credit_capability(self) -> None:
        temporary, outcome = synthetic_outcome()
        self.addCleanup(temporary.cleanup)
        envelope = build_envelope(outcome)
        self.assertFalse(
            envelope[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )
        self.assertFalse(envelope["benchmark_launch_or_evaluator_authorized"])
        altered = copy.deepcopy(envelope)
        altered["benchmark_launch_or_evaluator_authorized"] = True
        with self.assertRaises(ValueError):
            validate_envelope(altered)


if __name__ == "__main__":
    unittest.main()
