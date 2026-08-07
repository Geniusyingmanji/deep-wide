from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24784_projection_funnel_package as audit  # noqa: E402


class V24784ProjectionFunnelPackageAuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        clean: bool = True,
        tracked: bool = True,
        parents: bool = True,
        implementation: bool = True,
        findings: tuple[list[str], list[str], list[str], list[str]] = ([], [], [], []),
        tests: bool = True,
        lease: bool = True,
        runners: list[int] | None = None,
        pristine: bool = True,
    ) -> dict:
        suites = iter(
            (tests, expected, "d" * 64)
            for _path, expected, _timeout in audit.TEST_SUITES
        )
        implementation_value = audit.implementation_contract()
        implementation_value["valid"] = implementation
        watchers = [
            {"pid": pid, "start_ticks": ticks, "marker": marker}
            for pid, ticks, marker in audit.contract.PROTECTED_WATCHERS
        ]
        with (
            patch.object(audit, "_manifest", return_value={"x": "a" * 64}),
            patch.object(audit, "_sha256", return_value="b" * 64),
            patch.object(audit, "_tracked", return_value=tracked),
            patch.object(audit, "_parents_valid", return_value=parents),
            patch.object(audit, "ast_findings", return_value=findings),
            patch.object(
                audit,
                "implementation_contract",
                return_value=implementation_value,
            ),
            patch.object(audit, "_run_test", side_effect=lambda *_args: next(suites)),
            patch.object(
                audit,
                "_git",
                side_effect=[head, remote, "" if clean else " M plan.md"],
            ),
            patch.object(
                audit.contract, "protected_watcher_snapshot", return_value=watchers
            ),
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
        self.assertEqual(value["entity_count_per_task"], [4] * 8)
        self.assertTrue(value["task_local_joint_replay_present"])

    def test_go_authorizes_only_preactivation_audit_generation(self) -> None:
        value = self.synthetic()
        with (
            patch.object(audit, "_manifest", return_value=value["source_manifest"]),
            patch.object(audit, "_sha256", return_value="b" * 64),
            patch.object(
                audit,
                "implementation_contract",
                return_value=value["implementation_contract"],
            ),
        ):
            audit.validate_audit(value)
        self.assertTrue(value["authorization"]["preactivation_audit_generation"])
        for name in (
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

    def test_unpushed_dirty_untracked_parent_or_implementation_fails_closed(self) -> None:
        self.assertIn(
            "v24784_source_commit_not_pushed",
            self.synthetic(head="a" * 40, remote="b" * 40)["findings"],
        )
        self.assertIn(
            "v24784_source_worktree_not_clean",
            self.synthetic(clean=False)["findings"],
        )
        self.assertIn("v24784_source_not_tracked", self.synthetic(tracked=False)["findings"])
        self.assertIn(
            "v24784_protocol_or_readiness_parent_drifted",
            self.synthetic(parents=False)["findings"],
        )
        self.assertIn(
            "v24784_implementation_contract_drifted",
            self.synthetic(implementation=False)["findings"],
        )

    def test_label_secret_test_lease_runner_or_surface_fails_closed(self) -> None:
        value = self.synthetic(
            findings=(["field"], ["import"], ["marker"], ["secret"]),
            tests=False,
            lease=False,
            runners=[123],
            pristine=False,
        )
        for finding in (
            "privileged_forward_field_access",
            "evaluator_or_gold_import_in_forward",
            "private_or_old_output_marker_in_forward",
            "credential_literal_in_forward",
            "regression_failed_or_count_drifted",
            "shared_api_lease_active",
            "v24784_runner_active",
            "future_surface_not_pristine",
        ):
            self.assertIn(finding, value["findings"])

    def test_expected_tests_and_manifest_exclude_private_surfaces(self) -> None:
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 131)
        self.assertEqual(audit.EXPECTED_TESTS, 131)
        self.assertNotIn(audit.OUTPUT, audit.SOURCES)
        self.assertFalse(any(path.parts[:1] == ("evaluation",) for path in audit.SOURCES))
        self.assertFalse(any(path.parts[:1] == ("outputs",) for path in audit.SOURCES))
        self.assertFalse(any("private_population" in path.as_posix() for path in audit.SOURCES))

    def test_resealed_launch_or_private_surface_tamper_is_rejected(self) -> None:
        value = self.synthetic()
        for field in ("external_launch", "private_truth_or_quality_surface_open"):
            altered = copy.deepcopy(value)
            altered["authorization"][field] = True
            altered.pop("audit_payload_sha256")
            altered["audit_payload_sha256"] = audit.contract.payload_sha256(altered)
            with (
                patch.object(audit, "_manifest", return_value=altered["source_manifest"]),
                patch.object(audit, "_sha256", return_value="b" * 64),
                patch.object(
                    audit,
                    "implementation_contract",
                    return_value=altered["implementation_contract"],
                ),
            ):
                with self.assertRaises(RuntimeError):
                    audit.validate_audit(altered)

    def test_source_manifest_rebind_is_rejected(self) -> None:
        value = self.synthetic()
        altered = copy.deepcopy(value)
        altered["source_manifest"] = {"x": "e" * 64}
        altered["source_manifest_sha256"] = audit.contract.payload_sha256(
            altered["source_manifest"]
        )
        altered.pop("audit_payload_sha256")
        altered["audit_payload_sha256"] = audit.contract.payload_sha256(altered)
        with (
            patch.object(audit, "_manifest", return_value=value["source_manifest"]),
            patch.object(audit, "_sha256", return_value="b" * 64),
            patch.object(
                audit,
                "implementation_contract",
                return_value=value["implementation_contract"],
            ),
        ):
            with self.assertRaises(RuntimeError):
                audit.validate_audit(altered)


if __name__ == "__main__":
    unittest.main()
