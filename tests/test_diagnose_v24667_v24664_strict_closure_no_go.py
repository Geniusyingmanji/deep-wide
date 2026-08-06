from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v24667_v24664_strict_closure_no_go as target  # noqa: E402


class V24667StrictClosureNoGoDiagnosisTests(unittest.TestCase):
    def test_frozen_aggregate_localizes_support_acquisition_failure(self) -> None:
        value = target.build_diagnosis(now=0)
        aggregate = value["aggregate"]
        taxonomy = value["support_failure_taxonomy"]
        self.assertEqual(aggregate["targeted_discovered_independent_source_count"], 399)
        self.assertEqual(aggregate["targeted_usable_page_count"], 38)
        self.assertEqual(aggregate["proposed_cell_change_count"], 3)
        self.assertEqual(aggregate["support_closure_added_evidence_id_count"], 0)
        self.assertEqual(taxonomy["declared_evidence_id_count_histogram"], {"1": 2, "2": 1})
        self.assertEqual(taxonomy["local_exact_support_source_count_histogram"], {"0": 1, "1": 2})
        self.assertEqual(
            taxonomy["proposal_with_two_or_more_local_exact_support_sources_count"], 0
        )

    def test_conclusion_and_authority_fail_closed(self) -> None:
        value = target.validate_diagnosis(target.build_diagnosis(now=0))
        self.assertFalse(
            value["diagnosis"][
                "model_citation_omission_is_supported_as_current_primary_bottleneck"
            ]
        )
        self.assertTrue(
            value["diagnosis"][
                "current_bottleneck_is_failure_to_acquire_same_value_two_source_exact_support"
            ]
        )
        self.assertTrue(
            value["authorization"]["visible_lead_alignment_successor_implementation"]
        )
        self.assertFalse(value["authorization"]["fresh_external_protocol_design"])
        self.assertFalse(value["authorization"]["evaluator"])
        self.assertFalse(value["authorization"]["dev64"])
        self.assertFalse(value["authorization"]["exact220"])

    def test_entropy_credit_requires_safe_change_and_outer_utility(self) -> None:
        value = target.build_diagnosis(now=0)
        credit = value["entropy_and_credit"]
        self.assertFalse(credit["positive_decision_credit_supported_by_v24664"])
        self.assertFalse(credit["raw_discovery_volume_earns_positive_credit"])
        self.assertTrue(
            credit["future_epistemic_credit_requires_measured_support_uncertainty_reduction"]
        )
        self.assertTrue(
            credit["future_decision_credit_requires_safe_admission_and_postfreeze_outer_utility"]
        )

    def test_resealed_authorization_tamper_fails_closed(self) -> None:
        value = target.build_diagnosis(now=0)
        changed = copy.deepcopy(value)
        changed["authorization"]["fresh_external_protocol_design"] = True
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.payload_sha256(changed)
        with self.assertRaises(ValueError):
            target.validate_diagnosis(changed)

    def test_label_blind_source_and_create_only_publisher(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("scripts/diagnose_v24667_v24664_strict_closure_no_go.py")
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
