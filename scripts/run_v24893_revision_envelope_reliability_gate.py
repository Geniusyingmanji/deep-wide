#!/usr/bin/env python3
"""Run the frozen neutral V2.48.93 reliability gate."""

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
from deepwide_agent.v24892_revision_envelope_subprocess_gate import (  # noqa: E402
    run_observed_bundle_subprocess,
    validate_parent_bundle_receipt,
)
from scripts import run_v24883_mapping_recovery_reliability_gate as base  # noqa: E402
from scripts import control_v24893_revision_envelope_reliability_gate as control  # noqa: E402


def configure() -> None:
    control.configure()
    base.contract = contract
    base.validate_bundle = validate_bundle
    base.STAGE_NAME = STAGE_NAME
    base.validate_stage_receipt = validate_stage_receipt
    base.run_observed_bundle_subprocess = run_observed_bundle_subprocess
    base.validate_parent_bundle_receipt = validate_parent_bundle_receipt
    for name in ("_validate_authorization", "main"):
        current = getattr(base, name)
        if not getattr(current, "_v24893_translated", False):
            code = control._translated_code(current.__code__)
            value = types.FunctionType(
                code, current.__globals__, name=f"v24893_{name}",
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
