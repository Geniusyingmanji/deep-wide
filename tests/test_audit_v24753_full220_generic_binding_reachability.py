from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import (  # noqa: E402
    audit_v24753_full220_generic_binding_reachability as target,
)


class V24753Full220ReachabilityAuditTests(unittest.TestCase):
    def test_real_visible_only_coverage_is_frozen(self) -> None:
        value = target.build_audit(now=0)
        self.assertEqual(target.validate_audit(value), value)
        coverage = value["coverage"]
        self.assertEqual(coverage["fixed_visible_task_denominator"], 220)
        self.assertEqual(coverage["current_v24745_executable_task_count"], 0)
        self.assertEqual(coverage["conditional_known_value_kind_task_count"], 52)
        self.assertEqual(coverage["conditional_exact_year_record_task_count"], 30)

    def test_current_and_conditional_coverage_cannot_be_conflated(self) -> None:
        value = target.build_audit(now=0)
        self.assertFalse(
            value["decision"][
                "current_adapter_has_nonzero_exact220_executable_coverage"
            ]
        )
        self.assertFalse(
            value["decision"][
                "conditional_counts_are_trigger_quality_or_score_evidence"
            ]
        )
        self.assertFalse(value["authorization"]["paired_dev64_protocol_or_launch"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_resealed_executable_coverage_tamper_fails(self) -> None:
        value = target.build_audit(now=0)
        altered = copy.deepcopy(value)
        altered["coverage"]["current_v24745_executable_task_count"] = 1
        altered.pop("audit_payload_sha256")
        altered["audit_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaises(ValueError):
            target.validate_audit(altered)

    def test_audit_source_has_no_privileged_subscript_access(self) -> None:
        self.assertEqual(target._forbidden_ast_accesses(Path(target.__file__)), [])


if __name__ == "__main__":
    unittest.main()
