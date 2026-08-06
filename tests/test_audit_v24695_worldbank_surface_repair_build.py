from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path: sys.path.insert(0, str(path))

from scripts import audit_v24695_worldbank_surface_repair_build as audit  # noqa: E402


SEMANTICS = {"contract_task_count": 12, "gold_row_count": 48,
             "provenance_record_count": 96, "exact_table_accepted": True,
             "wrong_value_rejected": True, "synthetic_complete_gate_passed": True,
             "synthetic_exact_gain": 12}


class V24695WorldBankSurfaceRepairBuildAuditTests(unittest.TestCase):
    def synthetic(self, *, head="c"*40, remote="c"*40, clean=True,
                  quarantine=True, semantics=True, lease=True, pristine=True) -> dict:
        tests = iter((True, count) for _path, count, _timeout in audit.TEST_SUITES)
        surfaces = audit.builder.build_surfaces()
        with (
            patch.object(audit.builder, "_quarantine_valid", return_value=quarantine),
            patch.object(audit, "_evaluator_semantics", return_value=SEMANTICS if semantics else {"failure_type":"TypeError"}),
            patch.object(audit, "_run_test", side_effect=lambda *_args: next(tests)),
            patch.object(audit.common, "_sha256", return_value="a"*64),
            patch.object(audit.common, "_ordinary", side_effect=lambda path: ROOT/path),
            patch.object(audit.common, "_git", side_effect=[head, remote, "" if clean else " M plan.md"]),
            patch.object(audit.common, "_tracked", return_value=True),
            patch.object(audit.common, "_watcher", return_value=True),
            patch.object(audit.common, "_lease_inactive", return_value=lease),
            patch.object(audit.common, "SECRET", re.compile(r"a^")),
            patch.object(audit.builder, "build_surfaces", return_value=surfaces),
            patch.object(Path, "exists", return_value=not pristine),
            patch.object(Path, "is_symlink", return_value=False),
        ):
            return audit.build_audit(now=0)

    def test_go_authorizes_repaired_publication_only(self) -> None:
        value=self.synthetic(); audit.validate_audit(value)
        self.assertEqual(value["tests"]["test_count"],28)
        self.assertTrue(value["authorization"]["one_repaired_surface_publication"])
        self.assertFalse(value["authorization"]["preactivation_or_launch"])

    def test_semantic_failure_fails_closed(self) -> None:
        self.assertIn("v24694_evaluator_semantics_failed",self.synthetic(semantics=False)["findings"])

    def test_quarantine_or_residue_fails_closed(self) -> None:
        self.assertIn("v24693_quarantine_drifted",self.synthetic(quarantine=False)["findings"])
        self.assertIn("v24694_surface_not_pristine",self.synthetic(pristine=False)["findings"])

    def test_unpushed_dirty_or_active_lease_fails_closed(self) -> None:
        self.assertIn("v24695_source_commit_not_pushed",self.synthetic(head="a"*40,remote="b"*40)["findings"])
        self.assertIn("v24695_source_worktree_not_clean",self.synthetic(clean=False)["findings"])
        self.assertIn("shared_api_lease_active",self.synthetic(lease=False)["findings"])

    def test_resealed_launch_tamper_fails_closed(self) -> None:
        changed=copy.deepcopy(self.synthetic());changed["authorization"]["preactivation_or_launch"]=True
        changed.pop("audit_payload_sha256");changed["audit_payload_sha256"]=audit.payload_sha256(changed)
        with self.assertRaises(RuntimeError):audit.validate_audit(changed)

    def test_resealed_evaluator_tamper_fails_closed(self) -> None:
        changed=copy.deepcopy(self.synthetic());changed["authorization"]["evaluator_execution_on_predictions"]=True
        changed.pop("audit_payload_sha256");changed["audit_payload_sha256"]=audit.payload_sha256(changed)
        with self.assertRaises(RuntimeError):audit.validate_audit(changed)


if __name__ == "__main__":unittest.main()
