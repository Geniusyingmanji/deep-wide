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

from scripts import audit_v24687_worldbank_target_value_build as audit  # noqa: E402


class V24687WorldBankTargetValueBuildAuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        clean: bool = True,
        implementation: bool = True,
        lease_inactive: bool = True,
        active: bool = False,
    ) -> dict:
        tests = iter((True, count) for _path, count, _timeout in audit.TEST_SUITES)
        with (
            patch.object(audit, "_implementation_valid", return_value=implementation),
            patch.object(audit, "_run_test", side_effect=lambda *_args: next(tests)),
            patch.object(audit, "_active", return_value=active),
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

    def test_go_authorizes_only_fresh_disjoint_design(self) -> None:
        value = self.synthetic()
        audit.validate_audit(value)
        self.assertEqual(value["tests"]["test_count"], 32)
        authorization = value["authorization"]
        self.assertTrue(
            authorization["fresh_disjoint_worldbank_population_and_protocol_design"]
        )
        self.assertFalse(authorization["population_gold_or_provenance_publication"])
        self.assertFalse(authorization["preactivation_or_launch"])
        self.assertFalse(authorization["dev64_or_exact220"])

    def test_unpushed_dirty_or_active_lease_fails_closed(self) -> None:
        self.assertIn(
            "v24687_source_commit_not_pushed",
            self.synthetic(head="a" * 40, remote="b" * 40)["findings"],
        )
        self.assertIn(
            "v24687_source_worktree_not_clean",
            self.synthetic(clean=False)["findings"],
        )
        self.assertIn(
            "shared_api_lease_active",
            self.synthetic(lease_inactive=False)["findings"],
        )

    def test_contract_drift_or_active_process_fails_closed(self) -> None:
        self.assertIn(
            "v24686_target_value_contract_drifted",
            self.synthetic(implementation=False)["findings"],
        )
        self.assertIn(
            "v24686_or_v24687_process_active",
            self.synthetic(active=True)["findings"],
        )

    def test_test_count_is_frozen(self) -> None:
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 32)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 32)

    def test_resealed_launch_tamper_fails_closed(self) -> None:
        changed = copy.deepcopy(self.synthetic())
        changed["authorization"]["preactivation_or_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = audit.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(changed)

    def test_resealed_population_publication_tamper_fails_closed(self) -> None:
        changed = copy.deepcopy(self.synthetic())
        changed["authorization"]["population_gold_or_provenance_publication"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = audit.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
