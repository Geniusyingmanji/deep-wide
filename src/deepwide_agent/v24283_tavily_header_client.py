"""Ephemeral header-authenticated Tavily client for neutral paired probes.

The legacy client places credentials in the JSON body.  This append-only
client follows the isolated V2.42.37 contract and sends a caller-supplied key
only in ``Authorization: Bearer``.  It never reads environment variables,
files or keyrings, never includes credential values in errors, and exposes the
same ``search_many`` interface used by the label-blind retrieval runtime.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests

from .clients import SearchRequestError, sanitize_search_response


POLICY_ID = "v24283_tavily_header_ephemeral_client_v1"
ENDPOINT = "https://api.tavily.com/search"
KEY_LOCAL_STATUSES = frozenset({401, 403, 432})
RETRYABLE_STATUSES = frozenset({408, 409, 429})


def _credentials(values: Iterable[str]) -> list[str]:
    keys = [str(value).strip() for value in values if str(value).strip()]
    if (
        not keys
        or len(keys) > 64
        or len(set(keys)) != len(keys)
        or any(
            not 8 <= len(key) <= 1024
            or not key.isascii()
            or any(not (character.isalnum() or character in "-_.") for character in key)
            for key in keys
        )
    ):
        raise ValueError("V2.42.83 credential pool is invalid")
    return keys


class TavilyHeaderClient:
    """Direct Tavily search with in-memory rotation and content-safe errors."""

    batch_size = 1
    fetch_pages = False

    def __init__(
        self,
        credentials: Iterable[str],
        *,
        timeout: int = 45,
        max_workers: int = 4,
        post: Any | None = None,
    ) -> None:
        self._keys = _credentials(credentials)
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 300:
            raise ValueError("V2.42.83 timeout is invalid")
        if (
            isinstance(max_workers, bool)
            or not isinstance(max_workers, int)
            or not 1 <= max_workers <= 32
        ):
            raise ValueError("V2.42.83 worker count is invalid")
        self.timeout = timeout
        self.max_workers = max_workers
        self._next = 0
        self._disabled: set[int] = set()
        self._lock = threading.Lock()
        self.calls = 0
        self.failures = 0
        self.transport_failures = 0
        self.status_counts: dict[int, int] = {}
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
            raise ValueError("V2.42.83 post transport is invalid")

    def _take_key(self) -> tuple[int, str] | None:
        with self._lock:
            for _ in range(len(self._keys)):
                index = self._next % len(self._keys)
                self._next += 1
                if index not in self._disabled:
                    return index, self._keys[index]
        return None

    def _disable(self, index: int) -> None:
        with self._lock:
            self._disabled.add(index)

    def search(
        self,
        query: str,
        *,
        max_results: int,
        search_depth: str = "advanced",
        include_raw_content: bool = False,
    ) -> dict[str, Any]:
        normalized = " ".join(str(query).split()).strip()
        if not normalized or len(normalized) > 32_768:
            raise ValueError("V2.42.83 query is invalid")
        if (
            isinstance(max_results, bool)
            or not isinstance(max_results, int)
            or not 1 <= max_results <= 20
            or search_depth not in {"basic", "advanced", "fast", "ultra-fast"}
            or not isinstance(include_raw_content, bool)
        ):
            raise ValueError("V2.42.83 request shape is invalid")
        if any(key in normalized for key in self._keys):
            raise ValueError("V2.42.83 query contains a caller credential")

        body = {
            "query": normalized,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": False,
            "include_raw_content": bool(include_raw_content),
        }
        encoded = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        attempts = max(2, len(self._keys))
        for _ in range(attempts):
            selected = self._take_key()
            if selected is None:
                break
            index, key = selected
            try:
                response = self._post(
                    ENDPOINT,
                    headers={
                        "Authorization": "Bearer " + key,
                        "Content-Type": "application/json",
                    },
                    data=encoded,
                    timeout=self.timeout,
                    allow_redirects=False,
                    verify=True,
                )
                with self._lock:
                    self.calls += 1
                    self.status_counts[response.status_code] = (
                        self.status_counts.get(response.status_code, 0) + 1
                    )
                if response.status_code in KEY_LOCAL_STATUSES:
                    self._disable(index)
                    continue
                if response.status_code in RETRYABLE_STATUSES or response.status_code >= 500:
                    continue
                if 300 <= response.status_code < 400:
                    break
                response.raise_for_status()
                payload = response.json()
                serialized = json.dumps(payload, ensure_ascii=False)
                if any(key in serialized for key in self._keys):
                    raise SearchRequestError("direct search echoed a caller credential")
                return sanitize_search_response(normalized, payload)
            except (requests.ConnectionError, requests.Timeout, json.JSONDecodeError):
                with self._lock:
                    self.transport_failures += 1
                continue
            except requests.HTTPError:
                break
        with self._lock:
            self.failures += 1
            disabled_count = len(self._disabled)
        raise SearchRequestError(
            "direct search failed "
            f"(disabled_keys={disabled_count}/{len(self._keys)}, "
            f"transport_failures={self.transport_failures})"
        )

    def search_many(
        self,
        queries: Iterable[str],
        *,
        max_results: int,
        search_depth: str = "advanced",
        include_raw_content: bool = False,
    ) -> list[dict[str, Any]]:
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
        workers = min(self.max_workers, len(unique))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    self.search,
                    query,
                    max_results=max_results,
                    search_depth=search_depth,
                    include_raw_content=include_raw_content,
                ): query
                for query in unique
            }
            for future in as_completed(futures):
                query = futures[future]
                try:
                    outputs[query] = future.result()
                except SearchRequestError:
                    outputs[query] = {
                        "query": query,
                        "answer": "",
                        "results": [],
                        "error": "direct search request failed",
                    }
        return [outputs[query] for query in unique]


__all__ = ["ENDPOINT", "POLICY_ID", "TavilyHeaderClient"]
