from __future__ import annotations

import ast
import copy
import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24977_atomic_parser_quality_contract as contract  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
from scripts import control_v24977_atomic_parser_quality as control  # noqa: E402
from scripts import finalize_v24977_atomic_parser_quality as finalizer  # noqa: E402
from scripts import run_v24973_identity_bound_field_quality as schema_runner  # noqa: E402
from scripts import run_v24977_atomic_parser_quality as runner  # noqa: E402


class V24977AtomicParserQualityTests(unittest.TestCase):
    def test_population_is_fresh_fixed_and_unprobed(self) -> None:
        projects = {project for project, _repo in contract.TASKS}
        self.assertEqual(len(contract.TASKS), 20)
        self.assertEqual(len(set(contract.TASKS)), 20)
        self.assertFalse(projects & contract.PRIOR_PROJECTS)
        self.assertFalse(projects & contract.PROBED_PROJECTS)
        self.assertTrue(all(set(row) == {"opaque_id", "question"} for row in contract.task_vector()))

    def test_protocol_freezes_atomic_parser_barrier(self) -> None:
        value = contract.validate_protocol_untracked(
            ROOT, contract.build_protocol_untracked(ROOT, now=1)
        )
        atomic = value["atomic_parser_readiness"]
        self.assertTrue(atomic["fetch_all_tasks_before_model"])
        self.assertEqual(atomic["parser_ready_tasks"], 20)
        self.assertEqual(atomic["parser_ready_unique_fields"], 80)
        self.assertEqual(atomic["model_calls_if_parser_no_go"], 0)
        self.assertFalse(atomic["output_root_created_if_parser_no_go"])

    def _prepared(self, count: int = 20) -> list[dict]:
        return [
            {
                "index": index,
                "opaque_id": contract.task_vector()[index]["opaque_id"],
                "ready": True,
                "fetch_attempts": 2,
                "fetch_successes": 2,
                "receipt": {
                    "unique_bound_field_count": 4,
                    "conflicting_field_count": 0,
                },
            }
            for index in range(count)
        ]

    def test_parser_readiness_requires_all_twenty_and_eighty_fields(self) -> None:
        value = runner.parser_readiness(self._prepared())
        self.assertTrue(value["passed"])
        self.assertTrue(value["authorization"]["paired_model_forward"])
        bad = self._prepared()
        bad[0]["ready"] = False
        bad[0]["receipt"]["unique_bound_field_count"] = 0
        value = runner.parser_readiness(bad)
        self.assertFalse(value["passed"])
        self.assertFalse(value["authorization"]["paired_model_forward"])

    def test_parser_readiness_receipt_is_counts_only(self) -> None:
        value = runner.parser_readiness(self._prepared())
        self.assertFalse(value["contains_identity_question_value_url_page_prediction_or_credential"])
        self.assertFalse(value["model_search_or_evaluator_called_before_receipt"])
        self.assertNotIn("rows", value)

    def test_parser_readiness_rejects_denominator_or_duplicate_identity(self) -> None:
        with self.assertRaises(RuntimeError):
            runner.parser_readiness(self._prepared(19))
        rows = self._prepared()
        rows[1]["opaque_id"] = rows[0]["opaque_id"]
        with self.assertRaises(RuntimeError):
            runner.parser_readiness(rows)

    def test_parser_no_go_contract_forbids_model_and_output_root(self) -> None:
        source = (ROOT / contract.RUNTIME).read_text(encoding="utf-8")
        tree = ast.parse(source)
        run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run_forward")
        returns = [node for node in ast.walk(run) if isinstance(node, ast.Return)]
        self.assertGreaterEqual(len(returns), 2)
        self.assertIn("if not readiness[\"passed\"]", source)
        self.assertLess(
            source.index("if not readiness[\"passed\"]"),
            source.index("mkdir(mode=0o700"),
        )

    def test_prepare_failure_is_content_free_and_never_calls_model(self) -> None:
        with mock.patch.object(
            runner.transport, "_fetch_exact", side_effect=ValueError("failed")
        ), mock.patch.object(runner.schema_runner, "_synthesize") as model:
            value = runner._prepare(0)
        self.assertFalse(value["ready"])
        self.assertNotIn("question", value)
        model.assert_not_called()

    def test_runner_rebinds_section_bound_extractor(self) -> None:
        runner.configure()
        self.assertIs(schema_runner.contract, contract)
        self.assertIs(schema_runner.compact, runner.compact)

    def test_control_audit_covers_all_transitive_forward_sources(self) -> None:
        control.configure()
        for required in (
            contract.SOURCE, contract.EXTRACTOR, contract.RUNTIME,
            contract.PARENT_RUNTIME, contract.SCHEMA_RUNTIME, contract.FIELD_EXTRACTOR,
        ):
            self.assertIn(required, control.base.FORWARD_SOURCES)
        self.assertEqual(control.base.EXPECTED_TESTS, 64)

    def test_finalizer_rebinds_atomic_contract_and_runner(self) -> None:
        finalizer.configure()
        self.assertIs(finalizer.base.contract, contract)
        self.assertIs(finalizer.base.runner, runner)

    def test_forward_sources_are_label_blind_and_evaluator_free(self) -> None:
        control.configure()
        for relative in control.base.FORWARD_SOURCES:
            path = ROOT / relative
            self.assertEqual(semantic_audit._accesses(path, ROOT), [])
            self.assertEqual(semantic_audit._evaluator_capabilities(path, ROOT), [])

    def test_arm_order_is_deterministic_and_balanced(self) -> None:
        orders = contract.arm_order_vector()
        self.assertEqual(sum(order[0] == contract.CANDIDATE_ARM for order in orders), 10)
        self.assertTrue(all(set(order) == set(contract.ARMS) for order in orders))


if __name__ == "__main__":
    unittest.main()
