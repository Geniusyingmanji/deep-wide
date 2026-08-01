"""DNS-to-transport pinned native HTTP fetch candidate.

V2.42.38 validates that every address returned immediately before a fetch is
public, but Requests resolves the hostname again while opening its socket.
This isolated successor closes that rebinding window: it canonicalizes the
validated address set, deterministically selects one address from the durable
attempt index, and creates a fresh urllib3 pool whose connection host is that
numeric address.  The original hostname remains the HTTP ``Host`` value and,
for HTTPS, both the TLS SNI name and certificate hostname assertion.

Each callback makes one ``urlopen`` call with redirects and urllib3 retries
disabled.  The module preserves the V2.42.38 retained-prefix bound and typed
meter observation.  A fresh pool and response are always asked to close, but
socket close success and a hard total wall deadline are not independently
attested.  This module is not imported by active clients, runtime, runner,
launcher, benchmark, or evaluator code.  Tests inject a pool factory and make
no network request.
"""

from __future__ import annotations

import hashlib
import ipaddress
import ssl
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urlsplit

import urllib3

from deepwide_agent.v24235_preauthorized_effect_harness import (
    ProviderAttemptResult,
    build_provider_attempt_observation,
)
from deepwide_agent.v24238_native_http_fetch_single_attempt import (
    ACCEPT,
    MAX_RESPONSE_BYTES,
    MAX_TIMEOUT_SECONDS,
    STREAM_CHUNK_BYTES,
    USER_AGENT,
    NativeHttpFetchAttemptValue,
    NativeHttpFetchRequest,
    NativeHttpFetchSingleAttemptError,
    _bounded_header,
    _integer,
    _normalize_url,
    _system_resolve,
    _validate_invocation,
    _validate_meter_compatibility,
    _validate_public_resolution,
)


POLICY_ID = "v24245_pinned_native_http_fetch_v1"

PRODUCTION_PACKAGE_AUTHORIZED = False
ACTIVE_FORWARD_INTEGRATION_AUTHORIZED = False
ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED = False
BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED = False
DEV64_OR_EXACT220_LAUNCH_AUTHORIZED = False
SHARED_API_LEASE_ACQUIRE_AUTHORIZED = False
LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED = False

CANDIDATE_SINGLE_ATTEMPT_NETWORK_CALL_CAPABILITY = True
PUBLIC_ADDRESS_DNS_PREFLIGHT_IMPLEMENTED = True
ALL_RESOLVED_ADDRESSES_MUST_BE_PUBLIC = True
DNS_PREFLIGHT_RESULT_PINNED_TO_TRANSPORT = True
DETERMINISTIC_ATTEMPT_INDEX_ADDRESS_SELECTION_IMPLEMENTED = True
ORIGINAL_HOST_HEADER_IMPLEMENTED = True
TLS_ORIGINAL_HOSTNAME_SNI_IMPLEMENTED = True
TLS_ORIGINAL_HOSTNAME_CERTIFICATE_ASSERTION_IMPLEMENTED = True
URLLIB3_INTERNAL_RETRY_DISABLED = True
REDIRECT_FOLLOWING_IMPLEMENTED = False
FRESH_POOL_PER_CALLBACK_IMPLEMENTED = True
ONE_URLOPEN_PER_CALLBACK_IMPLEMENTED = True
SYSTEM_RESOLVER_USED_BY_DEFAULT = True
RETAINED_RESPONSE_BYTE_CAP_IMPLEMENTED = True
TOTAL_TRANSPORT_RESPONSE_BYTES_HARD_CAPPED = False
FULL_PROVIDER_RESPONSE_HASHED_WHEN_TRUNCATED = False
RESPONSE_CLOSE_ATTEMPTED = True
RESPONSE_RELEASE_ATTEMPTED = True
POOL_CLOSE_ATTEMPTED = True
RESPONSE_AND_POOL_CLOSE_SUCCESS_INDEPENDENTLY_VERIFIED = False
SINGLE_SOCKET_CONNECTION_ATTEMPT_INDEPENDENTLY_ATTESTED = False
PROVIDER_RESPONSE_AUTHENTICITY_INDEPENDENTLY_VERIFIED = False
REQUESTS_OR_ENVIRONMENT_PROXY_USED = False
ARBITRARY_CALLER_HEADERS_ACCEPTED = False
ENVIRONMENT_OR_KEYRING_CREDENTIAL_READ_IMPLEMENTED = False
REQUEST_URL_DIRECTLY_PERSISTED_OR_EMITTED = False
CALLER_PUBLIC_NONSECRET_URL_REQUIRED = True
URL_SECRET_ABSENCE_INDEPENDENTLY_VERIFIED = False
SENSITIVE_QUERY_KEY_REJECTION_IMPLEMENTED = True
PROVIDER_CHALLENGE_HEADER_SENT = False
PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED = False
NOMINAL_TIMEOUT_RESERVATION_CHECKED = True
URLLIB3_TIMEOUT_IS_TOTAL_WALL_DEADLINE = False

