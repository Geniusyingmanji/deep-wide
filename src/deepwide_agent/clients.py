"""Network clients used by the label-blind runtime.

Credentials are accepted only through environment variables and are never
included in returned traces or exception messages.
"""

from __future__ import annotations

import dataclasses
import json
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests


class ModelRequestError(RuntimeError):
    """A model request failed without exposing prompt or response content.

    ``model_traces`` is deliberately safe to persist.  It contains only
    request accounting and a coarse failure class/status, never credentials,
    request bodies, URLs, or provider error messages.
    """

    def __init__(
        self,
        message: str,
        *,
        model_traces: Iterable[dict[str, Any]] = (),
    ) -> None:
        super().__init__(message)
        self.model_traces = [dict(trace) for trace in model_traces]


class SearchRequestError(RuntimeError):
    pass


@dataclasses.dataclass
class ModelResult:
    text: str
    usage: dict[str, Any]
    response_id: str | None
    attempts: int
    request_index: int | None = None
    input_chars: int = 0
    input_utf8_bytes: int = 0
    request_body_bytes: int = 0
    max_output_tokens: int = 0
    output_truncated: bool = False


def extract_response_text(payload: dict[str, Any]) -> str:
    chunks: list[str] = []
    for item in payload.get("output", []) or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"}:
                chunks.append(str(content.get("text", "")))
    if chunks:
        return "\n".join(chunks).strip()
    return str(payload.get("output_text") or "").strip()


def parse_json_object(text: str) -> dict[str, Any]:
    candidate = text.strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError as raw_error:
        # Only treat a fence as an envelope when it wraps the entire response.
        # Visible benchmark questions often contain a literal ```markdown ...```
        # example inside an otherwise valid JSON string.
        fenced = re.fullmatch(
            r"```(?:json)?\s*(.*?)\s*```",
            candidate,
            re.DOTALL | re.IGNORECASE,
        )
        if fenced:
            value = json.loads(fenced.group(1).strip())
        else:
            start = candidate.find("{")
            if start < 0:
                raise ValueError("model did not return a JSON object") from raw_error
            try:
                value, _ = json.JSONDecoder().raw_decode(candidate[start:])
            except json.JSONDecodeError as embedded_error:
                raise embedded_error from raw_error
    if not isinstance(value, dict):
        raise ValueError("model JSON response is not an object")
    return value


