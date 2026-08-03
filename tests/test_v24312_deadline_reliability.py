from __future__ import annotations

import fcntl
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import ModelRequestError  # noqa: E402
from deepwide_agent.v24312_deadline_reliability import (  # noqa: E402
    DeadlineAwareGlobalModelSlotLimiter,
    DeadlineAwareResponsesClient,
    run_v24312_total_task,
    validate_receipt,
)


def _slots(root: Path, cap: int = 2) -> Path:
    value = root / "slots"
    value.mkdir()
    for index in range(1, cap + 1):
        (value / f"slot_{index:02d}.lock").write_text(
            json.dumps({"slot": index}) + "\n", encoding="utf-8"
        )
    return value


class _Response:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers: dict[str, str] = {}

    def json(self) -> dict:
        return self._payload


class _Session:
    def __init__(self, function):
        self.function = function

    def post(self, *args, **kwargs):
        return self.function(*args, **kwargs)


class DeadlineReliabilityTests(unittest.TestCase):
    def test_slot_starvation_fails_inside_child_before_cleanup_reserve(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            slots = _slots(output, cap=1)
            holder = open(slots / "slot_01.lock", "r+", encoding="utf-8")
            fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                inner = SimpleNamespace(deadline_failures=0)
                limiter = DeadlineAwareGlobalModelSlotLimiter(
                    inner,
                    slot_directory=slots,
                    output_root=output,
                    absolute_deadline=time.monotonic() + 0.18,
                    cleanup_reserve_seconds=0.08,
                    minimum_attempt_seconds=0.02,
                    slot_cap=1,
                    poll_seconds=0.005,
                )
                started = time.monotonic()
                with self.assertRaises(ModelRequestError) as raised:
                    limiter.complete("secret", "secret", max_output_tokens=1)
                elapsed = time.monotonic() - started
                self.assertLess(elapsed, 0.16)
                self.assertEqual(
                    raised.exception.model_traces[0]["error_type"],
                    "model_slot_deadline_exhausted",
                )
                receipt = limiter.receipt()
                validate_receipt(receipt, expected_cap=1, expected_acquisitions=0)
                self.assertEqual(receipt["slot_timeouts"], 1)
                self.assertGreaterEqual(receipt["remaining_seconds_at_receipt"], 0.05)
            finally:
                fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
                holder.close()

    def test_cap_two_releases_waiters_without_exceeding_two(self) -> None:
        active = 0
        maximum = 0
        lock = threading.Lock()
        barrier = threading.Barrier(5)

        class Inner:
            deadline_failures = 0

            def complete(self, *_args, **_kwargs):
                nonlocal active, maximum
                with lock:
                    active += 1
                    maximum = max(maximum, active)
                try:
                    time.sleep(0.04)
                    return SimpleNamespace(text="ok")
                finally:
                    with lock:
                        active -= 1

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            slots = _slots(output, cap=2)
            clients = [
                DeadlineAwareGlobalModelSlotLimiter(
                    Inner(),
                    slot_directory=slots,
                    output_root=output,
                    absolute_deadline=time.monotonic() + 1.0,
                    cleanup_reserve_seconds=0.1,
                    minimum_attempt_seconds=0.01,
                    slot_cap=2,
                    poll_seconds=0.002,
                )
                for _ in range(4)
            ]
            errors: list[BaseException] = []

            def run(client):
                try:
                    barrier.wait()
                    client.complete("s", "u", max_output_tokens=1)
                except BaseException as error:  # pragma: no cover - diagnostic
                    errors.append(error)

            threads = [threading.Thread(target=run, args=(client,)) for client in clients]
            for thread in threads:
                thread.start()
            barrier.wait()
            for thread in threads:
                thread.join(timeout=2)
            self.assertFalse(errors)
            self.assertEqual(maximum, 2)
            self.assertEqual(sum(client.acquisitions for client in clients), 4)

    def test_provider_timeout_is_clamped_to_remaining_effect_window(self) -> None:
        observed: list[float] = []

        def post(*_args, **kwargs):
            observed.append(float(kwargs["timeout"]))
            return _Response(
                {
                    "id": "x",
                    "output": [
                        {
                            "type": "message",
                            "content": [{"type": "output_text", "text": "ok"}],
                        }
                    ],
                    "usage": {},
                }
            )

        client = DeadlineAwareResponsesClient(
            "http://invalid.local/responses",
            "synthetic",
            timeout=180,
            max_retries=2,
            absolute_deadline=time.monotonic() + 0.22,
            cleanup_reserve_seconds=0.08,
            minimum_attempt_seconds=0.01,
        )
        client._thread_local.session = _Session(post)
        result = client.complete("s", "u", max_output_tokens=1)
        self.assertEqual(result.text, "ok")
        self.assertEqual(len(observed), 1)
        self.assertGreater(observed[0], 0)
        self.assertLess(observed[0], 0.16)

    def test_slow_provider_returns_content_free_failure_before_parent_deadline(self) -> None:
        def post(*_args, **kwargs):
            time.sleep(float(kwargs["timeout"]) + 0.005)
            raise requests.Timeout()

        import requests

        client = DeadlineAwareResponsesClient(
            "http://invalid.local/responses",
            "synthetic",
            timeout=180,
            max_retries=2,
            absolute_deadline=time.monotonic() + 0.20,
            cleanup_reserve_seconds=0.08,
            minimum_attempt_seconds=0.01,
        )
        client._thread_local.session = _Session(post)
        started = time.monotonic()
        with mock.patch(
            "deepwide_agent.v24312_deadline_reliability.random.random",
            return_value=0.0,
        ):
            with self.assertRaises(ModelRequestError) as raised:
                client.complete("secret-system", "secret-user", max_output_tokens=1)
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.18)
        self.assertEqual(
            raised.exception.model_traces[0]["error_type"],
            "task_deadline_exhausted",
        )
        self.assertNotIn("secret", json.dumps(raised.exception.model_traces))
        self.assertEqual(client.deadline_failures, 1)

    def test_no_provider_attempt_when_only_cleanup_reserve_remains(self) -> None:
        calls = 0

        def post(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            raise AssertionError("provider must not be called")

        client = DeadlineAwareResponsesClient(
            "http://invalid.local/responses",
            "synthetic",
            timeout=180,
            max_retries=2,
            absolute_deadline=time.monotonic() + 0.04,
            cleanup_reserve_seconds=0.05,
            minimum_attempt_seconds=0.01,
        )
        client._thread_local.session = _Session(post)
        with self.assertRaises(ModelRequestError) as raised:
            client.complete("s", "u", max_output_tokens=1)
        self.assertEqual(calls, 0)
        self.assertEqual(client.attempts, 0)
        self.assertEqual(
            raised.exception.model_traces[0]["error_type"],
            "task_deadline_exhausted",
        )

    def test_receipt_rejects_resealed_forbidden_field(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            output = Path(directory)
            slots = _slots(output, cap=1)

            class Inner:
                deadline_failures = 0

                def complete(self, *_args, **_kwargs):
                    return SimpleNamespace(text="ok")

            limiter = DeadlineAwareGlobalModelSlotLimiter(
                Inner(),
                slot_directory=slots,
                output_root=output,
                absolute_deadline=time.monotonic() + 1,
                cleanup_reserve_seconds=0.1,
                minimum_attempt_seconds=0.01,
                slot_cap=1,
            )
            limiter.complete("s", "u", max_output_tokens=1)
            receipt = limiter.receipt()
            receipt["question"] = "forbidden"
            receipt.pop("receipt_payload_sha256")
            from deepwide_agent.v24263_global_model_limiter import payload_sha256

            receipt["receipt_payload_sha256"] = payload_sha256(receipt)
            with self.assertRaisesRegex(ValueError, "receipt drifted"):
                validate_receipt(receipt, expected_cap=1)

    def test_outer_projection_failure_is_converted_to_total_fallback(self) -> None:
        from deepwide_agent.v24257_score_first_runtime import ScoreFirstLimits
        from deepwide_agent.v24272_two_wave_entropy_voc import TwoWavePolicy
        from deepwide_agent.v24310_paired_dev_runtime import RECEIPT_FIELD

        class Counter:
            requests = 0
            attempts = 0
            input_tokens = 0
            output_tokens = 0
            total_tokens = 0

        class Search:
            calls = failures = tool_calls = fetch_calls = fetch_failures = 0
            input_tokens = output_tokens = total_tokens = 0

        limits = ScoreFirstLimits(
            wall_seconds=120,
            model_calls=3,
            search_queries=4,
            fetch_targets=10,
            search_results_per_query=3,
            evidence_chars=60_000,
            page_chars=5_000,
        )
        visible = {
            "opaque_id": "task_0123456789abcdef01234567",
            "question": "Return columns: A, B.",
        }
        with mock.patch(
            "deepwide_agent.v24312_deadline_reliability.run_v24310_task",
            side_effect=lambda *_args, **_kwargs: self._effect_then_fail(
                _kwargs["model"]
            ),
        ):
            result = run_v24312_total_task(
                visible,
                arm="baseline",
                model=Counter(),
                search=Search(),
                limits=limits,
                two_wave_policy=TwoWavePolicy(),
            )
        self.assertEqual(result["completion_kind"], "worker_failure_fallback")
        self.assertEqual(result["failures"][0]["type"], "ValidationError")
        self.assertEqual(result["cost"]["model"]["requests"], 1)
        self.assertEqual(result[RECEIPT_FIELD]["total_effects_admitted"], 1)
        self.assertNotIn("must never", json.dumps(result))

    @staticmethod
    def _effect_then_fail(model) -> None:
        model.requests += 1
        model.attempts += 2
        raise ValueError("must never be persisted")


if __name__ == "__main__":
    unittest.main()
