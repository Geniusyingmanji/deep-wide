from __future__ import annotations

import concurrent.futures
import copy
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from deepwide_agent.v24263_global_model_limiter import (  # noqa: E402
    GlobalModelSlotLimiter,
    POOL_ID,
    validate_receipt,
)
from scripts import v24301_neutral_concurrent_synthesis_recovery as target  # noqa: E402


TABLE = (
    "| Name | Version | Date |\n"
    "| --- | --- | --- |\n"
    "| NeutralWidget | 1.0 | 2026-08-03 |"
)


class Real:
    def __init__(self) -> None:
        self.requests = self.attempts = 0
        self.input_tokens = self.output_tokens = self.total_tokens = 0

    def complete(self, *args, **kwargs):
        del args, kwargs
        self.requests += 1
        self.attempts += 1
        self.input_tokens += 10
        self.output_tokens += 5
        self.total_tokens += 15
        return SimpleNamespace(text=TABLE)


def successful_worker(index: int) -> dict:
    return {
        "worker_index": index,
        "wall_seconds": 1.0,
        "completion_kind": "primary",
        "model_budget": {
            "limit": 3,
            "admitted": 3,
            "logical_provider_requests": 3,
            "provider_attempts": 3,
            "slot_acquisitions": 3,
            "slot_acquisition_counts": [3 if slot == index - 1 else 0 for slot in range(8)],
            "slot_wait_seconds": 0.0,
            "fourth_provider_effect": False,
        },
        "recovery": {
            "effects_by_stage": {
                "plan": 1,
                "synthesis_initial": 1,
                "synthesis_recovery": 1,
                "repair": 0,
            },
            "total_effects_admitted": 3,
            "initial_synthesis_model_request_error": True,
            "recovery_attempted": True,
            "recovery_succeeded": True,
            "recovery_model_request_error": False,
            "real_recovery_requests": 1,
        },
        "shared_slot_barrier": {"arrivals": 1, "passes": 1, "failures": 0},
        "search": {"calls": 0, "fetch_calls": 0},
    }


class V24301NeutralConcurrentSynthesisRecoveryTests(unittest.TestCase):
    def test_protocol_is_neutral_label_blind_and_unauthorized(self) -> None:
        protocol = target.build_protocol(ROOT, now=1, require_pristine=False)
        self.assertEqual(protocol["task_contract"]["task_count"], 8)
        self.assertEqual(protocol["concurrency_contract"]["shared_global_model_slot_cap"], 8)
        self.assertEqual(protocol["budget_contract"]["model_calls_total"], 24)
        self.assertEqual(set(target.neutral_task(1)), {"opaque_id", "question"})
        self.assertFalse(protocol["authorization"]["benchmark_dev64_launch"])
        self.assertFalse(protocol["authorization"]["exact220_launch"])
        self.assertFalse(protocol["authorization"]["evaluator_call"])

    def test_barrier_is_reached_while_each_worker_holds_shared_slot(self) -> None:
        output_root = ROOT / "outputs"
        barrier = threading.Barrier(2)
        with tempfile.TemporaryDirectory(dir=output_root) as directory:
            slots = Path(directory)
            for index in range(1, 3):
                (slots / f"slot_{index:02d}.lock").write_text("{}\n", encoding="utf-8")
            injected = [
                target.ConcurrentNeutralFaultInjectedModel(Real(), barrier)
                for _ in range(2)
            ]
            models = [
                GlobalModelSlotLimiter(
                    inner,
                    slot_directory=slots,
                    output_root=output_root,
                    slot_cap=2,
                    pool_id=POOL_ID,
                )
                for inner in injected
            ]
            for model in models:
                self.assertTrue(model.complete("", "", max_output_tokens=1).text)
                with self.assertRaises(target.ModelRequestError):
                    model.complete("", "", max_output_tokens=1)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                values = list(
                    executor.map(
                        lambda model: model.complete("", "", max_output_tokens=1),
                        models,
                    )
                )
            self.assertTrue(all(value.text == TABLE for value in values))
            self.assertEqual(sum(inner.shared_slot_barrier_passes for inner in injected), 2)
            for model in models:
                receipt = validate_receipt(
                    model.receipt(), expected_cap=2, expected_acquisitions=3
                )
                self.assertEqual(receipt["acquisitions"], 3)

    def test_projection_and_decision_require_all_twenty_four_effects(self) -> None:
        workers = [successful_worker(index) for index in range(1, 9)]
        value = target.project(
            workers, wall_seconds=2.0, barrier_broken=False, now=1
        )
        target.validate_projection(value)
        checks = target._checks(value, target.GATES)
        self.assertTrue(all(checks.values()))
        self.assertEqual(value["observed"]["logical_provider_requests"], 24)
        self.assertEqual(value["observed"]["slot_acquisitions"], 24)
        self.assertEqual(value["observed"]["shared_slot_barrier_participants"], 8)
        encoded = json.dumps(value)
        for literal in target.CONTENT_LITERALS:
            self.assertNotIn(literal, encoded)

    def test_resealed_worker_tamper_is_recomputed_and_rejected(self) -> None:
        value = target.project(
            [successful_worker(index) for index in range(1, 9)],
            wall_seconds=2.0,
            barrier_broken=False,
            now=1,
        )
        altered = copy.deepcopy(value)
        altered["observed"]["slot_acquisitions"] = 23
        unsigned = dict(altered)
        unsigned.pop("result_payload_sha256")
        altered["result_payload_sha256"] = target.payload_sha256(unsigned)
        with self.assertRaises(RuntimeError):
            target.validate_projection(altered)

    def test_gate_fails_if_one_recovery_is_not_primary(self) -> None:
        workers = [successful_worker(index) for index in range(1, 9)]
        workers[-1]["completion_kind"] = "best_effort_fallback"
        workers[-1]["recovery"]["recovery_succeeded"] = False
        workers[-1]["recovery"]["recovery_model_request_error"] = True
        workers[-1]["recovery"]["real_recovery_requests"] = 0
        value = target.project(
            workers, wall_seconds=2.0, barrier_broken=False, now=1
        )
        checks = target._checks(value, target.GATES)
        self.assertFalse(checks["primary_tasks"])
        self.assertFalse(checks["recovery_successes"])
        self.assertFalse(checks["recovery_provider_failures"])


if __name__ == "__main__":
    unittest.main()
