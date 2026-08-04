from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import (  # noqa: E402
    child_receipt,
    parent_receipt,
)
from deepwide_agent.v24320_forward_contract import payload_sha256  # noqa: E402
from deepwide_agent.v24391_uncertainty_active_evidence_runner import (  # noqa: E402
    run_v24391_task,
)
from deepwide_agent.v24397_failure_observability import (  # noqa: E402
    aggregate_observations,
    build_failure_snapshot,
    build_task_observation,
    validate_failure_snapshot,
    validate_observation_aggregate,
    validate_task_observation,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24343_semantic_active_runner import Clock  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24391_uncertainty_active_evidence_runner import clients  # noqa: E402


def successful_parent() -> dict:
    return parent_receipt(
        return_code=0,
        timed_out=False,
        elapsed_seconds=4.0,
        subprocess_exception=False,
        child_terminal_receipt_present=True,
        child_terminal_receipt_valid=True,
        result_envelope_present=True,
        result_envelope_valid=True,
        model_receipt_present=True,
        model_receipt_valid=True,
        transport_receipt_present=True,
        transport_receipt_valid=True,
    )


def failed_parent(*, timed_out: bool = False) -> dict:
    return parent_receipt(
        return_code=-15 if timed_out else 1,
        timed_out=timed_out,
        elapsed_seconds=12.0,
        subprocess_exception=False,
        child_terminal_receipt_present=not timed_out,
        child_terminal_receipt_valid=not timed_out,
        result_envelope_present=False,
        result_envelope_valid=False,
        model_receipt_present=not timed_out,
        model_receipt_valid=not timed_out,
        transport_receipt_present=not timed_out,
        transport_receipt_valid=not timed_out,
    )


class V24397FailureObservabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        clock = Clock()
        model, search = clients(Path(cls.temporary.name), clock, deadline=300)
        cls.outcome = run_v24391_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_failure_snapshot_is_content_free_and_binds_partial_receipts(self) -> None:
        outcome = self.outcome
        snapshot = build_failure_snapshot(
            RuntimeError("private detail must not be read"),
            failure_stage="runtime",
            model_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_receipt=outcome.search_single_shot_receipt,
            expected_model_cap=2,
        )
        validate_failure_snapshot(
            snapshot,
            model_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_receipt=outcome.search_single_shot_receipt,
            expected_model_cap=2,
        )
        encoded = repr(snapshot)
        self.assertNotIn("private detail", encoded)
        self.assertEqual(snapshot["exception_type"], "RuntimeError")

    def test_nonzero_failure_preserves_taxonomy_and_partial_effects(self) -> None:
        outcome = self.outcome
        snapshot = build_failure_snapshot(
            RuntimeError("ignored"),
            failure_stage="runtime",
            model_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_receipt=outcome.search_single_shot_receipt,
            expected_model_cap=2,
        )
        child = child_receipt(
            stage="child_exception",
            exception_type="RuntimeError",
            model_receipt_written=True,
            transport_receipt_written=True,
            result_envelope_written=False,
        )
        value = build_task_observation(
            1,
            failed_parent(),
            child=child,
            failure_snapshot=snapshot,
            model_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_receipt=outcome.search_single_shot_receipt,
            expected_model_cap=2,
        )
        validate_task_observation(value)
        self.assertEqual(
            value["parent_taxonomy"], "child_nonzero_with_terminal_receipt"
        )
        self.assertEqual(value["effect_scope"], "failure_partial_receipts")
        self.assertEqual(
            value["model_acquisitions"], outcome.model_slot_receipt["acquisitions"]
        )
        self.assertEqual(
            value["hosted_search_attempts"],
            outcome.transport_health["hosted_search_attempts"],
        )
        self.assertNotEqual(value["deadline_evidence"], "parent_hard_timeout")

    def test_hard_timeout_preserves_unknown_effect_scope(self) -> None:
        value = build_task_observation(
            2,
            failed_parent(timed_out=True),
            child=None,
            failure_snapshot=None,
            model_receipt=None,
            transport_health=None,
            search_receipt=None,
            expected_model_cap=2,
        )
        self.assertEqual(value["parent_taxonomy"], "hard_deadline_timeout")
        self.assertEqual(value["effect_scope"], "unobserved_lower_bound")
        self.assertEqual(value["deadline_evidence"], "parent_hard_timeout")
        self.assertTrue(value["partial_effect_counts_are_lower_bounds"])

    def test_success_requires_terminal_effect_receipts(self) -> None:
        outcome = self.outcome
        value = build_task_observation(
            1,
            successful_parent(),
            child=child_receipt(
                stage="result_envelope_written",
                exception_type=None,
                model_receipt_written=True,
                transport_receipt_written=True,
                result_envelope_written=True,
            ),
            failure_snapshot=None,
            model_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_receipt=outcome.search_single_shot_receipt,
            expected_model_cap=2,
        )
        self.assertEqual(value["parent_taxonomy"], "success")
        self.assertEqual(value["effect_scope"], "successful_terminal_receipts")
        self.assertFalse(value["partial_effect_counts_are_lower_bounds"])

    def test_aggregate_separates_exact_and_lower_bound_counts(self) -> None:
        outcome = self.outcome
        snapshot = build_failure_snapshot(
            RuntimeError("ignored"),
            failure_stage="runtime",
            model_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_receipt=outcome.search_single_shot_receipt,
            expected_model_cap=2,
        )
        observed_failure = build_task_observation(
            1,
            failed_parent(),
            child=child_receipt(
                stage="child_exception",
                exception_type="RuntimeError",
                model_receipt_written=True,
                transport_receipt_written=True,
                result_envelope_written=False,
            ),
            failure_snapshot=snapshot,
            model_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            search_receipt=outcome.search_single_shot_receipt,
            expected_model_cap=2,
        )
        timeout = build_task_observation(
            2,
            failed_parent(timed_out=True),
            child=None,
            failure_snapshot=None,
            model_receipt=None,
            transport_health=None,
            search_receipt=None,
            expected_model_cap=2,
        )
        aggregate = aggregate_observations(
            [observed_failure, timeout], selected=2
        )
        validate_observation_aggregate(aggregate, expected_selected=2)
        self.assertEqual(aggregate["failure_tasks"], 2)
        self.assertEqual(aggregate["failure_snapshot_tasks"], 1)
        self.assertEqual(aggregate["fully_observed_effect_tasks"], 1)
        self.assertEqual(aggregate["unobserved_effect_tasks"], 1)
        self.assertEqual(
            aggregate["model_acquisitions_lower_bound"],
            outcome.model_slot_receipt["acquisitions"],
        )

    def test_resealed_tamper_fails_closed(self) -> None:
        value = build_task_observation(
            1,
            failed_parent(timed_out=True),
            child=None,
            failure_snapshot=None,
            model_receipt=None,
            transport_health=None,
            search_receipt=None,
            expected_model_cap=2,
        )
        altered = copy.deepcopy(value)
        altered["effect_scope"] = "failure_partial_receipts"
        altered.pop("observation_payload_sha256")
        altered["observation_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_task_observation(altered)


if __name__ == "__main__":
    unittest.main()
