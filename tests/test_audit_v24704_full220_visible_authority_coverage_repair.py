from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24704_full220_visible_authority_coverage_repair as audit  # noqa: E402


class V24704CoverageRepairTests(unittest.TestCase):
    def test_real_repair_supersedes_false_who_coverage(self) -> None:
        value = audit.build_audit(now=0)
        audit.validate_audit(value)
        self.assertTrue(value["repair"]["predecessor_superseded"])
        self.assertEqual(value["repair"]["observed_false_positive_task_count"], 19)
        self.assertEqual(value["coverage"]["adapter_route_eligible_task_count"], 3)
        self.assertNotIn("who", value["coverage"]["visible_namespace_task_counts"])

    def test_low_coverage_does_not_authorize_runtime_or_benchmark(self) -> None:
        value = audit.build_audit(now=0)
        self.assertFalse(value["authorization"]["runtime_adapter_implementation"])
        self.assertFalse(value["authorization"]["fresh_dev64_protocol_or_launch"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_resealed_runtime_authority_tamper_fails_closed(self) -> None:
        value = audit.build_audit(now=0)
        changed = copy.deepcopy(value)
        changed["authorization"]["runtime_adapter_implementation"] = True
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = audit.payload_sha256(changed)
        with self.assertRaises(ValueError):
            audit.validate_audit(changed)

    def test_output_remains_aggregate_only(self) -> None:
        value = audit.build_audit(now=0)
        self.assertTrue(value["source_policy"]["aggregate_counts_only"])
        self.assertFalse(
            value["source_policy"][
                "question_column_name_namespace_per_task_or_opaque_id_persisted_or_emitted"
            ]
        )


if __name__ == "__main__":
    unittest.main()