PoolFactory = Callable[..., Any]


class PinnedNativeHttpFetchError(NativeHttpFetchSingleAttemptError):
    """Sanitized pinned-fetch error that never embeds URL or content."""


def _canonical_public_addresses(addresses: Sequence[str]) -> tuple[str, ...]:
    normalized: dict[tuple[int, bytes], str] = {}
    for supplied in addresses:
        if not isinstance(supplied, str) or not supplied or "%" in supplied:
            raise PinnedNativeHttpFetchError(
                "public-address DNS preflight returned a noncanonical address"
            )
        try:
            address = ipaddress.ip_address(supplied)
        except ValueError:
            raise PinnedNativeHttpFetchError(
                "public-address DNS preflight returned a noncanonical address"
            ) from None
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        if not address.is_global:
            raise PinnedNativeHttpFetchError(
                "public-address DNS preflight rejected the destination"
            )
        normalized[(address.version, address.packed)] = str(address)
    if not normalized:
        raise PinnedNativeHttpFetchError(
            "public-address DNS preflight returned no destination"
        )
    return tuple(normalized[key] for key in sorted(normalized))


def _select_pinned_address(
    addresses: Sequence[str], *, attempt_index: int
) -> str:
    if (
        isinstance(attempt_index, bool)
        or not isinstance(attempt_index, int)
        or attempt_index < 1
    ):
        raise ValueError("V2.42.45 attempt index is invalid")
    canonical = _canonical_public_addresses(addresses)
    return canonical[(attempt_index - 1) % len(canonical)]


def _default_pool_factory(
    *,
    scheme: str,
    pinned_address: str,
    port: int,
    original_hostname: str,
    timeout_seconds: int,
) -> Any:
    shared = {
        "host": pinned_address,
        "port": port,
        "timeout": timeout_seconds,
        "maxsize": 1,
        "block": True,
        "retries": False,
    }
    if scheme == "http":
        return urllib3.HTTPConnectionPool(**shared)
    if scheme == "https":
        return urllib3.HTTPSConnectionPool(
            **shared,
            cert_reqs=ssl.CERT_REQUIRED,
            server_hostname=original_hostname,
            assert_hostname=original_hostname,
        )
    raise ValueError("V2.42.45 URL scheme is invalid")


def _request_target(normalized_url: str) -> str:
    parsed = urlsplit(normalized_url)
    target = parsed.path or "/"
    if parsed.query:
        target = f"{target}?{parsed.query}"
    return target


def _host_header(hostname: str) -> str:
    return f"[{hostname}]" if ":" in hostname else hostname


def _bounded_pool_stream(response: Any, *, maximum: int) -> tuple[bytes, bool]:
    chunks: list[bytes] = []
    retained = 0
    truncated = False
    try:
        stream = response.stream(
            amt=min(STREAM_CHUNK_BYTES, maximum + 1),
            decode_content=True,
        )
    except (AttributeError, TypeError):
        raise PinnedNativeHttpFetchError(
            "single fetch response stream interface is invalid"
        ) from None
    for chunk in stream:
        if not isinstance(chunk, bytes):
            raise PinnedNativeHttpFetchError(
                "single fetch response stream yielded invalid bytes"
            )
        if not chunk:
            continue
        remaining = maximum - retained
        if remaining <= 0:
            truncated = True
            break
        if len(chunk) > remaining:
            chunks.append(chunk[:remaining])
            retained += remaining
            truncated = True
            break
        chunks.append(chunk)
        retained += len(chunk)
    return b"".join(chunks), truncated


