from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24494_v24493_targeted_conversion as target  # noqa: E402


class V24494TargetedConversionDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_report(now=0)

    def test_observed_mechanism_and_reliability_are_exact(self) -> None:
        observed = self.value["observed"]
        self.assertTrue(observed["reliability_transport_validation_all_passed"])
        self.assertEqual(observed["target_plan_tasks"], 1)
        self.assertEqual(observed["additional_fetch_effects_success_rows"], 2)
        self.assertEqual(observed["safe_change_improvement_tasks"], 0)
        self.assertEqual(observed["total_decision_credit_nats"], 0)

    def test_diagnosis_does_not_invent_specific_semantic_root_cause(self) -> None:
        inferences = self.value["inferences"]
        self.assertTrue(inferences["targeted_stage_activated"])
        self.assertTrue(
            inferences[
                "targeted_effect_failed_to_convert_to_safe_change_or_decision_credit"
            ]
        )
        self.assertFalse(
            inferences["positive_information_gain_after_targeted_search_is_proven"]
        )
        self.assertFalse(
            inferences[
                "targeted_sources_produced_new_usable_observations_is_proven"
            ]
        )
        self.assertFalse(inferences["specific_threshold_failure_cause_is_proven"])
        self.assertGreaterEqual(len(self.value["missing_content_free_fields"]), 8)

    def test_resealed_claim_and_authorization_tamper_fail_closed(self) -> None:
        from deepwide_agent.v24320_forward_contract import payload_sha256

        cases = (
            lambda item: item["inferences"].__setitem__(
                "specific_threshold_failure_cause_is_proven", True
            ),
            lambda item: item["authorization"].__setitem__(
                "same_population_rerun_or_revaluation", True
            ),
            lambda item: item["source_policy"].__setitem__(
                "temporary_execution_directory_opened", True
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
            Path("scripts/diagnose_v24494_v24493_targeted_conversion.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
