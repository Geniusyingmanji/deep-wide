from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24356_explicit_partition_runner import (  # noqa: E402
    build_envelope,
    run_v24356_task,
    validate_envelope,
    validate_observed_bundle,
)
from test_v24342_semantic_active_runtime import TASK, limits  # noqa: E402
from test_v24343_semantic_active_runner import Clock, clients  # noqa: E402


SEED = "b" * 64


class V24356ExplicitPartitionRunnerTests(unittest.TestCase):
    def run_case(self):
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = Clock()
        model, search = clients(output, clock, deadline=300, eligible=True)
        outcome = run_v24356_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        return outcome, model, search

    def test_nine_plus_one_fetch_closes_transport_and_model_equations(self) -> None:
        outcome, _, search = self.run_case()
        envelope = build_envelope(outcome)
        validate_envelope(envelope)
        validate_observed_bundle(
            envelope,
            model_slot_receipt=outcome.model_slot_receipt,
            transport_health=outcome.transport_health,
            expected_cap=2,
        )
        receipt = outcome.result["hidden_verifier_receipt"]
        self.assertEqual(receipt["parent_fetch_calls"], 9)
        self.assertEqual(receipt["hidden_verifier_fetch_calls"], 1)
        self.assertEqual(receipt["total_fetch_calls"], 10)
        self.assertEqual(outcome.transport_health["hard_fetch_helper_calls"], 10)
        self.assertEqual(outcome.model_slot_receipt["acquisitions"], 3)
        self.assertEqual(search.fetch_invocations, 3)

    def test_transport_drift_is_rejected(self) -> None:
        outcome, _, _ = self.run_case()
        drifted = copy.deepcopy(outcome.transport_health)
        drifted["hard_fetch_helper_calls"] += 1
        with self.assertRaises(ValueError):
            validate_observed_bundle(
                build_envelope(outcome),
                model_slot_receipt=outcome.model_slot_receipt,
                transport_health=drifted,
                expected_cap=2,
            )

    def test_private_utility_tamper_fails_envelope(self) -> None:
        outcome, _, _ = self.run_case()
        altered = copy.deepcopy(build_envelope(outcome))
        altered["result"]["private_replay_state"]["utility_catalog"][
            "utility_sets"
        ][0]["proposal_support_set_id"] = "f" * 64
        result = altered["result"]
        result.pop("result_sha256")
        result["result_sha256"] = payload_sha256(result)
        altered.pop("envelope_payload_sha256")
        altered["envelope_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            validate_envelope(altered)

    def test_privileged_input_rejected_before_effect(self) -> None:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        output = Path(temporary.name)
        clock = Clock()
        model, search = clients(output, clock, deadline=300, eligible=True)
        with self.assertRaises(ValueError):
            run_v24356_task(
                {**TASK, "question_type": "forbidden"},
                model=model,
                search=search,
                partition_seed_sha256=SEED,
                limits=limits(),
                monotonic=clock,
            )
        self.assertEqual(model.acquisitions, 0)
        self.assertEqual(search.calls, 0)
        self.assertEqual(search.fetch_calls, 0)


if __name__ == "__main__":
    unittest.main()
