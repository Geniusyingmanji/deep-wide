"""Content-free enforcing watchdog for one bounded external wave.

The historical ``maximum_batch_wall_seconds`` field was only checked after
all futures returned.  This module turns the same ceiling into an active
deadline without touching task, query, URL, page, prediction, evaluator, or
credential content.  At expiry it targets only descendant process groups
whose command line contains the caller's unique runner marker and a frozen
``supervisor`` or ``worker`` command token.

The watchdog never restarts, resumes, skips, or selectively retries work.  It
emits counts and booleans only; process identifiers and command lines remain
private to the in-memory control path.
"""

from __future__ import annotations

import os
import signal
import threading
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any


POLICY_ID = "v24620_descendant_process_group_batch_watchdog_v1"
DEFAULT_GRACE_SECONDS = 2.0
_RUNTIME_TOKENS = (b"supervisor", b"worker")


def _proc_record(path: Path) -> tuple[int, int, bytes] | None:
    """Return ``(ppid, process_group, cmdline)`` without exposing content."""

    try:
        stat = (path / "stat").read_text(encoding="utf-8")
        closing = stat.rfind(")")
        if closing < 0:
            return None
        fields = stat[closing + 2 :].split()
        if len(fields) < 3:
            return None
        ppid = int(fields[1])
        process_group = int(fields[2])
        command = (path / "cmdline").read_bytes()
        return ppid, process_group, command
    except (FileNotFoundError, PermissionError, ProcessLookupError, ValueError):
        return None


def descendant_runner_process_groups(
    root_pid: int,
    runner_marker: str,
    *,
    proc_root: Path = Path("/proc"),
) -> tuple[int, ...]:
    """Find only marked supervisor/worker groups below ``root_pid``."""

    if (
        isinstance(root_pid, bool)
        or not isinstance(root_pid, int)
        or root_pid <= 0
        or not isinstance(runner_marker, str)
        or not runner_marker
        or "\x00" in runner_marker
    ):
        raise ValueError("V2.46.20 watchdog identity is invalid")
    records: dict[int, tuple[int, int, bytes]] = {}
    try:
        entries = tuple(proc_root.iterdir())
    except (FileNotFoundError, PermissionError):
        return ()
    for entry in entries:
        if not entry.name.isdigit():
            continue
        record = _proc_record(entry)
        if record is not None:
            records[int(entry.name)] = record
    descendants = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, (ppid, _group, _command) in records.items():
            if pid not in descendants and ppid in descendants:
                descendants.add(pid)
                changed = True
    marker = runner_marker.encode("utf-8")
    own_group = os.getpgrp()
    groups = {
        group
        for pid, (_ppid, group, command) in records.items()
        if pid in descendants
        and pid != root_pid
        and group > 0
        and group != own_group
        and marker in command
        and any(token in command.split(b"\x00") for token in _RUNTIME_TOKENS)
    }
    return tuple(sorted(groups))


def _signal_process_groups(groups: Sequence[int], sig: int) -> tuple[int, int]:
    signaled = 0
    absent = 0
    for group in tuple(dict.fromkeys(int(item) for item in groups)):
        try:
            os.killpg(group, sig)
            signaled += 1
        except ProcessLookupError:
            absent += 1
        except PermissionError:
            # The caller records a content-free failure count.
            raise
    return signaled, absent


