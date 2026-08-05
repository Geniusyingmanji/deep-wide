from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent import v24504_proof_carrying_record_bound_reserve as parent  # noqa: E402
from deepwide_agent import v24524_alias_title_integration as integration  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import RESULT_NAME  # noqa: E402
from deepwide_agent.v24525_proof_carrying_alias_title import (  # noqa: E402
    ALIAS_RESULT_NAME,
    CERTIFICATE_NAME,
    SUCCESS_NAMES,
    ValidatedProofCarryingAliasTitle,
    run_alias_title_worker,
    validate_outer_certificate,
    validate_proof_carrying_alias_bundle,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24524_alias_title_integration import TASK, clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24525-test-validator-manifest").hexdigest()


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


class V24525ProofCarryingAliasTitleTests(unittest.TestCase):
    def populate(self, directory: Path):
        fixture = directory.parent / "fixture"
        fixture.mkdir(exist_ok=True)
        clock = AdvancingClock()
        model, search = clients(fixture, clock, mode="support")
        result = run_alias_title_worker(
            TASK,
            output_root=directory.parent,
            directory=directory,
            model_factory=lambda: model,
            search_factory=lambda: search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
            expected_model_cap=2,
            writer=writer(directory),
            validator_manifest_sha256=MANIFEST,
        )
        return result, model, search

    def validate(self, directory: Path):
        return validate_proof_carrying_alias_bundle(
            read(directory / RESULT_NAME),
            directory=directory,
            expected_model_cap=2,
            expected_validator_manifest_sha256=MANIFEST,
        )

    def make_populated(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        directory = root / "task"
        directory.mkdir()
        result, model, search = self.populate(directory)
        return directory, result, model, search

    def test_capability_binds_parent_proof_and_alias_credit(self) -> None:
        directory, result, model, search = self.make_populated()
        capability = self.validate(directory)
        self.assertIsInstance(capability, ValidatedProofCarryingAliasTitle)
        self.assertEqual(
            capability.counts_only_receipt(), result["alias_title_receipt"]
        )
        self.assertGreater(
            capability.counts_only_receipt()["decision_credit_gain_nats"], 0
        )
        self.assertTrue(
            parent.task_projection(1, capability.parent_capability())["passed"]
        )
        self.assertFalse(
            result["alias_title_receipt"]["additional_model_requests"]
        )
        self.assertFalse(
            result["alias_title_receipt"]["additional_search_batches"]
        )
        self.assertFalse(
            result["alias_title_receipt"]["additional_fetch_calls"]
        )
        self.assertEqual(model.acquisitions, 2)
        # V2.45.25 installs the neutral-discovery planner for the complete
        # parent execution.  Its parent path therefore has one targeted
        # search and two targeted fetch batches beyond the legacy V2.45.24
        # fixture; the alias projection itself remains zero-effect above.
        self.assertEqual(search.request_invocations, 4)
        self.assertEqual(search.fetch_invocations, 5)
        self.assertEqual({path.name for path in directory.iterdir()}, SUCCESS_NAMES)

    def test_outer_certificate_binds_exact_bytes_memos_and_planner(self) -> None:
        directory, result, _model, _search = self.make_populated()
        certificate = validate_outer_certificate(
            read(directory / CERTIFICATE_NAME),
            directory=directory,
            expected_validator_manifest_sha256=MANIFEST,
        )
        self.assertEqual(
            certificate["alias_title_receipt"], result["alias_title_receipt"]
        )
        self.assertEqual(
            set(certificate["artifact_byte_receipts"]),
            {
                RESULT_NAME,
                parent.MODEL_NAME,
                parent.TRANSPORT_NAME,
                parent.SEARCH_NAME,
                parent.CERTIFICATE_NAME,
                ALIAS_RESULT_NAME,
            },
        )
        planner = certificate["neutral_discovery_planner_receipt"]
        self.assertEqual(planner["cell_discovery_plan_builds"], 1)
        self.assertFalse(planner["cell_discovery_seed_value_present"])

    def test_parent_validation_does_not_replay_private_alias_semantics(self) -> None:
        directory, _result, _model, _search = self.make_populated()
        with (
            patch.object(
                integration,
                "validate_result",
                side_effect=AssertionError("private alias replay"),
            ),
            patch.object(
                integration,
                "_validate_result_in_scope",
                side_effect=AssertionError("private alias replay"),
            ),
            patch.object(
                parent,
                "validate_cross_artifacts",
                side_effect=AssertionError("private parent replay"),
            ),
        ):
            capability = self.validate(directory)
        self.assertIsInstance(capability, ValidatedProofCarryingAliasTitle)

    def test_alias_result_parent_certificate_and_private_parent_tamper_fail(self) -> None:
        for mode in ("alias", "parent_certificate", "private_parent"):
            with self.subTest(mode=mode):
                directory, _result, _model, _search = self.make_populated()
                if mode == "alias":
                    value = read(directory / ALIAS_RESULT_NAME)
                    value["alias_title_receipt"]["decision_credit_gain_nats"] = 0
                    value["alias_title_receipt"].pop("receipt_sha256")
                    value["alias_title_receipt"]["receipt_sha256"] = payload_sha256(
                        value["alias_title_receipt"]
                    )
                    value.pop("result_sha256")
                    value["result_sha256"] = payload_sha256(value)
                    rewrite(directory / ALIAS_RESULT_NAME, value)
                elif mode == "parent_certificate":
                    value = read(directory / parent.CERTIFICATE_NAME)
                    value["validation_memo_receipt"]["total_hits"] = 0
                    value.pop("certificate_payload_sha256")
                    value["certificate_payload_sha256"] = payload_sha256(value)
                    rewrite(directory / parent.CERTIFICATE_NAME, value)
                else:
                    value = read(directory / RESULT_NAME)
                    value["record_bound_result"]["candidate_prediction"] += "\n"
                    value["record_bound_result"].pop("result_sha256")
                    value["record_bound_result"]["result_sha256"] = payload_sha256(
                        value["record_bound_result"]
                    )
                    value.pop("envelope_payload_sha256")
                    value["envelope_payload_sha256"] = payload_sha256(value)
                    rewrite(directory / RESULT_NAME, value)
                with self.assertRaises((RuntimeError, ValueError)):
                    self.validate(directory)

    def test_outer_resealed_receipt_planner_manifest_and_byte_tamper_fail(self) -> None:
        for mode in ("receipt", "planner", "manifest", "bytes"):
            with self.subTest(mode=mode):
                directory, _result, _model, _search = self.make_populated()
                certificate = read(directory / CERTIFICATE_NAME)
                if mode == "receipt":
                    certificate["alias_title_receipt"][
                        "decision_credit_gain_nats"
                    ] = 0
                    inner = certificate["alias_title_receipt"]
                    inner.pop("receipt_sha256")
                    inner["receipt_sha256"] = payload_sha256(inner)
                elif mode == "planner":
                    certificate["neutral_discovery_planner_receipt"][
                        "cell_discovery_seed_value_present"
                    ] = True
                elif mode == "manifest":
                    with self.assertRaises(ValueError):
                        validate_proof_carrying_alias_bundle(
                            read(directory / RESULT_NAME),
                            directory=directory,
                            expected_model_cap=2,
                            expected_validator_manifest_sha256="0" * 64,
                        )
                    continue
                else:
                    certificate["artifact_byte_receipts"][ALIAS_RESULT_NAME][
                        "byte_length"
                    ] += 1
                certificate.pop("certificate_payload_sha256")
                certificate["certificate_payload_sha256"] = payload_sha256(
                    certificate
                )
                rewrite(directory / CERTIFICATE_NAME, certificate)
                with self.assertRaises((RuntimeError, ValueError)):
                    self.validate(directory)

    def test_extra_file_and_symlink_surface_fail_closed(self) -> None:
        for mode in ("extra", "symlink"):
            with self.subTest(mode=mode):
                directory, _result, _model, _search = self.make_populated()
                if mode == "extra":
                    (directory / "unexpected.json").write_text("{}\n")
                else:
                    (directory / "unexpected-link").symlink_to(ALIAS_RESULT_NAME)
                with self.assertRaises(RuntimeError):
                    self.validate(directory)

    def test_raw_mapping_cannot_forge_capability_and_receipt_is_content_free(self) -> None:
        directory, result, _model, _search = self.make_populated()
        capability = self.validate(directory)
        with self.assertRaises(TypeError):
            ValidatedProofCarryingAliasTitle(result)
        encoded = json.dumps(
            capability.counts_only_receipt(), ensure_ascii=False, sort_keys=True
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

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24495_targeted_conversion_projection_build as audit

        accesses, imports = audit.ast_findings(
            Path("src/deepwide_agent/v24525_proof_carrying_alias_title.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        directory = root / "task"
        directory.mkdir()
        clock = AdvancingClock()
        model, search = clients(root, clock, mode="support")
        with self.assertRaises(ValueError):
            run_alias_title_worker(
                {**TASK, "category": "forbidden"},
                output_root=root,
                directory=directory,
                model_factory=lambda: model,
                search_factory=lambda: search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
                expected_model_cap=2,
                writer=lambda _name, _value: None,
                validator_manifest_sha256=MANIFEST,
            )
        self.assertEqual(model.acquisitions, 0)
        self.assertEqual(search.request_invocations, 0)
        self.assertEqual(search.fetch_invocations, 0)


if __name__ == "__main__":
    unittest.main()
