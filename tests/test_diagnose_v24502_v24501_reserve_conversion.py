from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24502_v24501_reserve_conversion as target  # noqa: E402


class V24502ReserveConversionDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(now=0)

    def test_public_aggregate_localizes_conversion_boundary(self) -> None:
        observed = self.value["observed_public_aggregate"]
        self.assertEqual(observed["reserve_selected_source_count"], 1)
        self.assertEqual(observed["reserve_usable_page_count"], 1)
        self.assertEqual(observed["reserve_new_observation_count"], 0)
        self.assertTrue(
            observed["reliability_parent_validation_and_latency_passed"]
        )

    def test_historical_claims_remain_content_free_and_calibrated(self) -> None:
        inferred = self.value["historical_inferences"]
        self.assertTrue(
            inferred[
                "usable_reserve_page_failed_to_produce_target_bound_observation"
            ]
        )
        self.assertFalse(inferred["historical_page_format_is_known"])
        self.assertFalse(
            inferred["split_label_year_caused_historical_failure_is_proven"]
        )
        self.assertFalse(
            inferred[
                "foreign_subject_misattribution_occurred_historically_is_proven"
            ]
        )

    def test_synthetic_matrix_exposes_coverage_and_misattribution_risks(self) -> None:
        matrix = self.value["synthetic_projector_matrix"]
        self.assertTrue(matrix["same_line_narrative"])
        self.assertTrue(matrix["same_line_label_value"])
        self.assertFalse(matrix["split_label_and_year"])
        self.assertFalse(matrix["bare_year"])
        self.assertFalse(matrix["visible_other_row_relation"])
        self.assertTrue(matrix["nonvisible_foreign_subject_relation"])

    def test_resealed_claim_source_and_authorization_tamper_fail_closed(self) -> None:
        from deepwide_agent.v24320_forward_contract import payload_sha256

        cases = (
            lambda item: item["historical_inferences"].__setitem__(
                "historical_page_format_is_known", True
            ),
            lambda item: item["source_policy"].__setitem__(
                "temporary_execution_directory_opened", True
            ),
            lambda item: item["authorization"].__setitem__(
                "same_population_rerun_retry_or_revaluation", True
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(self.value)
            alter(changed)
            changed.pop("diagnosis_payload_sha256")
            changed["diagnosis_payload_sha256"] = payload_sha256(changed)
            with self.assertRaises(RuntimeError):
                target.validate_report(changed)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("scripts/diagnose_v24502_v24501_reserve_conversion.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
