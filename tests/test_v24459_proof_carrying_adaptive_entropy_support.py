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

from deepwide_agent.v24308_child_exit_observability import child_receipt  # noqa: E402
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    CHILD_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
)
from deepwide_agent.v24457_adaptive_entropy_support import (  # noqa: E402
    build_envelope,
    run_v24457_task,
)
from deepwide_agent.v24459_proof_carrying_adaptive_entropy_support import (  # noqa: E402
    CERTIFICATE_NAME,
    ValidatedProofCarryingAdaptiveEnvelope,
    build_terminal_certificate,
    validate_proof_carrying_adaptive_bundle,
)
from deepwide_agent.v24460_adaptive_capability_projection import (  # noqa: E402
    aggregate_projections,
    task_projection,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24447_third_source_entropy_to_decision import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24459-test-validator-manifest").hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class V24459ProofCarryingAdaptiveEntropySupportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_root = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = AdvancingClock()
        model, search = clients(Path(cls.fixture_root.name), clock, third=True)
        cls.outcome = run_v24457_task(
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

    def populate(self, directory: Path) -> None:
        artifacts = {
            RESULT_NAME: self.envelope,
            MODEL_NAME: self.outcome.model_slot_receipt,
            TRANSPORT_NAME: self.outcome.transport_health,
            SEARCH_NAME: self.outcome.search_single_shot_receipt,
        }
        for name, value in artifacts.items():
            write_json(directory / name, value)
        certificate = build_terminal_certificate(
            directory,
            self.outcome,
            validator_manifest_sha256=MANIFEST,
            expected_artifacts=artifacts,
        )
        write_json(directory / CERTIFICATE_NAME, certificate)
        write_json(
            directory / CHILD_NAME,
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
        return validate_proof_carrying_adaptive_bundle(
            value,
            directory=directory,
            expected_model_cap=2,
            expected_validator_manifest_sha256=MANIFEST,
        )

    def test_capability_projection_matches_validated_receipts(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            capability = self.validate(directory)
            projected = task_projection(1, capability)
            receipt = self.outcome.adaptive_result["adaptive_support_receipt"]
            self.assertIsInstance(capability, ValidatedProofCarryingAdaptiveEnvelope)
            expected_stop = {
                "lead_pool_exhausted": "pool_exhausted"
            }.get(receipt["stop_reason"], receipt["stop_reason"])
            self.assertEqual(projected["adaptive_stop_reason"], expected_stop)
            self.assertEqual(
                projected["adaptive_final_decision_credit_total_nats"],
                receipt["final_decision_credit_total_nats"],
            )
            self.assertTrue(projected["passed"])
            self.assertEqual(
                aggregate_projections([projected], selected=1)["selected"], 1
            )

    def test_public_projection_keys_contain_no_lead_page_or_hash(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            projected = task_projection(1, self.validate(directory))

        observed = json.dumps(projected, ensure_ascii=False, sort_keys=True).casefold()
        for prohibited in ("lead", "page", "hash", "sha256"):
            self.assertNotIn(prohibited, observed)

    def test_raw_mapping_cannot_forge_capability(self) -> None:
        with self.assertRaises(TypeError):
            ValidatedProofCarryingAdaptiveEnvelope(self.envelope)
        with self.assertRaises(TypeError):
            task_projection(1, self.envelope)  # type: ignore[arg-type]

    def test_private_result_or_terminal_receipt_tamper_fails_closed(self) -> None:
        for mode in ("private_result", "model_receipt", "child_terminal"):
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
                    directory = Path(temporary)
                    self.populate(directory)
                    target = directory / {
                        "private_result": RESULT_NAME,
                        "model_receipt": MODEL_NAME,
                        "child_terminal": CHILD_NAME,
                    }[mode]
                    value = json.loads(target.read_text(encoding="utf-8"))
                    if mode == "private_result":
                        value["adaptive_result"]["adaptive_private_state"][
                            "stop_reason"
                        ] = "budget_exhausted"
                    elif mode == "model_receipt":
                        value["remaining_seconds_at_receipt"] = max(
                            0.0,
                            float(value["remaining_seconds_at_receipt"]) - 0.1,
                        )
                    else:
                        value["stage"] = "runtime_returned"
                    write_json(target, value)
                    with self.assertRaises((RuntimeError, ValueError)):
                        self.validate(directory)

    def test_resealed_private_tamper_fails_exact_byte_certificate(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            value = json.loads((directory / RESULT_NAME).read_text(encoding="utf-8"))
            result = value["adaptive_result"]
            result["adaptive_private_state"]["stop_reason"] = "budget_exhausted"
            result.pop("result_sha256")
            result["result_sha256"] = payload_sha256(result)
            value.pop("envelope_payload_sha256")
            value["envelope_payload_sha256"] = payload_sha256(value)
            write_json(directory / RESULT_NAME, value)
            with self.assertRaises(ValueError):
                self.validate(directory)

    def test_manifest_missing_extra_and_symlink_drift_fail_closed(self) -> None:
        for mode in ("manifest", "missing", "extra", "symlink"):
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
                    directory = Path(temporary)
                    self.populate(directory)
                    if mode == "manifest":
                        value = json.loads(
                            (directory / RESULT_NAME).read_text(encoding="utf-8")
                        )
                        with self.assertRaises(ValueError):
                            validate_proof_carrying_adaptive_bundle(
                                value,
                                directory=directory,
                                expected_model_cap=2,
                                expected_validator_manifest_sha256="0" * 64,
                            )
                        continue
                    if mode == "missing":
                        (directory / SEARCH_NAME).unlink()
                    elif mode == "extra":
                        write_json(directory / "unexpected.json", {})
                    else:
                        (directory / CERTIFICATE_NAME).unlink()
                        (directory / CERTIFICATE_NAME).symlink_to(
                            directory / RESULT_NAME
                        )
                    with self.assertRaises((RuntimeError, ValueError)):
                        self.validate(directory)

    def test_parent_validation_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            durations = []
            for _ in range(5):
                started = time.perf_counter()
                self.validate(directory)
                durations.append(time.perf_counter() - started)
            self.assertLess(max(durations), 1.0)


if __name__ == "__main__":
    unittest.main()
