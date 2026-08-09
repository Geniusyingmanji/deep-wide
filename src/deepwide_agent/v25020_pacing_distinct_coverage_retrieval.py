"""Pacing-aware production retrieval with one isolated selection treatment.

This wrapper reuses the frozen V2.48.56 parent retrieval code object.  Its
private globals mapping preserves the pacing-aware controller and replaces
only (1) the budget-equivalent adapter with an observational subclass that
captures same-run first-wave pages and (2) the second invocation of the frozen
lead selector with V2.50.19's matched-count distinct-identity selector.

The first-wave selection and all search/fetch effects remain parent-identical.
When the strict visible multi-row strategy is inapplicable or produces no
strict distinct-coverage gain, the second-wave request vector is byte-for-byte
the frozen V2.48.57 vector.  Context-local state prevents concurrent tasks from
sharing questions, pages, or receipts.  No parent module globals are mutated.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from contextvars import ContextVar
from types import FunctionType
from typing import Any

from . import v24272_two_wave_retrieval as parent_retrieval
from . import v24856_pacing_aware_admission as pacing
from .clients import canonicalize_url
from .v24270_budget_equivalent_union import BudgetEquivalentTaskUnionSearchClient
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v25019_production_distinct_coverage_selection import (
    select_production_second_wave,
    validate_receipt as validate_selection_receipt,
)


POLICY_ID = "v25020_pacing_aware_distinct_coverage_retrieval_v1"
_CONTEXT: ContextVar[dict[str, Any] | None] = ContextVar(
    "v25020_production_retrieval_context", default=None
)
_ORIGINAL_LEAD_REQUESTS = parent_retrieval._lead_requests
_ORIGINAL_BUDGET_CLIENT = parent_retrieval.BudgetEquivalentTaskUnionSearchClient
_ORIGINAL_PACING_PARENT = pacing._RUN_PARENT_ISOLATED
_ORIGINAL_PACING_WRAPPER = pacing.run_pacing_aware_two_wave_retrieval


def _clone(function: Any, replacements: Mapping[str, Any], *, name: str) -> Any:
    if function.__closure__:
        raise RuntimeError("V2.50.20 frozen parent unexpectedly has closure state")
    namespace = dict(function.__globals__)
    namespace.update(dict(replacements))
    cloned = FunctionType(
        function.__code__,
        namespace,
        name=name,
        argdefs=function.__defaults__,
        closure=None,
    )
    cloned.__kwdefaults__ = copy.deepcopy(function.__kwdefaults__)
    cloned.__annotations__ = copy.deepcopy(function.__annotations__)
    return cloned


class _ObservedBudgetEquivalentTaskUnionSearchClient(
    BudgetEquivalentTaskUnionSearchClient
):
    """Capture first-wave pages without changing the inherited effects."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._v25020_fetch_invocations = 0

    def fetch_urls(self, requests_: Sequence[dict[str, str]]) -> Any:
        value = super().fetch_urls(requests_)
        context = _CONTEXT.get()
        if context is None:
            raise RuntimeError("V2.50.20 retrieval context is absent")
        if self._v25020_fetch_invocations == 0:
            context["first_wave_page_batches"] = copy.deepcopy(value)
        self._v25020_fetch_invocations += 1
        return value


def _distinct_lead_requests(
    batches: Sequence[Mapping[str, Any]], limit: int
) -> list[dict[str, str]]:
    context = _CONTEXT.get()
    if context is None:
        raise RuntimeError("V2.50.20 lead-selection context is absent")
    invocation = int(context["lead_invocations"])
    context["lead_invocations"] = invocation + 1
    if invocation == 0:
        values = _ORIGINAL_LEAD_REQUESTS(batches, limit)
        context["first_wave_requests"] = copy.deepcopy(values)
        return values
    if invocation != 1:
        raise RuntimeError("V2.50.20 unexpected lead-selection invocation")
    first_requests = list(context.get("first_wave_requests") or [])
    excluded = {
        canonical
        for value in first_requests
        if (canonical := canonicalize_url(str(value.get("url") or "")))
    }
    selected = select_production_second_wave(
        context.get("first_wave_page_batches") or [],
        batches,
        question=str(context["visible_question"]),
        cap=limit,
        exclude_urls=excluded,
    )
    context["selection_receipt"] = copy.deepcopy(
        selected["content_free_receipt"]
    )
    context["control_second_wave_requests"] = copy.deepcopy(selected["control"])
    context["candidate_second_wave_requests"] = copy.deepcopy(selected["candidate"])
    return copy.deepcopy(selected["candidate"])


