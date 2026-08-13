from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import diagnose_v25439_v25438_source_candidate_funnel as target  # noqa: E402


class V25439SourceCandidateFunnelDiagnosisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_diagnosis(now=1)

    def test_existing_registry_localizes_the_zero_candidate_funnel(self) -> None:
        funnel = self.value["existing_registry_funnel_counts"]
        self.assertEqual(funnel["accepted_page_count"], 107)
        self.assertEqual(funnel["labelled_record_surface_count"], 29)
        self.assertEqual(funnel["raw_observation_attempt_count"], 29)
        self.assertEqual(funnel["missing_row_rejected_count"], 29)
        self.assertEqual(funnel["evidence_closed_observation_count"], 0)
        self.assertEqual(funnel["available_candidate_count"], 0)

    def test_key_label_qualification_is_unique_but_insufficient(self) -> None:
        layout = self.value["key_anchored_layout_counts"]
        counterfactual = self.value[
            "identity_qualification_only_counterfactual"
        ]
        self.assertEqual(layout["key_anchored_label_blocks"], 29)
        self.assertEqual(layout["key_qualified_identity_unique_blocks"], 29)
        self.assertEqual(counterfactual["coordinate_group_count"], 29)
        self.assertEqual(counterfactual["unchanged_coordinate_count"], 29)
        self.assertEqual(counterfactual["available_candidate_count"], 0)
        self.assertEqual(counterfactual["tasks_with_available_candidate"], 0)

    def test_bounded_metadata_layout_and_whitespace_failure_are_exact(self) -> None:
        layout = self.value["key_anchored_layout_counts"]
        self.assertEqual(layout["minimum_block_line_count"], 5)
        self.assertEqual(layout["maximum_block_line_count"], 7)
        self.assertEqual(layout["blocks_with_exact_published"], 29)
        self.assertEqual(layout["blocks_with_exact_authors"], 18)
        self.assertEqual(layout["blocks_with_nonexact_singular_author"], 11)
        self.assertEqual(layout.get("blocks_with_exact_title", 0), 0)
        self.assertEqual(layout["strict_safe_cell_rejected__Authors"], 17)
        self.assertEqual(layout["whitespace_only_normalizable__Authors"], 17)

    def test_build_only_authorization_and_tamper_fail_closed(self) -> None:
        self.assertEqual(target.validate_diagnosis(self.value), self.value)
        authorization = self.value["authorization"]
        self.assertTrue(
            authorization["key_anchored_bounded_metadata_parser_build_only"]
        )
        self.assertFalse(authorization["reuse_v25438_population_or_forward"])
        self.assertFalse(authorization["new_external_forward_or_evaluator"])
        changed = copy.deepcopy(self.value)
        changed["identity_qualification_only_counterfactual"][
            "available_candidate_count"
        ] = 1
        changed.pop("diagnosis_payload_sha256")
        changed["diagnosis_payload_sha256"] = target.contract.payload_sha256(
            changed
        )
        with self.assertRaises(ValueError):
            target.validate_diagnosis(changed)


if __name__ == "__main__":
    unittest.main()
