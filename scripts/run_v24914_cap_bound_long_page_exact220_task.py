#!/usr/bin/env python3
"""Run one V2.49.14 task through the frozen V2.49.13 child binding."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24914_cap_bound_long_page_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24913_observable_long_page_packer import (  # noqa: E402
    build_observable_packing,
)
from deepwide_agent.v24913_observable_long_page_packer import validate_receipt  # noqa: E402
from scripts import run_v24913_cap_bound_long_page_task as child  # noqa: E402


def configure() -> None:
    child.configure(contract)


def _validate_projection_receipt() -> None:
    result_index = sys.argv.index("--result") + 1
    path = Path(sys.argv[result_index]).parent / child.PROJECTION_RECEIPT_NAME
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.49.14 projection receipt missing")
    value = child.algorithm._read(path)
    validate_receipt(value)


def main() -> None:
    configure()
    try:
        child.main()
    finally:
        result_index = sys.argv.index("--result") + 1
        path = Path(sys.argv[result_index]).parent / child.PROJECTION_RECEIPT_NAME
        if not path.exists() and not path.is_symlink():
            empty = build_observable_packing("visible terminal fallback", [
            ])["content_free_receipt"]
            child.algorithm._atomic_new(path, empty)
        _validate_projection_receipt()


if __name__ == "__main__":
    main()
