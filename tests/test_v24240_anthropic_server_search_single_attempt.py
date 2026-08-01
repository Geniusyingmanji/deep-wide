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
from deepwide_agent.v24240_anthropic_server_search_single_attempt import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ARBITRARY_CALLER_HEADERS_ACCEPTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CACHE_TOKENS_INCLUDED_IN_METERED_INPUT,
    CALLER_SUPPLIED_CREDENTIAL_REQUIRED,
    CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
    CREDENTIAL_DURABLY_PERSISTED_HASHED_OR_EMITTED,
    CREDENTIAL_EXCLUDED_FROM_REQUEST_BODY,
    CREDENTIAL_RETAINED_IN_ADAPTER_MEMORY,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    DIRECT_CREDENTIAL_ECHO_REJECTED_BEFORE_RESPONSE_HASH,
    ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
    EXACT_HTTPS_ENDPOINT_ENFORCED,
    INPUT_TOKEN_RESERVATION_COVERAGE_PRE_EFFECT_PROVEN,
    INTERNAL_RETRY_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    NOMINAL_TIMEOUT_OUTPUT_AND_TOOL_RESERVATION_CHECKED,
    OBSERVED_PROVIDER_TOOL_ACTIONS_METERED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROVIDER_ACTION_COUNTER_CROSS_CHECKED,
    PROVIDER_ACTION_COUNTER_MISMATCH_FAILS_CLOSED,
    PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
    PROVIDER_CHALLENGE_HEADER_SENT,
    PROVIDER_DECLARED_MAX_USES_SENT,
    PROVIDER_DECLARED_MAX_USES_VIOLATION_REJECTED_POST_EFFECT,
    PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
    PROVIDER_TOOL_ACTION_HARD_LIMIT_ENFORCED_PRE_EFFECT,
    PROVIDER_TOOL_ACTION_IS_PAGE_EVIDENCE,
    REDIRECT_FOLLOWING_IMPLEMENTED,
    REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
    REQUESTS_TRUST_ENV_DISABLED,
    RESPONSE_BODY_STREAM_CAP_IMPLEMENTED,
    RESPONSE_CLOSE_ATTEMPTED,
    RESPONSE_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    TLS_VERIFICATION_DISABLED,
    AnthropicServerSearchAttemptValue,
    AnthropicServerSearchRequest,
    AnthropicServerSearchSingleAttemptAdapter,
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
        self.closed = False

    def close(self) -> None:
        self.closed = True


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
    text: str = "private answer",
    input_tokens: int = 100,
    output_tokens: int = 20,
    cache_creation_tokens: int = 10,
    cache_read_tokens: int = 5,
    action_count: int = 1,
    reported_tool_calls: int | None = None,
    include_usage: bool = True,
    include_actions: bool = True,
    include_results: bool = True,
    include_text: bool = True,
    stop_reason: str = "end_turn",
) -> bytes:
    content: list[dict[str, object]] = []
    actual_actions = action_count if include_actions else 0
    for index in range(actual_actions):
        action_id = f"srvtoolu_synthetic_{index}"
        content.append(
            {
                "type": "server_tool_use",
                "id": action_id,
                "name": "web_search",
                "input": {"query": f"private provider query {index}"},
            }
        )
        if include_results:
            content.append(
                {
                    "type": "web_search_tool_result",
                    "tool_use_id": action_id,
                    "content": [
                        {
                            "type": "web_search_result",
                            "url": (
                                "https://Example.COM/source/"
                                f"{index}?utm_source=x#fragment"
                            ),
                            "title": f"Private source {index}",
                            "page_age": "2026-08-01",
                            "encrypted_content": "must-not-be-retained",
                        }
                    ],
                }
            )
    if include_text:
        content.append(
            {
                "type": "text",
                "text": text,
                "citations": [
                    {
                        "type": "web_search_result_location",
                        "url": "https://Example.COM/source/0?utm_source=x#fragment",
                        "title": "Private citation",
                        "cited_text": "private cited lead",
                        "encrypted_index": "must-not-be-retained",
                    }
                ],
            }
        )
    value: dict[str, object] = {
        "id": "msg_synthetic_search",
        "stop_reason": stop_reason,
        "content": content,
    }
    if include_usage:
        value["usage"] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_creation_input_tokens": cache_creation_tokens,
            "cache_read_input_tokens": cache_read_tokens,
            "server_tool_use": {
                "web_search_requests": (
                    actual_actions
                    if reported_tool_calls is None
                    else reported_tool_calls
                )
            },
        }
    return json.dumps(value, sort_keys=True).encode("utf-8")


