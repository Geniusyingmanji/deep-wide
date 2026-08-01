from __future__ import annotations

import hashlib
import json
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

from deepwide_agent.v24232_webswarm_total_budget import (  # noqa: E402
    build_cost_vector,
)
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
from deepwide_agent.v24237_tavily_search_single_attempt import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ARBITRARY_CALLER_HEADERS_ACCEPTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLER_SUPPLIED_CREDENTIAL_REQUIRED,
    CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
    CREDENTIAL_EXCLUDED_FROM_REQUEST_BODY,
    CREDENTIAL_DURABLY_PERSISTED_HASHED_OR_EMITTED,
    CREDENTIAL_RETAINED_IN_ADAPTER_MEMORY,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    DIRECT_CREDENTIAL_ECHO_REJECTED_BEFORE_RESPONSE_HASH,
    ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
    EXACT_HTTPS_ENDPOINT_ENFORCED,
    INTERNAL_RETRY_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    NOMINAL_TIMEOUT_RESERVATION_CHECKED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
    PROVIDER_CHALLENGE_HEADER_SENT,
    PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
    REDIRECT_FOLLOWING_IMPLEMENTED,
    REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
    REQUESTS_TRUST_ENV_DISABLED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    TLS_VERIFICATION_DISABLED,
    TavilySearchAttemptValue,
    TavilySearchRequest,
    TavilySearchSingleAttemptAdapter,
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
    def __init__(self, status_code: int, content: bytes) -> None:
        self.status_code = status_code
        self.content = content


