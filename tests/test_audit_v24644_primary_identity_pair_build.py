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

from scripts import audit_v24644_primary_identity_pair_build as audit


class AuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        implementation_valid: bool = True,
    ) -> dict:
        with (
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
        self.assertEqual(value["tests"]["test_count"], 44)
        self.assertTrue(
            value["authorization"]["fresh_external_population_and_protocol_design"]
        )
        self.assertFalse(value["authorization"]["fresh_external_activation_or_launch"])
        self.assertFalse(value["authorization"]["paired_dev64_or_exact220"])

    def test_unpushed_source_fails_closed(self) -> None:
        value = self.synthetic(head="a" * 40, remote="b" * 40)
        self.assertFalse(value["audit_valid"])
        self.assertIn("v24644_source_commit_not_pushed", value["findings"])

    def test_private_binding_drift_fails_closed(self) -> None:
        value = self.synthetic(implementation_valid=False)
        self.assertFalse(value["audit_valid"])
        self.assertIn("v24644_private_frozen_binding_drifted", value["findings"])

    def test_test_count_is_frozen(self) -> None:
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 44)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 44)

    def test_authorization_tamper_changes_seal(self) -> None:
        value = self.synthetic()
        seal = value.pop("audit_payload_sha256")
        value["authorization"]["fresh_external_activation_or_launch"] = True
        self.assertNotEqual(audit.payload_sha256(value), seal)


if __name__ == "__main__":
    unittest.main()
