from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24303_paired_dev_runtime as parent  # noqa: E402
from deepwide_agent import v24306_paired_dev_runtime as target  # noqa: E402


class V24306PairedDevRuntimeTests(unittest.TestCase):
    def test_task_runtime_is_exact_parent_alias(self) -> None:
        self.assertIs(target.run_v24306_task, parent.run_v24303_task)
        self.assertIs(target.validate_v24306_result, parent.validate_v24303_result)
        self.assertIs(target.zero_effect_receipt, parent.zero_effect_receipt)
        self.assertEqual(target.RECEIPT_FIELD, parent.RECEIPT_FIELD)
        self.assertEqual(target.POLICY_ID, parent.POLICY_ID)

    def test_only_cross_task_contract_may_change(self) -> None:
        self.assertIs(
            target.SynthesisRecoveryControlModel,
            parent.SynthesisRecoveryControlModel,
        )
        self.assertIs(target.validate_receipt, parent.validate_receipt)


if __name__ == "__main__":
    unittest.main()
