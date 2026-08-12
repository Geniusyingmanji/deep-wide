"""Single-attempt bounded transport for four frozen public snapshots.

Importing this module performs no effect.  ``fetch_snapshot`` maps one explicit
call to at most one HTTP GET, rejects redirects, disables environment-derived
session state, performs a public-address DNS preflight, and bounds retained
bytes.  Raw bytes are returned only in memory; the receipt is content-free.
"""

from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import math
import socket
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any
from urllib.parse import urlsplit

import requests


POLICY_ID = "v25217_single_snapshot_transport_v1"
ROLE = "v25217_content_free_single_snapshot_transport_receipt"
CONNECT_TIMEOUT_SECONDS = 10.0
READ_TIMEOUT_SECONDS = 120.0
TOTAL_WALL_SECONDS = 180.0
STREAM_CHUNK_BYTES = 64 * 1024
USER_AGENT = "DeepWideResearch/2.52.16 (public snapshot reliability study)"
ENDPOINTS = {
    "single_authority_exact_record": {
        "url": "https://crates.io/api/v1/crates?page=1&per_page=100&sort=recent-downloads",
        "maximum_response_bytes": 4 * 1024 * 1024,
        "accepted_content_types": ("application/json",),
        "accept": "application/json",
    },
    "single_authority_multivalue_record": {
        "url": "https://cran.r-project.org/src/contrib/PACKAGES",
        "maximum_response_bytes": 32 * 1024 * 1024,
        "accepted_content_types": ("text/plain",),
        "accept": "text/plain",
    },
    "same_identity_multipage_record": {
        "url": "https://api.crossref.org/works?filter=type:journal-article&select=DOI,title,publisher,container-title&sort=published&order=desc&rows=100",
        "maximum_response_bytes": 8 * 1024 * 1024,
        "accepted_content_types": ("application/json",),
        "accept": "application/json",
    },
    "sparse_ambiguous_open_web_record": {
        "url": "https://pypi.org/simple/",
        "maximum_response_bytes": 128 * 1024 * 1024,
        "accepted_content_types": (
            "text/html",
            "application/vnd.pypi.simple.v1+html",
        ),
        "accept": "text/html",
    },
}
FAILURE_CODES = (
    "dns_failure",
    "dns_nonpublic",
    "transport_timeout",
    "transport_error",
    "http_redirect",
    "http_non200",
    "content_type",
    "empty_response",
    "response_oversize",
    "stream_error",
    "wall_exceeded",
)


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value.split("%", 1)[0])
    except ValueError:
        return False
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_global


def _system_resolve(hostname: str, port: int) -> tuple[str, ...]:
    rows = socket.getaddrinfo(
        hostname,
        port,
        family=socket.AF_UNSPEC,
        type=socket.SOCK_STREAM,
        proto=socket.IPPROTO_TCP,
    )
    return tuple(str(row[4][0]) for row in rows)


def _public_resolution(
    hostname: str,
    *,
    resolve: Callable[[str, int], Sequence[str]],
) -> tuple[str, ...]:
    try:
        supplied = resolve(hostname, 443)
    except (OSError, socket.gaierror):
        raise RuntimeError("dns_failure") from None
    if (
        isinstance(supplied, (str, bytes))
        or not isinstance(supplied, Sequence)
        or not supplied
        or len(supplied) > 256
        or any(not isinstance(value, str) for value in supplied)
        or any(not _public_address(value) for value in supplied)
    ):
        raise RuntimeError("dns_nonpublic")
    return tuple(dict.fromkeys(supplied))


