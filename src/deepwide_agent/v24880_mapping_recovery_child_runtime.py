"""V2.48.75 child runtime with the V2.48.79 effect validator."""

from __future__ import annotations

import copy
import types
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from . import v24875_keyless_coverage_child_runtime as frozen
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
)
from .v24879_mapping_recovery_effect_bundle import (
    ALL_NAMES,
    BUNDLE_NAME,
    FINAL_MODEL_NAME,
    RESULT_NAME,
    TRANSPORT_NAME,
    validate_bundle,
    write_bundle,
)


POLICY_ID = "v24880_mapping_recovery_aware_child_runtime_v1"
TERMINAL_NAME = frozen.TERMINAL_NAME


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.48.80 frozen child function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__,
        namespace,
        name=f"v24880_isolated_{original.__name__}",
        argdefs=original.__defaults__,
        closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


_RUN_CHILD_BUNDLE = _isolated_function(
    frozen.run_child_bundle,
    ALL_NAMES=ALL_NAMES,
    BUNDLE_NAME=BUNDLE_NAME,
    FINAL_MODEL_NAME=FINAL_MODEL_NAME,
    RESULT_NAME=RESULT_NAME,
    TRANSPORT_NAME=TRANSPORT_NAME,
    validate_bundle=validate_bundle,
    write_bundle=write_bundle,
)


def run_child_bundle(
    *,
    output_root: Path,
    directory: Path,
    task: Mapping[str, Any],
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: ThinSameResponseCitationTitleBackfillSearchClient,
    limits: ScoreFirstLimits,
    expected_model_slot_cap: int,
    monotonic: Callable[[], float],
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    return _RUN_CHILD_BUNDLE(
        output_root=output_root,
        directory=directory,
        task=task,
        model=model,
        search=search,
        limits=limits,
        expected_model_slot_cap=expected_model_slot_cap,
        monotonic=monotonic,
        progress=progress,
    )


def validate_isolation() -> None:
    if (
        frozen.run_child_bundle.__globals__["write_bundle"] is not frozen.write_bundle
        or frozen.run_child_bundle.__globals__["validate_bundle"]
        is not frozen.validate_bundle
        or _RUN_CHILD_BUNDLE.__globals__["write_bundle"] is not write_bundle
        or _RUN_CHILD_BUNDLE.__globals__["validate_bundle"] is not validate_bundle
        or _RUN_CHILD_BUNDLE.__code__ is not frozen.run_child_bundle.__code__
    ):
        raise RuntimeError("V2.48.80 isolated child binding drifted")


__all__ = [
    "POLICY_ID",
    "TERMINAL_NAME",
    "run_child_bundle",
    "validate_isolation",
]
