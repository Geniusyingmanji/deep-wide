#!/usr/bin/env python3
"""Benchmark-external child that deliberately exceeds its fetch deadline."""

from __future__ import annotations

import sys
import time


def main() -> int:
    sys.stdin.read()
    time.sleep(60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
