from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24857_pacing_aware_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24969_pacing_aware_replication_contract as contract  # noqa: E402
from scripts import control_v24969_pacing_aware_replication as control  # noqa: E402
from scripts import finalize_v24969_pacing_aware_replication as finalizer  # noqa: E402
from scripts import run_v24800_exact220 as parent_runner  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220 as pacing_runner  # noqa: E402
from scripts import run_v24857_pacing_aware_exact220_task as pacing_child  # noqa: E402
from scripts import run_v24969_pacing_aware_replication as runner  # noqa: E402
from scripts import run_v24969_pacing_aware_replication_task as child  # noqa: E402


class V24969PacingAwareReplicationTests(unittest.TestCase):
    def test_algorithm_budget_capacity_and_policies_equal_parent(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertEqual(contract.rate_policy(), parent.rate_policy())
        self.assertEqual(contract.pacing_policy(), parent.pacing_policy())
        self.assertEqual(
            (
                contract.SELECTED_COUNT,
                contract.EXECUTOR_CONCURRENCY,
                contract.MODEL_SLOT_CAP,
                contract.TAVILY_KEY_SLOT_CAP,
            ),
            (220, 20, 8, 12),
        )

    def test_only_namespace_changes(self) -> None:
        self.assertNotEqual(contract.PROTOCOL, parent.PROTOCOL)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)
        change = contract._single_change()
        self.assertTrue(change["fresh_execution_and_artifact_surfaces_only"])
        self.assertTrue(change["independent_cold_single_rollout_replication"])
        self.assertFalse(change["entropy_or_information_gain_assigns_credit_or_routes"])

    def test_keyless_model_endpoint_and_fixed_hard_caps(self) -> None:
        self.assertEqual(contract.MODEL["proxy_url"], "http://127.0.0.1:9878/responses")
        self.assertEqual(
            {
                key: contract.LIMITS[key]
                for key in ("wall_seconds", "model_calls", "search_queries", "fetch_targets")
            },
            {
                "wall_seconds": 240,
                "model_calls": 3,
                "search_queries": 4,
                "fetch_targets": 10,
            },
        )

    def test_task_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_all_four_watchers_are_protected(self) -> None:
        self.assertEqual(
            [item["pid"] for item in contract.protected_watcher_snapshot()],
            [795336, 3061652, 2808901, 2889939],
        )

    def test_runner_rebinds_fresh_namespace(self) -> None:
        runner.configure()
        self.assertIs(pacing_runner.contract, contract)
        pacing_runner.configure()
        self.assertIs(parent_runner.contract, contract)

    def test_child_rebinds_fresh_namespace(self) -> None:
        child.configure()
        self.assertIs(pacing_child.contract, contract)

    def test_runtime_audit_has_no_privileged_or_evaluator_capability(self) -> None:
        control.configure()
        self.assertEqual(control.base._runtime_findings(), ([], [], []))
        self.assertEqual(control.base.EXPECTED_TESTS, 102)

    def test_finalizer_uses_fresh_complete_evaluator_surface(self) -> None:
        finalizer.configure()
        engine = finalizer.parent.base
        self.assertIn("v24969_pacing_aware_replication", str(engine.FINAL_RESULT))
        self.assertTrue(str(engine.EVALUATOR_ROOT).startswith(str(contract.OUTPUT_ROOT)))

    def test_create_only_publication_rejects_overwrite(self) -> None:
        control.configure()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            path = Path(directory) / "stage.json"
            control.base.publish_new(path, {})
            with self.assertRaises(FileExistsError):
                control.base.publish_new(path, {})


if __name__ == "__main__":
    unittest.main()
