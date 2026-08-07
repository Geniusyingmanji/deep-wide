from __future__ import annotations

import ast
import dataclasses
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24272_two_wave_entropy_voc as kernel  # noqa: E402
from deepwide_agent import v24831_keyless_exact220_contract as parent  # noqa: E402
from deepwide_agent import v24833_coverage_margin_controller as controller  # noqa: E402
from deepwide_agent import v24834_coverage_margin_exact220_contract as contract  # noqa: E402
from scripts import run_v24834_coverage_margin_exact220_task as child  # noqa: E402


class V24834CoverageMarginExact220Tests(unittest.TestCase):
    def test_task_vector_is_exact220_and_label_blind(self) -> None:
        tasks = contract.task_vector(ROOT)
        self.assertEqual(len(tasks), 220)
        self.assertEqual(len({task["opaque_id"] for task in tasks}), 220)
        self.assertTrue(all(set(task) == {"opaque_id", "question"} for task in tasks))

    def test_only_policy_and_fresh_namespace_change_from_v24831(self) -> None:
        self.assertEqual(contract.LIMITS, parent.LIMITS)
        self.assertEqual(contract.MODEL, parent.MODEL)
        self.assertEqual(contract.SEARCH, parent.SEARCH)
        self.assertEqual(contract.EXECUTOR_CONCURRENCY, parent.EXECUTOR_CONCURRENCY)
        self.assertEqual(contract.MODEL_SLOT_CAP, parent.MODEL_SLOT_CAP)
        self.assertNotEqual(contract.TWO_WAVE_POLICY, parent.TWO_WAVE_POLICY)
        self.assertNotEqual(contract.OUTPUT_ROOT, parent.OUTPUT_ROOT)

    def test_policy_exactly_matches_v24833(self) -> None:
        self.assertEqual(contract.TWO_WAVE_POLICY, controller.POLICY_VALUES)
        policy = kernel.TwoWavePolicy(**contract.TWO_WAVE_POLICY)
        policy.validate()
        self.assertEqual(dataclasses.asdict(policy), controller.POLICY_VALUES)

    def test_entropy_and_latency_credit_are_zero(self) -> None:
        self.assertEqual(contract.TWO_WAVE_POLICY["information_gain_weight"], 0.0)
        self.assertEqual(contract.TWO_WAVE_POLICY["latency_loss_per_second"], 0.0)

    def test_incomplete_usable_prefix_expands(self) -> None:
        observation = kernel.FirstWaveObservation(
            queries_executed=2, sources_discovered=6, fetches_attempted=6,
            usable_pages=5, novel_pages=5, unique_hosts=5, content_chars=20_000,
            required_column_count=4, explicit_row_target=0,
            search_seconds=10.0, fetch_seconds=10.0,
        )
        receipt = child.coverage_margin_decision(
            observation, policy=kernel.TwoWavePolicy(**contract.TWO_WAVE_POLICY)
        )
        self.assertEqual(receipt["decision"], "expand")

    def test_complete_content_rich_prefix_can_stop(self) -> None:
        observation = kernel.FirstWaveObservation(
            queries_executed=2, sources_discovered=6, fetches_attempted=6,
            usable_pages=6, novel_pages=6, unique_hosts=3, content_chars=20_000,
            required_column_count=4, explicit_row_target=0,
            search_seconds=10.0, fetch_seconds=10.0,
        )
        receipt = child.coverage_margin_decision(
            observation, policy=kernel.TwoWavePolicy(**contract.TWO_WAVE_POLICY)
        )
        self.assertEqual(receipt["decision"], "stop")
        self.assertEqual(receipt["reason"], "first_wave_sufficient")

    def test_policy_mismatch_is_rejected(self) -> None:
        observation = kernel.FirstWaveObservation(
            queries_executed=2, sources_discovered=6, fetches_attempted=6,
            usable_pages=6, novel_pages=6, unique_hosts=3, content_chars=20_000,
            required_column_count=4, explicit_row_target=0,
            search_seconds=10.0, fetch_seconds=10.0,
        )
        with self.assertRaises(RuntimeError):
            child.coverage_margin_decision(observation, policy=kernel.TwoWavePolicy())

    def test_all_four_watchers_are_protected(self) -> None:
        self.assertEqual(
            [item["pid"] for item in contract.protected_watcher_snapshot()],
            [795336, 3061652, 2808901, 2889939],
        )

    def test_child_source_has_no_evaluator_import(self) -> None:
        tree = ast.parse(contract.CHILD.read_text(encoding="utf-8"))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        self.assertFalse(any("evaluator" in name or "finalize" in name for name in imports))

    def test_fresh_surfaces_are_bound(self) -> None:
        self.assertIn("v24834", str(contract.PROTOCOL))
        self.assertIn("v24834", str(contract.OUTPUT_ROOT))
        self.assertIn("v24834", contract.RUNNER_MARKER)
        self.assertIn("v24834", contract.CHILD_MARKER)


if __name__ == "__main__":
    unittest.main()
