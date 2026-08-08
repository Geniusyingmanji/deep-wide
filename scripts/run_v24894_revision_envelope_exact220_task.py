#!/usr/bin/env python3
"""Static V2.48.94 child using the revision-envelope runtime."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24891_revision_envelope_child_runtime as child_runtime  # noqa: E402
from deepwide_agent import v24894_revision_envelope_exact220_contract as contract  # noqa: E402
from scripts import run_v24877_keyless_coverage_exact220_task as base  # noqa: E402


def configure() -> None:
    base.contract = contract
    base.run_child_bundle = child_runtime.run_child_bundle


def main() -> None:
    configure()
    base.main()


if __name__ == "__main__":
    main()
