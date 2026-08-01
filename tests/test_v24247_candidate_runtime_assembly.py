from __future__ import annotations

import copy
import hashlib
import inspect
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
    build_provider_meter_contract,
)
from deepwide_agent.v24236_azure_responses_single_attempt import (  # noqa: E402
    AzureResponsesRequest,
    AzureResponsesSingleAttemptAdapter,
)
from deepwide_agent.v24237_tavily_search_single_attempt import (  # noqa: E402
    TavilySearchRequest,
    TavilySearchSingleAttemptAdapter,
)
from deepwide_agent.v24239_azure_hosted_search_single_attempt import (  # noqa: E402
    AzureHostedSearchRequest,
    AzureHostedSearchSingleAttemptAdapter,
)
from deepwide_agent.v24240_anthropic_server_search_single_attempt import (  # noqa: E402
    AnthropicServerSearchRequest,
    AnthropicServerSearchSingleAttemptAdapter,
)
from deepwide_agent.v24242_durable_effect_coordinator import (  # noqa: E402
    DurablePreauthorizedEffectCoordinator,
)
from deepwide_agent.v24243_retry_deadline_scheduler import (  # noqa: E402
    RetryDeadlineEffectScheduler,
    build_retry_deadline_contract,
)
from deepwide_agent.v24244_strict_json_parser_boundary import (  # noqa: E402
    build_strict_json_parser_contract,
)
from deepwide_agent.v24245_pinned_native_http_fetch import (  # noqa: E402
    NativeHttpFetchRequest,
    PinnedNativeHttpFetchAdapter,
)
from deepwide_agent.v24246_search_page_projection import (  # noqa: E402
    PageTextProjection,
    SearchLeadProjection,
    build_search_page_projection_contract,
)
from deepwide_agent.v24247_candidate_runtime_assembly import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED,
    ALL_EFFECTS_ROUTED_THROUGH_DURABLE_DEADLINE_SCHEDULER,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLER_SUPPLIED_CALLBACK_INTERFACE_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    KNOWN_ADAPTER_EXACT_TYPE_ENFORCEMENT_IMPLEMENTED,
    KNOWN_REQUEST_EXACT_TYPE_ENFORCEMENT_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    POST_SETTLEMENT_TYPED_PROCESSING_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SCHEMA_RESEALING_WITHOUT_SECRET_CRYPTOGRAPHICALLY_EXCLUDED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    CandidateRuntimeAssembly,
    CandidateRuntimeAssemblyError,
    build_candidate_runtime_assembly_contract,
    validate_candidate_runtime_assembly_contract,
    validate_candidate_runtime_assembly_receipt,
)
from tests.test_v24232_webswarm_total_budget import (  # noqa: E402
    contract,
    guidance,
    ledger,
)
from tests.test_v24236_azure_responses_single_attempt import (  # noqa: E402
    FakeResponse as ModelResponse,
    RecordingPost as ModelPost,
    response_bytes as model_response_bytes,
)
from tests.test_v24237_tavily_search_single_attempt import (  # noqa: E402
    FakeResponse as TavilyResponse,
    RecordingPost as TavilyPost,
    response_bytes as tavily_response_bytes,
)
from tests.test_v24239_azure_hosted_search_single_attempt import (  # noqa: E402
    FakeResponse as HostedResponse,
    RecordingPost as HostedPost,
    response_bytes as hosted_response_bytes,
)
from tests.test_v24240_anthropic_server_search_single_attempt import (  # noqa: E402
    FakeResponse as AnthropicResponse,
    RecordingPost as AnthropicPost,
    response_bytes as anthropic_response_bytes,
)
from tests.test_v24245_pinned_native_http_fetch import (  # noqa: E402
    FakeResponse as FetchResponse,
    RecordingPoolFactory,
    RecordingResolver,
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


class V24247CandidateRuntimeAssemblyTests(unittest.TestCase):
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
        coordinator = DurablePreauthorizedEffectCoordinator.initialize(
            root=self.root,
            journal_namespace_sha256=digest("v24247-journal"),
            initial_state=initial,
            **self.coordinator_shared,
        )
        self.coordinator = coordinator
        self.clock = VirtualClock()
        scheduler = RetryDeadlineEffectScheduler(
            coordinator=coordinator,
            monotonic_ns=self.clock.monotonic_ns,
            sleeper=self.clock.sleep,
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
        self.projection_contract = build_search_page_projection_contract(
            maximum_leads=8,
            maximum_page_bytes=4096,
            maximum_page_text_characters=500,
            maximum_title_characters=100,
            maximum_url_characters=1024,
            maximum_html_tags=100,
        )
        self.assembly_contract = build_candidate_runtime_assembly_contract(
            model_parser_contract=self.parser_contract,
            search_page_projection_contract=self.projection_contract,
        )
        self.runtime = CandidateRuntimeAssembly(
            scheduler=scheduler,
            assembly_contract=self.assembly_contract,
        )
        self.counter = 0

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
    def meter(provider_kind: str, *, output_reservation: int = 200):
        values = {
            "model_calls": 0,
            "model_attempts": 0,
            "search_calls": 0,
            "fetch_calls": 0,
            "other_tool_calls": 0,
            "orchestrator_calls": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "wall_milliseconds": 1000,
        }
        if provider_kind == "azure_responses_model":
            values.update(
                model_calls=1,
                model_attempts=1,
                input_tokens=1000,
                output_tokens=output_reservation,
            )
            charge = "renderer"
        elif provider_kind == "native_http_fetch":
            values["fetch_calls"] = 1
            charge = "fanout_execution"
        elif provider_kind == "tavily_search_api":
            values["search_calls"] = 1
            charge = "fanout_execution"
        else:
            values.update(
                search_calls=1,
                other_tool_calls=2,
                input_tokens=1000,
                output_tokens=output_reservation,
            )
            charge = "fanout_execution"
        return build_provider_meter_contract(
            provider_kind=provider_kind,
            charge_kind=charge,
            max_attempts=1,
            reserved_cost=build_cost_vector(**values),
        )

    @staticmethod
    def schedule(meter):
        return build_retry_deadline_contract(
            meter_contract=meter,
            total_deadline_milliseconds=500,
            minimum_attempt_window_milliseconds=50,
            initial_backoff_milliseconds=10,
            backoff_multiplier=2,
            maximum_backoff_milliseconds=100,
        )

    def invocation(self, label: str) -> str:
        self.counter += 1
        return digest(f"{label}-{self.counter}")

    def test_contract_freezes_five_exact_typed_routes(self) -> None:
        validate_candidate_runtime_assembly_contract(self.assembly_contract)
        routes = self.assembly_contract["operation_adapter_request_provider_map"]
        self.assertEqual(len(routes), 5)
        self.assertEqual(
            {row["provider_kind"] for row in routes},
            {
                "azure_responses_model",
                "tavily_search_api",
                "azure_responses_web_search",
                "anthropic_server_web_search",
                "native_http_fetch",
            },
        )
        tampered = copy.deepcopy(self.assembly_contract)
        tampered["caller_supplied_callback_authorized"] = True
        with self.assertRaisesRegex(ValueError, "drifted"):
            validate_candidate_runtime_assembly_contract(tampered)

    def test_model_runs_durably_then_returns_ephemeral_strict_json(self) -> None:
        private = "PRIVATE_MODEL_VALUE"
        post = ModelPost(
            ModelResponse(
                200,
                model_response_bytes(
                    text='{"ready":true,"value":"' + private + '"}',
                    input_tokens=20,
                    output_tokens=5,
                ),
            )
        )
        adapter = AzureResponsesSingleAttemptAdapter(
            endpoint="http://127.0.0.1:9878/responses",
            model="gpt-5.6-sol",
            timeout_seconds=1,
            post=post,
        )
        request = AzureResponsesRequest(
            system="private system prompt",
            user="private user prompt",
            max_output_tokens=200,
            json_mode=True,
            reasoning_effort="high",
            service_tier="priority",
        )
        meter = self.meter("azure_responses_model")
        result = self.runtime.run_model_json(
            adapter=adapter,
            request=request,
            meter_contract=meter,
            scheduler_contract=self.schedule(meter),
            invocation_ref_sha256=self.invocation("model"),
        )
        validate_candidate_runtime_assembly_receipt(result.receipt)
        self.assertEqual(result.value["value"], private)
        self.assertEqual(len(post.calls), 1)
        self.assertEqual(result.receipt["operation_kind"], "model_json")
        self.assertFalse(
            result.receipt[
                "raw_provider_value_or_projected_output_entered_receipt"
            ]
        )
        self.assertFalse(
            result.receipt[
                "prompt_query_search_lead_url_page_text_or_parsed_json_present_in_receipt"
            ]
        )
        encoded = repr(result.receipt)
        for item in (private, "private system prompt", "private user prompt"):
            self.assertNotIn(item, encoded)

    def test_three_search_adapters_return_only_ephemeral_untrusted_leads(self) -> None:
        cases = []

        tavily_post = TavilyPost(
            TavilyResponse(
                200,
                tavily_response_bytes(
                    answer="PRIVATE_TAVILY_ANSWER",
                    results=[
                        {
                            "title": "Tavily title",
                            "url": "https://example.com/tavily",
                            "content": "PRIVATE_TAVILY_SNIPPET",
                            "raw_content": "PRIVATE_TAVILY_RAW",
                            "score": 0.9,
                        }
                    ],
                ),
            )
        )
        cases.append(
            (
                TavilySearchSingleAttemptAdapter(
                    endpoint="https://api.tavily.com/search",
                    credentials=("synthetic-credential",),
                    timeout_seconds=1,
                    post=tavily_post,
                ),
                TavilySearchRequest(query="visible query", max_results=1),
                "tavily_search_api",
                tavily_post,
                "PRIVATE_TAVILY_ANSWER",
            )
        )

        hosted_post = HostedPost(
            HostedResponse(
                200,
                hosted_response_bytes(
                    text="PRIVATE_HOSTED_ANSWER",
                    input_tokens=20,
                    output_tokens=5,
                    action_count=1,
                ),
            )
        )
        cases.append(
            (
                AzureHostedSearchSingleAttemptAdapter(
                    endpoint="http://127.0.0.1:9878/responses",
                    model="gpt-5.6-sol",
                    timeout_seconds=1,
                    post=hosted_post,
                ),
                AzureHostedSearchRequest(
                    queries=("visible query",),
                    max_output_tokens=200,
                ),
                "azure_responses_web_search",
                hosted_post,
                "PRIVATE_HOSTED_ANSWER",
            )
        )

        anthropic_post = AnthropicPost(
            AnthropicResponse(
                200,
                anthropic_response_bytes(
                    text="PRIVATE_ANTHROPIC_ANSWER",
                    input_tokens=15,
                    output_tokens=5,
                    cache_creation_tokens=3,
                    cache_read_tokens=2,
                    action_count=1,
                ),
            )
        )
        cases.append(
            (
                AnthropicServerSearchSingleAttemptAdapter(
                    endpoint="https://api.anthropic.com/v1/messages",
                    model="claude-haiku-4-5-20251001",
                    anthropic_version="2023-06-01",
                    credential="synthetic-anthropic-credential",
                    timeout_seconds=1,
                    post=anthropic_post,
                ),
                AnthropicServerSearchRequest(
                    query="visible query",
                    max_output_tokens=200,
                    max_uses=1,
                ),
                "anthropic_server_web_search",
                anthropic_post,
                "PRIVATE_ANTHROPIC_ANSWER",
            )
        )

        for adapter, request, provider, transport, private in cases:
            with self.subTest(provider=provider):
                meter = self.meter(provider)
                result = self.runtime.run_search_leads(
                    adapter=adapter,
                    request=request,
                    meter_contract=meter,
                    scheduler_contract=self.schedule(meter),
                    invocation_ref_sha256=self.invocation(provider),
                )
                validate_candidate_runtime_assembly_receipt(result.receipt)
                self.assertTrue(result.value)
                self.assertTrue(
                    all(isinstance(item, SearchLeadProjection) for item in result.value)
                )
                self.assertEqual(len(transport.calls), 1)
                self.assertEqual(result.receipt["operation_kind"], "search_leads")
                self.assertNotIn(private, repr(result.receipt))
                self.assertNotIn(private, repr(result.value))

    def test_pinned_fetch_runs_once_and_returns_ephemeral_untrusted_page(self) -> None:
        private = b"<html><body>PRIVATE_VISIBLE_FACT<script>PRIVATE_SCRIPT</script></body></html>"
        response = FetchResponse(
            200,
            [private],
            headers={"Content-Type": "text/html; charset=utf-8"},
        )
        resolver = RecordingResolver(("93.184.216.34",))
        factory = RecordingPoolFactory(response)
        adapter = PinnedNativeHttpFetchAdapter(
            timeout_seconds=1,
            max_response_bytes=4096,
            resolve=resolver,
            pool_factory=factory,
        )
        meter = self.meter("native_http_fetch")
        result = self.runtime.run_fetched_page(
            adapter=adapter,
            request=NativeHttpFetchRequest("https://example.com/page"),
            meter_contract=meter,
            scheduler_contract=self.schedule(meter),
            invocation_ref_sha256=self.invocation("fetch"),
        )
        validate_candidate_runtime_assembly_receipt(result.receipt)
        self.assertIsInstance(result.value, PageTextProjection)
        self.assertEqual(result.value.text, "PRIVATE_VISIBLE_FACT")
        self.assertFalse(result.value.instruction_authority)
        self.assertFalse(result.value.active_evidence_eligible)
        self.assertEqual(len(factory.pools), 1)
        self.assertEqual(len(factory.pools[0].urlopen_calls), 1)
        self.assertNotIn("PRIVATE_VISIBLE_FACT", repr(result.receipt))

    def test_wrong_adapter_request_and_meter_fail_before_effect(self) -> None:
        class Subclass(TavilySearchSingleAttemptAdapter):
            pass

        post = TavilyPost(
            TavilyResponse(200, tavily_response_bytes())
        )
        subclass = Subclass(
            endpoint="https://api.tavily.com/search",
            credentials=("synthetic-credential",),
            timeout_seconds=1,
            post=post,
        )
        request = TavilySearchRequest(query="visible", max_results=1)
        meter = self.meter("tavily_search_api")
        before = self.coordinator.journal.load()["state_sha256"]
        with self.assertRaises(CandidateRuntimeAssemblyError):
            self.runtime.run_search_leads(
                adapter=subclass,
                request=request,
                meter_contract=meter,
                scheduler_contract=self.schedule(meter),
                invocation_ref_sha256=self.invocation("subclass"),
            )
        adapter = TavilySearchSingleAttemptAdapter(
            endpoint="https://api.tavily.com/search",
            credentials=("synthetic-credential",),
            timeout_seconds=1,
            post=post,
        )
        wrong_meter = self.meter("native_http_fetch")
        with self.assertRaises(ValueError):
            self.runtime.run_search_leads(
                adapter=adapter,
                request=request,
                meter_contract=wrong_meter,
                scheduler_contract=self.schedule(wrong_meter),
                invocation_ref_sha256=self.invocation("wrong-meter"),
            )
        after = self.coordinator.journal.load()["state_sha256"]
        self.assertEqual(before, after)
        self.assertEqual(post.calls, [])

    def test_private_execute_rechecks_exact_types_before_binding(self) -> None:
        class Subclass(TavilySearchSingleAttemptAdapter):
            pass

        post = TavilyPost(TavilyResponse(200, tavily_response_bytes()))
        adapter = Subclass(
            endpoint="https://api.tavily.com/search",
            credentials=("synthetic-credential",),
            timeout_seconds=1,
            post=post,
        )
        request = TavilySearchRequest(query="visible", max_results=1)
        meter = self.meter("tavily_search_api")
        before = self.coordinator.journal.load()["state_sha256"]
        with self.assertRaisesRegex(CandidateRuntimeAssemblyError, "exact"):
            self.runtime._execute(
                operation_kind="search_leads",
                adapter=adapter,
                request=request,
                meter_contract=meter,
                scheduler_contract=self.schedule(meter),
                invocation_ref_sha256=self.invocation("private-subclass"),
            )
        after = self.coordinator.journal.load()["state_sha256"]
        self.assertEqual(before, after)
        self.assertEqual(post.calls, [])

    def test_binding_uses_frozen_exact_class_descriptor(self) -> None:
        post = TavilyPost(TavilyResponse(200, tavily_response_bytes()))
        adapter = TavilySearchSingleAttemptAdapter(
            endpoint="https://api.tavily.com/search",
            credentials=("synthetic-credential",),
            timeout_seconds=1,
            post=post,
        )
        instance_bind_called = False

        def instance_bind(*_args, **_kwargs):
            nonlocal instance_bind_called
            instance_bind_called = True
            raise AssertionError("instance-level bind dispatch must not occur")

        adapter.bind = instance_bind
        meter = self.meter("tavily_search_api")
        result = self.runtime.run_search_leads(
            adapter=adapter,
            request=TavilySearchRequest(query="visible", max_results=1),
            meter_contract=meter,
            scheduler_contract=self.schedule(meter),
            invocation_ref_sha256=self.invocation("class-descriptor-bind"),
        )
        validate_candidate_runtime_assembly_receipt(result.receipt)
        self.assertFalse(instance_bind_called)
        self.assertEqual(len(post.calls), 1)

    def test_public_methods_do_not_accept_callback_or_fault_hook(self) -> None:
        for name in ("run_model_json", "run_search_leads", "run_fetched_page"):
            parameters = inspect.signature(getattr(CandidateRuntimeAssembly, name)).parameters
            self.assertNotIn("callback", parameters)
            self.assertNotIn("fault_hook", parameters)
        self.assertNotIn("callback", inspect.signature(CandidateRuntimeAssembly).parameters)

    def test_receipt_tamper_and_reseal_fail_closed(self) -> None:
        post = TavilyPost(TavilyResponse(200, tavily_response_bytes()))
        adapter = TavilySearchSingleAttemptAdapter(
            endpoint="https://api.tavily.com/search",
            credentials=("synthetic-credential",),
            timeout_seconds=1,
            post=post,
        )
        meter = self.meter("tavily_search_api")
        result = self.runtime.run_search_leads(
            adapter=adapter,
            request=TavilySearchRequest(query="visible", max_results=1),
            meter_contract=meter,
            scheduler_contract=self.schedule(meter),
            invocation_ref_sha256=self.invocation("tamper"),
        )
        tampered = copy.deepcopy(result.receipt)
        tampered["caller_supplied_callback_accepted"] = True
        unsigned = dict(tampered)
        unsigned.pop("assembly_receipt_sha256")
        tampered["assembly_receipt_sha256"] = object_sha256(unsigned)
        with self.assertRaisesRegex(ValueError, "drifted"):
            validate_candidate_runtime_assembly_receipt(tampered)

    def test_capability_and_authorization_flags_are_exact(self) -> None:
        for value in (
            KNOWN_ADAPTER_EXACT_TYPE_ENFORCEMENT_IMPLEMENTED,
            KNOWN_REQUEST_EXACT_TYPE_ENFORCEMENT_IMPLEMENTED,
            ALL_EFFECTS_ROUTED_THROUGH_DURABLE_DEADLINE_SCHEDULER,
            POST_SETTLEMENT_TYPED_PROCESSING_IMPLEMENTED,
        ):
            self.assertTrue(value)
        for value in (
            CALLER_SUPPLIED_CALLBACK_INTERFACE_IMPLEMENTED,
            ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED,
            SCHEMA_RESEALING_WITHOUT_SECRET_CRYPTOGRAPHICALLY_EXCLUDED,
            PRODUCTION_PACKAGE_AUTHORIZED,
            ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
            ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
            EXTERNAL_SIDE_EFFECT_AUTHORIZED,
            BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
            DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
            SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
            LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
        ):
            self.assertFalse(value)


if __name__ == "__main__":
    unittest.main()
