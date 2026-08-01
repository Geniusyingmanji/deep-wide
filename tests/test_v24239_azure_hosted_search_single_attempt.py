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
from deepwide_agent.v24239_azure_hosted_search_single_attempt import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ARBITRARY_CALLER_HEADERS_ACCEPTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
    INTERNAL_RETRY_IMPLEMENTED,
    INPUT_TOKEN_RESERVATION_COVERAGE_PRE_EFFECT_PROVEN,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    LOOPBACK_ONLY_ENDPOINT_ENFORCED,
    MULTI_QUERY_MARKER_COVERAGE_VALIDATED_BY_ADAPTER,
    NOMINAL_TIMEOUT_AND_OUTPUT_RESERVATION_CHECKED,
    OBSERVED_PROVIDER_TOOL_ACTIONS_METERED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
    PROVIDER_CHALLENGE_HEADER_SENT,
    PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED,
    PROVIDER_TOOL_ACTION_HARD_LIMIT_ENFORCED_PRE_EFFECT,
    PROVIDER_TOOL_ACTION_IS_PAGE_EVIDENCE,
    REDIRECT_FOLLOWING_IMPLEMENTED,
    RESPONSE_BODY_STREAM_CAP_IMPLEMENTED,
    RESPONSE_CLOSE_ATTEMPTED,
    RESPONSE_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED,
    REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE,
    REQUESTS_TRUST_ENV_DISABLED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    AzureHostedSearchAttemptValue,
    AzureHostedSearchRequest,
    AzureHostedSearchSingleAttemptAdapter,
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
    text: str = "[[QUERY Q0001]] private answer [[END Q0001]]",
    input_tokens: int = 100,
    output_tokens: int = 20,
    action_count: int = 1,
    include_usage: bool = True,
    include_actions: bool = True,
    include_message: bool = True,
) -> bytes:
    output: list[dict[str, object]] = []
    if include_actions:
        for index in range(action_count):
            output.append(
                {
                    "type": "web_search_call",
                    "id": f"ws_synthetic_{index}",
                    "status": "completed",
                    "action": {
                        "type": "search",
                        "query": f"private provider query {index}",
                        "queries": [f"private provider query {index}"],
                        "sources": [
                            {
                                "type": "url",
                                "url": f"https://Example.COM/source/{index}?utm_source=x#frag",
                                "title": f"Private source {index}",
                            }
                        ],
                    },
                }
            )
    if include_message:
        output.append(
            {
                "type": "message",
                "content": [
                    {
                        "type": "output_text",
                        "text": text,
                        "annotations": [
                            {
                                "type": "url_citation",
                                "url": "https://Example.COM/source/0?utm_source=x#frag",
                                "title": "Private citation",
                                "start_index": 0,
                                "end_index": min(10, len(text)),
                            }
                        ],
                    }
                ],
            }
        )
    value: dict[str, object] = {
        "id": "resp_synthetic_search",
        "status": "completed",
        "output": output,
    }
    if include_usage:
        value["usage"] = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
    return json.dumps(value, sort_keys=True).encode("utf-8")


