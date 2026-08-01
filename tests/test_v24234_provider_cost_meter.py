from __future__ import annotations

import copy
import sys
import unittest
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
    validate_effect_preauthorization_state,
)
from deepwide_agent.v24234_provider_cost_meter import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    USAGE_NOT_APPLICABLE,
    USAGE_OBSERVED,
    USAGE_UNAVAILABLE,
    build_provider_attempt,
    build_provider_cost_measurement,
    build_provider_meter_contract,
    issue_metered_effect_permit,
    settle_metered_effect_permit,
    validate_provider_attempt,
    validate_provider_cost_measurement,
    validate_provider_meter_contract,
)
from tests.test_v24232_webswarm_total_budget import (  # noqa: E402
    contract as guidance_contract,
    digest,
    guidance,
    ledger,
)


def cost(**overrides: int) -> dict[str, int]:
    values = {
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
    values.update(overrides)
    return build_cost_vector(**values)


def reserved(provider: str, *, max_attempts: int = 3) -> dict[str, int]:
    if provider == "azure_responses_model":
        return cost(
            model_calls=1,
            model_attempts=max_attempts,
            input_tokens=2_000,
            output_tokens=500,
        )
    if provider in {
        "azure_responses_web_search",
        "anthropic_server_web_search",
    }:
        return cost(
            search_calls=max_attempts,
            other_tool_calls=6,
            input_tokens=2_000,
            output_tokens=500,
        )
    if provider == "tavily_search_api":
        return cost(search_calls=max_attempts)
    if provider == "native_http_fetch":
        return cost(fetch_calls=max_attempts)
    if provider == "local_orchestrator":
        return cost(orchestrator_calls=1)
    if provider == "local_other_tool":
        return cost(other_tool_calls=1)
    raise AssertionError(provider)


def charge_kind(provider: str) -> str:
    if provider == "azure_responses_model":
        return "renderer"
    if provider == "local_orchestrator":
        return "orchestrator"
    if provider == "local_other_tool":
        return "other_tool"
    return "fanout_execution"


class V24234ProviderCostMeterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.guidance_contract = guidance_contract()
        self.policy, _, self.arms, self.sources = guidance(self.guidance_contract)
        self.arm = next(arm for arm in self.arms if arm["arm_name"] == "full")
        self.source = self.sources["full"]
        self.initial_ledger = ledger(
            self.guidance_contract,
            self.policy,
            self.arm,
            self.source,
        )
        self.state = initialize_effect_preauthorization_state(
            initial_budget_ledger=self.initial_ledger,
            **self.shared,
        )

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

    def meter(
        self, provider: str, *, max_attempts: int = 3, reserve=None
    ) -> dict[str, object]:
        return build_provider_meter_contract(
            provider_kind=provider,
            charge_kind=charge_kind(provider),
            max_attempts=max_attempts,
            reserved_cost=(
                reserved(provider, max_attempts=max_attempts)
                if reserve is None
                else reserve
            ),
        )

    def issue(
        self, meter: dict[str, object], *, suffix: str = "1"
    ) -> dict[str, object]:
        return issue_metered_effect_permit(
            self.state,
            contract=meter,
            guidance_contract=self.guidance_contract,
            guidance_policy=self.policy,
            guidance_arm=self.arm,
            scouts=self.source["scouts"],
            probe=self.source["probe"],
            experience=self.source["experience"],
            permit_ref_sha256=digest(f"permit-{suffix}"),
            charge_ref_sha256=digest(f"charge-{suffix}"),
        )

    def pending_permit(self, state: dict[str, object]) -> dict[str, object]:
        return next(
            event for event in state["events"] if event["role"].endswith("effect_permit")
        )

    def attempt(
        self,
        meter: dict[str, object],
        index: int,
        *,
        outcome: str = "success",
        http_status: int | None = 200,
        token_state: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        tool_state: str | None = None,
        tool_calls: int | None = None,
        response_ref: str | None = "auto",
        wall: int = 1000,
        request_bytes: int | None = None,
        response_bytes: int | None = 200,
        ref_suffix: str | None = None,
        counter_suffix: str | None = None,
    ) -> dict[str, object]:
        provider = str(meter["provider_kind"])
        local = provider.startswith("local_")
        if token_state is None:
            token_state = (
                USAGE_OBSERVED
                if meter["token_usage_policy"] == "required"
                else USAGE_NOT_APPLICABLE
            )
        if token_state == USAGE_OBSERVED:
            input_tokens = 10 if input_tokens is None else input_tokens
            output_tokens = 20 if output_tokens is None else output_tokens
        else:
            input_tokens = None
            output_tokens = None
        if tool_state is None:
            tool_state = (
                USAGE_OBSERVED
                if meter["provider_tool_usage_policy"] == "required"
                else USAGE_NOT_APPLICABLE
            )
        if tool_state == USAGE_OBSERVED:
            tool_calls = 1 if tool_calls is None else tool_calls
        else:
            tool_calls = None
        if response_ref == "auto":
            response_ref = (
                None
                if outcome == "transport_error"
                else digest(f"response-{ref_suffix or index}")
            )
        if request_bytes is None:
            request_bytes = 0 if local or provider == "native_http_fetch" else 100
        if local:
            http_status = None
            response_bytes = None
        elif outcome == "transport_error":
            http_status = None
            response_bytes = None
        return build_provider_attempt(
            contract=meter,
            attempt_index=index,
            attempt_ref_sha256=digest(f"attempt-{ref_suffix or index}"),
            local_counter_ref_sha256=digest(
                f"counter-{counter_suffix or index}"
            ),
            outcome=outcome,
            http_status=http_status,
            provider_response_ref_sha256=response_ref,
            token_usage_state=token_state,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_tool_usage_state=tool_state,
            provider_tool_calls=tool_calls,
            wall_milliseconds=wall,
            request_body_bytes=request_bytes,
            response_body_bytes=response_bytes,
        )

    def measurement(
        self,
        meter: dict[str, object],
        state: dict[str, object],
        attempts: list[dict[str, object]],
        *,
        suffix: str = "1",
    ) -> dict[str, object]:
        return build_provider_cost_measurement(
            contract=meter,
            permit=self.pending_permit(state),
            measurement_ref_sha256=digest(f"measurement-{suffix}"),
            attempts=attempts,
        )

    def settle(
        self,
        meter: dict[str, object],
        state: dict[str, object],
        measurement: dict[str, object],
    ) -> dict[str, object]:
        return settle_metered_effect_permit(
            state,
            meter_contract=meter,
            measurement=measurement,
            guidance_contract=self.guidance_contract,
            guidance_policy=self.policy,
            guidance_arm=self.arm,
            scouts=self.source["scouts"],
            probe=self.source["probe"],
            experience=self.source["experience"],
        )

    def test_contracts_freeze_all_provider_mappings(self) -> None:
        providers = (
            "azure_responses_model",
            "azure_responses_web_search",
            "anthropic_server_web_search",
            "tavily_search_api",
            "native_http_fetch",
            "local_orchestrator",
            "local_other_tool",
        )
        for provider in providers:
            with self.subTest(provider=provider):
                max_attempts = 1 if provider.startswith("local_") else 3
                meter = self.meter(provider, max_attempts=max_attempts)
                validate_provider_meter_contract(meter)
                self.assertTrue(meter["build_only"])
                self.assertFalse(meter["missing_applicable_usage_is_zero"])
                self.assertFalse(meter["runtime_provider_wrapper_integrated"])
                self.assertFalse(meter["external_side_effect_authorized"])
                self.assertFalse(
                    meter["benchmark_forward_or_evaluator_authorized"]
                )

    def test_contract_rejects_unknown_mismatched_and_optimistic_reservations(self) -> None:
        with self.assertRaisesRegex(ValueError, "provider kind"):
            build_provider_meter_contract(
                provider_kind="unknown",
                charge_kind="fanout_execution",
                max_attempts=1,
                reserved_cost=cost(search_calls=1),
            )
        with self.assertRaisesRegex(ValueError, "reserved model_attempts"):
            self.meter(
                "azure_responses_model",
                reserve=cost(
                    model_calls=1,
                    model_attempts=2,
                    input_tokens=100,
                    output_tokens=10,
                ),
            )
        with self.assertRaisesRegex(ValueError, "tool calls"):
            self.meter(
                "azure_responses_web_search",
                reserve=cost(
                    search_calls=3,
                    input_tokens=100,
                    output_tokens=10,
                ),
            )
        with self.assertRaisesRegex(ValueError, "token-inapplicable"):
            self.meter(
                "tavily_search_api",
                reserve=cost(search_calls=3, input_tokens=1),
            )
        with self.assertRaisesRegex(ValueError, "charge kind"):
            build_provider_meter_contract(
                provider_kind="native_http_fetch",
                charge_kind="renderer",
                max_attempts=3,
                reserved_cost=reserved("native_http_fetch"),
            )
        with self.assertRaisesRegex(ValueError, "one attempt"):
            self.meter("local_orchestrator", max_attempts=2)

    def test_model_complete_retry_measurement_settles_v24233(self) -> None:
        meter = self.meter("azure_responses_model")
        state = self.issue(meter)
        attempts = [
            self.attempt(
                meter,
                1,
                outcome="retryable_http",
                http_status=429,
                input_tokens=0,
                output_tokens=0,
                wall=1500,
            ),
            self.attempt(meter, 2, input_tokens=100, output_tokens=30, wall=2500),
        ]
        measurement = self.measurement(meter, state, attempts)
        validate_provider_cost_measurement(
            measurement,
            contract=meter,
            permit=self.pending_permit(state),
        )
        self.assertEqual(measurement["logical_status"], "completed")
        self.assertTrue(measurement["all_applicable_usage_observed"])
        self.assertTrue(measurement["settlement_eligible"])
        self.assertEqual(measurement["settlement_cost"]["model_calls"], 1)
        self.assertEqual(measurement["settlement_cost"]["model_attempts"], 2)
        self.assertEqual(measurement["settlement_cost"]["input_tokens"], 100)
        self.assertEqual(measurement["settlement_cost"]["output_tokens"], 30)
        self.assertEqual(measurement["settlement_cost"]["wall_milliseconds"], 4000)
        self.assertFalse(measurement["reservation_fallback_applied"])
        settled = self.settle(meter, state, measurement)
        validate_effect_preauthorization_state(settled, **self.shared)
        self.assertEqual(settled["settled_permit_count"], 1)
        self.assertEqual(
            settled["events"][-1]["actual_cost_source_sha256"],
            measurement["measurement_sha256"],
        )

    def test_missing_applicable_usage_uses_reservation_fallback_not_zero(self) -> None:
        meter = self.meter("azure_responses_model")
        state = self.issue(meter)
        attempts = [
            self.attempt(
                meter,
                1,
                outcome="retryable_http",
                http_status=429,
                token_state=USAGE_UNAVAILABLE,
            ),
            self.attempt(meter, 2, input_tokens=100, output_tokens=30),
        ]
        measurement = self.measurement(meter, state, attempts)
        self.assertEqual(
            measurement["unavailable_dimensions"],
            ["input_tokens", "output_tokens"],
        )
        self.assertEqual(
            measurement["observed_cost_lower_bound"]["input_tokens"], 100
        )
        self.assertEqual(
            measurement["settlement_cost"]["input_tokens"],
            meter["reserved_cost"]["input_tokens"],
        )
        self.assertEqual(
            measurement["settlement_cost"]["output_tokens"],
            meter["reserved_cost"]["output_tokens"],
        )
        self.assertEqual(measurement["settlement_cost"]["model_attempts"], 2)
        self.assertEqual(measurement["settlement_cost"]["wall_milliseconds"], 2000)
        self.assertEqual(
            measurement["reservation_fallback_dimensions"],
            ["input_tokens", "output_tokens"],
        )
        self.assertTrue(measurement["reservation_fallback_applied"])
        self.assertEqual(
            measurement["settlement_cost_basis"],
            "declared_reservation_fallback",
        )
        self.assertTrue(measurement["settlement_eligible"])
        self.assertFalse(measurement["missing_applicable_usage_treated_as_zero"])
        settled = self.settle(meter, state, measurement)
        self.assertEqual(settled["settled_permit_count"], 1)
        self.assertFalse(
            settled["events"][-1]["actual_cost_independently_measured"]
        )

    def test_fallback_does_not_mask_observed_over_reservation(self) -> None:
        meter = self.meter("azure_responses_model")
        state = self.issue(meter)
        measurement = self.measurement(
            meter,
            state,
            [
                self.attempt(
                    meter,
                    1,
                    outcome="retryable_http",
                    http_status=429,
                    token_state=USAGE_UNAVAILABLE,
                ),
                self.attempt(
                    meter,
                    2,
                    input_tokens=meter["reserved_cost"]["input_tokens"] + 1,
                    output_tokens=1,
                ),
            ],
        )
        self.assertTrue(measurement["reservation_fallback_applied"])
        self.assertEqual(
            measurement["reservation_fallback_dimensions"],
            ["input_tokens", "output_tokens"],
        )
        self.assertGreater(
            measurement["observed_cost_lower_bound"]["input_tokens"],
            meter["reserved_cost"]["input_tokens"],
        )
        self.assertEqual(
            measurement["settlement_cost"]["input_tokens"],
            meter["reserved_cost"]["input_tokens"],
        )
        self.assertFalse(measurement["observed_lower_bound_within_reservation"])
        self.assertTrue(measurement["settlement_cost_within_reservation"])
        self.assertFalse(measurement["settlement_eligible"])
        with self.assertRaisesRegex(ValueError, "over-reservation"):
            self.settle(meter, state, measurement)

    def test_hosted_search_maps_attempts_tokens_and_provider_tool_calls(self) -> None:
        for provider in (
            "azure_responses_web_search",
            "anthropic_server_web_search",
        ):
            with self.subTest(provider=provider):
                meter = self.meter(provider)
                state = self.issue(meter, suffix=provider)
                attempts = [
                    self.attempt(
                        meter,
                        1,
                        input_tokens=200,
                        output_tokens=50,
                        tool_calls=2,
                    )
                ]
                measurement = self.measurement(
                    meter,
                    state,
                    attempts,
                    suffix=provider,
                )
                actual = measurement["settlement_cost"]
                self.assertEqual(actual["search_calls"], 1)
                self.assertEqual(actual["other_tool_calls"], 2)
                self.assertEqual(actual["input_tokens"], 200)
                self.assertEqual(actual["output_tokens"], 50)
                self.assertTrue(measurement["settlement_eligible"])

    def test_tavily_key_rotation_is_complete_without_fake_tokens(self) -> None:
        meter = self.meter("tavily_search_api")
        state = self.issue(meter)
        attempts = [
            self.attempt(
                meter,
                1,
                outcome="key_local_http",
                http_status=432,
            ),
            self.attempt(meter, 2),
        ]
        measurement = self.measurement(meter, state, attempts)
        actual = measurement["settlement_cost"]
        self.assertEqual(actual["search_calls"], 2)
        self.assertEqual(actual["input_tokens"], 0)
        self.assertEqual(actual["output_tokens"], 0)
        self.assertEqual(measurement["unavailable_dimensions"], [])
        self.assertTrue(measurement["settlement_eligible"])

    def test_fetch_transport_and_success_map_to_fetch_calls_and_bytes(self) -> None:
        meter = self.meter("native_http_fetch")
        state = self.issue(meter)
        attempts = [
            self.attempt(
                meter,
                1,
                outcome="transport_error",
                response_ref=None,
            ),
            self.attempt(meter, 2, response_bytes=4096),
        ]
        measurement = self.measurement(meter, state, attempts)
        self.assertEqual(measurement["settlement_cost"]["fetch_calls"], 2)
        self.assertEqual(attempts[0]["response_body_bytes"], None)
        self.assertEqual(attempts[1]["response_body_bytes"], 4096)
        self.assertTrue(measurement["settlement_eligible"])

    def test_local_effects_have_no_http_or_token_accounting(self) -> None:
        for provider, dimension in (
            ("local_orchestrator", "orchestrator_calls"),
            ("local_other_tool", "other_tool_calls"),
        ):
            with self.subTest(provider=provider):
                meter = self.meter(provider, max_attempts=1)
                state = self.issue(meter, suffix=provider)
                attempt = self.attempt(
                    meter,
                    1,
                    outcome="local_success",
                    response_ref=digest(f"local-{provider}"),
                )
                measurement = self.measurement(
                    meter,
                    state,
                    [attempt],
                    suffix=provider,
                )
                self.assertEqual(measurement["settlement_cost"][dimension], 1)
                self.assertIsNone(attempt["http_status"])
                self.assertIsNone(attempt["response_body_bytes"])
                self.assertTrue(measurement["settlement_eligible"])

    def test_attempt_schema_status_usage_and_byte_rules_fail_closed(self) -> None:
        meter = self.meter("azure_responses_model")
        cases = (
            {
                "outcome": "success",
                "http_status": 200,
                "token_state": USAGE_UNAVAILABLE,
            },
            {"outcome": "retryable_http", "http_status": 400},
            {"outcome": "transport_error", "response_ref": digest("bad")},
            {"outcome": "success", "response_bytes": None},
            {
                "outcome": "success",
                "input_tokens": 0,
                "output_tokens": 0,
            },
        )
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    self.attempt(meter, 1, **kwargs)
        tavily = self.meter("tavily_search_api")
        with self.assertRaisesRegex(ValueError, "not applicable"):
            self.attempt(tavily, 1, token_state=USAGE_OBSERVED)
        local = self.meter("local_orchestrator", max_attempts=1)
        with self.assertRaisesRegex(ValueError, "local outcome"):
            self.attempt(local, 1, outcome="success")

    def test_measurement_rejects_duplicate_noncontiguous_and_invalid_sequences(self) -> None:
        meter = self.meter("azure_responses_model")
        state = self.issue(meter)
        permit = self.pending_permit(state)
        first = self.attempt(
            meter,
            1,
            outcome="retryable_http",
            http_status=429,
            input_tokens=0,
            output_tokens=0,
        )
        duplicate = self.attempt(
            meter,
            2,
            ref_suffix="1",
            counter_suffix="2",
        )
        with self.assertRaisesRegex(ValueError, "duplicate attempt"):
            build_provider_cost_measurement(
                contract=meter,
                permit=permit,
                measurement_ref_sha256=digest("measurement"),
                attempts=[first, duplicate],
            )
        duplicate_counter = self.attempt(
            meter,
            2,
            ref_suffix="2",
            counter_suffix="1",
        )
        with self.assertRaisesRegex(ValueError, "duplicate local counter"):
            build_provider_cost_measurement(
                contract=meter,
                permit=permit,
                measurement_ref_sha256=digest("measurement"),
                attempts=[first, duplicate_counter],
            )
        success_first = self.attempt(meter, 1)
        retry_second = self.attempt(
            meter,
            2,
            outcome="retryable_http",
            http_status=429,
            input_tokens=0,
            output_tokens=0,
        )
        with self.assertRaisesRegex(ValueError, "success must be unique and final"):
            build_provider_cost_measurement(
                contract=meter,
                permit=permit,
                measurement_ref_sha256=digest("measurement"),
                attempts=[success_first, retry_second],
            )
        terminal_first = self.attempt(
            meter,
            1,
            outcome="terminal_http",
            http_status=400,
            input_tokens=0,
            output_tokens=0,
        )
        with self.assertRaisesRegex(ValueError, "terminal outcome must be final"):
            build_provider_cost_measurement(
                contract=meter,
                permit=permit,
                measurement_ref_sha256=digest("measurement"),
                attempts=[terminal_first, retry_second],
            )

    def test_complete_over_reservation_measurement_cannot_settle(self) -> None:
        reserve = reserved("azure_responses_model")
        reserve["input_tokens"] = 5
        meter = self.meter("azure_responses_model", reserve=reserve)
        state = self.issue(meter)
        measurement = self.measurement(
            meter,
            state,
            [self.attempt(meter, 1, input_tokens=6, output_tokens=1)],
        )
        self.assertTrue(measurement["all_applicable_usage_observed"])
        self.assertFalse(measurement["settlement_cost_within_reservation"])
        self.assertFalse(measurement["settlement_eligible"])
        with self.assertRaisesRegex(ValueError, "over-reservation"):
            self.settle(meter, state, measurement)

    def test_cross_contract_permit_and_tamper_reseal_fail_closed(self) -> None:
        meter = self.meter("azure_responses_model")
        state = self.issue(meter)
        attempt = self.attempt(meter, 1)
        measurement = self.measurement(meter, state, [attempt])

        other = self.meter("azure_responses_web_search")
        with self.assertRaises(ValueError):
            build_provider_cost_measurement(
                contract=other,
                permit=self.pending_permit(state),
                measurement_ref_sha256=digest("wrong"),
                attempts=[self.attempt(other, 1)],
            )

        tampered_attempt = copy.deepcopy(attempt)
        tampered_attempt["input_tokens"] += 1
        tampered_attempt.pop("attempt_sha256")
        tampered_attempt["attempt_sha256"] = object_sha256(tampered_attempt)
        validate_provider_attempt(tampered_attempt, contract=meter)
        self.assertFalse(
            tampered_attempt[
                "provider_response_authenticity_independently_verified"
            ]
        )
        self.assertFalse(
            tampered_attempt["local_counter_and_clock_independently_attested"]
        )

        tampered_measurement = copy.deepcopy(measurement)
        tampered_measurement["settlement_cost"]["input_tokens"] += 1
        tampered_measurement.pop("measurement_sha256")
        tampered_measurement["measurement_sha256"] = object_sha256(
            tampered_measurement
        )
        with self.assertRaises(ValueError):
            validate_provider_cost_measurement(
                tampered_measurement,
                contract=meter,
                permit=self.pending_permit(state),
            )

    def test_failed_complete_attempts_are_chargeable_but_not_success(self) -> None:
        meter = self.meter("tavily_search_api")
        state = self.issue(meter)
        failed = self.attempt(
            meter,
            1,
            outcome="terminal_http",
            http_status=400,
        )
        measurement = self.measurement(meter, state, [failed])
        self.assertEqual(measurement["logical_status"], "failed")
        self.assertTrue(measurement["settlement_eligible"])
        self.assertEqual(measurement["settlement_cost"]["search_calls"], 1)
        settled = self.settle(meter, state, measurement)
        self.assertEqual(settled["settled_permit_count"], 1)

    def test_all_attestations_and_authorizations_remain_false(self) -> None:
        meter = self.meter("azure_responses_model")
        state = self.issue(meter)
        attempt = self.attempt(meter, 1)
        measurement = self.measurement(meter, state, [attempt])
        for value in (meter, attempt, measurement):
            for field in (
                "provider_response_authenticity_independently_verified",
                "local_counter_and_clock_independently_attested",
            ):
                self.assertFalse(value[field], field)
        self.assertFalse(measurement["runtime_provider_wrapper_integrated"])
        self.assertFalse(measurement["external_side_effect_authorized"])
        self.assertFalse(PRODUCTION_PACKAGE_AUTHORIZED)
        self.assertFalse(ACTIVE_FORWARD_INTEGRATION_AUTHORIZED)
        self.assertFalse(EXTERNAL_SIDE_EFFECT_AUTHORIZED)
        self.assertFalse(BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED)
        self.assertFalse(DEV64_OR_EXACT220_LAUNCH_AUTHORIZED)
        self.assertFalse(SHARED_API_LEASE_ACQUIRE_AUTHORIZED)
        self.assertFalse(LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED)


if __name__ == "__main__":
    unittest.main()
