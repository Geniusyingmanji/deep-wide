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

from scripts import audit_v24782_projection_funnel_build as audit  # noqa: E402


class V24782ProjectionFunnelBuildAuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        clean: bool = True,
        parent: bool = True,
        implementation: bool = True,
        findings: tuple[list[str], list[str], list[str], list[str]] = ([], [], [], []),
        lease: bool = True,
        runners: list[int] | None = None,
        pristine: bool = True,
    ) -> dict:
        tests = iter(
            (True, expected, "d" * 64)
            for _path, expected, _timeout in audit.TEST_SUITES
        )
        with (
            patch.object(audit, "_sha256", return_value="a" * 64),
            patch.object(audit, "_tracked", return_value=True),
            patch.object(audit, "_parent_valid", return_value=parent),
            patch.object(audit, "ast_findings", return_value=findings),
            patch.object(
                audit,
                "implementation_contract",
                return_value={"valid": implementation},
            ),
            patch.object(audit, "_run_test", side_effect=lambda *_args: next(tests)),
            patch.object(
                audit,
                "_git",
                side_effect=[head, remote, "" if clean else " M x"],
            ),
            patch.object(audit.contract, "protected_watcher_snapshot", return_value=[]),
            patch.object(audit, "_lease_inactive", return_value=lease),
            patch.object(audit, "_active_runners", return_value=runners or []),
            patch.object(Path, "exists", return_value=not pristine),
            patch.object(Path, "is_symlink", return_value=False),
        ):
            return audit.build_audit(now=0)

    def test_actual_parent_ast_and_implementation_contract_are_clean(self) -> None:
        self.assertTrue(audit._parent_valid())
        self.assertEqual(audit.ast_findings(), ([], [], [], []))
        implementation = audit.implementation_contract()
        self.assertTrue(implementation["valid"])
        self.assertEqual(len(implementation["fixed_reason_partition"]), 7)
        self.assertEqual(len(implementation["fixed_count_fields"]), 25)

    def test_synthetic_go_authorizes_only_fresh_design(self) -> None:
        value = self.synthetic()
        audit.validate_audit(value)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(
            value["authorization"][
                "fresh_disjoint_population_and_inert_protocol_design"
            ]
        )
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(value["authorization"]["same_population_forward_retry_resume_or_rerun"])
        self.assertFalse(value["authorization"]["v24780_private_output_or_quality_surface_open"])

    def test_dirty_unpushed_parent_or_implementation_fails_closed(self) -> None:
        self.assertIn(
            "v24782_source_commit_not_pushed",
            self.synthetic(head="a" * 40, remote="b" * 40)["findings"],
        )
        self.assertIn(
            "v24782_source_worktree_not_clean",
            self.synthetic(clean=False)["findings"],
        )
        self.assertIn(
            "v24780_content_free_parent_drifted",
            self.synthetic(parent=False)["findings"],
        )
        self.assertIn(
            "v24781_implementation_contract_drifted",
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
            "v24780_v24783_or_v24784_runner_active",
            "future_surface_not_pristine",
        ):
            self.assertIn(finding, value["findings"])

    def test_expected_test_count_and_sources_are_frozen(self) -> None:
        self.assertEqual(
            sum(count for _path, count, _timeout in audit.TEST_SUITES), 51
        )
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 51)
        self.assertNotIn(audit.AUDIT, audit.SOURCES)
        self.assertFalse(any(path.parts[:1] == ("evaluation",) for path in audit.SOURCES))

    def test_resealed_launch_tamper_and_create_only_publish_are_rejected(self) -> None:
        value = self.synthetic()
        altered = copy.deepcopy(value)
        altered["authorization"]["fresh_external_activation_or_launch"] = True
        altered.pop("audit_payload_sha256")
        altered["audit_payload_sha256"] = audit.contract.payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(altered)
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            audit.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                audit.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
