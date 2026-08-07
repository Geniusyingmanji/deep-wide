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

from scripts import audit_v24784_projection_funnel_control_plane_readiness as audit  # noqa: E402


class V24784ProjectionFunnelControlPlaneReadinessTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        parents: bool = True,
        implementation: bool = True,
        findings: tuple[list[str], list[str], list[str], list[str]] = ([], [], [], []),
        tests: bool = True,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        clean: bool = True,
        tracked: bool = True,
        endpoint: bool = True,
        lease: bool = True,
        runners: list[int] | None = None,
        pristine: bool = True,
    ) -> dict:
        suites = [
            {
                "path": str(path),
                "expected": expected,
                "observed": expected,
                "output_sha256": "d" * 64,
                "passed": tests,
            }
            for path, expected in audit.TEST_SUITES
        ]
        with (
            patch.object(audit, "_manifest", return_value={"x": "a" * 64}),
            patch.object(audit, "_sha256", return_value="b" * 64),
            patch.object(audit, "_parents_valid", return_value=parents),
            patch.object(audit, "ast_findings", return_value=findings),
            patch.object(
                audit,
                "implementation_contract",
                return_value={"valid": implementation},
            ),
            patch.object(
                audit,
                "_run_tests",
                return_value=(tests, audit.EXPECTED_TESTS, suites),
            ),
            patch.object(
                audit,
                "_git",
                side_effect=[head, remote, "" if clean else " M plan.md"],
            ),
            patch.object(audit, "_tracked", return_value=tracked),
            patch.object(audit.contract, "protected_watcher_snapshot", return_value=[]),
            patch.object(audit, "_endpoint", return_value=endpoint),
            patch.object(audit, "_lease_inactive", return_value=lease),
            patch.object(audit, "_active_runners", return_value=runners or []),
            patch.object(Path, "exists", return_value=not pristine),
            patch.object(Path, "is_symlink", return_value=False),
        ):
            return audit.build_audit(now=0)

    def test_actual_parents_ast_and_implementation_are_valid(self) -> None:
        self.assertTrue(audit._parents_valid())
        self.assertEqual(audit.ast_findings(), ([], [], [], []))
        value = audit.implementation_contract()
        self.assertTrue(value["valid"])
        self.assertEqual(value["task_count"], 8)
        self.assertEqual(value["forward_status_vocabulary"], [
            "validated", "private_catalog_absent", "base_runtime_failure",
            "funnel_validation_failure", "parent_failure",
        ])
        self.assertEqual(value["trusted_integration_call_count"], 1)

    def test_go_authorizes_only_package_audit_generation(self) -> None:
        value = self.synthetic()
        with (
            patch.object(audit, "_manifest", return_value=value["source_manifest"]),
            patch.object(
                audit,
                "_sha256",
                side_effect=[
                    value["protocol_sha256"],
                    value["integration_build_sha256"],
                ],
            ),
        ):
            audit.validate_audit(value)
        self.assertEqual(value["tests"]["observed"], 63)
        self.assertTrue(value["authorization"]["package_audit_artifact_generation"])
        for name in (
            "preactivation_audit_generation",
            "activation",
            "execution_start",
            "external_launch",
            "private_truth_or_quality_surface_open",
            "paired_dev64",
            "exact220",
            "entropy_or_credit_experiment",
            "leaderboard_or_sota",
        ):
            self.assertFalse(value["authorization"][name])

    def test_parent_implementation_or_regression_failure_fails_closed(self) -> None:
        self.assertIn(
            "v24784_protocol_or_integration_parent_invalid",
            self.synthetic(parents=False)["findings"],
        )
        self.assertIn(
            "v24784_execution_package_contract_drifted",
            self.synthetic(implementation=False)["findings"],
        )
        self.assertIn(
            "regression_failed_or_count_drifted",
            self.synthetic(tests=False)["findings"],
        )

    def test_leakage_endpoint_lease_runner_or_future_surface_fails_closed(self) -> None:
        value = self.synthetic(
            findings=(["field"], ["import"], ["marker"], ["secret"]),
            endpoint=False,
            lease=False,
            runners=[123],
            pristine=False,
        )
        for finding in (
            "privileged_forward_field_access",
            "evaluator_or_gold_import_in_forward",
            "private_or_old_output_marker_in_forward",
            "credential_literal_in_forward",
            "gpt56_endpoint_unreachable",
            "shared_api_lease_active",
            "v24784_runner_active",
            "future_surface_not_pristine",
        ):
            self.assertIn(finding, value["findings"])

    def test_unpushed_dirty_or_untracked_source_fails_closed(self) -> None:
        self.assertIn(
            "source_commit_not_pushed",
            self.synthetic(head="a" * 40, remote="b" * 40)["findings"],
        )
        self.assertIn("source_worktree_not_clean", self.synthetic(clean=False)["findings"])
        self.assertIn("source_not_tracked", self.synthetic(tracked=False)["findings"])

    def test_source_and_test_manifests_exclude_private_paths(self) -> None:
        self.assertFalse(any(path.parts[:1] == ("evaluation",) for path in audit.SOURCES))
        self.assertFalse(any(path.parts[:1] == ("outputs",) for path in audit.SOURCES))
        self.assertEqual(sum(count for _path, count in audit.TEST_SUITES), 63)
        self.assertEqual(audit.EXPECTED_TESTS, 63)

    def test_resealed_launch_tamper_and_create_only_publish_are_rejected(self) -> None:
        value = self.synthetic()
        changed = copy.deepcopy(value)
        changed["authorization"]["external_launch"] = True
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
