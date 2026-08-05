from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24580_total_prededup_preservation_projection as total  # noqa: E402
from test_v24524_alias_title_integration import TASK  # noqa: E402
from test_v24579_proof_carrying_prededup_preservation import (  # noqa: E402
    populate,
    validate,
)


class V24580TotalPrededupPreservationProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.root = Path(cls.temporary.name)
        populate(cls.root)
        cls.capability = validate(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_success_row_consumes_only_opaque_capability(self) -> None:
        row = total.task_projection(1, self.capability)
        receipt = self.capability.prededup_preservation_receipt()
        self.assertEqual(row["status"], "validated_capability")
        self.assertTrue(
            row[
                "prededup_preservation_receipt_consumed_validated_capability"
            ]
        )
        for name in total.PRESERVATION_COUNT_NAMES:
            self.assertEqual(row[f"prededup_preservation_{name}"], receipt[name])
        self.assertGreater(row["prededup_preservation_preserved_candidate_count"], 0)
        self.assertGreater(
            row[
                "validator_aligned_selection_validator_aligned_title_replacement_count"
            ],
            0,
        )
        self.assertFalse(
            row[
                "prededup_preservation_projection_claims_candidate_or_effect_causality"
            ]
        )
        self.assertFalse(row["prededup_preservation_preserved_url_received_credit"])

    def test_failure_row_is_exact_zero_without_private_effect_claim(self) -> None:
        row = total.failure_projection(2)
        self.assertEqual(row["status"], "failure_as_zero")
        self.assertFalse(
            row["prededup_preservation_additional_private_effects_known_zero"]
        )
        self.assertTrue(
            all(row[name] == 0 for name in total.PRESERVATION_COUNT_FIELDS)
        )

    def test_public_success_dictionary_cannot_be_reingested_as_proof(self) -> None:
        row = total.task_projection(1, self.capability)
        with self.assertRaises(TypeError):
            total.task_projection(1, row)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            total.aggregate_projections([row], selected=1)

    def test_mixed_aggregate_preserves_parent_and_cooccurrence_counts(self) -> None:
        value = total.aggregate_projections(
            [self.capability, total.failure_projection(2)], selected=2
        )
        self.assertEqual(value["selected"], 2)
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["failure_as_zero_tasks"], 1)
        counts = value["total_prededup_preservation_count_fields"]
        self.assertGreater(counts["preserved_candidate_count"], 0)
        self.assertEqual(value["prededup_preserved_candidate_tasks"], 1)
        self.assertEqual(
            value["prededup_and_source_replacement_cooccurrence_tasks"], 1
        )
        self.assertEqual(
            value["prededup_and_title_replacement_cooccurrence_tasks"], 1
        )
        self.assertFalse(
            value[
                "prededup_preservation_same_task_cooccurrence_claims_lead_level_causality"
            ]
        )
        self.assertTrue(
            value[
                "all_prededup_preservation_failure_rows_are_content_free_zero_projections"
            ]
        )

    def test_row_and_aggregate_coordinated_tamper_fail_closed(self) -> None:
        row = total.task_projection(1, self.capability)
        changed = copy.deepcopy(row)
        changed["prededup_preservation_preserved_candidate_count"] += 1
        with self.assertRaises(ValueError):
            total.validate_total_row(changed)
        aggregate = total.aggregate_projections([self.capability], selected=1)
        cases = (
            lambda value: value[
                "total_prededup_preservation_count_fields"
            ].__setitem__(
                "projection_calls",
                value["total_prededup_preservation_count_fields"][
                    "projection_calls"
                ]
                + 1,
            ),
            lambda value: value.__setitem__(
                "prededup_preservation_projection_claims_candidate_or_effect_causality",
                True,
            ),
        )
        for alter in cases:
            changed = copy.deepcopy(aggregate)
            alter(changed)
            with self.assertRaises(ValueError):
                total.validate_aggregate(changed)

    def test_public_projection_is_content_free_and_label_blind(self) -> None:
        encoded = json.dumps(
            total.task_projection(1, self.capability),
            ensure_ascii=False,
            sort_keys=True,
        )
        for prohibited in (
            TASK["question"],
            TASK["opaque_id"],
            "University of Southern Queensland",
            "1967",
            "example.edu",
            "raw_content",
            "candidate_prediction",
        ):
            self.assertNotIn(prohibited, encoded)
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path(
                "src/deepwide_agent/"
                "v24580_total_prededup_preservation_projection.py"
            )
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
