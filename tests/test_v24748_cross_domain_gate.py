from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24748_cross_domain_gate as target  # noqa: E402


class V24748CrossDomainGateTests(unittest.TestCase):
    def test_successor_binds_revoked_parent_and_preserves_vectors(self) -> None:
        value = target.successor_bindings()
        self.assertTrue(value["parent_failure_seal_valid"])
        self.assertTrue(value["failure_declared_protocol_hash_matches"])
        self.assertTrue(value["failure_declared_source_hash_matches"])
        self.assertFalse(value["old_activation_authorized"])
        self.assertTrue(value["task_vector_matches_old_protocol"])
        self.assertTrue(value["request_vector_matches_old_protocol"])
        self.assertTrue(value["gate_vector_matches_old_protocol"])
        self.assertTrue(value["budget_vector_matches_old_protocol"])
        self.assertEqual(
            value["only_control_change"],
            "isolated_unittest_discovery_by_exact_filename",
        )
        self.assertEqual(target.base.TASK_COUNT, 6)
        self.assertEqual(target.base.REQUEST_COUNT, 32)
        self.assertEqual(target.base.WORKERS, 32)
        self.assertEqual(len(target.base.REQUIRED_CHECKS), 10)

    def test_successor_paths_are_append_only_and_manifest_complete(self) -> None:
        self.assertNotEqual(target.base.PROTOCOL, target.OLD_PROTOCOL)
        self.assertNotEqual(
            target.base.SCRIPT, Path("scripts/v24747_cross_domain_gate.py")
        )
        self.assertIn(target.OLD_PROTOCOL, target.base.CONTROL_SURFACE)
        self.assertIn(target.PARENT_FAILURE, target.base.CONTROL_SURFACE)
        self.assertIn(target.SCRIPT, target.base.CONTROL_SURFACE)
        self.assertIn(target.SCRIPT_TEST, target.base.CONTROL_SURFACE)
        self.assertEqual(target.base.EXPECTED_TESTS, 34)


if __name__ == "__main__":
    unittest.main()
