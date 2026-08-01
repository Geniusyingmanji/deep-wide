"""Isolated one-HTTP-attempt adapter for the Tavily Search API.

The active Tavily client owns key rotation and retry internally.  Passing it
directly to the V2.42.35 harness would therefore hide multiple HTTP attempts
inside one metered callback.  This candidate maps one callback to exactly one
``POST`` and selects a distinct caller-supplied credential by the sealed
attempt index.  Credentials are sent only in the ephemeral Authorization
header: they are absent from the canonical request body and from receipts.

This module has external network capability when explicitly instantiated.  It
is not imported by active clients, runtime, runner, launcher, or benchmark
code.  Tests and the build audit inject a fake ``post`` callable and perform
no socket or provider request.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

import requests

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24234_provider_cost_meter import validate_provider_meter_contract
from deepwide_agent.v24235_preauthorized_effect_harness import (
    ATTEMPT_INVOCATION_KEYS,
    ProviderAttemptResult,
    build_provider_attempt_observation,
)


POLICY_ID = "v24237_tavily_search_single_attempt_v1"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY = True
EXACT_HTTPS_ENDPOINT_ENFORCED = True
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
INTERNAL_RETRY_IMPLEMENTED = False
REDIRECT_FOLLOWING_IMPLEMENTED = False
ARBITRARY_CALLER_HEADERS_ACCEPTED = False
ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED = False
CALLER_SUPPLIED_CREDENTIAL_REQUIRED = True
CREDENTIAL_RETAINED_IN_ADAPTER_MEMORY = True
CREDENTIAL_DURABLY_PERSISTED_HASHED_OR_EMITTED = False
CREDENTIAL_EXCLUDED_FROM_REQUEST_BODY = True
DIRECT_CREDENTIAL_ECHO_REJECTED_BEFORE_RESPONSE_HASH = True
REQUESTS_TRUST_ENV_DISABLED = True
TLS_VERIFICATION_DISABLED = False
PROVIDER_CHALLENGE_HEADER_SENT = True
PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED = False
PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED = False
NOMINAL_TIMEOUT_RESERVATION_CHECKED = True
REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE = False

ALLOWED_ENDPOINT = "https://api.tavily.com/search"
SEARCH_DEPTHS = frozenset({"basic", "advanced", "fast", "ultra-fast"})
MAX_TIMEOUT_SECONDS = 3600
MAX_QUERY_CHARS = 32_768
MAX_RESULTS = 20
MAX_RESPONSE_BYTES = 32_000_000
MAX_FIELD_CHARS = 4_000_000
MIN_CREDENTIAL_CHARS = 8
MAX_CREDENTIAL_CHARS = 1024


class TavilySearchSingleAttemptError(RuntimeError):
    """Safe adapter error that never embeds credential or provider content."""


@dataclasses.dataclass(frozen=True)
class TavilySearchRequest:
    query: str
    max_results: int
    search_depth: str = "advanced"
    include_raw_content: bool = True
    include_answer: bool = True


@dataclasses.dataclass(frozen=True)
class TavilySearchResultValue:
    title: str
    url: str
    content: str
    raw_content: str
    score: float | None


@dataclasses.dataclass(frozen=True)
class TavilySearchAttemptValue:
    query: str
    answer: str
    results: tuple[TavilySearchResultValue, ...]


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
        raise ValueError(f"V2.42.37 {label} is outside the frozen range")
    return value


def _validate_endpoint(endpoint: str) -> str:
    if not isinstance(endpoint, str) or endpoint != ALLOWED_ENDPOINT:
        raise ValueError("V2.42.37 endpoint is outside the frozen Tavily shape")
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as error:
        raise ValueError("V2.42.37 endpoint is invalid") from error
    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.tavily.com"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.path != "/search"
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("V2.42.37 endpoint is outside the frozen Tavily shape")
    return endpoint


def _validate_credentials(credentials: Sequence[str]) -> tuple[str, ...]:
    if isinstance(credentials, (str, bytes)) or not isinstance(credentials, Sequence):
        raise ValueError("V2.42.37 credentials must be a sequence")
    frozen = tuple(credentials)
    if not frozen or len(frozen) > 64:
        raise ValueError("V2.42.37 credential count is outside the frozen range")
    for credential in frozen:
        if (
            not isinstance(credential, str)
            or not MIN_CREDENTIAL_CHARS <= len(credential) <= MAX_CREDENTIAL_CHARS
            or not credential.isascii()
            or any(
                not (
                    character.isalnum()
                    or character in {"-", "_", "."}
                )
                for character in credential
            )
        ):
            raise ValueError("V2.42.37 caller credential is invalid")
    if len(set(frozen)) != len(frozen):
        raise ValueError("V2.42.37 caller credentials must be distinct")
    return frozen


def _validate_request(request: TavilySearchRequest) -> TavilySearchRequest:
    if not isinstance(request, TavilySearchRequest):
        raise ValueError("V2.42.37 request type is invalid")
    if (
        not isinstance(request.query, str)
        or not request.query.strip()
        or request.query != request.query.strip()
        or len(request.query) > MAX_QUERY_CHARS
    ):
        raise ValueError("V2.42.37 query is outside the frozen range")
    _integer(
        request.max_results,
        label="max results",
        minimum=1,
        maximum=MAX_RESULTS,
    )
    if request.search_depth not in SEARCH_DEPTHS:
        raise ValueError("V2.42.37 search depth is invalid")
    if not isinstance(request.include_raw_content, bool) or not isinstance(
        request.include_answer, bool
    ):
        raise ValueError("V2.42.37 inclusion flag is invalid")
    return request


def _validate_request_credential_separation(
    request: TavilySearchRequest, *, credentials: Sequence[str]
) -> None:
    if any(credential in request.query for credential in credentials):
        raise ValueError("V2.42.37 query contains a caller credential")


def _validate_invocation(
    invocation: Mapping[str, Any], *, meter_contract: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(invocation, Mapping) or set(invocation) != ATTEMPT_INVOCATION_KEYS:
        raise ValueError("V2.42.37 invocation schema is not exact")
    value = dict(invocation)
    seal = value.pop("attempt_invocation_sha256", None)
    if (
        not _is_sha256(seal)
        or seal != object_sha256(value)
        or invocation.get("provider_kind") != "tavily_search_api"
        or invocation.get("effect_kind") != "search_request"
        or invocation.get("meter_contract_sha256")
        != meter_contract["contract_sha256"]
        or invocation.get("raw_request_or_response_content_present") is not False
        or invocation.get("credential_or_url_present") is not False
        or invocation.get("benchmark_or_evaluator_metadata_present") is not False
    ):
        raise ValueError("V2.42.37 invocation binding drifted")
    return dict(invocation)


def _validate_meter_compatibility(
    meter_contract: Mapping[str, Any],
    *,
    credential_count: int,
    timeout_seconds: int,
) -> dict[str, Any]:
    validate_provider_meter_contract(meter_contract)
    contract = dict(meter_contract)
    if (
        contract["provider_kind"] != "tavily_search_api"
        or contract["effect_kind"] != "search_request"
        or credential_count < int(contract["max_attempts"])
        or int(contract["reserved_cost"]["wall_milliseconds"])
        < int(contract["max_attempts"]) * timeout_seconds * 1000
    ):
        raise ValueError("V2.42.37 meter reservation is not adapter-compatible")
    return contract


def _request_body(request: TavilySearchRequest) -> tuple[dict[str, Any], bytes]:
    body: dict[str, Any] = {
        "query": request.query,
        "search_depth": request.search_depth,
        "max_results": request.max_results,
        "include_answer": request.include_answer,
        "include_raw_content": request.include_raw_content,
    }
    encoded = json.dumps(
        body,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return body, encoded


def _canonical_url(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 8192:
        return ""
    try:
        parsed = urlsplit(value)
        _ = parsed.port
    except ValueError:
        return ""
    if (
        parsed.scheme.casefold() not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        return ""
    return urlunsplit(
        (
            parsed.scheme.casefold(),
            parsed.netloc.casefold(),
            parsed.path or "/",
            parsed.query,
            "",
        )
    )


def _bounded_text(value: object, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return ""
    if not isinstance(value, str) or len(value) > MAX_FIELD_CHARS:
        return None
    return value


def _optional_score(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("V2.42.37 result score is invalid")
    score = float(value)
    if not math.isfinite(score):
        raise ValueError("V2.42.37 result score is invalid")
    return score


def _decode_value(
    content: bytes, *, request: TavilySearchRequest
) -> TavilySearchAttemptValue | None:
    if len(content) > MAX_RESPONSE_BYTES:
        return None
    try:
        payload = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    answer = _bounded_text(payload.get("answer"), optional=True)
    raw_results = payload.get("results")
    if answer is None or not isinstance(raw_results, list) or len(raw_results) > request.max_results:
        return None
    results: list[TavilySearchResultValue] = []
    for item in raw_results:
        if not isinstance(item, Mapping):
            return None
        url = _canonical_url(item.get("url"))
        title = _bounded_text(item.get("title"), optional=True)
        text = _bounded_text(item.get("content"), optional=True)
        raw_text = _bounded_text(item.get("raw_content"), optional=True)
        if title is None or text is None or raw_text is None:
            return None
        try:
            score = _optional_score(item.get("score"))
        except ValueError:
            return None
        if not url:
            continue
        results.append(
            TavilySearchResultValue(
                title=title,
                url=url,
                content=text,
                raw_content=raw_text,
                score=score,
            )
        )
    if not results:
        return TavilySearchAttemptValue(
            query=request.query,
            answer=answer,
            results=(),
        )
    return TavilySearchAttemptValue(
        query=request.query,
        answer=answer,
        results=tuple(results),
    )


def _contains_direct_credential_echo(
    content: bytes, *, credentials: Sequence[str]
) -> bool:
    return any(credential.encode("ascii") in content for credential in credentials)


class TavilySearchSingleAttemptAdapter:
    """Bind an ephemeral query and caller credentials to one metered POST."""

    def __init__(
        self,
        *,
        endpoint: str,
        credentials: Sequence[str],
        timeout_seconds: int,
        post: Callable[..., Any] | None = None,
    ) -> None:
        self._endpoint = _validate_endpoint(endpoint)
        self._credentials = _validate_credentials(credentials)
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
            raise ValueError("V2.42.37 post transport is not callable")

    def bind(
        self,
        request: TavilySearchRequest,
        *,
        meter_contract: Mapping[str, Any],
    ) -> Callable[[Mapping[str, Any]], ProviderAttemptResult]:
        frozen = _validate_request(request)
        _validate_request_credential_separation(
            frozen,
            credentials=self._credentials,
        )
        contract = _validate_meter_compatibility(
            meter_contract,
            credential_count=len(self._credentials),
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
        request: TavilySearchRequest,
        meter_contract: Mapping[str, Any],
    ) -> ProviderAttemptResult:
        frozen = _validate_request(request)
        _validate_request_credential_separation(
            frozen,
            credentials=self._credentials,
        )
        contract = _validate_meter_compatibility(
            meter_contract,
            credential_count=len(self._credentials),
            timeout_seconds=self._timeout_seconds,
        )
        bound = _validate_invocation(invocation, meter_contract=contract)
        credential_index = int(bound["attempt_index"]) - 1
        if not 0 <= credential_index < int(contract["max_attempts"]):
            raise ValueError("V2.42.37 attempt index is outside the meter")
        credential = self._credentials[credential_index]
        _body, encoded = _request_body(frozen)
        headers = {
            "Authorization": "Bearer " + credential,
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
                verify=True,
            )
        except (requests.ConnectionError, requests.Timeout):
            observation = build_provider_attempt_observation(
                invocation=bound,
                outcome="transport_error",
                http_status=None,
                provider_response_ref_sha256=None,
                token_usage_state="not_applicable",
                input_tokens=None,
                output_tokens=None,
                provider_tool_usage_state="not_applicable",
                provider_tool_calls=None,
                request_body_bytes=len(encoded),
                response_body_bytes=None,
            )
            return ProviderAttemptResult(observation=observation, value=None)
        except requests.RequestException:
            raise TavilySearchSingleAttemptError(
                "single Tavily POST failed outside the typed transport class"
            ) from None

        try:
            status = response.status_code
        except AttributeError:
            raise TavilySearchSingleAttemptError(
                "single Tavily POST response interface is invalid"
            ) from None
        if isinstance(status, bool) or not isinstance(status, int) or not 100 <= status <= 599:
            raise TavilySearchSingleAttemptError(
                "single Tavily POST returned an invalid HTTP status"
            )
        try:
            content = bytes(response.content)
        except Exception:
            raise TavilySearchSingleAttemptError(
                "single Tavily POST response bytes are unavailable"
            ) from None
        if _contains_direct_credential_echo(content, credentials=self._credentials):
            raise TavilySearchSingleAttemptError(
                "single Tavily POST directly echoed a caller credential"
            )
        response_ref = hashlib.sha256(content).hexdigest()

        if status in {401, 403, 432}:
            outcome = "key_local_http"
            value = None
        elif status in {408, 409, 429} or status >= 500:
            outcome = "retryable_http"
            value = None
        elif 400 <= status < 500:
            outcome = "terminal_http"
            value = None
        elif 300 <= status < 400:
            raise TavilySearchSingleAttemptError(
                "single Tavily POST redirect was rejected"
            )
        elif 200 <= status < 300:
            value = _decode_value(content, request=frozen)
            if value is None:
                outcome = "invalid_json"
            elif not value.results:
                outcome = "empty_output"
                value = None
            else:
                outcome = "success"
        else:
            raise TavilySearchSingleAttemptError(
                "single Tavily POST informational status was rejected"
            )

        observation = build_provider_attempt_observation(
            invocation=bound,
            outcome=outcome,
            http_status=status,
            provider_response_ref_sha256=response_ref,
            token_usage_state="not_applicable",
            input_tokens=None,
            output_tokens=None,
            provider_tool_usage_state="not_applicable",
            provider_tool_calls=None,
            request_body_bytes=len(encoded),
            response_body_bytes=len(content),
        )
        return ProviderAttemptResult(observation=observation, value=value)
