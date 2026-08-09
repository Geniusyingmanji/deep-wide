#!/usr/bin/env python3
"""Run one frozen V2.49.37 paired task."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24937_layout_diverse_contextual_external_contract as contract  # noqa: E402
from scripts import run_v24923_target_value_external_task as engine  # noqa: E402
from scripts import run_v24934_contextual_record_external_task as parent  # noqa: E402


def configure() -> None:
    parent.contract = contract
    parent.base.contract = contract
    engine.contract = contract
    parent.configure()


def main() -> None:
    configure()
    try:
        task_path = Path(sys.argv[sys.argv.index("--task") + 1])
        raw = json.loads(task_path.read_text(encoding="utf-8"))
        opaque_id = str(raw["opaque_id"])
    except (IndexError, KeyError, ValueError, json.JSONDecodeError):
        raise RuntimeError("V2.49.37 child task order binding is absent") from None
    contract.ARMS = contract.arm_order(opaque_id)
    engine.main()


if __name__ == "__main__":
    main()
