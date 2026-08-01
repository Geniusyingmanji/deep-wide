"""One-HTTP-attempt adapter for bounded public-page fetching.

The active native fetcher follows redirects internally, so one call can hide
several GETs inside a single V2.42.35 callback.  This isolated candidate maps
one callback to one GET, rejects redirects, bounds streamed response bytes,
and performs a public-address DNS preflight immediately before transport.

The DNS result is not pinned to the Requests connection; DNS rebinding between
preflight and transport therefore remains an explicit limitation.  The module
is not imported by active clients, runtime, runner, launcher, or benchmark
code.  Tests and the audit inject both resolver and transport and make no
network request.
"""

from __future__ import annotations

import dataclasses
import hashlib
import ipaddress
import socket
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import requests

from deepwide_agent.v24232_webswarm_total_budget import object_sha256
from deepwide_agent.v24234_provider_cost_meter import validate_provider_meter_contract
from deepwide_agent.v24235_preauthorized_effect_harness import (
    ATTEMPT_INVOCATION_KEYS,
    ProviderAttemptResult,
    build_provider_attempt_observation,
)


POLICY_ID = "v24238_native_http_fetch_single_attempt_v1"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY = True
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
INTERNAL_RETRY_IMPLEMENTED = False
REDIRECT_FOLLOWING_IMPLEMENTED = False
ARBITRARY_CALLER_HEADERS_ACCEPTED = False
ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED = False
REQUESTS_TRUST_ENV_DISABLED = True
TLS_VERIFICATION_DISABLED = False
PUBLIC_ADDRESS_DNS_PREFLIGHT_IMPLEMENTED = True
DNS_PREFLIGHT_RESULT_PINNED_TO_TRANSPORT = False
SYSTEM_RESOLVER_USED_BY_DEFAULT = True
RETAINED_RESPONSE_BYTE_CAP_IMPLEMENTED = True
TOTAL_TRANSPORT_RESPONSE_BYTES_HARD_CAPPED = False
FULL_PROVIDER_RESPONSE_HASHED_WHEN_TRUNCATED = False
RESPONSE_CLOSE_ATTEMPTED = True
RESPONSE_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED = False
REQUEST_URL_DIRECTLY_PERSISTED_OR_EMITTED = False
CALLER_PUBLIC_NONSECRET_URL_REQUIRED = True
URL_SECRET_ABSENCE_INDEPENDENTLY_VERIFIED = False
SENSITIVE_QUERY_KEY_REJECTION_IMPLEMENTED = True
PROVIDER_CHALLENGE_HEADER_SENT = False
PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED = False
PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED = False
NOMINAL_TIMEOUT_RESERVATION_CHECKED = True
REQUESTS_TIMEOUT_IS_TOTAL_WALL_DEADLINE = False

MAX_URL_CHARS = 8192
MAX_TIMEOUT_SECONDS = 3600
MAX_RESPONSE_BYTES = 32_000_000
STREAM_CHUNK_BYTES = 65_536
USER_AGENT = "DeepWideResearch/1.0 (label-blind bounded fetch candidate)"
ACCEPT = "text/html,application/xhtml+xml,application/json,text/plain,application/xml;q=0.9,*/*;q=0.1"
SENSITIVE_QUERY_KEYS = frozenset(
    {
        "access_token",
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "credential",
        "key",
        "password",
        "secret",
        "sig",
        "signature",
        "token",
        "x-amz-credential",
        "x-amz-security-token",
        "x-amz-signature",
    }
)


class NativeHttpFetchSingleAttemptError(RuntimeError):
    """Safe adapter error that never embeds URL or provider content."""


@dataclasses.dataclass(frozen=True)
class NativeHttpFetchRequest:
    url: str


@dataclasses.dataclass(frozen=True)
class NativeHttpFetchAttemptValue:
    url: str
    body: bytes
    content_type: str
    encoding: str | None
    truncated: bool


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
        raise ValueError(f"V2.42.38 {label} is outside the frozen range")
    return value


