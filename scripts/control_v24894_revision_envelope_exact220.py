#!/usr/bin/env python3
"""Freeze and authorize V2.48.94 exact-220 artifacts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24894_revision_envelope_exact220_contract as contract  # noqa: E402
from scripts import control_v24884_mapping_recovery_exact220 as parent  # noqa: E402


def configure() -> None:
    parent.contract = contract
    parent.parent.PREAUDIT_ROLE = "v24894_revision_envelope_exact220_preactivation_audit"
    parent.parent.START_ROLE = "v24894_revision_envelope_exact220_execution_start"
    parent.configure()
    parent.parent.base.RUNTIME_SOURCES = tuple(
        dict.fromkeys((*parent.parent.base.RUNTIME_SOURCES, *contract.CORRECTED_SOURCES))
    )
    parent.parent.base.TEST_SUITES = (
        (contract.TEST, 15, 240),
        (Path("tests/test_v24886_revision_envelope_passthrough.py"), 7, 240),
        (Path("tests/test_v24887_revision_envelope_integration.py"), 13, 240),
        (Path("tests/test_v24889_revision_envelope_runtime.py"), 7, 240),
        (Path("tests/test_v24890_revision_envelope_mapping_bundle.py"), 14, 240),
        (Path("tests/test_v24891_revision_envelope_child_runtime.py"), 8, 240),
        (Path("tests/test_v24892_revision_envelope_subprocess_gate.py"), 2, 240),
        *parent.parent.base.TEST_SUITES[1:],
    )
    parent.parent.base.EXPECTED_TESTS = sum(
        expected for _path, expected, _timeout in parent.parent.base.TEST_SUITES
    )


def main() -> None:
    configure()
    parent.parent.base.main()


if __name__ == "__main__":
    main()
