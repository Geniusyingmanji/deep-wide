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
from deepwide_agent.v24236_azure_responses_single_attempt import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ARBITRARY_CALLER_HEADERS_ACCEPTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
    INTERNAL_RETRY_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    LOOPBACK_ONLY_ENDPOINT_ENFORCED,
    NOMINAL_TIMEOUT_AND_OUTPUT_RESERVATION_CHECKED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
    PROVIDER_CHALLENGE_HEADER_SENT,
    PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
    REDIRECT_FOLLOWING_IMPLEMENTED,
    REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
    REQUESTS_TRUST_ENV_DISABLED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    AzureResponsesAttemptValue,
    AzureResponsesRequest,
    AzureResponsesSingleAttemptAdapter,
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
    text: str = "answer",
    input_tokens: int = 100,
    output_tokens: int = 20,
    include_usage: bool = True,
    status: str = "completed",
    incomplete_reason: str | None = None,
    response_id: str = "resp_synthetic",
) -> bytes:
    value: dict[str, object] = {
        "id": response_id,
        "status": status,
        "output": [
            {
                "type": "message",
                "content": [{"type": "output_text", "text": text}],
            }
        ],
    }
    if include_usage:
        value["usage"] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
    if incomplete_reason is not None:
        value["incomplete_details"] = {"reason": incomplete_reason}
    return json.dumps(value, sort_keys=True).encode("utf-8")


