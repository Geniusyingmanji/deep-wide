"""Deadline-aware model transport for future DeepWide task runners.

V2.43.11 exposed a lifetime mismatch: the task runtime admitted a model
effect using its wall budget, but the shared model-slot limiter could then
wait forever and the provider client could still use its full static timeout.
The parent consequently killed the child before it could write a total result
or its terminal receipts.

This append-only module gives every model effect the same absolute child
deadline.  It bounds both slot acquisition and every provider attempt, keeps
time for result/receipt cleanup, and raises a content-free ``ModelRequestError``
inside the child when no safe request window remains.  Search and fetch calls
do not pass through this wrapper.  It grants no benchmark launch authority.
"""

from __future__ import annotations

import fcntl
import json
import math
import os
import random
import stat
import threading
import time
from collections.abc import Callable, Iterable, Mapping
from pathlib import Path
from typing import Any

import requests

from .clients import (
    ModelRequestError,
    ModelResult,
    ResponsesClient,
    _retry_delay,
    extract_response_text,
)
from .v24263_global_model_limiter import POOL_ID, payload_sha256
from .v24257_score_first_runtime import (
    ScoreFirstLimits,
    _counter_delta,
    _counter_snapshot,
    validate_visible_task,
)
from .v24267_total_fallback import build_total_fallback_result
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24294_staged_reserve import StagedReservePolicy
from .v24308_child_exit_observability import coarse_exception_type
from .v24310_paired_dev_runtime import (
    ARMS,
    MODEL_COUNTERS,
    RECEIPT_FIELD as RECOVERY_RECEIPT_FIELD,
    SEARCH_COUNTERS,
    parent_exit_receipt,
    run_v24310_task,
    validate_v24310_result,
)


ROLE = "v24312_deadline_aware_model_receipt"
TOTALITY_ROLE = "v24312_deadline_aware_task_totality"
DEFAULT_CLEANUP_RESERVE_SECONDS = 5.0
DEFAULT_MINIMUM_ATTEMPT_SECONDS = 0.05
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "pool_id",
        "slot_cap",
        "acquisitions",
        "slot_timeouts",
        "provider_deadline_failures",
        "total_wait_seconds",
        "max_wait_seconds",
        "slot_acquisition_counts",
        "cleanup_reserve_seconds",
        "minimum_attempt_seconds",
        "remaining_seconds_at_receipt",
        "deadline_exhausted",
        "label_blind",
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
)


