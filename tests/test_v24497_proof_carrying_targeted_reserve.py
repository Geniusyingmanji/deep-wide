from __future__ import annotations

import copy
import hashlib
import json
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
from deepwide_agent.v24399_failure_observable_runner import (  # noqa: E402
    CHILD_NAME,
    MODEL_NAME,
    RESULT_NAME,
    SEARCH_NAME,
    TRANSPORT_NAME,
)
from deepwide_agent import v24491_proof_carrying_targeted_support as parent_proof  # noqa: E402
from deepwide_agent import v24496_targeted_reserve_contradiction as reserve  # noqa: E402
from deepwide_agent.v24497_proof_carrying_targeted_reserve import (  # noqa: E402
    CERTIFICATE_NAME,
    ValidatedProofCarryingReserveEnvelope,
    aggregate_projections,
    run_memoized_reserve_worker,
    run_single_validation_v24496_task,
    task_projection,
    validate_aggregate,
    validate_proof_carrying_reserve_bundle,
    validate_terminal_certificate,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24496_targeted_reserve_contradiction import clients  # noqa: E402
from deepwide_agent.v24485_execution_scoped_validation_memo import (  # noqa: E402
    ExecutionValidationMemo,
)


MANIFEST = hashlib.sha256(b"v24497-test-validator-manifest").hexdigest()
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


class V24497ProofCarryingTargetedReserveTests(unittest.TestCase):
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
        model, search = clients(base, clock, mode="support")
        cls.execution = run_memoized_reserve_worker(
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
        return validate_proof_carrying_reserve_bundle(
            _read(directory / RESULT_NAME),
            directory=directory,
            expected_model_cap=2,
            expected_validator_manifest_sha256=MANIFEST,
        )

    def test_capability_projection_exposes_incremental_conversion_only(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            capability = self.validate(directory)
            projection = task_projection(1, capability)
        self.assertIsInstance(capability, ValidatedProofCarryingReserveEnvelope)
        self.assertEqual(projection["reserve_selected_source_count"], 2)
        self.assertEqual(projection["reserve_usable_page_count"], 2)
        self.assertEqual(projection["safe_change_improvement_count"], 1)
        self.assertGreater(projection["decision_credit_gain_nats"], 0)
        self.assertEqual(projection["decision_credit_regression_nats"], 0)
        self.assertTrue(projection["passed"])

    def test_exact_ordinal_aggregate_preserves_conversion_funnel(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            capability = self.validate(directory)
        first = task_projection(1, capability)
        second = task_projection(2, capability)
        value = aggregate_projections([second, first], selected=2)
        self.assertEqual(value["reserve_engaged_tasks"], 2)
        self.assertEqual(value["reserve_usable_page_tasks"], 2)
        self.assertEqual(value["reserve_new_observation_tasks"], 2)
        self.assertEqual(value["safe_change_improvement_tasks"], 2)
        self.assertEqual(value["positive_decision_credit_gain_tasks"], 2)
        self.assertGreater(value["total_decision_credit_gain_nats"], 0)
        validate_aggregate(value)

    def test_aggregate_coordinated_tamper_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            capability = self.validate(directory)
        value = aggregate_projections([task_projection(1, capability)], selected=1)
        for field, replacement in (
            ("reserve_usable_page_tasks", 0),
            ("safe_change_improvement_tasks", 0),
            ("positive_decision_credit_gain_tasks", 0),
            ("total_additional_fetch_effects", 0),
        ):
            changed = copy.deepcopy(value)
            changed[field] = replacement
            with self.assertRaises(ValueError):
                validate_aggregate(changed)

    def test_certificate_binds_exact_bytes_reserve_receipts_and_memo(self) -> None:
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
        self.assertEqual(certificate["validation_memo_receipt"]["total_mismatches"], 0)
        self.assertTrue(certificate["parent_v24490_outcome_reused_without_runtime_rerun"])
        self.assertEqual(
            set(certificate["artifact_byte_receipts"]),
            {RESULT_NAME, MODEL_NAME, TRANSPORT_NAME, SEARCH_NAME},
        )

    def test_continuation_is_equivalent_to_legacy_v24496_entrypoint(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            base = Path(temporary)
            legacy_root = base / "legacy"
            integrated_root = base / "integrated"
            legacy_root.mkdir()
            integrated_root.mkdir()
            legacy_clock = AdvancingClock()
            legacy_model, legacy_search = clients(
                legacy_root, legacy_clock, mode="support"
            )
            legacy = reserve.run_v24496_task(
                TASK,
                model=legacy_model,
                search=legacy_search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=legacy_clock,
            )
            integrated_clock = AdvancingClock()
            integrated_model, integrated_search = clients(
                integrated_root, integrated_clock, mode="support"
            )
            with ExecutionValidationMemo():
                integrated = run_single_validation_v24496_task(
                    TASK,
                    model=integrated_model,
                    search=integrated_search,
                    partition_seed_sha256=SEED,
                    limits=limits(),
                    monotonic=integrated_clock,
                )._trusted_outcome()
        self.assertEqual(legacy.reserve_result, integrated.reserve_result)
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
            result = value["reserve_result"]
            result["reserve_private_state"]["reserve_pages"][0]["content"] += " tamper"
            result.pop("result_sha256")
            result["result_sha256"] = __import__(
                "deepwide_agent.v24323_shared_prefix_cell_entropy",
                fromlist=["payload_sha256"],
            ).payload_sha256(result)
            value.pop("envelope_payload_sha256")
            value["envelope_payload_sha256"] = __import__(
                "deepwide_agent.v24323_shared_prefix_cell_entropy",
                fromlist=["payload_sha256"],
            ).payload_sha256(value)
            _write(directory / RESULT_NAME, value)
            with self.assertRaises(ValueError):
                self.validate(directory)

    def test_certificate_memo_support_effect_and_terminal_tamper_fail_closed(self) -> None:
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
                            certificate["reserve_support_receipt"][
                                "decision_credit_gain_nats"
                            ] = 0
                        else:
                            certificate["reserve_effect_delta_receipt"][
                                "additional_model_acquisitions"
                            ] = 1
                        certificate.pop("certificate_payload_sha256")
                        certificate["certificate_payload_sha256"] = __import__(
                            "deepwide_agent.v24323_shared_prefix_cell_entropy",
                            fromlist=["payload_sha256"],
                        ).payload_sha256(certificate)
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
                            validate_proof_carrying_reserve_bundle(
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
                    reserve,
                    "validate_result",
                    side_effect=AssertionError("reserve semantic replay"),
                ),
                patch.object(
                    parent_proof,
                    "validate_cross_artifacts",
                    side_effect=AssertionError("parent semantic replay"),
                ),
            ):
                capability = self.validate(directory)
        self.assertIsInstance(capability, ValidatedProofCarryingReserveEnvelope)

    def test_capability_cannot_be_forged_and_projection_emits_no_private_content(self) -> None:
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temporary:
            directory = Path(temporary)
            self.populate(directory)
            result = _read(directory / RESULT_NAME)
            capability = self.validate(directory)
            projection = task_projection(1, capability)
        with self.assertRaises(TypeError):
            ValidatedProofCarryingReserveEnvelope(result)
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

    def test_privileged_input_rejected_before_effect_and_runtime_is_label_blind(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        base = Path(temporary.name)
        clock = AdvancingClock()
        model, search = clients(base, clock, mode="support")
        with self.assertRaises(ValueError):
            run_single_validation_v24496_task(
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
            Path("src/deepwide_agent/v24497_proof_carrying_targeted_reserve.py")
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
