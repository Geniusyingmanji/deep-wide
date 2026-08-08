"""Stage-observable child runtime bound to the parser-total production seam."""

from __future__ import annotations

import copy
import types
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Callable

from . import v24891_revision_envelope_child_runtime as frozen
from .v24257_score_first_runtime import ScoreFirstLimits
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24630_thin_backfill_search import ThinSameResponseCitationTitleBackfillSearchClient
from .v24900_revision_parser_total_runtime import run_v24900_task
from .v24901_revision_parser_total_mapping_bundle import (
    ALL_NAMES, BUNDLE_NAME, FINAL_MODEL_NAME, RESULT_NAME, TRANSPORT_NAME,
    validate_bundle, write_bundle,
)


POLICY_ID = "v24902_revision_parser_total_child_runtime_v1"
TERMINAL_NAME = frozen.TERMINAL_NAME
STAGE_NAME = frozen.STAGE_NAME
STAGES = frozen.STAGES
build_stage_receipt = frozen.build_stage_receipt
validate_stage_receipt = frozen.validate_stage_receipt


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.49.02 frozen child function has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__, namespace, name=f"v24902_isolated_{original.__name__}",
        argdefs=original.__defaults__, closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


_RUN_CHILD_BUNDLE = _isolated_function(
    frozen._RUN_CHILD_BUNDLE,
    ALL_NAMES=ALL_NAMES, BUNDLE_NAME=BUNDLE_NAME,
    FINAL_MODEL_NAME=FINAL_MODEL_NAME, RESULT_NAME=RESULT_NAME,
    TRANSPORT_NAME=TRANSPORT_NAME, run_v24873_task=run_v24900_task,
    validate_bundle=validate_bundle, write_bundle=write_bundle,
)


def run_child_bundle(
    *, output_root: Path, directory: Path, task: Mapping[str, Any],
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: ThinSameResponseCitationTitleBackfillSearchClient,
    limits: ScoreFirstLimits, expected_model_slot_cap: int,
    monotonic: Callable[[], float],
    progress: Callable[[Mapping[str, Any]], None] | None = None,
) -> dict[str, Any]:
    return _RUN_CHILD_BUNDLE(
        output_root=output_root, directory=directory, task=task, model=model,
        search=search, limits=limits,
        expected_model_slot_cap=expected_model_slot_cap, monotonic=monotonic,
        progress=progress,
    )


def validate_isolation() -> None:
    if (
        frozen._RUN_CHILD_BUNDLE.__globals__["run_v24873_task"]
        is not frozen.run_v24889_task
        or _RUN_CHILD_BUNDLE.__globals__["run_v24873_task"] is not run_v24900_task
        or _RUN_CHILD_BUNDLE.__globals__["write_bundle"] is not write_bundle
        or _RUN_CHILD_BUNDLE.__globals__["validate_bundle"] is not validate_bundle
        or _RUN_CHILD_BUNDLE.__code__ is not frozen._RUN_CHILD_BUNDLE.__code__
    ):
        raise RuntimeError("V2.49.02 isolated child binding drifted")


__all__ = [
    "POLICY_ID", "STAGES", "STAGE_NAME", "TERMINAL_NAME",
    "build_stage_receipt", "run_child_bundle", "validate_isolation",
    "validate_stage_receipt",
]
