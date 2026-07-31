from __future__ import annotations

import unittest
from unittest import mock

from scripts.audit_v24194_capacity_ladder_wait_activation import ROOT, build_audit
from scripts.preregister_v24194_capacity_ladder import build_protocol


class AuditV24194CapacityLadderWaitActivationTests(unittest.TestCase):
    def test_missing_real_wait_state_fails_closed_before_publication(self) -> None:
        protocol = build_protocol(ROOT, created_at_unix=1, require_pristine=False)
        verified = {"path": ROOT / "results/synthetic_v24194.json", "sha256": "a" * 64, "value": protocol}
        with mock.patch(
            "scripts.audit_v24194_capacity_ladder_wait_activation.validate_protocol",
            return_value=verified,
        ), mock.patch(
            "scripts.audit_v24194_capacity_ladder_wait_activation._read",
            side_effect=RuntimeError("missing"),
        ), self.assertRaisesRegex(RuntimeError, "missing"):
            build_audit(ROOT, created_at_unix=1)


if __name__ == "__main__":
    unittest.main()
