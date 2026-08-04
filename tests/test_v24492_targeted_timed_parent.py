from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24492_targeted_timed_parent import (  # noqa: E402
    run_targeted_parent_with_separated_budget,
    run_targeted_worker,
    supervise_targeted_worker_with_separated_budget,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24490_entropy_targeted_support_search import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24492-test-validator-manifest").hexdigest()


def writer(directory: Path):
    return lambda name, value: _new_json(directory / name, value)


def process_mode(args: argparse.Namespace) -> int:
    output_root = Path(args.output_root)
    directory = Path(args.directory)
    checkpoint = Path(args.checkpoint_directory)
    fixture = Path(args.fixture)
    if args.command == "worker":
        clock = AdvancingClock()
        model, search = clients(fixture, clock)
        run_targeted_worker(
            TASK,
            ordinal=1,
            expected_supervisor_pid=int(
                os.environ["DEEPWIDE_EXPECTED_SUPERVISOR_PID"]
            ),
            checkpoint_directory=checkpoint,
            output_root=output_root,
            directory=directory,
            model_factory=lambda _callback: model,
            search_factory=lambda _callback: search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
            expected_model_cap=2,
            writer=writer(directory),
            validator_manifest_sha256=MANIFEST,
        )
        return 0
    command = [
        str(ROOT / ".venv-eval/bin/python"),
        "-I",
        "-B",
        str(Path(__file__).resolve()),
        "worker",
        "--output-root",
        str(output_root),
        "--directory",
        str(directory),
        "--checkpoint-directory",
        str(checkpoint),
        "--fixture",
        str(fixture),
    ]
    supervise_targeted_worker_with_separated_budget(
        ordinal=1,
        cwd=ROOT,
        output_root=output_root,
        directory=directory,
        checkpoint_directory=checkpoint,
        worker_command=command,
        deadline_origin=args.deadline_origin_monotonic,
        expected_model_cap=2,
        writer=writer(directory),
    )
    return 0


class V24492TargetedTimedParentTests(unittest.TestCase):
    def test_real_parent_supervisor_worker_chain_uses_targeted_capability(self) -> None:
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
                "--output-root",
                str(output_root),
                "--directory",
                str(directory),
                "--checkpoint-directory",
                str(checkpoint),
                "--fixture",
                str(fixture),
            ]
            started = time.monotonic()
            outcome = run_targeted_parent_with_separated_budget(
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
        self.assertLess(elapsed, 70)
        self.assertEqual(
            outcome.proof.parent_receipt["failure_taxonomy"], "success"
        )
        self.assertTrue(outcome.proof.adaptive_projection["passed"])
        self.assertEqual(
            outcome.proof.adaptive_projection[
                "safe_change_count_after_targeted_search"
            ],
            1,
        )
        self.assertEqual(
            outcome.proof.timing_receipt["certificate_validation_invocations"],
            1,
        )
        self.assertFalse(
            outcome.proof.timing_receipt[
                "parent_recursive_historical_semantic_replay_performed"
            ]
        )
        self.assertEqual(outcome.supervision_receipt["last_stage"], "worker_complete")
        self.assertTrue(outcome.supervision_receipt["complete_validation_returned"])

    def test_parent_and_supervisor_share_one_origin_and_separate_cutoffs(self) -> None:
        captured_parent: dict = {}
        captured_supervisor: dict = {}
        with patch(
            "deepwide_agent.v24492_targeted_timed_parent.run_targeted_timed_subprocess",
            side_effect=lambda **kwargs: captured_parent.update(kwargs)
            or type("Proof", (), {"parent_receipt": {"failure_taxonomy": "success"}})(),
        ), patch(
            "deepwide_agent.v24492_targeted_timed_parent._read_supervision_receipt",
            return_value={
                "worker_hard_timeout": False,
                "return_code": 0,
                "last_stage": "worker_complete",
            },
        ):
            run_targeted_parent_with_separated_budget(
                ordinal=1,
                cwd=ROOT,
                output_root=ROOT / "outputs",
                directory=ROOT / "outputs" / "task",
                checkpoint_directory=ROOT / "outputs" / "checkpoint",
                supervisor_command=["python", "runner", "supervisor"],
                expected_model_cap=2,
                expected_validator_manifest_sha256="a" * 64,
                monotonic=iter((1000.0, 1000.25)).__next__,
            )
        self.assertEqual(captured_parent["timeout_seconds"], 244.75)
        self.assertEqual(captured_parent["command"][-2:], [
            "--deadline-origin-monotonic", "1000.0"
        ])

        with patch(
            "deepwide_agent.v24492_targeted_timed_parent.supervise_and_publish",
            side_effect=lambda **kwargs: captured_supervisor.update(kwargs) or {},
        ):
            supervise_targeted_worker_with_separated_budget(
                ordinal=1,
                cwd=ROOT,
                output_root=ROOT / "outputs",
                directory=ROOT / "outputs" / "task",
                checkpoint_directory=ROOT / "outputs" / "checkpoint",
                worker_command=["python", "runner", "worker"],
                deadline_origin="1000.0",
                expected_model_cap=2,
                writer=lambda _name, _value: None,
                monotonic=lambda: 1000.5,
            )
        self.assertEqual(captured_supervisor["timeout_seconds"], 219.5)
        self.assertEqual(captured_supervisor["command"][-2:], [
            "--deadline-origin-monotonic", "1000.0"
        ])

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24492_targeted_timed_parent.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] in {"worker", "supervisor"}:
        parser = argparse.ArgumentParser()
        parser.add_argument("command")
        parser.add_argument("--output-root", required=True)
        parser.add_argument("--directory", required=True)
        parser.add_argument("--checkpoint-directory", required=True)
        parser.add_argument("--fixture", required=True)
        parser.add_argument("--deadline-origin-monotonic")
        raise SystemExit(process_mode(parser.parse_args()))
    unittest.main()


if __name__ == "__main__":
    main()
