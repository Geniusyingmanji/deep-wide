from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

import urllib3


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
    NativeHttpFetchAttemptValue,
    NativeHttpFetchRequest,
)
from deepwide_agent.v24245_pinned_native_http_fetch import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ALL_RESOLVED_ADDRESSES_MUST_BE_PUBLIC,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
    DETERMINISTIC_ATTEMPT_INDEX_ADDRESS_SELECTION_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    DNS_PREFLIGHT_RESULT_PINNED_TO_TRANSPORT,
    ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
    FRESH_POOL_PER_CALLBACK_IMPLEMENTED,
    FULL_PROVIDER_RESPONSE_HASHED_WHEN_TRUNCATED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    NOMINAL_TIMEOUT_RESERVATION_CHECKED,
    ONE_URLOPEN_PER_CALLBACK_IMPLEMENTED,
    ORIGINAL_HOST_HEADER_IMPLEMENTED,
    POOL_CLOSE_ATTEMPTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
    PROVIDER_CHALLENGE_HEADER_SENT,
    PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
    PUBLIC_ADDRESS_DNS_PREFLIGHT_IMPLEMENTED,
    REDIRECT_FOLLOWING_IMPLEMENTED,
    REQUESTS_OR_ENVIRONMENT_PROXY_USED,
    REQUEST_URL_DIRECTLY_PERSISTED_OR_EMITTED,
    RESPONSE_AND_POOL_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED,
    RESPONSE_CLOSE_ATTEMPTED,
    RESPONSE_RELEASE_ATTEMPTED,
    RETAINED_RESPONSE_BYTE_CAP_IMPLEMENTED,
    SENSITIVE_QUERY_KEY_REJECTION_IMPLEMENTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    SINGLE_SOCKET_CONNECTION_ATTEMPT_INDEPENDENTLY_ATTESTED,
    SYSTEM_RESOLVER_USED_BY_DEFAULT,
    TLS_ORIGINAL_HOSTNAME_CERTIFICATE_ASSERTION_IMPLEMENTED,
    TLS_ORIGINAL_HOSTNAME_SNI_IMPLEMENTED,
    TOTAL_TRANSPORT_RESPONSE_BYTES_HARD_CAPPED,
    URL_SECRET_ABSENCE_INDEPENDENTLY_VERIFIED,
    URLLIB3_INTERNAL_RETRY_DISABLED,
    URLLIB3_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
    PinnedNativeHttpFetchAdapter,
    PinnedNativeHttpFetchError,
    _default_pool_factory,
    _select_pinned_address,
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
        status: int,
        chunks: list[bytes],
        *,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status = status
        self._chunks = list(chunks)
        self.headers = {} if headers is None else dict(headers)
        self.stream_calls: list[dict[str, object]] = []
        self.close_calls = 0
        self.release_calls = 0

    def stream(self, **kwargs):
        self.stream_calls.append(dict(kwargs))
        yield from self._chunks

    def close(self) -> None:
        self.close_calls += 1

    def release_conn(self) -> None:
        self.release_calls += 1


class FakePool:
    def __init__(self, action) -> None:
        self.action = action
        self.urlopen_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.close_calls = 0

    def urlopen(self, *args, **kwargs):
        self.urlopen_calls.append((args, dict(kwargs)))
        if isinstance(self.action, BaseException):
            raise self.action
        return self.action

    def close(self) -> None:
        self.close_calls += 1


class RecordingPoolFactory:
    def __init__(self, *actions) -> None:
        self.actions = list(actions)
        self.calls: list[dict[str, object]] = []
        self.pools: list[FakePool] = []

    def __call__(self, **kwargs):
        self.calls.append(dict(kwargs))
        if not self.actions:
            raise AssertionError("unexpected extra pool")
        action = self.actions.pop(0)
        if isinstance(action, BaseException):
            raise action
        pool = action if isinstance(action, FakePool) else FakePool(action)
        self.pools.append(pool)
        return pool


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


