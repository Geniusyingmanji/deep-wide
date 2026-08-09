"""Same-process, one-shot readiness capability for the Tavily pool.

The probe is intentionally benchmark-blind.  Every ephemeral credential is
tested once with the frozen rate-aware production transport and one fixed
neutral public-documentation query.  Only aggregate counters are returned;
credential values and hashes, per-key rows, query text, URLs, provider payloads,
and pages are never included in the receipt.

A successful probe returns an in-memory capability that can release the exact
same tuple of credentials once.  A failed probe returns no capability.  This
lets an armed production runner prove readiness and later start with the same
memory-resident pool without persisting a credential fingerprint.
"""

from __future__ import annotations

import copy
import json
import math
import secrets
import time
from collections import Counter
from collections.abc import Callable, Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from .v24796_deadline_tavily_search import validate_receipt as validate_direct
from .v24852_rate_aware_tavily_search import (
    RateAwareDeadlineTavilyThinCompatibilityClient,
    prepare_rate_aware_key_slots,
    validate_receipt as validate_rate,
)
from .v24263_global_model_limiter import payload_sha256


POLICY_ID = "v24970_same_process_all_key_search_readiness_v1"
ROLE = "v24970_same_process_search_readiness_receipt"
EXPECTED_KEY_COUNT = 12
EXECUTOR_CONCURRENCY = 12
ATTEMPTS_PER_KEY = 1
RESULTS_PER_QUERY = 1
DEADLINE_SECONDS = 45.0
NEUTRAL_QUERY = "Python 3.13 official documentation what's new"
MODEL_PROXY_URL = "http://127.0.0.1:9878/responses"
MODEL_NAME = "gpt-5.6-sol"

_DIRECT_COUNTERS = (
    "provider_attempts",
    "successful_queries",
    "failed_queries",
    "slot_acquisitions",
    "slot_timeouts",
    "key_local_disables",
    "retryable_responses",
    "transport_failures",
    "invalid_payloads",
    "credential_echo_rejections",
    "projected_url_leads",
    "invalid_or_duplicate_results",
    "status_2xx",
    "status_401",
    "status_403",
    "status_408",
    "status_409",
    "status_429",
    "status_432",
    "status_5xx",
    "status_other",
)
_RATE_COUNTERS = (
    "provider_start_reservations",
    "provider_gate_timeouts",
    "provider_pacing_wait_events",
    "provider_cooldown_wait_events",
    "provider_cooldown_activations",
    "retry_after_values_honored",
    "provider_429_responses",
    "provider_non429_retryable_responses",
    "provider_transport_retry_events",
)
_DISALLOWED_DIRECT_NONZERO = (
    "failed_queries",
    "slot_timeouts",
    "key_local_disables",
    "retryable_responses",
    "transport_failures",
    "invalid_payloads",
    "credential_echo_rejections",
    "status_401",
    "status_403",
    "status_408",
    "status_409",
    "status_429",
    "status_432",
    "status_5xx",
    "status_other",
)
_DISALLOWED_RATE_NONZERO = (
    "provider_gate_timeouts",
    "provider_cooldown_wait_events",
    "provider_cooldown_activations",
    "retry_after_values_honored",
    "provider_429_responses",
    "provider_non429_retryable_responses",
    "provider_transport_retry_events",
)
_CAPABILITY_SENTINEL = object()


def _credentials(values: Iterable[str]) -> tuple[str, ...]:
    copied = tuple(str(value) for value in values)
    if (
        len(copied) != EXPECTED_KEY_COUNT
        or len(set(copied)) != EXPECTED_KEY_COUNT
        or any(
            not 8 <= len(value) <= 1024
            or not value.isascii()
            or any(
                not (character.isalnum() or character in "-_.")
                for character in value
            )
            for value in copied
        )
    ):
        raise ValueError("V2.49.70 requires twelve distinct ephemeral credentials")
    return copied


def _nonce(value: str | None) -> str:
    observed = secrets.token_hex(16) if value is None else str(value)
    if (
        not 16 <= len(observed) <= 128
        or not observed.isascii()
        or any(not (character.isalnum() or character in "-_") for character in observed)
    ):
        raise ValueError("V2.49.70 session nonce is invalid")
    return observed


def _ordinary_empty_root(path: Path) -> Path:
    if path.is_symlink() or not path.is_dir():
        raise ValueError("V2.49.70 readiness root is not an ordinary directory")
    target = path.resolve()
    if any(path.iterdir()):
        raise ValueError("V2.49.70 readiness root is not empty")
    return target


