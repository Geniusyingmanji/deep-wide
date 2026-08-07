"""Header-only, deadline-aware Tavily URL-lead transport for exact runs.

Credentials are caller-injected in memory.  This module never reads the
environment, files, keyrings, benchmark metadata, or evaluator state.  Tavily
answer/snippet/raw-content/score fields are discarded; only canonical URL
leads and bounded titles survive until the existing deterministic page fetch.
"""

from __future__ import annotations

import fcntl
import json
import math
import os
import stat
import threading
import time
from collections.abc import Iterable, Mapping
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable

import requests

from .clients import SearchRequestError, canonicalize_url
from .v24263_global_model_limiter import payload_sha256
from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
)


POLICY_ID = "v24796_deadline_tavily_url_leads_v1"
POOL_ID = "v24796_global_tavily_key_slots_v1"
ROLE = "v24796_deadline_tavily_search_receipt"
ENDPOINT = "https://api.tavily.com/search"
KEY_LOCAL_STATUSES = frozenset({401, 403, 432})
RETRYABLE_STATUSES = frozenset({408, 409, 429})
STATUS_BUCKETS = (
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
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "pool_id",
        "key_slot_cap",
        "provider_attempts",
        "successful_queries",
        "failed_queries",
        "slot_acquisitions",
        "slot_timeouts",
        "total_slot_wait_seconds",
        "max_slot_wait_seconds",
        "key_local_disables",
        "retryable_responses",
        "transport_failures",
        "invalid_payloads",
        "credential_echo_rejections",
        "projected_url_leads",
        "invalid_or_duplicate_results",
        *STATUS_BUCKETS,
        "provider_answer_snippet_raw_content_or_score_forwarded",
        "deterministic_public_page_fetch_is_only_active_evidence",
        "credential_value_persisted_hashed_emitted_or_in_error",
        "query_url_page_prediction_answer_or_opaque_id_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
)


def _credentials(values: Iterable[str]) -> tuple[str, ...]:
    keys = tuple(str(value).strip() for value in values if str(value).strip())
    if (
        not keys
        or len(keys) > 64
        or len(set(keys)) != len(keys)
        or any(
            not 8 <= len(key) <= 1024
            or not key.isascii()
            or any(
                not (character.isalnum() or character in "-_.")
                for character in key
            )
            for key in keys
        )
    ):
        raise ValueError("V2.47.96 credential pool is invalid")
    return keys


def _ordinary_directory(path: Path, output_root: Path) -> Path:
    root = output_root.resolve()
    target = path.resolve(strict=False)
    if (
        output_root.is_symlink()
        or not output_root.is_dir()
        or path.is_symlink()
        or not path.is_dir()
        or not target.is_relative_to(root)
    ):
        raise ValueError("V2.47.96 key slot directory escaped output root")
    return target


def _slot_path(directory: Path, index: int) -> Path:
    return directory / f"slot_{index + 1:02d}.lock"


def prepare_key_slots(path: Path, key_count: int) -> None:
    if (
        isinstance(key_count, bool)
        or not isinstance(key_count, int)
        or not 1 <= key_count <= 64
    ):
        raise ValueError("V2.47.96 key slot count is invalid")
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    for index in range(key_count):
        slot = _slot_path(path, index)
        descriptor = os.open(
            slot,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NOFOLLOW
            | os.O_CLOEXEC,
            0o600,
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "artifact_version": 1,
                    "role": "v24796_tavily_key_slot",
                    "slot": index + 1,
                    "disabled": False,
                },
                handle,
                sort_keys=True,
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())


def _read_slot(handle: Any, *, expected: int) -> dict[str, Any]:
    handle.seek(0)
    try:
        value = json.load(handle)
    except (json.JSONDecodeError, OSError):
        raise RuntimeError("V2.47.96 key slot state is invalid") from None
    if (
        not isinstance(value, dict)
        or value.get("role") != "v24796_tavily_key_slot"
        or value.get("slot") != expected + 1
        or not isinstance(value.get("disabled"), bool)
    ):
        raise RuntimeError("V2.47.96 key slot identity drifted")
    return value


def _write_disabled(handle: Any, *, index: int, status: int) -> None:
    handle.seek(0)
    handle.truncate()
    json.dump(
        {
            "artifact_version": 1,
            "role": "v24796_tavily_key_slot",
            "slot": index + 1,
            "disabled": True,
            "disabled_status": int(status),
        },
        handle,
        sort_keys=True,
    )
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())


