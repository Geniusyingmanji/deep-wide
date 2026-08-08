from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24904_revision_parser_total_reliability_contract as contract  # noqa: E402
from deepwide_agent import v24901_revision_parser_total_mapping_bundle as bundle  # noqa: E402
from deepwide_agent import v24902_revision_parser_total_child_runtime as child_runtime  # noqa: E402
from deepwide_agent import v24903_revision_parser_total_subprocess_gate as gate  # noqa: E402
from scripts import control_v24904_revision_parser_total_reliability_gate as control  # noqa: E402
from scripts import run_v24904_revision_parser_total_reliability_gate as runner  # noqa: E402
from scripts import run_v24904_revision_parser_total_reliability_task as child  # noqa: E402


class V24904RevisionParserTotalReliabilityGateTests(unittest.TestCase):
    def test_neutral_vector_is_exact_twenty_and_label_blind(self) -> None:
        tasks = contract.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_gate_go_threshold_is_nineteen_and_postaudit_requires_twenty(self) -> None:
        self.assertEqual(contract.MINIMUM_VALID_BUNDLES, 19)
        self.assertEqual(contract.TASK_COUNT, 20)
        self.assertEqual(contract.MAXIMUM_HARD_TIMEOUTS, 0)

    def test_resource_shape_is_full_concurrency(self) -> None:
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)
        self.assertEqual(contract.LIMITS["model_calls"], 3)

    def test_vector_covers_plain_fullwidth_and_row_boundaries(self) -> None:
        text = "\n".join(task["question"] for task in contract.task_vector())
        for token in ("U+FF5C", "512 data rows", "513 data rows", "700 data rows"):
            self.assertIn(token, text)

    def test_control_uses_fresh_contract(self) -> None:
        control.configure()
        self.assertIs(control.base.contract, contract)

    def test_child_binds_parser_total_runtime(self) -> None:
        child.configure()
        self.assertIs(child.base.run_child_bundle, child_runtime.run_child_bundle)

    def test_runner_binds_parser_total_bundle_and_gate(self) -> None:
        runner.configure()
        self.assertIs(runner.base.validate_bundle, bundle.validate_bundle)
        self.assertIs(runner.base.run_observed_bundle_subprocess, gate.run_observed_bundle_subprocess)

    def test_runtime_static_audit_is_label_blind(self) -> None:
        control.configure()
        fields, evaluator, secrets = control.base._runtime_findings()
        self.assertEqual((fields, evaluator, secrets), ([], [], []))

    def test_task_source_is_keyless(self) -> None:
        source = (ROOT / contract.CHILD).read_text(encoding="utf-8")
        self.assertNotIn("TAVILY_API_KEY", source)
        self.assertIn("v24902_revision_parser_total_child_runtime", source)


if __name__ == "__main__":
    unittest.main()
