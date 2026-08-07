#!/usr/bin/env python3
"""Run one V2.48.40 task with the frozen V2.48.39 projector."""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24257_score_first_runtime as runtime  # noqa: E402
from deepwide_agent import v24259_deterministic_table_normalizer as normalizer  # noqa: E402
from deepwide_agent import v24840_structure_preserving_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24839_structure_preserving_projector import (  # noqa: E402
    ProjectionPolicy,
    build_projection,
)
from scripts import run_v24834_coverage_margin_exact220_task as parent  # noqa: E402


_VISIBLE_QUESTION: str | None = None


def _fetched_pages(
    page_batches: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
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
    return pages


def structure_preserving_evidence_projection(
    search_batches: Sequence[Mapping[str, Any]],
    page_batches: Sequence[Mapping[str, Any]],
    limits: Any,
) -> str:
    """Project visible-question-aligned fetched pages; search narrative is inactive."""

    if _VISIBLE_QUESTION is None or not _VISIBLE_QUESTION.strip():
        raise RuntimeError("V2.48.40 visible question was not bound")
    if int(limits.evidence_chars) < contract.PROJECTOR_POLICY["total_character_cap"]:
        raise RuntimeError("V2.48.40 parent evidence cap is below projector cap")
    projection = build_projection(
        _VISIBLE_QUESTION,
        _fetched_pages(page_batches),
        policy=ProjectionPolicy(
            total_character_cap=contract.PROJECTOR_POLICY["total_character_cap"],
            maximum_page_chars=contract.PROJECTOR_POLICY["maximum_page_chars"],
            block_character_cap=contract.PROJECTOR_POLICY["block_character_cap"],
            maximum_visible_groups=contract.PROJECTOR_POLICY["maximum_visible_groups"],
            maximum_query_terms=contract.PROJECTOR_POLICY["maximum_query_terms"],
        ),
    )
    if search_batches and projection["provider_narrative_or_search_snippet_forwarded"] is not False:
        raise RuntimeError("V2.48.40 search narrative entered projection")
    if projection["missed_supported_visible_requirement_group_count"] != 0:
        raise RuntimeError("V2.48.40 supported visible requirement was dropped")
    return str(projection["projection"])


def configure() -> None:
    parent.configure()
    parent.algorithm.OUTPUT_ROOT = contract.OUTPUT_ROOT
    parent.algorithm.TASK_ROOT = contract.TASK_ROOT
    parent.algorithm.MODEL_SLOT_DIRECTORY = contract.MODEL_SLOT_DIRECTORY
    parent.algorithm.LIMITS = contract.LIMITS
    parent.algorithm.MODEL = contract.MODEL
    parent.algorithm.SEARCH = contract.SEARCH
    parent.algorithm.TWO_WAVE_POLICY = contract.TWO_WAVE_POLICY
    runtime._evidence_projection = structure_preserving_evidence_projection
    normalizer.run_score_first_task.__globals__["_evidence_projection"] = (
        structure_preserving_evidence_projection
    )


def main() -> None:
    global _VISIBLE_QUESTION
    configure()
    inherited_read = parent.algorithm._read

    def visible_read(path: Path) -> dict[str, Any]:
        global _VISIBLE_QUESTION
        value = inherited_read(path)
        if path.name == "visible_task.json":
            if set(value) != {"opaque_id", "question"}:
                raise RuntimeError("V2.48.40 child runtime input drifted")
            _VISIBLE_QUESTION = str(value["question"])
        return value

    parent.algorithm._read = visible_read
    try:
        parent.algorithm.main()
    finally:
        parent.algorithm._read = inherited_read
        _VISIBLE_QUESTION = None


if __name__ == "__main__":
    main()
