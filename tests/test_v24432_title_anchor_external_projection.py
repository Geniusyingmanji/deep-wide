from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24308_child_exit_observability import parent_receipt  # noqa: E402
from deepwide_agent.v24430_title_anchor_effect_runner import (  # noqa: E402
    build_envelope,
    run_v24430_task,
)
from scripts.v24432_title_anchor_external_projection import (  # noqa: E402
    aggregate_tasks,
    local_failure,
    task_checks,
    task_projection,
    validate_aggregate,
    validate_task_projection,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402
from test_v24430_title_anchor_effect_runner import clients  # noqa: E402


GATES = {
    "selected": 16,
    "executor_count": 8,
    "model_slot_cap": 2,
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
    "minimum_combined_observation_tasks": 0,
    "minimum_novel_structured_observation_tasks": 0,
    "minimum_positive_epistemic_tasks": 0,
    "minimum_safe_change_tasks": 0,
    "minimum_epistemic_credit_nats": 0.0,
    "minimum_title_novel_observation_tasks": 1,
    "minimum_title_positive_epistemic_tasks": 1,
    "minimum_title_safe_change_tasks": 1,
    "minimum_title_decision_credit_nats": 1e-12,
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
        clock = AdvancingClock()
        model, search = clients(output, clock)
        outcome = run_v24430_task(
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


class V24432TitleAnchorExternalProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = projected()

    def test_task_projects_title_credit_without_private_content(self) -> None:
        value = self.value
        self.assertTrue(value["passed"])
        self.assertEqual(value["title_unique_anchor_page_count"], 2)
        self.assertEqual(value["title_projection_count"], 2)
        self.assertEqual(value["title_novel_observation_count"], 2)
        self.assertEqual(value["title_safe_change_count"], 1)
        self.assertGreater(value["title_decision_credit_total_nats"], 0)
        self.assertTrue(value["title_effect_equivalence_valid"])
        encoded = json.dumps(value, sort_keys=True)
        for private in ("Alpha", "Beta", "2025", "https://"):
            self.assertNotIn(private, encoded)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))

    def test_title_count_credit_or_attestation_tamper_fails(self) -> None:
        for name in (
            "title_unique_anchor_page_count",
            "title_decision_credit_total_nats",
            "title_effect_equivalence_valid",
        ):
            with self.subTest(name=name):
                altered = copy.deepcopy(self.value)
                if isinstance(altered[name], bool):
                    altered[name] = not altered[name]
                else:
                    altered[name] += 1
                with self.assertRaises(RuntimeError):
                    validate_task_projection(altered)

    def test_aggregate_requires_title_observation_and_decision_credit(self) -> None:
        tasks = [copy.deepcopy(self.value) for _ in range(16)]
        for ordinal, item in enumerate(tasks, start=1):
            item["ordinal"] = ordinal
            item["checks"] = task_checks(item)
            item["passed"] = all(item["checks"].values())
        summary = aggregate_tasks(tasks, 100.0, GATES)
        validate_aggregate(summary, GATES)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["title_novel_observation_tasks"], 16)
        self.assertEqual(summary["title_safe_change_tasks"], 16)
        self.assertEqual(summary["title_decision_credit_tasks"], 16)
        self.assertTrue(summary["all_title_effect_equivalence_attested"])

    def test_failure_as_zero_does_not_claim_title_equivalence(self) -> None:
        tasks = [copy.deepcopy(self.value) for _ in range(16)]
        for ordinal, item in enumerate(tasks, start=1):
            item["ordinal"] = ordinal
            item["checks"] = task_checks(item)
            item["passed"] = all(item["checks"].values())
        tasks[0] = local_failure(1)
        summary = aggregate_tasks(tasks, 100.0, GATES)
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["title_effect_equivalent_tasks"], 15)
        self.assertFalse(
            summary["checks"]["all_title_effect_equivalence_attested"]
        )


if __name__ == "__main__":
    unittest.main()
