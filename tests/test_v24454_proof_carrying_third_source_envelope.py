from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    CHILD_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
)
from deepwide_agent.v24447_third_source_entropy_to_decision import (  # noqa: E402
    build_envelope,
    run_v24447_task,
)
from deepwide_agent.v24448_serialized_third_source_envelope import (  # noqa: E402
    validate_serialized_observed_bundle,
)
from deepwide_agent.v24454_proof_carrying_third_source_envelope import (  # noqa: E402
    CERTIFICATE_NAME,
    ValidatedProofCarryingThirdSourceEnvelope,
    build_terminal_certificate,
    validate_proof_carrying_observed_bundle,
)
from scripts import v24449_third_source_external_projection as projection  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import clients  # noqa: E402
from deepwide_agent.v24308_child_exit_observability import child_receipt  # noqa: E402


MANIFEST = hashlib.sha256(b"v24454-test-validator-manifest").hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class V24454ProofCarryingThirdSourceEnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_root = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = AdvancingClock()
        model, search = clients(Path(cls.fixture_root.name), clock, third=True)
        cls.outcome = run_v24447_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        cls.envelope = build_envelope(cls.outcome)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_root.cleanup()

    def populated_directory(self, root: Path) -> None:
        artifacts = {
            RESULT_NAME: self.envelope,
            MODEL_NAME: self.outcome.model_slot_receipt,
            TRANSPORT_NAME: self.outcome.transport_health,
            SEARCH_NAME: self.outcome.search_single_shot_receipt,
        }
        for name, value in artifacts.items():
            write_json(root / name, value)
        certificate = build_terminal_certificate(
            root,
            self.outcome,
            validator_manifest_sha256=MANIFEST,
            expected_artifacts=artifacts,
        )
        write_json(root / CERTIFICATE_NAME, certificate)
        write_json(
            root / CHILD_NAME,
            child_receipt(
                stage="result_envelope_written",
                exception_type=None,
                model_receipt_written=True,
                transport_receipt_written=True,
                result_envelope_written=True,
            ),
        )

    def validate(self, directory: Path):
        value = json.loads((directory / RESULT_NAME).read_text(encoding="utf-8"))
        return validate_proof_carrying_observed_bundle(
            value,
            directory=directory,
            expected_model_cap=2,
            expected_validator_manifest_sha256=MANIFEST,
        )

    def test_projection_is_exactly_equal_to_complete_parent_replay(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populated_directory(directory)
            proof = self.validate(directory)
            full = validate_serialized_observed_bundle(
                json.loads((directory / RESULT_NAME).read_text(encoding="utf-8")),
                model_slot_receipt=self.outcome.model_slot_receipt,
                transport_health=self.outcome.transport_health,
                search_single_shot_receipt=self.outcome.search_single_shot_receipt,
                expected_cap=2,
            )
            self.assertIsInstance(
                proof, ValidatedProofCarryingThirdSourceEnvelope
            )
            self.assertEqual(
                projection.task_projection(1, proof),
                projection.task_projection(1, full),
            )

    def test_private_page_or_receipt_byte_tamper_fails_closed(self) -> None:
        for mode in ("private_page", "model_receipt"):
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
                    directory = Path(temporary)
                    self.populated_directory(directory)
                    if mode == "private_page":
                        value = json.loads(
                            (directory / RESULT_NAME).read_text(encoding="utf-8")
                        )
                        value["third_source_result"]["third_source_private_state"][
                            "third_fetch_batches"
                        ][0]["results"][0]["raw_content"] += " tamper"
                        write_json(directory / RESULT_NAME, value)
                    else:
                        value = json.loads(
                            (directory / MODEL_NAME).read_text(encoding="utf-8")
                        )
                        value["remaining_seconds_at_receipt"] = max(
                            0.0, float(value["remaining_seconds_at_receipt"]) - 0.1
                        )
                        write_json(directory / MODEL_NAME, value)
                    with self.assertRaises((RuntimeError, ValueError)):
                        self.validate(directory)

    def test_certificate_builder_rejects_writer_value_drift(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            artifacts = {
                RESULT_NAME: self.envelope,
                MODEL_NAME: self.outcome.model_slot_receipt,
                TRANSPORT_NAME: self.outcome.transport_health,
                SEARCH_NAME: self.outcome.search_single_shot_receipt,
            }
            for name, value in artifacts.items():
                write_json(directory / name, value)
            drifted = copy.deepcopy(artifacts)
            drifted[RESULT_NAME]["third_source_result"][
                "candidate_prediction"
            ] += " drift"
            with self.assertRaises(ValueError):
                build_terminal_certificate(
                    directory,
                    self.outcome,
                    validator_manifest_sha256=MANIFEST,
                    expected_artifacts=drifted,
                )

    def test_resealed_result_still_fails_exact_byte_certificate(self) -> None:
        from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256

        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populated_directory(directory)
            value = json.loads(
                (directory / RESULT_NAME).read_text(encoding="utf-8")
            )
            result = value["third_source_result"]
            result["third_source_private_state"]["third_fetch_batches"][0][
                "results"
            ][0]["raw_content"] += " resealed-tamper"
            result.pop("result_sha256")
            result["result_sha256"] = payload_sha256(result)
            value.pop("envelope_payload_sha256")
            value["envelope_payload_sha256"] = payload_sha256(value)
            write_json(directory / RESULT_NAME, value)
            with self.assertRaises(ValueError):
                self.validate(directory)

    def test_manifest_certificate_or_symlink_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populated_directory(directory)
            value = json.loads(
                (directory / RESULT_NAME).read_text(encoding="utf-8")
            )
            with self.assertRaises(ValueError):
                validate_proof_carrying_observed_bundle(
                    value,
                    directory=directory,
                    expected_model_cap=2,
                    expected_validator_manifest_sha256="0" * 64,
                )
            (directory / CERTIFICATE_NAME).unlink()
            (directory / CERTIFICATE_NAME).symlink_to(directory / RESULT_NAME)
            with self.assertRaises(RuntimeError):
                self.validate(directory)

    def test_missing_or_extra_terminal_artifact_fails_closed(self) -> None:
        for mode in ("missing", "extra"):
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
                    directory = Path(temporary)
                    self.populated_directory(directory)
                    if mode == "missing":
                        (directory / SEARCH_NAME).unlink()
                    else:
                        write_json(directory / "unexpected.json", {})
                    with self.assertRaises(RuntimeError):
                        self.validate(directory)

    def test_parent_validation_is_bounded_and_capability_not_forgeable(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populated_directory(directory)
            durations = []
            for _ in range(5):
                started = time.perf_counter()
                self.validate(directory)
                durations.append(time.perf_counter() - started)
            self.assertLess(max(durations), 1.0)
            with self.assertRaises(TypeError):
                ValidatedProofCarryingThirdSourceEnvelope(self.envelope)


if __name__ == "__main__":
    unittest.main()
