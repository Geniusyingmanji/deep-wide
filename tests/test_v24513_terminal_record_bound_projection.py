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

from deepwide_agent.v24513_terminal_record_bound_projection import (  # noqa: E402
    aggregate_projections,
    failure_projection,
    task_projection,
    validate_aggregate,
    validate_total_row,
)
from deepwide_agent.v24504_proof_carrying_record_bound_reserve import (  # noqa: E402
    task_projection as base_task_projection,
)
from deepwide_agent import (  # noqa: E402
    v24504_proof_carrying_record_bound_reserve as base,
)
import test_v24504_proof_carrying_record_bound_reserve as fixture  # noqa: E402


class V24513TerminalRecordBoundProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture.V24504ProofCarryingRecordBoundReserveTests.setUpClass()
        owner = fixture.V24504ProofCarryingRecordBoundReserveTests()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            owner.populate(directory)
            cls.capability = owner.validate(directory)

    @classmethod
    def tearDownClass(cls) -> None:
        fixture.V24504ProofCarryingRecordBoundReserveTests.tearDownClass()

    def test_success_exposes_absolute_parent_and_terminal_state(self) -> None:
        row = task_projection(1, self.capability)
        self.assertEqual(row["parent_safe_change_count"], 0)
        self.assertEqual(row["terminal_safe_change_count"], 1)
        self.assertEqual(row["parent_decision_credit_total_nats"], 0)
        self.assertGreater(row["terminal_decision_credit_total_nats"], 0)
        self.assertTrue(row["terminal_state_consumed_validated_capability"])

    def test_failure_is_total_but_does_not_claim_private_effects(self) -> None:
        row = failure_projection(2)
        self.assertEqual(row["terminal_safe_change_count"], 0)
        self.assertEqual(row["terminal_decision_credit_total_nats"], 0)
        self.assertFalse(row["terminal_state_consumed_validated_capability"])
        self.assertFalse(row["private_effects_known_zero"])

    def test_aggregate_distinguishes_terminal_success_from_stage_gain(self) -> None:
        preserved = copy.deepcopy(base_task_projection(1, self.capability))
        preserved["parent_safe_change_count"] = 1
        preserved["parent_candidate_changed_cell_count"] = 1
        preserved["candidate_change_improvement_count"] = 0
        preserved["parent_positive_information_gain_total_nats"] = preserved[
            "record_bound_positive_information_gain_total_nats"
        ]
        preserved["positive_information_gain_gain_nats"] = 0.0
        preserved["parent_epistemic_credit_total_nats"] = preserved[
            "record_bound_epistemic_credit_total_nats"
        ]
        preserved["epistemic_credit_gain_nats"] = 0.0
        preserved["parent_decision_credit_total_nats"] = preserved[
            "record_bound_decision_credit_total_nats"
        ]
        preserved["safe_change_improvement_count"] = 0
        preserved["decision_credit_gain_nats"] = 0.0
        preserved["checks"] = base._projection_checks(preserved)
        preserved["passed"] = all(preserved["checks"].values())
        preserved = base.validate_task_projection(preserved)
        value = aggregate_projections([preserved, failure_projection(2)], selected=2)
        self.assertEqual(value["safe_change_improvement_tasks"], 0)
        self.assertEqual(value["positive_decision_credit_gain_tasks"], 0)
        self.assertEqual(value["terminal_safe_change_tasks"], 1)
        self.assertEqual(value["terminal_positive_decision_credit_tasks"], 1)
        self.assertGreater(value["total_terminal_decision_credit_nats"], 0)

    def test_aggregate_accepts_existing_parent_success_projection_directly(self) -> None:
        raw = base_task_projection(1, self.capability)
        value = aggregate_projections([raw, failure_projection(2)], selected=2)
        self.assertEqual(value["success_tasks"], 1)
        self.assertEqual(value["terminal_safe_change_tasks"], 1)
        self.assertEqual(value["terminal_positive_decision_credit_tasks"], 1)
        self.assertGreater(value["total_terminal_decision_credit_nats"], 0)

    def test_terminal_tamper_fails_closed(self) -> None:
        row = task_projection(1, self.capability)
        cases = (
            ("terminal_safe_change_count", 0),
            ("terminal_decision_credit_total_nats", 0.0),
            ("terminal_state_consumed_validated_capability", False),
        )
        for field, replacement in cases:
            changed = copy.deepcopy(row)
            changed[field] = replacement
            with self.assertRaises(ValueError, msg=field):
                validate_total_row(changed)
        aggregate = aggregate_projections(
            [base_task_projection(1, self.capability)], selected=1
        )
        changed = copy.deepcopy(aggregate)
        changed["terminal_safe_change_tasks"] = 0
        with self.assertRaises(ValueError):
            validate_aggregate(changed)
        for field in (
            "total_terminal_safe_change_count",
            "total_terminal_decision_credit_nats",
        ):
            changed = copy.deepcopy(aggregate)
            changed[field] = 0
            with self.assertRaises(ValueError, msg=field):
                validate_aggregate(changed)

    def test_expanded_terminal_row_cannot_launder_provenance(self) -> None:
        row = task_projection(1, self.capability)
        self.assertEqual(validate_total_row(row), row)
        with self.assertRaises(ValueError):
            aggregate_projections([row], selected=1)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24513_terminal_record_bound_projection.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
