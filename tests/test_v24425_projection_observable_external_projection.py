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
from deepwide_agent.v24423_projection_observable_runner import (  # noqa: E402
    build_envelope,
    run_v24423_task,
)
from scripts.v24425_projection_observable_external_projection import (  # noqa: E402
    aggregate_tasks,
    local_failure,
    task_projection,
    validate_aggregate,
    validate_task_projection,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24409_structured_uncertainty_runner import clients  # noqa: E402
from test_v24411_structured_uncertainty_external_projection import GATES  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import AdvancingClock  # noqa: E402


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
        outcome = run_v24423_task(
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


class V24425ProjectionObservableExternalProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.value = projected()

    def test_task_projects_only_counts_and_conserves_reasons(self) -> None:
        value = self.value
        self.assertTrue(value["passed"])
        self.assertTrue(value["projection_observability_valid"])
        self.assertEqual(
            value["projection_page_count"], value["active_page_count"]
        )
        reason_total = sum(
            value[name]
            for name in (
                "projection_unsupported_column_kind_pairs",
                "projection_exact_structured_entity_anchor_absent_pairs",
                "projection_exact_label_absent_in_entity_scope_pairs",
                "projection_exact_label_value_year_absent_pairs",
                "projection_emitted_pairs",
            )
        )
        self.assertEqual(reason_total, value["projection_page_target_pair_count"])
        encoded = json.dumps(value, sort_keys=True)
        for private in ("Alpha", "Beta", "2025", "https://"):
            self.assertNotIn(private, encoded)
        self.assertIsNone(re.search(r"task_[0-9a-f]{24}", encoded))

    def test_task_count_or_attestation_tamper_fails(self) -> None:
        for name in (
            "projection_page_count",
            "projection_exact_label_value_year_absent_pairs",
            "projection_reason_partition_exact",
        ):
            with self.subTest(name=name):
                altered = copy.deepcopy(self.value)
                if isinstance(altered[name], bool):
                    altered[name] = not altered[name]
                else:
                    altered[name] += 1
                with self.assertRaises(RuntimeError):
                    validate_task_projection(altered)

    def test_aggregate_conserves_every_reason_and_attestation(self) -> None:
        tasks = [copy.deepcopy(self.value) for _ in range(16)]
        for ordinal, item in enumerate(tasks, start=1):
            item["ordinal"] = ordinal
            item["checks"] = {
                **item["checks"],
            }
            from scripts.v24425_projection_observable_external_projection import (
                task_checks,
            )

            item["checks"] = task_checks(item)
            item["passed"] = all(item["checks"].values())
        summary = aggregate_tasks(tasks, 100.0, GATES)
        validate_aggregate(summary, GATES)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["projection_observable_tasks"], 16)
        self.assertEqual(
            summary["projection_total_pages"], summary["active_pages"]
        )
        self.assertTrue(summary["all_projection_observability_attested"])

    def test_failure_as_zero_does_not_claim_observability(self) -> None:
        tasks = [copy.deepcopy(self.value) for _ in range(16)]
        from scripts.v24425_projection_observable_external_projection import task_checks

        for ordinal, item in enumerate(tasks, start=1):
            item["ordinal"] = ordinal
            item["checks"] = task_checks(item)
            item["passed"] = all(item["checks"].values())
        tasks[0] = local_failure(1)
        summary = aggregate_tasks(tasks, 100.0, GATES)
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["projection_observable_tasks"], 15)
        self.assertFalse(
            summary["checks"]["all_projection_observability_attested"]
        )


if __name__ == "__main__":
    unittest.main()
