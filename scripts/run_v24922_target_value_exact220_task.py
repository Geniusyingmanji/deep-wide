#!/usr/bin/env python3
"""Run one V2.49.22 task with pacing-aware retrieval and target-value projection."""

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
from deepwide_agent import v24922_target_value_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24921_target_value_coverage_projector import (  # noqa: E402
    build_projection,
    validate_receipt,
)
from scripts import run_v24857_pacing_aware_exact220_task as parent  # noqa: E402


_VISIBLE_QUESTION: str | None = None
_LAST_PROJECTION_RECEIPT: dict[str, Any] | None = None


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


def target_value_evidence_projection(
    search_batches: Sequence[Mapping[str, Any]],
    page_batches: Sequence[Mapping[str, Any]],
    limits: Any,
) -> str:
    if _VISIBLE_QUESTION is None or not _VISIBLE_QUESTION.strip():
        raise RuntimeError("V2.49.22 visible question was not bound")
    if int(limits.page_chars) != 5_000 or int(limits.evidence_chars) < 30_000:
        raise RuntimeError("V2.49.22 parent evidence cap drifted")
    global _LAST_PROJECTION_RECEIPT
    projection = build_projection(_VISIBLE_QUESTION, _fetched_pages(page_batches))
    receipt = validate_receipt(projection["content_free_receipt"])
    _LAST_PROJECTION_RECEIPT = receipt
    if (
        search_batches
        and projection[
            "benchmark_label_mapping_gold_evaluator_score_reward_or_historical_result_read"
        ]
        is not False
    ):
        raise RuntimeError("V2.49.22 search narrative entered projection")
    if receipt["orphan_selected_table_continuation_block_count"] != 0:
        raise RuntimeError("V2.49.22 orphan table continuation entered projection")
    return str(projection["projection"])


def configure(argv: list[str] | None = None) -> Path:
    parent.contract = contract
    directory = parent.configure(argv)
    runtime._evidence_projection = target_value_evidence_projection
    normalizer.run_score_first_task.__globals__["_evidence_projection"] = (
        target_value_evidence_projection
    )
    return directory


def main() -> None:
    global _VISIBLE_QUESTION, _LAST_PROJECTION_RECEIPT
    parent.validate_isolation()
    directory = configure()
    inherited_read = parent.algorithm._read

    def visible_read(path: Path) -> dict[str, Any]:
        global _VISIBLE_QUESTION
        value = inherited_read(path)
        if path.name == "visible_task.json":
            if set(value) != {"opaque_id", "question"}:
                raise RuntimeError("V2.49.22 child runtime input drifted")
            _VISIBLE_QUESTION = str(value["question"])
        return value

    parent.algorithm._read = visible_read
    try:
        parent.algorithm.main()
    finally:
        try:
            if _LAST_PROJECTION_RECEIPT is not None:
                receipt_path = directory / contract.PROJECTION_RECEIPT_NAME
                if receipt_path.exists() or receipt_path.is_symlink():
                    raise FileExistsError(receipt_path)
                parent.algorithm._atomic_new(receipt_path, _LAST_PROJECTION_RECEIPT)
        finally:
            parent.algorithm._read = inherited_read
            _VISIBLE_QUESTION = None
            _LAST_PROJECTION_RECEIPT = None


if __name__ == "__main__":
    main()
