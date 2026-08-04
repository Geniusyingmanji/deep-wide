from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    child_receipt,
    payload_sha256,
    validate_child_receipt,
)
from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24397_failure_observability import (  # noqa: E402
    validate_failure_snapshot,
)
from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    FAILURE_NAME,
)
from deepwide_agent.v24469_bounded_worker_supervisor import (  # noqa: E402
    STAGES,
    WORKER_RECEIPT_NAME,
    StageJournal,
    bind_worker_to_parent,
    build_checkpoint,
    read_checkpoints,
    supervise_worker,
    validate_checkpoint,
    validate_worker_receipt,
)


def worker(args: argparse.Namespace) -> int:
    parent = int(os.environ["DEEPWIDE_EXPECTED_SUPERVISOR_PID"])
    bind_worker_to_parent(expected_parent_pid=parent)
    directory = Path(args.directory)
    checkpoint = Path(args.checkpoint_directory)
    journal = StageJournal(checkpoint, ordinal=1)
    journal.record("worker_entered")
    if args.behavior == "timeout":
        if args.stage.endswith("_effect_started"):
            journal.record(args.stage)
        else:
            journal.record(args.stage)
        time.sleep(10)
        return 7
    if args.behavior == "timeout_grandchild":
        child = subprocess.Popen(
            ["/bin/sleep", "10"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        (directory / "grandchild_pid.txt").write_text(str(child.pid))
        journal.record(args.stage)
        time.sleep(10)
        return 7
    if args.behavior == "nonzero":
        journal.record(args.stage)
        _new_json(
            directory / FAILURE_NAME,
            {
                "synthetic": True,
            },
        )
        _new_json(
            directory / "child_terminal_receipt.json",
            child_receipt(
                stage="child_exception",
                exception_type="RuntimeError",
                model_receipt_written=False,
                transport_receipt_written=False,
                result_envelope_written=False,
            ),
        )
        return 9
    _new_json(
        directory / "child_terminal_receipt.json",
        child_receipt(
            stage="runtime_returned",
            exception_type=None,
            model_receipt_written=False,
            transport_receipt_written=False,
            result_envelope_written=False,
        ),
    )
    journal.record("worker_complete")
    return 0


class V24469BoundedWorkerSupervisorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.directory = self.base / "task"
        self.checkpoint = self.base / "checkpoint"
        self.directory.mkdir()
        self.checkpoint.mkdir()

    def command(self, behavior: str, stage: str = "complete_validation_entered") -> list[str]:
        return [
            str(ROOT / ".venv-eval/bin/python"),
            "-I",
            "-B",
            str(Path(__file__).resolve()),
            "worker",
            "--behavior",
            behavior,
            "--stage",
            stage,
            "--directory",
            str(self.directory),
            "--checkpoint-directory",
            str(self.checkpoint),
        ]

    def writer(self, name, value) -> None:
        _new_json(self.directory / name, value)

    def test_append_only_chain_is_thread_safe_and_tamper_evident(self) -> None:
        journal = StageJournal(self.checkpoint, ordinal=1)
        threads = [
            threading.Thread(target=journal.record, args=(stage,))
            for stage in STAGES[:8]
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=2)
        values = read_checkpoints(self.checkpoint, ordinal=1)
        self.assertEqual(len(values), 8)
        self.assertEqual([value["sequence"] for value in values], list(range(1, 9)))
        for previous, current in zip(values, values[1:]):
            self.assertEqual(
                current["previous_checkpoint_sha256"],
                previous["checkpoint_payload_sha256"],
            )
        path = sorted(self.checkpoint.iterdir())[3]
        altered = json.loads(path.read_text())
        altered["stage"] = "worker_complete"
        altered["checkpoint_payload_sha256"] = payload_sha256(
            {k: v for k, v in altered.items() if k != "checkpoint_payload_sha256"}
        )
        path.write_text(json.dumps(altered))
        with self.assertRaisesRegex(RuntimeError, "chain drifted"):
            read_checkpoints(self.checkpoint, ordinal=1)

    def test_checkpoint_rejects_resealed_private_field(self) -> None:
        value = build_checkpoint(
            ordinal=1,
            sequence=1,
            stage="worker_entered",
            previous_checkpoint_sha256=None,
        )
        altered = copy.deepcopy(value)
        altered["question"] = "forbidden"
        altered.pop("checkpoint_payload_sha256")
        altered["checkpoint_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_checkpoint(altered)

    def test_success_preserves_task_surface_and_cleans_checkpoint(self) -> None:
        value = supervise_worker(
            ordinal=1,
            cwd=ROOT,
            directory=self.directory,
            checkpoint_directory=self.checkpoint,
            command=self.command("success"),
            timeout_seconds=2,
            expected_model_cap=2,
            writer=self.writer,
        )
        self.assertFalse(value["worker_hard_timeout"])
        self.assertEqual(value["last_stage"], "worker_complete")
        self.assertEqual(value["return_code"], 0)
        self.assertEqual(list(self.checkpoint.iterdir()), [])
        self.assertEqual(
            {path.name for path in self.directory.iterdir()},
            {"child_terminal_receipt.json"},
        )
        validate_child_receipt(
            json.loads((self.directory / "child_terminal_receipt.json").read_text())
        )

    def test_hard_timeout_closes_inside_reserve_with_last_stage(self) -> None:
        started = time.monotonic()
        value = supervise_worker(
            ordinal=1,
            cwd=ROOT,
            directory=self.directory,
            checkpoint_directory=self.checkpoint,
            command=self.command("timeout", "complete_validation_entered"),
            timeout_seconds=0.25,
            expected_model_cap=2,
            writer=self.writer,
        )
        elapsed = time.monotonic() - started
        self.assertLess(elapsed, 0.8)
        self.assertTrue(value["worker_hard_timeout"])
        self.assertEqual(value["last_stage"], "complete_validation_entered")
        self.assertTrue(value["failure_snapshot_written"])
        self.assertEqual(list(self.checkpoint.iterdir()), [])
        receipt = validate_worker_receipt(
            json.loads((self.directory / WORKER_RECEIPT_NAME).read_text())
        )
        self.assertTrue(receipt["worker_hard_timeout"])
        terminal = validate_child_receipt(
            json.loads((self.directory / "child_terminal_receipt.json").read_text())
        )
        self.assertEqual(terminal["exception_type"], "TimeoutError")
        validate_failure_snapshot(
            json.loads((self.directory / FAILURE_NAME).read_text()),
            model_receipt=None,
            transport_health=None,
            search_receipt=None,
            expected_model_cap=2,
        )

    def test_effect_timeout_preserves_started_without_finished_lower_bound(self) -> None:
        value = supervise_worker(
            ordinal=1,
            cwd=ROOT,
            directory=self.directory,
            checkpoint_directory=self.checkpoint,
            command=self.command("timeout", "model_effect_started"),
            timeout_seconds=0.25,
            expected_model_cap=2,
            writer=self.writer,
        )
        self.assertEqual(value["last_stage"], "model_effect_started")
        self.assertEqual(value["model_effect_started_lower_bound"], 1)
        self.assertEqual(value["model_effect_finished_lower_bound"], 0)
        self.assertEqual(value["hosted_search_effect_started_lower_bound"], 0)
        self.assertFalse(value["complete_validation_entered"])
        self.assertFalse(value["complete_validation_returned"])

    def test_validation_timeout_is_distinct_from_effect_timeout(self) -> None:
        value = supervise_worker(
            ordinal=1,
            cwd=ROOT,
            directory=self.directory,
            checkpoint_directory=self.checkpoint,
            command=self.command("timeout", "complete_validation_entered"),
            timeout_seconds=0.25,
            expected_model_cap=2,
            writer=self.writer,
        )
        self.assertTrue(value["complete_validation_entered"])
        self.assertFalse(value["complete_validation_returned"])
        self.assertEqual(value["model_effect_started_lower_bound"], 0)

    def test_corrupt_checkpoint_still_closes_with_unknown_stage(self) -> None:
        class CorruptingProcess:
            pid = 99_999_999
            returncode = None

            def wait(inner, timeout=None):
                del timeout
                path = self.checkpoint / "content_free_stage_000001.json"
                path.write_text("{not-json")
                raise subprocess.TimeoutExpired("worker", 0.1)

        process = CorruptingProcess()
        with mock.patch("os.killpg", side_effect=ProcessLookupError):
            value = supervise_worker(
                ordinal=1,
                cwd=ROOT,
                directory=self.directory,
                checkpoint_directory=self.checkpoint,
                command=["synthetic"],
                timeout_seconds=0.2,
                expected_model_cap=2,
                writer=self.writer,
                popen=lambda *_args, **_kwargs: process,
            )
        self.assertTrue(value["worker_hard_timeout"])
        self.assertFalse(value["checkpoint_chain_valid"])
        self.assertIsNone(value["last_stage"])
        self.assertEqual(value["last_stage_sequence"], 0)
        self.assertTrue((self.directory / "child_terminal_receipt.json").is_file())

    def test_worker_receipt_rejects_resealed_lower_bound_tamper(self) -> None:
        value = supervise_worker(
            ordinal=1,
            cwd=ROOT,
            directory=self.directory,
            checkpoint_directory=self.checkpoint,
            command=self.command("timeout", "model_effect_started"),
            timeout_seconds=0.25,
            expected_model_cap=2,
            writer=self.writer,
        )
        altered = copy.deepcopy(value)
        altered["model_effect_finished_lower_bound"] = 2
        altered.pop("receipt_payload_sha256")
        altered["receipt_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_worker_receipt(altered)

    def test_worker_process_group_kills_grandchild(self) -> None:
        supervise_worker(
            ordinal=1,
            cwd=ROOT,
            directory=self.directory,
            checkpoint_directory=self.checkpoint,
            command=self.command("timeout_grandchild", "model_effect_started"),
            timeout_seconds=0.35,
            expected_model_cap=2,
            writer=self.writer,
        )
        pid = int((self.directory / "grandchild_pid.txt").read_text())
        for _ in range(20):
            if not Path(f"/proc/{pid}").exists():
                break
            time.sleep(0.02)
        state = None
        stat = Path(f"/proc/{pid}/stat")
        if stat.exists():
            state = stat.read_text().split()[2]
        self.assertIn(state, (None, "Z"))

    def test_nonzero_worker_is_observable_and_not_reclassified_success(self) -> None:
        value = supervise_worker(
            ordinal=1,
            cwd=ROOT,
            directory=self.directory,
            checkpoint_directory=self.checkpoint,
            command=self.command("nonzero", "runtime_entered"),
            timeout_seconds=2,
            expected_model_cap=2,
            writer=self.writer,
        )
        self.assertFalse(value["worker_hard_timeout"])
        self.assertEqual(value["return_code"], 9)
        self.assertEqual(value["last_stage"], "runtime_entered")
        self.assertTrue((self.directory / WORKER_RECEIPT_NAME).is_file())
        self.assertTrue((self.directory / "child_terminal_receipt.json").is_file())

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24465_single_validation_adaptive_build as audit

        accesses, imports = audit.base._ast_findings(
            Path("src/deepwide_agent/v24469_bounded_worker_supervisor.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "worker":
        parser = argparse.ArgumentParser()
        parser.add_argument("command")
        parser.add_argument("--behavior", required=True)
        parser.add_argument("--stage", required=True)
        parser.add_argument("--directory", required=True)
        parser.add_argument("--checkpoint-directory", required=True)
        raise SystemExit(worker(parser.parse_args()))
    unittest.main()


if __name__ == "__main__":
    main()
