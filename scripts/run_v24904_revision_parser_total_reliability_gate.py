#!/usr/bin/env python3
"""Run the frozen benchmark-external V2.49.04 reliability gate."""

from __future__ import annotations

import sys
import types
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24904_revision_parser_total_reliability_contract as contract  # noqa: E402
from deepwide_agent.v24901_revision_parser_total_mapping_bundle import validate_bundle  # noqa: E402
from deepwide_agent.v24902_revision_parser_total_child_runtime import (  # noqa: E402
    STAGE_NAME, validate_stage_receipt,
)
from deepwide_agent.v24903_revision_parser_total_subprocess_gate import (  # noqa: E402
    run_observed_bundle_subprocess, validate_parent_bundle_receipt,
)
from scripts import run_v24883_mapping_recovery_reliability_gate as base  # noqa: E402
from scripts import control_v24904_revision_parser_total_reliability_gate as control  # noqa: E402


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
        if not getattr(current, "_v24904_translated", False):
            value = types.FunctionType(
                control._translated_code(current.__code__), current.__globals__,
                name=f"v24904_{name}", argdefs=current.__defaults__,
                closure=current.__closure__,
            )
            value.__kwdefaults__ = current.__kwdefaults__
            value.__annotations__ = current.__annotations__
            value._v24904_translated = True
            setattr(base, name, value)


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
