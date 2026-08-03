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

from deepwide_agent.v24330_forward_contract import payload_sha256  # noqa: E402
from scripts import (  # noqa: E402
    build_v24332_v24330_stratified_effect_aggregate as target,
)


class V24332V24330StratifiedAggregateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(ROOT, now=1)

    def test_exact220_projection_matches_frozen_taxonomy(self) -> None:
        aggregate = self.value["aggregate"]
        self.assertEqual(aggregate["selected_tasks"], 220)
        self.assertEqual(aggregate["terminal_kinds"], {
            "complete_fallback": 22,
            "complete_success": 135,
            "incomplete_fallback": 63,
        })
        self.assertEqual(aggregate["complete_tasks"], 157)
        self.assertEqual(aggregate["incomplete_tasks"], 63)
        self.assertTrue(aggregate["complete_subset_conservation_verified"])
        self.assertTrue(aggregate["incomplete_lower_bounds_verified"])

    def test_validator_fix_does_not_promote_frozen_run(self) -> None:
        decision = self.value["decision"]
        self.assertTrue(decision["structural_accounting_valid"])
        self.assertFalse(decision["promotion_passed"])
        self.assertEqual(decision["failed_checks"], ["incomplete_task_count"])
        self.assertFalse(decision["same_run_evaluation_authorized"])
        self.assertFalse(decision["new_exact220_authorized"])

    def test_content_free_and_fault_matrix_is_benchmark_external(self) -> None:
        encoded = json.dumps(self.value, ensure_ascii=False)
        self.assertIsNone(target.SECRET.search(encoded))
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertNotIn("| Result |", encoded)
        self.assertTrue(self.value["fault_matrix_contract"]["benchmark_external"])
        self.assertEqual(self.value["fault_matrix_contract"]["remote_effects"], 0)

    def test_resealed_promotion_tamper_is_rejected(self) -> None:
        altered = copy.deepcopy(self.value)
        altered["decision"]["promotion_passed"] = True
        altered.pop("result_payload_sha256")
        altered["result_payload_sha256"] = payload_sha256(altered)
        with self.assertRaisesRegex(RuntimeError, "aggregate result drifted"):
            target.validate_report(ROOT, altered)


if __name__ == "__main__":
    unittest.main()
