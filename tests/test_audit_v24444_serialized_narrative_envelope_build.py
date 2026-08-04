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
from scripts import audit_v24444_serialized_narrative_envelope_build as target  # noqa: E402


class V24444SerializedNarrativeEnvelopeBuildAuditTests(unittest.TestCase):
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

    def test_runtime_surface_has_no_privileged_or_evaluator_hits(self) -> None:
        for path in target.RUNTIME_SOURCES:
            accesses, imports = target.base._ast_findings(path)
            self.assertEqual(accesses, [])
            self.assertEqual(imports, [])

    def test_clean_build_authorizes_only_fresh_successor_design(self) -> None:
        value = self.build_clean()
        target.validate_audit(value)
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 100)
        self.assertTrue(value["tests"]["passed"])
        self.assertEqual(
            value["failed_gate_evidence"]["parent_result_envelope_invalid"], 16
        )
        self.assertTrue(value["repair_evidence"]["canonical_json_value_preserved"])
        self.assertTrue(
            value["authorization"][
                "fresh_serialization_fixed_external_probe_design"
            ]
        )
        for name in (
            "external_probe_launch",
            "v24442_rerun",
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

    def test_privileged_finding_closes_successor_design(self) -> None:
        with patch.object(
            target.base,
            "_ast_findings",
            return_value=(["runtime.py:1:ground_truth"], []),
        ):
            value = self.build_clean()
        self.assertFalse(value["audit_valid"])
        self.assertIn("privileged_field_access_in_v24443_runtime", value["findings"])
        self.assertFalse(
            value["authorization"][
                "fresh_serialization_fixed_external_probe_design"
            ]
        )


if __name__ == "__main__":
    unittest.main()
