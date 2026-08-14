from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import audit_v25480_outcome_blind_qualified_label_population as target  # noqa: E402


class V25480PopulationAuditTests(unittest.TestCase):
    def test_build_and_failure_barriers_are_exact(self) -> None:
        self.assertTrue(target._build_barrier())
        self.assertTrue(target._failure_barrier())
        self.assertEqual(
            target._git("rev-parse", target.population.SELECTION_PARENT_COMMIT),
            target.population.SELECTION_PARENT_COMMIT,
        )

    def test_audit_passes_without_effect_or_outcome_access(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        self.assertEqual(target.validate_audit(value), value)
        self.assertTrue(value["audit_valid"])
        self.assertFalse(
            value[
                "historical_forward_page_prediction_score_metric_quality_or_per_task_outcome_read"
            ]
        )
        self.assertFalse(value["authorization"]["external_forward"])

    def test_selection_is_union_disjoint_and_hash_bound(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        selection = value["selection"]
        self.assertEqual(selection["consumed_public_clue_count"], 60)
        self.assertEqual(selection["overlap_count_by_block"], [20, 0])
        self.assertEqual(selection["selected_overlap_count"], 0)
        self.assertFalse(value["v25476_population_reused"])

    def test_resealed_outcome_launch_credit_or_reuse_tamper_fails(self) -> None:
        value = target.build_audit(now=1, tracked=False)
        for kind in ("outcome", "launch", "credit", "reuse"):
            changed = copy.deepcopy(value)
            if kind == "outcome":
                changed[
                    "historical_forward_page_prediction_score_metric_quality_or_per_task_outcome_read"
                ] = True
            elif kind == "launch":
                changed["authorization"]["external_forward"] = True
            elif kind == "credit":
                changed["positive_signed_credit_count"] = 1
            else:
                changed["v25476_population_reused"] = True
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.base.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)


if __name__ == "__main__":
    unittest.main()
