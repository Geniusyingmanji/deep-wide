"""Single-attempt CRAN semantic transport with strict body admission.

Importing this module performs no effect.  One explicit call targets only the
literal official CRAN PACKAGES endpoint, performs the frozen V2.52.17 safety
checks, observes but does not persist Content-Type, and returns candidate
identities only when V2.52.24 strict extraction succeeds on the same body.

This is a new policy namespace: missing or unknown MIME is never relabelled or
added to an alternate allowlist, but it does not decide semantic success.  A
fixed HTTPS origin, one bounded HTTP-200 body, and strict DCF extraction must
all succeed.  Direct calls still require an independent hard-wall controller
before any future effectful protocol may be authorized.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from . import v25217_single_snapshot_transport as transport
from . import v25220_content_type_disposition as disposition
from . import v25224_strict_cran_candidate_extractor as extractor


POLICY_ID = "v25226_cran_semantic_transport_v1"
ROLE = "v25226_content_free_cran_semantic_transport_receipt"
STRATUM = "single_authority_multivalue_record"
ENDPOINT = "https://cran.r-project.org/src/contrib/PACKAGES"
ENDPOINT_SHA256 = hashlib.sha256(ENDPOINT.encode("utf-8")).hexdigest()
HOSTNAME = "cran.r-project.org"
MAXIMUM_RESPONSE_BYTES = 32 * 1024 * 1024
CONNECT_TIMEOUT_SECONDS = transport.CONNECT_TIMEOUT_SECONDS
READ_TIMEOUT_SECONDS = transport.READ_TIMEOUT_SECONDS
TOTAL_WALL_SECONDS = transport.TOTAL_WALL_SECONDS
USER_AGENT = "DeepWideResearch/2.52.26 (CRAN semantic transport study)"
FAILURE_CODES = (
    "dns_failure",
    "dns_nonpublic",
    "transport_timeout",
    "transport_error",
    "http_redirect",
    "http_non200",
    "content_type_observation",
    "empty_response",
    "response_oversize",
    "stream_error",
    "semantic_gate",
    "semantic_gate_exception",
    "clock_error",
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


def _header(headers: object) -> tuple[bool, str | None]:
    if not isinstance(headers, Mapping):
        return False, None
    matches = [value for key, value in headers.items() if str(key).casefold() == "content-type"]
    if not matches:
        return False, None
    if len(matches) != 1 or not isinstance(matches[0], str):
        raise RuntimeError("content_type_observation")
    return True, matches[0]


def _clock_value(monotonic: Callable[[], float]) -> float:
    try:
        value = monotonic()
    except Exception:
        raise RuntimeError("clock_error") from None
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise RuntimeError("clock_error")
    return float(value)


def _elapsed_or_none(
    monotonic: Callable[[], float], started: float
) -> float | None:
    try:
        current = _clock_value(monotonic)
    except RuntimeError:
        return None
    elapsed = current - started
    return elapsed if math.isfinite(elapsed) and elapsed >= 0 else None


def _receipt(
    *,
    provider_attempt_count: int,
    terminal_outcome: str,
    failure_code: str | None,
    http_status: int | None,
    elapsed_seconds: float,
    response_bytes: int,
    response_sha256: str | None,
    dns_preflight_called: bool,
    content_type_observation: Mapping[str, Any] | None,
    extraction_observation: Mapping[str, Any] | None,
    extracted_candidate_count: int,
) -> dict[str, Any]:
    value: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "stratum": STRATUM,
        "url_sha256": ENDPOINT_SHA256,
        "maximum_provider_attempts": 1,
        "provider_attempt_count": provider_attempt_count,
        "redirect_count": 0,
        "retry_count": 0,
        "conditional_refetch_count": 0,
        "connect_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
        "read_timeout_seconds": READ_TIMEOUT_SECONDS,
        "total_wall_seconds": TOTAL_WALL_SECONDS,
        "maximum_response_bytes": MAXIMUM_RESPONSE_BYTES,
        "requests_trust_env_disabled": True,
        "tls_and_hostname_verification_required": True,
        "public_address_dns_preflight_performed": dns_preflight_called,
        "dns_preflight_result_pinned_to_transport": False,
        "requests_timeout_is_hard_total_wall_deadline": False,
        "independent_hard_deadline_controller_required_for_execution": True,
        "terminal_outcome": terminal_outcome,
        "failure_code": failure_code,
        "http_status": http_status,
        "elapsed_seconds": round(float(elapsed_seconds), 6),
        "response_bytes": response_bytes,
        "response_sha256": response_sha256,
        "content_type_observation": (
            copy.deepcopy(dict(content_type_observation))
            if content_type_observation is not None
            else None
        ),
        "strict_extraction_observation": (
            copy.deepcopy(dict(extraction_observation))
            if extraction_observation is not None
            else None
        ),
        "extracted_candidate_count": extracted_candidate_count,
        "known_safe_alternate_mime_allowlist_count": 0,
        "missing_or_unknown_mime_relabelled_as_text_plain": False,
        "mime_alone_establishes_semantic_success": False,
        "new_policy_differs_from_v25217_mime_only_admission": True,
        "v25217_source_or_receipt_modified": False,
        "raw_or_normalized_header_value_or_hash_persisted": False,
        "contains_url_body_identity_record_field_value_question_prediction_evidence_exception_message_traceback_or_credential": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read": False,
        "public_snapshot_network_or_api_called": dns_preflight_called,
        "model_hosted_search_tavily_evaluator_or_benchmark_called": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "population_freeze_external_forward_runtime_compatibility_or_benchmark_authorized": False,
    }
    value["receipt_payload_sha256"] = payload_sha256(value)
    return validate_receipt(value)


def fetch_strict_cran_candidates(
    *,
    session: Any | None = None,
    resolve: Callable[[str, int], Sequence[str]] = transport._system_resolve,
    monotonic: Callable[[], float] = time.monotonic,
) -> tuple[list[str], dict[str, Any]]:
    """Perform at most one fixed GET and return strict identities in memory."""

    try:
        started = _clock_value(monotonic)
    except RuntimeError:
        return [], _receipt(
            provider_attempt_count=0,
            terminal_outcome="failure",
            failure_code="clock_error",
            http_status=None,
            elapsed_seconds=0.0,
            response_bytes=0,
            response_sha256=None,
            dns_preflight_called=False,
            content_type_observation=None,
            extraction_observation=None,
            extracted_candidate_count=0,
        )
    attempt_count = 0
    dns_preflight_called = False
    status: int | None = None
    own_session = session is None
    response: Any | None = None
    body = b""
    body_digest: str | None = None
    observed: dict[str, Any] | None = None
    extracted: dict[str, Any] | None = None
    candidates: list[str] = []
    failure: str | None = None
    elapsed = 0.0
    try:
        dns_preflight_called = True
        transport._public_resolution(HOSTNAME, resolve=resolve)
        try:
            client = transport.requests.Session() if session is None else session
            if hasattr(client, "trust_env"):
                client.trust_env = False
        except Exception:
            failure = "transport_error"
        if failure is None:
            attempt_count = 1
            try:
                response = client.get(
                    ENDPOINT,
                    headers={"User-Agent": USER_AGENT, "Accept": "text/plain"},
                    timeout=(CONNECT_TIMEOUT_SECONDS, READ_TIMEOUT_SECONDS),
                    allow_redirects=False,
                    stream=True,
                    verify=True,
                )
            except transport.requests.Timeout:
                failure = "transport_timeout"
            except transport.requests.RequestException:
                failure = "transport_error"
            except Exception:
                failure = "transport_error"
        if failure is None:
            raw_status = getattr(response, "status_code", None)
            status = (
                raw_status
                if isinstance(raw_status, int) and not isinstance(raw_status, bool)
                else None
            )
            if status is not None and 300 <= status <= 399:
                failure = "http_redirect"
            elif status != 200:
                failure = "http_non200"
            else:
                try:
                    present, raw_header = _header(getattr(response, "headers", {}))
                    observed = disposition.observe_content_type(
                        STRATUM,
                        header_present=present,
                        raw_header=raw_header,
                    )
                except Exception:
                    failure = "content_type_observation"
        if failure is None:
            try:
                body = transport._bounded_body(
                    response, maximum=MAXIMUM_RESPONSE_BYTES
                )
                body_digest = hashlib.sha256(body).hexdigest()
            except RuntimeError as exc:
                code = str(exc)
                failure = code if code in {"empty_response", "response_oversize", "stream_error"} else "stream_error"
        if failure is None:
            try:
                candidates, extracted = extractor.extract_strict_cran_candidates(
                    body,
                    expected_body_bytes=len(body),
                    expected_body_sha256=body_digest,
                )
            except Exception:
                candidates = []
                failure = "semantic_gate_exception"
            if failure is None and (
                extracted["extraction_completed"] is not True
                or extracted["candidate_count_parity"] is not True
                or len(candidates) != extracted["extracted_candidate_count"]
                or len(candidates) < extractor.parent.MINIMUM_DISTINCT_CANDIDATES
            ):
                candidates = []
                failure = "semantic_gate"
        measured = _elapsed_or_none(monotonic, started)
        if measured is None:
            candidates = []
            body = b""
            body_digest = None
            observed = None
            extracted = None
            status = None
            failure = "clock_error"
            elapsed = 0.0
        else:
            elapsed = measured
        if measured is not None and elapsed > TOTAL_WALL_SECONDS:
            candidates = []
            status = None
            body = b""
            body_digest = None
            observed = None
            extracted = None
            failure = "wall_exceeded"
    except RuntimeError as exc:
        measured = _elapsed_or_none(monotonic, started)
        elapsed = measured if measured is not None else 0.0
        code = str(exc)
        failure = code if code in {"dns_failure", "dns_nonpublic"} else "transport_error"
    except Exception:
        measured = _elapsed_or_none(monotonic, started)
        elapsed = measured if measured is not None else 0.0
        candidates = []
        body = b""
        body_digest = None
        observed = None
        extracted = None
        status = None
        failure = "transport_error"
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

    elapsed = max(0.0, min(float(elapsed), TOTAL_WALL_SECONDS))
    if failure is not None:
        candidates = []
        keep_binding = body_digest is not None
        return candidates, _receipt(
            provider_attempt_count=attempt_count,
            terminal_outcome="failure",
            failure_code=(failure if failure in FAILURE_CODES else "transport_error"),
            http_status=status,
            elapsed_seconds=elapsed,
            response_bytes=(len(body) if keep_binding else 0),
            response_sha256=(body_digest if keep_binding else None),
            dns_preflight_called=dns_preflight_called,
            content_type_observation=observed,
            extraction_observation=extracted,
            extracted_candidate_count=0,
        )
    return candidates, _receipt(
        provider_attempt_count=attempt_count,
        terminal_outcome="success",
        failure_code=None,
        http_status=status,
        elapsed_seconds=elapsed,
        response_bytes=len(body),
        response_sha256=body_digest,
        dns_preflight_called=dns_preflight_called,
        content_type_observation=observed,
        extraction_observation=extracted,
        extracted_candidate_count=len(candidates),
    )


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    expected_fields = {
        "artifact_version",
        "role",
        "policy_id",
        "stratum",
        "url_sha256",
        "maximum_provider_attempts",
        "provider_attempt_count",
        "redirect_count",
        "retry_count",
        "conditional_refetch_count",
        "connect_timeout_seconds",
        "read_timeout_seconds",
        "total_wall_seconds",
        "maximum_response_bytes",
        "requests_trust_env_disabled",
        "tls_and_hostname_verification_required",
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
        "content_type_observation",
        "strict_extraction_observation",
        "extracted_candidate_count",
        "known_safe_alternate_mime_allowlist_count",
        "missing_or_unknown_mime_relabelled_as_text_plain",
        "mime_alone_establishes_semantic_success",
        "new_policy_differs_from_v25217_mime_only_admission",
        "v25217_source_or_receipt_modified",
        "raw_or_normalized_header_value_or_hash_persisted",
        "contains_url_body_identity_record_field_value_question_prediction_evidence_exception_message_traceback_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "public_snapshot_network_or_api_called",
        "model_hosted_search_tavily_evaluator_or_benchmark_called",
        "entropy_or_information_gain_assigns_signed_credit",
        "population_freeze_external_forward_runtime_compatibility_or_benchmark_authorized",
        "receipt_payload_sha256",
    }
    attempt = copied.get("provider_attempt_count")
    outcome = copied.get("terminal_outcome")
    failure = copied.get("failure_code")
    status = copied.get("http_status")
    elapsed = copied.get("elapsed_seconds")
    response_bytes = copied.get("response_bytes")
    digest = copied.get("response_sha256")
    observed = copied.get("content_type_observation")
    extracted = copied.get("strict_extraction_observation")
    candidate_count = copied.get("extracted_candidate_count")
    false_flags = (
        "dns_preflight_result_pinned_to_transport",
        "requests_timeout_is_hard_total_wall_deadline",
        "missing_or_unknown_mime_relabelled_as_text_plain",
        "mime_alone_establishes_semantic_success",
        "v25217_source_or_receipt_modified",
        "raw_or_normalized_header_value_or_hash_persisted",
        "contains_url_body_identity_record_field_value_question_prediction_evidence_exception_message_traceback_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_result_read",
        "model_hosted_search_tavily_evaluator_or_benchmark_called",
        "entropy_or_information_gain_assigns_signed_credit",
        "population_freeze_external_forward_runtime_compatibility_or_benchmark_authorized",
    )
    if (
        set(copied) != expected_fields
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("stratum") != STRATUM
        or copied.get("url_sha256") != ENDPOINT_SHA256
        or copied.get("maximum_provider_attempts") != 1
        or isinstance(attempt, bool)
        or attempt not in {0, 1}
        or copied.get("redirect_count") != 0
        or copied.get("retry_count") != 0
        or copied.get("conditional_refetch_count") != 0
        or copied.get("connect_timeout_seconds") != CONNECT_TIMEOUT_SECONDS
        or copied.get("read_timeout_seconds") != READ_TIMEOUT_SECONDS
        or copied.get("total_wall_seconds") != TOTAL_WALL_SECONDS
        or copied.get("maximum_response_bytes") != MAXIMUM_RESPONSE_BYTES
        or copied.get("requests_trust_env_disabled") is not True
        or copied.get("tls_and_hostname_verification_required") is not True
        or not isinstance(copied.get("public_address_dns_preflight_performed"), bool)
        or attempt == 1
        and copied.get("public_address_dns_preflight_performed") is not True
        or copied.get("independent_hard_deadline_controller_required_for_execution") is not True
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
        or not 0 <= response_bytes <= MAXIMUM_RESPONSE_BYTES
        or (
            digest is not None
            and (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            )
        )
        or isinstance(candidate_count, bool)
        or not isinstance(candidate_count, int)
        or candidate_count < 0
        or copied.get("known_safe_alternate_mime_allowlist_count") != 0
        or copied.get("new_policy_differs_from_v25217_mime_only_admission") is not True
        or any(copied.get(name) is not False for name in false_flags)
        or copied.get("public_snapshot_network_or_api_called")
        is not copied.get("public_address_dns_preflight_performed")
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.52.26 CRAN semantic transport receipt drifted")

    checked_observed: dict[str, Any] | None = None
    if observed is not None:
        if not isinstance(observed, Mapping):
            raise ValueError("V2.52.26 content-type observation shape drifted")
        checked_observed = disposition.validate_observation(observed)
        if checked_observed["stratum"] != STRATUM:
            raise ValueError("V2.52.26 content-type observation binding drifted")
    checked_extracted: dict[str, Any] | None = None
    if extracted is not None:
        if not isinstance(extracted, Mapping):
            raise ValueError("V2.52.26 extraction observation shape drifted")
        checked_extracted = extractor.validate_observation(extracted)
        if (
            checked_extracted["expected_body_byte_count"] != response_bytes
            or checked_extracted["body_byte_count"] != response_bytes
            or checked_extracted["expected_body_sha256"] != digest
            or checked_extracted["body_sha256"] != digest
        ):
            raise ValueError("V2.52.26 strict body binding drifted")

    if outcome == "success":
        if (
            attempt != 1
            or status != 200
            or response_bytes < 1
            or digest is None
            or checked_observed is None
            or checked_extracted is None
            or checked_extracted["extraction_completed"] is not True
            or checked_extracted["candidate_count_parity"] is not True
            or candidate_count != checked_extracted["extracted_candidate_count"]
            or candidate_count < extractor.parent.MINIMUM_DISTINCT_CANDIDATES
        ):
            raise ValueError("V2.52.26 successful receipt drifted")
    else:
        if candidate_count != 0:
            raise ValueError("V2.52.26 failed receipt retained candidates")
        if failure in {"semantic_gate", "wall_exceeded"} and digest is not None:
            if status != 200 or checked_observed is None or checked_extracted is None:
                raise ValueError("V2.52.26 post-body failure drifted")
        elif failure == "semantic_gate_exception" and digest is not None:
            if status != 200 or checked_observed is None or checked_extracted is not None:
                raise ValueError("V2.52.26 semantic exception failure drifted")
        elif digest is not None or response_bytes != 0 or checked_extracted is not None:
            raise ValueError("V2.52.26 pre-semantic failure retained body")
        if (
            failure == "clock_error"
            and (
                (
                    copied["public_address_dns_preflight_performed"] is False
                    and attempt != 0
                    or copied["public_address_dns_preflight_performed"] is True
                    and attempt not in {0, 1}
                )
                or status is not None
                or checked_observed is not None
            )
            or failure in {"dns_failure", "dns_nonpublic"}
            and (
                copied["public_address_dns_preflight_performed"] is not True
                or attempt != 0
                or status is not None
                or checked_observed is not None
            )
            or failure == "transport_timeout"
            and (attempt != 1 or status is not None or checked_observed is not None)
            or failure == "http_redirect"
            and (
                attempt != 1
                or not isinstance(status, int)
                or not 300 <= status <= 399
                or checked_observed is not None
            )
            or failure == "http_non200"
            and (
                attempt != 1
                or status == 200
                or isinstance(status, int)
                and 300 <= status <= 399
                or checked_observed is not None
            )
            or failure == "content_type_observation"
            and (attempt != 1 or status != 200 or checked_observed is not None)
            or failure in {"empty_response", "response_oversize", "stream_error"}
            and (attempt != 1 or status != 200 or checked_observed is None)
            or failure in {"semantic_gate", "semantic_gate_exception"}
            and (attempt != 1 or status != 200 or checked_observed is None)
            or failure == "wall_exceeded"
            and (
                status is not None
                or checked_observed is not None
                or checked_extracted is not None
            )
        ):
            raise ValueError("V2.52.26 failure-stage state drifted")
    return copied


__all__ = [
    "CONNECT_TIMEOUT_SECONDS",
    "ENDPOINT",
    "FAILURE_CODES",
    "MAXIMUM_RESPONSE_BYTES",
    "POLICY_ID",
    "READ_TIMEOUT_SECONDS",
    "ROLE",
    "TOTAL_WALL_SECONDS",
    "fetch_strict_cran_candidates",
    "validate_receipt",
]
