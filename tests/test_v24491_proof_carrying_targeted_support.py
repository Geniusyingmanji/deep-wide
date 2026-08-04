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
from deepwide_agent import v24457_adaptive_entropy_support as adaptive  # noqa: E402
from deepwide_agent import v24490_entropy_targeted_support_search as targeted  # noqa: E402
from deepwide_agent.v24485_execution_scoped_validation_memo import (  # noqa: E402
    ExecutionValidationMemo,
)
from deepwide_agent.v24491_proof_carrying_targeted_support import (  # noqa: E402
    CERTIFICATE_NAME,
    ValidatedProofCarryingTargetedEnvelope,
    aggregate_projections,
    run_memoized_targeted_worker,
    run_single_validation_v24490_task,
    task_projection,
    validate_proof_carrying_targeted_bundle,
    validate_terminal_certificate,
)
from scripts import audit_v24398_failure_observability_build as audit  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24490_entropy_targeted_support_search import clients  # noqa: E402


MANIFEST = hashlib.sha256(b"v24491-test-validator-manifest").hexdigest()
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


class V24491ProofCarryingTargetedSupportTests(unittest.TestCase):
    fixture_root: tempfile.TemporaryDirectory
    raw_surface: dict[str, bytes]
    execution: object

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_root = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        base = Path(cls.fixture_root.name)
        directory = base / "task"
        directory.mkdir()
        clock = AdvancingClock()
        model, search = clients(base, clock)
        cls.execution = run_memoized_targeted_worker(
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
        return validate_proof_carrying_targeted_bundle(
            _read(directory / RESULT_NAME),
            directory=directory,
            expected_model_cap=2,
            expected_validator_manifest_sha256=MANIFEST,
        )

    def test_capability_projection_and_aggregate_match_validated_receipts(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            capability = self.validate(directory)
            projection = task_projection(1, capability)
        support = self.execution.outcome.targeted_result["targeted_support_receipt"]
        self.assertIsInstance(
            capability, ValidatedProofCarryingTargetedEnvelope
        )
        self.assertEqual(projection["targeted_selected_source_count"], 1)
        self.assertEqual(
            projection["decision_credit_total_nats_after_targeted_search"],
            support["decision_credit_total_nats_after_targeted_search"],
        )
        self.assertTrue(projection["passed"])
        aggregate = aggregate_projections([projection], selected=1)
        self.assertEqual(aggregate["safe_change_improvement_tasks"], 1)
        self.assertEqual(aggregate["positive_decision_credit_tasks"], 1)
        self.assertEqual(aggregate["total_additional_model_acquisitions"], 0)

    def test_certificate_binds_exact_bytes_targeted_receipts_and_memo(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            certificate = _read(directory / CERTIFICATE_NAME)
            validated = validate_terminal_certificate(
                certificate,
                directory=directory,
                expected_validator_manifest_sha256=MANIFEST,
            )
        self.assertEqual(validated["validation_memo_receipt"]["total_misses"], 8)
        self.assertGreaterEqual(
            validated["validation_memo_receipt"]["total_hits"], 8
        )
        self.assertEqual(validated["validation_memo_receipt"]["total_mismatches"], 0)
        self.assertTrue(
            validated["parent_v24457_outcome_reused_without_runtime_rerun"]
        )
        self.assertTrue(validated["validation_memo_fail_closed_before_terminal_success"])
        self.assertEqual(
            set(validated["artifact_byte_receipts"]),
            {RESULT_NAME, MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME},
        )

    def test_continuation_is_equivalent_to_legacy_v24490_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            legacy_root = base / "legacy"
            integrated_root = base / "integrated"
            legacy_root.mkdir()
            integrated_root.mkdir()
            legacy_clock = AdvancingClock()
            legacy_model, legacy_search = clients(legacy_root, legacy_clock)
            with ExecutionValidationMemo():
                legacy = targeted.run_v24490_task(
                    TASK,
                    model=legacy_model,
                    search=legacy_search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=legacy_clock,
                )
            integrated_clock = AdvancingClock()
            integrated_model, integrated_search = clients(
                integrated_root, integrated_clock
            )
            with ExecutionValidationMemo():
                integrated = run_single_validation_v24490_task(
                    TASK,
                    model=integrated_model,
                    search=integrated_search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=integrated_clock,
                )._trusted_outcome()
        self.assertEqual(legacy.targeted_result, integrated.targeted_result)
        self.assertEqual(legacy.effect_delta_receipt, integrated.effect_delta_receipt)
        self.assertEqual(legacy.model_slot_receipt, integrated.model_slot_receipt)
        self.assertEqual(legacy.transport_health, integrated.transport_health)
        self.assertEqual(
            legacy.search_single_shot_receipt,
            integrated.search_single_shot_receipt,
        )

    def test_resealed_private_result_tamper_fails_exact_byte_certificate(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            value = _read(directory / RESULT_NAME)
            result = value["targeted_result"]
            result["targeted_private_state"]["targeted_pages"][0]["text"] = (
                "tampered page"
            )
            result.pop("result_sha256")
            result["result_sha256"] = payload_sha256(result)
            value.pop("envelope_payload_sha256")
            value["envelope_payload_sha256"] = payload_sha256(value)
            _write(directory / RESULT_NAME, value)
            with self.assertRaises(ValueError):
                self.validate(directory)

    def test_memo_support_effect_and_terminal_tamper_fail_closed(self) -> None:
        for mode in ("memo", "support", "effect", "terminal"):
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
                    directory = Path(temporary)
                    self.populate(directory)
                    if mode == "terminal":
                        terminal = _read(directory / CHILD_NAME)
                        terminal["stage"] = "runtime_returned"
                        _write(directory / CHILD_NAME, terminal)
                    else:
                        certificate = _read(directory / CERTIFICATE_NAME)
                        if mode == "memo":
                            certificate["validation_memo_receipt"]["total_hits"] = 0
                        elif mode == "support":
                            certificate["targeted_support_receipt"][
                                "decision_credit_total_nats_after_targeted_search"
                            ] = 0
                        else:
                            certificate["targeted_effect_delta_receipt"][
                                "additional_model_acquisitions"
                            ] = 1
                        certificate.pop("certificate_payload_sha256")
                        certificate["certificate_payload_sha256"] = payload_sha256(
                            certificate
                        )
                        _write(directory / CERTIFICATE_NAME, certificate)
                    with self.assertRaises((RuntimeError, ValueError)):
                        self.validate(directory)

    def test_manifest_missing_extra_and_symlink_drift_fail_closed(self) -> None:
        for mode in ("manifest", "missing", "extra", "symlink"):
            with self.subTest(mode=mode):
                with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
                    directory = Path(temporary)
                    self.populate(directory)
                    if mode == "manifest":
                        with self.assertRaises(ValueError):
                            validate_proof_carrying_targeted_bundle(
                                _read(directory / RESULT_NAME),
                                directory=directory,
                                expected_model_cap=2,
                                expected_validator_manifest_sha256="0" * 64,
                            )
                        continue
                    if mode == "missing":
                        (directory / SEARCH_NAME).unlink()
                    elif mode == "extra":
                        _write(directory / "unexpected.json", {})
                    else:
                        (directory / CERTIFICATE_NAME).unlink()
                        (directory / CERTIFICATE_NAME).symlink_to(
                            directory / RESULT_NAME
                        )
                    with self.assertRaises((RuntimeError, ValueError)):
                        self.validate(directory)

    def test_parent_validation_uses_compact_shell_not_semantic_replay(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            with (
                patch.object(
                    targeted,
                    "validate_result",
                    side_effect=AssertionError("targeted semantic replay"),
                ),
                patch.object(
                    adaptive,
                    "validate_envelope",
                    side_effect=AssertionError("adaptive semantic replay"),
                ),
            ):
                capability = self.validate(directory)
        self.assertIsInstance(
            capability, ValidatedProofCarryingTargetedEnvelope
        )

    def test_capability_cannot_be_forged_and_projection_emits_no_private_content(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            result = _read(directory / RESULT_NAME)
            capability = self.validate(directory)
            projection = task_projection(1, capability)
        with self.assertRaises(TypeError):
            ValidatedProofCarryingTargetedEnvelope(result)
        with self.assertRaises(TypeError):
            task_projection(1, result)  # type: ignore[arg-type]
        encoded = json.dumps(projection, ensure_ascii=False, sort_keys=True)
        self.assertNotIn(TASK["question"], encoded)
        self.assertNotIn(TASK["opaque_id"], encoded)
        self.assertNotIn("targeted-alpha-three.example", encoded)
        self.assertNotIn("| Alpha | 2025 |", encoded)
        for prohibited in ("query_vector", "raw_content", "candidate_prediction"):
            self.assertNotIn(prohibited, encoded)

    def test_privileged_input_rejected_before_effect_and_runtime_is_label_blind(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        clock = AdvancingClock()
        model, search = clients(Path(temporary.name), clock)
        with self.assertRaises(ValueError):
            run_single_validation_v24490_task(
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
        accesses, imports = audit._ast_findings(
            Path("src/deepwide_agent/v24491_proof_carrying_targeted_support.py")
        )
        self.assertEqual(accesses, [])
        self.assertEqual(imports, [])

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
