from __future__ import annotations

import argparse
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import (  # noqa: E402
    v24482_separated_budget_worker_integration as target,
)
from test_v24470_bounded_adaptive_integration import (  # noqa: E402
    MANIFEST,
    run_worker_mode as run_frozen_worker_mode,
    writer,
)


class SequenceClock:
    def __init__(self, *values: float) -> None:
        self.values = iter(values)

    def __call__(self) -> float:
        return next(self.values)


class V24482SeparatedBudgetWorkerIntegrationTests(unittest.TestCase):
    def test_deadline_origin_roundtrip_and_remote_cap(self) -> None:
        deadlines = target.deadlines_from_origin("1000.0")
        self.assertEqual(deadlines.remote_effect, 1150.0)
        self.assertEqual(deadlines.worker, 1220.0)
        self.assertEqual(deadlines.parent, 1245.0)
        self.assertEqual(
            target.remote_effect_deadline("1000.0", monotonic=lambda: 1100.0),
            1150.0,
        )
        with self.assertRaisesRegex(RuntimeError, "remote-effect deadline"):
            target.remote_effect_deadline(
                "1000.0", monotonic=lambda: 1150.0
            )

    def test_parent_uses_245_second_cutoff_and_passes_one_origin(self) -> None:
        captured: dict = {}
        expected = SimpleNamespace(proof="proof", supervision_receipt={})
        with patch.object(
            target,
            "run_bounded_parent_subprocess",
            side_effect=lambda **kwargs: captured.update(kwargs) or expected,
        ):
            observed = target.run_parent_with_separated_budget(
                ordinal=1,
                cwd=ROOT,
                output_root=ROOT / "outputs",
                directory=ROOT / "outputs" / "task",
                checkpoint_directory=ROOT / "outputs" / "checkpoint",
                supervisor_command=["python", "runner.py", "supervisor"],
                expected_model_cap=2,
                expected_validator_manifest_sha256="a" * 64,
                monotonic=SequenceClock(1000.0, 1000.25),
            )
        self.assertIs(observed, expected)
        self.assertEqual(captured["parent_timeout_seconds"], 244.75)
        self.assertEqual(
            captured["command"][-2:],
            [target.DEADLINE_ORIGIN_ARGUMENT, "1000.0"],
        )
        self.assertEqual(captured["expected_model_cap"], 2)

    def test_supervisor_uses_220_second_cutoff_and_same_origin(self) -> None:
        captured: dict = {}
        expected = SimpleNamespace(worker_hard_timeout=False)
        with patch.object(
            target,
            "supervise_and_publish",
            side_effect=lambda **kwargs: captured.update(kwargs) or expected,
        ):
            observed = target.supervise_worker_with_separated_budget(
                ordinal=1,
                cwd=ROOT,
                output_root=ROOT / "outputs",
                directory=ROOT / "outputs" / "task",
                checkpoint_directory=ROOT / "outputs" / "checkpoint",
                worker_command=["python", "runner.py", "worker"],
                deadline_origin="1000.0",
                expected_model_cap=2,
                writer=lambda _name, _value: None,
                monotonic=lambda: 1000.5,
            )
        self.assertIs(observed, expected)
        self.assertEqual(captured["timeout_seconds"], 219.5)
        self.assertEqual(
            captured["command"][-2:],
            [target.DEADLINE_ORIGIN_ARGUMENT, "1000.0"],
        )

    def test_real_parent_supervisor_worker_chain_preserves_one_origin(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output_root = Path(temporary)
            directory = output_root / "task"
            checkpoint = output_root / "checkpoint"
            fixture = output_root / "fixture"
            directory.mkdir()
            checkpoint.mkdir()
            fixture.mkdir()
            command = [
                str(ROOT / ".venv-eval/bin/python"),
                "-I",
                "-B",
                str(Path(__file__).resolve()),
                "supervisor",
                "--behavior",
                "success",
                "--stage",
                "complete_validation_entered",
                "--directory",
                str(directory),
                "--checkpoint-directory",
                str(checkpoint),
                "--output-root",
                str(output_root),
                "--fixture",
                str(fixture),
            ]
            started = time.monotonic()
            outcome = target.run_parent_with_separated_budget(
                ordinal=1,
                cwd=ROOT,
                output_root=output_root,
                directory=directory,
                checkpoint_directory=checkpoint,
                supervisor_command=command,
                expected_model_cap=2,
                expected_validator_manifest_sha256=MANIFEST,
            )
            elapsed = time.monotonic() - started
        self.assertLess(elapsed, 70.0)
        self.assertEqual(
            outcome.proof.parent_receipt["failure_taxonomy"], "success"
        )
        self.assertTrue(outcome.proof.adaptive_projection["passed"])
        self.assertFalse(outcome.supervision_receipt["worker_hard_timeout"])
        self.assertEqual(outcome.supervision_receipt["return_code"], 0)
        self.assertEqual(outcome.supervision_receipt["last_stage"], "worker_complete")
        self.assertTrue(
            outcome.supervision_receipt["complete_validation_returned"]
        )

    def test_expired_worker_retains_only_minimal_cleanup_window(self) -> None:
        captured: dict = {}
        with patch.object(
            target,
            "supervise_and_publish",
            side_effect=lambda **kwargs: captured.update(kwargs),
        ):
            target.supervise_worker_with_separated_budget(
                ordinal=1,
                cwd=ROOT,
                output_root=ROOT / "outputs",
                directory=ROOT / "outputs" / "task",
                checkpoint_directory=ROOT / "outputs" / "checkpoint",
                worker_command=["python", "runner.py", "worker"],
                deadline_origin=1000.0,
                expected_model_cap=2,
                writer=lambda _name, _value: None,
                monotonic=lambda: 1221.0,
            )
        self.assertEqual(captured["timeout_seconds"], 1e-6)

    def test_command_and_contract_fail_closed(self) -> None:
        deadlines = target.deadlines_from_origin(1000.0)
        for command in (
            [],
            ["python", ""],
            ["python", target.DEADLINE_ORIGIN_ARGUMENT, "999.0"],
        ):
            with self.subTest(command=command):
                with self.assertRaises(ValueError):
                    target.append_deadline_origin(command, deadlines)
        contract = target.integration_contract()
        self.assertEqual(contract["remote_effect_seconds"], 150.0)
        self.assertEqual(contract["worker_total_seconds"], 220.0)
        self.assertEqual(contract["parent_total_seconds"], 245.0)
        self.assertTrue(contract["remote_clients_receive_only_remote_effect_deadline"])
        self.assertFalse(contract["benchmark_launch_or_evaluator_authorized"])

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path(
                "src/deepwide_agent/v24482_separated_budget_worker_integration.py"
            )
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


def run_process_mode(args: argparse.Namespace) -> int:
    if args.command == "worker":
        return run_frozen_worker_mode(args)
    directory = Path(args.directory)
    checkpoint = Path(args.checkpoint_directory)
    worker_command = [
        str(ROOT / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(Path(__file__).resolve()),
        "worker",
        "--behavior",
        args.behavior,
        "--stage",
        args.stage,
        "--directory",
        str(directory),
        "--checkpoint-directory",
        str(checkpoint),
        "--output-root",
        args.output_root,
        "--fixture",
        args.fixture,
    ]
    target.supervise_worker_with_separated_budget(
        ordinal=1,
        cwd=ROOT,
        output_root=Path(args.output_root),
        directory=directory,
        checkpoint_directory=checkpoint,
        worker_command=worker_command,
        deadline_origin=args.deadline_origin_monotonic,
        expected_model_cap=2,
        writer=writer(directory),
    )
    return 0


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in {"worker", "supervisor"}:
        parser = argparse.ArgumentParser()
        parser.add_argument("command")
        parser.add_argument("--behavior", required=True)
        parser.add_argument("--stage", required=True)
        parser.add_argument("--directory", required=True)
        parser.add_argument("--checkpoint-directory", required=True)
        parser.add_argument("--output-root", required=True)
        parser.add_argument("--fixture", required=True)
        parser.add_argument(target.DEADLINE_ORIGIN_ARGUMENT, required=True)
        args = parser.parse_args()
        raise SystemExit(run_process_mode(args))
    unittest.main()


if __name__ == "__main__":
    main()