_RUN_PARENT_DISTINCT = _clone(
    _ORIGINAL_PACING_PARENT,
    {
        "BudgetEquivalentTaskUnionSearchClient": (
            _ObservedBudgetEquivalentTaskUnionSearchClient
        ),
        "_lead_requests": _distinct_lead_requests,
    },
    name="v25020_isolated_run_two_wave_retrieval",
)
_RUN_PACING_DISTINCT = _clone(
    _ORIGINAL_PACING_WRAPPER,
    {"_RUN_PARENT_ISOLATED": _RUN_PARENT_DISTINCT},
    name="v25020_pacing_distinct_coverage_retrieval",
)


def run_pacing_distinct_coverage_retrieval(
    queries: Sequence[str],
    *,
    search: Any,
    visible_question: str,
    required_column_count: int,
    explicit_row_target: int = 0,
    search_results_per_query: int = 3,
    policy: TwoWavePolicy | None = None,
    monotonic: Any = None,
) -> dict[str, Any]:
    """Run the frozen pacing chain plus one matched second-wave treatment."""

    if not isinstance(visible_question, str) or not visible_question.strip():
        raise ValueError("V2.50.20 visible question is absent")
    chosen = policy or TwoWavePolicy()
    chosen.validate()
    context: dict[str, Any] = {
        "visible_question": visible_question.strip(),
        "lead_invocations": 0,
        "first_wave_requests": [],
        "first_wave_page_batches": [],
        "selection_receipt": None,
        "control_second_wave_requests": [],
        "candidate_second_wave_requests": [],
    }
    token = _CONTEXT.set(context)
    try:
        kwargs: dict[str, Any] = {
            "search": search,
            "required_column_count": required_column_count,
            "explicit_row_target": explicit_row_target,
            "search_results_per_query": search_results_per_query,
            "policy": chosen,
        }
        if monotonic is not None:
            kwargs["monotonic"] = monotonic
        value = _RUN_PACING_DISTINCT(list(queries), **kwargs)
    finally:
        _CONTEXT.reset(token)
    receipt = context.get("selection_receipt")
    if receipt is None:
        # No second wave was admitted.  Materialize the same content-free zero
        # receipt without starting a search, fetch, model, or other effect.
        cap = max(1, int(chosen.wave2_fetches))
        receipt = select_production_second_wave(
            context.get("first_wave_page_batches") or [],
            [],
            question=visible_question,
            cap=cap,
            exclude_urls={
                canonical
                for item in context.get("first_wave_requests") or []
                if (canonical := canonicalize_url(str(item.get("url") or "")))
            },
        )["content_free_receipt"]
    output = dict(value)
    output["distinct_coverage_selection_receipt"] = validate_selection_receipt(
        receipt
    )
    return output


def validate_isolation() -> None:
    if (
        parent_retrieval._lead_requests is not _ORIGINAL_LEAD_REQUESTS
        or parent_retrieval.BudgetEquivalentTaskUnionSearchClient
        is not _ORIGINAL_BUDGET_CLIENT
        or pacing._RUN_PARENT_ISOLATED is not _ORIGINAL_PACING_PARENT
        or pacing.run_pacing_aware_two_wave_retrieval
        is not _ORIGINAL_PACING_WRAPPER
        or _RUN_PARENT_DISTINCT.__code__ is not _ORIGINAL_PACING_PARENT.__code__
        or _RUN_PACING_DISTINCT.__code__ is not _ORIGINAL_PACING_WRAPPER.__code__
        or _RUN_PARENT_DISTINCT.__globals__["_lead_requests"]
        is not _distinct_lead_requests
        or _RUN_PARENT_DISTINCT.__globals__["BudgetEquivalentTaskUnionSearchClient"]
        is not _ObservedBudgetEquivalentTaskUnionSearchClient
        or _RUN_PACING_DISTINCT.__globals__["_RUN_PARENT_ISOLATED"]
        is not _RUN_PARENT_DISTINCT
    ):
        raise RuntimeError("V2.50.20 private production binding drifted")


__all__ = [
    "POLICY_ID",
    "run_pacing_distinct_coverage_retrieval",
    "validate_isolation",
]
