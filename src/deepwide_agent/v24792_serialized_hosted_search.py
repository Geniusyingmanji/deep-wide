"""Deadline-aware cross-process serialization for unstable hosted search.

The local GPT-5.6 endpoint accepts concurrent ordinary model requests, but a
neutral capacity probe showed that concurrent hosted-web-search requests lose
their query-local search result contract.  This append-only transport keeps
the validated V2.46.30 search/parser/fetch stack and serializes only the
provider search POST.  It never reads benchmark metadata or evaluator state.
"""

from __future__ import annotations

import fcntl
import math
import os
import random
import stat
import threading
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from .clients import SearchRequestError
from .native_search import _web_search_actions
from .v24263_global_model_limiter import payload_sha256
from .v24468_total_wall_transport import (
    _retry_delay_from_fields,
    run_total_wall_post,
)
from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
)


POLICY_ID = "v24792_serialized_hosted_search_v1"
POOL_ID = "v24792_global_hosted_search_slots_v1"
ROLE = "v24792_serialized_hosted_search_receipt"
SLOT_BASENAME = "slot_01.lock"
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "policy_id",
        "pool_id",
        "slot_cap",
        "acquisitions",
        "slot_timeouts",
        "total_wait_seconds",
        "max_wait_seconds",
        "slot_acquisition_counts",
        "no_action_responses",
        "no_action_retries",
        "remaining_seconds_at_receipt",
        "deadline_exhausted",
        "label_blind",
        "contains_question_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_reward_read",
        "benchmark_launch_or_evaluator_authorized",
        "receipt_payload_sha256",
    }
)


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
        raise ValueError("V2.47.92 search slot directory is outside output root")
    return target


