#!/usr/bin/env python3
"""Run one fresh label-blind V2.49.05 exact-220 forward."""

from __future__ import annotations

import copy
import sys
import types
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24905_revision_parser_total_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24898_revision_parser_total_integration import (  # noqa: E402
    RESULT_ROLE as COVERAGE_RESULT_ROLE,
    validate_integration_receipt,
)
from deepwide_agent.v24899_revision_parser_total_exact_task import validate_envelope  # noqa: E402
from deepwide_agent import v24901_revision_parser_total_mapping_bundle as bundle  # noqa: E402
from deepwide_agent import v24903_revision_parser_total_subprocess_gate as gate  # noqa: E402
from scripts import run_v24877_keyless_coverage_exact220 as base  # noqa: E402


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.49.05 collector function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__, namespace, name=f"v24905_isolated_{original.__name__}",
        argdefs=original.__defaults__, closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


def configure() -> None:
    base.contract = contract
    base.PREAUDIT_ROLE = "v24905_revision_parser_total_exact220_preactivation_audit"
    base.START_ROLE = "v24905_revision_parser_total_exact220_execution_start"
    base.PROGRESS_ROLE = "v24905_revision_parser_total_exact220_safe_forward_progress"
    base.SUMMARY_ROLE = "v24905_revision_parser_total_exact220_run_summary"
    base.FREEZE_ROLE = "v24905_revision_parser_total_exact220_prediction_freeze"
    base.FORWARD_ROLE = "v24905_revision_parser_total_exact220_forward_result"
    base.validate_envelope = validate_envelope
    base.validate_integration_receipt = validate_integration_receipt
    base.COVERAGE_RESULT_ROLE = COVERAGE_RESULT_ROLE
    base.validate_bundle = bundle.validate_bundle
    base.validate_effect_receipt = bundle.validate_effect_receipt
    base.run_observed_bundle_subprocess = gate.run_observed_bundle_subprocess
    bindings = {
        "contract": contract,
        "validate_envelope": validate_envelope,
        "validate_integration_receipt": validate_integration_receipt,
        "COVERAGE_RESULT_ROLE": COVERAGE_RESULT_ROLE,
        "validate_bundle": bundle.validate_bundle,
        "validate_effect_receipt": bundle.validate_effect_receipt,
    }
    base._validate_scheduler_result = _isolated_function(
        base._validate_scheduler_result, **bindings
    )
    base._coverage_totals = _isolated_function(base._coverage_totals, **bindings)
    base._effect_totals = _isolated_function(base._effect_totals, **bindings)


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