class EnforcingBatchWatchdog:
    """Enforce a wall deadline over marked descendant process groups."""

    def __init__(
        self,
        *,
        runner_marker: str,
        timeout_seconds: float,
        root_pid: int | None = None,
        grace_seconds: float = DEFAULT_GRACE_SECONDS,
        snapshot: Callable[[], Sequence[int]] | None = None,
        signal_groups: Callable[[Sequence[int], int], tuple[int, int]] | None = None,
    ) -> None:
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 0 < float(timeout_seconds) <= 600.0
            or isinstance(grace_seconds, bool)
            or not isinstance(grace_seconds, (int, float))
            or not 0 <= float(grace_seconds) <= 10.0
        ):
            raise ValueError("V2.46.20 watchdog budget is invalid")
        self._root_pid = os.getpid() if root_pid is None else int(root_pid)
        self._runner_marker = runner_marker
        self._timeout = float(timeout_seconds)
        self._grace = float(grace_seconds)
        self._snapshot = snapshot or (
            lambda: descendant_runner_process_groups(
                self._root_pid, self._runner_marker
            )
        )
        self._signal = signal_groups or _signal_process_groups
        self._cancel = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._started = False
        self._closed = False
        self._triggered = False
        self._initial_group_count = 0
        self._remaining_group_count = 0
        self._term_signal_count = 0
        self._kill_signal_count = 0
        self._already_absent_count = 0
        self._signal_failure_count = 0

    def _signal_once(self, groups: Sequence[int], sig: int) -> tuple[int, int]:
        try:
            return self._signal(tuple(groups), sig)
        except (OSError, RuntimeError, TypeError, ValueError):
            with self._lock:
                self._signal_failure_count += len(tuple(groups))
            return 0, 0

    def _run(self) -> None:
        if self._cancel.wait(self._timeout):
            return
        with self._lock:
            self._triggered = True
        initial = tuple(self._snapshot())
        term, absent = self._signal_once(initial, signal.SIGTERM)
        with self._lock:
            self._initial_group_count = len(initial)
            self._term_signal_count = term
            self._already_absent_count += absent
        if self._grace:
            time.sleep(self._grace)
        # A terminated supervisor can orphan a separately-sessioned worker.
        # Keep the initial groups so reparenting cannot evade SIGKILL.
        remaining = tuple(sorted(set(initial) | set(self._snapshot())))
        killed, absent = self._signal_once(remaining, signal.SIGKILL)
        with self._lock:
            self._remaining_group_count = len(remaining)
            self._kill_signal_count = killed
            self._already_absent_count += absent

    def start(self) -> "EnforcingBatchWatchdog":
        with self._lock:
            if self._started or self._closed:
                raise RuntimeError("V2.46.20 watchdog cannot be started twice")
            self._started = True
            self._thread = threading.Thread(
                target=self._run,
                name="v24620-enforcing-batch-watchdog",
                daemon=True,
            )
            self._thread.start()
        return self

    def close(self) -> None:
        with self._lock:
            if not self._started or self._closed:
                raise RuntimeError("V2.46.20 watchdog lifecycle drifted")
            self._closed = True
            thread = self._thread
        self._cancel.set()
        if thread is not None:
            thread.join(timeout=self._grace + 5.0)
            if thread.is_alive():
                raise RuntimeError("V2.46.20 watchdog thread did not close")

    def content_free_receipt(self) -> dict[str, Any]:
        with self._lock:
            return {
                "policy_id": POLICY_ID,
                "timeout_seconds": self._timeout,
                "grace_seconds": self._grace,
                "started": self._started,
                "closed": self._closed,
                "triggered": self._triggered,
                "initial_marked_process_group_count": self._initial_group_count,
                "remaining_marked_process_group_count": self._remaining_group_count,
                "term_signal_count": self._term_signal_count,
                "kill_signal_count": self._kill_signal_count,
                "already_absent_count": self._already_absent_count,
                "signal_failure_count": self._signal_failure_count,
                "process_identifier_or_command_line_emitted": False,
                "task_question_query_url_title_page_prediction_or_value_opened": False,
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read": False,
                "retry_resume_skip_or_selective_rerun_performed": False,
            }

    def __enter__(self) -> "EnforcingBatchWatchdog":
        return self.start()

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        self.close()


__all__ = [
    "DEFAULT_GRACE_SECONDS",
    "EnforcingBatchWatchdog",
    "POLICY_ID",
    "descendant_runner_process_groups",
]
