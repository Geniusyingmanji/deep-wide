"""Observed subprocess gate bound to the parser-total bundle validator."""

from __future__ import annotations

import copy
import types
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import v24892_revision_envelope_subprocess_gate as frozen
from .v24901_revision_parser_total_mapping_bundle import (
    BUNDLE_NAME, DATA_NAMES, FINAL_MODEL_NAME, RESULT_NAME, TRANSPORT_NAME,
    validate_bundle,
)
from .v24902_revision_parser_total_child_runtime import TERMINAL_NAME


POLICY_ID = "v24903_revision_parser_total_subprocess_gate_v1"
BASE_PARENT_NAME = frozen.BASE_PARENT_NAME
PARENT_NAME = frozen.PARENT_NAME
DISPOSITIONS = frozen.DISPOSITIONS
validate_parent_bundle_receipt = frozen.validate_parent_bundle_receipt


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.49.03 frozen gate function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__, namespace, name=f"v24903_isolated_{original.__name__}",
        argdefs=original.__defaults__, closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


_RUN_OBSERVED = _isolated_function(
    frozen._RUN_OBSERVED,
    BUNDLE_NAME=BUNDLE_NAME, DATA_NAMES=DATA_NAMES,
    FINAL_MODEL_NAME=FINAL_MODEL_NAME, RESULT_NAME=RESULT_NAME,
    TRANSPORT_NAME=TRANSPORT_NAME, TERMINAL_NAME=TERMINAL_NAME,
    validate_bundle=validate_bundle,
)


def run_observed_bundle_subprocess(
    *, cwd: Path, output_root: Path, directory: Path,
    command: Sequence[str], environment: Mapping[str, str],
    timeout_seconds: float, expected_model_slot_cap: int,
    popen: Any = frozen.frozen.frozen.subprocess.Popen,
):
    return _RUN_OBSERVED(
        cwd=cwd, output_root=output_root, directory=directory,
        command=command, environment=environment,
        timeout_seconds=timeout_seconds,
        expected_model_slot_cap=expected_model_slot_cap, popen=popen,
    )


def validate_isolation() -> None:
    if (
        frozen._RUN_OBSERVED.__globals__["validate_bundle"]
        is not frozen.validate_bundle
        or _RUN_OBSERVED.__globals__["validate_bundle"] is not validate_bundle
        or _RUN_OBSERVED.__code__ is not frozen._RUN_OBSERVED.__code__
    ):
        raise RuntimeError("V2.49.03 isolated gate binding drifted")


__all__ = [
    "BASE_PARENT_NAME", "DISPOSITIONS", "PARENT_NAME", "POLICY_ID",
    "run_observed_bundle_subprocess", "validate_isolation",
    "validate_parent_bundle_receipt",
]
