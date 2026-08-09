#!/usr/bin/env python3
"""Run one V2.49.48 task with injective schema-signature projection."""

from __future__ import annotations

import copy
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
from deepwide_agent import v24945_injective_schema_signature_ledger as projector  # noqa: E402
from deepwide_agent import v24948_schema_signature_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24907_keyless_fixed_budget_binding import bind_child_algorithm  # noqa: E402
from scripts import run_v24635_exact220_task as algorithm  # noqa: E402


_VISIBLE_QUESTION: str | None = None
_LAST_RECEIPT: dict[str, Any] | None = None


def _fetched_pages(page_batches: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "title": str(result.get("title", "")),
            "url": str(result.get("url", "")),
            "content": str(result.get("raw_content") or result.get("content") or ""),
        }
        for batch in page_batches
        if isinstance(batch, Mapping)
        for result in (batch.get("results") or [])
        if isinstance(result, Mapping)
    ]


def validate_runtime_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = copy.deepcopy(dict(value))
    unsigned = dict(copied)
    seal = unsigned.pop("receipt_payload_sha256", None)
    candidate = projector.validate_receipt(copied.get("candidate_receipt") or {})
    if (
        copied.get("artifact_version") != 1
        or copied.get("role") != "v24948_content_free_schema_signature_projection_receipt"
        or candidate != copied.get("candidate_receipt")
        or copied.get("contains_question_query_url_host_page_projection_prediction_or_hash") is not False
        or copied.get("mapping_gold_category_question_type_split_evaluator_score_reward_read") is not False
        or copied.get("entropy_or_information_gain_assigns_credit") is not False
        or seal != contract.payload_sha256(unsigned)
    ):
        raise ValueError("V2.49.48 runtime receipt drifted")
    return copied


def schema_signature_evidence_projection(search_batches, page_batches, limits) -> str:
    del search_batches
    if _VISIBLE_QUESTION is None or not _VISIBLE_QUESTION.strip():
        raise RuntimeError("V2.49.48 visible question absent")
    if int(limits.page_chars) != 5_000 or int(limits.evidence_chars) < 30_000:
        raise RuntimeError("V2.49.48 evidence cap drifted")
    pages = _fetched_pages(page_batches)
    value = projector.build_projection(_VISIBLE_QUESTION, pages)
    projector.validate_projection(
        value, question=_VISIBLE_QUESTION, pages=pages, replay=False
    )
    global _LAST_RECEIPT
    _LAST_RECEIPT = {
        "artifact_version": 1,
        "role": "v24948_content_free_schema_signature_projection_receipt",
        "candidate_receipt": copy.deepcopy(value["content_free_receipt"]),
        "contains_question_query_url_host_page_projection_prediction_or_hash": False,
        "mapping_gold_category_question_type_split_evaluator_score_reward_read": False,
        "entropy_or_information_gain_assigns_credit": False,
    }
    _LAST_RECEIPT["receipt_payload_sha256"] = contract.payload_sha256(_LAST_RECEIPT)
    validate_runtime_receipt(_LAST_RECEIPT)
    return str(value["projection"])


def configure() -> None:
    bind_child_algorithm(algorithm, contract)
    runtime._evidence_projection = schema_signature_evidence_projection
    normalizer.run_score_first_task.__globals__["_evidence_projection"] = schema_signature_evidence_projection


def _result_directory() -> Path:
    try:
        result = Path(sys.argv[sys.argv.index("--result") + 1]).resolve(strict=False)
    except (IndexError, ValueError):
        raise RuntimeError("V2.49.48 result argument absent") from None
    root = (ROOT / contract.TASK_ROOT).resolve()
    if result.name != "result.json" or not result.parent.is_relative_to(root):
        raise RuntimeError("V2.49.48 result path escaped")
    return result.parent


def main() -> None:
    global _VISIBLE_QUESTION, _LAST_RECEIPT
    configure()
    directory = _result_directory()
    inherited = algorithm._read

    def visible_read(path: Path):
        global _VISIBLE_QUESTION
        value = inherited(path)
        if path.name == "visible_task.json":
            if set(value) != {"opaque_id", "question"}:
                raise RuntimeError("V2.49.48 child input drifted")
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
            algorithm._read = inherited
            _VISIBLE_QUESTION = None
            _LAST_RECEIPT = None


if __name__ == "__main__":
    main()
