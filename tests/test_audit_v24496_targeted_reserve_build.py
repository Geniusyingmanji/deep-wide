from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24496_targeted_reserve_build as target  # noqa: E402


class V24496TargetedReserveBuildAuditTests(unittest.TestCase):
    def test_runtime_ast_is_label_blind(self) -> None:
        accesses: list[str] = []
        imports: list[str] = []
        for path in target.RUNTIME_SOURCES:
            current_accesses, current_imports = target.base.ast_findings(path)
            accesses.extend(current_accesses)
            imports.extend(current_imports)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])

    def test_clean_surface_authorizes_proof_integration_only(self) -> None:
        def git(*args: str) -> str:
            return "" if args == ("status", "--porcelain") else "a" * 40

        with (
            patch.object(target.base, "_git", side_effect=git),
            patch.object(target.base, "_tracked", return_value=True),
            patch.object(target.base, "_run_test", return_value=True),
            patch.object(target.base, "_watcher", return_value=True),
            patch.object(target.base, "_lease_inactive", return_value=True),
        ):
            value = target.build_audit(now=0)
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 35)
        self.assertTrue(
            value["authorization"]["proof_carrying_reserve_integration_design"]
        )
        self.assertFalse(
            value["authorization"]["new_external_gate_design_or_launch"]
        )
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_regression_leakage_watcher_and_lease_fail_closed(self) -> None:
        cases = (
            ("tests", "v24490_96_regression_failed_or_count_drifted"),
            ("access", "privileged_field_access_in_v24496_runtime"),
            ("watcher", "protected_watcher_identity_drifted"),
            ("lease", "shared_api_lease_active"),
        )
        for mode, expected in cases:
            with self.subTest(mode=mode):
                def git(*args: str) -> str:
                    return "" if args == ("status", "--porcelain") else "a" * 40

                ast_value = (
                    (["runtime.py:1:category"], [])
                    if mode == "access"
                    else ([], [])
                )
                with (
                    patch.object(target.base, "_git", side_effect=git),
                    patch.object(target.base, "_tracked", return_value=True),
                    patch.object(target.base, "_run_test", return_value=mode != "tests"),
                    patch.object(target.base, "ast_findings", return_value=ast_value),
                    patch.object(target.base, "_watcher", return_value=mode != "watcher"),
                    patch.object(target.base, "_lease_inactive", return_value=mode != "lease"),
                ):
                    value = target.build_audit(now=0)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["audit_valid"])
                self.assertFalse(
                    value["authorization"][
                        "proof_carrying_reserve_integration_design"
                    ]
                )


if __name__ == "__main__":
    unittest.main()
