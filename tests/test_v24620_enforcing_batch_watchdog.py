from __future__ import annotations

import signal
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24620_enforcing_batch_watchdog as target  # noqa: E402


class V24620EnforcingBatchWatchdogTests(unittest.TestCase):
    def test_quiet_completion_cancels_without_signal(self) -> None:
        calls: list[tuple[tuple[int, ...], int]] = []
        watchdog = target.EnforcingBatchWatchdog(
            runner_marker="scripts/fresh_runner.py",
            timeout_seconds=1.0,
            grace_seconds=0.0,
            snapshot=lambda: (101,),
            signal_groups=lambda groups, sig: (
                calls.append((tuple(groups), sig)) or (len(groups), 0)
            ),
        ).start()
        watchdog.close()
        receipt = watchdog.content_free_receipt()
        self.assertFalse(receipt["triggered"])
        self.assertEqual(calls, [])

    def test_expiry_sends_term_then_kill(self) -> None:
        calls: list[tuple[tuple[int, ...], int]] = []
        snapshots = iter(((101, 102), (102,)))

        def send(groups, sig):
            calls.append((tuple(groups), sig))
            return len(groups), 0

        watchdog = target.EnforcingBatchWatchdog(
            runner_marker="scripts/fresh_runner.py",
            timeout_seconds=0.02,
            grace_seconds=0.0,
            snapshot=lambda: next(snapshots),
            signal_groups=send,
        ).start()
        time.sleep(0.05)
        watchdog.close()
        receipt = watchdog.content_free_receipt()
        self.assertTrue(receipt["triggered"])
        self.assertEqual(
            calls,
            [((101, 102), signal.SIGTERM), ((101, 102), signal.SIGKILL)],
        )
        self.assertEqual(receipt["term_signal_count"], 2)
        self.assertEqual(receipt["kill_signal_count"], 2)

    def test_reparented_initial_group_remains_in_kill_set(self) -> None:
        calls: list[tuple[tuple[int, ...], int]] = []
        snapshots = iter(((101, 102), ()))

        def send(groups, sig):
            calls.append((tuple(groups), sig))
            return len(groups), 0

        watchdog = target.EnforcingBatchWatchdog(
            runner_marker="scripts/fresh_runner.py",
            timeout_seconds=0.01,
            grace_seconds=0.0,
            snapshot=lambda: next(snapshots),
            signal_groups=send,
        ).start()
        time.sleep(0.03)
        watchdog.close()
        self.assertEqual(
            calls,
            [((101, 102), signal.SIGTERM), ((101, 102), signal.SIGKILL)],
        )

    def test_receipt_is_fixed_vocabulary_and_content_free(self) -> None:
        watchdog = target.EnforcingBatchWatchdog(
            runner_marker="scripts/fresh_runner.py",
            timeout_seconds=1.0,
            grace_seconds=0.0,
            snapshot=tuple,
        ).start()
        watchdog.close()
        receipt = watchdog.content_free_receipt()
        encoded = repr(receipt)
        self.assertNotIn("fresh_runner", encoded)
        self.assertFalse(receipt["process_identifier_or_command_line_emitted"])
        self.assertFalse(
            receipt["task_question_query_url_title_page_prediction_or_value_opened"]
        )
        self.assertFalse(
            receipt[
                "mapping_gold_category_question_type_split_evaluator_score_or_reward_read"
            ]
        )

    def test_lifecycle_fails_closed(self) -> None:
        watchdog = target.EnforcingBatchWatchdog(
            runner_marker="runner.py", timeout_seconds=1.0, grace_seconds=0.0
        )
        with self.assertRaises(RuntimeError):
            watchdog.close()
        watchdog.start()
        with self.assertRaises(RuntimeError):
            watchdog.start()
        watchdog.close()
        with self.assertRaises(RuntimeError):
            watchdog.close()

    def test_invalid_budget_or_identity_fails_closed(self) -> None:
        for timeout in (0, -1, True, 601):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    target.EnforcingBatchWatchdog(
                        runner_marker="runner.py", timeout_seconds=timeout
                    )
        with self.assertRaises(ValueError):
            target.descendant_runner_process_groups(0, "runner.py")
        with self.assertRaises(ValueError):
            target.descendant_runner_process_groups(1, "")

    def test_proc_scan_selects_only_marked_descendant_runtime_groups(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as directory:
            proc = Path(directory)

            def record(pid: int, ppid: int, group: int, command: bytes) -> None:
                path = proc / str(pid)
                path.mkdir()
                (path / "stat").write_text(
                    f"{pid} (process name) S {ppid} {group} {group} 0 0\n",
                    encoding="utf-8",
                )
                (path / "cmdline").write_bytes(command)

            record(100, 1, 100, b"python\x00runner.py\x00run")
            record(
                101,
                100,
                101,
                b"python\x00scripts/fresh_runner.py\x00supervisor\x00",
            )
            record(
                102,
                101,
                102,
                b"python\x00scripts/fresh_runner.py\x00worker\x00",
            )
            record(103, 100, 103, b"python\x00unrelated.py\x00worker\x00")
            record(104, 999, 104, b"python\x00scripts/fresh_runner.py\x00worker\x00")
            groups = target.descendant_runner_process_groups(
                100, "scripts/fresh_runner.py", proc_root=proc
            )
        self.assertEqual(groups, (101, 102))

    def test_signal_failure_is_counted_without_details(self) -> None:
        def fail(_groups, _sig):
            raise PermissionError("synthetic")

        watchdog = target.EnforcingBatchWatchdog(
            runner_marker="runner.py",
            timeout_seconds=0.01,
            grace_seconds=0.0,
            snapshot=lambda: (101,),
            signal_groups=fail,
        ).start()
        time.sleep(0.03)
        watchdog.close()
        receipt = watchdog.content_free_receipt()
        self.assertTrue(receipt["triggered"])
        self.assertEqual(receipt["signal_failure_count"], 2)

    def test_runtime_source_is_label_blind_and_secret_free(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        path = Path("src/deepwide_agent/v24620_enforcing_batch_watchdog.py")
        accesses, imports = audit.ast_findings(path)
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        self.assertIsNone(audit.SECRET.search((ROOT / path).read_text(encoding="utf-8")))


if __name__ == "__main__":
    unittest.main()
