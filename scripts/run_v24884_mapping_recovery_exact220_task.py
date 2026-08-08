#!/usr/bin/env python3
"""Static V2.48.84 child using the V2.48.82 stage runtime."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24882_mapping_recovery_stage_runtime as child_runtime  # noqa: E402
from deepwide_agent import v24884_mapping_recovery_exact220_contract as contract  # noqa: E402
from scripts import run_v24877_keyless_coverage_exact220_task as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.run_child_bundle = child_runtime.run_child_bundle
    if base.run_child_bundle is not child_runtime.run_child_bundle:
        raise RuntimeError("V2.48.84 static child binding drifted")


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
