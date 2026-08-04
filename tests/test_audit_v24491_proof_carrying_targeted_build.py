from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24491_proof_carrying_targeted_build as target  # noqa: E402


class V24491ProofCarryingTargetedBuildAuditTests(unittest.TestCase):
    def test_ast_audit_is_label_blind(self) -> None:
        accesses: list[str] = []
        imports: list[str] = []
        for path in target.RUNTIME_SOURCES:
            current_accesses, current_imports = target.ast_findings(path)
            accesses.extend(current_accesses)
            imports.extend(current_imports)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])

    def test_audit_passes_with_frozen_regressions_and_runtime_state(self) -> None:
        with patch.object(target, "_run_test", return_value=True):
            value = target.build_audit(now=0)
        self.assertEqual(value["findings"], [])
        self.assertTrue(value["tests"]["passed"])
        self.assertEqual(value["tests"]["test_count"], 21)
        self.assertTrue(value["label_blind_audit"]["passed"])
        self.assertTrue(value["authorization"]["v24491_build_go"])
        self.assertTrue(value["authorization"]["new_external_gate_design"])
        self.assertFalse(value["authorization"]["new_external_gate_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_regression_privileged_and_watcher_failures_close_gate(self) -> None:
        cases = (
            ("tests", "v24490_91_regression_failed_or_count_drifted"),
            ("access", "privileged_field_access_in_v24490_91_runtime"),
            ("watcher", "protected_watcher_identity_drifted"),
            ("lease", "shared_api_lease_active"),
        )
        for mode, expected in cases:
            with self.subTest(mode=mode):
                run = True if mode != "tests" else False
                ast_value = (
                    (["runtime.py:1:category"], [])
                    if mode == "access"
                    else ([], [])
                )
                watcher = mode != "watcher"
                lease = mode != "lease"
                with (
                    patch.object(target, "_run_test", return_value=run),
                    patch.object(target, "ast_findings", return_value=ast_value),
                    patch.object(target, "_watcher", return_value=watcher),
                    patch.object(target, "_lease_inactive", return_value=lease),
                ):
                    value = target.build_audit(now=0)
                self.assertIn(expected, value["findings"])
                self.assertFalse(value["authorization"]["v24491_build_go"])
                self.assertFalse(value["authorization"]["new_external_gate_design"])


if __name__ == "__main__":
    unittest.main()
