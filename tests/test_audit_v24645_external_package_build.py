from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24645_external_package_build as audit


class AuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        parent_valid: bool = True,
        literals: list[str] | None = None,
    ) -> dict:
        with (
            patch.object(audit, "_parent_valid", return_value=parent_valid),
            patch.object(
                audit,
                "_forward_capability_findings",
                return_value=([], [], literals or []),
            ),
            patch.object(audit.runtime, "binding_is_private_and_stable", return_value=True),
            patch.object(audit.common, "_sha256", return_value="a" * 64),
            patch.object(audit.common, "_ordinary", side_effect=lambda path: ROOT / path),
            patch.object(audit.common, "_run_test", return_value=True),
            patch.object(audit.common, "_git", side_effect=[head, remote, ""]),
            patch.object(audit.common, "_tracked", return_value=True),
            patch.object(audit.common, "_watcher", return_value=True),
            patch.object(audit.common, "_lease_inactive", return_value=True),
            patch.object(Path, "exists", return_value=False),
            patch.object(Path, "is_symlink", return_value=False),
        ):
            return audit.build_audit(now=0)

    def test_synthetic_go_only_authorizes_protocol_publication(self) -> None:
        value = self.synthetic()
        self.assertTrue(value["audit_valid"])
        self.assertEqual(value["tests"]["test_count"], 31)
        self.assertTrue(value["authorization"]["external_protocol_publication"])
        self.assertFalse(value["authorization"]["preactivation_audit"])
        self.assertFalse(value["authorization"]["activation_or_launch"])

    def test_unpushed_source_fails_closed(self) -> None:
        value = self.synthetic(head="a" * 40, remote="b" * 40)
        self.assertFalse(value["audit_valid"])
        self.assertIn("v24645_source_commit_not_pushed", value["findings"])

    def test_population_parent_failure_fails_closed(self) -> None:
        value = self.synthetic(parent_valid=False)
        self.assertFalse(value["audit_valid"])
        self.assertIn("v24645_population_parent_invalid", value["findings"])

    def test_private_literal_fails_closed(self) -> None:
        value = self.synthetic(literals=["runner:evaluation/"])
        self.assertFalse(value["audit_valid"])
        self.assertIn("private_or_evaluator_literal_in_v24645_forward", value["findings"])

    def test_test_count_and_authorization_are_frozen(self) -> None:
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 31)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 31)


if __name__ == "__main__":
    unittest.main()
