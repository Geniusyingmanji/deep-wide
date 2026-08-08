"""V2.48.76 parent gate with V2.48.79 bundle validation."""

from __future__ import annotations

import copy
import types
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24876_keyless_coverage_subprocess_gate as frozen
from .v24879_mapping_recovery_effect_bundle import (
    BUNDLE_NAME,
    DATA_NAMES,
    FINAL_MODEL_NAME,
    RESULT_NAME,
    TRANSPORT_NAME,
    validate_bundle,
)
from .v24880_mapping_recovery_child_runtime import TERMINAL_NAME


POLICY_ID = "v24881_mapping_recovery_aware_subprocess_gate_v1"
BASE_PARENT_NAME = frozen.BASE_PARENT_NAME
PARENT_NAME = frozen.PARENT_NAME
DISPOSITIONS = frozen.DISPOSITIONS
validate_parent_bundle_receipt = frozen.validate_parent_bundle_receipt


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.48.81 frozen gate function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__,
        namespace,
        name=f"v24881_isolated_{original.__name__}",
        argdefs=original.__defaults__,
        closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


_RUN_OBSERVED = _isolated_function(
    frozen.run_observed_bundle_subprocess,
    BUNDLE_NAME=BUNDLE_NAME,
    DATA_NAMES=DATA_NAMES,
    FINAL_MODEL_NAME=FINAL_MODEL_NAME,
    RESULT_NAME=RESULT_NAME,
    TRANSPORT_NAME=TRANSPORT_NAME,
    TERMINAL_NAME=TERMINAL_NAME,
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
    popen: Any = frozen.subprocess.Popen,
):
    return _RUN_OBSERVED(
        cwd=cwd,
        output_root=output_root,
        directory=directory,
        command=command,
        environment=environment,
        timeout_seconds=timeout_seconds,
        expected_model_slot_cap=expected_model_slot_cap,
        popen=popen,
    )


def validate_isolation() -> None:
    if (
        frozen.run_observed_bundle_subprocess.__globals__["validate_bundle"]
        is not frozen.validate_bundle
        or _RUN_OBSERVED.__globals__["validate_bundle"] is not validate_bundle
        or _RUN_OBSERVED.__code__
        is not frozen.run_observed_bundle_subprocess.__code__
    ):
        raise RuntimeError("V2.48.81 isolated gate binding drifted")


__all__ = [
    "BASE_PARENT_NAME",
    "DISPOSITIONS",
    "PARENT_NAME",
    "POLICY_ID",
    "run_observed_bundle_subprocess",
    "validate_isolation",
    "validate_parent_bundle_receipt",
]
