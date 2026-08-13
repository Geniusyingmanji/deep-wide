from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25425_population_overlap_and_candidate_funnel as target  # noqa: E402


class V25425PopulationOverlapAndCandidateFunnelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.diagnose(now=1)

    def test_structural_range_parser_finds_consumed_overlap(self) -> None:
        self.assertEqual(
            target._source_range(target.PRIOR_POPULATION_SOURCE), (9680, 9759)
        )
        self.assertEqual(
            target._source_range(target.CURRENT_POPULATION_SOURCE), (9720, 9799)
        )
        erratum = self.value["population_erratum"]
        self.assertEqual(erratum["overlap_identity_count"], 40)
        self.assertEqual(erratum["overlap_current_task_count"], 10)
        self.assertFalse(erratum["v25421_fresh_disjoint_claim_valid"])

    def test_erratum_preserves_shared_parent_no_go(self) -> None:
        erratum = self.value["population_erratum"]
        self.assertFalse(erratum["v25423_within_run_shared_parent_comparison_invalidated"])
        self.assertFalse(erratum["v25424_quality_no_go_changed"])
        delta = self.value["quality_summary"]["guarded_minus_base"]
        self.assertEqual(delta["exact_table_successes"], 0)
        self.assertEqual(delta["quality_composite"], 0)

    def test_guard_rejects_harm_but_candidate_has_zero_improvement(self) -> None:
        self.assertEqual(
            self.value["coordinate_transition_counts"],
            {"rejected:harm": 3, "retained:neutral_correct": 3},
        )
        self.assertEqual(
            self.value["field_coordinate_transition_counts"],
            {
                "Authors:rejected:harm": 3,
                "Stream:retained:neutral_correct": 3,
            },
        )
        self.assertTrue(self.value["checks"]["zero_truth_improving_edits"])

    def test_candidate_funnel_localizes_missing_row_and_zero_gain(self) -> None:
        funnel = self.value["candidate_funnel_counts"]
        self.assertEqual(funnel["parsed_record_count"], 8)
        self.assertEqual(funnel["parsed_field_count"], 30)
        self.assertEqual(funnel["verified_field_count"], 24)
        self.assertEqual(funnel["missing_row_rejected_field_count"], 12)
        self.assertEqual(funnel["unchanged_verified_coordinate_count"], 6)
        self.assertEqual(funnel["changed_safe_coordinate_count"], 6)
        self.assertEqual(
            self.value["remaining_error_surface"]["wrong_cells_by_arm_and_field"][
                target.quality.BASE_ARM
            ],
            {
                "Authors": 30,
                "Published": 33,
                "Status": 34,
                "Stream": 30,
                "Title": 30,
            },
        )

    def test_authorization_is_build_only_and_tamper_fails(self) -> None:
        self.assertEqual(target.validate(self.value), self.value)
        authorization = self.value["authorization"]
        self.assertTrue(authorization["population_freshness_erratum"])
        self.assertTrue(authorization["combined_visible_membership_and_list_guard_build"])
        self.assertFalse(authorization["reuse_v25423_population_or_truth"])
        self.assertFalse(authorization["external_forward_or_evaluator"])
        self.assertFalse(
            authorization["deepwidebench_successor_build_forward_or_evaluator"]
        )
        changed = copy.deepcopy(self.value)
        changed["population_erratum"]["overlap_identity_count"] = 0
        changed.pop("diagnosis_payload_sha256")
        changed = target.contract.seal(changed, "diagnosis_payload_sha256")
        with self.assertRaises(ValueError):
            target.validate(changed)


if __name__ == "__main__":
    unittest.main()
