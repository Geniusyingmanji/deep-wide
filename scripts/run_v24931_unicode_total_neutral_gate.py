#!/usr/bin/env python3
"""Launch V2.49.29 through the frozen V2.49.31 role adapter."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24929_unicode_total_neutral_contract as contract  # noqa: E402
from scripts import control_v24929_unicode_total_neutral_gate as control  # noqa: E402
from scripts import control_v24930_unicode_total_neutral_start as corrected  # noqa: E402
from scripts import control_v24931_unicode_total_neutral_activation as activation  # noqa: E402
from scripts import run_v24929_unicode_total_neutral_gate as parent  # noqa: E402


def _validate_authorization() -> tuple[dict[str, Any], dict[str, Any]]:
    protocol = control.validate_protocol(control._read(ROOT / contract.PROTOCOL))
    control.validate_audit(control._read(ROOT / contract.PREAUDIT))
    start = corrected.validate_start(control._read(ROOT / contract.EXECUTION_START))
    activation.validate_activation(control._read(ROOT / activation.ACTIVATION))
    return protocol, start


def main() -> None:
    parent._validate_authorization = _validate_authorization
    parent.main()


if __name__ == "__main__":
    main()