class SearchReadinessCapability:
    """Non-serializable, redacted, single-consumer credential handoff."""

    __slots__ = ("_credentials", "_receipt_sha256", "_consumed")

    def __init__(
        self,
        credentials: tuple[str, ...],
        receipt_sha256: str,
        *,
        sentinel: object,
    ) -> None:
        if sentinel is not _CAPABILITY_SENTINEL:
            raise TypeError("V2.49.70 capability construction is private")
        self._credentials = credentials
        self._receipt_sha256 = receipt_sha256
        self._consumed = False

    def __repr__(self) -> str:
        return "<SearchReadinessCapability redacted one-shot>"

    def __copy__(self) -> Any:
        raise TypeError("V2.49.70 capability cannot be copied")

    def __deepcopy__(self, _memo: dict[int, Any]) -> Any:
        raise TypeError("V2.49.70 capability cannot be copied")

    def __reduce__(self) -> Any:
        raise TypeError("V2.49.70 capability cannot be serialized")

    @property
    def consumed(self) -> bool:
        return self._consumed

    def consume(self, receipt: Mapping[str, Any]) -> tuple[str, ...]:
        checked = validate_receipt(receipt)
        if self._consumed or checked["receipt_payload_sha256"] != self._receipt_sha256:
            raise RuntimeError("V2.49.70 capability is consumed or receipt-mismatched")
        credentials = self._credentials
        self._credentials = ()
        self._consumed = True
        return credentials


def _client(
    credential: str,
    directory: Path,
    output_root: Path,
    *,
    direct_post: Any | None,
) -> RateAwareDeadlineTavilyThinCompatibilityClient:
    prepare_rate_aware_key_slots(directory, 1)
    return RateAwareDeadlineTavilyThinCompatibilityClient(
        MODEL_PROXY_URL,
        MODEL_NAME,
        timeout=30,
        max_retries=1,
        absolute_deadline=time.monotonic() + DEADLINE_SECONDS,
        cleanup_reserve_seconds=3,
        minimum_attempt_seconds=0.05,
        max_workers=1,
        batch_size=1,
        search_context_size="low",
        max_output_tokens=1000,
        fetch_pages=False,
        fetch_workers=1,
        fetch_timeout=10,
        max_page_chars=1000,
        hard_fetch_deadline_seconds=25,
        credentials=(credential,),
        key_slot_directory=directory,
        output_root=output_root,
        direct_timeout_seconds=30,
        direct_workers=1,
        direct_post=direct_post,
        provider_attempt_cap=ATTEMPTS_PER_KEY,
    )


def _probe_one(
    ordinal: int,
    credential: str,
    root: Path,
    post_factory: Callable[[int], Any] | None,
) -> dict[str, int | bool]:
    directory = root / f"probe_{ordinal:02d}"
    client = _client(
        credential,
        directory,
        root,
        direct_post=None if post_factory is None else post_factory(ordinal),
    )
    try:
        batches = client.search_many(
            [NEUTRAL_QUERY],
            max_results=RESULTS_PER_QUERY,
            search_depth="basic",
            include_raw_content=False,
        )
    except BaseException:
        batches = []
    direct = validate_direct(client.direct_search_receipt())
    rate = validate_rate(client.rate_aware_search_receipt())
    usable_batch = (
        len(batches) == 1
        and isinstance(batches[0], Mapping)
        and bool(batches[0].get("results"))
        and not batches[0].get("error")
    )
    healthy = (
        usable_batch
        and direct["provider_attempts"] == 1
        and direct["slot_acquisitions"] == 1
        and direct["successful_queries"] == 1
        and direct["status_2xx"] == 1
        and direct["projected_url_leads"] >= 1
        and all(direct[name] == 0 for name in _DISALLOWED_DIRECT_NONZERO)
        and rate["provider_start_reservations"] == 1
        and all(rate[name] == 0 for name in _DISALLOWED_RATE_NONZERO)
    )
    return {
        "healthy": bool(healthy),
        **{name: int(direct[name]) for name in _DIRECT_COUNTERS},
        **{name: int(rate[name]) for name in _RATE_COUNTERS},
    }


def _aggregate(rows: list[dict[str, int | bool]]) -> dict[str, Any]:
    counters: Counter[str] = Counter()
    healthy = 0
    for row in rows:
        healthy += int(row["healthy"] is True)
        for name, value in row.items():
            if name != "healthy":
                counters[name] += int(value)
    return {
        "tested_key_count": len(rows),
        "healthy_key_count": healthy,
        "unhealthy_key_count": len(rows) - healthy,
        **{
            name: int(counters[name])
            for name in sorted(set(_DIRECT_COUNTERS) | set(_RATE_COUNTERS))
        },
    }


def _passed(aggregate: Mapping[str, Any]) -> bool:
    return (
        aggregate.get("tested_key_count") == EXPECTED_KEY_COUNT
        and aggregate.get("healthy_key_count") == EXPECTED_KEY_COUNT
        and aggregate.get("unhealthy_key_count") == 0
        and aggregate.get("provider_attempts") == EXPECTED_KEY_COUNT
        and aggregate.get("slot_acquisitions") == EXPECTED_KEY_COUNT
        and aggregate.get("provider_start_reservations") == EXPECTED_KEY_COUNT
        and aggregate.get("successful_queries") == EXPECTED_KEY_COUNT
        and aggregate.get("status_2xx") == EXPECTED_KEY_COUNT
        and aggregate.get("projected_url_leads", 0) >= EXPECTED_KEY_COUNT
        and all(aggregate.get(name) == 0 for name in _DISALLOWED_DIRECT_NONZERO)
        and all(aggregate.get(name) == 0 for name in _DISALLOWED_RATE_NONZERO)
    )


