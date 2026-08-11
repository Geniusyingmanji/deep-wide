from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25130_causal_salience_exact220_contract as contract  # noqa: E402
from scripts import finalize_v25132_v25130_terminal_summary_exact220 as target  # noqa: E402


class V25132TerminalSummaryExact220Tests(unittest.TestCase):
    def test_projection_preserves_failure_as_zero_and_adds_zero_nonterminal(self) -> None:
        value = json.loads((ROOT / contract.RUN_SUMMARY).read_text(encoding="utf-8"))
        projected = target._project_terminal_summary(value)
        self.assertEqual(projected["completed"], 220)
        self.assertEqual(projected["failed"], 0)
        self.assertEqual(
            projected["terminal_summary_compatibility_projection"][
                "internal_runtime_failure_as_zero_tasks_preserved"
            ],
            value["failure_as_zero_tasks"],
        )
        self.assertEqual(value.get("failed"), None)

    def test_projection_rejects_nonterminal_or_unattributable_tamper(self) -> None:
        value = json.loads((ROOT / contract.RUN_SUMMARY).read_text(encoding="utf-8"))
        for field, changed in (("completed", 219), ("unattributable_prediction_changed_tasks", 1)):
            tampered = dict(value)
            tampered[field] = changed
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                target._project_terminal_summary(tampered)

    def test_prior_attempt_stopped_before_any_evaluator_effect(self) -> None:
        value = target._predecessor_disposition()
        self.assertEqual(
            value["failure_stage"],
            "pre_worker_terminal_summary_compatibility_check",
        )
        self.assertFalse(value["evaluator_root_created"])
        self.assertFalse(value["official_worker_started"])
        self.assertFalse(value["prediction_or_forward_artifact_modified"])

    def test_new_evaluator_paths_are_disjoint(self) -> None:
        self.assertNotEqual(target.EVALUATOR_PROTOCOL, contract.EVALUATOR_PROTOCOL)
        self.assertNotEqual(target.FINAL_RESULT, contract.RESULT)
        self.assertNotEqual(target.POSTAUDIT, contract.POSTAUDIT)
        self.assertNotEqual(target.EVALUATOR_ROOT, target.PRIOR_EVALUATOR_ROOT)

    def test_configure_installs_process_local_prepare_projection(self) -> None:
        target.configure()
        self.assertIs(
            target.parent.base.evaluator.prepare_evaluator_inputs,
            target._prepare_with_terminal_projection,
        )
        self.assertEqual(target.parent.base.EVALUATOR_PROTOCOL, target.EVALUATOR_PROTOCOL)
        self.assertIn(str(target.SOURCE), target.parent.base.CONTROL_FILES)

    def test_protocol_build_binds_projection_and_failed_predecessor(self) -> None:
        # build_evaluator_protocol requires clean/pushed controls, so inspect the
        # explicit source contract before publication in this unit test.
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertIn('"internal_failure_as_zero_rows_preserved": 27', source)
        self.assertIn('"projected_failed_nonterminal_rows": 0', source)
        self.assertIn('"forward_retry_resume_or_selective_rerun": False', source)


if __name__ == "__main__":
    unittest.main()
