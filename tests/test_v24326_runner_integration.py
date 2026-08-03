from __future__ import annotations

import fcntl
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import POOL_ID  # noqa: E402
from deepwide_agent.v24313_runner_integration import build_deadline_model  # noqa: E402
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
)
from deepwide_agent.v24326_runner_integration import (  # noqa: E402
    build_envelope,
    run_v24326_task,
    validate_cross_artifacts,
    validate_envelope,
)
from test_v24325_shared_prefix_revision_runtime import (  # noqa: E402
    BASELINE_UNKNOWN,
    PLAN,
    TASK,
    candidate,
    limits,
    proposal,
)


class Clock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += float(seconds)


class InnerModel:
    def __init__(self) -> None:
        self.values = [
            PLAN,
            BASELINE_UNKNOWN,
            proposal(candidate("2025"), ["R0001", "R0002"]),
        ]
        self.requests = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self.deadline_failures = 0

    def complete(self, *_args, **_kwargs):
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return SimpleNamespace(text=self.values.pop(0))


class SyntheticDeadlineSearch(DeadlineAwareNativeSearchClient):
    def __init__(self, clock: Clock, *, deadline: float, fail_reserve: bool = False):
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
        self.fail_reserve = fail_reserve

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
        if self.fetch_invocations == 2 and self.fail_reserve:
            self._increment("fetch_failures", len(values))
            self._increment("fetch_helper_failures", len(values))
            raise RuntimeError("private reserve failure")
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
                            "Independent official record: Alpha year is 2025."
                            if reserve
                            else "Independent core record about Alpha."
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


def clients(output: Path, clock: Clock, *, deadline: float, fail_reserve=False):
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
        inner=InnerModel(),
    )
    search = SyntheticDeadlineSearch(
        clock, deadline=deadline, fail_reserve=fail_reserve
    )
    return model, search


class V24326RunnerIntegrationTests(unittest.TestCase):
    def test_success_closes_model_and_fetch_cross_artifact_equations(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock = Clock()
            model, search = clients(output, clock, deadline=300)
            outcome = run_v24326_task(
                TASK,
                model=model,
                search=search,
                limits=limits(),
                monotonic=clock,
            )
            envelope = build_envelope(outcome)
            validate_envelope(envelope)
            receipt = outcome.result["shared_prefix_revision_receipt"]
            self.assertEqual(receipt["logical_model_admissions"], 3)
            self.assertEqual(receipt["provider_model_requests"], 3)
            self.assertEqual(outcome.model_slot_receipt["acquisitions"], 3)
            self.assertEqual(outcome.model_slot_receipt["slot_timeouts"], 0)
            self.assertEqual(outcome.result["cost"]["search"]["fetch_calls"], 10)
            self.assertEqual(outcome.transport_health["hard_fetch_helper_calls"], 10)

    def test_slot_deadline_rejections_are_complete_identity_result(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock = Clock()
            model, search = clients(output, clock, deadline=100.10)
            handles = [
                open(output / "slots" / f"slot_{index:02d}.lock", "r+", encoding="utf-8")
                for index in range(1, 3)
            ]
            for handle in handles:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                outcome = run_v24326_task(
                    TASK,
                    model=model,
                    search=search,
                    limits=limits(),
                    monotonic=clock,
                )
            finally:
                for handle in handles:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    handle.close()
            receipt = outcome.result["shared_prefix_revision_receipt"]
            self.assertGreater(receipt["pre_provider_model_rejections"], 0)
            self.assertEqual(
                receipt["pre_provider_model_rejections"],
                outcome.model_slot_receipt["slot_timeouts"],
            )
            self.assertTrue(receipt["candidate_identity_handoff"])

    def test_reserve_transport_failure_is_complete_identity_result(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock = Clock()
            model, search = clients(
                output, clock, deadline=300, fail_reserve=True
            )
            outcome = run_v24326_task(
                TASK,
                model=model,
                search=search,
                limits=limits(),
                monotonic=clock,
            )
            receipt = outcome.result["shared_prefix_revision_receipt"]
            self.assertTrue(receipt["candidate_identity_handoff"])
            self.assertEqual(receipt["admitted_cell_changes"], 0)
            self.assertEqual(
                receipt["recoverable_failures"],
                [{"stage": "reserve_fetch", "type": "RuntimeError"}],
            )
            self.assertEqual(outcome.transport_health["fetch_helper_failures"], 3)

    def test_deadline_mismatch_and_resealed_cross_artifact_drift_fail(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock = Clock()
            model, search = clients(output, clock, deadline=300)
            search.absolute_deadline = 301
            with self.assertRaises(ValueError):
                run_v24326_task(
                    TASK,
                    model=model,
                    search=search,
                    limits=limits(),
                    monotonic=clock,
                )

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            clock = Clock()
            model, search = clients(output, clock, deadline=300)
            outcome = run_v24326_task(
                TASK,
                model=model,
                search=search,
                limits=limits(),
                monotonic=clock,
            )
            altered = dict(outcome.model_slot_receipt)
            altered["slot_timeouts"] += 1
            altered.pop("receipt_payload_sha256")
            from deepwide_agent.v24263_global_model_limiter import payload_sha256

            altered["receipt_payload_sha256"] = payload_sha256(altered)
            with self.assertRaises(ValueError):
                validate_cross_artifacts(
                    outcome.result,
                    model_slot_receipt=altered,
                    transport_health=outcome.transport_health,
                    expected_cap=2,
                )


if __name__ == "__main__":
    unittest.main()
