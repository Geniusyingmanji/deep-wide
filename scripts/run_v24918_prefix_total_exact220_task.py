#!/usr/bin/env python3
"""Run one V2.49.18 task through the frozen V2.49.16 binding."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24918_prefix_total_exact220_contract as contract  # noqa: E402
from deepwide_agent.v24916_prefix_total_long_page_packer import (  # noqa: E402
    build_prefix_total_packing,
    validate_receipt,
)
from scripts import run_v24916_prefix_total_long_page_task as child  # noqa: E402


def configure() -> None:
    child.configure(contract)


def _receipt_path() -> Path:
    result_index = sys.argv.index("--result") + 1
    return Path(sys.argv[result_index]).parent / child.PROJECTION_RECEIPT_NAME


def _validate_projection_receipt() -> None:
    path = _receipt_path()
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("V2.49.18 projection receipt missing")
    validate_receipt(child.algorithm._read(path))


def main() -> None:
    configure()
    try:
        child.main()
    finally:
        path = _receipt_path()
        if not path.exists() and not path.is_symlink():
            empty = build_prefix_total_packing("visible terminal fallback", [])[
                "content_free_receipt"
            ]
            child.algorithm._atomic_new(path, empty)
        _validate_projection_receipt()


if __name__ == "__main__":
    main()
