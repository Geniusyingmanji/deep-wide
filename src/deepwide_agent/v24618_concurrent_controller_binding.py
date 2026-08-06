"""Shared-mode concurrent controller binding after the V2.46.16 deadlock.

V2.46.14 correctly stopped mutating proof modules, but its exclusive ``RLock``
was held by the main runtime context while eight task threads tried to enter
protocol validation.  A Python ``RLock`` is re-entrant only for its owning
thread, so all task threads blocked before any parent/worker process started.

This append-only repair is a readers-by-mode lease.  Any number of holders may
share the exact same controller, binding mode, and four-object binding vector.
The first holder installs the vector; the final holder restores the original
controller attributes.  A different mode/controller waits, while a thread
that tries to nest a different mode fails immediately instead of deadlocking.
The real proof/total/bounded modules remain immutable.
"""

from __future__ import annotations

import copy
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from . import v24614_title_provenance_controller_binding as frozen


POLICY_ID = "v24618_shared_mode_concurrent_controller_binding_v1"
MODE_PROTOCOL = "protocol"
MODE_RUNTIME = "runtime"
MODES = frozenset({MODE_PROTOCOL, MODE_RUNTIME})
DEFAULT_WAIT_SECONDS = 30.0


class _SharedModeLease:
    def __init__(self) -> None:
        self._condition = threading.Condition(threading.RLock())
        self._mode: str | None = None
        self._controller: Any = None
        self._expected: dict[str, Any] = {}
        self._originals: dict[str, Any] = {}
        self._missing: Any = None
        self._holders = 0
        self._threads: dict[int, tuple[str, int]] = {}
        self._maximum_simultaneous_holders = 0

    @staticmethod
    def _requested_mode(protocol_compatibility: bool) -> str:
        return MODE_PROTOCOL if protocol_compatibility else MODE_RUNTIME

    def _compatible(self, controller: Any, mode: str) -> bool:
        return self._mode == mode and self._controller is controller

    def _validate_installed(self) -> None:
        if (
            self._mode not in MODES
            or self._controller is None
            or self._holders < 1
            or set(self._expected)
            != {"proof", "total", "bounded", "collector_repair"}
            or any(
                getattr(self._controller, name, self._missing) is not value
                for name, value in self._expected.items()
            )
            or not frozen.invariant_valid()
        ):
            raise RuntimeError("V2.46.18 installed controller binding drifted")

    def acquire(
        self,
        controller: Any,
        *,
        protocol_compatibility: bool,
        wait_seconds: float = DEFAULT_WAIT_SECONDS,
    ) -> tuple[int, str]:
        if (
            isinstance(wait_seconds, bool)
            or not isinstance(wait_seconds, (int, float))
            or not 0 < float(wait_seconds) <= 300.0
        ):
            raise ValueError("V2.46.18 wait budget is invalid")
        if not frozen.invariant_valid():
            raise RuntimeError("V2.46.18 runtime proof binding drifted before entry")
        mode = self._requested_mode(protocol_compatibility)
        thread_id = threading.get_ident()
        deadline = time.monotonic() + float(wait_seconds)
        with self._condition:
            held = self._threads.get(thread_id)
            if held is not None and held[0] != mode:
                raise RuntimeError(
                    "V2.46.18 cross-mode nested binding would deadlock"
                )
            while self._mode is not None and not self._compatible(controller, mode):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("V2.46.18 incompatible binding remained active")
                self._condition.wait(timeout=remaining)
            if self._mode is None:
                expected = frozen.binding_vector(
                    protocol_compatibility=protocol_compatibility
                )
                missing = object()
                originals = {
                    name: getattr(controller, name, missing) for name in expected
                }
                for name, value in expected.items():
                    setattr(controller, name, value)
                self._mode = mode
                self._controller = controller
                self._expected = expected
                self._originals = originals
                self._missing = missing
                self._holders = 0
            self._holders += 1
            self._maximum_simultaneous_holders = max(
                self._maximum_simultaneous_holders, self._holders
            )
            current = self._threads.get(thread_id)
            self._threads[thread_id] = (mode, 1 if current is None else current[1] + 1)
            self._validate_installed()
            return thread_id, mode

    def release(self, controller: Any, token: tuple[int, str]) -> None:
        thread_id, mode = token
        if thread_id != threading.get_ident() or mode not in MODES:
            raise RuntimeError("V2.46.18 release token drifted")
        with self._condition:
            if not self._compatible(controller, mode):
                raise RuntimeError("V2.46.18 release binding drifted")
            current = self._threads.get(thread_id)
            if current is None or current[0] != mode or current[1] < 1:
                raise RuntimeError("V2.46.18 thread does not own binding")
            self._validate_installed()
            if current[1] == 1:
                del self._threads[thread_id]
            else:
                self._threads[thread_id] = (mode, current[1] - 1)
            self._holders -= 1
            if self._holders < 0:
                raise RuntimeError("V2.46.18 holder count underflow")
            if self._holders == 0:
                for name, value in self._originals.items():
                    if value is self._missing:
                        delattr(controller, name)
                    else:
                        setattr(controller, name, value)
                self._mode = None
                self._controller = None
                self._expected = {}
                self._originals = {}
                self._missing = None
                self._condition.notify_all()
            if not frozen.invariant_valid():
                raise RuntimeError("V2.46.18 release contaminated runtime proof")

    def snapshot(self) -> dict[str, Any]:
        with self._condition:
            return {
                "mode": self._mode,
                "holder_count": self._holders,
                "holder_thread_count": len(self._threads),
                "maximum_simultaneous_holders": self._maximum_simultaneous_holders,
                "controller_present": self._controller is not None,
                "runtime_module_invariant_valid": frozen.invariant_valid(),
                "proof_total_bounded_or_collector_object_emitted": False,
            }


_LEASE = _SharedModeLease()


@contextmanager
def controller_bindings(
    controller: Any,
    *,
    protocol_compatibility: bool,
    wait_seconds: float = DEFAULT_WAIT_SECONDS,
) -> Iterator[None]:
    token = _LEASE.acquire(
        controller,
        protocol_compatibility=protocol_compatibility,
        wait_seconds=wait_seconds,
    )
    try:
        yield
    finally:
        _LEASE.release(controller, token)


def binding_vector(*, protocol_compatibility: bool) -> dict[str, Any]:
    return frozen.binding_vector(protocol_compatibility=protocol_compatibility)


def invariant_valid() -> bool:
    return frozen.invariant_valid()


def content_free_snapshot() -> dict[str, Any]:
    return copy.deepcopy(_LEASE.snapshot())


__all__ = [
    "DEFAULT_WAIT_SECONDS",
    "MODE_PROTOCOL",
    "MODE_RUNTIME",
    "MODES",
    "POLICY_ID",
    "binding_vector",
    "content_free_snapshot",
    "controller_bindings",
    "frozen",
    "invariant_valid",
]
