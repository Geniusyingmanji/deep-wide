"""Hard total-wall model and hosted-search transports for V2.44.68.

``requests`` timeouts bound connect/read inactivity, not total response wall
time.  A peer that sends one byte before every read timeout can therefore keep
the V2.43.12/V2.43.16 calls alive beyond their absolute deadline.  This module
preserves their counters and retry policy while moving each HTTP POST into a
short-lived, loopback-only helper process.  The caller enforces the remaining
effect window with ``communicate(timeout=...)`` and kills the process group on
expiry.

Prompt, response, query, and URL data travel only through anonymous pipes and
are never returned by receipts or exceptions.  This module has no benchmark
selection, label, mapping, gold, evaluator, reward, or score capability.
"""

from __future__ import annotations

import json
import math
import os
import random
import signal
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Callable

from .clients import ModelResult, SearchRequestError, _retry_delay, extract_response_text
from .native_search import _web_search_actions
from .v24312_deadline_reliability import (
    DeadlineAwareResponsesClient,
)
from .v24316_deadline_search import DeadlineAwareNativeSearchClient


POLICY_ID = "v24468_hard_total_wall_loopback_transport_v1"
ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/v24468_total_wall_http_helper.py"
HELPER_RESULT_KEYS = frozenset(
    {"kind", "status_code", "retry_after", "payload", "payload_is_object"}
)
HELPER_KINDS = frozenset(
    {
        "response",
        "transport_error",
        "response_too_large",
        "invalid_input_or_payload",
        "hard_total_wall_timeout",
        "helper_nonzero_or_invalid",
    }
)


def _ordinary_helper(path: Path = HELPER) -> Path:
    expected = (ROOT / "scripts/v24468_total_wall_http_helper.py").resolve()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not path.is_file()
        or resolved != expected
        or not resolved.is_relative_to(ROOT)
    ):
        raise ValueError("V2.44.68 helper identity drifted")
    return resolved


def _environment() -> dict[str, str]:
    value = {
        "HOME": os.environ.get("HOME", str(Path.home())),
        "USER": os.environ.get("USER", "azureuser"),
        "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONSAFEPATH": "1",
    }
    value["DEEPWIDE_EXPECTED_PARENT_PID"] = str(os.getpid())
    return value


def _terminate_process(process: Any) -> None:
    try:
        process.terminate()
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=0.1)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        process.kill()
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=0.2)
    except subprocess.TimeoutExpired:
        return


def _close_process_pipes(process: Any) -> None:
    for name in ("stdin", "stdout", "stderr"):
        stream = getattr(process, name, None)
        if stream is not None and not stream.closed:
            try:
                stream.close()
            except OSError:
                pass


def _fallback(kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "status_code": None,
        "retry_after": "",
        "payload": None,
        "payload_is_object": False,
    }


