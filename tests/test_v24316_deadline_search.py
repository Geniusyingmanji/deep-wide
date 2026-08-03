from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.clients import SearchRequestError  # noqa: E402
from deepwide_agent.v24316_deadline_search import (  # noqa: E402
    DeadlineAwareNativeSearchClient,
    validate_transport_health,
)


class Clock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += float(seconds)


def client(clock: Clock, *, deadline: float = 110.0, popen=None):
    kwargs = {}
    if popen is not None:
        kwargs["popen"] = popen
    return DeadlineAwareNativeSearchClient(
        "http://unused/responses",
        "model",
        timeout=180,
        max_retries=2,
        fetch_pages=False,
        max_workers=1,
        hard_fetch_deadline_seconds=25,
        absolute_deadline=deadline,
        cleanup_reserve_seconds=2.0,
        minimum_attempt_seconds=0.05,
        monotonic=clock,
        sleeper=clock.sleep,
        **kwargs,
    )


class DeadlineSearchTests(unittest.TestCase):
    def test_successful_hosted_request_preserves_native_payload_and_accounting(self) -> None:
        clock = Clock()

        class Response:
            status_code = 200
            headers = {}

            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "usage": {
                        "input_tokens": 11,
                        "output_tokens": 7,
                        "total_tokens": 18,
                    },
                    "output": [
                        {
                            "type": "web_search_call",
                            "id": "visible-call",
                            "status": "completed",
                            "action": {
                                "type": "search",
                                "query": "visible synthetic query",
                                "sources": [],
                            },
                        }
                    ],
                }

        class Session:
            def post(self, *args, timeout, **kwargs):
                del args, kwargs
                self.timeout = timeout
                return Response()

        session = Session()
        target = client(clock)
        target._thread_local.session = session
        payload = target._request(["visible synthetic query"])
        self.assertEqual(payload["usage"]["total_tokens"], 18)
        self.assertEqual(session.timeout, 8.0)
        self.assertEqual(target.calls, 1)
        self.assertEqual(target.tool_calls, 1)
        self.assertEqual(target.total_tokens, 18)
        self.assertEqual(target.hosted_search_attempts, 1)
        self.assertEqual(target.hosted_search_deadline_failures, 0)

    def test_hosted_request_timeout_is_clamped_to_remaining_effect_window(self) -> None:
        clock = Clock()
        seen: list[float] = []

        class Session:
            def post(self, *args, timeout, **kwargs):
                del args, kwargs
                seen.append(float(timeout))
                clock.sleep(float(timeout))
                raise requests.Timeout("synthetic")

        target = client(clock)
        target._thread_local.session = Session()
        with self.assertRaisesRegex(SearchRequestError, "shared task deadline"):
            target._request(["visible synthetic query"])
        self.assertEqual(seen, [8.0])
        self.assertEqual(target.hosted_search_attempts, 1)
        self.assertEqual(target.hosted_search_deadline_failures, 1)
        self.assertTrue(target.transport_health()["deadline_exhausted"])

    def test_retry_after_sleep_cannot_cross_cleanup_reserve(self) -> None:
        clock = Clock()
        seen: list[float] = []

        class Response:
            status_code = 429
            headers = {"Retry-After": "100"}

        class Session:
            def post(self, *args, timeout, **kwargs):
                del args, kwargs
                seen.append(float(timeout))
                return Response()

        target = client(clock)
        target._thread_local.session = Session()
        with self.assertRaises(SearchRequestError):
            target._request(["visible synthetic query"])
        self.assertEqual(len(seen), 1)
        self.assertEqual(clock.value, 108.0)
        self.assertEqual(target.hosted_search_deadline_failures, 1)

    def test_fetch_helper_timeout_is_clamped_to_same_deadline(self) -> None:
        clock = Clock(105.0)

        class Process:
            pid = 123456789
            returncode = None
            timeout = None

            def communicate(self, value, timeout=None):
                del value
                self.timeout = timeout
                raise subprocess.TimeoutExpired("helper", timeout)

            def wait(self, timeout=None):
                del timeout
                self.returncode = -15
                return self.returncode

        process = Process()
        target = client(clock, popen=lambda *args, **kwargs: process)
        with mock.patch("os.killpg") as killpg:
            result = target._fetch_url("https://example.com/visible")
        self.assertEqual(process.timeout, 3.0)
        self.assertEqual(result["status"], "hard_deadline_exceeded")
        self.assertEqual(target.hard_fetch_deadline_failures, 1)
        killpg.assert_called_once()

    def test_fetch_timeout_is_recomputed_after_process_launch(self) -> None:
        clock = Clock(105.0)

        class Process:
            pid = 123456789
            returncode = None
            timeout = None

            def communicate(self, value, timeout=None):
                del value
                self.timeout = timeout
                raise subprocess.TimeoutExpired("helper", timeout)

            def wait(self, timeout=None):
                del timeout
                self.returncode = -15
                return self.returncode

        process = Process()

        def launch(*args, **kwargs):
            del args, kwargs
            clock.sleep(1.25)
            return process

        target = client(clock, popen=launch)
        with mock.patch("os.killpg"):
            result = target._fetch_url("https://example.com/visible")
        self.assertEqual(process.timeout, 1.75)
        self.assertEqual(result["status"], "hard_deadline_exceeded")

    def test_no_fetch_process_is_launched_inside_cleanup_reserve(self) -> None:
        clock = Clock(108.0)
        target = client(clock, popen=mock.Mock())
        result = target._fetch_url("https://example.com/visible")
        self.assertEqual(result["status"], "task_deadline_exhausted")
        target._fetch_popen.assert_not_called()
        self.assertEqual(target.hard_fetch_deadline_failures, 0)
        self.assertEqual(target.fetch_deadline_rejections, 1)
        self.assertEqual(target.transport_health()["fetch_deadline_rejections"], 1)

    def test_transport_health_is_fixed_and_content_free(self) -> None:
        value = validate_transport_health(
            {
                "hosted_search_attempts": 2,
                "hosted_search_deadline_failures": 1,
                "hard_fetch_helper_calls": 3,
                "hard_fetch_deadline_failures": 1,
                "fetch_deadline_rejections": 1,
                "fetch_helper_failures": 1,
                "deadline_exhausted": False,
            }
        )
        self.assertEqual(value["hosted_search_attempts"], 2)
        altered = dict(value)
        altered["question_type"] = "forbidden"
        with self.assertRaises(ValueError):
            validate_transport_health(altered)


if __name__ == "__main__":
    unittest.main()