class V24245PinnedNativeHttpFetchTests(unittest.TestCase):
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
        *, max_attempts: int = 2, wall_milliseconds: int | None = None
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
        resolver,
        factory,
        *,
        max_response_bytes: int = 1024,
    ) -> PinnedNativeHttpFetchAdapter:
        return PinnedNativeHttpFetchAdapter(
            timeout_seconds=45,
            max_response_bytes=max_response_bytes,
            resolve=resolver,
            pool_factory=factory,
        )

    def execute(
        self,
        meter,
        resolver,
        factory,
        *,
        suffix: str = "1",
        request: NativeHttpFetchRequest | None = None,
        max_response_bytes: int = 1024,
    ):
        adapter = self.adapter(
            resolver,
            factory,
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

    def test_https_success_pins_ip_and_preserves_host_target_and_bounds(self) -> None:
        body = b"private fetched page"
        response = FakeResponse(
            200,
            [body],
            headers={"Content-Type": "text/html; charset=utf-8"},
        )
        resolver = RecordingResolver(("2606:2800:220:1:248:1893:25c8:1946", "93.184.216.34"))
        factory = RecordingPoolFactory(response)
        result = self.execute(self.meter(max_attempts=1), resolver, factory)
        self.assertEqual(resolver.calls, [("example.com", 443)])
        self.assertEqual(
            factory.calls,
            [
                {
                    "scheme": "https",
                    "pinned_address": "93.184.216.34",
                    "port": 443,
                    "original_hostname": "example.com",
                    "timeout_seconds": 45,
                }
            ],
        )
        pool = factory.pools[0]
        self.assertEqual(len(pool.urlopen_calls), 1)
        args, kwargs = pool.urlopen_calls[0]
        self.assertEqual(args, ("GET", "/public/path?q=visible"))
        self.assertEqual(kwargs["headers"]["Host"], "example.com")
        self.assertEqual(kwargs["headers"]["Accept-Encoding"], "identity")
        self.assertFalse(kwargs["retries"])
        self.assertFalse(kwargs["redirect"])
        self.assertTrue(kwargs["assert_same_host"])
        self.assertFalse(kwargs["preload_content"])
        self.assertFalse(kwargs["decode_content"])
        self.assertFalse(kwargs["release_conn"])
        self.assertEqual(response.stream_calls, [{"amt": 1025, "decode_content": True}])
        self.assertEqual(response.close_calls, 1)
        self.assertEqual(response.release_calls, 1)
        self.assertEqual(pool.close_calls, 1)
        self.assertIsInstance(result.value, NativeHttpFetchAttemptValue)
        self.assertEqual(result.value.body, body)
        self.assertIsNone(result.value.encoding)
        self.assertNotIn("example.com", repr(result.receipt))
        self.assertNotIn("private fetched page", repr(result.receipt))
        attempt = result.receipt["measurement"]["attempts"][0]
        self.assertEqual(attempt["response_body_bytes"], len(body))
        self.assertEqual(
            attempt["provider_response_ref_sha256"], hashlib.sha256(body).hexdigest()
        )

    def test_attempt_index_rotates_canonical_addresses_without_hidden_retry(self) -> None:
        resolver = RecordingResolver(
            ("2606:2800:220:1:248:1893:25c8:1946", "93.184.216.35", "93.184.216.34"),
            ("93.184.216.34", "93.184.216.35", "2606:2800:220:1:248:1893:25c8:1946"),
        )
        factory = RecordingPoolFactory(
            FakeResponse(500, [b"private error"]),
            FakeResponse(200, [b"ok"]),
        )
        result = self.execute(self.meter(), resolver, factory, suffix="rotate")
        self.assertEqual(
            [call["pinned_address"] for call in factory.calls],
            ["93.184.216.34", "93.184.216.35"],
        )
        self.assertEqual([len(pool.urlopen_calls) for pool in factory.pools], [1, 1])
        self.assertEqual(
            [attempt["outcome"] for attempt in result.receipt["measurement"]["attempts"]],
            ["retryable_http", "success"],
        )
        self.assertEqual(_select_pinned_address(("93.184.216.35", "93.184.216.34"), attempt_index=3), "93.184.216.34")

    def test_http_host_header_and_literal_address_are_pinned(self) -> None:
        resolver = RecordingResolver()
        factory = RecordingPoolFactory(FakeResponse(200, [b"ok"]))
        result = self.execute(
            self.meter(max_attempts=1),
            resolver,
            factory,
            suffix="http",
            request=NativeHttpFetchRequest("http://93.184.216.34/a?b=c"),
        )
        self.assertEqual(resolver.calls, [])
        self.assertEqual(factory.calls[0]["scheme"], "http")
        self.assertEqual(factory.calls[0]["pinned_address"], "93.184.216.34")
        _, kwargs = factory.pools[0].urlopen_calls[0]
        self.assertEqual(kwargs["headers"]["Host"], "93.184.216.34")
        self.assertEqual(result.value.url, "http://93.184.216.34/a?b=c")

    def test_mixed_private_invalid_zone_and_dns_failure_never_create_pool(self) -> None:
        actions = (
            ("93.184.216.34", "10.0.0.1"),
            ("fe80::1%eth0",),
            ("not-an-address",),
            OSError("private resolver detail"),
        )
        for index, action in enumerate(actions):
            with self.subTest(index=index):
                resolver = RecordingResolver(action)
                factory = RecordingPoolFactory()
                with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
                    self.execute(
                        self.meter(max_attempts=1),
                        resolver,
                        factory,
                        suffix=f"dns-{index}",
                    )
                self.assertEqual(factory.calls, [])
                self.assertNotIn("private resolver detail", repr(caught.exception))

    def test_transport_error_is_typed_and_always_closes_fresh_pool(self) -> None:
        resolver = RecordingResolver(("93.184.216.34",), ("93.184.216.34",))
        factory = RecordingPoolFactory(
            FakePool(
                urllib3.exceptions.ConnectTimeoutError(
                    None, None, "private detail"
                )
            ),
            FakeResponse(200, [b"ok"]),
        )
        result = self.execute(self.meter(), resolver, factory, suffix="transport")
        self.assertEqual(
            [attempt["outcome"] for attempt in result.receipt["measurement"]["attempts"]],
            ["transport_error", "success"],
        )
        self.assertEqual([pool.close_calls for pool in factory.pools], [1, 1])
        self.assertNotIn("private detail", repr(result.receipt))

    def test_redirect_invalid_stream_and_prefix_cap_fail_closed(self) -> None:
        redirect = FakeResponse(302, [b"private redirect"])
        with self.assertRaises(PreauthorizedEffectExecutionError):
            self.execute(
                self.meter(max_attempts=1),
                RecordingResolver(("93.184.216.34",)),
                RecordingPoolFactory(redirect),
                suffix="redirect",
            )
        self.assertEqual(redirect.close_calls, 1)
        self.assertEqual(redirect.release_calls, 1)

        invalid = FakeResponse(200, ["not bytes"])  # type: ignore[list-item]
        with self.assertRaises(PreauthorizedEffectExecutionError):
            self.execute(
                self.meter(max_attempts=1),
                RecordingResolver(("93.184.216.34",)),
                RecordingPoolFactory(invalid),
                suffix="invalid",
            )
        self.assertEqual(invalid.close_calls, 1)

        capped = FakeResponse(200, [b"abc", b"def", b"ghi"])
        result = self.execute(
            self.meter(max_attempts=1),
            RecordingResolver(("93.184.216.34",)),
            RecordingPoolFactory(capped),
            suffix="cap",
            max_response_bytes=5,
        )
        self.assertEqual(result.value.body, b"abcde")
        self.assertTrue(result.value.truncated)
        attempt = result.receipt["measurement"]["attempts"][0]
        self.assertEqual(attempt["response_body_bytes"], 5)

    def test_default_pool_factory_pins_tcp_and_https_identity_without_network(self) -> None:
        http = _default_pool_factory(
            scheme="http",
            pinned_address="93.184.216.34",
            port=80,
            original_hostname="example.com",
            timeout_seconds=45,
        )
        https = _default_pool_factory(
            scheme="https",
            pinned_address="93.184.216.34",
            port=443,
            original_hostname="example.com",
            timeout_seconds=45,
        )
        try:
            self.assertIsInstance(http, urllib3.HTTPConnectionPool)
            self.assertNotIsInstance(http, urllib3.HTTPSConnectionPool)
            self.assertEqual(http.host, "93.184.216.34")
            self.assertFalse(http.retries)
            self.assertIsInstance(https, urllib3.HTTPSConnectionPool)
            self.assertEqual(https.host, "93.184.216.34")
            self.assertEqual(https.assert_hostname, "example.com")
            connection = https._new_conn()
            self.assertEqual(connection.host, "93.184.216.34")
            self.assertEqual(connection.server_hostname, "example.com")
            self.assertEqual(connection.assert_hostname, "example.com")
            self.assertEqual(connection.cert_reqs, 2)
        finally:
            http.close()
            https.close()

    def test_validation_occurs_before_resolver_or_pool(self) -> None:
        resolver = RecordingResolver()
        factory = RecordingPoolFactory()
        adapter = self.adapter(resolver, factory)
        with self.assertRaises(ValueError):
            adapter.bind(
                NativeHttpFetchRequest("https://example.com/x?token=private"),
                meter_contract=self.meter(max_attempts=1),
            )
        with self.assertRaisesRegex(ValueError, "reservation"):
            adapter.bind(
                self.request,
                meter_contract=self.meter(max_attempts=1, wall_milliseconds=44_999),
            )
        self.assertEqual(resolver.calls, [])
        self.assertEqual(factory.calls, [])

    def test_authorization_and_residual_limits_are_explicit(self) -> None:
        for value in (
            CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
            PUBLIC_ADDRESS_DNS_PREFLIGHT_IMPLEMENTED,
            ALL_RESOLVED_ADDRESSES_MUST_BE_PUBLIC,
            DNS_PREFLIGHT_RESULT_PINNED_TO_TRANSPORT,
            DETERMINISTIC_ATTEMPT_INDEX_ADDRESS_SELECTION_IMPLEMENTED,
            ORIGINAL_HOST_HEADER_IMPLEMENTED,
            TLS_ORIGINAL_HOSTNAME_SNI_IMPLEMENTED,
            TLS_ORIGINAL_HOSTNAME_CERTIFICATE_ASSERTION_IMPLEMENTED,
            URLLIB3_INTERNAL_RETRY_DISABLED,
            FRESH_POOL_PER_CALLBACK_IMPLEMENTED,
            ONE_URLOPEN_PER_CALLBACK_IMPLEMENTED,
            SYSTEM_RESOLVER_USED_BY_DEFAULT,
            RETAINED_RESPONSE_BYTE_CAP_IMPLEMENTED,
            RESPONSE_CLOSE_ATTEMPTED,
            RESPONSE_RELEASE_ATTEMPTED,
            POOL_CLOSE_ATTEMPTED,
            SENSITIVE_QUERY_KEY_REJECTION_IMPLEMENTED,
            NOMINAL_TIMEOUT_RESERVATION_CHECKED,
        ):
            self.assertTrue(value)
        for value in (
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            REDIRECT_FOLLOWING_IMPLEMENTED,
            TOTAL_TRANSPORT_RESPONSE_BYTES_HARD_CAPPED,
            FULL_PROVIDER_RESPONSE_HASHED_WHEN_TRUNCATED,
            RESPONSE_AND_POOL_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED,
            SINGLE_SOCKET_CONNECTION_ATTEMPT_INDEPENDENTLY_ATTESTED,
            PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
            REQUESTS_OR_ENVIRONMENT_PROXY_USED,
            ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
            REQUEST_URL_DIRECTLY_PERSISTED_OR_EMITTED,
            URL_SECRET_ABSENCE_INDEPENDENTLY_VERIFIED,
            PROVIDER_CHALLENGE_HEADER_SENT,
            PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
            URLLIB3_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
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
