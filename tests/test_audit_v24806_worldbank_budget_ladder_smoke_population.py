from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    audit_v24806_worldbank_budget_ladder_smoke_population as target,
)


class V24806PopulationAuditTests(unittest.TestCase):
    def test_controlled_predecessor_failure_is_before_every_effect(self) -> None:
        self.assertEqual(target.controlled_predecessor_failure_replay(), {
            "failure_type": "RuntimeError",
            "failure_message": "V2.48.05 population publication requires clean pushed HEAD",
            "authorization_checks": 0,
            "network_fetch_calls": 0,
            "publication_calls": 0,
        })

    def test_failure_audit_is_narrow_and_sealed(self) -> None:
        value = target.build_failure_audit(now=1)
        target.validate_failure_audit(value)
        self.assertTrue(
            value["authorization"]["append_only_clean_gate_successor_build_audit"]
        )
        self.assertFalse(value["authorization"]["population_publication"])
        self.assertFalse(value["authorization"]["smoke_launch"])

    def test_clean_gate_rejects_every_other_status(self) -> None:
        with patch.object(target.design.base, "_git", return_value=""):
            self.assertTrue(target.design._clean_except_local_research_tmp())
        with patch.object(
            target.design.base, "_git", return_value="?? .research/tmp/"
        ):
            self.assertTrue(target.design._clean_except_local_research_tmp())
        for status in (" M plan.md", "?? other/", "?? .research/tmp/\n?? other/"):
            with self.subTest(status=status), patch.object(
                target.design.base, "_git", return_value=status
            ):
                self.assertFalse(target.design._clean_except_local_research_tmp())

    def test_successor_preserves_population_algorithm_and_policy(self) -> None:
        self.assertEqual(target.design.base.TARGETS, target.predecessor.TARGETS)
        self.assertEqual(
            target.design.base.STRATUM_VECTOR, target.predecessor.STRATUM_VECTOR
        )
        self.assertEqual(target.design.base.POLICY, target.predecessor.POLICY)
        self.assertIs(
            target.design.base.select_population,
            target.predecessor.select_population,
        )

    def test_resealed_build_authority_escalation_fails(self) -> None:
        value = {
            "artifact_version": 1,
            "role": "v24806_worldbank_budget_ladder_smoke_population_build_audit",
            "audit_valid": True,
            "findings": [],
            "checks": {"synthetic_contract_check": True},
            "authorization": {
                "one_smoke_population_publication": True,
                "smoke_protocol_design": False,
                "smoke_launch": False,
                "main_calibration_lock_validation_or_confirmatory_launch": False,
                "evaluator_access": False,
                "public_dev64_or_exact220": False,
            },
        }
        value["audit_payload_sha256"] = target.payload_sha256(value)
        target.validate_audit(value)
        changed = copy.deepcopy(value)
        changed["authorization"]["smoke_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
