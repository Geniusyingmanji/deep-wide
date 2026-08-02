#!/usr/bin/env python3
"""Isolated-import successor for the frozen V2.42.59 task runner."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.run_v24259_score_first_task import main  # noqa: E402


if __name__ == "__main__":
    main()