class V24236AzureResponsesSingleAttemptTests(unittest.TestCase):
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
        self.request = AzureResponsesRequest(
            system="visible system instruction",
            user="visible user request",
            max_output_tokens=200,
            json_mode=True,
            reasoning_effort="high",
            service_tier="priority",
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
        input_tokens: int = 1000,
        output_tokens: int = 200,
        wall_milliseconds: int | None = None,
    ) -> dict[str, object]:
        return build_provider_meter_contract(
            provider_kind="azure_responses_model",
            charge_kind="renderer",
            max_attempts=max_attempts,
            reserved_cost=cost(
                model_calls=1,
                model_attempts=max_attempts,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                wall_milliseconds=(
                    max_attempts * 300_000
                    if wall_milliseconds is None
                    else wall_milliseconds
                ),
            ),
        )

    @staticmethod
    def adapter(post) -> AzureResponsesSingleAttemptAdapter:
        return AzureResponsesSingleAttemptAdapter(
            endpoint="http://127.0.0.1:9878/responses",
            model="gpt-5.6-sol",
            timeout_seconds=300,
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

    def test_success_is_exactly_one_post_and_raw_value_is_ephemeral(self) -> None:
        body = response_bytes(text="private response body")
        post = RecordingPost(FakeResponse(200, body))
        result = self.execute(self.meter(max_attempts=2), post)
        self.assertEqual(len(post.calls), 1)
        call = post.calls[0]
        self.assertEqual(call["url"], "http://127.0.0.1:9878/responses")
        self.assertEqual(call["timeout"], 300)
        self.assertFalse(call["allow_redirects"])
        self.assertEqual(
            set(call["headers"]),
            {
                "Content-Type",
                "X-DeepWide-Execution-Challenge",
                "X-DeepWide-Attempt-Ref",
            },
        )
        sent = json.loads(call["data"].decode("utf-8"))
        self.assertEqual(sent["model"], "gpt-5.6-sol")
        self.assertEqual(sent["reasoning"], {"effort": "high"})
        self.assertEqual(sent["service_tier"], "priority")
        self.assertEqual(sent["text"], {"format": {"type": "json_object"}})
        self.assertIsInstance(result.value, AzureResponsesAttemptValue)
        self.assertEqual(result.value.text, "private response body")
        self.assertEqual(result.value.usage["total_tokens"], 120)
        self.assertEqual(result.value.response_id, "resp_synthetic")
        self.assertFalse(result.value.output_truncated)
        self.assertNotIn("private response body", repr(result.receipt))
        attempt = result.receipt["measurement"]["attempts"][0]
        self.assertEqual(
            attempt["provider_response_ref_sha256"],
            hashlib.sha256(body).hexdigest(),
        )
        self.assertEqual(attempt["response_body_bytes"], len(body))
        self.assertEqual(attempt["request_body_bytes"], len(call["data"]))
        self.assertEqual(result.receipt["settlement_cost"]["model_attempts"], 1)

    def test_retryable_429_then_success_is_two_callbacks_and_two_posts(self) -> None:
        error = json.dumps({"error": {"type": "rate_limit"}}).encode("utf-8")
        post = RecordingPost(
            FakeResponse(429, error),
            FakeResponse(200, response_bytes()),
        )
        meter = self.meter(max_attempts=2, input_tokens=1000, output_tokens=200)
        result = self.execute(meter, post, suffix="retry")
        self.assertEqual(len(post.calls), 2)
        self.assertEqual(result.receipt["attempt_count"], 2)
        attempts = result.receipt["measurement"]["attempts"]
        self.assertEqual([item["outcome"] for item in attempts], ["retryable_http", "success"])
        self.assertNotEqual(
            post.calls[0]["headers"]["X-DeepWide-Attempt-Ref"],
            post.calls[1]["headers"]["X-DeepWide-Attempt-Ref"],
        )
        self.assertEqual(
            post.calls[0]["headers"]["X-DeepWide-Execution-Challenge"],
            post.calls[1]["headers"]["X-DeepWide-Execution-Challenge"],
        )
        self.assertTrue(result.receipt["reservation_fallback_applied"])
        self.assertEqual(result.receipt["settlement_cost"]["input_tokens"], 1000)
        self.assertEqual(result.receipt["settlement_cost"]["output_tokens"], 200)

    def test_transport_timeout_is_one_post_per_attempt_and_no_fake_response(self) -> None:
        post = RecordingPost(requests.Timeout("raw secret"), requests.Timeout("again"))
        result = self.execute(self.meter(max_attempts=2), post, suffix="timeout")
        self.assertEqual(len(post.calls), 2)
        self.assertEqual(result.receipt["logical_status"], "failed")
        for attempt in result.receipt["measurement"]["attempts"]:
            self.assertEqual(attempt["outcome"], "transport_error")
            self.assertIsNone(attempt["provider_response_ref_sha256"])
            self.assertIsNone(attempt["response_body_bytes"])
        self.assertNotIn("raw secret", repr(result.receipt))

    def test_terminal_4xx_settles_failed_after_one_post(self) -> None:
        content = json.dumps({"error": {"type": "bad_request"}}).encode("utf-8")
        post = RecordingPost(FakeResponse(400, content))
        result = self.execute(self.meter(max_attempts=3), post, suffix="terminal")
        self.assertEqual(len(post.calls), 1)
        self.assertEqual(result.receipt["logical_status"], "failed")
        self.assertEqual(
            result.receipt["measurement"]["attempts"][0]["outcome"],
            "terminal_http",
        )

    def test_redirect_is_rejected_without_following_and_permit_stays_pending(self) -> None:
        post = RecordingPost(FakeResponse(307, b"redirect target hidden"))
        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(self.meter(max_attempts=2), post, suffix="redirect")
        self.assertEqual(len(post.calls), 1)
        self.assertFalse(post.calls[0]["allow_redirects"])
        self.assertEqual(caught.exception.receipt["failure_phase"], "callback_exception")
        self.assertTrue(caught.exception.receipt["permit_remains_pending"])
        self.assertNotIn("redirect target hidden", repr(caught.exception.receipt))

    def test_invalid_json_and_empty_output_are_bounded_retryable_failures(self) -> None:
        cases = (
            (b"not-json", "invalid_json"),
            (response_bytes(text=""), "empty_output"),
        )
        for index, (content, expected) in enumerate(cases):
            with self.subTest(expected=expected):
                post = RecordingPost(FakeResponse(200, content))
                result = self.execute(
                    self.meter(max_attempts=1),
                    post,
                    suffix=f"parse-{index}",
                )
                self.assertEqual(len(post.calls), 1)
                self.assertEqual(result.receipt["logical_status"], "failed")
                self.assertEqual(
                    result.receipt["measurement"]["attempts"][0]["outcome"],
                    expected,
                )

    def test_missing_usage_is_not_zero_token_success(self) -> None:
        post = RecordingPost(
            FakeResponse(200, response_bytes(include_usage=False))
        )
        result = self.execute(self.meter(max_attempts=1), post, suffix="usage")
        attempt = result.receipt["measurement"]["attempts"][0]
        self.assertEqual(attempt["outcome"], "invalid_json")
        self.assertEqual(attempt["token_usage_state"], "unavailable")
        self.assertIsNone(attempt["input_tokens"])
        self.assertEqual(result.receipt["logical_status"], "failed")
        self.assertTrue(result.receipt["reservation_fallback_applied"])

    def test_incomplete_response_returns_ephemeral_truncation_signal(self) -> None:
        post = RecordingPost(
            FakeResponse(
                200,
                response_bytes(
                    text="partial",
                    output_tokens=200,
                    status="incomplete",
                    incomplete_reason="max_output_tokens",
                ),
            )
        )
        result = self.execute(self.meter(max_attempts=1), post, suffix="truncated")
        self.assertTrue(result.value.output_truncated)
        self.assertEqual(result.receipt["logical_status"], "completed")

    def test_non_typed_request_exception_is_sanitized_and_not_retried_inside_adapter(self) -> None:
        post = RecordingPost(requests.RequestException("provider secret body"))
        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(self.meter(max_attempts=2), post, suffix="request-error")
        self.assertEqual(len(post.calls), 1)
        self.assertNotIn("provider secret body", repr(caught.exception.receipt))
        self.assertEqual(caught.exception.receipt["failure_phase"], "callback_exception")

    def test_endpoint_request_and_model_validation_happen_before_post(self) -> None:
        invalid_endpoints = (
            "https://user:pass@example.com/responses",
            "https://example.com/other",
            "https://example.com/responses?token=x",
            "https://example.com:443/responses",
            "http://localhost:9878/responses",
            "http://127.0.0.1/responses",
            "ftp://example.com/responses",
        )
        for endpoint in invalid_endpoints:
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    AzureResponsesSingleAttemptAdapter(
                        endpoint=endpoint,
                        model="gpt-5.6-sol",
                        timeout_seconds=300,
                        post=RecordingPost(),
                    )
        with self.assertRaises(ValueError):
            AzureResponsesSingleAttemptAdapter(
                endpoint="http://127.0.0.1:9878/responses",
                model="",
                timeout_seconds=300,
                post=RecordingPost(),
            )
        adapter = self.adapter(RecordingPost())
        for request in (
            AzureResponsesRequest("", "user", 10),
            AzureResponsesRequest("system", "", 10),
            AzureResponsesRequest("system", "user", 0),
            AzureResponsesRequest("system", "user", 10, reasoning_effort="extreme"),
            AzureResponsesRequest("system", "user", 10, service_tier="secret-tier"),
        ):
            with self.subTest(request=request):
                with self.assertRaises(ValueError):
                    adapter.bind(request, meter_contract=self.meter())

        post = RecordingPost()
        adapter = self.adapter(post)
        under_output = self.meter(max_attempts=1, output_tokens=199)
        with self.assertRaisesRegex(ValueError, "reservation"):
            adapter.bind(self.request, meter_contract=under_output)
        under_wall = self.meter(max_attempts=1, wall_milliseconds=299_999)
        with self.assertRaisesRegex(ValueError, "reservation"):
            adapter.bind(self.request, meter_contract=under_wall)
        self.assertEqual(len(post.calls), 0)

    def test_default_session_disables_environment_proxy_and_netrc(self) -> None:
        fake_session = mock.Mock()
        fake_session.headers = {}
        fake_session.proxies = {}
        fake_session.cookies = mock.Mock()
        with mock.patch(
            "deepwide_agent.v24236_azure_responses_single_attempt.requests.Session",
            return_value=fake_session,
        ):
            adapter = AzureResponsesSingleAttemptAdapter(
                endpoint="http://127.0.0.1:9878/responses",
                model="gpt-5.6-sol",
                timeout_seconds=300,
            )
        self.assertFalse(fake_session.trust_env)
        self.assertIsNone(fake_session.auth)
        fake_session.cookies.clear.assert_called_once_with()
        self.assertIs(adapter._session, fake_session)
        self.assertIs(adapter._post, fake_session.post)

    def test_wrong_provider_invocation_is_rejected_before_post(self) -> None:
        tavily = build_provider_meter_contract(
            provider_kind="tavily_search_api",
            charge_kind="fanout_execution",
            max_attempts=1,
            reserved_cost=cost(search_calls=1),
        )
        post = RecordingPost()
        adapter = self.adapter(post)
        with self.assertRaisesRegex(ValueError, "reservation"):
            adapter.bind(self.request, meter_contract=tavily)
        self.assertEqual(len(post.calls), 0)

    def test_public_single_attempt_cannot_bypass_meter_compatibility(self) -> None:
        valid_meter = self.meter(max_attempts=1)
        under_output = self.meter(max_attempts=1, output_tokens=199)
        post = RecordingPost()
        adapter = self.adapter(post)
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
                meter_contract=under_output,
            )
        self.assertEqual(len(post.calls), 0)

    def test_authorization_and_capability_boundary_is_explicit(self) -> None:
        self.assertTrue(CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY)
        self.assertTrue(PROVIDER_CHALLENGE_HEADER_SENT)
        self.assertTrue(LOOPBACK_ONLY_ENDPOINT_ENFORCED)
        self.assertTrue(NOMINAL_TIMEOUT_AND_OUTPUT_RESERVATION_CHECKED)
        self.assertTrue(REQUESTS_TRUST_ENV_DISABLED)
        for value in (
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            INTERNAL_RETRY_IMPLEMENTED,
            REDIRECT_FOLLOWING_IMPLEMENTED,
            ARBITRARY_CALLER_HEADERS_ACCEPTED,
            ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
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
