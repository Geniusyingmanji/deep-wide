from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24875_keyless_coverage_child_runtime as frozen  # noqa: E402
from deepwide_agent import v24880_mapping_recovery_child_runtime as target  # noqa: E402


class V24880MappingRecoveryChildRuntimeTests(unittest.TestCase):
    def test_isolation(self) -> None:
        target.validate_isolation()
        self.assertIsNot(target.run_child_bundle, frozen.run_child_bundle)

    def test_static_interface(self) -> None:
        self.assertTrue(callable(target.run_child_bundle))
        self.assertEqual(target.TERMINAL_NAME, "child_terminal_receipt.json")


if __name__ == "__main__":
    unittest.main()
