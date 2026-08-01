"""Isolated one-HTTP-attempt adapter for a local Responses-compatible proxy.

The active DeepWide Responses client owns its own retry loop, so placing that
client behind the V2.42.35 callback would hide several HTTP attempts inside a
single metered attempt.  This candidate adapter performs exactly one
``POST`` per callback invocation, disables redirects, and maps the resulting
transport/HTTP/JSON/usage state into the V2.42.35 sanitized observation.

Raw prompts and response text are ephemeral callback inputs/outputs.  They are
not copied into the V2.42.35 receipt.  This module has real network capability
when explicitly instantiated, but it is not imported by the active clients,
runtime, runner, launcher, or benchmark chain.  Tests and the build audit use
an injected fake ``post`` callable and perform no network request.
"""

from __future__ import annotations

import dataclasses
import hashlib
import ipaddress
import json
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

import requests

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24234_provider_cost_meter import validate_provider_meter_contract
from deepwide_agent.v24235_preauthorized_effect_harness import (
    ATTEMPT_INVOCATION_KEYS,
    ProviderAttemptResult,
    build_provider_attempt_observation,
)


POLICY_ID = "v24236_azure_responses_single_attempt_v1"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY = True
LOOPBACK_ONLY_ENDPOINT_ENFORCED = True
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
INTERNAL_RETRY_IMPLEMENTED = False
REDIRECT_FOLLOWING_IMPLEMENTED = False
ARBITRARY_CALLER_HEADERS_ACCEPTED = False
ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED = False
REQUESTS_TRUST_ENV_DISABLED = True
PROVIDER_CHALLENGE_HEADER_SENT = True
PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED = False
PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED = False
NOMINAL_TIMEOUT_AND_OUTPUT_RESERVATION_CHECKED = True
REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE = False

MAX_TEXT_CHARS = 4_000_000
MAX_OUTPUT_TOKENS = 1_000_000
MAX_TIMEOUT_SECONDS = 3600
ALLOWED_ENDPOINT = "http://127.0.0.1:9878/responses"
ALLOWED_MODEL = "gpt-5.6-sol"
REASONING_EFFORTS = frozenset({"", "low", "medium", "high"})
SERVICE_TIERS = frozenset({"", "auto", "default", "flex", "priority"})


class AzureResponsesSingleAttemptError(RuntimeError):
    """Safe adapter error that never embeds endpoint or provider content."""


@dataclasses.dataclass(frozen=True)
class AzureResponsesRequest:
    system: str
    user: str
    max_output_tokens: int
    json_mode: bool = False
    reasoning_effort: str = "high"
    service_tier: str = "priority"


@dataclasses.dataclass(frozen=True)
class AzureResponsesAttemptValue:
    text: str
    usage: Mapping[str, int]
    response_id: str | None
    output_truncated: bool


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _integer(
    value: object,
    *,
    label: str,
    minimum: int,
    maximum: int,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"V2.42.36 {label} is outside the frozen range")
    return value


def _validate_endpoint(endpoint: str) -> str:
    if not isinstance(endpoint, str) or not endpoint:
        raise ValueError("V2.42.36 endpoint is invalid")
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
        address = ipaddress.ip_address(parsed.hostname or "")
    except ValueError as error:
        raise ValueError("V2.42.36 endpoint is invalid") from error
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or not address.is_loopback
        or port is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path.rstrip("/") != "/responses"
        or not 1 <= port <= 65535
        or endpoint != ALLOWED_ENDPOINT
    ):
        raise ValueError("V2.42.36 endpoint is outside the frozen Responses shape")
    return endpoint


def _validate_request(request: AzureResponsesRequest) -> AzureResponsesRequest:
    if not isinstance(request, AzureResponsesRequest):
        raise ValueError("V2.42.36 request type is invalid")
    if (
        not isinstance(request.system, str)
        or not isinstance(request.user, str)
        or not request.system
        or not request.user
        or len(request.system) > MAX_TEXT_CHARS
        or len(request.user) > MAX_TEXT_CHARS
    ):
        raise ValueError("V2.42.36 prompt text is outside the frozen range")
    _integer(
        request.max_output_tokens,
        label="max output tokens",
        minimum=1,
        maximum=MAX_OUTPUT_TOKENS,
    )
    if not isinstance(request.json_mode, bool):
        raise ValueError("V2.42.36 json mode is invalid")
    if request.reasoning_effort not in REASONING_EFFORTS:
        raise ValueError("V2.42.36 reasoning effort is invalid")
    if request.service_tier not in SERVICE_TIERS:
        raise ValueError("V2.42.36 service tier is invalid")
    return request


