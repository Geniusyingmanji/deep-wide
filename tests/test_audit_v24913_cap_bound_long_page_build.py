from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v24913_cap_bound_long_page_build as audit  # noqa: E402


class V24913CapBoundLongPageBuildAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = audit.build(now=1_786_212_000)

    def test_audit_is_valid_when_clean_pushed(self) -> None:
        self.assertTrue(self.value["audit_valid"])
        self.assertEqual(self.value["findings"], [])
        self.assertTrue(all(self.value["checks"].values()))

    def test_parent_nonengagement_is_bound(self) -> None:
        self.assertIn("v24912_v24911_nonengagement", self.value["parent"]["path"])
        self.assertTrue(
            self.value["checks"]["parent_nonengagement_diagnosis_valid"]
        )

    def test_runtime_is_label_blind_and_evaluator_free(self) -> None:
        semantic = self.value["runtime_semantic_audit"]
        self.assertEqual(semantic["privileged_runtime_field_accesses"], [])
        self.assertEqual(semantic["evaluator_capabilities"], [])
        self.assertEqual(semantic["credential_literal_hits"], [])

    def test_cap_and_mechanism_are_engaged(self) -> None:
        mechanism = self.value["content_free_mechanism"]
        self.assertEqual(mechanism["fetch_input_cap"], 12_000)
        self.assertEqual(mechanism["active_output_per_page_cap"], 5_000)
        self.assertGreater(mechanism["long_input_characters_beyond_output_page_cap"], 0)
        self.assertTrue(mechanism["long_page_mechanism_engaged"])
        self.assertFalse(mechanism["receipt_contains_private_content"])

    def test_benchmark_launch_remains_unauthorized(self) -> None:
        authorization = self.value["authorization"]
        self.assertFalse(authorization["external_gate_launch"])
        self.assertFalse(authorization["public_dev64_or_exact220"])
        self.assertFalse(authorization["evaluator"])
        self.assertFalse(authorization["sota_claim"])

    def test_published_audit_matches_when_present(self) -> None:
        path = ROOT / audit.OUTPUT
        if path.is_file():
            published = json.loads(path.read_text(encoding="utf-8"))
            unsigned = dict(published)
            seal = unsigned.pop("audit_payload_sha256")
            self.assertEqual(seal, audit.packer.parent.payload_sha256(unsigned))
            self.assertTrue(published["audit_valid"])


if __name__ == "__main__":
    unittest.main()
