"""Production fetch seam for page-self-identified record representation.

This append-only client preserves the complete V2.49.85 search, retry, fetch,
deadline, response-byte, and page-character boundary.  It replaces only the
repository-local isolated helper selected before any effect can occur.  The
helper applies V2.50.49 to the same decoded public page; a page that cannot be
strictly bound is returned as the inherited raw 5,000-character prefix
byte-for-byte.

The runtime-visible input remains the current question plus same-forward
public pages.  No benchmark label, mapping, gold, evaluator, score, reward, or
historical result is available to this component.  Entropy/information gain
is observational only and assigns no signed credit.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .v24980_late_page_bound_projection import (
    MAXIMUM_INPUT_PAGE_CHARACTERS,
    PAGE_CHARACTER_CAP,
)
from .v24981_late_page_bound_fetch import LatePageBoundFetchMixin
from .v24985_robust_late_page_fetch import RobustLatePageBoundSearchClient


POLICY_ID = "v25055_page_self_production_fetch_v1"
ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "scripts/run_v25055_page_self_production_fetch_helper.py"


def _ordinary_helper(path: Path = HELPER) -> Path:
    expected = HELPER.resolve()
    resolved = path.resolve()
    if (
        path.is_symlink()
        or not path.is_file()
        or resolved != expected
        or not resolved.is_relative_to(ROOT)
    ):
        raise ValueError("V2.50.55 helper identity drifted")
    return resolved


class PageSelfProductionSearchClient(RobustLatePageBoundSearchClient):
    """Frozen production search with only the pure projection helper changed."""

    def __init__(
        self,
        *args: Any,
        visible_question: str,
        page_self_fetch_helper: Path = HELPER,
        late_page_fetch_popen: Any = subprocess.Popen,
        **kwargs: Any,
    ) -> None:
        # The parent initializes the complete bounded effect state.  Replacing
        # this ordinary helper path is a local assignment and happens before
        # the constructed client is returned to any caller.
        super().__init__(
            *args,
            visible_question=visible_question,
            late_page_fetch_popen=late_page_fetch_popen,
            **kwargs,
        )
        self._v24981_fetch_helper = _ordinary_helper(page_self_fetch_helper)


def validate_search_class() -> None:
    cls = PageSelfProductionSearchClient
    fetch_owner = next(base for base in cls.__mro__ if "_fetch_url" in base.__dict__)
    if (
        fetch_owner is not LatePageBoundFetchMixin
        or not issubclass(cls, RobustLatePageBoundSearchClient)
        or _ordinary_helper() != HELPER.resolve()
    ):
        raise RuntimeError("V2.50.55 search MRO or helper drifted")


def validate_policy() -> dict[str, Any]:
    value = {
        "policy_id": POLICY_ID,
        "maximum_network_response_bytes_per_fetch": MAXIMUM_INPUT_PAGE_CHARACTERS,
        "parent_page_character_cap": PAGE_CHARACTER_CAP,
        "same_parent_search_retry_fetch_and_hard_deadline": True,
        "same_forward_decoded_page_only": True,
        "strict_binding_failure_is_exact_raw_prefix_handoff": True,
        "additional_query_fetch_model_token_context_wall_or_network_byte_cap": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "entropy_or_information_gain_assigns_signed_credit": False,
        "benchmark_or_evaluator_launch_authorized": False,
    }
    if (
        value["maximum_network_response_bytes_per_fetch"] != 3_000_000
        or value["parent_page_character_cap"] != 5_000
        or value[
            "additional_query_fetch_model_token_context_wall_or_network_byte_cap"
        ]
        is not False
        or value["entropy_or_information_gain_assigns_signed_credit"] is not False
    ):
        raise RuntimeError("V2.50.55 production fetch policy drifted")
    return value


__all__ = [
    "HELPER",
    "POLICY_ID",
    "PageSelfProductionSearchClient",
    "validate_policy",
    "validate_search_class",
]
