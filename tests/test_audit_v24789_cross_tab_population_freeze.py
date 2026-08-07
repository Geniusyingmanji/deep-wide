from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24789_cross_tab_population_freeze as audit  # noqa: E402


class V24789CrossTabPopulationFreezeAuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        clean: bool = True,
        tracked: bool = True,
        private_ok: bool = True,
        population: bool = True,
        findings: tuple[list[str], list[str], list[str]] = ([], [], []),
        lease: bool = True,
        runners: list[int] | None = None,
        pristine: bool = True,
    ) -> dict:
        suites = iter((True, expected, "d" * 64) for _path, expected, _timeout in audit.TEST_SUITES)
        private = {
            "relative_path": str(audit.PRIVATE),
            "under_evaluation_directory": True,
            "tracked": private_ok,
            "ordinary_file_by_lstat_without_content_read": private_ok,
            "symlink": False,
            "bytes_opened_parsed_imported_copied_or_hashed_by_audit": False,
        }
        with (
            patch.object(audit, "_sha256", return_value="a" * 64),
            patch.object(audit, "_private_path_receipt", return_value=private),
            patch.object(audit, "population_contract", return_value={"valid": population}),
            patch.object(audit, "label_blind_contract_findings", return_value=findings),
            patch.object(audit, "_run_test", side_effect=lambda *_args: next(suites)),
            patch.object(audit, "_git", side_effect=[head, remote]),
            patch.object(audit, "_public_scope_clean", return_value=clean),
            patch.object(audit, "_tracked", return_value=tracked),
            patch.object(audit.contract, "protected_watcher_snapshot", return_value=[]),
            patch.object(audit, "_lease_inactive", return_value=lease),
            patch.object(audit, "_active_runners", return_value=runners or []),
            patch.object(Path, "exists", return_value=not pristine),
            patch.object(Path, "is_symlink", return_value=False),
        ):
            return audit.build_audit(now=0)

    def test_actual_public_population_is_valid_fresh_and_label_blind(self) -> None:
        value = audit.population_contract()
        self.assertTrue(value["valid"])
        self.assertEqual(value["task_keys"], ["opaque_id", "question"])
        self.assertEqual(value["entity_count"], 32)
        self.assertEqual(value["historical_visible_entity_count"], 4_816)
        self.assertEqual(value["literal_overlap_with_history"], 0)
        self.assertEqual(value["canonical_overlap_with_history"], 0)
        self.assertTrue(value["failed_v24787_surfaces_pristine"])
        self.assertTrue(value["one_unknown_target_future_contract_frozen"])

    def test_private_receipt_uses_lstat_without_open_or_hash(self) -> None:
        receipt = audit._private_path_receipt()
        self.assertTrue(receipt["under_evaluation_directory"])
        self.assertTrue(receipt["tracked"])
        self.assertTrue(receipt["ordinary_file_by_lstat_without_content_read"])
        self.assertFalse(receipt["symlink"])
        self.assertFalse(receipt["bytes_opened_parsed_imported_copied_or_hashed_by_audit"])
        with self.assertRaises(RuntimeError):
            audit._sha256(audit.PRIVATE)
        with self.assertRaises(RuntimeError):
            audit._read_public(audit.PRIVATE)

    def test_go_authorizes_inert_protocol_only(self) -> None:
        value = self.synthetic()
        audit.validate_audit(value)
        self.assertEqual(value["tests"]["observed"], 30)
        self.assertTrue(value["authorization"]["inert_v24790_protocol_publication"])
        for name in (
            "trusted_child_integration_or_runner_build",
            "preactivation_audit",
            "activation_or_external_launch",
            "quality_or_evaluator_surface_open",
            "paired_dev64",
            "exact220",
            "entropy_or_credit_experiment",
            "leaderboard_or_sota",
        ):
            self.assertFalse(value["authorization"][name])

    def test_unpushed_dirty_private_or_population_drift_fails_closed(self) -> None:
        self.assertIn("v24789_freeze_source_commit_not_pushed", self.synthetic(head="a" * 40, remote="b" * 40)["findings"])
        self.assertIn("v24789_public_source_scope_not_clean", self.synthetic(clean=False)["findings"])
        self.assertIn("v24789_private_path_separation_drifted", self.synthetic(private_ok=False)["findings"])
        self.assertIn("v24789_public_population_contract_drifted", self.synthetic(population=False)["findings"])

    def test_leakage_lease_runner_or_future_surface_fails_closed(self) -> None:
        value = self.synthetic(findings=(["field"], ["import"], ["secret"]), lease=False, runners=[123], pristine=False)
        for finding in (
            "visible_contract_privileged_field_access",
            "visible_contract_evaluator_or_gold_import",
            "credential_literal_in_public_source",
            "shared_api_lease_active",
            "v24784_v24789_or_v24790_runner_active",
            "v24789_v24790_future_surface_not_pristine",
        ):
            self.assertIn(finding, value["findings"])

    def test_private_path_is_excluded_and_test_count_frozen(self) -> None:
        self.assertNotIn(audit.PRIVATE, audit.PUBLIC_SOURCES)
        self.assertFalse(any(path.parts[:1] == ("evaluation",) for path in audit.PUBLIC_SOURCES))
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 30)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 30)

    def test_resealed_launch_tamper_and_create_only_publish_are_rejected(self) -> None:
        value = self.synthetic()
        changed = copy.deepcopy(value)
        changed["authorization"]["activation_or_external_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = audit.contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(changed)
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            audit.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                audit.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