def _validate_invocation(
    invocation: Mapping[str, Any], *, meter_contract: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(invocation, Mapping) or set(invocation) != ATTEMPT_INVOCATION_KEYS:
        raise ValueError("V2.42.36 invocation schema is not exact")
    value = dict(invocation)
    seal = value.pop("attempt_invocation_sha256", None)
    if (
        not _is_sha256(seal)
        or seal != object_sha256(value)
        or invocation.get("provider_kind") != "azure_responses_model"
        or invocation.get("effect_kind") != "model_request"
        or invocation.get("meter_contract_sha256")
        != meter_contract["contract_sha256"]
        or invocation.get("raw_request_or_response_content_present") is not False
        or invocation.get("credential_or_url_present") is not False
        or invocation.get("benchmark_or_evaluator_metadata_present") is not False
    ):
        raise ValueError("V2.42.36 invocation binding drifted")
    return dict(invocation)


def _request_body(
    *, adapter_model: str, request: AzureResponsesRequest
) -> tuple[dict[str, Any], bytes]:
    body: dict[str, Any] = {
        "model": adapter_model,
        "input": [
            {"role": "system", "content": request.system},
            {"role": "user", "content": request.user},
        ],
        "max_output_tokens": request.max_output_tokens,
    }
    if request.reasoning_effort:
        body["reasoning"] = {"effort": request.reasoning_effort}
    if request.service_tier:
        body["service_tier"] = request.service_tier
    if request.json_mode:
        body["text"] = {"format": {"type": "json_object"}}
    encoded = json.dumps(
        body,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return body, encoded


def _response_text(payload: Mapping[str, Any]) -> str:
    chunks: list[str] = []
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, Mapping) or item.get("type") != "message":
                continue
            content = item.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if (
                    isinstance(block, Mapping)
                    and block.get("type") in {"output_text", "text"}
                    and isinstance(block.get("text"), str)
                ):
                    chunks.append(str(block["text"]))
    if chunks:
        return "\n".join(chunks).strip()
    fallback = payload.get("output_text")
    return fallback.strip() if isinstance(fallback, str) else ""


def _usage(payload: Mapping[str, Any]) -> tuple[str, int | None, int | None, dict[str, int]]:
    source = payload.get("usage")
    if not isinstance(source, Mapping):
        return "unavailable", None, None, {}
    try:
        input_tokens = _integer(
            source.get("input_tokens"),
            label="input tokens",
            minimum=0,
            maximum=1_000_000_000_000_000,
        )
        output_tokens = _integer(
            source.get("output_tokens"),
            label="output tokens",
            minimum=0,
            maximum=1_000_000_000_000_000,
        )
    except ValueError:
        return "unavailable", None, None, {}
    total_source = source.get("total_tokens")
    if total_source is None:
        total_tokens = input_tokens + output_tokens
    else:
        try:
            total_tokens = _integer(
                total_source,
                label="total tokens",
                minimum=0,
                maximum=1_000_000_000_000_000,
            )
        except ValueError:
            total_tokens = input_tokens + output_tokens
    return (
        "observed",
        input_tokens,
        output_tokens,
        {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        },
    )


def _decode_payload(content: bytes) -> Mapping[str, Any] | None:
    try:
        value = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, Mapping) else None


def _output_truncated(
    payload: Mapping[str, Any], *, output_tokens: int, max_output_tokens: int
) -> bool:
    details = payload.get("incomplete_details")
    reason = (
        str(details.get("reason", "")).casefold()
        if isinstance(details, Mapping)
        else ""
    )
    return bool(
        str(payload.get("status", "")).casefold() == "incomplete"
        or reason in {"max_output_tokens", "max_tokens", "length"}
        or output_tokens >= max_output_tokens
    )


def _validate_meter_compatibility(
    meter_contract: Mapping[str, Any],
    *,
    request: AzureResponsesRequest,
    timeout_seconds: int,
) -> dict[str, Any]:
    validate_provider_meter_contract(meter_contract)
    contract = dict(meter_contract)
    if (
        contract["provider_kind"] != "azure_responses_model"
        or contract["effect_kind"] != "model_request"
        or int(contract["reserved_cost"]["output_tokens"])
        < request.max_output_tokens
        or int(contract["reserved_cost"]["wall_milliseconds"])
        < int(contract["max_attempts"]) * timeout_seconds * 1000
    ):
        raise ValueError("V2.42.36 meter reservation is not adapter-compatible")
    return contract