class PinnedNativeHttpFetchAdapter:
    """Bind one ephemeral URL to one DNS-pinned, metered GET per callback."""

    def __init__(
        self,
        *,
        timeout_seconds: int,
        max_response_bytes: int,
        resolve: Callable[[str, int], Sequence[str]] | None = None,
        pool_factory: PoolFactory | None = None,
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
        self._pool_factory = (
            _default_pool_factory if pool_factory is None else pool_factory
        )
        if not callable(self._resolve):
            raise ValueError("V2.42.45 resolver is not callable")
        if not callable(self._pool_factory):
            raise ValueError("V2.42.45 pool factory is not callable")

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
            raise ValueError("V2.42.45 bound URL identity drifted")
        contract = _validate_meter_compatibility(
            meter_contract,
            timeout_seconds=self._timeout_seconds,
        )
        bound = _validate_invocation(invocation, meter_contract=contract)
        attempt_index = bound.get("attempt_index")
        if (
            isinstance(attempt_index, bool)
            or not isinstance(attempt_index, int)
            or attempt_index < 1
            or attempt_index > int(contract["max_attempts"])
            or bound.get("max_attempts") != contract["max_attempts"]
        ):
            raise ValueError("V2.42.45 invocation attempt bounds drifted")
        resolved = _validate_public_resolution(
            hostname=hostname,
            port=port,
            resolve=self._resolve,
        )
        pinned_address = _select_pinned_address(
            resolved,
            attempt_index=attempt_index,
        )
        scheme = urlsplit(normalized).scheme
        try:
            pool = self._pool_factory(
                scheme=scheme,
                pinned_address=pinned_address,
                port=port,
                original_hostname=hostname,
                timeout_seconds=self._timeout_seconds,
            )
        except (OSError, urllib3.exceptions.HTTPError):
            return self._transport_error(bound)
        except Exception:
            raise PinnedNativeHttpFetchError(
                "single fetch pool construction failed"
            ) from None
        try:
            urlopen = pool.urlopen
        except AttributeError:
            try:
                pool.close()
            except Exception:
                pass
            raise PinnedNativeHttpFetchError(
                "single fetch pool interface is invalid"
            ) from None
        if pool is None or not callable(urlopen):
            try:
                pool.close()
            except Exception:
                pass
            raise PinnedNativeHttpFetchError(
                "single fetch pool interface is invalid"
            )

        response: Any | None = None
        try:
            response = urlopen(
                "GET",
                _request_target(normalized),
                headers={
                    "Host": _host_header(hostname),
                    "Accept": ACCEPT,
                    "Accept-Encoding": "identity",
                    "User-Agent": USER_AGENT,
                },
                retries=False,
                redirect=False,
                assert_same_host=True,
                timeout=self._timeout_seconds,
                preload_content=False,
                decode_content=False,
                release_conn=False,
            )
            try:
                status = response.status
            except AttributeError:
                raise PinnedNativeHttpFetchError(
                    "single fetch response interface is invalid"
                ) from None
            if (
                isinstance(status, bool)
                or not isinstance(status, int)
                or not 100 <= status <= 599
            ):
                raise PinnedNativeHttpFetchError(
                    "single fetch returned an invalid HTTP status"
                )
            if 300 <= status < 400:
                raise PinnedNativeHttpFetchError(
                    "single fetch redirect was rejected"
                )
            if 100 <= status < 200:
                raise PinnedNativeHttpFetchError(
                    "single fetch informational status was rejected"
                )
            body, truncated = _bounded_pool_stream(
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
                try:
                    headers = response.headers
                    content_type = _bounded_header(headers.get("Content-Type", ""))
                except (AttributeError, TypeError):
                    raise PinnedNativeHttpFetchError(
                        "single fetch response headers are invalid"
                    ) from None
                outcome = "success"
                value = NativeHttpFetchAttemptValue(
                    url=normalized,
                    body=body,
                    content_type=content_type,
                    encoding=None,
                    truncated=truncated,
                )
        except (OSError, urllib3.exceptions.HTTPError):
            return self._transport_error(bound)
        finally:
            if response is not None:
                try:
                    response.close()
                except Exception:
                    pass
                try:
                    response.release_conn()
                except Exception:
                    pass
            try:
                pool.close()
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

    @staticmethod
    def _transport_error(invocation: Mapping[str, Any]) -> ProviderAttemptResult:
        observation = build_provider_attempt_observation(
            invocation=invocation,
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
