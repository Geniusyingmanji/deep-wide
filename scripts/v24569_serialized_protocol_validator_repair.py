#!/usr/bin/env python3
"""Serialized protocol-validator repair after the quarantined V2.45.67 wave.

V2.45.67 temporarily patches the shared V2.44.92 control module while
validating a successor protocol.  Its eight parent threads could interleave
that critical section.  This append-only repair owns a re-entrant lock around
the complete validator call.  It changes no task, model, search, fetch,
evidence, credit, budget, or evaluator behavior.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from scripts import v24567_strict_reachability_conversion_external_gate as frozen


POLICY_ID = "v24569_serialized_strict_protocol_validator_repair_v1"
_FROZEN_VALIDATE_PROTOCOL = frozen.validate_protocol
_PROTOCOL_VALIDATOR_LOCK = threading.RLock()


@contextmanager
def serialized_protocol_validation() -> Iterator[None]:
    """Own the entire nested control-module patch/validation critical section."""

    with _PROTOCOL_VALIDATOR_LOCK:
        yield


def validate_protocol(
    root: Path = frozen.ROOT,
    *,
    value: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    with serialized_protocol_validation():
        return _FROZEN_VALIDATE_PROTOCOL(root, value=value)


def binding_valid() -> bool:
    return (
        callable(_FROZEN_VALIDATE_PROTOCOL)
        and _FROZEN_VALIDATE_PROTOCOL is frozen.validate_protocol
        and isinstance(_PROTOCOL_VALIDATOR_LOCK, type(threading.RLock()))
    )


__all__ = [
    "POLICY_ID",
    "binding_valid",
    "serialized_protocol_validation",
    "validate_protocol",
]
