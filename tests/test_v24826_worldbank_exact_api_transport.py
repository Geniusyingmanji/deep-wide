from __future__ import annotations

import copy
import json
import sys
import time
import unittest
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24686_worldbank_target_value_runtime import (  # noqa: E402
    _visible_contract,
    target_lookup_requests,
)
from deepwide_agent.v24826_worldbank_exact_api_transport import (  # noqa: E402
    WorldBankExactAPITransportSearchClient,
    exact_target_key,
    payload_sha256,
    validate_exact_transport_receipt,
    validate_helper_result,
)
from scripts.run_v24826_worldbank_exact_fetch_helper import (  # noqa: E402
    MAX_RESPONSE_BYTES,
    fetch_exact_json,
)
from tests.test_v24804_shared_prefix_budget_ladder import (  # noqa: E402
    response,
    visible_question,
)


def exact_url() -> str:
    return (
        "https://api.worldbank.org/v2/country/BTN/indicator/"
        "IT.NET.USER.ZS?date=2022&format=json&per_page=100"
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
    return response(
        "BTN", "IT.NET.USER.ZS", "2022", "88.35620117"
    ).encode()


def helper_value(url: str, raw: bytes | None = None) -> dict:
    content = raw if raw is not None else valid_raw()
    import hashlib

    attempt = {
        "attempt": 1,
        "outcome": "success",
        "http_status": 200,
        "error_type": None,
        "retryable": False,
        "elapsed_seconds": 0.1,
        "response_bytes": len(content),
        "response_sha256": hashlib.sha256(content).hexdigest(),
    }
    value = {
        "artifact_version": 1,
        "role": "v24826_worldbank_exact_fetch_result",
        "status": "ok",
        "url": url,
        "raw_content": content.decode(),
        "attempt_count": 1,
        "attempts": [attempt],
        "elapsed_seconds": 0.1,
        "response_bytes": len(content),
        "response_sha256": hashlib.sha256(content).hexdigest(),
    }
    value["result_payload_sha256"] = payload_sha256(value)
    return validate_helper_result(value)


class FakeProcess:
    def __init__(self) -> None:
        self.returncode = 0

    def communicate(self, input_text, timeout):
        self.timeout = timeout
        url = json.loads(input_text)["url"]
        return json.dumps(helper_value(url)), ""


class PopenFactory:
    def __init__(self) -> None:
        self.calls = []

    def __call__(self, command, **kwargs):
        self.calls.append((command, kwargs))
        return FakeProcess()


def client(*, popen=None):
    requests_ = target_lookup_requests(_visible_contract(visible_question()))
    return WorldBankExactAPITransportSearchClient(
        "http://127.0.0.1:9878/responses",
        "gpt-5.6-sol",
        reasoning_effort="low",
        timeout=65,
        max_retries=2,
        max_workers=1,
        batch_size=8,
        search_context_size="medium",
        max_output_tokens=7000,
        fetch_pages=False,
        fetch_workers=10,
        fetch_timeout=35,
        max_page_chars=5000,
        hard_fetch_deadline_seconds=40,
        absolute_deadline=time.monotonic() + 240,
        cleanup_reserve_seconds=5,
        minimum_attempt_seconds=0.05,
        allowed_exact_requests=requests_,
        exact_popen=popen or PopenFactory(),
    ), requests_


class V24826WorldBankExactTransportTests(unittest.TestCase):
    def test_exact_url_shape_is_strict(self) -> None:
        self.assertEqual(
            exact_target_key(exact_url()),
            "BTN|IT.NET.USER.ZS|2022",
        )
        for changed in (
            exact_url().replace("https://", "http://"),
            exact_url().replace("api.worldbank.org", "example.org"),
            exact_url().replace("date=2022&format=json", "format=json&date=2022"),
            exact_url() + "&extra=1",
            exact_url() + "#fragment",
        ):
            with self.assertRaises(ValueError):
                exact_target_key(changed)

    def test_helper_retries_503_then_succeeds_without_redirects(self) -> None:
        sleeps = []
        session = FakeSession(
            [FakeResponse(503), FakeResponse(200, valid_raw())]
        )
        value = fetch_exact_json(
            exact_url(),
            session=session,
            monotonic=Clock(),
            sleeper=sleeps.append,
        )
        self.assertEqual(value["status"], "ok")
        self.assertEqual(value["attempt_count"], 2)
        self.assertEqual(value["attempts"][0]["http_status"], 503)
        self.assertEqual(value["attempts"][1]["http_status"], 200)
        self.assertEqual(sleeps, [0.25])
        self.assertTrue(
            all(call[1]["allow_redirects"] is False for call in session.calls)
        )

    def test_helper_timeout_exhausts_at_three_attempts(self) -> None:
        sleeps = []
        session = FakeSession(
            [requests.Timeout("slow") for _ in range(3)]
        )
        value = fetch_exact_json(
            exact_url(),
            session=session,
            monotonic=Clock(),
            sleeper=sleeps.append,
        )
        self.assertEqual(value["status"], "exhausted")
        self.assertEqual(value["attempt_count"], 3)
        self.assertEqual(
            [attempt["error_type"] for attempt in value["attempts"]],
            ["timeout", "timeout", "timeout"],
        )
        self.assertEqual(sleeps, [0.25, 0.5])

    def test_helper_does_not_follow_or_retry_redirect(self) -> None:
        session = FakeSession([FakeResponse(302)])
        value = fetch_exact_json(
            exact_url(), session=session, monotonic=Clock()
        )
        self.assertEqual(value["status"], "exhausted")
        self.assertEqual(value["attempt_count"], 1)
        self.assertEqual(value["attempts"][0]["error_type"], "http_302")

    def test_helper_rejects_large_response(self) -> None:
        session = FakeSession(
            [FakeResponse(200, b"x" * (MAX_RESPONSE_BYTES + 1))]
        )
        value = fetch_exact_json(
            exact_url(), session=session, monotonic=Clock()
        )
        self.assertEqual(value["status"], "exhausted")
        self.assertEqual(
            value["attempts"][0]["error_type"], "response_too_large"
        )

    def test_unbound_exact_url_is_rejected_before_effect(self) -> None:
        target, requests_ = client()
        changed = copy.deepcopy(requests_[0])
        changed["url"] = changed["url"].replace("BTN", "WLD")
        changed["member_label"] = changed["member_label"].replace("BTN", "WLD")
        with self.assertRaisesRegex(ValueError, "unbound"):
            target.fetch_urls([changed])
        self.assertEqual(target.fetch_calls, 0)
        self.assertEqual(target.exact_api_transport_receipt()["logical_requests"], 0)

    def test_exact_fetches_are_sequential_and_receipted(self) -> None:
        popen = PopenFactory()
        target, requests_ = client(popen=popen)
        batches = target.fetch_urls(requests_[:4])
        self.assertEqual(len(batches), 4)
        self.assertTrue(all(len(batch["results"]) == 1 for batch in batches))
        self.assertEqual(len(popen.calls), 4)
        receipt = target.exact_api_transport_receipt()
        self.assertEqual(receipt["logical_requests"], 4)
        self.assertEqual(receipt["direct_helper_calls"], 4)
        self.assertEqual(receipt["terminal_successes"], 4)
        self.assertEqual(receipt["provider_attempts"], 4)
        self.assertEqual(receipt["provider_retries"], 0)
        self.assertEqual(receipt["http_status_counts"], {"200": 4})
        self.assertTrue(receipt["sequential_within_task"])

    def test_receipt_tamper_fails_even_when_resealed(self) -> None:
        target, requests_ = client()
        target.fetch_urls(requests_[:1])
        receipt = target.exact_api_transport_receipt()
        changed = copy.deepcopy(receipt)
        changed["terminal_successes"] = 2
        changed.pop("receipt_payload_sha256")
        changed["receipt_payload_sha256"] = payload_sha256(changed)
        with self.assertRaisesRegex(ValueError, "conservation"):
            validate_exact_transport_receipt(changed)


if __name__ == "__main__":
    unittest.main()
