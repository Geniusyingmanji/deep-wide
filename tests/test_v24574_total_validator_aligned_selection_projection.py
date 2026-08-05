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

from deepwide_agent import v24574_total_validator_aligned_selection_projection as total  # noqa: E402
from test_v24524_alias_title_integration import TASK  # noqa: E402
from test_v24573_proof_carrying_validator_aligned_selection import (  # noqa: E402
    populate,
    validate,
)


class V24574TotalValidatorAlignedSelectionProjectionTests(unittest.TestCase):
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
        receipt = self.capability.validator_aligned_selection_receipt()
        self.assertEqual(row["status"], "validated_capability")
        self.assertTrue(
            row[
                "validator_aligned_selection_receipt_consumed_validated_capability"
            ]
        )
        for name in total.SELECTION_COUNT_NAMES:
            self.assertEqual(row[f"validator_aligned_selection_{name}"], receipt[name])
        self.assertFalse(
            row[
                "validator_aligned_selection_projection_claims_lead_or_effect_causality"
            ]
        )
        self.assertFalse(
            row["validator_aligned_selection_url_alias_hint_received_credit"]
        )

    def test_failure_row_is_exact_zero_without_private_effect_claim(self) -> None:
        row = total.failure_projection(2)
        self.assertEqual(row["status"], "failure_as_zero")
        self.assertFalse(
            row[
                "validator_aligned_selection_additional_private_effects_known_zero"
            ]
        )
        self.assertTrue(
            all(row[name] == 0 for name in total.SELECTION_COUNT_FIELDS)
        )

    def test_public_success_dictionary_cannot_be_reingested_as_proof(self) -> None:
        row = total.task_projection(1, self.capability)
        with self.assertRaises(TypeError):
            total.task_projection(1, row)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            total.aggregate_projections([row], selected=1)

    def test_mixed_aggregate_preserves_strict_parent_and_selection_counts(self) -> None:
        value = total.aggregate_projections(
            [self.capability, total.failure_projection(2)], selected=2
        )
        self.assertEqual(value["selected"], 2)
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["failure_as_zero_tasks"], 1)
        counts = value["total_validator_aligned_selection_count_fields"]
        self.assertGreaterEqual(counts["selection_calls"], 1)
        self.assertEqual(
            value["validator_aligned_selection_activity_tasks"], 1
        )
        self.assertIn(
            "decision_reachability_one_observation_changed_legacy_full_conversion_joint_tasks",
            value,
        )
        self.assertTrue(
            value[
                "all_validator_aligned_selection_failure_rows_are_content_free_zero_projections"
            ]
        )

    def test_row_and_aggregate_coordinated_tamper_fail_closed(self) -> None:
        row = total.task_projection(1, self.capability)
        changed = copy.deepcopy(row)
        changed["validator_aligned_selection_visible_input_lead_count"] += 1
        with self.assertRaises(ValueError):
            total.validate_total_row(changed)
        aggregate = total.aggregate_projections([self.capability], selected=1)
        cases = (
            lambda value: value[
                "total_validator_aligned_selection_count_fields"
            ].__setitem__(
                "selection_calls",
                value["total_validator_aligned_selection_count_fields"][
                    "selection_calls"
                ]
                + 1,
            ),
            lambda value: value.__setitem__(
                "validator_aligned_selection_projection_claims_lead_or_effect_causality",
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
            "usq-one.example",
            "raw_content",
            "candidate_prediction",
        ):
            self.assertNotIn(prohibited, encoded)
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path(
                "src/deepwide_agent/"
                "v24574_total_validator_aligned_selection_projection.py"
            )
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
