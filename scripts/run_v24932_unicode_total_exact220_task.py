#!/usr/bin/env python3
"""Run one V2.49.32 task with Unicode-total evidence projection."""

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
from deepwide_agent import v24932_unicode_total_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24907_keyless_fixed_budget_binding import bind_child_algorithm  # noqa: E402
from deepwide_agent.v24928_unicode_total_visible_row_compactor import (  # noqa: E402
    build_projection,
    validate_projection,
)
from scripts import run_v24635_exact220_task as algorithm  # noqa: E402


_VISIBLE_QUESTION: str | None = None
_LAST_RECEIPT: dict[str, Any] | None = None


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


def unicode_total_evidence_projection(
    search_batches: Sequence[Mapping[str, Any]],
    page_batches: Sequence[Mapping[str, Any]],
    limits: Any,
) -> str:
    del search_batches
    if _VISIBLE_QUESTION is None or not _VISIBLE_QUESTION.strip():
        raise RuntimeError("V2.49.32 visible question was not bound")
    if int(limits.page_chars) != 5_000 or int(limits.evidence_chars) < 30_000:
        raise RuntimeError("V2.49.32 evidence cap drifted")
    pages = _fetched_pages(page_batches)
    projection = build_projection(_VISIBLE_QUESTION, pages)
    validate_projection(
        projection,
        question=_VISIBLE_QUESTION,
        pages=pages,
        replay=False,
    )
    global _LAST_RECEIPT
    _LAST_RECEIPT = {
        "artifact_version": 1,
        "role": "v24932_content_free_unicode_total_projection_receipt",
        "projection_receipt": projection["projection_receipt"],
        "compaction_receipt": projection["compaction_receipt"],
        "contains_question_query_url_host_page_projection_prediction_or_hash": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "entropy_or_information_gain_assigns_credit": False,
    }
    _LAST_RECEIPT["receipt_payload_sha256"] = contract.payload_sha256(_LAST_RECEIPT)
    return str(projection["projection"])


def configure() -> None:
    bind_child_algorithm(algorithm, contract)
    runtime._evidence_projection = unicode_total_evidence_projection
    normalizer.run_score_first_task.__globals__["_evidence_projection"] = (
        unicode_total_evidence_projection
    )


def _result_directory() -> Path:
    try:
        result = Path(sys.argv[sys.argv.index("--result") + 1]).resolve(strict=False)
    except (IndexError, ValueError):
        raise RuntimeError("V2.49.32 child result argument is absent") from None
    root = (ROOT / contract.TASK_ROOT).resolve()
    if result.name != "result.json" or not result.parent.is_relative_to(root):
        raise RuntimeError("V2.49.32 child result path escaped task root")
    return result.parent


def main() -> None:
    global _VISIBLE_QUESTION, _LAST_RECEIPT
    configure()
    directory = _result_directory()
    inherited_read = algorithm._read

    def visible_read(path: Path) -> dict[str, Any]:
        global _VISIBLE_QUESTION
        value = inherited_read(path)
        if path.name == "visible_task.json":
            if set(value) != {"opaque_id", "question"}:
                raise RuntimeError("V2.49.32 child runtime input drifted")
            _VISIBLE_QUESTION = str(value["question"])
        return value

    algorithm._read = visible_read
    try:
        algorithm.main()
    finally:
        try:
            if _LAST_RECEIPT is not None:
                path = directory / contract.PROJECTION_RECEIPT_NAME
                if path.exists() or path.is_symlink():
                    raise FileExistsError(path)
                algorithm._atomic_new(path, _LAST_RECEIPT)
        finally:
            algorithm._read = inherited_read
            _VISIBLE_QUESTION = None
            _LAST_RECEIPT = None


if __name__ == "__main__":
    main()