def _status_bucket(status: int) -> str:
    if 200 <= status < 300:
        return "status_2xx"
    if status in {401, 403, 408, 409, 429, 432}:
        return f"status_{status}"
    if status >= 500:
        return "status_5xx"
    return "status_other"


class DeadlineTavilyThinCompatibilityClient(
    ThinSameResponseCitationTitleBackfillSearchClient
):
    """Direct URL-lead search compatible with the frozen V2.46.30 runtime."""

    def __init__(
        self,
        *args: Any,
        credentials: Iterable[str],
        key_slot_directory: Path,
        output_root: Path,
        direct_timeout_seconds: int = 45,
        direct_workers: int = 4,
        direct_post: Any | None = None,
        slot_monotonic: Callable[[], float] = time.monotonic,
        slot_sleeper: Callable[[float], None] = time.sleep,
        slot_poll_seconds: float = 0.025,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._credentials = _credentials(credentials)
        if (
            isinstance(direct_timeout_seconds, bool)
            or not isinstance(direct_timeout_seconds, int)
            or not 1 <= direct_timeout_seconds <= 300
            or isinstance(direct_workers, bool)
            or not isinstance(direct_workers, int)
            or not 1 <= direct_workers <= 64
            or isinstance(slot_poll_seconds, bool)
            or not isinstance(slot_poll_seconds, (int, float))
            or not math.isfinite(float(slot_poll_seconds))
            or not 0 < float(slot_poll_seconds) <= 1
        ):
            raise ValueError("V2.47.96 direct search configuration is invalid")
        self.key_slot_directory = _ordinary_directory(
            key_slot_directory, output_root
        )
        self.direct_timeout_seconds = direct_timeout_seconds
        self.direct_workers = direct_workers
        self.slot_monotonic = slot_monotonic
        self.slot_sleeper = slot_sleeper
        self.slot_poll_seconds = float(slot_poll_seconds)
        self._key_slots = tuple(
            _slot_path(self.key_slot_directory, index)
            for index in range(len(self._credentials))
        )
        if any(path.is_symlink() or not path.is_file() for path in self._key_slots):
            raise ValueError("V2.47.96 key slot file is absent")
        self._direct_lock = threading.Lock()
        self._direct_next = 0
        self._direct_stats = {
            "provider_attempts": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "slot_acquisitions": 0,
            "slot_timeouts": 0,
            "total_slot_wait_seconds": 0.0,
            "max_slot_wait_seconds": 0.0,
            "key_local_disables": 0,
            "retryable_responses": 0,
            "transport_failures": 0,
            "invalid_payloads": 0,
            "credential_echo_rejections": 0,
            "projected_url_leads": 0,
            "invalid_or_duplicate_results": 0,
            **{name: 0 for name in STATUS_BUCKETS},
        }
        self._direct_thread_local = threading.local()
        self._direct_post = direct_post

    def _post(self) -> Any:
        if self._direct_post is not None:
            return self._direct_post
        session = getattr(self._direct_thread_local, "session", None)
        if session is None:
            session = requests.Session()
            session.trust_env = False
            session.auth = None
            session.headers.clear()
            session.proxies.clear()
            session.cookies.clear()
            self._direct_thread_local.session = session
        return session.post

    def _stat(self, name: str, amount: int | float = 1) -> None:
        with self._direct_lock:
            self._direct_stats[name] += amount

    def _slot_timeout(self, waited: float) -> SearchRequestError:
        with self._direct_lock:
            self._direct_stats["slot_timeouts"] += 1
            self._direct_stats["total_slot_wait_seconds"] += waited
            self._direct_stats["max_slot_wait_seconds"] = max(
                self._direct_stats["max_slot_wait_seconds"], waited
            )
        return SearchRequestError(
            "V2.47.96 direct-search key slot deadline exhausted"
        )

    def _acquire_key_slot(self) -> tuple[Any, int, str]:
        started = float(self.slot_monotonic())
        with self._direct_lock:
            offset = (os.getpid() + self._direct_next) % len(self._key_slots)
            self._direct_next += 1
        while True:
            enabled_seen = False
            for delta in range(len(self._key_slots)):
                index = (offset + delta) % len(self._key_slots)
                path = self._key_slots[index]
                descriptor = os.open(
                    path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC
                )
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    os.close(descriptor)
                    raise RuntimeError("V2.47.96 key slot is not regular")
                handle = os.fdopen(descriptor, "r+", encoding="utf-8")
                try:
                    fcntl.flock(
                        handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                    )
                except BlockingIOError:
                    handle.close()
                    enabled_seen = True
                    continue
                state = _read_slot(handle, expected=index)
                if state["disabled"]:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    handle.close()
                    continue
                enabled_seen = True
                waited = max(0.0, float(self.slot_monotonic()) - started)
                if self.remaining_effect_seconds() < self.minimum_attempt_seconds:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    handle.close()
                    raise self._slot_timeout(waited)
                with self._direct_lock:
                    self._direct_stats["slot_acquisitions"] += 1
                    self._direct_stats["total_slot_wait_seconds"] += waited
                    self._direct_stats["max_slot_wait_seconds"] = max(
                        self._direct_stats["max_slot_wait_seconds"], waited
                    )
                return handle, index, self._credentials[index]
            if not enabled_seen:
                raise SearchRequestError(
                    "V2.47.96 all direct-search key slots are disabled"
                )
            remaining = self.remaining_effect_seconds()
            if remaining < self.minimum_attempt_seconds:
                waited = max(0.0, float(self.slot_monotonic()) - started)
                raise self._slot_timeout(waited)
            self.slot_sleeper(min(self.slot_poll_seconds, remaining))

    def _direct_search(
        self, query: str, *, max_results: int, search_depth: str
    ) -> dict[str, Any]:
        normalized = " ".join(str(query).split()).strip()
        if (
            not normalized
            or len(normalized) > 32_768
            or isinstance(max_results, bool)
            or not isinstance(max_results, int)
            or not 1 <= max_results <= 20
            or search_depth not in {"basic", "advanced", "fast", "ultra-fast"}
            or any(key in normalized for key in self._credentials)
        ):
            raise ValueError("V2.47.96 direct query shape is invalid")
        body = json.dumps(
            {
                "query": normalized,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_answer": False,
                "include_raw_content": False,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        attempts = max(2, len(self._credentials))
        for _attempt in range(attempts):
            try:
                handle, index, key = self._acquire_key_slot()
            except SearchRequestError:
                break
            terminal_key_local = False
            try:
                remaining = self.remaining_effect_seconds()
                if remaining < self.minimum_attempt_seconds:
                    raise self._slot_timeout(0.0)
                self._increment("hosted_search_attempts")
                self._stat("provider_attempts")
                try:
                    response = self._post()(
                        ENDPOINT,
                        headers={
                            "Authorization": "Bearer " + key,
                            "Content-Type": "application/json",
                        },
                        data=body,
                        timeout=min(self.direct_timeout_seconds, remaining),
                        allow_redirects=False,
                        verify=True,
                    )
                    self._increment("calls")
                    status = int(response.status_code)
                    self._stat(_status_bucket(status))
                    if status in KEY_LOCAL_STATUSES:
                        _write_disabled(handle, index=index, status=status)
                        self._stat("key_local_disables")
                        terminal_key_local = True
                        continue
                    if status in RETRYABLE_STATUSES or status >= 500:
                        self._stat("retryable_responses")
                        continue
                    if 300 <= status < 400 or status >= 400:
                        break
                    payload = response.json()
                except (requests.ConnectionError, requests.Timeout, json.JSONDecodeError):
                    self._increment("transport_failures")
                    self._stat("transport_failures")
                    continue
                if not isinstance(payload, Mapping):
                    self._stat("invalid_payloads")
                    continue
                serialized = json.dumps(payload, ensure_ascii=False)
                if any(secret in serialized for secret in self._credentials):
                    self._stat("credential_echo_rejections")
                    break
                leads: list[dict[str, Any]] = []
                seen: set[str] = set()
                raw_results = payload.get("results") or []
                if not isinstance(raw_results, list):
                    self._stat("invalid_payloads")
                    continue
                invalid = 0
                for raw in raw_results:
                    if not isinstance(raw, Mapping):
                        invalid += 1
                        continue
                    supplied = str(raw.get("url", "")).strip()
                    canonical = canonicalize_url(supplied)
                    if not canonical or canonical in seen:
                        invalid += 1
                        continue
                    seen.add(canonical)
                    leads.append(
                        {
                            "title": " ".join(str(raw.get("title", "")).split())[:500],
                            "url": canonical,
                            "fetch_url": supplied,
                            "content": "",
                            "raw_content": "",
                            "score": None,
                            "source_type": "tavily_untrusted_url_lead",
                        }
                    )
                    if len(leads) >= max_results:
                        break
                invalid += max(0, len(raw_results) - len(leads) - invalid)
                self._stat("projected_url_leads", len(leads))
                self._stat("invalid_or_duplicate_results", invalid)
                if leads:
                    self._stat("successful_queries")
                    return {
                        "query": normalized,
                        "answer": "",
                        "results": leads,
                        "error": None,
                        "provider": "v24796-tavily-url-leads",
                    }
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()
            if terminal_key_local:
                continue
        self._increment("failures")
        self._stat("failed_queries")
        return {
            "query": normalized,
            "answer": "",
            "results": [],
            "error": "direct search request failed",
            "provider": "v24796-tavily-url-leads",
        }

    def search_many(
        self,
        queries: Iterable[str],
        *,
        max_results: int,
        search_depth: str = "advanced",
        include_raw_content: bool = False,
    ) -> list[dict[str, Any]]:
        if include_raw_content is not False:
            raise ValueError("V2.47.96 provider content forwarding is forbidden")
        unique: list[str] = []
        seen: set[str] = set()
        for raw in queries:
            query = " ".join(str(raw).split()).strip()
            folded = query.casefold()
            if query and folded not in seen:
                unique.append(query)
                seen.add(folded)
        if not unique:
            return []
        outputs: dict[str, dict[str, Any]] = {}
        workers = min(self.direct_workers, len(unique))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    self._direct_search,
                    query,
                    max_results=max_results,
                    search_depth=search_depth,
                ): query
                for query in unique
            }
            for future in as_completed(futures):
                query = futures[future]
                outputs[query] = future.result()
        return [outputs[query] for query in unique]

    def direct_search_receipt(self) -> dict[str, Any]:
        with self._direct_lock:
            stats = dict(self._direct_stats)
        value = {
            "artifact_version": 1,
            "role": ROLE,
            "policy_id": POLICY_ID,
            "pool_id": POOL_ID,
            "key_slot_cap": len(self._credentials),
            **{
                name: int(stats[name])
                for name in (
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
                    *STATUS_BUCKETS,
                )
            },
            "total_slot_wait_seconds": round(
                float(stats["total_slot_wait_seconds"]), 6
            ),
            "max_slot_wait_seconds": round(
                float(stats["max_slot_wait_seconds"]), 6
            ),
            "provider_answer_snippet_raw_content_or_score_forwarded": False,
            "deterministic_public_page_fetch_is_only_active_evidence": True,
            "credential_value_persisted_hashed_emitted_or_in_error": False,
            "query_url_page_prediction_answer_or_opaque_id_persisted": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    integer_fields = RECEIPT_KEYS - {
        "role",
        "policy_id",
        "pool_id",
        "total_slot_wait_seconds",
        "max_slot_wait_seconds",
        "provider_answer_snippet_raw_content_or_score_forwarded",
        "deterministic_public_page_fetch_is_only_active_evidence",
        "credential_value_persisted_hashed_emitted_or_in_error",
        "query_url_page_prediction_answer_or_opaque_id_persisted",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("pool_id") != POOL_ID
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integer_fields
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), (int, float))
            or not math.isfinite(float(copied[name]))
            or float(copied[name]) < 0
            for name in ("total_slot_wait_seconds", "max_slot_wait_seconds")
        )
        or copied.get("slot_acquisitions") != copied.get("provider_attempts")
        or copied.get("status_2xx", 0)
        + copied.get("status_401", 0)
        + copied.get("status_403", 0)
        + copied.get("status_408", 0)
        + copied.get("status_409", 0)
        + copied.get("status_429", 0)
        + copied.get("status_432", 0)
        + copied.get("status_5xx", 0)
        + copied.get("status_other", 0)
        > copied.get("provider_attempts", 0)
        or copied.get("provider_answer_snippet_raw_content_or_score_forwarded")
        is not False
        or copied.get("deterministic_public_page_fetch_is_only_active_evidence")
        is not True
        or copied.get("credential_value_persisted_hashed_emitted_or_in_error")
        is not False
        or copied.get("query_url_page_prediction_answer_or_opaque_id_persisted")
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.96 direct-search receipt drifted")
    return copied


def validate_search_class() -> None:
    cls = DeadlineTavilyThinCompatibilityClient
    owner = next(base for base in cls.__mro__ if "search_many" in base.__dict__)
    if (
        owner is not cls
        or not issubclass(
            cls, ThinSameResponseCitationTitleBackfillSearchClient
        )
    ):
        raise RuntimeError("V2.47.96 direct-search class MRO drifted")


__all__ = [
    "DeadlineTavilyThinCompatibilityClient",
    "ENDPOINT",
    "POLICY_ID",
    "POOL_ID",
    "prepare_key_slots",
    "validate_receipt",
    "validate_search_class",
]
