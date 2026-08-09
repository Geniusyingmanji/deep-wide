"""Strict contracts for bounded World Bank aggregate snapshot transport.

The V2.49.51 external gate used one opaque ``urllib`` attempt for each bulk
World Bank response.  A read timeout occurred before any response, prediction,
or evaluator artifact was published.  This append-only transport contract
allows only the frozen country catalog and ``country/all/indicator`` JSON URL
shapes.  A helper may make at most three bounded provider attempts.  Its result
is sealed and exposes a content-free attempt ledger plus raw JSON only to the
calling snapshot freezer.

This module performs validation only.  It has no file, environment, process,
network, model, benchmark metadata, answer, evaluator, score, reward, or
credential capability.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl, urlsplit


POLICY_ID = "v24952_bounded_worldbank_aggregate_snapshot_transport_v1"
HELPER_ROLE = "v24952_worldbank_snapshot_fetch_result"
WORLD_BANK_HOST = "api.worldbank.org"
MAXIMUM_ATTEMPTS = 3
CONNECT_TIMEOUT_SECONDS = 5.0
READ_TIMEOUT_SECONDS = 10.0
HELPER_TOTAL_WALL_SECONDS = 50.0
MAXIMUM_RESPONSE_BYTES = 2 * 1024 * 1024
INDICATOR = re.compile(r"[A-Z][A-Z0-9.]{4,40}")
YEAR = re.compile(r"20[0-3][0-9]")
SHA256 = re.compile(r"[0-9a-f]{64}")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def snapshot_request_key(url: object) -> str:
    """Validate one immutable aggregate API URL and return its request key."""

    try:
        parsed = urlsplit(str(url))
    except ValueError as exc:
        raise ValueError("V2.49.52 snapshot URL is invalid") from exc
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").casefold() != WORLD_BANK_HOST
        or parsed.port is not None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError("V2.49.52 snapshot URL authority drifted")
    if parsed.path == "/v2/country":
        if pairs != [("format", "json"), ("per_page", "400")]:
            raise ValueError("V2.49.52 catalog query drifted")
        return "country_catalog"
    parts = parsed.path.strip("/").split("/")
    parameters = dict(pairs)
    if (
        len(parts) != 5
        or parts[:3] != ["v2", "country", "all"]
        or parts[3] != "indicator"
        or INDICATOR.fullmatch(parts[4]) is None
        or pairs
        != [
            ("date", parameters.get("date", "")),
            ("format", "json"),
            ("per_page", "400"),
        ]
        or YEAR.fullmatch(parameters.get("date", "")) is None
    ):
        raise ValueError("V2.49.52 indicator snapshot URL shape drifted")
    return f"{parts[4]}@{parameters['date']}"


def validate_helper_result(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    expected = {
        "artifact_version",
        "role",
        "policy_id",
        "status",
        "request_key",
        "url_sha256",
        "raw_content",
        "attempt_count",
        "attempts",
        "elapsed_seconds",
        "response_bytes",
        "response_sha256",
        "content_free_receipt",
        "result_payload_sha256",
    }
    unsigned = dict(copied)
    seal = unsigned.pop("result_payload_sha256", None)
    attempts = copied.get("attempts")
    receipt = copied.get("content_free_receipt")
    if (
        set(copied) != expected
        or copied.get("artifact_version") != 1
        or copied.get("role") != HELPER_ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("status") not in {"ok", "exhausted"}
        or not isinstance(copied.get("request_key"), str)
        or not copied["request_key"]
        or SHA256.fullmatch(str(copied.get("url_sha256", ""))) is None
        or not isinstance(copied.get("raw_content"), str)
        or isinstance(copied.get("attempt_count"), bool)
        or not isinstance(copied.get("attempt_count"), int)
        or not 1 <= copied["attempt_count"] <= MAXIMUM_ATTEMPTS
        or not isinstance(attempts, list)
        or len(attempts) != copied["attempt_count"]
        or isinstance(copied.get("elapsed_seconds"), bool)
        or not isinstance(copied.get("elapsed_seconds"), (int, float))
        or not math.isfinite(float(copied["elapsed_seconds"]))
        or not 0 <= float(copied["elapsed_seconds"]) <= HELPER_TOTAL_WALL_SECONDS
        or isinstance(copied.get("response_bytes"), bool)
        or not isinstance(copied.get("response_bytes"), int)
        or not 0 <= copied["response_bytes"] <= MAXIMUM_RESPONSE_BYTES
        or not isinstance(receipt, Mapping)
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.52 helper result drifted")
    successes = 0
    for index, attempt in enumerate(attempts, 1):
        if (
            not isinstance(attempt, Mapping)
            or set(attempt)
            != {
                "attempt",
                "outcome",
                "http_status",
                "error_type",
                "retryable",
                "elapsed_seconds",
                "response_bytes",
                "response_sha256",
            }
            or attempt.get("attempt") != index
            or attempt.get("outcome") not in {"success", "failure"}
            or (
                attempt.get("http_status") is not None
                and (
                    isinstance(attempt.get("http_status"), bool)
                    or not isinstance(attempt.get("http_status"), int)
                    or not 100 <= attempt["http_status"] <= 599
                )
            )
            or (
                attempt.get("error_type") is not None
                and not isinstance(attempt.get("error_type"), str)
            )
            or not isinstance(attempt.get("retryable"), bool)
            or isinstance(attempt.get("elapsed_seconds"), bool)
            or not isinstance(attempt.get("elapsed_seconds"), (int, float))
            or not math.isfinite(float(attempt["elapsed_seconds"]))
            or float(attempt["elapsed_seconds"]) < 0
            or isinstance(attempt.get("response_bytes"), bool)
            or not isinstance(attempt.get("response_bytes"), int)
            or not 0 <= attempt["response_bytes"] <= MAXIMUM_RESPONSE_BYTES
            or (
                attempt.get("response_sha256") is not None
                and SHA256.fullmatch(str(attempt["response_sha256"])) is None
            )
        ):
            raise ValueError("V2.49.52 helper attempt drifted")
        successes += int(attempt["outcome"] == "success")
    expected_receipt = {
        "request_key": copied["request_key"],
        "url_sha256": copied["url_sha256"],
        "maximum_attempts": MAXIMUM_ATTEMPTS,
        "connect_timeout_seconds": CONNECT_TIMEOUT_SECONDS,
        "read_timeout_seconds": READ_TIMEOUT_SECONDS,
        "helper_total_wall_seconds": HELPER_TOTAL_WALL_SECONDS,
        "maximum_response_bytes": MAXIMUM_RESPONSE_BYTES,
        "attempt_count": copied["attempt_count"],
        "attempts": attempts,
        "terminal_outcome": "success" if copied["status"] == "ok" else "exhausted",
        "elapsed_seconds": copied["elapsed_seconds"],
        "response_bytes": copied["response_bytes"],
        "response_sha256": copied["response_sha256"],
        "url_or_response_content_emitted": False,
        "benchmark_metadata_answer_evaluator_score_reward_or_credential_read": False,
    }
    expected_receipt["receipt_payload_sha256"] = payload_sha256(expected_receipt)
    if dict(receipt) != expected_receipt:
        raise ValueError("V2.49.52 content-free receipt drifted")
    if copied["status"] == "ok":
        raw = copied["raw_content"].encode()
        if (
            successes != 1
            or attempts[-1]["outcome"] != "success"
            or not raw
            or len(raw) != copied["response_bytes"]
            or hashlib.sha256(raw).hexdigest() != copied["response_sha256"]
        ):
            raise ValueError("V2.49.52 successful helper result drifted")
        try:
            json.loads(copied["raw_content"])
        except json.JSONDecodeError as exc:
            raise ValueError("V2.49.52 successful helper JSON drifted") from exc
    elif (
        successes != 0
        or copied["raw_content"] != ""
        or copied["response_bytes"] != 0
        or copied["response_sha256"] is not None
    ):
        raise ValueError("V2.49.52 exhausted helper result drifted")
    return copied


__all__ = [
    "CONNECT_TIMEOUT_SECONDS",
    "HELPER_ROLE",
    "HELPER_TOTAL_WALL_SECONDS",
    "MAXIMUM_ATTEMPTS",
    "MAXIMUM_RESPONSE_BYTES",
    "POLICY_ID",
    "READ_TIMEOUT_SECONDS",
    "payload_sha256",
    "snapshot_request_key",
    "validate_helper_result",
]
