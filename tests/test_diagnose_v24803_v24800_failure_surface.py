from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24800_exact220_contract as contract  # noqa: E402
from scripts import diagnose_v24803_v24800_failure_surface as target  # noqa: E402


class V24803FailureSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1786112000)

    def test_exact_failure_partition_and_parent_reconciliation(self) -> None:
        self.assertEqual(self.value["failure_class_counts"], {
            "entity_anchor_failure": 53,
            "evaluator_internal_error": 11,
            "evaluator_out_of_range_metric": 2,
            "partial_quality": 136,
            "visible_schema_mismatch": 10,
            "whole_table_success": 8,
        })
        self.assertTrue(all(self.value["checks"].values()))
        self.assertEqual(self.value["findings"], [])
        self.assertTrue(self.value["diagnosis_valid"])

    def test_boundary_and_claims_are_conservative(self) -> None:
        boundary = self.value["boundary"]
        conclusions = self.value["conclusions"]
        self.assertTrue(boundary["post_prediction_freeze_aggregate_only"])
        self.assertFalse(boundary["network_model_search_fetch_or_evaluator_called"])
        self.assertTrue(
            boundary["aggregate_diagnosis_must_not_feed_public_benchmark_runtime_routing"]
        )
        self.assertFalse(conclusions["fixed_full_budget_causal_superiority_established"])
        self.assertFalse(conclusions["entropy_or_information_gain_credit_validated"])
        self.assertFalse(conclusions["sota_established"])
        self.assertFalse(self.value["authorization"]["new_public_exact220"])

    def test_public_report_emits_no_task_level_content(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False, sort_keys=True)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.INSTANCE.search(encoded))
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertNotIn("required_columns", encoded)
        self.assertNotIn("the entity is wrong", encoded)

    def test_resealed_tamper_fails_reproducibility(self) -> None:
        changed = copy.deepcopy(self.value)
        changed["failure_class_counts"]["partial_quality"] -= 1
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = contract.payload_sha256(changed)
        with self.assertRaises(RuntimeError):
            target.validate_report(ROOT, changed)

    def test_published_artifact_is_reproducible_when_present(self) -> None:
        path = ROOT / target.OUTPUT
        if not path.is_file():
            self.skipTest("V2.48.03 publication has not been created yet")
        value = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(value, target.validate_report(ROOT, value))


if __name__ == "__main__":
    unittest.main()
