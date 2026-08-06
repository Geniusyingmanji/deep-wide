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
from deepwide_agent.v24645_ror_external_contract import visible_task
from scripts import audit_v24645_primary_identity_forward as forward_audit
from scripts import run_v24645_primary_identity_pair as runner


class ForwardPackageTests(unittest.TestCase):
    def test_forward_sources_have_no_evaluator_or_private_surface(self) -> None:
        paths = (
            ROOT / "scripts/run_v24645_ror_task.py",
            ROOT / "scripts/run_v24645_primary_identity_pair.py",
            ROOT / "scripts/audit_v24645_primary_identity_forward.py",
        )
        forbidden = (
            "evaluation/",
            "v24645_ror_external_evaluator",
            "v24645_ror_population_private",
            "v24645_ror_gold_v1",
            "v24645_ror_gold_provenance",
        )
        for path in paths:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            imports: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imports.append(node.module or "")
            self.assertFalse(
                any("evaluator" in name.casefold() or "gold" in name.casefold() for name in imports)
            )
            for marker in forbidden:
                self.assertNotIn(marker, source)

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

    def test_identity_funnel_counts_are_complete_and_unique(self) -> None:
        expected = {
            "model_visible_page_count",
            "page_with_any_explicit_ror_count",
            "official_api_page_count",
            "entity_page_hit_count",
            "unique_page_pair_hit_count",
            "ambiguous_page_hit_count",
            "unknown_target_unique_pair_count",
            "unknown_target_ambiguous_pair_count",
            "unknown_target_no_pair_count",
            "admitted_replacement_count",
            "nonunknown_target_pair_count",
            "exact_title_identity_pair_count",
            "structured_primary_identity_pair_count",
            "body_only_identity_rejected_pair_count",
        }
        self.assertEqual(set(forward_audit.DISCOVERY_COUNTS), expected)
        self.assertEqual(len(forward_audit.DISCOVERY_COUNTS), len(expected))

    def test_runner_has_no_resume_retry_skip_or_selective_entrypoint(self) -> None:
        tree = ast.parse(
            (ROOT / "scripts/run_v24645_primary_identity_pair.py").read_text(
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
