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

from deepwide_agent.v24505_record_bound_timed_parent import (  # noqa: E402
    failure_projection,
)
from deepwide_agent.v24505_total_record_bound_projection import (  # noqa: E402
    aggregate_projections,
    normalize_projection,
    validate_aggregate,
)
import test_v24504_proof_carrying_record_bound_reserve as fixture  # noqa: E402


class V24505TotalRecordBoundProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture.V24504ProofCarryingRecordBoundReserveTests.setUpClass()
        owner = fixture.V24504ProofCarryingRecordBoundReserveTests()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            owner.populate(directory)
            capability = owner.validate(directory)
            from deepwide_agent.v24504_proof_carrying_record_bound_reserve import (
                task_projection,
            )

            cls.success = task_projection(1, capability)

    @classmethod
    def tearDownClass(cls) -> None:
        fixture.V24504ProofCarryingRecordBoundReserveTests.tearDownClass()

    def test_success_and_failure_normalize_to_same_total_surface(self) -> None:
        success = normalize_projection(self.success)
        failure = normalize_projection(failure_projection(2))
        self.assertEqual(set(success), set(failure))
        self.assertEqual(success["status"], "validated_capability")
        self.assertEqual(failure["status"], "failure_as_zero")
        self.assertTrue(success["projection_consumed_validated_capability"])
        self.assertFalse(failure["projection_consumed_validated_capability"])
        self.assertTrue(success["private_effects_known_zero"])
        self.assertFalse(failure["private_effects_known_zero"])

    def test_mixed_aggregate_preserves_conversion_and_failure_as_zero(self) -> None:
        value = aggregate_projections(
            [self.success, failure_projection(2)], selected=2
        )
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["failure_as_zero_tasks"], 1)
        self.assertEqual(value["record_bound_added_observation_tasks"], 1)
        self.assertEqual(value["safe_change_improvement_tasks"], 1)
        self.assertEqual(value["positive_decision_credit_gain_tasks"], 1)
        self.assertFalse(value["failure_rows_claim_zero_private_effects"])
        validate_aggregate(value)

    def test_failure_and_coordinated_aggregate_tamper_fail_closed(self) -> None:
        failure = failure_projection(2)
        for field, replacement in (
            ("additional_external_effects", 1),
            ("projection_consumed_validated_capability", True),
            ("private_effects_known_zero", True),
            ("private_task_content_emitted", True),
        ):
            changed = copy.deepcopy(failure)
            changed[field] = replacement
            with self.assertRaises(ValueError):
                normalize_projection(changed)
        value = aggregate_projections(
            [self.success, failure_projection(2)], selected=2
        )
        for field, replacement in (
            ("record_bound_added_observation_tasks", 0),
            ("positive_decision_credit_gain_tasks", 0),
            ("failure_rows_claim_zero_private_effects", True),
        ):
            changed = copy.deepcopy(value)
            changed[field] = replacement
            with self.assertRaises(ValueError):
                validate_aggregate(changed)

    def test_runtime_sources_are_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        for path in (
            Path("src/deepwide_agent/v24505_record_bound_timed_parent.py"),
            Path("src/deepwide_agent/v24505_total_record_bound_projection.py"),
        ):
            accesses, imports = audit._ast_findings(path)
            self.assertEqual(accesses, [])
            self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
