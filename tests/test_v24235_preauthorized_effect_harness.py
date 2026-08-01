from __future__ import annotations

import copy
import hashlib
import sys
import threading
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
    validate_effect_preauthorization_state,
)
from deepwide_agent.v24234_provider_cost_meter import (  # noqa: E402
    USAGE_NOT_APPLICABLE,
    USAGE_OBSERVED,
    USAGE_UNAVAILABLE,
    build_provider_meter_contract,
)
from deepwide_agent.v24235_preauthorized_effect_harness import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLBACK_CONCURRENCY_BETWEEN_PERMITS_IMPLEMENTED,
    CALLBACK_TIMEOUT_IMPLEMENTED,
    CALLER_SUPPLIED_EFFECT_CALLBACK_INVOCATION_AUTHORIZED,
    CRASH_DURABLE_JOURNAL_IMPLEMENTED,
    CROSS_PROCESS_COMPARE_AND_SWAP_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
    RETRY_BACKOFF_IMPLEMENTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    EffectExecutionResult,
    PreauthorizedEffectExecutionError,
    PreauthorizedEffectHarness,
    ProviderAttemptResult,
    build_provider_attempt_observation,
    validate_effect_execution_receipt,
    validate_effect_failure_receipt,
)
from deepwide_agent.v24233_webswarm_effect_preauthorization import (  # noqa: E402
    initialize_effect_preauthorization_state,
)
from tests.test_v24232_webswarm_total_budget import (  # noqa: E402
    contract as guidance_contract,
    guidance,
    ledger,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def cost(**overrides: int) -> dict[str, int]:
    value = {
        "model_calls": 0,
        "model_attempts": 0,
        "search_calls": 0,
        "fetch_calls": 0,
        "other_tool_calls": 0,
        "orchestrator_calls": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "wall_milliseconds": 30_000,
    }
    value.update(overrides)
    return build_cost_vector(**value)


class V24235PreauthorizedEffectHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = guidance_contract()
        self.policy, _, self.arms, self.sources = guidance(self.contract)
        self.arm = next(arm for arm in self.arms if arm["arm_name"] == "full")
        self.source = self.sources["full"]
        initial_ledger = ledger(
            self.contract,
            self.policy,
            self.arm,
            self.source,
        )
        initial_state = initialize_effect_preauthorization_state(
            initial_budget_ledger=initial_ledger,
            **self.shared,
        )
        self.harness = PreauthorizedEffectHarness(initial_state, **self.harness_shared)

    @property
    def shared(self) -> dict[str, object]:
        return {
            "contract": self.contract,
            "guidance_policy": self.policy,
            "guidance_arm": self.arm,
            "scouts": self.source["scouts"],
            "probe": self.source["probe"],
            "experience": self.source["experience"],
        }

    @property
    def harness_shared(self) -> dict[str, object]:
        return {
            "guidance_contract": self.contract,
            "guidance_policy": self.policy,
            "guidance_arm": self.arm,
            "scouts": self.source["scouts"],
            "probe": self.source["probe"],
            "experience": self.source["experience"],
        }

    def model_meter(
        self,
        *,
        max_attempts: int = 3,
        input_tokens: int = 1000,
        output_tokens: int = 200,
        wall_milliseconds: int = 30_000,
    ) -> dict[str, object]:
        return build_provider_meter_contract(
            provider_kind="azure_responses_model",
            charge_kind="renderer",
            max_attempts=max_attempts,
            reserved_cost=cost(
                model_calls=1,
                model_attempts=max_attempts,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                wall_milliseconds=wall_milliseconds,
            ),
        )

    def tavily_meter(self, *, max_attempts: int = 3) -> dict[str, object]:
        return build_provider_meter_contract(
            provider_kind="tavily_search_api",
            charge_kind="fanout_execution",
            max_attempts=max_attempts,
            reserved_cost=cost(
                search_calls=max_attempts,
                wall_milliseconds=30_000,
            ),
        )

    @staticmethod
    def observation(
        invocation: dict[str, object],
        *,
        outcome: str = "success",
        http_status: int | None = 200,
        response: bool = True,
        token_state: str = USAGE_OBSERVED,
        input_tokens: int | None = 100,
        output_tokens: int | None = 20,
        tool_state: str = USAGE_NOT_APPLICABLE,
        tool_calls: int | None = None,
        request_bytes: int = 128,
        response_bytes: int | None = 256,
    ) -> dict[str, object]:
        return build_provider_attempt_observation(
            invocation=invocation,
            outcome=outcome,
            http_status=http_status,
            provider_response_ref_sha256=(
                digest(f"response-{invocation['attempt_ref_sha256']}")
                if response
                else None
            ),
            token_usage_state=token_state,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_tool_usage_state=tool_state,
            provider_tool_calls=tool_calls,
            request_body_bytes=request_bytes,
            response_body_bytes=response_bytes,
        )

    def execute(
        self,
        meter: dict[str, object],
        callback,
        *,
        suffix: str = "1",
    ) -> EffectExecutionResult:
        return self.harness.run_effect(
            meter_contract=meter,
            invocation_ref_sha256=digest(f"invocation-{suffix}"),
            permit_ref_sha256=digest(f"permit-{suffix}"),
            charge_ref_sha256=digest(f"charge-{suffix}"),
            callback=callback,
        )

    def test_success_permit_precedes_callback_and_settlement_follows(self) -> None:
        meter = self.model_meter()
        observed_states: list[dict[str, object]] = []

        def callback(invocation):
            observed_states.append(self.harness.snapshot_state())
            return ProviderAttemptResult(
                observation=self.observation(invocation),
                value={"ephemeral": "provider value"},
            )

        result = self.execute(meter, callback)
        self.assertEqual(result.value, {"ephemeral": "provider value"})
        validate_effect_execution_receipt(result.receipt)
        self.assertEqual(len(observed_states), 1)
        self.assertEqual(observed_states[0]["issued_permit_count"], 1)
        self.assertEqual(observed_states[0]["settled_permit_count"], 0)
        self.assertIn(digest("permit-1"), observed_states[0]["pending_permit_refs"])
        final = self.harness.snapshot_state()
        validate_effect_preauthorization_state(final, **self.shared)
        self.assertEqual(final["settled_permit_count"], 1)
        self.assertEqual(final["pending_permit_refs"], [])
        self.assertFalse(result.receipt["raw_provider_value_persisted_hashed_or_emitted"])
        encoded = repr(result.receipt)
        self.assertNotIn("provider value", encoded)

    def test_retry_sequence_is_bounded_and_each_callback_has_existing_permit(self) -> None:
        meter = self.model_meter(max_attempts=3)
        invocations: list[dict[str, object]] = []

        def callback(invocation):
            invocations.append(dict(invocation))
            state = self.harness.snapshot_state()
            self.assertIn(digest("permit-retry"), state["pending_permit_refs"])
            if invocation["attempt_index"] == 1:
                return ProviderAttemptResult(
                    observation=self.observation(
                        invocation,
                        outcome="retryable_http",
                        http_status=429,
                        input_tokens=0,
                        output_tokens=0,
                    )
                )
            return ProviderAttemptResult(observation=self.observation(invocation))

        result = self.execute(meter, callback, suffix="retry")
        receipt = result.receipt
        self.assertEqual(receipt["attempt_count"], 2)
        self.assertEqual([row["attempt_index"] for row in invocations], [1, 2])
        self.assertNotEqual(
            invocations[0]["attempt_ref_sha256"],
            invocations[1]["attempt_ref_sha256"],
        )
        self.assertLess(
            receipt["callback_complete_sequences"][0],
            receipt["callback_start_sequences"][1],
        )

    def test_exhausted_retry_settles_as_failed_consumed_effect(self) -> None:
        meter = self.tavily_meter(max_attempts=2)

        def callback(invocation):
            return ProviderAttemptResult(
                observation=self.observation(
                    invocation,
                    outcome="transport_error",
                    http_status=None,
                    response=False,
                    token_state=USAGE_NOT_APPLICABLE,
                    input_tokens=None,
                    output_tokens=None,
                    request_bytes=128,
                    response_bytes=None,
                )
            )

        result = self.execute(meter, callback, suffix="failed")
        self.assertEqual(result.receipt["logical_status"], "failed")
        self.assertEqual(result.receipt["attempt_count"], 2)
        self.assertEqual(result.receipt["settlement_cost"]["search_calls"], 2)
        self.assertEqual(self.harness.snapshot_state()["settled_permit_count"], 1)

    def test_callback_exception_leaves_charged_pending_permit_and_safe_receipt(self) -> None:
        meter = self.model_meter()

        def callback(_invocation):
            raise RuntimeError("secret provider body https://private.invalid")

        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(meter, callback, suffix="exception")
        receipt = caught.exception.receipt
        validate_effect_failure_receipt(receipt)
        self.assertEqual(receipt["failure_phase"], "callback_exception")
        self.assertTrue(receipt["provider_effect_may_have_occurred"])
        self.assertFalse(receipt["automatic_whole_effect_replay_authorized"])
        self.assertNotIn("private.invalid", repr(receipt))
        state = self.harness.snapshot_state()
        self.assertEqual(state["issued_permit_count"], 1)
        self.assertEqual(state["settled_permit_count"], 0)
        self.assertIn(digest("permit-exception"), state["pending_permit_refs"])

    def test_invalid_challenge_or_attempt_binding_leaves_pending(self) -> None:
        meter = self.model_meter()

        def callback(invocation):
            observation = self.observation(invocation)
            observation["execution_challenge_sha256"] = digest("wrong")
            return ProviderAttemptResult(observation=observation)

        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(meter, callback, suffix="binding")
        receipt = caught.exception.receipt
        self.assertEqual(receipt["failure_phase"], "observation_validation")
        self.assertTrue(receipt["permit_remains_pending"])

    def test_unavailable_usage_uses_reservation_fallback(self) -> None:
        meter = self.model_meter(input_tokens=500, output_tokens=100)
        seen = 0

        def callback(invocation):
            nonlocal seen
            seen += 1
            if seen == 1:
                return ProviderAttemptResult(
                    observation=self.observation(
                        invocation,
                        outcome="retryable_http",
                        http_status=429,
                        token_state=USAGE_UNAVAILABLE,
                        input_tokens=None,
                        output_tokens=None,
                    )
                )
            return ProviderAttemptResult(
                observation=self.observation(
                    invocation,
                    input_tokens=80,
                    output_tokens=10,
                )
            )

        result = self.execute(meter, callback, suffix="fallback")
        self.assertEqual(
            result.receipt["reservation_fallback_dimensions"],
            ["input_tokens", "output_tokens"],
        )
        self.assertEqual(result.receipt["settlement_cost"]["input_tokens"], 500)
        self.assertEqual(result.receipt["settlement_cost"]["output_tokens"], 100)

    def test_observed_over_reservation_is_not_masked_and_remains_pending(self) -> None:
        meter = self.model_meter(input_tokens=5, output_tokens=5)

        def callback(invocation):
            return ProviderAttemptResult(
                observation=self.observation(
                    invocation,
                    input_tokens=6,
                    output_tokens=1,
                )
            )

        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(meter, callback, suffix="over")
        receipt = caught.exception.receipt
        self.assertEqual(receipt["failure_phase"], "settlement_validation")
        self.assertTrue(receipt["reservation_remains_charged"])
        self.assertIn(digest("permit-over"), self.harness.snapshot_state()["pending_permit_refs"])

    def test_callbacks_for_two_permits_overlap_but_admission_and_settlement_serialize(self) -> None:
        meter = self.model_meter(max_attempts=1)
        barrier = threading.Barrier(2)

        def run_one(suffix: str):
            def callback(invocation):
                state = self.harness.snapshot_state()
                self.assertGreaterEqual(state["issued_permit_count"], 1)
                barrier.wait(timeout=5)
                return ProviderAttemptResult(
                    observation=self.observation(invocation),
                    value=suffix,
                )

            return self.execute(meter, callback, suffix=suffix)

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(run_one, "parallel-a")
            second = pool.submit(run_one, "parallel-b")
            results = [first.result(timeout=10), second.result(timeout=10)]
        receipts = sorted(results, key=lambda row: row.receipt["admission_sequence"])
        self.assertLess(
            receipts[1].receipt["admission_sequence"],
            receipts[0].receipt["settlement_sequence"],
        )
        final = self.harness.snapshot_state()
        self.assertEqual(final["issued_permit_count"], 2)
        self.assertEqual(final["settled_permit_count"], 2)
        self.assertEqual(sorted(result.value for result in results), ["parallel-a", "parallel-b"])

    def test_duplicate_invocation_is_rejected_before_second_permit(self) -> None:
        meter = self.model_meter(max_attempts=1)

        def callback(invocation):
            return ProviderAttemptResult(observation=self.observation(invocation))

        self.execute(meter, callback, suffix="duplicate")
        state_before = self.harness.snapshot_state()
        with self.assertRaisesRegex(ValueError, "duplicate invocation"):
            self.harness.run_effect(
                meter_contract=meter,
                invocation_ref_sha256=digest("invocation-duplicate"),
                permit_ref_sha256=digest("permit-duplicate-2"),
                charge_ref_sha256=digest("charge-duplicate-2"),
                callback=callback,
            )
        self.assertEqual(self.harness.snapshot_state(), state_before)

    def test_state_and_receipt_snapshots_are_defensive_copies(self) -> None:
        meter = self.model_meter(max_attempts=1)

        def callback(invocation):
            return ProviderAttemptResult(observation=self.observation(invocation))

        result = self.execute(meter, callback, suffix="copy")
        state = self.harness.snapshot_state()
        state["events"].clear()
        receipt = copy.deepcopy(result.receipt)
        receipt["settlement_cost"]["input_tokens"] += 1
        self.assertEqual(self.harness.snapshot_state()["event_count"], 2)
        self.assertEqual(self.harness.execution_receipts()[0], result.receipt)

    def test_receipt_tamper_and_reseal_fail_closed(self) -> None:
        meter = self.model_meter(max_attempts=1)

        def callback(invocation):
            return ProviderAttemptResult(observation=self.observation(invocation))

        result = self.execute(meter, callback, suffix="tamper")
        tampered = copy.deepcopy(result.receipt)
        tampered["callback_start_sequences"][0] = tampered["admission_sequence"]
        tampered.pop("execution_receipt_sha256")
        tampered["execution_receipt_sha256"] = object_sha256(tampered)
        with self.assertRaises(ValueError):
            validate_effect_execution_receipt(tampered)

        summary_tampered = copy.deepcopy(result.receipt)
        summary_tampered["settlement_cost"]["input_tokens"] += 1
        summary_tampered.pop("execution_receipt_sha256")
        summary_tampered["execution_receipt_sha256"] = object_sha256(
            summary_tampered
        )
        with self.assertRaisesRegex(ValueError, "execution receipt"):
            validate_effect_execution_receipt(summary_tampered)

        graph_tampered = copy.deepcopy(result.receipt)
        graph_tampered["measurement"]["settlement_cost"]["input_tokens"] += 1
        graph_tampered["settlement_cost"]["input_tokens"] += 1
        graph_tampered["measurement"].pop("measurement_sha256")
        graph_tampered["measurement"]["measurement_sha256"] = object_sha256(
            graph_tampered["measurement"]
        )
        graph_tampered["measurement_sha256"] = graph_tampered["measurement"][
            "measurement_sha256"
        ]
        graph_tampered.pop("execution_receipt_sha256")
        graph_tampered["execution_receipt_sha256"] = object_sha256(
            graph_tampered
        )
        with self.assertRaisesRegex(ValueError, "embedded execution graph"):
            validate_effect_execution_receipt(graph_tampered)

    def test_failure_receipt_embedded_graph_rejects_tamper_and_reseal(self) -> None:
        meter = self.model_meter()

        def callback(_invocation):
            raise RuntimeError("private provider failure")

        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(meter, callback, suffix="failure-tamper")
        receipt = caught.exception.receipt
        tampered = copy.deepcopy(receipt)
        tampered["permit"]["reserved_cost"]["input_tokens"] += 1
        tampered.pop("failure_receipt_sha256")
        tampered["failure_receipt_sha256"] = object_sha256(tampered)
        with self.assertRaisesRegex(ValueError, "embedded failure graph"):
            validate_effect_failure_receipt(tampered)

    def test_second_callback_exception_reports_partial_completion_exactly(self) -> None:
        meter = self.model_meter(max_attempts=2)
        calls = 0

        def callback(invocation):
            nonlocal calls
            calls += 1
            if calls == 1:
                return ProviderAttemptResult(
                    observation=self.observation(
                        invocation,
                        outcome="retryable_http",
                        http_status=429,
                        input_tokens=0,
                        output_tokens=0,
                    )
                )
            raise RuntimeError("second callback failed")

        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(meter, callback, suffix="partial")
        receipt = caught.exception.receipt
        validate_effect_failure_receipt(receipt)
        self.assertEqual(len(receipt["callback_start_sequences"]), 2)
        self.assertEqual(receipt["completed_callback_count"], 1)
        self.assertFalse(receipt["all_started_callbacks_completed"])
        self.assertEqual(len(receipt["attempts"]), 1)
        self.assertEqual(len(receipt["attempt_invocations"]), 2)

    def test_invocation_to_attempt_binding_cannot_be_resealed_away(self) -> None:
        meter = self.model_meter()
        calls = 0

        def callback(invocation):
            nonlocal calls
            calls += 1
            if calls == 1:
                return ProviderAttemptResult(
                    observation=self.observation(
                        invocation,
                        outcome="retryable_http",
                        http_status=429,
                        input_tokens=0,
                        output_tokens=0,
                    )
                )
            raise RuntimeError("stop after one valid attempt")

        with self.assertRaises(PreauthorizedEffectExecutionError) as caught:
            self.execute(meter, callback, suffix="attempt-binding")
        receipt = caught.exception.receipt
        tampered = copy.deepcopy(receipt)
        tampered["attempts"][0]["attempt_ref_sha256"] = digest("different-attempt")
        tampered["attempts"][0].pop("attempt_sha256")
        tampered["attempts"][0]["attempt_sha256"] = object_sha256(
            tampered["attempts"][0]
        )
        tampered["attempt_sha256s"][0] = tampered["attempts"][0][
            "attempt_sha256"
        ]
        tampered.pop("failure_receipt_sha256")
        tampered["failure_receipt_sha256"] = object_sha256(tampered)
        with self.assertRaisesRegex(ValueError, "embedded failure graph"):
            validate_effect_failure_receipt(tampered)

    def test_capability_and_authorization_boundaries_are_explicit(self) -> None:
        self.assertTrue(CALLER_SUPPLIED_EFFECT_CALLBACK_INVOCATION_AUTHORIZED)
        self.assertTrue(CALLBACK_CONCURRENCY_BETWEEN_PERMITS_IMPLEMENTED)
        for value in (
            PRODUCTION_PACKAGE_AUTHORIZED,
            ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
            CROSS_PROCESS_COMPARE_AND_SWAP_IMPLEMENTED,
            CRASH_DURABLE_JOURNAL_IMPLEMENTED,
            CALLBACK_TIMEOUT_IMPLEMENTED,
            RETRY_BACKOFF_IMPLEMENTED,
            PROVIDER_CHALLENGE_CONSUMPTION_INDEPENDENTLY_VERIFIED,
        ):
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
