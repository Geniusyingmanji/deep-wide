from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24492_targeted_timed_parent import failure_projection  # noqa: E402
from deepwide_agent.v24493_total_targeted_projection import (  # noqa: E402
    aggregate_projections,
    normalize_projection,
    validate_aggregate,
)
import test_v24491_proof_carrying_targeted_support as proof_fixture  # noqa: E402


class V24493TotalTargetedProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        proof_fixture.V24491ProofCarryingTargetedSupportTests.setUpClass()
        cls.owner = proof_fixture.V24491ProofCarryingTargetedSupportTests()
        with __import__("tempfile").TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            cls.owner.populate(directory)
            capability = cls.owner.validate(directory)
            from deepwide_agent.v24491_proof_carrying_targeted_support import task_projection

            cls.success = task_projection(1, capability)

    @classmethod
    def tearDownClass(cls) -> None:
        proof_fixture.V24491ProofCarryingTargetedSupportTests.tearDownClass()

    def test_success_and_failure_normalize_to_same_total_surface(self) -> None:
        success = normalize_projection(self.success)
        failure = normalize_projection(failure_projection(2))
        self.assertEqual(set(success), set(failure))
        self.assertEqual(success["status"], "validated_capability")
        self.assertEqual(failure["status"], "failure_as_zero")
        self.assertTrue(success["projection_consumed_validated_capability"])
        self.assertFalse(failure["projection_consumed_validated_capability"])

    def test_mixed_aggregate_is_total_and_conservative(self) -> None:
        value = aggregate_projections(
            [self.success, failure_projection(2)], selected=2
        )
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["failure_as_zero_tasks"], 1)
        self.assertEqual(value["safe_change_improvement_tasks"], 1)
        self.assertEqual(value["positive_decision_credit_tasks"], 1)
        self.assertFalse(value["failure_rows_claim_zero_private_effects"])
        validate_aggregate(value)

    def test_failure_tamper_and_resealed_aggregate_tamper_fail_closed(self) -> None:
        failure = failure_projection(2)
        for field, value in (
            ("additional_fetch_effects", 1),
            ("projection_consumed_validated_capability", True),
            ("private_task_content_emitted", True),
        ):
            changed = copy.deepcopy(failure)
            changed[field] = value
            with self.assertRaises(ValueError):
                normalize_projection(changed)
        aggregate = aggregate_projections(
            [self.success, failure_projection(2)], selected=2
        )
        aggregate["failure_rows_claim_zero_private_effects"] = True
        with self.assertRaises(ValueError):
            validate_aggregate(aggregate)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24493_total_targeted_projection.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
