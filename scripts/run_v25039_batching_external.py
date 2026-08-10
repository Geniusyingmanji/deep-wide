#!/usr/bin/env python3
"""V2.50.39 append-only runner over the frozen V2.50.38 engine."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25039_batching_external_contract as contract  # noqa: E402
from scripts import run_v25038_batching_external as engine  # noqa: E402


def configure() -> None:
    engine.contract = contract
    engine.MODEL_SLOT_DIRECTORY = contract.OUTPUT_ROOT / "model_slots"


def validate_task_row(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    return engine.validate_task_row(value)


def aggregate_rows(*args: Any, **kwargs: Any) -> dict[str, Any]:
    configure()
    return engine.aggregate_rows(*args, **kwargs)


def mechanism_decision(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    return engine.mechanism_decision(value)


def validate_forward_result(value: Mapping[str, Any]) -> dict[str, Any]:
    configure()
    return engine.validate_forward_result(value)


def run_forward() -> dict[str, Any]:
    configure()
    return engine.run_forward()


def _read_jsonl(relative: Path) -> list[dict[str, Any]]:
    configure()
    return engine._read_jsonl(relative)


def main() -> None:
    value = run_forward()
    print(json.dumps({
        "path": str(contract.FORWARD_RESULT),
        "aggregate": value["aggregate"],
        "decision": value["mechanism_decision"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
