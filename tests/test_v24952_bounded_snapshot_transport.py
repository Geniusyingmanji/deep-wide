from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24952_bounded_snapshot_transport import (  # noqa: E402
    CONNECT_TIMEOUT_SECONDS,
    MAXIMUM_ATTEMPTS,
    READ_TIMEOUT_SECONDS,
    payload_sha256,
    snapshot_request_key,
    validate_content_free_receipt,
    validate_helper_result,
)
from scripts.run_v24952_worldbank_snapshot_fetch_helper import (  # noqa: E402
    BACKOFF_SECONDS,
    fetch_snapshot_json,
)


CATALOG_URL = "https://api.worldbank.org/v2/country?format=json&per_page=400"
TARGET_URL = (
    "https://api.worldbank.org/v2/country/all/indicator/AG.LND.FRST.ZS"
    "?date=2021&format=json&per_page=400"
)


class Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        self.value += 0.01
        return self.value


class FakeResponse:
    def __init__(
        self,
        status: int,
        raw: bytes = b"",
        content_type: str = "application/json",
    ) -> None:
        self.status_code = status
        self.raw = raw
        self.headers = {"Content-Type": content_type}
        self.closed = False

    def iter_content(self, chunk_size: int):
        del chunk_size
        if self.raw:
            yield self.raw

    def close(self) -> None:
        self.closed = True


class FakeSession:
    def __init__(self, outcomes) -> None:
        self.outcomes = list(outcomes)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


def valid_raw() -> bytes:
    return json.dumps([{}, [{"id": "USA"}]]).encode()


class V24952BoundedSnapshotTransportTests(unittest.TestCase):
    def test_strict_catalog_and_indicator_shapes(self) -> None:
        self.assertEqual(snapshot_request_key(CATALOG_URL), "country_catalog")
        self.assertEqual(snapshot_request_key(TARGET_URL), "AG.LND.FRST.ZS@2021")
        for changed in (
            TARGET_URL.replace("https://", "http://"),
            TARGET_URL.replace("api.worldbank.org", "example.org"),
            TARGET_URL.replace("date=2021&format=json", "format=json&date=2021"),
            TARGET_URL + "&extra=1",
            TARGET_URL + "#fragment",
            TARGET_URL.replace("country/all", "country/USA"),
        ):
            with self.assertRaises(ValueError):
                snapshot_request_key(changed)

    def test_503_retries_then_succeeds_with_bounded_timeouts(self) -> None:
        sleeps = []
        session = FakeSession(
            [FakeResponse(503), FakeResponse(200, valid_raw())]
        )
        value = fetch_snapshot_json(
            TARGET_URL,
            session=session,
            monotonic=Clock(),
            sleeper=sleeps.append,
        )
        self.assertEqual(value["status"], "ok")
        self.assertEqual(value["attempt_count"], 2)
        self.assertEqual(sleeps, [BACKOFF_SECONDS[0]])
        self.assertTrue(
            all(call[1]["allow_redirects"] is False for call in session.calls)
        )
        self.assertTrue(
            all(
                call[1]["timeout"]
                == (CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS)
                for call in session.calls
            )
        )

    def test_timeout_exhausts_at_three_attempts(self) -> None:
        sleeps = []
        value = fetch_snapshot_json(
            TARGET_URL,
            session=FakeSession(
                [requests.Timeout("slow") for _ in range(MAXIMUM_ATTEMPTS)]
            ),
            monotonic=Clock(),
            sleeper=sleeps.append,
        )
        self.assertEqual(value["status"], "exhausted")
        self.assertEqual(value["attempt_count"], 3)
        self.assertEqual(
            [attempt["error_type"] for attempt in value["attempts"]],
            ["timeout", "timeout", "timeout"],
        )
        self.assertEqual(sleeps, list(BACKOFF_SECONDS))

    def test_redirect_invalid_json_and_non_json_fail_closed(self) -> None:
        for response, error in (
            (FakeResponse(302), "http_302"),
            (FakeResponse(200, b"not-json"), "invalid_json"),
            (FakeResponse(200, valid_raw(), "text/html"), "invalid_content_type"),
        ):
            value = fetch_snapshot_json(
                TARGET_URL, session=FakeSession([response]), monotonic=Clock()
            )
            self.assertEqual(value["status"], "exhausted")
            self.assertEqual(value["attempt_count"], 1)
            self.assertEqual(value["attempts"][0]["error_type"], error)

    def test_content_free_receipt_contains_no_url_or_body(self) -> None:
        value = fetch_snapshot_json(
            TARGET_URL,
            session=FakeSession([FakeResponse(200, valid_raw())]),
            monotonic=Clock(),
        )
        receipt = value["content_free_receipt"]
        rendered = json.dumps(receipt, sort_keys=True)
        self.assertNotIn(TARGET_URL, rendered)
        self.assertNotIn(valid_raw().decode(), rendered)
        self.assertFalse(receipt["url_or_response_content_emitted"])
        self.assertFalse(
            receipt[
                "benchmark_metadata_answer_evaluator_score_reward_or_credential_read"
            ]
        )

    def test_nested_tamper_fails_even_when_outer_seal_is_refreshed(self) -> None:
        value = fetch_snapshot_json(
            TARGET_URL,
            session=FakeSession([FakeResponse(200, valid_raw())]),
            monotonic=Clock(),
        )
        changed = copy.deepcopy(value)
        changed["content_free_receipt"]["attempt_count"] = 2
        changed.pop("result_payload_sha256")
        changed["result_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            validate_helper_result(changed)

    def test_persisted_receipt_validates_without_raw_content(self) -> None:
        value = fetch_snapshot_json(
            TARGET_URL,
            session=FakeSession([FakeResponse(200, valid_raw())]),
            monotonic=Clock(),
        )
        receipt = value["content_free_receipt"]
        self.assertEqual(validate_content_free_receipt(receipt), receipt)
        changed = copy.deepcopy(receipt)
        changed["attempts"][-1]["response_bytes"] += 1
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = payload_sha256(changed)
        with self.assertRaises(ValueError):
            validate_content_free_receipt(changed)


if __name__ == "__main__":
    unittest.main()
