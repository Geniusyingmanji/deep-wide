from __future__ import annotations

import concurrent.futures
import copy
import json
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts import v24305_lowcap_neutral_recovery_reliability as target  # noqa: E402


class FakeReal:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, *args, **kwargs):
        del args, kwargs
        self.requests += 1
        self.attempts += 1
        time.sleep(0.02)
        if self.fail:
            raise target.ModelRequestError("synthetic provider failure")
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return SimpleNamespace(text="synthetic nonempty result")


def successful_worker(index: int) -> dict:
    return {
        "worker_index": index,
        "wall_seconds": 1.0,
        "outcome": "recovery_success",
        "failure_type": None,
        "start_barrier_passed": True,
        "model_budget": {
            "limit": 3,
            "effects_by_stage": {
                "plan": 1,
                "synthesis_initial": 1,
                "synthesis_recovery": 1,
                "repair": 0,
            },
            "admitted": 3,
            "logical_provider_requests": 3,
            "provider_attempts": 3,
            "slot_cap": 2,
            "slot_acquisitions": 3,
            "slot_acquisition_counts": [2, 1],
            "slot_wait_seconds": 0.02,
            "slot_max_wait_seconds": 0.01,
            "fourth_provider_effect": False,
        },
        "recovery": {
            "initial_synthesis_model_request_error": True,
            "attempted": True,
            "succeeded": True,
            "provider_failure": False,
            "real_calls": 1,
            "real_successes": 1,
            "real_failures": 0,
        },
        "search": {"calls": 0, "fetch_calls": 0},
    }


class V24305LowCapNeutralRecoveryTests(unittest.TestCase):
    def test_protocol_decouples_eight_executors_from_two_gpt_slots(self) -> None:
        protocol = target.build_protocol(ROOT, now=1, require_pristine=False)
        self.assertEqual(protocol["concurrency_contract"]["executor_workers"], 8)
        self.assertEqual(
            protocol["concurrency_contract"]["shared_global_model_slot_cap"], 2
        )
        self.assertEqual(protocol["budget_contract"]["model_calls_total"], 24)
        self.assertFalse(protocol["authorization"]["benchmark_dev64_launch"])
        self.assertFalse(protocol["authorization"]["exact220_launch"])
        for index in range(1, 9):
            self.assertEqual(set(target.neutral_task(index)), {"opaque_id", "question"})

    def test_eight_workers_reach_real_peak_two_and_all_recover(self) -> None:
        output_root = ROOT / "outputs"
        tracker = target.RecoveryConcurrencyTracker()
        barrier = threading.Barrier(8)
        with tempfile.TemporaryDirectory(dir=output_root) as directory:
            slots = Path(directory)
            for index in range(1, 3):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                workers = list(
                    executor.map(
                        lambda index: target._execute_worker(
                            index,
                            real=FakeReal(),
                            slot_directory=slots,
                            output_root=output_root,
                            tracker=tracker,
                            start_barrier=barrier,
                        ),
                        range(1, 9),
                    )
                )
        snapshot = tracker.snapshot()
        self.assertEqual(snapshot, {"entries": 8, "exits": 8, "active_final": 0, "peak": 2})
        value = target.project(workers, tracker=snapshot, wall_seconds=1.0, now=1)
        self.assertTrue(all(target._checks(value, target.GATES).values()))
        self.assertEqual(value["observed"]["slot_acquisitions"], 24)
        self.assertEqual(value["observed"]["logical_provider_requests"], 24)

    def test_provider_failure_is_content_free_and_fails_gate(self) -> None:
        workers = [successful_worker(index) for index in range(1, 9)]
        workers[-1]["outcome"] = "recovery_provider_failure"
        workers[-1]["failure_type"] = "recovery_provider_model_request_error"
        workers[-1]["recovery"]["succeeded"] = False
        workers[-1]["recovery"]["provider_failure"] = True
        workers[-1]["recovery"]["real_successes"] = 0
        workers[-1]["recovery"]["real_failures"] = 1
        value = target.project(
            workers,
            tracker={"entries": 8, "exits": 8, "active_final": 0, "peak": 2},
            wall_seconds=1.0,
            now=1,
        )
        checks = target._checks(value, target.GATES)
        self.assertFalse(checks["recovery_successes"])
        self.assertFalse(checks["recovery_provider_failures"])
        encoded = json.dumps(value)
        self.assertIsNone(target.OPAQUE.search(encoded))
        self.assertIsNone(target.SECRET.search(encoded))

    def test_projection_tamper_is_recomputed_and_rejected(self) -> None:
        value = target.project(
            [successful_worker(index) for index in range(1, 9)],
            tracker={"entries": 8, "exits": 8, "active_final": 0, "peak": 2},
            wall_seconds=1.0,
            now=1,
        )
        altered = copy.deepcopy(value)
        altered["observed"]["slot_acquisitions"] = 23
        altered.pop("result_payload_sha256")
        altered["result_payload_sha256"] = target.payload_sha256(altered)
        with self.assertRaisesRegex(RuntimeError, "aggregate projection drifted"):
            target.validate_projection(altered)

    def test_decision_claim_scope_never_authorizes_launch_or_sota(self) -> None:
        value = {
            "artifact_version": 1,
            "role": "v24305_lowcap_neutral_recovery_decision",
            "protocol_id": target.PROTOCOL_ID,
            "created_at_unix": 1,
            "status": "lowcap_neutral_reliability_go",
            "passed": True,
            "checks": {"all": True},
            "failed_checks": [],
            "observed": {},
            "provenance": {},
            "claim_scope": {
                "eight_executor_two_gpt_slot_fault_injected_recovery_reliability": True,
                "natural_failure_frequency_measured": False,
                "benchmark_quality_measured": False,
                "causal_quality_improvement_proven": False,
                "sota_supported": False,
            },
            "authorization": {
                "successor_fresh_paired_dev64_design": True,
                "successor_fresh_paired_dev64_launch": False,
                "exact220_launch": False,
                "evaluator_call": False,
                "leaderboard_submission_or_sota_claim": False,
            },
        }
        value["decision_payload_sha256"] = target.payload_sha256(value)
        target.validate_decision(value)


if __name__ == "__main__":
    unittest.main()
