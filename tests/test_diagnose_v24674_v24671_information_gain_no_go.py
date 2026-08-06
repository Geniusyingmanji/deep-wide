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

from scripts import diagnose_v24674_v24671_information_gain_no_go as target  # noqa: E402


class V24674InformationGainNoGoDiagnosisTests(unittest.TestCase):
    def test_frozen_aggregate_localizes_credit_proxy_failure(self) -> None:
        value = target.build_diagnosis(now=0)
        aggregate = value["aggregate"]
        information = value["information_aggregate"]
        self.assertEqual(aggregate["targeted_usable_page_count"], 33)
        self.assertEqual(aggregate["visible_surface_aligned_source_count"], 82)
        self.assertEqual(aggregate["visible_surface_title_aligned_source_count"], 0)
        self.assertEqual(aggregate["visible_surface_url_only_aligned_source_count"], 82)
        self.assertEqual(aggregate["proposed_cell_change_count"], 0)
        self.assertEqual(aggregate["support_closure_eligible_change_count"], 0)
        self.assertEqual(information["epistemic_action_credit_nats"], 16.890354182535)

    def test_candidate_revision_executed_without_proposal_or_failure(self) -> None:
        value = target.build_diagnosis(now=0)
        self.assertEqual(
            value["provider_model_stage_histogram"],
            {
                "shared_plan|baseline_synthesis": 1,
                "shared_plan|baseline_synthesis|candidate_revision": 11,
            },
        )
        self.assertEqual(value["aggregate"]["recoverable_failure_count"], 0)
        self.assertEqual(
            value["histograms"]["proposed_cell_change_count"], {"0": 12}
        )

    def test_credit_and_authority_fail_closed(self) -> None:
        value = target.validate_diagnosis(target.build_diagnosis(now=0))
        diagnosis = value["diagnosis"]
        self.assertFalse(
            diagnosis["prefetch_entity_localization_gain_is_target_value_posterior_gain"]
        )
        self.assertFalse(diagnosis["positive_task_or_decision_credit_supported"])
        self.assertTrue(
            value["authorization"]["label_blind_full_visible_question_coverage_audit"]
        )
        self.assertFalse(value["authorization"]["new_runtime_implementation"])
        self.assertFalse(value["authorization"]["dev64"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_resealed_authorization_tamper_fails_closed(self) -> None:
        value = target.build_diagnosis(now=0)
        changed = copy.deepcopy(value)
        changed["authorization"]["dev64"] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_diagnosis(changed)

    def test_label_blind_source_and_create_only_publisher(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/diagnose_v24674_v24671_information_gain_no_go.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "diagnosis.json"
            target.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
