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

from deepwide_agent import v24608_total_title_provenance_projection as total  # noqa: E402
from test_v24524_alias_title_integration import TASK  # noqa: E402
from test_v24607_proof_carrying_title_provenance import populate, validate  # noqa: E402


class V24608TotalTitleProvenanceProjectionTests(unittest.TestCase):
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
        receipt = self.capability.content_free_title_provenance_receipt()
        self.assertEqual(row["status"], "validated_capability")
        self.assertTrue(
            row[
                "content_free_title_provenance_receipt_consumed_validated_capability"
            ]
        )
        for name in total.PROVENANCE_COUNT_NAMES:
            self.assertEqual(row[f"content_free_title_provenance_{name}"], receipt[name])
        self.assertFalse(
            row[
                "content_free_title_provenance_projection_claims_provider_or_transport_causality"
            ]
        )

    def test_failure_row_is_exact_zero_without_private_effect_claim(self) -> None:
        row = total.failure_projection(2)
        self.assertEqual(row["status"], "failure_as_zero")
        self.assertFalse(
            row["content_free_title_provenance_additional_private_effects_known_zero"]
        )
        self.assertTrue(all(row[name] == 0 for name in total.PROVENANCE_COUNT_FIELDS))

    def test_public_success_dictionary_cannot_be_reingested_as_proof(self) -> None:
        row = total.task_projection(1, self.capability)
        with self.assertRaises(TypeError):
            total.task_projection(1, row)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            total.aggregate_projections([row], selected=1)

    def test_mixed_aggregate_preserves_parent_and_provenance_counts(self) -> None:
        value = total.aggregate_projections(
            [self.capability, total.failure_projection(2)], selected=2
        )
        self.assertEqual(value["selected"], 2)
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["failure_as_zero_tasks"], 1)
        counts = value["total_content_free_title_provenance_count_fields"]
        self.assertEqual(
            counts["action_source_empty_title_count"]
            + counts["action_source_nonempty_title_count"],
            counts["action_source_count"],
        )
        self.assertTrue(
            value[
                "all_content_free_title_provenance_failure_rows_are_content_free_zero_projections"
            ]
        )
        self.assertFalse(
            value["content_free_title_provenance_changes_effect_or_credit_surface"]
        )

    def test_row_and_aggregate_tamper_fail_closed(self) -> None:
        row = total.task_projection(1, self.capability)
        changed = copy.deepcopy(row)
        changed["content_free_title_provenance_action_source_count"] += 1
        with self.assertRaises(ValueError):
            total.validate_total_row(changed)
        aggregate = total.aggregate_projections([self.capability], selected=1)
        changed = copy.deepcopy(aggregate)
        changed["content_free_title_provenance_changes_effect_or_credit_surface"] = True
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
            "example.edu",
            "raw_content",
            "candidate_prediction",
        ):
            self.assertNotIn(prohibited, encoded)
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24608_total_title_provenance_projection.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
