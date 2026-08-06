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

from scripts import audit_v24689_worldbank_population_design_build as audit  # noqa: E402


class V24689WorldBankPopulationDesignBuildAuditTests(unittest.TestCase):
    def synthetic(
        self,
        *,
        head: str = "c" * 40,
        remote: str = "c" * 40,
        clean: bool = True,
        parent: bool = True,
        lease_inactive: bool = True,
        pristine: bool = True,
    ) -> dict:
        tests = iter((True, count) for _path, count, _timeout in audit.TEST_SUITES)
        with (
            patch.object(audit.design, "_parent_valid", return_value=parent),
            patch.object(audit, "_run_test", side_effect=lambda *_args: next(tests)),
            patch.object(audit.common, "_sha256", return_value="a" * 64),
            patch.object(audit.common, "_ordinary", side_effect=lambda path: ROOT / path),
            patch.object(
                audit.common,
                "_git",
                side_effect=[head, remote, "" if clean else " M plan.md"],
            ),
            patch.object(audit.common, "_tracked", return_value=True),
            patch.object(audit.common, "_watcher", return_value=True),
            patch.object(audit.common, "_lease_inactive", return_value=lease_inactive),
            patch.object(audit.common, "SECRET", re.compile(r"a^")),
            patch.object(Path, "exists", return_value=not pristine),
            patch.object(Path, "is_symlink", return_value=False),
        ):
            return audit.build_audit(now=0)

    def test_go_authorizes_one_population_design_publication_only(self) -> None:
        value = self.synthetic()
        audit.validate_audit(value)
        self.assertEqual(value["tests"]["test_count"], 12)
        authorization = value["authorization"]
        self.assertTrue(authorization["one_population_design_publication"])
        self.assertFalse(authorization["forward_or_evaluator_surface_publication"])
        self.assertFalse(authorization["preactivation_or_launch"])

    def test_unpushed_dirty_or_active_lease_fails_closed(self) -> None:
        self.assertIn(
            "v24689_source_commit_not_pushed",
            self.synthetic(head="a" * 40, remote="b" * 40)["findings"],
        )
        self.assertIn(
            "v24689_source_worktree_not_clean",
            self.synthetic(clean=False)["findings"],
        )
        self.assertIn(
            "shared_api_lease_active",
            self.synthetic(lease_inactive=False)["findings"],
        )

    def test_parent_or_population_residue_fails_closed(self) -> None:
        self.assertIn(
            "v24687_parent_build_audit_drifted",
            self.synthetic(parent=False)["findings"],
        )
        self.assertIn(
            "v24688_population_surface_not_pristine",
            self.synthetic(pristine=False)["findings"],
        )

    def test_test_count_is_frozen(self) -> None:
        self.assertEqual(sum(count for _path, count, _timeout in audit.TEST_SUITES), 12)
        self.assertEqual(audit.EXPECTED_TEST_COUNT, 12)

    def test_resealed_launch_tamper_fails_closed(self) -> None:
        changed = copy.deepcopy(self.synthetic())
        changed["authorization"]["preactivation_or_launch"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = audit.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(changed)

    def test_resealed_evaluator_publication_tamper_fails_closed(self) -> None:
        changed = copy.deepcopy(self.synthetic())
        changed["authorization"]["forward_or_evaluator_surface_publication"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = audit.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            audit.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
