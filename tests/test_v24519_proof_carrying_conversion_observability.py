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

from deepwide_agent import v24503_record_bound_reserve_integration as recovery  # noqa: E402
from deepwide_agent import v24504_proof_carrying_record_bound_reserve as parent  # noqa: E402
from deepwide_agent.v24309_runner_exit_integration import _new_json  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import RESULT_NAME  # noqa: E402
from deepwide_agent.v24519_proof_carrying_conversion_observability import (  # noqa: E402
    CERTIFICATE_NAME,
    RECEIPT_NAME,
    SUCCESS_NAMES,
    ValidatedProofCarryingConversionObservability,
    run_conversion_observable_worker,
    validate_outer_certificate,
    validate_proof_carrying_conversion_bundle,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24516_neutral_discovery_record_bound_worker import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24519-test-validator-manifest").hexdigest()


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


class V24519ProofCarryingConversionObservabilityTests(unittest.TestCase):
    def populate(self, directory: Path) -> tuple[dict, object, object]:
        fixture = directory.parent / "fixture"
        fixture.mkdir(exist_ok=True)
        clock = AdvancingClock()
        model, search = clients(fixture, clock)
        receipt = run_conversion_observable_worker(
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
        return receipt, model, search

    def validate(self, directory: Path):
        return validate_proof_carrying_conversion_bundle(
            read(directory / RESULT_NAME),
            directory=directory,
            expected_model_cap=2,
            expected_validator_manifest_sha256=MANIFEST,
        )

    def make_populated(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output_root = Path(temporary.name)
        directory = output_root / "task"
        directory.mkdir()
        receipt, model, search = self.populate(directory)
        return directory, receipt, model, search

    def test_outer_capability_binds_old_proof_and_new_counts(self) -> None:
        directory, receipt, model, search = self.make_populated()
        capability = self.validate(directory)
        self.assertIsInstance(
            capability, ValidatedProofCarryingConversionObservability
        )
        self.assertEqual(capability.counts_only_receipt(), receipt)
        parent_projection = parent.task_projection(
            1, capability.parent_capability()
        )
        self.assertTrue(parent_projection["passed"])
        self.assertGreaterEqual(receipt["grammar_projection_pair_count"], 1)
        self.assertEqual(
            receipt["reason_counts"][
                "projection_duplicate_parent_observation"
            ],
            receipt["grammar_projection_pair_count"],
        )
        self.assertEqual(model.acquisitions, 2)
        self.assertEqual(search.request_invocations, 4)
        self.assertEqual(search.fetch_invocations, 4)
        self.assertEqual(
            {path.name for path in directory.iterdir()}, SUCCESS_NAMES
        )

    def test_outer_certificate_binds_neutral_planner_and_exact_bytes(self) -> None:
        directory, receipt, _model, _search = self.make_populated()
        certificate = validate_outer_certificate(
            read(directory / CERTIFICATE_NAME),
            directory=directory,
            expected_validator_manifest_sha256=MANIFEST,
        )
        planner = certificate["neutral_discovery_planner_receipt"]
        self.assertEqual(planner["cell_discovery_plan_builds"], 1)
        self.assertFalse(planner["cell_discovery_seed_value_present"])
        self.assertEqual(
            certificate["conversion_observability_receipt"], receipt
        )
        self.assertEqual(
            set(certificate["artifact_byte_receipts"]),
            {
                RESULT_NAME,
                parent.MODEL_NAME,
                parent.TRANSPORT_NAME,
                parent.SEARCH_NAME,
                parent.CERTIFICATE_NAME,
                RECEIPT_NAME,
            },
        )

    def test_parent_validation_does_not_replay_private_semantics(self) -> None:
        directory, _receipt, _model, _search = self.make_populated()
        with (
            patch.object(
                recovery,
                "validate_result",
                side_effect=AssertionError("private record semantic replay"),
            ),
            patch.object(
                parent,
                "validate_cross_artifacts",
                side_effect=AssertionError("private parent semantic replay"),
            ),
        ):
            capability = self.validate(directory)
        self.assertIsInstance(
            capability, ValidatedProofCarryingConversionObservability
        )

    def test_receipt_parent_certificate_and_private_result_tamper_fail(self) -> None:
        for mode in ("receipt", "parent_certificate", "private_result"):
            with self.subTest(mode=mode):
                directory, _receipt, _model, _search = self.make_populated()
                if mode == "receipt":
                    value = read(directory / RECEIPT_NAME)
                    value["reason_counts"]["new_observation_emitted"] -= 1
                    value["reason_counts"][
                        "no_projection_explicit_relation_absent"
                    ] += 1
                    value.pop("receipt_sha256")
                    value["receipt_sha256"] = payload_sha256(value)
                    rewrite(directory / RECEIPT_NAME, value)
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
                directory, _receipt, _model, _search = self.make_populated()
                certificate = read(directory / CERTIFICATE_NAME)
                if mode == "receipt":
                    certificate["conversion_observability_receipt"][
                        "reason_counts"
                    ]["new_observation_emitted"] -= 1
                    certificate["conversion_observability_receipt"][
                        "reason_counts"
                    ]["no_projection_explicit_relation_absent"] += 1
                    inner = certificate["conversion_observability_receipt"]
                    inner.pop("receipt_sha256")
                    inner["receipt_sha256"] = payload_sha256(inner)
                elif mode == "planner":
                    certificate["neutral_discovery_planner_receipt"][
                        "cell_discovery_seed_value_present"
                    ] = True
                elif mode == "manifest":
                    with self.assertRaises(ValueError):
                        validate_proof_carrying_conversion_bundle(
                            read(directory / RESULT_NAME),
                            directory=directory,
                            expected_model_cap=2,
                            expected_validator_manifest_sha256="0" * 64,
                        )
                    continue
                else:
                    certificate["artifact_byte_receipts"][RECEIPT_NAME][
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
                directory, _receipt, _model, _search = self.make_populated()
                if mode == "extra":
                    (directory / "unexpected.json").write_text("{}\n")
                else:
                    (directory / "unexpected-link").symlink_to(RECEIPT_NAME)
                with self.assertRaises(RuntimeError):
                    self.validate(directory)

    def test_raw_mapping_cannot_forge_capability_and_receipt_is_content_free(self) -> None:
        directory, receipt, _model, _search = self.make_populated()
        capability = self.validate(directory)
        with self.assertRaises(TypeError):
            ValidatedProofCarryingConversionObservability(receipt)
        with self.assertRaises(TypeError):
            parent.task_projection(1, receipt)  # type: ignore[arg-type]
        encoded = json.dumps(
            capability.counts_only_receipt(), ensure_ascii=False, sort_keys=True
        )
        for prohibited in (
            TASK["question"],
            TASK["opaque_id"],
            "Alpha",
            "2025",
            "neutral-discovery",
            "query_vector",
            "raw_content",
            "candidate_prediction",
        ):
            self.assertNotIn(prohibited, encoded)
        self.assertEqual(
            [key for key in capability.counts_only_receipt() if "sha256" in key],
            ["receipt_sha256"],
        )

    def test_runtime_source_is_label_blind(self) -> None:
        from scripts import audit_v24398_failure_observability_build as audit

        for path in (
            Path("src/deepwide_agent/v24518_conversion_observability.py"),
            Path(
                "src/deepwide_agent/v24519_proof_carrying_conversion_observability.py"
            ),
        ):
            accesses, imports = audit._ast_findings(path)
            self.assertEqual(accesses, [])
            self.assertEqual(imports, [])


if __name__ == "__main__":
    unittest.main()
