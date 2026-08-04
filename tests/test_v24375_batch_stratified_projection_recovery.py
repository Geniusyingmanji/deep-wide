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
from deepwide_agent.v24323_shared_prefix_cell_entropy import payload_sha256  # noqa: E402
from deepwide_agent.v24372_batch_stratified_verifier_runner import (  # noqa: E402
    build_envelope,
    run_v24372_task,
)
from scripts import v24374_batch_stratified_external_gate as frozen  # noqa: E402
from scripts.v24375_batch_stratified_projection_recovery import project_task  # noqa: E402
from test_v24342_semantic_active_runtime import limits  # noqa: E402
from test_v24343_semantic_active_runner import Clock  # noqa: E402
from test_v24367_target_segment_verifier_runtime import SEED, TASK  # noqa: E402
from test_v24372_batch_stratified_verifier_runner import clients  # noqa: E402


def successful_parent() -> dict:
    return parent_receipt(
        return_code=0,
        timed_out=False,
        elapsed_seconds=1.0,
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


class V24375BatchStratifiedProjectionRecoveryTests(unittest.TestCase):
    def envelope(self) -> dict:
        temporary = tempfile.TemporaryDirectory(dir=ROOT / "outputs")
        self.addCleanup(temporary.cleanup)
        clock = Clock()
        model, search = clients(Path(temporary.name), clock, deadline=300)
        outcome = run_v24372_task(
            TASK,
            model=model,
            search=search,
            partition_seed_sha256=SEED,
            limits=limits(),
            monotonic=clock,
        )
        return build_envelope(outcome)

    def test_frozen_projector_depth_bug_and_append_only_recovery(self) -> None:
        envelope = self.envelope()
        with self.assertRaises(RuntimeError):
            frozen._task_projection(1, successful_parent(), envelope)
        projection = project_task(1, successful_parent(), envelope)
        self.assertTrue(projection["passed"])
        self.assertEqual(projection["logical_query_count"], 4)
        self.assertEqual(projection["selected_batch_host_counts"], [5, 5])
        self.assertEqual(projection["proposal_batch_host_counts"], [4, 4])
        self.assertEqual(projection["verifier_batch_host_counts"], [1, 1])
        self.assertEqual(projection["model_requests"], 3)
        self.assertEqual(projection["total_fetch_calls"], 10)

    def test_envelope_tamper_fails_before_projection(self) -> None:
        altered = copy.deepcopy(self.envelope())
        altered["result"]["private_replay_state"]["selected_batch_leads"][0][0][
            "title"
        ] += " tamper"
        result = altered["result"]
        result.pop("result_sha256")
        result["result_sha256"] = payload_sha256(result)
        altered.pop("envelope_payload_sha256")
        altered["envelope_payload_sha256"] = payload_sha256(altered)
        with self.assertRaises(ValueError):
            project_task(1, successful_parent(), altered)

    def test_parent_taxonomy_tamper_fails(self) -> None:
        parent = successful_parent()
        parent["failure_taxonomy"] = "hard_deadline_timeout"
        parent.pop("receipt_payload_sha256")
        parent["receipt_payload_sha256"] = payload_sha256(parent)
        with self.assertRaises(ValueError):
            project_task(1, parent, self.envelope())


if __name__ == "__main__":
    unittest.main()
