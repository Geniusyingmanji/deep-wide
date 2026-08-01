from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
import os
import sys
import tempfile
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
    initialize_effect_preauthorization_state,
    validate_effect_preauthorization_state,
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
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ATTEMPT_MEASUREMENT_DURABLY_PERSISTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLBACK_OR_SETTLEMENT_FAILURE_AUTOMATIC_REPLAY_IMPLEMENTED,
    CALLBACK_TIMEOUT_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    LOCAL_POSIX_CRASH_DURABLE_EFFECT_ORDERING_IMPLEMENTED,
    NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN,
    PREEXISTING_PENDING_PERMIT_AUTOMATIC_REPLAY_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    RETRY_BACKOFF_IMPLEMENTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    TOTAL_WALL_DEADLINE_IMPLEMENTED,
    DurableEffectExecutionError,
    DurableEffectReplayRejected,
    DurablePreauthorizedEffectCoordinator,
    derive_effect_references,
    validate_durable_effect_execution_receipt,
    validate_durable_effect_failure_receipt,
    validate_durable_effect_recovery_status,
)
from deepwide_agent.v24236_azure_responses_single_attempt import (  # noqa: E402
    AzureResponsesRequest,
    AzureResponsesSingleAttemptAdapter,
)
from tests.test_v24232_webswarm_total_budget import (  # noqa: E402
    contract,
    digest,
    guidance,
    ledger,
)


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


def crash_process_worker(
    root: str,
    namespace: str,
    shared: dict[str, object],
    meter: dict[str, object],
    invocation_ref: str,
    crash_stage: str,
    callback_marker: str,
) -> None:
    coordinator = DurablePreauthorizedEffectCoordinator(
        root=Path(root),
        journal_namespace_sha256=namespace,
        **shared,
    )

    def callback(invocation):
        Path(callback_marker).write_text("called", encoding="utf-8")
        return ProviderAttemptResult(
            observation=V24242DurableEffectCoordinatorTests.observation(invocation)
        )

    def crash(stage: str) -> None:
        if stage == crash_stage:
            os._exit(73)

    coordinator.run_effect(
        meter_contract=meter,
        invocation_ref_sha256=invocation_ref,
        callback=callback,
        fault_hook=crash,
    )


def race_process_worker(
    root: str,
    namespace: str,
    shared: dict[str, object],
    meter: dict[str, object],
    invocation_ref: str,
    gate,
    callback_counter,
    outcomes,
) -> None:
    coordinator = DurablePreauthorizedEffectCoordinator(
        root=Path(root),
        journal_namespace_sha256=namespace,
        **shared,
    )
    gate.wait(timeout=10)

    def callback(invocation):
        with callback_counter.get_lock():
            callback_counter.value += 1
        return ProviderAttemptResult(
            observation=V24242DurableEffectCoordinatorTests.observation(invocation)
        )

    try:
        coordinator.run_effect(
            meter_contract=meter,
            invocation_ref_sha256=invocation_ref,
            callback=callback,
        )
    except DurableEffectReplayRejected:
        outcomes.put("rejected")
    except BaseException as error:  # pragma: no cover - reported to parent
        outcomes.put("error:" + type(error).__name__)
    else:
        outcomes.put("completed")


class InjectedCrash(RuntimeError):
    pass


class FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.status_code = 200
        self.content = content
        self.closed = False

    def close(self) -> None:
        self.closed = True


class RecordingPost:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    def __call__(self, url, **kwargs):
        self.calls.append({"url": url, **kwargs})
        return self.response


