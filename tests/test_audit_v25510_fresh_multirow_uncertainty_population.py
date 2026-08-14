from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25510_fresh_multirow_uncertainty_population as target  # noqa: E402


class V25510FreshMultirowUncertaintyPopulationAuditTests(unittest.TestCase):
    def test_fixed_hashes_commit_and_build_barrier_are_exact(self) -> None:
        self.assertTrue(target._build_barrier())
        self.assertTrue(
            all(
                target.base.sha256(path) == digest
                for path, digest in target.FIXED_HASHES.items()
            )
        )
        history = target._git("rev-list", target._git("rev-parse", "HEAD"))
        self.assertIn(target.IMPLEMENTATION_COMMIT, history)

    def test_population_audit_passes_without_external_effect(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["selection"]["pair_count"], 20)
        self.assertEqual(value["selection"]["row_identity_count"], 40)
        self.assertEqual(
            value["selection"]["visible_prior_cctld_identity_overlap_count"], 0
        )
        self.assertFalse(value["authorization"]["external_forward"])
        self.assertTrue(value["authorization"]["fresh_external_protocol_design"])

    def test_resealed_selection_credit_or_launch_tamper_fails(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        for kind in ("selection", "credit", "launch"):
            changed = copy.deepcopy(value)
            if kind == "selection":
                changed["selection"]["pair_count"] = 19
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["authorization"]["external_forward"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_watcher_or_lease_drift_fails_checks(self) -> None:
        fake = [{"pid": 1, "start_ticks": 1, "marker": "wrong"}]
        with mock.patch.object(
            target.watchers, "watcher_snapshot", return_value=fake
        ), self.assertRaises(ValueError):
            target.build_audit(now=1, tracked=False)


if __name__ == "__main__":
    unittest.main()
