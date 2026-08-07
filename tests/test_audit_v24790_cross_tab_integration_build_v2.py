from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path: sys.path.insert(0, str(path))

from scripts import audit_v24790_cross_tab_integration_build_v2 as audit  # noqa: E402


class V24790IntegrationBuildAuditV2Tests(unittest.TestCase):
    def synthetic(self, *, head="c" * 40, remote="c" * 40, clean=True, tracked=True, parent=True, implementation=True, findings=([], [], [], [], []), lease=True, runners=None, pristine=True):
        suites = iter((True, expected, "d" * 64) for _path, expected, _timeout in audit.TEST_SUITES)
        with (
            patch.object(audit, "_sha256", return_value="a" * 64),
            patch.object(audit, "_tracked", return_value=tracked),
            patch.object(audit, "_parent_valid", return_value=parent),
            patch.object(audit, "ast_findings", return_value=findings),
            patch.object(audit, "implementation_contract", return_value={"valid": implementation}),
            patch.object(audit, "_run_test", side_effect=lambda *_args: next(suites)),
            patch.object(audit, "_git", side_effect=[head, remote, "" if clean else " M plan.md"]),
            patch.object(audit.old_contract, "protected_watcher_snapshot", return_value=[]),
            patch.object(audit, "_lease_inactive", return_value=lease),
            patch.object(audit, "_active_runners", return_value=runners or []),
            patch.object(Path, "exists", return_value=not pristine),
            patch.object(Path, "is_symlink", return_value=False),
        ):
            return audit.build_audit(now=0)

    def test_actual_parent_ast_and_implementation_are_clean(self) -> None:
        self.assertTrue(audit._parent_valid())
        self.assertEqual(audit.ast_findings(), ([], [], [], [], []))
        value = audit.implementation_contract()
        self.assertTrue(value["valid"])
        self.assertEqual(value["base_runtime_call_count"], 1)
        self.assertEqual(value["one_target_catalog_builder_call_count"], 0)
        self.assertEqual(value["full_catalog_validator_call_count"], 1)

    def test_go_authorizes_runner_build_only(self) -> None:
        value = self.synthetic()
        audit.validate_audit(value)
        self.assertEqual(value["tests"]["observed"], 58)
        self.assertTrue(value["authorization"]["append_only_execution_contract_and_runner_build"])
        for name in ("package_audit_generation", "preactivation_audit_generation", "activation_or_external_launch", "quality_or_evaluator_surface_open", "paired_dev64", "exact220", "entropy_or_credit_experiment", "leaderboard_or_sota"):
            self.assertFalse(value["authorization"][name])

    def test_unpushed_dirty_parent_or_implementation_fails(self) -> None:
        self.assertIn("v24790_integration_source_commit_not_pushed", self.synthetic(head="a" * 40, remote="b" * 40)["findings"])
        self.assertIn("v24790_integration_source_worktree_not_clean", self.synthetic(clean=False)["findings"])
        self.assertIn("v24790_corrected_protocol_drifted", self.synthetic(parent=False)["findings"])
        self.assertIn("v24790_integration_contract_drifted", self.synthetic(implementation=False)["findings"])

    def test_leakage_effect_lease_runner_or_future_fails(self) -> None:
        value = self.synthetic(findings=(["field"], ["import"], ["effect"], ["marker"], ["secret"]), lease=False, runners=[123], pristine=False)
        for finding in ("privileged_runtime_field_access", "evaluator_or_gold_import_in_runtime", "direct_external_effect_capability_in_runtime", "private_output_or_evaluator_marker_in_runtime", "credential_literal_in_runtime", "shared_api_lease_active", "v24784_or_v24790_runner_active", "v24790_future_surface_not_pristine"):
            self.assertIn(finding, value["findings"])

    def test_sources_and_test_count_exclude_private_paths(self) -> None:
        self.assertFalse(any(path.parts[:1] in {("evaluation",), ("outputs",)} for path in audit.SOURCES))
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 58)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 58)

    def test_v1_rebuild_never_reappears_in_runtime(self) -> None:
        source = (ROOT / audit.SELECTED).read_text(encoding="utf-8")
        self.assertNotIn("build_target_segment_catalog(", source)
        self.assertIn("segment.validate_target_segment_catalog(catalog)", source)

    def test_resealed_launch_tamper_and_create_only_fail(self) -> None:
        value = self.synthetic()
        changed = copy.deepcopy(value)
        changed["authorization"]["activation_or_external_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = audit.old_contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError): audit.validate_audit(changed)
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            audit.publish_new(path, {})
            with self.assertRaises(FileExistsError): audit.publish_new(path, {})


if __name__ == "__main__": unittest.main()