class DeadlineAwareResponsesClient(ResponsesClient):
    """Responses client whose attempts and backoff share one absolute deadline."""

    def __init__(
        self,
        *args: Any,
        absolute_deadline: float,
        cleanup_reserve_seconds: float = DEFAULT_CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds: float = DEFAULT_MINIMUM_ATTEMPT_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if (
            isinstance(absolute_deadline, bool)
            or not isinstance(absolute_deadline, (int, float))
            or not math.isfinite(float(absolute_deadline))
            or isinstance(cleanup_reserve_seconds, bool)
            or not isinstance(cleanup_reserve_seconds, (int, float))
            or not math.isfinite(float(cleanup_reserve_seconds))
            or float(cleanup_reserve_seconds) <= 0
            or isinstance(minimum_attempt_seconds, bool)
            or not isinstance(minimum_attempt_seconds, (int, float))
            or not math.isfinite(float(minimum_attempt_seconds))
            or float(minimum_attempt_seconds) <= 0
        ):
            raise ValueError("invalid V2.43.12 provider deadline configuration")
        self.absolute_deadline = float(absolute_deadline)
        self.cleanup_reserve_seconds = float(cleanup_reserve_seconds)
        self.minimum_attempt_seconds = float(minimum_attempt_seconds)
        self.monotonic = monotonic
        self.sleeper = sleeper
        self.deadline_failures = 0

    def remaining_effect_seconds(self) -> float:
        return max(
            0.0,
            self.absolute_deadline
            - float(self.monotonic())
            - self.cleanup_reserve_seconds,
        )

    def _failure_trace(
        self,
        *,
        attempts: int,
        request_index: int,
        error_type: str,
        last_status: int | None,
        input_chars: int,
        input_utf8_bytes: int,
        request_body_bytes: int,
        max_output_tokens: int,
    ) -> dict[str, Any]:
        return {
            "purpose": "request_failure",
            "response_id": None,
            "usage": {},
            "attempts": attempts,
            "request_index": request_index,
            "success": False,
            "error_type": error_type,
            "last_status": last_status,
            "input_chars": input_chars,
            "input_utf8_bytes": input_utf8_bytes,
            "request_body_bytes": request_body_bytes,
            "max_output_tokens": max_output_tokens,
        }

    def _raise_failure(
        self,
        *,
        attempts: int,
        request_index: int,
        error_type: str,
        last_status: int | None,
        input_chars: int,
        input_utf8_bytes: int,
        request_body_bytes: int,
        max_output_tokens: int,
    ) -> None:
        with self._lock:
            self.failures += 1
            if error_type == "task_deadline_exhausted":
                self.deadline_failures += 1
        trace = self._failure_trace(
            attempts=attempts,
            request_index=request_index,
            error_type=error_type,
            last_status=last_status,
            input_chars=input_chars,
            input_utf8_bytes=input_utf8_bytes,
            request_body_bytes=request_body_bytes,
            max_output_tokens=max_output_tokens,
        )
        raise ModelRequestError(
            "V2.43.12 model request failed within the shared task deadline",
            model_traces=[trace],
        )

    def _bounded_sleep(self, requested: float) -> bool:
        remaining = self.remaining_effect_seconds()
        if remaining < self.minimum_attempt_seconds:
            return False
        delay = min(max(0.0, float(requested)), remaining)
        if delay > 0:
            self.sleeper(delay)
        return self.remaining_effect_seconds() >= self.minimum_attempt_seconds

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
            request_timeout = min(float(self.timeout), remaining)
            try:
                response = self._session().post(
                    self.url,
                    headers={"Content-Type": "application/json"},
                    json=body,
                    timeout=request_timeout,
                )
                last_status = response.status_code
                if response.status_code in {408, 409, 429} or response.status_code >= 500:
                    last_error_type = "retryable_http_status"
                    if attempt < self.max_retries and not self._bounded_sleep(
                        _retry_delay(response, attempt)
                    ):
                        last_error_type = "task_deadline_exhausted"
                        break
                    continue
                if response.status_code >= 400:
                    last_error_type = "terminal_http_status"
                    break
                payload = response.json()
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
                    if isinstance(incomplete_details, dict)
                    else ""
                ).casefold()
                output_truncated = bool(
                    str(payload.get("status", "")).casefold() == "incomplete"
                    or incomplete_reason in {"max_output_tokens", "max_tokens", "length"}
                    or (max_output_tokens > 0 and output_tokens >= max_output_tokens)
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
                last_error_type = (
                    "task_deadline_exhausted"
                    if self.remaining_effect_seconds() < self.minimum_attempt_seconds
                    else "transport_error"
                )
                if attempt >= self.max_retries or not self._bounded_sleep(
                    min(2**attempt + random.random(), 60)
                ):
                    if self.remaining_effect_seconds() < self.minimum_attempt_seconds:
                        last_error_type = "task_deadline_exhausted"
                    break
            except json.JSONDecodeError:
                last_error_type = "invalid_response_json"
                if attempt >= self.max_retries or not self._bounded_sleep(
                    min(2**attempt + random.random(), 60)
                ):
                    if self.remaining_effect_seconds() < self.minimum_attempt_seconds:
                        last_error_type = "task_deadline_exhausted"
                    break
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


def _ordinary_output_directory(path: Path, output_root: Path) -> Path:
    root = output_root.resolve()
    target = path.resolve(strict=False)
    if path.is_symlink() or not path.is_dir() or not target.is_relative_to(root):
        raise ValueError("V2.43.12 model slot directory is outside outputs")
    return target


class DeadlineAwareGlobalModelSlotLimiter:
    """Cross-process model limiter whose queue shares the provider deadline."""

    def __init__(
        self,
        inner: Any,
        *,
        slot_directory: Path,
        output_root: Path,
        absolute_deadline: float,
        slot_cap: int = 2,
        pool_id: str = POOL_ID,
        cleanup_reserve_seconds: float = DEFAULT_CLEANUP_RESERVE_SECONDS,
        minimum_attempt_seconds: float = DEFAULT_MINIMUM_ATTEMPT_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        poll_seconds: float = 0.025,
    ) -> None:
        numbers = (
            absolute_deadline,
            cleanup_reserve_seconds,
            minimum_attempt_seconds,
            poll_seconds,
        )
        if (
            isinstance(slot_cap, bool)
            or not isinstance(slot_cap, int)
            or not 1 <= slot_cap <= 32
            or pool_id != POOL_ID
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or float(value) <= 0
                for value in numbers
            )
            or float(poll_seconds) > 1.0
        ):
            raise ValueError("invalid V2.43.12 model slot configuration")
        self.inner = inner
        self.slot_directory = _ordinary_output_directory(slot_directory, output_root)
        self.absolute_deadline = float(absolute_deadline)
        self.slot_cap = slot_cap
        self.pool_id = pool_id
        self.cleanup_reserve_seconds = float(cleanup_reserve_seconds)
        self.minimum_attempt_seconds = float(minimum_attempt_seconds)
        self.monotonic = monotonic
        self.sleeper = sleeper
        self.poll_seconds = float(poll_seconds)
        self.acquisitions = 0
        self.slot_timeouts = 0
        self.total_wait_seconds = 0.0
        self.max_wait_seconds = 0.0
        self.slot_acquisition_counts = [0] * slot_cap
        self._lock = threading.Lock()
        self._slot_paths = tuple(
            self.slot_directory / f"slot_{index:02d}.lock"
            for index in range(1, slot_cap + 1)
        )
        for path in self._slot_paths:
            if path.is_symlink() or not path.is_file():
                raise ValueError("V2.43.12 model slot file is absent")

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def remaining_effect_seconds(self) -> float:
        return max(
            0.0,
            self.absolute_deadline
            - float(self.monotonic())
            - self.cleanup_reserve_seconds,
        )

    def _timeout_error(self, waited: float) -> ModelRequestError:
        with self._lock:
            self.slot_timeouts += 1
            self.total_wait_seconds += waited
            self.max_wait_seconds = max(self.max_wait_seconds, waited)
        return ModelRequestError(
            "V2.43.12 model slot deadline exhausted before provider effect",
            model_traces=[
                {
                    "purpose": "request_failure",
                    "response_id": None,
                    "usage": {},
                    "attempts": 0,
                    "request_index": None,
                    "success": False,
                    "error_type": "model_slot_deadline_exhausted",
                    "last_status": None,
                    "input_chars": 0,
                    "input_utf8_bytes": 0,
                    "request_body_bytes": 0,
                    "max_output_tokens": 0,
                }
            ],
        )

    def _acquire(self) -> tuple[Any, int, float]:
        started = float(self.monotonic())
        with self._lock:
            offset = (os.getpid() + self.acquisitions) % self.slot_cap
        while True:
            for delta in range(self.slot_cap):
                index = (offset + delta) % self.slot_cap
                path = self._slot_paths[index]
                descriptor = os.open(path, os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    os.close(descriptor)
                    raise ValueError("V2.43.12 model slot is not a regular file")
                handle = os.fdopen(descriptor, "r+", encoding="utf-8")
                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    handle.close()
                    continue
                waited = max(0.0, float(self.monotonic()) - started)
                if self.remaining_effect_seconds() < self.minimum_attempt_seconds:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    handle.close()
                    raise self._timeout_error(waited)
                with self._lock:
                    self.acquisitions += 1
                    self.total_wait_seconds += waited
                    self.max_wait_seconds = max(self.max_wait_seconds, waited)
                    self.slot_acquisition_counts[index] += 1
                return handle, index, waited
            remaining = self.remaining_effect_seconds()
            if remaining < self.minimum_attempt_seconds:
                waited = max(0.0, float(self.monotonic()) - started)
                raise self._timeout_error(waited)
            self.sleeper(min(self.poll_seconds, remaining))

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_output_tokens: int,
        json_mode: bool = False,
    ) -> Any:
        handle, _, _ = self._acquire()
        try:
            return self.inner.complete(
                system,
                user,
                max_output_tokens=max_output_tokens,
                json_mode=json_mode,
            )
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            handle.close()

    def receipt(self) -> dict[str, Any]:
        with self._lock:
            acquisitions = self.acquisitions
            slot_timeouts = self.slot_timeouts
            total_wait = self.total_wait_seconds
            max_wait = self.max_wait_seconds
            counts = list(self.slot_acquisition_counts)
        remaining = max(0.0, self.absolute_deadline - float(self.monotonic()))
        value = {
            "artifact_version": 1,
            "role": ROLE,
            "pool_id": self.pool_id,
            "slot_cap": self.slot_cap,
            "acquisitions": acquisitions,
            "slot_timeouts": slot_timeouts,
            "provider_deadline_failures": int(
                getattr(self.inner, "deadline_failures", 0) or 0
            ),
            "total_wait_seconds": round(total_wait, 6),
            "max_wait_seconds": round(max_wait, 6),
            "slot_acquisition_counts": counts,
            "cleanup_reserve_seconds": self.cleanup_reserve_seconds,
            "minimum_attempt_seconds": self.minimum_attempt_seconds,
            "remaining_seconds_at_receipt": round(remaining, 6),
            "deadline_exhausted": self.remaining_effect_seconds()
            < self.minimum_attempt_seconds,
            "label_blind": True,
            "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        validate_receipt(value, expected_cap=self.slot_cap)
        return value


def validate_receipt(
    value: Mapping[str, Any],
    *,
    expected_cap: int = 2,
    expected_acquisitions: int | None = None,
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = value.get("slot_acquisition_counts")
    integer_fields = (
        "acquisitions",
        "slot_timeouts",
        "provider_deadline_failures",
    )
    numeric_fields = (
        "total_wait_seconds",
        "max_wait_seconds",
        "cleanup_reserve_seconds",
        "minimum_attempt_seconds",
        "remaining_seconds_at_receipt",
    )
    if (
        set(value) != RECEIPT_KEYS
        or value.get("artifact_version") != 1
        or value.get("role") != ROLE
        or value.get("pool_id") != POOL_ID
        or value.get("slot_cap") != expected_cap
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), int)
            or int(value[name]) < 0
            for name in integer_fields
        )
        or not isinstance(counts, list)
        or len(counts) != expected_cap
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for count in counts
        )
        or sum(counts) != value.get("acquisitions")
        or any(
            isinstance(value.get(name), bool)
            or not isinstance(value.get(name), (int, float))
            or not math.isfinite(float(value[name]))
            or float(value[name]) < 0
            for name in numeric_fields
        )
        or float(value["cleanup_reserve_seconds"]) <= 0
        or float(value["minimum_attempt_seconds"]) <= 0
        or float(value["max_wait_seconds"])
        > float(value["total_wait_seconds"]) + 1e-6
        or not isinstance(value.get("deadline_exhausted"), bool)
        or value.get("label_blind") is not True
        or value.get(
            "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or value.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
        or (
            expected_acquisitions is not None
            and value.get("acquisitions") != expected_acquisitions
        )
    ):
        raise ValueError("V2.43.12 deadline-aware model receipt drifted")
    return dict(value)


