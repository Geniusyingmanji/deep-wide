from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24649_unknown_target_structured_build as audit


class BuildAuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        parent_valid: bool = True,
        implementation_valid: bool = True,
    ) -> dict:
        with (
            patch.object(audit, "_parent_valid", return_value=parent_valid),
            patch.object(
                audit, "_implementation_valid", return_value=implementation_valid
            ),
            patch.object(audit.common, "_sha256", return_value="a" * 64),
            patch.object(audit.common, "_ordinary", side_effect=lambda path: ROOT / path),
            patch.object(audit.common, "ast_findings", return_value=([], [])),
            patch.object(audit.common, "_run_test", return_value=True),
            patch.object(audit.common, "_git", side_effect=[head, remote, ""]),
            patch.object(audit.common, "_tracked", return_value=True),
            patch.object(audit.common, "_watcher", return_value=True),
            patch.object(audit.common, "_lease_inactive", return_value=True),
        ):
            return audit.build_audit(now=0)

    def test_synthetic_go_only_authorizes_fresh_design(self) -> None:
        value = self.synthetic()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["findings"], [])
        self.assertEqual(value["tests"]["test_count"], 50)
        self.assertTrue(
            value["authorization"]["fresh_external_population_and_protocol_design"]
        )
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(value["authorization"]["evaluator_access"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_parent_or_implementation_failure_fails_closed(self) -> None:
        parent = self.synthetic(parent_valid=False)
        implementation = self.synthetic(implementation_valid=False)
        self.assertIn("v24647_parent_diagnosis_drifted", parent["findings"])
        self.assertIn(
            "v24648_implementation_contract_drifted", implementation["findings"]
        )
        self.assertFalse(parent["audit_valid"])
        self.assertFalse(implementation["audit_valid"])

    def test_unpushed_source_fails_closed(self) -> None:
        value = self.synthetic(head="a" * 40, remote="b" * 40)
        self.assertFalse(value["audit_valid"])
        self.assertIn("v24649_source_commit_not_pushed", value["findings"])

    def test_test_count_is_frozen(self) -> None:
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 50)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 50)

    def test_authorization_tamper_changes_seal(self) -> None:
        value = self.synthetic()
        seal = value.pop("audit_payload_sha256")
        value["authorization"]["fresh_external_activation_or_launch"] = True
        self.assertNotEqual(audit.payload_sha256(value), seal)


if __name__ == "__main__":
    unittest.main()
