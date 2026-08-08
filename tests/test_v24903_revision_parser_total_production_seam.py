from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24899_revision_parser_total_exact_task as exact_task  # noqa: E402
from deepwide_agent import v24900_revision_parser_total_runtime as runtime  # noqa: E402
from deepwide_agent import v24901_revision_parser_total_mapping_bundle as bundle  # noqa: E402
from deepwide_agent import v24902_revision_parser_total_child_runtime as child  # noqa: E402
from deepwide_agent import v24903_revision_parser_total_subprocess_gate as gate  # noqa: E402
from scripts import audit_v24635_exact220 as semantic_audit  # noqa: E402
import test_v24860_coverage_revision_integration as core  # noqa: E402
import test_v24875_keyless_coverage_child_runtime as child_fixture  # noqa: E402


PLAN = json.dumps(
    {"columns": ["Name", "Code", "Note"], "queries": ["one", "two", "three", "four"]}
)
TABLE = "| Name | Code | Note |\n| --- | --- | --- |\n| Alpha | left｜right | Stable |"
TASK = {
    "opaque_id": "task_0123456789abcdef01234567",
    "question": "Return one table. The column names are: Name, Code, Note.",
}


class V24903RevisionParserTotalProductionSeamTests(unittest.TestCase):
    def _clients(self, output: Path):
        clock, inner, model, search = (
            child_fixture.V24875KeylessCoverageChildRuntimeTests().clients(
                output, child_fixture.MeteredFullSearch
            )
        )
        inner.values = [PLAN, TABLE, "must-not-be-consumed"]
        return clock, inner, model, search

    def test_runtime_fullwidth_pipe_is_two_call_identity(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            clock, inner, model, search = self._clients(output)
            outcome = runtime.run_v24900_task(
                TASK, arm="baseline", model=model, search=search,
                limits=core.limits(), monotonic=clock,
            )
            self.assertEqual(inner.requests, 2)
            self.assertEqual(model.receipt()["acquisitions"], 2)
            self.assertEqual(
                outcome.coverage_revision_receipt["disposition"],
                "identity_parent_not_eligible",
            )
            self.assertEqual(
                outcome.result["prediction"],
                outcome.result["parent_result"]["prediction"],
            )

    def test_mapping_bundle_round_trips_fullwidth_pipe(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            clock, inner, model, search = self._clients(output)
            outcome = runtime.run_v24900_task(
                TASK, arm="baseline", model=model, search=search,
                limits=core.limits(), monotonic=clock,
            )
            directory = output / "task"
            directory.mkdir()
            bundle.write_bundle(
                output_root=output, directory=directory, outcome=outcome,
                status_counts=search.status_counts,
                transport_failures=search.transport_failures,
                hard_total_wall_timeouts=search.hard_total_wall_timeouts,
                expected_model_slot_cap=2,
            )
            bundle.validate_bundle(
                output_root=output, directory=directory,
                expected_model_slot_cap=2,
            )
            envelope = exact_task.validate_envelope(
                json.loads((directory / bundle.RESULT_NAME).read_text(encoding="utf-8"))
            )
            self.assertEqual(inner.requests, 2)
            self.assertEqual(
                envelope["result"]["prediction"],
                envelope["result"]["parent_result"]["prediction"],
            )

    def test_child_commits_fullwidth_pipe_bundle(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output = Path(temporary)
            directory = output / "task"
            directory.mkdir()
            clock, inner, model, search = self._clients(output)
            child.run_child_bundle(
                output_root=output, directory=directory, task=TASK,
                model=model, search=search, limits=core.limits(),
                expected_model_slot_cap=2, monotonic=clock,
            )
            bundle.validate_bundle(
                output_root=output, directory=directory,
                expected_model_slot_cap=2,
            )
            self.assertEqual(inner.requests, 2)
            self.assertTrue((directory / child.TERMINAL_NAME).is_file())

    def test_all_append_only_bindings_are_isolated(self) -> None:
        exact_task.validate_isolation()
        runtime.validate_isolation()
        bundle.validate_isolation()
        child.validate_isolation()
        gate.validate_isolation()

    def test_runtime_sources_are_label_blind(self) -> None:
        paths = (
            "src/deepwide_agent/v24897_revision_parser_totality.py",
            "src/deepwide_agent/v24898_revision_parser_total_integration.py",
            "src/deepwide_agent/v24899_revision_parser_total_exact_task.py",
            "src/deepwide_agent/v24900_revision_parser_total_runtime.py",
            "src/deepwide_agent/v24901_revision_parser_total_mapping_bundle.py",
            "src/deepwide_agent/v24902_revision_parser_total_child_runtime.py",
            "src/deepwide_agent/v24903_revision_parser_total_subprocess_gate.py",
        )
        for relative in paths:
            with self.subTest(relative=relative):
                path = (ROOT / relative).resolve()
                self.assertEqual(semantic_audit._accesses(path, ROOT), [])
                self.assertEqual(semantic_audit._evaluator_capabilities(path, ROOT), [])


if __name__ == "__main__":
    unittest.main()