def run_readiness(
    credentials: Iterable[str],
    root: Path,
    *,
    session_nonce: str | None = None,
    post_factory: Callable[[int], Any] | None = None,
) -> tuple[dict[str, Any], SearchReadinessCapability | None]:
    """Probe all keys once and return aggregate receipt plus one-shot capability."""

    copied = _credentials(credentials)
    target = _ordinary_empty_root(root)
    nonce = _nonce(session_nonce)
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=EXECUTOR_CONCURRENCY) as pool:
        rows = list(
            pool.map(
                lambda item: _probe_one(
                    item[0], item[1], target, post_factory
                ),
                enumerate(copied, start=1),
            )
        )
    aggregate = _aggregate(rows)
    passed = _passed(aggregate)
    receipt: dict[str, Any] = {
        "artifact_version": 1,
        "role": ROLE,
        "policy_id": POLICY_ID,
        "session_nonce": nonce,
        "created_at_unix": int(time.time()),
        "wall_seconds": round(max(0.0, time.monotonic() - started), 6),
        "aggregate": aggregate,
        "passed": passed,
        "same_process_same_memory_pool_handoff_required": True,
        "credential_values_or_hashes_persisted_emitted_or_logged": False,
        "per_key_rows_persisted": False,
        "query_url_title_snippet_page_answer_or_provider_payload_persisted": False,
        "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read": False,
        "model_fetch_evaluator_or_benchmark_forward_effect": False,
        "benchmark_forward_authorized_by_receipt_alone": False,
    }
    receipt["receipt_payload_sha256"] = payload_sha256(receipt)
    checked = validate_receipt(receipt)
    capability = (
        SearchReadinessCapability(
            copied,
            checked["receipt_payload_sha256"],
            sentinel=_CAPABILITY_SENTINEL,
        )
        if passed
        else None
    )
    return checked, capability


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    aggregate = copied.get("aggregate")
    expected_keys = {
        "artifact_version",
        "role",
        "policy_id",
        "session_nonce",
        "created_at_unix",
        "wall_seconds",
        "aggregate",
        "passed",
        "same_process_same_memory_pool_handoff_required",
        "credential_values_or_hashes_persisted_emitted_or_logged",
        "per_key_rows_persisted",
        "query_url_title_snippet_page_answer_or_provider_payload_persisted",
        "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read",
        "model_fetch_evaluator_or_benchmark_forward_effect",
        "benchmark_forward_authorized_by_receipt_alone",
        "receipt_payload_sha256",
    }
    aggregate_keys = {
        "tested_key_count",
        "healthy_key_count",
        "unhealthy_key_count",
        *(_DIRECT_COUNTERS),
        *(_RATE_COUNTERS),
    }
    if (
        set(copied) != expected_keys
        or copied.get("artifact_version") != 1
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or _nonce(str(copied.get("session_nonce", "")))
        != copied.get("session_nonce")
        or isinstance(copied.get("created_at_unix"), bool)
        or not isinstance(copied.get("created_at_unix"), int)
        or copied["created_at_unix"] < 0
        or isinstance(copied.get("wall_seconds"), bool)
        or not isinstance(copied.get("wall_seconds"), (int, float))
        or not math.isfinite(float(copied["wall_seconds"]))
        or float(copied["wall_seconds"]) < 0
        or not isinstance(aggregate, dict)
        or set(aggregate) != aggregate_keys
        or any(
            isinstance(aggregate.get(name), bool)
            or not isinstance(aggregate.get(name), int)
            or aggregate[name] < 0
            for name in aggregate_keys
        )
        or aggregate["healthy_key_count"] + aggregate["unhealthy_key_count"]
        != aggregate["tested_key_count"]
        or aggregate["provider_attempts"] != aggregate["slot_acquisitions"]
        or copied.get("passed") is not _passed(aggregate)
        or copied.get("same_process_same_memory_pool_handoff_required") is not True
        or copied.get("credential_values_or_hashes_persisted_emitted_or_logged")
        is not False
        or copied.get("per_key_rows_persisted") is not False
        or copied.get(
            "query_url_title_snippet_page_answer_or_provider_payload_persisted"
        )
        is not False
        or copied.get(
            "benchmark_manifest_question_prediction_mapping_gold_category_split_evaluator_score_reward_read"
        )
        is not False
        or copied.get("model_fetch_evaluator_or_benchmark_forward_effect") is not False
        or copied.get("benchmark_forward_authorized_by_receipt_alone") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.70 readiness receipt drifted")
    return copied


__all__ = [
    "ATTEMPTS_PER_KEY",
    "DEADLINE_SECONDS",
    "EXECUTOR_CONCURRENCY",
    "EXPECTED_KEY_COUNT",
    "NEUTRAL_QUERY",
    "POLICY_ID",
    "RESULTS_PER_QUERY",
    "ROLE",
    "SearchReadinessCapability",
    "run_readiness",
    "validate_receipt",
]
