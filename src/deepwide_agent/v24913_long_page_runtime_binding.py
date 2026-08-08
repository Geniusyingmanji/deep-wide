"""Static production-child binding for cap-bound observable long-page packing."""

from __future__ import annotations

import copy
from collections.abc import Mapping, Sequence
from types import ModuleType
from typing import Any

from .v24911_long_page_evidence_packer import PackingPolicy
from .v24913_cap_bound_long_page_fetch import (
    CapBoundLongPageSearchClient,
    PAGE_CHARACTER_CAP,
    validate_search_class,
)
from .v24913_observable_long_page_packer import build_observable_packing


POLICY_ID = "v24913_cap_bound_observable_long_page_runtime_binding_v1"
REQUIRED_LIMITS = {
    "wall_seconds": 240,
    "model_calls": 3,
    "search_queries": 4,
    "fetch_targets": 10,
    "evidence_chars": 60_000,
    "page_chars": 12_000,
}
OUTPUT_PAGE_CHARACTER_CAP = 5_000
BLOCK_CHARACTER_CAP = 1_200
MAXIMUM_PAGES = 10
MAXIMUM_VISIBLE_GROUPS = 64
MAXIMUM_QUERY_TERMS = 96


def validate_binding_contract(contract: ModuleType) -> None:
    limits = getattr(contract, "LIMITS", None)
    if (
        not isinstance(limits, Mapping)
        or any(limits.get(name) != expected for name, expected in REQUIRED_LIMITS.items())
        or getattr(contract, "MODEL_SLOT_CAP", None) != 8
        or getattr(contract, "EXECUTOR_CONCURRENCY", None) != 20
        or PAGE_CHARACTER_CAP != REQUIRED_LIMITS["page_chars"]
    ):
        raise ValueError("V2.49.13 production budget or capacity drifted")


def bind_child_algorithm(algorithm: ModuleType, contract: ModuleType) -> None:
    validate_binding_contract(contract)
    validate_search_class()
    assignments = {
        "OUTPUT_ROOT": contract.OUTPUT_ROOT,
        "TASK_ROOT": contract.TASK_ROOT,
        "MODEL_SLOT_DIRECTORY": contract.MODEL_SLOT_DIRECTORY,
        "LIMITS": copy.deepcopy(contract.LIMITS),
        "MODEL": copy.deepcopy(contract.MODEL),
        "SEARCH": copy.deepcopy(contract.SEARCH),
        "TWO_WAVE_POLICY": copy.deepcopy(contract.TWO_WAVE_POLICY),
        "ThinSameResponseCitationTitleBackfillSearchClient": (
            CapBoundLongPageSearchClient
        ),
        "validate_thin_search_class": validate_search_class,
    }
    for name, value in assignments.items():
        setattr(algorithm, name, value)


def project_evidence(
    visible_question: str,
    search_batches: Sequence[Mapping[str, Any]],
    page_batches: Sequence[Mapping[str, Any]],
    limits: Any,
) -> tuple[str, dict[str, Any]]:
    if not isinstance(visible_question, str) or not visible_question.strip():
        raise RuntimeError("V2.49.13 visible question was not bound")
    if (
        int(limits.page_chars) != PAGE_CHARACTER_CAP
        or int(limits.evidence_chars) < REQUIRED_LIMITS["evidence_chars"]
    ):
        raise RuntimeError("V2.49.13 parent evidence budget drifted")
    pages: list[dict[str, Any]] = []
    for batch in page_batches:
        if not isinstance(batch, Mapping):
            continue
        for result in batch.get("results") or []:
            if not isinstance(result, Mapping):
                continue
            pages.append(
                {
                    "title": str(result.get("title", "")),
                    "url": str(result.get("url", "")),
                    "content": str(
                        result.get("raw_content") or result.get("content") or ""
                    ),
                }
            )
    packing = build_observable_packing(
        visible_question,
        pages,
        policy=PackingPolicy(
            input_page_character_cap=PAGE_CHARACTER_CAP,
            output_page_character_cap=OUTPUT_PAGE_CHARACTER_CAP,
            block_character_cap=BLOCK_CHARACTER_CAP,
            total_rendered_character_cap=REQUIRED_LIMITS["evidence_chars"],
            maximum_pages=MAXIMUM_PAGES,
            maximum_visible_groups=MAXIMUM_VISIBLE_GROUPS,
            maximum_query_terms=MAXIMUM_QUERY_TERMS,
        ),
    )
    if (
        packing["candidate_requirement_coverage_not_less_than_prefix_baseline"]
        is not True
        or packing["short_page_content_byte_identity_preserved"] is not True
        or packing["orphan_selected_table_continuation_block_count"] != 0
        or packing["entropy_or_information_gain_assigns_credit"] is not False
        or packing[
            "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
        ]
        is not False
        or search_batches
        and packing["search_provider_narrative_or_snippet_forwarded"] is not False
    ):
        raise RuntimeError("V2.49.13 evidence packing invariant drifted")
    return str(packing["projection"]), dict(packing["content_free_receipt"])


__all__ = [
    "POLICY_ID",
    "REQUIRED_LIMITS",
    "bind_child_algorithm",
    "project_evidence",
    "validate_binding_contract",
]