def prepare_slot_directory(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.mkdir(mode=0o700, parents=True, exist_ok=False)
    slot = path / SLOT_BASENAME
    descriptor = os.open(
        slot,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
        0o600,
    )
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write('{"artifact_version":1,"role":"v24792_hosted_search_slot","slot":1}\n')
        handle.flush()
        os.fsync(handle.fileno())


class SerializedThinHostedSearchClient(
    ThinSameResponseCitationTitleBackfillSearchClient
):
    """The validated thin search client with one global hosted-search slot."""

    def __init__(
        self,
        *args: Any,
        search_slot_directory: Path,
        output_root: Path,
        search_slot_cap: int = 1,
        slot_monotonic: Callable[[], float] = time.monotonic,
        slot_sleeper: Callable[[float], None] = time.sleep,
        slot_poll_seconds: float = 0.025,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        if (
            search_slot_cap != 1
            or isinstance(slot_poll_seconds, bool)
            or not isinstance(slot_poll_seconds, (int, float))
            or not math.isfinite(float(slot_poll_seconds))
            or not 0 < float(slot_poll_seconds) <= 1
        ):
            raise ValueError("V2.47.92 search slot configuration is invalid")
        self.search_slot_directory = _ordinary_directory(
            search_slot_directory, output_root
        )
        self.search_slot_cap = search_slot_cap
        self.slot_monotonic = slot_monotonic
        self.slot_sleeper = slot_sleeper
        self.slot_poll_seconds = float(slot_poll_seconds)
        self.search_slot_acquisitions = 0
        self.search_slot_timeouts = 0
        self.search_slot_total_wait_seconds = 0.0
        self.search_slot_max_wait_seconds = 0.0
        self.search_slot_acquisition_counts = [0]
        self.no_action_responses = 0
        self.no_action_retries = 0
        self._slot_counter_lock = threading.Lock()
        self._slot_path = self.search_slot_directory / SLOT_BASENAME
        if self._slot_path.is_symlink() or not self._slot_path.is_file():
            raise ValueError("V2.47.92 hosted-search slot file is absent")

    def _slot_timeout(self, waited: float) -> SearchRequestError:
        with self._slot_counter_lock:
            self.search_slot_timeouts += 1
            self.search_slot_total_wait_seconds += waited
            self.search_slot_max_wait_seconds = max(
                self.search_slot_max_wait_seconds, waited
            )
        return SearchRequestError(
            "V2.47.92 hosted-search slot deadline exhausted before provider effect"
        )

    def _acquire_search_slot(self) -> tuple[Any, float]:
        started = float(self.slot_monotonic())
        while True:
            descriptor = os.open(
                self._slot_path,
                os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
            )
            if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                os.close(descriptor)
                raise ValueError("V2.47.92 hosted-search slot is not regular")
            handle = os.fdopen(descriptor, "r+", encoding="utf-8")
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                handle.close()
            else:
                waited = max(0.0, float(self.slot_monotonic()) - started)
                if self.remaining_effect_seconds() < self.minimum_attempt_seconds:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                    handle.close()
                    raise self._slot_timeout(waited)
                with self._slot_counter_lock:
                    self.search_slot_acquisitions += 1
                    self.search_slot_total_wait_seconds += waited
                    self.search_slot_max_wait_seconds = max(
                        self.search_slot_max_wait_seconds, waited
                    )
                    self.search_slot_acquisition_counts[0] += 1
                return handle, waited
            remaining = self.remaining_effect_seconds()
            if remaining < self.minimum_attempt_seconds:
                waited = max(0.0, float(self.slot_monotonic()) - started)
                raise self._slot_timeout(waited)
            self.slot_sleeper(min(self.slot_poll_seconds, remaining))

    def _request(self, queries: list[str]) -> dict[str, Any]:
        body = self._request_body(queries)
        last_status: int | None = None
        deadline_failure = False
        for attempt in range(1, self.max_retries + 1):
            if self.remaining_effect_seconds() < self.minimum_attempt_seconds:
                deadline_failure = True
                break
            try:
                handle, _waited = self._acquire_search_slot()
            except SearchRequestError:
                deadline_failure = True
                break
            try:
                remaining = self.remaining_effect_seconds()
                if remaining < self.minimum_attempt_seconds:
                    deadline_failure = True
                    break
                self._increment("hosted_search_attempts")
                self._stage_callback("hosted_search_effect_started")
                try:
                    response = run_total_wall_post(
                        url=self.url,
                        body=body,
                        timeout_seconds=remaining,
                        static_socket_timeout_seconds=self.static_search_timeout_seconds,
                        popen=self._total_wall_popen,
                        helper=self._total_wall_helper,
                    )
                finally:
                    self._stage_callback("hosted_search_effect_finished")
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()

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
                self.status_counts[last_status] = (
                    self.status_counts.get(last_status, 0) + 1
                )
            if last_status in {408, 409, 429} or last_status >= 500:
                if attempt < self.max_retries and self._bounded_sleep(
                    _retry_delay_from_fields(
                        last_status, str(response["retry_after"]), attempt
                    )
                ):
                    continue
                deadline_failure = (
                    self.remaining_effect_seconds() < self.minimum_attempt_seconds
                )
                break
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
            usage = (
                payload.get("usage")
                if isinstance(payload.get("usage"), Mapping)
                else {}
            )
            self._increment("input_tokens", int(usage.get("input_tokens", 0) or 0))
            self._increment(
                "output_tokens", int(usage.get("output_tokens", 0) or 0)
            )
            self._increment(
                "total_tokens",
                int(usage.get("total_tokens", 0) or 0)
                or int(usage.get("input_tokens", 0) or 0)
                + int(usage.get("output_tokens", 0) or 0),
            )
            actions = _web_search_actions(payload)
            self._increment("tool_calls", len(actions))
            if actions:
                return payload
            with self._slot_counter_lock:
                self.no_action_responses += 1
            if attempt < self.max_retries and self._bounded_sleep(
                min(2**attempt + random.random(), 60.0)
            ):
                with self._slot_counter_lock:
                    self.no_action_retries += 1
                continue
            deadline_failure = (
                self.remaining_effect_seconds() < self.minimum_attempt_seconds
            )
            break
        if deadline_failure:
            self._mark_search_deadline_failure()
        raise SearchRequestError(
            "V2.47.92 serialized native web search failed within its task deadline "
            f"(last_status={last_status})"
        )

    def search_slot_receipt(self) -> dict[str, Any]:
        with self._slot_counter_lock:
            acquisitions = self.search_slot_acquisitions
            timeouts = self.search_slot_timeouts
            total_wait = self.search_slot_total_wait_seconds
            max_wait = self.search_slot_max_wait_seconds
            counts = list(self.search_slot_acquisition_counts)
            no_action = self.no_action_responses
            no_action_retries = self.no_action_retries
        remaining = max(0.0, self.absolute_deadline - float(self.monotonic()))
        value = {
            "artifact_version": 1,
            "role": ROLE,
            "policy_id": POLICY_ID,
            "pool_id": POOL_ID,
            "slot_cap": 1,
            "acquisitions": acquisitions,
            "slot_timeouts": timeouts,
            "total_wait_seconds": round(total_wait, 6),
            "max_wait_seconds": round(max_wait, 6),
            "slot_acquisition_counts": counts,
            "no_action_responses": no_action,
            "no_action_retries": no_action_retries,
            "remaining_seconds_at_receipt": round(remaining, 6),
            "deadline_exhausted": self.remaining_effect_seconds()
            < self.minimum_attempt_seconds,
            "label_blind": True,
            "contains_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
            "benchmark_launch_or_evaluator_authorized": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        return validate_receipt(value)


def validate_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = dict(value)
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = copied.get("slot_acquisition_counts")
    integers = (
        "acquisitions",
        "slot_timeouts",
        "no_action_responses",
        "no_action_retries",
    )
    numerics = (
        "total_wait_seconds",
        "max_wait_seconds",
        "remaining_seconds_at_receipt",
    )
    if (
        set(copied) != RECEIPT_KEYS
        or copied.get("role") != ROLE
        or copied.get("policy_id") != POLICY_ID
        or copied.get("pool_id") != POOL_ID
        or copied.get("slot_cap") != 1
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), int)
            or copied[name] < 0
            for name in integers
        )
        or any(
            isinstance(copied.get(name), bool)
            or not isinstance(copied.get(name), (int, float))
            or not math.isfinite(float(copied[name]))
            or float(copied[name]) < 0
            for name in numerics
        )
        or not isinstance(counts, list)
        or len(counts) != 1
        or counts[0] != copied.get("acquisitions")
        or copied.get("no_action_retries", 0)
        > copied.get("no_action_responses", 0)
        or copied.get("label_blind") is not True
        or copied.get(
            "contains_question_query_url_page_prediction_answer_opaque_id_or_credential"
        )
        is not False
        or copied.get(
            "mapping_gold_category_question_type_split_evaluator_score_reward_read"
        )
        is not False
        or copied.get("benchmark_launch_or_evaluator_authorized") is not False
        or seal != payload_sha256(unsigned)
    ):
        raise ValueError("V2.47.92 serialized hosted-search receipt drifted")
    return copied


def validate_search_class() -> None:
    cls = SerializedThinHostedSearchClient
    request_owner = next(base for base in cls.__mro__ if "_request" in base.__dict__)
    if (
        request_owner is not cls
        or not issubclass(
            cls, ThinSameResponseCitationTitleBackfillSearchClient
        )
    ):
        raise RuntimeError("V2.47.92 serialized hosted-search MRO drifted")


__all__ = [
    "POLICY_ID",
    "POOL_ID",
    "ROLE",
    "SerializedThinHostedSearchClient",
    "prepare_slot_directory",
    "validate_receipt",
    "validate_search_class",
]
