#!/usr/bin/env python3
"""Run one V2.48.37 task with the frozen V2.48.36 projector."""

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
from deepwide_agent import v24837_information_bottleneck_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24836_information_bottleneck_projector import (  # noqa: E402
    ProjectionPolicy,
    build_projection,
)
from scripts import run_v24834_coverage_margin_exact220_task as parent  # noqa: E402


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


def information_bottleneck_evidence_projection(
    search_batches: Sequence[Mapping[str, Any]],
    page_batches: Sequence[Mapping[str, Any]],
    limits: Any,
) -> str:
    """Project fetched pages only; search narrative remains inactive."""

    if int(limits.evidence_chars) < contract.PROJECTOR_POLICY["total_character_cap"]:
        raise RuntimeError("V2.48.37 parent evidence cap is below projector cap")
    projection = build_projection(
        _fetched_pages(page_batches),
        policy=ProjectionPolicy(
            total_character_cap=contract.PROJECTOR_POLICY["total_character_cap"],
            minimum_page_prefix_chars=contract.PROJECTOR_POLICY[
                "minimum_page_prefix_chars"
            ],
            round_robin_chunk_chars=contract.PROJECTOR_POLICY[
                "round_robin_chunk_chars"
            ],
            maximum_page_chars=contract.PROJECTOR_POLICY["maximum_page_chars"],
        ),
    )
    if search_batches and projection["query_or_provider_narrative_forwarded"] is not False:
        raise RuntimeError("V2.48.37 search narrative entered projection")
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
    runtime._evidence_projection = information_bottleneck_evidence_projection
    normalizer.run_score_first_task.__globals__["_evidence_projection"] = (
        information_bottleneck_evidence_projection
    )


def main() -> None:
    configure()
    parent.algorithm.main()


if __name__ == "__main__":
    main()
