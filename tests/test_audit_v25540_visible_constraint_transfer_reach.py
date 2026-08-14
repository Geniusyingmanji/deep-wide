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

from scripts import audit_v25540_visible_constraint_transfer_reach as target  # noqa: E402


class V25540VisibleConstraintTransferReachTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = target.build_audit(now=1)

    def test_parent_and_fixed_forward_barriers_are_exact(self) -> None:
        self.assertEqual(
            target.base.sha256(target.PARENT_DIAGNOSIS),
            target.PARENT_DIAGNOSIS_SHA256,
        )
        self.assertEqual(
            target.base.sha256(target.FORWARD_AUDIT),
            target.FORWARD_AUDIT_SHA256,
        )
        self.assertTrue(self.value["audit_valid"])
        self.assertEqual(self.value["findings"], [])

    def test_visible_constraint_reach_is_nonzero_and_broad(self) -> None:
        transfer = self.value["visible_transfer"]
        self.assertEqual(transfer["task_count"], 220)
        self.assertEqual(transfer["exact_visible_schema_tasks"], 194)
        self.assertEqual(transfer["expanded_only_visible_schema_tasks"], 21)
        self.assertEqual(transfer["any_explicit_visible_schema_tasks"], 215)
        self.assertEqual(transfer["strict_visible_membership_tasks"], 11)
        self.assertEqual(transfer["temporal_constraint_union_tasks"], 122)
        self.assertEqual(transfer["numeric_scale_constraint_tasks"], 23)
        self.assertEqual(transfer["rank_or_order_constraint_union_tasks"], 48)
        self.assertEqual(transfer["any_constraint_union_tasks"], 145)
        self.assertEqual(
            transfer["any_constraint_with_explicit_schema_tasks"], 144
        )

    def test_current_exact220_closure_has_no_equivalent_mechanical_capability(self) -> None:
        capability = self.value["current_production_capability"]
        self.assertFalse(
            capability["legacy_general_runtime_in_forward_dependency_closure"]
        )
        self.assertEqual(capability["constraint_primitive_reference_hit_count"], 0)
        self.assertTrue(
            capability["visible_question_is_in_current_synthesis_prompt"]
        )
        self.assertTrue(
            capability[
                "temporal_numeric_scale_and_rank_order_are_only_model_instructions"
            ]
        )
        self.assertFalse(
            capability[
                "temporal_numeric_scale_or_rank_order_post_generation_validator"
            ]
        )

    def test_authority_stops_at_build_and_credit_stays_zero(self) -> None:
        authorization = self.value["authorization"]
        self.assertTrue(authorization["generic_visible_constraint_successor_build"])
        self.assertFalse(authorization["new_external_population_protocol_or_forward"])
        self.assertFalse(authorization["deepwidebench_forward_or_evaluator"])
        self.assertEqual(self.value["positive_signed_credit_count"], 0)
        self.assertFalse(
            self.value[
                "task_rows_question_column_opaque_id_prediction_url_page_truth_evaluator_or_per_task_feature_persisted"
            ]
        )

    def test_resealed_reach_capability_launch_or_credit_tamper_fails(self) -> None:
        self.assertEqual(target.validate_audit(self.value), self.value)
        for kind in ("reach", "capability", "launch", "credit"):
            changed = copy.deepcopy(self.value)
            if kind == "reach":
                changed["visible_transfer"]["temporal_constraint_union_tasks"] = 121
            elif kind == "capability":
                changed["current_production_capability"][
                    "constraint_primitive_reference_hit_count"
                ] = 1
            elif kind == "launch":
                changed["authorization"]["deepwidebench_forward_or_evaluator"] = True
            else:
                changed["positive_signed_credit_count"] = 1
            changed.pop("audit_payload_sha256")
            changed["audit_payload_sha256"] = target.exact220.payload_sha256(
                changed
            )
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                target.validate_audit(changed)

    def test_create_exclusive_publisher(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "audit.json"
            target.publish_exclusive(path, {})
            with self.assertRaises(FileExistsError):
                target.publish_exclusive(path, {})

    def test_source_is_label_blind_under_semantic_ast_audit(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        for relative in (target.SOURCE, target.TEST):
            accesses, imports = audit.ast_findings(relative)
            self.assertEqual(accesses, [])
            self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
