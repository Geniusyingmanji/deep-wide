from __future__ import annotations

import copy
import hashlib
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from deepwide_agent.v24232_webswarm_total_budget import (  # noqa: E402
    build_cost_vector,
    object_sha256,
)
from deepwide_agent.v24233_webswarm_effect_preauthorization import (  # noqa: E402
    initialize_effect_preauthorization_state,
)
from deepwide_agent.v24234_provider_cost_meter import (  # noqa: E402
    USAGE_NOT_APPLICABLE,
    USAGE_OBSERVED,
    build_provider_meter_contract,
)
from deepwide_agent.v24235_preauthorized_effect_harness import (  # noqa: E402
    ProviderAttemptResult,
    build_provider_attempt_observation,
)
from deepwide_agent.v24242_durable_effect_coordinator import (  # noqa: E402
    DurablePreauthorizedEffectCoordinator,
)
from deepwide_agent.v24243_retry_deadline_scheduler import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ALREADY_RUNNING_CALLBACK_FORCE_CANCELLATION_IMPLEMENTED,
    BACKOFF_PREAUTHORIZED_IN_WALL_RESERVATION_IMPLEMENTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    DETERMINISTIC_CAPPED_BACKOFF_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    INJECTABLE_MONOTONIC_CLOCK_AND_SLEEPER_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    POST_CALLBACK_DEADLINE_CHECK_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    REQUESTS_PER_CALL_TIMEOUT_TREATED_AS_TOTAL_DEADLINE,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    STRICT_RETRY_ADMISSION_DEADLINE_IMPLEMENTED,
    TRUSTED_HARD_TOTAL_WALL_TIMEOUT_IMPLEMENTED,
    RetryDeadlineEffectScheduler,
    RetryDeadlineExecutionError,
    build_retry_deadline_contract,
    validate_retry_deadline_contract,
    validate_retry_deadline_execution_receipt,
    validate_retry_deadline_failure_receipt,
)
from tests.test_v24232_webswarm_total_budget import (  # noqa: E402
    contract,
    guidance,
    ledger,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def cost(**overrides: int) -> dict[str, int]:
    value = {
        "model_calls": 1,
        "model_attempts": 3,
        "search_calls": 0,
        "fetch_calls": 0,
        "other_tool_calls": 0,
        "orchestrator_calls": 0,
        "input_tokens": 1000,
        "output_tokens": 200,
        "wall_milliseconds": 1000,
    }
    value.update(overrides)
    return build_cost_vector(**value)


class VirtualTime:
    def __init__(self, *, start_ns: int = 10_000_000_000) -> None:
        self.now_ns = start_ns
        self.sleep_calls: list[float] = []
        self.lock = threading.Lock()

    def monotonic_ns(self) -> int:
        with self.lock:
            return self.now_ns

    def sleep(self, seconds: float) -> None:
        with self.lock:
            self.sleep_calls.append(seconds)
            self.now_ns += int(round(seconds * 1_000_000_000))

    def advance_ms(self, milliseconds: int) -> None:
        with self.lock:
            self.now_ns += milliseconds * 1_000_000


class V24243RetryDeadlineSchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.root = Path(self.temporary.name).resolve()
        self.guidance_contract = contract()
        self.policy, _, arms, sources = guidance(self.guidance_contract)
        self.arm = next(arm for arm in arms if arm["arm_name"] == "full")
        self.source = sources["full"]
        self.initial = initialize_effect_preauthorization_state(
            initial_budget_ledger=ledger(
                self.guidance_contract,
                self.policy,
                self.arm,
                self.source,
            ),
            **self.shared,
        )
        self.coordinator = DurablePreauthorizedEffectCoordinator.initialize(
            root=self.root,
            journal_namespace_sha256=digest("v24243-journal"),
            initial_state=self.initial,
            **self.coordinator_shared,
        )
        self.time = VirtualTime()
        self.scheduler = RetryDeadlineEffectScheduler(
            coordinator=self.coordinator,
            monotonic_ns=self.time.monotonic_ns,
            sleeper=self.time.sleep,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @property
    def shared(self) -> dict[str, object]:
        return {
            "contract": self.guidance_contract,
            "guidance_policy": self.policy,
            "guidance_arm": self.arm,
            "scouts": self.source["scouts"],
            "probe": self.source["probe"],
            "experience": self.source["experience"],
        }

    @property
    def coordinator_shared(self) -> dict[str, object]:
        return {
            "guidance_contract": self.guidance_contract,
            "guidance_policy": self.policy,
            "guidance_arm": self.arm,
            "scouts": self.source["scouts"],
            "probe": self.source["probe"],
            "experience": self.source["experience"],
        }

    @staticmethod
    def meter(
        *, max_attempts: int = 3, wall_milliseconds: int = 1000
    ) -> dict[str, object]:
        return build_provider_meter_contract(
            provider_kind="azure_responses_model",
            charge_kind="renderer",
            max_attempts=max_attempts,
            reserved_cost=cost(
                model_attempts=max_attempts,
                wall_milliseconds=wall_milliseconds,
            ),
        )

    @staticmethod
    def schedule(
        meter: dict[str, object],
        *,
        total_ms: int = 500,
        window_ms: int = 50,
        initial_ms: int = 20,
        multiplier: int = 2,
        maximum_ms: int = 100,
    ) -> dict[str, object]:
        return build_retry_deadline_contract(
            meter_contract=meter,
            total_deadline_milliseconds=total_ms,
            minimum_attempt_window_milliseconds=window_ms,
            initial_backoff_milliseconds=initial_ms,
            backoff_multiplier=multiplier,
            maximum_backoff_milliseconds=maximum_ms,
        )

    @staticmethod
    def observation(
        invocation: dict[str, object],
        *,
        outcome: str = "success",
        status: int = 200,
    ) -> dict[str, object]:
        return build_provider_attempt_observation(
            invocation=invocation,
            outcome=outcome,
            http_status=status,
            provider_response_ref_sha256=digest(
                f"response-{invocation['attempt_ref_sha256']}"
            ),
            token_usage_state=USAGE_OBSERVED,
            input_tokens=100 if outcome == "success" else 0,
            output_tokens=20 if outcome == "success" else 0,
            provider_tool_usage_state=USAGE_NOT_APPLICABLE,
            provider_tool_calls=None,
            request_body_bytes=128,
            response_body_bytes=256,
        )

    def execute(
        self,
        suffix: str,
        callback,
        *,
        meter=None,
        schedule=None,
        scheduler=None,
    ):
        current_meter = self.meter() if meter is None else meter
        current_schedule = (
            self.schedule(current_meter) if schedule is None else schedule
        )
        active = self.scheduler if scheduler is None else scheduler
        return active.run_effect(
            meter_contract=current_meter,
            scheduler_contract=current_schedule,
            invocation_ref_sha256=digest(f"v24243-invocation-{suffix}"),
            callback=callback,
        )

    def test_contract_freezes_capped_exponential_backoff_and_wall_coverage(self) -> None:
        meter = self.meter(max_attempts=5, wall_milliseconds=2000)
        schedule = self.schedule(
            meter,
            total_ms=1000,
            initial_ms=20,
            multiplier=3,
            maximum_ms=100,
        )
        validate_retry_deadline_contract(schedule, meter_contract=meter)
        self.assertEqual(
            schedule["retry_backoff_schedule_milliseconds"],
            [20, 60, 100, 100],
        )
        self.assertEqual(schedule["maximum_cumulative_backoff_milliseconds"], 280)
        self.assertEqual(schedule["wall_reservation_milliseconds"], 2000)
        self.assertEqual(
            schedule["minimum_required_wall_reservation_milliseconds"], 1004
        )
        self.assertFalse(schedule["callback_force_cancellation_implemented"])
        self.assertTrue(schedule["already_running_callback_may_outlive_deadline"])

    def test_contract_rejects_deadline_or_schedule_outside_reservation(self) -> None:
        meter = self.meter(wall_milliseconds=400)
        with self.assertRaisesRegex(ValueError, "exceeds wall reservation"):
            self.schedule(meter, total_ms=401)
        with self.assertRaisesRegex(ValueError, "cannot fit"):
            self.schedule(
                meter,
                total_ms=100,
                window_ms=50,
                initial_ms=30,
                multiplier=2,
                maximum_ms=60,
            )
        with self.assertRaisesRegex(ValueError, "below initial"):
            self.schedule(meter, initial_ms=30, maximum_ms=20)
        rounding_meter = self.meter(max_attempts=3, wall_milliseconds=500)
        with self.assertRaisesRegex(ValueError, "per-attempt rounding"):
            self.schedule(rounding_meter, total_ms=499)

    def test_success_uses_no_sleep_and_returns_ephemeral_value(self) -> None:
        def callback(invocation):
            self.time.advance_ms(10)
            return ProviderAttemptResult(
                observation=self.observation(invocation),
                value={"private": "ephemeral"},
            )

        result = self.execute("success", callback)
        validate_retry_deadline_execution_receipt(result.receipt)
        self.assertEqual(result.value, {"private": "ephemeral"})
        self.assertEqual(self.time.sleep_calls, [])
        self.assertEqual(result.receipt["attempt_count"], 1)
        self.assertEqual(result.receipt["total_elapsed_nanoseconds"], 10_000_000)
        self.assertNotIn("ephemeral", repr(result.receipt))

    def test_retry_backoff_is_deterministic_cumulative_and_metered(self) -> None:
        indices: list[int] = []

        def callback(invocation):
            indices.append(int(invocation["attempt_index"]))
            self.time.advance_ms(5)
            if invocation["attempt_index"] < 3:
                return ProviderAttemptResult(
                    observation=self.observation(
                        invocation,
                        outcome="retryable_http",
                        status=429,
                    )
                )
            return ProviderAttemptResult(observation=self.observation(invocation))

        result = self.execute("retry", callback)
        validate_retry_deadline_execution_receipt(result.receipt)
        self.assertEqual(indices, [1, 2, 3])
        self.assertEqual(self.time.sleep_calls, [0.02, 0.04])
        self.assertEqual(result.receipt["required_backoff_total_milliseconds"], 60)
        self.assertEqual(result.receipt["observed_backoff_total_nanoseconds"], 60_000_000)
        self.assertEqual(result.receipt["total_elapsed_nanoseconds"], 75_000_000)
        parent_attempts = result.receipt["parent_execution_receipt"]["measurement"][
            "attempts"
        ]
        self.assertEqual(
            [attempt["wall_milliseconds"] for attempt in parent_attempts],
            [1, 1, 1],
        )
        self.assertEqual(result.receipt["parent_measured_wall_milliseconds"], 3)

    def test_real_sleeper_backoff_is_in_parent_wall_measurement(self) -> None:
        meter = self.meter(max_attempts=2, wall_milliseconds=500)
        schedule = self.schedule(
            meter,
            total_ms=400,
            window_ms=50,
            initial_ms=30,
            maximum_ms=30,
        )
        scheduler = RetryDeadlineEffectScheduler(
            coordinator=self.coordinator,
            monotonic_ns=time.monotonic_ns,
            sleeper=time.sleep,
        )

        def callback(invocation):
            if invocation["attempt_index"] == 1:
                return ProviderAttemptResult(
                    observation=self.observation(
                        invocation,
                        outcome="retryable_http",
                        status=429,
                    )
                )
            return ProviderAttemptResult(observation=self.observation(invocation))

        result = self.execute(
            "real-backoff-meter",
            callback,
            meter=meter,
            schedule=schedule,
            scheduler=scheduler,
        )
        validate_retry_deadline_execution_receipt(result.receipt)
        parent_attempts = result.receipt["parent_execution_receipt"]["measurement"][
            "attempts"
        ]
        self.assertGreaterEqual(parent_attempts[1]["wall_milliseconds"], 30)
        self.assertGreaterEqual(result.receipt["parent_measured_wall_milliseconds"], 31)

    def test_deadline_boundary_equal_minimum_window_admits_callback(self) -> None:
        meter = self.meter(max_attempts=1, wall_milliseconds=100)
        schedule = self.schedule(
            meter,
            total_ms=50,
            window_ms=50,
            initial_ms=1,
            maximum_ms=1,
        )
        calls = 0

        def callback(invocation):
            nonlocal calls
            calls += 1
            self.time.advance_ms(1)
            return ProviderAttemptResult(observation=self.observation(invocation))

        result = self.execute(
            "boundary-admit",
            callback,
            meter=meter,
            schedule=schedule,
        )
        self.assertEqual(calls, 1)
        validate_retry_deadline_execution_receipt(result.receipt)

    def test_retry_is_rejected_before_sleep_when_window_cannot_fit(self) -> None:
        meter = self.meter(max_attempts=2, wall_milliseconds=101)
        schedule = self.schedule(
            meter,
            total_ms=100,
            window_ms=40,
            initial_ms=20,
            maximum_ms=20,
        )
        calls = 0

        def callback(invocation):
            nonlocal calls
            calls += 1
            self.time.advance_ms(50)
            return ProviderAttemptResult(
                observation=self.observation(
                    invocation,
                    outcome="retryable_http",
                    status=429,
                )
            )

        with self.assertRaises(RetryDeadlineExecutionError) as caught:
            self.execute(
                "reject-before-sleep",
                callback,
                meter=meter,
                schedule=schedule,
            )
        receipt = caught.exception.receipt
        validate_retry_deadline_failure_receipt(receipt)
        self.assertEqual(receipt["failure_reason"], "deadline_before_backoff")
        self.assertEqual(calls, 1)
        self.assertEqual(self.time.sleep_calls, [])
        self.assertEqual(receipt["provider_callback_started_count"], 1)
        self.assertTrue(receipt["reservation_remains_charged"])
        self.assertFalse(receipt["settlement_durably_committed"])

    def test_sleeper_overshoot_is_rejected_before_second_provider_callback(self) -> None:
        meter = self.meter(max_attempts=2, wall_milliseconds=200)
        schedule = self.schedule(
            meter,
            total_ms=100,
            window_ms=30,
            initial_ms=20,
            maximum_ms=20,
        )
        calls = 0

        def oversleep(seconds: float) -> None:
            self.time.sleep_calls.append(seconds)
            self.time.advance_ms(75)

        scheduler = RetryDeadlineEffectScheduler(
            coordinator=self.coordinator,
            monotonic_ns=self.time.monotonic_ns,
            sleeper=oversleep,
        )

        def callback(invocation):
            nonlocal calls
            calls += 1
            return ProviderAttemptResult(
                observation=self.observation(
                    invocation,
                    outcome="retryable_http",
                    status=429,
                )
            )

        with self.assertRaises(RetryDeadlineExecutionError) as caught:
            self.execute(
                "oversleep",
                callback,
                meter=meter,
                schedule=schedule,
                scheduler=scheduler,
            )
        receipt = caught.exception.receipt
        validate_retry_deadline_failure_receipt(receipt)
        self.assertEqual(
            receipt["failure_reason"], "deadline_before_provider_callback"
        )
        self.assertEqual(calls, 1)
        self.assertEqual(self.time.sleep_calls, [0.02])

    def test_short_sleep_fails_closed_before_provider_callback(self) -> None:
        meter = self.meter(max_attempts=2, wall_milliseconds=200)
        schedule = self.schedule(
            meter,
            total_ms=100,
            window_ms=30,
            initial_ms=20,
            maximum_ms=20,
        )
        calls = 0

        def short_sleep(_seconds: float) -> None:
            self.time.advance_ms(19)

        scheduler = RetryDeadlineEffectScheduler(
            coordinator=self.coordinator,
            monotonic_ns=self.time.monotonic_ns,
            sleeper=short_sleep,
        )

        def callback(invocation):
            nonlocal calls
            calls += 1
            return ProviderAttemptResult(
                observation=self.observation(
                    invocation,
                    outcome="retryable_http",
                    status=429,
                )
            )

        with self.assertRaises(RetryDeadlineExecutionError) as caught:
            self.execute(
                "short-sleep",
                callback,
                meter=meter,
                schedule=schedule,
                scheduler=scheduler,
            )
        validate_retry_deadline_failure_receipt(caught.exception.receipt)
        self.assertEqual(caught.exception.receipt["failure_reason"], "backoff_incomplete")
        self.assertEqual(calls, 1)

    def test_callback_can_outlive_deadline_but_is_rejected_on_return(self) -> None:
        meter = self.meter(max_attempts=1, wall_milliseconds=200)
        schedule = self.schedule(
            meter,
            total_ms=100,
            window_ms=20,
            initial_ms=1,
            maximum_ms=1,
        )
        calls = 0

        def callback(invocation):
            nonlocal calls
            calls += 1
            self.time.advance_ms(101)
            return ProviderAttemptResult(observation=self.observation(invocation))

        with self.assertRaises(RetryDeadlineExecutionError) as caught:
            self.execute(
                "callback-overrun",
                callback,
                meter=meter,
                schedule=schedule,
            )
        receipt = caught.exception.receipt
        validate_retry_deadline_failure_receipt(receipt)
        self.assertEqual(
            receipt["failure_reason"],
            "provider_callback_returned_at_or_after_deadline",
        )
        self.assertEqual(calls, 1)
        self.assertTrue(receipt["already_running_callback_may_outlive_deadline"])
        self.assertFalse(receipt["callback_force_cancellation_implemented"])
        self.assertEqual(receipt["provider_callback_returned_count"], 1)

    def test_parent_postprocessing_overrun_is_detected_after_settlement(self) -> None:
        meter = self.meter(max_attempts=1, wall_milliseconds=200)
        schedule = self.schedule(
            meter,
            total_ms=100,
            window_ms=20,
            initial_ms=1,
            maximum_ms=1,
        )
        original_settle = self.coordinator._settle

        def slow_settle(**kwargs):
            value = original_settle(**kwargs)
            self.time.advance_ms(101)
            return value

        self.coordinator._settle = slow_settle  # type: ignore[method-assign]
        with self.assertRaises(RetryDeadlineExecutionError) as caught:
            self.execute(
                "parent-overrun",
                lambda invocation: ProviderAttemptResult(
                    observation=self.observation(invocation)
                ),
                meter=meter,
                schedule=schedule,
            )
        receipt = caught.exception.receipt
        validate_retry_deadline_failure_receipt(receipt)
        self.assertEqual(receipt["failure_reason"], "parent_returned_at_or_after_deadline")
        self.assertTrue(receipt["settlement_durably_committed"])
        self.assertTrue(receipt["reservation_remains_charged"])

    def test_non_monotonic_clock_fails_closed_and_sanitizes_exception(self) -> None:
        readings = iter([100_000_000, 100_000_000, 99_000_000])
        scheduler = RetryDeadlineEffectScheduler(
            coordinator=self.coordinator,
            monotonic_ns=lambda: next(readings),
            sleeper=lambda _seconds: None,
        )

        def callback(invocation):
            return ProviderAttemptResult(observation=self.observation(invocation))

        with self.assertRaises(RetryDeadlineExecutionError) as caught:
            self.execute("bad-clock", callback, scheduler=scheduler)
        receipt = caught.exception.receipt
        validate_retry_deadline_failure_receipt(receipt)
        self.assertEqual(
            receipt["failure_reason"], "clock_invalid_after_provider_callback"
        )
        self.assertNotIn("next", repr(receipt))

    def test_clock_failure_at_first_callback_entry_fails_closed(self) -> None:
        readings = iter([100_000_000, 99_000_000])
        scheduler = RetryDeadlineEffectScheduler(
            coordinator=self.coordinator,
            monotonic_ns=lambda: next(readings),
            sleeper=lambda _seconds: None,
        )
        calls = 0

        def callback(invocation):
            nonlocal calls
            calls += 1
            return ProviderAttemptResult(observation=self.observation(invocation))

        with self.assertRaises(RetryDeadlineExecutionError) as caught:
            self.execute("entry-clock-failure", callback, scheduler=scheduler)
        validate_retry_deadline_failure_receipt(caught.exception.receipt)
        self.assertEqual(
            caught.exception.receipt["failure_reason"],
            "clock_invalid_during_backoff",
        )
        self.assertEqual(calls, 0)

    def test_invalid_parent_observation_is_reported_as_parent_failure(self) -> None:
        def callback(invocation):
            observation = self.observation(invocation)
            observation["execution_challenge_sha256"] = digest("wrong-challenge")
            return ProviderAttemptResult(observation=observation)

        with self.assertRaises(RetryDeadlineExecutionError) as caught:
            self.execute("invalid-observation", callback)
        validate_retry_deadline_failure_receipt(caught.exception.receipt)
        self.assertEqual(
            caught.exception.receipt["failure_reason"], "parent_execution_failure"
        )
        self.assertEqual(
            caught.exception.receipt["schedule_records"][0]["outcome"], "success"
        )

    def test_callback_exception_is_sanitized_and_remains_charged(self) -> None:
        def callback(_invocation):
            raise RuntimeError("private provider response and credential")

        with self.assertRaises(RetryDeadlineExecutionError) as caught:
            self.execute("callback-exception", callback)
        receipt = caught.exception.receipt
        validate_retry_deadline_failure_receipt(receipt)
        self.assertEqual(receipt["failure_reason"], "provider_callback_exception")
        self.assertNotIn("private provider", repr(receipt))
        self.assertTrue(receipt["reservation_remains_charged"])

    def test_concurrent_effects_keep_independent_virtual_deadlines(self) -> None:
        first_time = VirtualTime(start_ns=1_000_000_000)
        second_time = VirtualTime(start_ns=2_000_000_000)
        first = RetryDeadlineEffectScheduler(
            coordinator=self.coordinator,
            monotonic_ns=first_time.monotonic_ns,
            sleeper=first_time.sleep,
        )
        second = RetryDeadlineEffectScheduler(
            coordinator=self.coordinator,
            monotonic_ns=second_time.monotonic_ns,
            sleeper=second_time.sleep,
        )
        barrier = threading.Barrier(2)

        def run(label: str, clock: VirtualTime, scheduler):
            def callback(invocation):
                barrier.wait(timeout=10)
                clock.advance_ms(5)
                return ProviderAttemptResult(observation=self.observation(invocation))

            return self.execute(label, callback, scheduler=scheduler)

        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(run, "parallel-a", first_time, first)
            b = pool.submit(run, "parallel-b", second_time, second)
            result_a = a.result(timeout=20)
            result_b = b.result(timeout=20)
        validate_retry_deadline_execution_receipt(result_a.receipt)
        validate_retry_deadline_execution_receipt(result_b.receipt)
        self.assertEqual(self.coordinator.journal.load()["settled_permit_count"], 2)

    def test_receipt_tamper_and_reseal_fail_closed(self) -> None:
        result = self.execute(
            "tamper",
            lambda invocation: ProviderAttemptResult(
                observation=self.observation(invocation)
            ),
        )
        tampered = copy.deepcopy(result.receipt)
        tampered["schedule_records"][0]["remaining_before_provider_callback_nanoseconds"] += 1
        tampered.pop("execution_receipt_sha256")
        tampered["execution_receipt_sha256"] = object_sha256(tampered)
        with self.assertRaisesRegex(ValueError, "schedule record"):
            validate_retry_deadline_execution_receipt(tampered)

    def test_capability_flags_are_exact_and_fail_closed(self) -> None:
        for flag in (
            STRICT_RETRY_ADMISSION_DEADLINE_IMPLEMENTED,
            DETERMINISTIC_CAPPED_BACKOFF_IMPLEMENTED,
            BACKOFF_PREAUTHORIZED_IN_WALL_RESERVATION_IMPLEMENTED,
            INJECTABLE_MONOTONIC_CLOCK_AND_SLEEPER_IMPLEMENTED,
            POST_CALLBACK_DEADLINE_CHECK_IMPLEMENTED,
        ):
            self.assertTrue(flag)
        for flag in (
            ALREADY_RUNNING_CALLBACK_FORCE_CANCELLATION_IMPLEMENTED,
            TRUSTED_HARD_TOTAL_WALL_TIMEOUT_IMPLEMENTED,
            REQUESTS_PER_CALL_TIMEOUT_TREATED_AS_TOTAL_DEADLINE,
            PRODUCTION_PACKAGE_AUTHORIZED,
            ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            EXTERNAL_SIDE_EFFECT_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
        ):
            self.assertFalse(flag)


if __name__ == "__main__":
    unittest.main()
