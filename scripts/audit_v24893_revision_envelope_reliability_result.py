#!/usr/bin/env python3
"""Read-only post-result audit for the V2.48.93 neutral gate."""

from __future__ import annotations

import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24893_revision_envelope_reliability_contract as contract  # noqa: E402
from deepwide_agent.v24890_revision_envelope_mapping_bundle import validate_bundle  # noqa: E402
from deepwide_agent.v24891_revision_envelope_child_runtime import (  # noqa: E402
    STAGE_NAME,
    validate_stage_receipt,
)
from scripts import audit_v24883_mapping_recovery_reliability_result as base  # noqa: E402
from scripts import control_v24893_revision_envelope_reliability_gate as control  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.validate_bundle = validate_bundle
    base.STAGE_NAME = STAGE_NAME
    base.validate_stage_receipt = validate_stage_receipt
    base.AUDIT = contract.POSTAUDIT
    for name in ("build", "main"):
        current = getattr(base, name)
        if not getattr(current, "_v24893_translated", False):
            value = types.FunctionType(
                control._translated_code(current.__code__),
                current.__globals__, name=f"v24893_{name}",
                argdefs=current.__defaults__, closure=current.__closure__,
            )
            value.__kwdefaults__ = current.__kwdefaults__
            value.__annotations__ = current.__annotations__
            value._v24893_translated = True
            setattr(base, name, value)
def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