class ResponsesClient:
    def __init__(
        self,
        url: str,
        model: str,
        reasoning_effort: str = "low",
        service_tier: str = "",
        timeout: int = 900,
        max_retries: int = 8,
    ) -> None:
        self.url = url
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.service_tier = service_tier
        self.timeout = timeout
        self.max_retries = max_retries
        self.requests = 0
        self.calls = 0
        self.failures = 0
        self.attempts = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.total_tokens = 0
        self._lock = threading.Lock()
        self._thread_local = threading.local()

    def _session(self) -> requests.Session:
        session = getattr(self._thread_local, "session", None)
        if session is None:
            session = requests.Session()
            self._thread_local.session = session
        return session

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> ModelResult:
        with self._lock:
            self.requests += 1
            request_index = self.requests
        body: dict[str, Any] = {
            "model": self.model,
            "input": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_output_tokens": max_output_tokens,
        }
        if self.reasoning_effort:
            body["reasoning"] = {"effort": self.reasoning_effort}
        if self.service_tier:
            body["service_tier"] = self.service_tier
        if json_mode:
            body["text"] = {"format": {"type": "json_object"}}
        input_chars = len(system) + len(user)
        input_utf8_bytes = len(system.encode("utf-8")) + len(user.encode("utf-8"))
        # Numeric envelope metadata is safe to persist and lets capacity
        # failures be compared without retaining prompt or response content.
        request_body_bytes = len(
            json.dumps(body, ensure_ascii=True, separators=(",", ":")).encode(
                "utf-8"
            )
        )

        last_status: int | None = None
        last_error_type = "request_exhausted"
        attempts_used = 0
        for attempt in range(1, self.max_retries + 1):
            attempts_used = attempt
            with self._lock:
                self.attempts += 1
            try:
                response = self._session().post(
                    self.url,
                    headers={"Content-Type": "application/json"},
                    json=body,
                    timeout=self.timeout,
                )
                last_status = response.status_code
                if response.status_code in {408, 409, 429} or response.status_code >= 500:
                    last_error_type = "retryable_http_status"
                    if attempt < self.max_retries:
                        delay = _retry_delay(response, attempt)
                        time.sleep(delay)
                    continue
                if response.status_code >= 400:
                    last_error_type = "terminal_http_status"
                    break
                payload = response.json()
                text = extract_response_text(payload)
                if not text:
                    last_error_type = "empty_output"
                    if attempt < self.max_retries:
                        time.sleep(min(2**attempt, 30))
                        continue
                    break
                usage = payload.get("usage", {}) or {}
                input_tokens = int(usage.get("input_tokens", 0) or 0)
                output_tokens = int(usage.get("output_tokens", 0) or 0)
                total_tokens = int(usage.get("total_tokens", 0) or 0)
                incomplete_details = payload.get("incomplete_details") or {}
                incomplete_reason = str(
                    incomplete_details.get("reason", "")
                    if isinstance(incomplete_details, dict)
                    else ""
                ).casefold()
                output_truncated = bool(
                    str(payload.get("status", "")).casefold() == "incomplete"
                    or incomplete_reason in {
                        "max_output_tokens",
                        "max_tokens",
                        "length",
                    }
                    or (
                        max_output_tokens > 0
                        and output_tokens >= max_output_tokens
                    )
                )
                with self._lock:
                    self.calls += 1
                    self.input_tokens += input_tokens
                    self.output_tokens += output_tokens
                    self.total_tokens += total_tokens or input_tokens + output_tokens
                return ModelResult(
                    text=text,
                    usage=usage,
                    response_id=payload.get("id"),
                    attempts=attempt,
                    request_index=request_index,
                    input_chars=input_chars,
                    input_utf8_bytes=input_utf8_bytes,
                    request_body_bytes=request_body_bytes,
                    max_output_tokens=max_output_tokens,
                    output_truncated=output_truncated,
                )
            except (requests.ConnectionError, requests.Timeout):
                last_error_type = "transport_error"
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2**attempt + random.random(), 60))
            except json.JSONDecodeError:
                last_error_type = "invalid_response_json"
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2**attempt + random.random(), 60))
        with self._lock:
            self.failures += 1
        failure_trace = {
            "purpose": "request_failure",
            "response_id": None,
            "usage": {},
            "attempts": attempts_used,
            "request_index": request_index,
            "success": False,
            "error_type": last_error_type,
            "last_status": last_status,
            "input_chars": input_chars,
            "input_utf8_bytes": input_utf8_bytes,
            "request_body_bytes": request_body_bytes,
            "max_output_tokens": max_output_tokens,
        }
        raise ModelRequestError(
            f"model request failed after {attempts_used} attempts (last_status={last_status})",
            model_traces=[failure_trace],
        )

    def complete_json(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        repair_tokens: int = 4096,
        max_parse_attempts: int = 3,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        first = self.complete(
            system,
            user,
            max_output_tokens=max_output_tokens,
            json_mode=True,
        )
        traces = [_model_trace(first, "initial")]
        try:
            return parse_json_object(first.text), traces
        except (ValueError, json.JSONDecodeError) as exc:
            previous = first.text
            previous_truncated = bool(
                getattr(first, "output_truncated", False)
            )
            last_error: Exception = exc
            for repair_index in range(1, max_parse_attempts):
                # A parse repair must have enough room to reproduce the object
                # it is repairing.  Escalate only after a response actually
                # reached its output boundary; ordinary small malformed JSON
                # keeps the cheaper bounded repair reservation.
                current_repair_tokens = (
                    max(repair_tokens, max_output_tokens)
                    if previous_truncated
                    else repair_tokens
                )
                try:
                    repair = self.complete(
                        "You repair malformed JSON. Return one valid JSON object only, without prose or fences.",
                        "Repair the following response while preserving its information. "
                        f"Parser error: {type(last_error).__name__}.\n\n{previous[:60000]}",
                        max_output_tokens=current_repair_tokens,
                        json_mode=True,
                    )
                except BaseException as exc:
                    prior = [dict(trace) for trace in traces]
                    failure = [
                        dict(trace)
                        for trace in (getattr(exc, "model_traces", []) or [])
                    ]
                    setattr(exc, "model_traces", [*prior, *failure])
                    raise
                traces.append(_model_trace(repair, f"json_repair_{repair_index}"))
                try:
                    return parse_json_object(repair.text), traces
                except (ValueError, json.JSONDecodeError) as repair_error:
                    previous = repair.text
                    previous_truncated = bool(
                        getattr(repair, "output_truncated", False)
                    )
                    last_error = repair_error
            error = ValueError(
                f"model did not produce parseable JSON after {max_parse_attempts} attempts: "
                f"{type(last_error).__name__}"
            )
            setattr(error, "model_traces", [dict(trace) for trace in traces])
            raise error from last_error


def _model_trace(result: ModelResult, purpose: str) -> dict[str, Any]:
    return {
        "purpose": purpose,
        "response_id": result.response_id,
        "usage": result.usage,
        "attempts": result.attempts,
        "request_index": getattr(result, "request_index", None),
        "success": True,
        "input_chars": int(getattr(result, "input_chars", 0) or 0),
        "input_utf8_bytes": int(getattr(result, "input_utf8_bytes", 0) or 0),
        "request_body_bytes": int(getattr(result, "request_body_bytes", 0) or 0),
        "max_output_tokens": int(getattr(result, "max_output_tokens", 0) or 0),
        "output_truncated": bool(
            getattr(result, "output_truncated", False)
        ),
    }


def _retry_delay(response: requests.Response, attempt: int) -> float:
    raw = response.headers.get("Retry-After", "")
    try:
        requested = max(float(raw), 1.0)
    except ValueError:
        requested = 1.0
    if response.status_code == 429:
        # A one-second Retry-After is often only the gateway's sampling
        # interval, not the time needed for a large reserved-output request to
        # regain capacity.  Exponential minimum backoff avoids burning every
        # retry in one short saturation burst.
        return min(max(requested, float(min(2**attempt, 60))), 90.0)
    if raw:
        return min(requested, 90.0)
    return min(2**attempt + random.random(), 60.0)


TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
}


