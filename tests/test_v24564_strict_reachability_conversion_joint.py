from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24564_strict_reachability_conversion_joint as target  # noqa: E402
import test_v24561_decision_reachability_conversion_joint as fixture  # noqa: E402


class V24564StrictReachabilityConversionJointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture.V24561DecisionReachabilityConversionJointTests.setUpClass()
        cls.capability = (
            fixture.V24561DecisionReachabilityConversionJointTests.capability
        )
        cls.positive = fixture.V24561DecisionReachabilityConversionJointTests.positive

    @classmethod
    def tearDownClass(cls) -> None:
        fixture.V24561DecisionReachabilityConversionJointTests.tearDownClass()

    def test_strict_joint_requires_one_observation_and_changed_legacy_same_task(self) -> None:
        row = target.task_projection(1, self.positive)
        self.assertEqual(row[target.FIELD], 1)
        self.assertGreater(
            row["decision_reachability_one_observation_plan_calls"], 0
        )
        self.assertGreater(
            row["decision_reachability_legacy_entropy_choice_changed_calls"], 0
        )
        self.assertEqual(
            row[
                "decision_reachability_one_observation_full_conversion_joint"
            ],
            1,
        )

    def test_failure_and_nonconversion_rows_are_zero(self) -> None:
        self.assertEqual(target.failure_projection(2)[target.FIELD], 0)
        self.assertEqual(target.task_projection(1, self.capability)[target.FIELD], 0)

    def test_public_success_row_cannot_be_reingested(self) -> None:
        row = target.task_projection(1, self.positive)
        with self.assertRaises(TypeError):
            target.task_projection(1, row)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            target.aggregate_projections([row], selected=1)

    def test_mixed_aggregate_and_tamper_fail_closed(self) -> None:
        value = target.aggregate_projections(
            [self.positive, target.failure_projection(2)], selected=2
        )
        self.assertEqual(value[target.TASK_FIELD], 1)
        changed = copy.deepcopy(value)
        changed[target.TASK_FIELD] = 0
        # Zero is internally possible from marginals, so use an impossible count
        # to verify the public aggregate bounds fail closed.
        changed[target.TASK_FIELD] = 2
        with self.assertRaises(ValueError):
            target.validate_aggregate(changed)
        row = target.task_projection(1, self.positive)
        changed_row = copy.deepcopy(row)
        changed_row[target.FIELD] = 0
        with self.assertRaises(ValueError):
            target.validate_total_row(changed_row)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24564_strict_reachability_conversion_joint.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
