from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24800_exact220_contract as parent  # noqa: E402
from deepwide_agent import (  # noqa: E402
    v24850_v24800_replication_exact220_contract as contract,
)
from scripts import control_v24850_v24800_replication_exact220 as control  # noqa: E402
from scripts import finalize_v24850_v24800_replication_exact220 as finalizer  # noqa: E402
from scripts import run_v24800_exact220 as parent_runner  # noqa: E402
from scripts import run_v24800_exact220_task as parent_child  # noqa: E402
from scripts import run_v24850_v24800_replication_exact220 as runner  # noqa: E402
from scripts import run_v24850_v24800_replication_exact220_task as child  # noqa: E402


class V24850ReplicationTests(unittest.TestCase):
    def test_algorithm_budget_and_policy_are_exact_parent_equal(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, 20)
        self.assertEqual(contract.MODEL_SLOT_CAP, 8)
        self.assertEqual(contract.TAVILY_KEY_SLOT_CAP, 12)

    def test_surfaces_are_fresh_and_do_not_alias_parent(self) -> None:
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)
        self.assertNotEqual(contract.RUNNER_MARKER, parent.RUNNER_MARKER)
        self.assertNotEqual(contract.CHILD_MARKER, parent.CHILD_MARKER)

    def test_visible_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_protocol_declares_replication_without_prior_outputs(self) -> None:
        value = contract.build_protocol(
            ROOT, now=1, require_clean=False, require_pristine=False
        )
        self.assertEqual(value["parent_algorithm"]["protocol_id"], parent.PROTOCOL_ID)
        self.assertTrue(
            value["single_change"]["fresh_execution_and_artifact_surfaces_only"]
        )
        self.assertFalse(
            value["source_policy"][
                "prior_v24800_output_prediction_result_score_or_evaluator_opened_or_hashed"
            ]
        )
        self.assertEqual(value["task_contract"]["runtime_input_keys"], ["opaque_id", "question"])

    def test_manifest_contains_only_tracked_in_repo_dependencies(self) -> None:
        manifest = contract.dependency_manifest(ROOT)
        self.assertIn(str(contract.SOURCE), manifest)
        self.assertIn(str(contract.RUNNER), manifest)
        self.assertIn(str(contract.CHILD), manifest)
        self.assertIn(str(parent.PROTOCOL), manifest)
        self.assertFalse(any(name.startswith("outputs/") for name in manifest))

    def test_runner_rebinds_parent_to_fresh_contract(self) -> None:
        original = parent_runner.contract
        try:
            runner.configure()
            self.assertIs(parent_runner.contract, contract)
        finally:
            parent_runner.contract = original

    def test_child_rebinds_parent_to_fresh_contract(self) -> None:
        original = parent_child.contract
        try:
            child.configure()
            self.assertIs(parent_child.contract, contract)
        finally:
            parent_child.contract = original

    def test_control_audits_new_and_inherited_runtime_surfaces(self) -> None:
        control.configure()
        self.assertEqual(control.base.EXPECTED_TESTS, 60)
        self.assertIn(contract.RUNNER, control.base.RUNTIME_SOURCES)
        self.assertIn(contract.CHILD, control.base.RUNTIME_SOURCES)
        fields, evaluator, secrets = control.base._runtime_findings()
        self.assertEqual((fields, evaluator, secrets), ([], [], []))

    def test_finalizer_uses_fresh_evaluator_surface_and_parent_reference(self) -> None:
        finalizer.configure()
        self.assertEqual(finalizer.base.contract, contract)
        self.assertTrue(str(finalizer.base.EVALUATOR_ROOT).startswith(str(contract.OUTPUT_ROOT)))
        self.assertIn("v24800", finalizer.base.REFERENCES)

    def test_runtime_wrappers_have_no_evaluator_import_or_privileged_literal(self) -> None:
        forbidden = {"category", "question_type", "ground_truth", "answer_key"}
        for path in (contract.RUNNER, contract.CHILD):
            source = (ROOT / path).read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))
            self.assertTrue(all(token not in source for token in forbidden))


if __name__ == "__main__":
    unittest.main()
