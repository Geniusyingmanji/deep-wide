"""Cross-process GPT request limiter with content-free accounting.

Each logical ``complete`` call holds exactly one advisory file lock for the
entire provider request, including provider-internal retries.  Search and page
fetches never pass through this wrapper.  Kernel lock release on process exit
keeps a hard-deadline child from leaking capacity.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import stat
import time
from pathlib import Path
from typing import Any, Callable


ROLE = "v24263_global_model_slot_receipt"
POOL_ID = "v24263_score_first_global_model_slots_v1"
DEFAULT_CAP = 2
RECEIPT_KEYS = frozenset(
    {
        "artifact_version",
        "role",
        "pool_id",
        "slot_cap",
        "acquisitions",
        "total_wait_seconds",
        "max_wait_seconds",
        "slot_acquisition_counts",
        "label_blind",
        "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential",
        "mapping_gold_category_question_type_split_evaluator_score_read",
        "receipt_payload_sha256",
    }
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


def _ordinary_output_directory(path: Path, output_root: Path) -> Path:
    root = output_root.resolve()
    target = path.resolve(strict=False)
    if (
        path.is_symlink()
        or not path.is_dir()
        or not target.is_relative_to(root)
    ):
        raise ValueError("V2.42.63 model slot directory is outside outputs")
    return target


class GlobalModelSlotLimiter:
    """Transparent model proxy capped by a cross-process slot pool."""

    def __init__(
        self,
        inner: Any,
        *,
        slot_directory: Path,
        output_root: Path,
        slot_cap: int = DEFAULT_CAP,
        pool_id: str = POOL_ID,
        monotonic: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
        poll_seconds: float = 0.025,
    ) -> None:
        if (
            isinstance(slot_cap, bool)
            or not isinstance(slot_cap, int)
            or not 1 <= slot_cap <= 32
            or pool_id != POOL_ID
            or not isinstance(poll_seconds, (int, float))
            or isinstance(poll_seconds, bool)
            or not 0.001 <= float(poll_seconds) <= 1.0
        ):
            raise ValueError("invalid V2.42.63 model slot configuration")
        self.inner = inner
        self.slot_directory = _ordinary_output_directory(
            slot_directory, output_root
        )
        self.slot_cap = slot_cap
        self.pool_id = pool_id
        self.monotonic = monotonic
        self.sleeper = sleeper
        self.poll_seconds = float(poll_seconds)
        self.acquisitions = 0
        self.total_wait_seconds = 0.0
        self.max_wait_seconds = 0.0
        self.slot_acquisition_counts = [0] * slot_cap
        self._slot_paths = tuple(
            self.slot_directory / f"slot_{index:02d}.lock"
            for index in range(1, slot_cap + 1)
        )
        for path in self._slot_paths:
            if path.is_symlink() or not path.is_file():
                raise ValueError("V2.42.63 model slot file is absent")

    def __getattr__(self, name: str) -> Any:
        return getattr(self.inner, name)

    def _acquire(self) -> tuple[Any, int, float]:
        started = float(self.monotonic())
        offset = (os.getpid() + self.acquisitions) % self.slot_cap
        while True:
            for delta in range(self.slot_cap):
                index = (offset + delta) % self.slot_cap
                path = self._slot_paths[index]
                descriptor = os.open(
                    path,
                    os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC,
                )
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    os.close(descriptor)
                    raise ValueError("V2.42.63 model slot is not a regular file")
                handle = os.fdopen(descriptor, "r+", encoding="utf-8")
                try:
                    fcntl.flock(
                        handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB
                    )
                except BlockingIOError:
                    handle.close()
                    continue
                waited = max(0.0, float(self.monotonic()) - started)
                self.acquisitions += 1
                self.total_wait_seconds += waited
                self.max_wait_seconds = max(self.max_wait_seconds, waited)
                self.slot_acquisition_counts[index] += 1
                return handle, index, waited
            self.sleeper(self.poll_seconds)

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
        value = {
            "artifact_version": 1,
            "role": ROLE,
            "pool_id": self.pool_id,
            "slot_cap": self.slot_cap,
            "acquisitions": self.acquisitions,
            "total_wait_seconds": round(self.total_wait_seconds, 6),
            "max_wait_seconds": round(self.max_wait_seconds, 6),
            "slot_acquisition_counts": list(self.slot_acquisition_counts),
            "label_blind": True,
            "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential": False,
            "mapping_gold_category_question_type_split_evaluator_score_read": False,
        }
        value["receipt_payload_sha256"] = payload_sha256(value)
        return value


def validate_receipt(
    value: dict[str, Any],
    *,
    expected_cap: int = DEFAULT_CAP,
    expected_acquisitions: int | None = None,
) -> dict[str, Any]:
    unsigned = dict(value)
    seal = unsigned.pop("receipt_payload_sha256", None)
    counts = value.get("slot_acquisition_counts")
    acquisitions = value.get("acquisitions")
    total_wait = value.get("total_wait_seconds")
    max_wait = value.get("max_wait_seconds")
    if (
        set(value) != RECEIPT_KEYS
        or value.get("role") != ROLE
        or value.get("pool_id") != POOL_ID
        or value.get("slot_cap") != expected_cap
        or isinstance(acquisitions, bool)
        or not isinstance(acquisitions, int)
        or acquisitions < 0
        or not isinstance(counts, list)
        or len(counts) != expected_cap
        or any(
            isinstance(count, bool) or not isinstance(count, int) or count < 0
            for count in counts
        )
        or sum(counts) != acquisitions
        or not isinstance(total_wait, (int, float))
        or isinstance(total_wait, bool)
        or float(total_wait) < 0
        or not isinstance(max_wait, (int, float))
        or isinstance(max_wait, bool)
        or not 0 <= float(max_wait) <= float(total_wait) + 1e-6
        or value.get("label_blind") is not True
        or value.get(
            "contains_prompt_response_question_query_url_page_prediction_answer_opaque_id_or_credential"
        )
        is not False
        or value.get(
            "mapping_gold_category_question_type_split_evaluator_score_read"
        )
        is not False
        or seal != payload_sha256(unsigned)
        or (
            expected_acquisitions is not None
            and acquisitions != expected_acquisitions
        )
    ):
        raise ValueError("V2.42.63 model slot receipt drifted")
    return dict(value)
