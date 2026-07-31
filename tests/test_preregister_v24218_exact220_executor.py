from __future__ import annotations

import unittest
from pathlib import Path
from unittest import mock

from scripts import preregister_v24218_exact220_executor as prereg


ROOT = Path(__file__).resolve().parents[1]


class PreregisterV24218Exact220ExecutorTests(unittest.TestCase):
    def test_live_protocol_is_label_blind_and_future_paths_are_absent(self) -> None:
        value = prereg.build_protocol(ROOT, created_at_unix=1, require_pristine=True)
        self.assertTrue(value["label_blind"])
        self.assertEqual(value["candidate_contract"]["runtime_boundary"], ["opaque_id", "question"])
        self.assertFalse(
            value["source_policy"][
                "benchmark_category_question_type_split_mapping_gold_answer_evaluator_score_route"
            ]
        )
        self.assertTrue(
            value["safe_wait_boundary"][
                "all_future_protocol_state_activation_execution_and_run_paths_absent"
            ]
        )
        self.assertFalse(value["authorization"]["leaderboard_submission_or_sota_claim"])

    def test_future_side_effect_breaks_pristine_freeze(self) -> None:
        with mock.patch.object(prereg, "_present", return_value=True):
            with self.assertRaisesRegex(RuntimeError, "not pristine"):
                prereg.build_protocol(ROOT, created_at_unix=1, require_pristine=True)

    def test_control_surface_includes_runner_watcher_and_tests(self) -> None:
        required = {
            "src/deepwide_agent/v24218_exact220_executor.py",
            "scripts/run_v24218_exact220_executor.py",
            "scripts/watch_v24218_exact220_executor.py",
            "tests/test_v24218_exact220_executor.py",
        }
        self.assertTrue(required.issubset(set(prereg.CONTROL_FILES)))


if __name__ == "__main__":
    unittest.main()