def _snapshot(client: Any, names: tuple[str, ...]) -> dict[str, int]:
    try:
        return _counter_snapshot(client, names)
    except BaseException:
        return {name: 0 for name in names}


def run_v24312_total_task(
    task: Mapping[str, Any],
    *,
    arm: str,
    model: Any,
    search: Any,
    limits: ScoreFirstLimits,
    two_wave_policy: TwoWavePolicy,
    reserve_policy: StagedReservePolicy | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    """Keep post-return projection/validation failures inside task totality.

    V2.43.10 already totalizes exceptions raised by its parent runtime.  The
    V2.43.11 baseline failure occurred later, while reconciling or validating
    the returned value.  This outer boundary therefore snapshots all effects,
    preserves the last safe progress, and converts any remaining exception to
    the same fixed-denominator fallback without reading its message.
    """

    visible = validate_visible_task(task)
    if arm not in ARMS or limits.model_calls != 3:
        raise ValueError("V2.43.12 arm or model-call cap drifted")
    limits.validate()
    two_wave_policy.validate()
    if arm == "baseline" and reserve_policy is not None:
        raise ValueError("V2.43.12 baseline must not receive reserve policy")
    if arm == "candidate" and reserve_policy is None:
        raise ValueError("V2.43.12 candidate reserve policy is absent")
    if reserve_policy is not None:
        reserve_policy.validate()
    started = float(monotonic())
    model_start = _snapshot(model, MODEL_COUNTERS)
    search_start = _snapshot(search, SEARCH_COUNTERS)
    last_progress: dict[str, Any] = {}

    def capture(value: Mapping[str, Any]) -> None:
        nonlocal last_progress
        last_progress = dict(value)
        if progress is not None:
            progress(last_progress)

    try:
        result = run_v24310_task(
            visible,
            arm=arm,
            model=model,
            search=search,
            limits=limits,
            two_wave_policy=two_wave_policy,
            reserve_policy=reserve_policy,
            monotonic=monotonic,
            progress=capture,
        )
        validate_v24310_result(result, arm)
        return result
    except BaseException as error:
        current = dict(last_progress)
        model_delta = _counter_delta(_snapshot(model, MODEL_COUNTERS), model_start)
        search_delta = _counter_delta(_snapshot(search, SEARCH_COUNTERS), search_start)
        current["model_cost"] = model_delta
        current["search_cost"] = search_delta
        request_count = min(limits.model_calls, int(model_delta["requests"]))
        attempt_count = max(request_count, int(model_delta["attempts"]))
        current["admitted_model_calls"] = request_count
        value = build_total_fallback_result(
            visible,
            limits=limits,
            completion_kind="worker_failure_fallback",
            failure_stage="v24312_outer_totality",
            failure_type=coarse_exception_type(error),
            elapsed_seconds=max(0.0, float(monotonic()) - started),
            last_progress=current,
        )
        value["budget"]["events"] = [
            {
                "stage": "v24312_unattributed_model_effect",
                "effect": "model",
                "admitted": True,
            }
            for _ in range(request_count)
        ]
        value[RECOVERY_RECEIPT_FIELD] = parent_exit_receipt(
            arm,
            provider_requests_lower_bound=request_count,
            provider_attempts_lower_bound=attempt_count,
            admitted_model_effects_upper_bound=request_count,
            effect_count_complete=True,
            provider_attempt_count_complete=True,
        )
        validate_v24310_result(value, arm)
        return value


__all__ = [
    "DEFAULT_CLEANUP_RESERVE_SECONDS",
    "DEFAULT_MINIMUM_ATTEMPT_SECONDS",
    "DeadlineAwareGlobalModelSlotLimiter",
    "DeadlineAwareResponsesClient",
    "ROLE",
    "TOTALITY_ROLE",
    "run_v24312_total_task",
    "validate_receipt",
]
