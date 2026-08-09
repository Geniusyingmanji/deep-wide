"""Hard-deadline fetch seam for the V2.49.84 robust projection.

The network, byte, page, process, and wall limits remain those of V2.49.81.
Only the isolated pure projector invoked after generic decode/HTML extraction
is replaced.  The visible question is still supplied by the current caller;
it is never read from a file, environment variable, or benchmark metadata.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .v24630_thin_backfill_search import (
    ThinSameResponseCitationTitleBackfillSearchClient,
    validate_thin_search_class,
)
from .v24981_late_page_bound_fetch import LatePageBoundFetchMixin
from .v24981_late_page_bound_fetch import LatePageBoundSearchClient


POLICY_ID = "v24985_hard_deadline_robust_late_page_fetch_v1"
ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/run_v24985_robust_late_page_fetch_helper.py"


def _ordinary_helper(path: Path = HELPER) -> Path:
    expected = HELPER.resolve()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not path.is_file()
        or resolved != expected
        or not resolved.is_relative_to(ROOT)
    ):
        raise ValueError("V2.49.85 helper identity drifted")
    return resolved


class RobustLatePageBoundFetchMixin(LatePageBoundFetchMixin):
    """Reuse the frozen effect boundary with one append-only helper identity."""

    def __init__(
        self,
        *args: Any,
        visible_question: str,
        robust_late_page_fetch_helper: Path = HELPER,
        late_page_fetch_popen: Any = subprocess.Popen,
        **kwargs: Any,
    ) -> None:
        # V2.49.81 validates and initializes the complete bounded effect state.
        # Its helper path is then replaced before any effect can occur.
        super().__init__(
            *args,
            visible_question=visible_question,
            late_page_fetch_popen=late_page_fetch_popen,
            **kwargs,
        )
        self._v24981_fetch_helper = _ordinary_helper(
            robust_late_page_fetch_helper
        )


class RobustLatePageBoundSearchClient(LatePageBoundSearchClient):
    """Frozen keyless search with the robust late-page projector seam.

    Inheriting the complete V2.49.81 client also preserves the production
    runtime's strict client-type boundary.  The helper identity is replaced in
    ``__init__`` before the object is observable by a caller and before any
    search or fetch effect can occur.
    """

    def __init__(
        self,
        *args: Any,
        visible_question: str,
        robust_late_page_fetch_helper: Path = HELPER,
        late_page_fetch_popen: Any = subprocess.Popen,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            *args,
            visible_question=visible_question,
            late_page_fetch_popen=late_page_fetch_popen,
            **kwargs,
        )
        self._v24981_fetch_helper = _ordinary_helper(
            robust_late_page_fetch_helper
        )


def validate_search_class() -> None:
    validate_thin_search_class()
    cls = RobustLatePageBoundSearchClient
    fetch_owner = next(base for base in cls.__mro__ if "_fetch_url" in base.__dict__)
    if (
        fetch_owner is not LatePageBoundFetchMixin
        or not issubclass(cls, LatePageBoundSearchClient)
        or not issubclass(cls, ThinSameResponseCitationTitleBackfillSearchClient)
        or _ordinary_helper() != HELPER.resolve()
    ):
        raise RuntimeError("V2.49.85 search MRO or helper drifted")


__all__ = [
    "HELPER",
    "POLICY_ID",
    "RobustLatePageBoundFetchMixin",
    "RobustLatePageBoundSearchClient",
    "validate_search_class",
]
