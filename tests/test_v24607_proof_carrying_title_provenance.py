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

from deepwide_agent import v24599_proof_carrying_title_funnel as parent  # noqa: E402
from deepwide_agent import v24607_proof_carrying_title_provenance as proof  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import RESULT_NAME  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24524_alias_title_integration import TASK  # noqa: E402
from test_v24590_proof_carrying_validator_aligned_title_query import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24607-test-validator-manifest").hexdigest()


def read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(path)
    return value


def rewrite(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def populate(root: Path):
    directory = root / "task"
    checkpoint = root / "checkpoint"
    fixture = root / "fixture"
    directory.mkdir()
    checkpoint.mkdir()
    fixture.mkdir()
    clock = AdvancingClock()
    model, search = clients(fixture, clock)
    with patch("deepwide_agent.v24469_bounded_worker_supervisor.bind_worker_to_parent"):
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
    return directory, result, model, search


def validate(root: Path):
    directory = root / "task"
    return proof.validate_proof_carrying_title_provenance_bundle(
        read(directory / RESULT_NAME),
        ordinal=1,
        directory=directory,
        output_root=root,
        expected_model_cap=2,
        expected_validator_manifest_sha256=MANIFEST,
    )


class V24607ProofCarryingTitleProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        cls.root = Path(cls.temporary.name)
        cls.directory, cls.result, cls.model, cls.search = populate(cls.root)
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

    def test_real_worker_mints_counts_only_provenance_capability(self) -> None:
        self.assertIsInstance(
            self.capability,
            proof.ValidatedProofCarryingContentFreeTitleProvenance,
        )
        receipt = self.capability.content_free_title_provenance_receipt()
        self.assertEqual(
            receipt["action_source_empty_title_count"]
            + receipt["action_source_nonempty_title_count"],
            receipt["action_source_count"],
        )
        self.assertEqual(
            read(proof.auxiliary_directory(self.root, 1) / proof.RECEIPT_NAME),
            receipt,
        )
        self.assertEqual(self.model.acquisitions, 2)
        self.assertEqual(self.search.request_invocations, 4)
        self.assertEqual(self.search.fetch_invocations, 4)

    def test_parent_validation_precedes_successor_without_private_replay(self) -> None:
        order: list[str] = []
        original = parent.validate_proof_carrying_title_funnel_bundle

        def wrapped(*args, **kwargs):
            order.append("parent")
            return original(*args, **kwargs)

        with (
            patch.object(
                parent,
                "validate_proof_carrying_title_funnel_bundle",
                side_effect=wrapped,
            ),
            patch.object(
                proof.provenance_policy.ContentFreeTitleProvenanceObserver,
                "_observe_payload",
                side_effect=AssertionError("private payload replay"),
            ),
        ):
            capability = validate(self.root)
        self.assertIsInstance(
            capability,
            proof.ValidatedProofCarryingContentFreeTitleProvenance,
        )
        self.assertEqual(order, ["parent"])

    def test_receipt_certificate_and_parent_byte_tamper_fail_closed(self) -> None:
        for mode in ("receipt", "certificate", "parent_receipt", "parent_certificate"):
            with self.subTest(mode=mode):
                root = self.copied_root()
                auxiliary = proof.auxiliary_directory(root, 1)
                parent_auxiliary = parent.auxiliary_directory(root, 1)
                if mode == "receipt":
                    (auxiliary / proof.RECEIPT_NAME).write_bytes(
                        (auxiliary / proof.RECEIPT_NAME).read_bytes() + b" "
                    )
                elif mode == "certificate":
                    path = auxiliary / proof.CERTIFICATE_NAME
                    value = read(path)
                    value[
                        "title_provenance_changes_query_search_fetch_ranking_validator_evidence_posterior_entropy_or_credit"
                    ] = True
                    value.pop("certificate_payload_sha256")
                    value["certificate_payload_sha256"] = payload_sha256(value)
                    rewrite(path, value)
                elif mode == "parent_receipt":
                    (parent_auxiliary / parent.RECEIPT_NAME).write_bytes(
                        (parent_auxiliary / parent.RECEIPT_NAME).read_bytes() + b"\n"
                    )
                else:
                    (parent_auxiliary / parent.CERTIFICATE_NAME).write_bytes(
                        (parent_auxiliary / parent.CERTIFICATE_NAME).read_bytes() + b"\n"
                    )
                with self.assertRaises((RuntimeError, TypeError, ValueError)):
                    validate(root)

    def test_raw_mapping_cannot_forge_and_receipt_is_content_free(self) -> None:
        with self.assertRaises(TypeError):
            proof.ValidatedProofCarryingContentFreeTitleProvenance(self.result)
        encoded = json.dumps(
            self.capability.content_free_title_provenance_receipt(),
            ensure_ascii=False,
            sort_keys=True,
        )
        for prohibited in (
            TASK["question"],
            TASK["opaque_id"],
            "University of Southern Queensland",
            "example.edu",
            "raw_content",
            "candidate_prediction",
        ):
            self.assertNotIn(prohibited, encoded)

    def test_privileged_task_rejected_before_directory_or_external_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            root = Path(temporary)
            directory = root / "task"
            checkpoint = root / "checkpoint"
            fixture = root / "fixture"
            directory.mkdir()
            checkpoint.mkdir()
            fixture.mkdir()
            clock = AdvancingClock()
            model, search = clients(fixture, clock)
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

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24607_proof_carrying_title_provenance.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
