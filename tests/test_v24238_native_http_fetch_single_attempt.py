from __future__ import annotations

import hashlib
import socket
import sys
import unittest
from pathlib import Path
from unittest import mock

import requests


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24232_webswarm_total_budget import build_cost_vector  # noqa: E402
from deepwide_agent.v24233_webswarm_effect_preauthorization import (  # noqa: E402
    initialize_effect_preauthorization_state,
)
from deepwide_agent.v24234_provider_cost_meter import (  # noqa: E402
    build_provider_meter_contract,
)
from deepwide_agent.v24235_preauthorized_effect_harness import (  # noqa: E402
    PreauthorizedEffectExecutionError,
    PreauthorizedEffectHarness,
)
from deepwide_agent.v24238_native_http_fetch_single_attempt import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ARBITRARY_CALLER_HEADERS_ACCEPTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLER_PUBLIC_NONSECRET_URL_REQUIRED,
    CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    DNS_PREFLIGHT_RESULT_PINNED_TO_TRANSPORT,
    ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
    FULL_PROVIDER_RESPONSE_HASHED_WHEN_TRUNCATED,
    INTERNAL_RETRY_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    NOMINAL_TIMEOUT_RESERVATION_CHECKED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
    PROVIDER_CHALLENGE_HEADER_SENT,
    PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
    PUBLIC_ADDRESS_DNS_PREFLIGHT_IMPLEMENTED,
    REDIRECT_FOLLOWING_IMPLEMENTED,
    REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
    REQUESTS_TRUST_ENV_DISABLED,
    REQUEST_URL_DIRECTLY_PERSISTED_OR_EMITTED,
    RETAINED_RESPONSE_BYTE_CAP_IMPLEMENTED,
    RESPONSE_CLOSE_ATTEMPTED,
    RESPONSE_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED,
    SENSITIVE_QUERY_KEY_REJECTION_IMPLEMENTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    SYSTEM_RESOLVER_USED_BY_DEFAULT,
    TLS_VERIFICATION_DISABLED,
    TOTAL_TRANSPORT_RESPONSE_BYTES_HARD_CAPPED,
    URL_SECRET_ABSENCE_INDEPENDENTLY_VERIFIED,
    NativeHttpFetchAttemptValue,
    NativeHttpFetchRequest,
    NativeHttpFetchSingleAttemptAdapter,
)
from tests.test_v24232_webswarm_total_budget import (  # noqa: E402
    contract as guidance_contract,
    guidance,
    ledger,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def cost(**overrides: int) -> dict[str, int]:
    value = {
        "model_calls": 0,
        "model_attempts": 0,
        "search_calls": 0,
        "fetch_calls": 0,
        "other_tool_calls": 0,
        "orchestrator_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "wall_milliseconds": 30_000,
    }
    value.update(overrides)
    return build_cost_vector(**value)


class FakeResponse:
    def __init__(
        self,
        status_code: int,
        chunks: list[bytes],
        *,
        headers: dict[str, str] | None = None,
        encoding: str | None = "utf-8",
    ) -> None:
        self.status_code = status_code
        self._chunks = list(chunks)
        self.headers = {} if headers is None else dict(headers)
        self.encoding = encoding
        self.closed = False
        self.chunk_sizes: list[int] = []

    def iter_content(self, *, chunk_size: int):
        self.chunk_sizes.append(chunk_size)
        yield from self._chunks

    def close(self) -> None:
        self.closed = True


class RecordingGet:
    def __init__(self, *actions) -> None:
        self.actions = list(actions)
        self.calls: list[dict[str, object]] = []

    def __call__(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        if not self.actions:
            raise AssertionError("unexpected extra GET")
        action = self.actions.pop(0)
        if isinstance(action, BaseException):
            raise action
        return action


class RecordingResolver:
    def __init__(self, *actions) -> None:
        self.actions = list(actions)
        self.calls: list[tuple[str, int]] = []

    def __call__(self, hostname: str, port: int):
        self.calls.append((hostname, port))
        if not self.actions:
            raise AssertionError("unexpected resolver call")
        action = self.actions.pop(0)
        if isinstance(action, BaseException):
            raise action
        return action


class V24238NativeHttpFetchSingleAttemptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = guidance_contract()
        self.policy, _, self.arms, self.sources = guidance(self.contract)
        self.arm = next(arm for arm in self.arms if arm["arm_name"] == "full")
        self.source = self.sources["full"]
        initial = initialize_effect_preauthorization_state(
            initial_budget_ledger=ledger(
                self.contract,
                self.policy,
                self.arm,
                self.source,
            ),
            **self.shared,
        )
        self.harness = PreauthorizedEffectHarness(initial, **self.harness_shared)
        self.request = NativeHttpFetchRequest(
            "https://Example.COM/public/path?q=visible#fragment"
        )

    @property
    def shared(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "guidance_policy": self.policy,
            "guidance_arm": self.arm,
            "scouts": self.source["scouts"],
            "probe": self.source["probe"],
            "experience": self.source["experience"],
        }

    @property
    def harness_shared(self) -> dict[str, object]:
        return {
            "guidance_contract": self.contract,
            "guidance_policy": self.policy,
            "guidance_arm": self.arm,
            "scouts": self.source["scouts"],
            "probe": self.source["probe"],
            "experience": self.source["experience"],
        }

    @staticmethod
    def meter(
        *,
        max_attempts: int = 2,
        wall_milliseconds: int | None = None,
    ) -> dict[str, object]:
        return build_provider_meter_contract(
            provider_kind="native_http_fetch",
            charge_kind="fanout_execution",
            max_attempts=max_attempts,
            reserved_cost=cost(
                fetch_calls=max_attempts,
                wall_milliseconds=(
                    max_attempts * 45_000
                    if wall_milliseconds is None
                    else wall_milliseconds
                ),
            ),
        )

    @staticmethod
    def adapter(
        get,
        resolve,
        *,
        max_response_bytes: int = 1024,
    ) -> NativeHttpFetchSingleAttemptAdapter:
        return NativeHttpFetchSingleAttemptAdapter(
            timeout_seconds=45,
            max_response_bytes=max_response_bytes,
            get=get,
            resolve=resolve,
        )

    def execute(
        self,
        meter,
        get,
        resolve,
        *,
        suffix: str = "1",
        request: NativeHttpFetchRequest | None = None,
        max_response_bytes: int = 1024,
    ):
        adapter = self.adapter(
            get,
            resolve,
            max_response_bytes=max_response_bytes,
        )
        return self.harness.run_effect(
            meter_contract=meter,
            invocation_ref_sha256=digest(f"invocation-{suffix}"),
            permit_ref_sha256=digest(f"permit-{suffix}"),
            charge_ref_sha256=digest(f"charge-{suffix}"),
            callback=adapter.bind(
                self.request if request is None else request,
                meter_contract=meter,
            ),
        )

    def test_success_is_one_get_and_raw_url_body_are_ephemeral(self) -> None:
        body = b"private fetched page"
        response = FakeResponse(
            200,
            [body],
            headers={"Content-Type": "text/html; charset=utf-8"},
        )
        get = RecordingGet(response)
        resolve = RecordingResolver(("93.184.216.34",))
        result = self.execute(self.meter(), get, resolve)
        self.assertEqual(resolve.calls, [("example.com", 443)])
        self.assertEqual(len(get.calls), 1)
        call = get.calls[0]
        self.assertEqual(call["url"], "https://example.com/public/path?q=visible")
        self.assertEqual(call["timeout"], 45)
        self.assertFalse(call["allow_redirects"])
        self.assertTrue(call["stream"])
        self.assertTrue(call["verify"])
        self.assertEqual(set(call["headers"]), {"Accept", "User-Agent"})
        self.assertTrue(response.closed)
        self.assertIsInstance(result.value, NativeHttpFetchAttemptValue)
        self.assertEqual(result.value.url, call["url"])
        self.assertEqual(result.value.body, body)
        self.assertEqual(result.value.content_type, "text/html; charset=utf-8")
        self.assertFalse(result.value.truncated)
        receipt = repr(result.receipt)
        self.assertNotIn("example.com", receipt)
        self.assertNotIn("private fetched page", receipt)
        attempt = result.receipt["measurement"]["attempts"][0]
        self.assertEqual(attempt["request_body_bytes"], 0)
        self.assertEqual(attempt["response_body_bytes"], len(body))
        self.assertEqual(
            attempt["provider_response_ref_sha256"],
            hashlib.sha256(body).hexdigest(),
        )
        self.assertEqual(result.receipt["settlement_cost"]["fetch_calls"], 1)

    def test_retryable_500_and_timeout_are_one_get_per_callback(self) -> None:
        cases = (
            (
                RecordingGet(
                    FakeResponse(500, [b"private error"]),
                    FakeResponse(200, [b"ok"]),
                ),
                ["retryable_http", "success"],
            ),
            (
                RecordingGet(
                    requests.Timeout("private timeout"),
                    FakeResponse(200, [b"ok"]),
                ),
                ["transport_error", "success"],
            ),
        )
        for index, (get, outcomes) in enumerate(cases):
            with self.subTest(index=index):
                resolve = RecordingResolver(
                    ("93.184.216.34",),
                    ("93.184.216.34",),
                )
                result = self.execute(
                    self.meter(),
                    get,
                    resolve,
                    suffix=f"retry-{index}",
                )
                self.assertEqual(len(get.calls), 2)
                self.assertEqual(len(resolve.calls), 2)
                self.assertEqual(
                    [
                        attempt["outcome"]
                        for attempt in result.receipt["measurement"]["attempts"]
                    ],
                    outcomes,
                )
                self.assertNotIn("private timeout", repr(result.receipt))

    def test_terminal_redirect_empty_and_invalid_stream_fail_closed(self) -> None:
        terminal = FakeResponse(404, [b"private not found"])
        result = self.execute(
            self.meter(max_attempts=1),
            RecordingGet(terminal),
            RecordingResolver(("93.184.216.34",)),
            suffix="terminal",
        )
        self.assertEqual(result.receipt["logical_status"], "failed")
        self.assertEqual(
            result.receipt["measurement"]["attempts"][0]["outcome"],
            "terminal_http",
        )
        self.assertTrue(terminal.closed)

        redirect = FakeResponse(302, [b"private redirect"])
        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(
                self.meter(max_attempts=1),
                RecordingGet(redirect),
                RecordingResolver(("93.184.216.34",)),
                suffix="redirect",
            )
        self.assertEqual(caught.exception.receipt["failure_phase"], "callback_exception")
        self.assertTrue(caught.exception.receipt["permit_remains_pending"])
        self.assertTrue(redirect.closed)

        empty = self.execute(
            self.meter(max_attempts=1),
            RecordingGet(FakeResponse(200, [])),
            RecordingResolver(("93.184.216.34",)),
            suffix="empty",
        )
        self.assertEqual(
            empty.receipt["measurement"]["attempts"][0]["outcome"],
            "empty_output",
        )

        invalid = FakeResponse(200, ["not bytes"])  # type: ignore[list-item]
        with self.assertRaises(PreauthorizedEffectExecutionError) as invalid_caught:
            self.execute(
                self.meter(max_attempts=1),
                RecordingGet(invalid),
                RecordingResolver(("93.184.216.34",)),
                suffix="invalid-stream",
            )
        self.assertEqual(
            invalid_caught.exception.receipt["failure_phase"],
            "callback_exception",
        )
        self.assertTrue(invalid.closed)

    def test_stream_cap_hashes_and_reports_only_bounded_prefix(self) -> None:
        response = FakeResponse(200, [b"abc", b"def", b"ghi"])
        result = self.execute(
            self.meter(max_attempts=1),
            RecordingGet(response),
            RecordingResolver(("93.184.216.34",)),
            suffix="cap",
            max_response_bytes=5,
        )
        self.assertEqual(result.value.body, b"abcde")
        self.assertTrue(result.value.truncated)
        attempt = result.receipt["measurement"]["attempts"][0]
        self.assertEqual(attempt["response_body_bytes"], 5)
        self.assertEqual(
            attempt["provider_response_ref_sha256"],
            hashlib.sha256(b"abcde").hexdigest(),
        )

    def test_dns_preflight_rejects_private_mixed_and_failure_before_get(self) -> None:
        cases = (
            NativeHttpFetchRequest("http://127.0.0.1/private"),
            NativeHttpFetchRequest("http://[::1]/private"),
            NativeHttpFetchRequest("http://localhost/private"),
            NativeHttpFetchRequest("https://example.com/private"),
            NativeHttpFetchRequest("https://example.com/failure"),
        )
        resolver_actions = (
            (),
            (),
            (),
            (("93.184.216.34", "10.0.0.1"),),
            (socket.gaierror("private DNS detail"),),
        )
        for index, (request, actions) in enumerate(zip(cases, resolver_actions)):
            with self.subTest(index=index):
                get = RecordingGet()
                resolver = RecordingResolver(*actions)
                with self.assertRaises((ValueError, PreauthorizedEffectExecutionError)) as caught:
                    self.execute(
                        self.meter(max_attempts=1),
                        get,
                        resolver,
                        suffix=f"ssrf-{index}",
                        request=request,
                    )
                self.assertEqual(len(get.calls), 0)
                self.assertNotIn("private DNS detail", repr(caught.exception))

    def test_url_meter_and_public_single_attempt_validate_before_get(self) -> None:
        invalid = (
            "ftp://example.com/x",
            "https://user:pass@example.com/x",
            "https://example.com:443/x",
            "https://example.com/x?access_token=private",
            " https://example.com/x",
            "https://example.com/\nheader",
        )
        for url in invalid:
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    self.adapter(RecordingGet(), RecordingResolver()).bind(
                        NativeHttpFetchRequest(url),
                        meter_contract=self.meter(),
                    )
        post = RecordingGet()
        resolver = RecordingResolver()
        adapter = self.adapter(post, resolver)
        under_wall = self.meter(max_attempts=1, wall_milliseconds=44_999)
        with self.assertRaisesRegex(ValueError, "reservation"):
            adapter.bind(self.request, meter_contract=under_wall)
        model_meter = build_provider_meter_contract(
            provider_kind="azure_responses_model",
            charge_kind="renderer",
            max_attempts=1,
            reserved_cost=cost(
                model_calls=1,
                model_attempts=1,
                input_tokens=100,
                output_tokens=100,
                wall_milliseconds=45_000,
            ),
        )
        with self.assertRaisesRegex(ValueError, "reservation"):
            adapter.bind(self.request, meter_contract=model_meter)

        valid_meter = self.meter(max_attempts=1)
        captured = None

        def callback(invocation):
            nonlocal captured
            captured = dict(invocation)
            raise RuntimeError("capture")

        with self.assertRaises(PreauthorizedEffectExecutionError):
            self.harness.run_effect(
                meter_contract=valid_meter,
                invocation_ref_sha256=digest("direct-invocation"),
                permit_ref_sha256=digest("direct-permit"),
                charge_ref_sha256=digest("direct-charge"),
                callback=callback,
            )
        self.assertIsNotNone(captured)
        with self.assertRaisesRegex(ValueError, "reservation"):
            adapter.single_attempt(
                invocation=captured,
                request=self.request,
                meter_contract=under_wall,
            )
        self.assertEqual(len(post.calls), 0)
        self.assertEqual(len(resolver.calls), 0)

    def test_default_session_disables_environment_auth_proxy_and_tls_bypass(self) -> None:
        fake_session = mock.Mock()
        fake_session.headers = {}
        fake_session.proxies = {}
        fake_session.cookies = mock.Mock()
        with mock.patch(
            "deepwide_agent.v24238_native_http_fetch_single_attempt.requests.Session",
            return_value=fake_session,
        ):
            adapter = NativeHttpFetchSingleAttemptAdapter(
                timeout_seconds=45,
                max_response_bytes=1024,
                resolve=RecordingResolver(("93.184.216.34",)),
            )
        self.assertFalse(fake_session.trust_env)
        self.assertIsNone(fake_session.auth)
        fake_session.cookies.clear.assert_called_once_with()
        self.assertIs(adapter._session, fake_session)
        self.assertIs(adapter._get, fake_session.get)

    def test_authorization_capability_and_dns_limit_are_explicit(self) -> None:
        for value in (
            CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
            PUBLIC_ADDRESS_DNS_PREFLIGHT_IMPLEMENTED,
            SYSTEM_RESOLVER_USED_BY_DEFAULT,
            RETAINED_RESPONSE_BYTE_CAP_IMPLEMENTED,
            RESPONSE_CLOSE_ATTEMPTED,
            CALLER_PUBLIC_NONSECRET_URL_REQUIRED,
            SENSITIVE_QUERY_KEY_REJECTION_IMPLEMENTED,
            REQUESTS_TRUST_ENV_DISABLED,
            NOMINAL_TIMEOUT_RESERVATION_CHECKED,
        ):
            self.assertTrue(value)
        for value in (
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            INTERNAL_RETRY_IMPLEMENTED,
            REDIRECT_FOLLOWING_IMPLEMENTED,
            ARBITRARY_CALLER_HEADERS_ACCEPTED,
            ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
            TLS_VERIFICATION_DISABLED,
            DNS_PREFLIGHT_RESULT_PINNED_TO_TRANSPORT,
            FULL_PROVIDER_RESPONSE_HASHED_WHEN_TRUNCATED,
            TOTAL_TRANSPORT_RESPONSE_BYTES_HARD_CAPPED,
            RESPONSE_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED,
            REQUEST_URL_DIRECTLY_PERSISTED_OR_EMITTED,
            URL_SECRET_ABSENCE_INDEPENDENTLY_VERIFIED,
            PROVIDER_CHALLENGE_HEADER_SENT,
            PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
            PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
            REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
            PRODUCTION_PACKAGE_AUTHORIZED,
            ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
        ):
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
