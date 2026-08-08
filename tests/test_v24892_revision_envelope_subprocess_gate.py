from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24881_mapping_recovery_subprocess_gate as frozen  # noqa: E402
from deepwide_agent import v24892_revision_envelope_subprocess_gate as target  # noqa: E402


class V24892RevisionEnvelopeSubprocessGateTests(unittest.TestCase):
    def test_isolation(self) -> None:
        target.validate_isolation()
        self.assertIsNot(
            target.run_observed_bundle_subprocess,
            frozen.run_observed_bundle_subprocess,
        )

    def test_parent_receipt_schema_is_unchanged(self) -> None:
        self.assertIs(
            target.validate_parent_bundle_receipt,
            frozen.validate_parent_bundle_receipt,
        )


if __name__ == "__main__":
    unittest.main()
