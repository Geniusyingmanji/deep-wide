#!/usr/bin/env python3
"""V2.48.31 child namespace around the frozen keyless algorithm."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24831_keyless_exact220_contract as contract  # noqa: E402
from scripts import run_v24635_exact220_task as algorithm  # noqa: E402


def configure() -> None:
    algorithm.OUTPUT_ROOT = contract.OUTPUT_ROOT
    algorithm.TASK_ROOT = contract.TASK_ROOT
    algorithm.MODEL_SLOT_DIRECTORY = contract.MODEL_SLOT_DIRECTORY


def main() -> None:
    configure()
    algorithm.main()


if __name__ == "__main__":
    main()
