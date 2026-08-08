#!/usr/bin/env python3
"""Production-shaped child for prefix-total long-page packing."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24257_score_first_runtime as runtime  # noqa: E402
from deepwide_agent import v24259_deterministic_table_normalizer as normalizer  # noqa: E402
from deepwide_agent.v24916_prefix_total_runtime_binding import (  # noqa: E402
    bind_child_algorithm,
    project_evidence,
)
from scripts import run_v24635_exact220_task as algorithm  # noqa: E402


PROJECTION_RECEIPT_NAME = "projection_receipt.json"
_CONTRACT: ModuleType | None = None
_VISIBLE_QUESTION: str | None = None
_LAST_PROJECTION_RECEIPT: dict[str, Any] | None = None


def configure(contract: ModuleType) -> None:
    global _CONTRACT
    bind_child_algorithm(algorithm, contract)
    _CONTRACT = contract

    def projection(search_batches: Any, page_batches: Any, limits: Any) -> str:
        global _LAST_PROJECTION_RECEIPT
        if _VISIBLE_QUESTION is None:
            raise RuntimeError("V2.49.16 visible question was not bound")
        evidence, receipt = project_evidence(
            _VISIBLE_QUESTION, search_batches, page_batches, limits
        )
        _LAST_PROJECTION_RECEIPT = receipt
        return evidence

    runtime._evidence_projection = projection
    normalizer.run_score_first_task.__globals__["_evidence_projection"] = projection


def main() -> None:
    global _VISIBLE_QUESTION, _LAST_PROJECTION_RECEIPT
    if _CONTRACT is None:
        raise RuntimeError("V2.49.16 frozen successor contract was not injected")
    inherited_read = algorithm._read

    def visible_read(path: Path) -> dict[str, Any]:
        global _VISIBLE_QUESTION
        value = inherited_read(path)
        if path.name == "visible_task.json":
            if set(value) != {"opaque_id", "question"}:
                raise RuntimeError("V2.49.16 child runtime input drifted")
            _VISIBLE_QUESTION = str(value["question"])
        return value

    algorithm._read = visible_read
    try:
        algorithm.main()
    finally:
        try:
            if _LAST_PROJECTION_RECEIPT is not None:
                result_index = sys.argv.index("--result") + 1
                receipt_path = (
                    Path(sys.argv[result_index]).parent / PROJECTION_RECEIPT_NAME
                )
                if receipt_path.exists() or receipt_path.is_symlink():
                    raise FileExistsError(receipt_path)
                algorithm._atomic_new(receipt_path, _LAST_PROJECTION_RECEIPT)
        finally:
            algorithm._read = inherited_read
            _VISIBLE_QUESTION = None
            _LAST_PROJECTION_RECEIPT = None


if __name__ == "__main__":
    main()
