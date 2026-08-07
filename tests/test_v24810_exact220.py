from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24807_exact220_contract as parent
from deepwide_agent import v24810_exact220_contract as contract
from scripts import run_v24810_exact220 as runner
from scripts import run_v24810_exact220_task as task


class V24810Exact220Tests(unittest.TestCase):
    def test_algorithm_and_budget_equal_parent(self):
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(
            (
                contract.SELECTED_COUNT,
                contract.EXECUTOR_CONCURRENCY,
                contract.MODEL_SLOT_CAP,
            ),
            (220, 20, 8),
        )

    def test_fresh_surfaces(self):
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)
        self.assertNotEqual(contract.RUNNER_MARKER, parent.RUNNER_MARKER)
        self.assertNotEqual(contract.CHILD_MARKER, parent.CHILD_MARKER)

    def test_task_vector_label_blind(self):
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in tasks))

    def test_credentials_require_exactly_twelve(self):
        runner.configure()
        with self.assertRaises(RuntimeError):
            runner.base._read_credentials(io.StringIO("x\n"))
        values = runner.base._read_credentials(
            io.StringIO("\n".join(f"k{i}" for i in range(12)))
        )
        self.assertEqual(len(values), 12)

    def test_runner_rebinds_fresh_contract(self):
        runner.configure()
        self.assertIs(runner.base.contract, contract)

    def test_child_rejects_escape(self):
        task.base.contract = contract
        with self.assertRaises(RuntimeError):
            task.base._result_directory(["x", "--result", "/tmp/result.json"])

    def test_parent_protocol_is_sealed_and_task_bound(self):
        value = json.loads((ROOT / parent.PROTOCOL).read_text())
        unsigned = dict(value)
        seal = unsigned.pop("protocol_payload_sha256")
        self.assertEqual(seal, contract.payload_sha256(unsigned))
        self.assertEqual(len(contract.task_vector(ROOT)), 220)


if __name__ == "__main__":
    unittest.main()
