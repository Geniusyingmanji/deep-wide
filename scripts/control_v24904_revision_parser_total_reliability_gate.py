#!/usr/bin/env python3
"""Preregister, audit, and authorize the V2.49.04 neutral gate."""

from __future__ import annotations

import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24904_revision_parser_total_reliability_contract as contract  # noqa: E402
from scripts import control_v24883_mapping_recovery_reliability_gate as base  # noqa: E402


_PARENT_TOKEN = "v24883_mapping_recovery_reliability"
_TOKEN = "v24904_revision_parser_total_reliability"


def _translated_code(code: types.CodeType) -> types.CodeType:
    constants = tuple(
        _translated_code(value)
        if isinstance(value, types.CodeType)
        else value.replace(_PARENT_TOKEN, _TOKEN)
        if isinstance(value, str)
        else value
        for value in code.co_consts
    )
    return code.replace(co_consts=constants)


def _translate(original):
    value = types.FunctionType(
        _translated_code(original.__code__), original.__globals__,
        name=f"v24904_{original.__name__}", argdefs=original.__defaults__,
        closure=original.__closure__,
    )
    value.__kwdefaults__ = original.__kwdefaults__
    value.__annotations__ = original.__annotations__
    value._v24904_translated = True
    return value


def configure() -> None:
    base.contract = contract
    for name in (
        "build_protocol", "validate_protocol", "build_audit", "validate_audit",
        "build_start", "validate_start",
    ):
        current = getattr(base, name)
        if not getattr(current, "_v24904_translated", False):
            setattr(base, name, _translate(current))


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
