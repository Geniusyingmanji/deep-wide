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

from scripts import audit_v24784_projection_funnel_integration_build as audit  # noqa: E402


class V24784ProjectionFunnelIntegrationBuildAuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        clean: bool = True,
        tracked: bool = True,
        parent: bool = True,
        implementation: bool = True,
        findings: tuple[list[str], list[str], list[str], list[str]] = ([], [], [], []),
        lease: bool = True,
        runners: list[int] | None = None,
        pristine: bool = True,
    ) -> dict:
        suites = iter(
            (True, expected, "d" * 64)
            for _path, expected, _timeout in audit.TEST_SUITES
        )
        with (
            patch.object(audit, "_sha256", return_value="a" * 64),
            patch.object(audit, "_tracked", return_value=tracked),
            patch.object(audit, "_protocol_valid", return_value=parent),
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
            patch.object(audit, "_lease_inactive", return_value=lease),
            patch.object(audit, "_active_runners", return_value=runners or []),
            patch.object(Path, "exists", return_value=not pristine),
            patch.object(Path, "is_symlink", return_value=False),
        ):
            return audit.build_audit(now=0)

    def test_actual_protocol_ast_and_implementation_contract_are_clean(self) -> None:
        self.assertTrue(audit._protocol_valid())
        self.assertEqual(audit.ast_findings(), ([], [], [], []))
        implementation = audit.implementation_contract()
        self.assertTrue(implementation["valid"])
        self.assertEqual(implementation["base_runtime_call_count_in_source"], 1)
        self.assertEqual(
            implementation[
                "redundant_base_full_result_validation_call_count_in_source"
            ],
            0,
        )
        self.assertEqual(implementation["private_catalog_access_count_in_source"], 1)
        self.assertEqual(implementation["funnel_builder_call_count_in_source"], 1)

    def test_go_authorizes_runner_build_only(self) -> None:
        value = self.synthetic()
        audit.validate_audit(value)
        self.assertEqual(value["tests"]["observed"], 57)
        self.assertTrue(
            value["authorization"]["append_only_execution_contract_and_runner_build"]
        )
        for name in (
            "package_audit_generation",
            "preactivation_audit_generation",
            "activation_or_external_launch",
            "quality_or_evaluator_surface_open",
            "paired_dev64",
            "exact220",
            "entropy_or_credit_experiment",
            "leaderboard_or_sota",
        ):
            self.assertFalse(value["authorization"][name])

    def test_unpushed_dirty_parent_or_implementation_fails_closed(self) -> None:
        self.assertIn(
            "v24784_integration_source_commit_not_pushed",
            self.synthetic(head="a" * 40, remote="b" * 40)["findings"],
        )
        self.assertIn(
            "v24784_integration_source_worktree_not_clean",
            self.synthetic(clean=False)["findings"],
        )
        self.assertIn(
            "v24784_inert_protocol_drifted",
            self.synthetic(parent=False)["findings"],
        )
        self.assertIn(
            "v24784_integration_contract_drifted",
            self.synthetic(implementation=False)["findings"],
        )

    def test_leakage_lease_runner_or_future_surface_fails_closed(self) -> None:
        value = self.synthetic(
            findings=(["field"], ["import"], ["marker"], ["secret"]),
            lease=False,
            runners=[123],
            pristine=False,
        )
        for finding in (
            "privileged_runtime_field_access",
            "evaluator_or_gold_import_in_runtime",
            "private_output_or_evaluator_marker_in_runtime",
            "credential_literal_in_runtime",
            "shared_api_lease_active",
            "v24780_or_v24784_runner_active",
            "v24784_future_surface_not_pristine",
        ):
            self.assertIn(finding, value["findings"])

    def test_sources_and_test_count_are_frozen_without_private_paths(self) -> None:
        self.assertFalse(any(path.parts[:1] == ("evaluation",) for path in audit.SOURCES))
        self.assertFalse(any(path.parts[:1] == ("outputs",) for path in audit.SOURCES))
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 57)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 57)

    def test_protocol_still_closes_launch_and_private_reads(self) -> None:
        value = audit._read(audit.PROTOCOL)
        self.assertFalse(value["authorization"]["one_external_forward_launch"])
        self.assertFalse(
            value["source_policy"][
                "v24780_output_prediction_task_result_page_or_visible_task_opened_or_hashed"
            ]
        )
        self.assertFalse(
            value["source_policy"][
                "v24783_private_population_truth_provenance_or_quality_opened_or_hashed"
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
