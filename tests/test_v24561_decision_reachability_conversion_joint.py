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

from deepwide_agent import v24555_decision_reachability_planner as planner  # noqa: E402
from deepwide_agent import v24557_proof_carrying_decision_reachability as proof  # noqa: E402
from deepwide_agent import v24561_decision_reachability_conversion_joint as target  # noqa: E402
from test_v24524_alias_title_integration import TASK  # noqa: E402
from test_v24550_total_alias_joint_projection import positive_capability  # noqa: E402
from test_v24549_proof_carrying_alias_joint import (  # noqa: E402
    populate as populate_parent,
)
from test_v24557_proof_carrying_decision_reachability import (  # noqa: E402
    populate,
    validate,
)


class V24561DecisionReachabilityConversionJointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.root = Path(cls.temporary.name)
        reachability_root = cls.root / "reachability"
        reachability_root.mkdir()
        populate(reachability_root)
        cls.capability = validate(reachability_root)
        parent_root = cls.root / "parent"
        parent_root.mkdir()
        populate_parent(parent_root)
        positive_root = cls.root / "positive"
        parent = positive_capability(parent_root, positive_root)
        receipt = cls.capability.decision_reachability_receipt()
        receipt["no_reachable_plan_calls"] -= 1
        receipt["one_observation_plan_calls"] += 1
        receipt["legacy_entropy_choice_changed_calls"] += 1
        receipt["reachable_candidate_count_total"] = max(
            receipt["reachable_candidate_count_total"], 1
        )
        planner.validate_receipt(receipt)
        cls.positive = proof.ValidatedProofCarryingDecisionReachability._create(
            parent=parent,
            receipt=receipt,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_positive_capability_mints_both_task_level_conversion_joints(self) -> None:
        row = target.task_projection(1, self.positive)
        self.assertEqual(row["status"], "validated_capability")
        self.assertEqual(
            row[
                "decision_reachability_one_observation_full_conversion_joint"
            ],
            1,
        )
        self.assertEqual(
            row[
                "decision_reachability_changed_legacy_full_conversion_joint"
            ],
            1,
        )
        self.assertFalse(
            row[
                "decision_reachability_conversion_joint_claims_call_or_lead_level_causality"
            ]
        )

    def test_failure_row_is_exact_zero_without_private_effect_claim(self) -> None:
        row = target.failure_projection(2)
        self.assertEqual(row["status"], "failure_as_zero")
        self.assertEqual(
            row[
                "decision_reachability_one_observation_full_conversion_joint"
            ],
            0,
        )
        self.assertFalse(
            row["decision_reachability_additional_private_effects_known_zero"]
        )

    def test_public_success_dictionary_cannot_be_reingested_as_proof(self) -> None:
        row = target.task_projection(1, self.positive)
        with self.assertRaises(TypeError):
            target.task_projection(1, row)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            target.aggregate_projections([row], selected=1)

    def test_mixed_aggregate_preserves_joint_denominator_and_parent_counts(self) -> None:
        value = target.aggregate_projections(
            [self.positive, target.failure_projection(2)], selected=2
        )
        self.assertEqual(value["selected"], 2)
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["failure_as_zero_tasks"], 1)
        self.assertEqual(
            value[
                "decision_reachability_one_observation_full_conversion_joint_tasks"
            ],
            1,
        )
        self.assertEqual(
            value[
                "decision_reachability_changed_legacy_full_conversion_joint_tasks"
            ],
            1,
        )
        self.assertEqual(value["alias_joint_safe_change_improvement_tasks"], 1)
        self.assertTrue(
            value[
                "all_decision_reachability_failure_rows_are_content_free_zero_projections"
            ]
        )

    def test_row_and_aggregate_coordinated_tamper_fail_closed(self) -> None:
        row = target.task_projection(1, self.positive)
        changed = copy.deepcopy(row)
        changed[
            "decision_reachability_changed_legacy_full_conversion_joint"
        ] = 0
        with self.assertRaises(ValueError):
            target.validate_total_row(changed)
        aggregate = target.aggregate_projections([self.positive], selected=1)
        cases = (
            lambda value: value.__setitem__(
                "decision_reachability_one_observation_full_conversion_joint_tasks",
                0,
            ),
            lambda value: value[
                "total_decision_reachability_conversion_joint_count_fields"
            ].__setitem__("changed_legacy_full_conversion_joint", 0),
            lambda value: value.__setitem__(
                "decision_reachability_conversion_joint_claims_call_or_lead_level_causality",
                True,
            ),
        )
        for alter in cases:
            with self.subTest(alter=alter):
                changed = copy.deepcopy(aggregate)
                alter(changed)
                with self.assertRaises(ValueError):
                    target.validate_aggregate(changed)

    def test_public_projection_is_content_free_and_label_blind(self) -> None:
        encoded = json.dumps(
            target.task_projection(1, self.positive),
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
                "src/deepwide_agent/v24561_decision_reachability_conversion_joint.py"
            )
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