class V24240AnthropicServerSearchSingleAttemptTests(unittest.TestCase):
    credential = "synthetic-anthropic-credential-value"

    def setUp(self) -> None:
        self.contract = guidance_contract()
        self.policy, _, self.arms, self.sources = guidance(self.contract)
        self.arm = next(arm for arm in self.arms if arm["arm_name"] == "full")
        self.source = self.sources["full"]
        self.initial = initialize_effect_preauthorization_state(
            initial_budget_ledger=ledger(
                self.contract,
                self.policy,
                self.arm,
                self.source,
            ),
            **self.shared,
        )
        self.harness = self.new_harness()
        self.request = AnthropicServerSearchRequest(
            query="visible query one",
            max_output_tokens=200,
            max_uses=2,
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

    def new_harness(self) -> PreauthorizedEffectHarness:
        return PreauthorizedEffectHarness(self.initial, **self.harness_shared)

    @staticmethod
    def meter(
        *,
        max_attempts: int = 2,
        input_tokens: int = 2000,
        output_tokens: int = 400,
        other_tool_calls: int = 4,
        wall_milliseconds: int | None = None,
    ) -> dict[str, object]:
        return build_provider_meter_contract(
            provider_kind="anthropic_server_web_search",
            charge_kind="fanout_execution",
            max_attempts=max_attempts,
            reserved_cost=cost(
                search_calls=max_attempts,
                other_tool_calls=other_tool_calls,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                wall_milliseconds=(
                    max_attempts * 300_000
                    if wall_milliseconds is None
                    else wall_milliseconds
                ),
            ),
        )

    @classmethod
    def adapter(cls, post) -> AnthropicServerSearchSingleAttemptAdapter:
        return AnthropicServerSearchSingleAttemptAdapter(
            endpoint="https://api.anthropic.com/v1/messages",
            model="claude-haiku-4-5-20251001",
            anthropic_version="2023-06-01",
            credential=cls.credential,
            timeout_seconds=300,
            post=post,
        )

    def execute(
        self,
        meter,
        post,
        *,
        suffix: str,
        request: AnthropicServerSearchRequest | None = None,
        harness: PreauthorizedEffectHarness | None = None,
    ):
        active = self.harness if harness is None else harness
        return active.run_effect(
            meter_contract=meter,
            invocation_ref_sha256=digest("invocation-" + suffix),
            permit_ref_sha256=digest("permit-" + suffix),
            charge_ref_sha256=digest("charge-" + suffix),
            callback=self.adapter(post).bind(
                self.request if request is None else request,
                meter_contract=meter,
            ),
        )

    def test_success_is_one_post_and_ephemeral_value_is_typed(self) -> None:
        response = FakeResponse(200, response_bytes())
        post = RecordingPost(response)
        result = self.execute(
            self.meter(max_attempts=1, output_tokens=200, other_tool_calls=2),
            post,
            suffix="success",
        )
        self.assertEqual(result.receipt["logical_status"], "completed")
        self.assertEqual(result.receipt["attempt_count"], 1)
        self.assertIsInstance(result.value, AnthropicServerSearchAttemptValue)
        self.assertEqual(result.value.text, "private answer")
        self.assertEqual(result.value.usage["metered_input_tokens"], 115)
        self.assertEqual(result.value.usage["web_search_requests"], 1)
        self.assertEqual(len(result.value.actions), 1)
        self.assertEqual(len(result.value.results), 1)
        self.assertEqual(
            result.value.results[0].url,
            "https://example.com/source/0",
        )
        self.assertIn("utm_source=x", result.value.results[0].fetch_url)
        self.assertNotIn("encrypted", repr(result.value))
        attempt = result.receipt["measurement"]["attempts"][0]
        self.assertEqual(attempt["input_tokens"], 115)
        self.assertEqual(attempt["output_tokens"], 20)
        self.assertEqual(attempt["provider_tool_calls"], 1)
        self.assertEqual(
            result.receipt["observed_cost_lower_bound"]["other_tool_calls"],
            1,
        )
        self.assertEqual(len(post.calls), 1)
        call = post.calls[0]
        self.assertEqual(call["url"], "https://api.anthropic.com/v1/messages")
        self.assertEqual(call["headers"]["x-api-key"], self.credential)
        self.assertEqual(call["headers"]["anthropic-version"], "2023-06-01")
        self.assertFalse(call["allow_redirects"])
        self.assertTrue(call["verify"])
        body = json.loads(call["data"])
        self.assertEqual(body["messages"][0]["content"], "visible query one")
        self.assertEqual(body["tools"][0]["type"], "web_search_20250305")
        self.assertEqual(body["tools"][0]["max_uses"], 2)
        self.assertEqual(
            body["tool_choice"],
            {"type": "tool", "name": "web_search"},
        )
        self.assertNotIn(self.credential, call["data"].decode("utf-8"))
        encoded_receipt = json.dumps(result.receipt)
        for private in (
            self.credential,
            self.request.query,
            result.value.text,
            result.value.results[0].url,
            result.value.actions[0].query,
        ):
            self.assertNotIn(private, encoded_receipt)
        self.assertTrue(response.closed)

    def test_retryable_429_and_timeout_are_one_post_per_callback(self) -> None:
        first = FakeResponse(429, b'{"error":"private rate limit"}')
        second = FakeResponse(200, response_bytes())
        post = RecordingPost(first, second)
        result = self.execute(self.meter(), post, suffix="retry")
        self.assertEqual(result.receipt["attempt_count"], 2)
        attempts = result.receipt["measurement"]["attempts"]
        self.assertEqual(
            [item["outcome"] for item in attempts],
            ["retryable_http", "success"],
        )
        self.assertEqual(attempts[0]["token_usage_state"], "unavailable")
        self.assertEqual(attempts[1]["token_usage_state"], "observed")
        self.assertEqual(len(post.calls), 2)
        self.assertEqual(
            post.calls[0]["headers"]["X-DeepWide-Execution-Challenge"],
            post.calls[1]["headers"]["X-DeepWide-Execution-Challenge"],
        )
        self.assertNotEqual(
            post.calls[0]["headers"]["X-DeepWide-Attempt-Ref"],
            post.calls[1]["headers"]["X-DeepWide-Attempt-Ref"],
        )
        self.assertTrue(first.closed)
        self.assertTrue(second.closed)

        timeout_post = RecordingPost(
            requests.Timeout("private timeout"),
            FakeResponse(200, response_bytes()),
        )
        timeout_result = self.execute(
            self.meter(),
            timeout_post,
            suffix="timeout",
            harness=self.new_harness(),
        )
        self.assertEqual(
            [
                item["outcome"]
                for item in timeout_result.receipt["measurement"]["attempts"]
            ],
            ["transport_error", "success"],
        )
        self.assertEqual(len(timeout_post.calls), 2)

    def test_action_counter_mismatch_is_conservatively_charged_and_failed(self) -> None:
        post = RecordingPost(
            FakeResponse(200, response_bytes(action_count=1, reported_tool_calls=2))
        )
        result = self.execute(
            self.meter(max_attempts=1, output_tokens=200, other_tool_calls=2),
            post,
            suffix="counter-mismatch",
        )
        self.assertEqual(result.receipt["logical_status"], "failed")
        attempt = result.receipt["measurement"]["attempts"][0]
        self.assertEqual(attempt["outcome"], "invalid_json")
        self.assertEqual(attempt["provider_tool_usage_state"], "observed")
        self.assertEqual(attempt["provider_tool_calls"], 2)
        self.assertIsNone(result.value)

    def test_provider_max_uses_overrun_is_observed_then_settlement_fails(self) -> None:
        request = AnthropicServerSearchRequest(
            query="visible overrun query",
            max_output_tokens=200,
            max_uses=1,
        )
        post = RecordingPost(
            FakeResponse(200, response_bytes(action_count=2, reported_tool_calls=2))
        )
        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(
                self.meter(
                    max_attempts=1,
                    output_tokens=200,
                    other_tool_calls=1,
                ),
                post,
                suffix="tool-overrun",
                request=request,
            )
        receipt = caught.exception.receipt
        self.assertEqual(receipt["failure_phase"], "settlement_validation")
        self.assertEqual(receipt["attempts"][0]["provider_tool_calls"], 2)
        self.assertEqual(receipt["attempts"][0]["outcome"], "invalid_json")
        self.assertTrue(receipt["permit_remains_pending"])
        self.assertTrue(receipt["reservation_remains_charged"])
        self.assertEqual(len(post.calls), 1)

    def test_terminal_redirect_parse_usage_and_empty_fail_closed(self) -> None:
        terminal = self.execute(
            self.meter(max_attempts=1, output_tokens=200, other_tool_calls=2),
            RecordingPost(FakeResponse(401, b'{"error":"private auth"}')),
            suffix="terminal",
        )
        self.assertEqual(terminal.receipt["logical_status"], "failed")
        self.assertEqual(
            terminal.receipt["measurement"]["attempts"][0]["outcome"],
            "terminal_http",
        )

        redirect_response = FakeResponse(307, b"private redirect")
        with self.assertRaises(PreauthorizedEffectExecutionError) as redirect:
            self.execute(
                self.meter(max_attempts=1, output_tokens=200, other_tool_calls=2),
                RecordingPost(redirect_response),
                suffix="redirect",
                harness=self.new_harness(),
            )
        self.assertEqual(redirect.exception.receipt["failure_phase"], "callback_exception")
        self.assertTrue(redirect_response.closed)

        cases = (
            (b"not-json", "invalid_json"),
            (response_bytes(include_usage=False), "invalid_json"),
            (response_bytes(include_actions=False), "empty_output"),
            (response_bytes(include_results=False), "empty_output"),
            (response_bytes(include_text=False), "empty_output"),
            (response_bytes(text=""), "empty_output"),
        )
        for index, (content, expected) in enumerate(cases):
            with self.subTest(index=index, expected=expected):
                result = self.execute(
                    self.meter(
                        max_attempts=1,
                        output_tokens=200,
                        other_tool_calls=2,
                    ),
                    RecordingPost(FakeResponse(200, content)),
                    suffix=f"parse-{index}",
                    harness=self.new_harness(),
                )
                self.assertEqual(result.receipt["logical_status"], "failed")
                self.assertEqual(
                    result.receipt["measurement"]["attempts"][0]["outcome"],
                    expected,
                )

    def test_endpoint_credential_request_and_meter_validate_before_post(self) -> None:
        base = {
            "model": "claude-haiku-4-5-20251001",
            "anthropic_version": "2023-06-01",
            "credential": self.credential,
            "timeout_seconds": 300,
            "post": RecordingPost(),
        }
        for endpoint in (
            "http://api.anthropic.com/v1/messages",
            "https://api.anthropic.com:443/v1/messages",
            "https://attacker.invalid/v1/messages",
            "https://api.anthropic.com/v1/messages?x=1",
            "https://user:pass@api.anthropic.com/v1/messages",
        ):
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    AnthropicServerSearchSingleAttemptAdapter(
                        endpoint=endpoint,
                        **base,
                    )
        for override in (
            {"model": "other"},
            {"anthropic_version": "other"},
            {"credential": "bad\ncredential"},
        ):
            values = {**base, **override}
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    AnthropicServerSearchSingleAttemptAdapter(
                        endpoint="https://api.anthropic.com/v1/messages",
                        **values,
                    )

        post = RecordingPost()
        adapter = self.adapter(post)
        for request in (
            AnthropicServerSearchRequest(query="", max_output_tokens=200),
            AnthropicServerSearchRequest(query=" x ", max_output_tokens=200),
            AnthropicServerSearchRequest(query="x", max_output_tokens=0),
            AnthropicServerSearchRequest(query="x", max_output_tokens=200, max_uses=0),
            AnthropicServerSearchRequest(
                query="query " + self.credential,
                max_output_tokens=200,
            ),
        ):
            with self.subTest(request=request):
                with self.assertRaises(ValueError):
                    adapter.bind(request, meter_contract=self.meter())
        for meter in (
            self.meter(max_attempts=2, output_tokens=399),
            self.meter(max_attempts=2, other_tool_calls=3),
            self.meter(
                max_attempts=2,
                input_tokens=1,
                output_tokens=400,
                other_tool_calls=4,
            ),
            self.meter(
                max_attempts=1,
                output_tokens=200,
                other_tool_calls=2,
                wall_milliseconds=299_999,
            ),
        ):
            with self.assertRaisesRegex(ValueError, "reservation"):
                adapter.bind(self.request, meter_contract=meter)
        self.assertEqual(len(post.calls), 0)

    def test_default_session_direct_bypass_and_credential_echo_are_safe(self) -> None:
        fake_session = mock.Mock()
        fake_session.headers = {}
        fake_session.proxies = {}
        fake_session.cookies = mock.Mock()
        with mock.patch(
            "deepwide_agent.v24240_anthropic_server_search_single_attempt.requests.Session",
            return_value=fake_session,
        ):
            AnthropicServerSearchSingleAttemptAdapter(
                endpoint="https://api.anthropic.com/v1/messages",
                model="claude-haiku-4-5-20251001",
                anthropic_version="2023-06-01",
                credential=self.credential,
                timeout_seconds=300,
            )
        self.assertFalse(fake_session.trust_env)
        self.assertIsNone(fake_session.auth)
        fake_session.cookies.clear.assert_called_once_with()

        valid_meter = self.meter(
            max_attempts=1,
            output_tokens=200,
            other_tool_calls=2,
        )
        captured = None

        def callback(invocation):
            nonlocal captured
            captured = dict(invocation)
            raise RuntimeError("capture")

        with self.assertRaises(PreauthorizedEffectExecutionError):
            self.new_harness().run_effect(
                meter_contract=valid_meter,
                invocation_ref_sha256=digest("direct-invocation"),
                permit_ref_sha256=digest("direct-permit"),
                charge_ref_sha256=digest("direct-charge"),
                callback=callback,
            )
        post = RecordingPost()
        with self.assertRaisesRegex(ValueError, "reservation"):
            self.adapter(post).single_attempt(
                invocation=captured,
                request=self.request,
                meter_contract=self.meter(
                    max_attempts=1,
                    output_tokens=199,
                    other_tool_calls=2,
                ),
            )
        self.assertEqual(len(post.calls), 0)

        echo_response = FakeResponse(
            200,
            (b'{"echo":"' + self.credential.encode("ascii") + b'"}'),
        )
        with self.assertRaises(PreauthorizedEffectExecutionError) as echo:
            self.execute(
                valid_meter,
                RecordingPost(echo_response),
                suffix="credential-echo",
                harness=self.new_harness(),
            )
        self.assertEqual(echo.exception.receipt["failure_phase"], "callback_exception")
        self.assertEqual(echo.exception.receipt["attempts"], [])
        self.assertNotIn(self.credential, json.dumps(echo.exception.receipt))
        self.assertTrue(echo_response.closed)

    def test_truncation_and_authorization_limits_are_explicit(self) -> None:
        result = self.execute(
            self.meter(max_attempts=1, output_tokens=200, other_tool_calls=2),
            RecordingPost(
                FakeResponse(
                    200,
                    response_bytes(output_tokens=200, stop_reason="max_tokens"),
                )
            ),
            suffix="truncation",
        )
        self.assertTrue(result.value.output_truncated)

        for value in (
            CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
            EXACT_HTTPS_ENDPOINT_ENFORCED,
            CALLER_SUPPLIED_CREDENTIAL_REQUIRED,
            CREDENTIAL_RETAINED_IN_ADAPTER_MEMORY,
            CREDENTIAL_EXCLUDED_FROM_REQUEST_BODY,
            DIRECT_CREDENTIAL_ECHO_REJECTED_BEFORE_RESPONSE_HASH,
            REQUESTS_TRUST_ENV_DISABLED,
            PROVIDER_CHALLENGE_HEADER_SENT,
            PROVIDER_DECLARED_MAX_USES_SENT,
            PROVIDER_DECLARED_MAX_USES_VIOLATION_REJECTED_POST_EFFECT,
            OBSERVED_PROVIDER_TOOL_ACTIONS_METERED,
            PROVIDER_ACTION_COUNTER_CROSS_CHECKED,
            PROVIDER_ACTION_COUNTER_MISMATCH_FAILS_CLOSED,
            CACHE_TOKENS_INCLUDED_IN_METERED_INPUT,
            RESPONSE_CLOSE_ATTEMPTED,
            NOMINAL_TIMEOUT_OUTPUT_AND_TOOL_RESERVATION_CHECKED,
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
            PROVIDER_TOOL_ACTION_HARD_LIMIT_ENFORCED_PRE_EFFECT,
            PROVIDER_TOOL_ACTION_IS_PAGE_EVIDENCE,
            INPUT_TOKEN_RESERVATION_COVERAGE_PRE_EFFECT_PROVEN,
            RESPONSE_BODY_STREAM_CAP_IMPLEMENTED,
            RESPONSE_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED,
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
