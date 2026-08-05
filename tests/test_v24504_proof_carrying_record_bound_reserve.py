from __future__ import annotations

import copy
import hashlib
import json
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
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    CHILD_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
)
from deepwide_agent import v24497_proof_carrying_targeted_reserve as parent_proof  # noqa: E402
from deepwide_agent import v24503_record_bound_reserve_integration as recovery  # noqa: E402
from deepwide_agent.v24504_proof_carrying_record_bound_reserve import (  # noqa: E402
    CERTIFICATE_NAME,
    ValidatedProofCarryingRecordBoundEnvelope,
    aggregate_projections,
    run_memoized_record_bound_worker,
    run_single_validation_v24503_task,
    task_projection,
    validate_aggregate,
    validate_proof_carrying_record_bound_bundle,
    validate_terminal_certificate,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24503_record_bound_reserve_integration import clients  # noqa: E402
from deepwide_agent.v24485_execution_scoped_validation_memo import (  # noqa: E402
    ExecutionValidationMemo,
)


MANIFEST = hashlib.sha256(b"v24504-test-validator-manifest").hexdigest()
SURFACE = {
    RESULT_NAME,
    MODEL_NAME,
    TRANSPORT_NAME,
    SEARCH_NAME,
    CERTIFICATE_NAME,
    CHILD_NAME,
}


def _read(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(path)
    return value


def _write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


class V24504ProofCarryingRecordBoundReserveTests(unittest.TestCase):
    fixture_root: tempfile.TemporaryDirectory
    raw_surface: dict[str, bytes]

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_root = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        base = Path(cls.fixture_root.name)
        directory = base / "task"
        directory.mkdir()
        clock = AdvancingClock()
        model, search = clients(base, clock, mode="split_support")
        run_memoized_record_bound_worker(
            TASK,
            output_root=base,
            directory=directory,
            model_factory=lambda: model,
            search_factory=lambda: search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
            expected_model_cap=2,
            writer=lambda name, value: _new_json(directory / name, value),
            validator_manifest_sha256=MANIFEST,
        )
        cls.raw_surface = {
            path.name: path.read_bytes() for path in directory.iterdir()
        }
        if set(cls.raw_surface) != SURFACE:
            raise AssertionError(set(cls.raw_surface))

    @classmethod
    def tearDownClass(cls) -> None:
        cls.fixture_root.cleanup()

    def populate(self, directory: Path) -> None:
        for name, raw in self.raw_surface.items():
            (directory / name).write_bytes(raw)

    def validate(self, directory: Path):
        return validate_proof_carrying_record_bound_bundle(
            _read(directory / RESULT_NAME),
            directory=directory,
            expected_model_cap=2,
            expected_validator_manifest_sha256=MANIFEST,
        )

    def test_capability_projection_exposes_record_bound_increment_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            capability = self.validate(directory)
            projection = task_projection(1, capability)
        self.assertIsInstance(
            capability, ValidatedProofCarryingRecordBoundEnvelope
        )
        self.assertGreaterEqual(projection["added_observation_count"], 1)
        self.assertEqual(projection["removed_observation_count"], 0)
        self.assertEqual(projection["safe_change_improvement_count"], 1)
        self.assertGreater(projection["decision_credit_gain_nats"], 0)
        self.assertEqual(
            sum(
                projection[name]
                for name in (
                    "additional_model_requests",
                    "additional_logical_queries",
                    "additional_search_batches",
                    "additional_provider_search_calls",
                    "additional_fetch_calls",
                )
            ),
            0,
        )
        self.assertTrue(projection["passed"])

    def test_aggregate_preserves_gain_regression_and_zero_effect(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            capability = self.validate(directory)
        first = task_projection(1, capability)
        second = task_projection(2, capability)
        value = aggregate_projections([second, first], selected=2)
        self.assertEqual(value["record_bound_added_observation_tasks"], 2)
        self.assertEqual(value["safe_change_improvement_tasks"], 2)
        self.assertEqual(value["positive_decision_credit_gain_tasks"], 2)
        self.assertEqual(value["total_additional_external_effects"], 0)
        self.assertTrue(value["all_zero_additional_effect"])
        validate_aggregate(value)

    def test_certificate_binds_exact_bytes_receipts_and_memo(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            certificate = validate_terminal_certificate(
                _read(directory / CERTIFICATE_NAME),
                directory=directory,
                expected_validator_manifest_sha256=MANIFEST,
            )
        self.assertEqual(certificate["validation_memo_receipt"]["total_misses"], 8)
        self.assertGreaterEqual(
            certificate["validation_memo_receipt"]["total_hits"], 8
        )
        self.assertEqual(
            certificate["validation_memo_receipt"]["total_mismatches"], 0
        )
        self.assertFalse(
            certificate["zero_effect_equivalence_receipt"][
                "external_effect_detected"
            ]
        )

    def test_continuation_is_equivalent_to_v24503_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            legacy_root = base / "legacy"
            integrated_root = base / "integrated"
            legacy_root.mkdir()
            integrated_root.mkdir()
            legacy_clock = AdvancingClock()
            legacy_model, legacy_search = clients(
                legacy_root, legacy_clock, mode="split_support"
            )
            legacy = recovery.run_v24503_task(
                TASK,
                model=legacy_model,
                search=legacy_search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=legacy_clock,
            )
            integrated_clock = AdvancingClock()
            integrated_model, integrated_search = clients(
                integrated_root, integrated_clock, mode="split_support"
            )
            with ExecutionValidationMemo():
                integrated = run_single_validation_v24503_task(
                    TASK,
                    model=integrated_model,
                    search=integrated_search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=integrated_clock,
                )._trusted_outcome()
        self.assertEqual(legacy.record_bound_result, integrated.record_bound_result)
        self.assertEqual(
            legacy.effect_equivalence_receipt,
            integrated.effect_equivalence_receipt,
        )
        self.assertEqual(legacy.model_slot_receipt, integrated.model_slot_receipt)

    def test_parent_validation_uses_compact_shell_not_semantic_replay(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            with (
                patch.object(
                    recovery,
                    "validate_result",
                    side_effect=AssertionError("record semantic replay"),
                ),
                patch.object(
                    parent_proof,
                    "validate_cross_artifacts",
                    side_effect=AssertionError("parent semantic replay"),
                ),
            ):
                capability = self.validate(directory)
        self.assertIsInstance(
            capability, ValidatedProofCarryingRecordBoundEnvelope
        )

    def test_resealed_private_result_tamper_fails_exact_byte_certificate(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            value = _read(directory / RESULT_NAME)
            result = value["record_bound_result"]
            result["record_bound_projection"]["pages"][0]["content"] += " tamper"
            result.pop("result_sha256")
            result["result_sha256"] = payload_sha256(result)
            value.pop("envelope_payload_sha256")
            value["envelope_payload_sha256"] = payload_sha256(value)
            _write(directory / RESULT_NAME, value)
            with self.assertRaises((RuntimeError, ValueError)):
                self.validate(directory)

    def test_certificate_receipt_terminal_and_manifest_tamper_fail_closed(self) -> None:
        for mode in ("record", "effect", "memo", "terminal", "manifest"):
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
                    directory = Path(temporary)
                    self.populate(directory)
                    if mode == "terminal":
                        terminal = _read(directory / CHILD_NAME)
                        terminal["stage"] = "runtime_returned"
                        _write(directory / CHILD_NAME, terminal)
                    elif mode == "manifest":
                        with self.assertRaises(ValueError):
                            validate_proof_carrying_record_bound_bundle(
                                _read(directory / RESULT_NAME),
                                directory=directory,
                                expected_model_cap=2,
                                expected_validator_manifest_sha256="0" * 64,
                            )
                        continue
                    else:
                        certificate = _read(directory / CERTIFICATE_NAME)
                        if mode == "record":
                            certificate["record_bound_receipt"][
                                "added_observation_count"
                            ] += 1
                        elif mode == "effect":
                            certificate["zero_effect_equivalence_receipt"][
                                "external_effect_detected"
                            ] = True
                        else:
                            certificate["validation_memo_receipt"]["total_hits"] = 0
                        certificate.pop("certificate_payload_sha256")
                        certificate["certificate_payload_sha256"] = payload_sha256(
                            certificate
                        )
                        _write(directory / CERTIFICATE_NAME, certificate)
                    with self.assertRaises((RuntimeError, ValueError)):
                        self.validate(directory)

    def test_capability_cannot_be_forged_and_projection_is_content_free(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            result = _read(directory / RESULT_NAME)
            capability = self.validate(directory)
            projection = task_projection(1, capability)
        with self.assertRaises(TypeError):
            ValidatedProofCarryingRecordBoundEnvelope(result)
        with self.assertRaises(TypeError):
            task_projection(1, result)  # type: ignore[arg-type]
        encoded = json.dumps(projection, ensure_ascii=False, sort_keys=True)
        for prohibited in (
            TASK["question"],
            TASK["opaque_id"],
            "targeted-alpha-four.example",
            "query_vector",
            "raw_content",
            "candidate_prediction",
            "sha256",
        ):
            self.assertNotIn(prohibited, encoded)

    def test_privileged_input_rejected_before_effect_and_source_is_label_blind(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        clock = AdvancingClock()
        model, search = clients(base, clock, mode="split_support")
        with self.assertRaises(ValueError):
            run_single_validation_v24503_task(
                {**TASK, "category": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
        self.assertEqual(model.acquisitions, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)
        from scripts import audit_v24398_failure_observability_build as audit

        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24504_proof_carrying_record_bound_reserve.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])

    def test_parent_validation_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            durations = []
            for _ in range(3):
                started = time.perf_counter()
                self.validate(directory)
                durations.append(time.perf_counter() - started)
        self.assertLess(max(durations), 1.0)


if __name__ == "__main__":
    unittest.main()
