from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24525_proof_carrying_alias_title as alias_proof  # noqa: E402
from deepwide_agent import v24548_alias_action_joint_observability as joint  # noqa: E402
from deepwide_agent import v24549_proof_carrying_alias_joint as proof  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import RESULT_NAME  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24524_alias_title_integration import TASK, clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24549-test-validator-manifest").hexdigest()


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


def populate(root: Path):
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
            writer=lambda name, value: _new_json(directory / name, value),
            validator_manifest_sha256=MANIFEST,
        )
    return directory, checkpoint, result, model, search


def validate(root: Path):
    directory = root / "task"
    return proof.validate_proof_carrying_alias_joint_bundle(
        read(directory / RESULT_NAME),
        ordinal=1,
        directory=directory,
        output_root=root,
        expected_model_cap=2,
        expected_validator_manifest_sha256=MANIFEST,
    )


class V24549ProofCarryingAliasJointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.root = Path(cls.temporary.name)
        cls.directory, _, cls.result, cls.model, cls.search = populate(cls.root)
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

    def test_worker_preserves_task_surface_and_mints_opaque_joint_capability(self) -> None:
        self.assertIsInstance(
            self.capability, proof.ValidatedProofCarryingAliasJoint
        )
        self.assertEqual(
            {path.name for path in self.directory.iterdir()},
            set(alias_proof.SUCCESS_NAMES),
        )
        auxiliary = proof.auxiliary_directory(self.root, 1)
        self.assertEqual(
            {path.name for path in auxiliary.iterdir()}, set(proof.AUXILIARY_NAMES)
        )
        receipt = self.capability.joint_observability_receipt()
        self.assertEqual(receipt, read(auxiliary / proof.RECEIPT_NAME))
        self.assertEqual(receipt["target_plan_count"], 1)
        self.assertTrue(
            receipt["same_task_joint_counts_do_not_claim_lead_level_causality"]
        )
        self.assertEqual(self.model.acquisitions, 2)
        self.assertEqual(self.search.request_invocations, 4)
        self.assertEqual(self.search.fetch_invocations, 5)

    def test_validation_is_read_only_and_does_not_replay_private_semantics(self) -> None:
        before = {
            path.relative_to(self.root): path.read_bytes()
            for path in (
                *self.directory.iterdir(),
                *proof.auxiliary_directory(self.root, 1).iterdir(),
            )
        }
        with patch.object(
            joint,
            "build_joint_receipt",
            side_effect=AssertionError("private joint replay"),
        ):
            capability = validate(self.root)
        self.assertIsInstance(capability, proof.ValidatedProofCarryingAliasJoint)
        after = {
            path.relative_to(self.root): path.read_bytes()
            for path in (
                *self.directory.iterdir(),
                *proof.auxiliary_directory(self.root, 1).iterdir(),
            )
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
                    value[
                        "same_task_joint_counts_do_not_claim_lead_level_causality"
                    ] = False
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
            proof.validate_proof_carrying_alias_joint_bundle(
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

    def test_raw_mapping_cannot_forge_capability_and_receipt_is_content_free(self) -> None:
        with self.assertRaises(TypeError):
            proof.ValidatedProofCarryingAliasJoint(self.result)
        encoded = json.dumps(
            self.capability.joint_observability_receipt(),
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

    def test_privileged_task_rejected_before_directory_model_or_search_effect(self) -> None:
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
                    writer=lambda name, value: _new_json(directory / name, value),
                    validator_manifest_sha256=MANIFEST,
                )
            self.assertFalse(proof.auxiliary_directory(root, 1).exists())
            self.assertEqual(model.acquisitions, 0)
            self.assertEqual(search.request_invocations, 0)
            self.assertEqual(search.fetch_invocations, 0)

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24549_proof_carrying_alias_joint.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
