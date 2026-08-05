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
from deepwide_agent import v24581_bounded_prededup_preservation_parent as frozen  # noqa: E402
from deepwide_agent import v24592_bounded_validator_aligned_title_query_parent as target  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24524_alias_title_integration import TASK  # noqa: E402
from test_v24590_proof_carrying_validator_aligned_title_query import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24592-test-validator-manifest").hexdigest()


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
        target.run_worker(
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
    target.supervise_worker_with_separated_budget(
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


class V24592BoundedValidatorAlignedTitleQueryParentTests(unittest.TestCase):
    def test_private_frozen_binding_does_not_patch_parent_module(self) -> None:
        before = (
            frozen.run_timed_subprocess,
            frozen.run_timed_subprocess.__globals__["proof"],
            frozen.run_timed_subprocess.__globals__["total"],
        )
        self.assertTrue(target.binding_is_private_and_stable())
        self.assertEqual(
            (
                frozen.run_timed_subprocess,
                frozen.run_timed_subprocess.__globals__["proof"],
                frozen.run_timed_subprocess.__globals__["total"],
            ),
            before,
        )

    def test_real_parent_supervisor_worker_chain_projects_query_once(self) -> None:
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
        projection = outcome.proof.adaptive_projection
        self.assertEqual(projection["status"], "validated_capability")
        self.assertGreater(
            projection["validator_aligned_title_query_query_vector_calls"], 0
        )
        self.assertEqual(
            projection["validator_aligned_title_query_logical_query_count"],
            2 * projection["validator_aligned_title_query_query_vector_calls"],
        )
        self.assertGreater(
            projection["prededup_preservation_preserved_candidate_count"], 0
        )
        self.assertFalse(
            projection[
                "validator_aligned_title_query_projection_claims_retrieval_effect_or_causality"
            ]
        )
        self.assertEqual(
            outcome.proof.timing_receipt["certificate_validation_invocations"], 1
        )
        self.assertEqual(
            outcome.proof.timing_receipt["adaptive_projection_invocations"], 1
        )
        self.assertTrue(target.binding_is_private_and_stable())

    def test_nonzero_child_uses_failure_zero_and_effect_lower_bound(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            output_root = Path(temporary)
            directory = output_root / "task"
            directory.mkdir()
            outcome = target.run_timed_subprocess(
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
        projection = outcome.adaptive_projection
        self.assertEqual(projection["status"], "failure_as_zero")
        self.assertTrue(
            all(projection[name] == 0 for name in target.total.QUERY_COUNT_FIELDS)
        )
        self.assertFalse(
            projection[
                "validator_aligned_title_query_additional_private_effects_known_zero"
            ]
        )
        self.assertEqual(outcome.observation["effect_scope"], "unobserved_lower_bound")

    def test_one_origin_preserves_budget_vector(self) -> None:
        self.assertEqual(
            target.budget_vector_seconds(), (150.0, 220.0, 245.0, 255.0)
        )
        captured: dict = {}
        fake = type("Proof", (), {"parent_receipt": {"failure_taxonomy": "success"}})()
        with patch.dict(
            target.run_parent_with_separated_budget.__globals__,
            {
                "run_timed_subprocess": lambda **kwargs: captured.update(kwargs)
                or fake,
                "_read_supervision_receipt": lambda *_args, **_kwargs: {
                    "worker_hard_timeout": False,
                    "return_code": 0,
                    "last_stage": "worker_complete",
                },
            },
        ):
            target.run_parent_with_separated_budget(
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
        self.assertEqual(captured["timeout_seconds"], 244.75)
        self.assertEqual(
            captured["command"][-2:],
            ["--deadline-origin-monotonic", "1000.0"],
        )
        self.assertTrue(target.binding_is_private_and_stable())

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path(
                "src/deepwide_agent/"
                "v24592_bounded_validator_aligned_title_query_parent.py"
            )
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
