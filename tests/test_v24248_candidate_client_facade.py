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

from deepwide_agent.v24233_webswarm_effect_preauthorization import (  # noqa: E402
    initialize_effect_preauthorization_state,
)
from deepwide_agent.v24236_azure_responses_single_attempt import (  # noqa: E402
    AzureResponsesSingleAttemptAdapter,
)
from deepwide_agent.v24237_tavily_search_single_attempt import (  # noqa: E402
    TavilySearchSingleAttemptAdapter,
)
from deepwide_agent.v24239_azure_hosted_search_single_attempt import (  # noqa: E402
    AzureHostedSearchSingleAttemptAdapter,
)
from deepwide_agent.v24240_anthropic_server_search_single_attempt import (  # noqa: E402
    AnthropicServerSearchSingleAttemptAdapter,
)
from deepwide_agent.v24242_durable_effect_coordinator import (  # noqa: E402
    DurableEffectReplayRejected,
    DurablePreauthorizedEffectCoordinator,
)
from deepwide_agent.v24243_retry_deadline_scheduler import (  # noqa: E402
    RetryDeadlineEffectScheduler,
)
from deepwide_agent.v24244_strict_json_parser_boundary import (  # noqa: E402
    build_strict_json_parser_contract,
)
from deepwide_agent.v24245_pinned_native_http_fetch import (  # noqa: E402
    PinnedNativeHttpFetchAdapter,
)
from deepwide_agent.v24246_search_page_projection import (  # noqa: E402
    PageTextProjection,
    SearchLeadProjection,
    build_search_page_projection_contract,
)
from deepwide_agent.v24247_candidate_runtime_assembly import (  # noqa: E402
    CandidateRuntimeAssembly,
    build_candidate_runtime_assembly_contract,
)
from deepwide_agent.v24248_candidate_client_facade import (  # noqa: E402
    ACTIVE_FORWARD_INTEGRATION_AUTHORIZED,
    ACTIVE_PROVIDER_TRAFFIC_AUTHORIZED,
    ADAPTER_CODE_IDENTITY_INDEPENDENTLY_ATTESTED,
    BENCHMARK_FORWARD_OR_EVALUATOR_AUTHORIZED,
    CALLER_ACTION_REF_SEMANTIC_INDEPENDENCE_VERIFIED,
    CONTENT_FREE_ACTION_REF_DERIVATION_IMPLEMENTED,
    DEV64_OR_EXACT220_LAUNCH_AUTHORIZED,
    EXACT_ADAPTER_AND_ASSEMBLY_TYPE_ENFORCEMENT_IMPLEMENTED,
    EXTERNAL_SIDE_EFFECT_AUTHORIZED,
    FROZEN_PROVIDER_METER_AND_DEADLINE_CONTRACTS_IMPLEMENTED,
    LEADERBOARD_SUBMISSION_OR_SOTA_CLAIM_AUTHORIZED,
    LEGACY_RUNTIME_CLIENT_SURFACE_IMPLEMENTED,
    PRODUCTION_PACKAGE_AUTHORIZED,
    SCHEMA_RESEALING_WITHOUT_SECRET_CRYPTOGRAPHICALLY_EXCLUDED,
    SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED,
    SHARED_API_LEASE_ACQUIRE_AUTHORIZED,
    CandidateClientFacade,
    CandidateClientFacadeError,
    build_candidate_client_facade_contract,
    derive_candidate_facade_action_ref,
    validate_candidate_client_facade_contract,
    validate_candidate_client_facade_receipt,
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


class V24248CandidateClientFacadeTests(unittest.TestCase):
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
            journal_namespace_sha256=digest("v24248-journal"),
            initial_state=initial,
            **self.coordinator_shared,
        )
        clock = VirtualClock()
        self.assembly_contract = build_candidate_runtime_assembly_contract(
            model_parser_contract=build_strict_json_parser_contract(
                maximum_text_characters=2000,
                maximum_utf8_bytes=4000,
                maximum_depth=8,
                maximum_nodes=100,
                maximum_object_members=20,
                maximum_array_items=20,
                maximum_string_characters=500,
            ),
            search_page_projection_contract=build_search_page_projection_contract(
                maximum_leads=8,
                maximum_page_bytes=4096,
                maximum_page_text_characters=500,
                maximum_title_characters=100,
                maximum_url_characters=1024,
                maximum_html_tags=100,
            ),
        )
        self.assembly = CandidateRuntimeAssembly(
            scheduler=RetryDeadlineEffectScheduler(
                coordinator=self.coordinator,
                monotonic_ns=clock.monotonic_ns,
                sleeper=clock.sleep,
            ),
            assembly_contract=self.assembly_contract,
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

    def facade_contract(
        self,
        provider: str = "tavily_search_api",
        *,
        model_attempts: int = 1,
        search_attempts: int = 1,
        fetch_attempts: int = 1,
        search_tool_calls: int | None = None,
    ):
        hosted = provider != "tavily_search_api"
        anthropic = provider == "anthropic_server_web_search"
        return build_candidate_client_facade_contract(
            assembly_contract=self.assembly_contract,
            search_provider_kind=provider,
            model_maximum_prompt_utf8_bytes=4000,
            model_maximum_output_tokens=200,
            model_reasoning_effort="high",
            model_service_tier="priority",
            model_timeout_seconds=1,
            model_max_attempts=model_attempts,
            model_reserved_input_tokens_per_attempt=8096,
            search_maximum_query_utf8_bytes=2000,
            search_maximum_output_tokens=200 if hosted else 0,
            search_maximum_provider_tool_calls_per_attempt=(
                search_tool_calls
                if search_tool_calls is not None
                else 2
                if anthropic
                else 1
                if hosted
                else 0
            ),
            search_maximum_results=2,
            search_context_size="" if anthropic or not hosted else "medium",
            search_reasoning_effort="" if anthropic or not hosted else "high",
            search_service_tier="" if anthropic or not hosted else "priority",
            search_timeout_seconds=1,
            search_max_attempts=search_attempts,
            search_reserved_input_tokens_per_attempt=6096 if hosted else 0,
            fetch_maximum_response_bytes=4096,
            fetch_timeout_seconds=1,
            fetch_max_attempts=fetch_attempts,
            initial_backoff_milliseconds=10,
            backoff_multiplier=2,
            maximum_backoff_milliseconds=100,
            deadline_margin_milliseconds=100,
        )

    def build_facade(
        self,
        *,
        provider: str = "tavily_search_api",
        model_post=None,
        search_post=None,
        fetch_response=None,
        model_attempts: int = 1,
        search_attempts: int = 1,
        fetch_attempts: int = 1,
        search_tool_calls: int | None = None,
    ):
        contract_value = self.facade_contract(
            provider,
            model_attempts=model_attempts,
            search_attempts=search_attempts,
            fetch_attempts=fetch_attempts,
            search_tool_calls=search_tool_calls,
        )
        model_adapter = AzureResponsesSingleAttemptAdapter(
            endpoint="http://127.0.0.1:9878/responses",
            model="gpt-5.6-sol",
            timeout_seconds=1,
            post=model_post
            or ModelPost(ModelResponse(200, model_response_bytes())),
        )
        if provider == "tavily_search_api":
            search_adapter = TavilySearchSingleAttemptAdapter(
                endpoint="https://api.tavily.com/search",
                credentials=tuple(
                    f"synthetic-credential-{index}"
                    for index in range(1, search_attempts + 1)
                ),
                timeout_seconds=1,
                post=search_post
                or TavilyPost(TavilyResponse(200, tavily_response_bytes())),
            )
        elif provider == "azure_responses_web_search":
            search_adapter = AzureHostedSearchSingleAttemptAdapter(
                endpoint="http://127.0.0.1:9878/responses",
                model="gpt-5.6-sol",
                timeout_seconds=1,
                post=search_post
                or HostedPost(HostedResponse(200, hosted_response_bytes())),
            )
        else:
            search_adapter = AnthropicServerSearchSingleAttemptAdapter(
                endpoint="https://api.anthropic.com/v1/messages",
                model="claude-haiku-4-5-20251001",
                anthropic_version="2023-06-01",
                credential="synthetic-anthropic-credential",
                timeout_seconds=1,
                post=search_post
                or AnthropicPost(
                    AnthropicResponse(200, anthropic_response_bytes())
                ),
            )
        response = fetch_response or FetchResponse(
            200,
            [b"<html><body>synthetic page</body></html>"],
            headers={"Content-Type": "text/html; charset=utf-8"},
        )
        fetch_factory = RecordingPoolFactory(response)
        facade = CandidateClientFacade(
            assembly=self.assembly,
            facade_contract=contract_value,
            model_adapter=model_adapter,
            search_adapter=search_adapter,
            fetch_adapter=PinnedNativeHttpFetchAdapter(
                timeout_seconds=1,
                max_response_bytes=4096,
                resolve=RecordingResolver(("93.184.216.34",)),
                pool_factory=fetch_factory,
            ),
        )
        return facade, contract_value, model_adapter, search_adapter, fetch_factory

    def action(self, operation: str, ordinal: int) -> str:
        return derive_candidate_facade_action_ref(
            task_scope_ref_sha256=digest("opaque-task-scope"),
            stage_ref_sha256=digest("visible-stage"),
            operation_kind=operation,
            action_ordinal=ordinal,
        )

    def test_contract_freezes_conservative_provider_budgets(self) -> None:
        for provider in (
            "tavily_search_api",
            "azure_responses_web_search",
            "anthropic_server_web_search",
        ):
            with self.subTest(provider=provider):
                value = self.facade_contract(provider)
                validate_candidate_client_facade_contract(value)
                self.assertEqual(value["search_provider_kind"], provider)
                self.assertGreaterEqual(
                    value["model_meter_contract"]["reserved_cost"][
                        "wall_milliseconds"
                    ],
                    value["model_scheduler_contract"][
                        "total_deadline_milliseconds"
                    ],
                )
                self.assertFalse(value["legacy_runtime_client_surface_implemented"])
                self.assertFalse(
                    value[
                        "search_leads_or_page_text_active_evidence_eligibility_granted"
                    ]
                )
        tampered = copy.deepcopy(self.facade_contract())
        tampered["search_maximum_results"] = 9
        with self.assertRaisesRegex(ValueError, "drifted"):
            validate_candidate_client_facade_contract(tampered)

    def test_action_ref_is_content_free_deterministic_and_typed(self) -> None:
        first = self.action("model_json", 1)
        second = self.action("model_json", 1)
        self.assertEqual(first, second)
        self.assertNotEqual(first, self.action("search_leads", 1))
        self.assertNotEqual(first, self.action("model_json", 2))
        with self.assertRaises(ValueError):
            derive_candidate_facade_action_ref(
                task_scope_ref_sha256="not-a-digest",
                stage_ref_sha256=digest("stage"),
                operation_kind="model_json",
                action_ordinal=1,
            )
        facade, _, _, _, _ = self.build_facade()
        before = self.coordinator.journal.load()["state_sha256"]
        with self.assertRaises(CandidateClientFacadeError):
            facade.run_model_json(
                action_ref=self.action("search_leads", 99),
                system="visible system",
                user="visible user",
                max_output_tokens=200,
            )
        self.assertEqual(before, self.coordinator.journal.load()["state_sha256"])

    def test_model_returns_ephemeral_json_and_content_free_receipt(self) -> None:
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
        facade, _, _, _, _ = self.build_facade(model_post=post)
        result = facade.run_model_json(
            action_ref=self.action("model_json", 1),
            system="private system prompt",
            user="private user prompt",
            max_output_tokens=200,
        )
        validate_candidate_client_facade_receipt(result.receipt)
        self.assertEqual(result.value["value"], private)
        self.assertEqual(len(post.calls), 1)
        encoded = repr(result.receipt)
        for item in (private, "private system prompt", "private user prompt"):
            self.assertNotIn(item, encoded)
        self.assertFalse(
            result.receipt[
                "raw_prompt_query_url_provider_value_or_projected_output_entered_receipt"
            ]
        )
        self.assertFalse(result.receipt["facade_created_new_ephemeral_content_hash"])
        self.assertTrue(
            result.receipt["parent_provider_response_reference_retained"]
        )

    def test_three_search_providers_return_only_quarantined_leads(self) -> None:
        cases = (
            (
                "tavily_search_api",
                TavilyPost(
                    TavilyResponse(
                        200,
                        tavily_response_bytes(
                            answer="PRIVATE_ANSWER",
                            results=[
                                {
                                    "title": "Synthetic title",
                                    "url": "https://example.com/page",
                                    "content": "PRIVATE_SNIPPET",
                                    "raw_content": "PRIVATE_RAW",
                                    "score": 0.9,
                                }
                            ],
                        ),
                    )
                ),
            ),
            (
                "azure_responses_web_search",
                HostedPost(
                    HostedResponse(
                        200,
                        hosted_response_bytes(
                            text="PRIVATE_ANSWER",
                            input_tokens=20,
                            output_tokens=5,
                            action_count=1,
                        ),
                    )
                ),
            ),
            (
                "anthropic_server_web_search",
                AnthropicPost(
                    AnthropicResponse(
                        200,
                        anthropic_response_bytes(
                            text="PRIVATE_ANSWER",
                            input_tokens=15,
                            output_tokens=5,
                            cache_creation_tokens=3,
                            cache_read_tokens=2,
                            action_count=1,
                        ),
                    )
                ),
            ),
        )
        for index, (provider, post) in enumerate(cases, start=1):
            with self.subTest(provider=provider):
                facade, _, _, _, _ = self.build_facade(
                    provider=provider,
                    search_post=post,
                )
                result = facade.run_search_leads(
                    action_ref=self.action("search_leads", index),
                    query="private visible query",
                    max_results=1,
                )
                validate_candidate_client_facade_receipt(result.receipt)
                self.assertTrue(result.value)
                self.assertTrue(
                    all(type(item) is SearchLeadProjection for item in result.value)
                )
                self.assertFalse(
                    result.receipt[
                        "search_leads_or_page_text_active_evidence_eligibility_granted"
                    ]
                )
                self.assertNotIn("private visible query", repr(result.receipt))
                self.assertNotIn("PRIVATE_ANSWER", repr(result.receipt))

    def test_hosted_search_result_limit_is_truncated_and_receipted(self) -> None:
        post = HostedPost(
            HostedResponse(
                200,
                hosted_response_bytes(
                    text="PRIVATE_ANSWER",
                    input_tokens=20,
                    output_tokens=5,
                    action_count=2,
                ),
            )
        )
        facade, _, _, _, _ = self.build_facade(
            provider="azure_responses_web_search",
            search_post=post,
            search_tool_calls=2,
        )
        result = facade.run_search_leads(
            action_ref=self.action("search_leads", 30),
            query="visible query",
            max_results=1,
        )
        validate_candidate_client_facade_receipt(result.receipt)
        self.assertEqual(len(result.value), 1)
        self.assertEqual(result.receipt["assembly_value_item_count"], 2)
        self.assertEqual(result.receipt["requested_value_item_limit"], 1)
        self.assertEqual(result.receipt["returned_value_item_count"], 1)
        self.assertTrue(result.receipt["facade_value_truncation_applied"])

    def test_fetch_returns_untrusted_page_without_evidence_authority(self) -> None:
        private = b"<html><body>PRIVATE_PAGE<script>PRIVATE_SCRIPT</script></body></html>"
        facade, _, _, _, factory = self.build_facade(
            fetch_response=FetchResponse(
                200,
                [private],
                headers={"Content-Type": "text/html; charset=utf-8"},
            )
        )
        result = facade.run_fetched_page(
            action_ref=self.action("fetched_page", 1),
            url="https://example.com/page",
        )
        validate_candidate_client_facade_receipt(result.receipt)
        self.assertIs(type(result.value), PageTextProjection)
        self.assertEqual(result.value.text, "PRIVATE_PAGE")
        self.assertTrue(result.value.untrusted_data)
        self.assertFalse(result.value.instruction_authority)
        self.assertFalse(result.value.active_evidence_eligible)
        self.assertEqual(len(factory.pools), 1)
        self.assertNotIn("PRIVATE_PAGE", repr(result.receipt))
        self.assertNotIn("example.com", repr(result.receipt))

    def test_same_action_ref_replay_is_rejected_before_second_effect(self) -> None:
        post = ModelPost(
            ModelResponse(200, model_response_bytes(text='{"ready":true}'))
        )
        facade, _, _, _, _ = self.build_facade(model_post=post)
        action = self.action("model_json", 7)
        first = facade.run_model_json(
            action_ref=action,
            system="first private system",
            user="first private user",
            max_output_tokens=200,
        )
        with self.assertRaises(DurableEffectReplayRejected):
            facade.run_model_json(
                action_ref=action,
                system="different private system",
                user="different private user",
                max_output_tokens=200,
            )
        self.assertEqual(len(post.calls), 1)
        self.assertEqual(
            first.receipt["invocation_ref_sha256"],
            first.receipt["assembly_receipt"]["invocation_ref_sha256"],
        )

    def test_frozen_two_attempt_model_budget_covers_retry_then_success(self) -> None:
        post = ModelPost(
            ModelResponse(429, b"{}"),
            ModelResponse(
                200,
                model_response_bytes(
                    text='{"ready":true}',
                    input_tokens=20,
                    output_tokens=5,
                ),
            ),
        )
        facade, contract_value, _, _, _ = self.build_facade(
            model_post=post,
            model_attempts=2,
        )
        result = facade.run_model_json(
            action_ref=self.action("model_json", 31),
            system="visible system",
            user="visible user",
            max_output_tokens=200,
        )
        validate_candidate_client_facade_receipt(result.receipt)
        self.assertEqual(len(post.calls), 2)
        self.assertEqual(result.receipt["attempt_count"], 2)
        self.assertEqual(
            contract_value["model_meter_contract"]["max_attempts"], 2
        )
        self.assertGreaterEqual(
            contract_value["model_meter_contract"]["reserved_cost"][
                "wall_milliseconds"
            ],
            contract_value["model_scheduler_contract"][
                "total_deadline_milliseconds"
            ]
            + 1,
        )

    def test_limits_and_wrong_adapter_fail_before_effect(self) -> None:
        post = ModelPost(ModelResponse(200, model_response_bytes()))
        facade, value, _, _, _ = self.build_facade(model_post=post)
        before = self.coordinator.journal.load()["state_sha256"]
        with self.assertRaises(CandidateClientFacadeError):
            facade.run_model_json(
                action_ref=self.action("model_json", 8),
                system="x" * 4001,
                user="y",
                max_output_tokens=200,
            )
        with self.assertRaises(CandidateClientFacadeError):
            facade.run_search_leads(
                action_ref=self.action("search_leads", 8),
                query="visible",
                max_results=3,
            )
        after = self.coordinator.journal.load()["state_sha256"]
        self.assertEqual(before, after)
        self.assertEqual(post.calls, [])

        class Subclass(TavilySearchSingleAttemptAdapter):
            pass

        with self.assertRaisesRegex(ValueError, "exact type"):
            CandidateClientFacade(
                assembly=self.assembly,
                facade_contract=value,
                model_adapter=AzureResponsesSingleAttemptAdapter(
                    endpoint="http://127.0.0.1:9878/responses",
                    model="gpt-5.6-sol",
                    timeout_seconds=1,
                    post=post,
                ),
                search_adapter=Subclass(
                    endpoint="https://api.tavily.com/search",
                    credentials=("synthetic-credential",),
                    timeout_seconds=1,
                    post=TavilyPost(TavilyResponse(200, tavily_response_bytes())),
                ),
                fetch_adapter=PinnedNativeHttpFetchAdapter(
                    timeout_seconds=1,
                    max_response_bytes=4096,
                    resolve=RecordingResolver(("93.184.216.34",)),
                    pool_factory=RecordingPoolFactory(
                        FetchResponse(200, [b"x"])
                    ),
                ),
            )

    def test_contract_mutation_is_revalidated_before_effect(self) -> None:
        post = ModelPost(
            ModelResponse(200, model_response_bytes(text='{"ready":true}'))
        )
        facade, _, _, _, _ = self.build_facade(model_post=post)
        before = self.coordinator.journal.load()["state_sha256"]
        facade._contract["model_maximum_output_tokens"] = 201
        with self.assertRaisesRegex(ValueError, "drifted"):
            facade.run_model_json(
                action_ref=self.action("model_json", 40),
                system="visible system",
                user="visible user",
                max_output_tokens=200,
            )
        self.assertEqual(before, self.coordinator.journal.load()["state_sha256"])
        self.assertEqual(post.calls, [])

    def test_transport_identity_mutation_is_rejected_before_effect(self) -> None:
        post = ModelPost(
            ModelResponse(200, model_response_bytes(text='{"ready":true}'))
        )
        facade, _, model_adapter, _, _ = self.build_facade(model_post=post)
        before = self.coordinator.journal.load()["state_sha256"]
        model_adapter._post = lambda *_args, **_kwargs: None
        with self.assertRaisesRegex(CandidateClientFacadeError, "binding drifted"):
            facade.run_model_json(
                action_ref=self.action("model_json", 41),
                system="visible system",
                user="visible user",
                max_output_tokens=200,
            )
        self.assertEqual(before, self.coordinator.journal.load()["state_sha256"])
        self.assertEqual(post.calls, [])

    def test_adapter_configuration_mutation_is_rejected_before_effect(self) -> None:
        post = ModelPost(
            ModelResponse(200, model_response_bytes(text='{"ready":true}'))
        )
        facade, _, model_adapter, _, _ = self.build_facade(model_post=post)
        before = self.coordinator.journal.load()["state_sha256"]
        model_adapter._model = "mutated-model"
        with self.assertRaisesRegex(CandidateClientFacadeError, "binding drifted"):
            facade.run_model_json(
                action_ref=self.action("model_json", 42),
                system="visible system",
                user="visible user",
                max_output_tokens=200,
            )
        self.assertEqual(before, self.coordinator.journal.load()["state_sha256"])
        self.assertEqual(post.calls, [])

    def test_public_surface_has_no_callback_or_legacy_drop_in_methods(self) -> None:
        for name in ("run_model_json", "run_search_leads", "run_fetched_page"):
            parameters = inspect.signature(getattr(CandidateClientFacade, name)).parameters
            self.assertNotIn("callback", parameters)
            self.assertNotIn("fault_hook", parameters)
        self.assertFalse(hasattr(CandidateClientFacade, "complete_json"))
        self.assertFalse(hasattr(CandidateClientFacade, "search_many"))
        self.assertFalse(hasattr(CandidateClientFacade, "fetch_urls"))

    def test_receipt_tamper_and_reseal_fail_closed(self) -> None:
        facade, _, _, _, _ = self.build_facade()
        result = facade.run_search_leads(
            action_ref=self.action("search_leads", 20),
            query="visible",
            max_results=1,
        )
        tampered = copy.deepcopy(result.receipt)
        tampered["legacy_runtime_client_surface_implemented"] = True
        unsigned = dict(tampered)
        unsigned.pop("facade_receipt_sha256")
        from deepwide_agent.v24232_webswarm_total_budget import object_sha256

        tampered["facade_receipt_sha256"] = object_sha256(unsigned)
        with self.assertRaisesRegex(ValueError, "drifted"):
            validate_candidate_client_facade_receipt(tampered)

    def test_capability_and_authorization_flags_are_exact(self) -> None:
        for value in (
            CONTENT_FREE_ACTION_REF_DERIVATION_IMPLEMENTED,
            FROZEN_PROVIDER_METER_AND_DEADLINE_CONTRACTS_IMPLEMENTED,
            EXACT_ADAPTER_AND_ASSEMBLY_TYPE_ENFORCEMENT_IMPLEMENTED,
        ):
            self.assertTrue(value)
        for value in (
            LEGACY_RUNTIME_CLIENT_SURFACE_IMPLEMENTED,
            SEARCH_LEADS_OR_PAGE_TEXT_ACTIVE_EVIDENCE_ELIGIBILITY_GRANTED,
            CALLER_ACTION_REF_SEMANTIC_INDEPENDENCE_VERIFIED,
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
