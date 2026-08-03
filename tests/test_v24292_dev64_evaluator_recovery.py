from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24292_dev64_evaluator_recovery as recovery  # noqa: E402


class V24292EvaluatorRecoveryTests(unittest.TestCase):
    def test_protocol_is_evaluator_only_full_both_arm_and_no_resume(self) -> None:
        value = recovery.build_protocol(ROOT, now=1, require_pristine=False)
        self.assertEqual(value["evaluation_contract"]["arms"], ["control", "candidate"])
        self.assertEqual(value["evaluation_contract"]["selected_per_arm"], 64)
        self.assertEqual(value["evaluation_contract"]["fixed_contiguous_partition_sizes_per_arm"], [16, 16, 16, 16])
        self.assertFalse(value["evaluation_contract"]["resume"])
        self.assertFalse(value["evaluation_contract"]["selective_retry_or_error_revaluation"])
        self.assertFalse(value["authorization"]["forward_call_or_rerun"])
        self.assertFalse(value["authorization"]["additional_dev64_or_exact220"])

    def test_failure_is_proven_before_evaluator_root_or_worker_call(self) -> None:
        value = recovery.build_protocol(ROOT, now=1, require_pristine=False)
        failed = value["failed_attempt"]
        self.assertEqual(failed["exception"], recovery.FAILURE_EXCEPTION)
        self.assertTrue(failed["failed_before_evaluator_root_creation"])
        self.assertTrue(failed["failed_before_evaluator_worker_or_api_call"])
        self.assertTrue(failed["evaluator_root_absent_after_failure"])

    def test_recovery_acquires_outer_lease_before_execution_surface(self) -> None:
        source = inspect.getsource(recovery.run_recovery)
        lease = source.index("with acquire_deepwide_api_lease")
        start = source.index("_publish(root / EXECUTION_START")
        finalize = source.index("v91_finalizer.finalize")
        self.assertLess(lease, start)
        self.assertLess(start, finalize)

    def test_adapter_is_exactly_two_existing_paths_and_nested_lease(self) -> None:
        source = inspect.getsource(recovery.run_recovery)
        self.assertIn("v91_finalizer.CONTROL_RESULT = v91_preregister.CONTROL_RESULT", source)
        self.assertIn("v91_finalizer.CONTROL_POSTAUDIT = v91_preregister.CONTROL_POSTAUDIT", source)
        self.assertIn("_nested_lease_adapter", source)
        self.assertIn("delattr(v91_finalizer, \"CONTROL_RESULT\")", source)
        self.assertIn("delattr(v91_finalizer, \"CONTROL_POSTAUDIT\")", source)

    def test_postaudit_revalidates_original_final_result(self) -> None:
        source = inspect.getsource(recovery.build_postaudit)
        self.assertIn("v91_finalizer.validate_final_result", source)
        self.assertIn("v91_audit.build_postresult_report", source)
        self.assertIn("forward_rerun_resume_skip_or_prediction_mutation", source)
        self.assertIn("evaluator_resume_selective_retry_or_error_revaluation", source)


if __name__ == "__main__":
    unittest.main()
