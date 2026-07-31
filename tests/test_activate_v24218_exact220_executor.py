from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import activate_v24218_exact220_executor as activate


VERIFIED = {"sha256": "p" * 64, "value": {}}
PROCESS = {
    "pid": 77,
    "argv": [
        "python",
        "-I",
        "-B",
        "/repo/scripts/watch_v24218_exact220_executor.py",
    ],
}


class ActivateV24218Exact220ExecutorTests(unittest.TestCase):
    def test_activation_binds_one_isolated_watcher(self) -> None:
        with mock.patch.object(activate, "validate_protocol", return_value=VERIFIED), mock.patch.object(
            activate, "process_snapshot", return_value=[PROCESS]
        ), mock.patch.object(activate, "_start_ticks", return_value=123):
            value = activate.build_activation(created_at_unix=1)
        self.assertEqual(value["watcher"]["pid"], 77)
        self.assertTrue(value["all_four_shards_terminal_before_mapping_or_evaluator"])
        self.assertFalse(
            value[
                "benchmark_category_question_type_split_mapping_gold_answer_evaluator_score_used_for_forward_routing"
            ]
        )

    def test_nonisolated_or_duplicate_watcher_is_rejected(self) -> None:
        bad = {**PROCESS, "argv": ["python", "scripts/watch_v24218_exact220_executor.py"]}
        with self.assertRaisesRegex(RuntimeError, "identity"):
            activate._watcher([bad])
        with self.assertRaisesRegex(RuntimeError, "identity"):
            activate._watcher([PROCESS, PROCESS])


if __name__ == "__main__":
    unittest.main()