class AzureResponsesSingleAttemptAdapter:
    """Bind ephemeral request content to one metered callback POST."""

    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        timeout_seconds: int,
        post: Callable[..., Any] | None = None,
    ) -> None:
        self._endpoint = _validate_endpoint(endpoint)
        if model != ALLOWED_MODEL:
            raise ValueError("V2.42.36 model name is invalid")
        self._model = model
        self._timeout_seconds = _integer(
            timeout_seconds,
            label="timeout seconds",
            minimum=1,
            maximum=MAX_TIMEOUT_SECONDS,
        )
        self._session: requests.Session | None = None
        if post is None:
            session = requests.Session()
            session.trust_env = False
            session.auth = None
            session.headers.clear()
            session.proxies.clear()
            session.cookies.clear()
            self._session = session
            self._post = session.post
        else:
            self._post = post
        if not callable(self._post):
            raise ValueError("V2.42.36 post transport is not callable")

    def bind(
        self,
        request: AzureResponsesRequest,
        *,
        meter_contract: Mapping[str, Any],
    ) -> Callable[[Mapping[str, Any]], ProviderAttemptResult]:
        frozen = _validate_request(request)
        contract = _validate_meter_compatibility(
            meter_contract,
            request=frozen,
            timeout_seconds=self._timeout_seconds,
        )

        def callback(invocation: Mapping[str, Any]) -> ProviderAttemptResult:
            return self.single_attempt(
                invocation=invocation,
                request=frozen,
                meter_contract=contract,
            )

        return callback

    def single_attempt(
        self,
        *,
        invocation: Mapping[str, Any],
        request: AzureResponsesRequest,
        meter_contract: Mapping[str, Any],
    ) -> ProviderAttemptResult:
        frozen = _validate_request(request)
        contract = _validate_meter_compatibility(
            meter_contract,
            request=frozen,
            timeout_seconds=self._timeout_seconds,
        )
        bound = _validate_invocation(
            invocation,
            meter_contract=contract,
        )
        _body, encoded = _request_body(adapter_model=self._model, request=frozen)
        headers = {
            "Content-Type": "application/json",
            "X-DeepWide-Execution-Challenge": str(
                bound["execution_challenge_sha256"]
            ),
            "X-DeepWide-Attempt-Ref": str(bound["attempt_ref_sha256"]),
        }
        try:
            response = self._post(
                self._endpoint,
                headers=headers,
                data=encoded,
                timeout=self._timeout_seconds,
                allow_redirects=False,
            )
        except (requests.ConnectionError, requests.Timeout):
            observation = build_provider_attempt_observation(
                invocation=bound,
                outcome="transport_error",
                http_status=None,
                provider_response_ref_sha256=None,
                token_usage_state="unavailable",
                input_tokens=None,
                output_tokens=None,
                provider_tool_usage_state="not_applicable",
                provider_tool_calls=None,
                request_body_bytes=len(encoded),
                response_body_bytes=None,
            )
            return ProviderAttemptResult(observation=observation, value=None)
        except requests.RequestException:
            raise AzureResponsesSingleAttemptError(
                "single Responses POST failed outside the typed transport class"
            ) from None

        try:
            status = response.status_code
        except AttributeError:
            raise AzureResponsesSingleAttemptError(
                "single Responses POST response interface is invalid"
            ) from None
        if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
            raise AzureResponsesSingleAttemptError(
                "single Responses POST returned an invalid HTTP status"
            )
        try:
            content = bytes(response.content)
        except Exception:
            raise AzureResponsesSingleAttemptError(
                "single Responses POST response bytes are unavailable"
            ) from None
        response_ref = hashlib.sha256(content).hexdigest()
        payload = _decode_payload(content)
        token_state, input_tokens, output_tokens, usage = (
            _usage(payload) if payload is not None else ("unavailable", None, None, {})
        )

        if status in {408, 409, 429} or status >= 500:
            outcome = "retryable_http"
            value = None
        elif 400 <= status < 500:
            outcome = "terminal_http"
            value = None
        elif 300 <= status < 400:
            raise AzureResponsesSingleAttemptError(
                "single Responses POST redirect was rejected"
            )
        elif 200 <= status < 300:
            text = _response_text(payload) if payload is not None else ""
            if payload is None:
                outcome = "invalid_json"
                value = None
            elif not text:
                outcome = "empty_output"
                value = None
            elif (
                token_state != "observed"
                or int(input_tokens or 0) + int(output_tokens or 0) < 1
            ):
                # Valid JSON with a missing/invalid required usage object is an
                # invalid Responses contract, not a zero-token success.
                outcome = "invalid_json"
                value = None
            else:
                outcome = "success"
                response_id = payload.get("id")
                value = AzureResponsesAttemptValue(
                    text=text,
                    usage=usage,
                    response_id=(
                        str(response_id) if isinstance(response_id, str) else None
                    ),
                    output_truncated=_output_truncated(
                        payload,
                        output_tokens=int(output_tokens),
                        max_output_tokens=frozen.max_output_tokens,
                    ),
                )
        else:
            raise AzureResponsesSingleAttemptError(
                "single Responses POST informational status was rejected"
            )

        observation = build_provider_attempt_observation(
            invocation=bound,
            outcome=outcome,
            http_status=status,
            provider_response_ref_sha256=response_ref,
            token_usage_state=token_state,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_tool_usage_state="not_applicable",
            provider_tool_calls=None,
            request_body_bytes=len(encoded),
            response_body_bytes=len(content),
        )
        return ProviderAttemptResult(observation=observation, value=value)
