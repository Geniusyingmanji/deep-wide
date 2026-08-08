"""Keyless fixed-budget same-task coverage-revision runtime.

This append-only successor removes the Tavily pacing-receipt dependency from
V2.48.62 while retaining its isolated parent chain and same-forward page
capture.  The frozen V2.47.99 no-entropy fixed-full-budget policy is mandatory:
four logical queries and ten fetches remain hard caps, while actual fetches are
the number of discovered source leads and may be lower than the cap.

The runtime accepts only the visible task and already-constructed bounded
model/search clients.  It has no benchmark mapping, label, gold, evaluator,
score, credential, environment, filesystem, or process capability and grants
no benchmark launch authority.
"""

from __future__ import annotations

import copy
import dataclasses
import types
from collections.abc import Mapping, Sequence
from typing import Any

from . import v24273_two_wave_task_runtime as retrieval_runtime
from . import v24318_deadline_conservation_runtime as conservation_runtime
from . import v24319_runner_integration as runner_integration
from . import v24630_exact220_task_integration as task_integration
from .clients import canonicalize_url
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
)
from .v24799_fixed_full_budget_control import (
    POLICY_VALUES,
    fixed_full_budget_policy,
)
from .v24859_full_evidence_coverage_revision import (
    EvidencePage,
    prepare_evidence_pages,
)
from .v24860_coverage_revision_integration import run_coverage_revision
from .v24861_coverage_revision_exact_task import (
    IntegratedCoverageRevisionTaskOutcome,
    integrate_parent_outcome,
)


POLICY_ID = "v24873_keyless_fixed_budget_same_task_coverage_runtime_v1"
PAGE_ATTRIBUTE = "_v24873_same_forward_evidence_pages"


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.48.73 frozen parent unexpectedly has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__,
        namespace,
        name=f"v24873_isolated_{original.__name__}",
        argdefs=original.__defaults__,
        closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    value.__annotations__ = copy.deepcopy(original.__annotations__)
    return value


_FIXED_SEARCH_MANY = _isolated_function(
    retrieval_runtime.TwoWaveCachingSearchClient.search_many,
    run_two_wave_retrieval=(
        retrieval_runtime.TwoWaveCachingSearchClient.search_many.__globals__[
            "run_two_wave_retrieval"
        ]
    ),
)


class KeylessFixedCoverageCachingSearchClient(
    retrieval_runtime.TwoWaveCachingSearchClient
):
    """Capture only the successfully fetched pages selected in this task."""

    def search_many(
        self, queries: Sequence[str], **kwargs: Any
    ) -> list[dict[str, Any]]:
        setattr(self.inner, PAGE_ATTRIBUTE, ())
        output = _FIXED_SEARCH_MANY(self, queries, **kwargs)
        raw_pages: list[EvidencePage] = []
        ordinal = 0
        for batch in output:
            if not isinstance(batch, Mapping):
                continue
            for result in batch.get("results") or []:
                if not isinstance(result, Mapping):
                    continue
                url = canonicalize_url(str(result.get("url") or ""))
                cached = self._page_cache.get(url)
                if not url or not isinstance(cached, Mapping):
                    continue
                content = str(
                    cached.get("raw_content") or cached.get("content") or ""
                )
                if not content:
                    continue
                ordinal += 1
                raw_pages.append(
                    EvidencePage(
                        evidence_id=f"E{ordinal:04d}",
                        url=url,
                        content=content,
                        fetch_integrity=True,
                    )
                )
        try:
            pages = prepare_evidence_pages(raw_pages)
        except (TypeError, ValueError):
            pages = ()
        setattr(self.inner, PAGE_ATTRIBUTE, pages)
        return output


_ISOLATED_RUN_PARENT = _isolated_function(
    conservation_runtime._run_parent,
    TwoWaveCachingSearchClient=KeylessFixedCoverageCachingSearchClient,
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


def validate_isolation() -> None:
    inherited = retrieval_runtime.TwoWaveCachingSearchClient.search_many
    if (
        inherited is _FIXED_SEARCH_MANY
        or conservation_runtime._run_parent is _ISOLATED_RUN_PARENT
        or runner_integration.run_v24319_task is _ISOLATED_RUN_V24319_TASK
        or task_integration.run_v24630_task is _PARENT_RUN_TASK
        or _FIXED_SEARCH_MANY.__code__ is not inherited.__code__
        or _FIXED_SEARCH_MANY.__globals__["run_two_wave_retrieval"]
        is not inherited.__globals__["run_two_wave_retrieval"]
    ):
        raise RuntimeError("V2.48.73 isolated integration binding drifted")


def run_v24873_task(
    task: Mapping[str, Any],
    *,
    arm: str,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: ThinSameResponseCitationTitleBackfillSearchClient,
    limits: ScoreFirstLimits,
    monotonic: Any,
    progress: Any = None,
) -> IntegratedCoverageRevisionTaskOutcome:
    visible = validate_visible_task(task)
    if arm != "baseline":
        raise ValueError("V2.48.73 requires the inherited baseline parent arm")
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.48.73 requires the inherited global model limiter")
    if not isinstance(search, ThinSameResponseCitationTitleBackfillSearchClient):
        raise ValueError("V2.48.73 requires the inherited keyless thin search")
    if (
        limits.search_queries != 4
        or limits.fetch_targets != 10
        or limits.model_calls != 3
    ):
        raise ValueError("V2.48.73 inherited hard budget drifted")
    policy = fixed_full_budget_policy()
    if dataclasses.asdict(policy) != POLICY_VALUES:
        raise RuntimeError("V2.48.73 fixed no-entropy policy drifted")
    validate_isolation()
    parent = _PARENT_RUN_TASK(
        visible,
        arm=arm,
        model=model,
        search=search,
        limits=limits,
        two_wave_policy=policy,
        monotonic=monotonic,
        progress=progress,
    )
    pages = getattr(search, PAGE_ATTRIBUTE, ())
    if not isinstance(pages, tuple) or any(
        not isinstance(page, EvidencePage) for page in pages
    ):
        pages = ()
    revision = run_coverage_revision(
        visible,
        parent_result=parent.result,
        parent_model_slot_receipt=parent.model_slot_receipt,
        model=model,
        pages=pages,
        limits=limits,
        monotonic=monotonic,
    )
    return integrate_parent_outcome(parent, revision)


__all__ = [
    "KeylessFixedCoverageCachingSearchClient",
    "PAGE_ATTRIBUTE",
    "POLICY_ID",
    "run_v24873_task",
    "validate_isolation",
]