class RecordingPost:
    def __init__(self, *actions) -> None:
        self.actions = list(actions)
        self.calls: list[dict[str, object]] = []

    def __call__(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        if not self.actions:
            raise AssertionError("unexpected extra POST")
        action = self.actions.pop(0)
        if isinstance(action, BaseException):
            raise action
        return action


def response_bytes(
    *,
    answer: str = "private search answer",
    results: list[dict[str, object]] | None = None,
) -> bytes:
    if results is None:
        results = [
            {
                "title": "Private title",
                "url": "https://Example.COM/source#fragment",
                "content": "private snippet",
                "raw_content": "private page text",
                "score": 0.9,
            }
        ]
    return json.dumps(
        {"answer": answer, "results": results},
        sort_keys=True,
    ).encode("utf-8")


class V24237TavilySearchSingleAttemptTests(unittest.TestCase):
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
        self.credentials = ("synthetic-credential-one", "synthetic-credential-two")
        self.request = TavilySearchRequest(
            query="visible synthetic query",
            max_results=5,
            search_depth="advanced",
            include_raw_content=True,
            include_answer=True,
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
            provider_kind="tavily_search_api",
            charge_kind="fanout_execution",
            max_attempts=max_attempts,
            reserved_cost=cost(
                search_calls=max_attempts,
                wall_milliseconds=(
                    max_attempts * 90_000
                    if wall_milliseconds is None
                    else wall_milliseconds
                ),
            ),
        )

    def adapter(
        self,
        post,
        *,
        credentials: tuple[str, ...] | None = None,
    ) -> TavilySearchSingleAttemptAdapter:
        return TavilySearchSingleAttemptAdapter(
            endpoint="https://api.tavily.com/search",
            credentials=self.credentials if credentials is None else credentials,
            timeout_seconds=90,
            post=post,
        )

    def execute(self, meter, post, *, suffix: str = "1", request=None):
        adapter = self.adapter(post)
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

    def test_success_is_one_post_and_ephemeral_value_is_sanitized(self) -> None:
        body = response_bytes()
        post = RecordingPost(FakeResponse(200, body))
        result = self.execute(self.meter(), post)
        self.assertEqual(len(post.calls), 1)
        call = post.calls[0]
        self.assertEqual(call["url"], "https://api.tavily.com/search")
        self.assertEqual(call["timeout"], 90)
        self.assertFalse(call["allow_redirects"])
        self.assertTrue(call["verify"])
        self.assertEqual(
            set(call["headers"]),
            {
                "Authorization",
                "Content-Type",
                "X-DeepWide-Execution-Challenge",
                "X-DeepWide-Attempt-Ref",
            },
        )
        self.assertEqual(
            call["headers"]["Authorization"],
            "Bearer synthetic-credential-one",
        )
        sent = json.loads(call["data"].decode("utf-8"))
        self.assertEqual(sent["query"], self.request.query)
        self.assertNotIn("api_key", sent)
        self.assertNotIn("synthetic-credential-one", call["data"].decode("utf-8"))
        self.assertIsInstance(result.value, TavilySearchAttemptValue)
        self.assertEqual(result.value.answer, "private search answer")
        self.assertEqual(len(result.value.results), 1)
        self.assertEqual(result.value.results[0].url, "https://example.com/source")
        self.assertEqual(result.value.results[0].score, 0.9)
        receipt_text = repr(result.receipt)
        for private in (
            self.request.query,
            "private search answer",
            "private snippet",
            "synthetic-credential-one",
        ):
            self.assertNotIn(private, receipt_text)
        attempt = result.receipt["measurement"]["attempts"][0]
        self.assertEqual(
            attempt["provider_response_ref_sha256"],
            hashlib.sha256(body).hexdigest(),
        )
        self.assertEqual(attempt["response_body_bytes"], len(body))
        self.assertEqual(attempt["token_usage_state"], "not_applicable")
        self.assertEqual(result.receipt["settlement_cost"]["search_calls"], 1)

    def test_key_local_432_rotates_to_distinct_credential(self) -> None:
        first = b'{"error":"quota"}'
        post = RecordingPost(
            FakeResponse(432, first),
            FakeResponse(200, response_bytes()),
        )
        result = self.execute(self.meter(), post, suffix="rotation")
        self.assertEqual(len(post.calls), 2)
        self.assertEqual(result.receipt["attempt_count"], 2)
        self.assertEqual(
            [item["outcome"] for item in result.receipt["measurement"]["attempts"]],
            ["key_local_http", "success"],
        )
        self.assertEqual(
            [call["headers"]["Authorization"] for call in post.calls],
            [
                "Bearer synthetic-credential-one",
                "Bearer synthetic-credential-two",
            ],
        )
        self.assertEqual(
            result.receipt["settlement_cost"]["search_calls"],
            2,
        )

    def test_retryable_429_and_timeout_are_one_post_per_callback(self) -> None:
        cases = (
            (
                RecordingPost(
                    FakeResponse(429, b'{"error":"rate"}'),
                    FakeResponse(200, response_bytes()),
                ),
                ["retryable_http", "success"],
            ),
            (
                RecordingPost(
                    requests.Timeout("private transport detail"),
                    FakeResponse(200, response_bytes()),
                ),
                ["transport_error", "success"],
            ),
        )
        for index, (post, outcomes) in enumerate(cases):
            with self.subTest(index=index):
                result = self.execute(self.meter(), post, suffix=f"retry-{index}")
                self.assertEqual(len(post.calls), 2)
                self.assertEqual(
                    [
                        item["outcome"]
                        for item in result.receipt["measurement"]["attempts"]
                    ],
                    outcomes,
                )
                self.assertNotIn("private transport detail", repr(result.receipt))

    def test_terminal_redirect_parse_and_empty_fail_closed(self) -> None:
        terminal = RecordingPost(FakeResponse(400, b'{"error":"bad"}'))
        terminal_result = self.execute(
            self.meter(max_attempts=1),
            terminal,
            suffix="terminal",
        )
        self.assertEqual(terminal_result.receipt["logical_status"], "failed")
        self.assertEqual(
            terminal_result.receipt["measurement"]["attempts"][0]["outcome"],
            "terminal_http",
        )

        redirect = RecordingPost(FakeResponse(307, b"private redirect"))
        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(self.meter(max_attempts=1), redirect, suffix="redirect")
        self.assertEqual(caught.exception.receipt["failure_phase"], "callback_exception")
        self.assertTrue(caught.exception.receipt["permit_remains_pending"])
        self.assertNotIn("private redirect", repr(caught.exception.receipt))

        cases = (
            (b"not-json", "invalid_json"),
            (response_bytes(results=[]), "empty_output"),
            (
                response_bytes(
                    results=[
                        {
                            "title": "bad",
                            "url": "file:///private",
                            "content": "x",
                            "raw_content": "y",
                        }
                    ]
                ),
                "empty_output",
            ),
            (
                response_bytes(
                    results=[
                        {
                            "title": "bad score",
                            "url": "https://example.test/source",
                            "content": "x",
                            "raw_content": "y",
                            "score": "not-a-number",
                        }
                    ]
                ),
                "invalid_json",
            ),
        )
        for index, (content, outcome) in enumerate(cases):
            with self.subTest(outcome=outcome, index=index):
                result = self.execute(
                    self.meter(max_attempts=1),
                    RecordingPost(FakeResponse(200, content)),
                    suffix=f"parse-{index}",
                )
                self.assertEqual(result.receipt["logical_status"], "failed")
                self.assertEqual(
                    result.receipt["measurement"]["attempts"][0]["outcome"],
                    outcome,
                )

    def test_non_typed_request_exception_is_sanitized(self) -> None:
        post = RecordingPost(requests.RequestException("private provider body"))
        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(self.meter(), post, suffix="request-error")
        self.assertEqual(len(post.calls), 1)
        self.assertEqual(caught.exception.receipt["failure_phase"], "callback_exception")
        self.assertNotIn("private provider body", repr(caught.exception.receipt))
        self.assertNotIn("synthetic-credential-one", repr(caught.exception.receipt))

    def test_direct_credential_echo_fails_before_response_hash(self) -> None:
        echoed = b'{"error":"synthetic-credential-one"}'
        post = RecordingPost(FakeResponse(500, echoed))
        meter = self.meter(max_attempts=1)
        fake_hashlib = mock.Mock()
        fake_hashlib.sha256.side_effect = AssertionError("response must not be hashed")
        with mock.patch(
            "deepwide_agent.v24237_tavily_search_single_attempt.hashlib",
            new=fake_hashlib,
        ):
            with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
                self.execute(meter, post, suffix="echo")
        self.assertEqual(caught.exception.receipt["failure_phase"], "callback_exception")
        self.assertNotIn("synthetic-credential-one", repr(caught.exception.receipt))

    def test_endpoint_credentials_request_and_meter_validate_before_post(self) -> None:
        invalid_endpoints = (
            "http://api.tavily.com/search",
            "https://user:pass@api.tavily.com/search",
            "https://api.tavily.com:443/search",
            "https://api.tavily.com/search?token=x",
            "https://example.com/search",
            "https://api.tavily.com/other",
        )
        for endpoint in invalid_endpoints:
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    TavilySearchSingleAttemptAdapter(
                        endpoint=endpoint,
                        credentials=("synthetic-credential-one",),
                        timeout_seconds=90,
                        post=RecordingPost(),
                    )
        for credentials in (
            (),
            ("short",),
            ("synthetic credential",),
            ("synthetic-credential-one", "synthetic-credential-one"),
        ):
            with self.subTest(credentials=credentials):
                with self.assertRaises(ValueError):
                    TavilySearchSingleAttemptAdapter(
                        endpoint="https://api.tavily.com/search",
                        credentials=credentials,
                        timeout_seconds=90,
                        post=RecordingPost(),
                    )
        post = RecordingPost()
        adapter = self.adapter(post)
        for request in (
            TavilySearchRequest("", 5),
            TavilySearchRequest(" padded ", 5),
            TavilySearchRequest("query synthetic-credential-one", 5),
            TavilySearchRequest("query", 0),
            TavilySearchRequest("query", 21),
            TavilySearchRequest("query", 5, search_depth="unknown"),
        ):
            with self.subTest(request=request):
                with self.assertRaises(ValueError):
                    adapter.bind(request, meter_contract=self.meter())
        under_wall = self.meter(max_attempts=1, wall_milliseconds=89_999)
        with self.assertRaisesRegex(ValueError, "reservation"):
            adapter.bind(self.request, meter_contract=under_wall)
        one_credential = self.adapter(
            post,
            credentials=("synthetic-credential-one",),
        )
        with self.assertRaisesRegex(ValueError, "reservation"):
            one_credential.bind(self.request, meter_contract=self.meter(max_attempts=2))
        self.assertEqual(len(post.calls), 0)

    def test_default_session_disables_environment_auth_proxy_and_tls_bypass(self) -> None:
        fake_session = mock.Mock()
        fake_session.headers = {}
        fake_session.proxies = {}
        fake_session.cookies = mock.Mock()
        with mock.patch(
            "deepwide_agent.v24237_tavily_search_single_attempt.requests.Session",
            return_value=fake_session,
        ):
            adapter = TavilySearchSingleAttemptAdapter(
                endpoint="https://api.tavily.com/search",
                credentials=("synthetic-credential-one",),
                timeout_seconds=90,
            )
        self.assertFalse(fake_session.trust_env)
        self.assertIsNone(fake_session.auth)
        fake_session.cookies.clear.assert_called_once_with()
        self.assertIs(adapter._session, fake_session)
        self.assertIs(adapter._post, fake_session.post)

    def test_wrong_provider_and_public_single_attempt_bypass_are_rejected(self) -> None:
        model_meter = build_provider_meter_contract(
            provider_kind="azure_responses_model",
            charge_kind="renderer",
            max_attempts=1,
            reserved_cost=cost(
                model_calls=1,
                model_attempts=1,
                input_tokens=100,
                output_tokens=100,
                wall_milliseconds=90_000,
            ),
        )
        post = RecordingPost()
        adapter = self.adapter(post)
        with self.assertRaisesRegex(ValueError, "reservation"):
            adapter.bind(self.request, meter_contract=model_meter)

        valid_meter = self.meter(max_attempts=1)
        under_wall = self.meter(max_attempts=1, wall_milliseconds=89_999)
        captured = None

        def callback(invocation):
            nonlocal captured
            captured = dict(invocation)
            raise RuntimeError("capture invocation")

        with self.assertRaises(PreauthorizedEffectExecutionError):
            self.harness.run_effect(
                meter_contract=valid_meter,
                invocation_ref_sha256=digest("invocation-direct"),
                permit_ref_sha256=digest("permit-direct"),
                charge_ref_sha256=digest("charge-direct"),
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

    def test_authorization_and_capability_boundary_is_explicit(self) -> None:
        for value in (
            CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
            EXACT_HTTPS_ENDPOINT_ENFORCED,
            CALLER_SUPPLIED_CREDENTIAL_REQUIRED,
            CREDENTIAL_EXCLUDED_FROM_REQUEST_BODY,
            CREDENTIAL_RETAINED_IN_ADAPTER_MEMORY,
            DIRECT_CREDENTIAL_ECHO_REJECTED_BEFORE_RESPONSE_HASH,
            REQUESTS_TRUST_ENV_DISABLED,
            PROVIDER_CHALLENGE_HEADER_SENT,
            NOMINAL_TIMEOUT_RESERVATION_CHECKED,
        ):
            self.assertTrue(value)
        for value in (
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            INTERNAL_RETRY_IMPLEMENTED,
            REDIRECT_FOLLOWING_IMPLEMENTED,
            ARBITRARY_CALLER_HEADERS_ACCEPTED,
            ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
            CREDENTIAL_DURABLY_PERSISTED_HASHED_OR_EMITTED,
            TLS_VERIFICATION_DISABLED,
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
