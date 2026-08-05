from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
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

from deepwide_agent import v24525_proof_carrying_alias_title as alias_proof  # noqa: E402
from deepwide_agent import v24527_bounded_alias_title_parent as bounded_parent  # noqa: E402
from deepwide_agent import v24530_alias_seeded_bounded_worker as seeded_worker  # noqa: E402
from deepwide_agent import v24533_alias_acquisition_entropy_credit as action_credit  # noqa: E402
from deepwide_agent import v24534_proof_carrying_alias_acquisition as proof  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import RESULT_NAME  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24524_alias_title_integration import TASK, clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24534-test-validator-manifest").hexdigest()


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(path)
    return value


def rewrite(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def writer(directory: Path):
    return lambda name, value: _new_json(directory / name, value)


def populate_direct(root: Path):
    directory = root / "task"
    checkpoint = root / "checkpoint"
    fixture = root / "fixture"
    directory.mkdir()
    checkpoint.mkdir()
    fixture.mkdir()
    clock = AdvancingClock()
    model, search = clients(fixture, clock, mode="support")
    with patch(
        "deepwide_agent.v24469_bounded_worker_supervisor.bind_worker_to_parent"
    ):
        result = proof.run_worker(
            TASK,
            ordinal=1,
            expected_supervisor_pid=os.getpid(),
            checkpoint_directory=checkpoint,
            output_root=root,
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
    return directory, checkpoint, result, model, search


def validate(root: Path):
    directory = root / "task"
    return proof.validate_proof_carrying_alias_acquisition_bundle(
        read(directory / RESULT_NAME),
        ordinal=1,
        directory=directory,
        output_root=root,
        expected_model_cap=2,
        expected_validator_manifest_sha256=MANIFEST,
    )


def process_mode(args: argparse.Namespace) -> int:
    output_root = Path(args.output_root)
    directory = Path(args.directory)
    checkpoint = Path(args.checkpoint_directory)
    fixture = Path(args.fixture)
    if args.command == "worker":
        clock = AdvancingClock()
        model, search = clients(fixture, clock, mode="support")
        proof.run_worker(
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
    proof.supervise_worker_with_separated_budget(
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


class V24534ProofCarryingAliasAcquisitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.root = Path(cls.temporary.name)
        (
            cls.directory,
            cls.checkpoint,
            cls.result,
            cls.model,
            cls.search,
        ) = populate_direct(cls.root)
        cls.capability = validate(cls.root)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def copied_root(self) -> Path:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "copy"
        shutil.copytree(self.root, root)
        return root

    def test_worker_preserves_frozen_task_surface_and_mints_opaque_capability(self) -> None:
        self.assertIsInstance(
            self.capability, proof.ValidatedProofCarryingAliasAcquisition
        )
        self.assertEqual(
            {path.name for path in self.directory.iterdir()},
            set(alias_proof.SUCCESS_NAMES),
        )
        auxiliary = proof.auxiliary_directory(self.root, 1)
        self.assertEqual(
            {path.name for path in auxiliary.iterdir()}, set(proof.AUXILIARY_NAMES)
        )
        receipt = self.capability.action_credit_receipt()
        self.assertEqual(
            receipt, read(auxiliary / proof.RECEIPT_NAME)
        )
        self.assertEqual(receipt["target_plan_count"], 1)
        self.assertGreater(receipt["alias_seeded_query_vector_calls"], 0)
        self.assertGreater(receipt["lead_selection_calls"], 0)
        self.assertEqual(self.model.acquisitions, 2)
        self.assertEqual(self.search.request_invocations, 4)
        self.assertEqual(self.search.fetch_invocations, 5)

    def test_validation_is_read_only_and_does_not_replay_private_semantics(self) -> None:
        before = {
            path.relative_to(self.root): path.read_bytes()
            for path in (*self.directory.iterdir(), *proof.auxiliary_directory(self.root, 1).iterdir())
        }
        with (
            patch.object(
                action_credit,
                "build_action_credit_receipt",
                side_effect=AssertionError("private action replay"),
            ),
            patch.object(
                seeded_worker,
                "validate_acquisition_activity",
                side_effect=AssertionError("private acquisition replay"),
            ),
        ):
            capability = validate(self.root)
        self.assertIsInstance(
            capability, proof.ValidatedProofCarryingAliasAcquisition
        )
        after = {
            path.relative_to(self.root): path.read_bytes()
            for path in (*self.directory.iterdir(), *proof.auxiliary_directory(self.root, 1).iterdir())
        }
        self.assertEqual(after, before)

    def test_receipt_certificate_alias_and_outer_byte_tamper_fail_closed(self) -> None:
        for mode in ("receipt", "certificate", "alias", "outer"):
            with self.subTest(mode=mode):
                root = self.copied_root()
                directory = root / "task"
                auxiliary = proof.auxiliary_directory(root, 1)
                if mode == "receipt":
                    path = auxiliary / proof.RECEIPT_NAME
                    path.write_bytes(path.read_bytes() + b" ")
                elif mode == "certificate":
                    path = auxiliary / proof.CERTIFICATE_NAME
                    value = read(path)
                    value["ordinal"] = 2
                    value.pop("certificate_payload_sha256")
                    value["certificate_payload_sha256"] = payload_sha256(value)
                    rewrite(path, value)
                elif mode == "alias":
                    path = directory / alias_proof.ALIAS_RESULT_NAME
                    path.write_bytes(path.read_bytes() + b"\n")
                else:
                    path = directory / alias_proof.CERTIFICATE_NAME
                    path.write_bytes(path.read_bytes() + b"\n")
                with self.assertRaises((RuntimeError, TypeError, ValueError)):
                    validate(root)

    def test_manifest_extra_file_and_symlink_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            proof.validate_proof_carrying_alias_acquisition_bundle(
                read(self.directory / RESULT_NAME),
                ordinal=1,
                directory=self.directory,
                output_root=self.root,
                expected_model_cap=2,
                expected_validator_manifest_sha256="not-a-digest",
            )
        for mode in ("extra", "symlink"):
            with self.subTest(mode=mode):
                root = self.copied_root()
                auxiliary = proof.auxiliary_directory(root, 1)
                if mode == "extra":
                    (auxiliary / "unexpected.json").write_text("{}\n")
                else:
                    (auxiliary / "unexpected-link").symlink_to(proof.RECEIPT_NAME)
                with self.assertRaises(RuntimeError):
                    validate(root)

    def test_real_parent_supervisor_worker_chain_retains_auxiliary_receipt(self) -> None:
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
            outcome = proof.run_parent_with_separated_budget(
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
            auxiliary_names = {
                path.name
                for path in proof.auxiliary_directory(output_root, 1).iterdir()
            }
            task_names = {path.name for path in directory.iterdir()}
        self.assertLess(elapsed, 70.0)
        self.assertEqual(outcome.proof.parent_receipt["failure_taxonomy"], "success")
        self.assertEqual(outcome.proof.adaptive_projection["status"], "validated_capability")
        self.assertEqual(
            outcome.proof.adaptive_projection[
                "acquisition_action_target_plan_count"
            ],
            1,
        )
        self.assertGreater(
            outcome.proof.adaptive_projection[
                "acquisition_action_alias_seeded_query_vector_calls"
            ],
            0,
        )
        self.assertEqual(outcome.supervision_receipt["last_stage"], "worker_complete")
        self.assertEqual(auxiliary_names, set(proof.AUXILIARY_NAMES))
        self.assertEqual(task_names, set(bounded_parent.SUCCESS_SURFACE))
        self.assertEqual(
            outcome.proof.timing_receipt["certificate_validation_invocations"], 1
        )

    def test_raw_mapping_cannot_forge_capability_and_public_receipt_is_content_free(self) -> None:
        with self.assertRaises(TypeError):
            proof.ValidatedProofCarryingAliasAcquisition(self.result)
        encoded = json.dumps(
            self.capability.action_credit_receipt(),
            ensure_ascii=False,
            sort_keys=True,
        )
        for prohibited in (
            TASK["question"],
            TASK["opaque_id"],
            "University of Southern Queensland",
            "1967",
            "usq-one.example",
            "raw_content",
            "candidate_prediction",
        ):
            self.assertNotIn(prohibited, encoded)

    def test_privileged_task_is_rejected_before_filesystem_model_or_search_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            root = Path(temporary)
            directory = root / "task"
            checkpoint = root / "checkpoint"
            fixture = root / "fixture"
            directory.mkdir()
            checkpoint.mkdir()
            fixture.mkdir()
            clock = AdvancingClock()
            model, search = clients(fixture, clock, mode="support")
            with self.assertRaises(ValueError):
                proof.run_worker(
                    {**TASK, "category": "forbidden"},
                    ordinal=1,
                    expected_supervisor_pid=os.getpid(),
                    checkpoint_directory=checkpoint,
                    output_root=root,
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
            self.assertFalse(proof.auxiliary_directory(root, 1).exists())
            self.assertEqual(model.acquisitions, 0)
            self.assertEqual(search.request_invocations, 0)
            self.assertEqual(search.fetch_invocations, 0)

    def test_runtime_sources_are_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        for path in (
            Path("src/deepwide_agent/v24534_proof_carrying_alias_acquisition.py"),
            Path("src/deepwide_agent/v24535_total_alias_acquisition_projection.py"),
        ):
            with self.subTest(path=path):
                accesses, imports = audit.ast_findings(path)
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
