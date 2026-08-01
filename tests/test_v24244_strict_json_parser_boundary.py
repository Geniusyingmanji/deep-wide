from __future__ import annotations

import copy
import hashlib
import sys
import tempfile
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
from deepwide_agent.v24236_azure_responses_single_attempt import (  # noqa: E402
    AzureResponsesAttemptValue,
)
from deepwide_agent.v24237_tavily_search_single_attempt import (  # noqa: E402
    TavilySearchAttemptValue,
)
from deepwide_agent.v24242_durable_effect_coordinator import (  # noqa: E402
    DurablePreauthorizedEffectCoordinator,
)
from deepwide_agent.v24243_retry_deadline_scheduler import (  # noqa: E402
    RetryDeadlineEffectScheduler,
    RetryDeadlineExecutionResult,
    build_retry_deadline_contract,
)
from deepwide_agent.v24244_strict_json_parser_boundary import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    DUPLICATE_KEY_REJECTION_IMPLEMENTED,
    EXACT_OBJECT_OR_WHOLE_FENCE_ONLY_IMPLEMENTED,
    EPHEMERAL_TEXT_TO_PARENT_RESPONSE_BINDING_INDEPENDENTLY_VERIFIED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    INTERNAL_REPAIR_PROVIDER_EFFECT_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    NESTED_PRIVILEGED_METADATA_REJECTION_IMPLEMENTED,
    NONFINITE_NUMBER_REJECTION_IMPLEMENTED,
    POST_DURABLE_SETTLEMENT_PARSE_BOUNDARY_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SEARCH_OR_PAGE_PARSER_INTEGRATION_IMPLEMENTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    STRUCTURAL_BUDGET_IMPLEMENTED,
    StrictJsonParserBoundaryError,
    build_strict_json_parser_contract,
    parse_settled_model_json,
    validate_strict_json_parser_contract,
    validate_strict_json_parser_receipt,
)
from tests.test_v24232_webswarm_total_budget import (  # noqa: E402
    contract,
    guidance,
    ledger,
)


def digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class VirtualClock:
    def __init__(self) -> None:
        self.now_ns = 10_000_000_000

    def monotonic_ns(self) -> int:
        return self.now_ns

    def sleep(self, seconds: float) -> None:
        self.now_ns += int(round(seconds * 1_000_000_000))

    def advance_ms(self, milliseconds: int) -> None:
        self.now_ns += milliseconds * 1_000_000


