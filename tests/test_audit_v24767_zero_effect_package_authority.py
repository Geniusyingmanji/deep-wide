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

from scripts import audit_v24767_zero_effect_package_authority as authority  # noqa: E402


class V24767ZeroEffectPackageAuthorityTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        parents: bool = True,
        clean: bool = True,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        lease: bool = True,
        runners: list[int] | None = None,
        implementation: bool = True,
        ast: tuple[list[str], list[str], list[str], list[str]] = ([], [], [], []),
        pristine: bool = True,
    ) -> dict:
        package = authority._package_module()
        suites = [
            {
                "path": str(path),
                "expected": expected,
                "observed": expected,
                "output_sha256": "d" * 64,
                "passed": True,
            }
            for path, expected, _timeout in package.TEST_SUITES
        ]
        with (
            patch.object(authority, "_parents_valid", return_value=parents),
            patch.object(authority, "_sha256", return_value="a" * 64),
            patch.object(authority, "_tracked", return_value=True),
            patch.object(package, "ast_findings", return_value=ast),
            patch.object(package, "implementation_contract", return_value={"valid": implementation}),
            patch.object(authority, "_run_tests", return_value=(74, True, suites)),
            patch.object(
                authority,
                "_git",
                side_effect=[head, remote, "" if clean else " M x"],
            ),
            patch.object(authority.contract, "protected_watcher_snapshot", return_value=[]),
            patch.object(authority, "_lease_inactive", return_value=lease),
            patch.object(authority, "_active_runners", return_value=runners or []),
            patch.object(Path, "exists", return_value=not pristine),
            patch.object(Path, "is_symlink", return_value=False),
            patch.object(authority, "SECRET", __import__("re").compile(r"a^")),
        ):
            return authority.build_authority(now=0)

    def test_synthetic_go_authorizes_only_package_audit_artifact(self) -> None:
        value = self.synthetic()
        authority.validate_authority(value)
        self.assertTrue(
            value["authorization"]["v24766_package_audit_artifact_generation"]
        )
        self.assertFalse(value["authorization"]["preactivation_audit_generation"])
        self.assertFalse(value["authorization"]["external_launch"])
        self.assertFalse(value["authorization"]["private_truth_or_quality_surface_open"])

    def test_unpushed_dirty_or_parent_failure_fails_closed(self) -> None:
        self.assertIn(
            "v24767_source_commit_not_pushed",
            self.synthetic(head="a" * 40, remote="b" * 40)["findings"],
        )
        self.assertIn(
            "v24767_source_worktree_not_clean",
            self.synthetic(clean=False)["findings"],
        )
        self.assertIn(
            "v24763_or_v24764_parent_drifted",
            self.synthetic(parents=False)["findings"],
        )

    def test_label_implementation_lease_runner_or_surface_fails_closed(self) -> None:
        value = self.synthetic(
            implementation=False,
            ast=(["field"], ["import"], ["marker"], ["secret"]),
            lease=False,
            runners=[123],
            pristine=False,
        )
        self.assertIn("v24765_implementation_contract_drifted", value["findings"])
        self.assertIn("privileged_forward_field_access", value["findings"])
        self.assertIn("evaluator_or_gold_import_in_forward", value["findings"])
        self.assertIn("private_or_evaluator_marker_in_forward", value["findings"])
        self.assertIn("credential_literal_in_package", value["findings"])
        self.assertIn("shared_api_lease_active", value["findings"])
        self.assertIn("v24765_runner_active", value["findings"])
        self.assertIn("package_or_downstream_surface_not_pristine", value["findings"])

    def test_source_manifest_excludes_private_and_future_artifacts(self) -> None:
        package = authority._package_module()
        self.assertNotIn(authority.OUTPUT, package.SOURCES)
        self.assertNotIn(authority.PACKAGE_AUDIT, package.SOURCES)
        self.assertTrue(
            all(path.parts[:1] != ("evaluation",) for path in package.SOURCES)
        )
        self.assertEqual(package.EXPECTED_TEST_COUNT, 74)

    def test_resealed_launch_or_preaudit_tamper_is_rejected(self) -> None:
        value = self.synthetic()
        for field in ("external_launch", "preactivation_audit_generation"):
            altered = copy.deepcopy(value)
            altered["authorization"][field] = True
            altered.pop("authority_payload_sha256")
            altered["authority_payload_sha256"] = authority.contract.payload_sha256(
                altered
            )
            with self.assertRaises(RuntimeError):
                authority.validate_authority(altered)

    def test_actual_parent_source_and_label_blind_contract_are_valid(self) -> None:
        package = authority._package_module()
        self.assertTrue(authority._parents_valid())
        self.assertEqual(package.ast_findings(), ([], [], [], []))
        self.assertTrue(package.implementation_contract()["valid"])


if __name__ == "__main__":
    unittest.main()