def _normalize_url(request: NativeHttpFetchRequest) -> tuple[str, str, int]:
    if not isinstance(request, NativeHttpFetchRequest):
        raise ValueError("V2.42.38 request type is invalid")
    raw = request.url
    if (
        not isinstance(raw, str)
        or not raw
        or raw != raw.strip()
        or len(raw) > MAX_URL_CHARS
        or any(ord(character) < 32 or ord(character) == 127 for character in raw)
    ):
        raise ValueError("V2.42.38 URL is invalid")
    try:
        parsed = urlsplit(raw)
        explicit_port = parsed.port
    except ValueError as error:
        raise ValueError("V2.42.38 URL is invalid") from error
    scheme = parsed.scheme.casefold()
    if (
        scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or explicit_port is not None
    ):
        raise ValueError("V2.42.38 URL is outside the public-fetch shape")
    try:
        hostname = parsed.hostname.rstrip(".").encode("idna").decode("ascii").casefold()
    except UnicodeError as error:
        raise ValueError("V2.42.38 hostname is invalid") from error
    if not hostname or hostname == "localhost" or hostname.endswith(".localhost"):
        raise ValueError("V2.42.38 hostname is not public")
    try:
        literal = ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        literal = None
    if literal is not None and not _public_address(hostname):
        raise ValueError("V2.42.38 literal address is not public")
    try:
        query_keys = {
            key.casefold()
            for key, _value in parse_qsl(parsed.query, keep_blank_values=True)
        }
    except ValueError as error:
        raise ValueError("V2.42.38 URL query is invalid") from error
    if query_keys & SENSITIVE_QUERY_KEYS:
        raise ValueError("V2.42.38 URL query contains a sensitive key")
    port = 80 if scheme == "http" else 443
    transport_host = f"[{hostname}]" if ":" in hostname else hostname
    normalized = urlunsplit(
        (
            scheme,
            transport_host,
            parsed.path or "/",
            parsed.query,
            "",
        )
    )
    return normalized, hostname, port


def _system_resolve(hostname: str, port: int) -> tuple[str, ...]:
    records = socket.getaddrinfo(
        hostname,
        port,
        family=socket.AF_UNSPEC,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
    )
    return tuple(str(record[4][0]) for record in records)


def _public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped is not None:
        address = address.ipv4_mapped
    return address.is_global


def _validate_public_resolution(
    *,
    hostname: str,
    port: int,
    resolve: Callable[[str, int], Sequence[str]],
) -> tuple[str, ...]:
    try:
        literal = ipaddress.ip_address(hostname.split("%", 1)[0])
    except ValueError:
        literal = None
    if literal is not None:
        addresses = (hostname,)
    else:
        try:
            supplied = resolve(hostname, port)
        except (OSError, socket.gaierror):
            raise NativeHttpFetchSingleAttemptError(
                "public-address DNS preflight failed"
            ) from None
        if isinstance(supplied, (str, bytes)) or not isinstance(supplied, Sequence):
            raise NativeHttpFetchSingleAttemptError(
                "public-address DNS preflight returned an invalid shape"
            )
        addresses = tuple(supplied)
    if (
        not addresses
        or len(addresses) > 256
        or any(not isinstance(address, str) for address in addresses)
        or any(not _public_address(address) for address in addresses)
    ):
        raise NativeHttpFetchSingleAttemptError(
            "public-address DNS preflight rejected the destination"
        )
    return tuple(dict.fromkeys(addresses))


