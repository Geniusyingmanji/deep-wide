from __future__ import annotations

import copy
import re
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24680_schema_dev64_runtime_build as audit  # noqa: E402


class V24680SchemaDev64RuntimeBuildAuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        clean: bool = True,
        parent: bool = True,
        implementation: bool = True,
        lease_inactive: bool = True,
        active: bool = False,
        pristine: bool = True,
    ) -> dict:
        tests = iter((True, count) for _path, count, _timeout in audit.TEST_SUITES)
        with (
            patch.object(audit, "_parent_valid", return_value=parent),
            patch.object(audit, "_implementation_valid", return_value=implementation),
            patch.object(audit, "_run_test", side_effect=lambda *_args: next(tests)),
            patch.object(audit, "_active", return_value=active),
            patch.object(audit, "_future_pristine", return_value=pristine),
            patch.object(audit.common, "_sha256", return_value="a" * 64),
            patch.object(audit.common, "_ordinary", side_effect=lambda path: ROOT / path),
            patch.object(audit.common, "ast_findings", return_value=([], [])),
            patch.object(
                audit.common,
                "_git",
                side_effect=[head, remote, "" if clean else " M plan.md"],
            ),
            patch.object(audit.common, "_tracked", return_value=True),
            patch.object(audit.common, "_watcher", return_value=True),
            patch.object(audit.common, "_lease_inactive", return_value=lease_inactive),
            patch.object(audit.common, "SECRET", re.compile(r"a^")),
        ):
            return audit.build_audit(now=0)

    def test_synthetic_go_authorizes_contract_publication_only(self) -> None:
        value = self.synthetic()
        audit.validate_audit(value)
        self.assertEqual(value["tests"]["test_count"], 59)
        self.assertTrue(value["authorization"]["forward_contract_publication"])
        self.assertFalse(value["authorization"]["preactivation_or_launch"])
        self.assertFalse(value["authorization"]["evaluator"])

    def test_parent_or_implementation_failure_fails_closed(self) -> None:
        parent = self.synthetic(parent=False)
        implementation = self.synthetic(implementation=False)
        self.assertIn("v24678_build_audit_drifted", parent["findings"])
        self.assertIn(
            "v24679_fixed_denominator_runtime_contract_drifted",
            implementation["findings"],
        )

    def test_unpushed_dirty_or_active_lease_fails_closed(self) -> None:
        unpushed = self.synthetic(head="a" * 40, remote="b" * 40)
        dirty = self.synthetic(clean=False)
        lease = self.synthetic(lease_inactive=False)
        self.assertIn("v24680_source_commit_not_pushed", unpushed["findings"])
        self.assertIn("v24680_source_worktree_not_clean", dirty["findings"])
        self.assertIn("shared_api_lease_active", lease["findings"])

    def test_active_runner_or_nonpristine_surface_fails_closed(self) -> None:
        active = self.synthetic(active=True)
        residue = self.synthetic(pristine=False)
        self.assertIn("v24679_forward_process_already_active", active["findings"])
        self.assertIn("v24679_future_surface_not_pristine", residue["findings"])

    def test_test_count_is_frozen(self) -> None:
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 59)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 59)

    def test_resealed_launch_tamper_fails_closed(self) -> None:
        value = self.synthetic()
        changed = copy.deepcopy(value)
        changed["authorization"]["preactivation_or_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = audit.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