def canonicalize_url(url: str) -> str:
    raw = url.strip()
    if not raw:
        return ""
    try:
        split = urlsplit(raw)
    except ValueError:
        return ""
    # A canonical web URL is also an ingestion boundary.  Returning malformed
    # or non-web input unchanged merely defers the same parser exception to a
    # later provenance field (for example ``urlsplit(url).netloc``), where one
    # bad hosted-search result can fail an otherwise valid query batch.
    try:
        if split.scheme.lower() not in {"http", "https"} or not split.hostname:
            return ""
        if split.username or split.password:
            return ""
        # Accessing .port validates bracket and numeric-port syntax.
        _ = split.port
    except ValueError:
        return ""
    query = [
        (key, value)
        for key, value in parse_qsl(split.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
    ]
    path = split.path.rstrip("/") or "/"
    return urlunsplit((split.scheme.lower(), split.netloc.lower(), path, urlencode(query), ""))


class TavilyClient:
    def __init__(
        self,
        keys: Iterable[str],
        *,
        timeout: int = 90,
        max_workers: int = 6,
    ) -> None:
        self._keys = [key.strip() for key in keys if key.strip()]
        if not self._keys:
            raise ValueError("at least one Tavily key is required")
        self.timeout = timeout
        self.max_workers = max_workers
        self._next = 0
        self._lock = threading.Lock()
        self._disabled_keys: set[str] = set()
        self.calls = 0
        self.failures = 0
        self.status_counts: dict[int, int] = {}
        self.transport_failures = 0

    def _take_key(self) -> str | None:
        with self._lock:
            for _ in range(len(self._keys)):
                key = self._keys[self._next % len(self._keys)]
                self._next += 1
                if key not in self._disabled_keys:
                    return key
            return None

    def _disable_key(self, key: str) -> None:
        with self._lock:
            self._disabled_keys.add(key)

    def search(
        self,
        query: str,
        *,
        max_results: int,
        search_depth: str,
        include_raw_content: bool,
    ) -> dict[str, Any]:
        last_status: int | None = None
        attempts = max(2, len(self._keys))
        for _ in range(attempts):
            key = self._take_key()
            if key is None:
                break
            body = {
                "api_key": key,
                "query": query,
                "search_depth": search_depth,
                "max_results": max_results,
                "include_answer": True,
                "include_raw_content": include_raw_content,
            }
            try:
                response = requests.post(
                    "https://api.tavily.com/search",
                    json=body,
                    timeout=self.timeout,
                )
                with self._lock:
                    self.calls += 1
                last_status = response.status_code
                with self._lock:
                    self.status_counts[response.status_code] = (
                        self.status_counts.get(response.status_code, 0) + 1
                    )
                # Tavily uses 432 when the current API key has exhausted its
                # plan quota.  It is key-local like 401/403/429, so rotate to
                # the next authorized key instead of aborting the whole pool.
                if response.status_code in {401, 403, 432}:
                    self._disable_key(key)
                    continue
                if response.status_code == 429:
                    continue
                response.raise_for_status()
                payload = response.json()
                return sanitize_search_response(query, payload)
            except (requests.ConnectionError, requests.Timeout, json.JSONDecodeError):
                with self._lock:
                    self.transport_failures += 1
                continue
            except requests.HTTPError:
                break
        with self._lock:
            self.failures += 1
        with self._lock:
            status_summary = ",".join(
                f"{status}:{count}"
                for status, count in sorted(self.status_counts.items())
            )
        raise SearchRequestError(
            "search failed "
            f"(last_status={last_status}, status_counts={status_summary or 'none'}, "
            f"disabled_keys={len(self._disabled_keys)}/{len(self._keys)}, "
            f"transport_failures={self.transport_failures})"
        )

    def search_many(
        self,
        queries: Iterable[str],
        *,
        max_results: int,
        search_depth: str = "advanced",
        include_raw_content: bool = True,
    ) -> list[dict[str, Any]]:
        unique: list[str] = []
        seen: set[str] = set()
        for query in queries:
            normalized = " ".join(str(query).split()).strip()
            if normalized and normalized.casefold() not in seen:
                unique.append(normalized)
                seen.add(normalized.casefold())
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
                except SearchRequestError as exc:
                    outputs[query] = {"query": query, "answer": "", "results": [], "error": str(exc)}
        return [outputs[query] for query in unique]


def sanitize_search_response(query: str, payload: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    for raw in payload.get("results", []) or []:
        if not isinstance(raw, dict):
            continue
        url = canonicalize_url(str(raw.get("url", "")))
        if not url:
            continue
        results.append(
            {
                "title": str(raw.get("title", "")),
                "url": url,
                "content": str(raw.get("content", "")),
                "raw_content": str(raw.get("raw_content") or ""),
                "score": raw.get("score"),
            }
        )
    return {
        "query": query,
        "answer": str(payload.get("answer") or ""),
        "results": results,
    }