def _validate_helper_result(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("V2.44.68 helper result is not an object")
    copied = dict(value)
    status = copied.get("status_code")
    if (
        set(copied) != HELPER_RESULT_KEYS
        or copied.get("kind") not in HELPER_KINDS
        or status is not None
        and (
            isinstance(status, bool)
            or not isinstance(status, int)
            or not 100 <= status <= 599
        )
        or not isinstance(copied.get("retry_after"), str)
        or len(copied["retry_after"]) > 128
        or not isinstance(copied.get("payload_is_object"), bool)
        or copied["payload_is_object"] is not isinstance(copied.get("payload"), Mapping)
        or copied.get("kind") == "response"
        and status is None
    ):
        raise ValueError("V2.44.68 helper result drifted")
    return copied


def run_total_wall_post(
    *,
    url: str,
    body: Mapping[str, Any],
    timeout_seconds: float,
    static_socket_timeout_seconds: float,
    popen: Any = subprocess.Popen,
    helper: Path = HELPER,
) -> dict[str, Any]:
    numbers = (timeout_seconds, static_socket_timeout_seconds)
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) <= 0
        for value in numbers
    ):
        raise ValueError("V2.44.68 invalid total-wall request timeout")
    helper_path = _ordinary_helper(helper)
    total_deadline = time.monotonic() + float(timeout_seconds)
    request = json.dumps(
        {
            "url": str(url),
            "body": dict(body),
            "socket_timeout_seconds": min(
                float(timeout_seconds), float(static_socket_timeout_seconds)
            ),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    process = popen(
        [sys.executable, "-I", "-B", str(helper_path)],
        cwd=ROOT,
        env=_environment(),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        # Inherit the worker group so a worker-level hard cutoff also kills an
        # in-flight helper.  Per-request expiry terminates this process only.
        start_new_session=False,
        text=True,
    )
    remaining_after_launch = max(0.0, total_deadline - time.monotonic())
    if remaining_after_launch <= 0:
        _terminate_process(process)
        _close_process_pipes(process)
        return _fallback("hard_total_wall_timeout")
    try:
        stdout, _ = process.communicate(request, timeout=remaining_after_launch)
    except subprocess.TimeoutExpired:
        _terminate_process(process)
        _close_process_pipes(process)
        return _fallback("hard_total_wall_timeout")
    finally:
        if process.returncode is not None:
            _close_process_pipes(process)
    if process.returncode != 0 or len(stdout.encode("utf-8")) > 40 * 1024 * 1024:
        return _fallback("helper_nonzero_or_invalid")
    try:
        return _validate_helper_result(json.loads(stdout))
    except (json.JSONDecodeError, TypeError, ValueError):
        return _fallback("helper_nonzero_or_invalid")


def _retry_delay_from_fields(status: int, retry_after: str, attempt: int) -> float:
    class Response:
        status_code = status
        headers = {"Retry-After": retry_after}

    return float(_retry_delay(Response(), attempt))


class HardTotalWallResponsesClient(DeadlineAwareResponsesClient):
    """Deadline-aware model client with an OS-enforced per-attempt wall."""

    def __init__(
        self,
        *args: Any,
        popen: Any = subprocess.Popen,
        helper: Path = HELPER,
        stage_callback: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._total_wall_popen = popen
        self._total_wall_helper = _ordinary_helper(helper)
        self._stage_callback = stage_callback or (lambda _event: None)
        self.hard_total_wall_timeouts = 0

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
        request_body_bytes = len(
            json.dumps(body, ensure_ascii=True, separators=(",", ":")).encode(
                "utf-8"
            )
        )
        last_status: int | None = None
        last_error_type = "request_exhausted"
        attempts_used = 0
        for attempt in range(1, self.max_retries + 1):
            remaining = self.remaining_effect_seconds()
            if remaining < self.minimum_attempt_seconds:
                last_error_type = "task_deadline_exhausted"
                break
            attempts_used = attempt
            with self._lock:
                self.attempts += 1
            self._stage_callback("model_effect_started")
            response = run_total_wall_post(
                url=self.url,
                body=body,
                timeout_seconds=remaining,
                static_socket_timeout_seconds=float(self.timeout),
                popen=self._total_wall_popen,
                helper=self._total_wall_helper,
            )
            self._stage_callback("model_effect_finished")
            kind = response["kind"]
            if kind == "hard_total_wall_timeout":
                with self._lock:
                    self.hard_total_wall_timeouts += 1
                last_error_type = "task_deadline_exhausted"
                break
            if kind != "response":
                last_error_type = "transport_error"
                if attempt >= self.max_retries or not self._bounded_sleep(
                    min(2**attempt + random.random(), 60)
                ):
                    if self.remaining_effect_seconds() < self.minimum_attempt_seconds:
                        last_error_type = "task_deadline_exhausted"
                    break
                continue
            last_status = int(response["status_code"])
            if last_status in {408, 409, 429} or last_status >= 500:
                last_error_type = "retryable_http_status"
                if attempt < self.max_retries and not self._bounded_sleep(
                    _retry_delay_from_fields(
                        last_status, str(response["retry_after"]), attempt
                    )
                ):
                    last_error_type = "task_deadline_exhausted"
                    break
                continue
            if last_status >= 400:
                last_error_type = "terminal_http_status"
                break
            payload = response.get("payload")
            if not isinstance(payload, Mapping):
                last_error_type = "invalid_response_json"
                if attempt >= self.max_retries or not self._bounded_sleep(
                    min(2**attempt + random.random(), 60)
                ):
                    if self.remaining_effect_seconds() < self.minimum_attempt_seconds:
                        last_error_type = "task_deadline_exhausted"
                    break
                continue
            payload = dict(payload)
            text = extract_response_text(payload)
            if not text:
                last_error_type = "empty_output"
                if attempt < self.max_retries and not self._bounded_sleep(
                    min(2**attempt, 30)
                ):
                    last_error_type = "task_deadline_exhausted"
                    break
                continue
            usage = payload.get("usage", {}) or {}
            input_tokens = int(usage.get("input_tokens", 0) or 0)
            output_tokens = int(usage.get("output_tokens", 0) or 0)
            total_tokens = int(usage.get("total_tokens", 0) or 0)
            incomplete_details = payload.get("incomplete_details") or {}
            incomplete_reason = str(
                incomplete_details.get("reason", "")
                if isinstance(incomplete_details, Mapping)
                else ""
            ).casefold()
            output_truncated = bool(
                str(payload.get("status", "")).casefold() == "incomplete"
                or incomplete_reason in {"max_output_tokens", "max_tokens", "length"}
                or max_output_tokens > 0
                and output_tokens >= max_output_tokens
            )
            with self._lock:
                self.calls += 1
                self.input_tokens += input_tokens
                self.output_tokens += output_tokens
                self.total_tokens += total_tokens or input_tokens + output_tokens
            return ModelResult(
                text=text,
                usage=dict(usage),
                response_id=payload.get("id"),
                attempts=attempt,
                request_index=request_index,
                input_chars=input_chars,
                input_utf8_bytes=input_utf8_bytes,
                request_body_bytes=request_body_bytes,
                max_output_tokens=max_output_tokens,
                output_truncated=output_truncated,
            )
        self._raise_failure(
            attempts=attempts_used,
            request_index=request_index,
            error_type=last_error_type,
            last_status=last_status,
            input_chars=input_chars,
            input_utf8_bytes=input_utf8_bytes,
            request_body_bytes=request_body_bytes,
            max_output_tokens=max_output_tokens,
        )


class HardTotalWallNativeSearchClient(DeadlineAwareNativeSearchClient):
    """Deadline-aware hosted search with an OS-enforced per-attempt wall."""

    def __init__(
        self,
        *args: Any,
        popen: Any = subprocess.Popen,
        helper: Path = HELPER,
        stage_callback: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._total_wall_popen = popen
        self._total_wall_helper = _ordinary_helper(helper)
        self._stage_callback = stage_callback or (lambda _event: None)
        self.hard_total_wall_timeouts = 0

    def _request(self, queries: list[str]) -> dict[str, Any]:
        body = self._request_body(queries)
        last_status: int | None = None
        deadline_failure = False
        for attempt in range(1, self.max_retries + 1):
            remaining = self.remaining_effect_seconds()
            if remaining < self.minimum_attempt_seconds:
                deadline_failure = True
                break
            self._increment("hosted_search_attempts")
            self._stage_callback("hosted_search_effect_started")
            response = run_total_wall_post(
                url=self.url,
                body=body,
                timeout_seconds=remaining,
                static_socket_timeout_seconds=self.static_search_timeout_seconds,
                popen=self._total_wall_popen,
                helper=self._total_wall_helper,
            )
            self._stage_callback("hosted_search_effect_finished")
            kind = response["kind"]
            if kind == "hard_total_wall_timeout":
                self._increment("hard_total_wall_timeouts")
                deadline_failure = True
                break
            if kind != "response":
                self._increment("transport_failures")
                if attempt < self.max_retries and self._bounded_sleep(
                    min(2**attempt + random.random(), 60.0)
                ):
                    continue
                deadline_failure = (
                    self.remaining_effect_seconds() < self.minimum_attempt_seconds
                )
                break
            self._increment("calls")
            last_status = int(response["status_code"])
            with self._lock:
                self.status_counts[last_status] = self.status_counts.get(last_status, 0) + 1
            if last_status in {408, 409, 429} or last_status >= 500:
                if attempt < self.max_retries:
                    if not self._bounded_sleep(
                        _retry_delay_from_fields(
                            last_status, str(response["retry_after"]), attempt
                        )
                    ):
                        deadline_failure = True
                        break
                continue
            if last_status >= 400:
                break
            payload = response.get("payload")
            if not isinstance(payload, Mapping):
                self._increment("transport_failures")
                if attempt < self.max_retries and self._bounded_sleep(
                    min(2**attempt + random.random(), 60.0)
                ):
                    continue
                deadline_failure = (
                    self.remaining_effect_seconds() < self.minimum_attempt_seconds
                )
                break
            payload = dict(payload)
            usage = payload.get("usage") if isinstance(payload.get("usage"), Mapping) else {}
            self._increment("input_tokens", int(usage.get("input_tokens", 0) or 0))
            self._increment("output_tokens", int(usage.get("output_tokens", 0) or 0))
            self._increment(
                "total_tokens",
                int(usage.get("total_tokens", 0) or 0)
                or int(usage.get("input_tokens", 0) or 0)
                + int(usage.get("output_tokens", 0) or 0),
            )
            actions = _web_search_actions(payload)
            self._increment("tool_calls", len(actions))
            if not actions:
                raise SearchRequestError(
                    "V2.44.68 hosted response contained no web-search action"
                )
            return payload
        if deadline_failure:
            self._mark_search_deadline_failure()
        raise SearchRequestError(
            "V2.44.68 native web search failed within the hard total-wall deadline"
        )

    def _fetch_url(self, url: str) -> dict[str, Any]:
        self._stage_callback("public_fetch_effect_started")
        try:
            return super()._fetch_url(url)
        finally:
            self._stage_callback("public_fetch_effect_finished")


__all__ = [
    "HELPER",
    "HardTotalWallNativeSearchClient",
    "HardTotalWallResponsesClient",
    "POLICY_ID",
    "run_total_wall_post",
]