def _validate_invocation(
    invocation: Mapping[str, Any], *, meter_contract: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(invocation, Mapping) or set(invocation) != ATTEMPT_INVOCATION_KEYS:
        raise ValueError("V2.42.38 invocation schema is not exact")
    value = dict(invocation)
    seal = value.pop("attempt_invocation_sha256", None)
    if (
        not _is_sha256(seal)
        or seal != object_sha256(value)
        or invocation.get("provider_kind") != "native_http_fetch"
        or invocation.get("effect_kind") != "fetch_request"
        or invocation.get("meter_contract_sha256")
        != meter_contract["contract_sha256"]
        or invocation.get("raw_request_or_response_content_present") is not False
        or invocation.get("credential_or_url_present") is not False
        or invocation.get("benchmark_or_evaluator_metadata_present") is not False
    ):
        raise ValueError("V2.42.38 invocation binding drifted")
    return dict(invocation)


def _validate_meter_compatibility(
    meter_contract: Mapping[str, Any], *, timeout_seconds: int
) -> dict[str, Any]:
    validate_provider_meter_contract(meter_contract)
    contract = dict(meter_contract)
    if (
        contract["provider_kind"] != "native_http_fetch"
        or contract["effect_kind"] != "fetch_request"
        or int(contract["reserved_cost"]["wall_milliseconds"])
        < int(contract["max_attempts"]) * timeout_seconds * 1000
    ):
        raise ValueError("V2.42.38 meter reservation is not adapter-compatible")
    return contract


def _bounded_stream(response: Any, *, maximum: int) -> tuple[bytes, bool]:
    chunks: list[bytes] = []
    size = 0
    truncated = False
    for chunk in response.iter_content(chunk_size=STREAM_CHUNK_BYTES):
        if not isinstance(chunk, bytes):
            raise NativeHttpFetchSingleAttemptError(
                "single fetch response stream yielded invalid bytes"
            )
        if not chunk:
            continue
        remaining = maximum - size
        if remaining <= 0:
            truncated = True
            break
        if len(chunk) > remaining:
            chunks.append(chunk[:remaining])
            size += remaining
            truncated = True
            break
        chunks.append(chunk)
        size += len(chunk)
    return b"".join(chunks), truncated


def _bounded_header(value: object, *, maximum: int = 1024) -> str:
    return str(value or "")[:maximum]


class NativeHttpFetchSingleAttemptAdapter:
    """Bind an ephemeral public URL to one bounded metered GET."""

    def __init__(
        self,
        *,
        timeout_seconds: int,
        max_response_bytes: int,
        get: Callable[..., Any] | None = None,
        resolve: Callable[[str, int], Sequence[str]] | None = None,
    ) -> None:
        self._timeout_seconds = _integer(
            timeout_seconds,
            label="timeout seconds",
            minimum=1,
            maximum=MAX_TIMEOUT_SECONDS,
        )
        self._max_response_bytes = _integer(
            max_response_bytes,
            label="max response bytes",
            minimum=1,
            maximum=MAX_RESPONSE_BYTES,
        )
        self._resolve = _system_resolve if resolve is None else resolve
        if not callable(self._resolve):
            raise ValueError("V2.42.38 resolver is not callable")
        self._session: requests.Session | None = None
        if get is None:
            session = requests.Session()
            session.trust_env = False
            session.auth = None
            session.headers.clear()
            session.proxies.clear()
            session.cookies.clear()
            self._session = session
            self._get = session.get
        else:
            self._get = get
        if not callable(self._get):
            raise ValueError("V2.42.38 GET transport is not callable")

    def bind(
        self,
        request: NativeHttpFetchRequest,
        *,
        meter_contract: Mapping[str, Any],
    ) -> Callable[[Mapping[str, Any]], ProviderAttemptResult]:
        normalized, hostname, port = _normalize_url(request)
        contract = _validate_meter_compatibility(
            meter_contract,
            timeout_seconds=self._timeout_seconds,
        )

        def callback(invocation: Mapping[str, Any]) -> ProviderAttemptResult:
            return self.single_attempt(
                invocation=invocation,
                request=NativeHttpFetchRequest(normalized),
                meter_contract=contract,
                expected_hostname=hostname,
                expected_port=port,
            )

        return callback

    def single_attempt(
        self,
        *,
        invocation: Mapping[str, Any],
        request: NativeHttpFetchRequest,
        meter_contract: Mapping[str, Any],
        expected_hostname: str | None = None,
        expected_port: int | None = None,
    ) -> ProviderAttemptResult:
        normalized, hostname, port = _normalize_url(request)
        if (
            (expected_hostname is not None and expected_hostname != hostname)
            or (expected_port is not None and expected_port != port)
        ):
            raise ValueError("V2.42.38 bound URL identity drifted")
        contract = _validate_meter_compatibility(
            meter_contract,
            timeout_seconds=self._timeout_seconds,
        )
        bound = _validate_invocation(invocation, meter_contract=contract)
        try:
            _validate_public_resolution(
                hostname=hostname,
                port=port,
                resolve=self._resolve,
            )
        except NativeHttpFetchSingleAttemptError:
            raise

        response: Any | None = None
        try:
            response = self._get(
                normalized,
                headers={"Accept": ACCEPT, "User-Agent": USER_AGENT},
                timeout=self._timeout_seconds,
                allow_redirects=False,
                stream=True,
                verify=True,
            )
            try:
                status = response.status_code
            except AttributeError:
                raise NativeHttpFetchSingleAttemptError(
                    "single fetch response interface is invalid"
                ) from None
            if (
                isinstance(status, bool)
                or not isinstance(status, int)
                or not 100 <= status <= 599
            ):
                raise NativeHttpFetchSingleAttemptError(
                    "single fetch returned an invalid HTTP status"
                )
            if 300 <= status < 400:
                raise NativeHttpFetchSingleAttemptError(
                    "single fetch redirect was rejected"
                )
            if 100 <= status < 200:
                raise NativeHttpFetchSingleAttemptError(
                    "single fetch informational status was rejected"
                )
            body, truncated = _bounded_stream(
                response,
                maximum=self._max_response_bytes,
            )
            response_ref = hashlib.sha256(body).hexdigest()
            if status in {408, 409, 429} or status >= 500:
                outcome = "retryable_http"
                value = None
            elif 400 <= status < 500:
                outcome = "terminal_http"
                value = None
            elif not body:
                outcome = "empty_output"
                value = None
            else:
                headers = response.headers
                content_type = _bounded_header(headers.get("Content-Type", ""))
                encoding_value = response.encoding
                encoding = (
                    _bounded_header(encoding_value, maximum=128)
                    if encoding_value is not None
                    else None
                )
                outcome = "success"
                value = NativeHttpFetchAttemptValue(
                    url=normalized,
                    body=body,
                    content_type=content_type,
                    encoding=encoding,
                    truncated=truncated,
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
                request_body_bytes=0,
                response_body_bytes=None,
            )
            return ProviderAttemptResult(observation=observation, value=None)
        except requests.RequestException:
            raise NativeHttpFetchSingleAttemptError(
                "single fetch failed outside the typed transport class"
            ) from None
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass

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
            request_body_bytes=0,
            response_body_bytes=len(body),
        )
        return ProviderAttemptResult(observation=observation, value=value)
