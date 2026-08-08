from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24883_mapping_recovery_reliability_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import control_v24883_mapping_recovery_reliability_gate as control  # noqa: E402
from scripts import run_v24883_mapping_recovery_reliability_gate as runner  # noqa: E402


class V24883MappingRecoveryReliabilityGateTests(unittest.TestCase):
    def test_neutral_vector_is_twenty_and_label_blind(self) -> None:
        tasks = contract.task_vector()
        self.assertEqual(len(tasks), 20)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_gate_requires_nineteen_of_twenty(self) -> None:
        self.assertEqual(contract.MINIMUM_VALID_BUNDLES, 19)
        self.assertEqual(contract.TASK_COUNT, 20)
        self.assertEqual(contract.MAXIMUM_HARD_TIMEOUTS, 0)

    def test_execution_matches_exact220_shape(self) -> None:
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)
        self.assertEqual(contract.LIMITS["search_queries"], 4)
        self.assertEqual(contract.LIMITS["fetch_targets"], 10)
        self.assertEqual(contract.LIMITS["model_calls"], 3)

    def test_runtime_sources_are_label_blind(self) -> None:
        fields, evaluator, secrets = control._runtime_findings()
        self.assertEqual((fields, evaluator, secrets), ([], [], []))

    def test_runner_persists_no_private_rows(self) -> None:
        source = (ROOT / contract.RUNNER).read_text(encoding="utf-8")
        self.assertNotIn('"rows": rows', source)
        self.assertIn("terminal_stage_counts", source)

    def test_child_uses_stage_runtime(self) -> None:
        source = (ROOT / contract.CHILD).read_text(encoding="utf-8")
        self.assertIn("v24882_mapping_recovery_stage_runtime", source)
        self.assertNotIn("TAVILY_API_KEY", source)

    def test_forward_sources_have_no_evaluator_import(self) -> None:
        for relative in contract.RUNTIME_SOURCES:
            path = ROOT / relative
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
            self.assertEqual(semantic_audit._accesses(path.resolve(), ROOT), [])

    def test_runner_environment_is_minimal_and_keyless(self) -> None:
        environment = runner._environment()
        self.assertNotIn("TAVILY_API_KEYS", environment)
        self.assertEqual(environment["PYTHONNOUSERSITE"], "1")


if __name__ == "__main__":
    unittest.main()
