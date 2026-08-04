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

from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from scripts import audit_v24439_bounded_narrative_build as target  # noqa: E402


class V24439BoundedNarrativeBuildAuditTests(unittest.TestCase):
    def build_clean(self) -> dict:
        def clean_git(*args: str) -> str:
            if args in (("rev-parse", "HEAD"), ("rev-parse", "target/main")):
                return "a" * 40
            if args == ("status", "--porcelain"):
                return ""
            raise AssertionError(args)

        with (
            patch.object(target.base, "_tracked", return_value=True),
            patch.object(target.base, "_git", side_effect=clean_git),
            patch.object(target.base, "_run_test", return_value=True),
            patch.object(
                target,
                "protected_watcher_snapshot",
                return_value=target.EXPECTED_WATCHERS,
            ),
            patch.object(target, "lease_observation", return_value={"active": False}),
        ):
            return target.build_audit(now=0)

    def test_runtime_sources_have_no_privileged_access_or_evaluator_import(self) -> None:
        for path in target.RUNTIME_SOURCES:
            with self.subTest(path=path):
                accesses, imports = target.base._ast_findings(path)
                self.assertEqual(accesses, [])
                self.assertEqual(imports, [])

    def test_build_audit_is_valid_after_sources_are_pushed(self) -> None:
        value = self.build_clean()
        target.validate_audit(value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertEqual(value["tests"]["test_count"], 87)
        self.assertTrue(value["tests"]["passed"])
        self.assertEqual(value["privileged_field_accesses"], [])
        self.assertEqual(value["evaluator_imports"], [])
        self.assertEqual(value["credential_literal_hits"], [])
        self.assertTrue(
            value["authorization"]["fresh_bounded_narrative_external_probe_design"]
        )
        for name in (
            "external_probe_launch",
            "paired_dev64",
            "exact220",
            "evaluator",
            "leaderboard_or_sota",
        ):
            self.assertFalse(value["authorization"][name])

    def test_resealed_launch_authorization_tamper_fails(self) -> None:
        value = self.build_clean()
        altered = copy.deepcopy(value)
        altered["authorization"]["external_probe_launch"] = True
        altered.pop("audit_payload_sha256")
        altered["audit_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(RuntimeError):
            target.validate_audit(altered)

    def test_privileged_or_secret_finding_closes_design(self) -> None:
        with (
            patch.object(
                target.base,
                "_ast_findings",
                return_value=(["runtime.py:1:ground_truth"], []),
            ),
            patch.object(
                target,
                "SECRET",
                type("SecretMatcher", (), {"search": lambda self, text: True})(),
            ),
            patch.object(target.base, "_tracked", return_value=True),
            patch.object(target.base, "_run_test", return_value=True),
            patch.object(
                target.base,
                "_git",
                side_effect=lambda *args: ""
                if args == ("status", "--porcelain")
                else "a" * 40,
            ),
            patch.object(
                target,
                "protected_watcher_snapshot",
                return_value=target.EXPECTED_WATCHERS,
            ),
            patch.object(target, "lease_observation", return_value={"active": False}),
        ):
            value = target.build_audit(now=0)
        self.assertFalse(value["audit_valid"])
        self.assertFalse(
            value["authorization"]["fresh_bounded_narrative_external_probe_design"]
        )
        self.assertIn("privileged_field_access_in_v24436_38_runtime", value["findings"])
        self.assertIn("credential_literal_in_v24436_39_surface", value["findings"])


if __name__ == "__main__":
    unittest.main()
