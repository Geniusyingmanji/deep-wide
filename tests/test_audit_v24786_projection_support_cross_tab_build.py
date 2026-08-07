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

from scripts import (  # noqa: E402
    audit_v24786_projection_support_cross_tab_build as audit,
)


class V24786ProjectionSupportCrossTabBuildAuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        clean: bool = True,
        tracked: bool = True,
        parent: bool = True,
        implementation: bool = True,
        findings: tuple[
            list[str], list[str], list[str], list[str], list[str]
        ] = ([], [], [], [], []),
    ) -> dict:
        suites = iter(
            (True, expected, "d" * 64)
            for _path, expected, _timeout in audit.TEST_SUITES
        )
        with (
            patch.object(audit, "_sha256", return_value="a" * 64),
            patch.object(audit, "_tracked", return_value=tracked),
            patch.object(audit, "_parent_valid", return_value=parent),
            patch.object(audit, "ast_findings", return_value=findings),
            patch.object(
                audit,
                "implementation_contract",
                return_value={"valid": implementation},
            ),
            patch.object(audit, "_run_test", side_effect=lambda *_args: next(suites)),
            patch.object(
                audit,
                "_git",
                side_effect=[head, remote, "" if clean else " M plan.md"],
            ),
            patch.object(audit.contract, "protected_watcher_snapshot", return_value=[]),
        ):
            return audit.build_audit(now=0)

    def test_actual_parent_ast_and_implementation_contract_are_clean(self) -> None:
        self.assertTrue(audit._parent_valid())
        self.assertEqual(audit.ast_findings(), ([], [], [], [], []))
        implementation = audit.implementation_contract()
        self.assertTrue(implementation["valid"])
        self.assertTrue(implementation["strict_joint_rederived_by_validator"])
        self.assertTrue(implementation["catalog_quarantine_replay_present"])

    def test_go_freezes_observer_and_population_design_only(self) -> None:
        value = self.synthetic()
        audit.validate_audit(value)
        self.assertEqual(value["tests"]["observed"], 55)
        self.assertTrue(value["authorization"]["cross_tab_observer_build_frozen"])
        self.assertTrue(value["authorization"]["fresh_disjoint_population_design"])
        for name in (
            "trusted_child_integration_or_runner_build",
            "package_or_preactivation_audit_generation",
            "activation_or_external_launch",
            "private_truth_or_quality_surface_open",
            "paired_dev64",
            "exact220",
            "entropy_or_credit_experiment",
            "leaderboard_or_sota",
        ):
            self.assertFalse(value["authorization"][name])

    def test_unpushed_dirty_parent_or_implementation_fails_closed(self) -> None:
        self.assertIn(
            "v24786_source_commit_not_pushed",
            self.synthetic(head="a" * 40, remote="b" * 40)["findings"],
        )
        self.assertIn(
            "v24786_source_worktree_not_clean",
            self.synthetic(clean=False)["findings"],
        )
        self.assertIn(
            "v24785_parent_authorization_drifted",
            self.synthetic(parent=False)["findings"],
        )
        self.assertIn(
            "v24786_observer_contract_drifted",
            self.synthetic(implementation=False)["findings"],
        )

    def test_leakage_effect_marker_or_secret_fails_closed(self) -> None:
        value = self.synthetic(
            findings=(["field"], ["import"], ["effect"], ["marker"], ["secret"])
        )
        for finding in (
            "privileged_runtime_field_access",
            "evaluator_or_gold_import_in_runtime",
            "external_effect_capability_in_runtime",
            "private_output_or_evaluator_marker_in_runtime",
            "credential_literal_in_runtime",
        ):
            self.assertIn(finding, value["findings"])

    def test_sources_and_test_count_exclude_private_surfaces(self) -> None:
        self.assertFalse(any(path.parts[:1] == ("evaluation",) for path in audit.SOURCES))
        self.assertFalse(any(path.parts[:1] == ("outputs",) for path in audit.SOURCES))
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 55)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 55)

    def test_parent_still_closes_launch_and_private_reads(self) -> None:
        value = audit._read(audit.PARENT)
        self.assertTrue(
            value["authorization"]["append_only_cross_tab_observer_build"]
        )
        self.assertFalse(value["authorization"]["activation_or_external_launch"])
        self.assertFalse(
            value["source_policy"][
                "v24784_output_visible_task_prediction_page_result_or_private_catalog_opened_or_hashed"
            ]
        )

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
