"""Production-shaped runtime binding for V2.49.20 projection totality."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import ModuleType
from typing import Any

from .v24911_long_page_evidence_packer import PackingPolicy
from .v24916_prefix_total_runtime_binding import (
    bind_child_algorithm,
    validate_binding_contract,
)
from .v24920_projection_totality import build_projection_totality


POLICY_ID = "v24920_projection_totality_runtime_binding_v1"


def project_evidence(
    visible_question: str,
    search_batches: Sequence[Mapping[str, Any]],
    page_batches: Sequence[Mapping[str, Any]],
    limits: Any,
) -> tuple[str, dict[str, Any]]:
    if not isinstance(visible_question, str) or not visible_question.strip():
        raise RuntimeError("V2.49.20 visible question was not bound")
    if int(limits.page_chars) != 12_000 or int(limits.evidence_chars) != 60_000:
        raise RuntimeError("V2.49.20 parent evidence budget drifted")
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
    packing = build_projection_totality(
        visible_question,
        pages,
        policy=PackingPolicy(
            input_page_character_cap=12_000,
            output_page_character_cap=5_000,
            block_character_cap=1_200,
            total_rendered_character_cap=60_000,
            maximum_pages=10,
            maximum_visible_groups=64,
            maximum_query_terms=96,
        ),
    )
    if (
        search_batches
        and packing["search_provider_narrative_or_snippet_forwarded"] is not False
    ):
        raise RuntimeError("V2.49.20 search narrative entered synthesis")
    return str(packing["projection"]), dict(packing["content_free_receipt"])


def bind_child_algorithm_total(algorithm: ModuleType, contract: ModuleType) -> None:
    validate_binding_contract(contract)
    bind_child_algorithm(algorithm, contract)


__all__ = [
    "POLICY_ID",
    "bind_child_algorithm_total",
    "project_evidence",
]