class V24242DurableEffectCoordinatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.root = Path(self.temporary.name).resolve()
        self.contract = contract()
        self.policy, _, arms, self.sources = guidance(self.contract)
        self.arm = next(arm for arm in arms if arm["arm_name"] == "full")
        self.source = self.sources["full"]
        self.initial = initialize_effect_preauthorization_state(
            initial_budget_ledger=ledger(
                self.contract,
                self.policy,
                self.arm,
                self.source,
            ),
            **self.shared,
        )
        self.namespace = digest("v24242-journal")
        self.coordinator = DurablePreauthorizedEffectCoordinator.initialize(
            root=self.root,
            journal_namespace_sha256=self.namespace,
            initial_state=self.initial,
            **self.coordinator_shared,
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

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
    def coordinator_shared(self) -> dict[str, object]:
        return {
            "guidance_contract": self.contract,
            "guidance_policy": self.policy,
            "guidance_arm": self.arm,
            "scouts": self.source["scouts"],
            "probe": self.source["probe"],
            "experience": self.source["experience"],
        }

    def reopen(self) -> DurablePreauthorizedEffectCoordinator:
        return DurablePreauthorizedEffectCoordinator(
            root=self.root,
            journal_namespace_sha256=self.namespace,
            **self.coordinator_shared,
        )

    @staticmethod
    def model_meter(
        *, max_attempts: int = 2, input_tokens: int = 1000
    ) -> dict[str, object]:
        return build_provider_meter_contract(
            provider_kind="azure_responses_model",
            charge_kind="renderer",
            max_attempts=max_attempts,
            reserved_cost=cost(
                model_calls=1,
                model_attempts=max_attempts,
                input_tokens=input_tokens,
                output_tokens=200,
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
        input_tokens: int | None = 100,
        output_tokens: int | None = 20,
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
            token_usage_state=USAGE_OBSERVED,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider_tool_usage_state=USAGE_NOT_APPLICABLE,
            provider_tool_calls=None,
            request_body_bytes=128,
            response_body_bytes=256 if response else None,
        )

    def execute(
        self,
        suffix: str,
        callback,
        *,
        meter=None,
        fault_hook=None,
        coordinator=None,
    ):
        active = self.coordinator if coordinator is None else coordinator
        return active.run_effect(
            meter_contract=self.model_meter() if meter is None else meter,
            invocation_ref_sha256=digest(f"invocation-{suffix}"),
            callback=callback,
            fault_hook=fault_hook,
        )

    def test_success_durably_commits_permit_before_callback_and_settlement_after(self) -> None:
        snapshots: list[dict[str, object]] = []

        def callback(invocation):
            snapshots.append(self.reopen().journal.load())
            return ProviderAttemptResult(
                observation=self.observation(invocation),
                value={"ephemeral": "private provider value"},
            )

        result = self.execute("success", callback)
        validate_durable_effect_execution_receipt(result.receipt)
        self.assertEqual(result.value, {"ephemeral": "private provider value"})
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["issued_permit_count"], 1)
        self.assertEqual(snapshots[0]["settled_permit_count"], 0)
        final = self.reopen().journal.load()
        validate_effect_preauthorization_state(final, **self.shared)
        self.assertEqual(final["event_count"], 2)
        self.assertEqual(final["settled_permit_count"], 1)
        self.assertEqual(final["pending_permit_refs"], [])
        self.assertTrue(result.receipt["durable_permit_before_every_callback"])
        self.assertTrue(result.receipt["durable_settlement_after_all_callbacks"])
        self.assertNotIn("private provider value", repr(result.receipt))

    def test_caller_meter_mutation_during_callback_cannot_change_frozen_contract(self) -> None:
        meter = self.model_meter()
        original_sha = meter["contract_sha256"]

        def callback(invocation):
            meter["reserved_cost"]["input_tokens"] += 1
            meter["contract_sha256"] = digest("caller-mutated-meter")
            return ProviderAttemptResult(observation=self.observation(invocation))

        result = self.execute("meter-snapshot", callback, meter=meter)
        self.assertEqual(result.receipt["meter_contract_sha256"], original_sha)
        self.assertNotEqual(result.receipt["meter_contract_sha256"], meter["contract_sha256"])
        validate_durable_effect_execution_receipt(result.receipt)

    def test_recovery_status_marks_live_owned_permit_then_clears_after_settlement(self) -> None:
        observed: list[dict[str, object]] = []

        def callback(invocation):
            status = self.coordinator.recovery_status()
            validate_durable_effect_recovery_status(status)
            observed.append(status)
            return ProviderAttemptResult(observation=self.observation(invocation))

        self.execute("owned-status", callback)
        self.assertEqual(observed[0]["pending_permit_count"], 1)
        self.assertEqual(observed[0]["owned_live_pending_permit_count"], 1)
        self.assertEqual(
            observed[0]["quarantined_or_preexisting_pending_permit_count"], 0
        )
        final_status = self.coordinator.recovery_status()
        self.assertEqual(final_status["pending_permit_count"], 0)
        self.assertEqual(final_status["owned_live_pending_permit_count"], 0)

    def test_gpt56_single_attempt_adapter_is_one_post_between_durable_generations(self) -> None:
        response = FakeResponse(
            json.dumps(
                {
                    "id": "synthetic-response",
                    "output_text": "private synthetic answer",
                    "usage": {"input_tokens": 40, "output_tokens": 8},
                }
            ).encode("utf-8")
        )
        post = RecordingPost(response)
        meter = build_provider_meter_contract(
            provider_kind="azure_responses_model",
            charge_kind="renderer",
            max_attempts=1,
            reserved_cost=cost(
                model_calls=1,
                model_attempts=1,
                input_tokens=500,
                output_tokens=100,
                wall_milliseconds=300_000,
            ),
        )
        adapter = AzureResponsesSingleAttemptAdapter(
            endpoint="http://127.0.0.1:9878/responses",
            model="gpt-5.6-sol",
            timeout_seconds=300,
            post=post,
        )
        callback = adapter.bind(
            AzureResponsesRequest(
                system="private synthetic system",
                user="private synthetic prompt",
                max_output_tokens=100,
                json_mode=False,
                reasoning_effort="high",
                service_tier="priority",
            ),
            meter_contract=meter,
        )
        result = self.execute("gpt56-adapter", callback, meter=meter)
        validate_durable_effect_execution_receipt(result.receipt)
        self.assertEqual(len(post.calls), 1)
        self.assertEqual(result.value.text, "private synthetic answer")
        self.assertFalse(response.closed)
        self.assertEqual(self.coordinator.journal.load()["event_count"], 2)
        encoded = json.dumps(result.receipt)
        self.assertNotIn("private synthetic prompt", encoded)
        self.assertNotIn("private synthetic answer", encoded)

    def test_crash_after_durable_permit_never_calls_or_replays_callback(self) -> None:
        calls = 0

        def callback(_invocation):
            nonlocal calls
            calls += 1
            raise AssertionError("callback must not run before injected crash")

        def crash(stage: str) -> None:
            if stage == "after_durable_permit_before_callback":
                raise InjectedCrash(stage)

        with self.assertRaisesRegex(InjectedCrash, "durable_permit"):
            self.execute("pre-callback-crash", callback, fault_hook=crash)
        self.assertEqual(calls, 0)
        reopened = self.reopen()
        status = reopened.recovery_status()
        validate_durable_effect_recovery_status(status)
        self.assertEqual(status["pending_permit_count"], 1)
        self.assertEqual(status["quarantined_or_preexisting_pending_permit_count"], 1)
        self.assertFalse(status["automatic_pending_effect_replay_authorized"])
        with self.assertRaisesRegex(DurableEffectReplayRejected, "already"):
            self.execute("pre-callback-crash", callback, coordinator=reopened)
        self.assertEqual(calls, 0)

    def test_crash_after_callback_quarantines_unknown_effect_and_never_replays(self) -> None:
        calls = 0

        def callback(invocation):
            nonlocal calls
            calls += 1
            return ProviderAttemptResult(observation=self.observation(invocation))

        def crash(stage: str) -> None:
            if stage == "after_callback_before_observation_commit":
                raise InjectedCrash(stage)

        with self.assertRaisesRegex(InjectedCrash, "after_callback"):
            self.execute("post-callback-crash", callback, fault_hook=crash)
        self.assertEqual(calls, 1)
        reopened = self.reopen()
        self.assertEqual(reopened.recovery_status()["pending_permit_count"], 1)
        with self.assertRaises(DurableEffectReplayRejected):
            self.execute("post-callback-crash", callback, coordinator=reopened)
        self.assertEqual(calls, 1)

    def test_crash_after_durable_settlement_is_committed_and_not_replayed(self) -> None:
        calls = 0

        def callback(invocation):
            nonlocal calls
            calls += 1
            return ProviderAttemptResult(observation=self.observation(invocation))

        def crash(stage: str) -> None:
            if stage == "after_durable_settlement_before_return":
                raise InjectedCrash(stage)

        with self.assertRaisesRegex(InjectedCrash, "durable_settlement"):
            self.execute("post-settlement-crash", callback, fault_hook=crash)
        self.assertEqual(calls, 1)
        final = self.reopen().journal.load()
        self.assertEqual(final["settled_permit_count"], 1)
        self.assertEqual(final["pending_permit_refs"], [])
        with self.assertRaises(DurableEffectReplayRejected):
            self.execute("post-settlement-crash", callback, coordinator=self.reopen())
        self.assertEqual(calls, 1)

    def test_real_process_exit_at_three_crash_cuts_recovers_without_replay(self) -> None:
        if "fork" not in multiprocessing.get_all_start_methods():
            self.skipTest("requires POSIX fork")
        context = multiprocessing.get_context("fork")
        for index, stage in enumerate(
            (
                "after_durable_permit_before_callback",
                "after_callback_before_observation_commit",
                "after_durable_settlement_before_return",
            ),
            start=1,
        ):
            with self.subTest(stage=stage):
                namespace = digest(f"real-crash-namespace-{index}")
                coordinator = DurablePreauthorizedEffectCoordinator.initialize(
                    root=self.root,
                    journal_namespace_sha256=namespace,
                    initial_state=self.initial,
                    **self.coordinator_shared,
                )
                marker = self.root / f"callback-marker-{index}"
                invocation = digest(f"real-crash-invocation-{index}")
                process = context.Process(
                    target=crash_process_worker,
                    args=(
                        str(self.root),
                        namespace,
                        self.coordinator_shared,
                        self.model_meter(),
                        invocation,
                        stage,
                        str(marker),
                    ),
                )
                process.start()
                process.join(timeout=20)
                self.assertFalse(process.is_alive())
                self.assertEqual(process.exitcode, 73)
                reopened = DurablePreauthorizedEffectCoordinator(
                    root=self.root,
                    journal_namespace_sha256=namespace,
                    **self.coordinator_shared,
                )
                state = reopened.journal.load()
                if stage == "after_durable_settlement_before_return":
                    self.assertEqual(state["settled_permit_count"], 1)
                    self.assertEqual(state["pending_permit_refs"], [])
                else:
                    self.assertEqual(state["settled_permit_count"], 0)
                    self.assertEqual(len(state["pending_permit_refs"]), 1)
                self.assertEqual(
                    marker.exists(),
                    stage != "after_durable_permit_before_callback",
                )
                before = marker.read_text() if marker.exists() else None
                with self.assertRaises(DurableEffectReplayRejected):
                    reopened.run_effect(
                        meter_contract=self.model_meter(),
                        invocation_ref_sha256=invocation,
                        callback=lambda _invocation: marker.write_text(
                            "replayed", encoding="utf-8"
                        ),
                    )
                self.assertEqual(marker.read_text() if marker.exists() else None, before)

    def test_two_processes_same_invocation_execute_exactly_one_callback(self) -> None:
        if "fork" not in multiprocessing.get_all_start_methods():
            self.skipTest("requires POSIX fork and flock")
        context = multiprocessing.get_context("fork")
        gate = context.Barrier(2)
        callback_counter = context.Value("i", 0)
        outcomes = context.Queue()
        invocation = digest("same-cross-process-invocation")
        processes = [
            context.Process(
                target=race_process_worker,
                args=(
                    str(self.root),
                    self.namespace,
                    self.coordinator_shared,
                    self.model_meter(max_attempts=1),
                    invocation,
                    gate,
                    callback_counter,
                    outcomes,
                ),
            )
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(timeout=20)
            self.assertFalse(process.is_alive())
            self.assertEqual(process.exitcode, 0)
        observed = sorted(outcomes.get(timeout=5) for _ in processes)
        self.assertEqual(observed, ["completed", "rejected"])
        self.assertEqual(callback_counter.value, 1)
        final = self.reopen().journal.load()
        self.assertEqual(final["issued_permit_count"], 1)
        self.assertEqual(final["settled_permit_count"], 1)

    def test_post_settlement_local_error_reports_committed_not_pending(self) -> None:
        original_settle = self.coordinator._settle

        def settle_then_raise(**kwargs):
            original_settle(**kwargs)
            raise RuntimeError("lost local return after durable settlement")

        self.coordinator._settle = settle_then_raise  # type: ignore[method-assign]
        with self.assertRaises(DurableEffectExecutionError) as caught:
            self.execute(
                "settlement-return-loss",
                lambda invocation: ProviderAttemptResult(
                    observation=self.observation(invocation)
                ),
            )
        receipt = caught.exception.receipt
        validate_durable_effect_failure_receipt(receipt)
        self.assertTrue(receipt["settlement_durably_committed"])
        self.assertFalse(receipt["permit_may_remain_pending"])
        self.assertTrue(receipt["reservation_remains_charged"])
        final = self.reopen().journal.load()
        self.assertEqual(final["settled_permit_count"], 1)
        self.assertEqual(final["pending_permit_refs"], [])

    def test_same_invocation_changed_meter_is_rejected_before_callback(self) -> None:
        calls = 0

        def callback(invocation):
            nonlocal calls
            calls += 1
            return ProviderAttemptResult(observation=self.observation(invocation))

        self.execute("meter-binding", callback)
        changed = self.model_meter(input_tokens=2000)
        with self.assertRaises(DurableEffectReplayRejected):
            self.execute("meter-binding", callback, meter=changed, coordinator=self.reopen())
        self.assertEqual(calls, 1)

    def test_callback_exception_is_sanitized_charged_and_quarantined(self) -> None:
        def callback(_invocation):
            raise RuntimeError("private provider body https://secret.invalid")

        with self.assertRaises(DurableEffectExecutionError) as caught:
            self.execute("callback-failure", callback)
        receipt = caught.exception.receipt
        validate_durable_effect_failure_receipt(receipt)
        self.assertEqual(receipt["failure_phase"], "callback_exception")
        self.assertEqual(receipt["completed_callback_count"], 0)
        self.assertTrue(receipt["provider_effect_may_have_occurred"])
        self.assertFalse(receipt["automatic_whole_effect_replay_authorized"])
        self.assertNotIn("secret.invalid", repr(receipt))
        state = self.coordinator.journal.load()
        self.assertEqual(state["pending_permit_refs"], [receipt["permit_ref_sha256"]])

    def test_invalid_observation_counts_completed_callback_but_not_valid_attempt(self) -> None:
        def callback(invocation):
            observation = self.observation(invocation)
            observation["execution_challenge_sha256"] = digest("wrong")
            return ProviderAttemptResult(observation=observation)

        with self.assertRaises(DurableEffectExecutionError) as caught:
            self.execute("bad-observation", callback)
        receipt = caught.exception.receipt
        validate_durable_effect_failure_receipt(receipt)
        self.assertEqual(receipt["completed_callback_count"], 1)
        self.assertEqual(len(receipt["attempt_invocation_sha256s"]), 1)
        self.assertEqual(receipt["attempt_sha256s"], [])

    def test_retry_sequence_is_bounded_then_durably_settles(self) -> None:
        indices: list[int] = []

        def callback(invocation):
            indices.append(int(invocation["attempt_index"]))
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

        result = self.execute("retry", callback)
        self.assertEqual(indices, [1, 2])
        self.assertEqual(result.receipt["attempt_count"], 2)
        self.assertEqual(self.coordinator.journal.load()["settled_permit_count"], 1)

    def test_unrelated_effect_can_complete_while_old_pending_is_quarantined(self) -> None:
        def crash(stage: str) -> None:
            if stage == "after_durable_permit_before_callback":
                raise InjectedCrash(stage)

        with self.assertRaises(InjectedCrash):
            self.execute("old-pending", lambda _invocation: None, fault_hook=crash)
        reopened = self.reopen()
        result = self.execute(
            "unrelated",
            lambda invocation: ProviderAttemptResult(
                observation=self.observation(invocation)
            ),
            coordinator=reopened,
        )
        validate_durable_effect_execution_receipt(result.receipt)
        final = reopened.journal.load()
        self.assertEqual(final["issued_permit_count"], 2)
        self.assertEqual(final["settled_permit_count"], 1)
        self.assertEqual(len(final["pending_permit_refs"]), 1)

    def test_two_callbacks_can_overlap_after_independent_durable_permits(self) -> None:
        barrier = threading.Barrier(2)
        observed: list[dict[str, object]] = []
        lock = threading.Lock()

        def run(suffix: str):
            def callback(invocation):
                state = self.reopen().journal.load()
                with lock:
                    observed.append(state)
                barrier.wait(timeout=10)
                return ProviderAttemptResult(observation=self.observation(invocation))

            return self.execute(suffix, callback)

        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(run, "parallel-a")
            second = pool.submit(run, "parallel-b")
            first_result = first.result(timeout=20)
            second_result = second.result(timeout=20)
        self.assertEqual(len(observed), 2)
        self.assertTrue(all(state["issued_permit_count"] >= 1 for state in observed))
        validate_durable_effect_execution_receipt(first_result.receipt)
        validate_durable_effect_execution_receipt(second_result.receipt)
        final = self.coordinator.journal.load()
        self.assertEqual(final["issued_permit_count"], 2)
        self.assertEqual(final["settled_permit_count"], 2)

    def test_journal_files_contain_no_invocation_measurement_or_callback_value(self) -> None:
        private = "private-value-not-for-disk"
        result = self.execute(
            "disk-boundary",
            lambda invocation: ProviderAttemptResult(
                observation=self.observation(invocation),
                value=private,
            ),
        )
        self.assertEqual(result.value, private)
        payload = b"".join(
            path.read_bytes()
            for path in sorted(self.coordinator.journal.directory.rglob("*"))
            if path.is_file()
        )
        for forbidden in (
            private.encode(),
            b"attempt_invocation_sha256",
            b"measurement_sha256",
            b"execution_challenge_sha256",
        ):
            self.assertNotIn(forbidden, payload)

    def test_receipt_tamper_and_reseal_fail_closed(self) -> None:
        result = self.execute(
            "tamper",
            lambda invocation: ProviderAttemptResult(
                observation=self.observation(invocation)
            ),
        )
        tampered = copy.deepcopy(result.receipt)
        tampered["measurement"]["settlement_cost"]["input_tokens"] += 1
        tampered.pop("execution_receipt_sha256")
        tampered["execution_receipt_sha256"] = object_sha256(tampered)
        with self.assertRaisesRegex(ValueError, "embedded execution graph"):
            validate_durable_effect_execution_receipt(tampered)

        def callback(_invocation):
            raise RuntimeError("private")

        with self.assertRaises(DurableEffectExecutionError) as caught:
            self.execute("failure-tamper", callback)
        failure = copy.deepcopy(caught.exception.receipt)
        failure["automatic_whole_effect_replay_authorized"] = True
        failure.pop("failure_receipt_sha256")
        failure["failure_receipt_sha256"] = object_sha256(failure)
        with self.assertRaisesRegex(ValueError, "failure receipt drifted"):
            validate_durable_effect_failure_receipt(failure)

        commit_tampered = copy.deepcopy(result.receipt)
        commit_tampered["settlement_commit"]["generation"] += 1
        commit_tampered.pop("execution_receipt_sha256")
        commit_tampered["execution_receipt_sha256"] = object_sha256(
            commit_tampered
        )
        with self.assertRaisesRegex(ValueError, "execution receipt drifted"):
            validate_durable_effect_execution_receipt(commit_tampered)

        event_tampered = copy.deepcopy(result.receipt)
        event_tampered["settlement_event"]["actual_cost"]["input_tokens"] += 1
        event_tampered["settlement_event"].pop("settlement_sha256")
        event_tampered["settlement_event"]["settlement_sha256"] = object_sha256(
            event_tampered["settlement_event"]
        )
        event_tampered.pop("execution_receipt_sha256")
        event_tampered["execution_receipt_sha256"] = object_sha256(event_tampered)
        with self.assertRaisesRegex(ValueError, "execution receipt drifted"):
            validate_durable_effect_execution_receipt(event_tampered)

        failure_graph = copy.deepcopy(caught.exception.receipt)
        failure_graph["admission_commit"]["entry_sha256"] = digest("forged")
        failure_graph.pop("failure_receipt_sha256")
        failure_graph["failure_receipt_sha256"] = object_sha256(failure_graph)
        with self.assertRaisesRegex(ValueError, "failure receipt drifted"):
            validate_durable_effect_failure_receipt(failure_graph)

    def test_reference_derivation_is_namespace_and_invocation_bound(self) -> None:
        first = derive_effect_references(
            journal_namespace_sha256=self.namespace,
            invocation_ref_sha256=digest("same-invocation"),
        )
        repeated = derive_effect_references(
            journal_namespace_sha256=self.namespace,
            invocation_ref_sha256=digest("same-invocation"),
        )
        other_namespace = derive_effect_references(
            journal_namespace_sha256=digest("other-namespace"),
            invocation_ref_sha256=digest("same-invocation"),
        )
        self.assertEqual(first, repeated)
        self.assertNotEqual(first, other_namespace)
        self.assertNotEqual(first["permit_ref_sha256"], first["charge_ref_sha256"])

    def test_authorization_and_remaining_risks_are_explicit(self) -> None:
        for value in (
            PRODUCTION_PACKAGE_AUTHORIZED,
            ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            EXTERNAL_SIDE_EFFECT_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
            PREEXISTING_PENDING_PERMIT_AUTOMATIC_REPLAY_IMPLEMENTED,
            CALLBACK_OR_SETTLEMENT_FAILURE_AUTOMATIC_REPLAY_IMPLEMENTED,
            CALLBACK_TIMEOUT_IMPLEMENTED,
            RETRY_BACKOFF_IMPLEMENTED,
            TOTAL_WALL_DEADLINE_IMPLEMENTED,
            ATTEMPT_MEASUREMENT_DURABLY_PERSISTED,
            NETWORK_OR_DISTRIBUTED_FILESYSTEM_SEMANTICS_PROVEN,
        ):
            self.assertFalse(value)
        self.assertTrue(LOCAL_POSIX_CRASH_DURABLE_EFFECT_ORDERING_IMPLEMENTED)


if __name__ == "__main__":
    unittest.main()
