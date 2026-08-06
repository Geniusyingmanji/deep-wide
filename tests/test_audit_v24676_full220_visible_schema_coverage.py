from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24676_full220_visible_schema_coverage as target  # noqa: E402


class V24676Full220VisibleSchemaCoverageTests(unittest.TestCase):
    def test_full220_coverage_is_exact_and_nonregressive(self) -> None:
        value = target.build_audit(now=0)
        coverage = value["coverage"]
        self.assertEqual(coverage["fixed_visible_task_denominator"], 220)
        self.assertEqual(coverage["frozen_parser_covered_task_count"], 194)
        self.assertEqual(coverage["expanded_parser_covered_task_count"], 215)
        self.assertEqual(coverage["newly_covered_task_count"], 21)
        self.assertEqual(coverage["already_covered_task_changed_count"], 0)
        self.assertEqual(coverage["remaining_no_unambiguous_explicit_schema_task_count"], 5)

    def test_ror_adapter_has_zero_natural_visible_coverage(self) -> None:
        value = target.build_audit(now=0)
        self.assertEqual(value["coverage"]["explicit_ror_namespace_task_count"], 0)
        self.assertFalse(
            value["interpretation"][
                "ror_structured_adapter_has_natural_visible_schema_coverage_on_full220"
            ]
        )

    def test_authority_stops_at_runtime_implementation(self) -> None:
        value = target.validate_audit(target.build_audit(now=0))
        self.assertTrue(
            value["authorization"]["concurrency_safe_runtime_integration_implementation"]
        )
        self.assertFalse(value["authorization"]["fresh_dev64_protocol_or_launch"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_resealed_coverage_tamper_fails_closed(self) -> None:
        value = target.build_audit(now=0)
        changed = copy.deepcopy(value)
        changed["coverage"]["newly_covered_task_count"] = 22
        changed.pop("audit_payload_sha256")
        changed["audit_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_audit(changed)

    def test_label_blind_source_and_create_only_publisher(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/audit_v24676_full220_visible_schema_coverage.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
