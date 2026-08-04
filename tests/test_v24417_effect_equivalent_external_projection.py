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
from deepwide_agent.v24415_effect_equivalent_structured_runner import (  # noqa: E402
    build_envelope,
    run_v24415_task,
)
from scripts.v24417_effect_equivalent_external_projection import (  # noqa: E402
    aggregate_tasks,
    local_failure,
    task_projection,
    validate_aggregate,
    validate_task_projection,
)
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24390_uncertainty_active_evidence_runtime import SEED, TASK  # noqa: E402
from test_v24411_structured_uncertainty_external_projection import GATES  # noqa: E402
from test_v24412_receipt_snapshot_diagnosis import (  # noqa: E402
    AdvancingClock,
    clients,
)


EQUIVALENCE_ONLY_GATES = {
    **GATES,
    # The advancing-clock fixture intentionally exercises the legacy active
    # observation path and has no structured-label projection.  Keep the
    # production external gate unchanged while isolating effect attestation.
    "minimum_novel_structured_observation_tasks": 0,
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
        outcome = run_v24415_task(
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


class V24417EffectEquivalentExternalProjectionTests(unittest.TestCase):
    def test_advancing_clock_envelope_projects_effect_attestation(self) -> None:
        value = projected()
        self.assertTrue(value["passed"])
        self.assertTrue(value["effect_equivalence_valid"])
        self.assertTrue(value["model_remaining_seconds_nonincreasing"])
        self.assertTrue(value["model_deadline_state_monotonic"])
        self.assertTrue(value["transport_deadline_state_monotonic"])
        encoded = repr(value)
        for private in ("Alpha", "Beta", "2025", "https://", "task_"):
            self.assertNotIn(private, encoded)

    def test_attestation_tamper_fails_projection(self) -> None:
        value = projected()
        for name in (
            "effect_equivalence_valid",
            "model_remaining_seconds_nonincreasing",
            "model_deadline_state_monotonic",
            "transport_deadline_state_monotonic",
        ):
            with self.subTest(name=name):
                altered = copy.deepcopy(value)
                altered[name] = False
                with self.assertRaises(RuntimeError):
                    validate_task_projection(altered)

    def test_aggregate_requires_every_effect_attestation(self) -> None:
        tasks = [projected(index) for index in range(1, 17)]
        summary = aggregate_tasks(tasks, 100.0, EQUIVALENCE_ONLY_GATES)
        validate_aggregate(summary, EQUIVALENCE_ONLY_GATES)
        self.assertTrue(summary["passed"])
        self.assertEqual(summary["effect_equivalent_tasks"], 16)
        self.assertTrue(summary["all_effect_equivalence_attested"])

    def test_failure_as_zero_does_not_claim_equivalence(self) -> None:
        tasks = [projected(index) for index in range(1, 17)]
        tasks[0] = local_failure(1)
        summary = aggregate_tasks(tasks, 100.0, EQUIVALENCE_ONLY_GATES)
        self.assertFalse(summary["passed"])
        self.assertEqual(summary["effect_equivalent_tasks"], 15)
        self.assertFalse(summary["checks"]["all_effect_equivalence_attested"])


if __name__ == "__main__":
    unittest.main()
