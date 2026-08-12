from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25213_population_selector_build as target  # noqa: E402


class V25213PopulationSelectorBuildAuditTests(unittest.TestCase):
    def test_fixed_hash_and_probe_authority_barriers(self) -> None:
        self.assertTrue(target._hash_barrier())
        self.assertTrue(target._probe_barrier())

    def test_expected_suite_total_is_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 23)

    def test_capability_is_git_only_without_shell_or_network_import(self) -> None:
        value = target._git_only_capability()
        self.assertEqual(value["forbidden_imports"], [])
        self.assertEqual(value["process_calls"], ["subprocess.run", "subprocess.run"])
        self.assertEqual(value["shell_or_executable_keyword_uses"], [])
        self.assertTrue(value["history_paths_repository_relative"])

    def test_selector_contract_is_exact_64_and_four_by_16(self) -> None:
        self.assertEqual(target.selector.TASK_COUNT, 64)
        self.assertEqual(target.selector.TASKS_PER_STRATUM, 16)
        self.assertEqual(len(target.selector.RISK_STRATA), 4)

    def test_selector_source_does_not_contain_external_credentials_or_roots(self) -> None:
        source = target.base.base._ordinary(target.SELECTOR_SOURCE).read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "ghp_",
            "tvly-dev-",
            "/mnt",
            "/data",
            "run_official_eval_local",
        ):
            self.assertNotIn(forbidden, source)

    def test_resealed_authorization_capability_or_hash_tamper_fails(self) -> None:
        fake_tests = {
            "expected": target.EXPECTED_TESTS,
            "observed": target.EXPECTED_TESTS,
            "passed": True,
            "suites": [],
        }
        audit = target.base.base

        def same(*args: str) -> str:
            return (
                "same"
                if args[:2] in {("rev-parse", "HEAD"), ("rev-parse", "target/main")}
                else ""
            )

        with mock.patch.object(audit, "_git", side_effect=same), mock.patch.object(
            target, "_tests", return_value=fake_tests
        ), mock.patch.object(
            audit,
            "_watchers",
            return_value={
                str(pid): {"matches_frozen_identity": True}
                for pid in audit.PROTECTED_WATCHERS
            },
        ), mock.patch.object(audit, "_lease_inactive", return_value=True):
            value = target.build_audit(now=1, tracked=False)
        for kind in ("authorization", "capability", "hash"):
            changed = copy.deepcopy(value)
            if kind == "authorization":
                changed["authorization"]["real_identity_selection_or_population_freeze"] = True
            elif kind == "capability":
                changed["git_only_capability_audit"]["forbidden_imports"] = ["requests"]
            else:
                changed["fixed_artifact_hashes"][str(target.PROBE_AUDIT)] = "0" * 64
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
