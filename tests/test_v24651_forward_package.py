from __future__ import annotations

import ast
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24639_ror_objective_runtime import _matrix
from deepwide_agent.v24651_ror_external_contract import visible_task
from scripts import audit_v24651_unknown_target_forward as forward_audit
from scripts import run_v24651_unknown_target_structured as runner


class ForwardPackageTests(unittest.TestCase):
    def test_authorization_artifacts_are_required_before_any_effect(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch.object(runner, "ROOT", root),
                patch.object(runner.socket, "create_connection") as socket_call,
                patch.object(runner.subprocess, "Popen") as process_call,
                patch.object(runner, "acquire_deepwide_api_lease") as lease_call,
            ):
                with self.assertRaisesRegex(RuntimeError, "expected ordinary object"):
                    runner.main()
            socket_call.assert_not_called()
            process_call.assert_not_called()
            lease_call.assert_not_called()

    def test_failure_projection_is_identical_for_both_arms(self) -> None:
        prediction = runner.fallback(visible_task(1))
        self.assertEqual(set(prediction), set(runner.ARMS))
        self.assertEqual(len(set(prediction.values())), 1)
        columns, rows = _matrix(next(iter(prediction.values())))
        self.assertEqual(tuple(columns), runner.EXPECTED_COLUMNS)
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(row[1] == "Unknown" and row[2] == "Unknown" for row in rows))

    def test_forward_audit_count_surfaces_are_complete_and_unique(self) -> None:
        self.assertEqual(len(forward_audit.LOOKUP_COUNTS), len(set(forward_audit.LOOKUP_COUNTS)))
        self.assertEqual(
            len(forward_audit.DISCOVERY_COUNTS),
            len(set(forward_audit.DISCOVERY_COUNTS)),
        )
        self.assertIn("admitted_replacement_count", forward_audit.DISCOVERY_COUNTS)
        self.assertIn("unique_exact_response_count", forward_audit.LOOKUP_COUNTS)

    def test_forward_audit_mechanism_gate_precedes_evaluator(self) -> None:
        source = (ROOT / "scripts/audit_v24651_unknown_target_forward.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("postfreeze_external_evaluator_protocol_design", source)
        self.assertIn("mechanism_triggered", source)
        self.assertNotIn("v24651_ror_external_evaluator", source)
        self.assertNotIn("evaluation/", source)

    def test_runner_has_no_resume_retry_skip_or_selective_entrypoint(self) -> None:
        tree = ast.parse(
            (ROOT / "scripts/run_v24651_unknown_target_structured.py").read_text(
                encoding="utf-8"
            )
        )
        functions = {
            node.name
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertFalse(
            functions
            & {
                "resume",
                "retry",
                "rerun",
                "skip",
                "run_missing",
                "resume_task",
                "retry_task",
            }
        )
        source = ast.unparse(tree)
        self.assertIn("resume_retry_skip_or_selective_rerun", source)
        self.assertIn("False", source)


if __name__ == "__main__":
    unittest.main()
