from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24662_strict_support_closure_build as audit  # noqa: E402


class V24662BuildAuditTests(unittest.TestCase):
    def synthetic(self, *, clean=True, parent=True, implementation=True, lease=False):
        tests = iter((True, count) for _path, count in audit.TEST_SUITES)
        with patch.object(audit, "_ordinary", side_effect=lambda path: ROOT / path), patch.object(
            audit, "_sha256", return_value="a" * 64
        ), patch.object(audit, "_ast_findings", return_value=([], [])), patch.object(
            audit, "_run_test", side_effect=lambda *_args: next(tests)
        ), patch.object(
            audit, "_git", side_effect=["c" * 40, "c" * 40, "" if clean else " M plan.md"]
        ), patch.object(audit, "_tracked", return_value=True), patch.object(
            audit, "_parent_valid", return_value=parent
        ), patch.object(audit, "_implementation_valid", return_value=implementation), patch.object(
            audit, "lease_observation", return_value={"active": lease}
        ), patch.object(audit, "protected_watcher_snapshot", return_value=[]), patch.object(
            audit, "SECRET", re.compile(r"a^")
        ):
            return audit.build_audit(now=0)

    def test_synthetic_go_authorizes_only_disjoint_external_design(self):
        value = self.synthetic()
        audit.validate_audit(value)
        auth = value["authorization"]
        self.assertTrue(auth["fresh_disjoint_external_population_and_protocol_design"])
        self.assertFalse(auth["fresh_external_activation_or_launch"])
        self.assertFalse(auth["paired_dev64_design_or_launch"])
        self.assertFalse(auth["exact220"])

    def test_parent_or_implementation_drift_fails_closed(self):
        self.assertIn("v24660_parent_build_audit_drifted", self.synthetic(parent=False)["findings"])
        self.assertIn("v24661_strict_closure_contract_drifted", self.synthetic(implementation=False)["findings"])

    def test_dirty_or_active_lease_fails_closed(self):
        self.assertIn("v24662_source_worktree_not_clean", self.synthetic(clean=False)["findings"])
        self.assertIn("shared_api_lease_active", self.synthetic(lease=True)["findings"])

    def test_test_count_is_frozen(self):
        self.assertEqual(sum(count for _path, count in audit.TEST_SUITES), 29)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 29)

    def test_resealed_launch_tamper_fails_closed(self):
        value = self.synthetic()
        tampered = copy.deepcopy(value)
        tampered["authorization"]["fresh_external_activation_or_launch"] = True
        tampered.pop("audit_payload_sha256")
        tampered["audit_payload_sha256"] = audit.payload_sha256(tampered)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(tampered)

    def test_precursor_is_explicitly_superseded(self):
        mechanism = self.synthetic()["mechanism"]
        self.assertTrue(mechanism["v24659_v24660_design_only_precursor_superseded"])
        self.assertTrue(mechanism["unresolved_declared_evidence_ids_preserved"])
        self.assertTrue(mechanism["non_supporting_declared_evidence_ids_preserved"])

    def test_no_threshold_entropy_or_new_effect_relaxation(self):
        mechanism = self.synthetic()["mechanism"]
        self.assertEqual(mechanism["minimum_independent_support_sources"], 2)
        self.assertFalse(mechanism["support_threshold_relaxed"])
        self.assertFalse(mechanism["proposal_value_changed_by_closure"])
        self.assertFalse(mechanism["new_model_search_fetch_or_evaluator_effect"])
        self.assertFalse(mechanism["entropy_or_task_credit_used"])


if __name__ == "__main__":
    unittest.main()
