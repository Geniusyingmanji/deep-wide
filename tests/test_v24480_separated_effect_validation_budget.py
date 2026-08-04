from __future__ import annotations

import copy
import sys
import unittest
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v24480_separated_effect_validation_budget as target,
)


class V24480SeparatedEffectValidationBudgetTests(unittest.TestCase):
    def test_exact_phase_budget_is_frozen(self) -> None:
        deadlines = target.build_phase_deadlines(origin=1000.0)
        self.assertEqual(deadlines.remote_effect, 1150.0)
        self.assertEqual(deadlines.worker, 1220.0)
        self.assertEqual(deadlines.parent, 1245.0)
        self.assertEqual(target.REMOTE_EFFECT_SECONDS, 150.0)
        self.assertEqual(target.LOCAL_VALIDATION_RESERVE_SECONDS, 70.0)
        self.assertEqual(target.PARENT_CLOSURE_RESERVE_SECONDS, 25.0)
        self.assertEqual(target.BATCH_WALL_CEILING_SECONDS, 255.0)

    def test_remote_effect_expires_while_local_validation_remains(self) -> None:
        deadlines = target.build_phase_deadlines(origin=1000.0)
        self.assertAlmostEqual(
            target.remaining_remote_effect_seconds(
                deadlines, monotonic=lambda: 1149.5
            ),
            0.5,
        )
        with self.assertRaisesRegex(RuntimeError, "remote-effect deadline"):
            target.remaining_remote_effect_seconds(
                deadlines, monotonic=lambda: 1150.0
            )
        self.assertEqual(
            target.remaining_worker_seconds(deadlines, monotonic=lambda: 1150.0),
            70.0,
        )
        self.assertEqual(
            target.remaining_parent_seconds(deadlines, monotonic=lambda: 1150.0),
            95.0,
        )

    def test_expired_worker_and_parent_return_only_minimal_cleanup_window(self) -> None:
        deadlines = target.build_phase_deadlines(origin=1000.0)
        self.assertEqual(
            target.remaining_worker_seconds(deadlines, monotonic=lambda: 1221.0),
            1e-6,
        )
        self.assertEqual(
            target.remaining_parent_seconds(deadlines, monotonic=lambda: 1246.0),
            1e-6,
        )

    def test_altered_deadline_or_contract_fails_closed(self) -> None:
        deadlines = target.build_phase_deadlines(origin=1000.0)
        for changed in (
            replace(deadlines, remote_effect=1151.0),
            replace(deadlines, worker=1219.0),
            replace(deadlines, parent=1246.0),
        ):
            with self.subTest(changed=changed):
                with self.assertRaises(ValueError):
                    target.validate_phase_deadlines(changed)
        contract = target.budget_contract()
        changed_contract = copy.deepcopy(contract)
        changed_contract["remote_effect_seconds"] = 220.0
        with self.assertRaises(ValueError):
            target.validate_budget_contract(changed_contract)

    def test_contract_is_content_free_and_does_not_authorize_launch(self) -> None:
        contract = target.budget_contract()
        self.assertTrue(contract["remote_effect_budget_unchanged_from_v24478"])
        self.assertTrue(
            contract[
                "local_validation_budget_is_not_available_to_remote_effect_clients"
            ]
        )
        self.assertFalse(contract["same_v24478_population_rerun_allowed"])
        self.assertFalse(contract["benchmark_launch_or_evaluator_authorized"])
        self.assertFalse(
            contract[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path(
                "src/deepwide_agent/v24480_separated_effect_validation_budget.py"
            )
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