class V24244StrictJsonParserBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.root = Path(self.temporary.name).resolve()
        self.guidance_contract = contract()
        self.policy, _, arms, sources = guidance(self.guidance_contract)
        self.arm = next(arm for arm in arms if arm["arm_name"] == "full")
        self.source = sources["full"]
        initial = initialize_effect_preauthorization_state(
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
            journal_namespace_sha256=digest("v24244-journal"),
            initial_state=initial,
            **self.coordinator_shared,
        )
        self.clock = VirtualClock()
        self.scheduler = RetryDeadlineEffectScheduler(
            coordinator=self.coordinator,
            monotonic_ns=self.clock.monotonic_ns,
            sleeper=self.clock.sleep,
        )
        self.meter = build_provider_meter_contract(
            provider_kind="azure_responses_model",
            charge_kind="renderer",
            max_attempts=1,
            reserved_cost=build_cost_vector(
                model_calls=1,
                model_attempts=1,
                search_calls=0,
                fetch_calls=0,
                other_tool_calls=0,
                orchestrator_calls=0,
                input_tokens=1000,
                output_tokens=500,
                wall_milliseconds=1000,
            ),
        )
        self.schedule = build_retry_deadline_contract(
            meter_contract=self.meter,
            total_deadline_milliseconds=500,
            minimum_attempt_window_milliseconds=50,
            initial_backoff_milliseconds=10,
            backoff_multiplier=2,
            maximum_backoff_milliseconds=100,
        )
        self.parser_contract = build_strict_json_parser_contract(
            maximum_text_characters=2000,
            maximum_utf8_bytes=4000,
            maximum_depth=8,
            maximum_nodes=100,
            maximum_object_members=20,
            maximum_array_items=20,
            maximum_string_characters=500,
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

    def settled(self, text: str, *, suffix: str, truncated: bool = False):
        def callback(invocation):
            self.clock.advance_ms(1)
            observation = build_provider_attempt_observation(
                invocation=invocation,
                outcome="success",
                http_status=200,
                provider_response_ref_sha256=digest(f"response-{suffix}"),
                token_usage_state=USAGE_OBSERVED,
                input_tokens=20,
                output_tokens=5,
                provider_tool_usage_state=USAGE_NOT_APPLICABLE,
                provider_tool_calls=None,
                request_body_bytes=64,
                response_body_bytes=len(text.encode("utf-8")),
            )
            return ProviderAttemptResult(
                observation=observation,
                value=AzureResponsesAttemptValue(
                    text=text,
                    usage={"input_tokens": 20, "output_tokens": 5},
                    response_id="synthetic-response",
                    output_truncated=truncated,
                ),
            )

        return self.scheduler.run_effect(
            meter_contract=self.meter,
            scheduler_contract=self.schedule,
            invocation_ref_sha256=digest(f"invocation-{suffix}"),
            callback=callback,
        )

    def parse(self, text: str, *, suffix: str):
        return parse_settled_model_json(
            self.settled(text, suffix=suffix),
            parser_contract=self.parser_contract,
        )

    def test_contract_is_exact_sealed_and_fail_closed(self) -> None:
        validate_strict_json_parser_contract(self.parser_contract)
        self.assertEqual(
            self.parser_contract["accepted_envelopes"],
            ["exact_json_object", "whole_response_json_fence"],
        )
        self.assertFalse(
            self.parser_contract["internal_repair_provider_effect_authorized"]
        )
        tampered = copy.deepcopy(self.parser_contract)
        tampered["maximum_depth"] += 1
        with self.assertRaisesRegex(ValueError, "drifted"):
            validate_strict_json_parser_contract(tampered)

    def test_exact_object_is_parsed_only_after_durable_settlement(self) -> None:
        result = self.parse(
            '{"rows":[{"name":"alpha","count":2}],"ready":true}',
            suffix="exact",
        )
        validate_strict_json_parser_receipt(result.receipt)
        self.assertEqual(result.value["rows"][0]["name"], "alpha")
        self.assertTrue(result.value["ready"])
        self.assertTrue(result.receipt["post_durable_settlement_parse_boundary"])
        self.assertEqual(result.receipt["envelope_kind"], "exact_json_object")
        self.assertEqual(self.coordinator.journal.load()["settled_permit_count"], 1)
        encoded = repr(result.receipt)
        self.assertNotIn("alpha", encoded)
        self.assertNotIn("rows", encoded)

    def test_whole_json_fence_is_accepted_but_partial_fences_are_rejected(self) -> None:
        accepted = self.parse(
            '```json\n{"answer":{"value":3}}\n```',
            suffix="fence",
        )
        self.assertEqual(accepted.value["answer"]["value"], 3)
        self.assertEqual(
            accepted.receipt["envelope_kind"], "whole_response_json_fence"
        )
        for index, text in enumerate(
            (
                'prefix {"value":1}',
                '{"value":1} suffix',
                'prefix ```json\n{"value":1}\n```',
                '```python\n{"value":1}\n```',
            )
        ):
            with self.subTest(text=text):
                with self.assertRaises(StrictJsonParserBoundaryError):
                    self.parse(text, suffix=f"partial-{index}")

    def test_duplicate_keys_are_rejected_at_every_depth(self) -> None:
        for index, text in enumerate(
            (
                '{"x":1,"x":2}',
                '{"outer":{"x":1,"x":2}}',
                '{"foo-bar":1,"foo_bar":2}',
            )
        ):
            with self.subTest(text=text):
                with self.assertRaisesRegex(
                    StrictJsonParserBoundaryError, "duplicate"
                ):
                    self.parse(text, suffix=f"duplicate-{index}")

    def test_nonfinite_numbers_and_overflow_are_rejected(self) -> None:
        for index, text in enumerate(
            ('{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', '{"x":1e9999}')
        ):
            with self.subTest(text=text):
                with self.assertRaisesRegex(
                    StrictJsonParserBoundaryError, "non-finite"
                ):
                    self.parse(text, suffix=f"nonfinite-{index}")

    def test_nested_privileged_metadata_is_rejected_after_normalization(self) -> None:
        for index, key in enumerate(
            (
                "ground_truth",
                "Ground-Truth",
                "question type",
                "evaluatorScore",
                "task-id",
                "ｇｒｏｕｎｄ＿ｔｒｕｔｈ",
                "nested_label",
            )
        ):
            actual_key = key if key != "nested_label" else "label"
            text = '{"outer":{"' + actual_key + '":"private"}}'
            with self.subTest(key=key):
                with self.assertRaisesRegex(
                    StrictJsonParserBoundaryError, "privileged"
                ):
                    self.parse(text, suffix=f"privileged-{index}")

    def test_structural_budgets_reject_depth_nodes_members_arrays_and_strings(self) -> None:
        small = build_strict_json_parser_contract(
            maximum_text_characters=1000,
            maximum_utf8_bytes=2000,
            maximum_depth=3,
            maximum_nodes=6,
            maximum_object_members=2,
            maximum_array_items=2,
            maximum_string_characters=5,
        )
        cases = (
            ('{"a":{"b":{"c":1}}}', "depth"),
            ('{"a":[1,2,3]}', "array"),
            ('{"a":1,"b":2,"c":3}', "member"),
            ('{"abcdef":1}', "string"),
            ('{"a":"abcdef"}', "string"),
            ('{"a":[1,2],"b":[3,4]}', "node"),
        )
        for index, (text, reason) in enumerate(cases):
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(StrictJsonParserBoundaryError, reason):
                    parse_settled_model_json(
                        self.settled(text, suffix=f"budget-{index}"),
                        parser_contract=small,
                    )

    def test_text_character_utf8_and_truncation_limits_fail_closed(self) -> None:
        character_contract = build_strict_json_parser_contract(
            maximum_text_characters=10,
            maximum_utf8_bytes=100,
            maximum_depth=4,
            maximum_nodes=20,
            maximum_object_members=4,
            maximum_array_items=4,
            maximum_string_characters=5,
        )
        with self.assertRaisesRegex(StrictJsonParserBoundaryError, "character"):
            parse_settled_model_json(
                self.settled('{"x":"12345"}', suffix="char-limit"),
                parser_contract=character_contract,
            )
        byte_contract = build_strict_json_parser_contract(
            maximum_text_characters=20,
            maximum_utf8_bytes=10,
            maximum_depth=4,
            maximum_nodes=20,
            maximum_object_members=4,
            maximum_array_items=4,
            maximum_string_characters=5,
        )
        with self.assertRaisesRegex(StrictJsonParserBoundaryError, "byte"):
            parse_settled_model_json(
                self.settled('{"x":"中文"}', suffix="byte-limit"),
                parser_contract=byte_contract,
            )
        with self.assertRaisesRegex(StrictJsonParserBoundaryError, "truncated"):
            parse_settled_model_json(
                self.settled('{"x":1}', suffix="truncated", truncated=True),
                parser_contract=self.parser_contract,
            )

    def test_wrong_provider_value_type_is_rejected(self) -> None:
        valid = self.settled('{"x":1}', suffix="wrong-value")
        wrong = RetryDeadlineExecutionResult(
            receipt=valid.receipt,
            value=TavilySearchAttemptValue(
                query="synthetic query",
                answer="synthetic answer",
                results=(),
            ),
        )
        with self.assertRaisesRegex(StrictJsonParserBoundaryError, "type"):
            parse_settled_model_json(
                wrong,
                parser_contract=self.parser_contract,
            )

    def test_same_type_text_substitution_is_disclosed_as_unverified(self) -> None:
        valid = self.settled('{"original":true}', suffix="text-binding")
        substituted = RetryDeadlineExecutionResult(
            receipt=valid.receipt,
            value=AzureResponsesAttemptValue(
                text='{"substituted":true}',
                usage=valid.value.usage,
                response_id=valid.value.response_id,
                output_truncated=False,
            ),
        )
        parsed = parse_settled_model_json(
            substituted,
            parser_contract=self.parser_contract,
        )
        self.assertTrue(parsed.value["substituted"])
        self.assertFalse(
            parsed.receipt[
                "ephemeral_text_to_parent_response_binding_independently_verified"
            ]
        )

    def test_ephemeral_usage_must_match_parent_attempt(self) -> None:
        valid = self.settled('{"x":1}', suffix="usage-binding")
        changed = RetryDeadlineExecutionResult(
            receipt=valid.receipt,
            value=AzureResponsesAttemptValue(
                text=valid.value.text,
                usage={"input_tokens": 21, "output_tokens": 5},
                response_id=valid.value.response_id,
                output_truncated=False,
            ),
        )
        with self.assertRaisesRegex(StrictJsonParserBoundaryError, "accounting"):
            parse_settled_model_json(
                changed,
                parser_contract=self.parser_contract,
            )

    def test_invalid_or_resealed_scheduler_receipt_is_rejected(self) -> None:
        valid = self.settled('{"x":1}', suffix="scheduler-tamper")
        tampered_receipt = copy.deepcopy(valid.receipt)
        tampered_receipt["parent_execution_receipt"]["logical_status"] = "failed"
        tampered_receipt.pop("execution_receipt_sha256")
        tampered_receipt["execution_receipt_sha256"] = object_sha256(
            tampered_receipt
        )
        tampered = RetryDeadlineExecutionResult(
            receipt=tampered_receipt,
            value=valid.value,
        )
        with self.assertRaisesRegex(StrictJsonParserBoundaryError, "scheduler"):
            parse_settled_model_json(
                tampered,
                parser_contract=self.parser_contract,
            )

    def test_parse_failure_does_not_call_repair_or_add_effect(self) -> None:
        settled = self.settled('{"broken":', suffix="no-repair")
        before = self.coordinator.journal.load()
        with self.assertRaises(StrictJsonParserBoundaryError):
            parse_settled_model_json(
                settled,
                parser_contract=self.parser_contract,
            )
        after = self.coordinator.journal.load()
        self.assertEqual(after["event_count"], before["event_count"])
        self.assertEqual(after["state_sha256"], before["state_sha256"])
        self.assertEqual(after["issued_permit_count"], 1)
        self.assertEqual(after["settled_permit_count"], 1)

    def test_parser_receipt_tamper_and_reseal_fail_closed(self) -> None:
        parsed = self.parse('{"x":1}', suffix="receipt-tamper")
        tampered = copy.deepcopy(parsed.receipt)
        tampered["node_count"] += 1
        tampered.pop("parser_receipt_sha256")
        tampered["parser_receipt_sha256"] = object_sha256(tampered)
        with self.assertRaisesRegex(ValueError, "drifted"):
            validate_strict_json_parser_receipt(tampered)

    def test_standalone_receipt_revalidates_embedded_scheduler_graph(self) -> None:
        parsed = self.parse('{"x":1}', suffix="embedded-parent")
        tampered = copy.deepcopy(parsed.receipt)
        tampered["scheduler_execution_receipt"]["parent_logical_status"] = "failed"
        tampered["scheduler_execution_receipt"].pop("execution_receipt_sha256")
        tampered["scheduler_execution_receipt"]["execution_receipt_sha256"] = (
            object_sha256(tampered["scheduler_execution_receipt"])
        )
        tampered.pop("parser_receipt_sha256")
        tampered["parser_receipt_sha256"] = object_sha256(tampered)
        with self.assertRaises(ValueError):
            validate_strict_json_parser_receipt(tampered)

    def test_capability_flags_are_exact(self) -> None:
        for flag in (
            POST_DURABLE_SETTLEMENT_PARSE_BOUNDARY_IMPLEMENTED,
            EXACT_OBJECT_OR_WHOLE_FENCE_ONLY_IMPLEMENTED,
            DUPLICATE_KEY_REJECTION_IMPLEMENTED,
            NONFINITE_NUMBER_REJECTION_IMPLEMENTED,
            STRUCTURAL_BUDGET_IMPLEMENTED,
            NESTED_PRIVILEGED_METADATA_REJECTION_IMPLEMENTED,
        ):
            self.assertTrue(flag)
        for flag in (
            INTERNAL_REPAIR_PROVIDER_EFFECT_IMPLEMENTED,
            SEARCH_OR_PAGE_PARSER_INTEGRATION_IMPLEMENTED,
            EPHEMERAL_TEXT_TO_PARENT_RESPONSE_BINDING_INDEPENDENTLY_VERIFIED,
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