class V24239AzureHostedSearchSingleAttemptTests(unittest.TestCase):
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
        self.request = AzureHostedSearchRequest(
            queries=("visible query one",),
            max_output_tokens=200,
            search_context_size="medium",
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

    def new_harness(self) -> PreauthorizedEffectHarness:
        return PreauthorizedEffectHarness(self.initial, **self.harness_shared)

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
        input_tokens: int = 2000,
        output_tokens: int = 400,
        other_tool_calls: int = 4,
        wall_milliseconds: int | None = None,
    ) -> dict[str, object]:
        return build_provider_meter_contract(
            provider_kind="azure_responses_web_search",
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

    @staticmethod
    def adapter(post) -> AzureHostedSearchSingleAttemptAdapter:
        return AzureHostedSearchSingleAttemptAdapter(
            endpoint="http://127.0.0.1:9878/responses",
            model="gpt-5.6-sol",
            timeout_seconds=300,
            post=post,
        )

    def execute(self, meter, post, *, suffix: str = "1", request=None):
        adapter = self.adapter(post)
        return self.new_harness().run_effect(
            meter_contract=meter,
            invocation_ref_sha256=digest(f"invocation-{suffix}"),
            permit_ref_sha256=digest(f"permit-{suffix}"),
            charge_ref_sha256=digest(f"charge-{suffix}"),
            callback=adapter.bind(
                self.request if request is None else request,
                meter_contract=meter,
            ),
        )

    def test_success_is_one_post_and_ephemeral_hosted_value_is_typed(self) -> None:
        body = response_bytes(action_count=2)
        response = FakeResponse(200, body)
        post = RecordingPost(response)
        result = self.execute(self.meter(other_tool_calls=4), post)
        self.assertEqual(len(post.calls), 1)
        self.assertTrue(response.closed)
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
        self.assertEqual(
            sent["tools"],
            [{"type": "web_search", "search_context_size": "medium"}],
        )
        self.assertEqual(sent["tool_choice"], "required")
        self.assertEqual(sent["include"], ["web_search_call.action.sources"])
        self.assertIsInstance(result.value, AzureHostedSearchAttemptValue)
        self.assertEqual(len(result.value.actions), 2)
        self.assertEqual(len(result.value.citations), 1)
        self.assertEqual(
            result.value.actions[0].sources[0].url,
            "https://example.com/source/0",
        )
        self.assertEqual(result.value.usage["total_tokens"], 120)
        receipt = repr(result.receipt)
        for private in (
            self.request.queries[0],
            "private answer",
            "private provider query",
            "example.com",
        ):
            self.assertNotIn(private, receipt)
        attempt = result.receipt["measurement"]["attempts"][0]
        self.assertEqual(attempt["provider_tool_usage_state"], "observed")
        self.assertEqual(attempt["provider_tool_calls"], 2)
        self.assertEqual(attempt["input_tokens"], 100)
        self.assertEqual(attempt["output_tokens"], 20)
        self.assertEqual(attempt["response_body_bytes"], len(body))
        self.assertEqual(result.receipt["settlement_cost"]["search_calls"], 1)
        self.assertEqual(result.receipt["settlement_cost"]["other_tool_calls"], 2)

    def test_retryable_429_and_timeout_are_one_post_per_callback(self) -> None:
        cases = (
            (
                RecordingPost(
                    FakeResponse(429, b'{"error":"private rate"}'),
                    FakeResponse(200, response_bytes()),
                ),
                ["retryable_http", "success"],
            ),
            (
                RecordingPost(
                    requests.Timeout("private timeout"),
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
                        attempt["outcome"]
                        for attempt in result.receipt["measurement"]["attempts"]
                    ],
                    outcomes,
                )
                first = result.receipt["measurement"]["attempts"][0]
                self.assertEqual(first["token_usage_state"], "unavailable")
                self.assertEqual(first["provider_tool_usage_state"], "unavailable")
                self.assertTrue(result.receipt["reservation_fallback_applied"])
                self.assertNotIn("private timeout", repr(result.receipt))

    def test_provider_tool_overrun_is_observed_then_settlement_fails_closed(self) -> None:
        post = RecordingPost(FakeResponse(200, response_bytes(action_count=2)))
        meter = self.meter(
            max_attempts=1,
            output_tokens=200,
            other_tool_calls=1,
            wall_milliseconds=300_000,
        )
        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(meter, post, suffix="overrun")
        self.assertEqual(len(post.calls), 1)
        receipt = caught.exception.receipt
        self.assertEqual(receipt["failure_phase"], "settlement_validation")
        self.assertTrue(receipt["permit_remains_pending"])
        self.assertTrue(receipt["reservation_remains_charged"])
        self.assertEqual(receipt["attempts"][0]["provider_tool_calls"], 2)

    def test_terminal_redirect_parse_usage_actions_and_empty_fail_closed(self) -> None:
        terminal = self.execute(
            self.meter(max_attempts=1, output_tokens=200, other_tool_calls=1),
            RecordingPost(FakeResponse(400, b'{"error":"private bad"}')),
            suffix="terminal",
        )
        self.assertEqual(terminal.receipt["logical_status"], "failed")
        self.assertEqual(
            terminal.receipt["measurement"]["attempts"][0]["outcome"],
            "terminal_http",
        )

        redirect = RecordingPost(FakeResponse(307, b"private redirect"))
        with self.assertRaises(PreauthorizedEffectExecutionError) as redirect_caught:
            self.execute(
                self.meter(max_attempts=1, output_tokens=200, other_tool_calls=1),
                redirect,
                suffix="redirect",
            )
        self.assertEqual(
            redirect_caught.exception.receipt["failure_phase"],
            "callback_exception",
        )

        cases = (
            (b"not-json", "invalid_json"),
            (response_bytes(include_usage=False), "invalid_json"),
            (response_bytes(include_actions=False), "empty_output"),
            (response_bytes(include_message=False), "empty_output"),
            (response_bytes(text=""), "empty_output"),
        )
        for index, (content, expected) in enumerate(cases):
            with self.subTest(index=index, expected=expected):
                result = self.execute(
                    self.meter(
                        max_attempts=1,
                        output_tokens=200,
                        other_tool_calls=1,
                    ),
                    RecordingPost(FakeResponse(200, content)),
                    suffix=f"parse-{index}",
                )
                self.assertEqual(result.receipt["logical_status"], "failed")
                self.assertEqual(
                    result.receipt["measurement"]["attempts"][0]["outcome"],
                    expected,
                )

    def test_endpoint_request_and_meter_validate_before_post(self) -> None:
        invalid_endpoints = (
            "https://127.0.0.1:9878/responses",
            "http://localhost:9878/responses",
            "http://127.0.0.1:9878/responses?x=1",
            "http://user:pass@127.0.0.1:9878/responses",
            "http://127.0.0.1:9878/other",
        )
        for endpoint in invalid_endpoints:
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(ValueError):
                    AzureHostedSearchSingleAttemptAdapter(
                        endpoint=endpoint,
                        model="gpt-5.6-sol",
                        timeout_seconds=300,
                        post=RecordingPost(),
                    )
        post = RecordingPost()
        adapter = self.adapter(post)
        for request in (
            AzureHostedSearchRequest(queries=(), max_output_tokens=200),
            AzureHostedSearchRequest(queries=("",), max_output_tokens=200),
            AzureHostedSearchRequest(queries=(" x ",), max_output_tokens=200),
            AzureHostedSearchRequest(queries=("same", " same"), max_output_tokens=200),
            AzureHostedSearchRequest(queries=("x",), max_output_tokens=0),
            AzureHostedSearchRequest(
                queries=("x",),
                max_output_tokens=200,
                search_context_size="unknown",
            ),
        ):
            with self.subTest(request=request):
                with self.assertRaises(ValueError):
                    adapter.bind(request, meter_contract=self.meter())
        under_output = self.meter(max_attempts=2, output_tokens=399)
        with self.assertRaisesRegex(ValueError, "reservation"):
            adapter.bind(self.request, meter_contract=under_output)
        under_wall = self.meter(max_attempts=1, output_tokens=200, wall_milliseconds=299_999)
        with self.assertRaisesRegex(ValueError, "reservation"):
            adapter.bind(self.request, meter_contract=under_wall)
        self.assertEqual(len(post.calls), 0)

    def test_default_session_and_public_single_attempt_bypass_are_safe(self) -> None:
        fake_session = mock.Mock()
        fake_session.headers = {}
        fake_session.proxies = {}
        fake_session.cookies = mock.Mock()
        with mock.patch(
            "deepwide_agent.v24239_azure_hosted_search_single_attempt.requests.Session",
            return_value=fake_session,
        ):
            adapter = AzureHostedSearchSingleAttemptAdapter(
                endpoint="http://127.0.0.1:9878/responses",
                model="gpt-5.6-sol",
                timeout_seconds=300,
            )
        self.assertFalse(fake_session.trust_env)
        self.assertIsNone(fake_session.auth)
        fake_session.cookies.clear.assert_called_once_with()

        valid_meter = self.meter(
            max_attempts=1,
            output_tokens=200,
            other_tool_calls=1,
        )
        under_output = self.meter(
            max_attempts=1,
            output_tokens=199,
            other_tool_calls=1,
        )
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
        post = RecordingPost()
        direct = self.adapter(post)
        with self.assertRaisesRegex(ValueError, "reservation"):
            direct.single_attempt(
                invocation=captured,
                request=self.request,
                meter_contract=under_output,
            )
        self.assertEqual(len(post.calls), 0)

    def test_authorization_capability_and_provider_limit_are_explicit(self) -> None:
        for value in (
            CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY,
            LOOPBACK_ONLY_ENDPOINT_ENFORCED,
            REQUESTS_TRUST_ENV_DISABLED,
            PROVIDER_CHALLENGE_HEADER_SENT,
            OBSERVED_PROVIDER_TOOL_ACTIONS_METERED,
            RESPONSE_CLOSE_ATTEMPTED,
            NOMINAL_TIMEOUT_AND_OUTPUT_RESERVATION_CHECKED,
        ):
            self.assertTrue(value)
        for value in (
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            INTERNAL_RETRY_IMPLEMENTED,
            REDIRECT_FOLLOWING_IMPLEMENTED,
            ARBITRARY_CALLER_HEADERS_ACCEPTED,
            ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED,
            PROVIDER_TOOL_ACTION_HARD_LIMIT_ENFORCED_PRE_EFFECT,
            PROVIDER_TOOL_ACTION_IS_PAGE_EVIDENCE,
            INPUT_TOKEN_RESERVATION_COVERAGE_PRE_EFFECT_PROVEN,
            MULTI_QUERY_MARKER_COVERAGE_VALIDATED_BY_ADAPTER,
            RESPONSE_BODY_STREAM_CAP_IMPLEMENTED,
            RESPONSE_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED,
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
