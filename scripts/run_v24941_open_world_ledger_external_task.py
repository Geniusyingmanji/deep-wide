#!/usr/bin/env python3
"""Run one V2.49.41 task with an exact visible-cohort page binding."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24941_open_world_ledger_external_contract as contract  # noqa: E402
from scripts import run_v24923_target_value_external_task as engine  # noqa: E402
from scripts import run_v24940_open_world_ledger_external_task as parent  # noqa: E402


def select_task_page(question: str, pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cohort = contract.parse_visible_cohort(question)
    matches = [
        page
        for page in pages
        if isinstance(page, dict)
        and sum(
            line.split("|")[1].strip() == cohort
            for line in str(page.get("content", "")).splitlines()[1:]
            if len(line.split("|")) >= 2
        )
        == contract.ROWS_PER_TASK
    ]
    if len(matches) != 1:
        raise RuntimeError("V2.49.41 visible cohort did not bind exactly one frozen page")
    return matches


def configure() -> None:
    parent.contract = contract
    parent.base.contract = contract
    engine.contract = contract
    parent.configure()
    inherited = engine._read

    def aligned_read(path: Path) -> dict[str, Any]:
        value = inherited(path)
        if path.name != "frozen_pages.json":
            return value
        task_path = Path(sys.argv[sys.argv.index("--task") + 1])
        task = json.loads(task_path.read_text(encoding="utf-8"))
        pages = value.get("pages")
        if not isinstance(pages, list):
            raise RuntimeError("V2.49.41 frozen page vector drifted")
        copied = dict(value)
        copied["pages"] = select_task_page(str(task["question"]), pages)
        return copied

    engine._read = aligned_read


def main() -> None:
    configure()
    try:
        task_path = Path(sys.argv[sys.argv.index("--task") + 1])
        raw = json.loads(task_path.read_text(encoding="utf-8"))
        opaque_id = str(raw["opaque_id"])
    except (IndexError, KeyError, ValueError, json.JSONDecodeError):
        raise RuntimeError("V2.49.41 child task order binding is absent") from None
    contract.ARMS = contract.arm_order(opaque_id)
    engine.main()


if __name__ == "__main__":
    main()
