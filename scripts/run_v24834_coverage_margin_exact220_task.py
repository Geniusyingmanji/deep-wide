#!/usr/bin/env python3
"""Run one V2.48.34 task with the frozen V2.48.33 controller."""

from __future__ import annotations

import copy
import dataclasses
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24272_two_wave_retrieval as retrieval  # noqa: E402
from deepwide_agent import v24833_coverage_margin_controller as controller  # noqa: E402
from deepwide_agent import v24834_coverage_margin_exact220_contract as contract  # noqa: E402
from scripts import run_v24635_exact220_task as algorithm  # noqa: E402


def coverage_margin_decision(observation: Any, *, policy: Any = None) -> dict[str, Any]:
    if policy is None or dataclasses.asdict(policy) != contract.TWO_WAVE_POLICY:
        raise RuntimeError("V2.48.34 coverage-margin policy drifted")
    outer = controller.decide_coverage_margin(observation)
    if outer["policy"] != contract.TWO_WAVE_POLICY:
        raise RuntimeError("V2.48.34 controller receipt policy drifted")
    return copy.deepcopy(outer["base_decision_receipt"])


def configure() -> None:
    algorithm.OUTPUT_ROOT = contract.OUTPUT_ROOT
    algorithm.TASK_ROOT = contract.TASK_ROOT
    algorithm.MODEL_SLOT_DIRECTORY = contract.MODEL_SLOT_DIRECTORY
    algorithm.LIMITS = contract.LIMITS
    algorithm.MODEL = contract.MODEL
    algorithm.SEARCH = contract.SEARCH
    algorithm.TWO_WAVE_POLICY = contract.TWO_WAVE_POLICY
    retrieval.decide_two_wave = coverage_margin_decision


def main() -> None:
    configure()
    algorithm.main()


if __name__ == "__main__":
    main()
