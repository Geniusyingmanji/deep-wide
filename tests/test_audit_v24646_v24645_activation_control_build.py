from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24646_v24645_activation_control_build as audit


class BuildAuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        protocol_valid: bool = True,
        package_valid: bool = True,
    ) -> dict:
        with (
            patch.object(audit, "_protocol_valid", return_value=protocol_valid),
            patch.object(audit, "_package_valid", return_value=package_valid),
            patch.object(audit.common, "_sha256", return_value="a" * 64),
            patch.object(audit.common, "_ordinary", side_effect=lambda path: ROOT / path),
            patch.object(audit.common, "ast_findings", return_value=([], [])),
            patch.object(audit.common, "_run_test", return_value=True),
            patch.object(audit.common, "_git", side_effect=[head, remote, ""]),
            patch.object(audit.common, "_tracked", return_value=True),
            patch.object(audit.common, "_watcher", return_value=True),
            patch.object(audit.common, "_lease_inactive", return_value=True),
            patch.object(Path, "exists", return_value=False),
            patch.object(Path, "is_symlink", return_value=False),
        ):
            return audit.build_audit(now=0)

    def test_synthetic_go_only_authorizes_preaudit(self) -> None:
        value = self.synthetic()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 32)
        self.assertTrue(value["authorization"]["preactivation_audit_generation"])
        self.assertFalse(value["authorization"]["activation_or_launch"])

    def test_unpushed_control_fails_closed(self) -> None:
        value = self.synthetic(head="a" * 40, remote="b" * 40)
        self.assertFalse(value["audit_valid"])
        self.assertIn("v24646_source_commit_not_pushed", value["findings"])

    def test_protocol_failure_fails_closed(self) -> None:
        value = self.synthetic(protocol_valid=False)
        self.assertFalse(value["audit_valid"])
        self.assertIn("v24645_protocol_invalid", value["findings"])

    def test_package_failure_fails_closed(self) -> None:
        value = self.synthetic(package_valid=False)
        self.assertFalse(value["audit_valid"])
        self.assertIn("v24645_package_build_invalid", value["findings"])

    def test_test_count_is_frozen(self) -> None:
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 32)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 32)


if __name__ == "__main__":
    unittest.main()
