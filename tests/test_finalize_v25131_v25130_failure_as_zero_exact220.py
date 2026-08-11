from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v25130_causal_salience_exact220_contract as contract  # noqa: E402
from scripts import finalize_v25131_v25130_failure_as_zero_exact220 as target  # noqa: E402


class V25131FailureAsZeroExact220Tests(unittest.TestCase):
    def test_frozen_barrier_accepts_all_terminal_failure_as_zero_rows(self) -> None:
        value = target._forward_barrier()
        self.assertEqual(value["summary"]["selected"], 220)
        self.assertEqual(value["summary"]["completed"], 220)
        self.assertEqual(
            value["summary"]["runtime_completed"]
            + value["summary"]["failure_as_zero_tasks"],
            220,
        )
        self.assertEqual(value["summary"]["unattributable_prediction_changed_tasks"], 0)

    def test_mechanism_is_no_go_but_completed_row_causal_safety_passes(self) -> None:
        summary = json.loads((ROOT / contract.RUN_SUMMARY).read_text(encoding="utf-8"))
        value = target._mechanism_decision(summary)
        self.assertFalse(value["mechanism_gate_passed"])
        self.assertTrue(value["completed_row_causal_safety_passed"])
        self.assertIn("all_runtime_tasks_completed", value["failed_checks"])
        self.assertIn("all_220_causal_receipts_present", value["failed_checks"])
        self.assertFalse(value["retry_resume_replacement_or_selective_rerun_authorized"])

    def test_mechanism_tamper_fails_completed_row_safety(self) -> None:
        summary = json.loads((ROOT / contract.RUN_SUMMARY).read_text(encoding="utf-8"))
        changed = copy.deepcopy(summary)
        changed["unattributable_prediction_changed_tasks"] = 1
        value = target._mechanism_decision(changed)
        self.assertFalse(value["completed_row_causal_safety_passed"])

    def test_configure_binds_fixed_32_worker_official_evaluator(self) -> None:
        target.configure()
        self.assertIs(target.base.contract, contract)
        self.assertIs(target.base._forward_barrier, target._forward_barrier)
        self.assertEqual(target.base.EVALUATOR_WORKERS, 32)
        self.assertIn(str(target.SOURCE), target.base.CONTROL_FILES)
        self.assertIn(str(target.TEST), target.base.CONTROL_FILES)

    def test_audit_design_authorizes_evaluator_not_rerun(self) -> None:
        source = (ROOT / target.SOURCE).read_text(encoding="utf-8")
        self.assertIn('"postfreeze_exact220_evaluator_protocol": not findings', source)
        self.assertIn('"forward_retry_resume_skip_or_rerun": False', source)
        self.assertIn('"selective_evaluation_or_revaluation": False', source)


if __name__ == "__main__":
    unittest.main()
