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
    revise_v25294_worldbank_monotone_fill_gate_r2 as target,
)


class V25294WorldBankMonotoneFillGateR2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_revision(now=1)

    def test_parent_and_frozen_metadata_evidence_are_exact(self) -> None:
        self.assertEqual(
            target.parent.base.sha256(target.PARENT), target.PARENT_SHA256
        )
        evidence = target._metadata_evidence()
        self.assertEqual(len(evidence), 4)
        self.assertTrue(
            all(row["total"] == 265 and row["record_count"] == 265 for row in evidence)
        )

    def test_pagination_correction_is_mathematically_complete(self) -> None:
        correction = self.value["correction"]
        snapshot = self.value["snapshot_and_representation_contract"]
        self.assertEqual(correction["old_page_count_for_observed_total"], 3)
        self.assertEqual(correction["corrected_page_count_for_observed_total"], 2)
        self.assertEqual(snapshot["world_bank_per_page"], 200)
        self.assertTrue(snapshot["complete_official_record_coverage_required"])
        self.assertTrue(
            snapshot["metadata_total_must_equal_sum_page_record_counts"]
        )

    def test_all_unrelated_contracts_and_authority_are_unchanged(self) -> None:
        parent = target._parent_design()
        self.assertEqual(self.value["runtime_contract"], parent["runtime_contract"])
        self.assertEqual(self.value["physical_caps"], parent["physical_caps"])
        self.assertEqual(
            self.value["mechanism_gate_before_evaluator"],
            parent["mechanism_gate_before_evaluator"],
        )
        self.assertEqual(self.value["authorization"], parent["authorization"])
        self.assertFalse(
            self.value["authorization"]["network_population_selection_or_freeze"]
        )

    def test_revision_is_label_blind_effect_free_and_credit_zero(self) -> None:
        self.assertEqual(target.validate_revision(self.value), self.value)
        self.assertFalse(
            self.value[
                "mapping_gold_category_question_type_split_evaluator_score_reward_or_historical_correctness_read"
            ]
        )
        self.assertFalse(
            self.value["network_model_search_fetch_evaluator_benchmark_or_api_called"]
        )
        self.assertEqual(
            self.value["runtime_contract"]["positive_signed_credit_count"], 0
        )

    def test_resealed_parent_page_coverage_authority_or_credit_tamper_fails(self) -> None:
        for kind in ("parent", "page", "coverage", "authority", "credit"):
            changed = copy.deepcopy(self.value)
            if kind == "parent":
                changed["parent_design"]["sha256"] = "0" * 64
            elif kind == "page":
                changed["snapshot_and_representation_contract"][
                    "world_bank_per_page"
                ] = 120
            elif kind == "coverage":
                changed["snapshot_and_representation_contract"][
                    "complete_official_record_coverage_required"
                ] = False
            elif kind == "authority":
                changed["authorization"]["network_population_selection_or_freeze"] = True
            else:
                changed["runtime_contract"]["positive_signed_credit_count"] = 1
            changed.pop("design_payload_sha256")
            changed["design_payload_sha256"] = target.payload_sha256(changed)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_revision(changed)


if __name__ == "__main__":
    unittest.main()
