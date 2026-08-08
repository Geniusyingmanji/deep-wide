from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24913_cap_bound_long_page_fetch import (  # noqa: E402
    CapBoundLongPageSearchClient,
    HELPER,
    PAGE_CHARACTER_CAP,
    validate_fetch_result,
    validate_policy,
    validate_search_class,
)


class Clock:
    def __init__(self, value: float = 100.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


class Process:
    def __init__(self, payload: dict, *, returncode: int = 0) -> None:
        self.pid = 123456789
        self.returncode = returncode
        self.payload = payload
        self.command = None

    def communicate(self, value: str, timeout: float | None = None):
        del value, timeout
        return json.dumps(self.payload), ""

    def wait(self, timeout: float | None = None):
        del timeout
        return self.returncode


def client(process: Process, *, page_chars: int = 12_000):
    def launch(command, **kwargs):
        del kwargs
        process.command = command
        return process

    return CapBoundLongPageSearchClient(
        "http://127.0.0.1:9878/responses",
        "gpt-5.6-sol",
        timeout=65,
        max_retries=2,
        fetch_pages=False,
        fetch_workers=1,
        fetch_timeout=20,
        max_page_chars=page_chars,
        hard_fetch_deadline_seconds=25,
        absolute_deadline=200.0,
        cleanup_reserve_seconds=5.0,
        minimum_attempt_seconds=0.05,
        monotonic=Clock(),
        long_page_fetch_popen=launch,
    )


class V24913CapBoundLongPageFetchTests(unittest.TestCase):
    def test_validator_accepts_12k_and_rejects_12k_plus_one(self) -> None:
        value = {"status": "ok", "url": "", "title": "", "text": "x" * 12_000, "links": []}
        self.assertEqual(len(validate_fetch_result(value)["text"]), 12_000)
        value["text"] += "x"
        with self.assertRaises(ValueError):
            validate_fetch_result(value)

    def test_cap_is_required_at_construction(self) -> None:
        with self.assertRaises(ValueError):
            client(Process({}), page_chars=5_000)

    def test_fetch_accepts_content_beyond_legacy_boundary(self) -> None:
        process = Process(
            {
                "status": "ok",
                "url": "https://example.com/data",
                "title": "Data",
                "text": "x" * 12_000,
                "links": [],
            }
        )
        target = client(process)
        result = target._fetch_url("https://example.com/data")
        self.assertEqual(len(result["text"]), 12_000)
        self.assertEqual(Path(process.command[-1]).resolve(), HELPER.resolve())
        self.assertEqual(target.fetch_calls, 1)
        self.assertEqual(target.hard_fetch_helper_calls, 1)
        self.assertEqual(target.fetch_helper_failures, 0)

    def test_oversized_helper_result_fails_closed(self) -> None:
        process = Process(
            {
                "status": "ok",
                "url": "https://example.com/data",
                "title": "Data",
                "text": "x" * 12_001,
                "links": [],
            }
        )
        target = client(process)
        result = target._fetch_url("https://example.com/data")
        self.assertEqual(result["status"], "helper_invalid_result")
        self.assertEqual(target.fetch_helper_failures, 1)

    def test_timeout_remains_hard_bounded(self) -> None:
        class SlowProcess(Process):
            def communicate(self, value, timeout=None):
                del value
                raise subprocess.TimeoutExpired("helper", timeout)

        process = SlowProcess({})
        target = client(process)
        target._terminate_group = lambda _process: None
        result = target._fetch_url("https://example.com/data")
        self.assertEqual(result["status"], "hard_deadline_exceeded")
        self.assertEqual(target.hard_fetch_deadline_failures, 1)

    def test_search_class_and_policy_are_frozen(self) -> None:
        validate_search_class()
        policy = validate_policy()
        self.assertEqual(policy["page_character_cap"], PAGE_CHARACTER_CAP)
        self.assertFalse(policy["additional_search_fetch_or_model_call"])
        self.assertFalse(
            policy["benchmark_label_mapping_gold_evaluator_score_reward_read"]
        )


if __name__ == "__main__":
    unittest.main()
