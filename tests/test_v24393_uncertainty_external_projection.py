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

from deepwide_agent.v24308_child_exit_observability import parent_receipt as build_parent_exit_receipt  # noqa: E402
from deepwide_agent.v24391_uncertainty_active_evidence_runner import (  # noqa: E402
    build_envelope,
    run_v24391_task,
)
from scripts.v24393_uncertainty_external_projection import (  # noqa: E402
    aggregate_tasks,
    task_projection,
    validate_aggregate,
    validate_task_projection,
)
from test_v24343_semantic_active_runner import Clock  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24391_uncertainty_active_evidence_runner import clients  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402


GATES = {
    "maximum_batch_wall_seconds": 480.0,
    "maximum_slot_timeouts": 0,
    "maximum_provider_deadline_failures": 0,
    "maximum_hosted_search_deadline_failures": 0,
    "maximum_hard_fetch_deadline_failures": 5,
    "maximum_fetch_helper_failures": 5,
    "maximum_deadline_exhausted_tasks": 0,
    "minimum_exact_proposal_two_batch_tasks": 16,
    "minimum_zero_recursive_split_tasks": 16,
    "minimum_full_proposal_partition_tasks": 12,
    "minimum_proposal_source_count_total": 96,
    "minimum_active_query_tasks": 16,
    "minimum_two_active_source_tasks": 1,
    "minimum_active_page_tasks": 1,
    "minimum_active_observation_tasks": 1,
    "minimum_positive_epistemic_tasks": 1,
    "minimum_safe_change_tasks": 1,
    "minimum_baseline_confirmation_tasks": 0,
    "minimum_epistemic_credit_nats": 1e-12,
}


def parent_receipt() -> dict:
    return build_parent_exit_receipt(
        return_code=0,
        timed_out=False,
        elapsed_seconds=12.5,
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


class V24393UncertaintyExternalProjectionTests(unittest.TestCase):
    def task_value(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = Clock()
        model, search = clients(output, clock, deadline=300)
        outcome = run_v24391_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        return task_projection(1, parent_receipt(), build_envelope(outcome))

    def test_projection_is_content_free_and_closes_mechanism_equations(self) -> None:
        value = self.task_value()
        validate_task_projection(value)
        self.assertTrue(value["passed"])
        self.assertEqual(value["active_logical_query_count"], 1)
        self.assertEqual(value["active_selected_source_count"], 2)
        self.assertEqual(value["safe_change_count"], 1)
        self.assertGreater(value["epistemic_credit_total_nats"], 0)
        self.assertGreater(value["decision_credit_total_nats"], 0)
        encoded = repr(value)
        for marker in ("Alpha", "Beta", "2025", "https://", "task_1123"):
            self.assertNotIn(marker, encoded)

    def test_projection_tamper_is_rejected(self) -> None:
        value = self.task_value()
        for field in (
            "source",
            "posterior",
            "merge",
            "union",
            "transport",
        ):
            with self.subTest(field=field):
                altered = copy.deepcopy(value)
                if field == "source":
                    altered["active_sources_disjoint_from_proposal_sources"] = False
                elif field == "posterior":
                    altered["safe_change_count"] += 1
                elif field == "merge":
                    altered["candidate_changed_cell_count"] += 1
                elif field == "union":
                    altered["final_union_logical_query_count"] += 1
                else:
                    altered["hard_fetch_helper_calls"] += 1
                with self.assertRaises(RuntimeError):
                    validate_task_projection(altered)

    def test_aggregate_separates_structural_validity_from_mechanism_gate(self) -> None:
        one = self.task_value()
        values = []
        for ordinal in range(1, 17):
            item = copy.deepcopy(one)
            item["ordinal"] = ordinal
            validate_task_projection(item)
            values.append(item)
        summary = aggregate_tasks(values, 120.0, GATES)
        validate_aggregate(summary, GATES)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["structurally_passed_tasks"], 16)
        self.assertEqual(summary["safe_change_tasks"], 16)


if __name__ == "__main__":
    unittest.main()
