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

from scripts import audit_v24790_cross_tab_control_plane_readiness_v2 as audit  # noqa: E402


class V24790CrossTabReadinessV2Tests(unittest.TestCase):
    def synthetic(
        self, *, parents=True, implementation=True,
        ast=([], [], [], []), tests=True, head="a" * 40,
        remote="a" * 40, clean=True, tracked=True, endpoint=True,
        lease=True, runners=None, pristine=True,
    ):
        with (
            patch.object(audit, "_manifest", return_value={}),
            patch.object(audit, "_parents_valid", return_value=parents),
            patch.object(audit, "implementation_contract", return_value={"valid": implementation}),
            patch.object(audit, "ast_findings", return_value=ast),
            patch.object(audit, "_run_tests", return_value=(tests, 48 if tests else 47, [])),
            patch.object(audit, "_git", side_effect=[head, remote, "" if clean else " M plan.md"]),
            patch.object(audit, "_tracked", return_value=tracked),
            patch.object(audit.contract, "protected_watcher_snapshot", return_value=[]),
            patch.object(audit, "_endpoint", return_value=endpoint),
            patch.object(audit, "_lease_inactive", return_value=lease),
            patch.object(audit, "_active_runners", return_value=runners or []),
            patch.object(Path, "exists", return_value=not pristine),
            patch.object(Path, "is_symlink", return_value=False),
            patch.object(audit, "_sha256", return_value="b" * 64),
        ):
            return audit.build_audit(now=0)

    def test_actual_parents_ast_and_implementation_are_clean(self) -> None:
        self.assertTrue(audit._parents_valid())
        self.assertEqual(audit.ast_findings(), ([], [], [], []))
        value = audit.implementation_contract()
        self.assertTrue(value["valid"])
        self.assertTrue(value["same_group_joint_aggregated_directly"])
        self.assertTrue(value["selected_receipts_only_aggregated_when_present"])

    def test_go_authorizes_package_audit_only(self) -> None:
        value = self.synthetic()
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["package_audit_artifact_generation"])
        for name in (
            "preactivation_audit_generation", "activation", "execution_start",
            "external_launch", "private_truth_or_quality_surface_open",
            "paired_dev64", "exact220", "entropy_or_credit_experiment",
            "leaderboard_or_sota",
        ):
            self.assertFalse(value["authorization"][name])

    def test_parent_implementation_test_or_git_drift_fails(self) -> None:
        self.assertIn("v24790_protocol_or_integration_parent_invalid", self.synthetic(parents=False)["findings"])
        self.assertIn("v24790_execution_package_contract_drifted", self.synthetic(implementation=False)["findings"])
        self.assertIn("regression_failed_or_count_drifted", self.synthetic(tests=False)["findings"])
        self.assertIn("source_commit_not_pushed", self.synthetic(remote="c" * 40)["findings"])
        self.assertIn("source_worktree_not_clean", self.synthetic(clean=False)["findings"])
        self.assertIn("source_not_tracked", self.synthetic(tracked=False)["findings"])

    def test_label_endpoint_lease_runner_or_surface_fails(self) -> None:
        value = self.synthetic(
            ast=(["field"], ["import"], ["marker"], ["secret"]),
            endpoint=False, lease=False, runners=[123], pristine=False,
        )
        for finding in (
            "privileged_forward_field_access", "evaluator_or_gold_import_in_forward",
            "private_or_consumed_output_marker_in_forward", "credential_literal_in_forward",
            "gpt56_endpoint_unreachable", "shared_api_lease_active",
            "v24790_runner_active", "future_surface_not_pristine",
        ):
            self.assertIn(finding, value["findings"])

    def test_source_and_test_contract_are_public_and_exact(self) -> None:
        self.assertFalse(any(path.parts[:1] in {("evaluation",), ("outputs",)} for path in audit.SOURCES))
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 48)
        self.assertEqual(audit.EXPECTED_TESTS, 48)

    def test_resealed_launch_tamper_fails_validation(self) -> None:
        value = self.synthetic()
        changed = copy.deepcopy(value)
        changed["authorization"]["external_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = audit.contract.payload_sha256(changed)
        with (
            patch.object(audit, "_manifest", return_value={}),
            patch.object(audit, "_sha256", return_value="b" * 64),
        ):
            with self.assertRaises(RuntimeError):
                audit.validate_audit(changed)

    def test_create_only_publish_rejects_overwrite(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            audit.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                audit.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
