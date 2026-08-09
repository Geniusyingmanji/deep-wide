"""Isolated single-task production integration for distinct row coverage.

The frozen V2.48.57 function chain is recreated with private globals mappings.
Only ``TwoWaveCachingSearchClient.search_many`` is rebound to the V2.50.20
pacing-aware distinct-coverage retrieval.  The model, planner, visible-schema
wrapper, cache serve, synthesis/repair, normalizer, progress, budget, deadline,
fallback, and parent result envelope remain the frozen parent code objects.

The injected search client already carries the original visible question in
memory.  Content-free pacing and distinct-selection receipts are attached to
that task-local client and removed from the parent retrieval payload, keeping
the frozen parent schema byte-compatible.  Parent globals remain untouched.
"""

from __future__ import annotations

import copy
from typing import Any

from . import v24273_two_wave_task_runtime as retrieval_runtime
from . import v24318_deadline_conservation_runtime as conservation_runtime
from . import v24319_runner_integration as runner_integration
from . import v24630_exact220_task_integration as task_integration
from .v24856_pacing_aware_admission import validate_receipt as validate_pacing_receipt
from .v25019_production_distinct_coverage_selection import (
    validate_receipt as validate_selection_receipt,
)
from .v25020_pacing_distinct_coverage_retrieval import (
    run_pacing_distinct_coverage_retrieval,
    validate_isolation as validate_retrieval_isolation,
)


POLICY_ID = "v25022_production_distinct_coverage_task_integration_v1"


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.50.22 frozen parent unexpectedly has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    from types import FunctionType

    value = FunctionType(
        original.__code__,
        namespace,
        name=f"v25022_isolated_{original.__name__}",
        argdefs=original.__defaults__,
        closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


def _production_retrieval(*args: Any, **kwargs: Any) -> dict[str, Any]:
    search = kwargs.get("search")
    if search is None and len(args) >= 2:
        search = args[1]
    question = getattr(search, "_v24981_visible_question", None)
    if not isinstance(question, str) or not question.strip():
        raise TypeError("V2.50.22 visible-question search binding is absent")
    forwarded = dict(kwargs)
    forwarded["visible_question"] = question
    value = run_pacing_distinct_coverage_retrieval(*args, **forwarded)
    pacing = validate_pacing_receipt(value["pacing_admission_receipt"])
    selection = validate_selection_receipt(
        value["distinct_coverage_selection_receipt"]
    )
    setattr(search, "_v25022_pacing_admission_receipt", copy.deepcopy(pacing))
    setattr(search, "_v25022_distinct_coverage_receipt", copy.deepcopy(selection))
    output = copy.deepcopy(value)
    output.pop("pacing_admission_receipt", None)
    output.pop("distinct_coverage_selection_receipt", None)
    return output


_ISOLATED_SEARCH_MANY = _isolated_function(
    retrieval_runtime.TwoWaveCachingSearchClient.search_many,
    run_two_wave_retrieval=_production_retrieval,
)


class ProductionDistinctCoverageCachingSearchClient(
    retrieval_runtime.TwoWaveCachingSearchClient
):
    search_many = _ISOLATED_SEARCH_MANY


_ISOLATED_RUN_PARENT = _isolated_function(
    conservation_runtime._run_parent,
    TwoWaveCachingSearchClient=ProductionDistinctCoverageCachingSearchClient,
)
_ISOLATED_RUN_V24318_TASK = _isolated_function(
    conservation_runtime.run_v24318_task,
    _run_parent=_ISOLATED_RUN_PARENT,
)
_ISOLATED_RUN_V24319_TASK = _isolated_function(
    runner_integration.run_v24319_task,
    run_v24318_task=_ISOLATED_RUN_V24318_TASK,
)
_PARENT_RUN_TASK = _isolated_function(
    task_integration.run_v24630_task,
    run_v24319_task=_ISOLATED_RUN_V24319_TASK,
)


def run_production_distinct_coverage_task(*args: Any, **kwargs: Any) -> Any:
    validate_isolation()
    return _PARENT_RUN_TASK(*args, **kwargs)


def validate_isolation() -> None:
    validate_retrieval_isolation()
    if (
        retrieval_runtime.TwoWaveCachingSearchClient.search_many
        is _ISOLATED_SEARCH_MANY
        or conservation_runtime._run_parent is _ISOLATED_RUN_PARENT
        or runner_integration.run_v24319_task is _ISOLATED_RUN_V24319_TASK
        or task_integration.run_v24630_task is _PARENT_RUN_TASK
        or _ISOLATED_SEARCH_MANY.__globals__["run_two_wave_retrieval"]
        is not _production_retrieval
        or retrieval_runtime.TwoWaveCachingSearchClient.search_many.__globals__[
            "run_two_wave_retrieval"
        ]
        is _production_retrieval
        or _ISOLATED_RUN_PARENT.__globals__["TwoWaveCachingSearchClient"]
        is not ProductionDistinctCoverageCachingSearchClient
        or _ISOLATED_RUN_V24318_TASK.__globals__["_run_parent"]
        is not _ISOLATED_RUN_PARENT
        or _ISOLATED_RUN_V24319_TASK.__globals__["run_v24318_task"]
        is not _ISOLATED_RUN_V24318_TASK
        or _PARENT_RUN_TASK.__globals__["run_v24319_task"]
        is not _ISOLATED_RUN_V24319_TASK
    ):
        raise RuntimeError("V2.50.22 isolated task integration binding drifted")


__all__ = [
    "POLICY_ID",
    "ProductionDistinctCoverageCachingSearchClient",
    "run_production_distinct_coverage_task",
    "validate_isolation",
]
