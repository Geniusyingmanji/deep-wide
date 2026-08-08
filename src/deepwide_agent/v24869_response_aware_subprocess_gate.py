"""V2.48.65 parent gate bound to the response-aware bundle validator.

The frozen parent subprocess observer and receipt format are retained through
an isolated closure-free clone.  Only the complete-bundle validator is
rebound to V2.48.67, so return-code, timeout, terminal, and artifact-presence
classification remain unchanged.  No evaluator capability is present.
"""

from __future__ import annotations

import copy
import types
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24865_coverage_revision_subprocess_gate as frozen
from .v24309_runner_exit_integration import ObservedChildOutcome
from .v24867_response_aware_coverage_bundle import validate_bundle


POLICY_ID = "v24869_response_aware_coverage_subprocess_gate_v1"
BASE_PARENT_NAME = frozen.BASE_PARENT_NAME
DISPOSITIONS = frozen.DISPOSITIONS
PARENT_NAME = frozen.PARENT_NAME
PARENT_ROLE = frozen.PARENT_ROLE


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.48.69 frozen parent function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__,
        namespace,
        name=f"v24869_isolated_{original.__name__}",
        argdefs=original.__defaults__,
        closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


_RUN_OBSERVED_BUNDLE_SUBPROCESS = _isolated_function(
    frozen.run_observed_bundle_subprocess,
    validate_bundle=validate_bundle,
)


def run_observed_bundle_subprocess(
    *,
    cwd: Path,
    output_root: Path,
    directory: Path,
    command: Sequence[str],
    environment: Mapping[str, str],
    timeout_seconds: float,
    expected_model_slot_cap: int,
    expected_tavily_key_slot_cap: int,
    popen: Any = frozen.subprocess.Popen,
) -> tuple[ObservedChildOutcome, dict[str, Any]]:
    return _RUN_OBSERVED_BUNDLE_SUBPROCESS(
        cwd=cwd,
        output_root=output_root,
        directory=directory,
        command=command,
        environment=environment,
        timeout_seconds=timeout_seconds,
        expected_model_slot_cap=expected_model_slot_cap,
        expected_tavily_key_slot_cap=expected_tavily_key_slot_cap,
        popen=popen,
    )


def validate_isolation() -> None:
    if (
        frozen.run_observed_bundle_subprocess.__globals__["validate_bundle"]
        is not frozen.validate_bundle
        or _RUN_OBSERVED_BUNDLE_SUBPROCESS.__globals__["validate_bundle"]
        is not validate_bundle
        or _RUN_OBSERVED_BUNDLE_SUBPROCESS.__code__
        is not frozen.run_observed_bundle_subprocess.__code__
    ):
        raise RuntimeError("V2.48.69 isolated subprocess binding drifted")


build_parent_receipt = frozen.build_parent_receipt
validate_parent_bundle_receipt = frozen.validate_parent_bundle_receipt


__all__ = [
    "BASE_PARENT_NAME",
    "DISPOSITIONS",
    "PARENT_NAME",
    "PARENT_ROLE",
    "POLICY_ID",
    "build_parent_receipt",
    "run_observed_bundle_subprocess",
    "validate_isolation",
    "validate_parent_bundle_receipt",
]
