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

from scripts import audit_v25218_snapshot_hard_deadline_controller_build as target  # noqa: E402


class V25218SnapshotHardDeadlineControllerBuildAuditTests(unittest.TestCase):
    def test_fixed_hash_and_parent_authority_barriers(self) -> None:
        self.assertTrue(target._hash_barrier())
        self.assertTrue(target._parent_barrier())

    def test_expected_suite_total_is_exact(self) -> None:
        self.assertEqual(target.EXPECTED_TESTS, 28)

    def test_capability_discloses_multiprocessing_mmap_without_file_process_import(self) -> None:
        value = target._direct_capability()
        self.assertTrue(value["multiprocessing_and_anonymous_mmap_present"])
        self.assertEqual(value["filesystem_subprocess_environment_imports"], [])
        self.assertEqual(value["top_level_effect_calls"], [])

    def test_dependency_closure_and_semantic_findings_are_exact(self) -> None:
        closure = target.base.base._dependency_closure((target.CONTROLLER_SOURCE,))
        self.assertEqual(closure, (target.parent.TRANSPORT_SOURCE, target.CONTROLLER_SOURCE))
        semantic = target.base.base._semantic_findings(closure)
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])

    def test_source_uses_anonymous_mmap_and_terminate_kill_without_file_open(self) -> None:
        source = target.base.base._ordinary(target.CONTROLLER_SOURCE).read_text(
            encoding="utf-8"
        )
        self.assertIn("mmap.mmap(\n                -1", source)
        self.assertIn("process.terminate()", source)
        self.assertIn("process.kill()", source)
        self.assertNotIn("Path(", source)
        self.assertNotIn("open(", source)

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
            "_semantic_findings",
            return_value={
                "privileged_runtime_field_accesses": [],
                "evaluator_capabilities": [],
                "credential_literal_hits": [],
                "allowed_provider_rank_access": [],
            },
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
                changed["authorization"]["public_snapshot_network_access_or_execution_start"] = True
            elif kind == "capability":
                changed["direct_capability_audit"]["filesystem_subprocess_environment_imports"] = ["pathlib"]
            else:
                changed["fixed_artifact_hashes"][str(target.PARENT_AUDIT)] = "0" * 64
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
