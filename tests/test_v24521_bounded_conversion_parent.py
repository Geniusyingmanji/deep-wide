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
from deepwide_agent.v24521_bounded_conversion_parent import (  # noqa: E402
    run_conversion_parent_with_separated_budget,
    run_conversion_timed_subprocess,
    run_conversion_worker,
    supervise_conversion_worker_with_separated_budget,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24516_neutral_discovery_record_bound_worker import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24521-test-validator-manifest").hexdigest()


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
        run_conversion_worker(
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
    supervise_conversion_worker_with_separated_budget(
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


class V24521BoundedConversionParentTests(unittest.TestCase):
    def test_real_parent_supervisor_worker_chain_projects_conversion_counts(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output_root = Path(temporary)
            directory = output_root / "task"
            checkpoint = output_root / "checkpoint"
            fixture = output_root / "fixture"
            directory.mkdir(); checkpoint.mkdir(); fixture.mkdir()
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
            outcome = run_conversion_parent_with_separated_budget(
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
        self.assertEqual(outcome.proof.parent_receipt["failure_taxonomy"], "success")
        projection = outcome.proof.adaptive_projection
        self.assertEqual(projection["status"], "validated_capability")
        self.assertGreater(projection["conversion_page_target_pair_count"], 0)
        self.assertEqual(
            sum(projection["conversion_reason_counts"].values()),
            projection["conversion_page_target_pair_count"],
        )
        self.assertEqual(outcome.supervision_receipt["last_stage"], "worker_complete")
        self.assertEqual(
            outcome.proof.timing_receipt["certificate_validation_invocations"], 1
        )
        self.assertFalse(
            outcome.proof.timing_receipt[
                "parent_recursive_historical_semantic_replay_performed"
            ]
        )

    def test_parent_and_supervisor_keep_one_origin_and_separate_cutoffs(self) -> None:
        captured_parent: dict = {}
        captured_supervisor: dict = {}
        fake_proof = type(
            "Proof",
            (),
            {"parent_receipt": {"failure_taxonomy": "success"}},
        )()
        with (
            patch(
                "deepwide_agent.v24521_bounded_conversion_parent.run_conversion_timed_subprocess",
                side_effect=lambda **kwargs: captured_parent.update(kwargs)
                or fake_proof,
            ),
            patch(
                "deepwide_agent.v24521_bounded_conversion_parent._read_supervision_receipt",
                return_value={
                    "worker_hard_timeout": False,
                    "return_code": 0,
                    "last_stage": "worker_complete",
                },
            ),
        ):
            run_conversion_parent_with_separated_budget(
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
        self.assertEqual(
            captured_parent["command"][-2:],
            ["--deadline-origin-monotonic", "1000.0"],
        )
        with patch(
            "deepwide_agent.v24521_bounded_conversion_parent.supervise_and_publish",
            side_effect=lambda **kwargs: captured_supervisor.update(kwargs) or {},
        ):
            supervise_conversion_worker_with_separated_budget(
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

    def test_worker_rejects_privileged_input_before_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output_root = Path(temporary)
            directory = output_root / "task"
            checkpoint = output_root / "checkpoint"
            fixture = output_root / "fixture"
            directory.mkdir(); checkpoint.mkdir(); fixture.mkdir()
            clock = AdvancingClock()
            model, search = clients(fixture, clock)
            with (
                patch(
                    "deepwide_agent.v24469_bounded_worker_supervisor.bind_worker_to_parent",
                ),
                self.assertRaises(ValueError),
            ):
                run_conversion_worker(
                    {**TASK, "category": "forbidden"},
                    ordinal=1,
                    expected_supervisor_pid=os.getpid(),
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
        self.assertEqual(model.acquisitions, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)

    def test_nonzero_child_uses_failure_zero_and_lower_bound_observation(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output_root = Path(temporary)
            directory = output_root / "task"
            directory.mkdir()
            outcome = run_conversion_timed_subprocess(
                ordinal=1,
                cwd=ROOT,
                output_root=output_root,
                directory=directory,
                command=[
                    str(ROOT / ".venv-eval/bin/python"),
                    "-I",
                    "-B",
                    "-c",
                    "raise SystemExit(7)",
                ],
                environment={
                    "HOME": os.environ.get("HOME", str(Path.home())),
                    "USER": os.environ.get("USER", "azureuser"),
                    "LOGNAME": os.environ.get("LOGNAME", "azureuser"),
                    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                },
                timeout_seconds=20.0,
                expected_model_cap=2,
                expected_validator_manifest_sha256=MANIFEST,
            )
        self.assertEqual(
            outcome.parent_receipt["failure_taxonomy"],
            "child_nonzero_without_terminal_receipt",
        )
        self.assertEqual(
            outcome.adaptive_projection["status"], "failure_as_zero"
        )
        self.assertFalse(
            outcome.adaptive_projection["private_effects_known_zero"]
        )
        self.assertEqual(outcome.observation["effect_scope"], "unobserved_lower_bound")
        self.assertTrue(
            outcome.timing_receipt[
                "failure_observation_uses_partial_effect_lower_bound_path"
            ]
        )

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24521_bounded_conversion_parent.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
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
