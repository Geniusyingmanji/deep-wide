"""Same-task production seam for bounded coverage revision.

The runtime clones the frozen V2.48.57 parent function chain with isolated
globals.  Its caching-search subclass exports only the successfully fetched
page prefix to the current inner search instance; no module-global task state
is used.  After the parent exact-task outcome is independently valid, the
same model limiter may spend its unused third logical call through V2.48.60.

This module grants no benchmark launch or evaluator authority.
"""

from __future__ import annotations

import copy
import types
from collections.abc import Mapping, Sequence
from typing import Any

from .clients import canonicalize_url
from . import v24273_two_wave_task_runtime as retrieval_runtime
from . import v24318_deadline_conservation_runtime as conservation_runtime
from . import v24319_runner_integration as runner_integration
from . import v24630_exact220_task_integration as task_integration
from .v24257_score_first_runtime import ScoreFirstLimits, validate_visible_task
from .v24272_two_wave_entropy_voc import TwoWavePolicy
from .v24312_deadline_reliability import DeadlineAwareGlobalModelSlotLimiter
from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
)
from .v24856_pacing_aware_admission import (
    run_pacing_aware_two_wave_retrieval,
    validate_receipt as validate_pacing_receipt,
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


POLICY_ID = "v24862_same_task_pacing_coverage_revision_runtime_v1"
PAGE_ATTRIBUTE = "_v24862_same_forward_evidence_pages"


def _isolated_function(original: Any, **bindings: Any) -> Any:
    if original.__closure__:
        raise RuntimeError("V2.48.62 frozen parent unexpectedly has closure state")
    namespace = dict(original.__globals__)
    namespace.update(bindings)
    value = types.FunctionType(
        original.__code__,
        namespace,
        name=f"v24862_isolated_{original.__name__}",
        argdefs=original.__defaults__,
        closure=None,
    )
    value.__kwdefaults__ = copy.deepcopy(original.__kwdefaults__)
    return value


def _pacing_retrieval(*args: Any, **kwargs: Any) -> dict[str, Any]:
    search = kwargs.get("search")
    if search is None and len(args) >= 2:
        search = args[1]
    if search is None:
        raise TypeError("V2.48.62 pacing search binding is absent")
    value = run_pacing_aware_two_wave_retrieval(*args, **kwargs)
    receipt = validate_pacing_receipt(value["pacing_admission_receipt"])
    setattr(search, "_v24862_pacing_admission_receipt", receipt)
    output = copy.deepcopy(value)
    output.pop("pacing_admission_receipt", None)
    return output


_PACING_SEARCH_MANY = _isolated_function(
    retrieval_runtime.TwoWaveCachingSearchClient.search_many,
    run_two_wave_retrieval=_pacing_retrieval,
)


class SameTaskCoverageCachingSearchClient(
    retrieval_runtime.TwoWaveCachingSearchClient
):
    """Pacing-aware cache that exposes only this task's fetched lead prefix."""

    def search_many(
        self, queries: Sequence[str], **kwargs: Any
    ) -> list[dict[str, Any]]:
        setattr(self.inner, PAGE_ATTRIBUTE, ())
        output = _PACING_SEARCH_MANY(self, queries, **kwargs)
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
    TwoWaveCachingSearchClient=SameTaskCoverageCachingSearchClient,
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
    if (
        retrieval_runtime.TwoWaveCachingSearchClient.search_many
        is _PACING_SEARCH_MANY
        or conservation_runtime._run_parent is _ISOLATED_RUN_PARENT
        or runner_integration.run_v24319_task is _ISOLATED_RUN_V24319_TASK
        or task_integration.run_v24630_task is _PARENT_RUN_TASK
        or _PACING_SEARCH_MANY.__globals__["run_two_wave_retrieval"]
        is not _pacing_retrieval
        or retrieval_runtime.TwoWaveCachingSearchClient.search_many.__globals__[
            "run_two_wave_retrieval"
        ]
        is _pacing_retrieval
    ):
        raise RuntimeError("V2.48.62 isolated integration binding drifted")


def run_v24862_task(
    task: Mapping[str, Any],
    *,
    arm: str,
    model: DeadlineAwareGlobalModelSlotLimiter,
    search: ThinSameResponseCitationTitleBackfillSearchClient,
    limits: ScoreFirstLimits,
    two_wave_policy: TwoWavePolicy,
    monotonic: Any,
    progress: Any = None,
) -> IntegratedCoverageRevisionTaskOutcome:
    visible = validate_visible_task(task)
    if arm != "baseline":
        raise ValueError("V2.48.62 requires the inherited baseline parent arm")
    if not isinstance(model, DeadlineAwareGlobalModelSlotLimiter):
        raise ValueError("V2.48.62 requires the inherited global model limiter")
    if not isinstance(search, ThinSameResponseCitationTitleBackfillSearchClient):
        raise ValueError("V2.48.62 requires the inherited thin search client")
    validate_isolation()
    parent = _PARENT_RUN_TASK(
        visible,
        arm=arm,
        model=model,
        search=search,
        limits=limits,
        two_wave_policy=two_wave_policy,
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
    "PAGE_ATTRIBUTE",
    "POLICY_ID",
    "SameTaskCoverageCachingSearchClient",
    "run_v24862_task",
    "validate_isolation",
]