def _receipt(
    *,
    stratum: str,
    provider_attempt_count: int,
    outcome: str,
    failure_code: str | None,
    http_status: int | None,
    elapsed_seconds: float,
    response_bytes: int,
    response_sha256: str | None,
) -> dict[str, Any]:
    spec = ENDPOINTS[stratum]
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "stratum": stratum,
        "url_sha256": hashlib.sha256(spec["url"].encode()).hexdigest(),
        "maximum_provider_attempts": 1,
        "provider_attempt_count": provider_attempt_count,
        "redirect_count": 0,
        "retry_count": 0,
        "connect_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
        "read_timeout_seconds": READ_TIMEOUT_SECONDS,
        "total_wall_seconds": TOTAL_WALL_SECONDS,
        "maximum_response_bytes": spec["maximum_response_bytes"],
        "requests_trust_env_disabled": True,
        "tls_verification_required": True,
        "public_address_dns_preflight_performed": provider_attempt_count == 1,
        "dns_preflight_result_pinned_to_transport": False,
        "requests_timeout_is_hard_total_wall_deadline": False,
        "independent_hard_deadline_controller_required_for_execution": True,
        "terminal_outcome": outcome,
        "failure_code": failure_code,
        "http_status": http_status,
        "elapsed_seconds": round(float(elapsed_seconds), 6),
        "response_bytes": response_bytes,
        "response_sha256": response_sha256,
        "contains_url_body_header_identity_record_value_question_prediction_evidence_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "model_search_evaluator_benchmark_or_api_effect": False,
        "population_freeze_external_forward_or_runtime_compatibility_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    stratum = copied.get("stratum")
    spec = ENDPOINTS.get(stratum) if isinstance(stratum, str) else None
    outcome = copied.get("terminal_outcome")
    failure = copied.get("failure_code")
    status = copied.get("http_status")
    elapsed = copied.get("elapsed_seconds")
    response_bytes = copied.get("response_bytes")
    digest = copied.get("response_sha256")
    false_flags = (
        "contains_url_body_header_identity_record_value_question_prediction_evidence_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "entropy_or_information_gain_assigns_signed_credit",
        "model_search_evaluator_benchmark_or_api_effect",
        "population_freeze_external_forward_or_runtime_compatibility_authorized",
    )
    if (
        set(copied)
        != {
            "artifact_version",
            "role",
            "policy_id",
            "stratum",
            "url_sha256",
            "maximum_provider_attempts",
            "provider_attempt_count",
            "redirect_count",
            "retry_count",
            "connect_timeout_seconds",
            "read_timeout_seconds",
            "total_wall_seconds",
            "maximum_response_bytes",
            "requests_trust_env_disabled",
            "tls_verification_required",
            "public_address_dns_preflight_performed",
            "dns_preflight_result_pinned_to_transport",
            "requests_timeout_is_hard_total_wall_deadline",
            "independent_hard_deadline_controller_required_for_execution",
            "terminal_outcome",
            "failure_code",
            "http_status",
            "elapsed_seconds",
            "response_bytes",
            "response_sha256",
            *false_flags,
            "receipt_payload_sha256",
        }
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or spec is None
        or copied.get("url_sha256")
        != hashlib.sha256(spec["url"].encode()).hexdigest()
        or copied.get("maximum_provider_attempts") != 1
        or copied.get("provider_attempt_count") not in {0, 1}
        or isinstance(copied.get("provider_attempt_count"), bool)
        or copied.get("redirect_count") != 0
        or copied.get("retry_count") != 0
        or copied.get("connect_timeout_seconds") != CONNECT_TIMEOUT_SECONDS
        or copied.get("read_timeout_seconds") != READ_TIMEOUT_SECONDS
        or copied.get("total_wall_seconds") != TOTAL_WALL_SECONDS
        or copied.get("maximum_response_bytes") != spec["maximum_response_bytes"]
        or copied.get("requests_trust_env_disabled") is not True
        or copied.get("tls_verification_required") is not True
        or copied.get("public_address_dns_preflight_performed")
        is not (copied.get("provider_attempt_count") == 1)
        or copied.get("dns_preflight_result_pinned_to_transport") is not False
        or copied.get("requests_timeout_is_hard_total_wall_deadline") is not False
        or copied.get("independent_hard_deadline_controller_required_for_execution")
        is not True
        or outcome not in {"success", "failure"}
        or failure not in {None, *FAILURE_CODES}
        or (failure is None) is not (outcome == "success")
        or (
            status is not None
            and (
                isinstance(status, bool)
                or not isinstance(status, int)
                or not 100 <= status <= 599
            )
        )
        or isinstance(elapsed, bool)
        or not isinstance(elapsed, (int, float))
        or not math.isfinite(float(elapsed))
        or not 0 <= float(elapsed) <= TOTAL_WALL_SECONDS
        or isinstance(response_bytes, bool)
        or not isinstance(response_bytes, int)
        or not 0 <= response_bytes <= spec["maximum_response_bytes"]
        or (
            digest is not None
            and (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            )
        )
        or any(copied.get(name) is not False for name in false_flags)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.17 snapshot transport receipt drifted")
    if outcome == "success":
        if (
            copied["provider_attempt_count"] != 1
            or status != 200
            or response_bytes < 1
            or digest is None
        ):
            raise ValueError("V2.52.17 successful receipt drifted")
    elif response_bytes != 0 or digest is not None:
        raise ValueError("V2.52.17 failed receipt drifted")
    return copied


def _bounded_body(response: Any, *, maximum: int) -> bytes:
    chunks: list[bytes] = []
    size = 0
    try:
        iterator = response.iter_content(chunk_size=STREAM_CHUNK_BYTES)
        for chunk in iterator:
            if not isinstance(chunk, bytes):
                raise RuntimeError("stream_error")
            if not chunk:
                continue
            if size + len(chunk) > maximum:
                raise RuntimeError("response_oversize")
            chunks.append(chunk)
            size += len(chunk)
    except RuntimeError as exc:
        if str(exc) in {"stream_error", "response_oversize"}:
            raise
        raise RuntimeError("stream_error") from None
    except Exception as exc:
        raise RuntimeError("stream_error") from exc
    body = b"".join(chunks)
    if not body:
        raise RuntimeError("empty_response")
    return body


def fetch_snapshot(
    stratum: str,
    *,
    session: Any | None = None,
    resolve: Callable[[str, int], Sequence[str]] = _system_resolve,
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[bytes, dict[str, Any]]:
    if stratum not in ENDPOINTS:
        raise ValueError("V2.52.17 snapshot stratum drifted")
    spec = ENDPOINTS[stratum]
    parsed = urlsplit(spec["url"])
    if parsed.scheme != "https" or not parsed.hostname:
        raise RuntimeError("V2.52.17 frozen endpoint drifted")
    started = monotonic()
    attempt_count = 0
    status: int | None = None
    own_session = session is None
    response: Any | None = None
    body = b""
    failure: str | None = None
    try:
        _public_resolution(parsed.hostname, resolve=resolve)
        client = requests.Session() if session is None else session
        if hasattr(client, "trust_env"):
            client.trust_env = False
        attempt_count = 1
        try:
            response = client.get(
                spec["url"],
                headers={"User-Agent": USER_AGENT, "Accept": spec["accept"]},
                timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
                allow_redirects=False,
                stream=True,
                verify=True,
            )
        except requests.Timeout:
            failure = "transport_timeout"
        except requests.RequestException:
            failure = "transport_error"
        except Exception:
            failure = "transport_error"
        if failure is None:
            raw_status = getattr(response, "status_code", None)
            status = raw_status if isinstance(raw_status, int) and not isinstance(raw_status, bool) else None
            if status is not None and 300 <= status <= 399:
                failure = "http_redirect"
            elif status != 200:
                failure = "http_non200"
            else:
                headers = getattr(response, "headers", {})
                raw_type = headers.get("Content-Type", "") if isinstance(headers, Mapping) else ""
                content_type = str(raw_type).split(";", 1)[0].strip().casefold()
                if content_type not in spec["accepted_content_types"]:
                    failure = "content_type"
                else:
                    try:
                        body = _bounded_body(
                            response, maximum=spec["maximum_response_bytes"]
                        )
                    except RuntimeError as exc:
                        failure = str(exc)
        elapsed = monotonic() - started
        if elapsed > TOTAL_WALL_SECONDS:
            body = b""
            failure = "wall_exceeded"
    except RuntimeError as exc:
        elapsed = monotonic() - started
        failure = str(exc)
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                pass
        if own_session and "client" in locals():
            try:
                client.close()
            except Exception:
                pass
    if failure is not None:
        body = b""
        return body, _receipt(
            stratum=stratum,
            provider_attempt_count=attempt_count,
            outcome="failure",
            failure_code=failure if failure in FAILURE_CODES else "transport_error",
            http_status=status,
            elapsed_seconds=max(0.0, min(float(elapsed), TOTAL_WALL_SECONDS)),
            response_bytes=0,
            response_sha256=None,
        )
    return body, _receipt(
        stratum=stratum,
        provider_attempt_count=attempt_count,
        outcome="success",
        failure_code=None,
        http_status=status,
        elapsed_seconds=max(0.0, min(float(elapsed), TOTAL_WALL_SECONDS)),
        response_bytes=len(body),
        response_sha256=hashlib.sha256(body).hexdigest(),
    )


__all__ = [
    "CONNECT_TIMEOUT_SECONDS",
    "ENDPOINTS",
    "FAILURE_CODES",
    "POLICY_ID",
    "READ_TIMEOUT_SECONDS",
    "ROLE",
    "TOTAL_WALL_SECONDS",
    "fetch_snapshot",
    "validate_receipt",
]
