#!/usr/bin/env python3
"""Cross-pipeline lease for expensive DeepWide benchmark/API work.

The lock is process-scoped through ``flock`` and the adjacent JSON record is
observability only.  Reading either file cannot expose benchmark content.
"""

from __future__ import annotations

import fcntl
import json
import os
import socket
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, TextIO


DEFAULT_RELATIVE_PATH = "outputs/deepwide_benchmark_api.lease.lock"


class DeepWideApiLeaseBusy(RuntimeError):
    """Another authorized pipeline currently owns the shared API lease."""


def _write_observation(handle: TextIO, value: dict[str, Any]) -> None:
    handle.seek(0)
    handle.truncate()
    json.dump(value, handle, ensure_ascii=False, sort_keys=True)
    handle.write("\n")
    handle.flush()
    os.fsync(handle.fileno())


@contextmanager
def acquire_deepwide_api_lease(
    root: Path,
    *,
    owner: str,
    purpose: str,
    path: Path | None = None,
) -> Iterator[dict[str, Any]]:
    """Acquire the one shared forward/evaluator API lease without waiting."""

    root = root.resolve()
    if not owner or not purpose or any(character in owner for character in "\r\n"):
        raise ValueError("lease owner and purpose must be non-empty single lines")
    lease_path = (path or (root / DEFAULT_RELATIVE_PATH)).resolve()
    if not lease_path.is_relative_to((root / "outputs").resolve()):
        raise ValueError("DeepWide API lease must remain below outputs/")
    lease_path.parent.mkdir(parents=True, exist_ok=True)
    with lease_path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            handle.seek(0)
            observed = handle.read(4096).strip()
            detail = f"; observed={observed}" if observed else ""
            raise DeepWideApiLeaseBusy(
                f"DeepWide benchmark/API lease is held{detail}"
            ) from exc
        record = {
            "artifact_version": 1,
            "role": "deepwide_shared_benchmark_api_lease",
            "owner": owner,
            "purpose": purpose,
            "pid": os.getpid(),
            "hostname": socket.gethostname(),
            "acquired_at_unix": int(time.time()),
            "label_blind": True,
            "benchmark_question_prediction_mapping_gold_score_read": False,
        }
        _write_observation(handle, record)
        try:
            yield record
        finally:
            # The lock, rather than this advisory record, is authoritative.
            released = {
                **record,
                "released_at_unix": int(time.time()),
                "active": False,
            }
            _write_observation(handle, released)
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
