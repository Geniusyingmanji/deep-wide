from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from deepwide_agent import v24273_two_wave_task_runtime as retrieval  # noqa: E402
from deepwide_agent import v24318_deadline_conservation_runtime as conservation  # noqa: E402
from deepwide_agent import v24319_runner_integration as runner  # noqa: E402
from deepwide_agent import v24630_exact220_task_integration as task  # noqa: E402
from deepwide_agent import v25022_production_distinct_coverage_task as target  # noqa: E402


class ProductionDistinctCoverageTaskTests(unittest.TestCase):
    def test_all_parent_bindings_remain_untouched(self) -> None:
        before = (
            retrieval.TwoWaveCachingSearchClient.search_many,
            conservation._run_parent,
            runner.run_v24319_task,
            task.run_v24630_task,
        )
        target.validate_isolation()
        self.assertEqual(
            before,
            (
                retrieval.TwoWaveCachingSearchClient.search_many,
                conservation._run_parent,
                runner.run_v24319_task,
                task.run_v24630_task,
            ),
        )

    def test_parent_code_objects_are_reused(self) -> None:
        self.assertIs(
            target._ISOLATED_SEARCH_MANY.__code__,
            retrieval.TwoWaveCachingSearchClient.search_many.__code__,
        )
        self.assertIs(target._ISOLATED_RUN_PARENT.__code__, conservation._run_parent.__code__)
        self.assertIs(
            target._ISOLATED_RUN_V24318_TASK.__code__,
            conservation.run_v24318_task.__code__,
        )
        self.assertIs(
            target._ISOLATED_RUN_V24319_TASK.__code__, runner.run_v24319_task.__code__
        )
        self.assertIs(target._PARENT_RUN_TASK.__code__, task.run_v24630_task.__code__)

    def test_parent_retrieval_payload_drops_sidecar_receipts(self) -> None:
        source = (ROOT / "src/deepwide_agent/v25022_production_distinct_coverage_task.py").read_text(
            encoding="utf-8"
        )
        self.assertIn('output.pop("pacing_admission_receipt", None)', source)
        self.assertIn(
            'output.pop("distinct_coverage_selection_receipt", None)', source
        )

    def test_module_has_no_direct_effect_or_privileged_import(self) -> None:
        path = ROOT / "src/deepwide_agent/v25022_production_distinct_coverage_task.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        for forbidden in (
            "os",
            "pathlib",
            "socket",
            "subprocess",
            "requests",
            "deepwidebench",
        ):
            self.assertFalse(
                any(name == forbidden or name.startswith(forbidden + ".") for name in imports)
            )
        for forbidden in ("ground_truth", "answer_key", "results.csv"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
