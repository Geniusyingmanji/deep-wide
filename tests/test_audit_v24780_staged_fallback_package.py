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

from scripts import audit_v24780_staged_fallback_package as audit  # noqa: E402


class V24780StagedFallbackPackageAuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        clean: bool = True,
        parents: bool = True,
        implementation: bool = True,
        findings: tuple[list[str], list[str], list[str], list[str]] = ([], [], [], []),
        lease: bool = True,
        runners: list[int] | None = None,
        pristine: bool = True,
    ) -> dict:
        tests = iter((True, expected, "d" * 64) for _path, expected, _timeout in audit.TEST_SUITES)
        implementation_value = {"valid": implementation}
        with (
            patch.object(audit, "_sha256", return_value="a" * 64),
            patch.object(audit, "_tracked", return_value=True),
            patch.object(audit, "_parents_valid", return_value=parents),
            patch.object(audit, "ast_findings", return_value=findings),
            patch.object(audit, "implementation_contract", return_value=implementation_value),
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

    def test_runtime_ast_manifest_and_implementation_contract_are_clean(self) -> None:
        self.assertEqual(audit.ast_findings(), ([], [], [], []))
        value = audit.implementation_contract()
        self.assertTrue(value["valid"])
        self.assertEqual(value["runtime_owned_visible_entity_scheduler_wrapper_call_count"], 1)
        self.assertEqual(value["entity_count_per_task"], [4] * 8)
        self.assertTrue(
            all(path.parts[:1] != ("evaluation",) for path in audit.SOURCES)
        )

    def test_synthetic_go_only_authorizes_future_preaudit(self) -> None:
        value = self.synthetic()
        audit.validate_audit(value)
        self.assertTrue(value["audit_valid"])
        self.assertTrue(value["authorization"]["preactivation_audit_generation"])
        self.assertFalse(value["authorization"]["activation"])
        self.assertFalse(value["authorization"]["external_launch"])
        self.assertFalse(value["authorization"]["private_truth_or_quality_surface_open"])

    def test_unpushed_dirty_parent_or_implementation_fails_closed(self) -> None:
        self.assertIn(
            "v24780_source_commit_not_pushed",
            self.synthetic(head="a" * 40, remote="b" * 40)["findings"],
        )
        self.assertIn(
            "v24780_source_worktree_not_clean",
            self.synthetic(clean=False)["findings"],
        )
        self.assertIn(
            "v24780_protocol_or_readiness_parent_drifted",
            self.synthetic(parents=False)["findings"],
        )
        self.assertIn(
            "v24780_implementation_contract_drifted",
            self.synthetic(implementation=False)["findings"],
        )

    def test_label_secret_lease_runner_or_surface_fails_closed(self) -> None:
        value = self.synthetic(
            findings=(["field"], ["import"], ["marker"], ["secret"]),
            lease=False,
            runners=[123],
            pristine=False,
        )
        self.assertIn("privileged_forward_field_access", value["findings"])
        self.assertIn("evaluator_or_gold_import_in_forward", value["findings"])
        self.assertIn("private_or_evaluator_marker_in_forward", value["findings"])
        self.assertIn("credential_literal_in_forward", value["findings"])
        self.assertIn("shared_api_lease_active", value["findings"])
        self.assertIn("v24780_runner_active", value["findings"])
        self.assertIn("future_surface_not_pristine", value["findings"])

    def test_expected_test_count_and_source_set_are_frozen(self) -> None:
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 94)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 94)
        self.assertNotIn(audit.AUDIT, audit.SOURCES)
        self.assertNotIn(audit.READINESS, audit.SOURCES)
        self.assertFalse(any("private" in path.name and "execution_contract" not in path.name for path in audit.SOURCES))

    def test_resealed_launch_or_private_surface_tamper_is_rejected(self) -> None:
        value = self.synthetic()
        for field in ("external_launch", "private_truth_or_quality_surface_open"):
            altered = copy.deepcopy(value)
            altered["authorization"][field] = True
            altered.pop("audit_payload_sha256")
            altered["audit_payload_sha256"] = audit.contract.payload_sha256(altered)
            with self.assertRaises(RuntimeError):
                audit.validate_audit(altered)


if __name__ == "__main__":
    unittest.main()
