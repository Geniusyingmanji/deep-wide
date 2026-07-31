from __future__ import annotations

import unittest
from unittest import mock

from scripts import activate_v24219_search_time_contamination as activate


PROCESS = {
    "pid": 77,
    "argv": [
        "python",
        "-I",
        "-B",
        "/repo/scripts/watch_v24219_search_time_contamination.py",
    ],
}


class ActivateV24219SearchTimeContaminationTests(unittest.TestCase):
    def test_activation_binds_one_isolated_watcher(self) -> None:
        with mock.patch.object(
            activate, "validate_protocol", return_value={"sha256": "p" * 64}
        ), mock.patch.object(activate, "process_snapshot", return_value=[PROCESS]), mock.patch.object(
            activate, "_start_ticks", return_value=123
        ), mock.patch.object(activate.Path, "exists", return_value=False), mock.patch.object(
            activate.Path, "is_symlink", return_value=False
        ):
            value = activate.build_activation(created_at_unix=1)
        self.assertEqual(value["watcher"]["pid"], 77)
        self.assertTrue(value["post_terminal_label_blind_offline_audit_only"])
        self.assertFalse(value["network_model_search_fetch_evaluator_or_api_called"])

    def test_duplicate_or_nonisolated_watcher_is_rejected(self) -> None:
        bad = {
            **PROCESS,
            "argv": ["python", "scripts/watch_v24219_search_time_contamination.py"],
        }
        with self.assertRaisesRegex(RuntimeError, "identity"):
            activate._watcher([bad])
        with self.assertRaisesRegex(RuntimeError, "identity"):
            activate._watcher([PROCESS, PROCESS])


if __name__ == "__main__":
    unittest.main()
