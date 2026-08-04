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

from deepwide_agent.v24308_child_exit_observability import parent_receipt  # noqa: E402
from deepwide_agent.v24409_structured_uncertainty_runner import (  # noqa: E402
    build_envelope,
    run_v24409_task,
)
from scripts.v24411_structured_uncertainty_external_projection import (  # noqa: E402
    aggregate_tasks,
    local_failure,
    task_projection,
    validate_aggregate,
    validate_task_projection,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24343_semantic_active_runner import Clock  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24409_structured_uncertainty_runner import clients  # noqa: E402


GATES = {
    "maximum_batch_wall_seconds": 480.0,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hosted_search_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 5,
    "maximum_fetch_helper_failures": 5,
    "maximum_deadline_exhausted_tasks": 0,
    "minimum_full_proposal_partition_tasks": 12,
    "minimum_two_active_source_tasks": 8,
    "minimum_active_page_tasks": 8,
    "minimum_combined_observation_tasks": 1,
    "minimum_novel_structured_observation_tasks": 1,
    "minimum_positive_epistemic_tasks": 1,
    "minimum_safe_change_tasks": 1,
    "minimum_epistemic_credit_nats": 1e-12,
}


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


def projected(ordinal: int = 1) -> dict:
    temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
    try:
        output = Path(temporary.name)
        clock = Clock()
        model, search = clients(output, clock)
        outcome = run_v24409_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        return task_projection(ordinal, successful_parent(), build_envelope(outcome))
    finally:
        temporary.cleanup()


class V24411StructuredUncertaintyExternalProjectionTests(unittest.TestCase):
    def test_private_envelope_projects_content_free_structured_counts(self) -> None:
        value = projected()
        self.assertTrue(value["passed"])
        self.assertEqual(value["legacy_active_observation_count"], 0)
        self.assertEqual(value["novel_structured_observation_count"], 2)
        self.assertEqual(value["combined_active_observation_count"], 2)
        self.assertEqual(value["recovered_safe_change_count"], 1)
        self.assertGreater(value["recovered_epistemic_credit_total_nats"], 0)
        encoded = repr(value)
        for private in ("Alpha", "Beta", "2025", "https://", "task_"):
            self.assertNotIn(private, encoded)

    def test_projection_and_parent_tamper_fail_closed(self) -> None:
        value = projected()
        for field in ("count", "effect", "parent"):
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                if field == "count":
                    altered["combined_active_observation_count"] += 1
                elif field == "effect":
                    altered["additional_fetch_calls"] = 1
                else:
                    altered["parent_taxonomy"] = "hard_deadline_timeout"
                with self.assertRaises(RuntimeError):
                    validate_task_projection(altered)

    def test_aggregate_requires_structured_information_gain_and_safe_change(self) -> None:
        tasks = [projected(index) for index in range(1, 17)]
        summary = aggregate_tasks(tasks, 100.0, GATES)
        validate_aggregate(summary, GATES)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["novel_structured_observation_tasks"], 16)
        self.assertEqual(summary["safe_change_tasks"], 16)
        self.assertTrue(summary["all_zero_additional_effects"])

    def test_failure_as_zero_is_structurally_valid_but_gate_fails(self) -> None:
        tasks = [local_failure(index) for index in range(1, 17)]
        summary = aggregate_tasks(tasks, 100.0, GATES)
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["terminal_success_tasks"], 0)
        self.assertEqual(summary["epistemic_credit_total_nats"], 0)


if __name__ == "__main__":
    unittest.main()
