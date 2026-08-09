"""Hard-deadline fetch seam for V2.50.14 multi-identity projection.

The frozen V2.49.81/V2.49.85 network, byte, page, process, retry, and wall
limits remain unchanged.  Only the ordinary isolated helper invoked after
generic decode and before the inherited 5,000-character boundary is replaced.
The current visible question is supplied in memory by the caller and is never
read from a file, environment variable, benchmark label, gold, or evaluator.
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
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25016_hard_deadline_multi_identity_detail_fetch_v1"
ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/run_v25016_multi_identity_detail_fetch_helper.py"


def _ordinary_helper(path: Path = HELPER) -> Path:
    expected = HELPER.resolve()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not path.is_file()
        or resolved != expected
        or not resolved.is_relative_to(ROOT)
    ):
        raise ValueError("V2.50.16 helper identity drifted")
    return resolved


class MultiIdentityDetailSearchClient(RobustLatePageBoundSearchClient):
    """Frozen robust search with only the isolated helper identity replaced."""

    def __init__(
        self,
        *args: Any,
        visible_question: str,
        multi_identity_fetch_helper: Path = HELPER,
        late_page_fetch_popen: Any = subprocess.Popen,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            *args,
            visible_question=visible_question,
            late_page_fetch_popen=late_page_fetch_popen,
            **kwargs,
        )
        self._v24981_fetch_helper = _ordinary_helper(multi_identity_fetch_helper)


def validate_search_class() -> None:
    validate_thin_search_class()
    cls = MultiIdentityDetailSearchClient
    fetch_owner = next(base for base in cls.__mro__ if "_fetch_url" in base.__dict__)
    if (
        fetch_owner is not LatePageBoundFetchMixin
        or not issubclass(cls, RobustLatePageBoundSearchClient)
        or not issubclass(cls, LatePageBoundSearchClient)
        or not issubclass(cls, ThinSameResponseCitationTitleBackfillSearchClient)
        or _ordinary_helper() != HELPER.resolve()
    ):
        raise RuntimeError("V2.50.16 search MRO or helper drifted")


__all__ = [
    "HELPER",
    "MultiIdentityDetailSearchClient",
    "POLICY_ID",
    "validate_search_class",
]
