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

from deepwide_agent import v24600_total_title_funnel_projection as total  # noqa: E402
from test_v24524_alias_title_integration import TASK  # noqa: E402
from test_v24599_proof_carrying_title_funnel import populate, validate  # noqa: E402


class V24600TotalTitleFunnelProjectionTests(unittest.TestCase):
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
        receipt = self.capability.content_free_title_funnel_receipt()
        self.assertEqual(row["status"], "validated_capability")
        self.assertTrue(
            row["content_free_title_funnel_receipt_consumed_validated_capability"]
        )
        for name in total.FUNNEL_COUNT_NAMES:
            self.assertEqual(row[f"content_free_title_funnel_{name}"], receipt[name])
        self.assertGreater(row["content_free_title_funnel_selection_calls"], 0)
        self.assertFalse(
            row[
                "content_free_title_funnel_projection_claims_retrieval_effect_or_causality"
            ]
        )

    def test_failure_row_is_exact_zero_without_private_effect_claim(self) -> None:
        row = total.failure_projection(2)
        self.assertEqual(row["status"], "failure_as_zero")
        self.assertFalse(
            row["content_free_title_funnel_additional_private_effects_known_zero"]
        )
        self.assertTrue(all(row[name] == 0 for name in total.FUNNEL_COUNT_FIELDS))

    def test_public_success_dictionary_cannot_be_reingested_as_proof(self) -> None:
        row = total.task_projection(1, self.capability)
        with self.assertRaises(TypeError):
            total.task_projection(1, row)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            total.aggregate_projections([row], selected=1)

    def test_mixed_aggregate_preserves_parent_and_funnel_counts(self) -> None:
        value = total.aggregate_projections(
            [self.capability, total.failure_projection(2)], selected=2
        )
        self.assertEqual(value["selected"], 2)
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["failure_as_zero_tasks"], 1)
        counts = value["total_content_free_title_funnel_count_fields"]
        self.assertGreater(counts["selection_calls"], 0)
        self.assertEqual(value["content_free_title_funnel_activity_tasks"], 1)
        self.assertTrue(
            value[
                "all_content_free_title_funnel_failure_rows_are_content_free_zero_projections"
            ]
        )
        self.assertFalse(value["content_free_title_funnel_changes_effect_or_credit_surface"])

    def test_row_and_aggregate_tamper_fail_closed(self) -> None:
        row = total.task_projection(1, self.capability)
        changed = copy.deepcopy(row)
        changed["content_free_title_funnel_visible_input_lead_count"] += 1
        with self.assertRaises(ValueError):
            total.validate_total_row(changed)
        aggregate = total.aggregate_projections([self.capability], selected=1)
        cases = (
            lambda value: value[
                "total_content_free_title_funnel_count_fields"
            ].__setitem__(
                "nonempty_title_lead_count",
                value["total_content_free_title_funnel_count_fields"][
                    "nonempty_title_lead_count"
                ]
                + 1,
            ),
            lambda value: value.__setitem__(
                "content_free_title_funnel_changes_effect_or_credit_surface", True
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
            Path("src/deepwide_agent/v24600_total_title_funnel_projection.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
